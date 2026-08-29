"""Create local-matrix null controls for a Maya Bezier curve.

The curve transform is the local-space reference.  Each generated null is
parented below ``<curve>_CP_NULL_GRP`` and drives one Bezier control point via:

    null.worldMatrix * curve.worldInverseMatrix
        -> multMatrix -> decomposeMatrix -> curveShape.controlPoints[i]

This keeps the control point values in the curve's local space even when the
curve transform is moved, rotated, or scaled.
"""

from __future__ import absolute_import

import maya.cmds as cmds
import maya.api.OpenMaya as om


_WINDOW = "bezierControlPointRigWin"
_curve_field = None


def _bezier_shape(node):
    if not node or not cmds.objExists(node):
        return None
    if cmds.nodeType(node) == "bezierCurve":
        return node
    shapes = cmds.listRelatives(
        node, shapes=True, noIntermediate=True,
        type="bezierCurve", fullPath=True) or []
    return shapes[0] if shapes else None


def _selected_curve():
    for node in cmds.ls(selection=True, long=True) or []:
        shape = _bezier_shape(node)
        if shape:
            return shape
    return None


def _control_point_position(shape, index):
    value = cmds.getAttr("{}.controlPoints[{}]".format(shape, index))
    if isinstance(value, (tuple, list)) and value and isinstance(value[0], (tuple, list)):
        value = value[0]
    if not value or len(value) < 3:
        raise RuntimeError("Cannot read control point {} on {}".format(index, shape))
    return tuple(float(v) for v in value[:3])


def create_rig(curve="bezier1", parent=None):
    """Create one local null and matrix driver for every Bezier control point."""
    shape = _bezier_shape(curve) or _selected_curve()
    if not shape:
        raise RuntimeError("Select a Bezier curve or provide its transform name.")

    curve_transform = (cmds.listRelatives(shape, parent=True, fullPath=False) or [curve])[0]
    count = cmds.getAttr(shape + ".controlPoints", size=True)
    if not count:
        raise RuntimeError("No Bezier control points found on {}.".format(shape))

    group_name = curve_transform + "_CP_NULL_GRP"
    # Keep the control group outside the curve transform hierarchy.  The
    # matrix driver below converts this world-space null back into curve-local
    # space before writing the Bezier control point.
    group = cmds.createNode("transform", name=group_name, parent=parent)
    curve_world_matrix = om.MMatrix(cmds.getAttr(curve_transform + ".worldMatrix[0]"))
    result = []

    for index in range(int(count)):
        base = "{}_CP{:02d}".format(curve_transform, index)
        null = cmds.createNode("transform", name=base + "_NULL", parent=group)
        local_point = om.MPoint(*_control_point_position(shape, index))
        world_point = local_point * curve_world_matrix
        cmds.xform(null, worldSpace=True,
                   translation=(world_point.x, world_point.y, world_point.z))
        cmds.setAttr(null + ".rotate", 0.0, 0.0, 0.0, type="double3")

        mult = cmds.createNode("multMatrix", name=base + "_MM")
        decompose = cmds.createNode("decomposeMatrix", name=base + "_DM")
        cmds.connectAttr(null + ".worldMatrix[0]", mult + ".matrixIn[0]", force=True)
        cmds.connectAttr(curve_transform + ".worldInverseMatrix[0]",
                         mult + ".matrixIn[1]", force=True)
        cmds.connectAttr(mult + ".matrixSum", decompose + ".inputMatrix", force=True)
        cmds.connectAttr(decompose + ".outputTranslate",
                         "{}.controlPoints[{}]".format(shape, index), force=True)

        if not cmds.attributeQuery("controlPointIndex", node=null, exists=True):
            cmds.addAttr(null, longName="controlPointIndex", attributeType="long",
                         keyable=False)
        cmds.setAttr(null + ".controlPointIndex", index)
        result.append(null)

    cmds.select(result, replace=True)
    print("Created {} Bezier control point nulls for {}".format(len(result), curve_transform))
    return result


def create_from_selection(*_):
    selection = cmds.ls(selection=True, long=False) or []
    if len(selection) != 1:
        raise RuntimeError("Select exactly one Bezier curve.")
    return create_rig(selection[0])


def _use_selection(*_):
    shape = _selected_curve()
    if shape and _curve_field:
        parent = cmds.listRelatives(shape, parent=True, fullPath=False) or [shape]
        cmds.textField(_curve_field, edit=True, text=parent[0])


def _build_from_ui(*_):
    try:
        curve = cmds.textField(_curve_field, query=True, text=True).strip()
        if not curve:
            raise RuntimeError("Bezier curve is required.")
        create_rig(curve)
    except RuntimeError as exc:
        cmds.warning("Bezier Control Point Rig: {}".format(exc))


def show():
    global _curve_field
    if cmds.window(_WINDOW, exists=True):
        cmds.deleteUI(_WINDOW)
    cmds.window(_WINDOW, title="Bezier Control Point Rig", widthHeight=(340, 120),
                sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                      columnOffset=("both", 8))
    cmds.text(label="Bezier control points → local matrix null controls", align="left")
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=2,
                   columnWidth3=(60, 210, 55))
    cmds.text(label="Curve")
    _curve_field = cmds.textField(text="bezier1")
    cmds.button(label="Use Sel", command=_use_selection)
    cmds.setParent("..")
    cmds.button(label="Create Controls", height=32, command=_build_from_ui)
    _use_selection()
    cmds.showWindow(_WINDOW)


if __name__ == "__main__":
    show()
