'''Various utility functions.'''

import hashlib
import json
import time
import webbrowser
from ctypes import pythonapi, c_void_p, py_object

__USE_LZ4__ = True
try:
    import lz4.frame as lz4f
except ImportError:
    __USE_LZ4__ = False

import c4d

import rokoko_ids as rid


# With the introduction of Python 3 in C4D R23 integers changed quite bit in
# Python.
# The return value of hash() can no longer be used directly as ID for
# BaseContainers (it's too wide/large).

def Hash31(s):
    '''Return a hash value cut to 31 bits.'''

    sha = hashlib.sha1()
    sha.update(s.encode("utf-8"))
    r = int(sha.hexdigest(), 16)
    r &= 0x7FFFFFFF
    return r


# Depending on C4D version have a common "function pointer" to always use the
# correct hash function.
if c4d.GetC4DVersion() // 1000 < 23:
    MyHash = hash
else:
    MyHash = Hash31


# In Rokoko Studio Live plugin most communication between different modules and
# "sub plugins" relies on SpecialEventAdd().
# SpecialEventAdd() allows to send a event message to be received in
# CoreMessage().
# Unfortunately including parameters into the event message is a bit limited
# in C4D's Python API (more or less limited to two numerical values).
# And with C4D R23 and Python 3, the way to access these parameters changed.
def GetCoreMessageParam23(msg, id=c4d.BFM_CORE_PAR1):
    '''C4D R23+: Get Parameter from an event message'''

    if msg.GetType(id) != c4d.DA_VOID:
        return 0
    vptr = msg.GetVoid(id)
    if vptr is None:
        return 0
    pythonapi.PyCapsule_GetPointer.restype = c_void_p
    pythonapi.PyCapsule_GetPointer.argtypes = [py_object]
    return pythonapi.PyCapsule_GetPointer(vptr, None)


def GetCoreMessageParamOld(msg, id=c4d.BFM_CORE_PAR1):
    '''C4D <R23: Get Parameter from an event message'''

    vptr = msg.GetVoid(id)
    pythonapi.PyCObject_AsVoidPtr.restype = c_void_p
    pythonapi.PyCObject_AsVoidPtr.argtypes = [py_object]
    return pythonapi.PyCObject_AsVoidPtr(vptr)


# Depending on C4D version have a common "function pointer" to always use the
# correct version.
if c4d.GetC4DVersion() // 1000 >= 23:
    GetCoreMessageParam = GetCoreMessageParam23
else:
    GetCoreMessageParam = GetCoreMessageParamOld


def iter_objs(obj, root=True):
    '''An iterator for an object tree.'''

    # If end of branch reached
    if obj is None:
        return

    yield obj

    # Iterate all children, if any
    if obj.GetDown() is not None:
        yield from iter_objs(obj.GetDown(), False)

    # If root, do not consider neighbors on same hierarchy level
    if root:
        return  # call it done on this level

    # Iterate neighbors
    obj = obj.GetNext()
    while obj is not None:
        yield from iter_objs(obj, True)  # handle child tree as new tree
        obj = obj.GetNext()


# TODO: While I always appreciate writing same stuff in multiple ways multiple
#       times, I should really stop doing so...

def IfTagAdd(tags, obj):
    '''Append Rokoko tag, if found, to list'''

    tag = obj.GetTag(rid.PLUGIN_ID_TAG)
    if tag is not None:
        tags.append(tag)


def AddTags(tags, obj):
    '''Recursively add tags to a list'''

    if obj is None:
        return
    while obj:
        IfTagAdd(tags, obj)
        AddTags(tags, obj.GetDown())
        obj = obj.GetNext()


def GetTagList():
    '''Iterate the scene and return a list of all Rokoko tags'''

    tags = []
    doc = c4d.documents.GetActiveDocument()
    AddTags(tags, doc.GetFirstObject())
    return tags


def JSONQuaternionToMatrix(r):
    '''Convert a quaternion from Studio's motion data into a C4D transformation
    matrix.
    '''

    x = r["x"]
    y = r["y"]
    z = r["z"]
    # w: Minus takes care of different orientation of character in Studio
    w = -r["w"]
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
    v1.y = 2 * (xy - zw)
    v1.z = 2 * (xz + yw)
    v2.x = 2 * (xy + zw)
    v2.y = 1 - 2 * (xx + zz)
    v2.z = 2 * (yz - xw)
    v3.x = 2 * (xz - yw)
    v3.y = 2 * (yz + xw)
    v3.z = 1 - 2 * (xx + yy)
    newMatrix = c4d.Matrix(vOff, v1, v2, v3)
    return newMatrix.GetNormalized()


# Preferences
#
# Rokoko Studio Live plugin needs to store vaious data
# (connection data, clip libraries, widget states and parameters,...).
#
# In C4D almost everything (well, almost all parameters) are stored inside
# BaseContainers in one way or another. Often stacking BaseContainers inside
# each other.
# For example in C4D's (world) preferences, a plugin can store its preferences
# parameters by simply storing a BaseContainer with plugin ID inside preferenes
# BaseContainer.
# In the same way a plugin can store parameters in documents or tags.
#
# Here's an overview of what gets sttored where:
# World preferences:
#   - Plugin enabled
#   - Manager UI states (like tab enabling, checkboxes,...)
#   - Global clip library
#   - Mapping presets (for actors and faces)
# Document:
#   - Project clip library
# Tag:
#   - Tag's parameters (of course...)
#   - Additonal data like T-Pose matrices, internal flags, ...


def GetDefaultPrefContainer():
    '''Returns a BaseContainer with default preferences values.

    TODO: Use this instead of current implementation. (it grew... :( )
    '''
    return c4d.BaseContainer()


def GetWorldPrefs():
    '''Return plugin's BaseContainer from world preferences.'''

    # Get a reference to plugin's BaseContainer.
    bcWorldPrefs = c4d.plugins.GetWorldPluginData(
        rid.PLUGIN_ID_COMMAND_MANAGER)

    # If the plugin has no container in preferences, yet, create a new one.
    if bcWorldPrefs is None:
        bcWorldPrefs = GetDefaultPrefContainer()
        c4d.plugins.SetWorldPluginData(
            rid.PLUGIN_ID_COMMAND_MANAGER, bcWorldPrefs, True)
        # Rather safe than sorry, so we work with the correct instance
        bcWorldPrefs = c4d.plugins.GetWorldPluginData(
            rid.PLUGIN_ID_COMMAND_MANAGER)
    return bcWorldPrefs


def GetPrefsContainer(idBc):
    '''Return a BaseContainer _reference_ (or instance) from plugin's
    BaseContainer in preferences.

    Function creates the BaseContainer.
    Only exception would be a failure to retrieve plugin's preferences,
    but then the plugin most likely has completely different problems, than
    just not being able to read a preference parameter.
    '''

    bcWorldPrefs = GetWorldPrefs()
    if bcWorldPrefs is None:
        return None  # something went sincerely wrong

    # Try to get a reference to the requestedd BaseContainer
    bc = bcWorldPrefs.GetContainerInstance(idBc)
    if bc is None:
        # Requested container does not exist, yet, create a new one
        bc = c4d.BaseContainer()
        bcWorldPrefs.SetContainer(idBc, bc)
        c4d.plugins.SetWorldPluginData(
            rid.PLUGIN_ID_COMMAND_MANAGER, bcWorldPrefs, add=True)
        # Just to be sure we return the correct instance
        bc = bcWorldPrefs.GetContainerInstance(idBc)

    return bc


def SetPref(id, val):
    '''Sets a numerical value (+some others, careful!) in plugin's preferences.
    '''

    bcWorldPrefs = GetWorldPrefs()
    bcWorldPrefs[id] = val
    c4d.plugins.SetWorldPluginData(
        rid.PLUGIN_ID_COMMAND_MANAGER, bcWorldPrefs, add=True)


def GetPref(id):
    '''Reads a numerical value from plugin's preferences.'''

    bcWorldPrefs = GetWorldPrefs()
    return bcWorldPrefs[id]


def InitBaseContainer():
    ''' Iniatialize stuff in global preferences.
    A classic..., see above TODO.
    '''

    bcConnections = GetPrefsContainer(rid.ID_BC_CONNECTIONS)
    if len(bcConnections) < 1:
        AddConnectionBc(BaseContainerConnection())
    enabled = GetPref(rid.ID_DLGMNGR_GROUP_CONNECTIONS)
    if enabled is None:
        SetPref(rid.ID_DLGMNGR_GROUP_CONNECTIONS, True)
    enabled = GetPref(rid.ID_DLGMNGR_GROUP_GLOBAL_DATA)
    if enabled is None:
        SetPref(rid.ID_DLGMNGR_GROUP_GLOBAL_DATA, False)
    enabled = GetPref(rid.ID_DLGMNGR_GROUP_LOCAL_DATA)
    if enabled is None:
        SetPref(rid.ID_DLGMNGR_GROUP_LOCAL_DATA, False)
    enabled = GetPref(rid.ID_DLGMNGR_GROUP_CONTROL)
    if enabled is None:
        SetPref(rid.ID_DLGMNGR_GROUP_CONTROL, True)
    enabled = GetPref(rid.ID_DLGMNGR_GROUP_PLAYER)
    if enabled is None:
        SetPref(rid.ID_DLGMNGR_GROUP_PLAYER, True)
    enabled = GetPref(rid.ID_DLGMNGR_GROUP_COMMAND_API)
    if enabled is None:
        SetPref(rid.ID_DLGMNGR_GROUP_COMMAND_API, False)
    value = GetPref(rid.ID_DLGSAVE_TARGET_TAKE)
    if value is None:
        SetPref(rid.ID_DLGSAVE_TARGET_TAKE, 0)
    value = GetPref(rid.ID_DLGSAVE_ACTIVATE_NEW_TAKE)
    if value is None:
        SetPref(rid.ID_DLGSAVE_ACTIVATE_NEW_TAKE, False)
    value = GetPref(rid.ID_DLGSAVE_WIPE_EXISTING_ANIMATION)
    if value is None:
        SetPref(rid.ID_DLGSAVE_WIPE_EXISTING_ANIMATION, True)
    value = GetPref(rid.ID_DLGSAVE_TIMING)
    if value is None:
        SetPref(rid.ID_DLGSAVE_TIMING, 0)
    value = GetPref(rid.ID_DLGSAVE_FRAME_SKIP)
    if value is None:
        SetPref(rid.ID_DLGSAVE_FRAME_SKIP, 1)
    value = GetPref(rid.ID_DLGSAVE_LENGTH)
    if value is None:
        SetPref(rid.ID_DLGSAVE_LENGTH, 0)
    value = GetPref(rid.ID_DLGSAVE_SET_KEYFRAMES_AUTOFORWARD)
    if value is None:
        SetPref(rid.ID_DLGSAVE_SET_KEYFRAMES_AUTOFORWARD, True)
    value = GetPref(rid.ID_DLGSAVE_USE_NEW_DATASET)
    if value is None:
        SetPref(rid.ID_DLGSAVE_USE_NEW_DATASET, False)
    value = GetPref(rid.ID_TAG_SELECTED_IN_MANAGER)
    if value is None:
        SetPref(rid.ID_TAG_SELECTED_IN_MANAGER, False)
    value = GetPref(rid.ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS)
    if value is None:
        SetPref(rid.ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS, False)


def GetDocData():
    '''Return plugin's BaseContainer from document.'''

    # Get a reference to plugin's BaseContainer.
    doc = c4d.documents.GetActiveDocument()
    bc = doc.GetDataInstance().GetContainerInstance(
        rid.PLUGIN_ID_COMMAND_MANAGER)

    # If the plugin has no container in document, yet, create a new one.
    if bc is None:
        doc.GetDataInstance().SetContainer(
            rid.PLUGIN_ID_COMMAND_MANAGER, c4d.BaseContainer())
        # make sure, we are returning correct reference
        bc = doc.GetDataInstance().GetContainerInstance(
            rid.PLUGIN_ID_COMMAND_MANAGER)
    return bc


def GetProjectScale():
    '''Project scale can be set in Manager dialog.
    Read project scale parameter from document.
    '''

    bcData = GetDocData()
    if bcData[rid.ID_PROJECT_SCALE] is None:
        bcData[rid.ID_PROJECT_SCALE] = 1.0
    return bcData[rid.ID_PROJECT_SCALE]


def SetProjectScale(scale):
    '''Set project scale parameter in document.'''

    bcData = GetDocData()
    bcData[rid.ID_PROJECT_SCALE] = scale


# Entities and Data Sets

# Entities
#
# In this plugin "entities" are actors, faces or props (in later versions
# probably more...).
# Basically one section of Rokoko's motion data that is assigned to
# a single Rokoko tag to animate its host object(s).
# E.g. an Actor (with suit and/or gloves) referenced by name or index.
# Entities are managed in BaseContainers, which get stored inside data set
# containers.
#
# Entity containers store some meta data (all as received from Studio):
#   - Type (Actor, Face, Prop)
#   - Name
#   - Color
# In case of an Acor, it also stores, which parts of an actor (suit, gloves,
# face) are available in the referenced motion data.


def BaseContainerEntity(
    name,
    entityType=0,
    color=c4d.Vector(0.0),
    hasSuit=False,
    hasGloveLeft=False,
    hasGloveRight=False,
    hasFace=False
):
    '''Create a new entity BaseContainer.'''

    bc = c4d.BaseContainer()

    # Set entity values
    bc[rid.ID_BC_ENTITY_NAME] = name
    bc[rid.ID_BC_ENTITY_COLOR] = color
    bc[rid.ID_BC_ENTITY_TYPE] = entityType
    bc[rid.ID_BC_ENTITY_HAS_SUIT] = hasSuit
    bc[rid.ID_BC_ENTITY_HAS_GLOVE_LEFT] = hasGloveLeft
    bc[rid.ID_BC_ENTITY_HAS_GLOVE_RIGHT] = hasGloveRight
    bc[rid.ID_BC_ENTITY_HAS_FACE] = hasFace
    return bc


def BaseContainerActor(
    name,
    color=c4d.Vector(0.0),
    hasSuit=False,
    hasGloveLeft=False,
    hasGloveRight=False,
    hasFace=False
):
    '''Create a new Actor BaseContainer.'''

    return BaseContainerEntity(
        name, 0, color, hasSuit, hasGloveLeft, hasGloveRight, hasFace)


def BaseContainerProp(name, color=c4d.Vector(0.0)):
    '''Create a new Prop BaseContainer.'''

    return BaseContainerEntity(name, 1, color)


def BaseContainerLight(name, color=c4d.Vector(0.0)):
    '''Create a new Light BaseContainer (currently not in use).'''

    return BaseContainerEntity(name, 2, color)


def BaseContainerCamera(name, color=c4d.Vector(0.0)):
    '''Create a new Camera BaseContainer (currently not in use).'''

    return BaseContainerEntity(name, 3, color)


# Data Sets
#
# Data sets are BaseContainers, which refer to Rokoko motion data in any form.
# This can be "connections" to Rokoko live stream (currently code allows only
# one active at a time) or clips from a file (usually just called data set in
# code).
#
# The BaseContainer stores all information to find the motion data, plus
# additional meta data.
#
# For live connection:
#   - port to receive from Rokoko Studio.
#   In this case the data set is often called connection inside the code.
# For clips:
#   - filepath
# Meta data: see below
#
# Data sets are either stored in preferences (connections and global clip
# library) or inside the document (project clip library).
# Data sets are referred to by their BaseContainer ID
# (which is a hash value of certain values of its content).


def BaseContainerConnection(
    name="Studio Connection",
    port="14043",
    autoConnect=False,
    ipCommandApi="127.0.0.1",
    portCommandApi="14053",
    keyCommandApi="1234"
):
    '''Create a live connection data set BaseContainer.'''

    bc = c4d.BaseContainer()

    # Set values relevant for connection data sets
    bc[rid.ID_BC_DATASET_NAME] = name
    # Type: 0 - connection, 1 - file global, 2 - file local
    bc[rid.ID_BC_DATASET_TYPE] = 0
    bc[rid.ID_BC_DATASET_CONNECTED] = False  # not used
    bc[rid.ID_BC_DATASET_AVAILABLE_IN_DOC] = True  # not used anymore
    bc[rid.ID_BC_DATASET_LIVE_PORT] = port
    bc[rid.ID_BC_DATASET_LIVE_AUTOCONNECT] = autoConnect
    bc[rid.ID_BC_DATASET_LIVE_FPS] = 0.0  # FPS transmitted by Studio
    bc[rid.ID_BC_DATASET_COMMANDAPI_IP] = ipCommandApi
    bc[rid.ID_BC_DATASET_COMMANDAPI_PORT] = portCommandApi
    bc[rid.ID_BC_DATASET_COMMANDAPI_KEY] = keyCommandApi
    bc[rid.ID_BC_DATASET_FILENAME] = ''
    bc[rid.ID_BC_DATASET_IS_LOCAL] = False
    bc[rid.ID_BC_DATASET_NUM_ACTORS] = 0
    bc[rid.ID_BC_DATASET_NUM_SUITS] = 0
    bc[rid.ID_BC_DATASET_NUM_GLOVES] = 0
    bc[rid.ID_BC_DATASET_NUM_FACES] = 0
    bc[rid.ID_BC_DATASET_NUM_LIGHTS] = 0
    bc[rid.ID_BC_DATASET_NUM_CAMERAS] = 0
    bc[rid.ID_BC_DATASET_NUM_PROPS] = 0
    # for Actor entity containers
    bc.SetContainer(rid.ID_BC_DATASET_ACTORS, c4d.BaseContainer())
    # for Light entity containers (currently not in use)
    bc.SetContainer(rid.ID_BC_DATASET_LIGHTS, c4d.BaseContainer())
    # for Camera entity containers (currently not in use)
    bc.SetContainer(rid.ID_BC_DATASET_CAMERAS, c4d.BaseContainer())
    # for Prop entity containers
    bc.SetContainer(rid.ID_BC_DATASET_PROPS, c4d.BaseContainer())

    # Set data set ID
    bc.SetId(
        MyHash(name + port + ipCommandApi + portCommandApi + keyCommandApi))
    return bc


def BaseContainerDataSet(
    name,
    file,
    numActors=0,
    numBody=0,
    numHands=0,
    numFaces=0,
    numLights=0,
    numCameras=0,
    numProps=0,
    availableInDocument=True,
    isLocal=False
):
    '''Create a clip data set BaseContainer.'''

    bc = c4d.BaseContainer()

    # Set values relevant for file referencing data sets
    bc[rid.ID_BC_DATASET_NAME] = name
    # Type: 0 - connection, 1 - file
    bc[rid.ID_BC_DATASET_TYPE] = 1
    bc[rid.ID_BC_DATASET_CONNECTED] = False
    bc[rid.ID_BC_DATASET_AVAILABLE_IN_DOC] = availableInDocument
    bc[rid.ID_BC_DATASET_LIVE_PORT] = ''
    bc[rid.ID_BC_DATASET_LIVE_AUTOCONNECT] = ''
    bc[rid.ID_BC_DATASET_LIVE_FPS] = 0.0
    bc[rid.ID_BC_DATASET_COMMANDAPI_IP] = ''
    bc[rid.ID_BC_DATASET_COMMANDAPI_PORT] = ''
    bc[rid.ID_BC_DATASET_COMMANDAPI_KEY] = ''
    # filepath to motion data clip
    bc[rid.ID_BC_DATASET_FILENAME] = file
    # data set resides in project's clip library
    bc[rid.ID_BC_DATASET_IS_LOCAL] = isLocal
    bc[rid.ID_BC_DATASET_NUM_ACTORS] = numActors
    bc[rid.ID_BC_DATASET_NUM_SUITS] = numBody
    bc[rid.ID_BC_DATASET_NUM_GLOVES] = numHands
    bc[rid.ID_BC_DATASET_NUM_FACES] = numFaces
    bc[rid.ID_BC_DATASET_NUM_LIGHTS] = numLights
    bc[rid.ID_BC_DATASET_NUM_CAMERAS] = numCameras
    bc[rid.ID_BC_DATASET_NUM_PROPS] = numProps
    bc.SetContainer(rid.ID_BC_DATASET_ACTORS, c4d.BaseContainer())
    bc.SetContainer(rid.ID_BC_DATASET_LIGHTS, c4d.BaseContainer())
    bc.SetContainer(rid.ID_BC_DATASET_CAMERAS, c4d.BaseContainer())
    bc.SetContainer(rid.ID_BC_DATASET_PROPS, c4d.BaseContainer())

    # Set data set ID
    bc.SetId(MyHash(name + file + str(isLocal)))
    return bc


def GetDataSetFromId(idDataSet):
    '''Returns the data set BaseContainer belonging to a data set ID.

    Returns None, if the data set is currently not available
    (like a live connection ID, but plugin is not connected).
    '''

    # If id of currently connected data set
    bcConnected = GetConnectedDataSet()
    if bcConnected is not None and idDataSet == bcConnected.GetId():
        return bcConnected

    # Try to find ID in global clip library
    bcDataSetsGlobal = GetPrefsContainer(rid.ID_BC_DATA_SETS)
    bcDataSet = bcDataSetsGlobal.GetData(idDataSet)
    if bcDataSet is not None:
        return bcDataSet

    # Try to find ID in project clip library
    bcDataSetsLocal = GetLocalDataSets()
    bcDataSet = bcDataSetsLocal.GetData(idDataSet)
    if bcDataSet is not None:
        return bcDataSet

    # Data set currently not available
    return None


def AddConnection(name, port):
    '''By specifying a port number create a new connection data set in
    preferences.
    '''

    # Get connections library (currently always containing only one connection)
    bcWorldConnections = GetPrefsContainer(rid.ID_BC_CONNECTIONS)

    # Create connection
    bcConnection = BaseContainerConnection(name, port)

    # Store in connections library in preferences
    bcWorldConnections[bcConnection.GetId()] = bcConnection
    SetPref(rid.ID_BC_CONNECTIONS, bcWorldConnections)


def AddConnectionBc(bcConnection):
    '''Store the provided connection data set in preferences.'''

    # Get connections library (currently always containing only one connection)
    bcWorldConnections = GetPrefsContainer(rid.ID_BC_CONNECTIONS)

    # Store in connections library in preferences
    bcWorldConnections[bcConnection.GetId()] = bcConnection
    SetPref(rid.ID_BC_CONNECTIONS, bcWorldConnections)


def RemoveConnection(id):
    '''Remove a connection data set from references.'''

    # Get connections library (currently always containing only one connection)
    bcWorldConnections = GetPrefsContainer(rid.ID_BC_CONNECTIONS)

    # Remove connection
    bcWorldConnections.RemoveData(id)

    # Store connections library in preferences
    SetPref(rid.ID_BC_CONNECTIONS, bcWorldConnections)


def AddGlobalDataSet(
    name,
    file,
    numBody=0,
    numHands=0,
    numFaces=0,
    numLights=0,
    numCameras=0,
    numProps=0,
    availableInDocument=True
):
    '''Create a new clip data set in global clip library.'''

    # Get global clip library
    bcWorldDataSets = GetPrefsContainer(rid.ID_BC_DATA_SETS)

    # Create data set
    bcDataSet = BaseContainerDataSet(
        name, file,
        numBody, numHands, numFaces, numLights, numCameras, numProps,
        availableInDocument,
        isLocal=False)

    # Store in global clip library in preferences
    bcWorldDataSets[bcDataSet.GetId()] = bcDataSet
    SetPref(rid.ID_BC_DATA_SETS, bcWorldDataSets)


def AddGlobalDataSetBC(bcDataSet):
    '''Store the provided clip data set in global clip library.'''

    # Get global clip library
    bcWorldDataSets = GetPrefsContainer(rid.ID_BC_DATA_SETS)

    # Store in global clip library in preferences
    bcWorldDataSets[bcDataSet.GetId()] = bcDataSet
    SetPref(rid.ID_BC_DATA_SETS, bcWorldDataSets)


def RemoveGlobalDataSet(id):
    '''Remove a clip data set from global clip library.'''

    # Get global clip library
    bcWorldDataSets = GetPrefsContainer(rid.ID_BC_DATA_SETS)

    # Remove data set
    bcWorldDataSets.RemoveData(id)

    # Store global clip library in preferences
    SetPref(rid.ID_BC_DATA_SETS, bcWorldDataSets)


def AddLocalDataSet(
    name,
    file,
    numBody=0,
    numHands=0,
    numFaces=0,
    numLights=0,
    numCameras=0,
    numProps=0,
    availableInDocument=True
):
    '''Create a new clip data set in project's clip library.'''

    # Get project's clip library
    bcData = GetDocData()
    if bcData[rid.ID_BC_DATA_SETS] is None:  # TODO: seems redundant here...
        bcData[rid.ID_BC_DATA_SETS] = c4d.BaseContainer()
    bcLocalDataSets = bcData.GetContainerInstance(rid.ID_BC_DATA_SETS)

    # Create data set
    bcDataSet = BaseContainerDataSet(
        name, file,
        numBody, numHands, numFaces, numLights, numCameras, numProps,
        availableInDocument,
        isLocal=True)

    # Store in project's clip library in document
    bcLocalDataSets[bcDataSet.GetId()] = bcDataSet


def AddLocalDataSetBC(bcDataSet):
    '''Store the provided clip data set in project's clip library.'''

    # Get project's clip library
    bcData = GetDocData()
    if bcData[rid.ID_BC_DATA_SETS] is None:  # TODO: seems redundant here...
        bcData[rid.ID_BC_DATA_SETS] = c4d.BaseContainer()
    bcLocalDataSets = bcData.GetContainerInstance(rid.ID_BC_DATA_SETS)

    # Store in project's clip library in document
    bcLocalDataSets[bcDataSet.GetId()] = bcDataSet

    # Mark current scene as changed (c4d will warn user when trying to quit
    # without saving)
    c4d.documents.GetActiveDocument().SetChanged()


def RemoveLocalDataSet(id):
    '''Remove a clip data set from project's clip library.'''

    # Get project's clip library
    bcData = GetDocData()
    bcLocalDataSets = bcData.GetContainerInstance(rid.ID_BC_DATA_SETS)
    if bcLocalDataSets is None:
        return

    # Remove clip's BaseContainer
    bcLocalDataSets.RemoveData(id)


def GetLocalDataSets():
    '''Returns BaseContainer with project clip library.'''

    bcData = GetDocData()

    # If no project clip library exists
    if bcData[rid.ID_BC_DATA_SETS] is None:
        # Create one
        bcData[rid.ID_BC_DATA_SETS] = c4d.BaseContainer()

    return bcData.GetContainerInstance(rid.ID_BC_DATA_SETS)


def AddDataSetBC(bcDataSet):
    '''Store the provided data set in either global or project's clip library.
    '''

    if bcDataSet[rid.ID_BC_DATASET_IS_LOCAL]:
        AddLocalDataSetBC(bcDataSet)
    else:
        AddGlobalDataSetBC(bcDataSet)


def RemoveDataSetBC(bcDataSet):
    '''Remove the provided data set from either global or project's clip
    library.
    '''

    idDataSet = bcDataSet.GetId()
    if bcDataSet[rid.ID_BC_DATASET_IS_LOCAL]:
        RemoveLocalDataSet(idDataSet)
    else:
        RemoveGlobalDataSet(idDataSet)


def SetConnectedDataSet(bc):
    '''Stores a copy of a connection data set as "the connected data set" in
    preferences.

    Upon connecting to Rokoko Studio a copy of the "active" connection data set
    is stored in a special place in preferences.
    Checking for this BaseContainer is an indicator of an active live
    connection (regardless of actual data being received).
    '''

    bcPrefs = GetWorldPrefs()
    return bcPrefs.SetContainer(rid.ID_BC_CONNECTED_DATA_SET, bc)


def GetConnectedDataSet():
    '''Returns the currently connected connection data set.

    Returns None if not connected.
    '''

    bcPrefs = GetWorldPrefs()
    return bcPrefs.GetContainerInstance(rid.ID_BC_CONNECTED_DATA_SET)


def IsConnected():
    '''Returns True, if connected.'''
    return GetConnectedDataSet() is not None


def GetConnectedDataSetId():
    '''Return ID of the connected data set.

    Returns -1, if not connected.
    '''

    bcConnected = GetConnectedDataSet()
    if bcConnected is None:
        return -1
    return bcConnected.GetId()


def GetConnectedDataSetIdx():
    '''Return BaseContainer index (_not_ ID!) of connected data set.

    Returns 999999, if not connected.
    TODO: I'm sure I had my reasons to not return -1,
          shouldn't occur anyway, since there always is one and only one
          connection.
    '''

    bcConnected = GetConnectedDataSet()
    if bcConnected is None:
        return 999999
    bcConnections = GetPrefsContainer(rid.ID_BC_CONNECTIONS)
    idxConnected = bcConnections.FindIndex(bcConnected.GetId())
    return idxConnected


def RemoveConnectedDataSet():
    '''Removes the copy of the connected data set from preferences.

    Upon disconnecting from Rokoko Studio the copy created during connection is
    removed again.
    '''

    bcPrefs = GetWorldPrefs()
    bcPrefs.RemoveData(rid.ID_BC_CONNECTED_DATA_SET)


def ReadDataSet(filename):
    '''Reads motion data from a file'''

    dataCompressed = None

    # Read data from file
    with open(filename, mode="rb") as f:
        dataCompressed = f.read()
        f.close()

    # Decompress JSON data
    if __USE_LZ4__:
        dataJSON = lz4f.decompress(
            dataCompressed, return_bytearray=True, return_bytes_read=False)
    else:
        dataJSON = dataCompressed

    # Decode data from JSON
    data = json.loads(dataJSON)
    return data


def StoreAvailableEntitiesInDataSet(dataScene, bcDataSet, fps=60.0):
    '''Determine information about all entities (actors, faces, props,...)
    contained in a given motion data frame and store it in the data set
    container.
    '''

    bcDataSet[rid.ID_BC_DATASET_LIVE_FPS] = fps

    # Actor
    # Reset all actor related data.
    bcDataSet[rid.ID_BC_DATASET_NUM_ACTORS] = 0
    bcDataSet[rid.ID_BC_DATASET_NUM_SUITS] = 0
    bcDataSet[rid.ID_BC_DATASET_NUM_GLOVES] = 0
    bcDataSet[rid.ID_BC_DATASET_NUM_FACES] = 0
    bcActors = bcDataSet.GetContainerInstance(rid.ID_BC_DATASET_ACTORS)
    bcActors.FlushAll()

    # Iterate all actors in motion data
    actors = dataScene["actors"]
    for idxActor, actor in enumerate(actors):
        nameActor = actor["name"]
        dataColor = actor.get("color", [128, 128, 128])
        color = c4d.Vector(dataColor[0] / 255.0,
                           dataColor[1] / 255.0,
                           dataColor[2] / 255.0)

        # Determine availability of body parts/devices in motion data
        hasSuit = False
        hasGloveLeft = False
        hasGloveRight = False
        hasFace = False
        bcDataSet[rid.ID_BC_DATASET_NUM_ACTORS] += 1
        if actor["meta"]["hasBody"]:
            bcDataSet[rid.ID_BC_DATASET_NUM_SUITS] += 1
            hasSuit = True
        if actor["meta"]["hasLeftGlove"]:
            bcDataSet[rid.ID_BC_DATASET_NUM_GLOVES] += 1
            hasGloveLeft = True
        if actor["meta"]["hasRightGlove"]:
            bcDataSet[rid.ID_BC_DATASET_NUM_GLOVES] += 1
            hasGloveRight = True
        if actor["meta"]["hasFace"]:
            bcDataSet[rid.ID_BC_DATASET_NUM_FACES] += 1
            hasFace = True

        # Store new actor entity in data set
        bcActors.SetContainer(idxActor, BaseContainerActor(nameActor,
                                                           color,
                                                           hasSuit,
                                                           hasGloveLeft,
                                                           hasGloveRight,
                                                           hasFace))

    # Lights (not yet supported)
    # Reset all light related data.
    bcDataSet[rid.ID_BC_DATASET_NUM_LIGHTS] = 0
    bcLights = bcDataSet.GetContainerInstance(rid.ID_BC_DATASET_LIGHTS)
    bcLights.FlushAll()
    # Iterate all lights in motion data
    lights = []  # dataScene[...]
    for idxLight, light in enumerate(lights):
        pass

    # Cameras (not yet supported)
    # Reset all camera related data.
    bcDataSet[rid.ID_BC_DATASET_NUM_CAMERAS] = 0
    bcCameras = bcDataSet.GetContainerInstance(rid.ID_BC_DATASET_CAMERAS)
    bcCameras.FlushAll()
    # Iterate all cameras in motion data
    cameras = []  # dataScene[...]
    for idxCamera, camera in enumerate(cameras):
        pass

    # Props
    # Reset all prop related data.
    bcDataSet[rid.ID_BC_DATASET_NUM_PROPS] = 0
    bcProps = bcDataSet.GetContainerInstance(rid.ID_BC_DATASET_PROPS)
    bcProps.FlushAll()

    # Iterate all props in motion data
    props = dataScene["props"]
    for idxProp, prop in enumerate(props):
        bcDataSet[rid.ID_BC_DATASET_NUM_PROPS] += 1
        nameProp = prop["name"]
        dataColor = prop["color"]
        color = c4d.Vector(dataColor[0] / 255.0,
                           dataColor[1] / 255.0,
                           dataColor[2] / 255.0)

        # Store new prop entity in data set
        bcProps.SetContainer(idxProp, BaseContainerProp(nameProp, color))


def StoreAvailableEntitiesInConnectedDataSet(data, fps=60.0):
    '''Shortcut to update information contained in live data.'''

    bcConnected = GetConnectedDataSet()
    StoreAvailableEntitiesInDataSet(data, bcConnected, fps)


def ConnectedDataSetStreamLost():
    '''Remove all entity data from connected data set.

    This is used for example, if Rokoko Studio stops the live stream
    (so Manager UI doesn't show stale entitiy information).
    '''

    # Get the currently connected data set
    bcConnected = GetConnectedDataSet()

    # Reset all entity related information (actujally all live stream related
    # information)
    bcConnected[rid.ID_BC_DATASET_LIVE_FPS] = 0.0
    bcConnected[rid.ID_BC_DATASET_NUM_ACTORS] = 0
    bcConnected[rid.ID_BC_DATASET_NUM_SUITS] = 0
    bcConnected[rid.ID_BC_DATASET_NUM_GLOVES] = 0
    bcConnected[rid.ID_BC_DATASET_NUM_FACES] = 0
    bcActors = bcConnected.GetContainerInstance(rid.ID_BC_DATASET_ACTORS)
    bcActors.FlushAll()
    bcConnected[rid.ID_BC_DATASET_NUM_LIGHTS] = 0
    bcLights = bcConnected.GetContainerInstance(rid.ID_BC_DATASET_LIGHTS)
    bcLights.FlushAll()
    bcConnected[rid.ID_BC_DATASET_NUM_CAMERAS] = 0
    bcCameras = bcConnected.GetContainerInstance(rid.ID_BC_DATASET_CAMERAS)
    bcCameras.FlushAll()
    bcConnected[rid.ID_BC_DATASET_NUM_PROPS] = 0
    bcProps = bcConnected.GetContainerInstance(rid.ID_BC_DATASET_PROPS)
    bcProps.FlushAll()


def DetermineRigType(obj):
    '''Auto determine tag type based on given object.'''

    if obj is None:
        return rid.RIG_TYPE_UNKNOWN
    if obj.CheckType(c4d.Ojoint):
        return rid.RIG_TYPE_ACTOR
    elif obj.CheckType(c4d.Olight):
        return rid.RIG_TYPE_PROP
        # return RIG_TYPE_LIGHT  # TODO: enable as soon as JSON V4 gets used
    elif obj.CheckType(c4d.Ocamera):
        return rid.RIG_TYPE_PROP
        # return RIG_TYPE_CAMERA  # TODO: enable as soon as JSON V4 gets used
    elif obj.CheckType(c4d.Onull):
        # Allow a Null object to be root of a rig
        objDown = obj.GetDown()
        if objDown is not None and objDown.CheckType(c4d.Ojoint):
            return rid.RIG_TYPE_ACTOR
    else:
        tagPoseMorph = obj.GetTag(c4d.Tposemorph)
        if tagPoseMorph is not None:
            return rid.RIG_TYPE_ACTOR_FACE
    return rid.RIG_TYPE_PROP


def DetermineRigTypeOptions(obj):
    '''Return all type options for a tag basded on given object.

    See encoding of type in rokoko_ids.
    '''

    if obj is None:
        return rid.RIG_TYPE_ACTOR | rid.RIG_TYPE_ACTOR_FACE | rid.RIG_TYPE_PROP
        #      | rid.RIG_TYPE_LIGHT | rid.RIG_TYPE_CAMERA
    types = rid.RIG_TYPE_PROP
    if obj.CheckType(c4d.Ojoint):
        types |= rid.RIG_TYPE_ACTOR
    elif obj.CheckType(c4d.Olight):
        # types |= RIG_TYPE_LIGHT
        pass  # TODO: enable as soon as JSON V4 gets used
    elif obj.CheckType(c4d.Ocamera):
        # types |= RIG_TYPE_CAMERA
        pass  # TODO: enable as soon as JSON V4 gets used
    elif obj.CheckType(c4d.Onull):
        objDown = obj.GetDown()
        if objDown is not None and objDown.CheckType(c4d.Ojoint):
            types |= rid.RIG_TYPE_ACTOR
    else:
        tagPoseMorph = obj.GetTag(c4d.Tposemorph)
        if tagPoseMorph is not None:
            types |= rid.RIG_TYPE_ACTOR_FACE
    return types


def RigTypeToEntitiesString(rigType):
    '''Return a name for a given tag type.'''

    if rigType is None:
        return "UNKNOWN"
    if rigType & rid.RIG_TYPE_ACTOR:
        name = "Actors"
    elif rigType & rid.RIG_TYPE_ACTOR_FACE:
        name = "Faces"
    elif rigType & rid.RIG_TYPE_LIGHT:
        name = "Lights"
    elif rigType & rid.RIG_TYPE_CAMERA:
        name = "Cameras"
    else:
        name = "Props"
    return name


def RigTypeToEntitiesBcId(rigType):
    '''Return ID of the entities BaseContainer for a given tag type'''

    if rigType & rid.RIG_TYPE_ACTOR:
        idEntitiesBc = rid.ID_BC_DATASET_ACTORS
    elif rigType & rid.RIG_TYPE_ACTOR_FACE:
        idEntitiesBc = rid.ID_BC_DATASET_ACTORS
    elif rigType & rid.RIG_TYPE_LIGHT:
        idEntitiesBc = rid.ID_BC_DATASET_LIGHTS
    elif rigType & rid.RIG_TYPE_CAMERA:
        idEntitiesBc = rid.ID_BC_DATASET_CAMERAS
    else:
        idEntitiesBc = rid.ID_BC_DATASET_PROPS
    return idEntitiesBc


def OpenLinkInBrowser(weblink):
    '''Open a link in an external browser.

    GeExecuteFile() doesn't do, as it does not support # in links on Mac.
    '''
    webbrowser.open(weblink)


# Debug tool to measure timing (very roughly)
# Use as function decorator (@timing),
# it simply prints execution time of wrapped function
g_timingMin = 1000000000000.0
g_timingMax = 0.0


def timing(f):
    def wrapTiming(*args, **kwargs):
        time1 = time.clock()
        ret = f(*args, **kwargs)
        time2 = time.clock()
        timeDiff = (time2 - time1) * 1000.0
        global g_timingMax, g_timingMin
        g_timingMin = min(g_timingMin, timeDiff)
        g_timingMax = max(g_timingMax, timeDiff)
        print(f"T {timeDiff} ms  {g_timingMin}  {g_timingMax}")
        return ret
    return wrapTiming
