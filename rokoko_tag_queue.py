'''A TagQueue is owned by a Rokoko tag and is the inbound "queue" for motion
data dispatched by the listener thread.

Originally it was designed as a real queue, thought to further decouple the
listener thread from tag's execution. But not only did this approach show no
noticable advantages, it imposed quite a bunch of issues (correct sync between
tags,...). In the end the tag queue is nothing more than a frame index inside
the tag's BaseContainer (only with a synchronized access).
'''

from threading import Condition

import rokoko_ids as rid


class TagQueue():

    def __init__(self):
        self._lock = Condition()  # serializes all access to the queue

    def Flush(self, tag):
        '''Removes any previously dispatched frames'''

        self._lock.acquire()
        tag.GetDataInstance().RemoveData(rid.ID_TAG_IDX_READ_FRAME)
        self._lock.release()

    def AddFrame(self, tag, idx):
        '''Called by listener thread to dispatch a frame to a tag.'''
        self._lock.acquire()
        tag.GetDataInstance().SetInt32(rid.ID_TAG_IDX_READ_FRAME, idx)
        self._lock.release()

    def GetFrameIdx(self, tag):
        '''Called by tag to get the index of the dispatched frame.

        As queues are static (in the sense data doesn't change during
        playback), the tag will then directly access the assigned data queue
        and retrieve the frame via this index.
        '''

        bcTag = tag.GetDataInstance()

        self._lock.acquire()
        idxFrame = bcTag.GetData(rid.ID_TAG_IDX_READ_FRAME)
        self._lock.release()
        return idxFrame
