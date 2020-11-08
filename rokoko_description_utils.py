import c4d

def GetDDescriptionCreateCombo(node, description, singleId, id, name, parentId, bcContent, anim=True, remove=False, valDefault=50):
    descId = c4d.DescID(c4d.DescLevel(id, c4d.DTYPE_LONG, node.GetType()))
    if singleId is not None and not descId.IsPartOf(singleId)[0]:
        return True
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_LONG)
    bc.SetString(c4d.DESC_NAME, name)
    bc.SetString(c4d.DESC_SHORT_NAME, name)
    bc.SetInt32(c4d.DESC_CUSTOMGUI, c4d.CUSTOMGUI_CYCLE)
    bc.SetContainer(c4d.DESC_CYCLE, bcContent)
    bc.SetInt32(c4d.DESC_DEFAULT, valDefault)
    bc.SetInt32(c4d.DESC_ANIMATE, anim)
    bc.SetBool(c4d.DESC_REMOVEABLE, remove)
    return description.SetParameter(descId, bc, parentId)

def GetDDescriptionCreateLong(node, description, singleId, id, name, parentId, anim=True, remove=False, unit=c4d.DESC_UNIT_INT, valDefault=50, valMin=0, valMax=100, step=1, slider=True, sliderMin=0, sliderMax=100):
    descId = c4d.DescID(c4d.DescLevel(id, c4d.DTYPE_LONG, node.GetType()))
    if singleId is not None and not descId.IsPartOf(singleId)[0]:
        return True
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_LONG)
    bc.SetString(c4d.DESC_NAME, name)
    bc.SetString(c4d.DESC_SHORT_NAME, name)
    if slider:
        bc.SetInt32(c4d.DESC_CUSTOMGUI, c4d.CUSTOMGUI_LONGSLIDER)
        bc.SetInt32(c4d.DESC_MINSLIDER, sliderMin)
        bc.SetInt32(c4d.DESC_MAXSLIDER, sliderMax)
    else:
        bc.SetInt32(c4d.DESC_CUSTOMGUI, c4d.CUSTOMGUI_LONG)
    bc.SetInt32(c4d.DESC_DEFAULT, valDefault)
    bc.SetInt32(c4d.DESC_MIN, valMin)
    bc.SetInt32(c4d.DESC_MAX, valMax)
    bc.SetInt32(c4d.DESC_STEP, step)
    bc.SetInt32(c4d.DESC_UNIT, unit)
    bc.SetInt32(c4d.DESC_ANIMATE, anim)
    bc.SetBool(c4d.DESC_REMOVEABLE, remove)
    return description.SetParameter(descId, bc, parentId)

def GetDDescriptionCreateReal(node, description, singleId, id, name, parentId, anim=True, remove=False, unit=c4d.DESC_UNIT_FLOAT, valDefault=0.5, valMin=0.0, valMax=1.0, step=0.01, slider=True, sliderMin=0.0, sliderMax=1.0):
    descId = c4d.DescID(c4d.DescLevel(id, c4d.DTYPE_REAL, node.GetType()))
    if singleId is not None and not descId.IsPartOf(singleId)[0]:
        return True
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_REAL)
    bc.SetString(c4d.DESC_NAME, name)
    bc.SetString(c4d.DESC_SHORT_NAME, name)
    if slider:
        bc.SetInt32(c4d.DESC_CUSTOMGUI, c4d.CUSTOMGUI_REALSLIDER)
        bc.SetFloat(c4d.DESC_MINSLIDER, sliderMin)
        bc.SetFloat(c4d.DESC_MAXSLIDER, sliderMax)
    else:
        bc.SetInt32(c4d.DESC_CUSTOMGUI, c4d.CUSTOMGUI_REAL)
    bc.SetFloat(c4d.DESC_DEFAULT, valDefault)
    bc.SetFloat(c4d.DESC_MIN, valMin)
    bc.SetFloat(c4d.DESC_MAX, valMax)
    bc.SetFloat(c4d.DESC_STEP, step)
    bc.SetInt32(c4d.DESC_UNIT, unit)
    bc.SetInt32(c4d.DESC_ANIMATE, anim)
    bc.SetBool(c4d.DESC_REMOVEABLE, remove)
    return description.SetParameter(descId, bc, parentId)

def GetDDescriptionCreateVector(node, description, singleId, id, name, parentId, anim=True, edit=True, hide=False, remove=False, unit=c4d.DESC_UNIT_FLOAT, color=False):
    descId = c4d.DescID(c4d.DescLevel(id, c4d.DTYPE_VECTOR, node.GetType()))
    if singleId is not None and not descId.IsPartOf(singleId)[0]:
        return True
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_VECTOR)
    bc.SetString(c4d.DESC_NAME, name)
    bc.SetString(c4d.DESC_SHORT_NAME, name)
    if color:
        bc.SetInt32(c4d.DESC_CUSTOMGUI, c4d.CUSTOMGUI_COLOR)
    else:
        bc.SetInt32(c4d.DESC_CUSTOMGUI, c4d.CUSTOMGUI_VECTOR)
    bc.SetVector(c4d.DESC_DEFAULT, c4d.Vector(0.0))
    bc.SetInt32(c4d.DESC_ANIMATE, anim)
    bc.SetBool(c4d.DESC_REMOVEABLE, remove)
    bc.SetBool(c4d.DESC_EDITABLE, edit)
    bc.SetBool(c4d.DESC_HIDE, hide)
    bc.SetBool(c4d.DESC_DISABLELAYOUTSWITCH, False)
    bc.SetBool(c4d.DESC_NOGUISWITCH, True)
    bc.SetBool(c4d.DESC_COLORALWAYSLINEAR , True)
    bc.SetBool(c4d.DESC_ALIGNLEFT, True)
    return description.SetParameter(descId, bc, parentId)

def GetDDescriptionCreateBool(node, description, singleId, id, name, parentId, anim=True, remove=False, valDefault=True):
    descId = c4d.DescID(c4d.DescLevel(id, c4d.DTYPE_BOOL, node.GetType()))
    if singleId is not None and not descId.IsPartOf(singleId)[0]:
        return True
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_BOOL)
    bc.SetString(c4d.DESC_NAME, name)
    bc.SetString(c4d.DESC_SHORT_NAME, name)
    bc.SetInt32(c4d.DESC_DEFAULT, valDefault)
    bc.SetInt32(c4d.DESC_ANIMATE, anim)
    bc.SetBool(c4d.DESC_REMOVEABLE, remove)
    return description.SetParameter(descId, bc, parentId)

def GetDDescriptionCreateGroup(node, description, singleId, id, name, parentId, numColumns=1, defaultOpen=False):
    descId = c4d.DescID(c4d.DescLevel(id, c4d.DTYPE_GROUP, node.GetType()))
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_GROUP)
    bc.SetString(c4d.DESC_NAME, name)
    bc.SetInt32(c4d.DESC_COLUMNS, numColumns)
    bc.SetBool(c4d.DESC_DEFAULT, defaultOpen)
    return description.SetParameter(descId, bc, c4d.DescID(c4d.DescLevel(parentId)))

def GetDDescriptionCreateButton(node, description, singleId, id, name, parentId, scaleH=False):
    descId = c4d.DescID(c4d.DescLevel(id, c4d.DTYPE_BUTTON, node.GetType()))
    if singleId is not None and not descId.IsPartOf(singleId)[0]:
        return True
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_BUTTON)
    bc.SetInt32(c4d.DESC_CUSTOMGUI, c4d.CUSTOMGUI_BUTTON)
    bc.SetString(c4d.DESC_NAME, name)
    bc.SetString(c4d.DESC_SHORT_NAME, name)
    bc.SetBool(c4d.DESC_REMOVEABLE, False)
    bc.SetBool(c4d.DESC_SCALEH, scaleH)
    return description.SetParameter(descId, bc, parentId)

def GetDDescriptionCreateString(node, description, singleId, id, name, parentId, anim=False, remove=False, static=True, valDefault='', scaleH=False):
    descId = c4d.DescID(c4d.DescLevel(id, c4d.DTYPE_STRING, node.GetType()))
    if singleId is not None and not descId.IsPartOf(singleId)[0]:
        return True
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_STRING)
    bc.SetString(c4d.DESC_NAME, name)
    bc.SetString(c4d.DESC_SHORT_NAME, name)
    if static:
        bc.SetInt32(c4d.DESC_CUSTOMGUI, c4d.CUSTOMGUI_STATICTEXT)
    else:
        bc.SetInt32(c4d.DESC_CUSTOMGUI, c4d.CUSTOMGUI_STRING)
    bc.SetString(c4d.DESC_DEFAULT, valDefault)
    bc.SetInt32(c4d.DESC_ANIMATE, anim)
    bc.SetBool(c4d.DESC_REMOVEABLE, remove)
    bc.SetBool(c4d.DESC_SCALEH, scaleH)
    return description.SetParameter(descId, bc, parentId)

def GetDDescriptionCreateLink(node, description, singleId, id, name, parentId, anim=False, remove=False, valDefault=None):
    descId = c4d.DescID(c4d.DescLevel(id, c4d.DTYPE_BASELISTLINK, node.GetType()))
    if singleId is not None and not descId.IsPartOf(singleId)[0]:
        return True
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_BASELISTLINK)
    bc.SetString(c4d.DESC_NAME, name)
    bc.SetString(c4d.DESC_SHORT_NAME, name)
    bc.SetInt32(c4d.DESC_CUSTOMGUI, c4d.CUSTOMGUI_LINKBOX)
    bc.SetString(c4d.DESC_DEFAULT, valDefault)
    bc.SetInt32(c4d.DESC_ANIMATE, anim)
    bc.SetBool(c4d.DESC_REMOVEABLE, remove)
    return description.SetParameter(descId, bc, parentId)
