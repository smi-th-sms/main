# -*- coding: utf-8 -*-
import maya.cmds as cmds


def getChildren_(object_, type_=None):
    """Get the children from top object

    Arguments:
        object_ (str): transform node name
        type_   (str): node type filter

    Returns:
        list: children list (top → bottom order)
    """
    if not type_:
        type_ = 'transform'
    child_ = cmds.listRelatives(object_, allDescendents=True, type=type_) or []
    child_ = child_ + [object_]
    child_.reverse()
    return child_


def hierarchy_(object_):
    for i, obj in enumerate(object_):
        if i > 0:
            cmds.parent(obj, object_[i - 1])


def list_chuck(arr, n):
    return [arr[i: i + n] for i in range(0, len(arr), n)]


def IKFKBlend(object_, ik_pos=1):
    total = len(object_)
    if total % 3 != 0:
        cmds.error('IKFKBlend: 선택 수({})가 3의 배수여야 합니다. '
                   'FK / IK / Drv 체인을 같은 수로 선택하세요.'.format(total))
        return

    chain_len    = total // 3
    result_array = list_chuck(object_, chain_len)
    FKChain, IKChain, DrvChain = result_array

    if ik_pos:
        cmds.select(cl=1)
        IKPos_ = [cmds.joint(name='{0}Pos'.format(ik))
                  for ik in IKChain]
        [cmds.matchTransform(IKPos_[i], IKC) for i, IKC in enumerate(IKChain)]
        hierarchy_(IKPos_)
        cmds.makeIdentity(IKPos_[0], apply=True, rotate=True)

    for i, drv in enumerate(DrvChain):
        name_ = drv
        print(name_, FKChain[i], IKChain[i])
        PB_ = cmds.createNode('pairBlend',
                              name='{0}PB'.format(name_))
        '''
        BC_ = cmds.shadingNode('blendColors', asUtility=True,
                               name='{0}BC'.format(name_))'''

        ik_src = IKPos_[i] if ik_pos else IKChain[i]

        cmds.connectAttr(FKChain[i] + '.r',            PB_    + '.ir2')
        cmds.connectAttr(FKChain[i] + '.t',            PB_    + '.it2')
        # cmds.connectAttr(FKChain[i] + '.s',            BC_    + '.color1')
        if ik_pos:
            cmds.parentConstraint(IKChain[i],IKPos_[i],mo=1)
        cmds.connectAttr(ik_src     + '.r',            PB_    + '.ir1')
        cmds.connectAttr(ik_src     + '.t',            PB_    + '.it1')
        # cmds.connectAttr(ik_src     + '.s',            BC_    + '.color2')
        # cmds.connectAttr(PB_        + '.outTranslate', drv    + '.t')
        cmds.connectAttr(PB_        + '.outRotate',    drv    + '.r')
        cmds.setAttr( f"{PB_}.rotInterpolation", 1)
        # cmds.connectAttr(BC_        + '.output',       drv    + '.s')


# FK 조인트 리스트, IK 조인트 리스트, Drv 조인트 리스트 선택 후 실행
sel = cmds.ls(sl=True, r=True, fl=True)
IKFKBlend(sel, ik_pos=1)
