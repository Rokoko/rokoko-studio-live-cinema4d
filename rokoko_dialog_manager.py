import os, shutil, json
import urllib.request
import c4d
currentOS = c4d.GeGetCurrentOS()
if currentOS == c4d.OPERATINGSYSTEM_WIN:
    import packages.win.lz4.frame as lz4f
elif currentOS == c4d.OPERATINGSYSTEM_OSX:
    import packages.mac.lz4.frame as lz4f
from rokoko_ids import *
from rokoko_utils import *
from rokoko_listener import *
from rokoko_dialog_utils import *
from rokoko_dialog_about import *
from rokoko_dialog_save_recording import *
from rokoko_dialog_edit_connection import *
from rokoko_dialog_edit_dataset import *

DO_FILE_ACTION = True

LINKS = { ID_DLGMNGR_WEB_ROKOKO : 'https://www.rokoko.com',
          ID_DLGMNGR_WEB_STUDIO_LIVE_LICENSE : 'https://github.com/Rokoko/rokoko-studio-live-cinema4d/blob/main/LICENSE',
          ID_DLGMNGR_WEB_DOCUMENTATION : 'https://help.rokoko.com/support/solutions/folders/47000773247',
          ID_DLGMNGR_WEB_FORUMS : 'https://rokoko.freshdesk.com/support/discussions/forums/47000400299',
        }
WIDTH_ADD_BUTTON = 16

g_thdListener = GetListenerThread() # owned by rokoko_listener
def DlgManagerDataDestroyGlobals():
    global g_thdListener
    g_thdListener = None


class DialogRokokoManager(c4d.gui.GeDialog):
    _quickTab = None
    _bitmapButtonPlayPause = None
    _bitmapButtonConnectionStatus = None
    _bitmapButtonsPerConnectionStatus = []
    _tags = None
    _buttonRecordState = False
    _connecting = False
    _dlgChild = None

    def CreateLayoutAddMenu(self):
        self.MenuFlushAll()
        self.MenuSubBegin('Help')
        self.MenuAddString(ID_DLGMNGR_WEB_ROKOKO, 'Rokoko Website')
        self.MenuAddString(ID_DLGMNGR_WEB_STUDIO_LIVE_LICENSE, 'Rokoko Studio Live License')
        self.MenuAddString(ID_DLGMNGR_WEB_DOCUMENTATION, 'Documentation')
        self.MenuAddString(ID_DLGMNGR_WEB_FORUMS, 'Join our forums')
        self.MenuAddSeparator()
        self.MenuAddString(ID_DLGMNGR_ABOUT, 'About')
        self.MenuSubEnd() # Help
        self.MenuFinished()

    def CreateLayoutInMenu(self):
        self.GroupBeginInMenuLine()
        self.AddComboBox(ID_DLGMNGR_CONNECTIONS_IN_MENU, c4d.BFH_RIGHT, initw=200)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=10, name='') # spacer
        self._bitmapButtonConnectionStatus = CreateLayoutAddBitmapButton(self, 0, idIcon1=465003508, tooltip='', button=False, toggle=False, flags=c4d.BFH_CENTER|c4d.BFV_CENTER)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=10, name='') # spacer
        self.AddSlider(ID_DLGMNGR_PLAYER_BUFFERING_IN_MENU, flags=c4d.BFH_LEFT, initw=40)
        self.Enable(ID_DLGMNGR_PLAYER_BUFFERING_IN_MENU, False)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=10, name='') # spacer
        self.GroupEnd()

    def UpdateLayoutInMenu(self):
        self.FreeChildren(ID_DLGMNGR_CONNECTIONS_IN_MENU)
        isConnected = IsConnected()
        idConnected = GetConnectedDataSetId()
        if isConnected:
            self.AddChild(ID_DLGMNGR_CONNECTIONS_IN_MENU, 999999, 'Disconnect')
            self.AddChild(ID_DLGMNGR_CONNECTIONS_IN_MENU, 1000000, '')
        bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
        idxConnected = 999999
        if len(bcConnections) > 0:
            idx = 0
            for id, bcConnection in bcConnections:
                self.AddChild(ID_DLGMNGR_CONNECTIONS_IN_MENU, idx, bcConnection[ID_BC_DATASET_NAME])
                if id == idConnected:
                    idxConnected = idx
                idx += 1
        if not isConnected:
            self.AddChild(ID_DLGMNGR_CONNECTIONS_IN_MENU, 1000000, '')
            self.AddChild(ID_DLGMNGR_CONNECTIONS_IN_MENU, 999999, 'Not Connected')
        self.SetInt32(ID_DLGMNGR_CONNECTIONS_IN_MENU, idxConnected)
        statusConnection = g_thdListener.GetConnectionStatus()
        if statusConnection == 0:
            idIcon = 465003508 # red dot
        elif statusConnection == 1:
            idIcon = 465001743 # green dot
        elif statusConnection == 2 and isConnected:
            idIcon = 465001740 # orange dot
        elif statusConnection == 2 and not isConnected:
            idIcon = 465001746 # grey dot
        self.Enable(ID_DLGMNGR_CONNECTION_STATUS_IN_MENU, statusConnection != 2 or isConnected)
        icon = c4d.gui.GetIcon(idIcon)
        bmpIcon = icon['bmp'].GetClonePart(icon['x'], icon['y'], icon['w'], icon['h'])
        self._bitmapButtonConnectionStatus.SetImage(bmpIcon)

    def CreateLayoutRowConnection(self, bc, idx):
        self.AddButton(ID_DLGMNGR_BASE_CONNECTION_POPUP + idx, c4d.BFH_FIT, initw=WIDTH_ADD_BUTTON, name='...')
        labelConnection = bc[ID_BC_DATASET_NAME] + ' (' + bc[ID_BC_DATASET_LIVE_PORT] + ')'
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name=labelConnection)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=20, name='')
        self.AddCheckbox(ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT + idx, c4d.BFH_CENTER, initw=0, inith=0, name='Auto Connect')
        self.AddStaticText(0, c4d.BFH_LEFT, initw=10, name='') # spacer
        bitmapButton = CreateLayoutAddBitmapButton(self, 0, idIcon1=465003508, tooltip='', button=False, toggle=False, flags=c4d.BFH_CENTER|c4d.BFV_CENTER)
        self._bitmapButtonsPerConnectionStatus.append(bitmapButton)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=10, name='') # spacer
        self.AddButton(ID_DLGMNGR_BASE_CONNECTION_CONNECT + idx, c4d.BFH_FIT, initw=100, name='')
        if self.GroupBegin(ID_DLGMNGR_GROUP_CONNECTION_DATA_CONTENT, flags=c4d.BFH_SCALEFIT, title='', rows=1):
            self.AddStaticText(0, c4d.BFH_LEFT, initw=20, name='') # spacer
            self.AddStaticText(ID_DLGMNGR_CONNECTION_FPS, c4d.BFH_CENTER, initw=0, name='')
        self.GroupEnd()

    def CreateLayoutGroupConnections(self):
        if self.GroupBegin(ID_DLGMNGR_GROUP_CONNECTIONS, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=1):
            CreateLayoutAddGroupBar(self, 'Connection')
            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=1, inith=16):
                scrollFlags = c4d.SCROLLGROUP_VERT | c4d.SCROLLGROUP_AUTOVERT | c4d.SCROLLGROUP_NOVGAP
                if self.ScrollGroupBegin(ID_DLGMNGR_SCROLL_CONNECTIONS, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, scrollFlags, initw=0, inith=0):
                    if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=9):
                        self.GroupBorderSpace(10, 2, 0, 0)
                        self._bitmapButtonsPerConnectionStatus.clear()
                        bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
                        if len(bcConnections) > 0:
                            idx = 0
                            for id, bcConnection in bcConnections:
                                self.CreateLayoutRowConnection(bcConnection, idx)
                                idx += 1
                        else:
                            self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='No connections configured.')
                    self.GroupEnd()
                self.GroupEnd()
            self.GroupEnd()
            if self.GroupBegin(ID_DLGMNGR_GROUP_CONNECTION_DATA, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=1):
                self.GroupBorderSpace(38, 0, 0, 0)
                if self.GroupBegin(ID_DLGMNGR_GROUP_CONNECTION_DATA_DETAILS, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=2): #, groupflags=c4d.BORDER_GROUP_IN):
                    self.GroupBorderSpace(10, 0, 0, 0)
                    # filled in UpdateLayoutGroupConnectedDataSet()
                self.GroupEnd()
            self.GroupEnd()
        self.GroupEnd()

    def UpdateLayoutGroupConnections(self):
        self.LayoutFlushGroup(ID_DLGMNGR_GROUP_CONNECTIONS)
        self.CreateLayoutGroupConnections()
        self.LayoutChanged(ID_DLGMNGR_GROUP_CONNECTIONS)

    def UpdateLayoutGroupConnectedDataSet(self):
        bc = GetConnectedDataSet()
        numActors = 0
        numGloves = 0
        numFaces = 0
        numLights = 0
        numCameras = 0
        numProps = 0
        name = ''
        fps = 0.0
        if bc is not None:
            name = bc[0]
            numActors = bc[ID_BC_DATASET_NUM_SUITS]
            numGloves = bc[ID_BC_DATASET_NUM_GLOVES]
            numFaces = bc[ID_BC_DATASET_NUM_FACES]
            numLights = bc[ID_BC_DATASET_NUM_LIGHTS]
            numCameras = bc[ID_BC_DATASET_NUM_CAMERAS]
            numProps = bc[ID_BC_DATASET_NUM_PROPS]
            fps = bc[ID_BC_DATASET_LIVE_FPS]
        self.SetString(ID_DLGMNGR_CONNECTION_NAME, name)
        self.SetString(ID_DLGMNGR_CONNECTION_FPS, '(FPS: ' + str(fps) + ')')
        self.LayoutFlushGroup(ID_DLGMNGR_GROUP_CONNECTION_DATA_DETAILS)
        if numActors > 0:
            bcActors = bc[ID_BC_DATASET_ACTORS]
            self.AddStaticText(ID_DLGMNGR_CONNECTION_NAMES_ACTORS_LABEL, c4d.BFH_LEFT, initw=0, name='') #'Actors:')
            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=6):
                for idxActor, bcActor in bcActors:
                    CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_PROFILE, tooltip='', button=False, toggle=False, flags=c4d.BFH_LEFT|c4d.BFV_CENTER)
                    self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name=bcActor[ID_BC_ENTITY_NAME])
                    if bcActor[ID_BC_ENTITY_HAS_SUIT]:
                        CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_SUIT, tooltip='', button=False, toggle=False, flags=c4d.BFH_LEFT|c4d.BFV_CENTER)
                    else:
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='')
                    if bcActor[ID_BC_ENTITY_HAS_FACE]:
                        CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_FACE, tooltip='', button=False, toggle=False, flags=c4d.BFH_LEFT|c4d.BFV_CENTER)
                    else:
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='')
                    if bcActor[ID_BC_ENTITY_HAS_GLOVE_LEFT]:
                        CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_GLOVE_LEFT, tooltip='', button=False, toggle=False, flags=c4d.BFH_LEFT|c4d.BFV_CENTER)
                    else:
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='')
                    if bcActor[ID_BC_ENTITY_HAS_GLOVE_RIGHT]:
                        CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_GLOVE_RIGHT, tooltip='', button=False, toggle=False, flags=c4d.BFH_LEFT|c4d.BFV_CENTER)
                    else:
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='')
            self.GroupEnd()
        if numProps > 0:
            bcProps = bc[ID_BC_DATASET_PROPS]
            self.AddStaticText(ID_DLGMNGR_CONNECTION_NAMES_PROPS_LABEL, c4d.BFH_LEFT, initw=0, name='') #'Props:')
            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=2):
                for idxProp, bcProp in bcProps:
                    CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_PROP, tooltip='', button=False, toggle=False, flags=c4d.BFH_LEFT|c4d.BFV_CENTER)
                    self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name=bcProp[ID_BC_ENTITY_NAME])
            self.GroupEnd()
        if numActors == 0 and numProps == 0:
            self.AddStaticText(ID_DLGMNGR_CONNECTION_NAMES_ACTORS_LABEL, c4d.BFH_LEFT, initw=0, name='Receiving no data!')
        self.LayoutChanged(ID_DLGMNGR_GROUP_CONNECTION_DATA_DETAILS)


    def CreateLayoutHeadingsDataSet(self, local):
        if local:
            idButtonPopup = ID_DLGMNGR_LOCAL_DATA_POPUP
        else:
            idButtonPopup = ID_DLGMNGR_GLOBAL_DATA_POPUP
        self.AddButton(idButtonPopup, c4d.BFH_LEFT, initw=WIDTH_ADD_BUTTON, inith=0, name='+')
        self.AddStaticText(0, c4d.BFH_LEFT, initw=150, name='Name')
        self.AddStaticText(0, c4d.BFH_LEFT, initw=20, name='') # spacer
        CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_SUIT, tooltip='Number of Suits', button=False, toggle=False, flags=c4d.BFH_RIGHT|c4d.BFV_CENTER)
        CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_GLOVE_LEFT, tooltip='Number of Gloves', button=False, toggle=False, flags=c4d.BFH_RIGHT|c4d.BFV_CENTER)
        CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_FACE, tooltip='Number of Faces', button=False, toggle=False, flags=c4d.BFH_RIGHT|c4d.BFV_CENTER)
        CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_PROP, tooltip='Number of Props', button=False, toggle=False, flags=c4d.BFH_RIGHT|c4d.BFV_CENTER)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=20, name='') # spacer
        self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=0, name='File')

    def CreateLayoutRowDataSet(self, bcDataSet, idx):
        if bcDataSet[ID_BC_DATASET_IS_LOCAL]:
            idButtonBase = ID_DLGMNGR_BASE_LOCAL_DATA_POPUP
        else:
            idButtonBase = ID_DLGMNGR_BASE_GLOBAL_DATA_POPUP
        self.AddButton(idButtonBase + idx, c4d.BFH_FIT, initw=WIDTH_ADD_BUTTON, name='...')
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name=bcDataSet[ID_BC_DATASET_NAME])
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='')
        self.AddStaticText(0, c4d.BFH_CENTER, initw=0, name=bcDataSet[ID_BC_DATASET_NUM_SUITS])
        self.AddStaticText(0, c4d.BFH_CENTER, initw=0, name=bcDataSet[ID_BC_DATASET_NUM_GLOVES])
        self.AddStaticText(0, c4d.BFH_CENTER, initw=0, name=bcDataSet[ID_BC_DATASET_NUM_FACES])
        self.AddStaticText(0, c4d.BFH_CENTER, initw=0, name=bcDataSet[ID_BC_DATASET_NUM_PROPS])
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='')
        self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=0, name=bcDataSet[ID_BC_DATASET_FILENAME])

    def CreateLayoutGroupDataSet(self, local):
        if local:
            idGroup = ID_DLGMNGR_GROUP_LOCAL_DATA
            nameGroup = 'Project Clips'
            bcDataSets = GetLocalDataSets()
        else:
            idGroup = ID_DLGMNGR_GROUP_GLOBAL_DATA
            nameGroup = 'Global Clips'
            bcDataSets = GetPrefsContainer(ID_BC_DATA_SETS)
        if self.GroupBegin(idGroup, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=1):
            CreateLayoutAddGroupBar(self, nameGroup)
            scrollFlags = c4d.SCROLLGROUP_VERT | c4d.SCROLLGROUP_AUTOVERT | c4d.SCROLLGROUP_NOVGAP
            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=1, inith=52):
                if self.ScrollGroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, scrollFlags, initw=0, inith=0):
                    if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=9):
                        self.GroupBorderSpace(10, 2, 0, 0)
                        self.CreateLayoutHeadingsDataSet(local)
                        if len(bcDataSets) > 0:
                            idx = 0
                            for id, bcDataSet in bcDataSets:
                                self.CreateLayoutRowDataSet(bcDataSet, idx)
                                idx += 1
                        else:
                            self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='')
                            self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='No data sets.')
                    self.GroupEnd()
                self.GroupEnd()
            self.GroupEnd()
        self.GroupEnd()

    def UpdateLayoutGroupDataSet(self, local):
        if local:
            idGroup = ID_DLGMNGR_GROUP_LOCAL_DATA
        else:
            idGroup = ID_DLGMNGR_GROUP_GLOBAL_DATA
        self.LayoutFlushGroup(idGroup)
        self.CreateLayoutGroupDataSet(local)
        self.LayoutChanged(idGroup)


    def CreateLayoutRowControl(self, tag, idx):
        if tag is None or not tag.IsAlive():
            return
        bmpObj = None
        obj = tag.GetObject()
        if obj is not None:
            objName = obj.GetName()
            iconDataObj = obj.GetIcon()
            bmpObj = iconDataObj['bmp'].GetClonePart(iconDataObj['x'], iconDataObj['y'], iconDataObj['w'], iconDataObj['h'])
        else:
            objName = 'Tag not assigned'
        iconDataTag = tag.GetIcon()
        bmpTag = iconDataTag['bmp'].GetClonePart(iconDataTag['x'], iconDataTag['y'], iconDataTag['w'], iconDataTag['h'])
        self.AddButton(ID_DLGMNGR_BASE_TAG_POPUP + idx, c4d.BFH_FIT, initw=WIDTH_ADD_BUTTON, name='...')
        CreateLayoutAddBitmapButton(self, 0, bmpTag, tooltip='', button=False, toggle=False, flags=c4d.BFH_LEFT|c4d.BFV_CENTER)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name=tag.GetName())
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='')
        CreateLayoutAddBitmapButton(self, 0, bmpObj, tooltip='', button=False, toggle=False, flags=c4d.BFH_LEFT|c4d.BFV_CENTER)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name=objName)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='')
        self.AddComboBox(ID_DLGMNGR_BASE_TAG_RIG_TYPES + idx, c4d.BFH_SCALEFIT)
        bcRigTypes = tag.GetDataInstance().GetContainerInstance(ID_TAG_BC_RIG_TYPES)
        for idxRigType, value in bcRigTypes:
            self.AddChild(ID_DLGMNGR_BASE_TAG_RIG_TYPES + idx, idxRigType, value)
        self.AddComboBox(ID_DLGMNGR_BASE_TAG_DATA_SETS + idx, c4d.BFH_SCALEFIT)
        bcDataSets = tag.GetDataInstance().GetContainerInstance(ID_TAG_BC_DATASETS)
        for idxDataSet, value in bcDataSets:
            self.AddChild(ID_DLGMNGR_BASE_TAG_DATA_SETS + idx, idxDataSet, value)
        self.AddComboBox(ID_DLGMNGR_BASE_TAG_ACTORS + idx, c4d.BFH_SCALEFIT)
        bcDataSets = tag.GetDataInstance().GetContainerInstance(ID_TAG_BC_ACTORS)
        for idxActor, value in bcDataSets:
            self.AddChild(ID_DLGMNGR_BASE_TAG_ACTORS + idx, idxActor, value)
        self.AddCheckbox(ID_DLGMNGR_BASE_DATA_SET_ENABLED + idx, c4d.BFH_CENTER, initw=0, inith=0, name='')

    def CreateLayoutGroupControl(self):
        if self.GroupBegin(ID_DLGMNGR_GROUP_CONTROL, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=1):
            CreateLayoutAddGroupBar(self, 'Tags')
            scrollFlags = c4d.SCROLLGROUP_VERT | c4d.SCROLLGROUP_AUTOVERT | c4d.SCROLLGROUP_NOVGAP
            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=1, inith=80):
                if self.ScrollGroupBegin(ID_DLGMNGR_SCROLL_LOCAL_DATA, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, scrollFlags, initw=0, inith=0):
                    if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=11):
                        self.GroupBorderSpace(10, 2, 0, 0)
                        self.AddButton(ID_DLGMNGR_TAGS_POPUP, c4d.BFH_LEFT, initw=WIDTH_ADD_BUTTON, inith=0, name='+')
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=30, name='')
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Tag')
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=20, name='') # spacer
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=30, name='')
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Object')
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=20, name='') # spacer
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=150, name='Rig Type')
                        self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=100, name='Live/Clip')
                        self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=100, name='Actor')
                        self.AddStaticText(0, c4d.BFH_RIGHT, initw=23, name='Sel')
                        if self._tags is not None and len(self._tags) > 0:
                            for idxTag, tag in enumerate(self._tags):
                                self.CreateLayoutRowControl(tag, idxTag)
                        else:
                            self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='No Rokoko tags found in current document.')
                    self.GroupEnd()
                self.GroupEnd()
            self.GroupEnd()
            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_BOTTOM, title='', cols=6):
                self.GroupBorderSpace(10, 0, 0, 0)
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Project Scale')
                self.AddEditNumberArrows(ID_DLGMNGR_PROJECT_SCALE, c4d.BFH_LEFT, initw=60)
                self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=30, name='') # spacer
                self.AddButton(ID_DLGMNGR_SELECT_ALL_TAGS, c4d.BFH_RIGHT, initw=150, inith=0, name='Select All')
                self.AddButton(ID_DLGMNGR_DESELECT_ALL_TAGS, c4d.BFH_RIGHT, initw=150, inith=0, name='Deselect All')
                self.AddButton(ID_DLGMNGR_INVERT_SELECTION, c4d.BFH_RIGHT, initw=150, inith=0, name='Invert Selection')
            self.GroupEnd()
        self.GroupEnd()

    def UpdateLayoutGroupControl(self):
        self.LayoutFlushGroup(ID_DLGMNGR_GROUP_CONTROL)
        self.CreateLayoutGroupControl()
        self.LayoutChanged(ID_DLGMNGR_GROUP_CONTROL)


    def CreateLayoutGroupLive(self):
        if self.GroupBegin(ID_DLGMNGR_GROUP_PLAYER, flags=c4d.BFH_SCALEFIT | c4d.BFV_FIT, title='', cols=1):
            CreateLayoutAddGroupBar(self, 'Player')
            wButton = c4d.gui.SizePix(200)
            hButton = c4d.gui.SizePix(50)
            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=2):
                self.GroupBorderSpace(10, 2, 0, 0)
                self.AddButton(ID_DLGMNGR_PLAYER_START_STOP, c4d.BFH_LEFT, initw=150, name='Start Player')
                self.AddRadioGroup(ID_DLGMNGR_PLAYER_TAG_SELECTION, c4d.BFH_LEFT, rows=1)
                self.AddChild(ID_DLGMNGR_PLAYER_TAG_SELECTION, 0, 'All')
                self.AddChild(ID_DLGMNGR_PLAYER_TAG_SELECTION, 1, 'Selected')
                self.AddChild(ID_DLGMNGR_PLAYER_TAG_SELECTION, 2, 'Live')
                self.AddChild(ID_DLGMNGR_PLAYER_TAG_SELECTION, 3, 'Clips')
            self.GroupEnd()
            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=1):
                self.GroupBorderSpace(10, 0, 0, 0)
                if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=2):
                    self.AddStaticText(ID_DLGMNGR_PLAYER_ACTIVE_TAGS_LABEL, c4d.BFH_LEFT, initw=0, name='Active Tags:')
                    self.AddStaticText(ID_DLGMNGR_PLAYER_ACTIVE_TAGS, c4d.BFH_SCALEFIT, initw=0, name='None')
                self.GroupEnd()
                if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=5):
                    self.AddEditSlider(ID_DLGMNGR_PLAYER_CURRENT_FRAME, flags=c4d.BFH_SCALEFIT)
                    CreateLayoutAddBitmapButton(self, ID_DLGMNGR_PLAYER_FIRST_FRAME, idIcon1=12501, tooltip='First Frame', button=True, toggle=False, flags=c4d.BFH_RIGHT|c4d.BFV_CENTER)
                    self._bitmapButtonPlayPause = CreateLayoutAddBitmapButton(self, ID_DLGMNGR_PLAYER_PAUSE, idIcon1=12412, idIcon2=12002, tooltip='Play/Pause', button=True, toggle=True, flags=c4d.BFH_RIGHT|c4d.BFV_CENTER)
                    CreateLayoutAddBitmapButton(self, ID_DLGMNGR_PLAYER_SYNC_WITH_LIVE, idIcon1=465001024, tooltip='Play Live', button=True, toggle=False, flags=c4d.BFH_RIGHT|c4d.BFV_CENTER)
                    CreateLayoutAddBitmapButton(self, ID_DLGMNGR_PLAYER_LAST_FRAME, idIcon1=12502, tooltip='Last Frame', button=True, toggle=False, flags=c4d.BFH_RIGHT|c4d.BFV_CENTER)
                self.GroupEnd()
                if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=1):
                    self.AddButton(ID_DLGMNGR_PLAYER_SAVE, c4d.BFH_SCALEFIT | c4d.BFV_CENTER, initw=0, inith=hButton, name='')
                self.GroupEnd()
                if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=6):
                    self.AddStaticText(ID_DLGMNGR_PLAYER_BUFFERING_LABEL, c4d.BFH_LEFT, initw=0, name='Buffering:')
                    self.AddSlider(ID_DLGMNGR_PLAYER_BUFFERING, flags=c4d.BFH_LEFT, initw=200)
                    self.Enable(ID_DLGMNGR_PLAYER_BUFFERING, False)
                    self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=0, name='')
                    self.AddCheckbox(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT, c4d.BFH_RIGHT|c4d.BFH_SCALE, initw=0, inith=0, name='Animate Document')
                    self.AddStaticText(0, c4d.BFH_RIGHT|c4d.BFH_SCALE, initw=0, name='Playback rate:')
                    self.AddComboBox(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, c4d.BFH_RIGHT, initw=0)
                    self.AddChild(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, 1, '1:1 (~60FPS)')
                    self.AddChild(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, 2, '1:2 (~30FPS)')
                    self.AddChild(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, 3, '1:3 (~20FPS)')
                    self.AddChild(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, 4, '1:4 (~15FPS)')
                    self.AddChild(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, 6, '1:6 (~10FPS)')
                    self.AddChild(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, 12, '1:12 (~5FPS)')
                    self.AddChild(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, 30, '1:30 (~2FPS)')
                    self.AddChild(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, 60, '1:60 (~1FPS)')
                self.GroupEnd()
            self.GroupEnd()
        self.GroupEnd()

    def UpdateLayoutGroupLive(self):
        self.LayoutFlushGroup(ID_DLGMNGR_GROUP_PLAYER)
        self.CreateLayoutGroupLive()
        self.LayoutChanged(ID_DLGMNGR_GROUP_PLAYER)

    def CreateLayoutGroupCommandAPI(self):
        if self.GroupBegin(ID_DLGMNGR_GROUP_COMMAND_API, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=1):
            CreateLayoutAddGroupBar(self, 'Command API')
            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=4):
                self.GroupBorderSpace(10, 2, 0, 0)
                CreateLayoutAddBitmapButton(self, ID_DLGMNGR_COMMANDAPI_START_RECORDING, idIcon1=PLUGIN_ID_COMMAND_API_ICON_RECORD_START, \
                                            tooltip='Start Recording in Studio', button=True, toggle=False, flags=c4d.BFH_SCALEFIT)
                CreateLayoutAddBitmapButton(self, ID_DLGMNGR_COMMANDAPI_STOP_RECORDING, idIcon1=PLUGIN_ID_COMMAND_API_ICON_RECORD_STOP, \
                                            tooltip='Stop Recording in Studio', button=True, toggle=False, flags=c4d.BFH_SCALEFIT)
                CreateLayoutAddBitmapButton(self, ID_DLGMNGR_COMMANDAPI_CALIBRATE_ALL_SUITS, idIcon1=PLUGIN_ID_COMMAND_API_ICON_CALIBRATE_SUIT, \
                                            tooltip='Start Calibration of all Smartsuits in Studio', button=True, toggle=False, flags=c4d.BFH_SCALEFIT)
                CreateLayoutAddBitmapButton(self, ID_DLGMNGR_COMMANDAPI_RESET_ALL_SUITS, idIcon1=PLUGIN_ID_COMMAND_API_ICON_RESTART_SUIT, \
                                            tooltip='Restart All Smartsuits', button=True, toggle=False, flags=c4d.BFH_SCALEFIT)
            self.GroupEnd()
        self.GroupEnd()

    def UpdateLayoutGroupCommandAPI(self):
        self.LayoutFlushGroup(ID_DLGMNGR_GROUP_COMMAND_API)
        self.CreateLayoutGroupCommandAPI()
        self.LayoutChanged(ID_DLGMNGR_GROUP_COMMAND_API)

    def CreateLayout(self):
        self.SetTitle('Rokoko Studio Live')
        self.CreateLayoutInMenu()
        if self.GroupBegin(ID_DLGMNGR_GROUP_MAIN, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=1):
            self.GroupBorderSpace(5, 5, 10, 5)
            self._quickTab = CreateLayoutAddQuickTab(self, ID_DLGMNGR_TABS)
            self._quickTab.AppendString(ID_DLGMNGR_GROUP_CONNECTIONS, 'Connection', GetPref(ID_DLGMNGR_GROUP_CONNECTIONS))
            self._quickTab.AppendString(ID_DLGMNGR_GROUP_GLOBAL_DATA, 'Global Clips', GetPref(ID_DLGMNGR_GROUP_GLOBAL_DATA))
            self._quickTab.AppendString(ID_DLGMNGR_GROUP_LOCAL_DATA, 'Project Clips', GetPref(ID_DLGMNGR_GROUP_LOCAL_DATA))
            self._quickTab.AppendString(ID_DLGMNGR_GROUP_CONTROL, 'Tags', GetPref(ID_DLGMNGR_GROUP_CONTROL))
            self._quickTab.AppendString(ID_DLGMNGR_GROUP_PLAYER, 'Player', GetPref(ID_DLGMNGR_GROUP_PLAYER))
            self._quickTab.AppendString(ID_DLGMNGR_GROUP_COMMAND_API, 'Command API', GetPref(ID_DLGMNGR_GROUP_COMMAND_API))
            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=1):
                self.GroupSpace(0, 15)
                self.CreateLayoutGroupConnections()
                self.CreateLayoutGroupDataSet(local=False)
                self.CreateLayoutGroupDataSet(local=True)
                self.CreateLayoutGroupControl()
                self.CreateLayoutGroupLive()
                self.CreateLayoutGroupCommandAPI()
            self.GroupEnd()
        self.GroupEnd()
        self.CreateLayoutAddMenu()
        self.HideElement(ID_DLGMNGR_GROUP_CONNECTIONS, True)
        self.HideElement(ID_DLGMNGR_GROUP_GLOBAL_DATA, True)
        self.HideElement(ID_DLGMNGR_GROUP_LOCAL_DATA, True)
        self.HideElement(ID_DLGMNGR_GROUP_CONTROL, True)
        self.HideElement(ID_DLGMNGR_GROUP_PLAYER, True)
        self.HideElement(ID_DLGMNGR_GROUP_COMMAND_API, True)
        return True

    def UpdateGroupVisibility(self, forcePlayerOpen=False):
        SetPref(ID_DLGMNGR_GROUP_CONNECTIONS, self._quickTab.IsSelected(ID_DLGMNGR_GROUP_CONNECTIONS))
        SetPref(ID_DLGMNGR_GROUP_GLOBAL_DATA, self._quickTab.IsSelected(ID_DLGMNGR_GROUP_GLOBAL_DATA))
        SetPref(ID_DLGMNGR_GROUP_LOCAL_DATA, self._quickTab.IsSelected(ID_DLGMNGR_GROUP_LOCAL_DATA))
        SetPref(ID_DLGMNGR_GROUP_CONTROL, self._quickTab.IsSelected(ID_DLGMNGR_GROUP_CONTROL))
        if forcePlayerOpen:
            SetPref(ID_DLGMNGR_GROUP_PLAYER, True)
            self._quickTab.Select(ID_DLGMNGR_GROUP_PLAYER, True)
        else:
            SetPref(ID_DLGMNGR_GROUP_PLAYER, self._quickTab.IsSelected(ID_DLGMNGR_GROUP_PLAYER))
        SetPref(ID_DLGMNGR_GROUP_COMMAND_API, self._quickTab.IsSelected(ID_DLGMNGR_GROUP_COMMAND_API))
        self.HideElement(ID_DLGMNGR_GROUP_CONNECTIONS, not GetPref(ID_DLGMNGR_GROUP_CONNECTIONS))
        self.HideElement(ID_DLGMNGR_GROUP_CONNECTION_DATA, not IsConnected())
        self.HideElement(ID_DLGMNGR_GROUP_CONNECTION_DATA_CONTENT, not IsConnected())
        self.HideElement(ID_DLGMNGR_GROUP_GLOBAL_DATA, not GetPref(ID_DLGMNGR_GROUP_GLOBAL_DATA))
        self.HideElement(ID_DLGMNGR_GROUP_LOCAL_DATA, not GetPref(ID_DLGMNGR_GROUP_LOCAL_DATA))
        self.HideElement(ID_DLGMNGR_GROUP_CONTROL, not GetPref(ID_DLGMNGR_GROUP_CONTROL))
        self.HideElement(ID_DLGMNGR_GROUP_PLAYER, not GetPref(ID_DLGMNGR_GROUP_PLAYER))
        self.HideElement(ID_DLGMNGR_GROUP_COMMAND_API, not GetPref(ID_DLGMNGR_GROUP_COMMAND_API))
        self.LayoutChanged(ID_DLGMNGR_GROUP_MAIN)

    def EnableLiveButtons(self):
        live = g_thdListener._receive
        allowWhileNotLive = not live and (self._tags is not None and len(self._tags) > 0)
        isConnected = IsConnected()
        self.Enable(ID_DLGMNGR_SELECT_ALL_TAGS, allowWhileNotLive)
        self.Enable(ID_DLGMNGR_DESELECT_ALL_TAGS, allowWhileNotLive)
        self.Enable(ID_DLGMNGR_INVERT_SELECTION, allowWhileNotLive)
        if live:
            self.SetString(ID_DLGMNGR_PLAYER_START_STOP, 'Stop Player')
        else:
            self.SetString(ID_DLGMNGR_PLAYER_START_STOP, 'Start Player')
        self.Enable(ID_DLGMNGR_PLAYER_TAG_SELECTION, allowWhileNotLive)
        self.Enable(ID_DLGMNGR_PLAYER_BUFFERING_LABEL, not allowWhileNotLive)
        self.Enable(ID_DLGMNGR_PLAYER_ACTIVE_TAGS_LABEL, not allowWhileNotLive)
        self.Enable(ID_DLGMNGR_CONNECTION_POPUP, not live)
        tagsLive = g_thdListener.GetTagConsumers()
        anyLiveDataSet = False
        if self._tags is not None:
            idConnected = GetConnectedDataSetId()
            for idxTag, tag in enumerate(self._tags):
                self.Enable(ID_DLGMNGR_BASE_TAG_RIG_TYPES + idxTag, allowWhileNotLive)
                self.Enable(ID_DLGMNGR_BASE_DATA_SET_ENABLED + idxTag, allowWhileNotLive)
                if not tag.IsAlive():
                    continue
                if tag not in tagsLive:
                    self.Enable(ID_DLGMNGR_BASE_TAG_DATA_SETS + idxTag, allowWhileNotLive)
                    self.Enable(ID_DLGMNGR_BASE_TAG_ACTORS + idxTag, allowWhileNotLive)
                if tag[ID_TAG_DATA_SET] == idConnected and tag in tagsLive:
                    anyLiveDataSet = True
        self.Enable(ID_DLGMNGR_PLAYER_SAVE, live and isConnected and anyLiveDataSet)
        self.Enable(ID_DLGMNGR_PLAYER_FIRST_FRAME, live)
        self.Enable(ID_DLGMNGR_PLAYER_LAST_FRAME, live)
        self._bitmapButtonPlayPause.SetToggleState(g_thdListener._play)
        self.Enable(ID_DLGMNGR_PLAYER_PAUSE, live)
        self.Enable(ID_DLGMNGR_PLAYER_CURRENT_FRAME, live)
        self.Enable(ID_DLGMNGR_PLAYER_ACTIVE_TAGS, live)
        self.Enable(ID_DLGMNGR_PLAYER_SYNC_WITH_LIVE, live and not g_thdListener._inSync)
        if self._buttonRecordState:
            self.SetString(ID_DLGMNGR_PLAYER_SAVE, 'Stop Recording...')
        else:
            self.SetString(ID_DLGMNGR_PLAYER_SAVE, 'Start Recording')

    def EnableDialog(self, enable):
        self.Enable(ID_DLGMNGR_CONNECTIONS_IN_MENU, enable)
        self.Enable(ID_DLGMNGR_GROUP_MAIN, enable)


    def InitValues(self):
        tagsLive = g_thdListener.GetTagConsumers()
        bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
        if self._tags is not None and len(self._tags) > 0:
            for idxTag, tag in enumerate(self._tags):
                if not tag.IsAlive():
                    continue
                self.SetBool(ID_DLGMNGR_BASE_DATA_SET_ENABLED + idxTag, tag[ID_TAG_SELECTED_IN_MANAGER])
                if tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR:
                    pass # TODO copy body and hands enabling
                self.SetBool(ID_DLGMNGR_BASE_DATA_SET_ENABLED + idxTag, tag[ID_TAG_SELECTED_IN_MANAGER])
                self.SetInt32(ID_DLGMNGR_BASE_TAG_RIG_TYPES + idxTag, tag[ID_TAG_RIG_TYPE])
                self.SetInt32(ID_DLGMNGR_BASE_TAG_DATA_SETS + idxTag, tag.GetDataInstance().GetInt32(ID_TAG_DATA_SET))
                self.SetInt32(ID_DLGMNGR_BASE_TAG_ACTORS + idxTag, tag.GetDataInstance().GetInt32(ID_TAG_ACTORS))
        playbackRate = GetPref(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED)
        if playbackRate is None:
            SetPref(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, 2)
            playbackRate = 2
        self.SetInt32(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, playbackRate)
        idxFrameCurrent, numFrames = g_thdListener.GetCurrentFrameNumber()
        maxSlider = (1 + numFrames // 100) * 100
        self.SetInt32(ID_DLGMNGR_PLAYER_CURRENT_FRAME, idxFrameCurrent, min=0, max=maxSlider, min2=0, max2=maxSlider)
        playChoice = GetPref(ID_DLGMNGR_PLAYER_TAG_SELECTION)
        if playChoice is None:
            SetPref(ID_DLGMNGR_PLAYER_TAG_SELECTION, 0)
            playChoice = 0
        self.SetInt32(ID_DLGMNGR_PLAYER_TAG_SELECTION, playChoice)
        animateDocument = GetPref(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT)
        if animateDocument is None:
            SetPref(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT, False)
            animateDocument = False
        self.SetInt32(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT, animateDocument)
        self.SetFloat(ID_DLGMNGR_PROJECT_SCALE, GetProjectScale(), step=0.1, min=0.0001)
        idxConnection = 0
        idConnected = GetConnectedDataSetId()
        for id, bcConnection in bcConnections:
            self.SetBool(ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT + idxConnection, bcConnection[ID_BC_DATASET_LIVE_AUTOCONNECT])
            idIcon = 465003508
            if bcConnection.GetId() == idConnected:
                statusConnection = g_thdListener.GetConnectionStatus()
                if statusConnection == 1:
                    idIcon = 465001743
                elif statusConnection == 2:
                    idIcon = 465001740
                self.UpdateLayoutGroupConnectedDataSet()
                self.SetString(ID_DLGMNGR_BASE_CONNECTION_CONNECT + idxConnection, 'Disconnect')
            else:
                self.SetString(ID_DLGMNGR_BASE_CONNECTION_CONNECT + idxConnection, 'Connect')
            self.Enable(ID_DLGMNGR_BASE_CONNECTION_CONNECT + idxConnection, not self._connecting)
            icon = c4d.gui.GetIcon(idIcon)
            bmpIcon = icon['bmp'].GetClonePart(icon['x'], icon['y'], icon['w'], icon['h'])
            self._bitmapButtonsPerConnectionStatus[idxConnection].SetImage(bmpIcon)
            idxConnection += 1
        if len(tagsLive):
            namesActiveTags = ''
            for tag in tagsLive:
                namesActiveTags += tag.GetName() + ', '
            namesActiveTags = namesActiveTags[:-2]
            self.SetString(ID_DLGMNGR_PLAYER_ACTIVE_TAGS, namesActiveTags)
        else:
            self.SetString(ID_DLGMNGR_PLAYER_ACTIVE_TAGS, 'None')
        self.Enable(ID_DLGMNGR_CONNECTIONS_IN_MENU, not self._connecting)
        self.UpdateGroupVisibility()
        self.UpdateLayoutInMenu()
        self.EnableLiveButtons()
        return True


    _lastEvent = 0
    def MessageBfmAction(self, msg):
        if msg[c4d.BFM_ACTION_ID] != ID_DLGMNGR_PLAYER_CURRENT_FRAME:
            return
        self.CommandPause(force=True)
        now = c4d.GeGetTimer()
        if now - self._lastEvent <= 50:
            return
        idxFrameCurrent = int(msg[c4d.BFM_ACTION_VALUE])
        g_thdListener.FlushTagConsumers()
        if GetPref(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT):
            doc = c4d.documents.GetActiveDocument()
            tMax = doc.GetMaxTime().Get()
            tDispatch = 0.01667 * idxFrameCurrent
            t = c4d.BaseTime(tDispatch % tMax)
            doc.SetTime(t)
        g_thdListener.DispatchFrame(idxFrameCurrent, event=False)
        c4d.DrawViews(c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW | c4d.DRAWFLAGS_NO_THREAD)
        self._lastEvent = now

    def Message(self, msg, result):
        idMsg = msg.GetId()
        if idMsg == c4d.BFM_ACTION:
            self.MessageBfmAction(msg)
        return c4d.gui.GeDialog.Message(self, msg, result)


    def CoreMessageUpdateTags(self):
        self._tags = GetTagList()
        self.UpdateLayoutGroupDataSet(local=True)
        self.UpdateLayoutGroupControl()
        self.InitValues()

    def CoreMessageUpdateTagParams(self):
        self.UpdateLayoutGroupControl()
        self.InitValues()

    _cntBuffering = 0
    def CoreMessageBufferPulse(self):
        if not g_thdListener._receive:
            return
        self._cntBuffering = (self._cntBuffering + 1) % 10
        self.SetInt32(ID_DLGMNGR_PLAYER_BUFFERING, self._cntBuffering, min=0, max=9, min2=0, max2=9)
        self.SetInt32(ID_DLGMNGR_PLAYER_BUFFERING_IN_MENU, self._cntBuffering % 5, min=0, max=4, min2=0, max2=4)

    def CoreMessageCurrentFrameNumber(self, msg):
        if not g_thdListener._play:
            return
        if g_thdListener._receive:
            idxFrameCurrent = GetCoreMessageParam23(msg)
            numFrames = GetCoreMessageParam23(msg, id=c4d.BFM_CORE_PAR2)
        else:
            idxFrameCurrent = 0
            numFrames = 0
        maxSlider = (1 + numFrames // 100) * 100
        self.SetInt32(ID_DLGMNGR_PLAYER_CURRENT_FRAME, idxFrameCurrent, min=0, max=maxSlider, min2=0, max2=maxSlider)

    def CoreMessageConnectionStatusChange(self):
        self._connecting = False
        self.InitValues()
        self.UpdateLayoutInMenu()

    def CoreMessagePlayerStatusChange(self):
        self.InitValues()
        self.SetInt32(ID_DLGMNGR_PLAYER_BUFFERING, 0, min=0, max=9, min2=0, max2=9)
        self.SetInt32(ID_DLGMNGR_PLAYER_BUFFERING_IN_MENU, 0, min=0, max=4, min2=0, max2=4)

    def CoreMessage(self, id, msg):
        if id == PLUGIN_ID_COREMESSAGE_MANAGER:
            subId = GetCoreMessageParam23(msg)
            if subId == CM_SUBID_MANAGER_UPDATE_TAGS:
                self.CoreMessageUpdateTags()
            elif subId == CM_SUBID_MANAGER_UPDATE_TAG_PARAMS:
                self.CoreMessageUpdateTagParams()
            elif subId == CM_SUBID_MANAGER_OPEN_PLAYER:
                self.UpdateGroupVisibility(forcePlayerOpen=True)
            elif subId == CM_SUBID_MANAGER_PLAYBACK_STATUS_CHANGE:
                self.CoreMessagePlayerStatusChange()
            elif subId == CM_SUBID_MANAGER_BUFFER_PULSE:
                self.CoreMessageBufferPulse()
            return True
        elif id == PLUGIN_ID_COREMESSAGE_MANAGER_CURRENT_FRAME_NUMBER:
            self.CoreMessageCurrentFrameNumber(msg)
            return True
        elif id == PLUGIN_ID_COREMESSAGE_CONNECTION:
            subId = GetCoreMessageParam23(msg)
            if subId == CM_SUBID_CONNECTION_STATUS_CHANGE:
                self.CoreMessageConnectionStatusChange()
            elif subId == CM_SUBID_CONNECTION_LIVE_DATA_CHANGE:
                self.CoreMessageUpdateTagParams()
            return True
        return c4d.gui.GeDialog.CoreMessage(self, id, msg)


    def AskClose(self):
        if self._dlgChild is not None and self._dlgChild.IsOpen():
            c4d.gui.MessageDialog('Save Dialog is still open.', c4d.GEMB_ICONEXCLAMATION)
            return True
        if g_thdListener._receive:
            result = c4d.gui.MessageDialog('Player is still running.\nDialog will be closed.\nStop player?\n', c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_YESNOCANCEL)
            if result == c4d.GEMB_R_YES:
                self.CommandPlayerExit()
            elif result == c4d.GEMB_R_CANCEL:
                return True
        return False


    def CommandConnectionsPopup(self):
        dlgEdit = DialogEditConnection(None)
        resultOpen = dlgEdit.Open(c4d.DLG_TYPE_MODAL_RESIZEABLE)
        if resultOpen == False:
            return
        result, bcConnectionNew = dlgEdit.GetResult()
        if result == False:
            return
        GetPrefsContainer(ID_BC_CONNECTIONS).SetContainer(bcConnectionNew.GetId(), bcConnectionNew.GetClone(c4d.COPYFLAGS_NONE))
        self.UpdateLayoutGroupConnections()
        self.InitValues()
        self.UpdateLayoutInMenu()

    def CommandConnectionPopup(self, id):
        idxConnection = id - ID_DLGMNGR_BASE_CONNECTION_POPUP
        bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
        idxConnected = bcConnections.FindIndex(GetConnectedDataSetId())
        bcMenu = c4d.BaseContainer()
        idConnected = GetConnectedDataSetId()
        idConnection = bcConnections.GetIndexId(idxConnection)
        if idConnected == idConnection:
            bcMenu.InsData(ID_SUBMENU_CONNECTION_CREATE_SCENE, 'Create Scene')
            bcMenu.InsData(0, '')
            bcMenu.InsData(ID_SUBMENU_CONNECTION_EDIT, 'Edit...&d&')
            bcMenu.InsData(0, '')
            bcMenu.InsData(ID_SUBMENU_CONNECTION_CONNECT, 'Disonnect')
        else:
            bcMenu.InsData(ID_SUBMENU_CONNECTION_CONNECT, 'Connect')
            bcMenu.InsData(0, '')
            bcMenu.InsData(ID_SUBMENU_CONNECTION_EDIT, 'Edit...')
            #bcMenu.InsData(ID_SUBMENU_CONNECTION_REMOVE, 'Remove')
        result = c4d.gui.ShowPopupDialog(cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)
        if result == ID_SUBMENU_CONNECTION_CONNECT:
            self.Connect(idxConnection)
        elif result == ID_SUBMENU_CONNECTION_EDIT:
            self.EditConnection(idxConnection)
        elif result == ID_SUBMENU_CONNECTION_REMOVE:
            self.RemoveConnection(idxConnection)
        elif result == ID_SUBMENU_CONNECTION_CREATE_SCENE:
            self.InsertRokokoStudioScene()
        elif result == 0:
            pass # menu canceled
        else:
            print('ERROR: Submenu Connection unknown command', result)

    def Connect(self, idxConnection):
        self._connecting = True
        if g_thdListener._receive:
            self.CommandPlayerExit()
        if idxConnection != 999999:
            bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
            idConnection = bcConnections.GetIndexId(idxConnection)
        else:
            idConnection = -1
        idConnected = GetConnectedDataSetId()
        if idConnected == idConnection:
            idConnected = -1
        else:
            if idConnected != -1 and idConnection != -1:
                c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_DISCONNECT)
            idConnected = idConnection
        if idConnected == -1:
            self.CommandPlayerExit()
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_DISCONNECT)
        else:
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_CONNECT, idConnected)
        self.InitValues()
        self.UpdateLayoutInMenu()
        self.EnableLiveButtons()

    def RemoveConnection(self, idxConnection):
        id = GetPrefsContainer(ID_BC_CONNECTIONS).GetIndexId(idxConnection)
        RemoveConnection(id)
        self.UpdateLayoutGroupConnections()
        self.InitValues()
        self.UpdateLayoutInMenu()

    def EditConnection(self, idxConnection):
        id = GetPrefsContainer(ID_BC_CONNECTIONS).GetIndexId(idxConnection)
        bcConnection = GetPrefsContainer(ID_BC_CONNECTIONS).GetContainer(id)
        idConnection = bcConnection.GetId()
        dlgEdit = DialogEditConnection(bcConnection)
        resultOpen = dlgEdit.Open(c4d.DLG_TYPE_MODAL_RESIZEABLE)
        if resultOpen == False:
            return
        result, bcConnectionNew = dlgEdit.GetResult()
        if result == False:
            return
        RemoveConnection(idConnection)
        GetPrefsContainer(ID_BC_CONNECTIONS).SetContainer(bcConnectionNew.GetId(), bcConnectionNew)
        self.UpdateLayoutGroupConnections()
        self.InitValues()
        self.UpdateLayoutInMenu()

    def CommandGlobalDataPopup(self):
        disableItem = ''
        if g_thdListener._receive:
            disableItem = '&d&'
        bcMenu = c4d.BaseContainer()
        bcMenu.InsData(ID_SUBMENU_GLOBAL_DATA_ADD_FILE, 'Add File...')
        bcMenu.InsData(ID_SUBMENU_GLOBAL_DATA_ADD_FOLDER, 'Add Folder...')
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_GLOBAL_DATA_REMOVE_ALL, 'Remove All' + disableItem)
        bcMenu.InsData(ID_SUBMENU_GLOBAL_DATA_DELETE_ALL, 'Delete All...' + disableItem)
        result = c4d.gui.ShowPopupDialog(cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)
        if result == ID_SUBMENU_GLOBAL_DATA_ADD_FILE:
            self.AddDataSet(local=False, folder=False)
        elif result == ID_SUBMENU_GLOBAL_DATA_ADD_FOLDER:
            self.AddDataSet(local=False, folder=True)
        elif result == ID_SUBMENU_GLOBAL_DATA_REMOVE_ALL:
            self.RemoveDataSet(local=False, all=True)
        elif result == ID_SUBMENU_GLOBAL_DATA_DELETE_ALL:
            self.RemoveDataSet(local=False, all=True, delete=True)
        elif result == 0:
            pass # menu canceled
        else:
            print('ERROR: Submenu Global Data unknown command', result)

    def CommandGlobalDataSetPopup(self, id):
        idxGlobalData = id - ID_DLGMNGR_BASE_GLOBAL_DATA_POPUP
        disableItem = ''
        if g_thdListener._receive:
            disableItem = '&d&'
        bcMenu = c4d.BaseContainer()
        bcMenu.InsData(ID_SUBMENU_GLOBAL_DATA_SET_CREATE_SCENE, 'Create Scene')
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_GLOBAL_DATA_SET_EDIT, 'Edit...' + disableItem)
        bcMenu.InsData(ID_SUBMENU_GLOBAL_DATA_SET_OPEN_DIRECTORY, 'Open Directory...')
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_GLOBAL_DATA_SET_COPY_LOCAL, 'Copy to Project Clips')
        bcMenu.InsData(ID_SUBMENU_GLOBAL_DATA_SET_MOVE_LOCAL, 'Move to Project Clips' + disableItem)
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_GLOBAL_DATA_SET_REMOVE, 'Remove' + disableItem)
        bcMenu.InsData(ID_SUBMENU_GLOBAL_DATA_SET_DELETE, 'Delete...' + disableItem)
        result = c4d.gui.ShowPopupDialog(cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)
        if result == ID_SUBMENU_GLOBAL_DATA_SET_COPY_LOCAL:
            self.DataSetChangeGlobalLocal(idxGlobalData, local=False)
        elif result == ID_SUBMENU_GLOBAL_DATA_SET_MOVE_LOCAL:
            self.DataSetChangeGlobalLocal(idxGlobalData, local=False, move=True)
        elif result == ID_SUBMENU_GLOBAL_DATA_SET_EDIT:
            self.EditDataSet(idxGlobalData, local=False)
        elif result == ID_SUBMENU_GLOBAL_DATA_SET_REMOVE:
            self.RemoveDataSet(local=False, idx=idxGlobalData)
        elif result == ID_SUBMENU_GLOBAL_DATA_SET_DELETE:
            self.RemoveDataSet(local=False, idx=idxGlobalData, delete=True)
        elif result == ID_SUBMENU_GLOBAL_DATA_SET_CREATE_SCENE:
            self.CreateSceneForDataSet(idxGlobalData, local=False)
        elif result == ID_SUBMENU_GLOBAL_DATA_SET_OPEN_DIRECTORY:
            self.DataSetOpenDirectory(local=False, idxDataSet=idxGlobalData)
        elif result == 0:
            pass # menu canceled
        else:
            print('ERROR: Submenu Global Data Set unknown command', result)

    def CommandLocalDataPopup(self):
        disableItem = ''
        if g_thdListener._receive:
            disableItem = '&d&'
        bcMenu = c4d.BaseContainer()
        bcMenu.InsData(ID_SUBMENU_LOCAL_DATA_ADD_FILE, 'Add File...')
        bcMenu.InsData(ID_SUBMENU_LOCAL_DATA_ADD_FOLDER, 'Add Folder...')
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_LOCAL_DATA_REMOVE_ALL, 'Remove All' + disableItem)
        bcMenu.InsData(ID_SUBMENU_LOCAL_DATA_DELETE_ALL, 'Delete All...' + disableItem)
        result = c4d.gui.ShowPopupDialog(cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)
        if result == ID_SUBMENU_LOCAL_DATA_ADD_FILE:
            self.AddDataSet(local=True, folder=False)
        elif result == ID_SUBMENU_LOCAL_DATA_ADD_FOLDER:
            self.AddDataSet(local=True, folder=True)
        elif result == ID_SUBMENU_LOCAL_DATA_REMOVE_ALL:
            self.RemoveDataSet(local=True, all=True)
        elif result == ID_SUBMENU_LOCAL_DATA_DELETE_ALL:
            self.RemoveDataSet(local=True, all=True, delete=True)
        elif result == 0:
            pass # menu canceled
        else:
            print('ERROR: Submenu Local Data unknown command', result)

    def CommandLocalDataSetPopup(self, id):
        idxLocalData = id - ID_DLGMNGR_BASE_LOCAL_DATA_POPUP
        disableItem = ''
        if g_thdListener._receive:
            disableItem = '&d&'
        bcMenu = c4d.BaseContainer()
        bcMenu.InsData(ID_SUBMENU_LOCAL_DATA_SET_CREATE_SCENE, 'Create Scene')
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_LOCAL_DATA_SET_EDIT, 'Edit...' + disableItem)
        bcMenu.InsData(ID_SUBMENU_LOCAL_DATA_SET_OPEN_DIRECTORY, 'Open Directory...')
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_LOCAL_DATA_SET_COPY_GLOBAL, 'Copy to Global Clips')
        bcMenu.InsData(ID_SUBMENU_LOCAL_DATA_SET_MOVE_GLOBAL, 'Move to Global Clips' + disableItem)
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_LOCAL_DATA_SET_REMOVE, 'Remove' + disableItem)
        bcMenu.InsData(ID_SUBMENU_LOCAL_DATA_SET_DELETE, 'Delete...' + disableItem)
        result = c4d.gui.ShowPopupDialog(cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)
        if result == ID_SUBMENU_LOCAL_DATA_SET_COPY_GLOBAL:
            self.DataSetChangeGlobalLocal(idxLocalData, local=True)
        elif result == ID_SUBMENU_LOCAL_DATA_SET_MOVE_GLOBAL:
            self.DataSetChangeGlobalLocal(idxLocalData, local=True, move=True)
        elif result == ID_SUBMENU_LOCAL_DATA_SET_EDIT:
            self.EditDataSet(idxLocalData, local=True)
        elif result == ID_SUBMENU_LOCAL_DATA_SET_REMOVE:
            self.RemoveDataSet(local=True, idx=idxLocalData)
        elif result == ID_SUBMENU_LOCAL_DATA_SET_DELETE:
            self.RemoveDataSet(local=True, idx=idxLocalData, delete=True)
        elif result == ID_SUBMENU_LOCAL_DATA_SET_CREATE_SCENE:
            self.CreateSceneForDataSet(idxLocalData, local=True)
        elif result == ID_SUBMENU_LOCAL_DATA_SET_OPEN_DIRECTORY:
            self.DataSetOpenDirectory(local=True, idxDataSet=idxLocalData)
        elif result == 0:
            pass # menu canceled
        else:
            print('ERROR: Submenu Local Data Set unknown command', result)

    def DataSetChangeGlobalLocal(self, idxDataSet, local, move=False):
        if local:
            bcDataSets = GetLocalDataSets()
        else:
            bcDataSets = GetPrefsContainer(ID_BC_DATA_SETS)
        id = bcDataSets.GetIndexId(idxDataSet)
        bcDataSet = bcDataSets.GetContainer(id)
        self.DataSetChangeGlobalLocalBC(bcDataSet, move=move)

    def DataSetChangeGlobalLocalBC(self, bcDataSet, move=False):
        isLocal = bcDataSet[ID_BC_DATASET_IS_LOCAL]
        filename = bcDataSet[ID_BC_DATASET_FILENAME]
        idDataSet = bcDataSet.GetId()
        bcDataSetNew = bcDataSet.GetClone(c4d.COPYFLAGS_NONE)
        isLocalNew = not isLocal
        filenameNew = filename
        pathDoc = c4d.documents.GetActiveDocument().GetDocumentPath()
        if isLocalNew:
            filenameDst = filename
            filenameNew = filename
            if pathDoc is not None and len(pathDoc) > 1:
                _, filenameDst = os.path.split(filename)
                filenameNew = os.path.join('.', filenameDst)
                filenameDst = os.path.join(pathDoc, filenameDst)
            if filenameNew != filename:
                if move:
                    msg = 'Move data set file to project folder?\n'
                    msg += 'From: {}\n'.format(filename)
                    msg += 'To: {}\n'.format(filenameDst)
                    msg += 'Yes: Move file\n'
                    msg += 'No: Move data set reference, only\n'
                    msg += 'Cancel: Abort'
                else:
                    msg = 'Copy data set file to project folder?\n'
                    msg += 'From: {}\n'.format(filename)
                    msg += 'To: {}\n'.format(filenameDst)
                    msg += 'Yes: Copy file\n'
                    msg += 'No: Copy data set reference, only\n'
                    msg += 'Cancel: Abort'
                result = c4d.gui.MessageDialog(msg, c4d.GEMB_YESNOCANCEL)
                if result == c4d.GEMB_R_YES:
                    if move:
                        #print('MOVE:', filename, ' -> ', filenameDst)
                        if DO_FILE_ACTION:
                            shutil.move(filename, filenameDst)
                    else:
                        #print('COPY:', filename, ' -> ', filenameDst)
                        if DO_FILE_ACTION:
                            shutil.copyfile(filename, filenameDst)
                elif result == c4d.GEMB_R_CANCEL:
                    return
        else:
            if pathDoc is not None and len(pathDoc) > 1 and filename[0] == '.':
                filenameNew = filename.replace('.', pathDoc, 1)
        if move:
            if isLocal:
                RemoveLocalDataSet(idDataSet)
            else:
                RemoveGlobalDataSet(idDataSet)
        bcDataSetNew[ID_BC_DATASET_FILENAME] = filenameNew
        bcDataSetNew[ID_BC_DATASET_IS_LOCAL] = isLocalNew
        bcDataSetNew.SetId(MyHash(bcDataSetNew[ID_BC_DATASET_NAME] + bcDataSetNew[ID_BC_DATASET_FILENAME] + str(bcDataSetNew[ID_BC_DATASET_IS_LOCAL])))
        if isLocalNew:
            AddLocalDataSetBC(bcDataSetNew)
        else:
            AddGlobalDataSetBC(bcDataSetNew)
        self.UpdateLayoutGroupDataSet(local=True)
        self.UpdateLayoutGroupDataSet(local=False)
        c4d.EventAdd()


    def DataSetOpenDirectory(self, local, idxDataSet):
        if local:
            bcDataSets = GetLocalDataSets()
        else:
            bcDataSets = GetPrefsContainer(ID_BC_DATA_SETS)
        id = bcDataSets.GetIndexId(idxDataSet)
        bcDataSet = bcDataSets.GetContainer(id)
        filename = bcDataSet[ID_BC_DATASET_FILENAME]
        if bcDataSet[ID_BC_DATASET_IS_LOCAL]:
            pathDoc = c4d.documents.GetActiveDocument().GetDocumentPath()
            if pathDoc is not None and len(pathDoc) > 1 and filename[0] == '.':
                filename = filename.replace('.', pathDoc, 1)
        path = filename[:filename.rfind(os.sep)]
        c4d.storage.GeExecuteFile(path)


    def AnalyzeFile(self, filename, local, nameDataSet=None):
        pathDocument = c4d.documents.GetActiveDocument().GetDocumentPath()
        dataLZ4 = None
        with open(filename, mode='rb') as f:
            dataLZ4 = f.read()
            f.close()
        if dataLZ4 is None:
            return None
        dataStudio = lz4f.decompress(dataLZ4, return_bytearray=True, return_bytes_read=False)
        data = json.loads(dataStudio)
        if nameDataSet is None:
            nameDataSet = filename[filename.rfind(os.sep)+1:]
            if nameDataSet[-4:] == '.rec':
                nameDataSet = nameDataSet[:-4]
        if local and pathDocument is not None and len(pathDocument) > 1:
            filename = filename.replace(pathDocument, '.')
        bcDataSet = BaseContainerDataSet(nameDataSet, filename, isLocal=local)
        StoreAvailableEntitiesInDataSet(data[0]['scene'], bcDataSet)
        return bcDataSet

    def AnalyzeDataSet(self, bcDataSet):
        return self.AnalyzeFile(bcDataSet[20], bcDataSet[21], bcDataSet[0])

    def AddDataSet(self, local, folder=False):
        filenames = []
        pathDocument = c4d.documents.GetActiveDocument().GetDocumentPath()
        if folder:
            pathFolder = c4d.storage.LoadDialog(type=c4d.FILESELECTTYPE_ANYTHING, title='Load All Clips From Folder...', flags=c4d.FILESELECT_DIRECTORY, force_suffix='rec', def_path=pathDocument, def_file='')
            if pathFolder is None or len(pathFolder) < 2:
                return True
            for filename in os.listdir(pathFolder):
                if filename[-4:] == '.rec':
                    filenames.append(os.path.join(pathFolder, filename))
        else:
            filename = c4d.storage.LoadDialog(type=c4d.FILESELECTTYPE_ANYTHING, title='Load Clip From File...', force_suffix='rec', def_path=pathDocument, def_file='')
            if filename is None or len(filename) < 2:
                return True
            filenames.append(filename)
        for idxFilename, filename in enumerate(filenames):
            bcDataSet = self.AnalyzeFile(filename, local)
            if local:
                AddLocalDataSetBC(bcDataSet)
            else:
                AddGlobalDataSetBC(bcDataSet)
        for tag in self._tags:
            tag.Message(c4d.MSG_MENUPREPARE)
        self.UpdateLayoutGroupDataSet(local)
        c4d.EventAdd()

    def EditDataSet(self, idxDataSet, local):
        if local:
            bcDataSets = GetLocalDataSets()
        else:
            bcDataSets = GetPrefsContainer(ID_BC_DATA_SETS)
        id = bcDataSets.GetIndexId(idxDataSet)
        bcDataSet = bcDataSets.GetContainer(id)
        dlgEdit = DialogEditDataSet(bcDataSet, local)
        resultOpen = dlgEdit.Open(c4d.DLG_TYPE_MODAL_RESIZEABLE)
        if resultOpen == False:
            return
        result, bcDataSetNew = dlgEdit.GetResult()
        if result == False:
            return
        bcDataSetNew = self.AnalyzeDataSet(bcDataSetNew)
        if local:
            RemoveLocalDataSet(id)
        else:
            RemoveGlobalDataSet(id)
        bcDataSets.SetContainer(bcDataSetNew.GetId(), bcDataSetNew.GetClone(c4d.COPYFLAGS_NONE))
        for tag in self._tags:
            tag.Message(c4d.MSG_MENUPREPARE)
        self.UpdateLayoutGroupDataSet(local)
        c4d.EventAdd()

    def CreateSceneForDataSet(self, idxDataSet, local):
        if local:
            bcDataSets = GetLocalDataSets()
        else:
            bcDataSets = GetPrefsContainer(ID_BC_DATA_SETS)
        id = bcDataSets.GetIndexId(idxDataSet)
        bcDataSet = bcDataSets.GetContainer(id)
        self.InsertDataSetScene(bcDataSet)

    def RemoveDataSet(self, local, idx=-1, all=False, delete=False):
        if local:
            bcDataSets = GetLocalDataSets()
        else:
            bcDataSets = GetPrefsContainer(ID_BC_DATA_SETS)
        filenamesDelete = []
        if delete:
            if all:
                for idDataSet, bcDataSet in bcDataSets:
                    filenamesDelete.append(bcDataSet[ID_BC_DATASET_FILENAME])
            else:
                idDataSet = bcDataSets.GetIndexId(idx)
                bcDataSet = bcDataSets[idDataSet]
                filenamesDelete.append(bcDataSet[ID_BC_DATASET_FILENAME])
            if len(filenamesDelete) <= 0:
                return
            message = 'Are you sure you want to delete the following data set(s)?\n'
            for filename in filenamesDelete:
                message += filename + '\n'
            message += 'Yes: Delete file(s)\nNo: Remove data set reference, only\nCancel: Abort'
            result = c4d.gui.MessageDialog(message, c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_YESNOCANCEL)
            if result == c4d.GEMB_R_NO:
                filenamesDelete = []
            elif result == c4d.GEMB_R_CANCEL:
                return
        if all:
            bcDataSets.FlushAll()
        else:
            idDataSet = bcDataSets.GetIndexId(idx)
            if local:
                RemoveLocalDataSet(idDataSet)
            else:
                RemoveGlobalDataSet(idDataSet)
        self._tags = GetTagList()
        for tag in self._tags:
            tag.Message(c4d.MSG_MENUPREPARE)
        self.UpdateLayoutGroupDataSet(local)
        c4d.EventAdd()
        if len(filenamesDelete) > 0:
            for filename in filenamesDelete:
                #print('DELETING FILE:', filename)
                if DO_FILE_ACTION:
                    os.remove(filename)

    def CommandTagsPopup(self):
        bcMenu = c4d.BaseContainer()
        bcConnected = GetConnectedDataSet()
        if bcConnected is not None:
            bcMenu.InsData(ID_SUBMENU_TAGS_CREATE_STUDIO_LIVE_SCENE, 'Create Connected Studio Scene')
            bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_TAGS_CREATE_CHARACTER_NEWTON, 'Create Rokoko Newton Character')
        bcMenu.InsData(ID_SUBMENU_TAGS_CREATE_BONES_NEWTON, 'Create Rokoko Newton Bones')
        bcMenu.InsData(ID_SUBMENU_TAGS_CREATE_CHARACTER_NEWTON_WITH_FACE, 'Create Rokoko Newton Character with Face')
        bcMenu.InsData(ID_SUBMENU_TAGS_CREATE_FACE_NEWTON, 'Create Rokoko Newton Face')
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_TAGS_CREATE_LIGHT, 'Create Light')
        bcMenu.InsData(ID_SUBMENU_TAGS_CREATE_CAMERA, 'Create Camera')
        bcMenu.InsData(ID_SUBMENU_TAGS_CREATE_PROP, 'Create Prop')
        result = c4d.gui.ShowPopupDialog(cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)
        if result == ID_SUBMENU_TAGS_CREATE_STUDIO_LIVE_SCENE:
            self.InsertRokokoStudioScene()
        elif result == ID_SUBMENU_TAGS_CREATE_CHARACTER_NEWTON:
            self.InsertRokokoCharacter(result)
        elif result == ID_SUBMENU_TAGS_CREATE_CHARACTER_NEWTON_WITH_FACE:
            self.InsertRokokoCharacterWithFace(result)
        elif result == ID_SUBMENU_TAGS_CREATE_BONES_NEWTON:
            self.InsertRokokoCharacter(result, bonesOnly=True)
        elif result == ID_SUBMENU_TAGS_CREATE_FACE_NEWTON:
            self.InsertRokokoFace(result)
        elif result == ID_SUBMENU_TAGS_CREATE_LIGHT:
            self.InsertRokokoLight()
        elif result == ID_SUBMENU_TAGS_CREATE_CAMERA:
            self.InsertRokokoCamera()
        elif result == ID_SUBMENU_TAGS_CREATE_PROP:
            self.InsertRokokoProp()
        elif result == 0:
            pass # menu canceled
        else:
            print('ERROR: Submenu Tags unknown command', result)

    def InsertDataSetScene(self, bcDataSet):
        docCurrent = c4d.documents.GetActiveDocument()
        filenameNewtonWithFace = os.path.join(os.path.dirname(__file__), 'res', 'tpose_rokoko_newton_with_face.c4d')
        filenameNewton = os.path.join(os.path.dirname(__file__), 'res', 'tpose_rokoko_newton_meshed.c4d')
        filenameNewtonFace = os.path.join(os.path.dirname(__file__), 'res', 'rokoko_newton_face.c4d')
        docsSrc = [None, None, None]
        docCurrent.StartUndo()
        objLast = None
        matLast = None
        bcActors = bcDataSet.GetContainerInstance(ID_BC_DATASET_ACTORS)
        for idxActor, _ in bcActors:
            bcActor = bcActors.GetContainerInstance(idxActor)
            hasSuit = bcActor[ID_BC_ENTITY_HAS_SUIT]
            hasFace = bcActor[ID_BC_ENTITY_HAS_FACE]
            name = bcActor[ID_BC_ENTITY_NAME]
            color = bcActor[ID_BC_ENTITY_COLOR]
            docSrc = None
            if hasSuit and hasFace:
                if docsSrc[0] is None:
                    docsSrc[0] = c4d.documents.LoadDocument(filenameNewtonWithFace, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS, None)
                docSrc = docsSrc[0]
            elif hasSuit:
                if docsSrc[1] is None:
                    docsSrc[1] = c4d.documents.LoadDocument(filenameNewton, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS, None)
                docSrc = docsSrc[1]
            else:
                if docsSrc[2] is None:
                    docsSrc[2] = c4d.documents.LoadDocument(filenameNewtonFace, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS, None)
                docSrc = docsSrc[2]
            if docSrc is None:
                print('ERROR: Source scene missing', hasSuit, hasFace)
                continue
            objRootSrc = docSrc.GetFirstObject()
            if objRootSrc is None:
                print('ERROR: No Newton Rig.')
                continue
            matSrc = docSrc.GetFirstMaterial()
            trans = c4d.AliasTrans()
            if not trans or not trans.Init(docSrc):
                print('ERROR: No Alias.')
                continue
            objRootNew = objRootSrc.GetClone(c4d.COPYFLAGS_NONE, trans)
            if objRootNew is None:
                print('ERROR: Failed to clone rig.')
                continue
            materials = []
            while matSrc is not None:
                mat = matSrc.GetClone(c4d.COPYFLAGS_NONE, trans)
                if mat is not None:
                    materials.append(mat)
                matSrc = matSrc.GetNext()
            trans.Translate(True)
            tag = objRootNew.GetTag(type=PLUGIN_ID_TAG)
            if tag is None:
                print('ERROR: Lacking Rokoko Tag.')
                continue
            objRootNew.SetName(name)
            tag.SetName('Rokoko Tag {}'.format(name))
            docCurrent.InsertObject(objRootNew, pred=objLast)
            docCurrent.AddUndo(c4d.UNDOTYPE_NEW, objRootNew)
            objLast = objRootNew
            if len(materials) > 0:
                materials[0][c4d.MATERIAL_COLOR_COLOR] = color
            for mat in materials:
                docCurrent.InsertMaterial(mat, pred=matLast)
                docCurrent.AddUndo(c4d.UNDOTYPE_NEW, mat)
                matLast = mat
            tag.Message(c4d.MSG_MENUPREPARE)
            tag[ID_TAG_DATA_SET] = bcDataSet.GetId()
            #tag[ID_TAG_ACTORS] = idxActor # TODO strange!!!
            tag.GetDataInstance().SetInt32(ID_TAG_ACTORS, idxActor)
            tag[ID_TAG_ACTOR_INDEX] = idxActor
        bcProps = bcDataSet.GetContainerInstance(ID_BC_DATASET_PROPS)
        for idxProp, _ in bcProps:
            bcProp = bcProps.GetContainerInstance(idxProp)
            name = bcProp[ID_BC_ENTITY_NAME]
            color = bcProp[ID_BC_ENTITY_COLOR]
            objProp = c4d.BaseObject(c4d.Onull)
            objProp.SetName(name)
            objProp[c4d.NULLOBJECT_DISPLAY] = 12 # 12: pyramid
            objProp[c4d.ID_BASEOBJECT_COLOR] = color
            objProp[c4d.ID_BASEOBJECT_USECOLOR] = 2
            tag = objProp.MakeTag(PLUGIN_ID_TAG)
            tag.SetName('Rokoko Tag {}'.format(name))
            docCurrent.InsertObject(objProp, pred=objLast)
            docCurrent.AddUndo(c4d.UNDOTYPE_NEW, objProp)
            objLast = objProp
            tag.Message(c4d.MSG_MENUPREPARE)
            #tag[ID_TAG_DATA_SET] = bcDataSet.GetId() # TODO strange!!!
            tag.GetDataInstance().SetInt32(ID_TAG_DATA_SET, bcDataSet.GetId())
            tag.GetDataInstance().SetInt32(ID_TAG_ACTORS, idxProp)
            tag[ID_TAG_ACTOR_INDEX] = idxProp
        docCurrent.EndUndo()
        c4d.EventAdd()

    def InsertRokokoStudioScene(self):
        bcConnected = GetConnectedDataSet()
        if bcConnected is None:
            return
        self.InsertDataSetScene(bcConnected)

    def InsertRokokoCharacter(self, id, bonesOnly=False):
        docCurrent = c4d.documents.GetActiveDocument()
        filenameNewton = os.path.join(os.path.dirname(__file__), 'res', 'tpose_rokoko_newton_meshed.c4d')
        if bonesOnly:
            docNewton = c4d.documents.LoadDocument(filenameNewton, c4d.SCENEFILTER_OBJECTS, None)
            if docNewton is None:
                print('ERROR: Failed to load Rokoko Newton.')
                return
            objRootNewton = docNewton.GetFirstObject()
            if objRootNewton is None or not objRootNewton.CheckType(c4d.Onull) or objRootNewton.GetName() != 'Rokoko Newton':
                print('ERROR: Failed to find Rokoko Newton bones.')
                return
            objRootNewton.Remove()
            docCurrent.StartUndo()
            docCurrent.AddUndo(c4d.UNDOTYPE_NEW, objRootNewton)
            docCurrent.InsertObject(objRootNewton)
            docCurrent.EndUndo()
        else:
            if not c4d.documents.MergeDocument(docCurrent, filenameNewton, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS, None):
                print('ERROR: Failed to merge Rokoko Newton.')
        c4d.EventAdd()

    def InsertRokokoCharacterWithFace(self, id):
        docCurrent = c4d.documents.GetActiveDocument()
        filenameNewton = os.path.join(os.path.dirname(__file__), 'res', 'tpose_rokoko_newton_with_face.c4d')
        if not c4d.documents.MergeDocument(docCurrent, filenameNewton, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS, None):
            print('ERROR: Failed to merge Rokoko Newton with Face')
        c4d.EventAdd()


    def InsertRokokoFace(self, id):
        docCurrent = c4d.documents.GetActiveDocument()
        filenameNewton = os.path.join(os.path.dirname(__file__), 'res', 'rokoko_newton_face.c4d')
        if not c4d.documents.MergeDocument(docCurrent, filenameNewton, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS, None):
            print('ERROR: Failed to merge Rokoko Newton Face')
        c4d.EventAdd()

    def InsertRokokoLight(self):
        light = c4d.BaseObject(c4d.Olight)
        tag = light.MakeTag(PLUGIN_ID_TAG)
        doc = c4d.documents.GetActiveDocument()
        doc.StartUndo()
        doc.InsertObject(light)
        doc.AddUndo(c4d.UNDOTYPE_NEW, light)
        doc.EndUndo()
        tag.Message(c4d.MSG_MENUPREPARE)
        c4d.EventAdd()

    def InsertRokokoCamera(self):
        camera = c4d.BaseObject(c4d.Ocamera)
        tag = camera.MakeTag(PLUGIN_ID_TAG)
        doc = c4d.documents.GetActiveDocument()
        doc.StartUndo()
        doc.InsertObject(camera)
        doc.AddUndo(c4d.UNDOTYPE_NEW, camera)
        doc.EndUndo()
        tag.Message(c4d.MSG_MENUPREPARE)
        c4d.EventAdd()

    def InsertRokokoProp(self):
        prop = c4d.BaseObject(c4d.Onull)
        tag = prop.MakeTag(PLUGIN_ID_TAG)
        doc = c4d.documents.GetActiveDocument()
        doc.StartUndo()
        doc.InsertObject(prop)
        doc.AddUndo(c4d.UNDOTYPE_NEW, prop)
        doc.EndUndo()
        tag.Message(c4d.MSG_MENUPREPARE)
        c4d.EventAdd()

    def CommandTagPopup(self, id):
        idxTag = id - ID_DLGMNGR_BASE_TAG_POPUP
        bcMenu = c4d.BaseContainer()
        disableItem = ''
        if g_thdListener._receive:
            disableItem = '&d&'
        bcMenu.InsData(ID_SUBMENU_TAG_PLAY, 'Play' + disableItem)
        bcMenu.InsData(ID_SUBMENU_TAG_TPOSE, 'Go to T-Pose' + disableItem)
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_TAG_SHOW_TAG, 'Show Tag in Attribute Manager')
        bcMenu.InsData(ID_SUBMENU_TAG_SHOW_OBJECT, 'Show Object in Attribute Manager')
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_TAG_DELETE, 'Delete Rokoko Tag' + disableItem)
        self._tags = GetTagList()
        result = c4d.gui.ShowPopupDialog(cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)
        if result == ID_SUBMENU_TAG_PLAY:
            self.CommandPlayerStart(idxTag=idxTag)
        elif result == ID_SUBMENU_TAG_SHOW_TAG:
            self.ShowInAttributeManager(self._tags[idxTag])
        elif result == ID_SUBMENU_TAG_SHOW_OBJECT:
            self.ShowInAttributeManager(self._tags[idxTag].GetObject())
        elif result == ID_SUBMENU_TAG_DELETE:
            self.DeleteTag(idxTag)
        elif result == ID_SUBMENU_TAG_TPOSE:
            c4d.CallButton(self._tags[idxTag], ID_TAG_BUTTON_GO_TO_TPOSE)
            c4d.EventAdd()
        elif result == 0:
            pass # menu canceled
        else:
            print('ERROR: Submenu Tags unknown command', result)

    def ShowInAttributeManager(self, bl):
        if bl.CheckType(c4d.Tbase):
            c4d.gui.ActiveObjectManager_SetObject(c4d.ACTIVEOBJECTMODE_TAG, bl, c4d.ACTIVEOBJECTMANAGER_SETOBJECTS_OPEN, activepage=c4d.DescID())
        else:
            c4d.gui.ActiveObjectManager_SetObject(c4d.ACTIVEOBJECTMODE_OBJECT, bl, c4d.ACTIVEOBJECTMANAGER_SETOBJECTS_OPEN, activepage=c4d.DescID())

    def DeleteTag(self, idxTag):
        tag = self._tags.pop(idxTag)
        doc = tag.GetDocument()
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_DELETE, tag)
        tag.Remove()
        doc.EndUndo()
        c4d.EventAdd()


    def CommandProjectScale(self):
        SetProjectScale(self.GetFloat(ID_DLGMNGR_PROJECT_SCALE))

    def CommandPlayChoice(self):
        SetPref(ID_DLGMNGR_PLAYER_TAG_SELECTION, self.GetInt32(ID_DLGMNGR_PLAYER_TAG_SELECTION))

    def CommandPlayerStart(self, all=False, live=False, idxTag=-1):
        live = g_thdListener._receive
        if not live and g_thdListener.GetConnectionStatus() == 2:
            result = c4d.gui.MessageDialog('Currently there is no data incoming from Live connection.\nDisconnect?', c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_YESNOCANCEL)
            if result == c4d.GEMB_R_YES:
                self.Connect(999999)
            elif result == c4d.GEMB_R_CANCEL:
                return
        if live:
            self.CommandPlayerExit()
            return
        choice = self.GetInt32(ID_DLGMNGR_PLAYER_TAG_SELECTION)
        tagsLive = []
        self._tags = GetTagList()
        if choice == 0: #all:
            tagsLive = self._tags
        elif choice == 2: #live:
            bcConnected = GetConnectedDataSet()
            if bcConnected is None:
                return
            for tag in self._tags:
                if tag[ID_TAG_DATA_SET] == bcConnected.GetId():
                    tagsLive.append(tag)
        elif choice == 3: # data sets, only
            bcConnected = GetConnectedDataSet()
            if bcConnected is None:
                return
            for tag in self._tags:
                if tag[ID_TAG_DATA_SET] != bcConnected.GetId():
                    tagsLive.append(tag)
        elif idxTag != -1:
            tagsLive = [self._tags[idxTag]]
        else:
            for tag in self._tags:
                if tag[ID_TAG_SELECTED_IN_MANAGER]:
                    tagsLive.append(tag)
        validTags = []
        for tag in tagsLive:
            if not tag[ID_TAG_VALID_DATA]:
                continue
            validTags.append(tag)
        if len(validTags) <= 0:
            c4d.gui.MessageDialog('No data to play.\nEither no tags selected or\nno valid data sets assigned to tags.')
            return
        for tag in tagsLive:
            g_thdListener.AddTagConsumer(tag.GetNodeData(), tag)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_START)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_PLAY, False)

    def CommandPlayerExit(self):
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_STOP)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_EXIT)
        self._buttonRecordState = False
        c4d.EventAdd()

    def CommandPlaybackSpeed(self):
        SetPref(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, self.GetInt32(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED))

    def CommandAnimateDocument(self):
        SetPref(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT, self.GetBool(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT))

    def CommandPause(self, force=False, returnToLive=False, idx=None):
        pause = (g_thdListener._play or force) and not returnToLive
        if pause:
            if idx is None:
                idx = self.GetInt32(ID_DLGMNGR_PLAYER_CURRENT_FRAME)
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_PAUSE, idx)
        else:
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_PLAY, returnToLive)

    def CommandJumpToFrame(self, idx):
        self.CommandPause(force=True, idx=idx)
        _, maxFrame = g_thdListener.GetCurrentFrameNumber()
        self.SetInt32(ID_DLGMNGR_PLAYER_CURRENT_FRAME, idx, min=0, max=maxFrame, min2=0, max2=maxFrame)

    def CommandStartNewRecording(self):
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_FLUSH_LIVE_BUFFER)

    def CommandSaveRecording(self):
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_PAUSE_RECEPTION)
        self.CommandPause(force=True)
        self.EnableDialog(False)
        self._dlgChild = DialogSaveRecording(self)
        self._dlgChild.Open(c4d.DLG_TYPE_ASYNC)

    def CommandStartSaveRecording(self):
        if self._buttonRecordState:
            self.CommandSaveRecording()
        else:
            self.CommandStartNewRecording()
        self._buttonRecordState = not self._buttonRecordState
        self.EnableLiveButtons()

    def CommandRemoveGlobalData(self, id):
        idxTag = id - ID_DLGMNGR_BASE_GLOBAL_DATA_REMOVE
        bcGlobalDataSets = GetPrefsContainer(ID_BC_DATA_SETS)
        if len(bcGlobalDataSets) <= 0:
            return
        idx = 0
        for id, bcGlobalData in bcGlobalDataSets:
            if idx == idxTag:
                bcGlobalDataSets.RemoveData(id)
                break
            idx += 1
        self._tags = GetTagList()
        for tag in self._tags:
            tag.Message(c4d.MSG_MENUPREPARE)
        c4d.EventAdd()

    def CommandRemoveLocalData(self, id):
        idxTag = id - ID_DLGMNGR_BASE_LOCAL_DATA_REMOVE
        bcLocalDataSets = GetLocalDataSets()
        if len(bcLocalDataSets) <= 0:
            return
        idx = 0
        for id, bcLocalData in bcLocalDataSets:
            if idx == idxTag:
                bcLocalDataSets.RemoveData(id)
                break
            idx += 1
        self._tags = GetTagList()
        for tag in self._tags:
            tag.Message(c4d.MSG_MENUPREPARE)
        c4d.EventAdd()

    def CommandTagEnable(self, id):
        idxTag = id - ID_DLGMNGR_BASE_DATA_SET_ENABLED
        self._tags = GetTagList()
        if self._tags is None or idxTag >= len(self._tags):
            return
        tag = self._tags[idxTag]
        doc = c4d.documents.GetActiveDocument()
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
        tag[ID_TAG_SELECTED_IN_MANAGER] = self.GetBool(id)
        doc.EndUndo()
        c4d.EventAdd()

    def CommandTagSelectAll(self, select=True):
        self._tags = GetTagList()
        if self._tags is None:
            return
        doc = c4d.documents.GetActiveDocument()
        doc.StartUndo()
        for tag in self._tags:
            doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
            tag[ID_TAG_SELECTED_IN_MANAGER] = select
        doc.EndUndo()
        c4d.EventAdd()

    def CommandTagInvertSelection(self):
        self._tags = GetTagList()
        if self._tags is None:
            return
        doc = c4d.documents.GetActiveDocument()
        doc.StartUndo()
        for tag in self._tags:
            doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
            tag[ID_TAG_SELECTED_IN_MANAGER] = not tag[ID_TAG_SELECTED_IN_MANAGER]
        doc.EndUndo()
        c4d.EventAdd()

    def CommandTagRigType(self, id):
        idxTag = id - ID_DLGMNGR_BASE_TAG_RIG_TYPES
        self._tags = GetTagList()
        if self._tags is None or idxTag >= len(self._tags):
            return
        tag = self._tags[idxTag]
        doc = c4d.documents.GetActiveDocument()
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
        tag[ID_TAG_RIG_TYPE] = self.GetInt32(id)
        doc.EndUndo()
        c4d.EventAdd()

    def CommandTagDataSet(self, id):
        idxTag = id - ID_DLGMNGR_BASE_TAG_DATA_SETS
        self._tags = GetTagList()
        if self._tags is None or idxTag >= len(self._tags):
            return
        tag = self._tags[idxTag]
        doc = c4d.documents.GetActiveDocument()
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
        tag[ID_TAG_DATA_SET] = self.GetInt32(id)
        doc.EndUndo()
        c4d.EventAdd()

    def CommandTagActor(self, id):
        idxTag = id - ID_DLGMNGR_BASE_TAG_ACTORS
        self._tags = GetTagList()
        if self._tags is None or idxTag >= len(self._tags):
            return
        tag = self._tags[idxTag]
        doc = c4d.documents.GetActiveDocument()
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
        tag[ID_TAG_ACTORS] = self.GetInt32(id)
        doc.EndUndo()
        c4d.EventAdd()

    def CommandConnect(self, id):
        if id == ID_DLGMNGR_CONNECTIONS_IN_MENU:
            idxConnection = self.GetInt32(id)
        else:
            idxConnection = id - ID_DLGMNGR_BASE_CONNECTION_CONNECT
        self.Connect(idxConnection)

    def CommandAutoConnect(self, id):
        idxConnection = id - ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT
        bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
        idConnectionClicked = bcConnections.GetIndexId(idxConnection)
        idx = 0
        for idConnection, bcConnection in bcConnections:
            enable = self.GetBool(id) and idConnectionClicked == idConnection
            bcConnections.GetContainerInstance(idConnection)[ID_BC_DATASET_LIVE_AUTOCONNECT] = enable
            self.SetBool(ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT + idx, enable)
            idx += 1

    def CommandCommandAPI(self, id):
        bcConnected = GetConnectedDataSet()
        if bcConnected is None:
            bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
            idFirstConnection = bcConnections.GetIndexId(0)
            bcConnected = bcConnections[idFirstConnection]
        url = 'http://' + bcConnected[ID_BC_DATASET_COMMANDAPI_IP] + ':'
        url += bcConnected[ID_BC_DATASET_COMMANDAPI_PORT] + '/v1/'
        url += bcConnected[ID_BC_DATASET_COMMANDAPI_KEY] + '/'
        actionText = 'UNKNOWN'
        if id == ID_DLGMNGR_COMMANDAPI_START_RECORDING:
            actionText = 'Start Recording'
            statusText = 'Rokoko Studio Recording started'
            url += 'recording/start'
        elif id == ID_DLGMNGR_COMMANDAPI_STOP_RECORDING:
            actionText = 'Stop Recording'
            statusText = 'Rokoko Studio Recording stopped'
            url += 'recording/stop'
        elif id == ID_DLGMNGR_COMMANDAPI_CALIBRATE_ALL_SUITS:
            actionText = 'Start Suit Calibration'
            statusText = 'Rokoko Studio Suit Calibration started'
            url += 'calibrate'
        elif id == ID_DLGMNGR_COMMANDAPI_RESET_ALL_SUITS:
            actionText = 'Reset All Suits'
            statusText = 'Reset All Suits in Rokoko Studio'
            url += 'restart'
        postData = {}
        postData = str(postData)
        postData = postData.encode('utf-8')
        response = None
        ok = True
        try:
            req = urllib.request.Request(url, postData, unverifiable=True)
            response = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            d = json.loads(e.__dict__['file'].read())
            responseCode = d['response_code']
            description = d['description']
            if responseCode == 'OK': # TODO
                pass
            else:
                #NO_LIVE_SMARTSUIT
                #NO_ACTIVE_RECORDING
                c4d.gui.MessageDialog('Rokoko Command API failed to {}\n\nError Code:       {}\nError Message: {}'.format(actionText, responseCode, description))
                ok = False
        except:
            c4d.gui.MessageDialog('Command API failed to connect to Rokoko Studio.\nPlease check IP, port and key configured for Command API in Connection.')
        if ok:
            c4d.StatusSetText(statusText)

    def CommandAbout(self):
        dlg = DialogAbout()
        dlg.Open(c4d.DLG_TYPE_MODAL)

    def CommandWeb(self, id):
        if id not in LINKS:
            print('ERROR: Unknown link ID')
            return
        c4d.storage.GeExecuteFile(LINKS[id])

    def Command(self, id, msg):
        if id == ID_DLGMNGR_TABS:
            self.UpdateGroupVisibility()
        elif id == ID_DLGMNGR_CONNECTION_POPUP:
            self.CommandConnectionsPopup()
        elif id >= ID_DLGMNGR_BASE_CONNECTION_POPUP and id < ID_DLGMNGR_BASE_CONNECTION_POPUP + 10000:
            self.CommandConnectionPopup(id)
        elif id >= ID_DLGMNGR_BASE_CONNECTION_CONNECT and id < ID_DLGMNGR_BASE_CONNECTION_CONNECT + 10000:
            self.CommandConnect(id)
        elif id == ID_DLGMNGR_CONNECTIONS_IN_MENU:
            self.CommandConnect(id)
        elif id >= ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT and id < ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT + 10000:
            self.CommandAutoConnect(id)
        elif id == ID_DLGMNGR_GLOBAL_DATA_POPUP:
            self.CommandGlobalDataPopup()
        elif id >= ID_DLGMNGR_BASE_GLOBAL_DATA_POPUP and id < ID_DLGMNGR_BASE_GLOBAL_DATA_POPUP + 10000:
            self.CommandGlobalDataSetPopup(id)
        elif id == ID_DLGMNGR_LOCAL_DATA_POPUP:
            self.CommandLocalDataPopup()
        elif id >= ID_DLGMNGR_BASE_LOCAL_DATA_POPUP and id < ID_DLGMNGR_BASE_LOCAL_DATA_POPUP + 10000:
            self.CommandLocalDataSetPopup(id)
        elif id == ID_DLGMNGR_TAGS_POPUP:
            self.CommandTagsPopup()
        elif id >= ID_DLGMNGR_BASE_TAG_POPUP and id < ID_DLGMNGR_BASE_TAG_POPUP + 10000:
            self.CommandTagPopup(id)
        elif id >= ID_DLGMNGR_BASE_TAG_RIG_TYPES and id < ID_DLGMNGR_BASE_TAG_RIG_TYPES + 10000:
            self.CommandTagRigType(id)
        elif id >= ID_DLGMNGR_BASE_TAG_DATA_SETS and id < ID_DLGMNGR_BASE_TAG_DATA_SETS + 10000:
            self.CommandTagDataSet(id)
        elif id >= ID_DLGMNGR_BASE_TAG_ACTORS and id < ID_DLGMNGR_BASE_TAG_ACTORS + 10000:
            self.CommandTagActor(id)
        elif id >= ID_DLGMNGR_BASE_DATA_SET_ENABLED and id < ID_DLGMNGR_BASE_DATA_SET_ENABLED + 10000:
            self.CommandTagEnable(id)
        elif id == ID_DLGMNGR_PROJECT_SCALE:
            self.CommandProjectScale()
        elif id == ID_DLGMNGR_PLAYER_START_STOP:
            self.CommandPlayerStart()
        elif id == ID_DLGMNGR_PLAYER_TAG_SELECTION:
            self.CommandPlayChoice()
        elif id == ID_DLGMNGR_SELECT_ALL_TAGS:
            self.CommandTagSelectAll()
        elif id == ID_DLGMNGR_DESELECT_ALL_TAGS:
            self.CommandTagSelectAll(select=False)
        elif id == ID_DLGMNGR_INVERT_SELECTION:
            self.CommandTagInvertSelection()
        elif id == ID_DLGMNGR_ABOUT:
            self.CommandAbout()
        elif id == ID_DLGMNGR_WEB_ROKOKO or id == ID_DLGMNGR_WEB_STUDIO_LIVE_LICENSE or \
             id == ID_DLGMNGR_WEB_DOCUMENTATION or id == ID_DLGMNGR_WEB_FORUMS:
            self.CommandWeb(id)
        elif id == ID_DLGMNGR_PLAYER_PAUSE:
            self.CommandPause()
        elif id == ID_DLGMNGR_PLAYER_SYNC_WITH_LIVE:
            self.CommandPause(returnToLive=True)
        elif id == ID_DLGMNGR_PLAYER_EXIT:
            self.CommandPlayerExit()
        elif id == ID_DLGMNGR_PLAYER_PLAYBACK_SPEED:
            self.CommandPlaybackSpeed()
        elif id == ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT:
            self.CommandAnimateDocument()
        elif id == ID_DLGMNGR_PLAYER_CURRENT_FRAME:
            self.CommandJumpToFrame(self.GetInt32(id))
        elif id == ID_DLGMNGR_PLAYER_FIRST_FRAME:
            self.CommandJumpToFrame(0)
        elif id == ID_DLGMNGR_PLAYER_LAST_FRAME:
            _, maxFrame = g_thdListener.GetCurrentFrameNumber()
            self.CommandJumpToFrame(maxFrame - 1)
        elif id == ID_DLGMNGR_PLAYER_SAVE:
            self.CommandStartSaveRecording()
        elif id == ID_DLGMNGR_COMMANDAPI_START_RECORDING or id == ID_DLGMNGR_COMMANDAPI_STOP_RECORDING or \
             id == ID_DLGMNGR_COMMANDAPI_CALIBRATE_ALL_SUITS or id == ID_DLGMNGR_COMMANDAPI_RESET_ALL_SUITS:
            self.CommandCommandAPI(id)
        return True
