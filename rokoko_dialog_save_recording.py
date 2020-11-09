import os
import c4d
from rokoko_ids import *
from rokoko_utils import *
from rokoko_listener import *
from rokoko_dialog_utils import *

g_thdListener = GetListenerThread() # owned by rokoko_listener
g_studioTPose = {}
def DlgSaveSetGlobalStudioTPose(tPose):
    global g_studioTPose
    g_studioTPose = tPose

def DlgSaveDestroyGlobals():
    global g_studioTPose
    global g_thdListener
    g_studioTPose = {}
    g_thdListener = None


class DialogSaveRecording(c4d.gui.GeDialog):
    _dlgParent = None

    def __init__(self, dlgParent, tags=None, bakingOnly=False):
        self._dlgParent = dlgParent
        self._bakingOnly = bakingOnly
        if tags is None:
            self._tags = g_thdListener.GetTagConsumers()
        else:
            self._tags = tags
        self._idxFrameLast = 0
        if self._bakingOnly:
            g_thdListener.StoreCurrentPositions(self._tags)
        idConnected = GetConnectedDataSetId()
        for tag in self._tags:
            if not tag[ID_TAG_VALID_DATA]:
                continue
            idDataSet = tag[ID_TAG_DATA_SET]
            includeDataSets = GetPref(ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS)
            if not includeDataSets and idDataSet != idConnected and not self._bakingOnly:
                continue
            if idDataSet == idConnected:
                self._idxFrameLast = max(g_thdListener.GetDataSetSize(idDataSet), self._idxFrameLast)
            else:
                self._idxFrameLast = max(tag[ID_TAG_DATA_SET_LAST_FRAME] - tag[ID_TAG_DATA_SET_FIRST_FRAME], self._idxFrameLast)
            if self._bakingOnly:
                g_thdListener.AddTagConsumer(tag.GetNodeData(), tag)
                tag[ID_TAG_EXECUTE_MODE] = 1
        c4d.gui.GeDialog.__init__(self)

    def CreateLayout(self):
        if self._bakingOnly:
            self.SetTitle('Bake Clip...')
        else:
            self.SetTitle('Save Recording...')
        if self.GroupBegin(ID_DLGSAVE_GROUP_MAIN, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=1): # Dialog main group
            self.GroupBorderSpace(5, 5, 10, 5)
            CreateLayoutAddGroupBar(self, 'Frame Range')
            if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2):
                self.GroupBorderSpace(10, 0, 0, 0)
                self.AddStaticText(0, c4d.BFH_LEFT, name='First Frame')
                self.AddEditSlider(ID_DLGSAVE_FIRST_FRAME, c4d.BFH_SCALEFIT)
                self.AddStaticText(0, c4d.BFH_LEFT, name='Last Frame')
                self.AddEditSlider(ID_DLGSAVE_LAST_FRAME, c4d.BFH_SCALEFIT)
            self.GroupEnd()
            CreateLayoutAddGroupBar(self, 'Bake Keyframes')
            if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=3):
                self.GroupBorderSpace(10, 0, 0, 0)
                self.AddStaticText(0, c4d.BFH_SCALEFIT, name='Timing')
                self.AddComboBox(ID_DLGSAVE_TIMING, c4d.BFH_SCALEFIT)
                self.AddChild(ID_DLGSAVE_TIMING, 0, 'Studio Time')
                self.AddChild(ID_DLGSAVE_TIMING, 1, 'By Frame')
                self.AddStaticText(0, c4d.BFH_SCALEFIT, name='') # Dummy
                self.AddStaticText(0, c4d.BFH_SCALEFIT, name='Skip Frames')
                self.AddComboBox(ID_DLGSAVE_FRAME_SKIP, c4d.BFH_SCALEFIT)
                self.AddStaticText(0, c4d.BFH_SCALEFIT, name='') # Dummy
                self.AddStaticText(0, c4d.BFH_SCALEFIT, name='Length')
                self.AddComboBox(ID_DLGSAVE_LENGTH, c4d.BFH_SCALEFIT)
                self.AddChild(ID_DLGSAVE_LENGTH, 0, "Extend Project's End Time")
                self.AddChild(ID_DLGSAVE_LENGTH, 1, "Stop at Project's End Time")
                self.AddChild(ID_DLGSAVE_LENGTH, 2, 'Ignore')
                self.AddStaticText(0, c4d.BFH_SCALEFIT, name='') # Dummy
                self.AddCheckbox(ID_DLGSAVE_CREATE_IN_TAKE, c4d.BFH_SCALEFIT, name='Create New Take', initw=0, inith=0)
                self.AddCheckbox(ID_DLGSAVE_ACTIVATE_NEW_TAKE, c4d.BFH_SCALEFIT, name='Activate New Take', initw=0, inith=0)
                self.AddStaticText(0, c4d.BFH_SCALEFIT, name='') # Dummy
                self.AddCheckbox(ID_DLGSAVE_WIPE_EXISTING_ANIMATION, c4d.BFH_SCALEFIT, name='Wipe Existing Animation', initw=0, inith=0)
                self.AddCheckbox(ID_DLGSAVE_SET_KEYFRAMES_AUTOFORWARD, c4d.BFH_SCALEFIT, name='Advance Current Frame', initw=0, inith=0)
                if not self._bakingOnly:
                    self.AddCheckbox(ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS, c4d.BFH_SCALEFIT, name='Include File Clips', initw=0, inith=0)
                else:
                    self.AddStaticText(0, c4d.BFH_SCALEFIT, name='') # Dummy
                self.AddButton(ID_DLGSAVE_SET_KEYFRAMES_AT_0, c4d.BFH_SCALEFIT, name='Bake Keyframes at 0')
                self.AddButton(ID_DLGSAVE_SET_KEYFRAMES_AT_CURRENT, c4d.BFH_SCALEFIT, name='Bake Keyframes at Current')
                self.AddStaticText(0, c4d.BFH_SCALEFIT, name='') # Dummy
            self.GroupEnd()
            if not self._bakingOnly:
                CreateLayoutAddGroupBar(self, 'Save Clip to File')
                if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2):
                    self.GroupBorderSpace(10, 0, 0, 0)
                    self.AddStaticText(0, c4d.BFH_LEFT, name='Clip Name')
                    self.AddEditText(ID_DLGSAVE_NAME_DATASET, c4d.BFH_SCALEFIT)
                    self.AddStaticText(0, c4d.BFH_LEFT, name='Path')
                    if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2):
                        self.AddEditText(ID_DLGSAVE_PATH_DATASET, c4d.BFH_SCALEFIT)
                        self.AddButton(ID_DLGSAVE_SET_PATH_DATASET, c4d.BFH_RIGHT, name='...', initw=30)
                    self.GroupEnd()
                self.GroupEnd()
                if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=3):
                    self.GroupBorderSpace(10, 0, 0, 0)
                    self.AddButton(ID_DLGSAVE_STORE_GLOBAL_DATA, c4d.BFH_SCALEFIT, name='Store Global Clip')
                    self.AddButton(ID_DLGSAVE_STORE_LOCAL_DATA, c4d.BFH_SCALEFIT, name='Store Clip in Project')
                    self.AddCheckbox(ID_DLGSAVE_USE_NEW_DATASET, c4d.BFH_SCALEFIT, name='Use New Clip', initw=0, inith=0)
                self.GroupEnd()
            #    self.AddButton(ID_DLGSAVE_DISCARD, c4d.BFH_SCALEFIT, name='DISCARD RECORDING')
            #else:
            #    self.AddButton(ID_DLGSAVE_DISCARD, c4d.BFH_SCALEFIT, name='Close')
        self.GroupEnd() # Dialog main group
        return True

    def UpdateComboSkipFrames(self):
        skipFramesOld = self.GetInt32(ID_DLGSAVE_FRAME_SKIP)
        doc = c4d.documents.GetActiveDocument()
        self.FreeChildren(ID_DLGSAVE_FRAME_SKIP)
        self.AddChild(ID_DLGSAVE_FRAME_SKIP, 1, 'None')
        self.AddChild(ID_DLGSAVE_FRAME_SKIP, 1001, '')
        self.AddChild(ID_DLGSAVE_FRAME_SKIP, 2, '2:1 (every 2nd Studio Frame)')
        self.AddChild(ID_DLGSAVE_FRAME_SKIP, 3, '3:1')
        self.AddChild(ID_DLGSAVE_FRAME_SKIP, 4, '4:1')
        if self.GetInt32(ID_DLGSAVE_TIMING) == 0:
            self.AddChild(ID_DLGSAVE_FRAME_SKIP, 1002, '')
            self.AddChild(ID_DLGSAVE_FRAME_SKIP, 500, '{} FPS (Project)'.format(doc.GetFps()))
            self.AddChild(ID_DLGSAVE_FRAME_SKIP, 1003, '')
            self.AddChild(ID_DLGSAVE_FRAME_SKIP, 10, '10 FPS')
            self.AddChild(ID_DLGSAVE_FRAME_SKIP, 24, '24 FPS')
            self.AddChild(ID_DLGSAVE_FRAME_SKIP, 25, '25 FPS')
            self.AddChild(ID_DLGSAVE_FRAME_SKIP, 30, '30 FPS')
            self.AddChild(ID_DLGSAVE_FRAME_SKIP, 60, '60 FPS')
            self.AddChild(ID_DLGSAVE_FRAME_SKIP, 100, '100 FPS')
        self.SetInt32(ID_DLGSAVE_FRAME_SKIP, skipFramesOld)
        if self.GetInt32(ID_DLGSAVE_TIMING) == 1 and self.GetInt32(ID_DLGSAVE_FRAME_SKIP) > 4:
            self.SetInt32(ID_DLGSAVE_FRAME_SKIP, 1)

    def UpdateSliders(self):
        idConnected = GetConnectedDataSetId()
        includeDataSets = self.GetBool(ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS)
        self._idxFrameLast = 0
        for tag in self._tags:
            if not tag[ID_TAG_VALID_DATA]:
                continue
            idDataSet = tag[ID_TAG_DATA_SET]
            if not includeDataSets and idDataSet != idConnected:
                continue
            if idDataSet == idConnected:
                self._idxFrameLast = max(g_thdListener.GetDataSetSize(idDataSet), self._idxFrameLast)
            else:
                self._idxFrameLast = max(tag[ID_TAG_DATA_SET_LAST_FRAME] - tag[ID_TAG_DATA_SET_FIRST_FRAME] + 1 , self._idxFrameLast)
        idxFrameFirst = self.GetInt32(ID_DLGSAVE_FIRST_FRAME)
        idxFrameLast = self.GetInt32(ID_DLGSAVE_LAST_FRAME)
        if idxFrameFirst > self._idxFrameLast - 1:
            idxFrameFirst = self._idxFrameLast - 1
        if idxFrameLast > self._idxFrameLast:
            idxFrameLast = self._idxFrameLast
        self.SetInt32(ID_DLGSAVE_FIRST_FRAME, idxFrameFirst, min=0, max=self._idxFrameLast-1, min2=0, max2=self._idxFrameLast-1)
        self.SetInt32(ID_DLGSAVE_LAST_FRAME, idxFrameLast, min=1, max=self._idxFrameLast, min2=1, max2=self._idxFrameLast)

    _idxFrameLast = 0
    def InitValues(self):
        nameDataSet = 'New Recording'
        doc = c4d.documents.GetActiveDocument()
        pathDataSet = doc.GetDocumentPath()
        pathDataSet = os.path.join(pathDataSet, nameDataSet + '.rec')
        self.SetString(ID_DLGSAVE_NAME_DATASET, nameDataSet)
        self.SetString(ID_DLGSAVE_PATH_DATASET, pathDataSet)
        bcConnected = GetConnectedDataSet()
        self.SetInt32(ID_DLGSAVE_FIRST_FRAME, 0, min=0, max=self._idxFrameLast-1, min2=0, max2=self._idxFrameLast-1)
        self.SetInt32(ID_DLGSAVE_LAST_FRAME, self._idxFrameLast, min=1, max=self._idxFrameLast, min2=1, max2=self._idxFrameLast)
        self.SetBool(ID_DLGSAVE_CREATE_IN_TAKE, GetPref(ID_DLGSAVE_CREATE_IN_TAKE))
        self.SetBool(ID_DLGSAVE_ACTIVATE_NEW_TAKE, GetPref(ID_DLGSAVE_ACTIVATE_NEW_TAKE))
        self.Enable(ID_DLGSAVE_ACTIVATE_NEW_TAKE, self.GetBool(ID_DLGSAVE_CREATE_IN_TAKE))
        self.SetBool(ID_DLGSAVE_WIPE_EXISTING_ANIMATION, GetPref(ID_DLGSAVE_WIPE_EXISTING_ANIMATION))
        self.SetInt32(ID_DLGSAVE_TIMING, GetPref(ID_DLGSAVE_TIMING))
        self.UpdateComboSkipFrames()
        self.SetInt32(ID_DLGSAVE_FRAME_SKIP, GetPref(ID_DLGSAVE_FRAME_SKIP))
        self.SetInt32(ID_DLGSAVE_LENGTH, GetPref(ID_DLGSAVE_LENGTH))
        self.SetBool(ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS, GetPref(ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS))
        self.SetBool(ID_DLGSAVE_SET_KEYFRAMES_AUTOFORWARD, GetPref(ID_DLGSAVE_SET_KEYFRAMES_AUTOFORWARD))
        self.SetBool(ID_DLGSAVE_USE_NEW_DATASET, GetPref(ID_DLGSAVE_USE_NEW_DATASET))
        return True

    def AskClose(self):
        if self._bakingOnly:
            tagsLive = g_thdListener.GetTagConsumers()
            if tagsLive is not None:
                for tag in tagsLive:
                    if not tag.IsAlive():
                        continue
                    tag[ID_TAG_EXECUTE_MODE] = 0
            g_thdListener.RestoreCurrentPositions()
        g_thdListener.RemoveAllTagConsumers()
        if self._dlgParent is not None:
            self._dlgParent.EnableDialog(True)
            self._dlgParent.CommandPlayerExit()
        c4d.EventAdd()
        return False

    _lastEvent = 0
    def Message(self, msg, result):
        idMsg = msg.GetId()
        if idMsg == c4d.BFM_ACTION:
            if msg[c4d.BFM_ACTION_ID] == ID_DLGSAVE_FIRST_FRAME:
                idxFrame = self.GetInt32(ID_DLGSAVE_FIRST_FRAME)
                if idxFrame > self.GetInt32(ID_DLGSAVE_LAST_FRAME):
                    self.SetInt32(ID_DLGSAVE_LAST_FRAME, idxFrame + 1, min=1, max=self._idxFrameLast, min2=1, max2=self._idxFrameLast)
            elif msg[c4d.BFM_ACTION_ID] == ID_DLGSAVE_LAST_FRAME:
                idxFrame = self.GetInt32(ID_DLGSAVE_LAST_FRAME)
                if idxFrame < self.GetInt32(ID_DLGSAVE_FIRST_FRAME):
                    self.SetInt32(ID_DLGSAVE_FIRST_FRAME, idxFrame - 1, min=0, max=self._idxFrameLast-1, min2=0, max2=self._idxFrameLast-1)
            else:
                return c4d.gui.GeDialog.Message(self, msg, result)
            now = c4d.GeGetTimer()
            if now - self._lastEvent < 50:
                return c4d.gui.GeDialog.Message(self, msg, result)
            g_thdListener.FlushTagConsumers()
            g_thdListener.DispatchFrame(idxFrame + 1, event=False)
            c4d.documents.GetActiveDocument().ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
            c4d.DrawViews(c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW | c4d.DRAWFLAGS_NO_THREAD)
            self._lastEvent = now
        return c4d.gui.GeDialog.Message(self, msg, result)


    def PrepareCurvesInTake(self, takeData, take, obj, overrides, curves, descId, mgTPose):
        if mgTPose is not None:
            if descId[0].id == c4d.ID_BASEOBJECT_REL_ROTATION:
                vDefault = c4d.utils.MatrixToHPB(~obj.GetUpMg() * MR_Y180 * mgTPose)
            else:
                vDefault = (~obj.GetUpMg() * MR_Y180 * mgTPose).off
        else:
            vDefault = obj.GetMl().off
        vectorComponents = [c4d.VECTOR_X, c4d.VECTOR_Y, c4d.VECTOR_Z]
        descIdComponents = [None, None, None]
        overrideComponents = [None, None, None]
        curveComponents = [None, None, None]
        for idxComponent in range(3):
            descIdComponents[idxComponent] = c4d.DescID(descId[0], c4d.DescLevel(vectorComponents[idxComponent], c4d.DTYPE_REAL, 0))
            overrideComponents[idxComponent] = take.FindOrAddOverrideParam(takeData, obj, descIdComponents[idxComponent], vDefault[idxComponent], None, False)
            if overrideComponents[idxComponent] is None:
                print('ERROR: Failed to override:', descId[0].id, idxComponent)
                break
            overrideComponents[idxComponent].UpdateSceneNode(takeData, descIdComponents[idxComponent])
            ctrack = overrideComponents[idxComponent].FindCTrack(descIdComponents[idxComponent])
            if ctrack is None:
                ctrack = c4d.CTrack(obj, descIdComponents[idxComponent])
                overrideComponents[idxComponent].InsertTrackSorted(ctrack)
            curveComponents[idxComponent] = ctrack.GetCurve(type=c4d.CCURVE_CURVE, bCreate=True)
            if self.GetBool(ID_DLGSAVE_WIPE_EXISTING_ANIMATION):
                curveComponents[idxComponent].FlushKeys()
        nameObj = obj.GetName()
        overrides[nameObj] = overrideComponents
        curves[nameObj] = curveComponents

    def PrepareCurves(self, obj, curves, descId, mgTPose):
        vectorComponents = [c4d.VECTOR_X, c4d.VECTOR_Y, c4d.VECTOR_Z]
        descIdComponents = [None, None, None]
        curveComponents = [None, None, None]
        for idxComponent in range(3):
            descIdComponents[idxComponent] = c4d.DescID(descId[0], c4d.DescLevel(vectorComponents[idxComponent], c4d.DTYPE_REAL, 0))
            ctrack = obj.FindCTrack(descIdComponents[idxComponent])
            if ctrack is None:
                ctrack = c4d.CTrack(obj, descIdComponents[idxComponent])
                obj.InsertTrackSorted(ctrack)
            curveComponents[idxComponent] = ctrack.GetCurve(type=c4d.CCURVE_CURVE, bCreate=True)
            if self.GetBool(ID_DLGSAVE_WIPE_EXISTING_ANIMATION):
                curveComponents[idxComponent].FlushKeys()
        nameObj = obj.GetName()
        curves[nameObj] = curveComponents

    def PrepareMorphCurvesInTake(self, takeData, take, tagPoseMorph, overrides, curves, descIdMorph, nameInStudio):
        valDefault = 0.0
        override = take.FindOrAddOverrideParam(takeData, tagPoseMorph, descIdMorph, valDefault, None, False)
        if override is None:
            print('ERROR: Failed to override pose:', descIdMorph[0].id)
            return
        override.UpdateSceneNode(takeData, descIdMorph)
        ctrack = override.FindCTrack(descIdMorph)
        if ctrack is None:
            ctrack = c4d.CTrack(tagPoseMorph, descIdMorph)
            override.InsertTrackSorted(ctrack)
        curve = ctrack.GetCurve(type=c4d.CCURVE_CURVE, bCreate=True)
        if self.GetBool(ID_DLGSAVE_WIPE_EXISTING_ANIMATION):
            curve.FlushKeys()
        overrides[nameInStudio] = override
        curves[nameInStudio] = curve

    def PrepareMorphCurves(self, tagPoseMorph, curves, descIdMorph, nameInStudio):
        ctrack = tagPoseMorph.FindCTrack(descIdMorph)
        if ctrack is None:
            ctrack = c4d.CTrack(tagPoseMorph, descIdMorph)
            tagPoseMorph.InsertTrackSorted(ctrack)
        curve = ctrack.GetCurve(type=c4d.CCURVE_CURVE, bCreate=True)
        if self.GetBool(ID_DLGSAVE_WIPE_EXISTING_ANIMATION):
            curve.FlushKeys()
        curves[nameInStudio] = curve

    def PrepareTPosePerTag(self, tag):
        tPoseTag = {}
        for nameInStudio, (idx, _, _, _, _, _, _, _) in STUDIO_NAMES_TO_GUESS.items():
            obj = tag[ID_TAG_BASE_RIG_LINKS + idx]
            if obj is None:
                continue
            nameObj = obj.GetName()
            mgBodyPartTPose = tag[ID_TAG_BASE_RIG_MATRICES + idx]
            mgBodyPartTPosePretransformed = tag[ID_TAG_BASE_RIG_MATRICES_PRETRANSFORMED + idx]

            tPoseTag[nameInStudio] = (obj, mgBodyPartTPose, nameObj, mgBodyPartTPosePretransformed)
        return tPoseTag

    def PrepareFacePosesPerTag(self, tag):
        facePoses = {}
        obj = tag.GetObject()
        tagPoseMorph = obj.GetTag(c4d.Tposemorph)
        for nameInStudio, (idxPose, _, _, _, _, _) in FACE_POSE_NAMES.items():
            namePoseC4D = tag[ID_TAG_BASE_FACE_POSES + idxPose]
            if namePoseC4D is None or len(namePoseC4D) <= 0:
                continue
            idxMorph = tag[ID_TAG_BASE_MORPH_INDECES + idxPose]
            descIdMorph = tagPoseMorph.GetMorphID(idxMorph)
            descIdMorph = c4d.DescID(c4d.DescLevel(descIdMorph[0].id, c4d.DTYPE_SUBCONTAINER, 0), c4d.DescLevel(descIdMorph[1].id, c4d.DTYPE_REAL, 0))
            facePoses[nameInStudio] = descIdMorph
        return facePoses

    ##@timing
    def KeyframeActor(self, tag, tPose, data, curvesRot, curvesPos, time):
        idxActor = tag[ID_TAG_ACTOR_INDEX]
        dataActors = data['actors']
        if idxActor == -1 or idxActor >= len(dataActors):
            return
        dataActor = dataActors[idxActor]
        dataBody = dataActor['body']
        objRoot = tag.GetObject()
        objHip = tag[ID_TAG_BASE_RIG_LINKS + 0]
        if objHip != objRoot:
            mgRoot = objRoot.GetMg()
        else:
            mgRoot = c4d.Matrix()
        mgRootTPose = tag[ID_TAG_ROOT_MATRIX]
        for nameInStudio, (obj, mgTPose, nameInRig, mRotOffsetRef) in tPose.items():
            dataBodyPart = dataBody[nameInStudio]
            mStudioNewPose = JSONQuaternionToMatrix(dataBodyPart['rotation'])
            mFinalRot = mStudioNewPose * mRotOffsetRef
            mFinalRot = MR_Y180 * mFinalRot # actually ~MR_Y180 * mFinalRot, but ~MR_Y180 == MR_Y180
            mFinalRot = ~mgRootTPose * mFinalRot
            mFinalRot = mgRoot * mFinalRot
            mFinalRot.off = obj.GetMg().off
            obj.SetMg(mFinalRot)
            vRot = obj.GetRelRot()
            curveComponents = curvesRot[nameInRig]
            for idxComponent in range(3):
                resAddKey = curveComponents[idxComponent].AddKey(time)
                if resAddKey is None:
                    print('ERROR: Failed to add rotation keyframe', nameInStudio, idxComponent)
                    break
                key = resAddKey['key']
                key.SetValue(curveComponents[idxComponent], vRot[idxComponent])
        if 'hip' in tPose:
            (_, mgTPose, nameInRig, _) = tPose['hip']
            hipHeightStudio = dataActor['dimensions']['hipHeight']
            hipHeightStudioC4D = hipHeightStudio * 100.0
            posStudio = dataBody['hip']['position']
            yTPoseHip = mgTPose.off[1]
            scale = yTPoseHip / hipHeightStudio
            y = yTPoseHip * (1 + (posStudio['y'] - hipHeightStudio))
            off = c4d.Vector(-posStudio['x'] * scale,
                             y,
                             -posStudio['z'] * scale)
            off = ~mgRootTPose * off
            off *= GetProjectScale()
            curveComponents = curvesPos[nameInRig]
            for idxComponent in range(3):
                resAddKey = curveComponents[idxComponent].AddKey(time)
                if resAddKey is None:
                    print('ERROR: Failed to add hip position keyframe', idxComponent)
                    break
                key = resAddKey['key']
                key.SetValue(curveComponents[idxComponent], off[idxComponent])

    def KeyframeFace(self, tag, facePoses, data, _, curves, time):
        idxActor = tag[ID_TAG_ACTOR_INDEX]
        dataFace = data['actors'][idxActor]['face']
        obj = tag.GetObject()
        tagPoseMorph = obj.GetTag(c4d.Tposemorph)
        for nameInStudio, descIdMorph in facePoses.items():
            curve = curves[nameInStudio]
            resAddKey = curve.AddKey(time)
            if resAddKey is None:
                print('ERROR: Failed to add posemorph keyframe', nameInStudio)
                break
            key = resAddKey['key']
            strength = float(dataFace[nameInStudio]) / 100.0
            key.SetValue(curve, strength)

    def KeyframeProp(self, tag, data, curvesRot, curvesPos, time):
        idxProp = tag[ID_TAG_ACTOR_INDEX]
        dataProps = data['props']
        if idxProp == -1 or idxProp >= len(dataProps):
            return
        dataProp = dataProps[idxProp]
        objProp = tag.GetObject()
        nameObjProp = objProp.GetName()
        mPropStudio = JSONQuaternionToMatrix(dataProp['rotation'])
        mFinalRot = MR_Y180 * mPropStudio
        mFinalRot.off = objProp.GetMg().off
        objProp.SetMg(mFinalRot)
        vRot = objProp.GetRelRot()
        curveComponents = curvesRot[nameObjProp]
        for idxComponent in range(3):
            resAddKey = curveComponents[idxComponent].AddKey(time)
            if resAddKey is None:
                print('ERROR: Failed to add prop rotation keyframe', idxComponent)
                break
            key = resAddKey['key']
            key.SetValue(curveComponents[idxComponent], vRot[idxComponent])
        posStudio = dataProp['position']
        off = c4d.Vector(-posStudio['x'] * 100.0,
                         posStudio['y'] * 100.0,
                         -posStudio['z'] * 100.0)
        off *= GetProjectScale()
        curveComponents = curvesPos[nameObjProp]
        for idxComponent in range(3):
            resAddKey = curveComponents[idxComponent].AddKey(time)
            if resAddKey is None:
                print('ERROR: Failed to add prop position keyframe', idxComponent)
                break
            key = resAddKey['key']
            key.SetValue(curveComponents[idxComponent], off[idxComponent])

    def KeyframeTags(self, dataQueue, idxFirstFrame, idxLastFrame, tag, tPose, curvesRot, curvesPos, time, timeStart, timeMax, idxLastKey):
        behaviorAtEnd = self.GetInt32(ID_DLGSAVE_LENGTH)
        timing = self.GetInt32(ID_DLGSAVE_TIMING)
        skipFrames = self.GetInt32(ID_DLGSAVE_FRAME_SKIP)
        skipByIndex = skipFrames < 10
        skipByTime = skipFrames >= 10
        if skipFrames == 500:
            doc = tag.GetDocument()
            skipFrames = doc.GetFps()
        if skipByTime:
            skipFrames = 1.0 / float(skipFrames)
        numFrames = idxLastFrame - idxFirstFrame + 1
        if tag[ID_TAG_DATA_SET] != GetConnectedDataSetId():
            idxFirstFrameTag = tag[ID_TAG_DATA_SET_FIRST_FRAME]
            idxLastFrameTag = tag[ID_TAG_DATA_SET_LAST_FRAME]
        else:
            idxFirstFrameTag = 0
            idxLastFrameTag = len(dataQueue) - 1
        lenTagClip = idxLastFrameTag - idxFirstFrameTag + 1
        idxFirstFrameEffective = idxFirstFrameTag + idxFirstFrame % lenTagClip
        tsLast = dataQueue[idxFirstFrameEffective]['scene']['timestamp']
        timeLast = timeStart
        for idxFrame in range(numFrames):
            idxFrameEffective = idxFirstFrameEffective + idxFrame % lenTagClip
            data = dataQueue[idxFrameEffective]
            c4d.StatusSetBar(int(100.0 * float(idxFrame) / float(numFrames)))
            if timing == 0:
                ts = dataQueue[idxFrameEffective]['scene']['timestamp']
                tsDiff = ts - tsLast
                if tsDiff < 0.0:
                    tsDiff = 1.0 / float(dataQueue[idxFrameEffective]['fps'])
                if skipByTime and tsDiff < skipFrames and idxFrame != 0:
                    continue
                time = timeLast + c4d.BaseTime(tsDiff)
                tsLast = ts
                timeLast = time
            else:
                time = timeStart + c4d.BaseTime(idxFrame, fps)
            if behaviorAtEnd == 1 and time > timeMax:
                break
            if skipByIndex and (idxFrame % skipFrames) != 0:
                continue
            if tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR:
                self.KeyframeActor(tag, tPose, data['scene'], curvesRot, curvesPos, time)
            elif tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR_FACE:
                self.KeyframeFace(tag, tPose, data['scene'], curvesRot, curvesPos, time)
            elif tag[ID_TAG_RIG_TYPE] & RIG_TYPE_PROP:
                self.KeyframeProp(tag, data['scene'], curvesRot, curvesPos, time)
            else:
                print('KEYFRAMES RIG TYPE MISSING', tag[ID_TAG_RIG_TYPE])
            idxLastKey[0] = max(idxLastKey[0], idxFrame)

    def CommandSetKeyframes(self, atCurrent=False, everyNth=1):
        idConnected = GetConnectedDataSetId()
        idxFirstFrame = self.GetInt32(ID_DLGSAVE_FIRST_FRAME)
        idxLastFrame = self.GetInt32(ID_DLGSAVE_LAST_FRAME)
        createTake = self.GetBool(ID_DLGSAVE_CREATE_IN_TAKE)
        if not self._bakingOnly:
            nameDataSet = self.GetString(ID_DLGSAVE_NAME_DATASET)
        else:
            nameDataSet = GetDataSetFromId(self._tags[0][ID_TAG_DATA_SET])[ID_BC_DATASET_NAME]
        behaviorAtEnd = self.GetInt32(ID_DLGSAVE_LENGTH)
        autoForward = self.GetBool(ID_DLGSAVE_SET_KEYFRAMES_AUTOFORWARD)
        includeDataSets = self.GetBool(ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS)
        doc = c4d.documents.GetActiveDocument()
        fps = doc.GetFps()
        if atCurrent:
            timeStart = doc.GetTime()
        else:
            timeStart = c4d.BaseTime(0.0)
        numDataFrames = idxLastFrame - idxFirstFrame + 1
        timeMax = doc.GetMaxTime()
        timeStudioMax = c4d.BaseTime(0.016667 * numDataFrames)
        if behaviorAtEnd == 0 and (timeStart + timeStudioMax) > timeMax:
            doc.SetMaxTime(timeStart + timeStudioMax)
        descIdRot = c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_ROTATION, c4d.DTYPE_VECTOR, 0))
        descIdRotComponents = [None, None, None]
        descIdRotComponents[0] = c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_ROTATION, c4d.DTYPE_VECTOR, 0), c4d.DescLevel(c4d.VECTOR_X, c4d.DTYPE_REAL, 0))
        descIdRotComponents[1] = c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_ROTATION, c4d.DTYPE_VECTOR, 0), c4d.DescLevel(c4d.VECTOR_Y, c4d.DTYPE_REAL, 0))
        descIdRotComponents[2] = c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_ROTATION, c4d.DTYPE_VECTOR, 0), c4d.DescLevel(c4d.VECTOR_Z, c4d.DTYPE_REAL, 0))
        descIdPos = c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION, c4d.DTYPE_VECTOR, 0))
        descIdPosComponents = [None, None, None]
        descIdPosComponents[0] = c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION, c4d.DTYPE_VECTOR, 0), c4d.DescLevel(c4d.VECTOR_X, c4d.DTYPE_REAL, 0))
        descIdPosComponents[1] = c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION, c4d.DTYPE_VECTOR, 0), c4d.DescLevel(c4d.VECTOR_Y, c4d.DTYPE_REAL, 0))
        descIdPosComponents[2] = c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION, c4d.DTYPE_VECTOR, 0), c4d.DescLevel(c4d.VECTOR_Z, c4d.DTYPE_REAL, 0))
        c4d.StatusClear()
        c4d.StatusSetText('Baking Rokoko Motion to Keyframes...')
        c4d.StatusSetBar(0)
        doc.StartUndo()
        idxLastKey = [0]
        if createTake:
            takeData = doc.GetTakeData()
            if takeData is None:
                print('ERROR: Failed to retrieve the take data.')
                return
            take = takeData.AddTake(nameDataSet, None, None)
            if take is None:
                print('ERROR: Failed to add a new take.')
                return
            doc.AddUndo(c4d.UNDOTYPE_NEW, take)
            takeOld = takeData.GetCurrentTake()
            takeData.SetCurrentTake(takeData.GetMainTake())
        g_thdListener.RestoreCurrentPositions()
        for tag in self._tags:
            idDataSet = tag[ID_TAG_DATA_SET]
            if (not self._bakingOnly and not includeDataSets and idDataSet != idConnected) or not tag[ID_TAG_VALID_DATA]:
                continue
            dataQueue = g_thdListener._dataQueues[idDataSet]
            if createTake:
                if tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR:
                    tPose = self.PrepareTPosePerTag(tag)
                elif tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR_FACE:
                    tPose = self.PrepareFacePosesPerTag(tag)
                else:
                    tPose = None
                overridesRot = {}
                curvesRot = {}
                overridesPos = {}
                curvesPos = {}
                if tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR:
                    for nameInStudio, (obj, mgTPose, nameObj, _) in tPose.items():
                        self.PrepareCurvesInTake(takeData, take, obj, overridesRot, curvesRot, descIdRot, mgTPose)
                        if nameInStudio == 'hip':
                            self.PrepareCurvesInTake(takeData, take, obj, overridesPos, curvesPos, descIdPos, mgTPose)
                elif tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR_FACE:
                    obj = tag.GetObject()
                    tagPoseMorph = obj.GetTag(c4d.Tposemorph)
                    for nameInStudio, descIdMorph in tPose.items():
                        self.PrepareMorphCurvesInTake(takeData, take, tagPoseMorph, overridesPos, curvesPos, descIdMorph, nameInStudio)
                else:
                    obj = tag.GetObject()
                    self.PrepareCurvesInTake(takeData, take, obj, overridesRot, curvesRot, descIdRot, None)
                    self.PrepareCurvesInTake(takeData, take, obj, overridesPos, curvesPos, descIdPos, None)
                self.KeyframeTags(dataQueue, idxFirstFrame, idxLastFrame, tag, tPose, curvesRot, curvesPos, time, timeStart, timeMax, idxLastKey)
                if tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR:
                    for nameInStudio, (obj, mgTPose, nameObj, _) in tPose.items():
                        for idxComponent in range(3):
                            overridesRot[nameObj][idxComponent].UpdateSceneNode(takeData, descIdRotComponents[idxComponent])
                            if nameInStudio == 'hip':
                                overridesPos[nameObj][idxComponent].UpdateSceneNode(takeData, descIdPosComponents[idxComponent])
                elif tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR_FACE:
                    for nameInStudio, descIdMorph in tPose.items():
                        overridesPos[nameInStudio].UpdateSceneNode(takeData, descIdMorph)
                else:
                    obj = tag.GetObject()
                    nameObj = obj.GetName()
                    for idxComponent in range(3):
                        overridesRot[nameObj][idxComponent].UpdateSceneNode(takeData, descIdRotComponents[idxComponent])
                        overridesPos[nameObj][idxComponent].UpdateSceneNode(takeData, descIdPosComponents[idxComponent])
            else:
                root = tag.GetObject()
                doc.AddUndo(c4d.UNDOTYPE_CHANGE, root)
                if tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR:
                    tPose = self.PrepareTPosePerTag(tag)
                elif tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR_FACE:
                    tPose = self.PrepareFacePosesPerTag(tag)
                curvesRot = {}
                curvesPos = {}
                if tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR:
                    for nameInStudio, (obj, mgTPose, nameObj, _) in tPose.items():
                        self.PrepareCurves(obj, curvesRot, descIdRot, mgTPose)
                        if nameInStudio == 'hip':
                            self.PrepareCurves(obj, curvesPos, descIdPos, mgTPose)
                elif tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR_FACE:
                    tagPoseMorph = root.GetTag(c4d.Tposemorph)
                    for nameInStudio, descIdMorph in tPose.items():
                        self.PrepareMorphCurves(tagPoseMorph, curvesPos, descIdMorph, nameInStudio)
                else:
                    self.PrepareCurves(root, curvesRot, descIdRot, None)
                    self.PrepareCurves(root, curvesPos, descIdPos, None)
                self.KeyframeTags(dataQueue, idxFirstFrame, idxLastFrame, tag, tPose, curvesRot, curvesPos, time, timeStart, timeMax, idxLastKey)
        if createTake:
            if self.GetBool(ID_DLGSAVE_ACTIVATE_NEW_TAKE):
                takeData.SetCurrentTake(take)
            else:
                takeData.SetCurrentTake(takeOld)

        if autoForward:
            doc.SetTime(timeStart + c4d.BaseTime(0.016667 * (idxLastKey[0] + 1)))
        doc.EndUndo()
        g_thdListener.RestoreCurrentPositions()
        c4d.EventAdd()
        c4d.StatusClear()
        if createTake:
            c4d.gui.MessageDialog('Successfully baked keyframes in Take "{}".'.format(nameDataSet))
        else:
            c4d.gui.MessageDialog('Successfully baked keyframes in current Take.')

    def CommandStoreDataSet(self, local=False):
        bcConnected = GetConnectedDataSet()
        if bcConnected is None:
            print('ERROR: No connected data set to store')
            return
        idConnected = bcConnected.GetId()
        name = self.GetString(ID_DLGSAVE_NAME_DATASET)
        filename = self.GetString(ID_DLGSAVE_PATH_DATASET)
        filenameInDataSet = filename
        if local:
            pathDocument = c4d.documents.GetActiveDocument().GetDocumentPath()
            if pathDocument is not None and len(pathDocument) > 1:
                filenameInDataSet = filenameInDataSet.replace(pathDocument, '.', 1)
        if name + '.rec' == filename:
            c4d.gui.MessageDialog('It seems you have not specified a path, yet.\nMaybe the project has not been saved?')
            return
        bcNewDataSet = bcConnected.GetClone(c4d.COPYFLAGS_NONE)
        bcNewDataSet[ID_BC_DATASET_NAME] = name
        bcNewDataSet[ID_BC_DATASET_TYPE] = 1 # type: 0 - connection, 1 - file
        bcNewDataSet[ID_BC_DATASET_CONNECTED] = False
        bcNewDataSet[ID_BC_DATASET_AVAILABLE_IN_DOC] = True
        bcNewDataSet[ID_BC_DATASET_LIVE_PORT] = ''
        bcNewDataSet[ID_BC_DATASET_LIVE_AUTOCONNECT] = False
        bcNewDataSet[ID_BC_DATASET_FILENAME] = filenameInDataSet
        bcNewDataSet[ID_BC_DATASET_IS_LOCAL] = local
        idDataSetNew = MyHash(name + filenameInDataSet + str(local))
        bcNewDataSet.SetId(idDataSetNew)
        AddDataSetBC(bcNewDataSet)
        if self._dlgParent is not None:
            self._dlgParent.UpdateLayoutGroupDataSet(local)
        g_thdListener.SaveLiveData(filename, self.GetInt32(ID_DLGSAVE_FIRST_FRAME), self.GetInt32(ID_DLGSAVE_LAST_FRAME))
        for tag in self._tags:
            tag.Message(c4d.MSG_MENUPREPARE)
            if self.GetBool(ID_DLGSAVE_USE_NEW_DATASET):
                if tag[ID_TAG_DATA_SET] == idConnected:
                    tag[ID_TAG_DATA_SET] = idDataSetNew
        c4d.EventAdd()
        if local:
            c4d.gui.MessageDialog('Successfully stored clip "{}" in project.'.format(name))
        else:
            c4d.gui.MessageDialog('Successfully stored global clip "{}".'.format(name))

    def Command(self, id, msg):
        if id == ID_DLGSAVE_SET_PATH_DATASET:
            pathDefault = c4d.documents.GetActiveDocument().GetDocumentPath()
            filenameDefault = self.GetString(ID_DLGSAVE_NAME_DATASET)
            filename = c4d.storage.SaveDialog(type=c4d.FILESELECTTYPE_ANYTHING, title='Choose Clip Filename...', force_suffix='rec', def_path=pathDefault, def_file=filenameDefault)
            if filename is None or len(filename) < 2:
                return True
            self.SetString(ID_DLGSAVE_PATH_DATASET, filename)
        elif id == ID_DLGSAVE_FIRST_FRAME:
            if self.GetInt32(ID_DLGSAVE_FIRST_FRAME) > self.GetInt32(ID_DLGSAVE_LAST_FRAME):
                self.SetInt32(ID_DLGSAVE_LAST_FRAME, self.GetInt32(ID_DLGSAVE_FIRST_FRAME) + 1, min=1, max=self._idxFrameLast, min2=1, max2=self._idxFrameLast)
        elif id == ID_DLGSAVE_LAST_FRAME:
            if self.GetInt32(ID_DLGSAVE_LAST_FRAME) < self.GetInt32(ID_DLGSAVE_FIRST_FRAME):
                self.SetInt32(ID_DLGSAVE_FIRST_FRAME, self.GetInt32(ID_DLGSAVE_LAST_FRAME) - 1, min=0, max=self._idxFrameLast-1, min2=0, max2=self._idxFrameLast-1)
        elif id == ID_DLGSAVE_STORE_LOCAL_DATA:
            self.CommandStoreDataSet(local=True)
        elif id == ID_DLGSAVE_STORE_GLOBAL_DATA:
            self.CommandStoreDataSet()
        elif id == ID_DLGSAVE_SET_KEYFRAMES_AT_CURRENT:
            self.CommandSetKeyframes(atCurrent=True)
        elif id == ID_DLGSAVE_SET_KEYFRAMES_AT_0:
            self.CommandSetKeyframes()
        elif id == ID_DLGSAVE_CREATE_IN_TAKE:
            SetPref(id, self.GetBool(id))
            self.Enable(ID_DLGSAVE_ACTIVATE_NEW_TAKE, self.GetBool(ID_DLGSAVE_CREATE_IN_TAKE))
        elif id == ID_DLGSAVE_ACTIVATE_NEW_TAKE:
            SetPref(id, self.GetBool(id))
        elif id == ID_DLGSAVE_WIPE_EXISTING_ANIMATION:
            SetPref(id, self.GetBool(id))
        elif id == ID_DLGSAVE_TIMING:
            SetPref(id, self.GetInt32(id))
            self.UpdateComboSkipFrames()
        elif id == ID_DLGSAVE_FRAME_SKIP:
            SetPref(id, self.GetInt32(id))
        elif id == ID_DLGSAVE_LENGTH:
            SetPref(id, self.GetInt32(id))
        elif id == ID_DLGSAVE_SET_KEYFRAMES_AUTOFORWARD:
            SetPref(id, self.GetBool(id))
        elif id == ID_DLGSAVE_USE_NEW_DATASET:
            SetPref(id, self.GetBool(id))
        elif id == ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS:
            SetPref(id, self.GetBool(id))
            self.UpdateSliders()
        elif id == ID_DLGSAVE_DISCARD:
            self.Close()
        return True
