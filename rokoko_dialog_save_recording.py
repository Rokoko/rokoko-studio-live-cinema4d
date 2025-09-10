'''This dialog is used in two ways. Either from Player (Manager dialog) in
order to save or bake a current recording (optionally including data from
Clip(s)). Or to bake a Clip from within a Rokoko tag. Besides hiding some
options in the latter case, the dialog is also owned differently. In the first
case the Manager dialog owns this dialog, in the later case the tag owns
the dialog.

Currently all baking logic (creation of curves, keyframes, Takes and overrides)
is within this dialog. Which was a very questionable decision, most likely this
code will be merged into the tag in future.
'''

import os

import c4d

import rokoko_ids as rid
from rokoko_rig_tables import (
    FACE_POSE_NAMES,
    STUDIO_NAMES_TO_GUESS,
)
from rokoko_utils import (
    AddDataSetBC,
    GetConnectedDataSet,
    GetConnectedDataSetId,
    GetDataSetFromId,
    GetPref,
    GetProjectScale,
    JSONQuaternionToMatrix,
    MyHash,
    SetPref,
)
from rokoko_listener import GetListenerThread
from rokoko_dialog_utils import CreateLayoutAddGroupBar


g_thdListener = GetListenerThread()  # owned by rokoko_listener
g_studioTPose = {}  # created and owned by rokoko_plugin_registration


# A note on this module:
# This module is probably the dirtiest code section of the plugin.
# Unfortunately I lacked the time before release to properly clean this up
# and also test those changes.
# This is not meant to be an excuse. It should have been written properly
# right away...
# Anyway, the result is quite a bit of code duplication (from rokoko_tag) and
# some functionality implemented here, which should have been implemented
# in rokoko_tag instead.
# It is planned to implement the changes before testing of the next release
# (not talking about potential bug fix releases here).


def DlgSaveSetGlobalStudioTPose(tPose):
    '''After Studio T-Pose has been loaded during startup in
    rokoko_plugin_registration, its reference is made available here.
    '''

    global g_studioTPose
    g_studioTPose = tPose


def DlgSaveDestroyGlobals():
    '''To be called during shutdown'''

    global g_studioTPose
    global g_thdListener

    g_studioTPose = {}
    g_thdListener = None


class DialogSaveRecording(c4d.gui.GeDialog):
    # reference to parenting Manager dialog, used to trigger updates and
    # re-enable it, when closing
    _dlgParent = None
    # when opened from a tag, the dialog will hide the save options and
    # only allows baking of an existing clip
    _bakingOnly = False
    # Set to True as soon as the user saves or bakes at least a part of clip
    _clipStored = False
    # list of tags involved in the baking process
    _tags = None
    # last valid frame index for the sliders
    _idxFrameLast = 0

    # Most relevant entry points:
    # - CreateLayout()
    # - InitValues()
    # - Message()
    # - Command()

    def __init__(self, dlgParent, tags=None, bakingOnly=False):
        # in case of a tag being parent, _dlgParent may be None
        self._dlgParent = dlgParent
        self._bakingOnly = bakingOnly

        # If no tags were passed, use the tags currently registered in Player
        if tags is None:
            self._tags = g_thdListener.GetTagConsumers()
        else:
            self._tags = tags

        # In case the dialog was opened from a tag, we need to backup current
        # state, so it can be restored, when dialog gets closed
        if self._bakingOnly:
            g_thdListener.StoreCurrentPositions(self._tags)

        # Determine length of sliders
        self._idxFrameLast = 0
        idConnected = GetConnectedDataSetId()
        includeDataSets = GetPref(rid.ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS)
        for tag in self._tags:
            if not tag[rid.ID_TAG_VALID_DATA]:  # only valid data can be baked
                continue

            idDataSet = tag[rid.ID_TAG_DATA_SET]

            # Skip clips, if not not explicitly enabled by the user
            # via "Include Clips"
            # (or we are here for the purpose of baking a clip)
            if not includeDataSets and idDataSet != idConnected and \
               not self._bakingOnly:
                continue

            # Last valid frame index is calculated a bit differently,
            # if it's a clip
            if idDataSet == idConnected:
                self._idxFrameLast = max(
                    g_thdListener.GetDataSetSize(idDataSet),
                    self._idxFrameLast)
            else:
                idxFrameLast = tag[rid.ID_TAG_DATA_SET_LAST_FRAME]
                idxFrameFirst = tag[rid.ID_TAG_DATA_SET_FIRST_FRAME]
                # TODO: Likely a bug, should be:
                #       idxFrameLast - idxFrameFirst - 1
                #       OR: Wrong in 372: (+1)
                self._idxFrameLast = max(
                    idxFrameLast - idxFrameFirst, self._idxFrameLast)

            # In case the dialog was opened from a tag, register the tag as
            # consumer and set its execution flag
            if self._bakingOnly:
                g_thdListener.AddTagConsumer(tag.GetNodeData(), tag)
                tag[rid.ID_TAG_EXECUTE_MODE] = 1

        c4d.gui.GeDialog.__init__(self)

    def CreateLayout(self):
        '''Called by C4D to draw the dialog'''

        # Window title
        if self._bakingOnly:
            self.SetTitle("Bake Clip...")
        else:
            self.SetTitle("Save Recording...")

        if self.GroupBegin(  # Dialog main group
                rid.ID_DLGSAVE_GROUP_MAIN,
                c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=1):
            self.GroupBorderSpace(5, 5, 10, 5)

            CreateLayoutAddGroupBar(self, "Frame Range")

            if self.GroupBegin(  # Frame range
                    0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2):
                self.GroupBorderSpace(10, 0, 0, 0)

                # Row 1
                self.AddStaticText(0, c4d.BFH_LEFT, name="First Frame")
                self.AddEditSlider(
                    rid.ID_DLGSAVE_FIRST_FRAME, c4d.BFH_SCALEFIT)

                # Row 2
                self.AddStaticText(0, c4d.BFH_LEFT, name="Last Frame")
                self.AddEditSlider(rid.ID_DLGSAVE_LAST_FRAME, c4d.BFH_SCALEFIT)
            self.GroupEnd()  # Frame range

            CreateLayoutAddGroupBar(self, "Bake Keyframes")

            if self.GroupBegin(  # Bake keyframes
                    0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=3):
                self.GroupBorderSpace(10, 0, 0, 0)

                # Row 1
                self.AddStaticText(0, c4d.BFH_SCALEFIT, name="Timing")
                self.AddComboBox(rid.ID_DLGSAVE_TIMING, c4d.BFH_SCALEFIT)
                self.AddChild(rid.ID_DLGSAVE_TIMING, 0, "Studio Time")
                self.AddChild(rid.ID_DLGSAVE_TIMING, 1, "By Frame")
                self.AddStaticText(0, c4d.BFH_SCALEFIT, name="")  # Dummy

                # Row 2
                self.AddStaticText(0, c4d.BFH_SCALEFIT, name="Skip Frames")
                self.AddComboBox(rid.ID_DLGSAVE_FRAME_SKIP, c4d.BFH_SCALEFIT)
                self.AddStaticText(0, c4d.BFH_SCALEFIT, name="")  # Dummy

                # Row 3
                self.AddStaticText(0, c4d.BFH_SCALEFIT, name="Length")
                self.AddComboBox(rid.ID_DLGSAVE_LENGTH, c4d.BFH_SCALEFIT)
                self.AddChild(
                    rid.ID_DLGSAVE_LENGTH, 0, "Extend Project's End Time")
                self.AddChild(
                    rid.ID_DLGSAVE_LENGTH, 1, "Stop at Project's End Time")
                self.AddChild(
                    rid.ID_DLGSAVE_LENGTH, 2, "Ignore")
                self.AddStaticText(0, c4d.BFH_SCALEFIT, name="")  # Dummy

                # Row 4
                self.AddCheckbox(rid.ID_DLGSAVE_CREATE_IN_TAKE,
                                 c4d.BFH_SCALEFIT,
                                 name="Create New Take",
                                 initw=0, inith=0)
                self.AddCheckbox(rid.ID_DLGSAVE_ACTIVATE_NEW_TAKE,
                                 c4d.BFH_SCALEFIT,
                                 name="Activate New Take",
                                 initw=0, inith=0)
                self.AddStaticText(0, c4d.BFH_SCALEFIT, name="")  # Dummy

                # Row 5
                self.AddCheckbox(rid.ID_DLGSAVE_WIPE_EXISTING_ANIMATION,
                                 c4d.BFH_SCALEFIT,
                                 name="Wipe Existing Animation",
                                 initw=0, inith=0)
                self.AddCheckbox(rid.ID_DLGSAVE_SET_KEYFRAMES_AUTOFORWARD,
                                 c4d.BFH_SCALEFIT,
                                 name="Advance Current Frame",
                                 initw=0, inith=0)
                if not self._bakingOnly:
                    self.AddCheckbox(rid.ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS,
                                     c4d.BFH_SCALEFIT,
                                     name="Include File Clips",
                                     initw=0, inith=0)
                else:
                    self.AddStaticText(0, c4d.BFH_SCALEFIT, name="")  # Dummy

                # Row 6
                self.AddButton(rid.ID_DLGSAVE_SET_KEYFRAMES_AT_0,
                               c4d.BFH_SCALEFIT,
                               name="Bake Keyframes at 0")
                self.AddButton(rid.ID_DLGSAVE_SET_KEYFRAMES_AT_CURRENT,
                               c4d.BFH_SCALEFIT,
                               name="Bake Keyframes at Current")
                self.AddStaticText(0, c4d.BFH_SCALEFIT, name="")  # Dummy
            self.GroupEnd()  # Bake keyframes

            if not self._bakingOnly:

                CreateLayoutAddGroupBar(self, "Save Clip to File")

                if self.GroupBegin(  # Save clip parameters
                        0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2):
                    self.GroupBorderSpace(10, 0, 0, 0)

                    # Row 1
                    self.AddStaticText(0, c4d.BFH_LEFT, name="Clip Name")
                    self.AddEditText(
                        rid.ID_DLGSAVE_NAME_DATASET, c4d.BFH_SCALEFIT)

                    # Row 2
                    self.AddStaticText(0, c4d.BFH_LEFT, name="Path")
                    if self.GroupBegin(  # Path string and button
                            0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2):
                        self.AddEditText(
                            rid.ID_DLGSAVE_PATH_DATASET, c4d.BFH_SCALEFIT)
                        self.AddButton(rid.ID_DLGSAVE_SET_PATH_DATASET,
                                       c4d.BFH_RIGHT,
                                       name="...", initw=30)
                    self.GroupEnd()  # Path string and button
                self.GroupEnd()  # Save clip parameters

                if self.GroupBegin(  # Save clip buttons
                        0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=3):
                    self.GroupBorderSpace(10, 0, 0, 0)

                    # Row 1
                    self.AddButton(rid.ID_DLGSAVE_STORE_GLOBAL_DATA,
                                   c4d.BFH_SCALEFIT,
                                   name="Store Global Clip")
                    self.AddButton(rid.ID_DLGSAVE_STORE_LOCAL_DATA,
                                   c4d.BFH_SCALEFIT,
                                   name="Store Clip in Project")
                    self.AddCheckbox(rid.ID_DLGSAVE_USE_NEW_DATASET,
                                     c4d.BFH_SCALEFIT,
                                     name="Use New Clip",
                                     initw=0, inith=0)
                self.GroupEnd()  # Save clip buttons

            # Discard button currently not shown in UI
            #    self.AddButton(ID_DLGSAVE_DISCARD,
            #                   c4d.BFH_SCALEFIT,
            #                   name="DISCARD RECORDING")
            # else:
            #    self.AddButton(ID_DLGSAVE_DISCARD,
            #                   c4d.BFH_SCALEFIT,
            #                   name="Close")
        self.GroupEnd()  # Dialog main group
        return True

    def UpdateComboSkipFrames(self):
        '''Depending on timing option chosen by user,
        there are different options available in "Skip Frames" combo box
        '''

        skipFramesOld = self.GetInt32(rid.ID_DLGSAVE_FRAME_SKIP)
        self.FreeChildren(rid.ID_DLGSAVE_FRAME_SKIP)
        self.AddChild(rid.ID_DLGSAVE_FRAME_SKIP, 1, "None")
        self.AddChild(rid.ID_DLGSAVE_FRAME_SKIP, 1001, "")
        self.AddChild(
            rid.ID_DLGSAVE_FRAME_SKIP, 2, "2:1 (every 2nd Studio Frame)")
        self.AddChild(rid.ID_DLGSAVE_FRAME_SKIP, 3, "3:1")
        self.AddChild(rid.ID_DLGSAVE_FRAME_SKIP, 4, "4:1")

        if self.GetInt32(rid.ID_DLGSAVE_TIMING) == 0:
            doc = c4d.documents.GetActiveDocument()
            self.AddChild(rid.ID_DLGSAVE_FRAME_SKIP, 1002, "")
            self.AddChild(rid.ID_DLGSAVE_FRAME_SKIP, 500,
                          f"{doc.GetFps()} FPS (Project)")
            self.AddChild(rid.ID_DLGSAVE_FRAME_SKIP, 1003, "")
            self.AddChild(rid.ID_DLGSAVE_FRAME_SKIP, 10, "10 FPS")
            self.AddChild(rid.ID_DLGSAVE_FRAME_SKIP, 24, "24 FPS")
            self.AddChild(rid.ID_DLGSAVE_FRAME_SKIP, 25, "25 FPS")
            self.AddChild(rid.ID_DLGSAVE_FRAME_SKIP, 30, "30 FPS")
            self.AddChild(rid.ID_DLGSAVE_FRAME_SKIP, 60, "60 FPS")
            self.AddChild(rid.ID_DLGSAVE_FRAME_SKIP, 100, "100 FPS")

        # Upon reinitilization the combo box looses its value.
        # Restore previous value and choose a default if previous selected
        # option is no longer available.
        self.SetInt32(rid.ID_DLGSAVE_FRAME_SKIP, skipFramesOld)
        if self.GetInt32(rid.ID_DLGSAVE_TIMING) == 1 and \
           self.GetInt32(rid.ID_DLGSAVE_FRAME_SKIP) > 4:
            self.SetInt32(rid.ID_DLGSAVE_FRAME_SKIP, 1)

    def UpdateSliders(self):
        '''The number of frames available changes depending on "Include Clips"
        option.

        UpdateSliders() calculates the last valid frame index and sets sliders
        accordingly.
        '''

        idConnected = GetConnectedDataSetId()
        includeDataSets = self.GetBool(rid.ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS)
        self._idxFrameLast = 0

        # Determine last valid frame index
        for tag in self._tags:
            if not tag[rid.ID_TAG_VALID_DATA]:  # only valid data can be baked
                continue

            idDataSet = tag[rid.ID_TAG_DATA_SET]

            # Skip clips, if not not explicitly enabled by the user
            # via "Include Clips"
            # (or we are here for the purpose of baking a clip)
            if not includeDataSets and idDataSet != idConnected and \
               not self._bakingOnly:
                continue

            # Last valid frame index is calculated a bit differently,
            # if it's a clip
            if idDataSet == idConnected:
                self._idxFrameLast = max(
                    g_thdListener.GetDataSetSize(idDataSet),
                    self._idxFrameLast)
            else:
                idxFrameLast = tag[rid.ID_TAG_DATA_SET_LAST_FRAME]
                idxFrameFirst = tag[rid.ID_TAG_DATA_SET_FIRST_FRAME]
                self._idxFrameLast = max(idxFrameLast - idxFrameFirst + 1,
                                         self._idxFrameLast)

        # Have slider values inside new range
        idxFrameFirst = self.GetInt32(rid.ID_DLGSAVE_FIRST_FRAME)
        idxFrameLast = self.GetInt32(rid.ID_DLGSAVE_LAST_FRAME)
        if idxFrameFirst > self._idxFrameLast - 1:
            idxFrameFirst = self._idxFrameLast - 1
        if idxFrameLast > self._idxFrameLast:
            idxFrameLast = self._idxFrameLast

        # Update sliders
        self.SetInt32(rid.ID_DLGSAVE_FIRST_FRAME,
                      idxFrameFirst,
                      min=0, max=self._idxFrameLast - 1,
                      min2=0, max2=self._idxFrameLast - 1)
        self.SetInt32(rid.ID_DLGSAVE_LAST_FRAME,
                      idxFrameLast,
                      min=1, max=self._idxFrameLast,
                      min2=1, max2=self._idxFrameLast)

    def InitValues(self):
        '''Called by C4D to initialize widget values.'''

        nameDataSet = "New Recording"
        doc = c4d.documents.GetActiveDocument()
        pathDataSet = doc.GetDocumentPath()
        pathDataSet = os.path.join(pathDataSet, nameDataSet + ".rec")

        self.SetString(rid.ID_DLGSAVE_NAME_DATASET, nameDataSet)
        self.SetString(rid.ID_DLGSAVE_PATH_DATASET, pathDataSet)
        self.SetInt32(rid.ID_DLGSAVE_FIRST_FRAME,
                      0,
                      min=0, max=self._idxFrameLast - 1,
                      min2=0, max2=self._idxFrameLast - 1)
        self.SetInt32(rid.ID_DLGSAVE_LAST_FRAME,
                      self._idxFrameLast,
                      min=1, max=self._idxFrameLast,
                      min2=1, max2=self._idxFrameLast)
        self.SetBool(rid.ID_DLGSAVE_CREATE_IN_TAKE,
                     GetPref(rid.ID_DLGSAVE_CREATE_IN_TAKE))
        self.SetBool(rid.ID_DLGSAVE_ACTIVATE_NEW_TAKE,
                     GetPref(rid.ID_DLGSAVE_ACTIVATE_NEW_TAKE))
        self.Enable(rid.ID_DLGSAVE_ACTIVATE_NEW_TAKE,
                    self.GetBool(rid.ID_DLGSAVE_CREATE_IN_TAKE))
        self.SetBool(rid.ID_DLGSAVE_WIPE_EXISTING_ANIMATION,
                     GetPref(rid.ID_DLGSAVE_WIPE_EXISTING_ANIMATION))
        self.SetInt32(rid.ID_DLGSAVE_TIMING, GetPref(rid.ID_DLGSAVE_TIMING))
        self.UpdateComboSkipFrames()
        self.SetInt32(rid.ID_DLGSAVE_FRAME_SKIP,
                      GetPref(rid.ID_DLGSAVE_FRAME_SKIP))
        self.SetInt32(rid.ID_DLGSAVE_LENGTH, GetPref(rid.ID_DLGSAVE_LENGTH))
        self.SetBool(rid.ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS,
                     GetPref(rid.ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS))
        self.SetBool(rid.ID_DLGSAVE_SET_KEYFRAMES_AUTOFORWARD,
                     GetPref(rid.ID_DLGSAVE_SET_KEYFRAMES_AUTOFORWARD))
        self.SetBool(rid.ID_DLGSAVE_USE_NEW_DATASET,
                     GetPref(rid.ID_DLGSAVE_USE_NEW_DATASET))
        return True

    def AskClose(self):
        '''Called by C4D when the dialog is about to be closed in whatever way.

        Returning True would deny the "close request" and the dialog stayed
        open.
        '''

        # If the user has not at least saved or baked a part of the recording,
        # show a warning.
        if not self._clipStored and not self._bakingOnly:
            msg = ("Recording has neither been saved nor baked.\n"
                   "Are you sure, you want to discard the recording and close "
                   "the dialog?")
            result = c4d.gui.MessageDialog(
                msg, c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_YESNO)
            if result == c4d.GEMB_R_NO:
                # User decided to keep Save Recording dialog open
                return True  # Dialog will NOT be closed

        # In case the dialog was opened from a tag...
        if self._bakingOnly:
            # Reset execute flag for all involved tags
            tagsLive = g_thdListener.GetTagConsumers()
            if tagsLive is not None:
                for tag in tagsLive:
                    if not tag.IsAlive():
                        continue
                    tag[rid.ID_TAG_EXECUTE_MODE] = 0

            # Restore states of all involved objects
            g_thdListener.RestoreCurrentPositions()

        # Unregister all tags from player
        g_thdListener.RemoveAllTagConsumers()

        # Restore the Manager dialog
        if self._dlgParent is not None:
            self._dlgParent.EnableDialog(True)
            self._dlgParent.CommandPlayerExit()
        c4d.EventAdd()
        return False

    # Used only here inside Message(BFM_ACTION), stores time of last
    # viewport redraw
    _lastEvent = 0

    def Message(self, msg, result):
        '''Called by C4D to send us a message.'''

        # Decode message (currently only interested in BFM_ACTION from the
        # sliders)
        idMsg = msg.GetId()
        if idMsg != c4d.BFM_ACTION:
            # pass message on to parenting classes
            return c4d.gui.GeDialog.Message(self, msg, result)

        # The sliders need a little extra attention, because we do not only
        # want them to set a frame index, but to also have the motion data
        # visualized in view port during drag.

        # Decode action ID (the widget this message is for)
        idAction = msg[c4d.BFM_ACTION_ID]
        if idAction == rid.ID_DLGSAVE_FIRST_FRAME:
            # Constrain last slider (first is always smaller than last)
            idxFrame = self.GetInt32(rid.ID_DLGSAVE_FIRST_FRAME)
            if idxFrame > self.GetInt32(rid.ID_DLGSAVE_LAST_FRAME):
                self.SetInt32(rid.ID_DLGSAVE_LAST_FRAME,
                              idxFrame + 1,
                              min=1, max=self._idxFrameLast,
                              min2=1, max2=self._idxFrameLast)
        elif idAction == rid.ID_DLGSAVE_LAST_FRAME:
            # Constrain first slider (first is always smaller than last)
            idxFrame = self.GetInt32(rid.ID_DLGSAVE_LAST_FRAME)
            if idxFrame < self.GetInt32(rid.ID_DLGSAVE_FIRST_FRAME):
                self.SetInt32(rid.ID_DLGSAVE_FIRST_FRAME,
                              idxFrame - 1,
                              min=0, max=self._idxFrameLast - 1,
                              min2=0, max2=self._idxFrameLast - 1)
        else:
            # BFM_ACTION for another widget, we are not interested in,
            # pass message on to parenting classes
            return c4d.gui.GeDialog.Message(self, msg, result)

        # Reduce the amount of viewport updates.
        # If last event is less than 50ms back, we'll simply skip the event.
        # TODO: This has the negative side effect, releasing the scrub bar
        #       slider is a bit imprecise.
        now = c4d.GeGetTimer()
        if now - self._lastEvent < 50:
            return c4d.gui.GeDialog.Message(self, msg, result)

        # Remove any unprocessed frames in tag's inbound queues,
        # so dispatched frame will be next to be consumed during tag's
        # Execute().
        g_thdListener.FlushTagConsumers()
        g_thdListener.DispatchFrame(idxFrame + 1, event=False)

        # Trigger execution of scene and redraw viewport
        c4d.DrawViews(c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW | c4d.DRAWFLAGS_NO_THREAD)

        # Store current time
        self._lastEvent = now

        # pass message on to parenting classes
        return c4d.gui.GeDialog.Message(self, msg, result)

    def PrepareCurvesInTake(
            self, takeData, take, obj, overrides, curves, descId, mgTPose):
        '''Finds or creates animation curves for a given DescId referencing
        a Vector.

        This is used for rotational or position keyframes.
        And it's only used in the case of baking into a new Take.

        All components of the Vector are handled separately.

        There is a second version of this function below, which is used in the
        case of baking without a Take (which will result in baking into the
        current Take).
        '''

        # Depending on DescID either need to store the offset or
        # its relative rotation as default value.
        if mgTPose is not None:
            if descId[0].id == c4d.ID_BASEOBJECT_REL_ROTATION:
                vDefault = c4d.utils.MatrixToHPB(
                    ~obj.GetUpMg() * rid.MR_Y180 * mgTPose)
            else:
                vDefault = (~obj.GetUpMg() * rid.MR_Y180 * mgTPose).off
        else:
            vDefault = obj.GetMl().off

        vectorComponents = [c4d.VECTOR_X, c4d.VECTOR_Y, c4d.VECTOR_Z]
        descIdComponents = [None, None, None]
        overrideComponents = [None, None, None]
        curveComponents = [None, None, None]

        # All components of a Vector are handled separately.
        for idxComponent in range(3):
            # DescID of vector component
            descIdComponents[idxComponent] = c4d.DescID(
                descId[0],
                c4d.DescLevel(vectorComponents[idxComponent],
                              c4d.DTYPE_REAL,
                              0))

            # Find or create the override
            overrideComponents[idxComponent] = take.FindOrAddOverrideParam(
                takeData,
                obj,
                descIdComponents[idxComponent],
                vDefault[idxComponent],
                None,
                False)
            if overrideComponents[idxComponent] is None:
                print("ERROR: Failed to override:", descId[0].id, idxComponent)
                break
            overrideComponents[idxComponent].UpdateSceneNode(
                takeData, descIdComponents[idxComponent])

            # Try to find an existing CTrack
            ctrack = overrideComponents[idxComponent].FindCTrack(
                descIdComponents[idxComponent])
            if ctrack is None:
                # Create and insert a new CTrack
                ctrack = c4d.CTrack(obj, descIdComponents[idxComponent])
                overrideComponents[idxComponent].InsertTrackSorted(ctrack)

            # We are not actually interested in the track,
            # but need the curve it contains
            curveComponents[idxComponent] = ctrack.GetCurve(
                type=c4d.CCURVE_CURVE, bCreate=True)

            # Optionally wipe all previous keyframes
            if self.GetBool(rid.ID_DLGSAVE_WIPE_EXISTING_ANIMATION):
                curveComponents[idxComponent].FlushKeys()

        # Store overrides and curves in dictionaries
        nameObj = obj.GetName()
        overrides[nameObj] = overrideComponents
        curves[nameObj] = curveComponents

    def PrepareCurves(self, obj, curves, descId):
        '''Finds or creates animation curves for a given DescId referencing
        a Vector.

        This is used for rotational or position keyframes.
        And it's only used in the case of NOT baking into a Take.

        All components of the Vector are handled separately.

        There is a second version of this function above, which is used in the
        case of baking into a new Take.
        '''

        vectorComponents = [c4d.VECTOR_X, c4d.VECTOR_Y, c4d.VECTOR_Z]
        descIdComponents = [None, None, None]
        curveComponents = [None, None, None]

        # All components of a Vector are handled separately.
        for idxComponent in range(3):
            # DescID of vector component
            descIdComponents[idxComponent] = c4d.DescID(
                descId[0],
                c4d.DescLevel(vectorComponents[idxComponent],
                              c4d.DTYPE_REAL,
                              0))

            # Try to find an existing CTrack
            ctrack = obj.FindCTrack(descIdComponents[idxComponent])
            if ctrack is None:
                # Create and insert a new CTrack
                ctrack = c4d.CTrack(obj, descIdComponents[idxComponent])
                obj.InsertTrackSorted(ctrack)

            # We are not actually interested in the track,
            # but need the curve it contains
            curveComponents[idxComponent] = ctrack.GetCurve(
                type=c4d.CCURVE_CURVE, bCreate=True)

            # Optionally wipe all previous keyframes
            if self.GetBool(rid.ID_DLGSAVE_WIPE_EXISTING_ANIMATION):
                curveComponents[idxComponent].FlushKeys()

        # Store curves in dictionary
        nameObj = obj.GetName()
        curves[nameObj] = curveComponents

    def PrepareMorphCurvesInTake(
        self,
        takeData,
        take,
        tagPoseMorph,
        overrides,
        curves,
        descIdMorph,
        nameInStudio
    ):
        '''Finds or creates an animation curve for a given DescId referencing
        a numerical value.

        This is used for face morph keyframes, as these only have a single
        float value.
        And it's only used in the case of baking into a new Take.

        There is a second version of this function below, which is used in the
        case of baking without a Take (which will result in baking into the
        current Take).
        '''

        valDefault = 0.0

        # Find or create the override
        override = take.FindOrAddOverrideParam(
            takeData, tagPoseMorph, descIdMorph, valDefault, None, False)
        if override is None:
            print("ERROR: Failed to override pose:", descIdMorph[0].id)
            return
        override.UpdateSceneNode(takeData, descIdMorph)

        # Try to find an existing CTrack
        ctrack = override.FindCTrack(descIdMorph)
        if ctrack is None:
            # Create and insert a new CTrack
            ctrack = c4d.CTrack(tagPoseMorph, descIdMorph)
            override.InsertTrackSorted(ctrack)

        # We are not actually interested in the track,
        # but need the curve it contains
        curve = ctrack.GetCurve(type=c4d.CCURVE_CURVE, bCreate=True)

        # Optionally wipe all previous keyframes
        if self.GetBool(rid.ID_DLGSAVE_WIPE_EXISTING_ANIMATION):
            curve.FlushKeys()

        # Store override and curve in dictionaries
        overrides[nameInStudio] = override
        curves[nameInStudio] = curve

    def PrepareMorphCurves(
            self, tagPoseMorph, curves, descIdMorph, nameInStudio):
        '''Finds or creates an animation curve for a given DescId.
        This is used for face morph keyframes, as these only have a
        single float value.
        And it's only used in the case of NOT baking into a Take.

        There is a second version of this function above, which is used in the
        case of baking into a new Take.
        '''

        # Try to find an existing CTrack
        ctrack = tagPoseMorph.FindCTrack(descIdMorph)
        if ctrack is None:
            # Create and insert a new CTrack
            ctrack = c4d.CTrack(tagPoseMorph, descIdMorph)
            tagPoseMorph.InsertTrackSorted(ctrack)

        # We are not actually interested in the track,
        # but need the curve it contains
        curve = ctrack.GetCurve(type=c4d.CCURVE_CURVE, bCreate=True)

        # Optionally wipe all previous keyframes
        if self.GetBool(rid.ID_DLGSAVE_WIPE_EXISTING_ANIMATION):
            curve.FlushKeys()

        # Store curve in dictionary
        curves[nameInStudio] = curve

    def PrepareTPosePerTag(self, tag):
        '''Creates a "T-Pose dictionary".

        Same as in tag... :(

        For all joints set in tag's mapping table,
        store object reference, object name and T-Pose matrices (normal and
        pretransformed).
        Entries are referred to by their Studio names.
        '''

        tPoseTag = {}

        for nameInStudio, (idx, _, _, _, _, _, _, _) in STUDIO_NAMES_TO_GUESS.items():  # noqa: E501
            obj = tag[rid.ID_TAG_BASE_RIG_LINKS + idx]

            # Skip empty mapping table entries
            if obj is None:
                continue

            # Store information in dictionary
            nameObj = obj.GetName()
            mgBodyPartTPose = tag[rid.ID_TAG_BASE_RIG_MATRICES + idx]
            mgBodyPartTPosePretransformed = tag[
                rid.ID_TAG_BASE_RIG_MATRICES_PRETRANSFORMED + idx]
            tPoseTag[nameInStudio] = (obj,
                                      mgBodyPartTPose,
                                      nameObj,
                                      mgBodyPartTPosePretransformed)
        return tPoseTag

    def PrepareFacePosesPerTag(self, tag):
        '''Creates a "face morph dictionary".

        During baking morphs are addressed by their DescID.
        Only morphs in tag's mapping table are stored in the dictionary.
        '''

        facePoses = {}
        obj = tag.GetObject()
        tagPoseMorph = obj.GetTag(c4d.Tposemorph)

        for nameInStudio, (idxPose, _, _, _, _, _) in FACE_POSE_NAMES.items():
            namePoseC4D = tag[rid.ID_TAG_BASE_FACE_POSES + idxPose]

            # Skip empty mapping table entries
            if namePoseC4D is None or len(namePoseC4D) <= 0:
                continue

            # Get DescID of this morph
            idxMorph = tag[rid.ID_TAG_BASE_MORPH_INDECES + idxPose]
            descIdMorph = tagPoseMorph.GetMorphID(idxMorph)
            # The returned DescID is not properly suited to set the morph
            # strength...
            descIdMorph = c4d.DescID(
                c4d.DescLevel(descIdMorph[0].id,
                              c4d.DTYPE_SUBCONTAINER,
                              0),
                c4d.DescLevel(descIdMorph[1].id,
                              c4d.DTYPE_REAL,
                              0))

            # Store in dict
            facePoses[nameInStudio] = descIdMorph
        return facePoses

    def AddVectorKeyframesToCurve(
            self, nameInStudio, time, curveComponents, v):
        '''As Takes seem to have an issue with applying keyframes for
        a Vector at once, this function adds the keyframes to the curves
        component wise.
        '''

        for idxComponent in range(3):
            resAddKey = curveComponents[idxComponent].AddKey(time)
            if resAddKey is None:
                print("ERROR: Failed to add keyframe",
                      nameInStudio, idxComponent)
                break
            key = resAddKey["key"]
            key.SetValue(curveComponents[idxComponent], v[idxComponent])

    def KeyframeActor(self, tag, tPose, data, curvesRot, curvesPos, time):
        '''Create all keyframes for a single Rokoko tag of type "actor"

        Code to calculate offsets and rotations is based on Philipp's nice
        Blender implementation:
        https://github.com/Rokoko/rokoko-studio-live-blender/blob/85f0569cc08fdee405f6c17bcb4e9c52804e43fa/core/animations.py#L88-L216

        In order to make up for some performance issues in C4D, the actual
        implementation is a bit different.
        There are certain parts of the calculation independent of the actual
        motion of an actor.
        In this plugin, these parts are moved out of this function
        (more important for Execute() of the tag).
        Instead these calculations are done, when the T-Pose gets stored.
        See ID_TAG_BASE_RIG_MATRICES_PRETRANSFORMED in rokoko_tag.
        '''

        # Get actor data from motion data frame
        idxActor = tag[rid.ID_TAG_ACTOR_INDEX]
        dataActors = data["actors"]
        # Bake only if data is valid
        if idxActor == -1 or idxActor >= len(dataActors):
            return
        dataActor = dataActors[idxActor]
        dataBody = dataActor["body"]
        objRoot = tag.GetObject()

        # In case there is no dedicated root object (but Rokoko tag is
        # assigned directly to hip joint), use identity matrix as root matrix
        objHip = tag[rid.ID_TAG_BASE_RIG_LINKS + 0]
        if objHip != objRoot:
            mgRoot = objRoot.GetMg()
        else:
            mgRoot = c4d.Matrix()

        mgRootTPose = tag[rid.ID_TAG_ROOT_MATRIX]

        # Rotation

        # Iterate all objects of the rig (well, only those assigned in tag's
        # mapping table)
        for nameInStudio, (obj, _, nameInRig, mRotOffsetRef) in tPose.items():
            # Get Studio rotation and convert into C4D transformation matrix
            dataBodyPart = dataBody[nameInStudio]
            mStudioNewPose = JSONQuaternionToMatrix(dataBodyPart["rotation"])

            # Transform the current Studio rotation
            # Apply pretransformed T-Pose matrix
            mFinalRot = mStudioNewPose * mRotOffsetRef

            # While sharing a similarly oriented coordinate system,
            # in C4D characters face forward in the opposite direction.
            # A character in T-Pose will usually look into -Z in T-Pose
            # (while in Rokoko Studio it looks into +Z).

            # Rotate Studio's rotation by 180 degree around Y
            # Actually ~MR_Y180 * mFinalRot, but ~MR_Y180 == MR_Y180
            mFinalRot = rid.MR_Y180 * mFinalRot

            # Reverse the rotation which may have been caused by a rotation of
            # T-Pose's root object
            mFinalRot = ~mgRootTPose * mFinalRot

            # Finally rotate by rigs current root rotation
            mFinalRot = mgRoot * mFinalRot

            # Preserve global position of the joint
            mFinalRot.off = obj.GetMg().off

            obj.SetMg(mFinalRot)

            # Keyframes are always relative rotations
            vRot = obj.GetRelRot()

            # Add keyframe for every component of the rotation to the curve
            curveComponents = curvesRot[nameInRig]
            self.AddVectorKeyframesToCurve(
                nameInStudio, time, curveComponents, vRot)

        # Hip Position
        if "hip" in tPose:
            # Get hip parameters
            (_, _, nameInRig, _) = tPose["hip"]
            # hip height of current actor in Studio
            hipHeightStudio = dataActor["dimensions"]["hipHeight"]
            # current position of hip in Studio
            posStudio = dataBody["hip"]["position"]
            yTPoseHip = tag[rid.ID_TAG_ACTOR_HIP_HEIGHT]

            # Scale hip height by ratio of current actor's hip height and
            # Studio's T-Pose base hip height
            scale = yTPoseHip / hipHeightStudio

            # Calculate hip's y position in C4D
            y = yTPoseHip * (1 + (posStudio["y"] - hipHeightStudio))

            # Merge into relative offset in C4D
            # -x/z due to different orientation of character in C4D
            off = c4d.Vector(-posStudio["x"] * scale,
                             y,
                             -posStudio["z"] * scale)

            # Reverse offset and rotation which may have been caused by
            # T-Pose's root object
            off = ~mgRootTPose * off

            # Scale position with "Project Scale" parameter
            # position relative to root object
            off *= GetProjectScale()

            # Add keyframe for every component of the offset to the curve
            curveComponents = curvesPos[nameInRig]
            self.AddVectorKeyframesToCurve("hip", time, curveComponents, off)

    def KeyframeFace(self, tag, facePoses, data, _, curves, time):
        '''Create all keyframes for a single Rokoko tag of type "face"'''

        # Get face data from motion data frame
        idxActor = tag[rid.ID_TAG_ACTOR_INDEX]
        dataActors = data["actors"]
        # bake only if data is valid
        if idxActor == -1 or idxActor >= len(dataActors):
            return
        dataFace = dataActors[idxActor]["face"]

        # Add keyframe for every morph to the curve
        for nameInStudio, descIdMorph in facePoses.items():
            curve = curves[nameInStudio]
            resAddKey = curve.AddKey(time)
            if resAddKey is None:
                print("ERROR: Failed to add posemorph keyframe", nameInStudio)
                break
            key = resAddKey["key"]
            strength = float(dataFace[nameInStudio]) / 100.0
            key.SetValue(curve, strength)

    def KeyframeProp(self, tag, data, curvesRot, curvesPos, time):
        '''Create all keyframes for a single Rokoko tag of type "prop"'''

        # Get prop data from motion data frame
        idxProp = tag[rid.ID_TAG_ACTOR_INDEX]
        dataProps = data["props"]
        # bake only if data is valid
        if idxProp == -1 or idxProp >= len(dataProps):
            return
        dataProp = dataProps[idxProp]
        objProp = tag.GetObject()
        nameObjProp = objProp.GetName()

        # Rotation

        # Convert Studio rotation into a C4D transformation matrix
        mPropStudio = JSONQuaternionToMatrix(dataProp["rotation"])

        # While sharing a similarly oriented coordinate system,
        # in C4D characters (and thus also props) face forward in the
        # opposite direction.
        # A character in T-Pose will usually look into -Z in T-Pose
        # (while in Rokoko Studio it looks into +Z).

        # Rotate Studio data by 180 degree around Y
        # absolute rotation of prop object in C4D
        mFinalRot = rid.MR_Y180 * mPropStudio

        # Preserve global position of the object (for the moment)
        mFinalRot.off = objProp.GetMg().off

        objProp.SetMg(mFinalRot)

        # Keyframes are always relative rotations
        vRot = objProp.GetRelRot()

        # Add keyframe for every component of the rotation to the curve
        curveComponents = curvesRot[nameObjProp]
        self.AddVectorKeyframesToCurve(
            nameObjProp, time, curveComponents, vRot)

        # Position

        # Convert absolute global position in Studio into a C4D offset vector
        posStudio = dataProp["position"]
        off = c4d.Vector(-posStudio["x"] * 100.0,
                         posStudio["y"] * 100.0,
                         -posStudio["z"] * 100.0)

        # Scale position with "Project Scale" parameter
        off *= GetProjectScale()

        # Add keyframe for every component of the offset to the curve
        curveComponents = curvesPos[nameObjProp]
        self.AddVectorKeyframesToCurve(nameObjProp, time, curveComponents, off)

    def KeyframeTags(
        self,
        dataQueue,
        idxFirstFrame,
        idxLastFrame,
        tag,
        tPose,
        curvesRot,
        curvesPos,
        fps,
        timeStart,
        timeMax,
        idxLastKey
    ):
        '''Create all keyframes for a single Rokoko tag'''

        # Get all needed parameters from dialog
        behaviorAtEnd = self.GetInt32(rid.ID_DLGSAVE_LENGTH)
        timing = self.GetInt32(rid.ID_DLGSAVE_TIMING)
        skipFrames = self.GetInt32(rid.ID_DLGSAVE_FRAME_SKIP)

        # Frame reduction parameters allow to specify in two ways:
        # Parameter (combo box) value < 10: Only bake every nth frame
        # Parameter (combo box) value >= 10: Basically specifying keyframes per
        #                                    second (C4D's document time)
        skipByIndex = skipFrames < 10
        skipByTime = skipFrames >= 10
        if skipFrames == 500:
            doc = tag.GetDocument()
            skipFrames = doc.GetFps()
        if skipByTime:
            skipFrames = 1.0 / float(skipFrames)

        # Number of motion data frames to bake (including frames to be skipped)
        numFrames = idxLastFrame - idxFirstFrame + 1

        # Determine first and last frame index
        if tag[rid.ID_TAG_DATA_SET] != GetConnectedDataSetId():
            idxFirstFrameTag = tag[rid.ID_TAG_DATA_SET_FIRST_FRAME]
            idxLastFrameTag = tag[rid.ID_TAG_DATA_SET_LAST_FRAME]
        else:
            idxFirstFrameTag = 0
            idxLastFrameTag = len(dataQueue) - 1

        lenTagClip = idxLastFrameTag - idxFirstFrameTag + 1
        idxFirstFrameEffective = idxFirstFrameTag + idxFirstFrame % lenTagClip
        tsLast = dataQueue[idxFirstFrameEffective]["scene"]["timestamp"]
        timeLast = timeStart
        for idxFrame in range(numFrames):
            # Calculate the effective frame index and get the motion data frame
            idxFrameEffective = idxFirstFrameEffective + idxFrame % lenTagClip
            data = dataQueue[idxFrameEffective]

            c4d.StatusSetBar(int(100.0 * float(idxFrame) / float(numFrames)))

            # Calculate time of new keyframe in C4D
            if timing == 0:  # Studio time
                ts = dataQueue[idxFrameEffective]["scene"]["timestamp"]
                # Studio time since last motion data frame
                tsDiff = ts - tsLast

                # Care for timestamp wrap around.
                # Happens, when Rokoko Studio is playing back a scene in a
                # loop.
                if tsDiff < 0.0:
                    tsDiff = 1.0 / float(dataQueue[idxFrameEffective]["fps"])

                # Optionally reduce keyframes by skipping motion data frames
                # (here "keyframes per second")
                if skipByTime and tsDiff < skipFrames and idxFrame != 0:
                    continue

                # C4D time for keyframe(s)
                time = timeLast + c4d.BaseTime(tsDiff)

                tsLast = ts
                timeLast = time
            else:  # Timing "by frame"
                # No calculations, keyframe time simply results from index
                time = timeStart + c4d.BaseTime(idxFrame, fps)

            # Optionally stop baking at the end of C4D's current project
            if behaviorAtEnd == 1 and time > timeMax:
                break

            # Optionally reduce keyframes by skipping motion data frames
            # (here "every nth frame")
            if skipByIndex and (idxFrame % skipFrames) != 0:
                continue

            # Create keyframes depending on type of tag (roughly the
            # equivalent to Execute() in tag)
            if tag[rid.ID_TAG_RIG_TYPE] & rid.RIG_TYPE_ACTOR:
                self.KeyframeActor(
                    tag, tPose, data["scene"], curvesRot, curvesPos, time)
            elif tag[rid.ID_TAG_RIG_TYPE] & rid.RIG_TYPE_ACTOR_FACE:
                self.KeyframeFace(
                    tag, tPose, data["scene"], curvesRot, curvesPos, time)
            elif tag[rid.ID_TAG_RIG_TYPE] & rid.RIG_TYPE_PROP:
                self.KeyframeProp(
                    tag, data["scene"], curvesRot, curvesPos, time)
            else:
                print("KEYFRAMES RIG TYPE MISSING", tag[rid.ID_TAG_RIG_TYPE])

            idxLastKey[0] = max(idxLastKey[0], idxFrame)

    def CommandSetKeyframes(self, atCurrent=False, everyNth=1):
        '''User pressed "Bake" button.

        All involved tags will bake their assigned motion data into their host
        object(s).
        '''

        # Get all needed parameters from the dialog
        idConnected = GetConnectedDataSetId()
        idxFirstFrame = self.GetInt32(rid.ID_DLGSAVE_FIRST_FRAME)
        idxLastFrame = self.GetInt32(rid.ID_DLGSAVE_LAST_FRAME)
        createTake = self.GetBool(rid.ID_DLGSAVE_CREATE_IN_TAKE)
        if not self._bakingOnly:
            nameDataSet = self.GetString(rid.ID_DLGSAVE_NAME_DATASET)
        else:
            nameDataSet = GetDataSetFromId(
                self._tags[0][rid.ID_TAG_DATA_SET])[rid.ID_BC_DATASET_NAME]
        behaviorAtEnd = self.GetInt32(rid.ID_DLGSAVE_LENGTH)
        autoForward = self.GetBool(rid.ID_DLGSAVE_SET_KEYFRAMES_AUTOFORWARD)
        includeDataSets = self.GetBool(rid.ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS)

        # Determine C4D document time of first frame to be baked.
        doc = c4d.documents.GetActiveDocument()
        fps = doc.GetFps()
        if atCurrent:
            timeStart = doc.GetTime()
        else:
            timeStart = c4d.BaseTime(0.0)

        # Number of motion data frames to be baked
        numDataFrames = idxLastFrame - idxFirstFrame + 1

        # Determine time of last frame to be baked and optionally extend
        # the project end time in C4D
        timeMax = doc.GetMaxTime()
        timeStudioMax = c4d.BaseTime(0.016667 * numDataFrames)
        if behaviorAtEnd == 0 and (timeStart + timeStudioMax) > timeMax:
            doc.SetMaxTime(timeStart + timeStudioMax)

        # Prepare descIds for positions and rotations.
        # Unfortunately the Takes system does seem to have issues with more
        # complex data types, thus the vectors are handled component-wise.
        descIdRot = c4d.DescID(
            c4d.DescLevel(c4d.ID_BASEOBJECT_REL_ROTATION, c4d.DTYPE_VECTOR, 0))
        descIdRotComponents = [None, None, None]
        descIdRotComponents[0] = c4d.DescID(
            c4d.DescLevel(c4d.ID_BASEOBJECT_REL_ROTATION, c4d.DTYPE_VECTOR, 0),
            c4d.DescLevel(c4d.VECTOR_X, c4d.DTYPE_REAL, 0))
        descIdRotComponents[1] = c4d.DescID(
            c4d.DescLevel(c4d.ID_BASEOBJECT_REL_ROTATION, c4d.DTYPE_VECTOR, 0),
            c4d.DescLevel(c4d.VECTOR_Y, c4d.DTYPE_REAL, 0))
        descIdRotComponents[2] = c4d.DescID(
            c4d.DescLevel(c4d.ID_BASEOBJECT_REL_ROTATION, c4d.DTYPE_VECTOR, 0),
            c4d.DescLevel(c4d.VECTOR_Z, c4d.DTYPE_REAL, 0))
        descIdPos = c4d.DescID(
            c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION, c4d.DTYPE_VECTOR, 0))
        descIdPosComponents = [None, None, None]
        descIdPosComponents[0] = c4d.DescID(
            c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION, c4d.DTYPE_VECTOR, 0),
            c4d.DescLevel(c4d.VECTOR_X, c4d.DTYPE_REAL, 0))
        descIdPosComponents[1] = c4d.DescID(
            c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION, c4d.DTYPE_VECTOR, 0),
            c4d.DescLevel(c4d.VECTOR_Y, c4d.DTYPE_REAL, 0))
        descIdPosComponents[2] = c4d.DescID(
            c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION, c4d.DTYPE_VECTOR, 0),
            c4d.DescLevel(c4d.VECTOR_Z, c4d.DTYPE_REAL, 0))

        # Try to display the progress in C4D's status bar.
        # This currently works very unreliably (most times not at all).
        # See:
        # https://plugincafe.maxon.net/topic/12726/how-to-enforce-statusbar-redraws
        c4d.StatusClear()
        c4d.StatusSetText("Baking Rokoko Motion to Keyframes...")
        c4d.StatusSetBar(0)

        doc.StartUndo()

        # Optionally create a new Take for the keyframes to be baked into
        if createTake:
            takeData = doc.GetTakeData()
            if takeData is None:
                print("ERROR: Failed to retrieve the take data.")
                return
            take = takeData.AddTake(nameDataSet, None, None)
            if take is None:
                print("ERROR: Failed to add a new take.")
                return

            doc.AddUndo(c4d.UNDOTYPE_NEW, take)

            # Have Main Take active during baking (store current selection to
            # be able to restore it later on)
            takeOld = takeData.GetCurrentTake()
            takeData.SetCurrentTake(takeData.GetMainTake())

        # Have all actors in their original position (before any playback
        # started)
        g_thdListener.RestoreCurrentPositions()

        # Iterate all tags in order to bake their motion data
        # idxLastKey stores the time of the last created keyframe for
        # auto forwarding afterwards
        idxLastKey = [0]
        for tag in self._tags:
            idDataSet = tag[rid.ID_TAG_DATA_SET]
            # Skip tags with invalid data or depending on user's options
            isNotBakeSet = not self._bakingOnly and \
                not includeDataSets and \
                idDataSet != idConnected
            if isNotBakeSet or not tag[rid.ID_TAG_VALID_DATA]:
                continue

            # Motion data used by the tag
            dataQueue = g_thdListener._dataQueues[idDataSet]

            # Prepare T-Pose dictionaries
            if tag[rid.ID_TAG_RIG_TYPE] & rid.RIG_TYPE_ACTOR:
                tPose = self.PrepareTPosePerTag(tag)
            elif tag[rid.ID_TAG_RIG_TYPE] & rid.RIG_TYPE_ACTOR_FACE:
                tPose = self.PrepareFacePosesPerTag(tag)
            else:
                tPose = None

            if createTake:
                # All curves and overrides needed during baking will be stored
                # in these dictionaries
                overridesRot = {}
                curvesRot = {}
                overridesPos = {}
                curvesPos = {}

                # Depending on type of tag prepare curves and overrides
                if tag[rid.ID_TAG_RIG_TYPE] & rid.RIG_TYPE_ACTOR:
                    for nameInStudio, (obj,
                                       mgTPose,
                                       nameObj,
                                       _) in tPose.items():
                        self.PrepareCurvesInTake(
                            takeData, take,
                            obj,
                            overridesRot, curvesRot, descIdRot,
                            mgTPose)
                        if nameInStudio == "hip":
                            self.PrepareCurvesInTake(
                                takeData, take,
                                obj,
                                overridesPos, curvesPos, descIdPos,
                                mgTPose)
                elif tag[rid.ID_TAG_RIG_TYPE] & rid.RIG_TYPE_ACTOR_FACE:
                    obj = tag.GetObject()
                    tagPoseMorph = obj.GetTag(c4d.Tposemorph)
                    for nameInStudio, descIdMorph in tPose.items():
                        self.PrepareMorphCurvesInTake(
                            takeData, take,
                            tagPoseMorph,
                            overridesPos, curvesPos, descIdMorph,
                            nameInStudio)
                else:
                    obj = tag.GetObject()
                    self.PrepareCurvesInTake(
                        takeData, take,
                        obj,
                        overridesRot, curvesRot, descIdRot,
                        None)
                    self.PrepareCurvesInTake(
                        takeData, take,
                        obj,
                        overridesPos, curvesPos, descIdPos,
                        None)

                # Create actual keyframes
                self.KeyframeTags(
                    dataQueue,
                    idxFirstFrame, idxLastFrame,
                    tag, tPose,
                    curvesRot, curvesPos,
                    fps, timeStart, timeMax,
                    idxLastKey)

                # Take overrides need to be updated (again depending on type
                # of tag)
                if tag[rid.ID_TAG_RIG_TYPE] & rid.RIG_TYPE_ACTOR:
                    for nameInStudio, (obj, _, nameObj, _) in tPose.items():
                        for idxComponent in range(3):
                            overrideRot = overridesRot[nameObj][idxComponent]
                            overrideRot.UpdateSceneNode(
                                takeData, descIdRotComponents[idxComponent])
                            if nameInStudio == "hip":
                                overridePos = overridesPos[
                                    nameObj][idxComponent]
                                overridePos.UpdateSceneNode(
                                    takeData,
                                    descIdPosComponents[idxComponent])
                elif tag[rid.ID_TAG_RIG_TYPE] & rid.RIG_TYPE_ACTOR_FACE:
                    for nameInStudio, descIdMorph in tPose.items():
                        overridesPos[nameInStudio].UpdateSceneNode(
                            takeData, descIdMorph)
                else:
                    obj = tag.GetObject()
                    nameObj = obj.GetName()
                    for idxComponent in range(3):
                        overridesRot[nameObj][idxComponent].UpdateSceneNode(
                            takeData, descIdRotComponents[idxComponent])
                        overridesPos[nameObj][idxComponent].UpdateSceneNode(
                            takeData, descIdPosComponents[idxComponent])
            else:
                # Create an undo for the host object (this includes all
                # children in case of actor rigs)
                # In the Take branch the Take system manages undo for us.
                root = tag.GetObject()
                doc.AddUndo(c4d.UNDOTYPE_CHANGE, root)

                # All curves and overrides needed during baking will be stored
                # in these dictionaries
                curvesRot = {}
                curvesPos = {}

                # Depending on type of tag prepare curves and overrides
                if tag[rid.ID_TAG_RIG_TYPE] & rid.RIG_TYPE_ACTOR:
                    for nameInStudio, (obj, _, nameObj, _) in tPose.items():
                        self.PrepareCurves(obj, curvesRot, descIdRot)
                        if nameInStudio == "hip":
                            self.PrepareCurves(obj, curvesPos, descIdPos)
                elif tag[rid.ID_TAG_RIG_TYPE] & rid.RIG_TYPE_ACTOR_FACE:
                    tagPoseMorph = root.GetTag(c4d.Tposemorph)
                    for nameInStudio, descIdMorph in tPose.items():
                        self.PrepareMorphCurves(
                            tagPoseMorph, curvesPos, descIdMorph, nameInStudio)
                else:
                    self.PrepareCurves(root, curvesRot, descIdRot)
                    self.PrepareCurves(root, curvesPos, descIdPos)

                # Create actual keyframes
                self.KeyframeTags(
                    dataQueue,
                    idxFirstFrame, idxLastFrame,
                    tag, tPose,
                    curvesRot, curvesPos,
                    fps, timeStart, timeMax, idxLastKey)

        # If a new Take was created, optionally select the new one
        if createTake:
            if self.GetBool(rid.ID_DLGSAVE_ACTIVATE_NEW_TAKE):
                takeData.SetCurrentTake(take)
            else:
                # restore previous Take selection
                takeData.SetCurrentTake(takeOld)

        # Optionally forward document time ("one motion data frame" after
        # the last created keyframe)
        if autoForward:
            doc.SetTime(
                timeStart + c4d.BaseTime(0.016667 * (idxLastKey[0] + 1)))

        doc.EndUndo()

        # Restore states of all involved objects
        g_thdListener.RestoreCurrentPositions()
        c4d.EventAdd()

        # Reset C4D's status bar
        c4d.StatusClear()

        # Do no longer show a warning, if dialog gets closed and thus recording
        # gets discarded
        self._clipStored = True

        # Success requester
        if createTake:
            c4d.gui.MessageDialog(
                f"Successfully baked keyframes in Take '{nameDataSet}'.")
        else:
            c4d.gui.MessageDialog(
                "Successfully baked keyframes in current Take.")

    def CommandStoreDataSet(self, local=False):
        '''User pressed "Store Clip" button.

        Motion data will be saved to a file and a Clip will be added to
        either the global or the project clip library.
        '''

        bcConnected = GetConnectedDataSet()
        if bcConnected is None:
            print("ERROR: No connected data set to store")
            return

        # Get data set name and filepath
        name = self.GetString(rid.ID_DLGSAVE_NAME_DATASET)
        filename = self.GetString(rid.ID_DLGSAVE_PATH_DATASET)
        filenameInDataSet = filename

        # Resolve path of local clips
        if local:
            pathDocument = c4d.documents.GetActiveDocument().GetDocumentPath()
            if pathDocument is not None and len(pathDocument) > 1:
                filenameInDataSet = filenameInDataSet.replace(
                    pathDocument, ".", 1)

        # If user set no path, exit
        if name + ".rec" == filename:
            c4d.gui.MessageDialog(
                "It seems you have not specified a path, yet.\n"
                "Maybe the project has not been saved?")
            return

        # Clone the connected data set and turn it into a data set referring to
        # a file (clip)
        bcNewDataSet = bcConnected.GetClone(c4d.COPYFLAGS_NONE)
        bcNewDataSet[rid.ID_BC_DATASET_NAME] = name
        # Type: 0 - connection, 1 - file
        bcNewDataSet[rid.ID_BC_DATASET_TYPE] = 1
        bcNewDataSet[rid.ID_BC_DATASET_CONNECTED] = False
        bcNewDataSet[rid.ID_BC_DATASET_AVAILABLE_IN_DOC] = True
        bcNewDataSet[rid.ID_BC_DATASET_LIVE_PORT] = ""
        bcNewDataSet[rid.ID_BC_DATASET_LIVE_AUTOCONNECT] = False
        bcNewDataSet[rid.ID_BC_DATASET_FILENAME] = filenameInDataSet
        bcNewDataSet[rid.ID_BC_DATASET_IS_LOCAL] = local

        # Recalculate the data set ID based on its data
        idDataSetNew = MyHash(name + filenameInDataSet + str(local))
        bcNewDataSet.SetId(idDataSetNew)

        # Store the new data set in either global or project's clip library
        AddDataSetBC(bcNewDataSet)

        # If Manager dialog is the parent (the only parent there can be),
        # update the respective Clip library group
        if self._dlgParent is not None:
            self._dlgParent.UpdateLayoutGroupDataSet(local)

        # Store motion data in a file
        g_thdListener.SaveLiveData(
            filename,
            self.GetInt32(rid.ID_DLGSAVE_FIRST_FRAME),
            self.GetInt32(rid.ID_DLGSAVE_LAST_FRAME))

        # Force tags to recognize new clip (to have it appear in the
        # combo boxes)
        idConnected = bcConnected.GetId()
        for tag in self._tags:
            tag.Message(c4d.MSG_MENUPREPARE)

            # Optionally assign the new clip to the tag
            if self.GetBool(rid.ID_DLGSAVE_USE_NEW_DATASET) and \
               tag[rid.ID_TAG_DATA_SET] == idConnected:
                tag[rid.ID_TAG_DATA_SET] = idDataSetNew

        c4d.EventAdd()

        # Do no longer show a warning, if dialog gets closed and thus recording
        # gets discarded
        self._clipStored = True

        # Success requester
        if local:
            c4d.gui.MessageDialog(
                f"Successfully stored clip '{name}' in project.")
        else:
            c4d.gui.MessageDialog(f"Successfully stored global clip '{name}'.")

    def Command(self, id, msg):
        '''Called by C4D to handle user's interaction with the dialog.'''

        # First and last frame sliders
        if id == rid.ID_DLGSAVE_FIRST_FRAME:
            idxFrameFirst = self.GetInt32(rid.ID_DLGSAVE_FIRST_FRAME)
            idxFrameLast = self.GetInt32(rid.ID_DLGSAVE_LAST_FRAME)
            if idxFrameFirst > idxFrameLast:
                self.SetInt32(rid.ID_DLGSAVE_LAST_FRAME,
                              idxFrameFirst + 1,
                              min=1, max=self._idxFrameLast,
                              min2=1, max2=self._idxFrameLast)
        elif id == rid.ID_DLGSAVE_LAST_FRAME:
            idxFrameFirst = self.GetInt32(rid.ID_DLGSAVE_FIRST_FRAME)
            idxFrameLast = self.GetInt32(rid.ID_DLGSAVE_LAST_FRAME)
            if idxFrameLast < idxFrameFirst:
                self.SetInt32(rid.ID_DLGSAVE_FIRST_FRAME,
                              idxFrameLast - 1,
                              min=0, max=self._idxFrameLast - 1,
                              min2=0, max2=self._idxFrameLast - 1)

        # Bake options
        elif id == rid.ID_DLGSAVE_CREATE_IN_TAKE:
            SetPref(id, self.GetBool(id))
            self.Enable(rid.ID_DLGSAVE_ACTIVATE_NEW_TAKE,
                        self.GetBool(rid.ID_DLGSAVE_CREATE_IN_TAKE))
        elif id == rid.ID_DLGSAVE_ACTIVATE_NEW_TAKE:
            SetPref(id, self.GetBool(id))
        elif id == rid.ID_DLGSAVE_WIPE_EXISTING_ANIMATION:
            SetPref(id, self.GetBool(id))
        elif id == rid.ID_DLGSAVE_TIMING:
            SetPref(id, self.GetInt32(id))
            self.UpdateComboSkipFrames()
        elif id == rid.ID_DLGSAVE_FRAME_SKIP:
            SetPref(id, self.GetInt32(id))
        elif id == rid.ID_DLGSAVE_LENGTH:
            SetPref(id, self.GetInt32(id))
        elif id == rid.ID_DLGSAVE_SET_KEYFRAMES_AUTOFORWARD:
            SetPref(id, self.GetBool(id))
        elif id == rid.ID_DLGSAVE_USE_NEW_DATASET:
            SetPref(id, self.GetBool(id))
        elif id == rid.ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS:
            SetPref(id, self.GetBool(id))
            self.UpdateSliders()

        # Bake buttons
        elif id == rid.ID_DLGSAVE_SET_KEYFRAMES_AT_CURRENT:
            self.CommandSetKeyframes(atCurrent=True)
        elif id == rid.ID_DLGSAVE_SET_KEYFRAMES_AT_0:
            self.CommandSetKeyframes()

        # Saving options
        elif id == rid.ID_DLGSAVE_SET_PATH_DATASET:
            pathDefault = c4d.documents.GetActiveDocument().GetDocumentPath()
            filenameDefault = self.GetString(rid.ID_DLGSAVE_NAME_DATASET)
            filename = c4d.storage.SaveDialog(
                type=c4d.FILESELECTTYPE_ANYTHING,
                title="Choose Clip Filename...",
                force_suffix="rec",
                def_path=pathDefault,
                def_file=filenameDefault)
            if filename is None or len(filename) < 2:
                return True
            self.SetString(rid.ID_DLGSAVE_PATH_DATASET, filename)

        # Saving buttons
        elif id == rid.ID_DLGSAVE_STORE_LOCAL_DATA:
            self.CommandStoreDataSet(local=True)
        elif id == rid.ID_DLGSAVE_STORE_GLOBAL_DATA:
            self.CommandStoreDataSet()

        # currently this button is not shown in the UI
        elif id == rid.ID_DLGSAVE_DISCARD:
            self.Close()
        return True
