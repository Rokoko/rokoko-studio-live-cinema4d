# In Cinema 4D object tags get implemented as TagData plugins.
# The actual action happens in Execute(), which is called by C4D during the evaluation of the
# scene/execution pipeline.
#
# In Rokoko Studio Live the tag provides the connection between some motion data source (namely
# a data queue (either from live stream or from a Clip) registered inside the listner thread) and scene
# objects (joint rigs, face meshes or arbitrary objects for props).
#
# The tag implemented for Rokoko Studio Live is in a few ways a bit different than most other tags.
#
# a) Depending on its type (Actor, Face, Prop) the tag provides slightly different parameters in the UI
# and uses different execute functions. In bounds of the given parent object the type can also be
# manually changed by the user. Auto detection of type happens on tag creation (via
# MSG_MENU_PREPARE), but also when being copied or dragged around (this is done under certain
# conditions in MSG_GET_CUSTOM_ICON, when we need to provide C4D with an icon of correct type,
# anyway).
#
# b) The tag is usually passive and doesn't do anything (or rather almost nothing) during Execute().
# Only after an "execute" flag was set (e.g. when the Player gets started) it will, depending on its type,
# map the dispatched motion data frame onto the scene object(s).
#
# Each tag owns a tag queue for inbound mottion data frames.
import c4d
from rokoko_ids import *
from rokoko_rig_tables import *
from rokoko_utils import *
from rokoko_tag_queue import *
from rokoko_description_utils import *
from rokoko_listener import *
from rokoko_dialog_save_recording import *

g_thdListener = GetListenerThread() # owned by rokoko_listener
g_studioTPose = {} # created and owned by rokoko_plugin_registration
def TagSetGlobalStudioTPose(tPose):
    global g_studioTPose
    g_studioTPose = tPose

# To be called during shutdown
def TagDestroyGlobals():
    global g_thdListener
    global g_studioTPose
    g_thdListener = None
    g_studioTPose = {}


class TagDataRokoko(c4d.plugins.TagData):
    _iconsValid = False
    _bmpIcon24 = None
    _bmpIcon32 = None
    _bmpIcon36 = None
    _bmpIcon48 = None
    _bmpIcon64 = None
    _lastObj = None
    _lastRigType = RIG_TYPE_UNKNOWN
    _queueReceive = TagQueue()
    _funcExecute = None
    _tPoseTag = {}
    _facePoses = {}
    _dataSets = {} # only temporarily valid (set during SetDataSetMenuContainer() to be used in SetActorMenuContainer())

    # Most relevant entry points:
    # - Init()
    # - GetDDescription()
    # - GetDEnabling()
    # - SetDParameter()
    # - Message()
    # - Execute()
    # - CopyTo()


    # Called by C4D to initialize a new tag instance.
    # This call happens _before_ the tag gets assigned to the host object.
    def Init(self, node):
        self._iconsValid = False
        self._bmpIcon24 = c4d.bitmaps.BaseBitmap()
        self._bmpIcon24.Init(24, 24)
        self._bmpIcon32 = c4d.bitmaps.BaseBitmap()
        self._bmpIcon32.Init(32, 32)
        self._bmpIcon36 = c4d.bitmaps.BaseBitmap()
        self._bmpIcon36.Init(36, 36)
        self._bmpIcon48 = c4d.bitmaps.BaseBitmap()
        self._bmpIcon48.Init(48, 48)
        self._bmpIcon64 = c4d.bitmaps.BaseBitmap()
        self._bmpIcon64.Init(64, 64)
        self._lastObj = None
        self._lastRigType = RIG_TYPE_UNKNOWN
        self._lastDataSet = -1
        self._tPoseTag = {}

        # Initialize description parameters
        self.InitAttr(node, int, ID_TAG_RIG_TYPE)
        self.InitAttr(node, int, ID_TAG_DATA_SET)
        self.InitAttr(node, int, ID_TAG_ACTORS)
        self.InitAttr(node, int, ID_TAG_ACTOR_INDEX)
        self.InitAttr(node, int, ID_TAG_DATA_SET_FIRST_FRAME)
        self.InitAttr(node, int, ID_TAG_DATA_SET_LAST_FRAME)
        self.InitAttr(node, bool, ID_TAG_OPEN_MANAGER_ON_PLAY)
        self.InitAttr(node, str, ID_TAG_ENTITY_STATUS)
        self.InitAttr(node, str, ID_TAG_ENTITY_NAME)
        self.InitAttr(node, c4d.Vector, ID_TAG_ENTITY_COLOR)
        self.InitAttr(node, float, ID_TAG_ACTOR_HIP_HEIGHT)
        self.InitAttr(node, bool, ID_TAG_ACTOR_MAP_BODY)
        self.InitAttr(node, bool, ID_TAG_ACTOR_MAP_HAND_LEFT)
        self.InitAttr(node, bool, ID_TAG_ACTOR_MAP_HAND_RIGHT)
        # internal parameters, not exposed in Attribute Manager
        self.InitAttr(node, bool, ID_TAG_SELECTED_IN_MANAGER)
        self.InitAttr(node, int, ID_TAG_EXECUTE_MODE)
        self.InitAttr(node, bool, ID_TAG_VALID_DATA)
        self.InitAttr(node, bool, ID_TAG_ACTOR_TPOSE_STORED)
        self.InitAttr(node, bool, ID_TAG_ACTOR_RIG_DETECTED)
        self.InitAttr(node, bool, ID_TAG_ACTOR_FACE_DETECTED)
        self.InitAttr(node, bool, ID_TAG_ACTOR_HAS_BODY)
        self.InitAttr(node, bool, ID_TAG_ACTOR_HAS_HIP)
        self.InitAttr(node, bool, ID_TAG_ACTOR_HAS_HAND_LEFT)
        self.InitAttr(node, bool, ID_TAG_ACTOR_HAS_HAND_RIGHT)
        self.InitAttr(node, c4d.BaseContainer, ID_TAG_BC_RIG_TYPES)
        self.InitAttr(node, c4d.BaseContainer, ID_TAG_BC_DATASETS)
        self.InitAttr(node, c4d.BaseContainer, ID_TAG_BC_ACTORS)

        # Set defaults
        bcTag = node.GetDataInstance()
        for (idxJoint, _, _, _, _, _, _, _) in STUDIO_NAMES_TO_GUESS.values():
            self.InitAttr(node, c4d.BaseList2D, ID_TAG_BASE_RIG_LINKS + idxJoint) # exposed in Attribute Manager
            self.InitAttr(node, c4d.Matrix, ID_TAG_BASE_RIG_MATRICES + idxJoint) # internal
            #bcTag.SetLink(ID_TAG_BASE_RIG_LINKS + idxJoint, None) # TODO: I'd prefer not to do a SetParameter()...
            node.SetParameter(ID_TAG_BASE_RIG_LINKS + idxJoint, None, c4d.DESCFLAGS_SET_NONE)
            bcTag.SetMatrix(ID_TAG_BASE_RIG_MATRICES + idxJoint, c4d.Matrix())
            bcTag.SetMatrix(ID_TAG_BASE_RIG_MATRICES_PRETRANSFORMED + idxJoint, c4d.Matrix())
        bcTag.SetMatrix(ID_TAG_ROOT_MATRIX, c4d.Matrix())
        for (idxPose, _, _, _, _, _) in FACE_POSE_NAMES.values():
            self.InitAttr(node, str, ID_TAG_BASE_FACE_POSES + idxPose) # exposed in Attribute Manager
            self.InitAttr(node, int, ID_TAG_BASE_MORPH_INDECES + idxPose) # internal
            bcTag.SetString(ID_TAG_BASE_FACE_POSES + idxPose, '')
            bcTag.SetInt32(ID_TAG_BASE_MORPH_INDECES + idxPose, 0)
        bcTag.SetInt32(ID_TAG_RIG_TYPE, 0)
        bcTag.SetInt32(ID_TAG_DATA_SET, 0)
        bcTag.SetInt32(ID_TAG_ACTORS, 0)
        bcTag.SetInt32(ID_TAG_ACTOR_INDEX, 0)
        bcTag.SetInt32(ID_TAG_DATA_SET_FIRST_FRAME, 0)
        bcTag.SetInt32(ID_TAG_DATA_SET_LAST_FRAME, 1)
        bcTag.SetBool(ID_TAG_OPEN_MANAGER_ON_PLAY, False) # option no longer in interface, always false
        bcTag.SetString(ID_TAG_ENTITY_STATUS, 'Data not valid')
        bcTag.SetString(ID_TAG_ENTITY_NAME, '')
        bcTag.SetVector(ID_TAG_ENTITY_COLOR, c4d.Vector(0.0))
        bcTag.SetFloat(ID_TAG_ACTOR_HIP_HEIGHT, 0.0)
        bcTag.SetBool(ID_TAG_ACTOR_MAP_BODY, False)
        bcTag.SetBool(ID_TAG_ACTOR_MAP_HAND_LEFT, False)
        bcTag.SetBool(ID_TAG_ACTOR_MAP_HAND_RIGHT, False)
        bcTag.SetBool(ID_TAG_SELECTED_IN_MANAGER, True)
        bcTag.SetInt32(ID_TAG_EXECUTE_MODE, 0)
        bcTag.SetBool(ID_TAG_VALID_DATA, False)
        bcTag.SetBool(ID_TAG_ACTOR_TPOSE_STORED, False)
        bcTag.SetBool(ID_TAG_ACTOR_RIG_DETECTED, False)
        bcTag.SetBool(ID_TAG_ACTOR_FACE_DETECTED, False)
        bcTag.SetBool(ID_TAG_ACTOR_HAS_BODY, False)
        bcTag.SetBool(ID_TAG_ACTOR_HAS_HIP, False)
        bcTag.SetBool(ID_TAG_ACTOR_HAS_HAND_LEFT, False)
        bcTag.SetBool(ID_TAG_ACTOR_HAS_HAND_RIGHT, False)
        bcTag.SetContainer(ID_TAG_BC_RIG_TYPES, c4d.BaseContainer())
        bcTag.SetContainer(ID_TAG_BC_DATASETS, c4d.BaseContainer())
        bcTag.SetContainer(ID_TAG_BC_ACTORS, c4d.BaseContainer())
        return True


    # Adds an entry to the "Data" combo box BaseContainer,
    # addition depends on tag type and data provided by data set.
    def DataSetMenuContainerAdd(self, rigType, bcDataSet, bcMenu):
        idDataSet = bcDataSet.GetId()
        nameDataSet = bcDataSet[ID_BC_DATASET_NAME]
        if rigType & RIG_TYPE_ACTOR and bcDataSet[ID_BC_DATASET_NUM_ACTORS] > 0:
            bcMenu[idDataSet] = '{0} ({1})'.format(nameDataSet, bcDataSet[ID_BC_DATASET_NUM_ACTORS])
        elif rigType & RIG_TYPE_ACTOR_FACE and bcDataSet[ID_BC_DATASET_NUM_FACES] > 0:
            bcMenu[idDataSet] = '{0} ({1})'.format(nameDataSet, bcDataSet[ID_BC_DATASET_NUM_FACES])
        elif rigType & RIG_TYPE_LIGHT and bcDataSet[ID_BC_DATASET_NUM_LIGHTS] > 0:
            bcMenu[idDataSet] = '{0} ({1})'.format(nameDataSet, bcDataSet[ID_BC_DATASET_NUM_LIGHTS])
        elif rigType & RIG_TYPE_CAMERA and bcDataSet[ID_BC_DATASET_NUM_CAMERAS] > 0:
            bcMenu[idDataSet] = '{0} ({1})'.format(nameDataSet, bcDataSet[ID_BC_DATASET_NUM_CAMERAS])
        elif rigType & RIG_TYPE_PROP and bcDataSet[ID_BC_DATASET_NUM_PROPS] > 0:
            bcMenu[idDataSet] = '{0} ({1})'.format(nameDataSet, bcDataSet[ID_BC_DATASET_NUM_PROPS])


    # Prepare a BaseContainer with the content for the "Data" combo box.
    # Available data sets depend on data being suitable for tag type.
    def SetDataSetMenuContainer(self, tag):
        description = tag.GetDescription(c4d.DESCFLAGS_DESC_NONE)
        self._dataSets = {} # stores only keys (data set IDs), for use in SetActorMenuContainer()
        bcMenu = c4d.BaseContainer()

        # If tag type is unknown
        rigType = tag[ID_TAG_RIG_TYPE]
        if rigType is None or rigType == RIG_TYPE_UNKNOWN:
            # Store a more or less empty container indicating the error
            bcMenu[0] = 'No clips, Rig type unknown!!!'
            tag.SetParameter(ID_TAG_BC_DATASETS, bcMenu, c4d.DESCFLAGS_SET_NONE)
            return

        # Add live connection (if any and suitable)
        bcConnected = GetConnectedDataSet()
        if bcConnected is not None:
            self._dataSets[bcConnected.GetId()] = '' # store index in dict
            self.DataSetMenuContainerAdd(rigType, bcConnected, bcMenu)
            bcMenu[2] = '' # separator

        # Add data sets from project clip library (if any and suitable)
        addSeparator = False
        bcDataSetsLocal = GetLocalDataSets()
        for id, bcDataSet in bcDataSetsLocal:
            self._dataSets[bcDataSet.GetId()] = '' # store index in dict
            self.DataSetMenuContainerAdd(rigType, bcDataSet, bcMenu)
            addSeparator = True
        # Add another separator only, if there were project data sets added
        if addSeparator:
            bcMenu[3] = '' # separator

        # Add data sets from global clip library (if any and suitable)
        bcDataSetsGlobal = GetPrefsContainer(ID_BC_DATA_SETS)
        for id, bcDataSet in bcDataSetsGlobal:
            self._dataSets[bcDataSet.GetId()] = '' # store index in dict
            self.DataSetMenuContainerAdd(rigType, bcDataSet, bcMenu)

        # Now check, if selected data set is actually amongst those in combo box
        idSelectedDataSet = bcMenu.GetData(tag[ID_TAG_DATA_SET])
        if idSelectedDataSet is None:
            # Selected data set is currently missing
            # Add another entry indicating this to the user and preserving the selected ID
            bcMenu[4] = '' # separator
            bcMenu[tag[ID_TAG_DATA_SET]] = 'Data not available'
            tag[ID_TAG_ENTITY_COLOR] = c4d.Vector(0.0)
            tag[ID_TAG_ENTITY_NAME] = ''
            tag[ID_TAG_ENTITY_STATUS] = 'Data not valid'

        # Finally add the option for no data selected
        bcMenu[5] = '' # separator
        bcMenu[0] = 'None'

        # Store prepared BaseContainer in tag's BaseContainer
        tag.SetParameter(ID_TAG_BC_DATASETS, bcMenu, c4d.DESCFLAGS_SET_FORCESET)


    # Returns the prepared BaseContainer with content for the "Data" combo box
    def GetDataSetMenuContainer(self, tag):
        bc = tag.GetDataInstance().GetContainerInstance(ID_TAG_BC_DATASETS)

        # If prepared BaseContainer does not exist
        if bc is None:
            # Return a more or less empty container indicating the error
            bc = c4d.BaseContainer()
            bc[0] = 'Error'
        return bc


    # Prepare a BaseContainer with the content for the "Type" combo box.
    # Available types depend on host object, the tag is assigned to.
    def SetRigTypeMenuContainer(self, tag):
        bc = c4d.BaseContainer()
        obj = tag.GetObject()
        if obj is None:
            # Store a more or less empty container indicating the error
            bc[0xFFFF] = 'Tag not attached'
            tag.SetParameter(ID_TAG_BC_RIG_TYPES, bc, c4d.DESCFLAGS_SET_NONE)
            return

        # Currently it's quite simple,
        # additonal to prop a tag can either be actor or face.
        rigTypeOptions = DetermineRigTypeOptions(obj)
        if rigTypeOptions & RIG_TYPE_ACTOR:
            bc[RIG_TYPE_ACTOR] = 'Actor'
        elif rigTypeOptions & RIG_TYPE_ACTOR_FACE:
            bc[RIG_TYPE_ACTOR_FACE] = 'Face'
        elif rigTypeOptions & RIG_TYPE_LIGHT: # not used currently
            bc[RIG_TYPE_LIGHT] = 'Light'
        elif rigTypeOptions & RIG_TYPE_CAMERA: # not used currently
            bc[RIG_TYPE_CAMERA] = 'Camera'

        # Every object can be a prop
        bc[RIG_TYPE_PROP] = 'Prop'

        # Store prepared BaseContainer in tag's BaseContainer
        tag.SetParameter(ID_TAG_BC_RIG_TYPES, bc, c4d.DESCFLAGS_SET_NONE)


    # Returns the prepared BaseContainer with content for the "Entity" combo box
    def GetRigTypeMenuContainer(self, tag):
        bc = tag.GetDataInstance().GetContainerInstance(ID_TAG_BC_RIG_TYPES)

        # If prepared BaseContainer does not exist
        if bc is None:
            # Return a more or less empty container indicating the error
            bc = c4d.BaseContainer()
            bc[0xFFFF] = 'Error'
        return bc


    # Prepare a BaseContainer with the content for the "Entity" combo box.
    # Basically list of Actors, Faces or Props.
    # This happens during initialization or when a new data set is selected,
    # in order to be used in GetDDescription().
    def SetActorMenuContainer(self, tag):
        bcMenu = c4d.BaseContainer()

        # If tag type is unknown, then there is no data set to select entities from.
        rigType = tag[ID_TAG_RIG_TYPE]
        if rigType is None or rigType == RIG_TYPE_UNKNOWN:
            bcMenu[0] = 'No clip, Actor unknown!!!'
            tag.SetParameter(ID_TAG_BC_ACTORS, bcMenu, c4d.DESCFLAGS_SET_NONE)
            tag.SetParameter(ID_TAG_VALID_DATA, False, c4d.DESCFLAGS_SET_NONE)
            return

        # If no data set is selected, then there is no data set to select entities from.
        idDataSet = tag[ID_TAG_DATA_SET]
        if idDataSet is None or idDataSet == 0:
            bcMenu[tag[ID_TAG_ACTORS]] = 'No clip selected'
            tag.SetParameter(ID_TAG_BC_ACTORS, bcMenu, c4d.DESCFLAGS_SET_NONE)
            tag.SetParameter(ID_TAG_VALID_DATA, False, c4d.DESCFLAGS_SET_NONE)
            return

        # The data set might be temporarily unavailable, then there is no data set to select entities from.
        bcDataSet = GetDataSetFromId(idDataSet)
        if bcDataSet is None:
            bcMenu[tag[ID_TAG_ACTORS]] = 'Clip not found'
            tag.SetParameter(ID_TAG_BC_ACTORS, bcMenu, c4d.DESCFLAGS_SET_NONE)
            tag.SetParameter(ID_TAG_VALID_DATA, False, c4d.DESCFLAGS_SET_NONE)
            return

        # Each entity will have two entries in the combo box.
        # One by name and one by index.

        # When the container for the "Data" combo box was prepared,
        # the list of data sets got cached temporarily.
        # Only if the selected data set is in there (it could be, data set is temporarily unavailable) and
        # the motion data also contains valid data for type of tag.
        if idDataSet in self._dataSets:
            # Get enitites container for type of tag
            idEntitiesBc = RigTypeToEntitiesBcId(rigType)
            actorsByIndex = [] # actors names stored by index
            bcEntities = bcDataSet.GetContainerInstance(idEntitiesBc)

            # Iterate all entities and create an entry to select entity by name
            for idxEntity, _ in bcEntities:
                bcEntity = bcEntities.GetContainerInstance(idxEntity)

                # Only add entry if entity's motion data contains data needed by tag type
                addEntry = False
                if (rigType & RIG_TYPE_ACTOR) and (bcEntity[ID_BC_ENTITY_HAS_SUIT] or bcEntity[ID_BC_ENTITY_HAS_GLOVE_LEFT] or bcEntity[ID_BC_ENTITY_HAS_GLOVE_RIGHT]):
                    addEntry = True
                elif (rigType & RIG_TYPE_ACTOR_FACE) and bcEntity[ID_BC_ENTITY_HAS_FACE]:
                    addEntry = True
                elif rigType & RIG_TYPE_LIGHT:
                    addEntry = True
                elif rigType & RIG_TYPE_CAMERA:
                    addEntry = True
                elif rigType & RIG_TYPE_PROP:
                    addEntry = True

                if addEntry:
                    # Create entry to select by name
                    name = bcEntity[ID_BC_ENTITY_NAME]
                    bcMenu[MyHash(name)] = '{0} (#{1})'.format(name, idxEntity)
                    nameByIndex = '#{0} - {1}'.format(idxEntity, name)

                    # Store name and index to create index selection entries in next loop
                    actorsByIndex.append((idxEntity, nameByIndex))

            bcMenu[111111] = '' # separator

            # Add entries to select entity by index
            for idxEntity, nameByIndex in actorsByIndex:
                bcMenu[idxEntity] = nameByIndex

        # Check, if the actually selected entity is inside the created container.
        # If not, create another entry to preserve the selection value.
        idSelectedActor = bcMenu.GetData(tag[ID_TAG_ACTORS])
        if idSelectedActor is None:
            validData = False
            bcMenu[111112] = ''
            bcMenu[tag[ID_TAG_ACTORS]] = 'Not available'
        else:
            validData = True

        # Store prepared BaseContainer in tag's BaseContainer
        tag.SetParameter(ID_TAG_BC_ACTORS, bcMenu, c4d.DESCFLAGS_SET_NONE)

        # Store valid data flag
        # TODO: STRANGE!
        tag.GetDataInstance()[ID_TAG_VALID_DATA] = validData
        tag.SetParameter(ID_TAG_VALID_DATA, validData, c4d.DESCFLAGS_SET_FORCESET)


    # Returns the prepared BaseContainer with content for the "Entity" combo box
    def GetActorMenuContainer(self, tag):
        bc = tag.GetDataInstance().GetContainerInstance(ID_TAG_BC_ACTORS)

        # If prepared BaseContainer does not exist
        if bc is None:
            # Return a more or less empty container indicating the error
            bc = c4d.BaseContainer()
            bc[0xFFFF] = 'Error'
        return bc


    # Create "Main" Description tab (Tag Properties)
    def GetDDescriptionGroupMain(self, tag, description, singleId):
        # Tag type combo box
        bcRigTypes = self.GetRigTypeMenuContainer(tag)
        if not GetDDescriptionCreateCombo(tag, description, singleId, ID_TAG_RIG_TYPE, 'Type', c4d.ID_TAGPROPERTIES, bcRigTypes, anim=False, valDefault=0):
            return False

        # Data combo box
        bcDataSets = self.GetDataSetMenuContainer(tag)
        if not GetDDescriptionCreateCombo(tag, description, singleId, ID_TAG_DATA_SET, 'Stream/Clips', c4d.ID_TAGPROPERTIES, bcDataSets, anim=False, valDefault=0):
            return False

        # Entity combo box
        bcActors = self.GetActorMenuContainer(tag)
        rigType = tag[ID_TAG_RIG_TYPE]
        if rigType is None:
            return True
        labelEntities = RigTypeToEntitiesString(rigType)
        if not GetDDescriptionCreateCombo(tag, description, singleId, ID_TAG_ACTORS, labelEntities, c4d.ID_TAGPROPERTIES, bcActors, anim=False, valDefault=0):
            return False

        # Only if the data set is properly connected, intialize first/last slider with clip length
        if tag[ID_TAG_DATA_SET] in g_thdListener._dataQueues:
            maxFrame = len(g_thdListener._dataQueues[tag[ID_TAG_DATA_SET]])
        else:
            maxFrame = 1
        if not GetDDescriptionCreateLong(tag, description, singleId, ID_TAG_DATA_SET_FIRST_FRAME, 'First Frame', c4d.ID_TAGPROPERTIES, anim=False, valDefault=0, valMax=maxFrame-1, sliderMax=maxFrame-1):
            return False
        if not GetDDescriptionCreateLong(tag, description, singleId, ID_TAG_DATA_SET_LAST_FRAME, 'Last Frame', c4d.ID_TAGPROPERTIES, anim=False, valDefault=maxFrame, valMin=1, sliderMin=1, valMax=maxFrame, sliderMax=maxFrame):
            return False
        return True


    # Create "Control" Description tab
    def GetDDescriptionGroupControl(self, tag, description, singleId):
        # Tab group
        if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_CONTROL, 'Control', 0, numColumns=2, defaultOpen=True):
            return False

        # Control buttons
        # Play button changes label according to Player state
        if g_thdListener._receive:
            if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_PLAY, 'Stop', ID_TAG_GROUP_CONTROL, scaleH=True):
                return False
        else:
            if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_PLAY, 'Play', ID_TAG_GROUP_CONTROL, scaleH=True):
                return False
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_GO_TO_TPOSE, 'Go to T-Pose', ID_TAG_GROUP_CONTROL, scaleH=True):
            return False
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_SET_KEYFRAMES, 'Bake Keyframes...', ID_TAG_GROUP_CONTROL, scaleH=True):
            return False
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_OPEN_MANAGER, 'Open Rokoko Studio Live', ID_TAG_GROUP_CONTROL, scaleH=True):
            return False
        return True


    # Create "Mapping" table for Actor tags
    def GetDDescriptionGroupMappingActor(self, tag, description, singleId):
        # Group for mapping table
        if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_MAPPING_ACTOR, '', ID_TAG_GROUP_MAPPING, numColumns=3, defaultOpen=True):
            return False

        # Mapping buttons (and hip height)
        # Row 1
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_GUESS_RIG, 'Auto Detect Rig', ID_TAG_GROUP_MAPPING_ACTOR, scaleH=True):
            return False
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_RIG_PRESET, 'Presets...', ID_TAG_GROUP_MAPPING_ACTOR, scaleH=True):
            return False
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_ADD_RIG_PRESET, 'Save Preset...', ID_TAG_GROUP_MAPPING_ACTOR, scaleH=True):
            return False
        # Row 2
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_STORE_TPOSE, 'Set as T-Pose', ID_TAG_GROUP_MAPPING_ACTOR, scaleH=True):
            return False
        if not GetDDescriptionCreateReal(tag, description, singleId, ID_TAG_ACTOR_HIP_HEIGHT, 'Hip Height', ID_TAG_GROUP_MAPPING_ACTOR, anim=False, slider=False, valDefault=0.0, valMax=9999.0, unit=c4d.DESC_UNIT_METER):
            return False
        if not GetDDescriptionCreateString(tag, description, singleId, ID_TAG_DUMMY, '', ID_TAG_GROUP_MAPPING_ACTOR, scaleH=True): # TODO WTF?!?! Without scaling the button above is only half active!!!
            return False
        # Row 3
        if tag[ID_TAG_ACTOR_HIP_HEIGHT] == 0.0:
            if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_MAPPING_ACTOR_HIP_HEIGHT_WARNING, '', ID_TAG_GROUP_MAPPING, numColumns=1, defaultOpen=True):
                return False
            if not GetDDescriptionCreateString(tag, description, singleId, ID_TAG_HIP_HEIGHT_WARNING, 'Hip Height is zero, character will be locked in place.', ID_TAG_GROUP_MAPPING_ACTOR_HIP_HEIGHT_WARNING):
                return False

        # Create groups for different body parts in mapping table
        if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_MAPPING_ACTOR_SUIT, 'Smartsuit Pro', ID_TAG_GROUP_MAPPING, numColumns=1, defaultOpen=True):
            return False
        if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_MAPPING_ACTOR_GLOVE_LEFT, 'Smartglove Left', ID_TAG_GROUP_MAPPING, numColumns=1, defaultOpen=True):
            return False
        if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_MAPPING_ACTOR_GLOVE_RIGHT, 'Smartglove Right', ID_TAG_GROUP_MAPPING, numColumns=1, defaultOpen=True):
            return False

        # Create the actual mapping table with body parts assigned to above groups
        for nameInStudio, (idxBodyPart, nameDisplay, device, _, _, _, _, _) in STUDIO_NAMES_TO_GUESS.items():
            if device == 1:
                group = ID_TAG_GROUP_MAPPING_ACTOR_SUIT
            elif device == 6:
                group = ID_TAG_GROUP_MAPPING_ACTOR_GLOVE_LEFT
            elif device == 10:
                group = ID_TAG_GROUP_MAPPING_ACTOR_GLOVE_RIGHT
            if not GetDDescriptionCreateLink(tag, description, singleId, ID_TAG_BASE_RIG_LINKS + idxBodyPart, nameDisplay, group):
                return False
        return True


    # Create "Mapping" table for Face tags
    def GetDDescriptionGroupMappingFace(self, tag, description, singleId):
        # Group for mapping table
        if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_MAPPING_FACE, '', ID_TAG_GROUP_MAPPING, numColumns=3, defaultOpen=True):
            return False

        # Mapping buttons
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_GUESS_FACE_POSES, 'Auto Detect Poses', ID_TAG_GROUP_MAPPING_FACE, scaleH=True):
            return False
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_FACE_PRESET, 'Presets...', ID_TAG_GROUP_MAPPING_FACE, scaleH=True):
            return False
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_ADD_FACE_PRESET, 'Save Preset...', ID_TAG_GROUP_MAPPING_FACE, scaleH=True):
            return False

        # Create the actual mapping table
        for nameInStudio, (idxPose, nameDisplay, _, _, _, _) in FACE_POSE_NAMES.items():
            if not GetDDescriptionCreateString(tag, description, singleId, ID_TAG_BASE_FACE_POSES + idxPose, nameDisplay, ID_TAG_GROUP_MAPPING, static=False):
                return False
        return True


    # Create "Mapping" Description tab for Actor or Face tags
    def GetDDescriptionGroupMapping(self, tag, description, singleId):
        if tag[ID_TAG_RIG_TYPE] is None:
            return True

        # Tab group
        if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_MAPPING, 'Mapping', 0, numColumns=1, defaultOpen=True):
            return False

        # Create mapping table depending on tag type
        if tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR:
            return self.GetDDescriptionGroupMappingActor(tag, description, singleId)
        elif tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR_FACE:
            return self.GetDDescriptionGroupMappingFace(tag, description, singleId)
        return True


    # Create "Info" Description tab
    def GetDDescriptionGroupEntityInfo(self, tag, description, singleId):
        # Tab group
        if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_ENTITY_INFO, 'Info', 0, numColumns=1, defaultOpen=True):
            return False

        if not GetDDescriptionCreateString(tag, description, singleId, ID_TAG_ENTITY_STATUS, 'Entity Status  ', ID_TAG_GROUP_ENTITY_INFO):
            return False
        if not GetDDescriptionCreateString(tag, description, singleId, ID_TAG_ENTITY_NAME, 'Entity Name  ', ID_TAG_GROUP_ENTITY_INFO):
            return False
        if not GetDDescriptionCreateVector(tag, description, singleId, ID_TAG_ENTITY_COLOR, 'Entity Color', ID_TAG_GROUP_ENTITY_INFO, color=True, anim=False):
            return False
        # TODO: Later to be moved to group mapping, so motion data transfer can be enabled/disabled per Suit or Glove
        if tag[ID_TAG_RIG_TYPE] is not None and tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR:
            if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_ENTITY_INFO_ACTOR, '', ID_TAG_GROUP_ENTITY_INFO, numColumns=3, defaultOpen=True):
                return False
            if not GetDDescriptionCreateBool(tag, description, singleId, ID_TAG_ACTOR_MAP_BODY, 'Suit', ID_TAG_GROUP_ENTITY_INFO_ACTOR, anim=False, valDefault=True):
                return False
            if not GetDDescriptionCreateBool(tag, description, singleId, ID_TAG_ACTOR_MAP_HAND_LEFT, 'Glove Left', ID_TAG_GROUP_ENTITY_INFO_ACTOR, anim=False, valDefault=True):
                return False
            if not GetDDescriptionCreateBool(tag, description, singleId, ID_TAG_ACTOR_MAP_HAND_RIGHT, 'Glove Right', ID_TAG_GROUP_ENTITY_INFO_ACTOR, anim=False, valDefault=True):
                return False
        return True


    # C4D calls GetDDescription() to request the Description of tag's parameters.
    # It does so for example to layout the Attribute Manager.
    # The Description of Hokoko tag's parameters is dynamically created here
    # (mainly ignoring the resource file system for reduced turnaround times during development).
    def GetDDescription(self, node, description, flags):
        if not description.LoadDescription(node.GetType()):
            return False
        singleId = description.GetSingleDescID()

        # Create the four parameter groups (tabs in Attribute Manager)
        if not self.GetDDescriptionGroupMain(node, description, singleId):
            return False
        if not self.GetDDescriptionGroupControl(node, description, singleId):
            return False
        if not self.GetDDescriptionGroupMapping(node, description, singleId):
            return False
        if not self.GetDDescriptionGroupEntityInfo(node, description, singleId):
            return False

        # Description successfully created
        return True, flags | c4d.DESCFLAGS_DESC_LOADED


    # C4D calls GetDEnabling() to determine if a Description parameter is enabled.
    def GetDEnabling(self, node, id, t_data, flags, itemdesc):
        id = id[0].id # incoming is DescID, we need only the numerical id

        # States and flags influencing
        live = g_thdListener._receive
        dataValid = node[ID_TAG_VALID_DATA] == 1
        dataSetIsLive = False
        idConnected = GetConnectedDataSetId()
        idDataSet = node[ID_TAG_DATA_SET]
        isOnlySelected = node.GetDocument().GetActiveTag() == node
        if idConnected != -1 and idConnected == idDataSet:
            dataSetIsLive = True

        # Decode parameter
        if id == ID_TAG_RIG_TYPE:
            return node[ID_TAG_EXECUTE_MODE] == 0 # tag type may not be changed if execution is enabled (in any form)

        # First/last frame index sliders
        elif id == ID_TAG_DATA_SET_FIRST_FRAME:
            return dataValid and not live and not dataSetIsLive
        elif id == ID_TAG_DATA_SET_LAST_FRAME:
            return dataValid and not live and not dataSetIsLive

        # Control buttons
        elif id == ID_TAG_BUTTON_PLAY:
            return dataValid or live and isOnlySelected
        elif id == ID_TAG_BUTTON_SET_KEYFRAMES:
            return dataValid and not live and not dataSetIsLive and isOnlySelected
        elif id == ID_TAG_BUTTON_GO_TO_TPOSE:
            return not live
        elif id == ID_TAG_OPEN_MANAGER_ON_PLAY:
            return not live

        # Actor buttons
        elif id == ID_TAG_BUTTON_GUESS_RIG:
            return not live
        elif id == ID_TAG_BUTTON_RIG_PRESET:
            return not live
        elif id == ID_TAG_BUTTON_STORE_TPOSE:
            return not live
        # Actor properties
        elif id == ID_TAG_ACTOR_HIP_HEIGHT:
            return not live and node[ID_TAG_ACTOR_HAS_HIP] == True
        # Actor mapping table
        elif id >= ID_TAG_BASE_RIG_LINKS and id < (ID_TAG_BASE_RIG_LINKS + len(STUDIO_NAMES_TO_GUESS)):
            return not live

        # Face buttons
        elif id == ID_TAG_BUTTON_GUESS_FACE_POSES:
            return not live
        elif id == ID_TAG_BUTTON_FACE_PRESET:
            return not live
        # Face mapping table
        elif id >= ID_TAG_BASE_FACE_POSES and id < (ID_TAG_BASE_FACE_POSES + len(FACE_POSE_NAMES)):
            return not live

        # Meta data in entity info
        # Currently these checkboxes only indicate the existence of the body parts
        elif id == ID_TAG_ACTOR_MAP_BODY:
            bcDataSet = GetDataSetFromId(idDataSet)
            idxActor = node[ID_TAG_ACTOR_INDEX]
            if bcDataSet is not None and idxActor is not None and idxActor < len(bcDataSet[ID_BC_DATASET_ACTORS]):
                return bcDataSet[ID_BC_DATASET_ACTORS][idxActor][ID_BC_ENTITY_HAS_SUIT] == 1
            else:
                return False
        elif id == ID_TAG_ACTOR_MAP_HAND_LEFT:
            bcDataSet = GetDataSetFromId(idDataSet)
            idxActor = node[ID_TAG_ACTOR_INDEX]
            if bcDataSet is not None and idxActor is not None and idxActor < len(bcDataSet[ID_BC_DATASET_ACTORS]):
                return bcDataSet[ID_BC_DATASET_ACTORS][idxActor][ID_BC_ENTITY_HAS_GLOVE_LEFT] == 1
            else:
                return False
        elif id == ID_TAG_ACTOR_MAP_HAND_RIGHT:
            bcDataSet = GetDataSetFromId(idDataSet)
            idxActor = node[ID_TAG_ACTOR_INDEX]
            if bcDataSet is not None and idxActor is not None and idxActor < len(bcDataSet[ID_BC_DATASET_ACTORS]):
                return bcDataSet[ID_BC_DATASET_ACTORS][idxActor][ID_BC_ENTITY_HAS_GLOVE_RIGHT] == 1
            else:
                return False

        # Currently not reflected in UI
        elif id == ID_TAG_SELECTED_IN_MANAGER:
            return dataValid

        # All other are permanently enabled
        return True


    # Connect the selected data set in listener thread,
    # resulting in a data queue with data set's motioon data inside listener thread.
    def ConnectDataSet(self, tag, idDataSet):
        bcDataSet = GetDataSetFromId(idDataSet)

        # If data set was not found or is a live connection, then there's nothing to do.
        # The data queue for live connection in listener thread has alread been created upon connection.
        if bcDataSet is None or bcDataSet[ID_BC_DATASET_TYPE] == 0:
            return

        # Data sets can be connected multiple times.
        # If it has been connected before, simply nothing happens.
        g_thdListener.ConnectDataSet(bcDataSet)


    # C4D calls SetDParameter() to change a parameter.
    # The call happens during the process and allows to interfere with the
    # parameter change in whatever way.
    # During this function the parameter still has its old value in tag's BaseContainer and
    # the new value is in t_data
    def SetDParameter(self, node, id, t_data, flags):
        id = id[0].id
        if id == ID_TAG_ACTORS:
            # The entity selection combo box (actors, faces, props,...) allows
            # to select an entity either by name or by index.

            # If there is a valifd data set belonging to current selection
            bcDataSet = GetDataSetFromId(node[ID_TAG_DATA_SET])
            if bcDataSet is not None:
                # Get enitites container for type of tag
                rigType = node[ID_TAG_RIG_TYPE]
                idEntitiesBc = RigTypeToEntitiesBcId(rigType)

                # Invalidate entity index, do not cause SetDParameter
                node.GetDataInstance().SetInt32(ID_TAG_ACTOR_INDEX, -1)

                # If there are entities of tag's type, try to find a name match
                setByName = False
                bcEntities = bcDataSet.GetContainerInstance(idEntitiesBc)
                if bcEntities is not None:
                    # Iterate all entities and try name match
                    for idxEntity, _ in bcEntities:
                        bcEntity = bcEntities.GetContainerInstance(idxEntity)
                        name = bcEntity[ID_BC_ENTITY_NAME]
                        if MyHash(name) != t_data:
                            continue

                        # Entity found by name, store its index (which will be the effective way to address the actor)
                        node[ID_TAG_ACTOR_INDEX] = idxEntity
                        setByName = True
                        break

                # If the actor was not found by name, assume the new value to be an actor index.
                # This will also preserve an actor's selection by name,
                # in case character is temporarily not available.
                if not setByName:
                    node[ID_TAG_ACTOR_INDEX] = t_data

        # Meta data parameters can unfortunately not be hidden that easily,
        # as I'd like to have them available in Xpresso (without further ado).
        # Thus these are simply locked constant
        # (we ignore the new value and declare the "set process" as successfully finished).
        elif id == ID_TAG_ACTOR_MAP_BODY and (flags & c4d.DESCFLAGS_SET_USERINTERACTION):
            return True, flags | c4d.DESCFLAGS_SET_PARAM_SET
        elif id == ID_TAG_ACTOR_MAP_HAND_LEFT and (flags & c4d.DESCFLAGS_SET_USERINTERACTION):
            return True, flags | c4d.DESCFLAGS_SET_PARAM_SET
        elif id == ID_TAG_ACTOR_MAP_HAND_RIGHT and (flags & c4d.DESCFLAGS_SET_USERINTERACTION):
            return True, flags | c4d.DESCFLAGS_SET_PARAM_SET
        elif id == ID_TAG_ENTITY_COLOR and (flags & c4d.DESCFLAGS_SET_USERINTERACTION):
            return True, flags | c4d.DESCFLAGS_SET_PARAM_SET

        # Have C4D handle all the rest of parameter changes
        # (which leads to the value stored in tag's BaseContainer)
        return True, flags | c4d.DESCFLAGS_SET_NONE


    # C4D calls Execute() during execution (or evaluation) of the scene.
    # Here we actually move around the objects (under certain conditions...)
    def Execute(self, tag, doc, op, bt, priority, flags):
        # If not activated via an execute flag or if data is not valid
        if tag[ID_TAG_EXECUTE_MODE] == 0 or not tag[ID_TAG_VALID_DATA]:
            return c4d.EXECUTIONRESULT_OK # do nothing, tag is passive

        # Not supposed to happen...
        if self._funcExecute is None:
            return c4d.EXECUTIONRESULT_OK # do nothing, tag is passive

        # Get dispatched frame index, otherwise leave
        idxFrame = self._queueReceive.GetFrameIdx(tag)
        if idxFrame is None:
            return c4d.EXECUTIONRESULT_OK # do nothing, tag is passive

        # Get actual motion data frame from data queue in listener thread
        data = g_thdListener.GetFrame(tag[ID_TAG_DATA_SET], idxFrame)
        if data is None:
            return c4d.EXECUTIONRESULT_OK # do nothing, tag is passive

        # Start actual execution based on tag's type
        # See ExecuteActor(), ExecuteFace() and ExecuteProp() below
        return self._funcExecute(tag, data)


    # Auto detect mapping of joints based on a given "string table".
    # By default it uses the one provided in rokoko_rig_tables.
    # Function results in tag's mapping table being reinitialized (with all consequences).
    # TODO: Cleanup, merge with face detection code
    def DetectRig(self, tag, tableBodyParts=STUDIO_NAMES_TO_GUESS):
        detectedRig = {}

        if tag is None:
            return detectedRig
        objRoot = tag.GetObject()
        if objRoot is None:
            return detectedRig

        hasBody = False
        hasHip = False
        hasHandLeft = False
        hasHandRight = False

        # Flush mapping table
        for (idxBodyPart, _, _, _, _, _, _, _) in STUDIO_NAMES_TO_GUESS.values():
            tag[ID_TAG_BASE_RIG_LINKS + idxBodyPart] = None

        # Iterate all objects of the rig (yes, all, not only joints)
        for obj in iter_objs(objRoot):
            objName = obj.GetName()
            objName = objName.lower()

            # Loop table with body part strings and see if joint object name matches
            for nameStudio, (idxBodyPart, nameDisplay, device, namesMain, namesInclude, namesExclude, namesSideInclude, namesSideExclude) in tableBodyParts.items():
                # namesMain contains multiple lists of strings
                # At least one list needs to be matched completely.
                hitMain = False
                for namesNeeded in namesMain:
                    hitMain = True
                    for name in namesNeeded:
                        if name not in objName:
                            hitMain = False
                            break
                    if hitMain:
                        break
                # If no list of strings matched completely, check next entry
                if not hitMain:
                    continue

                # nameInclude is a list of string from which at least needs to match
                hitInclude = False
                for nameInclude in namesInclude:
                    if nameInclude in objName:
                        hitInclude = True
                        break
                # If no string matched, check next entry
                if not hitInclude and len(namesInclude) > 0:
                    continue

                # namesExclude is a list of strings, which must not appear in pose name
                hitExclude = False
                for nameExclude in namesExclude:
                    if nameExclude in objName:
                        hitExclude = True
                        break
                # If any string matched, check next entry
                if hitExclude:
                    continue

                # For side detection, it's supposed to be enough to only mark
                # joints of one side with a label (e.g. "left", but right side has no side label at all).

                # namesSideInclude is a list of strings, which, if matched, would assign the object to a side.
                # One match from the list is enough to decide the side.
                hitSideInclude = False
                hitSideExclude = False
                for nameSideInclude in namesSideInclude:
                    if nameSideInclude in objName:
                        hitSideInclude = True
                        break
                # If no match in side include list
                if not hitSideInclude:
                    # Side not decided yet, check absence of strings in exclude list
                    # namesSideExclude is a list of strings, which may not appear in pose name.
                    for nameSideExclude in namesSideExclude:
                        if nameSideExclude in objName:
                            hitSideExclude = True
                            break
                    # If any string matched, side of object is undecided, while string table expects a side
                    if hitSideExclude:
                        continue

                # Joint match

                # If body part has been stored previously, continue with next entry to check for further matches
                # (e.g. multiple spine joints (which are not part of current Studio motion data) could work this way)
                if nameStudio in detectedRig:
                    continue

                # Store joint object link in tag's parameters
                detectedRig[nameStudio] = (idxBodyPart, obj, objName, device)
                tag[ID_TAG_BASE_RIG_LINKS + idxBodyPart] = obj

                # Depending on device (suit, glove,...) note existence of certain body parts.
                if device == 1:
                    hasBody = True
                elif device == 6:
                    hasHandLeft = True
                elif device == 10:
                    hasHandRight = True
                break

        # If a hip joint was found
        if 'hip' in detectedRig:
            hasHip = True

            # Get local matrix (relative to parent) of hip joint
            mlHip = detectedRig['hip'][1].GetMl()

            axis = 1
            if round(mlHip.off.y, 0) == round(mlHip.off.z, 0) == 0:
                axis = 0
            elif round(mlHip.off.x, 0) == round(mlHip.off.y, 0) == 0:
                axis = 2
            hipHeight = detectedRig['hip'][1].GetMl().off[axis]
            tag[ID_TAG_ACTOR_HIP_HEIGHT] = abs(hipHeight)

        # Store meta information about body parts
        # Currently it may seem as if body and hands are duplicate.
        # This is in anticipation of an user option to manually disable
        # motion of these parts separately.
        tag[ID_TAG_ACTOR_HAS_BODY] = hasBody
        tag[ID_TAG_ACTOR_HAS_HIP] = hasHip
        tag[ID_TAG_ACTOR_HAS_HAND_LEFT] = hasHandLeft
        tag[ID_TAG_ACTOR_HAS_HAND_RIGHT] = hasHandRight
        tag[ID_TAG_ACTOR_MAP_BODY] = hasBody
        tag[ID_TAG_ACTOR_MAP_HAND_LEFT] = hasHandLeft
        tag[ID_TAG_ACTOR_MAP_HAND_RIGHT] = hasHandRight

        # Lock against further auto detection
        tag[ID_TAG_ACTOR_RIG_DETECTED] = True

        # Mark tag's Description dirty, the result may influence on
        # availability of certain parameters.
        tag.SetDirty(c4d.DIRTYFLAGS_DESCRIPTION)
        return detectedRig


    # Calculates the T-Pose matrices for all joints in tag's mapping table.
    # In order to speed up Execute() a bit, the matrices are not stored directly,
    # but calculations independent of actual motion get cached here.
    def SetTPose(self, tag):
        objRoot = tag.GetObject()
        if objRoot is None:
            return

        # If tag is assigned directtly to hip, we lack a root object.
        # In this case a unity matrix as root matrix.
        objHip = tag[ID_TAG_BASE_RIG_LINKS + 0]
        if objHip != objRoot:
            mgRootTPose = objRoot.GetMg()
        else:
            mgRootTPose = c4d.Matrix()

        # Store global matrix of root object as is
        tag[ID_TAG_ROOT_MATRIX] = mgRootTPose

        # Iterate all body parts
        for nameInStudio, (idx, _, _, _, _, _, _, _) in STUDIO_NAMES_TO_GUESS.items():
            obj = tag[ID_TAG_BASE_RIG_LINKS + idx]

            # Skip if no joint assigned
            if obj is None:
                continue

            # Revert transformation of root object (as if character was standing at world origin)
            # and rotate into Studio character orientation
            mgJoint = obj.GetMg()
            mgBodyPartTPose = MR_Y180 * ~mgRootTPose * mgJoint
            tag[ID_TAG_BASE_RIG_MATRICES + idx] = mgBodyPartTPose

            # In Execute() we need the T-Pose in "pretransformed" form
            # It's a bit hard to see, with the entire calculation ripped apart into
            # this preparation step and the step in Execute().
            # Maybe also consider look into the code of the Blender plugin, where it's implemented in one function:
            # https://github.com/Rokoko/rokoko-studio-live-blender/blob/85f0569cc08fdee405f6c17bcb4e9c52804e43fa/core/animations.py#L88-L216
            #
            # Both multiplications have their counterpart in Execute()
            #
            # a) Revert transformation of root object. Indeed once more, as the character is supposed to
            #    move and rotate with its root. So this transformation will come back in (together with any
            #    changes the user did to the root) in Execute() in form of the global matrix of
            #    the then current actual root.
            # b) Transform (rotate actually) with Studio T-Pose. Together with the multiplication
            #    of the current live data rotation this results basically in a rotation needed to
            #    rotate Studio T-Pose into current position (or the difference between both rotations,
            mgBodyPartTPosePretransformed = g_studioTPose[nameInStudio] * (~mgRootTPose * mgBodyPartTPose)
            tag[ID_TAG_BASE_RIG_MATRICES_PRETRANSFORMED + idx] = mgBodyPartTPosePretransformed

        # Lock against further auto detection
        tag[ID_TAG_ACTOR_TPOSE_STORED] = True


    # Creates a "T-Pose dictionary".
    # For all joints set in tag's mapping table,
    # store object reference, object name and T-Pose matrices (normal and pretransformed).
    # Entries are referred to by their Studio names.
    #
    # This dictionary serves only a single purpose:
    # Make the code in Execute() simple and a bit faster.
    def PrepareTPoseDict(self, tag):
        if len(g_studioTPose) <= 0:
            return
        self._tPoseTag = {}

        for nameInStudio, (idx, _, _, _, _, _, _, _) in STUDIO_NAMES_TO_GUESS.items():
            obj = tag[ID_TAG_BASE_RIG_LINKS + idx]

            # Skip empty mapping table entries
            if obj is None:
                continue

            # Store information in dictionary
            nameObj = obj.GetName()
            mgBodyPartTPose = tag[ID_TAG_BASE_RIG_MATRICES + idx]
            mgBodyPartTPosePretransformed = tag[ID_TAG_BASE_RIG_MATRICES_PRETRANSFORMED + idx]
            self._tPoseTag[nameInStudio] = (obj, mgBodyPartTPose, nameObj, mgBodyPartTPosePretransformed)


    # Execute() function for Actors
    #
    # Code to calculate offsets and rotations is based on Philipp's nice Blender implementation:
    # https://github.com/Rokoko/rokoko-studio-live-blender/blob/85f0569cc08fdee405f6c17bcb4e9c52804e43fa/core/animations.py#L88-L216
    # In general calculation is a bit simpler compared to Blender, because Rokoko Studio and C4D share
    # basically the same coordinate system (both left handed, while Blender is right handed).
    # Here it is only the orientation of characters, which is different.
    # Essentially just a 180 degree rotation on Y.
    #
    # In order to make up for some performance issues in C4D, the actual implementation is a bit different compared to Blender.
    # There are certain parts of the calculation independent of the actual motion of an actor.
    # In this plugin, these parts are moved out of this function (more important for Execute() of the tag).
    # Instead these calculations are done, when the T-Pose gets stored.
    # See ID_TAG_BASE_RIG_MATRICES_PRETRANSFORMED in rokoko_tag.
    #
    # Another difference is, here it's all calculated with matrices.
    # Mainly because the author of these lines doesn't get comfortable with C4D's quaternion class
    # (not quaternions themselves, only their implementation).
    # TODO: Quaternions probably had the potential to increase performance a bit, so it's definitely worth a try one day.
    #@timing
    def ExecuteActor(self, tag, data):
        # Get actor data from motion data frame
        idxActor = tag[ID_TAG_ACTOR_INDEX]
        dataActor = data['actors'][idxActor]
        dataBody = dataActor['body']
        objRoot = tag.GetObject()
        objHip = tag[ID_TAG_BASE_RIG_LINKS + 0]

        # In case there is no dedicated root object (but Rokoko tag is assigned directly to hip joint),
        # use identity matrix as root matrix
        if objHip != objRoot:
            mgRoot = objRoot.GetMg()
        else:
            mgRoot = c4d.Matrix()

        mgRootTPose = tag[ID_TAG_ROOT_MATRIX]

        ### Rotation

        # Iterate all objects of the rig (well, only those assigned in tag's mapping table)
        for nameInStudio, (obj, _, nameInRig, mRotOffsetRef) in self._tPoseTag.items():
            # Get Studio rotation and convert into C4D transformation matrix
            dataBodyPart = dataBody[nameInStudio]
            mStudioNewPose = JSONQuaternionToMatrix(dataBodyPart['rotation'])

            # Transform the current Studio rotation
            # Apply pretransformed T-Pose matrix
            mFinalRot = mStudioNewPose * mRotOffsetRef

            # While sharing a similarly oriented coordinate system,
            # in C4D characters face forward in the opposite direction.
            # A character in T-Pose will usually look into -Z in T-Pose (while in Rokoko Studio it looks into +Z).

            # Rotate Studio's rotation by 180 degree around Y
            mFinalRot = MR_Y180 * mFinalRot # actually ~MR_Y180 * mFinalRot, but ~MR_Y180 == MR_Y180

            # Reverse the rotation which may have been caused by a rotation of T-Pose's root object
            mFinalRot = ~mgRootTPose * mFinalRot

            # Finally rotate by rigs current root rotation
            mFinalRot = mgRoot * mFinalRot

            # Preserve global position of the joint
            mFinalRot.off = obj.GetMg().off

            obj.SetMg(mFinalRot)

        ### Hip Position
        if 'hip' in self._tPoseTag:
            # Get hip parameters
            objHip, _, nameInRigHip, _ = self._tPoseTag['hip']
            dataBodyPart = dataBody['hip']
            hipHeightStudio = dataActor['dimensions']['hipHeight']
            hipHeightStudioC4D = hipHeightStudio * 100.0
            posStudio = dataBodyPart['position']
            yTPoseHip = tag[ID_TAG_ACTOR_HIP_HEIGHT]

            # Scale hip height by ratio of current actor's hip height and Studio's T-Pose base hip height
            scale = yTPoseHip / hipHeightStudio

            # Calculate hip's y position in C4D
            y = yTPoseHip * (1 + (posStudio['y'] - hipHeightStudio))

            # Merge into relative offset in C4D
            # -x/z due to different orientation of character in C4D
            off = c4d.Vector(-posStudio['x'] * scale,
                             y,
                             -posStudio['z'] * scale)

            # Reverse offset and rotation which may have been caused by T-Pose's root object
            off = ~mgRootTPose * off

            # Scale position with "Project Scale" parameter
            off *= GetProjectScale()

            objHip.SetRelPos(off)
        return c4d.EXECUTIONRESULT_OK


    # Auto detect mapping of face poses based on a given "string table".
    # By default it uses the one provided in rokoko_rig_tables.
    # Function results in tag's mapping table being reinitialized (with all consequences).
    def DetectFacePoses(self, tag, tablePoseNames=FACE_POSE_NAMES):
        detectedPoses = {}

        if tag is None:
            return detectedPoses

        objRoot = tag.GetObject()
        if objRoot is None:
            return detectedPoses

        # Try to find a PoseMorph tag
        tagPoseMorph = objRoot.GetTag(c4d.Tposemorph)
        if tagPoseMorph is None:
            return detectedPoses

        # Flush mapping table
        for (idxInStudio, _, _, _, _, _) in FACE_POSE_NAMES.values():
            tag[ID_TAG_BASE_FACE_POSES + idxInStudio] = ''

        # Iterate all poses of the PoseMorph tag
        for idxMorph in range(1, tagPoseMorph.GetMorphCount()):
            morph = tagPoseMorph.GetMorph(idxMorph)
            nameMorphC4D = morph.GetName()
            nameMorphC4DLower = nameMorphC4D.lower()

            # Loop table with pose name strings and see if pose name matches
            for nameStudio, (idxInStudio, nameDisplay, namesMain, namesExclude, namesSideInclude, namesSideExclude) in tablePoseNames.items():
                # namesMain contains multiple lists of strings
                # At least one list needs to be matched completely.
                hitMain = False
                for namesNeeded in namesMain:
                    hitMain = True
                    for name in namesNeeded:
                        if name not in nameMorphC4DLower:
                            hitMain = False
                            break
                    if hitMain:
                        break
                # If no list of strings matched completely, check next entry
                if not hitMain:
                    continue

                # namesExclude is a list of strings, which must not appear in pose name
                hitExclude = False
                for nameExclude in namesExclude:
                    if nameExclude in nameMorphC4DLower:
                        hitExclude = True
                        break
                # If any string matched, check next entry
                if hitExclude:
                    continue

                # For side detection, it's supposed to be enough to only mark
                # poses of one side with a label (e.g. "left", but right side has no side label at all).
                hitSideInclude = False
                hitSideExclude = False
                # namesSideInclude is a list of strings, which, if matched, would assign the object to a side.
                # One match from the list is enough to decide the side.
                for nameSideInclude in namesSideInclude:
                    if nameSideInclude in nameMorphC4DLower:
                        hitSideInclude = True
                        break
                # If no match in side include list
                if not hitSideInclude:
                    # Side not decided yet, check absence of strings in exclude list
                    # namesSideExclude is a list of strings, which may not appear in pose name.
                    for nameSideExclude in namesSideExclude:
                        if nameSideExclude in nameMorphC4DLower:
                            hitSideExclude = True
                            break
                    # If any string matched, side of pose is undecided, while string table expects a side
                    if hitSideExclude:
                        continue

                # Pose match

                # If pose has been stored previously, continue with next entry to check for further matches
                if nameStudio in detectedPoses:
                    continue

                # Store pose mapping in tag's parameters
                detectedPoses[nameStudio] = (idxMorph, nameMorphC4D)
                tag[ID_TAG_BASE_FACE_POSES + idxInStudio] = nameMorphC4D
                tag[ID_TAG_BASE_MORPH_INDECES + idxInStudio] = idxMorph
                break # continue with next PoseMorph pose

        # Lock against further auto detection
        tag[ID_TAG_ACTOR_FACE_DETECTED] = True


    # Creates the "face morph dictionary".
    # Only morphs set in tag's mapping table are stored in the dictionary.
    #
    # This dictionary serves only a single purpose:
    # Make the code in Execute() simple and a bit faster.
    def PrepareFacePoseDict(self, tag):
        self._facePoses = {} # stores: "morph name in Studio" : "C4D's pose DescID"
        obj = tag.GetObject()
        if obj is None:
            return

        # Find PoseMorph tag (we wouldn't be here if it didn't exist)
        tagPoseMorph = obj.GetTag(c4d.Tposemorph)

        # Collect pose DescIDs
        for nameInStudio, (idxPose, _, _, _, _, _) in FACE_POSE_NAMES.items():
            namePoseC4D = tag[ID_TAG_BASE_FACE_POSES + idxPose]

            # Skip, if no pose assigned in tag's mapping table
            if namePoseC4D is None or len(namePoseC4D) <= 0:
                continue

            # Store DescID in dictionary
            idxMorph = tag[ID_TAG_BASE_MORPH_INDECES + idxPose]
            if idxMorph is not None:
                descIdMorph = tagPoseMorph.GetMorphID(idxMorph)
                self._facePoses[nameInStudio] = descIdMorph


    # Execute() function for Faces
    def ExecuteFace(self, tag, data):
        # Get face data from motion data frame
        idxActor = tag[ID_TAG_ACTOR_INDEX]
        dataFace = data['actors'][idxActor]['face']
        obj = tag.GetObject()
        tagPoseMorph = obj.GetTag(c4d.Tposemorph)

        # Set PoseMorph strength parameters with values received from Studio
        # TODO: Could it be helpful to have some kind of range mapping here?
        for nameInStudio, descIdMorph in self._facePoses.items():
            tagPoseMorph.SetParameter(descIdMorph, float(dataFace[nameInStudio]) / 100.0, c4d.DESCFLAGS_SET_NONE) # in C4D strength is 0.0 to 1.0
        return c4d.EXECUTIONRESULT_OK


    # Execute() function for Props
    def ExecuteProp(self, tag, data):
        # Get prop data from motion data frame
        objProp = tag.GetObject()
        idxProp = tag[ID_TAG_ACTOR_INDEX]
        dataProp = data['props'][idxProp]

        ### Rotation

        # Convert Studio rotation into a C4D transformation matrix
        mPropStudio = JSONQuaternionToMatrix(dataProp['rotation'])

        # While sharing a similarly oriented coordinate system,
        # in C4D characters (and thus also props) face forward in the opposite direction.
        # A character in T-Pose will usually look into -Z in T-Pose (while in Rokoko Studio it looks into +Z).

        # Rotate Studio data by 180 degree around Y
        mFinalRot = MR_Y180 * mPropStudio # actually ~MR_Y180 * mFinalRot, but ~MR_Y180 == MR_Y180

        # Preserve global position of the object (for the moment)
        mFinalRot.off = objProp.GetMg().off

        objProp.SetMg(mFinalRot)

        ### Position

        # Convert absolute global position in Studio into a C4D offset vector
        posStudio = dataProp['position']
        off = c4d.Vector(-posStudio['x'] * 100.0,
                         posStudio['y'] * 100.0,
                         -posStudio['z'] * 100.0)

        # Scale position with "Project Scale" parameter
        off *= GetProjectScale() # Position of prop object relative to parent
        objProp.SetRelPos(off)
        return c4d.EXECUTIONRESULT_OK


    # Reaction to message MSG_MENUPREPARE.
    # C4D sends this message, when the tag gets created by the user via menu.
    # In contrast to Init() (which is called when the tag is created, but not yet inserted into the document)m
    # MSG_MENUPREPARE is sent after the tag has been inserted into the object.
    #
    # Time for some initialization...
    def MessageMenuPrepare(self, tag):
        # Auto detect type of tag based on host object
        rigType = DetermineRigType(tag.GetObject())
        tag.SetParameter(ID_TAG_RIG_TYPE, rigType, c4d.DESCFLAGS_SET_NONE)

        # Prepare combo box content (Type, Data, Actor)
        self.SetRigTypeMenuContainer(tag)
        self.SetDataSetMenuContainer(tag)
        self.SetActorMenuContainer(tag)

        # Type dependend initialization
        if rigType & RIG_TYPE_ACTOR:
            # If not done so yet, auto detect rig mapping
            if not tag[ID_TAG_ACTOR_RIG_DETECTED]:
                self.DetectRig(tag)

            # If not done so yet, store T-Pose
            if not tag[ID_TAG_ACTOR_TPOSE_STORED]:
                self.SetTPose(tag)

            # Update T-Pose dictionary
            self.PrepareTPoseDict(tag)

            # In Execute() use function for Actors
            self._funcExecute = self.ExecuteActor

        elif rigType & RIG_TYPE_ACTOR_FACE:
            # If not done so yet, auto detect pose mapping
            if not tag[ID_TAG_ACTOR_FACE_DETECTED]:
                self.DetectFacePoses(tag)

            # Update face pose dictionary
            self.PrepareFacePoseDict(tag)

            # In Execute() use function for Faces
            self._funcExecute = self.ExecuteFace

        elif rigType & RIG_TYPE_PROP:
            # In Execute() use function for Props
            self._funcExecute = self.ExecuteProp

        # Currently not in use
        elif rigType & RIG_TYPE_LIGHT:
            pass
        elif rigType & RIG_TYPE_CAMERA:
            pass
        elif rigType & RIG_TYPE_UNKNOWN:
            pass
        else:
            pass

        # Register the selected data set in listener thread
        self.ConnectDataSet(tag, tag[ID_TAG_DATA_SET])

        # Announce new tag to Manager dialog
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAGS)


    # Reaction to message MSG_DESCRIPTION_POSTSETPARAMETER.
    # This message is sent after SetDParameter() has happened
    # (so the actual value already changed in tag's BaseContainer)
    #
    # Here we can for example resolve dependencies between multiple parameters.
    def MessagePostSetParameter(self, tag, data):
        id = data['descid'][0].id

        if id >= ID_TAG_BASE_RIG_LINKS and id < ID_TAG_BASE_RIG_LINKS + len(STUDIO_NAMES_TO_GUESS):
            # Mapping table of an Actor was changed
            idxBodyPart = id - ID_TAG_BASE_RIG_LINKS

            #
            if idxBodyPart == STUDIO_NAMES_TO_GUESS['hip'][0]:
                tag[ID_TAG_ACTOR_HAS_HIP] = tag[id] != None

            # The Description needs to be updated afterwards (-> GetDDescription)
            tag.SetDirty(c4d.DIRTYFLAGS_DESCRIPTION)

            # Store T-Pose matrices and update T-Pose dictionary
            self.SetTPose(tag)
            self.PrepareTPoseDict(tag)

        elif id >= ID_TAG_BASE_FACE_POSES and id < ID_TAG_BASE_FACE_POSES + len(FACE_POSE_NAMES):
            # Mapping table of a Face was changed
            # Update face pose dictionary
            self.PrepareFacePoseDict(tag)

        elif id == ID_TAG_DATA_SET:

            idDataSet = tag[ID_TAG_DATA_SET]
            if idDataSet != 0: # if not "None" selected
                # Register data set in listener thread
                self.ConnectDataSet(tag, idDataSet)

                # Initialize first/last frame sliders
                if idDataSet != GetConnectedDataSetId():
                    tag[ID_TAG_DATA_SET_FIRST_FRAME] = 0
                    tag[ID_TAG_DATA_SET_LAST_FRAME] = g_thdListener.GetDataSetSize(idDataSet)
                else:
                    # Live connection has no first or last frame
                    tag[ID_TAG_DATA_SET_FIRST_FRAME] = 0
                    tag[ID_TAG_DATA_SET_LAST_FRAME] = 0

        # Last frame is always at least one frame ahead of first frame
        elif id == ID_TAG_DATA_SET_FIRST_FRAME:
            if tag[ID_TAG_DATA_SET_LAST_FRAME] is not None and tag[ID_TAG_DATA_SET_FIRST_FRAME] >= tag[ID_TAG_DATA_SET_LAST_FRAME]:
                tag[ID_TAG_DATA_SET_LAST_FRAME] = tag[ID_TAG_DATA_SET_FIRST_FRAME] + 1
        elif id == ID_TAG_DATA_SET_LAST_FRAME:
            if tag[ID_TAG_DATA_SET_FIRST_FRAME] is not None and tag[ID_TAG_DATA_SET_LAST_FRAME] <= tag[ID_TAG_DATA_SET_FIRST_FRAME]:
                tag[ID_TAG_DATA_SET_FIRST_FRAME] = tag[ID_TAG_DATA_SET_LAST_FRAME] - 1

        elif id == ID_TAG_ACTOR_HIP_HEIGHT:
            # Change of hip height
            hipHeightNew = tag[ID_TAG_ACTOR_HIP_HEIGHT]
            idxHip = STUDIO_NAMES_TO_GUESS['hip'][0]
            objHip = tag[ID_TAG_BASE_RIG_LINKS + idxHip]

            if objHip is not None: # if there is a hip joint
                # Correct hip's global matrix in T-Pose
                mgHip = tag[ID_TAG_BASE_RIG_MATRICES + idxHip]
                mgHip.off = c4d.Vector(mgHip.off.x, hipHeightNew, mgHip.off.z)
                tag.GetDataInstance().SetMatrix(ID_TAG_BASE_RIG_MATRICES + idxHip, mgHip)

                # Update T-Pose dictionary
                self.PrepareTPoseDict(tag)

        # Now, that all parameter dependencies got resolved,
        # check if any parameter changed, which may have an effect on data validity or changes in meta data
        if id == ID_TAG_RIG_TYPE or id == ID_TAG_DATA_SET or \
           id == ID_TAG_ACTORS or id == ID_TAG_ACTOR_INDEX or \
           id == ID_TAG_VALID_DATA:
            if tag[ID_TAG_VALID_DATA]:
                # Data is valid, update meta data (entity name, color,...)
                rigType = tag[ID_TAG_RIG_TYPE]
                idDataSet = tag[ID_TAG_DATA_SET]
                idxEntity = tag[ID_TAG_ACTOR_INDEX]
                idEntitiesBc = RigTypeToEntitiesBcId(rigType)
                bcDataSet = GetDataSetFromId(idDataSet)

                # Selected data set may be temporarily unavailable (e.g. got disconnected)
                if bcDataSet is not None:
                    bcEntity = bcDataSet.GetContainerInstance(idEntitiesBc).GetContainerInstance(int(idxEntity))

                    # Selected entity may be temporarily unavlaible
                    # (e.g. live stream changed and entity is no longer contained)
                    if bcEntity is not None:
                        tag[ID_TAG_ENTITY_NAME] = bcEntity[ID_BC_ENTITY_NAME]
                        tag[ID_TAG_ENTITY_COLOR] = bcEntity[ID_BC_ENTITY_COLOR]
                        tag[ID_TAG_ACTOR_MAP_BODY] = bcEntity[ID_BC_ENTITY_HAS_SUIT]
                        tag[ID_TAG_ACTOR_MAP_HAND_LEFT] = bcEntity[ID_BC_ENTITY_HAS_GLOVE_LEFT]
                        tag[ID_TAG_ACTOR_MAP_HAND_RIGHT] = bcEntity[ID_BC_ENTITY_HAS_GLOVE_RIGHT]
                        tag[ID_TAG_ENTITY_STATUS] = 'Data valid'
            else:
                tag[ID_TAG_ENTITY_NAME] = ''
                tag[ID_TAG_ENTITY_STATUS] = 'Data not valid'

            # Announce change to Manager dialog
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAG_PARAMS)


    # Reaction to message MSG_GETALLASSETS.
    # This is the first of two messages received during "Save Project with Assets",
    # MSG_MULTI_CLEARSUGGESTEDFOLDER being the other.
    #
    # Here we need to provide C4D with filepath to the motion clip used by the tag (if any).
    # C4D will use this information to copy all referenced assets to the new project folder.
    def MessageGetAllAssets(self, tag, data):
        doc = data['doc']
        flags = data['flags']
        if flags & c4d.ASSETDATA_FLAG_TEXTURESONLY:
            return True

        bcDataSet = GetDataSetFromId(tag[ID_TAG_DATA_SET])
        if bcDataSet is None:
            return True # Skip if no valid data set assigned

        if bcDataSet[ID_BC_DATASET_TYPE] == 0 or bcDataSet.GetId() == GetConnectedDataSetId():
            return True # Skip live connection

        # Resolve filename for local data sets (clips in project library)
        filename = bcDataSet[ID_BC_DATASET_FILENAME]
        if bcDataSet[ID_BC_DATASET_IS_LOCAL]:
            if filename[0] == '.':
                pathDoc = doc.GetDocumentPath()
                filename = filename.replace('.', pathDoc, 1)

        # Provide C4D with filepath to clip
        data['assets'].append({'filename' : filename, 'bl' : tag, 'netRequestOnDemand' : False})


    # Reaction to message MSG_MULTI_CLEARSUGGESTEDFOLDER.
    # This is the second of two messages received during "Save Project with Assets",
    # MSG_GETALLASSETS being the first.
    #
    # After all motion clips have been copied (MSG_GETALLASSETS) to the new project folder,
    # we need new clip entries in project library, referencing the copied clips.
    def MessageClearSuggestedFolder(self, tag):
        idDataSet = tag[ID_TAG_DATA_SET]
        bcDataSet = GetDataSetFromId(idDataSet)
        if bcDataSet is None:  # Skip if no valid data set assigned
            return True

        if bcDataSet[ID_BC_DATASET_TYPE] == 0 or bcDataSet.GetId() == GetConnectedDataSetId():
            return True # Skip live connection

        # Clone the data set
        bcDataSet = bcDataSet.GetClone(c4d.COPYFLAGS_NONE)

        # If the data set was in project library, the old clip reference can be removed
        if bcDataSet[ID_BC_DATASET_IS_LOCAL]:
            RemoveLocalDataSet(idDataSet)

        # Update filename in data set and mark it to be local (in prject library)
        _, bcDataSet[ID_BC_DATASET_FILENAME] = os.path.split(bcDataSet[ID_BC_DATASET_FILENAME])
        bcDataSet[ID_BC_DATASET_IS_LOCAL] = True
        # Update ID of data set
        bcDataSet.SetId(MyHash(bcDataSet[ID_BC_DATASET_NAME] + bcDataSet[ID_BC_DATASET_FILENAME] + str(bcDataSet[ID_BC_DATASET_IS_LOCAL])))

        # Add data set to local library
        AddLocalDataSetBC(bcDataSet)

        # Change the tag to use the freshly created clip
        tag.GetDataInstance()[ID_TAG_DATA_SET] = bcDataSet.GetId()

        # Announce change to Manager dialog
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAGS) # TODO: actually CM_SUBID_MANAGER_UPDATE_TAG_PARAMS should suffice


    # Reaction to message MSG_DOCUMENTINFO.
    # TODO: Re-check, if this is really impossible to receive in MessageData. Would be the better place...
    def MessageDocumentInfo(self, tag, data):
        didId = data['type']

        # We are only interested in messages indicating a change of the active document.
        if didId != c4d.MSG_DOCUMENTINFO_TYPE_LOAD and didId != c4d.MSG_DOCUMENTINFO_TYPE_MERGE and \
           didId != c4d.MSG_DOCUMENTINFO_TYPE_SETACTIVE and didId != c4d.MSG_DOCUMENTINFO_TYPE_UNDO:
           return

        # Announce document change to Manager dialog (it needs to collect tags from new document).
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAGS)


    # Reaction to message MSG_GETCUSTOMICON.
    # With this message C4D requests the icon of the tag for display in e.g. Object or Attribute Manager.
    # In C4D it can be a bit tricky (at least for me) to find out, if a tag was re-assigned to another object.
    # At least not without checking all the time, for example in MSG_CHANGE or MSG_UPDATE.
    # Here in Rokoko Studio Live plugin I (mis-)use MSG_GETCUSTOMICON for this purpose, because C4D requesting
    # a new icon seems to be quite a good indicator for a possible change of tag's type.
    def MessageGetCustomIcon(self, tag, data):
        obj = None
        try: # TODO Andreas: Check exception during tag drag and drop
            obj = tag.GetObject()
        except:
            pass
        # During drag of the tag it may happen, there is no host object (obj is None)
        # I was tempted to simply return with data['filled'] = False in this case.
        # But it leads to the strange situation, that during drag of a tag, the _first_
        # tag in Object Manager shows the plugin's icon (instead of the icon for correct type)
        # until drag is finished.
        # Instead below code lives with fact obj may be None.

        # Size of requested icon
        w = data['w']
        h = data['h']

        # Currently selected type and data set
        rigTypeConfigured = tag.GetDataInstance().GetInt32(ID_TAG_RIG_TYPE)
        dataSetConfigured = tag.GetDataInstance().GetInt32(ID_TAG_DATA_SET)

        # If the host object, the selected type or chosen data set changed...
        if self._lastObj == None or not self._lastObj.IsAlive() or self._lastObj != obj or \
           self._lastRigType != rigTypeConfigured or self._lastDataSet != dataSetConfigured:
            self._iconsValid = False # invalidate icon cache, forcing new icons below

        # Are currently cached icons valid?
        if not self._iconsValid:
            # Check, if currently set type is compatible with type options based on host object
            rigTypeOptions = DetermineRigTypeOptions(obj)
            if (rigTypeOptions & rigTypeConfigured) == 0:
                # Auto detect new type
                rigType = DetermineRigType(obj)
                tag.GetDataInstance().SetInt32(ID_TAG_RIG_TYPE, rigType)
            else:
                # Stay with currently set type
                rigType = tag.GetDataInstance().GetInt32(ID_TAG_RIG_TYPE)

            # Prepare combo box content (Type, Data, Actor)
            self.SetRigTypeMenuContainer(tag)
            self.SetDataSetMenuContainer(tag)
            self.SetActorMenuContainer(tag)

            # Register the selected data set in listener thread
            self.ConnectDataSet(tag, tag[ID_TAG_DATA_SET])

            if rigType & RIG_TYPE_ACTOR:
                # If not done so yet, auto detect rig mapping
                if not tag[ID_TAG_ACTOR_RIG_DETECTED]:
                    self.DetectRig(tag)

                # If not done so yet, store T-Pose
                if not tag[ID_TAG_ACTOR_TPOSE_STORED]:
                    self.SetTPose(tag)

                # Update T-Pose dictionary
                self.PrepareTPoseDict(tag)

                # In Execute() use function for Actors
                self._funcExecute = self.ExecuteActor

                # Provide Actor icon
                icon = c4d.gui.GetIcon(PLUGIN_ID_TAG_ICON_ACTOR)

            elif rigType & RIG_TYPE_ACTOR_FACE:
                # If not done so yet, auto detect pose mapping
                if not tag[ID_TAG_ACTOR_FACE_DETECTED]:
                    self.DetectFacePoses(tag)

                # Update face pose dictionary
                self.PrepareFacePoseDict(tag)

                # In Execute() use function for Faces
                self._funcExecute = self.ExecuteFace

                # Provide Face icon
                icon = c4d.gui.GetIcon(PLUGIN_ID_TAG_ICON_FACE)

            elif rigType & RIG_TYPE_PROP:
                # In Execute() use function for Props
                self._funcExecute = self.ExecuteProp

                # Provide Prop icon
                icon = c4d.gui.GetIcon(PLUGIN_ID_TAG_ICON_PROP)

            elif rigType & RIG_TYPE_LIGHT: # currently not in use
                icon = c4d.gui.GetIcon(PLUGIN_ID_TAG_ICON_LIGHT)
            elif rigType & RIG_TYPE_CAMERA: # currently not in use
                icon = c4d.gui.GetIcon(PLUGIN_ID_TAG_ICON_CAMERA)

            # Should not occur, use plugin logo to raise attention
            elif rigType & RIG_TYPE_UNKNOWN:
                print('ERROR A')
                icon = c4d.gui.GetIcon(PLUGIN_ID_ICON_STUDIO_LIVE)
            else:
                print('ERROR B')
                icon = c4d.gui.GetIcon(PLUGIN_ID_ICON_STUDIO_LIVE)

            # Cache common sizes of the icon
            bmpIcon = icon['bmp']
            bmpIcon.ScaleIt(self._bmpIcon24, 256, True, False)
            bmpIcon.ScaleIt(self._bmpIcon32, 256, True, False)
            bmpIcon.ScaleIt(self._bmpIcon36, 256, True, False)
            bmpIcon.ScaleIt(self._bmpIcon48, 256, True, False)
            bmpIcon.ScaleIt(self._bmpIcon64, 256, True, False)

            self._iconsValid = True
            self._lastRigType = rigType
            self._lastDataSet = dataSetConfigured
            self._lastObj = obj

        # Deliver icon of requested size
        # TODO: This entire caching approach is maybe not really
        #       suited with all those different DPI screens out there.
        #       Instead the sizes should rather be cached on request.
        if w == 24:
            data['bmp'] = self._bmpIcon24
        elif w == 32:
            data['bmp'] = self._bmpIcon32
        elif w == 36:
            data['bmp'] = self._bmpIcon36
        elif w == 48:
            data['bmp'] = self._bmpIcon48
        elif w == 64:
            data['bmp'] = self._bmpIcon64
        else:
            data['bmp'] = self._bmpIcon24
            #print('ERROR: Strange icon size', w)
        data['x'] = 0
        data['y'] = 0
        data['flags'] = c4d.ICONDATAFLAGS_NONE
        data['filled'] = True


    # Reaction to user pressing "Open Rokoko Manager" button in a tag.
    def CommandOpenManager(self):
        c4d.CallCommand(PLUGIN_ID_COMMAND_MANAGER)


    # Reaction to user pressing "Set as T-Pose" button in a tag.
    # Stores T-Pose matrices and updates the T-Pose dictionary.
    def CommandStoreTPose(self, tag):
        self.SetTPose(tag)
        self.PrepareTPoseDict(tag)


    # Reaction to user pressing "Go to T-Pose" button in a tag.
    # Sets rig back into its T-Pose.
    def CommandRestoreTPose(self, tag):
        doc = tag.GetDocument()
        objRoot = tag.GetObject()
        mgRoot = objRoot.GetMg()

        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, objRoot) # one undo on root object is enough

        # Apply all global matrices of joints mapped in T-Pose
        for nameInStudio, (obj, mgTPose, _, _) in self._tPoseTag.items():
            # Stored T-Pose matrices contain already a few transformations, which need to be reversed here
            obj.SetMg(mgRoot * MR_Y180 * mgTPose)

        doc.EndUndo()


    # Reaction to user pressing "Auto Detect Poses" button in a tag.
    # Starts a new auto detection of the joints, populating the mapping table of the tag.
    # Afterwards T-Pose matrices and dictionary are updated.
    def CommandGuessRig(self, tag):
        self.DetectRig(tag)
        self.SetTPose(tag)
        self.PrepareTPoseDict(tag)


    # Reaction to user pressing "Auto Detect Poses" button in a tag.
    # Starts a new auto detection of the pose morphs, populating the mapping table of the tag.
    # Afterwards pose dictionary is updated.
    def CommandGuessFace(self, tag):
        self.DetectFacePoses(tag)
        self.PrepareFacePoseDict(tag)


    # Starts playback of this tag.
    def CommandPlayerStart(self, tag):
        # In case of a Studio connection not delivering a stream, ask to switch to offline player
        live = tag[ID_TAG_DATA_SET] == GetConnectedDataSetId()
        if not live and g_thdListener.GetConnectionStatus() == 2:
            result = c4d.gui.MessageDialog('Currently there is no data incoming from Live connection.\nDisconnect?', c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_YESNOCANCEL)
            if result == c4d.GEMB_R_YES:
                c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_DISCONNECT)
            elif result == c4d.GEMB_R_CANCEL:
                return

        # Register tag as consumer in listener thread.
        g_thdListener.AddTagConsumer(tag.GetNodeData(), tag)

        # Start reception and Player
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_START)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_PLAY, False)

        # Optionally open the Manager dialog and activate the Player tab.
        # Option NOT exposed in UI.
        if tag[ID_TAG_OPEN_MANAGER_ON_PLAY]:
            c4d.CallCommand(PLUGIN_ID_COMMAND_MANAGER)
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_OPEN_PLAYER)


    # Stops playback.
    def CommandPlayerStop(self, tag):
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_STOP)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_EXIT)
        c4d.EventAdd()


    # Reaction to user pressing "Play" button in a tag.
    # Starts or Stops playback of this tag.
    def CommandPlayerStartStop(self, tag):
        if not g_thdListener._receive:
            self.CommandPlayerStart(tag)
        else:
            self.CommandPlayerStop(tag)


    # Reaction to user pressing "Bake..." button in a tag.
    # Opens the "Save Recording" dialog with "baking only" option.
    def CommandBakeKeyframes(self, tag):
        self._dlgBake = DialogSaveRecording(dlgParent=None, tags=[tag], bakingOnly=True)
        self._dlgBake.Open(c4d.DLG_TYPE_ASYNC)


    # Reaction to user pressing "Store Preset" button in a tag of type Face.
    def CommandAddRigPreset(self, tag):
        # Ask user for preset name
        namePreset = c4d.gui.RenameDialog(tag.GetName())
        if namePreset is None or len(namePreset) <= 0:
            return

        # Create preset BaseContainer
        bcRigPresets = GetPrefsContainer(ID_BC_RIG_PRESETS)
        bcPreset = c4d.BaseContainer()
        bcPreset[ID_BC_PRESET_NAME] = namePreset
        bcPreset[ID_BC_PRESET_TYPE] = 0 # rig

        # Store all joint mappings from tag's mapping table in BaseContainer
        for (idxInStudio, _, _, _, _, _, _, _) in STUDIO_NAMES_TO_GUESS.values():
            obj = tag[ID_TAG_BASE_RIG_LINKS + idxInStudio]
            if obj is None:
                continue
            bcPreset[idxInStudio] = obj.GetName()

        # Store the new preset BaseContainer as last
        idxNewPreset = len(bcRigPresets)
        bcRigPresets.SetContainer(idxNewPreset, bcPreset)


    # Apply a rig preset
    def RigPresetApply(self, tag, bcPreset):
        # Build mapping table
        tableBodyParts = {} # the preset will be converted into a dictionary like in rokoko_rig_tables
        for nameStudio, (idxBodyPart, _, device, _, _, _, _, _) in STUDIO_NAMES_TO_GUESS.items():
            nameObj = bcPreset[idxBodyPart]
            if nameObj is None or len(nameObj) <= 0: # skip if body part not mapped
                continue

            # Store joint name in dictionary
            nameObj = nameObj.lower()
            tableBodyParts[nameStudio] = (idxBodyPart, '', device, [[nameObj]], [nameObj], [], [], [])

        # Using above generated table the auto detection fills tag's mapping table
        self.DetectRig(tag, tableBodyParts)

        # After changes to the mapping table, the T-Pose matrices and dictionary need to be updated
        self.SetTPose(tag)
        self.PrepareTPoseDict(tag)


    # Renames a preset
    def PresetRename(self, bcPreset):
        # Ask user for new name
        namePresetNew = c4d.gui.RenameDialog(bcPreset[ID_BC_PRESET_NAME])
        if namePresetNew is None or len(namePresetNew) <= 0:
            return

        # Store new name
        bcPreset[ID_BC_PRESET_NAME] = namePresetNew


    # Deletes a preset
    def PresetDelete(self, bcPresets, idxPreset):
        numPresets = len(bcPresets)

        # Delete preset
        bcPresets.RemoveData(idxPreset)

        # Preset are refereced by index, compact indeces inside of preset BaseContainer
        for idxPresetOld in range(idxPreset + 1, numPresets):
            bcPresets.SetContainer(idxPresetOld - 1, bcPresets.GetContainer(idxPresetOld))
            bcPresets.RemoveData(idxPresetOld)


    # Reaction to user pressing "Presets..." button in a tag of type Actor.
    def CommandPopupRigPresets(self, tag):
        bcRigPresets = GetPrefsContainer(ID_BC_RIG_PRESETS)

        # Create a popup menu BaseContainer
        bcPresetMenu = c4d.BaseContainer()
        if bcRigPresets is not None and len(bcRigPresets) > 0:
            for idx, _ in bcRigPresets:
                bcPreset = bcRigPresets.GetContainerInstance(idx)
                idPresetBase = c4d.FIRST_POPUP_ID + idx * 1000 # Factor 1000: Have plenty space for submenu IDs

                # Submenu per preset
                bcSubMenu = c4d.BaseContainer()
                bcSubMenu.InsData(1, bcPreset[ID_BC_PRESET_NAME])
                bcSubMenu.InsData(idPresetBase + 1, 'Apply')
                bcSubMenu.InsData(idPresetBase + 2, 'Rename')
                bcSubMenu.InsData(idPresetBase + 3, 'Delete')
                bcPresetMenu.SetContainer(idPresetBase, bcSubMenu)
        else:
            bcPresetMenu[c4d.FIRST_POPUP_ID + 999999] = 'No presets available'

        # Show the menu
        result = c4d.gui.ShowPopupDialog(cd=None, bc=bcPresetMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)
        if result == c4d.FIRST_POPUP_ID + 999999 or result == 0:
            return

        # Menu IDs store the preset index with a factor of 1000,
        # to have enough room for submenu command IDs
        idxPreset = (result - c4d.FIRST_POPUP_ID) // 1000
        command = (result - c4d.FIRST_POPUP_ID) % 1000
        bcPreset = bcRigPresets.GetContainerInstance(idxPreset)

        # Decode menu entry clicked on
        if command == 1: # Apply preset
            self.RigPresetApply(tag, bcPreset)
        elif command == 2: # Rename preset
            self.PresetRename(bcPreset)
        elif command == 3: # Delete preset
            self.PresetDelete(bcRigPresets, idxPreset)


    # Reaction to user pressing "Store Preset" button in a tag of type Face.
    def CommandAddFacePreset(self, tag):
        # Ask user for preset name
        namePreset = c4d.gui.RenameDialog(tag.GetName())
        if namePreset is None or len(namePreset) <= 0:
            return

        # Create preset BaseContainer
        bcFacePresets = GetPrefsContainer(ID_BC_FACE_PRESETS)
        bcPreset = c4d.BaseContainer()
        bcPreset[ID_BC_PRESET_NAME] = namePreset
        bcPreset[ID_BC_PRESET_TYPE] = 1 # face

        # Store all pose names from mapping table in BaseContainer
        for (idxInStudio, _, _, _, _, _) in FACE_POSE_NAMES.values():
            namePose = tag[ID_TAG_BASE_FACE_POSES + idxInStudio]
            if namePose is None or len(namePose) <= 0:
                continue
            bcPreset[idxInStudio] = namePose

        # Store the new preset BaseContainer as last
        idxNewPreset = len(bcFacePresets)
        bcFacePresets.SetContainer(idxNewPreset, bcPreset)


    # Apply a face preset
    def FacePresetApply(self, tag, bcPreset):
        # Build mapping table
        tablePoses = {} # the preset will be converted into a dictionary like in rokoko_rig_tables
        for nameStudio, (idxPose, _, _, _, _, _) in FACE_POSE_NAMES.items():
            namePose = bcPreset[idxPose]
            if namePose is None or len(namePose) <= 0: # skip if pose not mapped
                continue

            # Store pose name in dictionary
            namePose = namePose.lower()
            tablePoses[nameStudio] = (idxPose, '', [[namePose]], [], [], [])

        # Using above generated table the auto detection fills tag's mapping table
        self.DetectFacePoses(tag, tablePoses)

        # After changes to the mapping table, the pose dictionary needs to be updated
        self.PrepareFacePoseDict(tag)


    # Reaction to user pressing "Presets..." button in a tag of type Face.
    def CommandPopupFacePresets(self, tag):
        bcFacePresets = GetPrefsContainer(ID_BC_FACE_PRESETS)

        # Create a popup menu BaseContainer
        bcPresetMenu = c4d.BaseContainer()
        if bcFacePresets is not None and len(bcFacePresets) > 0:
            for idx, _ in bcFacePresets:
                bcPreset = bcFacePresets.GetContainerInstance(idx)
                idPresetBase = c4d.FIRST_POPUP_ID + idx * 1000 # Factor 1000: Have plenty space for submenu IDs

                # Submenu per preset
                bcSubMenu = c4d.BaseContainer()
                bcSubMenu.InsData(1, bcPreset[ID_BC_PRESET_NAME])
                bcSubMenu.InsData(idPresetBase + 1, 'Apply')
                bcSubMenu.InsData(idPresetBase + 2, 'Rename')
                bcSubMenu.InsData(idPresetBase + 3, 'Delete')
                bcPresetMenu.SetContainer(idPresetBase, bcSubMenu)
        else:
            bcPresetMenu[c4d.FIRST_POPUP_ID + 999999] = 'No presets available'

        # Show the menu
        result = c4d.gui.ShowPopupDialog(cd=None, bc=bcPresetMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)
        if result == c4d.FIRST_POPUP_ID + 999999 or result == 0:
            return

        # Menu IDs store the preset index with a factor of 1000,
        # to have enough room for submenu command IDs
        idxPreset = (result - c4d.FIRST_POPUP_ID) // 1000
        command = (result - c4d.FIRST_POPUP_ID) % 1000
        bcPreset = bcFacePresets.GetContainerInstance(idxPreset)

        # Decode menu entry clicked on
        if command == 1: # Apply preset
            self.FacePresetApply(tag, bcPreset)
        elif command == 2: # Rename preset
            self.PresetRename(bcPreset)
        elif command == 3: # Delete preset
            self.PresetDelete(bcFacePresets, idxPreset)


    # Reaction to message MSG_DESCRIPTION_COMMAND.
    # In NodeData derived plugins parameters are described via Descriptions.
    # In contrast to widgets in a dialog, parameter access is usually handled in
    # SetDParameter() and GetDParameter(). An exception are buttons in a Description,
    # which need to be handled via MSG_DESCRIPTION_COMMAND.
    def MessageCommand(self, tag, data):
        # Decode command/button ID
        id = data['id'][0].id

        # General command buttons
        if id == ID_TAG_BUTTON_OPEN_MANAGER:
            self.CommandOpenManager()
        elif id == ID_TAG_BUTTON_PLAY:
            self.CommandPlayerStartStop(tag)
        elif id == ID_TAG_BUTTON_SET_KEYFRAMES:
            self.CommandBakeKeyframes(tag)

        # Actor buttons
        elif id == ID_TAG_BUTTON_STORE_TPOSE:
            self.CommandStoreTPose(tag)
        elif id == ID_TAG_BUTTON_GO_TO_TPOSE:
            self.CommandRestoreTPose(tag)
        elif id == ID_TAG_BUTTON_GUESS_RIG:
            self.CommandGuessRig(tag)
        # Actor preset buttons
        elif id == ID_TAG_BUTTON_ADD_RIG_PRESET:
            self.CommandAddRigPreset(tag)
        elif id == ID_TAG_BUTTON_RIG_PRESET:
            self.CommandPopupRigPresets(tag)

        # Face buttons
        elif id == ID_TAG_BUTTON_GUESS_FACE_POSES:
            self.CommandGuessFace(tag)
        # Face preset buttons
        elif id == ID_TAG_BUTTON_ADD_FACE_PRESET:
            self.CommandAddFacePreset(tag)
        elif id == ID_TAG_BUTTON_FACE_PRESET:
            self.CommandPopupFacePresets(tag)


    # Reaction to message PLUGIN_ID_MSG_DATA_CHANGE
    # External event (maybe a change inside Studio's motion data stream,...) causes the need
    # to update things in the tag (currently the contents of the combo boxes).
    def MessageStudioDataChange(self, tag):
        self.SetDataSetMenuContainer(tag)
        self.SetActorMenuContainer(tag)

        # Announce change of tag's parameters to Manager dialog
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAG_PARAMS)


    # Called by C4D to send a message to the tag.
    def Message(self, node, type, data):
        # Decode message type

        # During initialization
        if type == c4d.MSG_MENUPREPARE:
            self.MessageMenuPrepare(node)

        # Description messages
        elif type == c4d.MSG_DESCRIPTION_POSTSETPARAMETER:
            self.MessagePostSetParameter(node, data)
        elif type == c4d.MSG_DESCRIPTION_COMMAND:
            self.MessageCommand(node, data)

        # Other messages
        elif type == c4d.MSG_DOCUMENTINFO:
            self.MessageDocumentInfo(node, data)
        elif type == c4d.MSG_GETCUSTOMICON:
            self.MessageGetCustomIcon(node, data)

        # Custom message
        elif type == PLUGIN_ID_MSG_DATA_CHANGE:
            self.MessageStudioDataChange(node)

        # Support "Save Project with Assets"
        elif type == c4d.MSG_GETALLASSETS:
            self.MessageGetAllAssets(node, data)
        elif type == c4d.MSG_MULTI_CLEARSUGGESTEDFOLDER:
            self.MessageClearSuggestedFolder(node)
        return True


    # Called by C4D, when the tag is being copied.
    # Most importantly one needs to care for member variables of the TagData implementation.
    #
    # Remember a tag inside C4D consists of two class instances,
    # the NodeData derived TagData "plugin" and
    # the BaseList2D derived BaseTag usually existing inside the scene graph.
    #
    # The BaseTag component (snode, dnode) usually is no problem during copy,
    # as it's not overloaded there are no custom member variables. Entire state should be
    # neatly stored inside its BaseContainer.
    def CopyTo(self, dest, snode, dnode, flags, trn):
        # Trigger Manager dialog to rebuild its tag list.
        # The thing is, we don't know about the reason for copy (well, not completely),
        # nor where the copy will end up. For example in case of adding a new undo step,
        # the tag gets copied onto the undo stack. A copy is created, but it does not
        # appear in the scene. So unfortunately we can not inform the Manager directly
        # about the new copy.
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAGS)

        # Initialize member variables of destination TagData
        dest._queueReceive = TagQueue()
        dest._tPoseTag = self._tPoseTag.copy()
        return True
