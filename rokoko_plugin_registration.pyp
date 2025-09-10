''' Besides some global initializations,
all plugins needed for Rokoko Studio Live are registered here.
Basically here's the entry/starting point of the plugin.

Additionally C4D's plugin messages (PluginMessage()) are handled here, mainly
some startup/shutdown logic.
'''

import json
import os
import subprocess
import sys

import c4d

c4dVersionMajor = c4d.GetC4DVersion() // 1000
if c4dVersionMajor > 22:
    from importlib import reload

basedir = __file__[:__file__.rfind(os.sep)]
sys.path.insert(0, basedir)


def ReloadRokokoModules():
    for module in list(sys.modules.values()):
        if module is None:
            continue
        end = len("rokoko_")
        if len(module.__name__) < end:
            end = len(module.__name__)
        if module.__name__[:end] == "rokoko_":
            reload(module)


# Import LZ4 module for the correct C4D Python version:
# Key: C4D major version
OS_PATHS = {
    c4d.OPERATINGSYSTEM_WIN: "win",
    c4d.OPERATINGSYSTEM_OSX: "mac",
    c4d.OPERATINGSYSTEM_LINUX: "linux",
}
PACKAGE_PATHS = {
    23: "packages",  # Python 3.7.7
    24: "packages_c4d_S24",  # Python 3.9.1
    25: "packages_c4d_S24",
    26: "packages_c4d_S24",
    2023: "packages_c4d_2023",  # Python 3.10.8
    2024: "packages_c4d_2024",  # Python 3.11.4
    2025: "packages_c4d_2024",
    2026: "packages_c4d_2024",
}
# This needs to be done BEFORE importing any rokoko plugin modules.
# Here the import path gets added, so all other modules can do a normal import.
# In this source file LZ4 itself is actually only needed for a test on startup
# to warn the user.
__USE_LZ4__ = True
try:
    # Try system-wide LZ4 first
    import lz4.frame as lz4f
    print("[Rokoko] LZ4 import provided by C4D")
except ImportError:
    currentOS = c4d.GeGetCurrentOS()
    try:
        # Fallback to bundled LZ4
        print(f"[Rokoko] LZ4 package path: {PACKAGE_PATHS[c4dVersionMajor]}")
        sys.path.insert(
            0,
            os.path.join(os.path.dirname(__file__),
                         PACKAGE_PATHS[c4dVersionMajor],
                         OS_PATHS[currentOS]))
        import lz4.frame as lz4f  # noqa: F401
    except Exception as e:
        print(f"[Rokoko] LZ4 import failed (OS: {currentOS}, "
              f"C4D: {c4dVersionMajor}): {e}")
        __USE_LZ4__ = False

import rokoko_ids as rid  # noqa: E402
from rokoko_utils import (  # noqa: E402
    GetPref,
    GetWorldPrefs,
    InitBaseContainer,
    JSONQuaternionToMatrix,
    OpenLinkInBrowser,
    RemoveConnectedDataSet,
    SetPref,
)
from rokoko_listener import DestroyListenerThread  # noqa: E402
from rokoko_dialog_about import (  # noqa: E402
    DlgAboutDestroyGlobals,
    InitRokokoLogo,
)
from rokoko_dialog_save_recording import (  # noqa: E402
    DlgSaveDestroyGlobals,
    DlgSaveSetGlobalStudioTPose
)
from rokoko_dialog_manager import DlgManagerDataDestroyGlobals  # noqa: E402
from rokoko_message_data import (  # noqa: E402
    MessageDataDestroyGlobals,
    MessageDataRokoko,
)
from rokoko_commands import (  # noqa: E402
    CommandDataRokokoManager,
    CommandsDestroyGlobals,
)
from rokoko_tag import (  # noqa: E402
    TagDataRokoko,
    TagDestroyGlobals,
    TagSetGlobalStudioTPose,
)
from rokoko_prefs import PreferenceDataRokoko  # noqa: E402


COMMAND_TEST_UDP_PAKET_SIZE = "sysctl -h net.inet.udp.maxdgram"
COMMAND_SET_UDP_PAKET_SIZE = "sudo sysctl -w net.inet.udp.maxdgram=65535"
COMMAND_RESULT_TOKEN = "net.inet.udp.maxdgram: "


# g_studioTPose dictionary contains Rokoko Studio's T-Pose.
# For every bodypart (referenced by it's name inside JSON data) it stores the
# rotation as a matrix.
# Note: The matrix is stored _inverted_, as this is the only form it's needed
# in.
g_studioTPose = {}


def LoadStudioTPose():
    global g_studioTPose

    # Load JSON T-Pose data
    filenameStudioTPose = os.path.join(
        os.path.dirname(__file__), "res", "tposeStudio.json")
    with open(filenameStudioTPose, mode='r') as f:
        # Read data from file
        studioData = f.read()
        f.close()

        # Decode JSON
        dataJSON = json.loads(studioData)
        # body is all we need
        dataBody = dataJSON["scene"]["actors"][0]["body"]

        # Store inverted matrices in the dictionary
        g_studioTPose = {}
        for nameBodyPart, dataPosRot in dataBody.items():
            g_studioTPose[nameBodyPart] = ~JSONQuaternionToMatrix(
                dataPosRot["rotation"])

        # Allow submodules (namely Rokoko tag and Svae Recording dialog) to
        # access this global resource
        TagSetGlobalStudioTPose(g_studioTPose)
        DlgSaveSetGlobalStudioTPose(g_studioTPose)


def WarnNoLZ4():
    '''Open a warning requester if no LZ module available.'''

    message = rid.PLUGIN_NAME_COMMAND_MANAGER + "\n\n"
    message += "Compression module not avalaible!\n"
    message += "Please set up custom connection in Rokoko Studio.\n\n"
    message += f"See here: {rid.LINK_CONNECTION_INSTRUCTIONS}\n\n"
    message += "Ok: Open instructions in web browser.\n"

    result = c4d.gui.MessageDialog(
        message, c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_OKCANCEL)
    if result == c4d.GEMB_R_OK:
        OpenLinkInBrowser(rid.LINK_CONNECTION_INSTRUCTIONS)


def WarnSmallUDPPaketSize():
    '''Open a warning requester if UDP paket size smaller than desired.'''

    message = rid.PLUGIN_NAME_COMMAND_MANAGER + "\n\n"
    message += "Low UDP paket size set in MacOS!\n"
    message += "Please call the following command in a terminal:\n"
    message += f"    {COMMAND_SET_UDP_PAKET_SIZE}\n\n"
    message += "Yes: Copy command to clipboard.\n"
    message += "No: Understood, but never show this warning again.\n"
    message += "Cancel: Do nothing.\n"

    result = c4d.gui.MessageDialog(
        message, c4d.GEMB_ICONEXCLAMATION | c4d.GEMB_YESNOCANCEL)
    if result == c4d.GEMB_R_YES:
        c4d.CopyStringToClipboard(COMMAND_SET_UDP_PAKET_SIZE)
    elif result == c4d.GEMB_R_NO:
        SetPref(rid.ID_PREF_UDP_SIZE_NO_WARNING, True)


def ExecShellCommand(command):
    '''Execute a command in a shell and return its output.'''

    proc = None
    try:
        proc = subprocess.Popen(
            command,
            shell=True, cwd=None,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            encoding="utf-8", text=True)
    except BaseException:  # deliberately surpressing any exception
        pass
    if proc is None or proc.poll() is not None:
        c4d.gui.MessageDialog(
            f"Rokoko Studio Live:\nFAILED to execute command!\n   {command}\n",
            type=c4d.GEMB_ICONEXCLAMATION)
        return
    stdout, stderr = proc.communicate()
    return str(stdout), str(stderr)


def TestUDPPaketSize():
    '''Test UDP paket size configured in MacOS and warn accordingly'''

    # Only for MacOS
    currentOS = c4d.GeGetCurrentOS()
    if currentOS != c4d.OPERATINGSYSTEM_OSX:
        return

    # Check, if user disabled the check (by selecting "No" in a previous run)
    if GetPref(rid.ID_PREF_UDP_SIZE_NO_WARNING) is True:
        return

    # Try to find out current UDP paket size
    stdout, stderr = ExecShellCommand(COMMAND_TEST_UDP_PAKET_SIZE)

    # Evaluate result
    result = ""
    if COMMAND_RESULT_TOKEN in stdout:
        result = stdout.replace(COMMAND_RESULT_TOKEN, "").strip()
    else:
        print(f"ERROR: Failed to test UDP paket size: {result}")
        return

    if len(result) < 3:
        print(f"ERROR: Failed to test UDP paket size: {result}")
        return

    paketSize = int(result)

    # If smaller than desired, open a warning requester
    if paketSize < 65535:
        WarnSmallUDPPaketSize()


def PluginMessage(id, data):
    '''PluginMessage() will be called by Cinema 4D to communicate status
    changes.

    Mainly these are related to certain phases during start up or shut down.
    We need to cleaanup properly during shut down, as well as when the user
    "Reloads Paython Plugins".
    '''

    if id == c4d.C4DPL_RELOADPYTHONPLUGINS or id == c4d.C4DPL_ENDACTIVITY:
        # Either C4D is shutting down or Python plugins are about to be
        # reloaded
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


def RegisterImageAsIcon(id, filename, mirrorHorizontally=False, size=None):
    '''RegisterImageAsIcon() load an image from a file and registers it with
    the given ID.

    IDs should be valid plugin IDs retrieved from Plugin Café.
    '''

    # Load icon bitmap
    bmpIcon = c4d.bitmaps.BaseBitmap()
    result, _ = bmpIcon.InitWith(
        os.path.join(os.path.dirname(__file__), "res", filename))
    if result != c4d.IMAGERESULT_OK:
        print(f"ERROR: Failed ({result}) to load icon bitmap: {filename}")
        return

    # Optionally mirror the icon (used for gloves for example)
    if mirrorHorizontally:
        bmpIconMirrored = bmpIcon.GetClone()
        w, h = bmpIcon.GetSize()
        for y in range(h):
            for x in range(w):
                xFromRight = w - x - 1
                r, g, b = bmpIconMirrored.GetPixel(xFromRight, y)
                a = bmpIconMirrored.GetAlphaPixel(
                    bmpIconMirrored.GetChannelNum(0), xFromRight, y)
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


def RegisterIcons():
    '''RegisterIcons() registers all icons needed by the plugin.

    It returns the bitmap of the Rokoko Studio Live logo for use during plugin
    registration.
    '''

    # Icons can not be registered twice.
    # "Reload Python Plugins" to work properly, we first need unregister all
    # icons, we registered in the previous run.
    c4d.gui.UnregisterIcon(rid.PLUGIN_ID_TAG_ICON_ACTOR)
    c4d.gui.UnregisterIcon(rid.PLUGIN_ID_TAG_ICON_FACE)
    c4d.gui.UnregisterIcon(rid.PLUGIN_ID_TAG_ICON_LIGHT)
    c4d.gui.UnregisterIcon(rid.PLUGIN_ID_TAG_ICON_CAMERA)
    c4d.gui.UnregisterIcon(rid.PLUGIN_ID_TAG_ICON_PROP)
    c4d.gui.UnregisterIcon(rid.PLUGIN_ID_ICON_SUIT)
    c4d.gui.UnregisterIcon(rid.PLUGIN_ID_ICON_GLOVE_LEFT)
    c4d.gui.UnregisterIcon(rid.PLUGIN_ID_ICON_GLOVE_RIGHT)
    c4d.gui.UnregisterIcon(rid.PLUGIN_ID_ICON_FACE)
    c4d.gui.UnregisterIcon(rid.PLUGIN_ID_ICON_PROP)
    c4d.gui.UnregisterIcon(rid.PLUGIN_ID_ICON_PROFILE)
    c4d.gui.UnregisterIcon(rid.PLUGIN_ID_ICON_STUDIO_LIVE)
    c4d.gui.UnregisterIcon(rid.PLUGIN_ID_COMMAND_API_ICON_RECORD_START)
    c4d.gui.UnregisterIcon(rid.PLUGIN_ID_COMMAND_API_ICON_RECORD_STOP)
    c4d.gui.UnregisterIcon(rid.PLUGIN_ID_COMMAND_API_ICON_CALIBRATE_SUIT)
    c4d.gui.UnregisterIcon(rid.PLUGIN_ID_COMMAND_API_ICON_RESTART_SUIT)

    # Register all icons
    RegisterImageAsIcon(
        rid.PLUGIN_ID_TAG_ICON_ACTOR, "icon-row-suit-32.png")
    RegisterImageAsIcon(
        rid.PLUGIN_ID_TAG_ICON_FACE, "icon-row-face-32.png")
    RegisterImageAsIcon(
        rid.PLUGIN_ID_TAG_ICON_LIGHT, "rokoko_tag_light.png")
    RegisterImageAsIcon(
        rid.PLUGIN_ID_TAG_ICON_CAMERA, "rokoko_tag_camera.png")
    RegisterImageAsIcon(
        rid.PLUGIN_ID_TAG_ICON_PROP, "icon-vp-32.png")
    RegisterImageAsIcon(
        rid.PLUGIN_ID_ICON_SUIT, "icon-row-suit-32.png", size=16)
    RegisterImageAsIcon(
        rid.PLUGIN_ID_ICON_GLOVE_LEFT, "icon-input-gloves-32px.png", size=16)
    RegisterImageAsIcon(
        rid.PLUGIN_ID_ICON_GLOVE_RIGHT, "icon-input-gloves-32px.png",
        mirrorHorizontally=True, size=16)
    RegisterImageAsIcon(
        rid.PLUGIN_ID_ICON_FACE, "icon-row-face-32.png", size=16)
    RegisterImageAsIcon(rid.PLUGIN_ID_ICON_PROP, "icon-vp-32.png", size=16)
    RegisterImageAsIcon(
        rid.PLUGIN_ID_ICON_PROFILE, "icon-rokoko-32.png", size=16)
    bmpIconForCommand = RegisterImageAsIcon(
        rid.PLUGIN_ID_ICON_STUDIO_LIVE, "icon-studio-live-32.png")
    RegisterImageAsIcon(
        rid.PLUGIN_ID_COMMAND_API_ICON_RECORD_START, "icon-record-32.png")
    RegisterImageAsIcon(
        rid.PLUGIN_ID_COMMAND_API_ICON_RECORD_STOP, "icon-stop-white-32.png")
    RegisterImageAsIcon(
        rid.PLUGIN_ID_COMMAND_API_ICON_CALIBRATE_SUIT,
        "icon-straight-pose-32.png")
    RegisterImageAsIcon(
        rid.PLUGIN_ID_COMMAND_API_ICON_RESTART_SUIT, "icon-restart-32.png")
    return bmpIconForCommand


def RegisterRokokoStudioLive():
    '''RegisterRokokoStudioLive() registers all plugins needed for
    Rokoko Studi Live.

    This is done depending on plugin's enabled state in prefs.
    '''

    # Check if the plugin is enabled in preferences
    bcPrefs = GetWorldPrefs()
    if bcPrefs[rid.ID_PREF_PLUGIN_ENABLED] or \
       bcPrefs[rid.ID_PREF_PLUGIN_ENABLED] is None:
        # Initialize globally needed structures
        InitBaseContainer()
        InitRokokoLogo()
        bmpIcon = RegisterIcons()
        LoadStudioTPose()

        # Register plugins
        result = c4d.plugins.RegisterMessagePlugin(
            id=rid.PLUGIN_ID_MESSAGEDATA,
            str="",
            info=0,
            dat=MessageDataRokoko())
        if not result:
            print(f"ERROR: Rokoko Studio Live ({rid.PLUGIN_VERSION}) failed "
                  "to register MessageData.")
            return
        result = c4d.plugins.RegisterTagPlugin(
            id=rid.PLUGIN_ID_TAG,
            str=rid.PLUGIN_NAME_TAG,
            info=c4d.TAG_EXPRESSION | c4d.TAG_VISIBLE,
            g=TagDataRokoko,
            description="Trokoko",
            icon=bmpIcon)
        if not result:
            print(f"ERROR: Rokoko Studio Live ({rid.PLUGIN_VERSION}) failed "
                  "to register Tag.")
            return
        result = c4d.plugins.RegisterCommandPlugin(
            id=rid.PLUGIN_ID_COMMAND_MANAGER,
            str=rid.PLUGIN_NAME_COMMAND_MANAGER,
            help=f"Open {rid.PLUGIN_NAME_COMMAND_MANAGER}",
            info=0,
            dat=CommandDataRokokoManager(),
            icon=bmpIcon)
        if not result:
            print(f"ERROR: Rokoko Studio Live ({rid.PLUGIN_VERSION}) failed "
                  "to register Manager CommandData.")
            return
        print("Successfully registered Rokoko Studio Live "
              f"({rid.PLUGIN_VERSION}).")

    # The preferences page is registered in any case (even if plugin got
    # disabled by the user).
    # It's needed by the user to reenable the plugin.
    res = c4d.plugins.RegisterPreferencePlugin(
        id=rid.PLUGIN_ID_PREFS,
        g=PreferenceDataRokoko,
        name=rid.PLUGIN_NAME_COMMAND_MANAGER,
        description="rokokopreferences",
        parentid=0,
        sortid=0)
    if not res:
        print(f"ERROR: Rokoko Studio Live ({rid.PLUGIN_VERSION}) failed to "
              "register PrefData.")


# EXECUTION STARTS HERE
if __name__ == "__main__":
    if not __USE_LZ4__:
        WarnNoLZ4()

    TestUDPPaketSize()

    RegisterRokokoStudioLive()
