import maya.cmds as cmds

def _get_shape(node):
    if cmds.objectType(node) != 'transform':
        return node
    shapes = cmds.listRelatives(node, shapes=True)
    return shapes[0] if shapes else None

def surfaceAtPos(object_):
    surfShape_ = _get_shape(object_[-1])
    if not surfShape_:
        cmds.warning('Surface shape not found: {0}'.format(object_[-1]))
        return

    for i in object_[:-1]:
        name_ = i
        cs_ = cmds.createNode('closestPointOnSurface', n='{0}CS'.format(name_))
        ps_ = cmds.createNode('pointOnSurfaceInfo', n='{0}PS'.format(name_))
        rh_ = cmds.createNode('rotateHelper', n='{0}RH'.format(name_))
        SurfPos_ = cmds.createNode('transform', n='{0}SurfPos'.format(name_))

        dm_ = cmds.createNode('decomposeMatrix', n='{0}DM'.format(name_))
        cmds.connectAttr(i + '.worldMatrix[0]', dm_ + '.inputMatrix')
        cmds.connectAttr(dm_ + '.outputTranslate', cs_ + '.inPosition')
        cmds.connectAttr(surfShape_ + '.worldSpace[0]', cs_ + '.inputSurface')
        cmds.connectAttr(surfShape_ + '.worldSpace[0]', ps_ + '.inputSurface')
        cmds.connectAttr(cs_ + '.parameterU', ps_ + '.parameterU')
        cmds.connectAttr(cs_ + '.parameterV', ps_ + '.parameterV')
        cmds.connectAttr(ps_ + '.normalizedNormal', rh_ + '.forward')
        cmds.connectAttr(ps_ + '.normalizedTangentU', rh_ + '.up')
        cmds.connectAttr(ps_ + '.position', SurfPos_ + '.translate')
        cmds.connectAttr(rh_ + '.rotate', SurfPos_ + '.rotate')

# 포지션 값을 받아올 오브젝트들 선택[:-1], 서페이스 선택[-1]
sel = cmds.ls(sl=True)
surfaceAtPos(sel)
