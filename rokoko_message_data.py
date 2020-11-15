# In Cinema 4D a MessageData plugin has no real function itself. As the name suggests it's main
# purpose is to receive messages. In contrast to dialogs it does so all the time
# (C4D's runtime, while a dialog needs to be open to receive messages).
#
# Messages are received in CoreMessage(), which is guranteed to be called from the main thread.
#
# In the context of Rokoko Studio Live it is a central component, owning the listener thread and being
# the listeners event interface. Receiving events for example to control the player and sending around
# status and.update events. The viewport updates during playback are also done here.
import sys
import c4d
from rokoko_ids import *
from rokoko_utils import *
from rokoko_listener import *

g_thdListener = GetListenerThread() # owned by rokoko_listener
def MessageDataDestroyGlobals():
    global g_thdListener
    g_thdListener = None

class MessageDataRokoko(c4d.plugins.MessageData):
    _docLast = None
    _init = 0

    def StartAutoConnect(self):
        self._init = 1
        bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
        bcConnected = GetConnectedDataSet()
        if bcConnected is not None: # TODO Not sure yet, how the connected dataset survives shutdown (it's deleted in PluginMessage END_ACTIVITY...)
            RemoveConnectedDataSet()
        if len(bcConnections) > 0:
            for id, bcConnection in bcConnections:
                if not bcConnection[ID_BC_DATASET_LIVE_AUTOCONNECT]:
                    continue
                SetConnectedDataSet(bcConnection)
                g_thdListener.Connect()
                break


    def FinishAutoConnect(self):
        global g_forceUpdate
        self._init = 2
        g_forceUpdate = True
        tags = GetTagList()
        for tag in tags:
            tag.Message(c4d.MSG_MENUPREPARE)
        g_forceUpdate = False


    _cntUpdateDlgFrameCount = 0
    def CoreMessageLiveDraw(self):
        frameNumberDispatch, frameMax = g_thdListener.GetCurrentFrameNumber()
        playbackRate = GetPref(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED)
        if playbackRate > 2:
            self._cntUpdateDlgFrameCount == 0
        else:
            div = 4 - playbackRate
            self._cntUpdateDlgFrameCount == (self._cntUpdateDlgFrameCount + 1) % div
        if self._cntUpdateDlgFrameCount == 0:
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER_CURRENT_FRAME_NUMBER, frameNumberDispatch, frameMax)
        if GetPref(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT):
            doc = c4d.documents.GetActiveDocument()
            tMax = doc.GetMaxTime().Get()
            tDispatch = 0.01667 * frameNumberDispatch
            t = c4d.BaseTime(tDispatch % tMax)
            doc.SetTime(t)
        c4d.DrawViews(c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW | c4d.DRAWFLAGS_NO_THREAD)


    def CoreMessageConnect(self, bc):
        if GetConnectedDataSet() is not None:
            return True
        idConnection = GetCoreMessageParam23(bc, id=c4d.BFM_CORE_PAR2)
        SetConnectedDataSet(GetPrefsContainer(ID_BC_CONNECTIONS)[idConnection])
        g_thdListener.Connect()


    def CoreMessageDisconnect(self):
        g_thdListener.Disconnect()
        RemoveConnectedDataSet()


    def CoreMessageStartListening(self):
        c4d.CallCommand(12002) # Stop
        if GetConnectedDataSet() is None:
            g_thdListener.ConnectNoConnection()
        doc = c4d.documents.GetActiveDocument()
        g_thdListener.StoreTime(doc.GetTime())
        tagsLive = g_thdListener.GetTagConsumers()
        g_thdListener.StoreCurrentPositions(tagsLive)
        if GetPref(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT):
            doc.SetTime(c4d.BaseTime(0.0))
        g_thdListener.StartReception()


    def CoreMessagePauseListening(self):
        g_thdListener.PauseReception()


    def CoreMessageStopListening(self):
        doc = c4d.documents.GetActiveDocument()
        storedTime = g_thdListener.GetStoredTime()
        if storedTime is not None:
            doc.SetTime(storedTime)
        g_thdListener.RestoreCurrentPositions()
        bcConnected = GetConnectedDataSet()
        g_thdListener.StopReception()
        if bcConnected is None:
            g_thdListener.DisconnectNoConnection()


    def CoreMessageClearLiveBuffer(self):
        if GetPref(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT):
            doc = c4d.documents.GetActiveDocument()
            doc.SetTime(c4d.BaseTime(0.0))
        g_thdListener.FlushBuffers()


    def CoreMessagePlay(self, bc):
        c4d.CallCommand(12002) # Stop
        returnToLive = GetCoreMessageParam23(bc, id=c4d.BFM_CORE_PAR2)
        if returnToLive == 1:
            g_thdListener.SyncFrameCounters()
        g_thdListener.FlushTagConsumers()
        g_thdListener._play = True
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_PLAYBACK_STATUS_CHANGE)
        tags = GetTagList()
        for tag in tags:
            tag.SetDirty(c4d.DIRTYFLAGS_DESCRIPTION)
        tagsLive = g_thdListener.GetTagConsumers()
        for tag in tagsLive:
            tag.GetDataInstance()[ID_TAG_EXECUTE_MODE] = 1 # avoid SetParameter


    def CoreMessagePause(self, bc):
        if g_thdListener._play:
            g_thdListener._play = False
            g_thdListener._inSync = False
            g_thdListener.FlushTagConsumers()
        idxFrame = GetCoreMessageParam23(bc, id=c4d.BFM_CORE_PAR2)
        g_thdListener.DispatchFrame(idxFrame)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_PLAYBACK_STATUS_CHANGE)


    def CoreMessageStop(self):
        if g_thdListener._play:
            g_thdListener._play = False
            g_thdListener._inSync = True
            g_thdListener.FlushTagConsumers()
            g_thdListener.RemoveAllTagConsumers()
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER_CURRENT_FRAME_NUMBER, 0, 0)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_PLAYBACK_STATUS_CHANGE)
        tags = GetTagList()
        for tag in tags:
            tag[ID_TAG_EXECUTE_MODE] = 0
            tag.SetDirty(c4d.DIRTYFLAGS_DESCRIPTION)


    def CoreMessageConnectionStatusChange(self):
        if self._init == 1:
            self.FinishAutoConnect()


    def CoreMessageLiveDataChange(self):
        bcConnected = GetConnectedDataSet()
        tags = GetTagList()
        for tag in tags:
            tag.Message(PLUGIN_ID_MSG_DATA_CHANGE)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAG_PARAMS)
        c4d.EventAdd()


    def CoreMessageEMsgChange(self):
        docCurrent = c4d.documents.GetActiveDocument()
        if self._docLast is not None and self._docLast.IsAlive() and docCurrent == self._docLast:
            return
        self._docLast = docCurrent
        self.CoreMessageStop()
        self.CoreMessageStopListening()
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAGS)
        global g_forceUpdate
        g_forceUpdate = True
        tags = GetTagList()
        for tag in tags:
            tag.Message(c4d.MSG_MENUPREPARE)
        g_forceUpdate = False


    def CoreMessage(self, id, bc):
        if self._init == 0:
            self.StartAutoConnect()
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
