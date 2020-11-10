import c4d
from rokoko_ids import *
from rokoko_rig_tables import *
from rokoko_utils import *
from rokoko_tag_queue import *
from rokoko_description_utils import *
from rokoko_listener import *
from rokoko_dialog_save_recording import *

g_thdListener = GetListenerThread() # owned by rokoko_listener
g_forceUpdate = False
g_studioTPose = {}
def TagSetGlobalStudioTPose(tPose):
    global g_studioTPose
    g_studioTPose = tPose

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
        bcTag = node.GetDataInstance()
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
        # internal, not exposed in Attribute Manager
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


    def DataSetMenuContainerAdd(self, rigType, bcDataSet, bcMenu):
        idDataSet = bcDataSet.GetId()
        nameDataSet = bcDataSet[ID_BC_DATASET_NAME]
        if rigType & RIG_TYPE_ACTOR and bcDataSet[ID_BC_DATASET_NUM_ACTORS] > 0:
            bcMenu[idDataSet] = '{} ({})'.format(nameDataSet, bcDataSet[ID_BC_DATASET_NUM_ACTORS])
        elif rigType & RIG_TYPE_ACTOR_FACE and bcDataSet[ID_BC_DATASET_NUM_FACES] > 0:
            bcMenu[idDataSet] = '{} ({})'.format(nameDataSet, bcDataSet[ID_BC_DATASET_NUM_FACES])
        elif rigType & RIG_TYPE_LIGHT and bcDataSet[ID_BC_DATASET_NUM_LIGHTS] > 0:
            bcMenu[idDataSet] = '{} ({})'.format(nameDataSet, bcDataSet[ID_BC_DATASET_NUM_LIGHTS])
        elif rigType & RIG_TYPE_CAMERA and bcDataSet[ID_BC_DATASET_NUM_CAMERAS] > 0:
            bcMenu[idDataSet] = '{} ({})'.format(nameDataSet, bcDataSet[ID_BC_DATASET_NUM_CAMERAS])
        elif rigType & RIG_TYPE_PROP and bcDataSet[ID_BC_DATASET_NUM_PROPS] > 0:
            bcMenu[idDataSet] = '{} ({})'.format(nameDataSet, bcDataSet[ID_BC_DATASET_NUM_PROPS])

    def SetDataSetMenuContainer(self, tag):
        description = tag.GetDescription(c4d.DESCFLAGS_DESC_NONE)
        self._dataSets = {}
        bcMenu = c4d.BaseContainer()
        rigType = tag[ID_TAG_RIG_TYPE]
        if rigType is None or rigType == RIG_TYPE_UNKNOWN:
            bcMenu[0] = 'No clips, Rig type unknown!!!'
            tag.SetParameter(ID_TAG_BC_DATASETS, bcMenu, c4d.DESCFLAGS_SET_NONE)
            return
        bcConnected = GetConnectedDataSet()
        if bcConnected is not None:
            self._dataSets[bcConnected.GetId()] = ''
            self.DataSetMenuContainerAdd(rigType, bcConnected, bcMenu)
            bcMenu[2] = ''
        bcDataSetsLocal = GetLocalDataSets()
        for id, bcDataSet in bcDataSetsLocal:
            self._dataSets[bcDataSet.GetId()] = ''
            self.DataSetMenuContainerAdd(rigType, bcDataSet, bcMenu)
        if len(bcMenu) > 2:
            bcMenu[3] = ''
        bcDataSetsGlobal = GetPrefsContainer(ID_BC_DATA_SETS)
        for id, bcDataSet in bcDataSetsGlobal:
            self._dataSets[bcDataSet.GetId()] = ''
            self.DataSetMenuContainerAdd(rigType, bcDataSet, bcMenu)
        idSelectedDataSet = bcMenu.GetData(tag[ID_TAG_DATA_SET])
        if idSelectedDataSet is None:
            bcMenu[4] = ''
            bcMenu[tag[ID_TAG_DATA_SET]] = 'Data not available'
            tag[ID_TAG_ENTITY_COLOR] = c4d.Vector(0.0)
            tag[ID_TAG_ENTITY_NAME] = ''
            tag[ID_TAG_ENTITY_STATUS] = 'Data not valid'
        bcMenu[5] = ''
        bcMenu[0] = 'None'
        tag.SetParameter(ID_TAG_BC_DATASETS, bcMenu, c4d.DESCFLAGS_SET_FORCESET)

    def GetDataSetMenuContainer(self, tag):
        bc = tag.GetDataInstance().GetContainerInstance(ID_TAG_BC_DATASETS)
        if bc is None:
            bc = c4d.BaseContainer()
            bc[0] = 'Error'
        return bc


    def SetRigTypeMenuContainer(self, tag):
        bc = c4d.BaseContainer()
        obj = tag.GetObject()
        if obj is None:
            bc[0xFFFF] = 'Tag not attached'
            tag.SetParameter(ID_TAG_BC_RIG_TYPES, bc, c4d.DESCFLAGS_SET_NONE)
            return
        rigTypeOptions = DetermineRigTypeOptions(obj)
        if rigTypeOptions & RIG_TYPE_ACTOR:
            bc[RIG_TYPE_ACTOR] = 'Actor'
        elif rigTypeOptions & RIG_TYPE_ACTOR_FACE:
            bc[RIG_TYPE_ACTOR_FACE] = 'Face'
        elif rigTypeOptions & RIG_TYPE_LIGHT:
            bc[RIG_TYPE_LIGHT] = 'Light'
        elif rigTypeOptions & RIG_TYPE_CAMERA:
            bc[RIG_TYPE_CAMERA] = 'Camera'
        bc[RIG_TYPE_PROP] = 'Prop'
        tag.SetParameter(ID_TAG_BC_RIG_TYPES, bc, c4d.DESCFLAGS_SET_NONE)

    def GetRigTypeMenuContainer(self, tag):
        bc = tag.GetDataInstance().GetContainerInstance(ID_TAG_BC_RIG_TYPES)
        if bc is None:
            bc = c4d.BaseContainer()
            bc[0xFFFF] = 'Error'
        return bc

    def SetActorMenuContainer(self, tag):
        bcMenu = c4d.BaseContainer()
        rigType = tag[ID_TAG_RIG_TYPE]
        if rigType is None or rigType == RIG_TYPE_UNKNOWN:
            bcMenu[0] = 'No clip, Actor unknown!!!'
            tag.SetParameter(ID_TAG_BC_ACTORS, bcMenu, c4d.DESCFLAGS_SET_NONE)
            tag.SetParameter(ID_TAG_VALID_DATA, False, c4d.DESCFLAGS_SET_NONE)
            return
        idDataSet = tag[ID_TAG_DATA_SET]
        if idDataSet is None or idDataSet == 0:
            bcMenu[tag[ID_TAG_ACTORS]] = 'No clip selected'
            tag.SetParameter(ID_TAG_BC_ACTORS, bcMenu, c4d.DESCFLAGS_SET_NONE)
            tag.SetParameter(ID_TAG_VALID_DATA, False, c4d.DESCFLAGS_SET_NONE)
            return
        bcDataSet = GetDataSetFromId(idDataSet)
        if bcDataSet is None:
            bcMenu[tag[ID_TAG_ACTORS]] = 'Clip not found'
            tag.SetParameter(ID_TAG_BC_ACTORS, bcMenu, c4d.DESCFLAGS_SET_NONE)
            tag.SetParameter(ID_TAG_VALID_DATA, False, c4d.DESCFLAGS_SET_NONE)
            return
        if idDataSet in self._dataSets:
            idEntitiesBc = RigTypeToEntitiesBcId(rigType)
            actorsByIndex = []
            bcEntities = bcDataSet.GetContainerInstance(idEntitiesBc)
            for idxEntity, _ in bcEntities:
                bcEntity = bcEntities.GetContainerInstance(idxEntity)
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
                    name = bcEntity[ID_BC_ENTITY_NAME]
                    bcMenu[MyHash(name)] = '{} (#{})'.format(name, idxEntity)
                    nameByIndex = '#{} - {}'.format(idxEntity, name)
                    actorsByIndex.append((idxEntity, nameByIndex))
            bcMenu[111111] = ''
            for idxEntity, nameByIndex in actorsByIndex:
                bcMenu[idxEntity] = nameByIndex
        idSelectedActor = bcMenu.GetData(tag[ID_TAG_ACTORS])
        if idSelectedActor is None:
            validData = False
            bcMenu[111112] = ''
            bcMenu[tag[ID_TAG_ACTORS]] = 'Not available'
        else:
            validData = True
        tag.SetParameter(ID_TAG_BC_ACTORS, bcMenu, c4d.DESCFLAGS_SET_NONE)
        # TODO: STRANGE!
        tag.GetDataInstance()[ID_TAG_VALID_DATA] = validData
        tag.SetParameter(ID_TAG_VALID_DATA, validData, c4d.DESCFLAGS_SET_FORCESET)

    def GetActorMenuContainer(self, tag):
        bc = tag.GetDataInstance().GetContainerInstance(ID_TAG_BC_ACTORS)
        if bc is None:
            bc = c4d.BaseContainer()
            bc[0xFFFF] = 'Error'
        return bc

    def GetDDescriptionGroupMain(self, tag, description, singleId):
        bcRigTypes = self.GetRigTypeMenuContainer(tag)
        if not GetDDescriptionCreateCombo(tag, description, singleId, ID_TAG_RIG_TYPE, 'Type', c4d.ID_TAGPROPERTIES, bcRigTypes, anim=False, valDefault=0):
            return False
        bcDataSets = self.GetDataSetMenuContainer(tag)
        if not GetDDescriptionCreateCombo(tag, description, singleId, ID_TAG_DATA_SET, 'Stream/Clips', c4d.ID_TAGPROPERTIES, bcDataSets, anim=False, valDefault=0):
            return False
        bcActors = self.GetActorMenuContainer(tag)
        rigType = tag[ID_TAG_RIG_TYPE]
        if rigType is None:
            return True
        labelEntities = RigTypeToEntitiesString(rigType)
        if not GetDDescriptionCreateCombo(tag, description, singleId, ID_TAG_ACTORS, labelEntities, c4d.ID_TAGPROPERTIES, bcActors, anim=False, valDefault=0):
            return False
        if tag[ID_TAG_DATA_SET] in g_thdListener._dataQueues:
            maxFrame = len(g_thdListener._dataQueues[tag[ID_TAG_DATA_SET]])
        else:
            maxFrame = 1
        if not GetDDescriptionCreateLong(tag, description, singleId, ID_TAG_DATA_SET_FIRST_FRAME, 'First Frame', c4d.ID_TAGPROPERTIES, anim=False, valDefault=0, valMax=maxFrame-1, sliderMax=maxFrame-1):
            return False
        if not GetDDescriptionCreateLong(tag, description, singleId, ID_TAG_DATA_SET_LAST_FRAME, 'Last Frame', c4d.ID_TAGPROPERTIES, anim=False, valDefault=maxFrame, valMin=1, sliderMin=1, valMax=maxFrame, sliderMax=maxFrame):
            return False
        return True

    def GetDDescriptionGroupControl(self, tag, description, singleId):
        if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_CONTROL, 'Control', 0, numColumns=2, defaultOpen=True):
            return False
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

    def GetDDescriptionGroupMappingActor(self, tag, description, singleId):
        if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_MAPPING_ACTOR, '', ID_TAG_GROUP_MAPPING, numColumns=3, defaultOpen=True):
            return False
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_GUESS_RIG, 'Auto Detect Rig', ID_TAG_GROUP_MAPPING_ACTOR, scaleH=True):
            return False
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_RIG_PRESET, 'Presets...', ID_TAG_GROUP_MAPPING_ACTOR, scaleH=True):
            return False
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_ADD_RIG_PRESET, 'Save Preset...', ID_TAG_GROUP_MAPPING_ACTOR, scaleH=True):
            return False
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_STORE_TPOSE, 'Set as T-Pose', ID_TAG_GROUP_MAPPING_ACTOR, scaleH=True):
            return False
        if not GetDDescriptionCreateReal(tag, description, singleId, ID_TAG_ACTOR_HIP_HEIGHT, 'Hip Height', ID_TAG_GROUP_MAPPING_ACTOR, anim=False, slider=False, valDefault=0.0, valMax=9999.0, unit=c4d.DESC_UNIT_METER):
            return False
        if not GetDDescriptionCreateString(tag, description, singleId, ID_TAG_DUMMY, '', ID_TAG_GROUP_MAPPING_ACTOR, scaleH=True): # TODO WTF?!?! Without scaling the button above is only half active!!!
            return False
        if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_MAPPING_ACTOR_SUIT, 'Smartsuit Pro', ID_TAG_GROUP_MAPPING, numColumns=1, defaultOpen=True):
            return False
        if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_MAPPING_ACTOR_GLOVE_LEFT, 'Smartglove Left', ID_TAG_GROUP_MAPPING, numColumns=1, defaultOpen=True):
            return False
        if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_MAPPING_ACTOR_GLOVE_RIGHT, 'Smartglove Right', ID_TAG_GROUP_MAPPING, numColumns=1, defaultOpen=True):
            return False
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

    def GetDDescriptionGroupMappingFace(self, tag, description, singleId):
        if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_MAPPING_FACE, '', ID_TAG_GROUP_MAPPING, numColumns=3, defaultOpen=True):
            return False
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_GUESS_FACE_POSES, 'Auto Detect Poses', ID_TAG_GROUP_MAPPING_FACE, scaleH=True):
            return False
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_FACE_PRESET, 'Presets...', ID_TAG_GROUP_MAPPING_FACE, scaleH=True):
            return False
        if not GetDDescriptionCreateButton(tag, description, singleId, ID_TAG_BUTTON_ADD_FACE_PRESET, 'Save Preset...', ID_TAG_GROUP_MAPPING_FACE, scaleH=True):
            return False
        for nameInStudio, (idxPose, nameDisplay, _, _, _, _) in FACE_POSE_NAMES.items():
            if not GetDDescriptionCreateString(tag, description, singleId, ID_TAG_BASE_FACE_POSES + idxPose, nameDisplay, ID_TAG_GROUP_MAPPING, static=False):
                return False
        return True

    def GetDDescriptionGroupMapping(self, tag, description, singleId):
        if tag[ID_TAG_RIG_TYPE] is None:
            return True
        if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_MAPPING, 'Mapping', 0, numColumns=1, defaultOpen=True):
            return False
        if tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR:
            return self.GetDDescriptionGroupMappingActor(tag, description, singleId)
        elif tag[ID_TAG_RIG_TYPE] & RIG_TYPE_ACTOR_FACE:
            return self.GetDDescriptionGroupMappingFace(tag, description, singleId)
        return True

    def GetDDescriptionGroupEntityInfo(self, tag, description, singleId):
        if not GetDDescriptionCreateGroup(tag, description, singleId, ID_TAG_GROUP_ENTITY_INFO, 'Info', 0, numColumns=1, defaultOpen=True):
            return False
        if not GetDDescriptionCreateString(tag, description, singleId, ID_TAG_ENTITY_STATUS, 'Entity Status  ', ID_TAG_GROUP_ENTITY_INFO):
            return False
        if not GetDDescriptionCreateString(tag, description, singleId, ID_TAG_ENTITY_NAME, 'Entity Name  ', ID_TAG_GROUP_ENTITY_INFO):
            return False
        if not GetDDescriptionCreateVector(tag, description, singleId, ID_TAG_ENTITY_COLOR, 'Entity Color', ID_TAG_GROUP_ENTITY_INFO, color=True, anim=False):
            return False
        # TODO Later to be moved to group mapping, so it can be enabled/disabled
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

    def GetDDescription(self, node, description, flags):
        if not description.LoadDescription(node.GetType()):
            return False
        singleId = description.GetSingleDescID()
        if not self.GetDDescriptionGroupMain(node, description, singleId):
            return False
        if not self.GetDDescriptionGroupControl(node, description, singleId):
            return False
        if not self.GetDDescriptionGroupMapping(node, description, singleId):
            return False
        if not self.GetDDescriptionGroupEntityInfo(node, description, singleId):
            return False
        return True, flags | c4d.DESCFLAGS_DESC_LOADED

    def GetDEnabling(self, node, id, t_data, flags, itemdesc):
        id = id[0].id
        live = g_thdListener._receive
        dataValid = node[ID_TAG_VALID_DATA] == 1
        dataSetIsLive = False
        idConnected = GetConnectedDataSetId()
        idDataSet = node[ID_TAG_DATA_SET]
        isOnlySelected = node.GetDocument().GetActiveTag() == node
        if idConnected != -1 and idConnected == idDataSet:
            dataSetIsLive = True
        if id == ID_TAG_DATA_SET_FIRST_FRAME:
            return dataValid and not live and not dataSetIsLive
        elif id == ID_TAG_DATA_SET_LAST_FRAME:
            return dataValid and not live and not dataSetIsLive
        elif id == ID_TAG_BUTTON_PLAY:
            return dataValid or live and isOnlySelected
        elif id == ID_TAG_SELECTED_IN_MANAGER:
            return dataValid
        elif id == ID_TAG_BUTTON_SET_KEYFRAMES_CURRENT:
            return dataValid and not live
        elif id == ID_TAG_BUTTON_SET_KEYFRAMES:
            return dataValid and not live and not dataSetIsLive and isOnlySelected
        elif id == ID_TAG_RIG_TYPE:
            return node[ID_TAG_EXECUTE_MODE] == 0
        elif id == ID_TAG_BUTTON_GO_TO_TPOSE:
            return not live
        elif id == ID_TAG_OPEN_MANAGER_ON_PLAY:
            return not live
        elif id == ID_TAG_ACTOR_HIP_HEIGHT:
            return not live and node[ID_TAG_ACTOR_HAS_HIP] == True
        elif id == ID_TAG_BUTTON_GUESS_RIG:
            return not live
        elif id == ID_TAG_BUTTON_RIG_PRESET:
            return not live
        elif id == ID_TAG_BUTTON_STORE_TPOSE:
            return not live
        elif id == ID_TAG_BUTTON_GUESS_FACE_POSES:
            return not live
        elif id == ID_TAG_BUTTON_FACE_PRESET:
            return not live
        elif id >= ID_TAG_BASE_RIG_LINKS and id < (ID_TAG_BASE_RIG_LINKS + len(STUDIO_NAMES_TO_GUESS)):
            return not live
        elif id >= ID_TAG_BASE_FACE_POSES and id < (ID_TAG_BASE_FACE_POSES + len(FACE_POSE_NAMES)):
            return not live
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
        return True


    def ConnectDataSet(self, tag, idDataSet):
        bcDataSet = GetDataSetFromId(idDataSet)
        if bcDataSet is None or bcDataSet[ID_BC_DATASET_TYPE] == 0:
            return
        g_thdListener.ConnectDataSet(bcDataSet)


    def SetDParameter(self, node, id, t_data, flags):
        id = id[0].id
        if id == ID_TAG_ACTORS:
            bcDataSet = GetDataSetFromId(node[ID_TAG_DATA_SET])
            if bcDataSet is not None:
                rigType = node[ID_TAG_RIG_TYPE]
                idEntitiesBc = RigTypeToEntitiesBcId(rigType)
                setByName = False
                node.GetDataInstance().SetInt32(ID_TAG_ACTOR_INDEX, -1)
                bcEntities = bcDataSet.GetContainerInstance(idEntitiesBc)
                if bcEntities is not None:
                    for idxEntity, _ in bcEntities:
                        bcEntity = bcEntities.GetContainerInstance(idxEntity)
                        name = bcEntity[ID_BC_ENTITY_NAME]
                        if MyHash(name) == t_data:
                            node[ID_TAG_ACTOR_INDEX] = idxEntity
                            setByName = True
                            break
                if not setByName:
                    node[ID_TAG_ACTOR_INDEX] = t_data
        elif id == ID_TAG_ACTOR_MAP_BODY and (flags & c4d.DESCFLAGS_SET_USERINTERACTION):
            return True, flags | c4d.DESCFLAGS_SET_PARAM_SET
        elif id == ID_TAG_ACTOR_MAP_HAND_LEFT and (flags & c4d.DESCFLAGS_SET_USERINTERACTION):
            return True, flags | c4d.DESCFLAGS_SET_PARAM_SET
        elif id == ID_TAG_ACTOR_MAP_HAND_RIGHT and (flags & c4d.DESCFLAGS_SET_USERINTERACTION):
            return True, flags | c4d.DESCFLAGS_SET_PARAM_SET
        elif id == ID_TAG_ENTITY_COLOR and (flags & c4d.DESCFLAGS_SET_USERINTERACTION):
            return True, flags | c4d.DESCFLAGS_SET_PARAM_SET
        return True, flags | c4d.DESCFLAGS_SET_NONE


    def Execute(self, tag, doc, op, bt, priority, flags):
        if tag[ID_TAG_EXECUTE_MODE] == 0 or not tag[ID_TAG_VALID_DATA]:
            return c4d.EXECUTIONRESULT_OK
        if self._funcExecute is None:
            return c4d.EXECUTIONRESULT_OK
        idxFrame = self._queueReceive.GetFrameIdx(tag)
        if idxFrame is None:
            return c4d.EXECUTIONRESULT_OK
        data = g_thdListener.GetFrame(tag[ID_TAG_DATA_SET], idxFrame)
        if data is None:
            return c4d.EXECUTIONRESULT_OK
        return self._funcExecute(tag, data)

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
        for (idxBodyPart, _, _, _, _, _, _, _) in STUDIO_NAMES_TO_GUESS.values():
            tag[ID_TAG_BASE_RIG_LINKS + idxBodyPart] = None
        for obj in iter_objs(objRoot):
            objName = obj.GetName()
            objName = objName.lower()
            for nameStudio, (idxBodyPart, nameDisplay, device, namesMain, namesInclude, namesExclude, namesSideInclude, namesSideExclude) in tableBodyParts.items():
                hitMain = False
                for namesNeeded in namesMain:
                    hitMain = True
                    for name in namesNeeded:
                        if name not in objName:
                            hitMain = False
                            break
                    if hitMain:
                        break
                if not hitMain:
                    continue
                hitInclude = False
                for nameInclude in namesInclude:
                    if nameInclude in objName:
                        hitInclude = True
                        break
                if not hitInclude and len(namesInclude) > 0:
                    continue
                hitExclude = False
                for nameExclude in namesExclude:
                    if nameExclude in objName:
                        hitExclude = True
                        break
                if hitExclude:
                    continue
                hitSideInclude = False
                hitSideExclude = False
                for nameSideInclude in namesSideInclude:
                    if nameSideInclude in objName:
                        hitSideInclude = True
                        break
                if not hitSideInclude:
                    for nameSideExclude in namesSideExclude:
                        if nameSideExclude in objName:
                            hitSideExclude = True
                            break
                    if hitSideExclude:
                        continue
                if nameStudio not in detectedRig:
                    detectedRig[nameStudio] = (idxBodyPart, obj, objName, device)
                    tag[ID_TAG_BASE_RIG_LINKS + idxBodyPart] = obj
                    if device == 1:
                        hasBody = True
                    elif device == 6:
                        hasHandLeft = True
                    elif device == 10:
                        hasHandRight = True
                    break
        if 'hip' in detectedRig:
            hasHip = True
            mgRoot = objRoot.GetMg()
            mlHip = detectedRig['hip'][1].GetMl()
            axis = 1
            if round(mlHip.off.y, 0) == round(mlHip.off.z, 0) == 0:
                axis = 0
            elif round(mlHip.off.x, 0) == round(mlHip.off.y, 0) == 0:
                axis = 2
            hipHeight = detectedRig['hip'][1].GetMl().off[axis]
            tag[ID_TAG_ACTOR_HIP_HEIGHT] = abs(hipHeight)
        tag[ID_TAG_ACTOR_HAS_BODY] = hasBody
        tag[ID_TAG_ACTOR_HAS_HIP] = hasHip
        tag[ID_TAG_ACTOR_HAS_HAND_LEFT] = hasHandLeft
        tag[ID_TAG_ACTOR_HAS_HAND_RIGHT] = hasHandRight
        tag[ID_TAG_ACTOR_MAP_BODY] = hasBody
        tag[ID_TAG_ACTOR_MAP_HAND_LEFT] = hasHandLeft
        tag[ID_TAG_ACTOR_MAP_HAND_RIGHT] = hasHandRight
        tag[ID_TAG_ACTOR_RIG_DETECTED] = True
        tag.SetDirty(c4d.DIRTYFLAGS_DESCRIPTION)
        return detectedRig

    def SetTPose(self, tag):
        objRoot = tag.GetObject()
        if objRoot is None:
            return
        objHip = tag[ID_TAG_BASE_RIG_LINKS + 0]
        if objHip != objRoot:
            mgRootTPose = objRoot.GetMg()
        else:
            mgRootTPose = c4d.Matrix()
        tag[ID_TAG_ROOT_MATRIX] = mgRootTPose
        for nameInStudio, (idx, _, _, _, _, _, _, _) in STUDIO_NAMES_TO_GUESS.items():
            obj = tag[ID_TAG_BASE_RIG_LINKS + idx]
            if obj is None:
                continue
            mgBodyPartTPose = MR_Y180 * ~mgRootTPose * obj.GetMg()
            tag[ID_TAG_BASE_RIG_MATRICES + idx] = mgBodyPartTPose
            tag[ID_TAG_BASE_RIG_MATRICES_PRETRANSFORMED + idx] = g_studioTPose[nameInStudio] * (~mgRootTPose * mgBodyPartTPose)
        tag[ID_TAG_ACTOR_TPOSE_STORED] = True

    def PrepareTPoseDict(self, tag):
        if len(g_studioTPose) <= 0:
            return
        self._tPoseTag = {}
        for nameInStudio, (idx, _, _, _, _, _, _, _) in STUDIO_NAMES_TO_GUESS.items():
            obj = tag[ID_TAG_BASE_RIG_LINKS + idx]
            if obj is None:
                continue
            nameObj = obj.GetName()
            mgBodyPartTPose = tag[ID_TAG_BASE_RIG_MATRICES + idx]
            mgBodyPartTPosePretransformed = tag[ID_TAG_BASE_RIG_MATRICES_PRETRANSFORMED + idx]
            self._tPoseTag[nameInStudio] = (obj, mgBodyPartTPose, nameObj, mgBodyPartTPosePretransformed)

    #@timing
    def ExecuteActor(self, tag, data):
        objRoot = tag.GetObject()
        objHip = tag[ID_TAG_BASE_RIG_LINKS + 0]
        if objHip != objRoot:
            mgRoot = objRoot.GetMg()
        else:
            mgRoot = c4d.Matrix()
        mgRootTPose = tag[ID_TAG_ROOT_MATRIX]
        idxActor = tag[ID_TAG_ACTOR_INDEX]
        dataActor = data['actors'][idxActor]
        dataBody = dataActor['body']
        for nameInStudio, (obj, _, nameInRig, mRotOffsetRef) in self._tPoseTag.items():
            dataBodyPart = dataBody[nameInStudio]
            mStudioNewPose = JSONQuaternionToMatrix(dataBodyPart['rotation'])
            mFinalRot = mStudioNewPose * mRotOffsetRef
            mFinalRot = MR_Y180 * mFinalRot # actually ~MR_Y180 * mFinalRot, but ~MR_Y180 == MR_Y180
            mFinalRot = ~mgRootTPose * mFinalRot
            mFinalRot = mgRoot * mFinalRot
            mFinalRot.off = obj.GetMg().off
            obj.SetMg(mFinalRot)
        if 'hip' in self._tPoseTag:
            objHip, _, nameInRigHip, _ = self._tPoseTag['hip']
            dataBodyPart = dataBody['hip']
            hipHeightStudio = dataActor['dimensions']['hipHeight']
            hipHeightStudioC4D = hipHeightStudio * 100.0
            posStudio = dataBodyPart['position']
            yTPoseHip = tag[ID_TAG_ACTOR_HIP_HEIGHT]
            scale = yTPoseHip / hipHeightStudio
            y = yTPoseHip * (1 + (posStudio['y'] - hipHeightStudio))
            off = c4d.Vector(-posStudio['x'] * scale,
                             y,
                             -posStudio['z'] * scale)
            off = ~mgRootTPose * off
            off *= GetProjectScale()
            objHip.SetRelPos(off)
        return c4d.EXECUTIONRESULT_OK

    def DetectFacePoses(self, tag, tablePoseNames=FACE_POSE_NAMES):
        detectedPoses = {}
        if tag is None:
            return detectedPoses
        objRoot = tag.GetObject()
        if objRoot is None:
            return detectedPoses
        tagPoseMorph = objRoot.GetTag(c4d.Tposemorph)
        if tagPoseMorph is None:
            return detectedPoses
        for (idxInStudio, _, _, _, _, _) in FACE_POSE_NAMES.values():
            tag[ID_TAG_BASE_FACE_POSES + idxInStudio] = ''
        for idxMorph in range(1, tagPoseMorph.GetMorphCount()):
            morph = tagPoseMorph.GetMorph(idxMorph)
            nameMorphC4D = morph.GetName()
            nameMorphC4DLower = nameMorphC4D.lower()
            for nameStudio, (idxInStudio, nameDisplay, namesMain, namesExclude, namesSideInclude, namesSideExclude) in tablePoseNames.items():
                hitMain = False
                for namesNeeded in namesMain:
                    hitMain = True
                    for name in namesNeeded:
                        if name not in nameMorphC4DLower:
                            hitMain = False
                            break
                    if hitMain:
                        break
                if not hitMain:
                    continue
                hitExclude = False
                for nameExclude in namesExclude:
                    if nameExclude in nameMorphC4DLower:
                        hitExclude = True
                        break
                if hitExclude:
                    continue
                hitSideInclude = False
                hitSideExclude = False
                for nameSideInclude in namesSideInclude:
                    if nameSideInclude in nameMorphC4DLower:
                        hitSideInclude = True
                        break
                if not hitSideInclude:
                    for nameSideExclude in namesSideExclude:
                        if nameSideExclude in nameMorphC4DLower:
                            hitSideExclude = True
                            break
                    if hitSideExclude:
                        continue
                if nameStudio not in detectedPoses:
                    detectedPoses[nameStudio] = (idxMorph, nameMorphC4D)
                    tag[ID_TAG_BASE_FACE_POSES + idxInStudio] = nameMorphC4D
                    tag[ID_TAG_BASE_MORPH_INDECES + idxInStudio] = idxMorph
                    break
        tag[ID_TAG_ACTOR_FACE_DETECTED] = True

    def PrepareFacePoseDict(self, tag):
        self._facePoses = {}
        obj = tag.GetObject()
        if obj is None:
            return
        tagPoseMorph = obj.GetTag(c4d.Tposemorph)
        for nameInStudio, (idxPose, _, _, _, _, _) in FACE_POSE_NAMES.items():
            namePoseC4D = tag[ID_TAG_BASE_FACE_POSES + idxPose]
            if namePoseC4D is None or len(namePoseC4D) <= 0:
                continue
            idxMorph = tag[ID_TAG_BASE_MORPH_INDECES + idxPose]
            if idxMorph is not None:
                descIdMorph = tagPoseMorph.GetMorphID(idxMorph)
                self._facePoses[nameInStudio] = descIdMorph

    def ExecuteFace(self, tag, data):
        idxActor = tag[ID_TAG_ACTOR_INDEX]
        dataFace = data['actors'][idxActor]['face']
        obj = tag.GetObject()
        tagPoseMorph = obj.GetTag(c4d.Tposemorph)
        for nameInStudio, descIdMorph in self._facePoses.items():
            tagPoseMorph.SetParameter(descIdMorph, float(dataFace[nameInStudio]) / 100.0, c4d.DESCFLAGS_SET_NONE)
        return c4d.EXECUTIONRESULT_OK

    def ExecuteProp(self, tag, data):
        objProp = tag.GetObject()
        idxProp = tag[ID_TAG_ACTOR_INDEX]
        dataProp = data['props'][idxProp]
        mPropStudio = JSONQuaternionToMatrix(dataProp['rotation'])
        mFinalRot = MR_Y180 * mPropStudio # actually ~MR_Y180 * mFinalRot, but ~MR_Y180 == MR_Y180
        mFinalRot.off = objProp.GetMg().off
        objProp.SetMg(mFinalRot)
        posStudio = dataProp['position']
        off = c4d.Vector(-posStudio['x'] * 100.0,
                         posStudio['y'] * 100.0,
                         -posStudio['z'] * 100.0)
        off *= GetProjectScale()
        objProp.SetRelPos(off)
        return c4d.EXECUTIONRESULT_OK


    def MessageMenuPrepare(self, tag):
        rigType = DetermineRigType(tag.GetObject())
        tag.SetParameter(ID_TAG_RIG_TYPE, rigType, c4d.DESCFLAGS_SET_NONE)
        self.SetRigTypeMenuContainer(tag)
        self.SetDataSetMenuContainer(tag)
        self.SetActorMenuContainer(tag)
        if rigType & RIG_TYPE_ACTOR:
            if not tag[ID_TAG_ACTOR_RIG_DETECTED]:
                self.DetectRig(tag)
            if not tag[ID_TAG_ACTOR_TPOSE_STORED]:
                self.SetTPose(tag)
            self.PrepareTPoseDict(tag)
            self._funcExecute = self.ExecuteActor
        elif rigType & RIG_TYPE_ACTOR_FACE:
            if not tag[ID_TAG_ACTOR_FACE_DETECTED]:
                self.DetectFacePoses(tag)
            self.PrepareFacePoseDict(tag)
            self._funcExecute = self.ExecuteFace
        elif rigType & RIG_TYPE_LIGHT:
            pass
        elif rigType & RIG_TYPE_CAMERA:
            pass
        elif rigType & RIG_TYPE_PROP:
            self._funcExecute = self.ExecuteProp
        elif rigType & RIG_TYPE_UNKNOWN:
            pass
        else:
            pass
        self.ConnectDataSet(tag, tag[ID_TAG_DATA_SET])
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAGS)

    def MessagePostSetParameter(self, tag, data):
        id = data['descid'][0].id
        if id >= ID_TAG_BASE_RIG_LINKS and id < ID_TAG_BASE_RIG_LINKS + len(STUDIO_NAMES_TO_GUESS):
            idxBodyPart = id - ID_TAG_BASE_RIG_LINKS
            if idxBodyPart == STUDIO_NAMES_TO_GUESS['hip'][0]:
                tag[ID_TAG_ACTOR_HAS_HIP] = tag[id] != None
            tag.SetDirty(c4d.DIRTYFLAGS_DESCRIPTION)
            self.SetTPose(tag)
            self.PrepareTPoseDict(tag)
        elif id >= ID_TAG_BASE_FACE_POSES and id < ID_TAG_BASE_FACE_POSES + len(FACE_POSE_NAMES):
            self.PrepareFacePoseDict(tag)
        elif id == ID_TAG_DATA_SET:
            idDataSet = tag[ID_TAG_DATA_SET]
            if idDataSet != 0:
                self.ConnectDataSet(tag, idDataSet)
                if idDataSet != GetConnectedDataSetId():
                    tag[ID_TAG_DATA_SET_FIRST_FRAME] = 0
                    tag[ID_TAG_DATA_SET_LAST_FRAME] = g_thdListener.GetDataSetSize(idDataSet)
                else:
                    tag[ID_TAG_DATA_SET_FIRST_FRAME] = 0
                    tag[ID_TAG_DATA_SET_LAST_FRAME] = 0
        elif id == ID_TAG_DATA_SET_FIRST_FRAME:
            if tag[ID_TAG_DATA_SET_LAST_FRAME] is not None and tag[ID_TAG_DATA_SET_FIRST_FRAME] >= tag[ID_TAG_DATA_SET_LAST_FRAME]:
                tag[ID_TAG_DATA_SET_LAST_FRAME] = tag[ID_TAG_DATA_SET_FIRST_FRAME] + 1
        elif id == ID_TAG_DATA_SET_LAST_FRAME:
            if tag[ID_TAG_DATA_SET_FIRST_FRAME] is not None and tag[ID_TAG_DATA_SET_LAST_FRAME] <= tag[ID_TAG_DATA_SET_FIRST_FRAME]:
                tag[ID_TAG_DATA_SET_FIRST_FRAME] = tag[ID_TAG_DATA_SET_LAST_FRAME] - 1
        elif id == ID_TAG_ACTOR_HIP_HEIGHT:
            hipHeightNew = tag[ID_TAG_ACTOR_HIP_HEIGHT]
            idxHip = STUDIO_NAMES_TO_GUESS['hip'][0]
            objHip = tag[ID_TAG_BASE_RIG_LINKS + idxHip]
            if objHip is not None:
                mgHip = tag[ID_TAG_BASE_RIG_MATRICES + idxHip]
                mgHip.off = c4d.Vector(mgHip.off.x, hipHeightNew, mgHip.off.z)
                tag.GetDataInstance().SetMatrix(ID_TAG_BASE_RIG_MATRICES + idxHip, mgHip)
                self.PrepareTPoseDict(tag)
        if id == ID_TAG_RIG_TYPE or id == ID_TAG_DATA_SET or \
           id == ID_TAG_ACTORS or id == ID_TAG_ACTOR_INDEX or \
           id == ID_TAG_VALID_DATA:
            if tag[ID_TAG_VALID_DATA]:
                rigType = tag[ID_TAG_RIG_TYPE]
                idDataSet = tag[ID_TAG_DATA_SET]
                idxEntity = tag[ID_TAG_ACTOR_INDEX]
                idEntitiesBc = RigTypeToEntitiesBcId(rigType)
                bcDataSet = GetDataSetFromId(idDataSet)
                if bcDataSet is not None:
                    bcEntity = bcDataSet.GetContainerInstance(idEntitiesBc).GetContainerInstance(int(idxEntity))
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
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAG_PARAMS)

    def MessageGetAllAssets(self, tag, data):
        doc = data['doc']
        flags = data['flags']
        if flags & c4d.ASSETDATA_FLAG_TEXTURESONLY:
            return True
        bcDataSet = GetDataSetFromId(tag[ID_TAG_DATA_SET])
        if bcDataSet is None:
            return True
        if bcDataSet[ID_BC_DATASET_TYPE] == 0 or bcDataSet.GetId() == GetConnectedDataSetId():
            return True
        filename = bcDataSet[ID_BC_DATASET_FILENAME]
        if bcDataSet[ID_BC_DATASET_IS_LOCAL]:
            if filename[0] == '.':
                pathDoc = doc.GetDocumentPath()
                filename = filename.replace('.', pathDoc, 1)
        data['assets'].append({'filename' : filename, 'bl' : tag, 'netRequestOnDemand' : False})

    def MessageClearSuggestedFolder(self, tag):
        idDataSet = tag[ID_TAG_DATA_SET]
        bcDataSet = GetDataSetFromId(idDataSet)
        if bcDataSet is None:
            return True
        bcDataSet = bcDataSet.GetClone(c4d.COPYFLAGS_NONE)
        if bcDataSet[ID_BC_DATASET_TYPE] == 0 or bcDataSet.GetId() == GetConnectedDataSetId():
            return True
        if bcDataSet[ID_BC_DATASET_IS_LOCAL]:
            RemoveLocalDataSet(idDataSet)
        _, bcDataSet[ID_BC_DATASET_FILENAME] = os.path.split(bcDataSet[ID_BC_DATASET_FILENAME])
        bcDataSet[ID_BC_DATASET_IS_LOCAL] = True
        bcDataSet.SetId(MyHash(bcDataSet[ID_BC_DATASET_NAME] + bcDataSet[ID_BC_DATASET_FILENAME] + str(bcDataSet[ID_BC_DATASET_IS_LOCAL])))
        AddLocalDataSetBC(bcDataSet)
        tag.GetDataInstance()[ID_TAG_DATA_SET] = bcDataSet.GetId()
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAGS)

    def MessageDocumentInfo(self, tag, data):
        didId = data['type']
        if didId != c4d.MSG_DOCUMENTINFO_TYPE_LOAD and didId != c4d.MSG_DOCUMENTINFO_TYPE_MERGE and \
           didId != c4d.MSG_DOCUMENTINFO_TYPE_SETACTIVE and didId != c4d.MSG_DOCUMENTINFO_TYPE_UNDO:
           return
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAGS)

    def MessageGetCustomIcon(self, tag, data):
        obj = None
        try: # TODO Andreas: Check exception during tag drag and drop
            obj = tag.GetObject()
        except:
            pass
        w = data['w']
        h = data['h']
        if obj is not None or not self._iconsValid:
            rigTypeConfigured = tag.GetDataInstance().GetInt32(ID_TAG_RIG_TYPE)
            dataSetConfigured = tag.GetDataInstance().GetInt32(ID_TAG_DATA_SET)
            if self._lastObj == None or not self._lastObj.IsAlive() or self._lastObj != obj or \
               self._lastRigType != rigTypeConfigured or self._lastDataSet != dataSetConfigured or g_forceUpdate:
                self._iconsValid = False
            if not self._iconsValid:
                rigTypeOptions = DetermineRigTypeOptions(obj)
                if (rigTypeOptions & rigTypeConfigured) == 0:
                    rigType = DetermineRigType(obj)
                    tag.GetDataInstance().SetInt32(ID_TAG_RIG_TYPE, rigType)
                else:
                    rigType = tag.GetDataInstance().GetInt32(ID_TAG_RIG_TYPE)
                self.SetRigTypeMenuContainer(tag)
                self.SetDataSetMenuContainer(tag)
                self.SetActorMenuContainer(tag)
                self.ConnectDataSet(tag, tag[ID_TAG_DATA_SET])
                if rigType & RIG_TYPE_ACTOR:
                    if not tag[ID_TAG_ACTOR_RIG_DETECTED]:
                        self.DetectRig(tag)
                    if not tag[ID_TAG_ACTOR_TPOSE_STORED]:
                        self.SetTPose(tag)
                    self.PrepareTPoseDict(tag)
                    self._funcExecute = self.ExecuteActor
                    icon = c4d.gui.GetIcon(PLUGIN_ID_TAG_ICON_ACTOR)
                elif rigType & RIG_TYPE_ACTOR_FACE:
                    if not tag[ID_TAG_ACTOR_FACE_DETECTED]:
                        self.DetectFacePoses(tag)
                    self.PrepareFacePoseDict(tag)
                    self._funcExecute = self.ExecuteFace
                    icon = c4d.gui.GetIcon(PLUGIN_ID_TAG_ICON_FACE)
                elif rigType & RIG_TYPE_LIGHT:
                    icon = c4d.gui.GetIcon(PLUGIN_ID_TAG_ICON_LIGHT)
                elif rigType & RIG_TYPE_CAMERA:
                    icon = c4d.gui.GetIcon(PLUGIN_ID_TAG_ICON_CAMERA)
                elif rigType & RIG_TYPE_PROP:
                    self._funcExecute = self.ExecuteProp
                    icon = c4d.gui.GetIcon(PLUGIN_ID_TAG_ICON_PROP)
                elif rigType & RIG_TYPE_UNKNOWN:
                    icon = c4d.gui.GetIcon(PLUGIN_ID_ICON_STUDIO_LIVE)
                else:
                    icon = c4d.gui.GetIcon(PLUGIN_ID_ICON_STUDIO_LIVE)
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
        data['filled'] = True
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


    def CommandOpenManager(self):
        c4d.CallCommand(PLUGIN_ID_COMMAND_MANAGER)

    def CommandStoreTPose(self, tag):
        self.SetTPose(tag)
        self.PrepareTPoseDict(tag)

    def CommandRestoreTPose(self, tag):
        doc = tag.GetDocument()
        objRoot = tag.GetObject()
        mgRoot = objRoot.GetMg()
        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, objRoot)
        for nameInStudio, (obj, mgTPose, _, _) in self._tPoseTag.items():
            obj.SetMg(mgRoot * MR_Y180 * mgTPose)
        doc.EndUndo()

    def CommandGuessRig(self, tag):
        self.DetectRig(tag)
        self.SetTPose(tag)
        self.PrepareTPoseDict(tag)

    def CommandGuessFace(self, tag):
        self.DetectFacePoses(tag)
        self.PrepareFacePoseDict(tag)

    def CommandPlayerStart(self, tag):
        live = tag[ID_TAG_DATA_SET] == GetConnectedDataSetId()
        if not live and g_thdListener.GetConnectionStatus() == 2:
            result = c4d.gui.MessageDialog('Currently there is no data incoming from Live connection.\nDisconnect?', c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_YESNOCANCEL)
            if result == c4d.GEMB_R_YES:
                c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_CONNECTION, CM_SUBID_CONNECTION_DISCONNECT)
            elif result == c4d.GEMB_R_CANCEL:
                return
        g_thdListener.AddTagConsumer(tag.GetNodeData(), tag)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_START)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_PLAY, False)
        if tag[ID_TAG_OPEN_MANAGER_ON_PLAY]:
            c4d.CallCommand(PLUGIN_ID_COMMAND_MANAGER)
            c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_OPEN_PLAYER)

    def CommandPlayerStop(self, tag):
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_STOP)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_PLAYER, CM_SUBID_PLAYER_EXIT)
        c4d.EventAdd()

    def CommandPlayerStartStop(self, tag):
        if not g_thdListener._receive:
            self.CommandPlayerStart(tag)
        else:
            self.CommandPlayerStop(tag)

    def CommandBakeKeyframes(self, tag):
        self._dlgBake = DialogSaveRecording(dlgParent=None, tags=[tag], bakingOnly=True)
        self._dlgBake.Open(c4d.DLG_TYPE_ASYNC)

    def CommandAddRigPreset(self, tag):
        namePreset = c4d.gui.RenameDialog(tag.GetName())
        if namePreset is None or len(namePreset) <= 0:
            return
        bcRigPresets = GetPrefsContainer(ID_BC_RIG_PRESETS)
        bcPreset = c4d.BaseContainer()
        bcPreset[ID_BC_PRESET_NAME] = namePreset
        bcPreset[ID_BC_PRESET_TYPE] = 0 # rig
        for (idxInStudio, _, _, _, _, _, _, _) in STUDIO_NAMES_TO_GUESS.values():
            obj = tag[ID_TAG_BASE_RIG_LINKS + idxInStudio]
            if obj is None:
                continue
            bcPreset[idxInStudio] = obj.GetName()
        idxNewPreset = len(bcRigPresets)
        bcRigPresets.SetContainer(idxNewPreset, bcPreset)

    def CommandApplyRigPreset(self, tag):
        bcRigPresets = GetPrefsContainer(ID_BC_RIG_PRESETS)
        bcPresetMenu = c4d.BaseContainer()
        if bcRigPresets is not None and len(bcRigPresets) > 0:
            for idx, _ in bcRigPresets:
                bcPreset = bcRigPresets.GetContainerInstance(idx)
                idPresetBase = c4d.FIRST_POPUP_ID + idx * 1000
                bcSubMenu = c4d.BaseContainer()
                bcSubMenu.InsData(1, bcPreset[ID_BC_PRESET_NAME])
                bcSubMenu.InsData(idPresetBase + 1, 'Apply')
                bcSubMenu.InsData(idPresetBase + 2, 'Rename')
                bcSubMenu.InsData(idPresetBase + 3, 'Delete')
                bcPresetMenu.SetContainer(idPresetBase, bcSubMenu)
        else:
            bcPresetMenu[c4d.FIRST_POPUP_ID + 999999] = 'No presets available'
        result = c4d.gui.ShowPopupDialog(cd=None, bc=bcPresetMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)
        if result == c4d.FIRST_POPUP_ID + 999999 or result == 0:
            return
        idxPreset = (result - c4d.FIRST_POPUP_ID) // 1000
        command = (result - c4d.FIRST_POPUP_ID) % 1000
        bcPreset = bcRigPresets.GetContainerInstance(idxPreset)
        if command == 2:
            namePresetNew = c4d.gui.RenameDialog(bcPreset[ID_BC_PRESET_NAME])
            if namePresetNew is None or len(namePresetNew) <= 0:
                return
            bcPreset[ID_BC_PRESET_NAME] = namePresetNew
            return
        elif command == 3:
            numPresets = len(bcRigPresets)
            bcRigPresets.RemoveData(idxPreset)
            for idxPresetOld in range(idxPreset + 1, numPresets):
                bcRigPresets.SetContainer(idxPresetOld - 1, bcRigPresets.GetContainer(idxPresetOld))
                bcRigPresets.RemoveData(idxPresetOld)
            return
        tableBodyParts = {}
        for nameStudio, (idxBodyPart, _, device, _, _, _, _, _) in STUDIO_NAMES_TO_GUESS.items():
            nameObj = bcPreset[idxBodyPart]
            if nameObj is None or len(nameObj) <= 0:
                continue
            nameObj = nameObj.lower()
            tableBodyParts[nameStudio] = (idxBodyPart, '', device, [[nameObj]], [nameObj], [], [], [])
        self.DetectRig(tag, tableBodyParts)
        self.SetTPose(tag)
        self.PrepareTPoseDict(tag)

    def CommandAddFacePreset(self, tag):
        namePreset = c4d.gui.RenameDialog(tag.GetName())
        if namePreset is None or len(namePreset) <= 0:
            return
        bcFacePresets = GetPrefsContainer(ID_BC_FACE_PRESETS)
        bcPreset = c4d.BaseContainer()
        bcPreset[ID_BC_PRESET_NAME] = namePreset
        bcPreset[ID_BC_PRESET_TYPE] = 1 # face
        for (idxInStudio, _, _, _, _, _) in FACE_POSE_NAMES.values():
            namePose = tag[ID_TAG_BASE_FACE_POSES + idxInStudio]
            if namePose is None or len(namePose) <= 0:
                continue
            bcPreset[idxInStudio] = namePose
        idxNewPreset = len(bcFacePresets)
        bcFacePresets.SetContainer(idxNewPreset, bcPreset)

    def CommandApplyFacePreset(self, tag):
        bcFacePresets = GetPrefsContainer(ID_BC_FACE_PRESETS)
        bcPresetMenu = c4d.BaseContainer()
        if bcFacePresets is not None and len(bcFacePresets) > 0:
            for idx, _ in bcFacePresets:
                bcPreset = bcFacePresets.GetContainerInstance(idx)
                idPresetBase = c4d.FIRST_POPUP_ID + idx * 1000
                bcSubMenu = c4d.BaseContainer()
                bcSubMenu.InsData(1, bcPreset[ID_BC_PRESET_NAME])
                bcSubMenu.InsData(idPresetBase + 1, 'Apply')
                bcSubMenu.InsData(idPresetBase + 2, 'Rename')
                bcSubMenu.InsData(idPresetBase + 3, 'Delete')
                bcPresetMenu.SetContainer(idPresetBase, bcSubMenu)
        else:
            bcPresetMenu[c4d.FIRST_POPUP_ID + 999999] = 'No presets available'
        result = c4d.gui.ShowPopupDialog(cd=None, bc=bcPresetMenu, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)
        if result == c4d.FIRST_POPUP_ID + 999999 or result == 0:
            return
        idxPreset = (result - c4d.FIRST_POPUP_ID) // 1000
        command = (result - c4d.FIRST_POPUP_ID) % 1000
        bcPreset = bcFacePresets[idxPreset]
        if command == 2:
            namePresetNew = c4d.gui.RenameDialog(bcPreset[ID_BC_PRESET_NAME])
            if namePresetNew is None or len(namePresetNew) <= 0:
                return
            bcPreset[ID_BC_PRESET_NAME] = namePresetNew
            return
        elif command == 3:
            numPresets = len(bcFacePresets)
            bcFacePresets.RemoveData(idxPreset)
            for idxPresetOld in range(idxPreset + 1, numPresets):
                bcFacePresets.SetContainer(idxPresetOld - 1, bcFacePresets.GetContainer(idxPresetOld))
                bcFacePresets.RemoveData(idxPresetOld)
            return
        tablePoses = {}
        for nameStudio, (idxPose, _, _, _, _, _) in FACE_POSE_NAMES.items():
            namePose = bcPreset[idxPose]
            if namePose is None or len(namePose) <= 0:
                continue
            namePose = namePose.lower()
            tablePoses[nameStudio] = (idxPose, '', [[namePose]], [], [], [])
        self.DetectFacePoses(tag, tablePoses)
        self.PrepareFacePoseDict(tag)

    def MessageCommand(self, tag, data):
        id = data['id'][0].id
        if id == ID_TAG_BUTTON_OPEN_MANAGER:
            self.CommandOpenManager()
        elif id == ID_TAG_BUTTON_STORE_TPOSE:
            self.CommandStoreTPose(tag)
        elif id == ID_TAG_BUTTON_GO_TO_TPOSE:
            self.CommandRestoreTPose(tag)
        elif id == ID_TAG_BUTTON_GUESS_RIG:
            self.CommandGuessRig(tag)
        elif id == ID_TAG_BUTTON_GUESS_FACE_POSES:
            self.CommandGuessFace(tag)
        elif id == ID_TAG_BUTTON_PLAY:
            self.CommandPlayerStartStop(tag)
        elif id == ID_TAG_BUTTON_SET_KEYFRAMES:
            self.CommandBakeKeyframes(tag)
        elif id == ID_TAG_BUTTON_ADD_RIG_PRESET:
            self.CommandAddRigPreset(tag)
        elif id == ID_TAG_BUTTON_RIG_PRESET:
            self.CommandApplyRigPreset(tag)
        elif id == ID_TAG_BUTTON_ADD_FACE_PRESET:
            self.CommandAddFacePreset(tag)
        elif id == ID_TAG_BUTTON_FACE_PRESET:
            self.CommandApplyFacePreset(tag)

    def MessageStudioDataChange(self, tag):
        self.SetDataSetMenuContainer(tag)
        self.SetActorMenuContainer(tag)
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAG_PARAMS)

    def Message(self, node, type, data):
        if type == c4d.MSG_MENUPREPARE:
            self.MessageMenuPrepare(node)
        elif type == c4d.MSG_DESCRIPTION_POSTSETPARAMETER:
            self.MessagePostSetParameter(node, data)
        elif type == c4d.MSG_GETALLASSETS:
            self.MessageGetAllAssets(node, data)
        elif type == c4d.MSG_MULTI_CLEARSUGGESTEDFOLDER:
            self.MessageClearSuggestedFolder(node)
        elif type == c4d.MSG_DOCUMENTINFO:
            self.MessageDocumentInfo(node, data)
        elif type == c4d.MSG_DESCRIPTION_COMMAND:
            self.MessageCommand(node, data)
        elif type == c4d.MSG_GETCUSTOMICON:
            self.MessageGetCustomIcon(node, data)
        elif type == PLUGIN_ID_MSG_DATA_CHANGE:
            self.MessageStudioDataChange(node)
        return True

    def CopyTo(self, dest, snode, dnode, flags, trn):
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAGS)
        dest._queueReceive = TagQueue()
        dest._tPoseTag = self._tPoseTag.copy()
        return True
