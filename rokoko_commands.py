# In Cinema 4D CommandData plugins represent commands, usually represented in the UI as
# menu entries or icons in command palettes.
#
# In Rokoko Studio Live there currently is only one command, which opens and owns the
# Rokoko Studio Live Manager dialog.
import c4d
from rokoko_ids import *
from rokoko_utils import *
from rokoko_dialog_manager import *

# The dialog needs to be globally accessible, so it can be properly shut down in PluginMessage()
g_dlgManager = None

# To be called during shutdown
def CommandsDestroyGlobals():
    global g_dlgManager
    if g_dlgManager is not None:
        if not g_dlgManager.Close():
            c4d.gui.MessageDialog('SEVERE ISSUE: FAILED TO CLOSE DIALOG')
        g_dlgManager = None


class CommandDataRokokoManager(c4d.plugins.CommandData):
    _dlg = None

    # Called by C4D, when the user executes the command
    def Execute(self, doc):
        # If there is already a dialog, reuse it, otherwise create one
        global g_dlgManager
        if self._dlg is None:
            self._dlg = g_dlgManager
        if self._dlg is None:
            self._dlg = DialogRokokoManager()
            g_dlgManager = self._dlg
        if self._dlg is None:
            return False

        # Force the dialog to gather tags from scene
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAGS)

        # Open the dialog
        return self._dlg.Open(dlgtype=c4d.DLG_TYPE_ASYNC, pluginid=PLUGIN_ID_COMMAND_MANAGER, defaulth=0, defaultw=0)


    # Called by C4D to restore the dialog (e.g. after the user switched the UI layout)
    def RestoreLayout(self, sec_ref):
        # If there is no dialog, yet, create one
        global g_dlgManager
        if self._dlg is None:
            self._dlg = DialogRokokoManager()
            g_dlgManager = self._dlg

        # Restore the dialog
        return self._dlg.Restore(pluginid=PLUGIN_ID_COMMAND_MANAGER, secret=sec_ref)


    # Called by C4D to detemine the state of this command, if it's enable or active
    def GetState(self, doc):
        # The command is always enabled
        state = c4d.CMD_ENABLED

        # If the manager dialog is open, reflect this in command's icon highlighting
        if self._dlg is not None and self._dlg.IsOpen():
            state |= c4d.CMD_VALUE
        return state
