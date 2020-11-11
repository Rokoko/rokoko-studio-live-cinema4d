import c4d
from rokoko_ids import *
from rokoko_utils import *
from rokoko_description_utils import *

try:
    # TODO Andreas: Check with Maxon, how to reliably access resource symbols...
    ROKOKOPREFERENCES_MAIN_GROUP = c4d.ROKOKOPREFERENCES_MAIN_GROUP
except:
    ROKOKOPREFERENCES_MAIN_GROUP = 999


class PreferenceDataRokoko(c4d.plugins.PreferenceData):

        def InitPrefValue(self, description, id, dtype, bcWorldPrefs):
            self.InitPreferenceValue(id, True, description, c4d.DescID(c4d.DescLevel(id, dtype, 0)), bcWorldPrefs)

        def Init(self, node, description=None):
            bcWorldPrefs = GetWorldPrefs()
            self.InitPrefValue(description, ID_PREF_PLUGIN_ENABLED, c4d.DTYPE_BOOL, bcWorldPrefs)
            return True

        def GetDDescription(self, node, description, flags):
            if not description.LoadDescription('rokokopreferences'):
                print('{0} ERROR: Failed to load Description'.format(PLUGIN_NAME_COMMAND_MANAGER))
                return False
            if flags & c4d.DESCFLAGS_DESC_NEEDDEFAULTVALUE:
                self.Init(node, description)
            singleId = description.GetSingleDescID()
            if not GetDDescriptionCreateBool(node, description, singleId, ID_PREF_PLUGIN_ENABLED, \
                                             'Enable Rokoko Studio Live Plugin (change needs C4D restart to take effect)', \
                                             ROKOKOPREFERENCES_MAIN_GROUP, anim=False, valDefault=True):
                return False
            return True, flags | c4d.DESCFLAGS_DESC_LOADED

        def SetDParameter(self, node, id, data, flags):
            bc = GetWorldPrefs()
            paramID = id[0].id
            if paramID == ID_PREF_PLUGIN_ENABLED:
                bc.SetBool(paramID, data)
            return True, flags | c4d.DESCFLAGS_SET_PARAM_SET

        def GetDParameter(self, node, id, flags):
            bc = GetWorldPrefs()
            paramID = id[0].id
            if paramID == ID_PREF_PLUGIN_ENABLED:
                return True, bc.GetBool(paramID), flags | c4d.DESCFLAGS_GET_PARAM_GET
