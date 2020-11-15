# Utility functions for use with C4D GeDialog.
import c4d

# Currently only a few additional Create (or in GeDialog context rather Add-) functions for the most used CustomGUIs.
#
# All work the same:
# 1) Create BaseContainer with the desired configuration for the CustomGUI.
# 2) Add the CustomGUI and return its handle
#    (e.g. a BitmapButton's image and toggle state can only changed calling functions using this handle).

# Adds a "Group Bar" (horizontal bar with a text label, used to visually separate groups).
def CreateLayoutAddGroupBar(dlg, title, flags=c4d.BFH_SCALEFIT|c4d.BFV_TOP, initw=0, inith=0):
    bc = c4d.BaseContainer()
    bc.SetInt32(c4d.QUICKTAB_BAR, 1)
    bc.SetString(c4d.QUICKTAB_BARTITLE, title)
    dlg.AddCustomGui(0, c4d.CUSTOMGUI_QUICKTAB, '', flags, initw, inith, bc)


# Adds a "QuickTab Bar" (those tabs to switch for example between different pages of a dialog).
def CreateLayoutAddQuickTab(dlg, id, noMultiselect=False, flags=c4d.BFH_SCALEFIT|c4d.BFV_TOP):
    bc = c4d.BaseContainer()
    bc.SetInt32(c4d.QUICKTAB_BAR, 0)
    bc.SetBool(c4d.QUICKTAB_NOMULTISELECT, noMultiselect)
    bc.SetBool(c4d.QUICKTAB_SHOWSINGLE, True)
    return dlg.AddCustomGui(id, c4d.CUSTOMGUI_QUICKTAB, '', flags, 0, 0, bc)


# Add a "Bitmap Button".
# In C4D there is no widget to display an image (or icon, bitmap, ...), instead such a
# BitmapButton CustomGUI is used.
# The image to be displayed on the button can be passed in two ways. Either as bitmap directly or
# or via passing an ID of a registered icon.
# Parameters to change button behavior:
# button: If True, results in a clickable button. Note: Since some versions of C4D, this parameter seems to have very little effect...
# toggle: If True, the button toggles between two states/and images
#         (image of second state can only be set via idIcon2, use SetImage() if second state needs to be set by bitmap)
def CreateLayoutAddBitmapButton(dlg, idButton, bmp=None, idIcon1=-1, idIcon2=-1, tooltip='', button=True, toggle=True, flags=c4d.BFH_CENTER|c4d.BFV_CENTER):
    bc = c4d.BaseContainer()
    bc.SetInt32(c4d.BITMAPBUTTON_IGNORE_BITMAP_WIDTH, False)
    bc.SetInt32(c4d.BITMAPBUTTON_IGNORE_BITMAP_HEIGHT, False)
    bc.SetBool(c4d.BITMAPBUTTON_BORDER, False)
    bc.SetBool(c4d.BITMAPBUTTON_BUTTON, button)
    bc.SetBool(c4d.BITMAPBUTTON_TOGGLE, toggle)
    bc.SetBool(c4d.BITMAPBUTTON_DISABLE_FADING, not button) # R22 feature
    bc.SetString(c4d.BITMAPBUTTON_TOOLTIP, tooltip)
    if idIcon1 != -1:
        bc.SetInt32(c4d.BITMAPBUTTON_ICONID1, idIcon1)
    if idIcon2 != -1:
        bc.SetInt32(c4d.BITMAPBUTTON_ICONID2, idIcon2)
    button = dlg.AddCustomGui(idButton, c4d.CUSTOMGUI_BITMAPBUTTON, '', flags, 0, 0, bc)
    if bmp is not None:
        bmpButton = c4d.bitmaps.BaseBitmap()
        size = bmp.GetSize()
        if size[0] == 32:
            bmpButton.Init(18, 18)
        else:
            bmpButton.Init(size[0] // 2, size[1] // 2)
        bmp.ScaleIt(bmpButton, 256, True, False)
        button.SetImage(bmpButton)
    return button
