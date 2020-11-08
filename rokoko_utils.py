import time, math, hashlib, json
from ctypes import pythonapi, c_void_p, py_object
import lz4.frame
import c4d
from rokoko_ids import *
from rokoko_rig_tables import *

def Hash31(s):
    sha = hashlib.sha1()
    sha.update(s.encode('utf-8'))
    r = int(sha.hexdigest(), 16)
    r &= 0x7FFFFFFF
    return r

if c4d.GetC4DVersion() // 1000 < 23:
    MyHash = hash
else:
    MyHash = Hash31

def GetCoreMessageParam23(msg, id=c4d.BFM_CORE_PAR1):
    if msg.GetType(id) != c4d.DA_VOID:
        return 0
    vptr = msg.GetVoid(id)
    if vptr is None:
        return 0
    pythonapi.PyCapsule_GetPointer.restype = c_void_p
    pythonapi.PyCapsule_GetPointer.argtypes = [py_object]
    return pythonapi.PyCapsule_GetPointer(vptr, None)

def GetCoreMessageParamOld(msg, id=c4d.BFM_CORE_PAR1):
    vptr = msg.GetVoid(id)
    pythonapi.PyCObject_AsVoidPtr.restype = c_void_p
    pythonapi.PyCObject_AsVoidPtr.argtypes = [py_object]
    return pythonapi.PyCObject_AsVoidPtr(vptr)

def GetDefaultPrefContainer():
    return c4d.BaseContainer()

def GetWorldPrefs():
    bcWorldPrefs = c4d.plugins.GetWorldPluginData(PLUGIN_ID_COMMAND_MANAGER)
    if bcWorldPrefs is None:
        bcWorldPrefs = GetDefaultPrefContainer()
        c4d.plugins.SetWorldPluginData(PLUGIN_ID_COMMAND_MANAGER, bcWorldPrefs, True)
    return bcWorldPrefs

def GetPrefsContainer(idBc):
    bcWorldPrefs = GetWorldPrefs()
    if bcWorldPrefs is None:
        return None
    bc = bcWorldPrefs.GetContainerInstance(idBc)
    if bc is None:
        bc = c4d.BaseContainer()
        bcWorldPrefs.SetContainer(idBc, bc)
        c4d.plugins.SetWorldPluginData(PLUGIN_ID_COMMAND_MANAGER, bcWorldPrefs, add=True)
        bc = bcWorldPrefs.GetContainerInstance(idBc) # just to be sure we return the correct instance
    return bc

def SetPref(id, val):
    bcWorldPrefs = GetWorldPrefs()
    bcWorldPrefs[id] = val
    c4d.plugins.SetWorldPluginData(PLUGIN_ID_COMMAND_MANAGER, bcWorldPrefs, add=True)

def GetPref(id):
    bcWorldPrefs = GetWorldPrefs()
    return bcWorldPrefs[id]

def BaseContainerEntity(name, entityType=0, color=c4d.Vector(0.0), hasSuit=False, hasGloveLeft=False, hasGloveRight=False, hasFace=False):
    bc = c4d.BaseContainer()
    bc[ID_BC_ENTITY_NAME] = name
    bc[ID_BC_ENTITY_COLOR] = color
    bc[ID_BC_ENTITY_TYPE] = entityType
    bc[ID_BC_ENTITY_HAS_SUIT] = hasSuit
    bc[ID_BC_ENTITY_HAS_GLOVE_LEFT] = hasGloveLeft
    bc[ID_BC_ENTITY_HAS_GLOVE_RIGHT] = hasGloveRight
    bc[ID_BC_ENTITY_HAS_FACE] = hasFace
    return bc

def BaseContainerActor(name, color=c4d.Vector(0.0), hasSuit=False, hasGloveLeft=False, hasGloveRight=False, hasFace=False):
    return BaseContainerEntity(name, 0, color, hasSuit, hasGloveLeft, hasGloveRight, hasFace)

def BaseContainerProp(name, color=c4d.Vector(0.0)):
    return BaseContainerEntity(name, 1, color)

def BaseContainerLight(name, color=c4d.Vector(0.0)):
    return BaseContainerEntity(name, 2, color)

def BaseContainerCamera(name, color=c4d.Vector(0.0)):
    return BaseContainerEntity(name, 3, color)

def BaseContainerConnection(name='Studio Connection', port='14043', autoConnect=False, ipCommandApi='127.0.0.1', portCommandApi='14053', keyCommandApi='1234'):
    bc = c4d.BaseContainer()
    bc[ID_BC_DATASET_NAME] = name
    bc[ID_BC_DATASET_TYPE] = 0 # type: 0 - connection, 1 - file global, 2 - file local
    bc[ID_BC_DATASET_CONNECTED] = False
    bc[ID_BC_DATASET_AVAILABLE_IN_DOC] = True
    bc[ID_BC_DATASET_LIVE_PORT] = port
    bc[ID_BC_DATASET_LIVE_AUTOCONNECT] = autoConnect
    bc[ID_BC_DATASET_LIVE_FPS] = 0.0
    bc[ID_BC_DATASET_COMMANDAPI_IP] = ipCommandApi
    bc[ID_BC_DATASET_COMMANDAPI_PORT] = portCommandApi
    bc[ID_BC_DATASET_COMMANDAPI_KEY] = keyCommandApi
    bc[ID_BC_DATASET_FILENAME] = ''
    bc[ID_BC_DATASET_IS_LOCAL] = False
    bc[ID_BC_DATASET_NUM_ACTORS] = 0
    bc[ID_BC_DATASET_NUM_SUITS] = 0
    bc[ID_BC_DATASET_NUM_GLOVES] = 0
    bc[ID_BC_DATASET_NUM_FACES] = 0
    bc[ID_BC_DATASET_NUM_LIGHTS] = 0
    bc[ID_BC_DATASET_NUM_CAMERAS] = 0
    bc[ID_BC_DATASET_NUM_PROPS] = 0
    bc.SetContainer(ID_BC_DATASET_ACTORS, c4d.BaseContainer())
    bc.SetContainer(ID_BC_DATASET_LIGHTS, c4d.BaseContainer())
    bc.SetContainer(ID_BC_DATASET_CAMERAS, c4d.BaseContainer())
    bc.SetContainer(ID_BC_DATASET_PROPS, c4d.BaseContainer())
    bc.SetId(MyHash(name + port + ipCommandApi + portCommandApi + keyCommandApi))
    return bc

def BaseContainerDataSet(name, file, numActors=0, numBody=0, numHands=0, numFaces=0, numLights=0, numCameras=0, numProps=0, availableInDocument=True, isLocal=False):
    bc = c4d.BaseContainer()
    bc[ID_BC_DATASET_NAME] = name
    bc[ID_BC_DATASET_TYPE] = 1 # type: 0 - connection, 1 - file
    bc[ID_BC_DATASET_CONNECTED] = False
    bc[ID_BC_DATASET_AVAILABLE_IN_DOC] = availableInDocument
    bc[ID_BC_DATASET_LIVE_PORT] = ''
    bc[ID_BC_DATASET_LIVE_AUTOCONNECT] = ''
    bc[ID_BC_DATASET_LIVE_FPS] = 0.0
    bc[ID_BC_DATASET_COMMANDAPI_IP] = ''
    bc[ID_BC_DATASET_COMMANDAPI_PORT] = ''
    bc[ID_BC_DATASET_COMMANDAPI_KEY] = ''
    bc[ID_BC_DATASET_FILENAME] = file
    bc[ID_BC_DATASET_IS_LOCAL] = isLocal
    bc[ID_BC_DATASET_NUM_ACTORS] = numActors
    bc[ID_BC_DATASET_NUM_SUITS] = numBody
    bc[ID_BC_DATASET_NUM_GLOVES] = numHands
    bc[ID_BC_DATASET_NUM_FACES] = numFaces
    bc[ID_BC_DATASET_NUM_LIGHTS] = numLights
    bc[ID_BC_DATASET_NUM_CAMERAS] = numCameras
    bc[ID_BC_DATASET_NUM_PROPS] = numProps
    bc.SetContainer(ID_BC_DATASET_ACTORS, c4d.BaseContainer())
    bc.SetContainer(ID_BC_DATASET_LIGHTS, c4d.BaseContainer())
    bc.SetContainer(ID_BC_DATASET_CAMERAS, c4d.BaseContainer())
    bc.SetContainer(ID_BC_DATASET_PROPS, c4d.BaseContainer())
    bc.SetId(MyHash(name + file + str(isLocal)))
    return bc

def AddConnection(name, port):
    bcWorldConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
    bcConnection = BaseContainerConnection(name, port)
    bcWorldConnections[bcConnection.GetId()] = bcConnection
    SetPref(ID_BC_CONNECTIONS, bcWorldConnections)

def AddConnectionBc(bcConnection):
    bcWorldConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
    bcWorldConnections[bcConnection.GetId()] = bcConnection
    SetPref(ID_BC_CONNECTIONS, bcWorldConnections)

def RemoveConnection(id):
    bcWorldConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
    bcWorldConnections.RemoveData(id)
    SetPref(ID_BC_CONNECTIONS, bcWorldConnections)

def AddGlobalDataSet(name, file, numBody=0, numHands=0, numFaces=0, numLights=0, numCameras=0, numProps=0, availableInDocument=True):
    bcWorldDataSets = GetPrefsContainer(ID_BC_DATA_SETS)
    bcDataSet = BaseContainerDataSet(name, file, numBody, numHands, numFaces, numLights, numCameras, numProps, availableInDocument, isLocal=False)
    bcWorldDataSets[bcDataSet.GetId()] = bcDataSet
    SetPref(ID_BC_DATA_SETS, bcWorldDataSets)

def AddGlobalDataSetBC(bcDataSet):
    bcWorldDataSets = GetPrefsContainer(ID_BC_DATA_SETS)
    bcWorldDataSets[bcDataSet.GetId()] = bcDataSet
    SetPref(ID_BC_DATA_SETS, bcWorldDataSets)

def RemoveGlobalDataSet(id):
    bcWorldDataSets = GetPrefsContainer(ID_BC_DATA_SETS)
    bcWorldDataSets.RemoveData(id)
    SetPref(ID_BC_DATA_SETS, bcWorldDataSets)

def GetDataSetFromId(idDataSet):
    bcConnected = GetConnectedDataSet()
    if bcConnected is not None and idDataSet == bcConnected.GetId():
        return bcConnected
    bcDataSetsGlobal = GetPrefsContainer(ID_BC_DATA_SETS)
    bcDataSet = bcDataSetsGlobal.GetData(idDataSet)
    if bcDataSet is not None:
        return bcDataSet
    bcDataSetsLocal = GetLocalDataSets()
    bcDataSet = bcDataSetsLocal.GetData(idDataSet)
    if bcDataSet is not None:
        return bcDataSet
    return None

def GetDocData():
    doc = c4d.documents.GetActiveDocument()
    bc = doc.GetDataInstance().GetContainerInstance(PLUGIN_ID_COMMAND_MANAGER)
    if bc is None:
        doc.GetDataInstance().SetContainer(PLUGIN_ID_COMMAND_MANAGER, c4d.BaseContainer())
        bc = doc.GetDataInstance().GetContainerInstance(PLUGIN_ID_COMMAND_MANAGER)
    return bc

def AddLocalDataSet(name, file, numBody=0, numHands=0, numFaces=0, numLights=0, numCameras=0, numProps=0, availableInDocument=True):
    bcData = GetDocData()
    if bcData[ID_BC_DATA_SETS] is None:
        bcData[ID_BC_DATA_SETS] = c4d.BaseContainer()
    bcLocalDataSets = bcData.GetContainerInstance(ID_BC_DATA_SETS)
    bcDataSet = BaseContainerDataSet(name, file, numBody, numHands, numFaces, numLights, numCameras, numProps, availableInDocument, isLocal=True)
    bcLocalDataSets[bcDataSet.GetId()] = bcDataSet

def AddLocalDataSetBC(bcDataSet):
    bcData = GetDocData()
    if bcData[ID_BC_DATA_SETS] is None:
        bcData[ID_BC_DATA_SETS] = c4d.BaseContainer()
    bcLocalDataSets = bcData.GetContainerInstance(ID_BC_DATA_SETS)
    bcLocalDataSets[bcDataSet.GetId()] = bcDataSet
    c4d.documents.GetActiveDocument().SetChanged()

def AddDataSetBC(bcDataSet):
    if bcDataSet[ID_BC_DATASET_IS_LOCAL]:
        AddLocalDataSetBC(bcDataSet)
    else:
        AddGlobalDataSetBC(bcDataSet)

def GetLocalDataSets():
    bcData = GetDocData()
    if bcData[ID_BC_DATA_SETS] is None:
        bcData[ID_BC_DATA_SETS] = c4d.BaseContainer()
    return bcData.GetContainerInstance(ID_BC_DATA_SETS)

def SetConnectedDataSet(bc):
    bcPrefs = GetWorldPrefs()
    return bcPrefs.SetContainer(ID_BC_CONNECTED_DATA_SET, bc)

def GetConnectedDataSet():
    bcPrefs = GetWorldPrefs()
    return bcPrefs.GetContainerInstance(ID_BC_CONNECTED_DATA_SET)

def IsConnected():
    return GetConnectedDataSet() is not None

def GetConnectedDataSetId():
    bcConnected = GetConnectedDataSet()
    if bcConnected is None:
        return -1
    return bcConnected.GetId()

def GetConnectedDataSetIdx():
    bcConnected = GetConnectedDataSet()
    if bcConnected is None:
        return 999999
    bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
    idxConnected = bcConnections.FindIndex(bcConnected.GetId())
    return idxConnected

def RemoveConnectedDataSet():
    bcPrefs = GetWorldPrefs()
    bcPrefs.RemoveData(ID_BC_CONNECTED_DATA_SET)

def RemoveLocalDataSet(id):
    bcData = GetDocData()
    bcLocalDataSets = bcData.GetContainerInstance(ID_BC_DATA_SETS)
    if bcLocalDataSets is None:
        return
    bcLocalDataSets.RemoveData(id)

def GetProjectScale():
    bcData = GetDocData()
    if bcData[ID_PROJECT_SCALE] is None:
        bcData[ID_PROJECT_SCALE] = 1.0
    return bcData[ID_PROJECT_SCALE]

def SetProjectScale(scale):
    bcData = GetDocData()
    bcData[ID_PROJECT_SCALE] = scale

def iter_objs(obj, root=True):
    if obj is None:
        return
    yield obj
    if obj.GetDown() is not None:
        yield from iter_objs(obj.GetDown(), False)
    if root:
        return
    obj = obj.GetNext()
    while obj is not None:
        yield from iter_objs(obj, True)
        obj = obj.GetNext()

def DetermineRigType(obj):
    if obj is None:
        return RIG_TYPE_UNKNOWN
    if obj.CheckType(c4d.Ojoint):
        return RIG_TYPE_ACTOR
    elif obj.CheckType(c4d.Olight):
        return RIG_TYPE_PROP
        #return RIG_TYPE_LIGHT # TODO enable as soon as JSON V4 gets used
    elif obj.CheckType(c4d.Ocamera):
        return RIG_TYPE_PROP
        #return RIG_TYPE_CAMERA  # TODO enable as soon as JSON V4 gets used
    elif obj.CheckType(c4d.Onull):
        objDown = obj.GetDown()
        if objDown is not None and objDown.CheckType(c4d.Ojoint):
            return RIG_TYPE_ACTOR
    else:
        tagPoseMorph = obj.GetTag(c4d.Tposemorph)
        if tagPoseMorph is not None:
            return RIG_TYPE_ACTOR_FACE
    return RIG_TYPE_PROP

def DetermineRigTypeOptions(obj):
    if obj is None:
        return RIG_TYPE_ACTOR | RIG_TYPE_ACTOR_FACE | RIG_TYPE_PROP # | RIG_TYPE_LIGHT | RIG_TYPE_CAMERA
    types = RIG_TYPE_PROP
    if obj.CheckType(c4d.Ojoint):
        types |= RIG_TYPE_ACTOR
    elif obj.CheckType(c4d.Olight):
        #types |= RIG_TYPE_LIGHT
        pass # TODO enable as soon as JSON V4 gets used
    elif obj.CheckType(c4d.Ocamera):
        #types |= RIG_TYPE_CAMERA
        pass # TODO enable as soon as JSON V4 gets used
    elif obj.CheckType(c4d.Onull):
        objDown = obj.GetDown()
        if objDown is not None and objDown.CheckType(c4d.Ojoint):
            types |= RIG_TYPE_ACTOR
    else:
        tagPoseMorph = obj.GetTag(c4d.Tposemorph)
        if tagPoseMorph is not None:
            types |= RIG_TYPE_ACTOR_FACE
    return types

def RigTypeToEntitiesString(rigType):
    if rigType is None:
        return 'UNKNOWN'
    if rigType & RIG_TYPE_ACTOR:
        name = 'Actors'
    elif rigType & RIG_TYPE_ACTOR_FACE:
        name = 'Faces'
    elif rigType & RIG_TYPE_LIGHT:
        name = 'Lights'
    elif rigType & RIG_TYPE_CAMERA:
        name = 'Cameras'
    else:
        name = 'Props'
    return name

def RigTypeToEntitiesBcId(rigType):
    if rigType & RIG_TYPE_ACTOR:
        idEntitiesBc = ID_BC_DATASET_ACTORS
    elif rigType & RIG_TYPE_ACTOR_FACE:
        idEntitiesBc = ID_BC_DATASET_ACTORS
    elif rigType & RIG_TYPE_LIGHT:
        idEntitiesBc = ID_BC_DATASET_LIGHTS
    elif rigType & RIG_TYPE_CAMERA:
        idEntitiesBc = ID_BC_DATASET_CAMERAS
    else:
        idEntitiesBc = ID_BC_DATASET_PROPS
    return idEntitiesBc

def IfTagAdd(tags, obj):
    tag = obj.GetTag(PLUGIN_ID_TAG)
    if tag is not None:
        tags.append(tag)

def AddTags(tags, obj):
    if obj is None:
        return
    while obj:
        IfTagAdd(tags, obj)
        AddTags(tags, obj.GetDown())
        obj = obj.GetNext()

def GetTagList():
    tags = []
    doc = c4d.documents.GetActiveDocument()
    AddTags(tags, doc.GetFirstObject())
    return tags

def StoreAvailableEntitiesInDataSet(dataScene, bcDataSet, fps=60.0):
    bcDataSet[ID_BC_DATASET_LIVE_FPS] = fps
    bcDataSet[ID_BC_DATASET_NUM_ACTORS] = 0
    bcDataSet[ID_BC_DATASET_NUM_SUITS] = 0
    bcDataSet[ID_BC_DATASET_NUM_GLOVES] = 0
    bcDataSet[ID_BC_DATASET_NUM_FACES] = 0
    bcActors = bcDataSet.GetContainerInstance(ID_BC_DATASET_ACTORS)
    bcActors.FlushAll()
    actors = dataScene['actors']
    for idxActor, actor in enumerate(actors):
        nameActor = actor['name']
        dataColor = actor['color']
        color = c4d.Vector(dataColor[0] / 255.0, dataColor[1] / 255.0, dataColor[2] / 255.0)
        hasSuit = False
        hasGloveLeft = False
        hasGloveRight = False
        hasFace = False
        bcDataSet[ID_BC_DATASET_NUM_ACTORS] += 1
        if actor['meta']['hasBody']:
            bcDataSet[ID_BC_DATASET_NUM_SUITS] += 1
            hasSuit = True
        if actor['meta']['hasLeftGlove']:
            bcDataSet[ID_BC_DATASET_NUM_GLOVES] += 1
            hasGloveLeft = True
        if actor['meta']['hasRightGlove']:
            bcDataSet[ID_BC_DATASET_NUM_GLOVES] += 1
            hasGloveRight = True
        if actor['meta']['hasFace']:
            bcDataSet[ID_BC_DATASET_NUM_FACES] += 1
            hasFace = True
        bcActors.SetContainer(idxActor, BaseContainerActor(nameActor, color, hasSuit, hasGloveLeft, hasGloveRight, hasFace))
    bcDataSet[ID_BC_DATASET_NUM_LIGHTS] = 0
    bcLights = bcDataSet.GetContainerInstance(ID_BC_DATASET_LIGHTS)
    bcLights.FlushAll()
    lights = []
    for idxLight, light in enumerate(lights):
        pass
    bcDataSet[ID_BC_DATASET_NUM_CAMERAS] = 0
    bcCameras = bcDataSet.GetContainerInstance(ID_BC_DATASET_CAMERAS)
    bcCameras.FlushAll()
    cameras = []
    for idxCamera, camera in enumerate(cameras):
        pass
    bcDataSet[ID_BC_DATASET_NUM_PROPS] = 0
    bcProps = bcDataSet.GetContainerInstance(ID_BC_DATASET_PROPS)
    bcProps.FlushAll()
    props = dataScene['props']
    for idxProp, prop in enumerate(props):
        bcDataSet[ID_BC_DATASET_NUM_PROPS] += 1
        nameProp = prop['name']
        dataColor = prop['color']
        color = c4d.Vector(dataColor[0] / 255.0, dataColor[1] / 255.0, dataColor[2] / 255.0)
        bcProps.SetContainer(idxProp, BaseContainerProp(nameProp, color))

def StoreAvailableEntitiesInConnectedDataSet(data, fps=60.0):
    bcConnected = GetConnectedDataSet()
    StoreAvailableEntitiesInDataSet(data, bcConnected, fps)

def ConnectedDataSetStreamLost():
    bcConnected = GetConnectedDataSet()
    bcConnected[ID_BC_DATASET_LIVE_FPS] = 0.0
    bcConnected[ID_BC_DATASET_NUM_ACTORS] = 0
    bcConnected[ID_BC_DATASET_NUM_SUITS] = 0
    bcConnected[ID_BC_DATASET_NUM_GLOVES] = 0
    bcConnected[ID_BC_DATASET_NUM_FACES] = 0
    bcActors = bcConnected.GetContainerInstance(ID_BC_DATASET_ACTORS)
    bcActors.FlushAll()
    bcConnected[ID_BC_DATASET_NUM_LIGHTS] = 0
    bcLights = bcConnected.GetContainerInstance(ID_BC_DATASET_LIGHTS)
    bcLights.FlushAll()
    bcConnected[ID_BC_DATASET_NUM_CAMERAS] = 0
    bcCameras = bcConnected.GetContainerInstance(ID_BC_DATASET_CAMERAS)
    bcCameras.FlushAll()
    bcConnected[ID_BC_DATASET_NUM_PROPS] = 0
    bcProps = bcConnected.GetContainerInstance(ID_BC_DATASET_PROPS)
    bcProps.FlushAll()

def ReadDataSet(filename):
    dataCompressed = None
    with open(filename, mode='rb') as f:
        dataCompressed = f.read()
        f.close()
    dataJSON = lz4.frame.decompress(dataCompressed, return_bytearray=True, return_bytes_read=False)
    data = json.loads(dataJSON)
    return data

def InitBaseContainer():
    bcConnections = GetPrefsContainer(ID_BC_CONNECTIONS)
    if len(bcConnections) < 1:
        AddConnectionBc(BaseContainerConnection())
    enabled = GetPref(ID_DLGMNGR_GROUP_CONNECTIONS)
    if enabled is None:
        SetPref(ID_DLGMNGR_GROUP_CONNECTIONS, True)
    enabled = GetPref(ID_DLGMNGR_GROUP_GLOBAL_DATA)
    if enabled is None:
        SetPref(ID_DLGMNGR_GROUP_GLOBAL_DATA, False)
    enabled = GetPref(ID_DLGMNGR_GROUP_LOCAL_DATA)
    if enabled is None:
        SetPref(ID_DLGMNGR_GROUP_LOCAL_DATA, False)
    enabled = GetPref(ID_DLGMNGR_GROUP_CONTROL)
    if enabled is None:
        SetPref(ID_DLGMNGR_GROUP_CONTROL, True)
    enabled = GetPref(ID_DLGMNGR_GROUP_PLAYER)
    if enabled is None:
        SetPref(ID_DLGMNGR_GROUP_PLAYER, True)
    enabled = GetPref(ID_DLGMNGR_GROUP_COMMAND_API)
    if enabled is None:
        SetPref(ID_DLGMNGR_GROUP_COMMAND_API, False)
    value = GetPref(ID_DLGSAVE_CREATE_IN_TAKE)
    if value is None:
        SetPref(ID_DLGSAVE_CREATE_IN_TAKE, True)
    value = GetPref(ID_DLGSAVE_ACTIVATE_NEW_TAKE)
    if value is None:
        SetPref(ID_DLGSAVE_ACTIVATE_NEW_TAKE, False)
    value = GetPref(ID_DLGSAVE_WIPE_EXISTING_ANIMATION)
    if value is None:
        SetPref(ID_DLGSAVE_WIPE_EXISTING_ANIMATION, True)
    value = GetPref(ID_DLGSAVE_TIMING)
    if value is None:
        SetPref(ID_DLGSAVE_TIMING, 0)
    value = GetPref(ID_DLGSAVE_FRAME_SKIP)
    if value is None:
        SetPref(ID_DLGSAVE_FRAME_SKIP, 1)
    value = GetPref(ID_DLGSAVE_LENGTH)
    if value is None:
        SetPref(ID_DLGSAVE_LENGTH, 0)
    value = GetPref(ID_DLGSAVE_SET_KEYFRAMES_AUTOFORWARD)
    if value is None:
        SetPref(ID_DLGSAVE_SET_KEYFRAMES_AUTOFORWARD, True)
    value = GetPref(ID_DLGSAVE_USE_NEW_DATASET)
    if value is None:
        SetPref(ID_DLGSAVE_USE_NEW_DATASET, False)
    value = GetPref(ID_TAG_SELECTED_IN_MANAGER)
    if value is None:
        SetPref(ID_TAG_SELECTED_IN_MANAGER, False)
    value = GetPref(ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS)
    if value is None:
        SetPref(ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS, False)

def JSONQuaternionToMatrix(r):
    x = r['x']
    y = r['y']
    z = r['z']
    w = -r['w']
    xx = x * x
    xy = x * y
    xz = x * z
    xw = x * w
    yy = y * y
    yz = y * z
    yw = y * w
    zz = z * z
    zw = z * w
    v1 = c4d.Vector()
    v2 = c4d.Vector()
    v3 = c4d.Vector()
    vOff = c4d.Vector()
    v1.x = 1 - 2 * (yy + zz)
    v1.y =     2 * (xy - zw)
    v1.z =     2 * (xz + yw)
    v2.x =     2 * (xy + zw)
    v2.y = 1 - 2 * (xx + zz)
    v2.z =     2 * (yz - xw)
    v3.x =     2 * (xz - yw)
    v3.y =     2 * (yz + xw)
    v3.z = 1 - 2 * (xx + yy)
    newMatrix = c4d.Matrix(vOff, v1, v2, v3)
    return newMatrix.GetNormalized()

g_timingMin = 1000000000000.0
g_timingMax = 0.0
def timing(f):
    def wrapTiming(*args, **kwargs):
        time1 = time.clock()
        ret = f(*args, **kwargs)
        time2 = time.clock()
        timeDiff = (time2-time1)*1000.0
        global g_timingMax, g_timingMin
        g_timingMin = min(g_timingMin, timeDiff)
        g_timingMax = max(g_timingMax, timeDiff)
        print('T {} ms  {}  {}'.format(timeDiff, g_timingMin, g_timingMax))
        return ret
    return wrapTiming
