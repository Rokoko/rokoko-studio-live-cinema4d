'''The central user interface of Rokoko Studio Live.

- Connection to Rokoko Studio
- Motion data Clip libraries (one global or C4D wide, one in current scene)
- All Rokoko Tags contained in a sceneare listed and can be configured here
- Player, really only the Player interface, the actual Player is inside the
  listener thread
- Command API

The dialog itself holds no (almost no) data or state. All data is stored in
world prefs, document data and/or Rokoko tag's BaseContainer. The dialog only
displays this data and provides means to change such distributed information
from a central place.
'''

import json
import os
import shutil
import urllib.request

__USE_LZ4__ = True
try:
    import lz4.frame as lz4f
except ImportError:
    __USE_LZ4__ = False

import c4d

import rokoko_ids as rid
from rokoko_utils import (
    AddDataSetBC,
    BaseContainerDataSet,
    GetConnectedDataSet,
    GetConnectedDataSetId,
    GetCoreMessageParam,
    GetLocalDataSets,
    GetPref,
    GetPrefsContainer,
    GetProjectScale,
    GetTagList,
    IsConnected,
    MyHash,
    RemoveConnection,
    RemoveDataSetBC,
    RigTypeToEntitiesBcId,
    SetPref,
    SetProjectScale,
    StoreAvailableEntitiesInDataSet,
)
from rokoko_listener import GetListenerThread
from rokoko_dialog_utils import (
    CreateLayoutAddBitmapButton,
    CreateLayoutAddGroupBar,
    CreateLayoutAddQuickTab,
)
from rokoko_dialog_about import DialogAbout
from rokoko_dialog_save_recording import DialogSaveRecording
from rokoko_dialog_edit_connection import DialogEditConnection
from rokoko_dialog_edit_dataset import DialogEditDataSet


# To disable actual file operations (clip management) during development
DO_FILE_ACTION = True

# Web links in Help menu
LINKS = {
    rid.ID_DLGMNGR_WEB_ROKOKO: rid.LINK_ROKOKO,
    rid.ID_DLGMNGR_WEB_STUDIO_LIVE_LICENSE: rid.LINK_STUDIO_LIVE_LICENSE,
    rid.ID_DLGMNGR_WEB_DOCUMENTATION: rid.LINK_DOCUMENTATION,
    rid.ID_DLGMNGR_WEB_FORUMS: rid.LINK_FORUMS,
}

# Width of left button column ("+" and "..." buttons)
WIDTH_ADD_BUTTON = 16


g_thdListener = GetListenerThread()  # owned by rokoko_listener


def DlgManagerDataDestroyGlobals():
    '''To be called during shutdown'''
    global g_thdListener

    g_thdListener = None


class DialogRokokoManager(c4d.gui.GeDialog):
    # Save Recording and Baking dialog
    _dlgChild = None

    # CustomGUI handles
    # Quick tab to switch between dialog groups
    _quickTab = None
    # Player's Play/Pause button (needed to toggle its state)
    _bitmapButtonPlayPause = None
    # Connection status dot in menu row
    _bitmapButtonConnectionStatus = None
    # Connection status dots in connection rows
    _bitmapButtonsPerConnectionStatus = []

    # List of all Rokoko tags in current document
    _tags = None

    # UI states
    # Start Recording"/"Save Recording..." button changes function according to
    # this flag
    _buttonRecordState = False
    # Used to disable "Connect" buttons while connecting
    _connecting = False

    def CreateLayoutAddMenu(self):
        '''Create main menu.'''

        self.MenuFlushAll()

        self.MenuSubBegin("Help")
        self.MenuAddString(rid.ID_DLGMNGR_WEB_ROKOKO, "Rokoko Website")
        self.MenuAddString(rid.ID_DLGMNGR_WEB_STUDIO_LIVE_LICENSE,
                           "Rokoko Studio Live License")
        self.MenuAddString(rid.ID_DLGMNGR_WEB_DOCUMENTATION, "Documentation")
        self.MenuAddString(rid.ID_DLGMNGR_WEB_FORUMS, "Join our forums")
        self.MenuAddSeparator()
        self.MenuAddString(rid.ID_DLGMNGR_ABOUT, "About")
        self.MenuSubEnd()  # Help

        self.MenuFinished()

    def CreateLayoutInMenu(self):
        '''Create widgets in main menu row (right of menu).'''

        self.GroupBeginInMenuLine()

        self.AddComboBox(
            rid.ID_DLGMNGR_CONNECTIONS_IN_MENU, c4d.BFH_RIGHT, initw=200)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=10, name="")  # spacer
        self._bitmapButtonConnectionStatus = CreateLayoutAddBitmapButton(
            self,
            0,
            idIcon1=465003508,
            tooltip="",
            button=False, toggle=False,
            flags=c4d.BFH_CENTER | c4d.BFV_CENTER)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=10, name="")  # spacer
        self.AddSlider(
            rid.ID_DLGMNGR_PLAYER_BUFFERING_IN_MENU,
            flags=c4d.BFH_LEFT, initw=40)
        self.Enable(rid.ID_DLGMNGR_PLAYER_BUFFERING_IN_MENU, False)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=10, name="")  # spacer

        self.GroupEnd()

    def UpdateLayoutInMenu(self):
        '''Update widgets in main menu row.'''

        # Rebuild Connection combo box.
        isConnected = IsConnected()
        idConnected = GetConnectedDataSetId()

        self.FreeChildren(rid.ID_DLGMNGR_CONNECTIONS_IN_MENU)

        # First add an option to
        if isConnected:
            self.AddChild(
                rid.ID_DLGMNGR_CONNECTIONS_IN_MENU, 999999, "Disconnect")
            self.AddChild(
                rid.ID_DLGMNGR_CONNECTIONS_IN_MENU, 1000000, "")  # separator

        bcConnections = GetPrefsContainer(rid.ID_BC_CONNECTIONS)
        idxConnected = 999999
        if len(bcConnections) > 0:
            idx = 0
            for id, bcConnection in bcConnections:
                self.AddChild(
                    rid.ID_DLGMNGR_CONNECTIONS_IN_MENU,
                    idx,
                    bcConnection[rid.ID_BC_DATASET_NAME])
                if id == idConnected:
                    idxConnected = idx
                idx += 1

        # Lastly add a "Not Connected" enttry, which will be selected and
        # shown, if this is the case
        if not isConnected:
            self.AddChild(
                rid.ID_DLGMNGR_CONNECTIONS_IN_MENU, 1000000, "")  # separator
            self.AddChild(
                rid.ID_DLGMNGR_CONNECTIONS_IN_MENU, 999999, "Not Connected")

        # Select current connection (or "Not Connencted")
        self.SetInt32(rid.ID_DLGMNGR_CONNECTIONS_IN_MENU, idxConnected)

        # Update the connection status dot
        statusConnection = g_thdListener.GetConnectionStatus()

        # Get icon based on connection status
        if statusConnection == 0:
            idIcon = 465003508  # red dot
        elif statusConnection == 1:
            idIcon = 465001743  # green dot
        elif statusConnection == 2 and isConnected:
            idIcon = 465001740  # orange dot
        elif statusConnection == 2 and not isConnected:
            idIcon = 465001746  # grey dot
        icon = c4d.gui.GetIcon(idIcon)

        # Get icon bitmap.
        # In C4D most application icons are stored in a single bitmap.
        # The icon structure only contains a reference to the correct part of
        # this bitmap.
        bmpIcon = icon["bmp"].GetClonePart(
            icon["x"], icon["y"], icon["w"], icon["h"])

        # Update image in status button.
        self._bitmapButtonConnectionStatus.SetImage(bmpIcon)

        # If player is in offline state (see rokoko_listener),
        # disable the status dot.
        self.Enable(rid.ID_DLGMNGR_CONNECTION_STATUS_IN_MENU,
                    statusConnection != 2 or isConnected)

        # Disable connections combo box while connecting
        self.Enable(rid.ID_DLGMNGR_CONNECTIONS_IN_MENU, not self._connecting)

    def CreateLayoutRowConnection(self, bc, idx):
        '''Creates the widgets for a single connection, one row.'''

        # Popup menu button.
        self.AddButton(
            rid.ID_DLGMNGR_BASE_CONNECTION_POPUP + idx,
            c4d.BFH_FIT,
            initw=WIDTH_ADD_BUTTON,
            name="...")

        # Name
        labelConnection = bc[rid.ID_BC_DATASET_NAME]
        labelConnection += f" ({bc[rid.ID_BC_DATASET_LIVE_PORT]})"
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name=labelConnection)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=20, name="")  # spacer

        # Auto Connect
        self.AddCheckbox(
            rid.ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT + idx,
            c4d.BFH_CENTER,
            initw=0, inith=0,
            name="Auto Connect")
        self.AddStaticText(0, c4d.BFH_LEFT, initw=10, name="")  # spacer

        # Connection status
        bitmapButton = CreateLayoutAddBitmapButton(
            self,
            0,
            idIcon1=465003508,
            tooltip="",
            button=False, toggle=False,
            flags=c4d.BFH_CENTER | c4d.BFV_CENTER)
        self._bitmapButtonsPerConnectionStatus.append(bitmapButton)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=10, name="")  # spacer

        # Connect/(Disconnect button)
        self.AddButton(
            rid.ID_DLGMNGR_BASE_CONNECTION_CONNECT + idx,
            c4d.BFH_FIT,
            initw=100,
            name="")

        # Meta data of connection, if connected.
        # Currently only the FPS contained in motion data get shown here.
        # TODO: Currently not prepared for multiple connections
        if self.GroupBegin(
                rid.ID_DLGMNGR_GROUP_CONNECTION_DATA_CONTENT,
                flags=c4d.BFH_SCALEFIT, title="", rows=1):
            self.AddStaticText(0, c4d.BFH_LEFT, initw=20, name="")  # spacer
            self.AddStaticText(
                rid.ID_DLGMNGR_CONNECTION_FPS,
                c4d.BFH_CENTER,
                initw=0,
                name="")
        self.GroupEnd()

    def CreateLayoutGroupConnections(self):
        '''Creates all widgets on "Connection" tab.

        The implementation allows for multiple connections (with only one
        active at a time). Currently this is deliberately restricted to just
        one connection, which always exists.
        Therefore the add connection button ("+") and the remove connection
        option in connection's popup menu got removed.
        '''

        if self.GroupBegin(  # Tab group
                rid.ID_DLGMNGR_GROUP_CONNECTIONS,
                flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP,
                title="", cols=1):

            CreateLayoutAddGroupBar(self, "Connection")

            if self.GroupBegin(  # Connections
                    0,
                    flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP,
                    title="",
                    cols=1,
                    inith=16):
                scrollFlags = \
                    c4d.SCROLLGROUP_VERT | \
                    c4d.SCROLLGROUP_AUTOVERT | \
                    c4d.SCROLLGROUP_NOVGAP
                if self.ScrollGroupBegin(  # Scroll connection rows
                        rid.ID_DLGMNGR_SCROLL_CONNECTIONS,
                        c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                        scrollFlags,
                        initw=0, inith=0):

                    if self.GroupBegin(  # Connection rows
                            0,
                            flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                            title="",
                            cols=9):
                        self.GroupBorderSpace(10, 2, 0, 0)

                        # Throw away all connection status buttons,
                        # these will be recreated below
                        self._bitmapButtonsPerConnectionStatus.clear()

                        bcConnections = GetPrefsContainer(
                            rid.ID_BC_CONNECTIONS)

                        if len(bcConnections) > 0:
                            # Iterate all connections
                            idx = 0
                            for id, bcConnection in bcConnections:
                                # Add a row with widgets per connection
                                self.CreateLayoutRowConnection(
                                    bcConnection, idx)
                                idx += 1
                        else:
                            self.AddStaticText(
                                0,
                                c4d.BFH_LEFT,
                                initw=0,
                                name="No connections configured.")
                    self.GroupEnd()  # Connection rows
                self.GroupEnd()  # Scroll connection rows
            self.GroupEnd()  # Connections

            # The two groups have historical reasons and are only kept as
            # we may want to return to a more complex design later on.
            if self.GroupBegin(  # # Connection data
                    rid.ID_DLGMNGR_GROUP_CONNECTION_DATA,
                    flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP,
                    title="",
                    cols=1):
                self.GroupBorderSpace(38, 0, 0, 0)

                if self.GroupBegin(  # Connection details
                        rid.ID_DLGMNGR_GROUP_CONNECTION_DATA_DETAILS,
                        flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                        title="",
                        cols=2):
                    self.GroupBorderSpace(10, 0, 0, 0)
                    # filled in UpdateLayoutGroupConnectedDataSet()
                self.GroupEnd()  # Connection details
            self.GroupEnd()  # Connection data
        self.GroupEnd()  # Tab group

    def UpdateLayoutGroupConnections(self):
        '''Relayouts (or updates)  the "Connection" tab'''

        self.LayoutFlushGroup(rid.ID_DLGMNGR_GROUP_CONNECTIONS)
        self.CreateLayoutGroupConnections()
        self.LayoutChanged(rid.ID_DLGMNGR_GROUP_CONNECTIONS)

    def UpdateLayoutGroupConnectedDataSet(self):
        '''Relayout subgroup of "Connection1" tab showing the content of
        the current connection
        '''

        # Get current connection and its meta data
        bc = GetConnectedDataSet()
        numActors = 0
        # numGloves = 0
        # numFaces = 0
        # numLights = 0
        # numCameras = 0
        numProps = 0
        # name = ""
        fps = 0.0
        if bc is not None:
            # name = bc[0]
            numActors = bc[rid.ID_BC_DATASET_NUM_SUITS]
            # numGloves = bc[rid.ID_BC_DATASET_NUM_GLOVES]
            # numFaces = bc[rid.ID_BC_DATASET_NUM_FACES]
            # numLights = bc[rid.ID_BC_DATASET_NUM_LIGHTS]
            # numCameras = bc[rid.ID_BC_DATASET_NUM_CAMERAS]
            numProps = bc[rid.ID_BC_DATASET_NUM_PROPS]
            fps = bc[rid.ID_BC_DATASET_LIVE_FPS]

        # Set FPS in row of connection # TODO: not correct with
        # multiple connections
        self.SetString(rid.ID_DLGMNGR_CONNECTION_FPS, f"(FPS: {fps})")

        # Relayout data content group
        self.LayoutFlushGroup(rid.ID_DLGMNGR_GROUP_CONNECTION_DATA_DETAILS)

        # Actors
        if numActors > 0:
            bcActors = bc[rid.ID_BC_DATASET_ACTORS]
            self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name="")  # spacer

            if self.GroupBegin(  # actor rows
                    0,
                    flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                    title="",
                    cols=6):
                for idxActor, bcActor in bcActors:
                    # Actor icon
                    CreateLayoutAddBitmapButton(
                        self,
                        0,
                        idIcon1=rid.PLUGIN_ID_ICON_PROFILE,
                        tooltip="",
                        button=False, toggle=False,
                        flags=c4d.BFH_LEFT | c4d.BFV_CENTER)

                    # Actor name
                    self.AddStaticText(
                        0,
                        c4d.BFH_LEFT,
                        initw=0,
                        name=bcActor[rid.ID_BC_ENTITY_NAME])

                    # Icons for Suit, Gloves and Face (spacer in order to have
                    # them in correctly aligned columns with multiple actors)
                    if bcActor[rid.ID_BC_ENTITY_HAS_SUIT]:
                        CreateLayoutAddBitmapButton(
                            self,
                            0,
                            idIcon1=rid.PLUGIN_ID_ICON_SUIT,
                            tooltip="",
                            button=False,
                            toggle=False,
                            flags=c4d.BFH_LEFT | c4d.BFV_CENTER)
                    else:
                        self.AddStaticText(
                            0, c4d.BFH_LEFT, initw=0, name="")  # spacer

                    if bcActor[rid.ID_BC_ENTITY_HAS_FACE]:
                        CreateLayoutAddBitmapButton(
                            self,
                            0,
                            idIcon1=rid.PLUGIN_ID_ICON_FACE,
                            tooltip="",
                            button=False, toggle=False,
                            flags=c4d.BFH_LEFT | c4d.BFV_CENTER)
                    else:
                        self.AddStaticText(
                            0, c4d.BFH_LEFT, initw=0, name="")  # spacer

                    if bcActor[rid.ID_BC_ENTITY_HAS_GLOVE_LEFT]:
                        CreateLayoutAddBitmapButton(
                            self,
                            0,
                            idIcon1=rid.PLUGIN_ID_ICON_GLOVE_LEFT,
                            tooltip="",
                            button=False,
                            toggle=False,
                            flags=c4d.BFH_LEFT | c4d.BFV_CENTER)
                    else:
                        self.AddStaticText(
                            0, c4d.BFH_LEFT, initw=0, name="")  # spacer

                    if bcActor[rid.ID_BC_ENTITY_HAS_GLOVE_RIGHT]:
                        CreateLayoutAddBitmapButton(
                            self,
                            0,
                            idIcon1=rid.PLUGIN_ID_ICON_GLOVE_RIGHT,
                            tooltip="",
                            button=False, toggle=False,
                            flags=c4d.BFH_LEFT | c4d.BFV_CENTER)
                    else:
                        self.AddStaticText(
                            0, c4d.BFH_LEFT, initw=0, name="")  # spacer
            self.GroupEnd()  # actor rows

        # Props
        if numProps > 0:
            bcProps = bc[rid.ID_BC_DATASET_PROPS]
            self.AddStaticText(
                0, c4d.BFH_LEFT, initw=0, name="")  # spacer

            if self.GroupBegin(  # Prop rows
                    0,
                    flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                    title="",
                    cols=2):

                for idxProp, bcProp in bcProps:
                    CreateLayoutAddBitmapButton(
                        self,
                        0,
                        idIcon1=rid.PLUGIN_ID_ICON_PROP,
                        tooltip="",
                        button=False, toggle=False,
                        flags=c4d.BFH_LEFT | c4d.BFV_CENTER)
                    self.AddStaticText(
                        0,
                        c4d.BFH_LEFT,
                        initw=0,
                        name=bcProp[rid.ID_BC_ENTITY_NAME])
            self.GroupEnd()  # Prop rows

        # If there are neither actors nor props, show message
        if numActors == 0 and numProps == 0:
            self.AddStaticText(
                0, c4d.BFH_LEFT, initw=0, name="Receiving no data!")

        self.LayoutChanged(rid.ID_DLGMNGR_GROUP_CONNECTION_DATA_DETAILS)

    def CreateLayoutHeadingsDataSet(self, local):
        '''Heading row for data sets'''

        # Add to the correct library "Add" button (global or project/local)
        if local:
            idButtonPopup = rid.ID_DLGMNGR_LOCAL_DATA_POPUP
        else:
            idButtonPopup = rid.ID_DLGMNGR_GLOBAL_DATA_POPUP

        # Data set library "+" button
        self.AddButton(
            idButtonPopup,
            c4d.BFH_LEFT,
            initw=WIDTH_ADD_BUTTON,
            inith=0,
            name="+")

        # Column Headings
        self.AddStaticText(0, c4d.BFH_LEFT, initw=150, name="Name")
        self.AddStaticText(0, c4d.BFH_LEFT, initw=20, name="")  # spacer
        CreateLayoutAddBitmapButton(
            self,
            0,
            idIcon1=rid.PLUGIN_ID_ICON_SUIT,
            tooltip="Number of Suits",
            button=False, toggle=False,
            flags=c4d.BFH_RIGHT | c4d.BFV_CENTER)
        CreateLayoutAddBitmapButton(
            self,
            0,
            idIcon1=rid.PLUGIN_ID_ICON_GLOVE_LEFT,
            tooltip="Number of Gloves",
            button=False, toggle=False,
            flags=c4d.BFH_RIGHT | c4d.BFV_CENTER)
        CreateLayoutAddBitmapButton(
            self,
            0,
            idIcon1=rid.PLUGIN_ID_ICON_FACE,
            tooltip="Number of Faces",
            button=False, toggle=False,
            flags=c4d.BFH_RIGHT | c4d.BFV_CENTER)
        CreateLayoutAddBitmapButton(
            self,
            0,
            idIcon1=rid.PLUGIN_ID_ICON_PROP,
            tooltip="Number of Props",
            button=False, toggle=False,
            flags=c4d.BFH_RIGHT | c4d.BFV_CENTER)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=20, name="")  # spacer
        self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=0, name="File")

    def CreateLayoutRowDataSet(self, bcDataSet, idx):
        '''Creates the widgets for a single data set (clip), one row.'''

        # Use correct ID base for buttons in global or project/local library
        if bcDataSet[rid.ID_BC_DATASET_IS_LOCAL]:
            idButtonBase = rid.ID_DLGMNGR_BASE_LOCAL_DATA_POPUP
        else:
            idButtonBase = rid.ID_DLGMNGR_BASE_GLOBAL_DATA_POPUP

        # Add popup menu button ("...")
        self.AddButton(
            idButtonBase + idx,
            c4d.BFH_FIT,
            initw=WIDTH_ADD_BUTTON,
            name="...")

        # Add data set info
        self.AddStaticText(
            0,
            c4d.BFH_LEFT,
            initw=0,
            name=bcDataSet[rid.ID_BC_DATASET_NAME])
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name="")  # spacer
        self.AddStaticText(
            0,
            c4d.BFH_CENTER,
            initw=0,
            name=bcDataSet[rid.ID_BC_DATASET_NUM_SUITS])
        self.AddStaticText(
            0,
            c4d.BFH_CENTER,
            initw=0,
            name=bcDataSet[rid.ID_BC_DATASET_NUM_GLOVES])
        self.AddStaticText(
            0,
            c4d.BFH_CENTER,
            initw=0,
            name=bcDataSet[rid.ID_BC_DATASET_NUM_FACES])
        self.AddStaticText(
            0,
            c4d.BFH_CENTER,
            initw=0,
            name=bcDataSet[rid.ID_BC_DATASET_NUM_PROPS])
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name="")  # spacer
        self.AddStaticText(
            0,
            c4d.BFH_SCALEFIT,
            initw=0,
            name=bcDataSet[rid.ID_BC_DATASET_FILENAME])

    def CreateLayoutGroupDataSet(self, local):
        '''Creates all widgets on a "Clips" library tab,
        either global or local.

        There are two clip libraries. Global in C4D's preferences and local in
        a document (project).
        Thus dialog also has two tabs representing these libraries.
        '''

        # Only few things
        if local:
            # ID of project library tab group
            idGroup = rid.ID_DLGMNGR_GROUP_LOCAL_DATA
            # tab title project library
            nameGroup = "Project Clips"
            # the project library
            bcDataSets = GetLocalDataSets()
        else:
            # ID of global library tab group
            idGroup = rid.ID_DLGMNGR_GROUP_GLOBAL_DATA
            # tab title global library
            nameGroup = "Global Clips"
            # the global library
            bcDataSets = GetPrefsContainer(rid.ID_BC_DATA_SETS)

        if self.GroupBegin(  # Tab group
                idGroup,
                flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                title="",
                cols=1):

            CreateLayoutAddGroupBar(self, nameGroup)

            if self.GroupBegin(  # Data sets
                    0,
                    flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                    title="",
                    cols=1,
                    inith=52):

                scrollFlags = \
                    c4d.SCROLLGROUP_VERT | \
                    c4d.SCROLLGROUP_AUTOVERT | \
                    c4d.SCROLLGROUP_NOVGAP
                if self.ScrollGroupBegin(  # Scroll data set rows
                        0,
                        c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                        scrollFlags,
                        initw=0, inith=0):

                    if self.GroupBegin(  # Data set rows
                            0,
                            flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                            title="",
                            cols=9):
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
                            self.AddStaticText(
                                0, c4d.BFH_LEFT, initw=0, name="")  # spacer
                            self.AddStaticText(
                                0, c4d.BFH_LEFT, initw=0, name="No data sets.")
                    self.GroupEnd()  # Data set rows
                self.GroupEnd()  # Scroll data set rows
            self.GroupEnd()  # Data sets
        self.GroupEnd()  # Tab group

    def UpdateLayoutGroupDataSet(self, local):
        '''Relayouts (or updates) a "Clips" tab, either global or local.'''

        # Use correct ID for tab group of global or project/local library
        if local:
            idGroup = rid.ID_DLGMNGR_GROUP_LOCAL_DATA
        else:
            idGroup = rid.ID_DLGMNGR_GROUP_GLOBAL_DATA

        # Relayout tab
        self.LayoutFlushGroup(idGroup)
        self.CreateLayoutGroupDataSet(local)
        self.LayoutChanged(idGroup)

    def CreateLayoutRowControl(self, tag, idx):
        '''Creates the widgets for a single Rokoko tag, one row.'''

        if tag is None or not tag.IsAlive():
            return

        # Get host object's icon
        bmpObj = None
        obj = tag.GetObject()
        if obj is not None:
            objName = obj.GetName()
            iconDataObj = obj.GetIcon()
            bmpObj = iconDataObj["bmp"].GetClonePart(
                iconDataObj["x"], iconDataObj["y"],
                iconDataObj["w"], iconDataObj["h"])
        else:
            objName = "Tag not assigned"

        # Get tag's icon
        iconDataTag = tag.GetIcon()
        bmpTag = iconDataTag["bmp"].GetClonePart(
            iconDataTag["x"], iconDataTag["y"],
            iconDataTag["w"], iconDataTag["h"])

        # Add popup menu button ("...")
        self.AddButton(
            rid.ID_DLGMNGR_BASE_TAG_POPUP + idx,
            c4d.BFH_FIT,
            initw=WIDTH_ADD_BUTTON,
            name="...")

        # Host object icon and name
        CreateLayoutAddBitmapButton(
            self,
            0,
            bmpTag,
            tooltip="",
            button=False, toggle=False,
            flags=c4d.BFH_LEFT | c4d.BFV_CENTER)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name=tag.GetName())
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name="")  # spacer

        # Tag icon and name
        CreateLayoutAddBitmapButton(
            self,
            0,
            bmpObj,
            tooltip="",
            button=False, toggle=False,
            flags=c4d.BFH_LEFT | c4d.BFV_CENTER)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name=objName)
        self.AddStaticText(0, c4d.BFH_LEFT, initw=0, name="")  # spacer

        # Tag type combo box
        self.AddComboBox(
            rid.ID_DLGMNGR_BASE_TAG_RIG_TYPES + idx, c4d.BFH_SCALEFIT)
        bcRigTypes = tag.GetDataInstance().GetContainerInstance(
            rid.ID_TAG_BC_RIG_TYPES)
        for idxRigType, value in bcRigTypes:
            self.AddChild(
                rid.ID_DLGMNGR_BASE_TAG_RIG_TYPES + idx, idxRigType, value)

        # Data combo box
        self.AddComboBox(
            rid.ID_DLGMNGR_BASE_TAG_DATA_SETS + idx, c4d.BFH_SCALEFIT)
        bcDataSets = tag.GetDataInstance().GetContainerInstance(
            rid.ID_TAG_BC_DATASETS)
        for idxDataSet, value in bcDataSets:
            self.AddChild(
                rid.ID_DLGMNGR_BASE_TAG_DATA_SETS + idx, idxDataSet, value)

        # Enttity combo box
        self.AddComboBox(
            rid.ID_DLGMNGR_BASE_TAG_ACTORS + idx, c4d.BFH_SCALEFIT)
        bcDataSets = tag.GetDataInstance().GetContainerInstance(
            rid.ID_TAG_BC_ACTORS)
        for idxActor, value in bcDataSets:
            self.AddChild(
                rid.ID_DLGMNGR_BASE_TAG_ACTORS + idx, idxActor, value)

        # "Select for Player" checkbox
        self.AddCheckbox(
            rid.ID_DLGMNGR_BASE_DATA_SET_ENABLED + idx,
            c4d.BFH_CENTER,
            initw=0, inith=0,
            name="")

    def CreateLayoutGroupControl(self):
        '''Creates all widgets on a "Tags" tab.'''

        if self.GroupBegin(  # Tab group
                rid.ID_DLGMNGR_GROUP_CONTROL,
                flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                title="",
                cols=1):

            CreateLayoutAddGroupBar(self, "Tags")

            if self.GroupBegin(  # Tags
                    0,
                    flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                    title="",
                    cols=1,
                    inith=80):

                scrollFlags = \
                    c4d.SCROLLGROUP_VERT | \
                    c4d.SCROLLGROUP_AUTOVERT | \
                    c4d.SCROLLGROUP_NOVGAP
                if self.ScrollGroupBegin(  # Scroll tag rows
                        rid.ID_DLGMNGR_SCROLL_LOCAL_DATA,
                        c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                        scrollFlags,
                        initw=0, inith=0):

                    if self.GroupBegin(  # Tag rows
                            0,
                            flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                            title="",
                            cols=11):
                        self.GroupBorderSpace(10, 2, 0, 0)

                        # Heading

                        # Tags "+" button ("Create Scene" and such)
                        self.AddButton(
                            rid.ID_DLGMNGR_TAGS_POPUP,
                            c4d.BFH_LEFT,
                            initw=WIDTH_ADD_BUTTON, inith=0,
                            name="+")

                        # Column headings
                        self.AddStaticText(
                            0, c4d.BFH_LEFT, initw=30, name="")  # spacer
                        self.AddStaticText(
                            0, c4d.BFH_LEFT, initw=0, name="Tag")
                        self.AddStaticText(
                            0, c4d.BFH_LEFT, initw=20, name="")  # spacer
                        self.AddStaticText(
                            0, c4d.BFH_LEFT, initw=30, name="")  # spacer
                        self.AddStaticText(
                            0, c4d.BFH_LEFT, initw=0, name="Object")
                        self.AddStaticText(
                            0, c4d.BFH_LEFT, initw=20, name="")  # spacer
                        self.AddStaticText(
                            0, c4d.BFH_LEFT, initw=150, name="Rig Typ")
                        self.AddStaticText(
                            0, c4d.BFH_SCALEFIT, initw=100, name="Live/Clip")
                        self.AddStaticText(
                            0, c4d.BFH_SCALEFIT, initw=100, name="Actor")
                        self.AddStaticText(
                            0, c4d.BFH_RIGHT, initw=35, name="Sel")

                        # Iterate all tags in current document
                        if self._tags is not None and len(self._tags) > 0:
                            for idxTag, tag in enumerate(self._tags):
                                # Add a row with widgets per tag
                                self.CreateLayoutRowControl(tag, idxTag)
                        else:
                            self.AddStaticText(
                                0,
                                c4d.BFH_LEFT,
                                initw=0,
                                name=("No Rokoko tags found in current "
                                      "document."))
                    self.GroupEnd()  # Tag rows
                self.GroupEnd()  # Scroll tag rows
            self.GroupEnd()  # Tags

            if self.GroupBegin(  # Bottom row
                    0,
                    flags=c4d.BFH_SCALEFIT | c4d.BFV_BOTTOM,
                    title="",
                    cols=8):
                self.GroupBorderSpace(10, 0, 0, 0)

                # Project scale
                self.AddStaticText(
                    0, c4d.BFH_LEFT, initw=0, name="Project Scale")
                self.AddEditNumberArrows(
                    rid.ID_DLGMNGR_PROJECT_SCALE, c4d.BFH_LEFT, initw=60)

                self.AddStaticText(
                    0, c4d.BFH_SCALEFIT, initw=10, name="")  # spacer

                # Assign unassigned tags to live connection
                self.AddButton(
                    rid.ID_DLGMNGR_ASSIGN_UNASSIGNED_TAGS,
                    c4d.BFH_RIGHT,
                    initw=150, inith=0,
                    name="Unassigned to Live")

                self.AddStaticText(
                    0, c4d.BFH_RIGHT, initw=10, name="")  # spacer

                # Select buttons
                self.AddButton(
                    rid.ID_DLGMNGR_SELECT_ALL_TAGS,
                    c4d.BFH_RIGHT,
                    initw=150, inith=0,
                    name="Select All")
                self.AddButton(
                    rid.ID_DLGMNGR_DESELECT_ALL_TAGS,
                    c4d.BFH_RIGHT,
                    initw=150, inith=0,
                    name="Deselect All")
                self.AddButton(
                    rid.ID_DLGMNGR_INVERT_SELECTION,
                    c4d.BFH_RIGHT,
                    initw=150, inith=0,
                    name="Invert Selection")
            self.GroupEnd()  # Bottom row
        self.GroupEnd()  # Tab group

    def UpdateLayoutGroupControl(self):
        '''Relayouts (or updates) the "Tags" tab.'''

        self.LayoutFlushGroup(rid.ID_DLGMNGR_GROUP_CONTROL)
        self.CreateLayoutGroupControl()
        self.LayoutChanged(rid.ID_DLGMNGR_GROUP_CONTROL)

    def CreateLayoutGroupLive(self):
        '''Creates all widgets on a "Player" tab.'''

        if self.GroupBegin(  # Tab group
                rid.ID_DLGMNGR_GROUP_PLAYER,
                flags=c4d.BFH_SCALEFIT | c4d.BFV_FIT,
                title="",
                cols=1):

            CreateLayoutAddGroupBar(self, "Player")

            # wButton = c4d.gui.SizePix(200)
            hButton = c4d.gui.SizePix(50)

            if self.GroupBegin(  # Start
                    0,
                    flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP,
                    title="",
                    cols=2):
                self.GroupBorderSpace(10, 2, 0, 0)

                # Start/Stop Player button
                self.AddButton(
                    rid.ID_DLGMNGR_PLAYER_START_STOP,
                    c4d.BFH_LEFT,
                    initw=150,
                    name="Start Player")

                # Radio button group to select involved tags
                self.AddRadioGroup(
                    rid.ID_DLGMNGR_PLAYER_TAG_SELECTION, c4d.BFH_LEFT, rows=1)
                self.AddChild(rid.ID_DLGMNGR_PLAYER_TAG_SELECTION, 0, "All")
                self.AddChild(
                    rid.ID_DLGMNGR_PLAYER_TAG_SELECTION, 1, "Selected")
                self.AddChild(rid.ID_DLGMNGR_PLAYER_TAG_SELECTION, 2, "Live")
                self.AddChild(rid.ID_DLGMNGR_PLAYER_TAG_SELECTION, 3, "Clips")
            self.GroupEnd()  # Start

            if self.GroupBegin(  # Player
                    0,
                    flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP,
                    title="",
                    cols=1):
                self.GroupBorderSpace(10, 0, 0, 0)

                # Row "Active Tags"
                # TODO: This needs to be a horizontal scroll group

                scrollFlags = \
                    c4d.SCROLLGROUP_HORIZ | \
                    c4d.SCROLLGROUP_AUTOHORIZ | \
                    c4d.SCROLLGROUP_NOVGAP
                if self.ScrollGroupBegin(  # Scroll active tags
                        0,
                        c4d.BFH_SCALEFIT | c4d.BFV_TOP,
                        scrollFlags,
                        initw=0, inith=0):
                    if self.GroupBegin(  # Active tags
                            0,
                            flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP,
                            title="",
                            cols=2):
                        # Label
                        self.AddStaticText(
                            rid.ID_DLGMNGR_PLAYER_ACTIVE_TAGS_LABEL,
                            c4d.BFH_LEFT,
                            initw=0,
                            name="Active Tags:")

                        # Actual tag names will be listed in here
                        self.AddStaticText(
                            rid.ID_DLGMNGR_PLAYER_ACTIVE_TAGS,
                            c4d.BFH_SCALEFIT,
                            initw=0,
                            name="None")
                    self.GroupEnd()  # Active tags
                self.GroupEnd()  # Scroll active tags

                if self.GroupBegin(  # Scrub bar and player buttons
                        0,
                        flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP,
                        title="",
                        cols=5):
                    # Scrub bar
                    self.AddEditSlider(
                        rid.ID_DLGMNGR_PLAYER_CURRENT_FRAME,
                        flags=c4d.BFH_SCALEFIT)

                    # First Frame
                    CreateLayoutAddBitmapButton(
                        self,
                        rid.ID_DLGMNGR_PLAYER_FIRST_FRAME,
                        idIcon1=12501,
                        tooltip="First Frame",
                        button=True, toggle=False,
                        flags=c4d.BFH_RIGHT | c4d.BFV_CENTER)

                    # Play/Pause
                    self._bitmapButtonPlayPause = CreateLayoutAddBitmapButton(
                        self,
                        rid.ID_DLGMNGR_PLAYER_PAUSE,
                        idIcon1=12412, idIcon2=12002,
                        tooltip="Play/Pause",
                        button=True, toggle=True,
                        flags=c4d.BFH_RIGHT | c4d.BFV_CENTER)

                    # Resync with live stream
                    CreateLayoutAddBitmapButton(
                        self,
                        rid.ID_DLGMNGR_PLAYER_SYNC_WITH_LIVE,
                        idIcon1=465001024,
                        tooltip="Play Live",
                        button=True, toggle=False,
                        flags=c4d.BFH_RIGHT | c4d.BFV_CENTER)

                    # Last Frame
                    CreateLayoutAddBitmapButton(
                        self,
                        rid.ID_DLGMNGR_PLAYER_LAST_FRAME,
                        idIcon1=12502,
                        tooltip="Last Frame",
                        button=True, toggle=False,
                        flags=c4d.BFH_RIGHT | c4d.BFV_CENTER)
                self.GroupEnd()  # Scrub bar and player buttons

                if self.GroupBegin(  # Start/save recording
                        0,
                        flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                        title="",
                        cols=1):
                    self.AddButton(
                        rid.ID_DLGMNGR_PLAYER_SAVE,
                        c4d.BFH_SCALEFIT | c4d.BFV_CENTER,
                        initw=0, inith=hButton,
                        name="")
                self.GroupEnd()  # Start/save recording

                # Bottom row with buffering indicator, playback rate,...
                if self.GroupBegin(  # Bottom row
                        0,
                        flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                        title="",
                        cols=6):
                    # Buffering indicator
                    self.AddStaticText(
                        rid.ID_DLGMNGR_PLAYER_BUFFERING_LABEL,
                        c4d.BFH_LEFT,
                        initw=0,
                        name="Buffering:")
                    self.AddSlider(
                        rid.ID_DLGMNGR_PLAYER_BUFFERING,
                        flags=c4d.BFH_LEFT,
                        initw=200)
                    # always disabled, only to show some movement
                    # if player is paused
                    self.Enable(
                        rid.ID_DLGMNGR_PLAYER_BUFFERING, False)

                    self.AddStaticText(
                        0, c4d.BFH_SCALEFIT, initw=0, name="")  # spacer

                    # Animate document
                    self.AddCheckbox(
                        rid.ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT,
                        c4d.BFH_RIGHT | c4d.BFH_SCALE,
                        initw=0, inith=0,
                        name="Animate Document")

                    # Playback rate
                    self.AddStaticText(
                        0,
                        c4d.BFH_RIGHT | c4d.BFH_SCALE,
                        initw=0,
                        name="Playback rate:")
                    self.AddComboBox(
                        rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED,
                        c4d.BFH_RIGHT,
                        initw=0)
                    self.AddChild(
                        rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED,
                        1, "1:1 (~60FPS)")
                    self.AddChild(
                        rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED,
                        2, "1:2 (~30FPS)")
                    self.AddChild(
                        rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED,
                        3, "1:3 (~20FPS)")
                    self.AddChild(
                        rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED,
                        4, "1:4 (~15FPS)")
                    self.AddChild(
                        rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED,
                        6, "1:6 (~10FPS)")
                    self.AddChild(
                        rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED,
                        12, "1:12 (~5FPS)")
                    self.AddChild(
                        rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED,
                        30, "1:30 (~2FPS)")
                    self.AddChild(
                        rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED,
                        60, "1:60 (~1FPS)")
                self.GroupEnd()  # Bottom row
            self.GroupEnd()  # Player
        self.GroupEnd()  # Tab group

    def UpdateLayoutGroupLive(self):
        '''Relayouts (or updates) the "Player" tab.'''

        self.LayoutFlushGroup(rid.ID_DLGMNGR_GROUP_PLAYER)
        self.CreateLayoutGroupLive()
        self.LayoutChanged(rid.ID_DLGMNGR_GROUP_PLAYER)

    def CreateLayoutGroupCommandAPI(self):
        '''Creates all widgets on a "Commandd API" tab.'''

        if self.GroupBegin(  # Tab group
                rid.ID_DLGMNGR_GROUP_COMMAND_API,
                flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP,
                title="",
                cols=1):

            CreateLayoutAddGroupBar(self, "Command API")

            if self.GroupBegin(  # Commands
                    0,
                    flags=c4d.BFH_SCALEFIT | c4d.BFV_TOP,
                    title="",
                    cols=4):
                self.GroupBorderSpace(10, 2, 0, 0)

                # Start recording
                CreateLayoutAddBitmapButton(
                    self,
                    rid.ID_DLGMNGR_COMMANDAPI_START_RECORDING,
                    idIcon1=rid.PLUGIN_ID_COMMAND_API_ICON_RECORD_START,
                    tooltip="Start Recording in Studio",
                    button=True, toggle=False,
                    flags=c4d.BFH_SCALEFIT)

                # Stop recording
                CreateLayoutAddBitmapButton(
                    self,
                    rid.ID_DLGMNGR_COMMANDAPI_STOP_RECORDING,
                    idIcon1=rid.PLUGIN_ID_COMMAND_API_ICON_RECORD_STOP,
                    tooltip="Stop Recording in Studio",
                    button=True, toggle=False,
                    flags=c4d.BFH_SCALEFIT)

                # Calibrate all suits
                CreateLayoutAddBitmapButton(
                    self,
                    rid.ID_DLGMNGR_COMMANDAPI_CALIBRATE_ALL_SUITS,
                    idIcon1=rid.PLUGIN_ID_COMMAND_API_ICON_CALIBRATE_SUIT,
                    tooltip="Start Calibration of all Smartsuits in Studio",
                    button=True, toggle=False,
                    flags=c4d.BFH_SCALEFIT)

                # Restart all suits
                CreateLayoutAddBitmapButton(
                    self,
                    rid.ID_DLGMNGR_COMMANDAPI_RESET_ALL_SUITS,
                    idIcon1=rid.PLUGIN_ID_COMMAND_API_ICON_RESTART_SUIT,
                    tooltip="Restart All Smartsuits",
                    button=True, toggle=False,
                    flags=c4d.BFH_SCALEFIT)
            self.GroupEnd()  # Commands
        self.GroupEnd()  # Tab group

    def UpdateLayoutGroupCommandAPI(self):
        '''Relayouts (or updates) the "Command API" tab.

        Currently not needed.
        '''

        self.LayoutFlushGroup(rid.ID_DLGMNGR_GROUP_COMMAND_API)
        self.CreateLayoutGroupCommandAPI()
        self.LayoutChanged(rid.ID_DLGMNGR_GROUP_COMMAND_API)

    def CreateLayout(self):
        '''Called by C4D to draw the dialog'''

        self.SetTitle("Rokoko Studio Live")  # dialog's window title

        self.CreateLayoutInMenu()

        if self.GroupBegin(  # Dialog main group
                rid.ID_DLGMNGR_GROUP_MAIN,
                flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                title="",
                cols=1):
            self.GroupBorderSpace(5, 5, 10, 5)

            # Add the tab bar to switch dialog groups
            self._quickTab = CreateLayoutAddQuickTab(self, rid.ID_DLGMNGR_TABS)
            self._quickTab.AppendString(
                rid.ID_DLGMNGR_GROUP_CONNECTIONS,
                "Connection",
                GetPref(rid.ID_DLGMNGR_GROUP_CONNECTIONS))
            self._quickTab.AppendString(
                rid.ID_DLGMNGR_GROUP_GLOBAL_DATA,
                "Global Clips",
                GetPref(rid.ID_DLGMNGR_GROUP_GLOBAL_DATA))
            self._quickTab.AppendString(
                rid.ID_DLGMNGR_GROUP_LOCAL_DATA,
                "Project Clips",
                GetPref(rid.ID_DLGMNGR_GROUP_LOCAL_DATA))
            self._quickTab.AppendString(
                rid.ID_DLGMNGR_GROUP_CONTROL,
                "Tags",
                GetPref(rid.ID_DLGMNGR_GROUP_CONTROL))
            self._quickTab.AppendString(
                rid.ID_DLGMNGR_GROUP_PLAYER,
                "Player",
                GetPref(rid.ID_DLGMNGR_GROUP_PLAYER))
            self._quickTab.AppendString(
                rid.ID_DLGMNGR_GROUP_COMMAND_API,
                "Command API",
                GetPref(rid.ID_DLGMNGR_GROUP_COMMAND_API))

            if self.GroupBegin(  # Tabs
                    0,
                    flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                    title="",
                    cols=1):
                self.GroupSpace(0, 15)

                # Add all six tabs
                self.CreateLayoutGroupConnections()
                self.CreateLayoutGroupDataSet(local=False)
                self.CreateLayoutGroupDataSet(local=True)
                self.CreateLayoutGroupControl()
                self.CreateLayoutGroupLive()
                self.CreateLayoutGroupCommandAPI()
            self.GroupEnd()  # Tabs
        self.GroupEnd()  # Dialog main group

        self.CreateLayoutAddMenu()

        # Hide _all_ tabs here. The size of the layout after CreateLayout()
        # will determine the minimum size of the dialog, when first opened.
        # It will then scale up according to its content, but it won't scale
        # down according to content (and there are no means to do so in
        # C4D's API).
        # As the dialog's supposed to start as small as possible,
        # all groups get hidden.
        #
        # TODO: Maybe this is cause of dialog initialization issues on Mac???
        #       Move to InitValues?
        self.HideElement(rid.ID_DLGMNGR_GROUP_CONNECTIONS, True)
        self.HideElement(rid.ID_DLGMNGR_GROUP_GLOBAL_DATA, True)
        self.HideElement(rid.ID_DLGMNGR_GROUP_LOCAL_DATA, True)
        self.HideElement(rid.ID_DLGMNGR_GROUP_CONTROL, True)
        self.HideElement(rid.ID_DLGMNGR_GROUP_PLAYER, True)
        self.HideElement(rid.ID_DLGMNGR_GROUP_COMMAND_API, True)
        return True

    def UpdateGroupVisibility(self, forcePlayerOpen=False):
        '''Update tab groups visibility according to tab states.'''

        # Store tab states in preferences
        SetPref(rid.ID_DLGMNGR_GROUP_CONNECTIONS,
                self._quickTab.IsSelected(rid.ID_DLGMNGR_GROUP_CONNECTIONS))
        SetPref(rid.ID_DLGMNGR_GROUP_GLOBAL_DATA,
                self._quickTab.IsSelected(rid.ID_DLGMNGR_GROUP_GLOBAL_DATA))
        SetPref(rid.ID_DLGMNGR_GROUP_LOCAL_DATA,
                self._quickTab.IsSelected(rid.ID_DLGMNGR_GROUP_LOCAL_DATA))
        SetPref(rid.ID_DLGMNGR_GROUP_CONTROL,
                self._quickTab.IsSelected(rid.ID_DLGMNGR_GROUP_CONTROL))
        if forcePlayerOpen:
            SetPref(rid.ID_DLGMNGR_GROUP_PLAYER, True)
            self._quickTab.Select(rid.ID_DLGMNGR_GROUP_PLAYER, True)
        else:
            SetPref(rid.ID_DLGMNGR_GROUP_PLAYER,
                    self._quickTab.IsSelected(rid.ID_DLGMNGR_GROUP_PLAYER))
        SetPref(rid.ID_DLGMNGR_GROUP_COMMAND_API,
                self._quickTab.IsSelected(rid.ID_DLGMNGR_GROUP_COMMAND_API))

        # Hide tab groups according to tab states
        self.HideElement(rid.ID_DLGMNGR_GROUP_CONNECTIONS,
                         not GetPref(rid.ID_DLGMNGR_GROUP_CONNECTIONS))
        self.HideElement(rid.ID_DLGMNGR_GROUP_CONNECTION_DATA,
                         not IsConnected())
        self.HideElement(rid.ID_DLGMNGR_GROUP_CONNECTION_DATA_CONTENT,
                         not IsConnected())
        self.HideElement(rid.ID_DLGMNGR_GROUP_GLOBAL_DATA,
                         not GetPref(rid.ID_DLGMNGR_GROUP_GLOBAL_DATA))
        self.HideElement(rid.ID_DLGMNGR_GROUP_LOCAL_DATA,
                         not GetPref(rid.ID_DLGMNGR_GROUP_LOCAL_DATA))
        self.HideElement(rid.ID_DLGMNGR_GROUP_CONTROL,
                         not GetPref(rid.ID_DLGMNGR_GROUP_CONTROL))
        self.HideElement(rid.ID_DLGMNGR_GROUP_PLAYER,
                         not GetPref(rid.ID_DLGMNGR_GROUP_PLAYER))
        self.HideElement(rid.ID_DLGMNGR_GROUP_COMMAND_API,
                         not GetPref(rid.ID_DLGMNGR_GROUP_COMMAND_API))

        # Announce layout change
        self.LayoutChanged(rid.ID_DLGMNGR_GROUP_MAIN)

    def EnableLiveButtons(self):
        '''En-/Disable Player buttons.'''

        # Gather some state information
        live = g_thdListener._receive
        tagsExist = self._tags is not None and len(self._tags) > 0
        allowWhileNotLive = not live and tagsExist
        isConnected = IsConnected()

        # Set label of "Start/Stop Player" button
        if live:
            self.SetString(rid.ID_DLGMNGR_PLAYER_START_STOP, "Stop Player")
        else:
            self.SetString(rid.ID_DLGMNGR_PLAYER_START_STOP, "Start Player")
        self.Enable(rid.ID_DLGMNGR_PLAYER_START_STOP, tagsExist)

        # Set label of "Start/Stop Recording..." button
        if self._buttonRecordState:
            self.SetString(rid.ID_DLGMNGR_PLAYER_SAVE, "Stop Recording...")
        else:
            self.SetString(rid.ID_DLGMNGR_PLAYER_SAVE, "Start Recording")

        # Toggle state of "Play/Pause" button
        self._bitmapButtonPlayPause.SetToggleState(g_thdListener._play)

        # Disable tag parameters of tags involved in playback
        tagsLive = g_thdListener.GetTagConsumers()
        anyLiveDataSet = False  # Is live connection involved
        if tagsExist:
            # Iterate all tags
            idConnected = GetConnectedDataSetId()
            for idxTag, tag in enumerate(self._tags):
                # Tag type combo box
                self.Enable(rid.ID_DLGMNGR_BASE_TAG_RIG_TYPES + idxTag,
                            allowWhileNotLive)

                # Tag selection Manager
                self.Enable(rid.ID_DLGMNGR_BASE_DATA_SET_ENABLED + idxTag,
                            allowWhileNotLive)

                if not tag.IsAlive():
                    continue

                # If tag is _not_ involved in playback, do not allow to switch
                # data set or actor.
                # This is not, because the user could break something,
                # but because during playback it is currently not possible
                # to add another tag to the list of involved tags.
                # If player is inactive, tagsLive is empty and all tags get
                # addressed.
                if tag not in tagsLive:
                    self.Enable(rid.ID_DLGMNGR_BASE_TAG_DATA_SETS + idxTag,
                                allowWhileNotLive)
                    self.Enable(rid.ID_DLGMNGR_BASE_TAG_ACTORS + idxTag,
                                allowWhileNotLive)

                if tag[rid.ID_TAG_DATA_SET] == idConnected and tag in tagsLive:
                    anyLiveDataSet = True

        # Connections "+" popup menu button
        # Currently not in GUI, always exactly one connection
        self.Enable(rid.ID_DLGMNGR_CONNECTION_POPUP, not live)

        # Assign unassigned tags to live connection
        self.Enable(
            rid.ID_DLGMNGR_ASSIGN_UNASSIGNED_TAGS,
            isConnected and not live and tagsExist)

        # Select buttons
        self.Enable(rid.ID_DLGMNGR_SELECT_ALL_TAGS, allowWhileNotLive)
        self.Enable(rid.ID_DLGMNGR_DESELECT_ALL_TAGS, allowWhileNotLive)
        self.Enable(rid.ID_DLGMNGR_INVERT_SELECTION, allowWhileNotLive)

        # Player widgets
        self.Enable(rid.ID_DLGMNGR_PLAYER_TAG_SELECTION, allowWhileNotLive)
        self.Enable(rid.ID_DLGMNGR_PLAYER_BUFFERING_LABEL,
                    not allowWhileNotLive)
        self.Enable(rid.ID_DLGMNGR_PLAYER_ACTIVE_TAGS_LABEL,
                    not allowWhileNotLive)
        self.Enable(rid.ID_DLGMNGR_PLAYER_SAVE,
                    live and isConnected and anyLiveDataSet)
        self.Enable(rid.ID_DLGMNGR_PLAYER_FIRST_FRAME, live)
        self.Enable(rid.ID_DLGMNGR_PLAYER_LAST_FRAME, live)
        self.Enable(rid.ID_DLGMNGR_PLAYER_PAUSE, live)
        self.Enable(rid.ID_DLGMNGR_PLAYER_CURRENT_FRAME, live)
        self.Enable(rid.ID_DLGMNGR_PLAYER_ACTIVE_TAGS, live)
        self.Enable(rid.ID_DLGMNGR_PLAYER_SYNC_WITH_LIVE,
                    live and not g_thdListener._inSync)

    def EnableDialog(self, enable):
        '''En-/Disable the entire Manager dialog.

        Happens for example, when the "Save Recording" child dialog gets
        opened.
        '''

        self.Enable(rid.ID_DLGMNGR_CONNECTIONS_IN_MENU, enable)
        self.Enable(rid.ID_DLGMNGR_GROUP_MAIN, enable)

    def InitValues(self):
        '''Called by C4D to initialize widget values.'''

        tagsLive = g_thdListener.GetTagConsumers()
        bcConnections = GetPrefsContainer(rid.ID_BC_CONNECTIONS)
        idConnected = GetConnectedDataSetId()

        # Iterate all connections
        idxConnection = 0
        for id, bcConnection in bcConnections:
            # Auto connect checkbox
            self.SetBool(
                rid.ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT + idxConnection,
                bcConnection[rid.ID_BC_DATASET_LIVE_AUTOCONNECT])

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
                self.SetString(
                    rid.ID_DLGMNGR_BASE_CONNECTION_CONNECT + idxConnection,
                    "Disconnect")
            else:
                # All disconnected data sets
                # Connect button label
                self.SetString(
                    rid.ID_DLGMNGR_BASE_CONNECTION_CONNECT + idxConnection,
                    "Connect")

            # Dis-/Connect button per connection, disabled when connecting
            self.Enable(rid.ID_DLGMNGR_BASE_CONNECTION_CONNECT + idxConnection,
                        not self._connecting)

            # Set connection status button to current status' dot image
            icon = c4d.gui.GetIcon(idIcon)
            bmpIcon = icon["bmp"].GetClonePart(
                icon["x"], icon["y"], icon["w"], icon["h"])
            self._bitmapButtonsPerConnectionStatus[idxConnection].SetImage(
                bmpIcon)

            idxConnection += 1

        # All listed tags
        if self._tags is not None and len(self._tags) > 0:
            # Iterate all tags in current document
            for idxTag, tag in enumerate(self._tags):
                if not tag.IsAlive():
                    continue

                # Combo boxes and selection state
                bcTag = tag.GetDataInstance()
                self.SetBool(rid.ID_DLGMNGR_BASE_DATA_SET_ENABLED + idxTag,
                             bcTag.GetBool(rid.ID_TAG_SELECTED_IN_MANAGER))
                self.SetInt32(rid.ID_DLGMNGR_BASE_TAG_RIG_TYPES + idxTag,
                              bcTag.GetInt32(rid.ID_TAG_RIG_TYPE))
                self.SetInt32(rid.ID_DLGMNGR_BASE_TAG_DATA_SETS + idxTag,
                              bcTag.GetInt32(rid.ID_TAG_DATA_SET))
                self.SetInt32(rid.ID_DLGMNGR_BASE_TAG_ACTORS + idxTag,
                              bcTag.GetInt32(rid.ID_TAG_ACTORS))

        # Select involved tags radio buttons
        playChoice = GetPref(rid.ID_DLGMNGR_PLAYER_TAG_SELECTION)
        if playChoice is None:
            SetPref(rid.ID_DLGMNGR_PLAYER_TAG_SELECTION, 0)
            playChoice = 0
        self.SetInt32(rid.ID_DLGMNGR_PLAYER_TAG_SELECTION, playChoice)

        # Scrub bar
        idxFrameCurrent, numFrames = g_thdListener.GetCurrentFrameNumber()
        maxSlider = (1 + numFrames // 100) * 100
        self.SetInt32(rid.ID_DLGMNGR_PLAYER_CURRENT_FRAME, idxFrameCurrent,
                      min=0, max=maxSlider, min2=0, max2=maxSlider)

        # Playback rate
        playbackRate = GetPref(rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED)
        # TODO: Cleanup pref init
        if playbackRate is None:
            SetPref(rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, 2)
            playbackRate = 2
        self.SetInt32(rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED, playbackRate)

        # Animate document checkbox
        animateDocument = GetPref(rid.ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT)
        # TODO: Cleanup pref init
        if animateDocument is None:
            SetPref(rid.ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT, False)
            animateDocument = False
        self.SetInt32(rid.ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT, animateDocument)

        # Project scale
        self.SetFloat(rid.ID_DLGMNGR_PROJECT_SCALE, GetProjectScale(),
                      step=0.1, min=0.0001)

        # Update list of involved tags ("Active Tags")
        if len(tagsLive):
            namesActiveTags = ""
            for tag in tagsLive:
                namesActiveTags += tag.GetName() + ", "
            namesActiveTags = namesActiveTags[:-2]
            self.SetString(rid.ID_DLGMNGR_PLAYER_ACTIVE_TAGS, namesActiveTags)
        else:
            self.SetString(rid.ID_DLGMNGR_PLAYER_ACTIVE_TAGS, "None")

        # Update tabs visibility
        self.UpdateGroupVisibility()

        # Update widgets in menu row
        self.UpdateLayoutInMenu()

        # Update enabling of Player buttons
        self.EnableLiveButtons()
        return True

    _lastEvent = 0

    def MessageBfmAction(self, msg):
        '''Reaction to BFM_ACTION.

        The scrub bar slider needs a little extra attention,
        because we do not only want it to set a frame index,
        but to also have the motion data visualized in view port during drag.
        '''

        # Check widget ID of BFM_ACTION. We are interested in scrub bar, only.
        if msg[c4d.BFM_ACTION_ID] != rid.ID_DLGMNGR_PLAYER_CURRENT_FRAME:
            return

        # Pause the Player
        self.CommandPause(force=True)

        # Reduce the amount of viewport updates.
        # If last event is less than 50ms back, we'll simply skip the event.
        # TODO: This has the negative side effect,
        #       releasing the scrub bar slider is a bit imprecise.
        now = c4d.GeGetTimer()
        if now - self._lastEvent <= 50:
            return

        # If user enabled "Animate Document" forward document time
        idxFrameCurrent = int(msg[c4d.BFM_ACTION_VALUE])
        if GetPref(rid.ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT):
            doc = c4d.documents.GetActiveDocument()
            tMax = doc.GetMaxTime().Get()
            # TODO: use Studio's FPS here?
            #       Which if multiple data sets with differing FPS?
            tDispatch = 0.01667 * idxFrameCurrent
            t = c4d.BaseTime(tDispatch % tMax)
            doc.SetTime(t)

        # Remove any unprocessed frames in tag's inbound queues,
        # so dispatched frame will be next to be consumed during tag's
        # Execute().
        g_thdListener.FlushTagConsumers()
        g_thdListener.DispatchFrame(idxFrameCurrent, event=False)

        # Trigger execution of scene and redraw viewport
        c4d.DrawViews(c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW | c4d.DRAWFLAGS_NO_THREAD)

        self._lastEvent = now

    def Message(self, msg, result):
        '''Called by C4D to send a message to the dialog.'''

        # Decode message (currently only interested in BFM_ACTION from
        # scrub bar)
        idMsg = msg.GetId()
        if idMsg == c4d.BFM_ACTION:
            self.MessageBfmAction(msg)

        # pass message on to parenting classes
        return c4d.gui.GeDialog.Message(self, msg, result)

    def CoreMessageUpdateTags(self):
        '''Reaction to
        PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAGS.

        Send if something significant happened in current scene.
        For example a new Rokoko tag, document changed, ...
        '''

        # Gather all Rokoko tags from current document
        self._tags = GetTagList()

        # Upate "Project Clips" library tab
        # (for example in case of document change)
        self.UpdateLayoutGroupDataSet(local=True)

        # Upate "Tags" tab (for example in case of document change)
        self.UpdateLayoutGroupControl()

        # Initialize widget values
        self.InitValues()

    def CoreMessageUpdateTagParams(self):
        '''Reaction to
        PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAG_PARAMS and
        PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_LIVE_DATA_CHANGE.

        Send if a tag's parameters changed,
        which may also happen due to content of live connection changing.
        '''

        # Upate "Tags" tab (for example in case of document change)
        self.UpdateLayoutGroupControl()

        # Initialize widget values
        self.InitValues()

    _cntBuffering = 0

    def CoreMessageBufferPulse(self):
        '''Reaction to
        PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_BUFFER_PULSE.

        Send by the listener threads every few received frames to have
        the Manager dialog show some motion (and thus indicate to user,
        it's still buffering), even if the user paused actual playback.
        '''

        # If Player is inactive, exit
        if not g_thdListener._receive:
            return

        # Advance buffering indicator sliders
        self._cntBuffering = (self._cntBuffering + 1) % 10
        self.SetInt32(rid.ID_DLGMNGR_PLAYER_BUFFERING,
                      self._cntBuffering,
                      min=0, max=9,
                      min2=0, max2=9)
        self.SetInt32(rid.ID_DLGMNGR_PLAYER_BUFFERING_IN_MENU,
                      self._cntBuffering % 5,
                      min=0, max=4,
                      min2=0, max2=4)

    def CoreMessageCurrentFrameNumber(self, msg):
        '''Reaction to PLUGIN_ID_COREMESSAGE_MANAGER_CURRENT_FRAME_NUMBER.

        During playback, player sends this event every few frames so Player
        can update scrub bar position and length.
        Note: This event gets (and has to be) muted, when the Player is paused.
              Otherwise the scrub bar would constantly update, while the user
              tries to interact with it.
        '''

        # If player is paused, do nothing
        if not g_thdListener._play:
            return

        if g_thdListener._receive:
            # Use frame index and length received from player
            idxFrameCurrent = GetCoreMessageParam(msg)
            numFrames = GetCoreMessageParam(msg, id=c4d.BFM_CORE_PAR2)
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
        self.SetInt32(rid.ID_DLGMNGR_PLAYER_CURRENT_FRAME,
                      idxFrameCurrent,
                      min=0, max=maxSlider,
                      min2=0, max2=maxSlider)

    def CoreMessageConnectionStatusChange(self):
        '''Reaction to
        PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_STATUS_CHANGE.

        Send by listener thread, whenever the status of the live connection
        changes.
        For example Studio stopped sending frames, connecting phase ended,...
        '''

        # Connecting phase ended, Connect/Disconnect" buttons can be reenabled
        self._connecting = False

        # Initialize widget values
        self.InitValues()

        # Update widgets in menu row (status dot)
        self.UpdateLayoutInMenu()

    def CoreMessagePlayerStatusChange(self):
        '''Reaction to
        PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_PLAYBACK_STATUS_CHANGE.

        Send by player upon status change (play, Pause, stop)
        '''

        # Initialize widget values
        self.InitValues()

        # Reset buffering indicator sliders
        self.SetInt32(rid.ID_DLGMNGR_PLAYER_BUFFERING,
                      0,
                      min=0, max=9,
                      min2=0, max2=9)
        self.SetInt32(rid.ID_DLGMNGR_PLAYER_BUFFERING_IN_MENU,
                      0,
                      min=0, max=4,
                      min2=0, max2=4)

    def CoreMessage(self, id, msg):
        '''C4D (or other modules of Rokoko Studio Live plugin) calls
        CoreMessage() to send an event message to the dialog.

        Using registered plugin IDs custom event messages can be send via
        SpecialEventAdd().

        In context of the main thread all kinds of events are received here.
        '''

        # Decode event message ID
        if id == rid.PLUGIN_ID_COREMESSAGE_MANAGER:
            # Decode message sub ID (first of two event parameters)
            subId = GetCoreMessageParam(msg)
            if subId == rid.CM_SUBID_MANAGER_UPDATE_TAGS:
                self.CoreMessageUpdateTags()
            elif subId == rid.CM_SUBID_MANAGER_UPDATE_TAG_PARAMS:
                self.CoreMessageUpdateTagParams()
            elif subId == rid.CM_SUBID_MANAGER_OPEN_PLAYER:
                self.UpdateGroupVisibility(forcePlayerOpen=True)
            elif subId == rid.CM_SUBID_MANAGER_PLAYBACK_STATUS_CHANGE:
                self.CoreMessagePlayerStatusChange()
            elif subId == rid.CM_SUBID_MANAGER_BUFFER_PULSE:
                self.CoreMessageBufferPulse()
            return True

        elif id == rid.PLUGIN_ID_COREMESSAGE_MANAGER_CURRENT_FRAME_NUMBER:
            self.CoreMessageCurrentFrameNumber(msg)
            return True

        elif id == rid.PLUGIN_ID_COREMESSAGE_CONNECTION:
            # Decode message sub ID (first of two event parameters)
            subId = GetCoreMessageParam(msg)
            if subId == rid.CM_SUBID_CONNECTION_STATUS_CHANGE:
                self.CoreMessageConnectionStatusChange()
            elif subId == rid.CM_SUBID_CONNECTION_LIVE_DATA_CHANGE:
                self.CoreMessageUpdateTagParams()
            return True
        return c4d.gui.GeDialog.CoreMessage(self, id, msg)

    def AskClose(self):
        '''Called by C4D when the dialog is about to be closed in whatever way.

        Returning True would deny "close request" and the dialog stayed open.
        '''

        # If "Save Recording" dialog is still open,
        # do not allow to close Manager dialog
        if self._dlgChild is not None and self._dlgChild.IsOpen():
            c4d.gui.MessageDialog(
                "Save Dialog is still open.", c4d.GEMB_ICONEXCLAMATION)
            return True  # Dialog will NOT be closed

        # If Player is active, ask user what to do
        if g_thdListener._receive:
            result = c4d.gui.MessageDialog(
                ("Player is still running.\nDialog will be closed.\n"
                 "Stop player?\n"),
                c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_YESNOCANCEL)
            if result == c4d.GEMB_R_YES:
                # User wants to stop player
                self.CommandPlayerExit()
            elif result == c4d.GEMB_R_CANCEL:
                # User decided to keep Manager dialog open
                return True  # Dialog will NOT be closed

        # Close manager dialog
        return False

    def CommandConnectionsPopup(self):
        '''User pressed "+" button on "Connection" tab.

        Open dialog to create a new connection data set (see
        rokoko_dialog_edit_connection) and stores resulting connection
        in preferences.
        '''

        # Open "Edit Connection..." dialog (dialog will create default
        # connection data set itself)
        dlgEdit = DialogEditConnection(None)
        resultOpen = dlgEdit.Open(c4d.DLG_TYPE_MODAL_RESIZEABLE)
        if resultOpen is False:
            return # failed to open dialog
        result, bcConnectionNew = dlgEdit.GetResult()
        if result is False:
            return  # user cancelled dialog

        # Store new connection in preferences
        GetPrefsContainer(rid.ID_BC_CONNECTIONS).SetContainer(
            bcConnectionNew.GetId(),
            bcConnectionNew.GetClone(c4d.COPYFLAGS_NONE))

        # Update "Connections" tab
        self.UpdateLayoutGroupConnections()

        # Initialize widget values
        self.InitValues()

        # Update widgets in menu row (connection combo box)
        self.UpdateLayoutInMenu()

    def CommandConnectionPopup(self, id):
        '''User pressed "..." button on a single connection in
        "Connection" tab.
        '''

        # Get connection data set belonging to the button
        idxConnection = id - rid.ID_DLGMNGR_BASE_CONNECTION_POPUP
        bcConnections = GetPrefsContainer(rid.ID_BC_CONNECTIONS)
        # idxConnected = bcConnections.FindIndex(GetConnectedDataSetId())

        # Create popup menu
        bcMenu = c4d.BaseContainer()
        idConnected = GetConnectedDataSetId()
        idConnection = bcConnections.GetIndexId(idxConnection)

        # Order of options depends a bit on connection state
        if idConnected == idConnection:
            bcMenu.InsData(
                rid.ID_SUBMENU_CONNECTION_CREATE_SCENE, "Create Scene")
            bcMenu.InsData(0, "")
            bcMenu.InsData(rid.ID_SUBMENU_CONNECTION_EDIT, "Edit...&d&")
            # currently always exactly one connection, can not be removed
            # bcMenu.InsData(rid.ID_SUBMENU_CONNECTION_REMOVE, 'Remove&d&')
            bcMenu.InsData(0, "")
            bcMenu.InsData(rid.ID_SUBMENU_CONNECTION_CONNECT, "Disonnect")
        else:
            bcMenu.InsData(rid.ID_SUBMENU_CONNECTION_CONNECT, "Connect")
            bcMenu.InsData(0, "")
            bcMenu.InsData(
                rid.ID_SUBMENU_CONNECTION_CREATE_SCENE, "Create Scene&d&")
            bcMenu.InsData(0, "")
            bcMenu.InsData(rid.ID_SUBMENU_CONNECTION_EDIT, "Edit...")
            # currently always exactly one connection, can not be removed
            # bcMenu.InsData(rid.ID_SUBMENU_CONNECTION_REMOVE, "Remove")

        # Show popup menu
        result = c4d.gui.ShowPopupDialog(
            cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)

        # Decode menu entry clicked on
        if result == rid.ID_SUBMENU_CONNECTION_CONNECT:
            self.Connect(idxConnection)
        elif result == rid.ID_SUBMENU_CONNECTION_EDIT:
            self.EditConnection(idxConnection)
        elif result == rid.ID_SUBMENU_CONNECTION_REMOVE:
            self.RemoveConnectionDataSet(idxConnection)
        elif result == rid.ID_SUBMENU_CONNECTION_CREATE_SCENE:
            self.InsertRokokoStudioScene()
        elif result == 0:
            pass  # menu canceled
        else:
            print("ERROR: Submenu Connection unknown command", result)

    def Connect(self, idxConnection):
        '''Connect a connection data set
        (referenced by index of connection in dialog).

        The listener thread will be started.
        '''

        # Disable all connection button until connection is established
        self._connecting = True

        # If player is active, stop it
        if g_thdListener._receive:
            self.CommandPlayerExit()

        if idxConnection != 999999:
            # Get ID of connection data set for given index
            bcConnections = GetPrefsContainer(rid.ID_BC_CONNECTIONS)
            idConnection = bcConnections.GetIndexId(idxConnection)
        else:
            # Disconnect request
            idConnection = -1

        idConnected = GetConnectedDataSetId()

        # Connect/Disconnect is a toggle button
        # If it's pressed on a currently connected connection,
        # it's a disconnect
        if idConnected == idConnection:
            idConnected = -1
        else:
            # If already connected and connect request is for another
            # connection data set, disconnect the old connection first.
            if idConnected != -1 and idConnection != -1:
                c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_CONNECTION,
                                    rid.CM_SUBID_CONNECTION_DISCONNECT)
            idConnected = idConnection

        if idConnected == -1:
            # Disconnect request
            # Exit the player
            self.CommandPlayerExit()

            # Ask listener thread to disconnect
            c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_CONNECTION,
                                rid.CM_SUBID_CONNECTION_DISCONNECT)
        else:
            # Connect request
            # Ask listener thread to disconnect
            c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_CONNECTION,
                                rid.CM_SUBID_CONNECTION_CONNECT, idConnected)

        # Initialize widget values
        self.InitValues()

        # Update widgets in menu row (status dot and connection combo box)
        self.UpdateLayoutInMenu()

        # Update player interface
        self.EnableLiveButtons()

    def RemoveConnectionDataSet(self, idxConnection):
        '''Remove a connection data set
        (referenced by index of connection in dialog) from preferences.

        Currently this is not used, as there is always exactly one connection.
        '''

        # Get ID of connection data set for given index
        id = GetPrefsContainer(rid.ID_BC_CONNECTIONS).GetIndexId(idxConnection)

        # Remove connection data set from preferences
        RemoveConnection(id)

        # Update connection library in "Connections" tab
        self.UpdateLayoutGroupConnections()

        # Initialize widget values
        self.InitValues()

        # Update widgets in menu row (status dot and connection combo box)
        self.UpdateLayoutInMenu()

    def EditConnection(self, idxConnection):
        '''Open a dialog to edit the parameters of a connection data set.'''

        # Get connection data set for given index
        id = GetPrefsContainer(rid.ID_BC_CONNECTIONS).GetIndexId(idxConnection)
        bcConnection = GetPrefsContainer(
            rid.ID_BC_CONNECTIONS).GetContainer(id)
        idConnection = bcConnection.GetId()

        # Open "Edit Connection..." dialog
        dlgEdit = DialogEditConnection(bcConnection)
        resultOpen = dlgEdit.Open(c4d.DLG_TYPE_MODAL_RESIZEABLE)
        if resultOpen is False:
            return  # failed to open dialog
        result, bcConnectionNew = dlgEdit.GetResult()
        if result is False:
            return  # user cancelled dialog

        # Remove previous connection data set from preferences
        RemoveConnection(idConnection)

        # Sttore edited connection data set in preferences
        GetPrefsContainer(
            rid.ID_BC_CONNECTIONS).SetContainer(bcConnectionNew.GetId(),
                                                bcConnectionNew)

        # Update connection library in "Connections" tab
        self.UpdateLayoutGroupConnections()

        # Initialize widget values
        self.InitValues()

        # Update widgets in menu row (status dot and connection combo box)
        self.UpdateLayoutInMenu()

    def CommandDataPopup(self, local):
        '''User pressed "+" button on global or project clip library tab.'''

        # If player is active, certain menu options get disabled
        disableItem = ""
        if g_thdListener._receive:
            disableItem = "&d&"

        # Create pop up menu
        bcMenu = c4d.BaseContainer()
        bcMenu.InsData(rid.ID_SUBMENU_DATA_ADD_FILE, "Add File...")
        bcMenu.InsData(rid.ID_SUBMENU_DATA_ADD_FOLDER, "Add Folder...")
        bcMenu.InsData(0, "")
        bcMenu.InsData(rid.ID_SUBMENU_DATA_REMOVE_ALL,
                       "Remove All" + disableItem)
        bcMenu.InsData(rid.ID_SUBMENU_DATA_DELETE_ALL,
                       "Delete All..." + disableItem)

        # Show popup menu
        result = c4d.gui.ShowPopupDialog(
            cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)

        # Decode menu entry clicked on
        if result == rid.ID_SUBMENU_DATA_ADD_FILE:
            self.AddDataSet(local=local, folder=False)
        elif result == rid.ID_SUBMENU_DATA_ADD_FOLDER:
            self.AddDataSet(local=local, folder=True)
        elif result == rid.ID_SUBMENU_DATA_REMOVE_ALL:
            self.RemoveDataSet(local=local, all=True)
        elif result == rid.ID_SUBMENU_DATA_DELETE_ALL:
            self.RemoveDataSet(local=local, all=True, delete=True)
        elif result == 0:
            pass  # menu canceled
        else:
            print('ERROR: Submenu Data unknown command:', result, local)

    def CommandDataSetPopup(self, id, local):
        '''User pressed "..." button on a single data set (clip) in global or
        project library tab.
        '''

        # Get actual data set index and label for copy and move menu entries
        if local:
            idxDataSet = id - rid.ID_DLGMNGR_BASE_LOCAL_DATA_POPUP
            nameTargetLib = "Global"
        else:
            idxDataSet = id - rid.ID_DLGMNGR_BASE_GLOBAL_DATA_POPUP
            nameTargetLib = "Project"

        # If player is active, certain menu options get disabled
        disableItem = ""
        if g_thdListener._receive:
            disableItem = "&d&"

        # Create pop up menu
        bcMenu = c4d.BaseContainer()
        bcMenu.InsData(rid.ID_SUBMENU_DATA_SET_CREATE_SCENE, "Create Scene")
        bcMenu.InsData(0, "")
        bcMenu.InsData(rid.ID_SUBMENU_DATA_SET_EDIT, f"Edit...{disableItem}")
        bcMenu.InsData(rid.ID_SUBMENU_DATA_SET_OPEN_DIRECTORY,
                       "Open Directory...")
        bcMenu.InsData(0, "")
        bcMenu.InsData(rid.ID_SUBMENU_DATA_SET_COPY_LOCAL,
                       f"Copy to {nameTargetLib} Clips")
        bcMenu.InsData(rid.ID_SUBMENU_DATA_SET_MOVE_LOCAL,
                       f"Move to {nameTargetLib} Clips{disableItem}")
        bcMenu.InsData(0, "")
        bcMenu.InsData(rid.ID_SUBMENU_DATA_SET_REMOVE, f"Remove{disableItem}")
        bcMenu.InsData(rid.ID_SUBMENU_DATA_SET_DELETE,
                       f"Delete...{disableItem}")

        # Show popup menu
        result = c4d.gui.ShowPopupDialog(
            cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)

        # Decode menu entry clicked on
        if result == rid.ID_SUBMENU_DATA_SET_COPY_LOCAL:
            self.DataSetChangeGlobalLocal(idxDataSet, local=local)
        elif result == rid.ID_SUBMENU_DATA_SET_MOVE_LOCAL:
            self.DataSetChangeGlobalLocal(idxDataSet, local=local, move=True)
        elif result == rid.ID_SUBMENU_DATA_SET_EDIT:
            self.EditDataSet(idxDataSet, local=local)
        elif result == rid.ID_SUBMENU_DATA_SET_REMOVE:
            self.RemoveDataSet(local=local, idx=idxDataSet)
        elif result == rid.ID_SUBMENU_DATA_SET_DELETE:
            self.RemoveDataSet(local=local, idx=idxDataSet, delete=True)
        elif result == rid.ID_SUBMENU_DATA_SET_CREATE_SCENE:
            self.CreateSceneForDataSet(idxDataSet, local=local)
        elif result == rid.ID_SUBMENU_DATA_SET_OPEN_DIRECTORY:
            self.DataSetOpenDirectory(local=local, idxDataSet=idxDataSet)
        elif result == 0:
            pass  # menu canceled
        else:
            print("ERROR: Submenu Data Set unknown command:", local, result)

    def GetDataSetByDialogIndex(self, local, idxDataSet):
        '''In Manager dialog all (active) widgets belonging to a single data
        set have an ID as sum of a base ID and data sets index in the dialog
        (which happens to be the index of the data set in its library's
        BaseContainer).

        This function returns a data set container for this index.
        '''

        # Get data set for given index in dialog from specified library
        if local:
            bcDataSets = GetLocalDataSets()
        else:
            bcDataSets = GetPrefsContainer(rid.ID_BC_DATA_SETS)
        idDataSet = bcDataSets.GetIndexId(idxDataSet)
        bcDataSet = bcDataSets.GetContainer(idDataSet)
        return bcDataSet

    def DataSetChangeGlobalLocal(self, idxDataSet, local, move=False):
        '''Copy (or move) a data set (referenced by dialog index)
        from global to project's clip library (or vice versa).
        '''

        # Get data set for given index in dialog from library it's currently in
        bcDataSet = self.GetDataSetByDialogIndex(local, idxDataSet)

        # Copy (or move) data set into the other library
        self.DataSetChangeGlobalLocalBC(bcDataSet, move=move)

    def DataSetChangeGlobalLocalBC(self, bcDataSet, move=False):
        '''Copy (or move) a data set container from global to project's
        clip library (or vice versa).
        '''

        isLocal = bcDataSet[rid.ID_BC_DATASET_IS_LOCAL]
        filename = bcDataSet[rid.ID_BC_DATASET_FILENAME]
        idDataSet = bcDataSet.GetId()

        bcDataSetNew = bcDataSet.GetClone(c4d.COPYFLAGS_NONE)
        isLocalNew = not isLocal
        filenameNew = filename

        pathDoc = c4d.documents.GetActiveDocument().GetDocumentPath()

        if isLocalNew:
            # Direction Global -> Project, old filename is absolute
            # new complete destination file path for fileaction
            filenameDst = filename
            # new destination path possibly relative to project folder stored
            # in data set
            filenameNew = filename

            # Assume, user will want the file copied/moved,
            # create destination path
            if pathDoc is not None and len(pathDoc) > 1:
                _, filenameDst = os.path.split(filename)
                filenameNew = os.path.join(".", filenameDst)
                filenameDst = os.path.join(pathDoc, filenameDst)

            # If motion data file not already in project folder
            if filenameDst != filename:
                # Offer to copy or move the motion data file

                # Create dialog message
                if move:
                    msg = "Move data set file to project folder?\n"
                    msg += f"From: {filename}\n"
                    msg += f"To: {filenameDst}\n"
                    msg += "Yes: Move file\n"
                    msg += "No: Move data set reference, only\n"
                    msg += "Cancel: Abort"
                else:
                    msg = "Copy data set file to project folder?\n"
                    msg += f"From: {filename}\n"
                    msg += f"To: {filenameDst}\n"
                    msg += "Yes: Copy file\n"
                    msg += "No: Copy data set reference, only\n"
                    msg += "Cancel: Abort"

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
                    # revert above assumption and use the previously set path
                    filenameNew = filename

                elif result == c4d.GEMB_R_CANCEL:
                    # user cancelled the dialog, don't do anything
                    return
        else:
            # Direction Project -> Global, old filename may be project relative
            # Resolve project relative path
            if pathDoc is not None and \
               len(pathDoc) > 1 and \
               filename[0] == "." or \
               os.sep not in filename:
                filenameNew = filename
                if filenameNew[0] == ".":
                    filenameNew = filenameNew[2:]
                filenameNew = filenameNew.replace("\\", os.sep)
                filenameNew = os.path.join(pathDoc, filenameNew)

        # Optionally remove the source data set (Move instead of Copy)
        if move:
            RemoveDataSetBC(bcDataSet)

        # Store new file reference and global/local marker in data set
        bcDataSetNew[rid.ID_BC_DATASET_FILENAME] = filenameNew
        bcDataSetNew[rid.ID_BC_DATASET_IS_LOCAL] = isLocalNew

        # Update data set ID
        sDataSet = bcDataSetNew[rid.ID_BC_DATASET_NAME]
        sDataSet += bcDataSetNew[rid.ID_BC_DATASET_FILENAME]
        sDataSet += str(bcDataSetNew[rid.ID_BC_DATASET_IS_LOCAL])
        bcDataSetNew.SetId(MyHash(sDataSet))

        # Add data set to other library
        AddDataSetBC(bcDataSetNew)

        # Iterate all tags in current scene
        for tag in self._tags:
            # Announce change in library to tags
            # (they need to rebuild their combo box content)
            tag.Message(c4d.MSG_MENUPREPARE)

            # If tag used the old data set, use new data set (if moving)
            if move and tag[rid.ID_TAG_DATA_SET] == idDataSet:
                tag[rid.ID_TAG_DATA_SET] = bcDataSetNew.GetId()

        # Update both clip library tabs
        self.UpdateLayoutGroupDataSet(local=True)
        self.UpdateLayoutGroupDataSet(local=False)
        c4d.EventAdd()

    def DataSetOpenDirectory(self, local, idxDataSet):
        '''Open the directory containing the motion data file referenced in
        a data set (clip).
        '''

        # Get data set for given index in dialog from library it's currently in
        bcDataSet = self.GetDataSetByDialogIndex(local, idxDataSet)

        # Resolve project relative path
        filename = bcDataSet[rid.ID_BC_DATASET_FILENAME]
        if bcDataSet[rid.ID_BC_DATASET_IS_LOCAL]:
            pathDoc = c4d.documents.GetActiveDocument().GetDocumentPath()
            if pathDoc is not None and \
               len(pathDoc) > 1 and \
               filename[0] == "." or \
               os.sep not in filename:
                if filename[0] == ".":
                    filename = filename[2:]
                filename = filename.replace("\\", os.sep)
                filename = os.path.join(pathDoc, filename)

        # Open path in Explorer/Finder
        path, _ = os.path.split(filename)
        c4d.storage.GeExecuteFile(path)

    def AnalyzeFile(self, filename, local, nameDataSet=None):
        '''Analyzes a motion data file and returns a new data set container,
        properly referencing the file and meta data set.

        Returns None on error.
        Note: File gets loaded, decompressed and decoded.
              So depending on file size, this can take a second or two.
        '''

        # Check file existence
        if not os.path.exists(filename):
            print(f"ERROR: Clip not found: {filename}")
            return None

        # Read LZ4 compressed data from file
        dataLZ4 = None
        with open(filename, mode="rb") as f:
            dataLZ4 = f.read()
            f.close()
        if dataLZ4 is None:
            return None

        # Decompress data
        if __USE_LZ4__:
            dataStudio = lz4f.decompress(
                dataLZ4,
                return_bytearray=True, return_bytes_read=False)
        else:
            dataStudio = dataLZ4

        # Decode JSON into dictionary
        data = json.loads(dataStudio)

        # If no data set name provided, create one from file name
        if nameDataSet is None:
            nameDataSet = filename[filename.rfind(os.sep) + 1:]
            if nameDataSet[-4:] == ".rec":
                nameDataSet = nameDataSet[:-4]

        # For local clips in project folder, the filename in data set is
        # relative to project folder
        pathDocument = c4d.documents.GetActiveDocument().GetDocumentPath()
        if local and pathDocument is not None and len(pathDocument) > 1:
            filename = filename.replace(pathDocument, ".")

        # Create a new data set
        bcDataSet = BaseContainerDataSet(nameDataSet, filename, isLocal=local)

        # Analyze first frame of motion data and store meta data in data set.
        StoreAvailableEntitiesInDataSet(data[0]["scene"], bcDataSet)

        return bcDataSet

    def AnalyzeDataSet(self, bcDataSet):
        '''Analyzes a motion data file referenced in a given clip data set and
        returns a new data set container containing correct meta data.

        Returns None on error.
        '''

        return self.AnalyzeFile(bcDataSet[rid.ID_BC_DATASET_FILENAME],
                                bcDataSet[rid.ID_BC_DATASET_IS_LOCAL],
                                bcDataSet[rid.ID_BC_DATASET_NAME])

    def AddDataSet(self, local, folder=False):
        '''Add a new clip data set to either global or project clip library.

        Optionally all clips found in a folder.
        '''

        filenames = []  # list of filenames to be added as clips
        pathDocument = c4d.documents.GetActiveDocument().GetDocumentPath()
        if folder:
            # Ask user to choose a folder
            pathFolder = c4d.storage.LoadDialog(
                type=c4d.FILESELECTTYPE_ANYTHING,
                title="Load All Clips From Folder...",
                flags=c4d.FILESELECT_DIRECTORY,
                force_suffix="rec",
                def_path=pathDocument, def_file="")
            if pathFolder is None or len(pathFolder) < 2:
                return True  # file dialog cancelled

            # Browse folder
            for filename in os.listdir(pathFolder):
                if filename[-4:] != ".rec":
                    continue
                # File found
                filenames.append(os.path.join(pathFolder, filename))
        else:
            # Ask user to choose a file
            filename = c4d.storage.LoadDialog(
                type=c4d.FILESELECTTYPE_ANYTHING,
                title="Load Clip From File...",
                force_suffix="rec",
                def_path=pathDocument, def_file="")
            if filename is None or len(filename) < 2:
                return True  # file dialog cancelled
            # File found
            filenames.append(filename)

        # Iterate all files found
        for idxFilename, filename in enumerate(filenames):
            # Get a new data set container for the given file
            bcDataSet = self.AnalyzeFile(filename, local)
            if bcDataSet is None:
                print(f"ERROR: Add data set: File not found: {filename}")
                continue

            # Store clip data set in respective library
            AddDataSetBC(bcDataSet)

        # Announce clip library change to tags (to update combo boxes)
        for tag in self._tags:
            tag.Message(c4d.MSG_MENUPREPARE)

        # Update respective library group
        self.UpdateLayoutGroupDataSet(local)
        c4d.EventAdd()

    def EditDataSet(self, idxDataSet, local):
        '''Opens a dialog to edit parameters of a clip data set in
        specified library.
        '''

        # Get data set for given index in dialog from library it's currently in
        bcDataSet = self.GetDataSetByDialogIndex(local, idxDataSet)
        idDataSet = bcDataSet.GetId()

        # Open "Edit Data Set..." dialog
        dlgEdit = DialogEditDataSet(bcDataSet, local)
        resultOpen = dlgEdit.Open(c4d.DLG_TYPE_MODAL_RESIZEABLE)
        if resultOpen is False:
            return  # failed to open dialog
        result, bcDataSetNew = dlgEdit.GetResult()
        if result is False:
            return  # dialog cancelled by user

        # Analyze the changed data set (user may have change the
        # referenced file, for example)

        # filename really only for error requester
        filename = bcDataSetNew[rid.ID_BC_DATASET_FILENAME]
        bcDataSetNew = self.AnalyzeDataSet(bcDataSetNew)
        if bcDataSetNew is None:
            c4d.gui.MessageDialog(
                f"Failed to open motion data file: {filename}.",
                c4d.GEMB_ICONEXCLAMATION)
            return

        # Remove the old and store changed data set in respective library
        # This is needed as the changed parameters may have caused a change
        # of the data set ID
        RemoveDataSetBC(bcDataSet)
        AddDataSetBC(bcDataSetNew)

        # Iterate all Rokoko tags in current document
        for tag in self._tags:
            # Announce change in library to tags (they need to rebuild their
            # combo box content)
            tag.Message(c4d.MSG_MENUPREPARE)

            # If tag used the old data set, use changed data set's ID
            if tag[rid.ID_TAG_DATA_SET] == idDataSet:
                tag[rid.ID_TAG_DATA_SET] = bcDataSetNew.GetId()

        # Update respective library group
        self.UpdateLayoutGroupDataSet(local)
        c4d.EventAdd()

    def CreateSceneForDataSet(self, idxDataSet, local):
        '''Creates and inserts a scene from a dataset.'''

        # Get data set for given index in dialog from library it's currently in
        bcDataSet = self.GetDataSetByDialogIndex(local, idxDataSet)

        # Merge all actors and props needed for this data set into the
        # current document
        self.InsertDataSetScene(bcDataSet)

    def RemoveDataSet(self, local, idx=-1, all=False, delete=False):
        '''Remove a clip data set from specified library.

        Optionally removes all clips from specified library.
        Optionally deletes referenced motion data files.
        '''

        if local:
            bcDataSets = GetLocalDataSets()
        else:
            bcDataSets = GetPrefsContainer(rid.ID_BC_DATA_SETS)

        # a list of filenames (for actual deletion of files at the end)
        filenamesDelete = []

        # Optionally delete the motion clip file(s)
        # Only collect filenames here, actual delete opration is at the enmd
        if delete:
            # Collect either all or just a single data set's filename
            if all:
                for idDataSet, bcDataSet in bcDataSets:
                    filenamesDelete.append(
                        bcDataSet[rid.ID_BC_DATASET_FILENAME])
            else:
                idDataSet = bcDataSets.GetIndexId(idx)
                bcDataSet = bcDataSets[idDataSet]
                filenamesDelete.append(bcDataSet[rid.ID_BC_DATASET_FILENAME])

            # Resolve project relative filenames
            pathDoc = c4d.documents.GetActiveDocument().GetDocumentPath()
            for idxFilename, filename in enumerate(filenamesDelete):
                if pathDoc is not None and \
                   len(pathDoc) > 1 and \
                   filename[0] == "." or \
                   os.sep not in filename:
                    if filename[0] == ".":
                        filename = filename[2:]
                    filename = filename.replace("\\", os.sep)
                    filenamesDelete[idxFilename] = os.path.join(pathDoc,
                                                                filename)

            # Create safety question
            message = ("Are you sure you want to delete the following "
                       "data set(s)?\n")
            for filename in filenamesDelete:
                message += filename + "\n"
            if len(filenamesDelete) <= 0:
                # Something is strange. Nevertheless allow user to continue,
                # so a stale data set still gets removed
                # (even if there is no file to delete).
                message += "No files to delete???\n"
            message += ("Yes: Delete file(s)\n"
                        "No: Remove data set reference, only\n"
                        "Cancel: Abort")

            # Ask user, if sure?
            result = c4d.gui.MessageDialog(
                message, c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_YESNOCANCEL)

            # Decode user's choice
            if result == c4d.GEMB_R_NO:
                filenamesDelete = []  # flush list, no files will be deleted
            elif result == c4d.GEMB_R_CANCEL:
                return  # user aborted the operation

        # Throw data set container(s) away
        if all:
            bcDataSets.FlushAll()
        else:
            idDataSet = bcDataSets.GetIndexId(idx)
            bcDataSet = bcDataSets.GetContainer(idDataSet)
            RemoveDataSetBC(bcDataSet)

        # Announce change in library to tags (they need to rebuild their
        # combo box content)
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

    def CommandTagsPopup(self):
        '''User pressed "+" button on "Tags" tab
        (create scene or create characters and such).
        '''

        # If not connected, some options get disabled
        disableItem = ""
        if not IsConnected():
            disableItem = "&d&"

        # Create menu BaseContainer
        bcMenu = c4d.BaseContainer()
        bcMenu.InsData(rid.ID_SUBMENU_TAGS_CREATE_STUDIO_LIVE_SCENE,
                       f"Create Connected Studio Scene{disableItem}")
        bcMenu.InsData(0, "")  # separator
        bcMenu.InsData(rid.ID_SUBMENU_TAGS_CREATE_CHARACTER_NEWTON,
                       "Create Rokoko Newton Character")
        bcMenu.InsData(rid.ID_SUBMENU_TAGS_CREATE_BONES_NEWTON,
                       "Create Rokoko Newton Bones")
        bcMenu.InsData(rid.ID_SUBMENU_TAGS_CREATE_CHARACTER_NEWTON_WITH_FACE,
                       "Create Rokoko Newton Character with Face")
        bcMenu.InsData(rid.ID_SUBMENU_TAGS_CREATE_FACE_NEWTON,
                       "Create Rokoko Newton Face")
        bcMenu.InsData(0, "")  # separator
        bcMenu.InsData(rid.ID_SUBMENU_TAGS_CREATE_LIGHT,
                       "Create Light")
        bcMenu.InsData(rid.ID_SUBMENU_TAGS_CREATE_CAMERA,
                       "Create Camera")
        bcMenu.InsData(rid.ID_SUBMENU_TAGS_CREATE_PROP,
                       "Create Prop")

        # Show popup menu
        result = c4d.gui.ShowPopupDialog(
            cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)

        # Decode user's selection
        if result == rid.ID_SUBMENU_TAGS_CREATE_STUDIO_LIVE_SCENE:
            self.InsertRokokoStudioScene()
        elif result == rid.ID_SUBMENU_TAGS_CREATE_CHARACTER_NEWTON:
            self.InsertRokokoCharacter(result)
        elif result == rid.ID_SUBMENU_TAGS_CREATE_CHARACTER_NEWTON_WITH_FACE:
            self.InsertRokokoCharacterWithFace(result)
        elif result == rid.ID_SUBMENU_TAGS_CREATE_BONES_NEWTON:
            self.InsertRokokoCharacter(result, bonesOnly=True)
        elif result == rid.ID_SUBMENU_TAGS_CREATE_FACE_NEWTON:
            self.InsertRokokoFace(result)
        elif result == rid.ID_SUBMENU_TAGS_CREATE_LIGHT:
            self.InsertRokokoLight()
        elif result == rid.ID_SUBMENU_TAGS_CREATE_CAMERA:
            self.InsertRokokoCamera()
        elif result == rid.ID_SUBMENU_TAGS_CREATE_PROP:
            self.InsertRokokoProp()
        elif result == 0:
            pass # menu canceled
        else:
            print("ERROR: Submenu Tags unknown command", result)

    def InsertDataSetScene(self, bcDataSet):
        '''Inserts all rigs and props needed for a given data set
        (regardless if live connection or clip)

        Note: Creates an undo.
        '''

        docCurrent = c4d.documents.GetActiveDocument()

        # Included default character files in plugin's resources
        pathBase = os.path.join(os.path.dirname(__file__), "res")
        filenameNewtonWithFace = os.path.join(
            pathBase,
            "tpose_rokoko_newton_with_face.c4d")
        filenameNewton = os.path.join(
            pathBase, "tpose_rokoko_newton_meshed.c4d")
        filenameNewtonFace = os.path.join(
            pathBase, "rokoko_newton_face.c4d")

        # default character scenes will be loaded only once during this
        # operation
        docsSrc = [None, None, None]
        objLast = None
        matLast = None

        # Create a new undo step
        docCurrent.StartUndo()

        # Actors
        # For all actors contained in referenced motion data
        bcActors = bcDataSet.GetContainerInstance(rid.ID_BC_DATASET_ACTORS)
        for idxActor, _ in bcActors:
            # Get actor entity and its meta data
            bcActor = bcActors.GetContainerInstance(idxActor)
            hasSuit = bcActor[rid.ID_BC_ENTITY_HAS_SUIT]
            hasFace = bcActor[rid.ID_BC_ENTITY_HAS_FACE]
            name = bcActor[rid.ID_BC_ENTITY_NAME]
            color = bcActor[rid.ID_BC_ENTITY_COLOR]

            # Get default character scene (load the scene if not done so
            # already for a previous actor)
            docSrc = None
            if hasSuit and hasFace:
                if docsSrc[0] is None:
                    docsSrc[0] = c4d.documents.LoadDocument(
                        filenameNewtonWithFace,
                        c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS,
                        None)
                docSrc = docsSrc[0]
            elif hasSuit:
                if docsSrc[1] is None:
                    docsSrc[1] = c4d.documents.LoadDocument(
                        filenameNewton,
                        c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS,
                        None)
                docSrc = docsSrc[1]
            else:
                if docsSrc[2] is None:
                    docsSrc[2] = c4d.documents.LoadDocument(
                        filenameNewtonFace,
                        c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS,
                        None)
                docSrc = docsSrc[2]
            if docSrc is None:
                print("ERROR: Source scene missing", hasSuit, hasFace)
                continue

            # The root object of the rig is always the first in all
            # default scenes.
            # NOTE: Take care of this when creating changing default scenes.
            objRootSrc = docSrc.GetFirstObject()
            if objRootSrc is None:
                print("ERROR: No Newton Rig.")
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
            # the created clones of the materials afterwards and not the
            # original materials of the default scene.
            #
            # The AliasTrans is simply passed to all cloning operations and
            # it will collect a list of BaseLinks of all entities involved
            # in the cloning.
            # Then when all cloning is finished, AliasTrans.Translate() gets
            # called, to replace all references to source objects with their
            # cloned counterparts within all involved entities (this includes
            # children or branches like tags).
            trans = c4d.AliasTrans()
            if not trans or not trans.Init(docSrc):
                print("ERROR: No AliasTrans.")
                continue

            # Clone the character rig from default scene
            objRootNew = objRootSrc.GetClone(c4d.COPYFLAGS_NONE, trans)
            if objRootNew is None:
                print("ERROR: Failed to clone rig.")
                continue

            # Clone all materials from default scene
            materials = []  # list of material clones
            while matSrc is not None:
                mat = matSrc.GetClone(c4d.COPYFLAGS_NONE, trans)
                if mat is not None:
                    materials.append(mat)
                matSrc = matSrc.GetNext()

            # Correct link dependencies
            trans.Translate(True)

            # Rename root object and Rokoko tag of the resulting rig with
            # actor name.
            tag = objRootNew.GetTag(type=rid.PLUGIN_ID_TAG)
            if tag is None:
                print("ERROR: Lacking Rokoko Tag.")
                continue
            objRootNew.SetName(name)
            tag.SetName(f"Rokoko Tag {name}")

            # Insert new character into current document
            # (and register insertion in the undo step)
            docCurrent.InsertObject(objRootNew, pred=objLast)
            docCurrent.AddUndo(c4d.UNDOTYPE_NEW, objRootNew)
            # remember last object inserted, in order to keep original
            # insertion order
            objLast = objRootNew

            if len(materials) > 0:
                # Change color channel color to actor color
                materials[0][c4d.MATERIAL_COLOR_COLOR] = color

            # Insert all materials into current document
            for mat in materials:
                docCurrent.InsertMaterial(mat, pred=matLast)
                docCurrent.AddUndo(c4d.UNDOTYPE_NEW, mat)
                matLast = mat

            # TODO: In case of a character rig with face we probably should
            #       update all tags, shouldn't we?

            # Enforce initialization of Rokoko tag
            tag.Message(c4d.MSG_MENUPREPARE)

            # Set tag to use this data set and actor
            tag[rid.ID_TAG_DATA_SET] = bcDataSet.GetId()
            # tag[rid.ID_TAG_ACTORS] = idxActor # TODO: strange!!!
            tag.GetDataInstance().SetInt32(rid.ID_TAG_ACTORS, idxActor)
            tag[rid.ID_TAG_ACTOR_INDEX] = idxActor

        # Props
        # For all props contained in referenced motion data
        bcProps = bcDataSet.GetContainerInstance(rid.ID_BC_DATASET_PROPS)
        for idxProp, _ in bcProps:
            # Get prop entity and its meta data
            bcProp = bcProps.GetContainerInstance(idxProp)
            name = bcProp[rid.ID_BC_ENTITY_NAME]
            color = bcProp[rid.ID_BC_ENTITY_COLOR]

            # Create a new Null object representing the prop
            objProp = c4d.BaseObject(c4d.Onull)

            # Configure the Null object
            objProp.SetName(name)
            objProp[c4d.NULLOBJECT_DISPLAY] = 12  # 12: pyramid
            objProp[c4d.ID_BASEOBJECT_COLOR] = color
            objProp[c4d.ID_BASEOBJECT_USECOLOR] = 2

            # Create Rokoko tag on prop object
            tag = objProp.MakeTag(rid.PLUGIN_ID_TAG)

            # Rename tag
            tag.SetName(f"Rokoko Tag {name}")

            # Insert prop object into the current document
            docCurrent.InsertObject(objProp, pred=objLast)
            docCurrent.AddUndo(c4d.UNDOTYPE_NEW, objProp)
            # remember last object inserted, in order to keep original
            # insertion order
            objLast = objProp

            # Enforce initialization of tag (as if the user created it)
            tag.Message(c4d.MSG_MENUPREPARE)

            # Set tag to use this data set and prop
            # tag[rid.ID_TAG_DATA_SET] = bcDataSet.GetId() # TODO: strange!!!
            tag.GetDataInstance().SetInt32(
                rid.ID_TAG_DATA_SET, bcDataSet.GetId())
            tag.GetDataInstance().SetInt32(rid.ID_TAG_ACTORS, idxProp)
            tag[rid.ID_TAG_ACTOR_INDEX] = idxProp

        # Finish undo step
        docCurrent.EndUndo()

        # Let C4D know, we have changed the scene
        c4d.EventAdd()

    def InsertRokokoStudioScene(self):
        '''Short cut to inserts all rigs and props needed for the current
        live connection.

        Note: Creates an undo.
        '''

        bcConnected = GetConnectedDataSet()
        if bcConnected is None:
            return
        self.InsertDataSetScene(bcConnected)

    def InsertRokokoCharacter(self, id, bonesOnly=False):
        '''Insert a default Rokoko Newton character without face poses into
        current scene.

        Optionally joints, only (don't ask why it's called bonesOnly...).

        Note: Creates an undo.
        '''

        docCurrent = c4d.documents.GetActiveDocument()
        filenameNewton = os.path.join(
            os.path.dirname(__file__), "res", "tpose_rokoko_newton_meshed.c4d")

        if bonesOnly:
            # If no skin is supposed to be added to the scene,
            # we need to extract the rig from default scene

            # Load default scene from plugin's resources
            docNewton = c4d.documents.LoadDocument(
                filenameNewton, c4d.SCENEFILTER_OBJECTS, None)
            if docNewton is None:
                print("ERROR: Failed to load Rokoko Newton.")
                return

            # Get rig from default scene. It has to be the first.
            objRootNewton = docNewton.GetFirstObject()
            if objRootNewton is None or \
               not objRootNewton.CheckType(c4d.Onull) or \
               objRootNewton.GetName() != "Rokoko Newton":
                print("ERROR: Failed to find Rokoko Newton bones.")
                return

            # Remove from default scene, we want to directly use it for
            # this scene (we could also clone it instead)
            objRootNewton.Remove()

            # Strip skin object(s)
            # NOTE: We expect a certain order of the hierarchy of the
            #       default scene.
            #       Take care of this when creating changing default scenes.
            objJoint = objRootNewton.GetDown()
            objMesh = objJoint.GetNext()  # Skip joints
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
            result = c4d.documents.MergeDocument(
                docCurrent,
                filenameNewton,
                c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS,
                None)
            if not result:
                print("ERROR: Failed to merge Rokoko Newton.")

        # Let C4D know, we have changed the scene
        c4d.EventAdd()

    def InsertRokokoCharacterWithFace(self, id):
        '''Insert a default Rokoko Newton character with face with poses into
        current scene.

        Note: Creates an undo (implicitly by MergeDocument()).
        '''

        # Simply merge the complete default scene into current document.
        docCurrent = c4d.documents.GetActiveDocument()
        filenameNewton = os.path.join(os.path.dirname(__file__),
                                      "res",
                                      "tpose_rokoko_newton_with_face.c4d")
        result = c4d.documents.MergeDocument(
            docCurrent,
            filenameNewton,
            c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS,
            None)
        if not result:
            print("ERROR: Failed to merge Rokoko Newton with Face")

        # Let C4D know, we have changed the scene
        c4d.EventAdd()

    def InsertRokokoFace(self, id):
        '''Insert a default Rokoko Newton face with poses (no rig) into
        current scene.

        Note: Creates an undo (implicitly by MergeDocument()).
        '''

        # Simply merge the complete default scene into current document.
        docCurrent = c4d.documents.GetActiveDocument()
        filenameNewton = os.path.join(os.path.dirname(__file__),
                                      "res",
                                      "rokoko_newton_face.c4d")
        result = c4d.documents.MergeDocument(
            docCurrent,
            filenameNewton,
            c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS,
            None)
        if not result:
            print("ERROR: Failed to merge Rokoko Newton Face")

        # Let C4D know, we have changed the scene
        c4d.EventAdd()

    def InsertRokokoLight(self):
        '''Insert a default light object with Rokoko tag into current scene.

        Note: Creates an undo.
        '''

        doc = c4d.documents.GetActiveDocument()

        # Create a new light object
        light = c4d.BaseObject(c4d.Olight)

        # Create Rokoko tag on light object
        tag = light.MakeTag(rid.PLUGIN_ID_TAG)

        # Insert light object into the scene
        doc.StartUndo()
        doc.InsertObject(light)
        doc.AddUndo(c4d.UNDOTYPE_NEW, light)
        doc.EndUndo()

        # Enforce initialization of tag (as if the user created it)
        tag.Message(c4d.MSG_MENUPREPARE)

        # Let C4D know, we have changed the scene
        c4d.EventAdd()

    def InsertRokokoCamera(self):
        '''Insert a default camera object with Rokoko tag into current scene.

        Note: Creates an undo.
        '''

        doc = c4d.documents.GetActiveDocument()

        # Create a new camera object
        camera = c4d.BaseObject(c4d.Ocamera)

        # Create Rokoko tag on camera object
        tag = camera.MakeTag(rid.PLUGIN_ID_TAG)

        # Insert camera object into the scene
        doc.StartUndo()
        doc.InsertObject(camera)
        doc.AddUndo(c4d.UNDOTYPE_NEW, camera)
        doc.EndUndo()

        # Enforce initialization of tag (as if the user created it)
        tag.Message(c4d.MSG_MENUPREPARE)

        # Let C4D know, we have changed the scene
        c4d.EventAdd()

    def InsertRokokoProp(self):
        '''Insert a default Null object with Rokoko tag into current scene.

        Note: Creates an undo.
        '''

        doc = c4d.documents.GetActiveDocument()

        # Create a new Null object
        prop = c4d.BaseObject(c4d.Onull)

        # Create Rokoko tag on Null object
        tag = prop.MakeTag(rid.PLUGIN_ID_TAG)

        # Insert Null object into the scene
        doc.StartUndo()
        doc.InsertObject(prop)
        doc.AddUndo(c4d.UNDOTYPE_NEW, prop)
        doc.EndUndo()

        # Enforce initialization of tag (as if the user created it)
        tag.Message(c4d.MSG_MENUPREPARE)

        # Let C4D know, we have changed the scene
        c4d.EventAdd()

    def CommandTagPopup(self, id):
        '''User pressed "..." button on a single tag in "Tags" tab.'''

        idxTag = id - rid.ID_DLGMNGR_BASE_TAG_POPUP

        # If player is active, certain menu options get disabled
        disableItem = ""
        if g_thdListener._receive:
            disableItem = "&d&"

        # Create menu BaseContainer
        bcMenu = c4d.BaseContainer()
        bcMenu.InsData(rid.ID_SUBMENU_TAG_PLAY, f"Play{disableItem}")
        bcMenu.InsData(rid.ID_SUBMENU_TAG_TPOSE, f"Go to T-Pose{disableItem}")
        bcMenu.InsData(0, "")  # separator
        bcMenu.InsData(rid.ID_SUBMENU_TAG_SHOW_TAG,
                       "Show Tag in Attribute Manager")
        bcMenu.InsData(rid.ID_SUBMENU_TAG_SHOW_OBJECT,
                       "Show Object in Attribute Manager")
        bcMenu.InsData(0, "")  # separator
        bcMenu.InsData(rid.ID_SUBMENU_TAG_DELETE,
                       f"Delete Rokoko Tag{disableItem}")

        # Show popup menu
        result = c4d.gui.ShowPopupDialog(
            cd=self, bc=bcMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)

        # Decode user choice
        self._tags = GetTagList()
        if result == rid.ID_SUBMENU_TAG_PLAY:
            self.CommandPlayerStart(idxTag=idxTag)
        elif result == rid.ID_SUBMENU_TAG_SHOW_TAG:
            self.ShowInAttributeManager(self._tags[idxTag])
        elif result == rid.ID_SUBMENU_TAG_SHOW_OBJECT:
            self.ShowInAttributeManager(self._tags[idxTag].GetObject())
        elif result == rid.ID_SUBMENU_TAG_DELETE:
            self.DeleteTag(idxTag)
        elif result == rid.ID_SUBMENU_TAG_TPOSE:
            c4d.CallButton(self._tags[idxTag], rid.ID_TAG_BUTTON_GO_TO_TPOSE)
            c4d.EventAdd()
        elif result == 0:
            pass  # menu canceled
        else:
            print("ERROR: Submenu Tags unknown command", result)

    def ShowInAttributeManager(self, bl):
        '''Show an object or tag in C4D's Attribute Manager'''

        if bl.CheckType(c4d.Tbase):
            c4d.gui.ActiveObjectManager_SetObject(
                c4d.ACTIVEOBJECTMODE_TAG,
                bl,
                c4d.ACTIVEOBJECTMANAGER_SETOBJECTS_OPEN,
                activepage=c4d.DescID())
        else:
            c4d.gui.ActiveObjectManager_SetObject(
                c4d.ACTIVEOBJECTMODE_OBJECT,
                bl,
                c4d.ACTIVEOBJECTMANAGER_SETOBJECTS_OPEN,
                activepage=c4d.DescID())

    def DeleteTag(self, idxTag):
        '''Delete Rokoko tag (referenced by dialog index) from scene.

        Note: Creates an undo.
        '''

        tag = self._tags.pop(idxTag)
        doc = tag.GetDocument()

        # Delete the tag
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_DELETE, tag)
        tag.Remove()
        doc.EndUndo()

        # Let C4D know, we have changed the scene
        c4d.EventAdd()

    def CommandAssignUnassignedTags(self):
        '''User pressed "Unassigned to Live" button on "Player" tab.'''

        bcConnected = GetConnectedDataSet()
        if bcConnected is None:
            return
        idConnected = bcConnected.GetId()

        # Prepare a dict to store rig type bits referenced by entity names.
        # The dict contains all actors and props.
        # No issue, if actors and props have identical names
        # (reason for storing bit mask).
        assigned = {}
        bcActors = bcConnected.GetContainerInstance(rid.ID_BC_DATASET_ACTORS)
        for idxActor, bcActor in bcActors:
            nameActor = bcActor[rid.ID_BC_ENTITY_NAME].lower()
            assigned[nameActor] = 0
        bcProps = bcConnected.GetContainerInstance(rid.ID_BC_DATASET_PROPS)
        for idxProp, bcProp in bcProps:
            nameProp = bcProp[rid.ID_BC_ENTITY_NAME].lower()
            assigned[nameProp] = 0

        # Iterate all tags in current scene
        for idxTag, tag in enumerate(self._tags):
            if not tag.IsAlive():
                continue

            # Skip tags with data assignment
            if tag[rid.ID_TAG_DATA_SET] != 0:
                continue

            # Skip unassigned tags (shouldn't happen actually)
            obj = tag.GetObject()
            if obj is None:
                continue

            bcTag = tag.GetDataInstance()

            # Assign live connection to tag
            bcTag.SetInt32(rid.ID_TAG_DATA_SET, idConnected)

            # Iterate all entities available in data
            rigType = tag[rid.ID_TAG_RIG_TYPE]
            idEntitiesBc = RigTypeToEntitiesBcId(rigType)
            bcEntities = bcConnected.GetContainerInstance(idEntitiesBc)
            for idxEntity, bcEntity in bcEntities:
                name = bcEntity[rid.ID_BC_ENTITY_NAME].lower()

                # If neither name matches and the entity has been
                # assigned before, skip to next
                if name not in tag.GetName().lower() and \
                   name not in obj.GetName().lower() and \
                   (assigned[name] & rigType):
                    continue

                # Assign entity to tag
                # TODO: See comment above about failing parameter set
                bcTag.SetInt32(rid.ID_TAG_ACTORS, idxEntity)

                # Entity has been assigned and will only be assigned again for
                # name matches
                assigned[name] |= rigType
                break

        c4d.EventAdd()

        # self.InitValues()

    def CommandProjectScale(self):
        '''User changed project scale,
        simply save new project scale in preferences.
        '''

        SetProjectScale(self.GetFloat(rid.ID_DLGMNGR_PROJECT_SCALE))

    def CommandPlayChoice(self):
        '''User changed the group (all, live, clips, selected) of tags to be
        used by Player.

        The choice is simply saved in preferences.
        '''

        SetPref(rid.ID_DLGMNGR_PLAYER_TAG_SELECTION,
                self.GetInt32(rid.ID_DLGMNGR_PLAYER_TAG_SELECTION))

    def CommandPlayerStart(self, all=False, live=False, idxTag=-1):
        '''User pressed "Player Start/Stop" button on "Player" tab.'''

        live = g_thdListener._receive

        # Button is a toggle button.
        # If Player is already started, stop it.
        if live:
            self.CommandPlayerExit()
            return

        # If connected to Studio without receiving data, we have an issue.
        # The listener thread waits for Studio and Player won't play without
        # received frames.
        # Thus user is asked to disconnect, so the offline Player thread can
        # be used.
        # User can still continue with the live connection, maybe if he plans
        # to start Live stream in a second.
        if not live and g_thdListener.GetConnectionStatus() == 2:
            result = c4d.gui.MessageDialog(
                ("Currently there is no data incoming from Live connection.\n"
                 "Disconnect?"),
                c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_YESNOCANCEL)
            if result == c4d.GEMB_R_YES:
                # Disconnect from Studio
                self.Connect(999999)
            elif result == c4d.GEMB_R_CANCEL:
                return  # user aborted

        # Get list of tags for Player based on user's choice in radio group
        # right of button
        choice = self.GetInt32(rid.ID_DLGMNGR_PLAYER_TAG_SELECTION)
        tagsLive = []
        self._tags = GetTagList()
        if choice == 0:
            # all
            tagsLive = self._tags
        elif choice == 2:
            # live
            idConnected = GetConnectedDataSetId()
            for tag in self._tags:
                if tag[rid.ID_TAG_DATA_SET] == idConnected:
                    tagsLive.append(tag)
        elif choice == 3:
            # data sets, only
            idConnected = GetConnectedDataSetId()
            for tag in self._tags:
                if tag[rid.ID_TAG_DATA_SET] != idConnected:
                    tagsLive.append(tag)
        elif idxTag != -1:
            # the one specified by idxTag (if user used "Play" in tag's popup
            # menu)
            tagsLive = [self._tags[idxTag]]
        else:
            # selected tags
            for tag in self._tags:
                if tag[rid.ID_TAG_SELECTED_IN_MANAGER]:
                    tagsLive.append(tag)

        # Check if there is at least one tag with valid data.
        # Otherwise abort.
        tagWithValidData = False
        for tag in tagsLive:
            if tag[rid.ID_TAG_VALID_DATA]:
                tagWithValidData = True
                break
        if not tagWithValidData:
            c4d.gui.MessageDialog(
                "No data to play.\n"
                "Either no tags selected or\n"
                "no valid data assigned to tags.")
            return

        # Register all selected tags in listener thread as consumers.
        # Not only those tags with valid data,
        # as the user shall be able to switch to valid data during playback.
        for tag in tagsLive:
            g_thdListener.AddTagConsumer(tag.GetNodeData(), tag)

        # Start Player and playback
        c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_PLAYER,
                            rid.CM_SUBID_PLAYER_START)
        c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_PLAYER,
                            rid.CM_SUBID_PLAYER_PLAY,
                            False)

    def CommandPlayerExit(self):
        '''User pressed "Player Start/Stop" button on "Player" tab to
        stop player.
        '''

        # Stop playback and exit player
        c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_PLAYER,
                            rid.CM_SUBID_PLAYER_STOP)
        c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_PLAYER,
                            rid.CM_SUBID_PLAYER_EXIT)

        # Reset state of "Start/Save Recording" button
        self._buttonRecordState = False

    def CommandPlaybackSpeed(self):
        '''User changed "Playback Rate" scale,
        simply save new playback rate in preferences.
        '''

        SetPref(rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED,
                self.GetInt32(rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED))

    def CommandAnimateDocument(self):
        '''User changed "Animate Document" scale,
        simply save new state in preferences.
        '''

        SetPref(rid.ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT,
                self.GetBool(rid.ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT))

    def CommandPause(self, force=False, returnToLive=False, idx=None):
        '''User pressed "Play/Pause" toggle button on "Player" tab.

        Force enforces "Pause" state (used by other buttons).
        If returnToLive is True, Player will unpause and resync with
        live stream.
        '''

        pause = (g_thdListener._play or force) and not returnToLive
        if pause:
            if idx is None:
                idx = self.GetInt32(rid.ID_DLGMNGR_PLAYER_CURRENT_FRAME)
            c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_PLAYER,
                                rid.CM_SUBID_PLAYER_PAUSE, idx)
        else:
            c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_PLAYER,
                                rid.CM_SUBID_PLAYER_PLAY, returnToLive)

    def CommandJumpToFrame(self, idx):
        '''User released scrub bar (or entered a frame index in edit field) in
        "Player" tab.

        Also used for "First/Last Frame" buttons.
        '''

        # Pause playback
        self.CommandPause(force=True, idx=idx)

        # Set scrub bar to paused frame
        # (needed for "First/Last Frame" and doesn't harm if request comes
        # from scrub bar)
        _, maxFrame = g_thdListener.GetCurrentFrameNumber()
        self.SetInt32(rid.ID_DLGMNGR_PLAYER_CURRENT_FRAME,
                      idx,
                      min=0, max=maxFrame,
                      min2=0, max2=maxFrame)

    def CommandStartNewRecording(self):
        '''Start a new recording,
        in reality simply flush live buffer.
        '''

        c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_PLAYER,
                            rid.CM_SUBID_PLAYER_FLUSH_LIVE_BUFFER)

    def CommandSaveRecording(self):
        '''Save a recording'''

        # Pause reception of live stream
        c4d.SpecialEventAdd(rid.PLUGIN_ID_COREMESSAGE_PLAYER,
                            rid.CM_SUBID_PLAYER_PAUSE_RECEPTION)

        # Pause playback
        self.CommandPause(force=True)

        # Disable entire Manager dialog
        self.EnableDialog(False)

        # Open "Save Recording..." dialog
        self._dlgChild = DialogSaveRecording(self)
        self._dlgChild.Open(c4d.DLG_TYPE_ASYNC)

    def CommandStartSaveRecording(self):
        '''User clicked "Start/Save Recording" toggle button on "Player" tab.
        '''

        if self._buttonRecordState:
            self.CommandSaveRecording()
        else:
            self.CommandStartNewRecording()

        # Toggle button state
        self._buttonRecordState = not self._buttonRecordState

        # Update player interface
        self.EnableLiveButtons()

    def CommandTagEnable(self, id):
        '''User clicked a tag's selection checkbox on "Tags" tab.

        Note: Creates an undo.
        '''

        idxTag = id - rid.ID_DLGMNGR_BASE_DATA_SET_ENABLED

        self._tags = GetTagList()
        if self._tags is None or idxTag >= len(self._tags):
            return

        tag = self._tags[idxTag]

        doc = c4d.documents.GetActiveDocument()

        # Select/deselect tag
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
        tag[rid.ID_TAG_SELECTED_IN_MANAGER] = self.GetBool(id)
        doc.EndUndo()

        # Let C4D know, we have changed the scene
        # Actually redundant currently, as the selection state is not
        # exposed in tag's parameters as originally planned
        c4d.EventAdd()

    def CommandTagSelectAll(self, select=True):
        '''User clicked "Select All" or "Deselect All" button on "Tags" tab.

        Note: Creates an undo.
        '''

        self._tags = GetTagList()
        if self._tags is None:
            return

        doc = c4d.documents.GetActiveDocument()

        # Select/deselect all tags
        doc.StartUndo()
        for tag in self._tags:
            doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
            tag[rid.ID_TAG_SELECTED_IN_MANAGER] = select
        doc.EndUndo()

        # Let C4D know, we have changed the scene
        # Actually redundant currently, as the selection state is not
        # exposed in tag's parameters as originally planned
        c4d.EventAdd()

    def CommandTagInvertSelection(self):
        '''User clicked "Invert Selection" button on "Tags" tab.

        Note: Creates an undo.
        '''

        self._tags = GetTagList()
        if self._tags is None:
            return

        doc = c4d.documents.GetActiveDocument()

        # Invert selection state of all tags
        doc.StartUndo()
        for tag in self._tags:
            doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
            tag[rid.ID_TAG_SELECTED_IN_MANAGER] = not tag[rid.ID_TAG_SELECTED_IN_MANAGER]  # noqa: E501
        doc.EndUndo()

        # Let C4D know, we have changed the scene
        # Actually redundant currently, as the selection state is not
        # exposed in tag's parameters as originally planned
        c4d.EventAdd()

    def CommandTagRigType(self, id):
        '''User changed type of a tag on "Tags" tab.

        Note: Creates an undo.
        '''

        idxTag = id - rid.ID_DLGMNGR_BASE_TAG_RIG_TYPES

        self._tags = GetTagList()
        if self._tags is None or idxTag >= len(self._tags):
            return

        tag = self._tags[idxTag]

        doc = c4d.documents.GetActiveDocument()

        # Change type of tag
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
        tag[rid.ID_TAG_RIG_TYPE] = self.GetInt32(id)
        doc.EndUndo()

        # Let C4D know, we have changed scene (e.g. tag in Attribute Manager)
        c4d.EventAdd()

    def CommandTagDataSet(self, id):
        '''User changed data set of a tag on "Tags" tab.

        Note: Creates an undo.
        '''

        idxTag = id - rid.ID_DLGMNGR_BASE_TAG_DATA_SETS

        self._tags = GetTagList()
        if self._tags is None or idxTag >= len(self._tags):
            return

        tag = self._tags[idxTag]

        doc = c4d.documents.GetActiveDocument()

        # Change selected data set
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
        tag[rid.ID_TAG_DATA_SET] = self.GetInt32(id)
        doc.EndUndo()

        # Let C4D know, we have changed scene (e.g. tag in Attribute Manager)
        c4d.EventAdd()

    def CommandTagActor(self, id):
        '''User selected another entity for a tag on "Tags" tab.

        Note: Creates an undo.
        '''

        idxTag = id - rid.ID_DLGMNGR_BASE_TAG_ACTORS

        self._tags = GetTagList()
        if self._tags is None or idxTag >= len(self._tags):
            return

        tag = self._tags[idxTag]

        doc = c4d.documents.GetActiveDocument()

        # Change selected entity
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, tag)
        tag[rid.ID_TAG_ACTORS] = self.GetInt32(id)
        doc.EndUndo()

        # Let C4D know, we have changed scene (e.g. tag in Attribute Manager)
        c4d.EventAdd()

    def CommandConnect(self, id):
        '''User "Connect/Disconnect" button of a connection on
        "Connection" tab.

        Also used for connection combo box in menu row.
        '''

        if id == rid.ID_DLGMNGR_CONNECTIONS_IN_MENU:
            idxConnection = self.GetInt32(id)
        else:
            idxConnection = id - rid.ID_DLGMNGR_BASE_CONNECTION_CONNECT
        self.Connect(idxConnection)

    def CommandAutoConnect(self, id):
        '''User changed "Auto Connect" state of a connection on
        "Connection" tab.

        Only one connction may have auto connect enabled.
        '''

        idxConnection = id - rid.ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT
        bcConnections = GetPrefsContainer(rid.ID_BC_CONNECTIONS)
        idConnectionClicked = bcConnections.GetIndexId(idxConnection)

        # Disable auto connect in all connections,
        # but the one clicked on (for which the checkbox state will be set).
        idx = 0
        for idConnection, bcConnection in bcConnections:
            enable = self.GetBool(id) and idConnectionClicked == idConnection
            bcConnections.GetContainerInstance(
                idConnection)[rid.ID_BC_DATASET_LIVE_AUTOCONNECT] = enable
            self.SetBool(
                rid.ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT + idx, enable)
            idx += 1

    def CommandCommandAPI(self, id):
        '''User clicked a Command API button'''

        bcConnected = GetConnectedDataSet()
        if bcConnected is None:
            # TODO: In case of multiple possible connections in UI,
            #       we'd probably need to insist on having a connection
            #       connected.
            # If there is currently no connection active,
            # use first defined connection instead.
            bcConnections = GetPrefsContainer(rid.ID_BC_CONNECTIONS)
            idFirstConnection = bcConnections.GetIndexId(0)
            bcConnected = bcConnections[idFirstConnection]

        # Build URL for selected command (and prepare some string for error
        # and status messages)
        url = "http://" + bcConnected[rid.ID_BC_DATASET_COMMANDAPI_IP] + ":"
        url += bcConnected[rid.ID_BC_DATASET_COMMANDAPI_PORT] + "/v1/"
        url += bcConnected[rid.ID_BC_DATASET_COMMANDAPI_KEY] + "/"
        actionText = "UNKNOWN"
        if id == rid.ID_DLGMNGR_COMMANDAPI_START_RECORDING:
            actionText = "Start Recording"
            statusText = "Rokoko Studio Recording started"
            url += "recording/start"
        elif id == rid.ID_DLGMNGR_COMMANDAPI_STOP_RECORDING:
            actionText = "Stop Recording"
            statusText = "Rokoko Studio Recording stopped"
            url += "recording/stop"
        elif id == rid.ID_DLGMNGR_COMMANDAPI_CALIBRATE_ALL_SUITS:
            actionText = "Start Suit Calibration"
            statusText = "Rokoko Studio Suit Calibration started"
            url += "calibrate"
        elif id == rid.ID_DLGMNGR_COMMANDAPI_RESET_ALL_SUITS:
            actionText = "Reset All Suits"
            statusText = "Reset All Suits in Rokoko Studio"
            url += "restart"

        # Do a POST request
        # Unfortunately Rokoko Studio returns an HTTP error,
        # even if communication was successful,
        # but another error occurred (like e.g. no suit connected).
        postData = {}
        postData = str(postData)
        postData = postData.encode("utf-8")
        ok = True
        try:
            req = urllib.request.Request(url, postData, unverifiable=True)
            _ = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            # Get actual answer from Rokoko Studio
            d = json.loads(e.__dict__["file"].read())
            responseCode = d["response_code"]
            description = d["description"]
            if responseCode == "OK":  # TODO
                pass
            else:
                # NO_LIVE_SMARTSUIT
                # NO_ACTIVE_RECORDING
                c4d.gui.MessageDialog(
                    f"Rokoko Command API failed to {actionText}\n\n"
                    f"Error Code:    {responseCode}\n"
                    f"Error Message: {description}")
                ok = False
        except BaseException:
            c4d.gui.MessageDialog(
                "Command API failed to connect to Rokoko Studio.\n"
                "Please check IP, port and key configured for Command API "
                "in Connection.")

        # Success message
        if ok:
            c4d.StatusSetText(statusText)

    def CommandAbout(self):
        '''User wants About dialog'''

        dlg = DialogAbout()
        dlg.Open(c4d.DLG_TYPE_MODAL)

    def CommandWeb(self, id):
        '''User wants a web link from "Help" menu'''

        if id not in LINKS:
            print("ERROR: Unknown link ID")
            return
        c4d.storage.GeExecuteFile(LINKS[id])

    def Command(self, id, msg):
        '''Called by C4D to handle user's interaction with the dialog.'''

        # Dialog tabs/groups
        if id == rid.ID_DLGMNGR_TABS:
            self.UpdateGroupVisibility()

        # Connection tab
        # Add connection button ("+"), currently not in UI
        elif id == rid.ID_DLGMNGR_CONNECTION_POPUP:
            self.CommandConnectionsPopup()
        # Per connection popup menu, button "..."
        elif rid.ID_DLGMNGR_BASE_CONNECTION_POPUP <= id < rid.ID_DLGMNGR_BASE_CONNECTION_POPUP + 10000:  # noqa: E501
            self.CommandConnectionPopup(id)
        # Per connection "Connect/Disconnect" button
        elif rid.ID_DLGMNGR_BASE_CONNECTION_CONNECT <= id < rid.ID_DLGMNGR_BASE_CONNECTION_CONNECT + 10000:  # noqa: E501
            self.CommandConnect(id)
        # Per connection "Auto Connect" checkbox
        elif rid.ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT <= id < rid.ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT + 10000:  # noqa: E501
            self.CommandAutoConnect(id)
        # Connection combo box in menu row
        elif id == rid.ID_DLGMNGR_CONNECTIONS_IN_MENU:
            self.CommandConnect(id)

        # Global Clips library tab
        # Main popup menu, button "+" ("Add File...", ...)
        elif id == rid.ID_DLGMNGR_GLOBAL_DATA_POPUP:
            self.CommandDataPopup(local=False)
        # Per clip popup menu, button "..."
        elif rid.ID_DLGMNGR_BASE_GLOBAL_DATA_POPUP <= id < rid.ID_DLGMNGR_BASE_GLOBAL_DATA_POPUP + 10000:  # noqa: E501
            self.CommandDataSetPopup(id, local=False)

        # Project Clips library tab
        # Main popup menu, button "+" ("Add File...", ...)
        elif id == rid.ID_DLGMNGR_LOCAL_DATA_POPUP:
            self.CommandDataPopup(local=True)
        # Per clip popup menu, button "..."
        elif rid.ID_DLGMNGR_BASE_LOCAL_DATA_POPUP <= id < rid.ID_DLGMNGR_BASE_LOCAL_DATA_POPUP + 10000:  # noqa: E501
            self.CommandDataSetPopup(id, local=True)

        # Tags tab
        # Main popup menu, button "+" ("Create character",...)
        elif id == rid.ID_DLGMNGR_TAGS_POPUP:
            self.CommandTagsPopup()
        # Per tag popup menu, button "..."
        elif rid.ID_DLGMNGR_BASE_TAG_POPUP <= id < rid.ID_DLGMNGR_BASE_TAG_POPUP + 10000:  # noqa: E501
            self.CommandTagPopup(id)
        # Tag parameters
        elif rid.ID_DLGMNGR_BASE_TAG_RIG_TYPES <= id < rid.ID_DLGMNGR_BASE_TAG_RIG_TYPES + 10000:  # noqa: E501
            self.CommandTagRigType(id)
        elif rid.ID_DLGMNGR_BASE_TAG_DATA_SETS <= id < rid.ID_DLGMNGR_BASE_TAG_DATA_SETS + 10000:  # noqa: E501
            self.CommandTagDataSet(id)
        elif rid.ID_DLGMNGR_BASE_TAG_ACTORS <= id < rid.ID_DLGMNGR_BASE_TAG_ACTORS + 10000:  # noqa: E501
            self.CommandTagActor(id)
        # Tag selection for player
        elif rid.ID_DLGMNGR_BASE_DATA_SET_ENABLED <= id < rid.ID_DLGMNGR_BASE_DATA_SET_ENABLED + 10000:  # noqa: E501
            self.CommandTagEnable(id)
        # Select buttons
        elif id == rid.ID_DLGMNGR_SELECT_ALL_TAGS:
            self.CommandTagSelectAll()
        elif id == rid.ID_DLGMNGR_DESELECT_ALL_TAGS:
            self.CommandTagSelectAll(select=False)
        elif id == rid.ID_DLGMNGR_INVERT_SELECTION:
            self.CommandTagInvertSelection()
        # Assign unassigned tags to live connection
        elif id == rid.ID_DLGMNGR_ASSIGN_UNASSIGNED_TAGS:
            self.CommandAssignUnassignedTags()
        # Project scale
        elif id == rid.ID_DLGMNGR_PROJECT_SCALE:
            self.CommandProjectScale()

        # Player tab
        # Player start/stop
        elif id == rid.ID_DLGMNGR_PLAYER_START_STOP:
            self.CommandPlayerStart()
        elif id == rid.ID_DLGMNGR_PLAYER_TAG_SELECTION:
            self.CommandPlayChoice()
        # Player playback control
        elif id == rid.ID_DLGMNGR_PLAYER_PAUSE:
            self.CommandPause()
        elif id == rid.ID_DLGMNGR_PLAYER_SYNC_WITH_LIVE:
            self.CommandPause(returnToLive=True)
        elif id == rid.ID_DLGMNGR_PLAYER_PLAYBACK_SPEED:
            self.CommandPlaybackSpeed()
        elif id == rid.ID_DLGMNGR_PLAYER_CURRENT_FRAME:  # scrub bar
            self.CommandJumpToFrame(self.GetInt32(id))
        elif id == rid.ID_DLGMNGR_PLAYER_FIRST_FRAME:
            self.CommandJumpToFrame(0)
        elif id == rid.ID_DLGMNGR_PLAYER_LAST_FRAME:
            _, maxFrame = g_thdListener.GetCurrentFrameNumber()
            self.CommandJumpToFrame(maxFrame - 1)
        # Player parameters
        elif id == rid.ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT:
            self.CommandAnimateDocument()
        elif id == rid.ID_DLGMNGR_PLAYER_SAVE:
            self.CommandStartSaveRecording()

        # Command API tab
        elif id in [rid.ID_DLGMNGR_COMMANDAPI_START_RECORDING,
                    rid.ID_DLGMNGR_COMMANDAPI_STOP_RECORDING,
                    rid.ID_DLGMNGR_COMMANDAPI_CALIBRATE_ALL_SUITS,
                    rid.ID_DLGMNGR_COMMANDAPI_RESET_ALL_SUITS]:
            self.CommandCommandAPI(id)

        # Help menu
        # Web links
        elif id in [rid.ID_DLGMNGR_WEB_ROKOKO,
                    rid.ID_DLGMNGR_WEB_STUDIO_LIVE_LICENSE,
                    rid.ID_DLGMNGR_WEB_DOCUMENTATION,
                    rid.ID_DLGMNGR_WEB_FORUMS]:
            self.CommandWeb(id)
        # About
        elif id == rid.ID_DLGMNGR_ABOUT:
            self.CommandAbout()
        return True
