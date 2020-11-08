import c4d

def CreateLayoutAddGroupBar(dlg, title, flags=c4d.BFH_SCALEFIT|c4d.BFV_TOP, initw=0, inith=0):
    bc = c4d.BaseContainer()
    bc.SetInt32(c4d.QUICKTAB_BAR, 1)
    bc.SetString(c4d.QUICKTAB_BARTITLE, title)
    dlg.AddCustomGui(0, c4d.CUSTOMGUI_QUICKTAB, '', flags, initw, inith, bc)

def CreateLayoutAddQuickTab(dlg, id, noMultiselect=False, flags=c4d.BFH_SCALEFIT|c4d.BFV_TOP):
    bc = c4d.BaseContainer()
    bc.SetInt32(c4d.QUICKTAB_BAR, 0)
    bc.SetBool(c4d.QUICKTAB_NOMULTISELECT, noMultiselect)
    bc.SetBool(c4d.QUICKTAB_SHOWSINGLE, True)
    return dlg.AddCustomGui(id, c4d.CUSTOMGUI_QUICKTAB, '', flags, 0, 0, bc)

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
