from threading import Condition
from rokoko_ids import *

class TagQueue():
    def __init__(self):
        self._lock = Condition()

    def Flush(self, tag):
        self._lock.acquire()
        tag.GetDataInstance().RemoveData(ID_TAG_IDX_READ_FRAME)
        self._lock.release()

    def AddFrame(self, tag, idx):
        self._lock.acquire()
        tag.GetDataInstance().SetInt32(ID_TAG_IDX_READ_FRAME, idx)
        self._lock.release()

    def GetFrameIdx(self, tag):
        bcTag = tag.GetDataInstance()
        self._lock.acquire()
        idxFrame = bcTag.GetData(ID_TAG_IDX_READ_FRAME)
        self._lock.release()
        return idxFrame
