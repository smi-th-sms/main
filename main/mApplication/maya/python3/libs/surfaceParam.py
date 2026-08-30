"""Create node-driven nulls distributed along a NURBS surface's U axis."""

import maya.cmds as cmds
import importlib
import sys


def _reload_module(module):
    if hasattr(importlib, 'reload'):
        return importlib.reload(module)
    return reload(module)


def _surface_shape(node):
    if not cmds.objExists(node):
        return None
    if cmds.nodeType(node) == 'nurbsSurface':
        return node
    shapes = cmds.listRelatives(node, shapes=True, noIntermediate=True,
                                type='nurbsSurface') or []
    return shapes[0] if shapes else None


def create_surface_u_nulls(surface, count=None, u_count=None, v_parameter=0.5,
                           use_percentage=True, parent=None,
                           name_prefix=None, create_joints=False, axis='U',
                           fixed_parameter=None):
    """Create transform nulls on one fixed-V U strip of *surface*.

    ``count`` controls the number of nulls. In percentage mode they are
    evenly distributed from U=0% to U=100%. ``u_count`` is kept as a
    backward-compatible alias. Each null exposes ``parameterU``/``parameterV``
    and drives its own
    pointOnSurfaceInfo, so the attachment remains editable after creation.
    """
    if fixed_parameter is None:
        fixed_parameter = v_parameter
    return create_surface_nulls(
        surface=surface, axis=axis, count=count, u_count=u_count,
        fixed_parameter=fixed_parameter, use_percentage=use_percentage,
        parent=parent, name_prefix=name_prefix,
        create_joints=create_joints)


def create_surface_nulls(surface, axis='U', count=None, u_count=None,
                         fixed_parameter=0.5, use_percentage=True,
                         parent=None, name_prefix=None, create_joints=False):
    """Create nulls distributed along the selected U or V parameter axis."""
    shape = _surface_shape(surface)
    if not shape:
        raise RuntimeError('A NURBS surface transform or shape is required')
    axis = str(axis).upper()
    if axis not in ('U', 'V'):
        raise ValueError('axis must be U or V')
    if count is not None and u_count is not None:
        raise ValueError('Use count or u_count, not both')
    if count is not None:
        u_count = count
    if u_count is None:
        u_count = int(cmds.getAttr(shape + '.spans' + axis)) + 1
    u_count = int(u_count)
    if u_count < 1:
        raise ValueError('u_count must be at least 1')
    u_max = float(cmds.getAttr(shape + '.spansU'))
    v_max = float(cmds.getAttr(shape + '.spansV'))
    if use_percentage:
        if not 0.0 <= float(fixed_parameter) <= 1.0:
            raise ValueError('fixed_parameter must be between 0 and 1')
    else:
        fixed_max = v_max if axis == 'U' else u_max
        if not 0.0 <= float(fixed_parameter) <= fixed_max:
            raise ValueError('fixed_parameter is outside the surface range')

    transform = (cmds.listRelatives(shape, parent=True, fullPath=False)
                 or [surface])[0]
    prefix = name_prefix or transform
    group = cmds.createNode('transform',
                            name='{}_{}_nulls_GRP'.format(prefix, axis))
    if parent:
        cmds.parent(group, parent)

    result = []
    for index in range(u_count):
        normalized = 0.0 if u_count == 1 else float(index) / (u_count - 1)
        varying_value = normalized if use_percentage else normalized * (u_max if axis == 'U' else v_max)
        fixed_value = fixed_parameter if use_percentage else fixed_parameter
        base = '{}_{:02d}'.format(prefix, index)
        psi = cmds.createNode('pointOnSurfaceInfo', name=base + '_PSI')
        cmds.connectAttr(shape + '.worldSpace[0]', psi + '.inputSurface',
                         force=True)
        cmds.setAttr(psi + '.turnOnPercentage', bool(use_percentage))

        rotate_helper = cmds.createNode('rotateHelper', name=base + '_RH')
        tangent_attr = ('normalizedTangentU' if axis == 'U'
                        else 'normalizedTangentV')
        cmds.connectAttr(psi + '.' + tangent_attr,
                         rotate_helper + '.forward', force=True)
        cmds.connectAttr(psi + '.normalizedNormal',
                         rotate_helper + '.up', force=True)

        null = cmds.createNode('transform', name=base + '_NULL')
        cmds.parent(null, group)
        cmds.addAttr(null, longName='parameterU', shortName='pu',
                     attributeType='double', keyable=True)
        cmds.addAttr(null, longName='parameterV', shortName='pv',
                     attributeType='double', keyable=True)
        if axis == 'U':
            cmds.setAttr(null + '.parameterU', varying_value)
            cmds.setAttr(null + '.parameterV', fixed_value)
        else:
            cmds.setAttr(null + '.parameterU', fixed_value)
            cmds.setAttr(null + '.parameterV', varying_value)
        cmds.connectAttr(null + '.parameterU', psi + '.parameterU', force=True)
        cmds.connectAttr(null + '.parameterV', psi + '.parameterV', force=True)

        decompose = cmds.createNode('decomposeMatrix', name=base + '_DM')
        cmds.connectAttr(rotate_helper + '.rotateMatrix',
                         decompose + '.inputMatrix', force=True)
        cmds.connectAttr(psi + '.position', null + '.translate', force=True)
        cmds.connectAttr(decompose + '.outputRotate', null + '.rotate',
                         force=True)
        result.append(null)

        if create_joints:
            add_child_joints([null])

    cmds.select(result, replace=True)
    return result


def add_child_joints(objects=None):
    """Add one zero-offset joint under each selected/provided transform."""
    objects = objects or (cmds.ls(selection=True, long=False) or [])
    if not objects:
        raise RuntimeError('Select at least one transform')

    joints = []
    for obj in objects:
        if not cmds.objExists(obj) or cmds.nodeType(obj) != 'transform':
            raise RuntimeError('{} is not a transform'.format(obj))
        joint = cmds.createNode('joint', name='{}_JNT'.format(obj))
        cmds.parent(joint, obj)
        cmds.setAttr(joint + '.translate', 0.0, 0.0, 0.0)
        cmds.setAttr(joint + '.rotate', 0.0, 0.0, 0.0)
        cmds.setAttr(joint + '.jointOrient', 0.0, 0.0, 0.0)
        joints.append(joint)

    cmds.select(joints, replace=True)
    return joints


def create_from_selection(**kwargs):
    """Create U/V nulls for exactly one selected NURBS surface."""
    selection = cmds.ls(selection=True, long=False) or []
    if len(selection) != 1:
        raise RuntimeError('Select exactly one NURBS surface')
    return create_surface_nulls(selection[0], **kwargs)


def reload_and_create(**kwargs):
    """Reload this module, then create U nulls from the current selection."""
    module = _reload_module(sys.modules[__name__])
    return module.create_from_selection(**kwargs)
