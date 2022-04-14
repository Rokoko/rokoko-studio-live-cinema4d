import c4d
from rokoko_dialog_utils import *
from rokoko_ids import *
from rokoko_utils import *


# Unique IDs registered in Plugin Cafe
# These IDs are not unique to a single plugin module,
# but used in all plugin modules using these requesters.
# C4D stores dialog's size information referenced by these IDs.
# Thus multiple IDs are used to avoid requesters with many lines leading to
# huge requesters with only few lines in succession.
PLUGIN_IDS_REQUESTER = [ 1059323, 1059324, 1059325, 1059326, 1059327 ]


# Icon IDs, just a few which may come in handy
DQ_ICON_QUESTION_WHITE = 300000157
DQ_ICON_QUESTION_RED = 300002170
DQ_ICON_QUESTION_ORANGE = 17190
DQ_ICON_QUESTION_DOC = 1050848
DQ_ICON_QUESTION_STRIPED = 1050586
DQ_ICON_QUESTION_CHECKER = 5616
DQ_ICON_QUESTION_FLOPPY =  100004743
DQ_ICON_RECYCLE = 440000296
DQ_ICON_EXCLAMATION_WHITE_BG = 1031728
DQ_ICON_EXCLAMATION_ORANGE_BAM = 1018880
DQ_ICON_LIGHTBULB = 5102
DQ_ICON_TRASHCAN = 13685
DQ_ICON_GLOBE_ORANGE = 450000017
DQ_ICON_RADIO_ACTIVE_ORANGE = 13663
DQ_ICON_X_GREY_BG = 13957

DQ_ICON_ERROR = DQ_ICON_EXCLAMATION_WHITE_BG


# The internal requester ID, may either be specified directly or
# a string may be passed, either as requester ID or via an requester's
# text message (actually the firrst line thereof).
# This function does so...
def EncodeRequesterId(idRequester=None, msgs=['']):
    if idRequester is None:
        if type(msgs[0]) == tuple:
            idRequester = MyHash(msgs[0][0])

        else:
            idRequester = MyHash(msgs[0])

    elif type(idRequester) == str:
        idRequester = MyHash(idRequester)

    else:
        pass

    return idRequester


# Reads user's previous choice from preferences.
# idRequester may also be a string, e.g. an requester's text.
def GetRequesterChoice(idRequester=None, msgs=['']):
    bcRequesters = GetPrefsContainer(ID_BC_REQUESTER_CHOICES)

    # If there is no BaseContainer with previous choices, well, then there were no choices...
    if bcRequesters is None:
        return None

    idRequester = EncodeRequesterId(idRequester, msgs)

    # Look for previous choice and return it
    choice = None

    if bcRequesters.FindIndex(idRequester)['index'] != -1:
        choice = bcRequesters.GetInt32(idRequester)

    return choice


# Stores user's choice in preferences, so the requester does not need to be shown again.
def SetRequesterChoice(idRequester, choice):
    bcRequesters = GetPrefsContainer(ID_BC_REQUESTER_CHOICES)

    # If there is no BaseContainer with previous choices, create one
    if bcRequesters is None:
        bcWorldPrefs = c4d.plugins.GetWorldPluginData(PLUGIN_ID_CAMS)

        bcWorldPrefs.SetContainer(ID_BC_REQUESTER_CHOICES, c4d.BaseContainer())

        bcRequesters = bcWorldPrefs.GetContainerInstance(ID_BC_REQUESTER_CHOICES)

    # Store user's choice
    bcRequesters.SetInt32(idRequester, choice)


# Normally handling of previous user choices
# and in the following avoiding the requester to be opened again,
# is handled internally.
# This may not always be good.
# Imagine a requester choice,
# which causes some action (e.g. opening a web link to documentation).
# Then it may not always be desired, to always directly open that link
# instead of the requester. Instead one may prefer to simply quiten the
# requester.
# Therefore the user choice can be overriden in such cases.
def OverrideRequesterChoice(choice, idRequester=None, msgs=['']):
    idRequester = EncodeRequesterId(idRequester, msgs)

    if GetRequesterChoice(idRequester) is None:
        return False # not overridden

    print('OVERRIDE CHOICE', idRequester, choice)
    SetRequesterChoice(idRequester, choice)

    return True # overridden



# Convenience function to open a requester with a bunch of default option.
# If there is a previous user choice for this requester, it will be returned directly,
# instead of opening the requester.
def OpenRequester(title='', msgs=[''], buttonLabels=['Ok'], icon=DQ_ICON_QUESTION_WHITE,
                  twoButtonRows=True, lastButtonExtra=True, idxFocus=-1, idxAbort=-1, scaleIcon=2.0,
                  wIcon=c4d.gui.SizePix(65), wButton=c4d.gui.SizePix(65), hButton=c4d.gui.SizePix(20),
                  idRequester=None, saveDefault=False,
                  xpos=-2, ypos=-2):
    # Create dialog instance
    dlg = DialogQuestion(title, msgs, buttonLabels, icon, twoButtonRows, lastButtonExtra, idxFocus,
                         idxAbort, scaleIcon, wIcon, wButton, hButton, idRequester, saveDefault)

    # Get user's previous choice. If any, return it.
    choice = GetRequesterChoice(dlg.GetRequesterId())
    if choice is not None:
        return choice

    # Choose a requester Plugin ID
    # taking number of text lines and number of button rows into account.
    idxSize = max(3, len(msgs)) - 3
    if twoButtonRows:
        idxSize += 1

    idxSize = min(idxSize, len(PLUGIN_IDS_REQUESTER) - 1)

    idPluginRequester = PLUGIN_IDS_REQUESTER[idxSize]

    # Open the requester
    dlg.Open(c4d.DLG_TYPE_MODAL, idPluginRequester, xpos=xpos, ypos=ypos, defaultw=0, defaulth=0)

    return dlg.GetResult()


# Convenience function to open a question requester.
def OpenQuestionDialog(title='', msgs=[''], buttonLabels=['Ok'], icon=DQ_ICON_QUESTION_WHITE,
                       twoButtonRows=False, lastButtonExtra=True, idxFocus=-1, idxAbort=-1, scaleIcon=2.0,
                       wIcon=c4d.gui.SizePix(65), wButton=c4d.gui.SizePix(65), hButton=c4d.gui.SizePix(20),
                       idRequester=None, saveDefault=False,
                       xpos=-2, ypos=-2):
    return OpenRequester(title, msgs, buttonLabels, icon, twoButtonRows, lastButtonExtra, idxFocus,
                         idxAbort, scaleIcon, wIcon, wButton, hButton, idRequester, saveDefault, xpos, ypos)


# Convenience function to open a question requester with buttons Yes and No.
DQ_RESULT_YES = 0
DQ_RESULT_NO = 1

def OpenYesNoDialog(title='', msgs=[''], buttonLabels=['Yes', 'No'], icon=DQ_ICON_QUESTION_WHITE,
                    twoButtonRows=False, lastButtonExtra=False, idxFocus=1, idxAbort=1, scaleIcon=2.0,
                    wIcon=c4d.gui.SizePix(65), wButton=c4d.gui.SizePix(65), hButton=c4d.gui.SizePix(20),
                    idRequester=None, saveDefault=False,
                    xpos=-2, ypos=-2):
    return OpenRequester(title, msgs, buttonLabels, icon, twoButtonRows, lastButtonExtra, idxFocus,
                         idxAbort, scaleIcon, wIcon, wButton, hButton, idRequester, saveDefault, xpos, ypos)


# Convenience function to open an error requester.
def OpenErrorDialog(title='ERROR', msgs=[''], buttonLabels=['Ok'], icon=DQ_ICON_ERROR,
                    twoButtonRows=False, lastButtonExtra=False, idxFocus=0, idxAbort=0, scaleIcon=2.0,
                    wIcon=c4d.gui.SizePix(65), wButton=c4d.gui.SizePix(65), hButton=c4d.gui.SizePix(20),
                    idRequester=None, saveDefault=False,
                    xpos=-2, ypos=-2):
    return OpenRequester(title, msgs, buttonLabels, icon, twoButtonRows, lastButtonExtra, idxFocus,
                         idxAbort, scaleIcon, wIcon, wButton, hButton, idRequester, saveDefault, xpos, ypos)


# Convenience function to open an info requester.
def OpenInfoDialog(title='', msgs=[''], buttonLabels=['Ok'], icon=DQ_ICON_LIGHTBULB,
                   twoButtonRows=False, lastButtonExtra=False, idxFocus=0, idxAbort=0, scaleIcon=2.0,
                   wIcon=c4d.gui.SizePix(65), wButton=c4d.gui.SizePix(65), hButton=c4d.gui.SizePix(20),
                   idRequester=None, saveDefault=False,
                   xpos=-2, ypos=-2):
    return OpenRequester(title, msgs, buttonLabels, icon, twoButtonRows, lastButtonExtra, idxFocus,
                         idxAbort, scaleIcon, wIcon, wButton, hButton, idRequester, saveDefault, xpos, ypos)



# Custom requester dialog class.
# The requester features an image (e.g. maybe an exclamation mark for errors),
# multiple lines of text message, an arbitrary number of choice buttons and
# an optional "Do not show again" checkbox.
class DialogQuestion(c4d.gui.GeDialog):

    ID_BASE_BUTTON = 1000
    ID_CHECKBOX_SAVEDEFAULT = 2000

    _id = None # Requester's ID, used to store user choices
    _title = '' # Requester's window title, if empty string, plugin's name will be used
    _msgs = [''] # List of strings (or tuples, see below), the actual text message, one list entry per line
    _buttonLabels = [] # List of strings, defines the number of buttons and their labels
    _icon = None # BaseBitmap to show left of the text
    _twoButtonRows = True
    _lastButtonExtra = True # If true, the last button will be in an extra column spanning both rows
    _idxFocus = -1 # Default button ID, the button to press by simply pressing return (depending on C4D version this works or not...)
    _idxAbort = -1 # -1: Do not allow abortion of the requester, otherwise return this value in case of abortion
    _wIcon = 32 # Image size, defined by width
    _wButton = 0 # Width of buttons
    _hButton = 0 # Height of button row
    _saveDefault = False # If true, display "Do not show again" checkbox

    _result = -1 # Holds requester's result to be retrieved via GetResult()


    # Note on _msgs:
    # The list entries can either be strings or tuples consisting of a string and a c4d.BORDER_ value.
    # The latter can be used to set lines in bold text (c4d.BORDER_WITH_TITLE_BOLD).


    def __init__(self, title='', msgs=[''], buttonLabels=['Ok'], icon=DQ_ICON_QUESTION_WHITE,
                 twoButtonRows=True, lastButtonExtra=True, idxFocus=-1, idxAbort=-1,
                 scaleIcon=1.0, wIcon=c4d.gui.SizePix(65),
                 wButton=c4d.gui.SizePix(65), hButton=c4d.gui.SizePix(20),
                 idRequester=None, saveDefault=False):

        self._id = EncodeRequesterId(idRequester, msgs)

        self._title = title
        self._msgs = msgs
        self._buttonLabels = buttonLabels

        if icon is None:
            self._icon = None

        elif type(icon) == c4d.bitmaps.BaseBitmap:
            self._icon = icon
            scaleIcon = 1.0

        elif type(icon) == int:
            self._icon = GetIconImage(icon)

        elif type(icon) == str:
            self._icon = LoadImage(icon)
            scaleIcon = 1.0

        else:
            self._icon = GetIconImage(DQ_ICON_QUESTION_RED)

        if self._icon is not None and scaleIcon != 1.0:
            self._icon = ScaleImage(self._icon, factor=scaleIcon)

        self._twoButtonRows = twoButtonRows
        self._lastButtonExtra = lastButtonExtra
        self._idxFocus = idxFocus
        self._idxAbort = idxAbort
        self._wIcon = wIcon
        self._wButton = wButton
        self._hButton = hButton
        self._saveDefault = saveDefault

        self._result = -1

        c4d.gui.GeDialog.__init__(self)


    # Called by C4D to draw the dialog
    def CreateLayout(self):
        # Layout has one or two columns, depending if an image is supposed to be shown
        numMainCols = 1
        if self._icon is not None:
            numMainCols = 2

        numButtonCols = 1
        buttonLabels = self._buttonLabels
        flagsMainButtons = c4d.BFH_SCALE | c4d.BFH_CENTER | c4d.BFV_BOTTOM
        if self._lastButtonExtra:
            numButtonCols = 2
            buttonLabels = self._buttonLabels[:-1]
            flagsMainButtons = c4d.BFH_SCALEFIT | c4d.BFV_BOTTOM

        numCols = len(buttonLabels)
        if self._twoButtonRows:
            numCols = len(buttonLabels) // 2

        if len(self._title) > 0:
            self.SetTitle('{0} - {1}'.format(PLUGIN_NAME_COMMAND_MANAGER, self._title)) # dialog's window title

        else:
            # If no window title specified, use plugin's name
            self.SetTitle('{0}'.format(PLUGIN_NAME_COMMAND_MANAGER))

        if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1): # Dialog main group
            self.GroupBorderSpace(10, 12, 10, 3)

            if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=numMainCols): # Image/Text group
                self.GroupSpace(15, 0)

                if self._icon is not None:
                    CreateLayoutAddBitmapButton(self, 0, bmp=self._icon, button=False, toggle=False, noHover=True, w=self._wIcon)

                if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_SCALE | c4d.BFV_CENTER, cols=1): # Text lines group
                    for msg in self._msgs:
                        if type(msg) == str:
                            self.AddStaticText(0, c4d.BFH_SCALEFIT, name=msg)

                        elif type(msg) == tuple:
                            self.AddStaticText(0, c4d.BFH_SCALEFIT, name=msg[0], borderstyle=msg[1])

                        else:
                            PrintError('Unknown message line type! {1}'.format(type(msg)))

                self.GroupEnd() # Text lines group

            self.GroupEnd() # Image/Text group

            self.AddStaticText(0, c4d.BFH_SCALEFIT, name='') # spacer

            if self._saveDefault:
                self.AddCheckbox(self.ID_CHECKBOX_SAVEDEFAULT, c4d.BFH_LEFT, initw=0, inith=0, name='Do not show again')

            if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_BOTTOM, cols=numButtonCols): # Buttons group

                if self.GroupBegin(0, flagsMainButtons, cols=numCols):
                    for idxLabel, label in enumerate(buttonLabels):
                        self.AddButton(self.ID_BASE_BUTTON + idxLabel, c4d.BFH_CENTER, initw=self._wButton, inith=self._hButton, name=label)

                self.GroupEnd() # Buttons group

                if self._lastButtonExtra:
                    self.AddButton(self.ID_BASE_BUTTON + len(self._buttonLabels) - 1, c4d.BFH_CENTER | c4d.BFV_SCALEFIT, initw=self._wButton, name=self._buttonLabels[-1])

            self.GroupEnd()

        self.GroupEnd() # Dialog main group

        if self._idxFocus != -1:
            self.Activate(self._idxFocus)

        return True


    # Called by C4D to initialize widget values.
    def InitValues(self):
        if self._saveDefault:
            self.SetBool(self.ID_CHECKBOX_SAVEDEFAULT, False)

        return True


    # Called by C4D when the dialog is about to be closed in whatever way.
    # Returning True would deny the "close request" and the dialog stayed open.
    def AskClose(self):
        # If user did not press a button and we are here...
        if self._result == -1:
            # Either force dialog to stay open
            if self._idxAbort == -1:
                return True

            # or return the abort value
            else:
                self._result = self._idxAbort

        # If "Do not show again" checkbox is enabled and checked, store user's button press
        if self._saveDefault and self.GetBool(self.ID_CHECKBOX_SAVEDEFAULT):
            SetRequesterChoice(self._id, self._result)

        return False


    # Called by C4D to handle user's interaction with the dialog.
    def Command(self, id, msg):
        # Any of the buttons pressed?
        if id >= self.ID_BASE_BUTTON and id < self.ID_BASE_BUTTON + len(self._buttonLabels):
            # Store button pressed by user and close the requester
            self._result = id - self.ID_BASE_BUTTON

            self.Close()

        return True


    # Returns the internal ID of this requesterr instance.
    def GetRequesterId(self):
        return self._id


    # Use to retrieve requester's result after requester has been closed.
    def GetResult(self):
        return self._result
