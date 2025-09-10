'''The listener thread receives the motion data stream from Rokoko Studio and
buffers it in a queue (only if actively receiving, that is).
Tags with assigned Clip data (in code called data sets) register the needed
Clip reference within the listener thread, which in turn creates an additional
motion daata queue per Clip.

The entire Player logic (play, pause, frame index, ...) is also incorporated
in here. If the Player gets started, all involved tags get registered inside
the listener thread in order to have frames dispatched into their "tag queues"
later on. Basically establishing the connection between a data queue (live or
clip) and a tag's tag queue.

During live playback the listener thread dispatches motion data frames to all
involved tags.  If no connection to Rokoko Studio exists, a slightly simpler
thread is used, which provides the "clock" for playback (instead of the
Studio stream being used for this purpose) and dispatches the frames from the
Clip queues to all involved tags.
'''

import json
import os
import socket
import time
from threading import Condition

__USE_LZ4__ = True
try:
    import lz4.frame as lz4f
except ImportError:
    __USE_LZ4__ = False

import c4d

import rokoko_ids as rid
from rokoko_rig_tables import STUDIO_NAMES_TO_GUESS
from rokoko_utils import (
    ConnectedDataSetStreamLost,
    GetConnectedDataSet,
    GetConnectedDataSetId,
    GetPref,
    GetTagList,
    OpenLinkInBrowser,
    ReadDataSet,
    StoreAvailableEntitiesInConnectedDataSet,
)


# There is one single global listener thread in Rokoko Studio Live.
g_thdListener = None


def GetListenerThread():
    '''Other modules may gain access to the global listener thread.'''

    return g_thdListener


def DestroyListenerThread():
    '''To be called during shutdown'''

    global g_thdListener

    if g_thdListener is not None:
        g_thdListener.Disconnect()
        g_thdListener.RemoveAllTagConsumers()
        g_thdListener.DiscardDataQueues()
        g_thdListener = None


class ThreadListener(c4d.threading.C4DThread):
    # socket used for connection to Rokoko Studio
    _sock = None

    # Connection states
    # 0: Not connected, 1: Connected Ok, 2: Connected No Data
    _statusConnection = 0
    _statusConnectionLast = 0
    # _lockConnect serializes socket access during connection
    _lockConnect = Condition()
    # _lockConnect was introduced when researching a connection threading
    # issue, which was then found somewhere else...
    # Unfortunetly I lacked the time to get rid of this lock again.
    # It shouldn't be needed. While removal would be quick,
    # it also needs to be tested extensively.

    # Player states
    _receive = False
    _play = False
    _inSync = True
    _frameNumberReceive = 0
    _frameNumberDispatch = 0
    # _lockFrameCounter only used to set both frame counters atomically
    _lockFrameCounter = Condition()

    # Data queues
    # One queue per clip in use,
    # regardless of how many tags are consuming data from this clip
    _dataQueues = {}
    # only a reference to the data queue with the ID of the live connection
    _liveQueue = None
    _maxFramesInDataSets = 0
    # _lockDataQueues serializes access to _dataQueues
    _lockDataQueues = Condition()

    # Tag consumers
    # List of tags involved in playback (tags that "want" to receive data)
    _tags = []
    # _lockTagQueues serializes access to the list of tag consumers
    _lockTagQueues = Condition()
    # _lockTagQueues really only protects the integrity of the list,
    # _not_ its content (referenced tags).
    # We have to live with the fact, tags may "die" or get lost anytime.
    # There is nothing we can do about this with any locking mechanism
    # whatsoever, but need to take it into account anyway.

    # Data detection
    _dataExample = None

    # Backup/restore state
    _timeStored = None
    _tLiveBackup = []
    _tLiveBackupPoseMorphs = []

    # Reduction counters
    _cntDetect = 0
    _cntBufferPulse = 0
    _cntPlaybackRate = 0

    def StoreTime(self, t):
        '''Stores a time value in a member variable.
        This is used by the Player to store current document time,
        when it's started, so it can be restored after exiting the Player.
        '''

        self._timeStored = t

    def GetStoredTime(self):
        '''Retrieves a time value previously stored by StoreTime().'''

        return self._timeStored

    def AddBackupMg(self, tag):
        '''For a given rig (tag with type Actor) store all global matrices.'''

        self._tLiveBackup.append({})  # add a new dictionary for this tag

        # Instead of iterating the object tree, we simply loop over the
        # detected body parts of the tag.
        for nameInStudio, (idx, _, _, _, _, _, _, _) in STUDIO_NAMES_TO_GUESS.items():  # noqa: E501
            obj = tag[rid.ID_TAG_BASE_RIG_LINKS + idx]
            if obj is None:
                continue
            nameObj = obj.GetName()
            self._tLiveBackup[-1][nameObj] = (obj, obj.GetMg())

    def AddBackupPoseMorph(self, tag):
        '''For a given face (tag with type Face) store all morph strength of
        the "connected" PoseMorph.
        '''

        # add a new dictionary for this tag
        self._tLiveBackupPoseMorphs.append({})

        # Iterate all morphs in PoseMorph
        obj = tag.GetObject()
        tagPoseMorph = obj.GetTag(c4d.Tposemorph)
        for idxMorph in range(1, tagPoseMorph.GetMorphCount()):
            descIdMorph = tagPoseMorph.GetMorphID(idxMorph)
            strength = tagPoseMorph.GetParameter(
                descIdMorph, c4d.DESCFLAGS_GET_NONE)
            self._tLiveBackupPoseMorphs[-1][idxMorph] = (tagPoseMorph,
                                                         descIdMorph,
                                                         strength)

    def StoreCurrentPositions(self, tags):
        '''Provided with a list of tags, StoreCurrentPositions() will store all
        parameters of all objects that may be influenced by the tags.

        This is done before the Player starts in order to restore the
        previous state later on.
        '''

        # Two local lists,
        # one for objects (actors + props), one for morphs (faces)
        # Each list contains a dictionary per tag storing information about
        # a given object or PoseMorph.
        self._tLiveBackup = []
        self._tLiveBackupPoseMorphs = []

        for tag in tags:
            obj = tag.GetObject()
            if tag[rid.ID_TAG_RIG_TYPE] & rid.RIG_TYPE_ACTOR:
                # For actors, traverse the entire rig and store its
                # global matrices
                self.AddBackupMg(tag)
            elif tag[rid.ID_TAG_RIG_TYPE] & rid.RIG_TYPE_ACTOR_FACE:
                # For faces, iterate all morphs in the PoseMorph tag and store
                # their strength
                self.AddBackupPoseMorph(tag)
            else:
                # For props only one global matrix needs to be stored
                self._tLiveBackup.append({})
                self._tLiveBackup[-1][obj.GetName()] = (obj, obj.GetMg())

    def RestoreCurrentPositions(self):
        '''Restore state stored during StoreCurrentPositions()'''

        # Restore all involved objects
        for objsPerTag in self._tLiveBackup:
            for (obj, mg) in objsPerTag.values():
                if not obj.IsAlive():
                    continue
                obj.SetMg(mg)

        # Restore all involved PoseMorphs
        for morphsPerTag in self._tLiveBackupPoseMorphs:
            for (tagPoseMorph, descIdMorph, strength) in morphsPerTag.values():
                if not tagPoseMorph.IsAlive():
                    continue
                tagPoseMorph.SetParameter(
                    descIdMorph, strength, c4d.DESCFLAGS_SET_NONE)

    def DetectDataChange(self, data, fps):
        '''Called to detect changes in the live data stream.

        Function does so by comparing certain aspects of the received frame
        with a previously stored example frame.
        Upon a detected change three things happen:
        - an event announcing the change is emitted
        - the changed stream content information is stored in the connected
          data set
        - current frame gets stored as example for consecutive detections
        '''

        # If no example exists, it's a change for sure
        if self._dataExample is None:
            StoreAvailableEntitiesInConnectedDataSet(data, fps)
            c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_CONNECTION,
                                rid.CM_SUBID_CONNECTION_LIVE_DATA_CHANGE)
            self._dataExample = data
            return

        equal = True  # assume "no change"

        # Compare actor related data
        actorsExample = self._dataExample["actors"]
        actors = data["actors"]
        if len(actors) == len(actorsExample):
            # If actor lists have same length, we need to look more into detail
            # Check all actors, break on first inequality
            for actor, actorExample in zip(actors, actorsExample):
                metaActorsExample = actorExample["meta"]
                metaActor = actor["meta"]
                if actor["name"] != actorExample["name"]:
                    equal = False
                    break
                if metaActor["hasBody"] != metaActorsExample["hasBody"]:
                    equal = False
                    break
                if metaActor["hasGloves"] != metaActorsExample["hasGloves"]:
                    equal = False
                    break
                if metaActor["hasLeftGlove"] != metaActorsExample["hasLeftGlove"]:  # noqa: E501
                    equal = False
                    break
                if metaActor["hasRightGlove"] != metaActorsExample["hasRightGlove"]:  # noqa: E501
                    equal = False
                    break
                if metaActor["hasFace"] != metaActorsExample["hasFace"]:
                    equal = False
                    break
                colorActor = actor.get("color", [128, 128, 128])
                colorActorExample = actorExample.get("color", [128, 128, 128])
                if colorActor != colorActorExample:
                    equal = False
                    break
        else:
            equal = False  # different number of actors

        # Compare prop related data
        propsExample = self._dataExample["props"]
        props = data["props"]
        if len(props) == len(propsExample):
            # if prop lists have same length, we need to look more into detail
            for prop, propExample in zip(props, propsExample):
                if prop["name"] != propExample["name"]:
                    equal = False
                    break
                if prop["color"] != propExample["color"]:
                    equal = False
                    break
        else:
            equal = False  # different number of props

        if equal:
            return  # frames are equal, no data change detected

        # Store information and announce data change
        StoreAvailableEntitiesInConnectedDataSet(data, fps)
        c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_CONNECTION,
                            rid.CM_SUBID_CONNECTION_LIVE_DATA_CHANGE)
        self._dataExample = data

    def GetConnectionStatus(self):
        '''Return connection status

        0: Not connected, 1: Connected Ok, 2: Connected No Data
        '''
        return self._statusConnection

    def AddTagConsumer(self, tagData, tag):
        '''Tags register themselves as "consumers", tag references are stored
        in list _tags.

        This list is used to dispatch frames to during playback.
        '''

        self._lockTagQueues.acquire()
        self._tags.append((tagData, tag))
        self._lockTagQueues.release()

    def RemoveTagConsumer(self, tagData, tag):
        '''Unregister a "consumer", the tag will no longer be provided with
        frames.
        '''

        self._lockTagQueues.acquire()
        if (tagData, tag) not in self._tags:
            print("ERROR: Tag queue not registered.")
            self._lockTagQueues.release()
            return
        self._tags.remove((tagData, tag))
        self._lockTagQueues.release()

    def RemoveAllTagConsumers(self):
        '''Unregister all "consumers", nobody wants to listen anymore.'''

        self._lockTagQueues.acquire()
        self._tags.clear()
        self._lockTagQueues.release()

    def GetTagConsumers(self):
        '''Return a copy of the current list of consumer tags (only BaseTags).
        '''

        tagConsumers = []

        self._lockTagQueues.acquire()
        for (tagData, tag) in self._tags:
            tagConsumers.append(tag)
        self._lockTagQueues.release()

        return tagConsumers

    def FlushTagConsumers(self):
        '''Flushes the inbound tag queues of each registered consumer tag.

        Since there are no real inbound queues in the tags anymore,
        this will only remove the last dispatched frame index from the tag.
        '''

        queuesToFlush = []

        self._lockTagQueues.acquire()
        queuesToFlush = self._tags.copy()
        self._lockTagQueues.release()

        for tagData, tag in queuesToFlush:
            if not tag.IsAlive():
                continue
            tagData._queueReceive.Flush(tag)

    def SyncFrameCounters(self):
        '''In order to resume live playback after user had paused the Player,
        frame counters need to be synched.
        '''

        self._lockFrameCounter.acquire()
        self._frameNumberDispatch = self._frameNumberReceive
        self._lockFrameCounter.release()
        self._inSync = True

    def ResetFrameCounters(self):
        '''Resets the frame counters...'''

        self._lockFrameCounter.acquire()
        self._frameNumberReceive = 0
        self._frameNumberDispatch = 0
        self._lockFrameCounter.release()

    def Connect(self):
        '''Connect to the currently selected live connection'''

        # Get connected data set and its ID
        bcConnection = GetConnectedDataSet()
        if bcConnection is None:
            return
        idConnected = GetConnectedDataSetId()

        self.FlushTagConsumers()  # there shouldn't be any, but nevertheless...

        # Create and bind the socket
        errorConnect = False

        self._lockConnect.acquire()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # we'll start with a short timeout for quick connection result
        self._sock.settimeout(0.2)
        try:
            self._sock.bind(
                ("", int(bcConnection[rid.ID_BC_DATASET_LIVE_PORT])))
        except OSError:
            errorConnect = True
        self._lockConnect.release()

        if errorConnect:
            self._statusConnection = 0  # Not connected
            self._statusConnectionLast = 0
            c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_CONNECTION,
                                rid.CM_SUBID_CONNECTION_CONNECT_ERROR)
            print("ERROR: Failed to bind socket (already in use?)")
            return

        # Initialize connection and player status
        self._statusConnection = 2  # Connected No Data
        self._statusConnectionLast = 2
        self._receive = False  # frames will not be buffered, player is off

        # Initialize frame counters
        self.ResetFrameCounters()

        # Create a data queue for this live connection
        self._lockDataQueues.acquire()
        self._dataQueues[idConnected] = []
        self._liveQueue = self._dataQueues[idConnected]
        self._lockDataQueues.release()

        # Try to receive a frame
        result = self.ReceiveFrame(force=True)
        if not result:
            self._statusConnection = 0  # Not connected
            self._statusConnectionLast = 0
            print("ERROR: Unexpected error during connection attempt")
            return

        # Check received frame (if any)
        data = None
        self._lockDataQueues.acquire()
        if len(self._liveQueue) > 0:
            data = self._liveQueue.pop(-1)
        self._liveQueue.clear()  # throw test frame away
        self._lockDataQueues.release()

        # Wipe traces of frame reception test
        self.ResetFrameCounters()

        # Store as example frame for data change detection (if any)
        self._dataExample = None
        if data is not None:
            self._dataExample = data["scene"]
            StoreAvailableEntitiesInConnectedDataSet(
                self._dataExample, float(data["fps"]))

        # Announce connection status and live data change
        c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_CONNECTION,
                            rid.CM_SUBID_CONNECTION_STATUS_CHANGE)
        c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_CONNECTION,
                            rid.CM_SUBID_CONNECTION_LIVE_DATA_CHANGE)

        # set the timeout used during this connection
        self._sock.settimeout(1.0)

        # Use the correct main function and start the listener thread
        self._funcMain = self.MainConnected
        self.Start()

    def ConnectNoConnection(self):
        '''There is no live connection, so we need to "connect" the offline
        player thread
        '''

        # there shouldn't be any, but nevertheless...
        self.FlushTagConsumers()

        # Initialize connection and player status
        self._statusConnection = 2  # Connected No Data
        self._statusConnectionLast = 2
        self._receive = False

        # Initialize frame counters
        self.ResetFrameCounters()

        # there is no data change detection without live connection
        self._dataExample = None

        # Use the correct main function and start the listener thread
        # (in this case rather "player only thread")
        self._funcMain = self.MainNotConnected
        self.Start()

    def DisconnectNoConnection(self):
        '''"Disconnect" the offline player thread'''

        # Reset connection and player status
        self._receive = False  # stop buffering frames and player
        self._statusConnection = 0  # Not connected
        self._statusConnectionLast = 0

        # Flush all frames already dispatched to tags
        self.FlushTagConsumers()

        # Wait for the thread to exit (but allow C4D events to wake us)
        self.Wait(True)

    def Disconnect(self):
        '''Disconnect the live connection'''

        # Reset connection and player status
        self._receive = False
        self._statusConnection = 0
        self._statusConnectionLast = 0

        # Destroy the live data queue
        idConnected = GetConnectedDataSetId()
        self._lockDataQueues.acquire()
        if idConnected in self._dataQueues:
            self._dataQueues.pop(idConnected)
        self._liveQueue = None
        self._lockDataQueues.release()

        # Flush all frames already dispatched to tags
        self.FlushTagConsumers()

        # Close the socket
        self._lockConnect.acquire()
        if self._sock is not None:
            self._sock.close()
            self._sock = None
        self._lockConnect.release()

        self._dataExample = None

        # Wait for listener thread to exit (but allow C4D events to wake us)
        self.Wait(True)

        # Announce connection status and live data change
        c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_CONNECTION,
                            rid.CM_SUBID_CONNECTION_STATUS_CHANGE)
        c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_CONNECTION,
                            rid.CM_SUBID_CONNECTION_LIVE_DATA_CHANGE)

    def GarbageCollectQueues(self):
        '''As multiple tags can register as consumers of the same motion clip,
        data queues can not be thrown away, when a tag unregisters. At least
        unless there was some usage counter or something.

        Instead I decided to garbage collect "stale" data queues
        (where no tag is interested in anymore), when a tag registers
        a data set (clip). This has the advantage of data staying in memory.
        If the user maybe temporarily switches a tag to "no data set",
        returning to the previous data set is instantanious, the data does not
        need to be reloaded.
        '''

        idConnected = GetConnectedDataSetId()
        tags = GetTagList()
        self._maxFramesInDataSets = 0

        self._lockDataQueues.acquire()

        # Check all data queues
        # inside of loop, ids of garbage collected queues are stored in here
        redundantQueues = []
        for idInQueue in self._dataQueues:
            if idInQueue == idConnected:  # never garbage collect live queue
                continue

            # Check if queue is used by any tag
            found = False
            for tag in tags:
                if idInQueue != tag[rid.ID_TAG_DATA_SET]:
                    continue

                # Queue is in use, queue contributes to maximum queue length
                self._maxFramesInDataSets = max(
                    self._maxFramesInDataSets,
                    len(self._dataQueues[idInQueue]))
                found = True
                break

            # If queue is not in use, store its id to have it destroyed
            # afterwards
            if not found:
                redundantQueues.append(idInQueue)

        # Destroy all queues found in previous loop
        for idRedundant in redundantQueues:
            self._dataQueues.pop(idRedundant)

        self._lockDataQueues.release()

    def DiscardDataQueues(self):
        '''Destroy all data queues (used during shut down)'''

        self._lockDataQueues.acquire()
        self._dataQueues.clear()
        self._liveQueue = None
        self._lockDataQueues.release()

    def ConnectDataSet(self, bcDataSet):
        '''Register a data set (clip).

        Done by tags to "connect" to motion data from a file source.
        The file is read and stored in a data queue.
        If the same file has already been registered before by another tag,
        simply nothing happes. There is always only one data queue per file,
        which is then used for an arbitrary number of consumer tags.
        '''

        # Check if there is already an existing data queue for this data set.
        # If so, we are done,
        self._lockDataQueues.acquire()
        idDataSet = bcDataSet.GetId()
        if idDataSet in self._dataQueues:
            if self._dataQueues[idDataSet] is None or \
               len(self._dataQueues[idDataSet]) <= 0:
                print("ERROR: Dataset already connected, "
                      "but no data queue found!")
            self._lockDataQueues.release()
            return
        self._lockDataQueues.release()

        # Get the filename and take care of relative filepath in
        # local data sets.
        # Note: Not every local data set, has a relative filepath,
        #       but global ones never have a relative path.
        filename = bcDataSet[rid.ID_BC_DATASET_FILENAME]
        isDataSetLocal = bcDataSet[rid.ID_BC_DATASET_IS_LOCAL]
        if isDataSetLocal and filename[0] == "." or os.sep not in filename:
            pathDoc = c4d.documents.GetActiveDocument().GetDocumentPath()
            if filename[0] == ".":
                filename = filename[2:]
            filename = filename.replace('\\', os.sep)
            filename = os.path.join(pathDoc, filename)

        # Read the motion data from file
        data = ReadDataSet(filename)
        if data is None:
            print(f"ERROR: Clip file not found {filename}.")
            return

        self.GarbageCollectQueues()

        # Store the motion data in a data queue
        self._lockDataQueues.acquire()
        self._dataQueues[idDataSet] = data
        self._lockDataQueues.release()

    def FlushBuffers(self):
        '''Flush all buffers involved in live playback
        (live data queue, plus all inbound queues in tags).
        '''

        # Only flush the live buffer,
        # clip data queues keep there data for obvious reasons
        self._lockDataQueues.acquire()
        if self._liveQueue is not None:
            self._liveQueue.clear()
        self._lockDataQueues.release()
        self.FlushTagConsumers()
        self.ResetFrameCounters()

    def GetDispatchCount(self):
        '''Returns the current dispatch frame counter.

        The counter gets incremented _after_ the frame has been dispatched.
        So it's actually the index of the next frame to be dispatched.
        '''

        self._lockFrameCounter.acquire()
        count = self._frameNumberDispatch
        self._lockFrameCounter.release()
        return count

    def GetLiveQueueCount(self):
        '''Returns the number of frames in the live data queue.'''

        self._lockDataQueues.acquire()
        count = len(self._liveQueue)
        self._lockDataQueues.release()
        return count

    def GetDataSetSize(self, idDataSet):
        '''Returns the number of frames in a registered clip.'''

        self._lockDataQueues.acquire()
        count = len(self._dataQueues[idDataSet])
        self._lockDataQueues.release()
        return count

    def GetCurrentFrameNumber(self):
        '''Return dispatch frame counter and
        index of last frame in scrub bar (see below).
        '''

        # Read dispatch frame counter
        self._lockFrameCounter.acquire()
        idx = self._frameNumberDispatch
        self._lockFrameCounter.release()

        # Get number of frames in live queue
        sizeLiveQueue = 0
        if self._liveQueue is not None:
            sizeLiveQueue = len(self._liveQueue)

        # In the end it's a frame index, not a number of frames
        if self._maxFramesInDataSets > 0:
            maxIdxFrameDataSets = self._maxFramesInDataSets - 1
        else:
            maxIdxFrameDataSets = 0

        # The player interface has a "scrub bar" to review the motion data.
        # The dialog's UI needs information about the length of this scrub bar
        # (the number of frames to be able to scrub through).
        # If data sets (clips) are involved, the scrub bar should at least
        # have the length of the longest data set.
        if GetConnectedDataSet() is None:
            frameMax = max(maxIdxFrameDataSets, idx)
        else:
            frameMax = max(maxIdxFrameDataSets, sizeLiveQueue - 1)
        return idx, frameMax

    def StartReception(self):
        '''Start the actual reception of motion data frames (buffering)'''

        # Always start from scratch
        self.FlushBuffers()
        self.FlushTagConsumers()
        self.ResetFrameCounters()
        self._receive = True

    def PauseReception(self):
        '''Stop buffering new data, but do not throw away the motion data
        received so far.
        Situation is "Save Recording".
        '''

        self._receive = False

    def StopReception(self):
        '''Stop reception (buffering) of live data and throw away any data
        received.
        '''

        self._receive = False
        self.ResetFrameCounters()
        self.FlushBuffers()
        self.FlushTagConsumers()

    def WrongStreamWarning(self, message):
        '''Open a warning requester, which allows to access the connection
        instructions.
        '''

        message = rid.PLUGIN_NAME_COMMAND_MANAGER + "\n\n" + message
        message += f"\nSee here: {rid.LINK_CONNECTION_INSTRUCTION}\n\n"
        message += "Ok: Open instructions in web browser.\n"
        result = c4d.gui.MessageDialog(
            message, c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_OKCANCEL)
        if result == c4d.GEMB_R_OK:
            OpenLinkInBrowser(rid.LINK_CONNECTION_INSTRUCTIONS)

    def DecodeReceivedFrame(self, udpData):
        '''Decode a received UDP frame'''

        global g_streamWarnOnce

        # Decompress the frame
        if __USE_LZ4__:
            try:
                studioData = lz4f.decompress(
                    udpData, return_bytearray=True, return_bytes_read=False)
            except BaseException:
                message = "The plugin does support the compressed stream.\n"
                message += ("Please configure Rokoko Studio to use the "
                            "standard Cinema 4D connection.\n")
                self.WrongStreamWarning(message)

                # Ask listener thread to disconnect
                c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_CONNECTION,
                                    rid.CM_SUBID_CONNECTION_DISCONNECT)
                return None
        else:
            studioData = udpData

        # Decode JSON data
        try:
            data = json.loads(studioData)
        except BaseException:
            message = ("It looks like, we are receiving a compressed stream "
                       "from Rokoko Studio,\n")
            message += "which is currently not supported on your system.\n"
            message += ("Please configure Rokoko Studio to use a custom "
                        "connection.\n")
            self.WrongStreamWarning(message)

            # Ask listener thread to disconnect
            c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_CONNECTION,
                                rid.CM_SUBID_CONNECTION_DISCONNECT)
            return None

        return data

    _flagTimeOut = False  # True, if timeout has occurred.

    def ReceiveFrame(self, force=False):
        '''Wait for and receive a motion data frame from the live connection.
        '''

        if self._sock is None:
            return False, False  # error

        # Wait for a frame, bail out on errors
        try:
            udpData = self._sock.recv(1024 * 64)
            self._flagTimeOut = False
        except socket.timeout:
            # In case of timeout announce change of live data, once
            if not self._flagTimeOut:
                ConnectedDataSetStreamLost()
                self._dataExample = None
                c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_CONNECTION,
                                    rid.CM_SUBID_CONNECTION_LIVE_DATA_CHANGE)
                self._flagTimeOut = True
            return True, False  # success, no new data
        except BaseException:
            return False, False  # error

        # If reception is enabled (player started)...
        if force or self._receive:
            data = self.DecodeReceivedFrame(udpData)
            if data is None:
                return False, False  # success, no new data

            # Check if data has changed
            self.DetectDataChange(data["scene"], float(data["fps"]))

            # Buffer the data (append to end of live data queue)
            self._lockDataQueues.acquire()
            self._liveQueue.append(data)
            self._lockDataQueues.release()

            # Increment receive counter
            self._lockFrameCounter.acquire()
            self._frameNumberReceive += 1
            self._lockFrameCounter.release()

            # Every once in a while emit a buffer pulse
            # Just so the user sees some movement in the "buffering" sliders,
            # even if user paused playback.
            self._cntBufferPulse = (self._cntBufferPulse + 1) % 15
            if self._cntBufferPulse == 0:
                c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_MANAGER,
                                    rid.CM_SUBID_MANAGER_BUFFER_PULSE)
        else:
            # In case reception is disabled (player not started),
            # we decode every 60th frame to check for data changes
            self._cntDetect = (self._cntDetect + 1) % 60
            if self._cntDetect == 0:
                data = self.DecodeReceivedFrame(udpData)
                if data is None:
                    return False, False  # success, no new data
                self.DetectDataChange(data["scene"], float(data["fps"]))
        return True, True  # success, new data

    def GetFrame(self, idDataSet, idxFrame):
        '''Get a frame from a data queue by index.

        Tags read the motion data frame during Execute() with
        the index they received during dispatch.
        '''

        frame = None
        self._lockDataQueues.acquire()
        if idDataSet in self._dataQueues:
            frame = self._dataQueues[idDataSet][idxFrame]["scene"]
        self._lockDataQueues.release()
        return frame

    def DispatchFrame(self, idx=-1, event=True):
        '''Dispatch a frame to the consumer tags.'''

        # If idx is not -1, dispatch counter is overwritten and from then on
        # stay asynchronous to receive counter. Until manually resynched by
        # user.
        if idx != -1:
            self._lockFrameCounter.acquire()
            self._frameNumberDispatch = idx
            self._lockFrameCounter.release()

        # Determine frame index to dispatch per data queue.
        # Queues wrap around if playing past their end.
        # Dictionary stores data queue specific frame indeces
        frameIndeces = {}
        self._lockDataQueues.acquire()
        for idDataSet, queue in self._dataQueues.items():
            if len(queue) <= 0:
                continue
            idxQueue = self._frameNumberDispatch % len(queue)
            frameIndeces[idDataSet] = idxQueue
        self._lockDataQueues.release()

        # Get a list of all involved tags (tags to dispatch frames to)
        self._lockTagQueues.acquire()
        queuesToAdd = self._tags.copy()
        self._lockTagQueues.release()

        # Dispatch frames to tags
        idConnected = GetConnectedDataSetId()
        for tagData, tag in queuesToAdd:
            if not tag.IsAlive() or not tag[rid.ID_TAG_VALID_DATA]:
                continue

            idDataSet = tag[rid.ID_TAG_DATA_SET]
            if idDataSet == 0:  # only dispatch from valid data queues
                continue

            # Determine frame index to dispatch
            idxFrame = frameIndeces[idDataSet]
            if tag[rid.ID_TAG_DATA_SET] != idConnected:
                # With clips the user may have set further reduced the size of
                # the clip in the tag
                idxFirstFrame = tag[rid.ID_TAG_DATA_SET_FIRST_FRAME]
                idxLastFrame = tag[rid.ID_TAG_DATA_SET_LAST_FRAME]
                idxFrame = idxFirstFrame + \
                    self._frameNumberDispatch % (idxLastFrame - idxFirstFrame)

            # Dispatch the frame (simply writing the index into the tag)
            tagData._queueReceive.AddFrame(tag, idxFrame)

        # If events are not disabled, request a scene execution and
        # viewport redraw
        # (events off happens for example, if dispatch is called during
        # user dragging the scrub bar)
        if event:
            c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_LIVE_DRAW,
                                p1=int(self._play))

    def Main(self):
        '''Main function of a C4DThread, which will be called upon
        c4DThread.Start().

        Depending on existence of a live connection, a slightly different
        thread function is used.
        '''

        self._funcMain()

    def MainConnected(self):
        '''Thread function used, when there is a live connection.

        In contrast to the "offline player" below, no time base needs to
        generated. Instead the frame reception is used as a "clock".
        '''

        while self._statusConnection != 0:
            # Wait for a frame from Rokoko Studio
            result, newData = self.ReceiveFrame()
            if not result:
                break  # an error occurred

            # If no new data received (timeout), announce the change in
            # connection status
            if not newData:
                self._statusConnection = 2
                # only one event per change
                if self._statusConnection != self._statusConnectionLast:
                    c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_CONNECTION,
                                        rid.CM_SUBID_CONNECTION_STATUS_CHANGE)
                    self._statusConnectionLast = self._statusConnection
                continue

            self._statusConnection = 1  # online and data incoming

            # If  connection status changed, announce this once
            if self._statusConnection != self._statusConnectionLast:
                c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_CONNECTION,
                                    rid.CM_SUBID_CONNECTION_STATUS_CHANGE)
                self._statusConnectionLast = self._statusConnection

            # If player is paused, we are done
            if not self._play:
                continue

            # Depending on playback rate set by the user, dispatch or skip
            # this frame
            playbackRate = GetPref(rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED)
            if playbackRate is None:
                playbackRate = 2
            self._cntPlaybackRate = (self._cntPlaybackRate + 1) % playbackRate
            if self._cntPlaybackRate == 0:
                self.DispatchFrame()

            # Increase dispatch counter after the fact
            self._lockFrameCounter.acquire()
            if self._play:
                self._frameNumberDispatch += 1
            self._lockFrameCounter.release()

    def MainNotConnected(self):
        '''Thread function used, when there is no live connection
        ("offline player").

        The main difference besides the absence of a live data queue is,
        it needs to generate its own time base.
        '''

        while self._statusConnection != 0:
            # Get playback rate set by user (may change during playback)
            playbackRate = GetPref(rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED)

            # Simply sleep according to playback rate
            # (this is probably highly inaccurate)
            # TODO: should actual FPS of data set be taken into account?
            #       If so, which data set, if there are multiple?
            time.sleep(0.01667 * playbackRate)

            # Increase dispatch counter and dispatch frame(s),
            # if player is not paused
            # (user clicked pause or used scrub bar, etc.)
            if self._play:
                self._lockFrameCounter.acquire()
                self._frameNumberDispatch += playbackRate
                self._lockFrameCounter.release()
                self.DispatchFrame()

    # Initialize effective thread function pointer
    # TODO: Having to do so after the declaration of the actual functions
    #       is a strong indicator for the need of an __init__()... ;)
    _funcMain = MainConnected

    def SaveLiveData(self, filename, idxFrameFirst=0, idxFrameLast=-1):
        '''Save current live data queue to a file.'''

        # Encode live data as JSON
        self._lockDataQueues.acquire()
        if idxFrameLast == -1:
            idxFrameLast = len(self._liveQueue)
        dataJSON = json.dumps(self._liveQueue[idxFrameFirst:idxFrameLast])
        self._lockDataQueues.release()

        # Compress JSON data
        if __USE_LZ4__:
            dataLZ4 = lz4f.compress(dataJSON.encode("utf-8"))
        else:
            dataLZ4 = dataJSON

        # Write compressed data to file
        with open(filename, mode="wb") as f:
            f.write(dataLZ4)
            f.close()


# Create a global instance of the listener thread (during startup)
g_thdListener = ThreadListener()
