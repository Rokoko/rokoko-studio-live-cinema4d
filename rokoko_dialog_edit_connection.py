import os
import c4d
from rokoko_ids import *
from rokoko_utils import *
from rokoko_dialog_utils import *

class DialogEditConnection(c4d.gui.GeDialog):

    def __init__(self, bcConnection, title='Edit Connection...'):
        self._title = title
        if bcConnection is None:
            self._bcConnection = BaseContainerConnection('New Connection', '', '14043', '')
        else:
            self._bcConnection = bcConnection
        self._result = False
        c4d.gui.GeDialog.__init__(self)

    def CreateLayout(self):
        self.SetTitle(self._title)
        if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=1): # Dialog main group
            self.GroupBorderSpace(5, 5, 10, 5)
            CreateLayoutAddGroupBar(self, 'Live Connection')
            self.GroupSpace(0, 15)
            if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2): #
                self.GroupSpace(20, 0)
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Name:')
                self.AddEditText(ID_DLGEDITCONN_NAME, c4d.BFH_SCALEFIT)
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Port:')
                self.AddEditText(ID_DLGEDITCONN_PORT, c4d.BFH_SCALEFIT)
            self.GroupEnd()  #
            CreateLayoutAddGroupBar(self, 'Command API Connection')
            self.GroupSpace(0, 15)
            if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2): #
                self.GroupSpace(20, 0)
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='IP:')
                self.AddEditText(ID_DLGEDITCONN_COMMANDAPI_IP, c4d.BFH_SCALEFIT)
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Port:')
                self.AddEditText(ID_DLGEDITCONN_COMMANDAPI_PORT, c4d.BFH_SCALEFIT)
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Key:')
                self.AddEditText(ID_DLGEDITCONN_COMMANDAPI_KEY, c4d.BFH_SCALEFIT)
            self.GroupEnd()  #
            self.AddDlgGroup(c4d.DLG_OK | c4d.DLG_CANCEL)
        self.GroupEnd() # Dialog main group
        return True

    def InitValues(self):
        self.SetString(ID_DLGEDITCONN_NAME, self._bcConnection[ID_BC_DATASET_NAME])
        self.SetString(ID_DLGEDITCONN_PORT, self._bcConnection[ID_BC_DATASET_LIVE_PORT])
        self.SetString(ID_DLGEDITCONN_COMMANDAPI_IP, self._bcConnection[ID_BC_DATASET_COMMANDAPI_IP])
        self.SetString(ID_DLGEDITCONN_COMMANDAPI_PORT, self._bcConnection[ID_BC_DATASET_COMMANDAPI_PORT])
        self.SetString(ID_DLGEDITCONN_COMMANDAPI_KEY, self._bcConnection[ID_BC_DATASET_COMMANDAPI_KEY])
        return True

    def Command(self, id, msg):
        if id == ID_DLGEDITCONN_NAME:
            self._bcConnection[ID_BC_DATASET_NAME] = self.GetString(id)
        elif id == ID_DLGEDITCONN_PORT:
            self._bcConnection[ID_BC_DATASET_LIVE_PORT] = self.GetString(id)
        elif id == ID_DLGEDITCONN_COMMANDAPI_IP:
            self._bcConnection[ID_BC_DATASET_COMMANDAPI_IP] = self.GetString(id)
        elif id == ID_DLGEDITCONN_COMMANDAPI_PORT:
            self._bcConnection[ID_BC_DATASET_COMMANDAPI_PORT] = self.GetString(id)
        elif id == ID_DLGEDITCONN_COMMANDAPI_KEY:
            self._bcConnection[ID_BC_DATASET_COMMANDAPI_KEY] = self.GetString(id)
        elif id == c4d.DLG_OK:
            idConnectionNew = MyHash(self._bcConnection[ID_BC_DATASET_NAME] + self._bcConnection[ID_BC_DATASET_LIVE_PORT] + \
                                     self._bcConnection[ID_BC_DATASET_COMMANDAPI_IP] + self._bcConnection[ID_BC_DATASET_COMMANDAPI_PORT] + \
                                     self._bcConnection[ID_BC_DATASET_COMMANDAPI_KEY])
            self._bcConnection.SetId(idConnectionNew)
            self._result = True
            self.Close()
        elif id == c4d.DLG_CANCEL:
            self._result = False
            self.Close()
        return True

    def GetResult(self):
        return self._result, self._bcConnection
