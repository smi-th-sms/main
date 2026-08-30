# -*- coding: utf-8 -*-
"""============================================================================
Half/Twist Joint Rotate 셋팅

lowerarm_half_l/r, upperarm_twist_l/r, calf_half_l/r, thigh_twist_l/r 같은
half/twist 보정 조인트에, 직속 부모 조인트 회전의 "음수 절반" 값만
받아오는 네트워크를 구성한다.

부모 조인트가 rotate delta를 가지면, half/twist 조인트는 하이어라키상
이미 그 rotate를 그대로 상속받고 있으므로(부모의 자식이기 때문),
월드 상에서 정확히 절반만 회전한 것처럼 보이게 하려면 로컬 rotate에
"-0.5 * parent.rotate"를 더해줘야 한다. 즉:
    최종 월드 회전 = (parent_orig + delta) + (-0.5 * delta) = parent_orig + 0.5 * delta

네트워크 구조:
    parent.rotate -> pairBlend.inRotate2   (inRotate1 = 0,0,0, weight = 0.5)
    pairBlend.outRotate -> multiplyDivide.input1   (input2 = -1,-1,-1, operation = multiply)
    multiplyDivide.output -> {half/twist joint}.rotate

Maya 기본 reverse 노드(output = 1 - input)는 0~1 weight 반전용이라
회전(도 단위) 값의 부호 반전에는 맞지 않아서 대신 multiplyDivide(-1)를 쓴다.

:Example:
    from python3.rigging import half_twist_rotate_setup
    reload(half_twist_rotate_setup)
    half_twist_rotate_setup.setup_half_rotate()  # 현재 선택된 조인트 기준
============================================================================"""
import maya.cmds as cmds

UTILITY_TYPES = ('unitConversion', 'pairBlend', 'reverse', 'multiplyDivide')

DEFAULT_TARGETS = [
    "lowerarm_half_l", "upperarm_twist_l", "lowerarm_half_r", "upperarm_twist_r",
    "calf_half_r", "thigh_twist_r", "calf_half_l", "thigh_twist_l",
]


def _clean_existing_rotate_network(jnt):
    """jnt.rotate에 걸려있는 pairBlend/reverse/multiplyDivide/unitConversion
    체인을 부모 조인트가 나올 때까지 거슬러 올라가며 삭제한다.
    """
    to_delete = set()
    frontier = cmds.listConnections(jnt + '.rotate', s=True, d=False, plugs=True) or []
    seen = set(frontier)
    while frontier:
        plug = frontier.pop()
        node = plug.split('.')[0]
        already = node in to_delete
        exists = cmds.objExists(node)
        if already or not exists:
            continue
        is_utility = cmds.nodeType(node) in UTILITY_TYPES
        if is_utility:
            to_delete.add(node)
            attrs = cmds.listAttr(node, connectable=True) or []
            for a in attrs:
                p = node + '.' + a
                srcs = cmds.listConnections(p, s=True, d=False, plugs=True) or []
                for src in srcs:
                    is_new = src in seen
                    if is_new:
                        continue
                    seen.add(src)
                    frontier.append(src)
    delete_list = list(to_delete)
    has_items = len(delete_list) > 0
    if has_items:
        cmds.delete(delete_list)
    return delete_list


def setup_half_rotate(joints=None):
    """half/twist 조인트(들)에 -0.5 * parent.rotate 셋팅을 구성한다.
    joints를 넘기지 않으면 현재 씬에서 선택된 조인트를 사용한다.
    """
    sel = joints
    if sel is None:
        sel = cmds.ls(selection=True, type='joint')
    has_joints = len(sel) > 0
    if not has_joints:
        cmds.warning('no joints selected')
        return []

    results = []
    for jnt in sel:
        parents = cmds.listRelatives(jnt, parent=True, type='joint')
        has_parent = parents is not None and len(parents) > 0
        if not has_parent:
            cmds.warning(jnt + ' has no parent joint, skip')
            continue
        parent = parents[0]

        removed = _clean_existing_rotate_network(jnt)
        removed_count = len(removed)
        if removed_count > 0:
            print(jnt + ' cleaned old nodes: ' + str(removed))

        pb = cmds.createNode('pairBlend', name=jnt + '_half_pairBlend')
        cmds.setAttr(pb + '.inRotate1', 0, 0, 0, type='double3')
        cmds.connectAttr(parent + '.rotate', pb + '.inRotate2', force=True)
        cmds.setAttr(pb + '.weight', 0.5)
        cmds.setAttr(pb + '.rotInterpolation', 1)  # quaternion interpolation

        md = cmds.createNode('multiplyDivide', name=jnt + '_half_negate')
        cmds.setAttr(md + '.operation', 1)  # multiply
        cmds.connectAttr(pb + '.outRotate', md + '.input1', force=True)
        cmds.setAttr(md + '.input2', -1, -1, -1, type='double3')

        cmds.connectAttr(md + '.output', jnt + '.rotate', force=True)

        results.append((jnt, parent, pb, md))
        print('OK ' + jnt + ' <- -0.5 * ' + parent + '.rotate  pairBlend=' + pb + ' multiplyDivide=' + md)

    return results


def setup_default_targets():
    """8개 기본 half/twist 조인트(DEFAULT_TARGETS)에 대해 한 번에 셋팅한다."""
    return setup_half_rotate(DEFAULT_TARGETS)
setup_default_targets()