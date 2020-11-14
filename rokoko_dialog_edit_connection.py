# Simple dialog to edit the parameters of a connection.
#
# In principle there could be multiple connections (only one connected at a time).
# For example to quickly switch between different production environments.
# Hence a connection has a name, just like data sets (clips).
# This functionality is currently not exposed in the Manager UI.
#
# Intended to be used as a modal dialog.
import os
import c4d
from rokoko_ids import *
from rokoko_utils import *
from rokoko_dialog_utils import *

class DialogEditConnection(c4d.gui.GeDialog):

    # The connection needs to be provided, when the dialog gets instanced.
    def __init__(self, bcConnection, title='Edit Connection...'):
        self._title = title
        if bcConnection is None:
            self._bcConnection = BaseContainerConnection('New Connection')
        else:
            self._bcConnection = bcConnection
        self._result = False
        c4d.gui.GeDialog.__init__(self)


    # Called by C4D to draw the dialog.
    def CreateLayout(self):
        self.SetTitle(self._title) # dialog's window title

        if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=1): # Dialog main group
            self.GroupBorderSpace(5, 5, 10, 5)

            CreateLayoutAddGroupBar(self, 'Live Connection')

            self.GroupSpace(0, 15)
            if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2): # Rokoko Studio Live parameters
                self.GroupSpace(20, 0)

                # Row 1
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Name:')
                self.AddEditText(ID_DLGEDITCONN_NAME, c4d.BFH_SCALEFIT)

                # Row 2
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Port:')
                self.AddEditText(ID_DLGEDITCONN_PORT, c4d.BFH_SCALEFIT)
            self.GroupEnd()  # Rokoko Studio Live parameters

            CreateLayoutAddGroupBar(self, 'Command API Connection')

            if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2): # Command API parameters
                self.GroupSpace(20, 0)

                # Row 1
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='IP:')
                self.AddEditText(ID_DLGEDITCONN_COMMANDAPI_IP, c4d.BFH_SCALEFIT)

                # Row 2
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Port:')
                self.AddEditText(ID_DLGEDITCONN_COMMANDAPI_PORT, c4d.BFH_SCALEFIT)

                # Row 3
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Key:')
                self.AddEditText(ID_DLGEDITCONN_COMMANDAPI_KEY, c4d.BFH_SCALEFIT)
            self.GroupEnd() # Command API parameters

            self.AddDlgGroup(c4d.DLG_OK | c4d.DLG_CANCEL)
        self.GroupEnd() # Dialog main group
        return True


    # Called by C4D to initialize widget values.
    def InitValues(self):
        self.SetString(ID_DLGEDITCONN_NAME, self._bcConnection[ID_BC_DATASET_NAME])
        self.SetString(ID_DLGEDITCONN_PORT, self._bcConnection[ID_BC_DATASET_LIVE_PORT])
        self.SetString(ID_DLGEDITCONN_COMMANDAPI_IP, self._bcConnection[ID_BC_DATASET_COMMANDAPI_IP])
        self.SetString(ID_DLGEDITCONN_COMMANDAPI_PORT, self._bcConnection[ID_BC_DATASET_COMMANDAPI_PORT])
        self.SetString(ID_DLGEDITCONN_COMMANDAPI_KEY, self._bcConnection[ID_BC_DATASET_COMMANDAPI_KEY])
        return True


    # Called by C4D to handle user's interaction with the dialog.
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

        elif id == c4d.DLG_OK: # User clicked Ok
            # Correct connection's ID
            idConnectionNew = MyHash(self._bcConnection[ID_BC_DATASET_NAME] + self._bcConnection[ID_BC_DATASET_LIVE_PORT] + \
                                     self._bcConnection[ID_BC_DATASET_COMMANDAPI_IP] + self._bcConnection[ID_BC_DATASET_COMMANDAPI_PORT] + \
                                     self._bcConnection[ID_BC_DATASET_COMMANDAPI_KEY])
            self._bcConnection.SetId(idConnectionNew)
            # Successfully leave the dialog
            self._result = True
            self.Close()

        elif id == c4d.DLG_CANCEL: # User canceleld the dialog
            self._result = False # results should not be used
            self.Close()
        return True


    # To be called by the code using this dialog to query the results after the user closed it.
    def GetResult(self):
        return self._result, self._bcConnection
