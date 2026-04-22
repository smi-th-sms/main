import maya.cmds as cmds
from collections import OrderedDict


def _get_shape(node):
    if cmds.objectType(node) == 'transform':
        shapes = cmds.listRelatives(node, shapes=True)
        return shapes[0] if shapes else None
    return node


class SurfParamSpace():
    def __init__(self, object_, *args, **kwargs):
        self.object_ = object_
        surf_ = self.object_[0]
        shape_ = _get_shape(surf_)
        uNum_ = cmds.getAttr(shape_ + '.spansU') + 1
        vNum_ = cmds.getAttr(shape_ + '.spansV') + 1
        spaces = self.surf_param_space(surf_, uNum_, vNum_)
        paramGRPs = self.param_structure(spaces.keys())
        for i, grp in enumerate(paramGRPs['V_param']):
            for spc in spaces[i]:
                cmds.parent(spc, grp)

    def surf_param_space(self, object_, uNum, vNum):
        spaceDict = OrderedDict()
        _shape = _get_shape(object_)
        uMax = cmds.getAttr(_shape + '.spansU')
        vMax = cmds.getAttr(_shape + '.spansV')
        _name = object_

        for v in range(vNum):
            uList = []
            spaceDict[v] = uList
            for u in range(uNum):
                name = '{}_U{}_V{}'.format(_name, u, v)

                _POSI = cmds.createNode('pointOnSurfaceInfo', n='{}PSI'.format(name))
                cmds.connectAttr(_shape + '.worldSpace[0]', _POSI + '.inputSurface')

                _rotH = cmds.createNode('rotateHelper', n='{}RH'.format(name))
                cmds.connectAttr(_POSI + '.normalizedNormal', _rotH + '.up')
                cmds.connectAttr(_POSI + '.normalizedTangentV', _rotH + '.forward')

                _space = cmds.createNode('transform', n='{}Grp'.format(name))
                cmds.addAttr(_space, ln='paramU', sn='pu', at='float', dv=u, min=0, max=uMax, k=True)
                cmds.addAttr(_space, ln='paramV', sn='pv', at='float', dv=v, min=0, max=vMax, k=True)

                cmds.connectAttr(_space + '.pu', _POSI + '.parameterU')
                cmds.connectAttr(_space + '.pv', _POSI + '.parameterV')
                cmds.connectAttr(_POSI + '.position', _space + '.translate')

                _DCM = cmds.createNode('decomposeMatrix', n='{}DM'.format(name))
                cmds.connectAttr(_rotH + '.rotateMatrix', _DCM + '.inputMatrix')
                cmds.connectAttr(_DCM + '.outputRotate', _space + '.rotate')

                uList.append(_space)
        return spaceDict

    def param_structure(self, list_):
        GRPDict = OrderedDict()
        GRPDict['param'] = cmds.createNode('transform', n='paramGrp')
        v_params = []
        for i in list_:
            grp = cmds.createNode('transform', n='V{}_spaceGrp'.format(i))
            cmds.parent(grp, GRPDict['param'])
            v_params.append(grp)
        GRPDict['V_param'] = v_params
        return GRPDict


sel = cmds.ls(sl=True)
SurfParamSpace(sel)
