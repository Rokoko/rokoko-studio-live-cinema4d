# Besides some global initializations, all plugins needed for Rokoko Studio Live are registered here.
# Basically here's the entry/starting point of the plugin.
#
# Additionally C4D's plugin messages (PluginMessage()) are handled here, mainly some
# startup/shutdown logic.
import sys, os, subprocess
import c4d
if c4d.GetC4DVersion() // 1000 > 22:
    from importlib import reload

basedir = __file__[:__file__.rfind(os.sep)]
sys.path.insert(0, basedir)

def ReloadRokokoModules():
    for module in list(sys.modules.values()):
        if module is None:
            continue
        end = len('rokoko_')
        if len(module.__name__) < end:
            end = len(module.__name__)
        if module.__name__[:end] == 'rokoko_':
            reload(module)

from rokoko_ids import *
from rokoko_rig_tables import *
from rokoko_utils import *
from rokoko_listener import *
from rokoko_dialog_about import *
from rokoko_dialog_save_recording import *
from rokoko_dialog_manager import *
from rokoko_message_data import *
from rokoko_commands import *
from rokoko_command_install import *
from rokoko_tag import *
from rokoko_prefs import *

# Import lz4 module for the correct platform
# Here it's only done for a test on startup to warn the user.
__USE_LZ4__ = True
try:
    currentOS = c4d.GeGetCurrentOS()
    if currentOS == c4d.OPERATINGSYSTEM_WIN:
        #import packages.win.lz4.frame as lz4f
        import lz4.frame as lz4f

    elif currentOS == c4d.OPERATINGSYSTEM_OSX:
        import lz4.frame as lz4f

except:
    __USE_LZ4__ = False


COMMAND_TEST_UDP_PAKET_SIZE = 'sysctl -h net.inet.udp.maxdgram'
COMMAND_SET_UDP_PAKET_SIZE = 'sudo sysctl -w net.inet.udp.maxdgram=65535'
COMMAND_RESULT_TOKEN = 'net.inet.udp.maxdgram: '


# g_studioTPose dictionary contains Rokoko Studio's T-Pose.
# For every bodypart (referenced by it's name inside JSON data) it stores the rotation as a matrix.
# Note: The matrix is stored _inverted_, as this is the only form it's needed in.
g_studioTPose = {}
def LoadStudioTPose():
    global g_studioTPose

    # Load JSON T-Pose data
    filenameStudioTPose = os.path.join(os.path.dirname(__file__), 'res', 'tposeStudio.json')
    with open(filenameStudioTPose, mode='r') as f:
        # Read data from file
        studioData = f.read()
        f.close()

        # Decode JSON
        dataJSON = json.loads(studioData)
        dataBody = dataJSON['scene']['actors'][0]['body'] # body is all we need

        # Store inverted matrices in the dictionary
        g_studioTPose = {}
        for nameBodyPart, dataPosRot in dataBody.items():
            g_studioTPose[nameBodyPart] = ~JSONQuaternionToMatrix(dataPosRot['rotation'])

        # Allow submodules (namely Rokoko tag and Svae Recording dialog) to access this global resource
        TagSetGlobalStudioTPose(g_studioTPose)
        DlgSaveSetGlobalStudioTPose(g_studioTPose)


# Open a warning requester if no LZ module available.
def WarnNoLZ4():
    message = PLUGIN_NAME_COMMAND_MANAGER + '\n\n'
    message += 'Compression module not avalaible!\n'
    message += 'Please set up custom connection in Rokoko Studio.\n\n'
    message += 'See here: {0}\n\n'.format(LINK_CONNECTION_INSTRUCTIONS)
    message += 'Ok: Open instructions in web browser.\n'

    result = c4d.gui.MessageDialog(message, c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_OKCANCEL)
    if result == c4d.GEMB_R_OK:
        OpenLinkInBrowser(LINK_CONNECTION_INSTRUCTIONS)


# Open a warning requester if UDP paket size smaller than desired.
def WarnSmallUDPPaketSize():
    message = PLUGIN_NAME_COMMAND_MANAGER + '\n\n'
    message += 'Low UDP paket size set in MacOS!\n'
    message += 'Please call the following command in a terminal:\n'
    message += '    {0}\n\n'.format(COMMAND_SET_UDP_PAKET_SIZE)
    message += 'Yes: Copy command to clipboard.\n'
    message += 'No: Understood, but never show this warning again.\n'
    message += 'Cancel: Do nothing.\n'

    result = c4d.gui.MessageDialog(message, c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_YESNOCANCEL)
    if result == c4d.GEMB_R_YES:
        c4d.CopyStringToClipboard(COMMAND_SET_UDP_PAKET_SIZE)

    elif result == c4d.GEMB_R_NO:
        SetPref(ID_PREF_UDP_SIZE_NO_WARNING, True)


# Execute a command in a shell and return its output.
def ExecShellCommand(command):
    proc = None
    try:
        proc = subprocess.Popen(command, shell=True, cwd=None,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                encoding='utf-8', text=True)
    except:
        pass # deliberately surpressing any exception
    if proc is None or proc.poll() is not None:
        c4d.gui.MessageDialog('Rokoko Studio Live:\nFAILED to execute command!\n    {0}\n'.format(command), type=c4d.GEMB_ICONEXCLAMATION)
        return
    stdout, stderr = proc.communicate()
    return str(stdout), str(stderr)


# Test UDP paket size configured in MacOS and warn accordingly
def TestUDPPaketSize():
    # Only for MacOS
    currentOS = c4d.GeGetCurrentOS()
    if currentOS != c4d.OPERATINGSYSTEM_OSX:
        return

    # Check, if user disabled the check (by selecting "No" in a previous run)
    if GetPref(ID_PREF_UDP_SIZE_NO_WARNING) == True:
        return

    # Try to find out current UDP paket size
    stdout, stderr = ExecShellCommand(COMMAND_TEST_UDP_PAKET_SIZE)

    # Evaluate result
    result = ''
    if COMMAND_RESULT_TOKEN in stdout:
        result = stdout.replace(COMMAND_RESULT_TOKEN, '').strip()
    else:
        print('ERROR: Failed to test UDP paket size: {0}'.format(result))
        return

    if len(result) < 3:
        print('ERROR: Failed to test UDP paket size: {0}'.format(result))
        return

    paketSize = int(result)

    # If smaller than desired, open a warning requester
    if paketSize < 65535:
        WarnSmallUDPPaketSize()


# PluginMessage() will be called by Cinema 4D to communicate status changes.
# Mainly these are related to certain phases during start up or shut down.
# We need to cleaanup properly during shut down, as well as when the user "Reloads Paython Plugins".
def PluginMessage(id, data):
    if id == c4d.C4DPL_RELOADPYTHONPLUGINS or id == c4d.C4DPL_ENDACTIVITY:
        # Either C4D is shutting down or Python plugins are about to be reloaded
        global g_studioTPose

        # Get rid of any global resources and references
        DestroyListenerThread()
        CommandsDestroyGlobals()
        RemoveConnectedDataSet()
        g_studioTPose = {}
        DlgAboutDestroyGlobals()
        DlgSaveDestroyGlobals()
        DlgManagerDataDestroyGlobals()
        TagDestroyGlobals()
        MessageDataDestroyGlobals()

        if id == c4d.C4DPL_RELOADPYTHONPLUGINS:
            ReloadRokokoModules()

        return True
    return False


# RegisterImageAsIcon() load an image from a file and registers it with the given ID.
# IDs should be valid plugin IDs retrieved from Plugin Café.
def RegisterImageAsIcon(id, filename, mirrorHorizontally=False, size=None):
    # Load icon bitmap
    bmpIcon = c4d.bitmaps.BaseBitmap()
    result, _ = bmpIcon.InitWith(os.path.join(os.path.dirname(__file__), 'res', filename))
    if result != c4d.IMAGERESULT_OK:
        print('ERROR: Failed ({0}) to load icon bitmap: {1}'.format(result, filename))
        return

    # Optionally mirror the icon (used for gloves for example)
    if mirrorHorizontally:
        bmpIconMirrored = bmpIcon.GetClone()
        w, h = bmpIcon.GetSize()
        for y in range(h):
            for x in range(w):
                xFromRight = w - x - 1
                r, g, b = bmpIconMirrored.GetPixel(xFromRight, y)
                a = bmpIconMirrored.GetAlphaPixel(bmpIconMirrored.GetChannelNum(0), xFromRight, y)
                bmpIcon.SetPixel(x, y, r, g, b)
                bmpIcon.SetAlphaPixel(bmpIcon.GetChannelNum(0), x, y, a)

    # Optionally scale the icon
    if size is not None:
        bmpIconNewSize = c4d.bitmaps.BaseBitmap()
        bmpIconNewSize.Init(size, size)
        bmpIcon.ScaleIt(bmpIconNewSize, 256, True, False)
        bmpIcon = bmpIconNewSize

    # Register the icon within C4D
    result = c4d.gui.RegisterIcon(id, bmpIcon, x=0, y=0, w=-1, h=-1)
    if not result:
        print('ERROR: Icon registration failed:', filename)
    return bmpIcon


# RegisterIcons() registers all icons needed by the plugin.
# It returns the bitmap of the Rokoko Studio Live logo for use during plugin registration.
def RegisterIcons():
    # Icons can not be registered twice.
    # For "Reload Python Plugins" to work properly, we first need unregister all icons,
    # we registered in the previous run.
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

    # Register all icons
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


# RegisterRokokoStudioLive() registers all plugins needed for Rokoko Studi Live.
# This is done depending on plugin's enabled state in prefs.
def RegisterRokokoStudioLive():
    # Check if the plugin is enabled in preferences
    bcPrefs = GetWorldPrefs()
    if bcPrefs[ID_PREF_PLUGIN_ENABLED] or bcPrefs[ID_PREF_PLUGIN_ENABLED] is None:
        # Initialize globally needed structures
        InitRokokoLogo()
        bmpIcon = RegisterIcons()

        if not __USE_LZ4__:
            currentOS = c4d.GeGetCurrentOS()

            if currentOS == c4d.OPERATINGSYSTEM_WIN:
                # On Windows we can pip install the Python LZ4 module.
                # So if LZ4 is missing here, we register only the install command.
                result = c4d.plugins.RegisterCommandPlugin(id=PLUGIN_ID_COMMAND_INSTALL, str=PLUGIN_NAME_COMMAND_INSTALL,
                                                           help='Install {0}'.format(PLUGIN_NAME_COMMAND_MANAGER),
                                                           info=0, dat=CommandDataRokokoInstall(), icon=bmpIcon)
                if not result:
                    print('ERROR: {0} ({1}) failed to register installer CommandData.'.format(PLUGIN_NAME_COMMAND_MANAGER, PLUGIN_VERSION))

                return # On Win we have no installation issue, so we force the user to run the install command

            elif currentOS == c4d.OPERATINGSYSTEM_OSX:
                WarnNoLZ4()

            else:
                print('ERROR: {0} ({1}) Operating system ({2}) not supported.'.format(PLUGIN_NAME_COMMAND_MANAGER, PLUGIN_VERSION, currentOS))

        TestUDPPaketSize()

        # Init preferences
        InitBaseContainer()

        # Load global T-pose data (reference T-pose from Rokoko Studio)
        LoadStudioTPose()

        # Register plugins
        result = c4d.plugins.RegisterMessagePlugin(id=PLUGIN_ID_MESSAGEDATA, str='',
                                                   info=0, dat=MessageDataRokoko())
        if not result:
            print('ERROR: {0} ({1}) failed to register MessageData.'.format(PLUGIN_NAME_COMMAND_MANAGER, PLUGIN_VERSION))
            return

        result = c4d.plugins.RegisterTagPlugin(id=PLUGIN_ID_TAG, str=PLUGIN_NAME_TAG,
                                               info=c4d.TAG_EXPRESSION | c4d.TAG_VISIBLE, g=TagDataRokoko,
                                               description='Trokoko', icon=bmpIcon)
        if not result:
            print('ERROR: {0} ({1}) failed to register Tag.'.format(PLUGIN_NAME_COMMAND_MANAGER, PLUGIN_VERSION))
            return

        result = c4d.plugins.RegisterCommandPlugin(id=PLUGIN_ID_COMMAND_MANAGER, str=PLUGIN_NAME_COMMAND_MANAGER,
                                                   help='Open {0}'.format(PLUGIN_NAME_COMMAND_MANAGER), info=0,
                                                   dat=CommandDataRokokoManager(), icon=bmpIcon)
        if not result:
            print('ERROR: {0} ({1}) failed to register Manager CommandData.'.format(PLUGIN_NAME_COMMAND_MANAGER, PLUGIN_VERSION))
            return

        print('Successfully registered {0} ({1}).'.format(PLUGIN_NAME_COMMAND_MANAGER, PLUGIN_VERSION))

    # The preferences page is registered in any case (even if plugin got disabled by the user).
    # It's needed by the user to reenable the plugin.
    result = c4d.plugins.RegisterPreferencePlugin(id=PLUGIN_ID_PREFS, g=PreferenceDataRokoko,
                                                  name=PLUGIN_NAME_COMMAND_MANAGER, description='rokokopreferences',
                                                  parentid=0, sortid=0)
    if not result:
        print('ERROR: {0} ({1}) failed to register PrefData.'.format(PLUGIN_NAME_COMMAND_MANAGER, PLUGIN_VERSION))


# EXECUTION STARTS HERE
if __name__ == "__main__":
    RegisterRokokoStudioLive()
