# In Cinema 4D a MessageData plugin has no real function itself. As the name suggests it's main
# purpose is to receive messages. In contrast to dialogs it does so all the time
# (C4D's runtime, while a dialog needs to be open to receive messages).
#
# Messages are received in CoreMessage(), which is guranteed to be called from the main thread.
#
# In the context of Rokoko Studio Live it is a central component, owning the listener thread (well, it's the
# listener thread is a global resource, so it's more in a sense of this MessageData (mainly) controlling
# the listener thread) and being the listener's event interface.
# Receiving events for example to control the player and sending around
# status and update events.
#
# The viewport updates during playback are also done here, basically in reaction to an event
# message caused by a frame dispatch.
import sys
import c4d
from rokoko_ids import *
from rokoko_utils import *
from rokoko_listener import *

g_thdListener = GetListenerThread() # created by rokoko_listener during initialization

# To be called during shutdown
def MessageDataDestroyGlobals():
    global g_thdListener
    g_thdListener = None


class MessageDataRokoko(c4d.plugins.MessageData):
    _docLast = None
    _init = 0 # State of auto connect during startup (0: auto connect not done, yet, 1: auto connect in progress, 2: auto connect done)

    # Used upon first received message to initiate auto connect
    def StartAutoConnect(self):
        self._init = 1 # auto connect in progress

        # TODO Not sure yet, how the connected dataset survives shutdown (it's deleted in PluginMessage END_ACTIVITY...)
        # Anyway, we'll simply throw any remaining connected data set away.
        bcConnected = GetConnectedDataSet()
        if bcConnected is not None:
            RemoveConnectedDataSet()

        # Connect the first connection with auto connect enabled (and only this, in case there should be multiple by mistake)
        bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
        for id, bcConnection in bcConnections:
            if not bcConnection[ID_BC_DATASET_LIVE_AUTOCONNECT]:
                continue
            SetConnectedDataSet(bcConnection)
            g_thdListener.Connect()
            break

    # Upon "connection status change" message, an auto connect in progress is finalized here
    def FinishAutoConnect(self):
        self._init = 2 # auto connect done

        # Have all tags recognize the new connection (e.g. to reflect new actors,...)
        tags = GetTagList()
        for tag in tags:
            tag.Message(c4d.MSG_MENUPREPARE)


    # Counter _cntUpdateDlgFrameCount is used here in CoreMessageLiveDraw(), only.
    # Its purpose is to reduce the number of update events send to the player to a
    # "reasonable yet good looking" amount.
    _cntUpdateDlgFrameCount = 0

    # CoreMessageLiveDraw() is the reaction to a "live draw request" message,
    # which is sent after frames got dispatched to tags.
    # This will trigger C4D's execution pipeline and scene evaluation, resulting in Execute() calls
    # to our (well, not only, actually all) tags, followed by a viewport update.
    def CoreMessageLiveDraw(self):
        # Depending on "Playback Rate" set by the user, send the current frame number
        # only every other frame to the Manager dialog.
        frameNumberDispatch, frameMax = g_thdListener.GetCurrentFrameNumber()
        playbackRate = GetPref(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED)
        if playbackRate > 2:
            self._cntUpdateDlgFrameCount == 0
        else:
            div = 4 - playbackRate
            self._cntUpdateDlgFrameCount == (self._cntUpdateDlgFrameCount + 1) % div
        if self._cntUpdateDlgFrameCount == 0:
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER_CURRENT_FRAME_NUMBER, frameNumberDispatch, frameMax)

        # Depending on "Animate Document" setting, set document's time
        if GetPref(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT):
            doc = c4d.documents.GetActiveDocument()
            tMax = doc.GetMaxTime().Get()
            tDispatch = 0.01667 * frameNumberDispatch
            t = c4d.BaseTime(tDispatch % tMax)
            doc.SetTime(t)

        # Trigger scene execution and draw viewport
        c4d.DrawViews(c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW | c4d.DRAWFLAGS_NO_THREAD)


    # React to "connect request" message from Manager dialog.
    def CoreMessageConnect(self, bc):
        if GetConnectedDataSet() is not None:
            return True
        idConnection = GetCoreMessageParam23(bc, id=c4d.BFM_CORE_PAR2)
        SetConnectedDataSet(GetPrefsContainer(ID_BC_CONNECTIONS)[idConnection])
        g_thdListener.Connect()


    # React to a "disconnect request" message from Manager dialog
    def CoreMessageDisconnect(self):
        g_thdListener.Disconnect()
        RemoveConnectedDataSet()


    # React to "start player request" message
    def CoreMessageStartListening(self):
        # In case C4D is currently playing an animation, stop it
        c4d.CallCommand(12002) # Stop

        # If there is no live connection, connect the "offline" player thread
        if GetConnectedDataSet() is None:
            g_thdListener.ConnectNoConnection()

        # Backup state of all objects we'll be messing with during playback (plus current document time)
        doc = c4d.documents.GetActiveDocument()
        g_thdListener.StoreTime(doc.GetTime())
        tagsLive = g_thdListener.GetTagConsumers()
        g_thdListener.StoreCurrentPositions(tagsLive)

        # If "Animate Document" is enabled, reset document time to zero
        if GetPref(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT):
            doc.SetTime(c4d.BaseTime(0.0))

        # Kick off the can... (start actively receiving)
        g_thdListener.StartReception()


    # React to "pause receiver request" message
    # This happens on "Save Recording". It is NOT a player pause,
    # but actually a receiver pause. Basically stopping reception
    # and keeping the already received motiuon data.
    def CoreMessagePauseListening(self):
        g_thdListener.PauseReception()


    # React to "stop player request" message
    def CoreMessageStopListening(self):
        # Restore previous document time
        storedTime = g_thdListener.GetStoredTime()
        if storedTime is not None:
            doc = c4d.documents.GetActiveDocument()
            doc.SetTime(storedTime)

        # Restore previous object states
        g_thdListener.RestoreCurrentPositions()

        # Stop reception (buffering of frames)
        g_thdListener.StopReception()

        # If playing offline, exit the offline player thread
        if not IsConnected():
            g_thdListener.DisconnectNoConnection()


    # React to "flush buffer request" message
    # Throws away any previously received frames.
    def CoreMessageClearLiveBuffer(self):
        # If "Animate Document" is enabled, also reset document time to zero
        if GetPref(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT):
            doc = c4d.documents.GetActiveDocument()
            doc.SetTime(c4d.BaseTime(0.0))

        g_thdListener.FlushBuffers()


    # React to "Player play request" message
    def CoreMessagePlay(self, bc):
        # In case C4D is playing an animation already, stop it
        c4d.CallCommand(12002) # Stop

        # If requested, player resyncs with incoming live stream
        returnToLive = GetCoreMessageParam23(bc, id=c4d.BFM_CORE_PAR2)
        if returnToLive == 1:
            g_thdListener.SyncFrameCounters()

        # Flush dispatch queues in tags
        g_thdListener.FlushTagConsumers()

        # Set player state
        g_thdListener._play = True

        # Inform Manager dialog about changed player status
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_PLAYBACK_STATUS_CHANGE)

        # Update all tags descriptions to properly reflect the new player state
        tags = GetTagList()
        for tag in tags:
            tag.SetDirty(c4d.DIRTYFLAGS_DESCRIPTION)

        # All involved tags have their execution flag set, in order to have their Execute()
        # function actually do something.
        tagsLive = g_thdListener.GetTagConsumers()
        for tag in tagsLive:
            tag.GetDataInstance()[ID_TAG_EXECUTE_MODE] = 1 # avoid SetParameter


    # React to "Player pause request" message
    def CoreMessagePause(self, bc):
        if g_thdListener._play:
            g_thdListener._play = False
            g_thdListener._inSync = False # player no longer plays incoming live stream
            g_thdListener.FlushTagConsumers()

        # Dispatch the frame, the player was paused upon
        idxFrame = GetCoreMessageParam23(bc, id=c4d.BFM_CORE_PAR2)
        g_thdListener.DispatchFrame(idxFrame)

        # Inform Manager dialog about changed player status
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_PLAYBACK_STATUS_CHANGE)


    # React to "Player stop request" message
    def CoreMessageStop(self):
        if g_thdListener._play:
            g_thdListener._play = False
            g_thdListener._inSync = True
            g_thdListener.FlushTagConsumers()
            g_thdListener.RemoveAllTagConsumers()

        # Have Manager dialog reset its frame counter and scrub bar
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER_CURRENT_FRAME_NUMBER, 0, 0)
        # Inform Manager dialog about changed player status
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_PLAYBACK_STATUS_CHANGE)

        # Reset execute flags in all tags and
        # update their descriptions to properly reflect the new player state
        tags = GetTagList()
        for tag in tags:
            tag[ID_TAG_EXECUTE_MODE] = 0
            tag.SetDirty(c4d.DIRTYFLAGS_DESCRIPTION)

        c4d.EventAdd()


    # React to "connection status change" message
    # Actually a message received by the Manager dialog to update connection status.
    # Hehe it's only used to finalize the auto connection process.
    def CoreMessageConnectionStatusChange(self):
        if self._init == 1:
            self.FinishAutoConnect()


    # React to "live data changed" message
    def CoreMessageLiveDataChange(self):
        # Inform tags about changed live data.
        # (e.g. new actors may become available or old ones might have gone missing)
        tags = GetTagList()
        for tag in tags:
            tag.Message(PLUGIN_ID_MSG_DATA_CHANGE)

        # Inform Manager dialog about possible change in tag parameters
        # (e.g. selected data sets or actors may have become available).
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAG_PARAMS)
        c4d.EventAdd()


    # React to C4D's EVMSG_CHANGE
    # In this plugin it's used only to detect if the current document has changed
    # (talking about a different document, NOT a change within a document).
    def CoreMessageEMsgChange(self):
        # Check if document has changed
        docCurrent = c4d.documents.GetActiveDocument()
        if self._docLast is not None and self._docLast.IsAlive() and docCurrent == self._docLast:
            return # document did not change, nothing to do
        self._docLast = docCurrent

        # Stop Player and reception (in case it's currently running)
        self.CoreMessageStop()
        self.CoreMessageStopListening()

        # Inform Manager dialog about document change (it will need to collect all tags, for example)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAGS)

        # Reinitialize all tags.
        # Several reasons could cause a need for a reinitialization, just a few examples:
        # - Tags may not have connected their data sets, yet.
        # - Connection status may have changed while document was in background.
        tags = GetTagList()
        for tag in tags:
            tag.Message(c4d.MSG_MENUPREPARE)


    # CoreMessage() is the main function of a MessageData plugin.
    # In context of the main thread all kinds of events are received here.
    def CoreMessage(self, id, bc):
        # If not done so already, initate auto connect (happens only once during startup)
        if self._init == 0:
            self.StartAutoConnect()

        # Decode received event message
        if id == c4d.EVMSG_CHANGE:
            self.CoreMessageEMsgChange()

        elif id == PLUGIN_ID_COREMESSAGE_LIVE_DRAW:
            self.CoreMessageLiveDraw()

        elif id == PLUGIN_ID_COREMESSAGE_CONNECTION:
            subId = GetCoreMessageParam23(bc)
            if subId == CM_SUBID_CONNECTION_CONNECT:
                self.CoreMessageConnect(bc)
            elif subId == CM_SUBID_CONNECTION_DISCONNECT:
                self.CoreMessageDisconnect()
            elif subId == CM_SUBID_CONNECTION_STATUS_CHANGE:
                self.CoreMessageConnectionStatusChange()
            elif subId == CM_SUBID_CONNECTION_LIVE_DATA_CHANGE:
                self.CoreMessageLiveDataChange()

        elif id == PLUGIN_ID_COREMESSAGE_PLAYER:
            subId = GetCoreMessageParam23(bc)
            if subId == CM_SUBID_PLAYER_START:
                self.CoreMessageStartListening()
            elif subId == CM_SUBID_PLAYER_PAUSE_RECEPTION:
                self.CoreMessagePauseListening()
            elif subId == CM_SUBID_PLAYER_EXIT:
                self.CoreMessageStopListening()
            elif subId == CM_SUBID_PLAYER_PLAY:
                self.CoreMessagePlay(bc)
            elif subId == CM_SUBID_PLAYER_PAUSE:
                self.CoreMessagePause(bc)
            elif subId == CM_SUBID_PLAYER_STOP:
                self.CoreMessageStop()
            elif subId == CM_SUBID_PLAYER_FLUSH_LIVE_BUFFER:
                self.CoreMessageClearLiveBuffer()
        return True
