# -*- coding: utf-8 -*-
"""Create a negative translate offset group above selected transforms.

Usage:
    from python2.tools import negative_translate_offset
    import importlib
    importlib.reload(negative_translate_offset)

    negative_translate_offset.setup_from_selection()

Result:
    selected.translate -> multiplyDivide.input1
    multiplyDivide.input2 = (-1, -1, -1)
    multiplyDivide.output -> offset_group.translate

The offset group keeps the current pose in offsetParentMatrix, so moving the
selected object's translate channels is cancelled by the parent group.
"""

import maya.cmds as cmds


def _short_name(node):
    return node.split('|')[-1].split(':')[-1]


def _as_matrix(value):
    if value and isinstance(value[0], (list, tuple)):
        return list(value[0])
    return list(value)


def _set_identity_trs(node):
    cmds.setAttr(node + '.translate', 0, 0, 0, type='double3')
    cmds.setAttr(node + '.rotate', 0, 0, 0, type='double3')
    cmds.setAttr(node + '.scale', 1, 1, 1, type='double3')


def _safe_connect(src, dst, force=True):
    if cmds.isConnected(src, dst):
        return
    cmds.connectAttr(src, dst, force=force)


def setup_negative_translate_offset(node, suffix='_negOffset_GRP',
                                    md_suffix='_negTranslate_MD'):
    """Create a negative translate offset group above one transform.

    Args:
        node (str): Transform node to wrap.
        suffix (str): Offset group name suffix.
        md_suffix (str): multiplyDivide node name suffix.

    Returns:
        dict: object, offset_group, multiply_divide.
    """
    if not cmds.objExists(node):
        raise RuntimeError('Object does not exist: {0}'.format(node))
    if cmds.nodeType(node) != 'transform':
        raise RuntimeError('Object must be a transform: {0}'.format(node))

    node = cmds.ls(node, long=True)[0]
    short = _short_name(node)
    parent = cmds.listRelatives(node, parent=True, fullPath=True)
    parent = parent[0] if parent else None

    group = cmds.createNode('transform', name=short + suffix)
    if parent:
        group = cmds.parent(group, parent)[0]

    # Match current world pose, move that local matrix into offsetParentMatrix,
    # then leave translate/rotate/scale free for the negative connection.
    world_matrix = cmds.xform(node, query=True, worldSpace=True, matrix=True)
    cmds.xform(group, worldSpace=True, matrix=world_matrix)
    local_matrix = _as_matrix(cmds.getAttr(group + '.matrix'))
    cmds.setAttr(group + '.offsetParentMatrix', local_matrix, type='matrix')
    _set_identity_trs(group)

    node = cmds.parent(node, group)[0]
    node = cmds.ls(node, long=True)[0]
    group = cmds.ls(group, long=True)[0]

    md = cmds.createNode('multiplyDivide', name=short + md_suffix)
    cmds.setAttr(md + '.input2X', -1)
    cmds.setAttr(md + '.input2Y', -1)
    cmds.setAttr(md + '.input2Z', -1)

    _safe_connect(node + '.translate', md + '.input1')
    _safe_connect(md + '.output', group + '.translate')

    return {
        'object': node,
        'offset_group': group,
        'multiply_divide': md,
    }


def setup_from_selection(nodes=None):
    """Create negative translate offset groups for selected transforms."""
    if nodes is None:
        nodes = cmds.ls(selection=True, type='transform', long=True) or []
    if not nodes:
        raise RuntimeError('Select one or more transform objects.')

    results = [setup_negative_translate_offset(node) for node in nodes]
    print('negative_translate_offset: created {0} setup(s).'.format(len(results)))
    return results


if __name__ == '__main__':
    setup_from_selection()
