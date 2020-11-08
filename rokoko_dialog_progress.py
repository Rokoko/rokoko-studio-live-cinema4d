import c4d
from rokoko_ids import *

class DialogBakeProgress(c4d.gui.GeDialog):
    _title = ''

    def __init__(self, title='{} Baking...'.format(PLUGIN_NAME_COMMAND_MANAGER)):
        self._title = title
        c4d.gui.GeDialog.__init__(self)

    def CreateLayout(self):
        self.SetTitle(self._title)
        if self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, initw=300, inith=200, cols=1): # Dialog main group
            self.GroupBorderSpace(7, 5, 7, 3)
            self.GroupSpace(0, 15)
            self.AddStaticText(0, c4d.BFH_SCALEFIT, initw=0, name='Baking...')
        self.GroupEnd() # Dialog main group
        return True

    def Command(self, id, msg):
        return True
