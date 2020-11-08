import os
import c4d
from rokoko_ids import *
from rokoko_dialog_utils import *

g_bmpLogo = None
def InitRokokoLogo():
    global g_bmpLogo
    g_bmpLogo = c4d.bitmaps.BaseBitmap()
    g_bmpLogo.Init(200, 200)
    bmp = c4d.bitmaps.BaseBitmap()
    bmp.InitWith(os.path.join(os.path.dirname(__file__), 'res', 'rokoko-studio-live-logo.png'))
    bmp.ScaleIt(g_bmpLogo, 256, True, False)

def DlgAboutDestroyGlobals():
    global g_bmpLogo
    g_bmpLogo = None

class DialogAbout(c4d.gui.GeDialog):

    def __init__(self, title='About {}'.format(PLUGIN_NAME_COMMAND_MANAGER)):
        self._title = title
        c4d.gui.GeDialog.__init__(self)

    def CreateLayout(self):
        self.SetTitle(self._title)
        if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1): # Dialog main group
            self.GroupBorderSpace(7, 5, 7, 3)
            self.GroupSpace(0, 15)
            if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=2): # About content group
                self.GroupSpace(20, 0)
                if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_CENTER, cols=1): # Logo
                    CreateLayoutAddBitmapButton(self, 0, bmp=g_bmpLogo, button=False, toggle=False)
                self.GroupEnd() # Logo
                if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_CENTER, cols=1): # About Text
                    self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=400, name='{0} for Cinema 4D (version {1})'.format(PLUGIN_NAME_COMMAND_MANAGER, PLUGIN_VERSION))
                    self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=400, name='')
                    self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=400, name='Developed by Rokoko Electronics ApS')
                self.GroupEnd() # About Text
            self.GroupEnd()  # About content group
            self.AddDlgGroup(c4d.DLG_OK)
        self.GroupEnd() # Dialog main group
        return True

    def Command(self, id, msg):
        if id == c4d.DLG_OK:
            self.Close()
        return True
