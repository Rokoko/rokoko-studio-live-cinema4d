# PreferenceData plugins allow to hook a plugin into Cinema 4D's preferences and have their
# own preferences page.
#
# The Rokoko Studio Live plugin has almost no parameters, that need to be handled via a PreferenceData.
# Actually only one: The option to enable and disable the Rokoko Studio Live plugin.
#
# This PreferenceData is also the only plugin, Rokoko Studio Live registers,
# even if the user decided to disable the plugin. For obvious reasons,
# it's needed for the user to be able to reenable the plugin.
import c4d
from rokoko_ids import *
from rokoko_utils import *
from rokoko_description_utils import *

# It seems not to be possible to register a PreferenceData without a description resource,
# even if one plans to create the content of the preferences page dynamically (as in this plugin).
# So there's a more or less empty description resource only providing a main group, where all
# dynamically created parameters will reside in.
# During development the group ID symbol sometimes went missing. Most likely this shouldn't be an
# issue for a user. Nevertheless we only try to use this constant and define it on our own,
# if it's not available.
try:
    # TODO Andreas: Check with Maxon, how to reliably access resource symbols...
    ROKOKOPREFERENCES_MAIN_GROUP = c4d.ROKOKOPREFERENCES_MAIN_GROUP
except:
    ROKOKOPREFERENCES_MAIN_GROUP = 999


class PreferenceDataRokoko(c4d.plugins.PreferenceData):

        def InitPrefValue(self, description, id, dtype, bcWorldPrefs):
            self.InitPreferenceValue(id, True, description, c4d.DescID(c4d.DescLevel(id, dtype, 0)), bcWorldPrefs)


        # Called by C4D to initialize the preference values.
        def Init(self, node, description=None):
            bcWorldPrefs = GetWorldPrefs()
            self.InitPrefValue(description, ID_PREF_PLUGIN_ENABLED, c4d.DTYPE_BOOL, bcWorldPrefs)
            return True


        # Called by C4D to set a preference parameter value
        def GetDDescription(self, node, description, flags):
            # Load the Description resource (C4D caches these internally)
            if not description.LoadDescription('rokokopreferences'):
                print('{0} ERROR: Failed to load Description'.format(PLUGIN_NAME_COMMAND_MANAGER))
                return False

            # If default values are requested, reinitialize
            if flags & c4d.DESCFLAGS_DESC_NEEDDEFAULTVALUE:
                self.Init(node, description)

            # For optimization purposes C4D doesn't always relayout the entire Description.
            # Based on singleId C4D may request to just relayout a single description parameter.
            singleId = description.GetSingleDescID()

            # Create "Rokoko Studio Live Plugin Enabled" parameter with a checkbox widget
            if not GetDDescriptionCreateBool(node, description, singleId, ID_PREF_PLUGIN_ENABLED, \
                                             'Enable Rokoko Studio Live Plugin (change needs C4D restart to take effect)', \
                                             ROKOKOPREFERENCES_MAIN_GROUP, anim=False, valDefault=True):
                return False
            return True, flags | c4d.DESCFLAGS_DESC_LOADED


        # Called by C4D to set a preference parameter value
        def SetDParameter(self, node, id, data, flags):
            bc = GetWorldPrefs()
            paramID = id[0].id
            if paramID == ID_PREF_PLUGIN_ENABLED:
                bc.SetBool(paramID, data)
            return True, flags | c4d.DESCFLAGS_SET_PARAM_SET


        # Called by C4D to read a preference parameter value
        def GetDParameter(self, node, id, flags):
            bc = GetWorldPrefs()
            paramID = id[0].id
            if paramID == ID_PREF_PLUGIN_ENABLED:
                return True, bc.GetBool(paramID), flags | c4d.DESCFLAGS_GET_PARAM_GET
