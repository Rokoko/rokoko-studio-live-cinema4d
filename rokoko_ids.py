import c4d

PLUGIN_NAME_COMMAND_MANAGER = 'Rokoko Studio Live'
PLUGIN_NAME_TAG = 'Rokoko Tag'

PLUGIN_VERSION_MAJOR = 1
PLUGIN_VERSION_MINOR = 1
PLUGIN_VERSION_PATCH = 20201127
PLUGIN_VERSION = '{0}.{1}.{2}'.format(PLUGIN_VERSION_MAJOR, PLUGIN_VERSION_MINOR, PLUGIN_VERSION_PATCH)

PLUGIN_ID_COMMAND_MANAGER                          = 1056094  # Main plugin ID (used to access BaseContainers, etc.)
PLUGIN_ID_TAG                                      = 1056095
PLUGIN_ID_MESSAGEDATA                              = 1056097
PLUGIN_ID_PREFS                                    = 1056096

PLUGIN_ID_COREMESSAGE_LIVE_DRAW                    = 1056098
PLUGIN_ID_COREMESSAGE_PLAYER                       = 1056099
CM_SUBID_PLAYER_START                              = 1
CM_SUBID_PLAYER_PAUSE_RECEPTION                    = 2
CM_SUBID_PLAYER_EXIT                               = 3
CM_SUBID_PLAYER_PLAY                               = 4
CM_SUBID_PLAYER_PAUSE                              = 5
CM_SUBID_PLAYER_STOP                               = 6
CM_SUBID_PLAYER_FLUSH_LIVE_BUFFER                  = 7
PLUGIN_ID_COREMESSAGE_MANAGER                      = 1056100
CM_SUBID_MANAGER_UPDATE_TAGS                       = 1
CM_SUBID_MANAGER_UPDATE_TAG_PARAMS                 = 2
CM_SUBID_MANAGER_OPEN_PLAYER                       = 3
CM_SUBID_MANAGER_PLAYBACK_STATUS_CHANGE            = 4
CM_SUBID_MANAGER_BUFFER_PULSE                      = 5
PLUGIN_ID_COREMESSAGE_MANAGER_CURRENT_FRAME_NUMBER = 1056101
PLUGIN_ID_COREMESSAGE_CONNECTION                   = 1056102
CM_SUBID_CONNECTION_CONNECT                        = 1
CM_SUBID_CONNECTION_DISCONNECT                     = 2
CM_SUBID_CONNECTION_STATUS_CHANGE                  = 3
CM_SUBID_CONNECTION_LIVE_DATA_CHANGE               = 4

PLUGIN_ID_MSG_DATA_CHANGE                          = 1056103

PLUGIN_ID_TAG_ICON_ACTOR                           = 1056104
PLUGIN_ID_TAG_ICON_FACE                            = 1056105
PLUGIN_ID_TAG_ICON_LIGHT                           = 1056106
PLUGIN_ID_TAG_ICON_CAMERA                          = 1056107
PLUGIN_ID_TAG_ICON_PROP                            = 1056108
PLUGIN_ID_ICON_SUIT                                = 1056109
PLUGIN_ID_ICON_GLOVE_LEFT                          = 1056110
PLUGIN_ID_ICON_GLOVE_RIGHT                         = 1056111
PLUGIN_ID_ICON_FACE                                = 1056112
PLUGIN_ID_ICON_PROP                                = 1056113
PLUGIN_ID_ICON_PROFILE                             = 1056114
PLUGIN_ID_ICON_STUDIO_LIVE                         = 1056115
PLUGIN_ID_COMMAND_API_ICON_RECORD_START            = 1056119
PLUGIN_ID_COMMAND_API_ICON_RECORD_STOP             = 1056118
PLUGIN_ID_COMMAND_API_ICON_CALIBRATE_SUIT          = 1056120
PLUGIN_ID_COMMAND_API_ICON_RESTART_SUIT            = 1056121

RIG_TYPE_UNKNOWN          = 0x0000
RIG_TYPE_ACTOR            = 0x0001
RIG_TYPE_ACTOR_FACE       = 0x0002
RIG_TYPE_LIGHT            = 0x0004
RIG_TYPE_CAMERA           = 0x0008
RIG_TYPE_PROP             = 0x0010


ID_PREF_PLUGIN_ENABLED = 1

ID_PROJECT_SCALE = 900000
ID_BC_CONNECTIONS = 1000000
ID_BC_DATA_SETS = 2000000
ID_BC_CONNECTED_DATA_SET = 3000000
ID_BC_RIG_PRESETS = 4000000
ID_BC_FACE_PRESETS = 5000000

ID_TAG_RIG_TYPE = 2001
ID_TAG_DATA_SET = 2002
ID_TAG_DATA_SET_FIRST_FRAME = 2003
ID_TAG_DATA_SET_LAST_FRAME = 2004
ID_TAG_ACTOR_FACE = 2007
ID_TAG_SELECTED_IN_MANAGER = 2008
ID_TAG_BUTTON_PLAY = 2009
ID_TAG_BUTTON_RECORD = 2010
ID_TAG_BUTTON_SET_KEYFRAMES = 2012
ID_TAG_BUTTON_OPEN_MANAGER = 2017
ID_TAG_ACTORS = 2018
ID_TAG_VALID_DATA = 2021
ID_TAG_ENTITY_NAME = 2022
ID_TAG_ENTITY_COLOR = 2023
ID_TAG_ACTOR_INDEX = 2024
ID_TAG_BUTTON_GO_TO_TPOSE = 2025
ID_TAG_ENTITY_STATUS = 2026
ID_TAG_BUTTON_GUESS_RIG = 2027
ID_TAG_BUTTON_STORE_TPOSE = 2028
ID_TAG_ACTOR_HIP_HEIGHT = 2029
ID_TAG_ACTOR_HAS_BODY = 2030
ID_TAG_ACTOR_HAS_HIP = 2046
ID_TAG_ACTOR_HAS_HAND_LEFT = 2031
ID_TAG_ACTOR_HAS_HAND_RIGHT = 2032
ID_TAG_ACTOR_MAP_BODY = 2033
ID_TAG_ACTOR_MAP_HAND_LEFT = 2034
ID_TAG_ACTOR_MAP_HAND_RIGHT = 2035
ID_TAG_ACTOR_TPOSE_STORED = 2036
ID_TAG_IDX_READ_FRAME = 2037
ID_TAG_OPEN_MANAGER_ON_PLAY = 2038
ID_TAG_BUTTON_GUESS_FACE_POSES = 2039
ID_TAG_ACTOR_RIG_DETECTED = 2040
ID_TAG_ACTOR_FACE_DETECTED = 2041
ID_TAG_BUTTON_RIG_PRESET = 2042
ID_TAG_BUTTON_ADD_RIG_PRESET = 2043
ID_TAG_BUTTON_FACE_PRESET = 2044
ID_TAG_BUTTON_ADD_FACE_PRESET = 2045
ID_TAG_ROOT_MATRIX = 2047
ID_TAG_HIP_HEIGHT_WARNING = 2048

ID_TAG_DUMMY = 2100

ID_TAG_GROUP_CONTROL = 2151
ID_TAG_GROUP_MAPPING = 2160
ID_TAG_GROUP_MAPPING_ACTOR = 2161
ID_TAG_GROUP_MAPPING_ACTOR_SUIT = 2162
ID_TAG_GROUP_MAPPING_ACTOR_GLOVE_LEFT = 2163
ID_TAG_GROUP_MAPPING_ACTOR_GLOVE_RIGHT = 2164
ID_TAG_GROUP_MAPPING_FACE = 2165
ID_TAG_GROUP_MAPPING_ACTOR_HIP_HEIGHT_WARNING = 2166
ID_TAG_GROUP_ENTITY_INFO = 2190
ID_TAG_GROUP_ENTITY_INFO_ACTOR = 2191

ID_TAG_EXECUTE_MODE = 3001
ID_TAG_BC_DATASETS = 3002
ID_TAG_BC_RIG_TYPES = 3003
ID_TAG_BC_ACTORS = 3004

ID_TAG_BASE_RIG_LINKS = 4000
ID_TAG_BASE_RIG_MATRICES = 5000
ID_TAG_BASE_FACE_POSES = 6000
ID_TAG_BASE_MORPH_INDECES = 7000
ID_TAG_BASE_RIG_MATRICES_PRETRANSFORMED = 8000


ID_DLGMNGR_GROUP_MAIN = 1000
ID_DLGMNGR_GROUP_CONNECTIONS = 1001
ID_DLGMNGR_GROUP_GLOBAL_DATA = 1002
ID_DLGMNGR_GROUP_LOCAL_DATA = 1003
ID_DLGMNGR_GROUP_CONTROL = 1004
ID_DLGMNGR_GROUP_PLAYER = 1005
ID_DLGMNGR_GROUP_CONNECTION_DATA = 1006
ID_DLGMNGR_GROUP_COMMAND_API = 1007
ID_DLGMNGR_SCROLL_CONNECTIONS = 1008
ID_DLGMNGR_SCROLL_GLOBAL_DATA = 1009
ID_DLGMNGR_SCROLL_LOCAL_DATA = 1010
ID_DLGMNGR_SCROLL_CONTROL = 1011
ID_DLGMNGR_GROUP_CONNECTION_DATA_DETAILS = 1012
ID_DLGMNGR_GROUP_CONNECTION_DATA_CONTENT = 1013

ID_DLGMNGR_TABS = 2000
ID_DLGMNGR_CONNECTION_POPUP = 2005
ID_DLGMNGR_GLOBAL_DATA_POPUP = 2006
ID_DLGMNGR_LOCAL_DATA_POPUP = 2007
ID_DLGMNGR_TAGS_POPUP = 2008
ID_DLGMNGR_SELECT_ALL_TAGS = 2009
ID_DLGMNGR_DESELECT_ALL_TAGS = 2010
ID_DLGMNGR_INVERT_SELECTION = 2021
ID_DLGMNGR_ABOUT = 2011
ID_DLGMNGR_WEB_ROKOKO = 2012
ID_DLGMNGR_PROJECT_SCALE = 2022
ID_DLGMNGR_WEB_STUDIO_LIVE_LICENSE = 2028
ID_DLGMNGR_WEB_DOCUMENTATION = 2029
ID_DLGMNGR_WEB_FORUMS = 2030
ID_DLGMNGR_ASSIGN_UNASSIGNED_TAGS = 2031

ID_DLGMNGR_COMMANDAPI_START_RECORDING = 2024
ID_DLGMNGR_COMMANDAPI_STOP_RECORDING = 2025
ID_DLGMNGR_COMMANDAPI_CALIBRATE_ALL_SUITS = 2026
ID_DLGMNGR_COMMANDAPI_RESET_ALL_SUITS = 2027

ID_DLGMNGR_CONNECTION_ACTORS = 2040
ID_DLGMNGR_CONNECTION_GLOVES = 2041
ID_DLGMNGR_CONNECTION_FACES = 2042
ID_DLGMNGR_CONNECTION_LIGHTS = 2043
ID_DLGMNGR_CONNECTION_CAMERAS = 2044
ID_DLGMNGR_CONNECTION_PROPS = 2045
ID_DLGMNGR_CONNECTION_NAMES_ACTORS = 2047
ID_DLGMNGR_CONNECTION_NAMES_FACES = 2049
ID_DLGMNGR_CONNECTION_NAMES_LIGHTS = 2051
ID_DLGMNGR_CONNECTION_NAMES_CAMERAS = 2053
ID_DLGMNGR_CONNECTION_NAMES_PROPS = 2055
ID_DLGMNGR_CONNECTIONS_IN_MENU = 2019
ID_DLGMNGR_CONNECTION_STATUS_IN_MENU = 2020
ID_DLGMNGR_CONNECTION_FPS = 2057

ID_DLGMNGR_PLAYER_START_STOP = 2001
ID_DLGMNGR_PLAYER_TAG_SELECTION = 2023
ID_DLGMNGR_PLAYER_PAUSE = 2061
ID_DLGMNGR_PLAYER_CURRENT_FRAME = 2065
ID_DLGMNGR_PLAYER_FIRST_FRAME = 2066
ID_DLGMNGR_PLAYER_LAST_FRAME = 2067
ID_DLGMNGR_PLAYER_SYNC_WITH_LIVE = 2071
ID_DLGMNGR_PLAYER_FLUSH_BUFFER = 2068
ID_DLGMNGR_PLAYER_SAVE = 2069
ID_DLGMNGR_PLAYER_ACTIVE_TAGS_LABEL = 2075
ID_DLGMNGR_PLAYER_ACTIVE_TAGS = 2070
ID_DLGMNGR_PLAYER_BUFFERING_LABEL = 2074
ID_DLGMNGR_PLAYER_BUFFERING = 2072
ID_DLGMNGR_PLAYER_BUFFERING_IN_MENU = 2073
ID_DLGMNGR_PLAYER_PLAYBACK_SPEED = 2062
ID_DLGMNGR_PLAYER_ANIMATE_DOCUMENT = 2076

ID_DLGMNGR_BASE_CONNECTION_AUTO_CONNECT = 10000
ID_DLGMNGR_BASE_CONNECTION_POPUP = 20000
ID_DLGMNGR_BASE_GLOBAL_DATA_AVAILABLE = 30000
ID_DLGMNGR_BASE_GLOBAL_DATA_REMOVE = 40000
ID_DLGMNGR_BASE_GLOBAL_DATA_POPUP = 50000
ID_DLGMNGR_BASE_LOCAL_DATA_REMOVE = 60000
ID_DLGMNGR_BASE_LOCAL_DATA_POPUP = 70000
ID_DLGMNGR_BASE_DATA_SET_ENABLED = 80000
ID_DLGMNGR_BASE_DATA_SET_BODY = 90000
ID_DLGMNGR_BASE_DATA_SET_HANDS = 100000
ID_DLGMNGR_BASE_DATA_SET_PLAY = 110000
ID_DLGMNGR_BASE_TAG_DATA_SETS = 120000
ID_DLGMNGR_BASE_TAG_RIG_TYPES = 130000
ID_DLGMNGR_BASE_TAG_POPUP = 140000
ID_DLGMNGR_BASE_TAG_ACTORS = 150000
ID_DLGMNGR_BASE_CONNECTION_CONNECT = 160000


ID_DLGSAVE_GROUP_MAIN = 5000

ID_DLGSAVE_NAME_DATASET = 6000
ID_DLGSAVE_PATH_DATASET = 6001
ID_DLGSAVE_SET_PATH_DATASET = 6002
ID_DLGSAVE_STORE_GLOBAL_DATA = 6003
ID_DLGSAVE_STORE_LOCAL_DATA = 6004
ID_DLGSAVE_FIRST_FRAME = 6005
ID_DLGSAVE_LAST_FRAME = 6006
ID_DLGSAVE_USE_NEW_DATASET = 6007
ID_DLGSAVE_SET_KEYFRAMES_AT_0 = 6008
ID_DLGSAVE_SET_KEYFRAMES_AT_CURRENT = 6009
ID_DLGSAVE_DISCARD = 6010
ID_DLGSAVE_CREATE_IN_TAKE = 6011
ID_DLGSAVE_TIMING = 6012
ID_DLGSAVE_FRAME_SKIP = 6013
ID_DLGSAVE_LENGTH = 6014
ID_DLGSAVE_ACTIVATE_NEW_TAKE = 6015
ID_DLGSAVE_SET_KEYFRAMES_AUTOFORWARD = 6016
ID_DLGSAVE_WIPE_EXISTING_ANIMATION = 6017
ID_DLGSAVE_BAKE_INCLUDE_DATA_SETS = 6018


ID_DLGEDITCONN_NAME = 7000
ID_DLGEDITCONN_PORT = 7001
ID_DLGEDITCONN_COMMANDAPI_IP = 7002
ID_DLGEDITCONN_COMMANDAPI_PORT = 7003
ID_DLGEDITCONN_COMMANDAPI_KEY = 7004


ID_DLGEDITDATASET_NAME = 8000
ID_DLGEDITDATASET_FILENAME = 8001
ID_DLGEDITDATASET_CHOOSE_FILE = 8002


ID_SUBMENU_CONNECTION_CONNECT = c4d.FIRST_POPUP_ID + 0
ID_SUBMENU_CONNECTION_EDIT = c4d.FIRST_POPUP_ID + 1
ID_SUBMENU_CONNECTION_REMOVE = c4d.FIRST_POPUP_ID + 2
ID_SUBMENU_CONNECTION_CREATE_SCENE = c4d.FIRST_POPUP_ID + 3

ID_SUBMENU_DATA_ADD_FILE = c4d.FIRST_POPUP_ID + 0
ID_SUBMENU_DATA_ADD_FOLDER = c4d.FIRST_POPUP_ID + 1
ID_SUBMENU_DATA_REMOVE_ALL = c4d.FIRST_POPUP_ID + 3
ID_SUBMENU_DATA_DELETE_ALL = c4d.FIRST_POPUP_ID + 4

ID_SUBMENU_DATA_SET_COPY_LOCAL = c4d.FIRST_POPUP_ID + 0
ID_SUBMENU_DATA_SET_MOVE_LOCAL = c4d.FIRST_POPUP_ID + 1
ID_SUBMENU_DATA_SET_EDIT = c4d.FIRST_POPUP_ID + 2
ID_SUBMENU_DATA_SET_REMOVE = c4d.FIRST_POPUP_ID + 4
ID_SUBMENU_DATA_SET_DELETE = c4d.FIRST_POPUP_ID + 5
ID_SUBMENU_DATA_SET_CREATE_SCENE = c4d.FIRST_POPUP_ID + 6
ID_SUBMENU_DATA_SET_OPEN_DIRECTORY = c4d.FIRST_POPUP_ID + 7

ID_SUBMENU_TAGS_CREATE_CHARACTER_NEWTON = c4d.FIRST_POPUP_ID + 0
ID_SUBMENU_TAGS_CREATE_LIGHT = c4d.FIRST_POPUP_ID + 2
ID_SUBMENU_TAGS_CREATE_CAMERA = c4d.FIRST_POPUP_ID + 3
ID_SUBMENU_TAGS_CREATE_PROP = c4d.FIRST_POPUP_ID + 4
ID_SUBMENU_TAGS_CREATE_STUDIO_LIVE_SCENE = c4d.FIRST_POPUP_ID + 5
ID_SUBMENU_TAGS_CREATE_BONES_NEWTON = c4d.FIRST_POPUP_ID + 6
ID_SUBMENU_TAGS_CREATE_FACE_NEWTON = c4d.FIRST_POPUP_ID + 7
ID_SUBMENU_TAGS_CREATE_CHARACTER_NEWTON_WITH_FACE = c4d.FIRST_POPUP_ID + 8

ID_SUBMENU_TAG_PLAY = c4d.FIRST_POPUP_ID + 0
ID_SUBMENU_TAG_SHOW_TAG = c4d.FIRST_POPUP_ID + 1
ID_SUBMENU_TAG_SHOW_OBJECT = c4d.FIRST_POPUP_ID + 2
ID_SUBMENU_TAG_DELETE = c4d.FIRST_POPUP_ID + 3
ID_SUBMENU_TAG_TPOSE = c4d.FIRST_POPUP_ID + 4


MR_Y180 = c4d.Matrix(c4d.Vector(0.0), c4d.Vector(-1.0, 0.0, 0.0), c4d.Vector(0.0, 1.0, 0.0), c4d.Vector(0.0, 0.0, -1.0))

ID_BC_DATASET_NAME = 0
ID_BC_DATASET_TYPE = 1
ID_BC_DATASET_CONNECTED = 2 # Not in use
ID_BC_DATASET_AVAILABLE_IN_DOC = 3 # Not in use

ID_BC_DATASET_LIVE_PORT = 11
ID_BC_DATASET_LIVE_AUTOCONNECT = 13
ID_BC_DATASET_LIVE_FPS = 14

ID_BC_DATASET_COMMANDAPI_IP = 15
ID_BC_DATASET_COMMANDAPI_PORT = 16
ID_BC_DATASET_COMMANDAPI_KEY = 17

ID_BC_DATASET_FILENAME = 20
ID_BC_DATASET_IS_LOCAL = 21

ID_BC_DATASET_NUM_SUITS = 30
ID_BC_DATASET_NUM_GLOVES = 31
ID_BC_DATASET_NUM_FACES = 32
ID_BC_DATASET_NUM_LIGHTS = 33
ID_BC_DATASET_NUM_CAMERAS = 34
ID_BC_DATASET_NUM_PROPS = 35
ID_BC_DATASET_NUM_ACTORS = 36

ID_BC_DATASET_ACTORS = 40
ID_BC_DATASET_LIGHTS = 42
ID_BC_DATASET_CAMERAS = 43
ID_BC_DATASET_PROPS = 44

ID_BC_ENTITY_NAME = 0
ID_BC_ENTITY_COLOR = 1
ID_BC_ENTITY_TYPE = 2 # not in use
ID_BC_ENTITY_HAS_SUIT = 3
ID_BC_ENTITY_HAS_GLOVE_LEFT = 4
ID_BC_ENTITY_HAS_GLOVE_RIGHT = 5
ID_BC_ENTITY_HAS_FACE = 6

ID_BC_PRESET_NAME = 1000
ID_BC_PRESET_TYPE = 0  # 0: rig, 1: face
