# -*- coding: utf-8 -*-
"""Build pointOnCurveInfo + transform nodes from a curve maxValue.

Usage:
    from python2.tools import curve_poci_builder
    import importlib
    importlib.reload(curve_poci_builder)

    # Uses curve1Shape and creates one pair for parameter 0..curve.maxValue.
    curve_poci_builder.build_from_curve_max('curve1Shape')

    # Or select a curve transform/shape and run:
    curve_poci_builder.build_from_selection()
"""

import math
import maya.cmds as cmds


def _short_name(node):
    return node.split('|')[-1].split(':')[-1]


def _curve_shape(node):
    if not cmds.objExists(node):
        raise RuntimeError('Curve does not exist: {0}'.format(node))

    if cmds.nodeType(node) == 'nurbsCurve':
        return node

    shapes = cmds.listRelatives(node, shapes=True, ni=True, fullPath=True) or []
    for shape in shapes:
        if cmds.nodeType(shape) == 'nurbsCurve':
            return shape

    raise RuntimeError('{0} is not a nurbsCurve transform or shape.'.format(node))


def _max_value(curve_shape):
    if not cmds.attributeQuery('maxValue', node=curve_shape, exists=True):
        raise RuntimeError('{0} has no maxValue attribute.'.format(curve_shape))
    return cmds.getAttr(curve_shape + '.maxValue')


def _param_values(curve_shape, include_zero=True):
    max_value = _max_value(curve_shape)
    max_int = int(math.floor(max_value))
    if max_int < 1:
        raise RuntimeError('{0}.maxValue must be >= 1. Current: {1}'.format(
            curve_shape, max_value))

    start = 0 if include_zero else 1
    return list(range(start, max_int + 1))


def _connect_position(poci, transform):
    if not cmds.isConnected(poci + '.position', transform + '.translate'):
        cmds.connectAttr(poci + '.position', transform + '.translate', force=True)


def build_from_curve_max(curve='curve1Shape', prefix=None, include_zero=True,
                         group=True, replace=False):
    """Create pointOnCurveInfo + transform pairs from curve.maxValue.

    Args:
        curve (str): Curve transform or curve shape. Example: 'curve1Shape'.
        prefix (str): Naming prefix. Defaults to curve transform/shape name.
        include_zero (bool): If True, creates parameter 0..maxValue.
            Default True creates parameter 0..maxValue.
        group (bool): If True, parents created transforms under a group.
        replace (bool): If True, deletes the existing output group first.

    Returns:
        dict: curve_shape, max_value, group, items.
            items contains transform, pointOnCurveInfo, parameter.
    """
    curve_shape = _curve_shape(curve)
    curve_base = _short_name(curve_shape).replace('Shape', '')
    prefix = prefix or curve_base

    group_node = None
    if group:
        group_name = prefix + '_POCI_GRP'
        if cmds.objExists(group_name) and replace:
            cmds.delete(group_name)
        if cmds.objExists(group_name):
            group_node = group_name
        else:
            group_node = cmds.createNode('transform', name=group_name)

    items = []
    for param in _param_values(curve_shape, include_zero=include_zero):
        suffix = str(param).zfill(2)
        poci = cmds.createNode('pointOnCurveInfo',
                               name='{0}_param{1}_POCI'.format(prefix, suffix))
        transform = cmds.createNode('transform',
                                    name='{0}_param{1}_TRS'.format(prefix, suffix),
                                    parent=group_node)

        cmds.setAttr(poci + '.turnOnPercentage', 0)
        cmds.setAttr(poci + '.parameter', param)
        cmds.connectAttr(curve_shape + '.worldSpace[0]', poci + '.inputCurve',
                         force=True)
        _connect_position(poci, transform)

        items.append({
            'transform': transform,
            'pointOnCurveInfo': poci,
            'parameter': param,
        })

    result = {
        'curve_shape': curve_shape,
        'max_value': _max_value(curve_shape),
        'group': group_node,
        'items': items,
    }

    print('curve_poci_builder: created {0} POCI/transform pairs from {1}'.format(
        len(items), curve_shape))
    return result


def build_from_selection(prefix=None, include_zero=True, group=True, replace=False):
    """Build from the first selected curve transform/shape."""
    selection = cmds.ls(selection=True, long=True) or []
    if not selection:
        raise RuntimeError('Select a curve transform or curve shape.')
    return build_from_curve_max(selection[0], prefix=prefix,
                                include_zero=include_zero,
                                group=group, replace=replace)


if __name__ == '__main__':
    build_from_selection()
