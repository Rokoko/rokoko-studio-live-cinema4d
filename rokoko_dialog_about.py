'''A very simple About dialog.'''

import os

import c4d

import rokoko_ids as rid
from rokoko_dialog_utils import (
    CreateLayoutAddBitmapButton,
)


# The logo bitmap is loaded once at startup.
# Only to save a small fraction of a second, when the user opens the dialog.
g_bmpLogo = None


def InitRokokoLogo():
    '''Loads annd scales the logo bitmap'''

    global g_bmpLogo

    g_bmpLogo = None

    # Load logo bitmap
    bmp = c4d.bitmaps.BaseBitmap()
    result, _ = bmp.InitWith(
        os.path.join(
            os.path.dirname(__file__), "res", "rokoko-studio-live-logo.png"))
    if result != c4d.IMAGERESULT_OK:
        print(f"ERROR: Failed ({result}) to load logo for About dialog")
        return

    # Scale the bitmap to the desired logo size
    g_bmpLogo = c4d.bitmaps.BaseBitmap()
    g_bmpLogo.Init(200, 200)
    bmp.ScaleIt(g_bmpLogo, 256, True, False)


def DlgAboutDestroyGlobals():
    '''To be called during shutdown'''

    global g_bmpLogo
    g_bmpLogo = None


class DialogAbout(c4d.gui.GeDialog):
    '''Simple About dialog, displaying a logo on the left side and multiple
    text lines on the right.
    '''

    def __init__(self, title=f"About {rid.PLUGIN_NAME_COMMAND_MANAGER}"):
        '''Title of the dialog can be set from outside upon instancing the
        dialog
        '''

        self._title = title
        c4d.gui.GeDialog.__init__(self)

    def CreateLayout(self):
        '''Called by C4D to draw the dialog'''

        self.SetTitle(self._title)  # dialog's window title

        if self.GroupBegin(  # Dialog main group
                0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1):
            self.GroupBorderSpace(7, 5, 7, 3)
            self.GroupSpace(0, 15)

            if self.GroupBegin(  # About content group
                    0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=2):
                self.GroupSpace(20, 0)

                if self.GroupBegin(  # Logo
                        0, c4d.BFH_SCALEFIT | c4d.BFV_CENTER, cols=1):
                    CreateLayoutAddBitmapButton(
                        self, 0, bmp=g_bmpLogo, button=False, toggle=False)
                self.GroupEnd()  # Logo

                if self.GroupBegin(  # About Text
                        0, c4d.BFH_SCALEFIT | c4d.BFV_CENTER, cols=1):
                    self.AddStaticText(
                        0, c4d.BFH_SCALEFIT,
                        initw=500,
                        name=(f"{rid.PLUGIN_NAME_COMMAND_MANAGER} for "
                              f"Cinema 4D (version {rid.PLUGIN_VERSION})"))
                    self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=500, name="")
                    self.AddStaticText(
                        0, c4d.BFH_SCALEFIT,
                        initw=500,
                        name="Developed by Rokoko Electronics ApS")
                self.GroupEnd()  # About Text
            self.GroupEnd()  # About content group

            self.AddDlgGroup(c4d.DLG_OK)
        self.GroupEnd()  # Dialog main group
        return True

    def Command(self, id, msg):
        '''Called by C4D to handle user's interaction with the dialog'''

        if id == c4d.DLG_OK:
            self.Close()
        return True
