# -*- coding: utf-8 -*-
"""============================================================================
Corr Joint Rotate 셋팅

씬에서 "_Corr" 접미사를 가진 보정(corrective) 조인트들을 찾고,
접미사를 뗀 이름과 같은 이름의 조인트(구동 조인트)를 찾아서
구동 조인트의 rotate 값의 절반(half)을 Corr 조인트의 rotate로 연결한다.

    예) index2      (구동 조인트)
        index2Corr  (보정 조인트)

네트워크 구조:
    driver.rotate -> pairBlend.inRotate1   (inRotate2 = 0,0,0, weight = 0.5)
    pairBlend.outRotate -> {corr joint}.rotate

:Example:
    from python3.rigging import corr_half_rotate_setup
    reload(corr_half_rotate_setup)
    corr_half_rotate_setup.setup_corr_half_rotate()  # 씬의 모든 "*_Corr" 조인트 대상
============================================================================"""
import maya.cmds as cmds

CORR_SUFFIX = 'Corr'
UTILITY_TYPES = ('unitConversion', 'pairBlend', 'reverse', 'multiplyDivide')


def _clean_existing_rotate_network(jnt):
    """jnt.rotate에 걸려있는 pairBlend/reverse/multiplyDivide/unitConversion
    체인을 구동 조인트가 나올 때까지 거슬러 올라가며 삭제한다.
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


def _find_driver_joint(corr_jnt):
    """Corr 조인트 이름에서 접미사를 뗀 이름과 같은 구동 조인트를 찾는다."""
    short_name = corr_jnt.split('|')[-1]
    is_corr = short_name.endswith(CORR_SUFFIX)
    if not is_corr:
        return None
    base_name = short_name[:-len(CORR_SUFFIX)]
    matches = cmds.ls(base_name, type='joint') or []
    has_match = len(matches) > 0
    if not has_match:
        return None
    return matches[0]


def setup_corr_half_rotate(corr_joints=None):
    """Corr 조인트(들)에 0.5 * driver.rotate 셋팅을 구성한다.
    corr_joints를 넘기지 않으면 씬의 모든 "*_Corr" 조인트를 대상으로 한다.
    """
    targets = corr_joints
    if targets is None:
        targets = cmds.ls('*' + CORR_SUFFIX, type='joint') or []
    has_targets = len(targets) > 0
    if not has_targets:
        cmds.warning('no Corr joints found')
        return []

    results = []
    for corr in targets:
        driver = _find_driver_joint(corr)
        if driver is None:
            cmds.warning(corr + ' has no matching driver joint, skip')
            continue

        removed = _clean_existing_rotate_network(corr)
        removed_count = len(removed)
        if removed_count > 0:
            print(corr + ' cleaned old nodes: ' + str(removed))

        pb = cmds.createNode('pairBlend', name=corr + '_half_pairBlend')
        cmds.connectAttr(driver + '.rotate', pb + '.inRotate1', force=True)
        cmds.setAttr(pb + '.inRotate2', 0, 0, 0, type='double3')
        cmds.setAttr(pb + '.weight', 0.5)
        cmds.setAttr(pb + '.rotInterpolation', 1)  # quaternion interpolation

        cmds.connectAttr(pb + '.outRotate', corr + '.rotate', force=True)

        results.append((corr, driver, pb))
        print('OK ' + corr + ' <- 0.5 * ' + driver + '.rotate  pairBlend=' + pb)

    return results
