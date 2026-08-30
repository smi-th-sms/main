"""UI wrapper around python3.libs.surfaceParam for live surface nulls."""

from __future__ import absolute_import

import maya.cmds as cmds
from python3.libs import surfaceParam


_WINDOW = "nurbsSurfaceNullSamplerWin"
_surface_field = None
_axis_field = None
_count_field = None
_v_field = None
_parent_field = None
_joints_field = None


def create_from_selection(axis='U', count=5, fixed_parameter=0.5, parent=None,
                          create_joints=False):
    """Create live U- or V-strip nulls on the one selected surface."""
    return surfaceParam.create_from_selection(
        axis=axis, count=int(count), fixed_parameter=float(fixed_parameter), parent=parent,
        use_percentage=True, create_joints=bool(create_joints))


def _use_selection(*_):
    selection = cmds.ls(selection=True, long=False) or []
    if len(selection) == 1 and _surface_field:
        cmds.textField(_surface_field, edit=True, text=selection[0])


def _set_parent_from_selection(*_):
    selection = cmds.ls(selection=True, long=False) or []
    if len(selection) == 1 and _parent_field:
        cmds.textField(_parent_field, edit=True, text=selection[0])


def _build(*_):
    try:
        surface = cmds.textField(_surface_field, query=True, text=True).strip()
        if surface:
            cmds.select(surface, replace=True)
        create_from_selection(
            axis=cmds.optionMenu(_axis_field, query=True, value=True),
            count=cmds.intField(_count_field, query=True, value=True),
            fixed_parameter=cmds.floatField(_v_field, query=True, value=True),
            parent=cmds.textField(_parent_field, query=True, text=True).strip() or None,
            create_joints=cmds.checkBox(_joints_field, query=True, value=True),
        )
    except (RuntimeError, ValueError) as exc:
        cmds.warning("NURBS Surface Null Tool: {}".format(exc))


def show():
    """Show the compact surface parameter null builder UI."""
    global _surface_field, _axis_field, _count_field, _v_field
    global _parent_field, _joints_field
    if cmds.window(_WINDOW, exists=True):
        cmds.deleteUI(_WINDOW)

    cmds.window(_WINDOW, title="Surface Parameter Null Tool",
                widthHeight=(360, 220), sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                      columnOffset=("both", 10))
    cmds.text(label="Live U/V parameter nulls on a NURBS surface", align="left")

    cmds.rowLayout(numberOfColumns=3, adjustableColumn=2,
                   columnWidth3=(70, 210, 60))
    cmds.text(label="Surface")
    _surface_field = cmds.textField(text="")
    cmds.button(label="Use Sel", command=_use_selection)
    cmds.setParent("..")

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                   columnWidth2=(100, 100))
    cmds.text(label="Direction")
    _axis_field = cmds.optionMenu()
    cmds.menuItem(label="U")
    cmds.menuItem(label="V")
    cmds.setParent("..")

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                   columnWidth2=(100, 100))
    cmds.text(label="Count")
    _count_field = cmds.intField(value=5, minValue=1)
    cmds.setParent("..")

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                   columnWidth2=(100, 100))
    cmds.text(label="Fixed Other UV")
    _v_field = cmds.floatField(value=0.5, minValue=0.0, maxValue=1.0)
    cmds.setParent("..")

    cmds.rowLayout(numberOfColumns=3, adjustableColumn=2,
                   columnWidth3=(100, 210, 60))
    cmds.text(label="Parent (optional)")
    _parent_field = cmds.textField(text="")
    cmds.button(label="Use Sel", command=_set_parent_from_selection)
    cmds.setParent("..")

    _joints_field = cmds.checkBox(label="Create child joints", value=False)
    cmds.separator(height=4)
    cmds.button(label="Create Nulls", height=36, command=_build)
    _use_selection()
    cmds.showWindow(_WINDOW)


if __name__ == "__main__":
    show()
