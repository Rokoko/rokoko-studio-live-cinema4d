import sys, os, importlib
import c4d

DEVELOPMENT = True # Users should rather have this set to False
basedir = __file__[:__file__.rfind(os.sep)]
sys.path.insert(0, basedir)

if DEVELOPMENT == True:
    # not nice, but during development the reload is needed for Reload Python Plugins to work properly (and use changed sources)
    for module in sys.modules.values():
        end = len('rokoko_')
        if len(module.__name__) < end:
            end = len(module.__name__)
        if module.__name__[:end] == 'rokoko_':
            importlib.reload(module)
from rokoko_ids import *
from rokoko_rig_tables import *
from rokoko_utils import *
from rokoko_listener import *
from rokoko_dialog_about import *
from rokoko_dialog_save_recording import *
from rokoko_dialog_manager import *
from rokoko_message_data import *
from rokoko_commands import *
from rokoko_tag import *
from rokoko_prefs import *

g_studioTPose = {}
def LoadStudioTPose():
    global g_studioTPose
    filenameStudioTPose = os.path.join(os.path.dirname(__file__), 'res', 'tposeStudio.json')
    with open(filenameStudioTPose, mode='r') as f:
        studioData = f.read()
        f.close()
        dataJSON = json.loads(studioData)
        dataBody = dataJSON['scene']['actors'][0]['body']
        g_studioTPose = {}
        for nameBodyPart, dataPosRot in dataBody.items():
            g_studioTPose[nameBodyPart] = ~JSONQuaternionToMatrix(dataPosRot['rotation'])
        TagSetGlobalStudioTPose(g_studioTPose)
        DlgSaveSetGlobalStudioTPose(g_studioTPose)

import time
def PluginMessage(id, data):
    if id == c4d.C4DPL_RELOADPYTHONPLUGINS or id == c4d.C4DPL_ENDACTIVITY:
        DestroyListenerThread()
        CommandsDestroyGlobals()
        RemoveConnectedDataSet()
        global g_tPose, g_studioTPose
        g_tPose = {}
        g_studioTPose = {}
        DlgAboutDestroyGlobals()
        DlgSaveDestroyGlobals()
        DlgManagerDataDestroyGlobals()
        TagDestroyGlobals()
        MessageDataDestroyGlobals()
        return True
    return False

def RegisterImageAsIcon(id, filename, mirrorHorizontally=False, size=None):
    bmpIcon = c4d.bitmaps.BaseBitmap()
    bmpIcon.InitWith(os.path.join(os.path.dirname(__file__), 'res', filename))
    if mirrorHorizontally:
        bmpIconMirrored = bmpIcon.GetClone()
        w, h = bmpIcon.GetSize()
        for y in range(h):
            for x in range(w):
                r, g, b = bmpIconMirrored.GetPixel(w-x-1, y)
                a = bmpIconMirrored.GetAlphaPixel(bmpIconMirrored.GetChannelNum(0), w-x-1, y)
                bmpIcon.SetPixel(x, y, r, g, b)
                bmpIcon.SetAlphaPixel(bmpIcon.GetChannelNum(0), x, y, a)
    if size is not None:
        bmpIconNewSize = c4d.bitmaps.BaseBitmap()
        bmpIconNewSize.Init(size, size)
        bmpIcon.ScaleIt(bmpIconNewSize, 256, True, False)
        bmpIcon = bmpIconNewSize
    result = c4d.gui.RegisterIcon(id, bmpIcon, x=0, y=0, w=-1, h=-1)
    if not result:
        print('ERROR: Icon registration failed:', filename)
    return bmpIcon

def RegisterIcons():
    if DEVELOPMENT:
        c4d.gui.UnregisterIcon(PLUGIN_ID_TAG_ICON_ACTOR)
        c4d.gui.UnregisterIcon(PLUGIN_ID_TAG_ICON_FACE)
        c4d.gui.UnregisterIcon(PLUGIN_ID_TAG_ICON_LIGHT)
        c4d.gui.UnregisterIcon(PLUGIN_ID_TAG_ICON_CAMERA)
        c4d.gui.UnregisterIcon(PLUGIN_ID_TAG_ICON_PROP)
        c4d.gui.UnregisterIcon(PLUGIN_ID_ICON_SUIT)
        c4d.gui.UnregisterIcon(PLUGIN_ID_ICON_GLOVE_LEFT)
        c4d.gui.UnregisterIcon(PLUGIN_ID_ICON_GLOVE_RIGHT)
        c4d.gui.UnregisterIcon(PLUGIN_ID_ICON_FACE)
        c4d.gui.UnregisterIcon(PLUGIN_ID_ICON_PROP)
        c4d.gui.UnregisterIcon(PLUGIN_ID_ICON_PROFILE)
        c4d.gui.UnregisterIcon(PLUGIN_ID_ICON_STUDIO_LIVE)
        c4d.gui.UnregisterIcon(PLUGIN_ID_COMMAND_API_ICON_RECORD_START)
        c4d.gui.UnregisterIcon(PLUGIN_ID_COMMAND_API_ICON_RECORD_STOP)
        c4d.gui.UnregisterIcon(PLUGIN_ID_COMMAND_API_ICON_CALIBRATE_SUIT)
        c4d.gui.UnregisterIcon(PLUGIN_ID_COMMAND_API_ICON_RESTART_SUIT)
    RegisterImageAsIcon(PLUGIN_ID_TAG_ICON_ACTOR, 'icon-row-suit-32.png')
    RegisterImageAsIcon(PLUGIN_ID_TAG_ICON_FACE, 'icon-row-face-32.png')
    RegisterImageAsIcon(PLUGIN_ID_TAG_ICON_LIGHT, 'rokoko_tag_light.png')
    RegisterImageAsIcon(PLUGIN_ID_TAG_ICON_CAMERA, 'rokoko_tag_camera.png')
    RegisterImageAsIcon(PLUGIN_ID_TAG_ICON_PROP, 'icon-vp-32.png')
    RegisterImageAsIcon(PLUGIN_ID_ICON_SUIT, 'icon-row-suit-32.png', size=16)
    RegisterImageAsIcon(PLUGIN_ID_ICON_GLOVE_LEFT, 'icon-input-gloves-32px.png', size=16)
    RegisterImageAsIcon(PLUGIN_ID_ICON_GLOVE_RIGHT, 'icon-input-gloves-32px.png', mirrorHorizontally=True, size=16)
    RegisterImageAsIcon(PLUGIN_ID_ICON_FACE, 'icon-row-face-32.png', size=16)
    RegisterImageAsIcon(PLUGIN_ID_ICON_PROP, 'icon-vp-32.png', size=16)
    RegisterImageAsIcon(PLUGIN_ID_ICON_PROFILE, 'icon-rokoko-32.png', size=16)
    bmpIconForCommand = RegisterImageAsIcon(PLUGIN_ID_ICON_STUDIO_LIVE, 'icon-studio-live-32.png')
    RegisterImageAsIcon(PLUGIN_ID_COMMAND_API_ICON_RECORD_START, 'icon-record-32.png')
    RegisterImageAsIcon(PLUGIN_ID_COMMAND_API_ICON_RECORD_STOP, 'icon-stop-white-32.png')
    RegisterImageAsIcon(PLUGIN_ID_COMMAND_API_ICON_CALIBRATE_SUIT, 'icon-straight-pose-32.png')
    RegisterImageAsIcon(PLUGIN_ID_COMMAND_API_ICON_RESTART_SUIT, 'icon-restart-32.png')
    return bmpIconForCommand

def RegisterRokokoStudioLive():
    bcPrefs = GetWorldPrefs()
    if bcPrefs[ID_PREF_PLUGIN_ENABLED] is None or bcPrefs[ID_PREF_PLUGIN_ENABLED]:
        InitBaseContainer()
        InitRokokoLogo()
        bmpIcon = RegisterIcons()
        LoadStudioTPose()
        res = c4d.plugins.RegisterMessagePlugin(id=PLUGIN_ID_MESSAGEDATA, str='', info=0, dat=MessageDataRokoko())
        if not res:
            print('ERROR: Rokoko Studio Live ({}) failed to register MessageData.'.format(PLUGIN_VERSION))
            return
        res = c4d.plugins.RegisterTagPlugin(id=PLUGIN_ID_TAG,
                                            str=PLUGIN_NAME_TAG,
                                            info=c4d.TAG_EXPRESSION | c4d.TAG_VISIBLE,
                                            g=TagDataRokoko,
                                            description='Trokoko',
                                            icon=bmpIcon)
        if not res:
            print('ERROR: Rokoko Studio Live ({}) failed to register Tag.'.format(PLUGIN_VERSION))
            return
        res = c4d.plugins.RegisterCommandPlugin(id=PLUGIN_ID_COMMAND_MANAGER,
                                                str=PLUGIN_NAME_COMMAND_MANAGER,
                                                help='Open {}'.format(PLUGIN_NAME_COMMAND_MANAGER),
                                                info=0,
                                                dat=CommandDataRokokoManager(),
                                                icon=bmpIcon)
        if not res:
            print('ERROR: Rokoko Studio Live ({}) failed to register Manager CommandData.'.format(PLUGIN_VERSION))
            return
        print('Successfully registered Rokoko Studio Live ({}).'.format(PLUGIN_VERSION))
    res = c4d.plugins.RegisterPreferencePlugin(id=PLUGIN_ID_PREFS,
                                               g=PreferenceDataRokoko,
                                               name=PLUGIN_NAME_COMMAND_MANAGER,
                                               description='rokokopreferences',
                                               parentid=0,
                                               sortid=0)
    if not res:
        print('ERROR: Rokoko Studio Live ({}) failed to register PrefData.'.format(PLUGIN_VERSION))


if __name__ == "__main__":
    RegisterRokokoStudioLive()
