import os, socket, json, time
from threading import Condition
import lz4.frame
import c4d
from rokoko_ids import *
from rokoko_rig_tables import *
from rokoko_utils import *
from rokoko_tag_queue import *

g_thdListener = None
def GetListenerThread():
    return g_thdListener

def DestroyListenerThread():
    global g_thdListener
    if g_thdListener is not None:
        g_thdListener.Disconnect()
        g_thdListener.ClearTagConsumers()
        g_thdListener.DiscardDataQueues()
        g_thdListener = None

class ThreadListener(c4d.threading.C4DThread):
    _idDataSet = -1
    _sock = None
    _receive = False
    _play = False
    _inSync = True
    _idLiveConnection = -1
    _liveQueue = None
    _dataQueues = {}
    _lockDataQueues = Condition()
    _frameNumberReceive = 0
    _frameNumberDispatch = 0
    _lockFrameCounter = Condition()
    _maxFramesInDataSets = 0
    _tags = []
    _lockTagQueues = Condition()
    _lockConnect = Condition()
    _statusConnection = 0 # 0: Not connected, 1: Connected Ok, 2: Connected No Data
    _statusConnectionLast = 0
    _dataExample = None
    _timeStored = None
    _tLiveBackup = []
    _tLiveBackupPoseMorphs = []
    _cntDetect = 0
    _cntBufferPulse = 0
    _cntPlaybackRate = 0

    def StoreTime(self, t):
        self._timeStored = t
    def GetStoredTime(self):
        return self._timeStored

    def AddBackupMg(self, tag):
        for nameInStudio, (idx, _, _, _, _, _, _, _) in STUDIO_NAMES_TO_GUESS.items():
            obj = tag[ID_TAG_BASE_RIG_LINKS + idx]
            if obj is None:
                continue
            nameObj = obj.GetName()
            self._tLiveBackup[-1][nameObj] = (obj, obj.GetMg())

    def AddBackupPoseMorph(self, tag):
        obj = tag.GetObject()
        tagPoseMorph = obj.GetTag(c4d.Tposemorph)
        for idxMorph in range(1, tagPoseMorph.GetMorphCount()):
            descIdMorph = tagPoseMorph.GetMorphID(idxMorph)
            strength = tagPoseMorph.GetParameter(descIdMorph, c4d.DESCFLAGS_GET_NONE)
            self._tLiveBackupPoseMorphs[-1][idxMorph] = (tagPoseMorph, descIdMorph, strength)

    def StoreCurrentPositions(self, tags):
        self._tLiveBackup = []
        self._tLiveBackupPoseMorphs = []
        for tag in tags:
            obj = tag.GetObject()
            if tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR:
                self._tLiveBackup.append({})
                self.AddBackupMg(tag)
            elif tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR_FACE:
                self._tLiveBackupPoseMorphs.append({})
                self.AddBackupPoseMorph(tag)
            else:
                self._tLiveBackup.append({})
                self._tLiveBackup[-1][obj.GetName()] = (obj, obj.GetMg())

    def RestoreCurrentPositions(self):
        for objsPerTag in self._tLiveBackup:
            for (obj, mg) in objsPerTag.values():
                if not obj.IsAlive():
                    continue
                obj.SetMg(mg)
        for morphsPerTag in self._tLiveBackupPoseMorphs:
            for (tagPoseMorph, descIdMorph, strength) in morphsPerTag.values():
                if tagPoseMorph.IsAlive():
                    tagPoseMorph.SetParameter(descIdMorph, strength, c4d.DESCFLAGS_SET_NONE)

    def DetectDataChange(self, data, fps):
        if self._dataExample is None:
            StoreAvailableEntitiesInConnectedDataSet(data, fps)
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_LIVE_DATA_CHANGE)
            self._dataExample = data
            return
        equal = True
        actorsExample = self._dataExample['actors']
        actors = data['actors']
        if len(actors) == len(actorsExample):
            for actor, actorExample in zip(actors, actorsExample):
                metaActorsExample = actorExample['meta']
                metaActor = actor['meta']
                if actor['name'] != actorExample['name']:
                    equal = False
                    break
                if metaActor['hasBody'] != metaActorsExample['hasBody']:
                    equal = False
                    break
                if metaActor['hasGloves'] != metaActorsExample['hasGloves']:
                    equal = False
                    break
                if metaActor['hasLeftGlove'] != metaActorsExample['hasLeftGlove']:
                    equal = False
                    break
                if metaActor['hasRightGlove'] != metaActorsExample['hasRightGlove']:
                    equal = False
                    break
                if metaActor['hasFace'] != metaActorsExample['hasFace']:
                    equal = False
                    break
                if actor['color'] != actorExample['color']:
                    equal = False
                    break
        else:
            equal = False
        propsExample = self._dataExample['props']
        props = data['props']
        if len(props) == len(propsExample):
            for prop, propExample in zip(props, propsExample):
                if prop['name'] != propExample['name']:
                    equal = False
                    break
                if prop['color'] != propExample['color']:
                    equal = False
                    break
        else:
            equal = False
        if equal:
            return
        StoreAvailableEntitiesInConnectedDataSet(data, fps)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_LIVE_DATA_CHANGE)
        self._dataExample = data

    def GetConnectionStatus(self):
        return self._statusConnection

    def ClearTagConsumers(self):
        self._lockTagQueues.acquire()
        self._tags.clear()
        self._lockTagQueues.release()

    def FlushTagConsumers(self):
        queuesToFlush = []
        self._lockTagQueues.acquire()
        queuesToFlush = self._tags.copy()
        self._lockTagQueues.release()
        for tagData, tag in queuesToFlush:
            if not tag.IsAlive():
                continue
            tagData._queueReceive.Flush(tag)

    def AddTagConsumer(self, tagData, tag):
        self._lockTagQueues.acquire()
        self._tags.append((tagData, tag))
        self._lockTagQueues.release()

    def RemoveTagConsumer(self, tagData, tag):
        self._lockTagQueues.acquire()
        if (tagData, tag) not in self._tags:
            print('ERROR: Tag queue not registered.')
            self._lockTagQueues.release()
            return
        idx = self._tags.index((tagData, tag))
        self._tags.pop(idx)
        self._lockTagQueues.release()

    def RemoveAllTagConsumers(self):
        self._lockTagQueues.acquire()
        del self._tags[:]
        self._lockTagQueues.release()

    def GetTagConsumers(self):
        tagConsumers = []
        self._lockTagQueues.acquire()
        for (tagData, tag) in self._tags:
            tagConsumers.append(tag)
        self._lockTagQueues.release()
        return tagConsumers

    def SyncFrameCounters(self):
        self._lockFrameCounter.acquire()
        self._frameNumberDispatch = self._frameNumberReceive
        self._lockFrameCounter.release()
        self._inSync = True

    def Connect(self):
        bcConnection = GetConnectedDataSet()
        if bcConnection is None:
            return
        self.FlushTagConsumers()
        self._idLiveConnection = GetConnectedDataSetId()

        self._lockConnect.acquire()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(0.2)
        self._sock.bind(('', int(bcConnection[ID_BC_DATASET_LIVE_PORT])))
        self._lockConnect.release()

        self._statusConnection = 2
        self._statusConnectionLast = 2
        self._receive = False

        self._lockFrameCounter.acquire()
        self._frameNumberReceive = 0
        self._frameNumberDispatch = 0
        self._lockFrameCounter.release()

        self._lockDataQueues.acquire()
        self._dataQueues[self._idLiveConnection] = []
        self._liveQueue = self._dataQueues[self._idLiveConnection]
        self._lockDataQueues.release()

        result = self.ReceiveFrame(force=True)
        if not result:
            self._statusConnection = 0
            print('ERROR: Unexpected error during connection attempt')
            return
        data = None

        self._lockDataQueues.acquire()
        if len(self._liveQueue) > 0:
            data = self._liveQueue.pop(-1)
        self._liveQueue.clear()
        self._lockDataQueues.release()

        self._lockFrameCounter.acquire()
        self._frameNumberReceive = 0
        self._frameNumberDispatch = 0
        self._lockFrameCounter.release()

        if data is None:
            self._dataExample = None
            self._statusConnection = 2
            self._statusConnectionLast = 2
        else:
            self._dataExample = data['scene']
            StoreAvailableEntitiesInConnectedDataSet(self._dataExample, float(data['fps']))
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_STATUS_CHANGE)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_LIVE_DATA_CHANGE)
        self._sock.settimeout(1.0)
        self._funcMain = self.MainConnected
        self.Start()

    def ConnectNoConnection(self):
        self.FlushTagConsumers()
        self._statusConnection = 2
        self._statusConnectionLast = 2
        self._receive = False
        self._lockFrameCounter.acquire()
        self._frameNumberReceive = 0
        self._frameNumberDispatch = 0
        self._lockFrameCounter.release()
        self._dataExample = None
        self._funcMain = self.MainNotConnected
        self.Start()

    def DisconnectNoConnection(self):
        self._receive = False
        self.FlushTagConsumers()
        self._statusConnection = 0
        self._statusConnectionLast = 0
        self.Wait(True)

    def Disconnect(self):
        self._receive = False
        bcConnected = GetConnectedDataSet()
        idConnected = None
        if bcConnected is not None:
            idConnected = bcConnected.GetId()
        self._lockDataQueues.acquire()
        if idConnected in self._dataQueues:
            self._dataQueues.pop(idConnected)
        self._liveQueue = None
        self._lockDataQueues.release()
        self._idLiveConnection = -1

        self.FlushTagConsumers()
        self._statusConnection = 0
        self._statusConnectionLast = 0

        self._lockConnect.acquire()
        if self._sock is not None:
            self._sock.close()
            self._sock = None
        self._lockConnect.release()

        self._dataExample = None
        self.Wait(True)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_STATUS_CHANGE)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_LIVE_DATA_CHANGE)

    def GarbageCollectQueues(self):
        tags = GetTagList()
        idConnected = -1
        bcConnected = GetConnectedDataSet()
        if bcConnected is not None:
            idConnected = bcConnected.GetId()
        redundantQueues = []
        self._maxFramesInDataSets = 0

        self._lockDataQueues.acquire()
        for idInQueue in self._dataQueues:
            if idInQueue == idConnected:
                continue
            found = False
            for tag in tags:
                if idInQueue == tag[ID_TAG_DATA_SET]:
                    self._maxFramesInDataSets = max(self._maxFramesInDataSets, len(self._dataQueues[idInQueue]))
                    found = True
                    break
            if not found:
                redundantQueues.append(idInQueue)
        for idRedundant in redundantQueues:
            self._dataQueues.pop(idRedundant)
        self._lockDataQueues.release()

    def DiscardDataQueues(self):
        self._lockDataQueues.acquire()
        self._dataQueues.clear()
        self._liveQueue = None
        self._lockDataQueues.release()

    def ConnectDataSet(self, bcDataSet):
        self._lockDataQueues.acquire()
        idDataSet = bcDataSet.GetId()
        if idDataSet in self._dataQueues:
            if self._dataQueues[idDataSet] is None or len(self._dataQueues[idDataSet]) <= 0:
                print('ERROR: Dataset already connected, but no data queue found!')
            self._lockDataQueues.release()
            return
        self._lockDataQueues.release()
        filename = bcDataSet[ID_BC_DATASET_FILENAME]
        if bcDataSet[ID_BC_DATASET_IS_LOCAL] and filename[0] == '.' or os.sep not in filename:
            pathDoc = c4d.documents.GetActiveDocument().GetDocumentPath()
            filename = os.path.join(pathDoc, filename)
        data = ReadDataSet(filename)
        if data is None:
            print('ERROR: Dataset lacks filename.')
            return
        self.GarbageCollectQueues()
        self._lockDataQueues.acquire()
        self._dataQueues[idDataSet] = data
        self._lockDataQueues.release()


    def FlushBuffers(self):
        self._lockDataQueues.acquire()
        if self._liveQueue is not None:
            self._liveQueue.clear()
        self._lockDataQueues.release()

        self.FlushTagConsumers()

        self._lockFrameCounter.acquire()
        self._frameNumberReceive = 0
        self._frameNumberDispatch = 0
        self._lockFrameCounter.release()

    def GetDispatchCount(self):
        self._lockFrameCounter.acquire()
        count = self._frameNumberDispatch
        self._lockFrameCounter.release()
        return count

    def GetLiveQueueCount(self):
        self._lockDataQueues.acquire()
        count = len(self._liveQueue)
        self._lockDataQueues.release()
        return count

    def GetDataSetSize(self, idDataSet):
        self._lockDataQueues.acquire()
        count = len(self._dataQueues[idDataSet])
        self._lockDataQueues.release()
        return count

    def GetCurrentFrameNumber(self):
        self._lockFrameCounter.acquire()
        idx = self._frameNumberDispatch
        if self._liveQueue is not None:
            sizeLiveQueue = len(self._liveQueue)
        else:
            sizeLiveQueue = 0
        self._lockFrameCounter.release()
        if self._maxFramesInDataSets > 0:
            maxFrameDataSets = self._maxFramesInDataSets - 1
        else:
            maxFrameDataSets = 0
        if GetConnectedDataSet() is None:
            frameMax = max(maxFrameDataSets, idx)
        else:
            frameMax = max(maxFrameDataSets, sizeLiveQueue - 1)
        return idx, frameMax

    def StartReception(self):
        self.FlushBuffers()
        self.FlushTagConsumers()
        self._lockFrameCounter.acquire()
        self._frameNumberReceive = 0
        self._frameNumberDispatch = 0
        self._lockFrameCounter.release()
        self._receive = True

    def PauseReception(self):
        self._receive = False

    def StopReception(self):
        self._receive = False
        self._lockFrameCounter.acquire()
        self._frameNumberReceive = 0
        self._frameNumberDispatch = 0
        self._lockFrameCounter.release()
        self.FlushBuffers()
        self.FlushTagConsumers()

    def ReceiveFrame(self, force=False):
        if self._sock is None:
            return False, False # error
        try:
            udpData = self._sock.recv(1024 * 64)
        except socket.timeout:
            ConnectedDataSetStreamLost()
            self._dataExample = None
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_LIVE_DATA_CHANGE)
            return True, False # success, no new data
        except:
            return False, False # error
        if force or self._receive:
            studioData = lz4.frame.decompress(udpData, return_bytearray=True, return_bytes_read=False)
            data = json.loads(studioData)

            self.DetectDataChange(data['scene'], float(data['fps']))

            self._lockDataQueues.acquire()
            self._liveQueue.append(data)
            self._lockDataQueues.release()

            if self._frameNumberReceive == 0:
                self._tsFirst = data['scene']['timestamp']

            self._lockFrameCounter.acquire()
            self._frameNumberReceive += 1
            self._lockFrameCounter.release()

            self._cntBufferPulse = (self._cntBufferPulse + 1) % 15
            if self._cntBufferPulse == 0:
                c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_BUFFER_PULSE)
        else:
            self._cntDetect = (self._cntDetect + 1) % 60
            if self._cntDetect == 0:
                studioData = lz4.frame.decompress(udpData, return_bytearray=True, return_bytes_read=False)
                data = json.loads(studioData)
                self.DetectDataChange(data['scene'], float(data['fps']))
        return True, True  # success, new data

    def GetFrame(self, idDataSet, idxFrame):
        frame = None
        self._lockDataQueues.acquire()
        if idDataSet in self._dataQueues:
            frame = self._dataQueues[idDataSet][idxFrame]['scene']
        self._lockDataQueues.release()
        return frame

    def DispatchFrame(self, idx=-1, event=True):
        frameIndeces = {}
        if idx != -1:
            self._lockFrameCounter.acquire()
            self._frameNumberDispatch = idx
            self._lockFrameCounter.release()

        idConnected = GetConnectedDataSetId()
        self._lockDataQueues.acquire()
        for idDataSet, queue in self._dataQueues.items():
            if len(queue) <= 0:
                continue
            idxQueue = self._frameNumberDispatch % len(queue)
            frameIndeces[idDataSet] = idxQueue
        self._lockDataQueues.release()

        self._lockTagQueues.acquire()
        queuesToAdd = self._tags.copy()
        self._lockTagQueues.release()

        for tagData, tag in queuesToAdd:
            if not tag.IsAlive() or not tag[ID_TAG_VALID_DATA]:
                continue
            idDataSet = tag[ID_TAG_DATA_SET]
            if idDataSet == 0:
                continue
            idxFrame = frameIndeces[idDataSet]
            if tag[ID_TAG_DATA_SET] != idConnected:
                idxFirstFrame = tag[ID_TAG_DATA_SET_FIRST_FRAME]
                idxLastFrame = tag[ID_TAG_DATA_SET_LAST_FRAME]
                idxFrame = idxFirstFrame + self._frameNumberDispatch % (idxLastFrame - idxFirstFrame)
            tagData._queueReceive.AddFrame(tag, idxFrame)
        if event:
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_LIVE_DRAW, p1=int(self._play))


    def Main(self):
        self._funcMain()

    def MainConnected(self):
        while self._statusConnection != 0:
            result, newData = self.ReceiveFrame()
            if not result:
                break
            if not newData:
                self._statusConnection = 2
                if self._statusConnection != self._statusConnectionLast:
                    c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_STATUS_CHANGE)
                    self._statusConnectionLast = self._statusConnection
                continue
            self._statusConnection = 1
            if self._statusConnection != self._statusConnectionLast:
                c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_STATUS_CHANGE)
                self._statusConnectionLast = self._statusConnection
            if not self._play:
                continue
            playbackRate = GetPref(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED)
            if playbackRate is None:
                playbackRate = 2
            self._cntPlaybackRate = (self._cntPlaybackRate + 1) % playbackRate
            if self._cntPlaybackRate == 0:
                self.DispatchFrame()

            self._lockFrameCounter.acquire()
            if self._play:
                self._frameNumberDispatch += 1
            self._lockFrameCounter.release()

    def MainNotConnected(self):
        while self._statusConnection != 0:
            playbackRate = GetPref(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED)
            time.sleep(0.01667 * playbackRate)
            if self._play:
                self._lockFrameCounter.acquire()
                self._frameNumberDispatch += playbackRate
                self._lockFrameCounter.release()
            self.DispatchFrame()

    _funcMain = MainConnected

    def SaveLiveData(self, filename, idxFrameFirst=0, idxFrameLast=-1):
        self._lockDataQueues.acquire()
        if idxFrameLast == -1:
            idxFrameLast = len(self._liveQueue)
        dataJSON = json.dumps(self._liveQueue[idxFrameFirst:idxFrameLast])
        self._lockDataQueues.release()
        dataLZ4 = lz4.frame.compress(dataJSON.encode('utf-8'))
        with open(filename, mode='wb') as f:
            f.write(dataLZ4)
            f.close()
        ReadDataSet(filename)

g_thdListener = ThreadListener()
