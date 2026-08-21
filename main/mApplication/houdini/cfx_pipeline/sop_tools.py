# -*- coding: utf-8 -*-
"""Small, non-destructive CFX SOP tools used by the cinematic2 shelf."""

from __future__ import annotations

from typing import Any


COLLISION_RULES_VEX = """// Vellum point collision rules.
s@collisionignore = chs("cfx_ignore_pattern");
s@collisiongroup = chs("cfx_collision_group");
i@disableself = chi("cfx_disable_self");
i@disableexternal = chi("cfx_disable_external");
"""

FRICTION_VEX = """// Vellum per-point friction multipliers.
f@friction = chf("cfx_static_friction");
f@dynamicfriction = chf("cfx_dynamic_friction");
"""


def _show(message: str, severity: str = "message") -> None:
    from .ui_feedback import show_message
    show_message("CFX SOP Tool", message, severity)


def _selected_sop():
    """Return one selected SOP without assuming a particular HDA depth."""

    import hou
    selected = [node for node in hou.selectedNodes()
                if node.type().category() == hou.sopNodeTypeCategory()]
    if len(selected) != 1:
        raise ValueError(
            "Select exactly one SOP node. The new wrangle is created beside "
            "that node and connected to its output.")
    source = selected[0]
    parent = source.parent()
    if parent is None or parent.childTypeCategory() != hou.sopNodeTypeCategory():
        raise ValueError("The selected node is not inside an editable SOP network.")
    if not parent.isEditable():
        raise ValueError(
            "The selected SOP is inside a locked HDA. Allow Editing of Contents "
            "or create the wrangle outside the HDA.")
    return source


def _append_controls(node, templates) -> None:
    import hou
    group = node.parmTemplateGroup()
    folder = hou.FolderParmTemplate(
        "cfx_controls", "CFX Controls", folder_type=hou.folderType.Simple)
    for template in templates:
        folder.addParmTemplate(template)
    group.append(folder)
    node.setParmTemplateGroup(group)


def _new_wrangle(source, name: str, snippet: str):
    import hou
    parent = source.parent()
    node = parent.createNode("attribwrangle", name)
    node.setInput(0, source, 0)
    node.parm("class").set(2)  # points
    node.parm("snippet").set(snippet)
    node.setPosition(source.position() + hou.Vector2(0.0, -1.5))
    for selected in hou.selectedNodes():
        selected.setSelected(False)
    node.setSelected(True, clear_all_selected=True)
    node.setCurrent(True, clear_all_selected=True)
    return node


def create_collision_rules() -> dict[str, Any]:
    """Create a point wrangle for Vellum collision-ignore/group attributes."""

    import hou
    try:
        source = _selected_sop()
        node = _new_wrangle(source, "cfx_collision_rules", COLLISION_RULES_VEX)
        ignore = hou.StringParmTemplate(
            "cfx_ignore_pattern", "Ignore Pattern", 1,
            default_value=("external",))
        ignore.setHelp(
            "Vellum collisionignore pattern. Examples: external, groundplane, "
            "self, external/body, or * to ignore every collision target.")
        collision_group = hou.StringParmTemplate(
            "cfx_collision_group", "Collision Group", 1,
            default_value=("",))
        collision_group.setHelp(
            "Optional Vellum collisiongroup label assigned to these points.")
        disable_self = hou.ToggleParmTemplate(
            "cfx_disable_self", "Disable Self Collision", default_value=False)
        disable_external = hou.ToggleParmTemplate(
            "cfx_disable_external", "Disable External Collision", default_value=False)
        _append_controls(
            node, (ignore, collision_group, disable_self, disable_external))
        node.setComment(
            "CFX Vellum collisionignore/collisiongroup/disableself/disableexternal")
        node.setGenericFlag(hou.nodeFlag.DisplayComment, True)
        _show("Collision Rules wrangle created.\n\n%s\n\nExisting downstream "
              "connections were not changed." % node.path())
        return {"node": node.path(), "source": source.path(), "rewired": False}
    except Exception as exc:
        _show("Collision Rules creation failed:\n%s" % exc, "error")
        raise


def create_friction() -> dict[str, Any]:
    """Create a point wrangle for Vellum static/dynamic friction multipliers."""

    import hou
    try:
        source = _selected_sop()
        node = _new_wrangle(source, "cfx_vellum_friction", FRICTION_VEX)
        static = hou.FloatParmTemplate(
            "cfx_static_friction", "Static Friction Multiplier", 1,
            default_value=(1.0,), min=0.0, min_is_strict=True)
        static.setHelp(
            "Point friction multiplier. Vellum multiplies the values from both "
            "colliding objects and the solver's Static Threshold.")
        dynamic = hou.FloatParmTemplate(
            "cfx_dynamic_friction", "Dynamic Friction Multiplier", 1,
            default_value=(1.0,), min=0.0, min_is_strict=True)
        dynamic.setHelp(
            "Point dynamicfriction multiplier applied to sliding collisions.")
        _append_controls(node, (static, dynamic))
        node.setComment("CFX Vellum friction/dynamicfriction multipliers")
        node.setGenericFlag(hou.nodeFlag.DisplayComment, True)
        _show("Vellum Friction wrangle created.\n\n%s\n\nExisting downstream "
              "connections were not changed." % node.path())
        return {"node": node.path(), "source": source.path(), "rewired": False}
    except Exception as exc:
        _show("Vellum Friction creation failed:\n%s" % exc, "error")
        raise
