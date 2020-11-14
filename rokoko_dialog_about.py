# A very simple About dialog.
import os
import c4d
from rokoko_ids import *
from rokoko_dialog_utils import *

# The logo bitmap is loaded once at startup.
# Only to save a small fraction of a second, when the user opens the dialog.
g_bmpLogo = None
def InitRokokoLogo():
    global g_bmpLogo
    g_bmpLogo = None

    # Load logo bitmap
    bmp = c4d.bitmaps.BaseBitmap()
    result, _ = bmp.InitWith(os.path.join(os.path.dirname(__file__), 'res', 'rokoko-studio-live-logo.png'))
    if result != c4d.IMAGERESULT_OK:
        print('ERROR: Failed ({}) to load logo for About dialog'.format(result))
        return

    # Scale the bitmap to the desired logo size
    g_bmpLogo = c4d.bitmaps.BaseBitmap()
    g_bmpLogo.Init(200, 200)
    bmp.ScaleIt(g_bmpLogo, 256, True, False)

# To be called during shutdown
def DlgAboutDestroyGlobals():
    global g_bmpLogo
    g_bmpLogo = None


# Simple About dialog, displaying a logo on the left side and multiple text lines on the right.
class DialogAbout(c4d.gui.GeDialog):

    # Title of the dialog can be set from outside upon instancing the dialog
    def __init__(self, title='About {0}'.format(PLUGIN_NAME_COMMAND_MANAGER)):
        self._title = title
        c4d.gui.GeDialog.__init__(self)


    # Called by C4D to draw the dialog
    def CreateLayout(self):
        self.SetTitle(self._title) # dialog's window title

        if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1): # Dialog main group
            self.GroupBorderSpace(7, 5, 7, 3)
            self.GroupSpace(0, 15)

            if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=2): # About content group
                self.GroupSpace(20, 0)

                if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_CENTER, cols=1): # Logo
                    CreateLayoutAddBitmapButton(self, 0, bmp=g_bmpLogo, button=False, toggle=False)
                self.GroupEnd() # Logo

                if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_CENTER, cols=1): # About Text
                    self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=500, name='{0} for Cinema 4D (version {1})'.format(PLUGIN_NAME_COMMAND_MANAGER, PLUGIN_VERSION))
                    self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=500, name='')
                    self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=500, name='Developed by Rokoko Electronics ApS')
                self.GroupEnd() # About Text
            self.GroupEnd()  # About content group

            self.AddDlgGroup(c4d.DLG_OK)
        self.GroupEnd() # Dialog main group
        return True


    # Called by C4D to handle user's interaction with the dialog
    def Command(self, id, msg):
        if id == c4d.DLG_OK:
            self.Close()
        return True
