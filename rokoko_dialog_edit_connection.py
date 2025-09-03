'''Simple dialog to edit the parameters of a connection.

In principle there could be multiple connections (only one connected at a
time).
For example to quickly switch between different production environments.
Hence a connection has a name, just like data sets (clips).
This functionality is currently not exposed in the Manager UI.

Intended to be used as a modal dialog.
'''

import c4d

import rokoko_ids as rid
from rokoko_utils import BaseContainerConnection
from rokoko_dialog_utils import (
    CreateLayoutAddGroupBar,
    MyHash,
)


class DialogEditConnection(c4d.gui.GeDialog):

    def __init__(self, bcConnection, title="Edit Connection..."):
        '''The connection needs to be provided, when the dialog gets instanced.
        '''

        self._title = title
        if bcConnection is None:
            self._bcConnection = BaseContainerConnection("New Connection")
        else:
            self._bcConnection = bcConnection.GetClone(c4d.COPYFLAGS_NONE)
        self._result = False
        c4d.gui.GeDialog.__init__(self)

    def CreateLayout(self):
        '''Called by C4D to draw the dialog.'''

        self.SetTitle(self._title)  # dialog's window title

        if self.GroupBegin(  # Dialog main group
                0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=1):
            self.GroupBorderSpace(5, 5, 10, 5)

            CreateLayoutAddGroupBar(self, "Live Connection")

            self.GroupSpace(0, 15)
            if self.GroupBegin(  # Rokoko Studio Live parameters
                    0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2):
                self.GroupSpace(20, 0)

                # Row 1
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name="Name:")
                self.AddEditText(rid.ID_DLGEDITCONN_NAME, c4d.BFH_SCALEFIT)

                # Row 2
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name="Port:")
                self.AddEditText(rid.ID_DLGEDITCONN_PORT, c4d.BFH_SCALEFIT)
            self.GroupEnd()  # Rokoko Studio Live parameters

            CreateLayoutAddGroupBar(self, "Command API Connection")

            if self.GroupBegin(  # Command API parameters
                    0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2):
                self.GroupSpace(20, 0)

                # Row 1
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name="IP:")
                self.AddEditText(
                    rid.ID_DLGEDITCONN_COMMANDAPI_IP, c4d.BFH_SCALEFIT)

                # Row 2
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name="Port:")
                self.AddEditText(
                    rid.ID_DLGEDITCONN_COMMANDAPI_PORT, c4d.BFH_SCALEFIT)

                # Row 3
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name="Key:")
                self.AddEditText(
                    rid.ID_DLGEDITCONN_COMMANDAPI_KEY, c4d.BFH_SCALEFIT)
            self.GroupEnd()  # Command API parameters

            self.AddDlgGroup(c4d.DLG_OK | c4d.DLG_CANCEL)
        self.GroupEnd()  # Dialog main group
        return True

    def InitValues(self):
        '''Called by C4D to initialize widget values.'''

        self.SetString(rid.ID_DLGEDITCONN_NAME,
                       self._bcConnection[rid.ID_BC_DATASET_NAME])
        self.SetString(rid.ID_DLGEDITCONN_PORT,
                       self._bcConnection[rid.ID_BC_DATASET_LIVE_PORT])
        self.SetString(rid.ID_DLGEDITCONN_COMMANDAPI_IP,
                       self._bcConnection[rid.ID_BC_DATASET_COMMANDAPI_IP])
        self.SetString(rid.ID_DLGEDITCONN_COMMANDAPI_PORT,
                       self._bcConnection[rid.ID_BC_DATASET_COMMANDAPI_PORT])
        self.SetString(rid.ID_DLGEDITCONN_COMMANDAPI_KEY,
                       self._bcConnection[rid.ID_BC_DATASET_COMMANDAPI_KEY])
        return True

    def Command(self, id, msg):
        '''Called by C4D to handle user's interaction with the dialog.'''

        if id == rid.ID_DLGEDITCONN_NAME:
            self._bcConnection[rid.ID_BC_DATASET_NAME] = self.GetString(id)

        elif id == rid.ID_DLGEDITCONN_PORT:
            self._bcConnection[
                rid.ID_BC_DATASET_LIVE_PORT] = self.GetString(id)

        elif id == rid.ID_DLGEDITCONN_COMMANDAPI_IP:
            self._bcConnection[
                rid.ID_BC_DATASET_COMMANDAPI_IP] = self.GetString(id)

        elif id == rid.ID_DLGEDITCONN_COMMANDAPI_PORT:
            self._bcConnection[
                rid.ID_BC_DATASET_COMMANDAPI_PORT] = self.GetString(id)

        elif id == rid.ID_DLGEDITCONN_COMMANDAPI_KEY:
            self._bcConnection[
                rid.ID_BC_DATASET_COMMANDAPI_KEY] = self.GetString(id)

        elif id == c4d.DLG_OK:
            # User clicked Ok

            # Correct connection's ID
            sConnectionNew = self._bcConnection[rid.ID_BC_DATASET_NAME] + \
                self._bcConnection[rid.ID_BC_DATASET_LIVE_PORT] + \
                self._bcConnection[rid.ID_BC_DATASET_COMMANDAPI_IP] + \
                self._bcConnection[rid.ID_BC_DATASET_COMMANDAPI_PORT] + \
                self._bcConnection[rid.ID_BC_DATASET_COMMANDAPI_KEY]
            idConnectionNew = MyHash(sConnectionNew)
            self._bcConnection.SetId(idConnectionNew)
            # Successfully leave the dialog
            self._result = True
            self.Close()

        elif id == c4d.DLG_CANCEL:
            # User cancelled the dialog

            self._result = False  # results should not be used
            self.Close()
        return True

    def GetResult(self):
        '''To be called by the code using this dialog to query the results
        after the user closed it.
        '''

        return self._result, self._bcConnection
