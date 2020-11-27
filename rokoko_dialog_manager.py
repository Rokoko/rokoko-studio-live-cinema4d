# The central user interface of Rokoko Studio Live.
# - Connection to Rokoko Studio
# - Motion data Clip libraries (one global or C4D wide, one in current scene)
# - All Rokoko Tags contained in a sceneare listed and can be configured here
# - Player, really only the Player interface, the actual Player is inside the listener thread
# - Command API
#
# The dialog itself holds no (almost no) data or state. All data is stored in world prefs, document
# data and/or Rokoko tag's BaseContainer. The dialog only displays this data and provides
# means to change such distributed information from a central place.
import os, shutil, json
import urllib.request
import c4d
# Import lz4 module for the correct platform
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

# To disable actual file operations (clip management) during development
DO_FILE_ACTION = True

# Web links in Help menu
LINKS = { ID_DLGMNGR_WEB_ROKOKO : 'https://www.rokoko.com',
          ID_DLGMNGR_WEB_STUDIO_LIVE_LICENSE : 'https://github.com/Rokoko/rokoko-studio-live-cinema4d/blob/main/LICENSE',
          ID_DLGMNGR_WEB_DOCUMENTATION : 'https://help.rokoko.com/support/solutions/folders/47000773247',
          ID_DLGMNGR_WEB_FORUMS : 'https://rokoko.freshdesk.com/support/discussions/forums/47000400299',
        }
# Width of left button column ("+" and "..." buttons)
WIDTH_ADD_BUTTON = 16


g_thdListener = GetListenerThread() # owned by rokoko_listener

# To be called during shutdown
def DlgManagerDataDestroyGlobals():
    global g_thdListener
    g_thdListener = None


class DialogRokokoManager(c4d.gui.GeDialog):
    # Save Recording and Baking dialog
    _dlgChild = None

    # CustomGUI handles
    _quickTab = None # Quick tab to switch between dialog groups
    _bitmapButtonPlayPause = None # Player's Play/Pause button (needed to toggle its state)
    _bitmapButtonConnectionStatus = None # Connection status dot in menu row
    _bitmapButtonsPerConnectionStatus = [] # Connection status dots in connection rows

    # List of all Rokoko tags in current document
    _tags = None

    # UI states
    _buttonRecordState = False # Start Recording"/"Save Recording..." button changes function according to this flag
    _connecting = False # Used to disable "Connect" buttons while connecting


    # Create main menu.
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


    # Create widgets in main menu row (right of menu).
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


    # Update widgets in main menu row.
    def UpdateLayoutInMenu(self):
        # Rebuild Connection combo box.
        isConnected = IsConnected()
        idConnected = GetConnectedDataSetId()

        self.FreeChildren(ID_DLGMNGR_CONNECTIONS_IN_MENU)

        # First add an option to
        if isConnected:
            self.AddChild(ID_DLGMNGR_CONNECTIONS_IN_MENU, 999999, 'Disconnect')
            self.AddChild(ID_DLGMNGR_CONNECTIONS_IN_MENU, 1000000, '') # separator

        bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
        idxConnected = 999999
        if len(bcConnections) > 0:
            idx = 0
            for id, bcConnection in bcConnections:
                self.AddChild(ID_DLGMNGR_CONNECTIONS_IN_MENU, idx, bcConnection[ID_BC_DATASET_NAME])
                if id == idConnected:
                    idxConnected = idx
                idx += 1

        # Lastly add a "Not Connected" enttry, which will be selected and shown, if this is the case
        if not isConnected:
            self.AddChild(ID_DLGMNGR_CONNECTIONS_IN_MENU, 1000000, '') # separator
            self.AddChild(ID_DLGMNGR_CONNECTIONS_IN_MENU, 999999, 'Not Connected')

        # Select current connection (or "Not Connencted")
        self.SetInt32(ID_DLGMNGR_CONNECTIONS_IN_MENU, idxConnected)

        # Update the connection status dot
        statusConnection = g_thdListener.GetConnectionStatus()

        # Get icon based on connection status
        if statusConnection == 0:
            idIcon = 465003508 # red dot
        elif statusConnection == 1:
            idIcon = 465001743 # green dot
        elif statusConnection == 2 and isConnected:
            idIcon = 465001740 # orange dot
        elif statusConnection == 2 and not isConnected:
            idIcon = 465001746 # grey dot
        icon = c4d.gui.GetIcon(idIcon)

        # Get icon bitmap.
        # In C4D most application icons are stored in a single bitmap.
        # The icon structure only contains a reference to the correct part of this bitmap.
        bmpIcon = icon['bmp'].GetClonePart(icon['x'], icon['y'], icon['w'], icon['h'])

        # Update image in status button.
        self._bitmapButtonConnectionStatus.SetImage(bmpIcon)

        # If player is in offline state (see rokoko_listener), disable the status dot.
        self.Enable(ID_DLGMNGR_CONNECTION_STATUS_IN_MENU, statusConnection != 2 or isConnected)

        # Disable connections combo box while connecting
        self.Enable(ID_DLGMNGR_CONNECTIONS_IN_MENU, not self._connecting)


    # Creates the widgets for a single connection, one row.
    def CreateLayoutRowConnection(self, bc, idx):
        # Popup menu button.
        self.AddButton(ID_DLGMNGR_BASE_CONNECTION_POPUP + idx, c4d.BFH_FIT, initw=WIDTH_ADD_BUTTON, name='...')

        # Name
        labelConnection = bc[ID_BC_DATASET_NAME] + ' (' + bc[ID_BC_DATASET_LIVE_PORT] + ')'
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name=labelConnection)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=20, name='') # spacer

        # Auto Connect
        self.AddCheckbox(ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT + idx, c4d.BFH_CENTER, initw=0, inith=0, name='Auto Connect')
        self.AddStaticText(0, c4d.BFH_LEFT, initw=10, name='') # spacer

        # Connection status
        bitmapButton = CreateLayoutAddBitmapButton(self, 0, idIcon1=465003508, tooltip='', button=False, toggle=False, flags=c4d.BFH_CENTER|c4d.BFV_CENTER)
        self._bitmapButtonsPerConnectionStatus.append(bitmapButton)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=10, name='') # spacer

        # Connect/(Disconnect button)
        self.AddButton(ID_DLGMNGR_BASE_CONNECTION_CONNECT + idx, c4d.BFH_FIT, initw=100, name='')

        # Meta data of connection, if connected.
        # Currently only the FPS contained in motion data get shown here.
        # TODO: Currently not prepared for multiple connections
        if self.GroupBegin(ID_DLGMNGR_GROUP_CONNECTION_DATA_CONTENT, flags=c4d.BFH_SCALEFIT, title='', rows=1):
            self.AddStaticText(0, c4d.BFH_LEFT, initw=20, name='') # spacer
            self.AddStaticText(ID_DLGMNGR_CONNECTION_FPS, c4d.BFH_CENTER, initw=0, name='')
        self.GroupEnd()


    # Creates all widgets on "Connection" tab.
    #
    # The implementation allows for multiple connections (with only one active at a time).
    # Currently this is deliberately restricted to just one connection, which always exists.
    # Therefore the add connection button ("+") and the remove connection option
    # in connection's popup menu got removed.
    def CreateLayoutGroupConnections(self):
        if self.GroupBegin(ID_DLGMNGR_GROUP_CONNECTIONS, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=1): # Tab group

            CreateLayoutAddGroupBar(self, 'Connection')

            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=1, inith=16): # Connections

                scrollFlags = c4d.SCROLLGROUP_VERT | c4d.SCROLLGROUP_AUTOVERT | c4d.SCROLLGROUP_NOVGAP
                if self.ScrollGroupBegin(ID_DLGMNGR_SCROLL_CONNECTIONS, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, scrollFlags, initw=0, inith=0): # Scroll connection rows

                    if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=9): # Connection rows
                        self.GroupBorderSpace(10, 2, 0, 0)

                        # Throw away all connection status buttons, these will be recreated below
                        self._bitmapButtonsPerConnectionStatus.clear()

                        bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)

                        if len(bcConnections) > 0:
                            # Iterate all connections
                            idx = 0
                            for id, bcConnection in bcConnections:
                                # Add a row with widgets per connection
                                self.CreateLayoutRowConnection(bcConnection, idx)
                                idx += 1
                        else:
                            self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='No connections configured.')
                    self.GroupEnd() # Connection rows
                self.GroupEnd() # Scroll connection rows
            self.GroupEnd() # Connections

            # The two groups have historical reasons and are only kept as we may want to return to a more complex design later on.
            if self.GroupBegin(ID_DLGMNGR_GROUP_CONNECTION_DATA, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=1): # Connection data
                self.GroupBorderSpace(38, 0, 0, 0)

                if self.GroupBegin(ID_DLGMNGR_GROUP_CONNECTION_DATA_DETAILS, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=2): # Connection details
                    self.GroupBorderSpace(10, 0, 0, 0)
                    # filled in UpdateLayoutGroupConnectedDataSet()
                self.GroupEnd() # Connection details
            self.GroupEnd() # Connection data
        self.GroupEnd() # Tab group


    # Relayouts (or updates)  the "Connection" tab
    def UpdateLayoutGroupConnections(self):
        self.LayoutFlushGroup(ID_DLGMNGR_GROUP_CONNECTIONS)
        self.CreateLayoutGroupConnections()
        self.LayoutChanged(ID_DLGMNGR_GROUP_CONNECTIONS)


    # Relayout subgroup of "Connection1" tab showing the content of the current connection
    def UpdateLayoutGroupConnectedDataSet(self):
        # Get current connection and its meta data
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

        # Set FPS in row of connection # TODO: not correct with multiple connections
        self.SetString(ID_DLGMNGR_CONNECTION_FPS, '(FPS: ' + str(fps) + ')')

        # Relayout data content group
        self.LayoutFlushGroup(ID_DLGMNGR_GROUP_CONNECTION_DATA_DETAILS)

        # Actors
        if numActors > 0:
            bcActors = bc[ID_BC_DATASET_ACTORS]
            self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='') # spacer

            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=6): # actor rows
                for idxActor, bcActor in bcActors:
                    # Actor icon
                    CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_PROFILE, tooltip='', button=False, toggle=False, flags=c4d.BFH_LEFT|c4d.BFV_CENTER)

                    # Actor name
                    self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name=bcActor[ID_BC_ENTITY_NAME])

                    # Icons for Suit, Gloves and Face (spacer in order to have them in correctly aligned columns with multiple actors)
                    if bcActor[ID_BC_ENTITY_HAS_SUIT]:
                        CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_SUIT, tooltip='', button=False, toggle=False, flags=c4d.BFH_LEFT|c4d.BFV_CENTER)
                    else:
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='') # spacer

                    if bcActor[ID_BC_ENTITY_HAS_FACE]:
                        CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_FACE, tooltip='', button=False, toggle=False, flags=c4d.BFH_LEFT|c4d.BFV_CENTER)
                    else:
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='') # spacer

                    if bcActor[ID_BC_ENTITY_HAS_GLOVE_LEFT]:
                        CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_GLOVE_LEFT, tooltip='', button=False, toggle=False, flags=c4d.BFH_LEFT|c4d.BFV_CENTER)
                    else:
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='') # spacer

                    if bcActor[ID_BC_ENTITY_HAS_GLOVE_RIGHT]:
                        CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_GLOVE_RIGHT, tooltip='', button=False, toggle=False, flags=c4d.BFH_LEFT|c4d.BFV_CENTER)
                    else:
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='') # spacer
            self.GroupEnd() # actor rows

        # Props
        if numProps > 0:
            bcProps = bc[ID_BC_DATASET_PROPS]
            self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='') # spacer

            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=2): # Prop rows

                for idxProp, bcProp in bcProps:
                    CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_PROP, tooltip='', button=False, toggle=False, flags=c4d.BFH_LEFT|c4d.BFV_CENTER)
                    self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name=bcProp[ID_BC_ENTITY_NAME])
            self.GroupEnd()# Prop rows

        # If there are neither actors nor props, show message
        if numActors == 0 and numProps == 0:
            self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Receiving no data!')

        self.LayoutChanged(ID_DLGMNGR_GROUP_CONNECTION_DATA_DETAILS)


    # Heading row for data sets
    def CreateLayoutHeadingsDataSet(self, local):
        # Add to the correct library "Add" button (global or project/local)
        if local:
            idButtonPopup = ID_DLGMNGR_LOCAL_DATA_POPUP
        else:
            idButtonPopup = ID_DLGMNGR_GLOBAL_DATA_POPUP

        # Data set library "+" button
        self.AddButton(idButtonPopup, c4d.BFH_LEFT, initw=WIDTH_ADD_BUTTON, inith=0, name='+')

        # Column Headings
        self.AddStaticText(0, c4d.BFH_LEFT, initw=150, name='Name')
        self.AddStaticText(0, c4d.BFH_LEFT, initw=20, name='') # spacer
        CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_SUIT, tooltip='Number of Suits', button=False, toggle=False, flags=c4d.BFH_RIGHT|c4d.BFV_CENTER)
        CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_GLOVE_LEFT, tooltip='Number of Gloves', button=False, toggle=False, flags=c4d.BFH_RIGHT|c4d.BFV_CENTER)
        CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_FACE, tooltip='Number of Faces', button=False, toggle=False, flags=c4d.BFH_RIGHT|c4d.BFV_CENTER)
        CreateLayoutAddBitmapButton(self, 0, idIcon1=PLUGIN_ID_ICON_PROP, tooltip='Number of Props', button=False, toggle=False, flags=c4d.BFH_RIGHT|c4d.BFV_CENTER)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=20, name='') # spacer
        self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=0, name='File')


    # Creates the widgets for a single data set (clip), one row.
    def CreateLayoutRowDataSet(self, bcDataSet, idx):
        # Use correct ID base for buttons in global or project/local library
        if bcDataSet[ID_BC_DATASET_IS_LOCAL]:
            idButtonBase = ID_DLGMNGR_BASE_LOCAL_DATA_POPUP
        else:
            idButtonBase = ID_DLGMNGR_BASE_GLOBAL_DATA_POPUP

        # Add popup menu button ("...")
        self.AddButton(idButtonBase + idx, c4d.BFH_FIT, initw=WIDTH_ADD_BUTTON, name='...')

        # Add data set info
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name=bcDataSet[ID_BC_DATASET_NAME])
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='') # spacer
        self.AddStaticText(0, c4d.BFH_CENTER, initw=0, name=bcDataSet[ID_BC_DATASET_NUM_SUITS])
        self.AddStaticText(0, c4d.BFH_CENTER, initw=0, name=bcDataSet[ID_BC_DATASET_NUM_GLOVES])
        self.AddStaticText(0, c4d.BFH_CENTER, initw=0, name=bcDataSet[ID_BC_DATASET_NUM_FACES])
        self.AddStaticText(0, c4d.BFH_CENTER, initw=0, name=bcDataSet[ID_BC_DATASET_NUM_PROPS])
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='') # spacer
        self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=0, name=bcDataSet[ID_BC_DATASET_FILENAME])


    # Creates all widgets on a "Clips" library tab, either global or local.
    #
    # There are two clip libraries. Global in C4D's preferences and local in a document (project).
    # Thus dialog also has two tabs representing these libraries.
    def CreateLayoutGroupDataSet(self, local):
        # Only few things
        if local:
            idGroup = ID_DLGMNGR_GROUP_LOCAL_DATA # ID of project library tab group
            nameGroup = 'Project Clips' # tab title project library
            bcDataSets = GetLocalDataSets() # the project library
        else:
            idGroup = ID_DLGMNGR_GROUP_GLOBAL_DATA # ID of global library tab group
            nameGroup = 'Global Clips' # tab title global library
            bcDataSets = GetPrefsContainer(ID_BC_DATA_SETS) # the global library

        if self.GroupBegin(idGroup, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=1): # Tab group

            CreateLayoutAddGroupBar(self, nameGroup)

            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=1, inith=52): # Data sets

                scrollFlags = c4d.SCROLLGROUP_VERT | c4d.SCROLLGROUP_AUTOVERT | c4d.SCROLLGROUP_NOVGAP
                if self.ScrollGroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, scrollFlags, initw=0, inith=0): # Scroll data set rows

                    if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=9): # Data set rows
                        self.GroupBorderSpace(10, 2, 0, 0)

                        # One row heading
                        self.CreateLayoutHeadingsDataSet(local)

                        if len(bcDataSets) > 0:
                            # Iterate all data sets of library
                            idx = 0
                            for id, bcDataSet in bcDataSets:
                                # Add a row with widgets per data set
                                self.CreateLayoutRowDataSet(bcDataSet, idx)
                                idx += 1
                        else:
                            self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='') # spacer
                            self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='No data sets.')
                    self.GroupEnd() # Data set rows
                self.GroupEnd() # Scroll data set rows
            self.GroupEnd() # Data sets
        self.GroupEnd() # Tab group


    # Relayouts (or updates) a "Clips" tab, either global or local.
    def UpdateLayoutGroupDataSet(self, local):
        # Use correct ID for tab group of global or project/local library
        if local:
            idGroup = ID_DLGMNGR_GROUP_LOCAL_DATA
        else:
            idGroup = ID_DLGMNGR_GROUP_GLOBAL_DATA

        # Relayout tab
        self.LayoutFlushGroup(idGroup)
        self.CreateLayoutGroupDataSet(local)
        self.LayoutChanged(idGroup)


    # Creates the widgets for a single Rokoko tag, one row.
    def CreateLayoutRowControl(self, tag, idx):
        if tag is None or not tag.IsAlive():
            return

        # Get host object's icon
        bmpObj = None
        obj = tag.GetObject()
        if obj is not None:
            objName = obj.GetName()
            iconDataObj = obj.GetIcon()
            bmpObj = iconDataObj['bmp'].GetClonePart(iconDataObj['x'], iconDataObj['y'], iconDataObj['w'], iconDataObj['h'])
        else:
            objName = 'Tag not assigned'

        # Get tag's icon
        iconDataTag = tag.GetIcon()
        bmpTag = iconDataTag['bmp'].GetClonePart(iconDataTag['x'], iconDataTag['y'], iconDataTag['w'], iconDataTag['h'])

        # Add popup menu button ("...")
        self.AddButton(ID_DLGMNGR_BASE_TAG_POPUP + idx, c4d.BFH_FIT, initw=WIDTH_ADD_BUTTON, name='...')

        # Host object icon and name
        CreateLayoutAddBitmapButton(self, 0, bmpTag, tooltip='', button=False, toggle=False, flags=c4d.BFH_LEFT|c4d.BFV_CENTER)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name=tag.GetName())
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='') # spacer

        # Tag icon and name
        CreateLayoutAddBitmapButton(self, 0, bmpObj, tooltip='', button=False, toggle=False, flags=c4d.BFH_LEFT|c4d.BFV_CENTER)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name=objName)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='') # spacer

        # Tag type combo box
        self.AddComboBox(ID_DLGMNGR_BASE_TAG_RIG_TYPES + idx, c4d.BFH_SCALEFIT)
        bcRigTypes = tag.GetDataInstance().GetContainerInstance(ID_TAG_BC_RIG_TYPES)
        for idxRigType, value in bcRigTypes:
            self.AddChild(ID_DLGMNGR_BASE_TAG_RIG_TYPES + idx, idxRigType, value)

        # Data combo box
        self.AddComboBox(ID_DLGMNGR_BASE_TAG_DATA_SETS + idx, c4d.BFH_SCALEFIT)
        bcDataSets = tag.GetDataInstance().GetContainerInstance(ID_TAG_BC_DATASETS)
        for idxDataSet, value in bcDataSets:
            self.AddChild(ID_DLGMNGR_BASE_TAG_DATA_SETS + idx, idxDataSet, value)

        # Enttity combo box
        self.AddComboBox(ID_DLGMNGR_BASE_TAG_ACTORS + idx, c4d.BFH_SCALEFIT)
        bcDataSets = tag.GetDataInstance().GetContainerInstance(ID_TAG_BC_ACTORS)
        for idxActor, value in bcDataSets:
            self.AddChild(ID_DLGMNGR_BASE_TAG_ACTORS + idx, idxActor, value)

        # "Select for Player" checkbox
        self.AddCheckbox(ID_DLGMNGR_BASE_DATA_SET_ENABLED + idx, c4d.BFH_CENTER, initw=0, inith=0, name='')


    # Creates all widgets on a "Tags" tab.
    def CreateLayoutGroupControl(self):
        if self.GroupBegin(ID_DLGMNGR_GROUP_CONTROL, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=1): # Tab group

            CreateLayoutAddGroupBar(self, 'Tags')

            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=1, inith=80): # Tags

                scrollFlags = c4d.SCROLLGROUP_VERT | c4d.SCROLLGROUP_AUTOVERT | c4d.SCROLLGROUP_NOVGAP
                if self.ScrollGroupBegin(ID_DLGMNGR_SCROLL_LOCAL_DATA, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, scrollFlags, initw=0, inith=0): # Scroll tag rows

                    if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=11): # Tag rows
                        self.GroupBorderSpace(10, 2, 0, 0)

                        # Heading

                        # Tags "+" button ("Create Scene" and such)
                        self.AddButton(ID_DLGMNGR_TAGS_POPUP, c4d.BFH_LEFT, initw=WIDTH_ADD_BUTTON, inith=0, name='+')

                        # Column headings
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=30, name='') # spacer
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Tag')
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=20, name='') # spacer
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=30, name='') # spacer
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Object')
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=20, name='') # spacer
                        self.AddStaticText(0, c4d.BFH_LEFT, initw=150, name='Rig Type')
                        self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=100, name='Live/Clip')
                        self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=100, name='Actor')
                        self.AddStaticText(0, c4d.BFH_RIGHT, initw=23, name='Sel')

                        # Iterate all tags in current document
                        if self._tags is not None and len(self._tags) > 0:
                            for idxTag, tag in enumerate(self._tags):
                                # Add a row with widgets per tag
                                self.CreateLayoutRowControl(tag, idxTag)
                        else:
                            self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='No Rokoko tags found in current document.')
                    self.GroupEnd() # Tag rows
                self.GroupEnd() # Scroll tag rows
            self.GroupEnd() # Tags

            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_BOTTOM, title='', cols=8): # Bottom row
                self.GroupBorderSpace(10, 0, 0, 0)

                # Project scale
                self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name='Project Scale')
                self.AddEditNumberArrows(ID_DLGMNGR_PROJECT_SCALE, c4d.BFH_LEFT, initw=60)

                self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=10, name='') # spacer

                # Assign unassigned tags to live connection
                self.AddButton(ID_DLGMNGR_ASSIGN_UNASSIGNED_TAGS, c4d.BFH_RIGHT, initw=150, inith=0, name='Unassigned to Live')

                self.AddStaticText(0, c4d.BFH_RIGHT, initw=10, name='') # spacer

                # Select buttons
                self.AddButton(ID_DLGMNGR_SELECT_ALL_TAGS, c4d.BFH_RIGHT, initw=150, inith=0, name='Select All')
                self.AddButton(ID_DLGMNGR_DESELECT_ALL_TAGS, c4d.BFH_RIGHT, initw=150, inith=0, name='Deselect All')
                self.AddButton(ID_DLGMNGR_INVERT_SELECTION, c4d.BFH_RIGHT, initw=150, inith=0, name='Invert Selection')
            self.GroupEnd() # Bottom row
        self.GroupEnd() # Tab group


    # Relayouts (or updates) the "Tags" tab.
    def UpdateLayoutGroupControl(self):
        self.LayoutFlushGroup(ID_DLGMNGR_GROUP_CONTROL)
        self.CreateLayoutGroupControl()
        self.LayoutChanged(ID_DLGMNGR_GROUP_CONTROL)


    # Creates all widgets on a "Player" tab.
    def CreateLayoutGroupLive(self):
        if self.GroupBegin(ID_DLGMNGR_GROUP_PLAYER, flags=c4d.BFH_SCALEFIT | c4d.BFV_FIT, title='', cols=1): # Tab group

            CreateLayoutAddGroupBar(self, 'Player')

            wButton = c4d.gui.SizePix(200)
            hButton = c4d.gui.SizePix(50)

            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=2): # Start
                self.GroupBorderSpace(10, 2, 0, 0)

                # Start/Stop Player button
                self.AddButton(ID_DLGMNGR_PLAYER_START_STOP, c4d.BFH_LEFT, initw=150, name='Start Player')

                # Radio button group to select involved tags
                self.AddRadioGroup(ID_DLGMNGR_PLAYER_TAG_SELECTION, c4d.BFH_LEFT, rows=1)
                self.AddChild(ID_DLGMNGR_PLAYER_TAG_SELECTION, 0, 'All')
                self.AddChild(ID_DLGMNGR_PLAYER_TAG_SELECTION, 1, 'Selected')
                self.AddChild(ID_DLGMNGR_PLAYER_TAG_SELECTION, 2, 'Live')
                self.AddChild(ID_DLGMNGR_PLAYER_TAG_SELECTION, 3, 'Clips')
            self.GroupEnd() # Start

            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=1): # Player
                self.GroupBorderSpace(10, 0, 0, 0)

                # Row "Active Tags"
                # TODO: This needs to be a horizontal scroll group
                if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=2):
                    self.AddStaticText(ID_DLGMNGR_PLAYER_ACTIVE_TAGS_LABEL, c4d.BFH_LEFT, initw=0, name='Active Tags:')
                    self.AddStaticText(ID_DLGMNGR_PLAYER_ACTIVE_TAGS, c4d.BFH_SCALEFIT, initw=0, name='None')
                self.GroupEnd()

                if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=5): # Scrub bar and player buttons
                    # Scrub bar
                    self.AddEditSlider(ID_DLGMNGR_PLAYER_CURRENT_FRAME, flags=c4d.BFH_SCALEFIT)

                    # First Frame
                    CreateLayoutAddBitmapButton(self, ID_DLGMNGR_PLAYER_FIRST_FRAME, idIcon1=12501, tooltip='First Frame', button=True, toggle=False, flags=c4d.BFH_RIGHT|c4d.BFV_CENTER)

                    # Play/Pause
                    self._bitmapButtonPlayPause = CreateLayoutAddBitmapButton(self, ID_DLGMNGR_PLAYER_PAUSE, idIcon1=12412, idIcon2=12002, tooltip='Play/Pause', button=True, toggle=True, flags=c4d.BFH_RIGHT|c4d.BFV_CENTER)

                    # Resync with live stream
                    CreateLayoutAddBitmapButton(self, ID_DLGMNGR_PLAYER_SYNC_WITH_LIVE, idIcon1=465001024, tooltip='Play Live', button=True, toggle=False, flags=c4d.BFH_RIGHT|c4d.BFV_CENTER)

                    # Last Frame
                    CreateLayoutAddBitmapButton(self, ID_DLGMNGR_PLAYER_LAST_FRAME, idIcon1=12502, tooltip='Last Frame', button=True, toggle=False, flags=c4d.BFH_RIGHT|c4d.BFV_CENTER)
                self.GroupEnd() # Scrub bar and player buttons

                if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=1): # Start/save recording
                    self.AddButton(ID_DLGMNGR_PLAYER_SAVE, c4d.BFH_SCALEFIT | c4d.BFV_CENTER, initw=0, inith=hButton, name='')
                self.GroupEnd() # Start/save recording

                # Bottom row with buffering indicator, playback rate,...
                if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=6): # Bottom row
                    # Buffering indicator
                    self.AddStaticText(ID_DLGMNGR_PLAYER_BUFFERING_LABEL, c4d.BFH_LEFT, initw=0, name='Buffering:')
                    self.AddSlider(ID_DLGMNGR_PLAYER_BUFFERING, flags=c4d.BFH_LEFT, initw=200)
                    self.Enable(ID_DLGMNGR_PLAYER_BUFFERING, False) # always disabled, only to show some movement if player is paused

                    self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=0, name='') # spacer

                    # Animate document
                    self.AddCheckbox(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT, c4d.BFH_RIGHT|c4d.BFH_SCALE, initw=0, inith=0, name='Animate Document')

                    # Playback rate
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
                self.GroupEnd() # Bottom row
            self.GroupEnd() # Player
        self.GroupEnd() # Tab group


    # Relayouts (or updates) the "Player" tab.
    def UpdateLayoutGroupLive(self):
        self.LayoutFlushGroup(ID_DLGMNGR_GROUP_PLAYER)
        self.CreateLayoutGroupLive()
        self.LayoutChanged(ID_DLGMNGR_GROUP_PLAYER)


    # Creates all widgets on a "Commandd API" tab.
    def CreateLayoutGroupCommandAPI(self):
        if self.GroupBegin(ID_DLGMNGR_GROUP_COMMAND_API, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=1): # Tab group

            CreateLayoutAddGroupBar(self, 'Command API')

            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP, title='', cols=4): # Commands
                self.GroupBorderSpace(10, 2, 0, 0)

                # Start recording
                CreateLayoutAddBitmapButton(self, ID_DLGMNGR_COMMANDAPI_START_RECORDING, idIcon1=PLUGIN_ID_COMMAND_API_ICON_RECORD_START, \
                                            tooltip='Start Recording in Studio', button=True, toggle=False, flags=c4d.BFH_SCALEFIT)

                # Stop recording
                CreateLayoutAddBitmapButton(self, ID_DLGMNGR_COMMANDAPI_STOP_RECORDING, idIcon1=PLUGIN_ID_COMMAND_API_ICON_RECORD_STOP, \
                                            tooltip='Stop Recording in Studio', button=True, toggle=False, flags=c4d.BFH_SCALEFIT)

                # Calibrate all suits
                CreateLayoutAddBitmapButton(self, ID_DLGMNGR_COMMANDAPI_CALIBRATE_ALL_SUITS, idIcon1=PLUGIN_ID_COMMAND_API_ICON_CALIBRATE_SUIT, \
                                            tooltip='Start Calibration of all Smartsuits in Studio', button=True, toggle=False, flags=c4d.BFH_SCALEFIT)

                # Restart all suits
                CreateLayoutAddBitmapButton(self, ID_DLGMNGR_COMMANDAPI_RESET_ALL_SUITS, idIcon1=PLUGIN_ID_COMMAND_API_ICON_RESTART_SUIT, \
                                            tooltip='Restart All Smartsuits', button=True, toggle=False, flags=c4d.BFH_SCALEFIT)
            self.GroupEnd() # Commands
        self.GroupEnd() # Tab group


    # Relayouts (or updates) the "Command API" tab.
    # Currently not needed.
    def UpdateLayoutGroupCommandAPI(self):
        self.LayoutFlushGroup(ID_DLGMNGR_GROUP_COMMAND_API)
        self.CreateLayoutGroupCommandAPI()
        self.LayoutChanged(ID_DLGMNGR_GROUP_COMMAND_API)


    # Called by C4D to draw the dialog
    def CreateLayout(self):
        self.SetTitle('Rokoko Studio Live') # dialog's window title

        self.CreateLayoutInMenu()

        if self.GroupBegin(ID_DLGMNGR_GROUP_MAIN, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=1): # Dialog main group
            self.GroupBorderSpace(5, 5, 10, 5)

            # Add the tab bar to switch dialog groups
            self._quickTab = CreateLayoutAddQuickTab(self, ID_DLGMNGR_TABS)
            self._quickTab.AppendString(ID_DLGMNGR_GROUP_CONNECTIONS, 'Connection', GetPref(ID_DLGMNGR_GROUP_CONNECTIONS))
            self._quickTab.AppendString(ID_DLGMNGR_GROUP_GLOBAL_DATA, 'Global Clips', GetPref(ID_DLGMNGR_GROUP_GLOBAL_DATA))
            self._quickTab.AppendString(ID_DLGMNGR_GROUP_LOCAL_DATA, 'Project Clips', GetPref(ID_DLGMNGR_GROUP_LOCAL_DATA))
            self._quickTab.AppendString(ID_DLGMNGR_GROUP_CONTROL, 'Tags', GetPref(ID_DLGMNGR_GROUP_CONTROL))
            self._quickTab.AppendString(ID_DLGMNGR_GROUP_PLAYER, 'Player', GetPref(ID_DLGMNGR_GROUP_PLAYER))
            self._quickTab.AppendString(ID_DLGMNGR_GROUP_COMMAND_API, 'Command API', GetPref(ID_DLGMNGR_GROUP_COMMAND_API))

            if self.GroupBegin(0, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, title='', cols=1): # Tabs
                self.GroupSpace(0, 15)

                # Add all six tabs
                self.CreateLayoutGroupConnections()
                self.CreateLayoutGroupDataSet(local=False)
                self.CreateLayoutGroupDataSet(local=True)
                self.CreateLayoutGroupControl()
                self.CreateLayoutGroupLive()
                self.CreateLayoutGroupCommandAPI()
            self.GroupEnd() # Tabs
        self.GroupEnd() # Dialog main group

        self.CreateLayoutAddMenu()

        # Hide _all_ tabs here. The size of the layout after CreateLayout()
        # will determine the minimum size of the dialog, when first opened.
        # It will then scale up according to its content, but it won't scale
        # down according to content (and there are no means to do so in C4D's API).
        # As the dialog's supposed to start as small as possible, all groups get hidden.
        #
        # TODO: Maybe this is the cause of dialog initialization issues on Mac???
        self.HideElement(ID_DLGMNGR_GROUP_CONNECTIONS, True)
        self.HideElement(ID_DLGMNGR_GROUP_GLOBAL_DATA, True)
        self.HideElement(ID_DLGMNGR_GROUP_LOCAL_DATA, True)
        self.HideElement(ID_DLGMNGR_GROUP_CONTROL, True)
        self.HideElement(ID_DLGMNGR_GROUP_PLAYER, True)
        self.HideElement(ID_DLGMNGR_GROUP_COMMAND_API, True)
        return True


    # Update tab groups visibility according to tab states.
    def UpdateGroupVisibility(self, forcePlayerOpen=False):
        # Store tab states in preferences
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

        # Hide tab groups according to tab states
        self.HideElement(ID_DLGMNGR_GROUP_CONNECTIONS, not GetPref(ID_DLGMNGR_GROUP_CONNECTIONS))
        self.HideElement(ID_DLGMNGR_GROUP_CONNECTION_DATA, not IsConnected())
        self.HideElement(ID_DLGMNGR_GROUP_CONNECTION_DATA_CONTENT, not IsConnected())
        self.HideElement(ID_DLGMNGR_GROUP_GLOBAL_DATA, not GetPref(ID_DLGMNGR_GROUP_GLOBAL_DATA))
        self.HideElement(ID_DLGMNGR_GROUP_LOCAL_DATA, not GetPref(ID_DLGMNGR_GROUP_LOCAL_DATA))
        self.HideElement(ID_DLGMNGR_GROUP_CONTROL, not GetPref(ID_DLGMNGR_GROUP_CONTROL))
        self.HideElement(ID_DLGMNGR_GROUP_PLAYER, not GetPref(ID_DLGMNGR_GROUP_PLAYER))
        self.HideElement(ID_DLGMNGR_GROUP_COMMAND_API, not GetPref(ID_DLGMNGR_GROUP_COMMAND_API))

        # Announce layout change
        self.LayoutChanged(ID_DLGMNGR_GROUP_MAIN)


    # En-/Disable Player buttons.
    def EnableLiveButtons(self):
        # Gather some state information
        live = g_thdListener._receive
        allowWhileNotLive = not live and (self._tags is not None and len(self._tags) > 0)
        isConnected = IsConnected()
        tagsExist = self._tags is not None

        # Set label of "Start/Stop Player" button
        if live:
            self.SetString(ID_DLGMNGR_PLAYER_START_STOP, 'Stop Player')
        else:
            self.SetString(ID_DLGMNGR_PLAYER_START_STOP, 'Start Player')

        # Set label of "Start/Stop Recording..." button
        if self._buttonRecordState:
            self.SetString(ID_DLGMNGR_PLAYER_SAVE, 'Stop Recording...')
        else:
            self.SetString(ID_DLGMNGR_PLAYER_SAVE, 'Start Recording')

        # Toggle state of "Play/Pause" button
        self._bitmapButtonPlayPause.SetToggleState(g_thdListener._play)

        # Disable tag parameters of tags involved in playback
        tagsLive = g_thdListener.GetTagConsumers()
        anyLiveDataSet = False # Is live connection involved
        if tagsExist:
            # Iterate all tags
            idConnected = GetConnectedDataSetId()
            for idxTag, tag in enumerate(self._tags):
                # Tag type combo box
                self.Enable(ID_DLGMNGR_BASE_TAG_RIG_TYPES + idxTag, allowWhileNotLive)

                # Tag selection Manager
                self.Enable(ID_DLGMNGR_BASE_DATA_SET_ENABLED + idxTag, allowWhileNotLive)

                if not tag.IsAlive():
                    continue

                # If tag is _not_ involved in playback, do not allow to switch data set or actor.
                # This is not, because the user could break something, but because during playback
                # it is currently not possible to add another tag to the list of involved tags.
                # If player is inactive, tagsLive is empty and all tags get addressed.
                if tag not in tagsLive:
                    self.Enable(ID_DLGMNGR_BASE_TAG_DATA_SETS + idxTag, allowWhileNotLive)
                    self.Enable(ID_DLGMNGR_BASE_TAG_ACTORS + idxTag, allowWhileNotLive)

                if tag[ID_TAG_DATA_SET] == idConnected and tag in tagsLive:
                    anyLiveDataSet = True

        # Connections "+" popup menu button
        # Currently not in GUI, always exactly one connection
        self.Enable(ID_DLGMNGR_CONNECTION_POPUP, not live)

        # Assign unassigned tags to live connection
        self.Enable(ID_DLGMNGR_ASSIGN_UNASSIGNED_TAGS, isConnected and not live and tagsExist and len(self._tags) > 0)

        # Select buttons
        self.Enable(ID_DLGMNGR_SELECT_ALL_TAGS, allowWhileNotLive)
        self.Enable(ID_DLGMNGR_DESELECT_ALL_TAGS, allowWhileNotLive)
        self.Enable(ID_DLGMNGR_INVERT_SELECTION, allowWhileNotLive)

        # Player widgets
        self.Enable(ID_DLGMNGR_PLAYER_TAG_SELECTION, allowWhileNotLive)
        self.Enable(ID_DLGMNGR_PLAYER_BUFFERING_LABEL, not allowWhileNotLive)
        self.Enable(ID_DLGMNGR_PLAYER_ACTIVE_TAGS_LABEL, not allowWhileNotLive)
        self.Enable(ID_DLGMNGR_PLAYER_SAVE, live and isConnected and anyLiveDataSet)
        self.Enable(ID_DLGMNGR_PLAYER_FIRST_FRAME, live)
        self.Enable(ID_DLGMNGR_PLAYER_LAST_FRAME, live)
        self.Enable(ID_DLGMNGR_PLAYER_PAUSE, live)
        self.Enable(ID_DLGMNGR_PLAYER_CURRENT_FRAME, live)
        self.Enable(ID_DLGMNGR_PLAYER_ACTIVE_TAGS, live)
        self.Enable(ID_DLGMNGR_PLAYER_SYNC_WITH_LIVE, live and not g_thdListener._inSync)


    # En-/Disable the entire Manager dialog.
    # Happens for example, when the "Save Recording" child dialog gets opened.
    def EnableDialog(self, enable):
        self.Enable(ID_DLGMNGR_CONNECTIONS_IN_MENU, enable)
        self.Enable(ID_DLGMNGR_GROUP_MAIN, enable)


    # Called by C4D to initialize widget values.
    def InitValues(self):
        tagsLive = g_thdListener.GetTagConsumers()
        bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
        idConnected = GetConnectedDataSetId()

        # Iterate all connections
        idxConnection = 0
        for id, bcConnection in bcConnections:
            # Auto connect checkbox
            self.SetBool(ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT + idxConnection, bcConnection[ID_BC_DATASET_LIVE_AUTOCONNECT])

            # Determine connection status icon ID
            idIcon = 465003508
            if bcConnection.GetId() == idConnected:
                # The connected data set
                statusConnection = g_thdListener.GetConnectionStatus()
                if statusConnection == 1:
                    idIcon = 465001743
                elif statusConnection == 2:
                    idIcon = 465001740

                # Update connection sub group displaying connection's content
                self.UpdateLayoutGroupConnectedDataSet()

                # Connect button label
                self.SetString(ID_DLGMNGR_BASE_CONNECTION_CONNECT + idxConnection, 'Disconnect')
            else:
                # All disconnected data sets
                # Connect button label
                self.SetString(ID_DLGMNGR_BASE_CONNECTION_CONNECT + idxConnection, 'Connect')

            # Connect/Disconnect button per connection, disabled when connecting
            self.Enable(ID_DLGMNGR_BASE_CONNECTION_CONNECT + idxConnection, not self._connecting)

            # Set connection status button to current status' dot image
            icon = c4d.gui.GetIcon(idIcon)
            bmpIcon = icon['bmp'].GetClonePart(icon['x'], icon['y'], icon['w'], icon['h'])
            self._bitmapButtonsPerConnectionStatus[idxConnection].SetImage(bmpIcon)

            idxConnection += 1

        # All listed tags
        if self._tags is not None and len(self._tags) > 0:
            # Iterate all tags in current document
            for idxTag, tag in enumerate(self._tags):
                if not tag.IsAlive():
                    continue

                # Combo boxes and selection state
                bcTag = tag.GetDataInstance()
                self.SetBool(ID_DLGMNGR_BASE_DATA_SET_ENABLED + idxTag, bcTag.GetBool(ID_TAG_SELECTED_IN_MANAGER))
                self.SetInt32(ID_DLGMNGR_BASE_TAG_RIG_TYPES + idxTag, bcTag.GetInt32(ID_TAG_RIG_TYPE))
                self.SetInt32(ID_DLGMNGR_BASE_TAG_DATA_SETS + idxTag, bcTag.GetInt32(ID_TAG_DATA_SET))
                self.SetInt32(ID_DLGMNGR_BASE_TAG_ACTORS + idxTag, bcTag.GetInt32(ID_TAG_ACTORS))

        # Select involved tags radio buttons
        playChoice = GetPref(ID_DLGMNGR_PLAYER_TAG_SELECTION)
        if playChoice is None:
            SetPref(ID_DLGMNGR_PLAYER_TAG_SELECTION, 0)
            playChoice = 0
        self.SetInt32(ID_DLGMNGR_PLAYER_TAG_SELECTION, playChoice)

        # Scrub bar
        idxFrameCurrent, numFrames = g_thdListener.GetCurrentFrameNumber()
        maxSlider = (1 + numFrames // 100) * 100
        self.SetInt32(ID_DLGMNGR_PLAYER_CURRENT_FRAME, idxFrameCurrent, min=0, max=maxSlider, min2=0, max2=maxSlider)

        # Playback rate
        playbackRate = GetPref(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED)
        # TODO: Cleanup pref init
        if playbackRate is None:
            SetPref(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, 2)
            playbackRate = 2
        self.SetInt32(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, playbackRate)

        # Animate document checkbox
        animateDocument = GetPref(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT)
        # TODO: Cleanup pref init
        if animateDocument is None:
            SetPref(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT, False)
            animateDocument = False
        self.SetInt32(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT, animateDocument)

        # Project scale
        self.SetFloat(ID_DLGMNGR_PROJECT_SCALE, GetProjectScale(), step=0.1, min=0.0001)

        # Update list of involved tags ("Active Tags")
        if len(tagsLive):
            namesActiveTags = ''
            for tag in tagsLive:
                namesActiveTags += tag.GetName() + ', '
            namesActiveTags = namesActiveTags[:-2]
            self.SetString(ID_DLGMNGR_PLAYER_ACTIVE_TAGS, namesActiveTags)
        else:
            self.SetString(ID_DLGMNGR_PLAYER_ACTIVE_TAGS, 'None')

        # Update tabs visibility
        self.UpdateGroupVisibility()

        # Update widgets in menu row
        self.UpdateLayoutInMenu()

        # Update enabling of Player buttons
        self.EnableLiveButtons()
        return True


    # Reaction to BFM_ACTION.
    # The scrub bar slider needs a little extra attention,
    # because we do not only want it to set a frame index,
    # but to also have the motion data visualized in view port during drag.
    _lastEvent = 0
    def MessageBfmAction(self, msg):
        # Check widget ID of BFM_ACTION. We are interested in the scrub bar, only.
        if msg[c4d.BFM_ACTION_ID] != ID_DLGMNGR_PLAYER_CURRENT_FRAME:
            return

        # Pause the Player
        self.CommandPause(force=True)

        # Reduce the amount of viewport updates.
        # If the last event is less than 50ms back, we'll simply skip the event.
        # TODO: This has the negative side effect, releasing the scrub bar slider is a bit imprecise.
        now = c4d.GeGetTimer()
        if now - self._lastEvent <= 50:
            return

        # If user enabled "Animate Document" forward document time
        idxFrameCurrent = int(msg[c4d.BFM_ACTION_VALUE])
        if GetPref(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT):
            doc = c4d.documents.GetActiveDocument()
            tMax = doc.GetMaxTime().Get()
            tDispatch = 0.01667 * idxFrameCurrent # TODO: use Studio's FPS here? Which if multiple data sets with differing FPS.
            t = c4d.BaseTime(tDispatch % tMax)
            doc.SetTime(t)

        # Remove any unprocessed frames in tag's inbound queues,
        # so dispatched frame will be next to be consumed during tag's Execute().
        g_thdListener.FlushTagConsumers()
        g_thdListener.DispatchFrame(idxFrameCurrent, event=False)

        # Trigger execution of scene and redraw viewport
        c4d.DrawViews(c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW | c4d.DRAWFLAGS_NO_THREAD)

        self._lastEvent = now


    # Called by C4D to send a message to the dialog.
    def Message(self, msg, result):
        # Decode message (currently only interested in BFM_ACTION from scrub bar)
        idMsg = msg.GetId()
        if idMsg == c4d.BFM_ACTION:
            self.MessageBfmAction(msg)

        return c4d.gui.GeDialog.Message(self, msg, result) # pass message on to parenting classes


    # Reaction to PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAGS.
    # Send if something significant happened in current scene.
    # For example a new Rokoko tag, document changed, ...
    def CoreMessageUpdateTags(self):
        # Gather all Rokoko tags from current document
        self._tags = GetTagList()

        # Upate "Project Clips" library tab (for example in case of document change)
        self.UpdateLayoutGroupDataSet(local=True)

        # Upate "Tags" tab (for example in case of document change)
        self.UpdateLayoutGroupControl()

        # Initialize widget values
        self.InitValues()

    # Reaction to PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAG_PARAMS and
    #             PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_LIVE_DATA_CHANGE.
    # Send if a tag's parameters changed,
    # which may also happen due to content of live connection changing.
    def CoreMessageUpdateTagParams(self):
        # Upate "Tags" tab (for example in case of document change)
        self.UpdateLayoutGroupControl()

        # Initialize widget values
        self.InitValues()


    # Reaction to PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_BUFFER_PULSE.
    # Send by the listener threads every few received frames to have
    # the Manager dialog show some motion (and thus indicate to user, it's still buffering),
    # even if the user paused actual playback.
    _cntBuffering = 0
    def CoreMessageBufferPulse(self):
        # If Player is inactive, exit
        if not g_thdListener._receive:
            return

        # Advance buffering indicator sliders
        self._cntBuffering = (self._cntBuffering + 1) % 10
        self.SetInt32(ID_DLGMNGR_PLAYER_BUFFERING, self._cntBuffering, min=0, max=9, min2=0, max2=9)
        self.SetInt32(ID_DLGMNGR_PLAYER_BUFFERING_IN_MENU, self._cntBuffering % 5, min=0, max=4, min2=0, max2=4)


    # Reaction to PLUGIN_ID_COREMESSAGE_MANAGER_CURRENT_FRAME_NUMBER.
    # During playback, player sends this event every few frames so Player can update
    # scrub bar position and length.
    # Note: This event gets (and has to be) muted, when the Player is paused.
    #       Otherwise the scrub bar would constantly update, while the user tries to interact with it.
    def CoreMessageCurrentFrameNumber(self, msg):
        # If player is paused, do nothing
        if not g_thdListener._play:
            return

        if g_thdListener._receive:
            # Use frame index and length received from player
            idxFrameCurrent = GetCoreMessageParam23(msg)
            numFrames = GetCoreMessageParam23(msg, id=c4d.BFM_CORE_PAR2)
        else:
            # Reset scrub bar
            idxFrameCurrent = 0
            numFrames = 0

        # It looks strange, if the scrub bar is constantly flickering
        # at the end of the scrub bar during live playback.
        # Therefore slider length is increased in chunks of hundred
        # frame to give the slider some space for "breathing"
        maxSlider = (1 + numFrames // 100) * 100

        # Update scrub bar
        self.SetInt32(ID_DLGMNGR_PLAYER_CURRENT_FRAME, idxFrameCurrent, min=0, max=maxSlider, min2=0, max2=maxSlider)


    # Reaction to PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_STATUS_CHANGE.
    # Send by listener thread, whenever the status of the live connection changes.
    # For example Studio stopped sending frames, connecting phase ended,...
    def CoreMessageConnectionStatusChange(self):
        # Connecting phase ended, Connect/Disconnect" buttons can be reenabled
        self._connecting = False

        # Initialize widget values
        self.InitValues()

        # Update widgets in menu row (status dot)
        self.UpdateLayoutInMenu()


    # Reaction to PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_PLAYBACK_STATUS_CHANGE.
    # Send by player upon status change (play, Pause, stop)
    def CoreMessagePlayerStatusChange(self):
        # Initialize widget values
        self.InitValues()

        # Reset buffering indicator sliders
        self.SetInt32(ID_DLGMNGR_PLAYER_BUFFERING, 0, min=0, max=9, min2=0, max2=9)
        self.SetInt32(ID_DLGMNGR_PLAYER_BUFFERING_IN_MENU, 0, min=0, max=4, min2=0, max2=4)


    # C4D (or other modules of Rokoko Studio Live plugin) calls CoreMessage() to
    # send an event message to the dialog.
    # Using registered plugin IDs custom event messages can be send via SpecialEventAdd().
    #
    # In context of the main thread all kinds of events are received here.
    def CoreMessage(self, id, msg):
        # Decode event message ID
        if id == PLUGIN_ID_COREMESSAGE_MANAGER:
            # Decode message sub ID (first of two event parameters)
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
            # Decode message sub ID (first of two event parameters)
            subId = GetCoreMessageParam23(msg)
            if subId == CM_SUBID_CONNECTION_STATUS_CHANGE:
                self.CoreMessageConnectionStatusChange()
            elif subId == CM_SUBID_CONNECTION_LIVE_DATA_CHANGE:
                self.CoreMessageUpdateTagParams()
            return True
        return c4d.gui.GeDialog.CoreMessage(self, id, msg)


    # Called by C4D when the dialog is about to be closed in whatever way.
    # Returning True would deny the "close request" and the dialog stayed open.
    def AskClose(self):
        # If "Save Recording" dialog is still open, do not allow to close Manager dialog
        if self._dlgChild is not None and self._dlgChild.IsOpen():
            c4d.gui.MessageDialog('Save Dialog is still open.', c4d.GEMB_ICONEXCLAMATION)
            return True # Dialog will NOT be closed

        # If Player is active, ask user what to do
        if g_thdListener._receive:
            result = c4d.gui.MessageDialog('Player is still running.\nDialog will be closed.\nStop player?\n', c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_YESNOCANCEL)
            if result == c4d.GEMB_R_YES:
                # User wants to stop player
                self.CommandPlayerExit()
            elif result == c4d.GEMB_R_CANCEL:
                # User decided to keep Manager dialog open
                return True # Dialog will NOT be closed

        # Close manager dialog
        return False


    # User pressed "+" button on "Connection" tab.
    # Open dialog to create a new connection data set (see rokoko_dialog_edit_connection)
    # and stores resulting connection in preferences.
    def CommandConnectionsPopup(self):
        # Open "Edit Connection..." dialog (dialog will create default connection data set itself)
        dlgEdit = DialogEditConnection(None)
        resultOpen = dlgEdit.Open(c4d.DLG_TYPE_MODAL_RESIZEABLE)
        if resultOpen == False:
            return # failed to open dialog
        result, bcConnectionNew = dlgEdit.GetResult()
        if result == False:
            return # user cancelled dialog

        # Store new connection in preferences
        GetPrefsContainer(ID_BC_CONNECTIONS).SetContainer(bcConnectionNew.GetId(), bcConnectionNew.GetClone(c4d.COPYFLAGS_NONE))

        # Update "Connections" tab
        self.UpdateLayoutGroupConnections()

        # Initialize widget values
        self.InitValues()

        # Update widgets in menu row (connection combo box)
        self.UpdateLayoutInMenu()


    # User pressed "..." button on a single connection in "Connection" tab.
    def CommandConnectionPopup(self, id):
        # Get connection data set belonging to the button
        idxConnection = id - ID_DLGMNGR_BASE_CONNECTION_POPUP
        bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
        idxConnected = bcConnections.FindIndex(GetConnectedDataSetId())

        # Create popup menu
        bcMenu = c4d.BaseContainer()
        idConnected = GetConnectedDataSetId()
        idConnection = bcConnections.GetIndexId(idxConnection)

        # Order of options depends a bit on connection state
        if idConnected == idConnection:
            bcMenu.InsData(ID_SUBMENU_CONNECTION_CREATE_SCENE, 'Create Scene')
            bcMenu.InsData(0, '')
            bcMenu.InsData(ID_SUBMENU_CONNECTION_EDIT, 'Edit...&d&')
            # bcMenu.InsData(ID_SUBMENU_CONNECTION_REMOVE, 'Remove&d&') # currently always exactly one connection, can not be removed
            bcMenu.InsData(0, '')
            bcMenu.InsData(ID_SUBMENU_CONNECTION_CONNECT, 'Disonnect')
        else:
            bcMenu.InsData(ID_SUBMENU_CONNECTION_CONNECT, 'Connect')
            bcMenu.InsData(0, '')
            bcMenu.InsData(ID_SUBMENU_CONNECTION_CREATE_SCENE, 'Create Scene&d&')
            bcMenu.InsData(0, '')
            bcMenu.InsData(ID_SUBMENU_CONNECTION_EDIT, 'Edit...')
            # bcMenu.InsData(ID_SUBMENU_CONNECTION_REMOVE, 'Remove') # currently always exactly one connection, can not be removed

        # Show popup menu
        result = c4d.gui.ShowPopupDialog(cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)

        # Decode menu entry clicked on
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


    # Connect a connection data set (referenced by index of connection in dialog).
    # The listener thread will be started.
    def Connect(self, idxConnection):
        # Disable all connection button until connection is established
        self._connecting = True

        # If player is active, stop it
        if g_thdListener._receive:
            self.CommandPlayerExit()

        if idxConnection != 999999:
            # Get ID of connection data set for given index
            bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
            idConnection = bcConnections.GetIndexId(idxConnection)
        else:
            # Disconnect request
            idConnection = -1

        idConnected = GetConnectedDataSetId()

        # Connect/Disconnect is a toggle button
        # If it's pressed on a currently connected connection, it's a disconnect
        if idConnected == idConnection:
            idConnected = -1
        else:
            # If already connected and connect request is for another connection data set,
            # disconnect the old connection first.
            if idConnected != -1 and idConnection != -1:
                c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_DISCONNECT)
            idConnected = idConnection

        if idConnected == -1:
            # Disconnect request
            # Exit the player
            self.CommandPlayerExit()

            # Ask listener thread to disconnect
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_DISCONNECT)
        else:
            # Connect request
            # Ask listener thread to disconnect
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_CONNECT, idConnected)

        # Initialize widget values
        self.InitValues()

        # Update widgets in menu row (status dot and connection combo box)
        self.UpdateLayoutInMenu()

        # Update player interface
        self.EnableLiveButtons()


    # Remove a connection data set (referenced by index of connection in dialog) from preferences.
    # Currently this is not used, as there is always exactly one connection.
    def RemoveConnection(self, idxConnection):
        # Get ID of connection data set for given index
        id = GetPrefsContainer(ID_BC_CONNECTIONS).GetIndexId(idxConnection)

        # Remove connection data set from preferences
        RemoveConnection(id)

        # Update connection library in "Connections" tab
        self.UpdateLayoutGroupConnections()

        # Initialize widget values
        self.InitValues()

        # Update widgets in menu row (status dot and connection combo box)
        self.UpdateLayoutInMenu()


    # Open a dialog to edit the parameters of a connection data set.
    def EditConnection(self, idxConnection):
        # Get connection data set for given index
        id = GetPrefsContainer(ID_BC_CONNECTIONS).GetIndexId(idxConnection)
        bcConnection = GetPrefsContainer(ID_BC_CONNECTIONS).GetContainer(id)
        idConnection = bcConnection.GetId()

        # Open "Edit Connection..." dialog
        dlgEdit = DialogEditConnection(bcConnection)
        resultOpen = dlgEdit.Open(c4d.DLG_TYPE_MODAL_RESIZEABLE)
        if resultOpen == False:
            return # failed to open dialog
        result, bcConnectionNew = dlgEdit.GetResult()
        if result == False:
            return # user cancelled dialog

        # Remove previous connection data set from preferences
        RemoveConnection(idConnection)

        # Sttore edited connection data set in preferences
        GetPrefsContainer(ID_BC_CONNECTIONS).SetContainer(bcConnectionNew.GetId(), bcConnectionNew)

        # Update connection library in "Connections" tab
        self.UpdateLayoutGroupConnections()

        # Initialize widget values
        self.InitValues()

        # Update widgets in menu row (status dot and connection combo box)
        self.UpdateLayoutInMenu()


    # User pressed "+" button on global or project clip library tab.
    def CommandDataPopup(self, local):
        # If player is active, certain menu options get disabled
        disableItem = ''
        if g_thdListener._receive:
            disableItem = '&d&'

        # Create pop up menu
        bcMenu = c4d.BaseContainer()
        bcMenu.InsData(ID_SUBMENU_DATA_ADD_FILE, 'Add File...')
        bcMenu.InsData(ID_SUBMENU_DATA_ADD_FOLDER, 'Add Folder...')
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_DATA_REMOVE_ALL, 'Remove All' + disableItem)
        bcMenu.InsData(ID_SUBMENU_DATA_DELETE_ALL, 'Delete All...' + disableItem)

        # Show popup menu
        result = c4d.gui.ShowPopupDialog(cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)

        # Decode menu entry clicked on
        if result == ID_SUBMENU_DATA_ADD_FILE:
            self.AddDataSet(local=local, folder=False)
        elif result == ID_SUBMENU_DATA_ADD_FOLDER:
            self.AddDataSet(local=local, folder=True)
        elif result == ID_SUBMENU_DATA_REMOVE_ALL:
            self.RemoveDataSet(local=local, all=True)
        elif result == ID_SUBMENU_DATA_DELETE_ALL:
            self.RemoveDataSet(local=local, all=True, delete=True)
        elif result == 0:
            pass # menu canceled
        else:
            print('ERROR: Submenu Data unknown command:', result, local)


    # User pressed "..." button on a single data set (clip) in global or project library tab.
    def CommandDataSetPopup(self, id, local):
        # Get actual data set index and label for copy and move menu entries
        if local:
            idxDataSet = id - ID_DLGMNGR_BASE_LOCAL_DATA_POPUP
            nameTargetLib = 'Global'
        else:
            idxDataSet = id - ID_DLGMNGR_BASE_GLOBAL_DATA_POPUP
            nameTargetLib = 'Project'

        # If player is active, certain menu options get disabled
        disableItem = ''
        if g_thdListener._receive:
            disableItem = '&d&'

        # Create pop up menu
        bcMenu = c4d.BaseContainer()
        bcMenu.InsData(ID_SUBMENU_DATA_SET_CREATE_SCENE, 'Create Scene')
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_DATA_SET_EDIT, 'Edit...' + disableItem)
        bcMenu.InsData(ID_SUBMENU_DATA_SET_OPEN_DIRECTORY, 'Open Directory...')
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_DATA_SET_COPY_LOCAL, 'Copy to {0} Clips'.format(nameTargetLib))
        bcMenu.InsData(ID_SUBMENU_DATA_SET_MOVE_LOCAL, 'Move to {0} Clips'.format(nameTargetLib) + disableItem)
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_DATA_SET_REMOVE, 'Remove' + disableItem)
        bcMenu.InsData(ID_SUBMENU_DATA_SET_DELETE, 'Delete...' + disableItem)

        # Show popup menu
        result = c4d.gui.ShowPopupDialog(cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)

        # Decode menu entry clicked on
        if result == ID_SUBMENU_DATA_SET_COPY_LOCAL:
            self.DataSetChangeGlobalLocal(idxDataSet, local=local)
        elif result == ID_SUBMENU_DATA_SET_MOVE_LOCAL:
            self.DataSetChangeGlobalLocal(idxDataSet, local=local, move=True)
        elif result == ID_SUBMENU_DATA_SET_EDIT:
            self.EditDataSet(idxDataSet, local=local)
        elif result == ID_SUBMENU_DATA_SET_REMOVE:
            self.RemoveDataSet(local=local, idx=idxDataSet)
        elif result == ID_SUBMENU_DATA_SET_DELETE:
            self.RemoveDataSet(local=local, idx=idxDataSet, delete=True)
        elif result == ID_SUBMENU_DATA_SET_CREATE_SCENE:
            self.CreateSceneForDataSet(idxDataSet, local=local)
        elif result == ID_SUBMENU_DATA_SET_OPEN_DIRECTORY:
            self.DataSetOpenDirectory(local=local, idxDataSet=idxDataSet)
        elif result == 0:
            pass # menu canceled
        else:
            print('ERROR: Submenu Data Set unknown command:', local, result)


    # In Manager dialog all (active) widgets belonging to a single data set
    # have an ID as sum of a base ID and data sets index in the dialog
    # (which happens to be the index of the data set in its library's BaseContainer).
    # This function returns a data set container for this index.
    def GetDataSetByDialogIndex(self, local, idxDataSet):
        # Get data set for given index in dialog from specified library
        if local:
            bcDataSets = GetLocalDataSets()
        else:
            bcDataSets = GetPrefsContainer(ID_BC_DATA_SETS)
        idDataSet = bcDataSets.GetIndexId(idxDataSet)
        bcDataSet = bcDataSets.GetContainer(idDataSet)
        return bcDataSet


    # Copy (or move) a data set (referenced by dialog index)
    # from global to project's clip library (or vice versa).
    def DataSetChangeGlobalLocal(self, idxDataSet, local, move=False):
        # Get data set for given index in dialog from library it's currently in
        bcDataSet = self.GetDataSetByDialogIndex(local, idxDataSet)

        # Copy (or move) data set into the other library
        self.DataSetChangeGlobalLocalBC(bcDataSet, move=move)


    # Copy (or move) a data set container from global to project's clip library (or vice versa).
    def DataSetChangeGlobalLocalBC(self, bcDataSet, move=False):
        isLocal = bcDataSet[ID_BC_DATASET_IS_LOCAL]
        filename = bcDataSet[ID_BC_DATASET_FILENAME]
        idDataSet = bcDataSet.GetId()

        bcDataSetNew = bcDataSet.GetClone(c4d.COPYFLAGS_NONE)
        isLocalNew = not isLocal
        filenameNew = filename

        pathDoc = c4d.documents.GetActiveDocument().GetDocumentPath()

        if isLocalNew:
            # Direction Global -> Project, old filename is absolute
            filenameDst = filename # new complete destination file path for fileaction
            filenameNew = filename # new destination path possibly relative to project folder stored in data set

            # Assume, user will want the file copied/moved, create destination path
            if pathDoc is not None and len(pathDoc) > 1:
                _, filenameDst = os.path.split(filename)
                filenameNew = os.path.join('.', filenameDst)
                filenameDst = os.path.join(pathDoc, filenameDst)

            # If motion data file not already in project folder
            if filenameDst != filename:
                # Offer to copy or move the motion data file

                # Create dialog message
                if move:
                    msg = 'Move data set file to project folder?\n'
                    msg += 'From: {0}\n'.format(filename)
                    msg += 'To: {0}\n'.format(filenameDst)
                    msg += 'Yes: Move file\n'
                    msg += 'No: Move data set reference, only\n'
                    msg += 'Cancel: Abort'
                else:
                    msg = 'Copy data set file to project folder?\n'
                    msg += 'From: {0}\n'.format(filename)
                    msg += 'To: {0}\n'.format(filenameDst)
                    msg += 'Yes: Copy file\n'
                    msg += 'No: Copy data set reference, only\n'
                    msg += 'Cancel: Abort'

                # Open question dialog
                result = c4d.gui.MessageDialog(msg, c4d.GEMB_YESNOCANCEL)

                # Decode user choice
                if result == c4d.GEMB_R_YES:
                    if move:
                        if DO_FILE_ACTION:
                            shutil.move(filename, filenameDst)
                    else:
                        if DO_FILE_ACTION:
                            shutil.copyfile(filename, filenameDst)

                elif result == c4d.GEMB_R_NO:
                    # User decided to stay with the original file
                    filenameNew = filename # revert above assumption and use the previously set path

                elif result == c4d.GEMB_R_CANCEL:
                    return # user cancelled the dialog, don't do anything
        else:
            # Direction Project -> Global, old filename may be project relative
            # Resolve project relative path
            if pathDoc is not None and len(pathDoc) > 1 and filename[0] == '.' or os.sep not in filename:
                filenameNew = filename
                if filenameNew[0] == '.':
                    filenameNew = filenameNew[2:]
                filenameNew = filenameNew.replace('\\', os.sep)
                filenameNew = os.path.join(pathDoc, filenameNew)

        # Optionally remove the source data set (Move instead of Copy)
        if move:
            RemoveDataSetBC(bcDataSet)

        # Store new file reference and global/local marker in data set
        bcDataSetNew[ID_BC_DATASET_FILENAME] = filenameNew
        bcDataSetNew[ID_BC_DATASET_IS_LOCAL] = isLocalNew

        # Update data set ID
        bcDataSetNew.SetId(MyHash(bcDataSetNew[ID_BC_DATASET_NAME] + bcDataSetNew[ID_BC_DATASET_FILENAME] + str(bcDataSetNew[ID_BC_DATASET_IS_LOCAL])))

        # Add data set to other library
        AddDataSetBC(bcDataSetNew)

        # Iterate all tags in current scene
        for tag in self._tags:
            # Announce change in library to tags (they need to rebuild their combo box content)
            tag.Message(c4d.MSG_MENUPREPARE)

            # If tag used the old data set, use new data set (if moving)
            if move and tag[ID_TAG_DATA_SET] == idDataSet:
                tag[ID_TAG_DATA_SET] = bcDataSetNew.GetId()

        # Update both clip library tabs
        self.UpdateLayoutGroupDataSet(local=True)
        self.UpdateLayoutGroupDataSet(local=False)
        c4d.EventAdd()


    # Open the directory containing the motion data file referenced in a data set (clip).
    def DataSetOpenDirectory(self, local, idxDataSet):
        # Get data set for given index in dialog from library it's currently in
        bcDataSet = self.GetDataSetByDialogIndex(local, idxDataSet)

        # Resolve project relative path
        filename = bcDataSet[ID_BC_DATASET_FILENAME]
        if bcDataSet[ID_BC_DATASET_IS_LOCAL]:
            pathDoc = c4d.documents.GetActiveDocument().GetDocumentPath()
            if pathDoc is not None and len(pathDoc) > 1 and filename[0] == '.' or os.sep not in filename:
                if filename[0] == '.':
                    filename = filename[2:]
                filename = filename.replace('\\', os.sep)
                filename = os.path.join(pathDoc, filename)

        # Open path in Explorer/Finder
        path, _ = os.path.split(filename)
        c4d.storage.GeExecuteFile(path)


    # Analyzes a motion data file and returns a new data set container,
    # properly referencing the file and meta data set.
    # Returns None on error.
    # Note: File gets loaded, decompressed and decoded.
    #       So depending on file size, this can take a second or two.
    def AnalyzeFile(self, filename, local, nameDataSet=None):
        # Check file existence
        if not os.path.exists(filename):
            print('ERROR: Clip not found: {0}'.format(filename))
            return None

        # Read LZ4 compressed data from file
        dataLZ4 = None
        with open(filename, mode='rb') as f:
            dataLZ4 = f.read()
            f.close()
        if dataLZ4 is None:
            return None

        # Decompress data
        dataStudio = lz4f.decompress(dataLZ4, return_bytearray=True, return_bytes_read=False)

        # Decode JSON into dictionary
        data = json.loads(dataStudio)

        # If no data set name provided, create one from file name
        if nameDataSet is None:
            nameDataSet = filename[filename.rfind(os.sep)+1:]
            if nameDataSet[-4:] == '.rec':
                nameDataSet = nameDataSet[:-4]

        # For local clips in project folder, the filename in data set is relative to project folder
        pathDocument = c4d.documents.GetActiveDocument().GetDocumentPath()
        if local and pathDocument is not None and len(pathDocument) > 1:
            filename = filename.replace(pathDocument, '.')

        # Create a new data set
        bcDataSet = BaseContainerDataSet(nameDataSet, filename, isLocal=local)

        # Analyze first frame of motion data and store meta data in data set.
        StoreAvailableEntitiesInDataSet(data[0]['scene'], bcDataSet)

        return bcDataSet


    # Analyzes a motion data file referenced in a given clip data set and
    # returns a new data set container containing correct meta data.
    # Returns None on error.
    def AnalyzeDataSet(self, bcDataSet):
        return self.AnalyzeFile(bcDataSet[ID_BC_DATASET_FILENAME], bcDataSet[ID_BC_DATASET_IS_LOCAL], bcDataSet[ID_BC_DATASET_NAME])


    # Add a new clip data set to either global or project clip library.
    # Optionally all clips found in a folder.
    def AddDataSet(self, local, folder=False):
        filenames = [] # list of filenames to be added as clips
        pathDocument = c4d.documents.GetActiveDocument().GetDocumentPath()
        if folder:
            # Ask user to choose a folder
            pathFolder = c4d.storage.LoadDialog(type=c4d.FILESELECTTYPE_ANYTHING, title='Load All Clips From Folder...', flags=c4d.FILESELECT_DIRECTORY, force_suffix='rec', def_path=pathDocument, def_file='')
            if pathFolder is None or len(pathFolder) < 2:
                return True # file dialog cancelled

            # Browse folder
            for filename in os.listdir(pathFolder):
                if filename[-4:] != '.rec':
                    continue
                # File found
                filenames.append(os.path.join(pathFolder, filename))
        else:
            # Ask user to choose a file
            filename = c4d.storage.LoadDialog(type=c4d.FILESELECTTYPE_ANYTHING, title='Load Clip From File...', force_suffix='rec', def_path=pathDocument, def_file='')
            if filename is None or len(filename) < 2:
                return True # file dialog cancelled
            # File found
            filenames.append(filename)

        # Iterate all files found
        for idxFilename, filename in enumerate(filenames):
            # Get a new data set container for the given file
            bcDataSet = self.AnalyzeFile(filename, local)
            if bcDataSet is None:
                print('ERROR: Add data set: File not found: {0}'.format(filename))
                continue

            # Store clip data set in respective library
            AddDataSetBC(bcDataSet)

        # Announce clip library change to tags (to update combo boxes)
        for tag in self._tags:
            tag.Message(c4d.MSG_MENUPREPARE)

        # Update respective library group
        self.UpdateLayoutGroupDataSet(local)
        c4d.EventAdd()


    # Opens a dialog to edit parameters of a clip data set in specified library.
    def EditDataSet(self, idxDataSet, local):
        # Get data set for given index in dialog from library it's currently in
        bcDataSet = self.GetDataSetByDialogIndex(local, idxDataSet)
        idDataSet = bcDataSet.GetId()

        # Open "Edit Data Set..." dialog
        dlgEdit = DialogEditDataSet(bcDataSet, local)
        resultOpen = dlgEdit.Open(c4d.DLG_TYPE_MODAL_RESIZEABLE)
        if resultOpen == False:
            return # failed to open dialog
        result, bcDataSetNew = dlgEdit.GetResult()
        if result == False:
            return # dialog cancelled by user

        # Analyze the changed data set (user may have change the referenced file, for example)
        filename = bcDataSetNew[ID_BC_DATASET_FILENAME] # really only for error requester
        bcDataSetNew = self.AnalyzeDataSet(bcDataSetNew)
        if bcDataSetNew is None:
            c4d.gui.MessageDialog('Failed to open motion data file: {0}.'.format(filename), c4d.GEMB_ICONEXCLAMATION)
            return

        # Remove the old and store changed data set in respective library
        # This is needed as the changed parameters may have caused a change of the data set ID
        RemoveDataSetBC(bcDataSet)
        AddDataSetBC(bcDataSetNew)

        # Iterate all Rokoko tags in current document
        for tag in self._tags:
            # Announce change in library to tags (they need to rebuild their combo box content)
            tag.Message(c4d.MSG_MENUPREPARE)

            # If tag used the old data set, use changed data set's ID
            if tag[ID_TAG_DATA_SET] == idDataSet:
                tag[ID_TAG_DATA_SET] = bcDataSetNew.GetId()

        # Update respective library group
        self.UpdateLayoutGroupDataSet(local)
        c4d.EventAdd()


    def CreateSceneForDataSet(self, idxDataSet, local):
        # Get data set for given index in dialog from library it's currently in
        bcDataSet = self.GetDataSetByDialogIndex(local, idxDataSet)

        # Merge all actors and props needed for this data set into the current document
        self.InsertDataSetScene(bcDataSet)


    # Remove a clip data set from specified library.
    # Optionally removes all clips from specified library.
    # Optionally deletes referenced motion data files.
    def RemoveDataSet(self, local, idx=-1, all=False, delete=False):
        if local:
            bcDataSets = GetLocalDataSets()
        else:
            bcDataSets = GetPrefsContainer(ID_BC_DATA_SETS)

        filenamesDelete = [] # a list of filenames (for actual deletion of files at the end)

        # Optionally delete the motion clip file(s)
        # Only collect filenames here, actual delete opration is at the enmd
        if delete:
            # Collect either all or just a single data set's filename
            if all:
                for idDataSet, bcDataSet in bcDataSets:
                    filenamesDelete.append(bcDataSet[ID_BC_DATASET_FILENAME])
            else:
                idDataSet = bcDataSets.GetIndexId(idx)
                bcDataSet = bcDataSets[idDataSet]
                filenamesDelete.append(bcDataSet[ID_BC_DATASET_FILENAME])

            # Resolve project relative filenames
            pathDoc = c4d.documents.GetActiveDocument().GetDocumentPath()
            for idxFilename, filename in enumerate(filenamesDelete):
                if pathDoc is not None and len(pathDoc) > 1 and filename[0] == '.' or os.sep not in filename:
                    if filename[0] == '.':
                        filename = filename[2:]
                    filename = filename.replace('\\', os.sep)
                    filenamesDelete[idxFilename] = os.path.join(pathDoc, filename)

            # Create safety question
            message = 'Are you sure you want to delete the following data set(s)?\n'
            for filename in filenamesDelete:
                message += filename + '\n'
            if len(filenamesDelete) <= 0:
                # Something is strange. Nevertheless allow user to continue,
                # so a stale data set still gets removed (even if there is no file to delete).
                message += 'No files to delete???\n'
            message += 'Yes: Delete file(s)\nNo: Remove data set reference, only\nCancel: Abort'

            # Ask user, if sure?
            result = c4d.gui.MessageDialog(message, c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_YESNOCANCEL)

            # Decode user's choice
            if result == c4d.GEMB_R_NO:
                filenamesDelete = [] # flush list, no files will be deleted
            elif result == c4d.GEMB_R_CANCEL:
                return # user aborted the operation

        # Throw data set container(s) away
        if all:
            bcDataSets.FlushAll()
        else:
            idDataSet = bcDataSets.GetIndexId(idx)
            bcDataSet = bcDataSets.GetContainer(idDataSet)
            RemoveDataSetBC(bcDataSet)

        # Announce change in library to tags (they need to rebuild their combo box content)
        self._tags = GetTagList()
        for tag in self._tags:
            tag.Message(c4d.MSG_MENUPREPARE)

        # Update respective library group
        self.UpdateLayoutGroupDataSet(local)
        c4d.EventAdd()

        # Finally do actually delete the file(s) (if any to delete)
        for filename in filenamesDelete:
            if DO_FILE_ACTION:
                os.remove(filename)


    # User pressed "+" button on "Tags" tab (create scene or create characters and such).
    def CommandTagsPopup(self):
        # If not connected, some options get disabled
        disableItem = ''
        if not IsConnected():
            disableItem = '&d&'

        # Create menu BaseContainer
        bcMenu = c4d.BaseContainer()
        bcMenu.InsData(ID_SUBMENU_TAGS_CREATE_STUDIO_LIVE_SCENE, 'Create Connected Studio Scene' + disableItem)
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_TAGS_CREATE_CHARACTER_NEWTON, 'Create Rokoko Newton Character')
        bcMenu.InsData(ID_SUBMENU_TAGS_CREATE_BONES_NEWTON, 'Create Rokoko Newton Bones')
        bcMenu.InsData(ID_SUBMENU_TAGS_CREATE_CHARACTER_NEWTON_WITH_FACE, 'Create Rokoko Newton Character with Face')
        bcMenu.InsData(ID_SUBMENU_TAGS_CREATE_FACE_NEWTON, 'Create Rokoko Newton Face')
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_TAGS_CREATE_LIGHT, 'Create Light')
        bcMenu.InsData(ID_SUBMENU_TAGS_CREATE_CAMERA, 'Create Camera')
        bcMenu.InsData(ID_SUBMENU_TAGS_CREATE_PROP, 'Create Prop')

        # Show popup menu
        result = c4d.gui.ShowPopupDialog(cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)

        # Decode user's selection
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


    # Inserts all rigs and props needed for a given data set (regardless if live connection or clip)
    # Note: Creates an undo.
    def InsertDataSetScene(self, bcDataSet):
        docCurrent = c4d.documents.GetActiveDocument()

        # Included default character files in plugin's resources
        filenameNewtonWithFace = os.path.join(os.path.dirname(__file__), 'res', 'tpose_rokoko_newton_with_face.c4d')
        filenameNewton = os.path.join(os.path.dirname(__file__), 'res', 'tpose_rokoko_newton_meshed.c4d')
        filenameNewtonFace = os.path.join(os.path.dirname(__file__), 'res', 'rokoko_newton_face.c4d')

        docsSrc = [None, None, None] # default character scenes will be loaded only once during this operation
        objLast = None
        matLast = None

        # Create a new undo step
        docCurrent.StartUndo()

        # Actors
        # For all actors contained in referenced motion data
        bcActors = bcDataSet.GetContainerInstance(ID_BC_DATASET_ACTORS)
        for idxActor, _ in bcActors:
            # Get actor entity and its meta data
            bcActor = bcActors.GetContainerInstance(idxActor)
            hasSuit = bcActor[ID_BC_ENTITY_HAS_SUIT]
            hasFace = bcActor[ID_BC_ENTITY_HAS_FACE]
            name = bcActor[ID_BC_ENTITY_NAME]
            color = bcActor[ID_BC_ENTITY_COLOR]

            # Get default character scene (load the scene if not done so already for a previous actor)
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

            # The root object of the rig is always the first in all default scenes.
            # NOTE: Take care of this when creating changing default scenes.
            objRootSrc = docSrc.GetFirstObject()
            if objRootSrc is None:
                print('ERROR: No Newton Rig.')
                continue

            # Get the first material from default scene
            # NOTE: Body color of the character should be the first material.
            #       Actors color will be changed only for the first material.
            #       Take care of this when creating changing default scenes.
            matSrc = docSrc.GetFirstMaterial()

            # AliasTrans is C4D's mechanism to have dependencies between
            # different entities resolved during a copy operation.
            #
            # In this case for example, we'll clone objects and materials
            # from the default scene. As the objects reference the materials
            # via their texture tags, we would like all objects to reference
            # the created clones of the materials afterwards and not the original
            # materials of the default scene.
            #
            # The AliasTrans is simply passed to all cloning operations and it will
            # collect a list of BaseLinks of all entities involved in the cloning.
            # Then when all cloning is finished, AliasTrans.Translate() gets called,
            # to replace all references to source objects with their cloned counterparts
            # within all involved entities (this includes children or branches like tags).
            trans = c4d.AliasTrans()
            if not trans or not trans.Init(docSrc):
                print('ERROR: No AliasTrans.')
                continue

            # Clone the character rig from default scene
            objRootNew = objRootSrc.GetClone(c4d.COPYFLAGS_NONE, trans)
            if objRootNew is None:
                print('ERROR: Failed to clone rig.')
                continue

            # Clone all materials from default scene
            materials = [] # list of material clones
            while matSrc is not None:
                mat = matSrc.GetClone(c4d.COPYFLAGS_NONE, trans)
                if mat is not None:
                    materials.append(mat)
                matSrc = matSrc.GetNext()

            # Correct link dependencies
            trans.Translate(True)

            # Rename root object and Rokoko tag of the resulting rig with actor name.
            tag = objRootNew.GetTag(type=PLUGIN_ID_TAG)
            if tag is None:
                print('ERROR: Lacking Rokoko Tag.')
                continue
            objRootNew.SetName(name)
            tag.SetName('Rokoko Tag {0}'.format(name))

            # Insert new character into current document (and register insertion in the undo step)
            docCurrent.InsertObject(objRootNew, pred=objLast)
            docCurrent.AddUndo(c4d.UNDOTYPE_NEW, objRootNew)
            objLast = objRootNew # remember last object inserted, in order to keep original insertion order

            if len(materials) > 0:
                # Change color channel color to actor color
                materials[0][c4d.MATERIAL_COLOR_COLOR] = color

            # Insert all materials into current document
            for mat in materials:
                docCurrent.InsertMaterial(mat, pred=matLast)
                docCurrent.AddUndo(c4d.UNDOTYPE_NEW, mat)
                matLast = mat

            # TODO: In case of a character rig with face we probably should update all tags, shouldn't we?

            # Enforce initialization of Rokoko tag
            tag.Message(c4d.MSG_MENUPREPARE)

            # Set tag to use this data set and actor
            tag[ID_TAG_DATA_SET] = bcDataSet.GetId()
            #tag[ID_TAG_ACTORS] = idxActor # TODO strange!!!
            tag.GetDataInstance().SetInt32(ID_TAG_ACTORS, idxActor)
            tag[ID_TAG_ACTOR_INDEX] = idxActor

        # Props
        # For all props contained in referenced motion data
        bcProps = bcDataSet.GetContainerInstance(ID_BC_DATASET_PROPS)
        for idxProp, _ in bcProps:
            # Get prop entity and its meta data
            bcProp = bcProps.GetContainerInstance(idxProp)
            name = bcProp[ID_BC_ENTITY_NAME]
            color = bcProp[ID_BC_ENTITY_COLOR]

            # Create a new Null object representing the prop
            objProp = c4d.BaseObject(c4d.Onull)

            # Configure the Null object
            objProp.SetName(name)
            objProp[c4d.NULLOBJECT_DISPLAY] = 12 # 12: pyramid
            objProp[c4d.ID_BASEOBJECT_COLOR] = color
            objProp[c4d.ID_BASEOBJECT_USECOLOR] = 2

            # Create Rokoko tag on prop object
            tag = objProp.MakeTag(PLUGIN_ID_TAG)

            # Rename tag
            tag.SetName('Rokoko Tag {0}'.format(name))

            # Insert prop object into the current document
            docCurrent.InsertObject(objProp, pred=objLast)
            docCurrent.AddUndo(c4d.UNDOTYPE_NEW, objProp)
            objLast = objProp # remember last object inserted, in order to keep original insertion order

            # Enforce initialization of tag (as if the user created it)
            tag.Message(c4d.MSG_MENUPREPARE)

            # Set tag to use this data set and prop
            #tag[ID_TAG_DATA_SET] = bcDataSet.GetId() # TODO strange!!!
            tag.GetDataInstance().SetInt32(ID_TAG_DATA_SET, bcDataSet.GetId())
            tag.GetDataInstance().SetInt32(ID_TAG_ACTORS, idxProp)
            tag[ID_TAG_ACTOR_INDEX] = idxProp

        # Finish undo step
        docCurrent.EndUndo()

        # Let C4D know, we have changed the scene
        c4d.EventAdd()


    # Short cut to inserts all rigs and props needed for the current live connection.
    # Note: Creates an undo.
    def InsertRokokoStudioScene(self):
        bcConnected = GetConnectedDataSet()
        if bcConnected is None:
            return
        self.InsertDataSetScene(bcConnected)


    # Insert a default Rokoko Newton character without face poses into current scene.
    # Optionally joints, only (don't ask why it's called bonesOnly...).
    # Note: Creates an undo.
    def InsertRokokoCharacter(self, id, bonesOnly=False):
        docCurrent = c4d.documents.GetActiveDocument()
        filenameNewton = os.path.join(os.path.dirname(__file__), 'res', 'tpose_rokoko_newton_meshed.c4d')

        if bonesOnly:
            # If no skin is supposed to be added to the scene,
            # we need to extract the rig from default scene

            # Load default scene from plugin's resources
            docNewton = c4d.documents.LoadDocument(filenameNewton, c4d.SCENEFILTER_OBJECTS, None)
            if docNewton is None:
                print('ERROR: Failed to load Rokoko Newton.')
                return

            # Get rig from default scene. It has to be the first.
            objRootNewton = docNewton.GetFirstObject()
            if objRootNewton is None or not objRootNewton.CheckType(c4d.Onull) or objRootNewton.GetName() != 'Rokoko Newton':
                print('ERROR: Failed to find Rokoko Newton bones.')
                return

            # Remove from default scene, we want to directly use it for this scene
            # (we could also clone it instead)
            objRootNewton.Remove()

            # Strip skin object(s)
            # NOTE: We expect a certain order of the hierarchy of the default scene.
            #       Take care of this when creating changing default scenes.
            objJoint = objRootNewton.GetDown()
            objMesh = objJoint.GetNext() # Skip joints
            while objMesh is not None:
                objMeshNext = objMesh.GetNext()
                if objMesh.CheckType(c4d.Opolygon):
                    objMesh.Remove()
                objMesh = objMeshNext

            # Insert rig into current document
            docCurrent.StartUndo()
            docCurrent.AddUndo(c4d.UNDOTYPE_NEW, objRootNewton)
            docCurrent.InsertObject(objRootNewton)
            docCurrent.EndUndo()
        else:
            # Simply merge the complete default scene into current document.
            if not c4d.documents.MergeDocument(docCurrent, filenameNewton, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS, None):
                print('ERROR: Failed to merge Rokoko Newton.')

        # Let C4D know, we have changed the scene
        c4d.EventAdd()


    # Insert a default Rokoko Newton character with face with poses into current scene.
    # Note: Creates an undo (implicitly by MergeDocument()).
    def InsertRokokoCharacterWithFace(self, id):
        # Simply merge the complete default scene into current document.
        docCurrent = c4d.documents.GetActiveDocument()
        filenameNewton = os.path.join(os.path.dirname(__file__), 'res', 'tpose_rokoko_newton_with_face.c4d')
        if not c4d.documents.MergeDocument(docCurrent, filenameNewton, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS, None):
            print('ERROR: Failed to merge Rokoko Newton with Face')

        # Let C4D know, we have changed the scene
        c4d.EventAdd()


    # Insert a default Rokoko Newton face with poses (no rig) into current scene.
    # Note: Creates an undo (implicitly by MergeDocument()).
    def InsertRokokoFace(self, id):
        # Simply merge the complete default scene into current document.
        docCurrent = c4d.documents.GetActiveDocument()
        filenameNewton = os.path.join(os.path.dirname(__file__), 'res', 'rokoko_newton_face.c4d')
        if not c4d.documents.MergeDocument(docCurrent, filenameNewton, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS, None):
            print('ERROR: Failed to merge Rokoko Newton Face')

        # Let C4D know, we have changed the scene
        c4d.EventAdd()


    # Insert a default light object with Rokoko tag into current scene.
    # Note: Creates an undo.
    def InsertRokokoLight(self):
        doc = c4d.documents.GetActiveDocument()

        # Create a new light object
        light = c4d.BaseObject(c4d.Olight)

        # Create Rokoko tag on light object
        tag = light.MakeTag(PLUGIN_ID_TAG)

        # Insert light object into the scene
        doc.StartUndo()
        doc.InsertObject(light)
        doc.AddUndo(c4d.UNDOTYPE_NEW, light)
        doc.EndUndo()

        # Enforce initialization of tag (as if the user created it)
        tag.Message(c4d.MSG_MENUPREPARE)

        # Let C4D know, we have changed the scene
        c4d.EventAdd()


    # Insert a default camera object with Rokoko tag into current scene.
    # Note: Creates an undo.
    def InsertRokokoCamera(self):
        doc = c4d.documents.GetActiveDocument()

        # Create a new camera object
        camera = c4d.BaseObject(c4d.Ocamera)

        # Create Rokoko tag on camera object
        tag = camera.MakeTag(PLUGIN_ID_TAG)

        # Insert camera object into the scene
        doc.StartUndo()
        doc.InsertObject(camera)
        doc.AddUndo(c4d.UNDOTYPE_NEW, camera)
        doc.EndUndo()

        # Enforce initialization of tag (as if the user created it)
        tag.Message(c4d.MSG_MENUPREPARE)

        # Let C4D know, we have changed the scene
        c4d.EventAdd()


    # Insert a default Null object with Rokoko tag into current scene.
    # Note: Creates an undo.
    def InsertRokokoProp(self):
        doc = c4d.documents.GetActiveDocument()

        # Create a new Null object
        prop = c4d.BaseObject(c4d.Onull)

        # Create Rokoko tag on Null object
        tag = prop.MakeTag(PLUGIN_ID_TAG)

        # Insert Null object into the scene
        doc.StartUndo()
        doc.InsertObject(prop)
        doc.AddUndo(c4d.UNDOTYPE_NEW, prop)
        doc.EndUndo()

        # Enforce initialization of tag (as if the user created it)
        tag.Message(c4d.MSG_MENUPREPARE)

        # Let C4D know, we have changed the scene
        c4d.EventAdd()


    # User pressed "..." button on a single tag in "Tags" tab.
    def CommandTagPopup(self, id):
        idxTag = id - ID_DLGMNGR_BASE_TAG_POPUP

        # If player is active, certain menu options get disabled
        disableItem = ''
        if g_thdListener._receive:
            disableItem = '&d&'

        # Create menu BaseContainer
        bcMenu = c4d.BaseContainer()
        bcMenu.InsData(ID_SUBMENU_TAG_PLAY, 'Play' + disableItem)
        bcMenu.InsData(ID_SUBMENU_TAG_TPOSE, 'Go to T-Pose' + disableItem)
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_TAG_SHOW_TAG, 'Show Tag in Attribute Manager')
        bcMenu.InsData(ID_SUBMENU_TAG_SHOW_OBJECT, 'Show Object in Attribute Manager')
        bcMenu.InsData(0, '')
        bcMenu.InsData(ID_SUBMENU_TAG_DELETE, 'Delete Rokoko Tag' + disableItem)

        # Show popup menu
        result = c4d.gui.ShowPopupDialog(cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)

        # Decode user choice
        self._tags = GetTagList()
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


    # Show an object or tag in C4D's Attribute Manager
    def ShowInAttributeManager(self, bl):
        if bl.CheckType(c4d.Tbase):
            c4d.gui.ActiveObjectManager_SetObject(c4d.ACTIVEOBJECTMODE_TAG, bl, c4d.ACTIVEOBJECTMANAGER_SETOBJECTS_OPEN, activepage=c4d.DescID())
        else:
            c4d.gui.ActiveObjectManager_SetObject(c4d.ACTIVEOBJECTMODE_OBJECT, bl, c4d.ACTIVEOBJECTMANAGER_SETOBJECTS_OPEN, activepage=c4d.DescID())


    # Delete Rokoko tag (referenced by dialog index) from scene.
    # Note: Creates an undo.
    def DeleteTag(self, idxTag):
        tag = self._tags.pop(idxTag)
        doc = tag.GetDocument()

        # Delete the tag
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_DELETE, tag)
        tag.Remove()
        doc.EndUndo()

        # Let C4D know, we have changed the scene
        c4d.EventAdd()


    # User pressed "Unassigned to Live" button on "Player" tab.
    def CommandAssignUnassignedTags(self):
        bcConnected = GetConnectedDataSet()
        if bcConnected is None:
            return
        idConnected = bcConnected.GetId()

        # Prepare a dict to store rig type bits referenced by entity names.
        # The dict contains all actors and props.
        # No issue, if actors and props have identical names (reason for storing bit mask).
        assigned = {}
        bcActors = bcConnected.GetContainerInstance(ID_BC_DATASET_ACTORS)
        for idxActor, bcActor in bcActors:
            nameActor = bcActor[ID_BC_ENTITY_NAME].lower()
            assigned[nameActor] = 0
        bcProps = bcConnected.GetContainerInstance(ID_BC_DATASET_PROPS)
        for idxProp, bcProp in bcProps:
            nameProp = bcProp[ID_BC_ENTITY_NAME].lower()
            assigned[nameProp] = 0

        # Iterate all tags in current scene
        for idxTag, tag in enumerate(self._tags):
            if not tag.IsAlive():
                continue

            # Skip tags with data assignment
            if tag[ID_TAG_DATA_SET] != 0:
                continue

            # Skip unassigned tags (shouldn't happen actually)
            obj = tag.GetObject()
            if obj is None:
                continue

            # Assign live connection to tag
            #print(tag[ID_TAG_DATA_SET], idConnected, type(idConnected))
            # TODO: Why is SetParametter not possible, here???
            #tag[ID_TAG_DATA_SET] = idConnected # -> error
            #tag.SetParameter(ID_TAG_DATA_SET, idConnected, c4d.DESCFLAGS_SET_NONE) # -> nothing happens
            tag.GetDataInstance().SetInt32(ID_TAG_DATA_SET, idConnected)

            # Iterate all entities available in data
            rigType =  tag[ID_TAG_RIG_TYPE]
            idEntitiesBc = RigTypeToEntitiesBcId(rigType)
            bcEntities = bcConnected.GetContainerInstance(idEntitiesBc)
            for idxEntity, bcEntity in bcEntities:
                name = bcEntity[ID_BC_ENTITY_NAME].lower()

                # If neither name matches and the entity has been assigned before, skip to next
                if name not in tag.GetName().lower() and name not in obj.GetName().lower() and \
                   (assigned[name] & rigType):
                    continue

                # Assign entity to tag
                tag[ID_TAG_ACTORS] = idxEntity

                # Entity has been assigned and will only be assigned again for name matches
                assigned[name] |= rigType
                break

        c4d.EventAdd()

        #self.InitValues()

    # User changed project scale,
    # simply save new project scale in preferences.
    def CommandProjectScale(self):
        SetProjectScale(self.GetFloat(ID_DLGMNGR_PROJECT_SCALE))


    # User changed the group (all, live, clips, selected) of tags to be used by Player.
    # The choice is simply saved in preferences.
    def CommandPlayChoice(self):
        SetPref(ID_DLGMNGR_PLAYER_TAG_SELECTION, self.GetInt32(ID_DLGMNGR_PLAYER_TAG_SELECTION))


    # User pressed "Player Start/Stop" button on "Player" tab.
    def CommandPlayerStart(self, all=False, live=False, idxTag=-1):
        live = g_thdListener._receive

        # Button is a toggle button.
        # If Player is already started, stop it.
        if live:
            self.CommandPlayerExit()
            return

        # If connected to Studio without receiving data, we have an issue.
        # The listener thread waits for Studio and Player won't play without received frames.
        # Thus user is asked to disconnect, so the offline Player thread can be used.
        # User can still continue with the live connection, maybe if he plans to start Live stream in a second.
        if not live and g_thdListener.GetConnectionStatus() == 2:
            result = c4d.gui.MessageDialog('Currently there is no data incoming from Live connection.\nDisconnect?', c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_YESNOCANCEL)
            if result == c4d.GEMB_R_YES:
                # Disconnect from Studio
                self.Connect(999999)
            elif result == c4d.GEMB_R_CANCEL:
                return # user aborted

        # Get list of tags for Player based on user's choice in radio group right of button
        choice = self.GetInt32(ID_DLGMNGR_PLAYER_TAG_SELECTION)
        tagsLive = []
        self._tags = GetTagList()
        if choice == 0: # all:
            tagsLive = self._tags
        elif choice == 2: # live:
            idConnected = GetConnectedDataSetId()
            for tag in self._tags:
                if tag[ID_TAG_DATA_SET] == idConnected:
                    tagsLive.append(tag)
        elif choice == 3: # data sets, only
            idConnected = GetConnectedDataSetId()
            for tag in self._tags:
                if tag[ID_TAG_DATA_SET] != idConnected:
                    tagsLive.append(tag)
        elif idxTag != -1: # the one specified by idxTag (if user used "Play" in tag's popup menu)
            tagsLive = [self._tags[idxTag]]
        else: # selected tags
            for tag in self._tags:
                if tag[ID_TAG_SELECTED_IN_MANAGER]:
                    tagsLive.append(tag)

        # Check if there is at least one tag with valid data.
        # Otherwise abort.
        tagWithValidData = False
        for tag in tagsLive:
            if tag[ID_TAG_VALID_DATA]:
                tagWithValidData = True
                break
        if not tagWithValidData:
            c4d.gui.MessageDialog('No data to play.\nEither no tags selected or\nno valid data assigned to tags.')
            return

        # Register all selected tags in listener thread as consumers.
        # Not only those tags with valid data,
        # as the user shall be able to switch to valid data during playback.
        for tag in tagsLive:
            g_thdListener.AddTagConsumer(tag.GetNodeData(), tag)

        # Start Player and playback
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_START)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_PLAY, False)


    # User pressed "Player Start/Stop" button on "Player" tab to stop player.
    def CommandPlayerExit(self):
        # Stop playback and exit player
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_STOP)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_EXIT)

        # Reset state of "Start/Save Recording" button
        self._buttonRecordState = False


    # User changed "Playback Rate" scale,
    # simply save new playback rate in preferences.
    def CommandPlaybackSpeed(self):
        SetPref(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, self.GetInt32(ID_DLGMNGR_PLAYER_PLAYBACK_SPEED))


    # User changed "Animate Document" scale,
    # simply save new state in preferences.
    def CommandAnimateDocument(self):
        SetPref(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT, self.GetBool(ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT))


    # User pressed "Play/Pause" toggle button on "Player" tab.
    # Force enforces "Pause" state (used by other buttons).
    # If returnToLive is True, Player will unpause and resync with live stream.
    def CommandPause(self, force=False, returnToLive=False, idx=None):
        pause = (g_thdListener._play or force) and not returnToLive
        if pause:
            if idx is None:
                idx = self.GetInt32(ID_DLGMNGR_PLAYER_CURRENT_FRAME)
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_PAUSE, idx)
        else:
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_PLAY, returnToLive)


    # User released scrub bar (or entered a frame index in edit field) in "Player" tab.
    # Also used for "First/Last Frame" buttons.
    def CommandJumpToFrame(self, idx):
        # Pause playback
        self.CommandPause(force=True, idx=idx)

        # Set scrub bar to paused frame
        # (needed for "First/Last Frame" and doesn't harm if request comes from scrub bar)
        _, maxFrame = g_thdListener.GetCurrentFrameNumber()
        self.SetInt32(ID_DLGMNGR_PLAYER_CURRENT_FRAME, idx, min=0, max=maxFrame, min2=0, max2=maxFrame)


    # Start a new recording,
    # in reality simply flush live buffer.
    def CommandStartNewRecording(self):
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_FLUSH_LIVE_BUFFER)


    # Save a recording
    def CommandSaveRecording(self):
        # Pause reception of live stream
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_PAUSE_RECEPTION)

        # Pause playback
        self.CommandPause(force=True)

        # Disable entire Manager dialog
        self.EnableDialog(False)

        # Open "Save Recording..." dialog
        self._dlgChild = DialogSaveRecording(self)
        self._dlgChild.Open(c4d.DLG_TYPE_ASYNC)


    # User clicked "Start/Save Recording" toggle button on "Player" tab.
    def CommandStartSaveRecording(self):
        if self._buttonRecordState:
            self.CommandSaveRecording()
        else:
            self.CommandStartNewRecording()

        # Toggle button state
        self._buttonRecordState = not self._buttonRecordState

        # Update player interface
        self.EnableLiveButtons()


    # User clicked a tag's selection checkbox on "Tags" tab.
    # Note: Creates an undo.
    def CommandTagEnable(self, id):
        idxTag = id - ID_DLGMNGR_BASE_DATA_SET_ENABLED

        self._tags = GetTagList()
        if self._tags is None or idxTag >= len(self._tags):
            return

        tag = self._tags[idxTag]

        doc = c4d.documents.GetActiveDocument()

        # Select/deselect tag
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
        tag[ID_TAG_SELECTED_IN_MANAGER] = self.GetBool(id)
        doc.EndUndo()

        # Let C4D know, we have changed the scene
        # Actually redundant currently, as the selection state is not
        # exposed in tag's parameters as originally planned
        c4d.EventAdd()


    # User clicked "Select All" or "Deselect All" button on "Tags" tab.
    # Note: Creates an undo.
    def CommandTagSelectAll(self, select=True):
        self._tags = GetTagList()
        if self._tags is None:
            return

        doc = c4d.documents.GetActiveDocument()

        # Select/deselect all tags
        doc.StartUndo()
        for tag in self._tags:
            doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
            tag[ID_TAG_SELECTED_IN_MANAGER] = select
        doc.EndUndo()

        # Let C4D know, we have changed the scene
        # Actually redundant currently, as the selection state is not
        # exposed in tag's parameters as originally planned
        c4d.EventAdd()


    # User clicked "Invert Selection" button on "Tags" tab.
    # Note: Creates an undo.
    def CommandTagInvertSelection(self):
        self._tags = GetTagList()
        if self._tags is None:
            return

        doc = c4d.documents.GetActiveDocument()

        # Invert selection state of all tags
        doc.StartUndo()
        for tag in self._tags:
            doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
            tag[ID_TAG_SELECTED_IN_MANAGER] = not tag[ID_TAG_SELECTED_IN_MANAGER]
        doc.EndUndo()

        # Let C4D know, we have changed the scene
        # Actually redundant currently, as the selection state is not
        # exposed in tag's parameters as originally planned
        c4d.EventAdd()


    # User changed type of a tag on "Tags" tab.
    # Note: Creates an undo.
    def CommandTagRigType(self, id):
        idxTag = id - ID_DLGMNGR_BASE_TAG_RIG_TYPES

        self._tags = GetTagList()
        if self._tags is None or idxTag >= len(self._tags):
            return

        tag = self._tags[idxTag]

        doc = c4d.documents.GetActiveDocument()

        # Change type of tag
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
        tag[ID_TAG_RIG_TYPE] = self.GetInt32(id)
        doc.EndUndo()

        # Let C4D know, we have changed the scene (e.g. tag in Attribute Manager)
        c4d.EventAdd()


    # User changed data set of a tag on "Tags" tab.
    # Note: Creates an undo.
    def CommandTagDataSet(self, id):
        idxTag = id - ID_DLGMNGR_BASE_TAG_DATA_SETS

        self._tags = GetTagList()
        if self._tags is None or idxTag >= len(self._tags):
            return

        tag = self._tags[idxTag]

        doc = c4d.documents.GetActiveDocument()

        # Change selected data set
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
        tag[ID_TAG_DATA_SET] = self.GetInt32(id)
        doc.EndUndo()

        # Let C4D know, we have changed the scene (e.g. tag in Attribute Manager)
        c4d.EventAdd()


    # User selected another entity for a tag on "Tags" tab.
    # Note: Creates an undo.
    def CommandTagActor(self, id):
        idxTag = id - ID_DLGMNGR_BASE_TAG_ACTORS

        self._tags = GetTagList()
        if self._tags is None or idxTag >= len(self._tags):
            return

        tag = self._tags[idxTag]

        doc = c4d.documents.GetActiveDocument()

        # Change selected entity
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
        tag[ID_TAG_ACTORS] = self.GetInt32(id)
        doc.EndUndo()

        # Let C4D know, we have changed the scene (e.g. tag in Attribute Manager)
        c4d.EventAdd()


    # User "Connect/Disconnect" button of a connection on "Connection" tab.
    # Also used for connection combo box in menu row.
    def CommandConnect(self, id):
        if id == ID_DLGMNGR_CONNECTIONS_IN_MENU:
            idxConnection = self.GetInt32(id)
        else:
            idxConnection = id - ID_DLGMNGR_BASE_CONNECTION_CONNECT
        self.Connect(idxConnection)


    # User changed "Auto Connect" state of a connection on "Connection" tab.
    # Only one connction may have auto connect enabled.
    def CommandAutoConnect(self, id):
        idxConnection = id - ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT
        bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
        idConnectionClicked = bcConnections.GetIndexId(idxConnection)

        # Disable auto connect in all connections,
        # but the one clicked on (for which the checkbox state will be set).
        idx = 0
        for idConnection, bcConnection in bcConnections:
            enable = self.GetBool(id) and idConnectionClicked == idConnection
            bcConnections.GetContainerInstance(idConnection)[ID_BC_DATASET_LIVE_AUTOCONNECT] = enable
            self.SetBool(ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT + idx, enable)
            idx += 1


    # User clicked a Command API button
    def CommandCommandAPI(self, id):
        bcConnected = GetConnectedDataSet()
        if bcConnected is None:
            # TODO: In case of multiple possible connections in UI,
            #       we'd probably need to insist on having a connection connected.
            # If there is currently no connection active,
            # use first defined connection instead.
            bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
            idFirstConnection = bcConnections.GetIndexId(0)
            bcConnected = bcConnections[idFirstConnection]

        # Build URL for selected command (and prepare some string for error and status messages)
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

        # Do a POST request
        # Unfortunately Rokoko Studio returns an HTTP error, even if communication was successful,
        # but another error occurred (like e.g. no suit connected).
        postData = {}
        postData = str(postData)
        postData = postData.encode('utf-8')
        response = None
        ok = True
        try:
            req = urllib.request.Request(url, postData, unverifiable=True)
            response = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            # Get actual answer from Rokoko Studio
            d = json.loads(e.__dict__['file'].read())
            responseCode = d['response_code']
            description = d['description']
            if responseCode == 'OK': # TODO
                pass
            else:
                #NO_LIVE_SMARTSUIT
                #NO_ACTIVE_RECORDING
                c4d.gui.MessageDialog('Rokoko Command API failed to {0}\n\nError Code:       {1}\nError Message: {2}'.format(actionText, responseCode, description))
                ok = False
        except:
            c4d.gui.MessageDialog('Command API failed to connect to Rokoko Studio.\nPlease check IP, port and key configured for Command API in Connection.')

        # Success message
        if ok:
            c4d.StatusSetText(statusText)


    # User wants About dialog
    def CommandAbout(self):
        dlg = DialogAbout()
        dlg.Open(c4d.DLG_TYPE_MODAL)


    # User wants a web link from "Help" menu
    def CommandWeb(self, id):
        if id not in LINKS:
            print('ERROR: Unknown link ID')
            return
        c4d.storage.GeExecuteFile(LINKS[id])


    # Called by C4D to handle user's interaction with the dialog.
    def Command(self, id, msg):
        # Dialog tabs/groups
        if id == ID_DLGMNGR_TABS:
            self.UpdateGroupVisibility()

        # Connection tab
        # Add connection button ("+"), currently not in UI
        elif id == ID_DLGMNGR_CONNECTION_POPUP:
            self.CommandConnectionsPopup()
        # Per connection popup menu, button "..."
        elif id >= ID_DLGMNGR_BASE_CONNECTION_POPUP and id < ID_DLGMNGR_BASE_CONNECTION_POPUP + 10000:
            self.CommandConnectionPopup(id)
        # Per connection "Connect/Disconnect" button
        elif id >= ID_DLGMNGR_BASE_CONNECTION_CONNECT and id < ID_DLGMNGR_BASE_CONNECTION_CONNECT + 10000:
            self.CommandConnect(id)
        # Per connection "Auto Connect" checkbox
        elif id >= ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT and id < ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT + 10000:
            self.CommandAutoConnect(id)
        # Connection combo box in menu row
        elif id == ID_DLGMNGR_CONNECTIONS_IN_MENU:
            self.CommandConnect(id)

        # Global Clips library tab
        # Main popup menu, button "+" ("Add File...", ...)
        elif id == ID_DLGMNGR_GLOBAL_DATA_POPUP:
            self.CommandDataPopup(local=False)
        # Per clip popup menu, button "..."
        elif id >= ID_DLGMNGR_BASE_GLOBAL_DATA_POPUP and id < ID_DLGMNGR_BASE_GLOBAL_DATA_POPUP + 10000:
            self.CommandDataSetPopup(id, local=False)

        # Project Clips library tab
        # Main popup menu, button "+" ("Add File...", ...)
        elif id == ID_DLGMNGR_LOCAL_DATA_POPUP:
            self.CommandDataPopup(local=True)
        # Per clip popup menu, button "..."
        elif id >= ID_DLGMNGR_BASE_LOCAL_DATA_POPUP and id < ID_DLGMNGR_BASE_LOCAL_DATA_POPUP + 10000:
            self.CommandDataSetPopup(id, local=True)

        # Tags tab
        # Main popup menu, button "+" ("Create character",...)
        elif id == ID_DLGMNGR_TAGS_POPUP:
            self.CommandTagsPopup()
        # Per tag popup menu, button "..."
        elif id >= ID_DLGMNGR_BASE_TAG_POPUP and id < ID_DLGMNGR_BASE_TAG_POPUP + 10000:
            self.CommandTagPopup(id)
        # Tag parameters
        elif id >= ID_DLGMNGR_BASE_TAG_RIG_TYPES and id < ID_DLGMNGR_BASE_TAG_RIG_TYPES + 10000:
            self.CommandTagRigType(id)
        elif id >= ID_DLGMNGR_BASE_TAG_DATA_SETS and id < ID_DLGMNGR_BASE_TAG_DATA_SETS + 10000:
            self.CommandTagDataSet(id)
        elif id >= ID_DLGMNGR_BASE_TAG_ACTORS and id < ID_DLGMNGR_BASE_TAG_ACTORS + 10000:
            self.CommandTagActor(id)
        # Tag selection for player
        elif id >= ID_DLGMNGR_BASE_DATA_SET_ENABLED and id < ID_DLGMNGR_BASE_DATA_SET_ENABLED + 10000:
            self.CommandTagEnable(id)
        # Select buttons
        elif id == ID_DLGMNGR_SELECT_ALL_TAGS:
            self.CommandTagSelectAll()
        elif id == ID_DLGMNGR_DESELECT_ALL_TAGS:
            self.CommandTagSelectAll(select=False)
        elif id == ID_DLGMNGR_INVERT_SELECTION:
            self.CommandTagInvertSelection()
        # Assign unassigned tags to live connection
        elif id == ID_DLGMNGR_ASSIGN_UNASSIGNED_TAGS:
            self.CommandAssignUnassignedTags()
        # Project scale
        elif id == ID_DLGMNGR_PROJECT_SCALE:
            self.CommandProjectScale()

        # Player tab
        # Player start/stop
        elif id == ID_DLGMNGR_PLAYER_START_STOP:
            self.CommandPlayerStart()
        elif id == ID_DLGMNGR_PLAYER_TAG_SELECTION:
            self.CommandPlayChoice()
        # Player playback control
        elif id == ID_DLGMNGR_PLAYER_PAUSE:
            self.CommandPause()
        elif id == ID_DLGMNGR_PLAYER_SYNC_WITH_LIVE:
            self.CommandPause(returnToLive=True)
        elif id == ID_DLGMNGR_PLAYER_PLAYBACK_SPEED:
            self.CommandPlaybackSpeed()
        elif id == ID_DLGMNGR_PLAYER_CURRENT_FRAME: # scrub bar
            self.CommandJumpToFrame(self.GetInt32(id))
        elif id == ID_DLGMNGR_PLAYER_FIRST_FRAME:
            self.CommandJumpToFrame(0)
        elif id == ID_DLGMNGR_PLAYER_LAST_FRAME:
            _, maxFrame = g_thdListener.GetCurrentFrameNumber()
            self.CommandJumpToFrame(maxFrame - 1)
        # Player parameters
        elif id == ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT:
            self.CommandAnimateDocument()
        elif id == ID_DLGMNGR_PLAYER_SAVE:
            self.CommandStartSaveRecording()

        # Command API tab
        elif id == ID_DLGMNGR_COMMANDAPI_START_RECORDING or id == ID_DLGMNGR_COMMANDAPI_STOP_RECORDING or \
             id == ID_DLGMNGR_COMMANDAPI_CALIBRATE_ALL_SUITS or id == ID_DLGMNGR_COMMANDAPI_RESET_ALL_SUITS:
            self.CommandCommandAPI(id)

        # Help menu
        # Web links
        elif id == ID_DLGMNGR_WEB_ROKOKO or id == ID_DLGMNGR_WEB_STUDIO_LIVE_LICENSE or \
             id == ID_DLGMNGR_WEB_DOCUMENTATION or id == ID_DLGMNGR_WEB_FORUMS:
            self.CommandWeb(id)
        # About
        elif id == ID_DLGMNGR_ABOUT:
            self.CommandAbout()
        return True
