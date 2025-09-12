'''PreferenceData plugins allow to hook a plugin into Cinema 4D's preferences
and have their own preferences page.

The Rokoko Studio Live plugin has almost no parameters, that need to be handled
via a PreferenceData.
Actually only one: The option to enable and disable the Rokoko Studio Live
plugin.

This PreferenceData is also the only plugin, Rokoko Studio Live registers,
even if the user decided to disable the plugin. For obvious reasons,
it's needed for the user to be able to reenable the plugin.
'''

import c4d

import rokoko_ids as rid
from rokoko_utils import GetWorldPrefs
from rokoko_description_utils import GetDDescriptionCreateBool


# It seems not to be possible to register a PreferenceData without a
# description resource, even if one plans to create the content of the
# preferences page dynamically (as in this plugin).
# So there's a more or less empty description resource only providing a main
# group, where all dynamically created parameters will reside in.

# From Maxon's example code:
# The first time Cinema 4D will compile this script into Python Bytecode,
# symbols will not be yet parsed.
# This will cause ROKOKOPREFERENCES_MAIN_GROUP not defined in the c4d module.
# Thats why we manually do it
if not hasattr(c4d, "ROKOKOPREFERENCES_MAIN_GROUP"):
    c4d.ROKOKOPREFERENCES_MAIN_GROUP = 999


DID_PREF_PLUGIN_ENABLED = c4d.DescID(c4d.DescLevel(rid.ID_PREF_PLUGIN_ENABLED,
                                                   c4d.DTYPE_BOOL,
                                                   0))


class PreferenceDataRokoko(c4d.plugins.PreferenceData):

    def InitValues(self, descId, description=None):
        bcWorldPrefs = GetWorldPrefs()

        paramId = descId[0].id
        if paramId == rid.ID_PREF_PLUGIN_ENABLED:
            self.InitPreferenceValue(
                paramId, True, description, descId, bcWorldPrefs)

        return True

    def Init(self, node, isCloneInit=False):
        '''Called by C4D to initialize the preference values.'''

        self.InitValues(DID_PREF_PLUGIN_ENABLED)
        return True

    def GetDDescription(self, node, description, flags):
        '''Called by C4D to set a preference parameter value'''

        # Load the Description resource (C4D caches these internally)
        if not description.LoadDescription("rokokopreferences"):
            print(f"{rid.PLUGIN_NAME_COMMAND_MANAGER} ERROR: "
                  "Failed to load Description")
            return False

        # If default values are requested, reinitialize
        if flags & c4d.DESCFLAGS_DESC_NEEDDEFAULTVALUE:
            self.InitValues(DID_PREF_PLUGIN_ENABLED, description)

        # For optimization purposes C4D doesn't always relayout the entire
        # Description.
        # Based on singleId C4D may request to just relayout a single
        # description parameter.
        singleId = description.GetSingleDescID()

        # Create "Rokoko Studio Live Plugin Enabled" parameter with a
        # checkbox widget
        if not GetDDescriptionCreateBool(
                node, description, singleId, rid.ID_PREF_PLUGIN_ENABLED,
                ("Enable Rokoko Studio Live Plugin "
                 "(change needs C4D restart to take effect)"),
                c4d.ROKOKOPREFERENCES_MAIN_GROUP, anim=False, valDefault=True):
            return False
        return True, flags | c4d.DESCFLAGS_DESC_LOADED

    def SetDParameter(self, node, id, data, flags):
        '''Called by C4D to set a preference parameter value'''

        bc = GetWorldPrefs()
        paramID = id[0].id

        if paramID == rid.ID_PREF_PLUGIN_ENABLED:
            bc.SetBool(paramID, data)

        return True, flags | c4d.DESCFLAGS_SET_PARAM_SET

    def GetDParameter(self, node, id, flags):
        '''Called by C4D to read a preference parameter value'''

        bc = GetWorldPrefs()
        paramID = id[0].id

        if paramID == rid.ID_PREF_PLUGIN_ENABLED:
            flags |= c4d.DESCFLAGS_GET_PARAM_GET
            return True, bc.GetBool(paramID), flags

        return False
