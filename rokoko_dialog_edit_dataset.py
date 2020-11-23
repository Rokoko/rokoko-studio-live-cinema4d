# Simple dialog to change a motion data clip reference (name, file reference).
#
# Intended to be used as a modal dialog.
import os
import c4d
from rokoko_ids import *
from rokoko_utils import *
from rokoko_dialog_utils import *

class DialogEditDataSet(c4d.gui.GeDialog):

    # The data set needs to be provided, when the dialog gets instanced.
    def __init__(self, bcDataSet, local, title='Edit Clip...'):
        self._title = title
        self._local = local
        if bcDataSet is None:
            self._bcDataSet = BaseContainerDataSet('New Clip', 'new clip.rec', isLocal=local)
        else:
            self._bcDataSet = bcDataSet.GetClone(c4d.COPYFLAGS_NONE)
        self._result = False
        c4d.gui.GeDialog.__init__(self)


    # Called by C4D to draw the dialog.
    def CreateLayout(self):
        self.SetTitle(self._title) # dialog's window title

        if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=1): # Dialog main group
            self.GroupBorderSpace(5, 5, 10, 5)

            CreateLayoutAddGroupBar(self, 'Clip')
            self.GroupSpace(0, 15)
            if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2): # parameters
                self.GroupSpace(20, 0)

                # Row 1
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Name:')
                self.AddEditText(ID_DLGEDITDATASET_NAME, c4d.BFH_SCALEFIT)

                # Row 2
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='File:')
                if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2): # filename
                    self.AddEditText(ID_DLGEDITDATASET_FILENAME, c4d.BFH_SCALEFIT, initw=600)
                    self.AddButton(ID_DLGEDITDATASET_CHOOSE_FILE, c4d.BFH_RIGHT, initw=30, name='...')
                self.GroupEnd()  # filename
            self.GroupEnd()  # parameters

            self.AddDlgGroup(c4d.DLG_OK | c4d.DLG_CANCEL)
        self.GroupEnd() # Dialog main group
        return True


    # Called by C4D to initialize widget values.
    def InitValues(self):
        self.SetString(ID_DLGEDITDATASET_NAME, self._bcDataSet[ID_BC_DATASET_NAME])
        filename = self._bcDataSet[ID_BC_DATASET_FILENAME]
        if self._bcDataSet[ID_BC_DATASET_IS_LOCAL] and filename[0] == '.' or os.sep not in filename:
            pathDoc = c4d.documents.GetActiveDocument().GetDocumentPath()
            if filename[0] == '.':
                filename = filename[2:]
            filename = filename.replace('\\', os.sep)
            filename = os.path.join(pathDoc, filename)
        self.SetString(ID_DLGEDITDATASET_FILENAME, filename)
        return True


    # Called by C4D to handle user's interaction with the dialog.
    def Command(self, id, msg):
        if id == ID_DLGEDITDATASET_NAME:
            self._bcDataSet[ID_BC_DATASET_NAME] = self.GetString(id)

        elif id == ID_DLGEDITDATASET_FILENAME:
            self._bcDataSet[ID_BC_DATASET_FILENAME] = self.GetString(id)

        elif id == ID_DLGEDITDATASET_CHOOSE_FILE: # user clicked "..." filename button
            # Open file requester to choose another motion data clip
            pathDefault, filenameDefault = os.path.split(self._bcDataSet[ID_BC_DATASET_FILENAME])
            filename = c4d.storage.LoadDialog(type=c4d.FILESELECTTYPE_ANYTHING, title='Load Clip File...', force_suffix='rec', def_path=pathDefault, def_file=filenameDefault)
            if filename is None or len(filename) < 2:
                return True

            self.SetString(ID_DLGEDITDATASET_FILENAME, filename)
            self._bcDataSet[ID_BC_DATASET_FILENAME] = filename

        elif id == c4d.DLG_OK: # User clicked Ok
            # Correct data set's ID
            idDataSetNew = MyHash(self._bcDataSet[ID_BC_DATASET_NAME] + self._bcDataSet[ID_BC_DATASET_FILENAME] + str(self._bcDataSet[ID_BC_DATASET_IS_LOCAL]))
            self._bcDataSet.SetId(idDataSetNew)

            # Successfully leave the dialog
            self._result = True
            self.Close()

        elif id == c4d.DLG_CANCEL: # User canceleld the dialog
            self._result = False # results should not be used
            self.Close()
        return True


    # To be called by the code using this dialog to query the results after the user closed it.
    def GetResult(self):
        return self._result, self._bcDataSet
