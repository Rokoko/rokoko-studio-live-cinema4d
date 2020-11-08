import c4d
from rokoko_ids import *
from rokoko_utils import *
from rokoko_dialog_manager import *

g_dlgManager = None
def CommandsDestroyGlobals():
    global g_dlgManager
    if g_dlgManager is not None:
        if not g_dlgManager.Close():
            c4d.gui.MessageDialog('SEVERE ISSUE: FAILED TO CLOSE DIALOG')
        g_dlgManager = None

class CommandDataRokokoManager(c4d.plugins.CommandData):
    _dlg = None

    def Execute(self, doc):
        global g_dlgManager
        if self._dlg is None:
            self._dlg = g_dlgManager
        if self._dlg is None:
            self._dlg = DialogRokokoManager()
            g_dlgManager = self._dlg
        if self._dlg is None:
            return False
        c4d.SpecialEventAdd(PLUGIN_ID_COREMESSAGE_MANAGER, CM_SUBID_MANAGER_UPDATE_TAGS)
        return self._dlg.Open(dlgtype=c4d.DLG_TYPE_ASYNC, pluginid=PLUGIN_ID_COMMAND_MANAGER, defaulth=0, defaultw=0)

    def RestoreLayout(self, sec_ref):
        global g_dlgManager
        if self._dlg is None:
            self._dlg = DialogRokokoManager()
            g_dlgManager = self._dlg
        return self._dlg.Restore(pluginid=PLUGIN_ID_COMMAND_MANAGER, secret=sec_ref)

    def GetState(self, doc):
        state = c4d.CMD_ENABLED
        if self._dlg is not None and self._dlg.IsOpen():
            state |= c4d.CMD_VALUE
        return state
