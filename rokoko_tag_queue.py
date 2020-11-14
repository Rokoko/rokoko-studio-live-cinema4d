# A TagQueue is owned by a Rokoko tag and is the inbound "queue" for motion data dispatched by
# the listener thread.
#
# Originally it was designed as a real queue, thought to further decouple the listener thread
# from tag's execution. But not only did this approach show no noticable advantages, it imposed quite
# a bunch of issues (correct sync between tags,...). In the end the tag queue is nothing more than a
# frame index inside the tag's BaseContainer (only with a synchronized access).
from threading import Condition
from rokoko_ids import *

class TagQueue():

    def __init__(self):
        self._lock = Condition() # serializes all access to the queue


    # Removes any previously dispatched frames
    def Flush(self, tag):
        self._lock.acquire()
        tag.GetDataInstance().RemoveData(ID_TAG_IDX_READ_FRAME)
        self._lock.release()


    # Called by listener thread to dispatch a frame to a tag.
    def AddFrame(self, tag, idx):
        self._lock.acquire()
        tag.GetDataInstance().SetInt32(ID_TAG_IDX_READ_FRAME, idx)
        self._lock.release()


    # Called by tag to get the index of the dispatched frame.
    # As queues are static (in the sense data doesn't change during playback),
    # the tag will then directly access the assigned data queue and
    # retrieve the frame via this index.
    def GetFrameIdx(self, tag):
        bcTag = tag.GetDataInstance()

        self._lock.acquire()
        idxFrame = bcTag.GetData(ID_TAG_IDX_READ_FRAME)
        self._lock.release()
        return idxFrame
