'''Simple dialog to change a motion data clip reference (name, file reference).

Intended to be used as a modal dialog.
'''

import os

import c4d

import rokoko_ids as rid
from rokoko_utils import (
    BaseContainerDataSet,
    MyHash,
)
from rokoko_dialog_utils import CreateLayoutAddGroupBar


class DialogEditDataSet(c4d.gui.GeDialog):

    def __init__(self, bcDataSet, local, title="Edit Clip..."):
        '''The data set needs to be provided, when the dialog gets instanced.
        '''

        self._title = title
        self._local = local
        if bcDataSet is None:
            self._bcDataSet = BaseContainerDataSet(
                "New Clip", "new clip.rec", isLocal=local)
        else:
            self._bcDataSet = bcDataSet.GetClone(c4d.COPYFLAGS_NONE)
        self._result = False
        c4d.gui.GeDialog.__init__(self)

    def CreateLayout(self):
        '''Called by C4D to draw the dialog.'''

        self.SetTitle(self._title)  # dialog's window title

        if self.GroupBegin(  # Dialog main group
                0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=1):
            self.GroupBorderSpace(5, 5, 10, 5)
            self.GroupSpace(0, 15)

            CreateLayoutAddGroupBar(self, "Clip")

            if self.GroupBegin(  # parameters
                    0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2):
                self.GroupSpace(20, 0)

                # Row 1
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name="Name:")
                self.AddEditText(rid.ID_DLGEDITDATASET_NAME, c4d.BFH_SCALEFIT)

                # Row 2
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name="File:")
                if self.GroupBegin(  # filename
                        0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2):
                    self.AddEditText(
                        rid.ID_DLGEDITDATASET_FILENAME,
                        c4d.BFH_SCALEFIT,
                        initw=600)
                    self.AddButton(
                        rid.ID_DLGEDITDATASET_CHOOSE_FILE,
                        c4d.BFH_RIGHT,
                        initw=30, name="...")
                self.GroupEnd()  # filename
            self.GroupEnd()  # parameters

            self.AddDlgGroup(c4d.DLG_OK | c4d.DLG_CANCEL)
        self.GroupEnd()  # Dialog main group
        return True

    def InitValues(self):
        '''Called by C4D to initialize widget values.'''

        self.SetString(rid.ID_DLGEDITDATASET_NAME,
                       self._bcDataSet[rid.ID_BC_DATASET_NAME])
        filename = self._bcDataSet[rid.ID_BC_DATASET_FILENAME]
        if self._bcDataSet[rid.ID_BC_DATASET_IS_LOCAL] and \
           filename[0] == "." or \
           os.sep not in filename:
            pathDoc = c4d.documents.GetActiveDocument().GetDocumentPath()
            if filename[0] == ".":
                filename = filename[2:]
            filename = filename.replace('\\', os.sep)
            filename = os.path.join(pathDoc, filename)
        self.SetString(rid.ID_DLGEDITDATASET_FILENAME, filename)
        return True

    def Command(self, id, msg):
        '''Called by C4D to handle user's interaction with the dialog.'''

        if id == rid.ID_DLGEDITDATASET_NAME:
            self._bcDataSet[rid.ID_BC_DATASET_NAME] = self.GetString(id)

        elif id == rid.ID_DLGEDITDATASET_FILENAME:
            self._bcDataSet[rid.ID_BC_DATASET_FILENAME] = self.GetString(id)

        elif id == rid.ID_DLGEDITDATASET_CHOOSE_FILE:
            # User clicked "..." filename button

            # Open file requester to choose another motion data clip
            pathDefault, filenameDefault = os.path.split(
                self._bcDataSet[rid.ID_BC_DATASET_FILENAME])
            filename = c4d.storage.LoadDialog(
                type=c4d.FILESELECTTYPE_ANYTHING,
                title="Load Clip File...",
                force_suffix="rec",
                def_path=pathDefault,
                def_file=filenameDefault)
            if filename is None or len(filename) < 2:
                return True

            self.SetString(rid.ID_DLGEDITDATASET_FILENAME, filename)
            self._bcDataSet[rid.ID_BC_DATASET_FILENAME] = filename

        elif id == c4d.DLG_OK:
            # User clicked Ok

            # Correct data set's ID
            sDataSetNew = self._bcDataSet[rid.ID_BC_DATASET_NAME] + \
                self._bcDataSet[rid.ID_BC_DATASET_FILENAME] + \
                str(self._bcDataSet[rid.ID_BC_DATASET_IS_LOCAL])
            idDataSetNew = MyHash(sDataSetNew)
            self._bcDataSet.SetId(idDataSetNew)

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

        return self._result, self._bcDataSet
