import os
import c4d
from rokoko_ids import *
from rokoko_utils import *
from rokoko_dialog_utils import *

class DialogEditDataSet(c4d.gui.GeDialog):

    def __init__(self, bcDataSet, local, title='Edit Clip...'):
        self._title = title
        self._local = local
        if bcDataSet is None:
            self._bcDataSet = BaseContainerDataSet(name, file, isLocal=local)
        else:
            self._bcDataSet = bcDataSet
        self._result = False
        c4d.gui.GeDialog.__init__(self)

    def CreateLayout(self):
        self.SetTitle(self._title)
        if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=1): # Dialog main group
            self.GroupBorderSpace(5, 5, 10, 5)
            CreateLayoutAddGroupBar(self, 'Clip')
            self.GroupSpace(0, 15)
            if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2): #
                self.GroupSpace(20, 0)
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Name:')
                self.AddEditText(ID_DLGEDITDATASET_NAME, c4d.BFH_SCALEFIT)
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='File:')
                if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=2): #
                    self.AddEditText(ID_DLGEDITDATASET_FILENAME, c4d.BFH_SCALEFIT)
                    self.AddButton(ID_DLGEDITDATASET_CHOOSE_FILE, c4d.BFH_RIGHT, initw=30, name='...')
                self.GroupEnd()  #
            self.GroupEnd()  #
            self.AddDlgGroup(c4d.DLG_OK | c4d.DLG_CANCEL)
        self.GroupEnd() # Dialog main group
        return True

    def InitValues(self):
        self.SetString(ID_DLGEDITDATASET_NAME, self._bcDataSet[ID_BC_DATASET_NAME])
        self.SetString(ID_DLGEDITDATASET_FILENAME, self._bcDataSet[ID_BC_DATASET_FILENAME])
        return True

    def Command(self, id, msg):
        if id == ID_DLGEDITDATASET_NAME:
            self._bcDataSet[ID_BC_DATASET_NAME] = self.GetString(id)
        elif id == ID_DLGEDITDATASET_FILENAME:
            self._bcDataSet[ID_BC_DATASET_FILENAME] = self.GetString(id)
        elif id == ID_DLGEDITDATASET_CHOOSE_FILE:
            pathDefault, filenameDefault = os.path.split(self._bcDataSet[ID_BC_DATASET_FILENAME])
            filename = c4d.storage.LoadDialog(type=c4d.FILESELECTTYPE_ANYTHING, title='Load Clip File...', force_suffix='rec', def_path=pathDefault, def_file=filenameDefault)
            if filename is None or len(filename) < 2:
                return True
            self.SetString(ID_DLGEDITDATASET_FILENAME, filename)
            self._bcDataSet[ID_BC_DATASET_FILENAME] = filename
        elif id == c4d.DLG_OK:
            idDataSetNew = MyHash(self._bcDataSet[ID_BC_DATASET_NAME] + self._bcDataSet[ID_BC_DATASET_FILENAME] + str(self._bcDataSet[ID_BC_DATASET_IS_LOCAL]))
            self._bcDataSet.SetId(idDataSetNew)
            self._result = True
            self.Close()
        elif id == c4d.DLG_CANCEL:
            self._result = False
            self.Close()
        return True

    def GetResult(self):
        return self._result, self._bcDataSet
