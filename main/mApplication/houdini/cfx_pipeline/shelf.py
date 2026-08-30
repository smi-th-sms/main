# -*- coding: utf-8 -*-
"""Register the CFX shelf tools (Asset / Shot entry points) on a LOCAL shelf.

Creates a ``cinematic2`` shelf in the user's local toolbar dir
(``$HOUDINI_USER_PREF_DIR/toolbar``) with CFX setup and SOP helper tools:

* **CFX Asset** -> :func:`ui_asset.create_asset_tool`
* **CFX Shot**  -> :func:`ui_shot.create_shot_tool`

Deliberately LOCAL (never writes to the shared ``Z:`` toolbar). Idempotent —
re-run :func:`install` to refresh the tool scripts/labels.

Install from Houdini's Python shell::

    import sys; sys.path.insert(0, r"E:\\script\\pythonWorkSpace")
    from main.mApplication.houdini.cfx_pipeline import shelf
    shelf.install()
"""

from __future__ import annotations

from typing import Any

_ROOT = r"E:\script\pythonWorkSpace"


def _tool_script(module: str, func: str) -> str:
    """Python shelf-button body: ensure sys.path, import the UI module, spawn
    the tool (robust to sys.path not being set yet)."""

    return (
        "import sys\n"
        f"root = r'{_ROOT}'\n"
        "sys.path.insert(0, root) if root not in sys.path else None\n"
        f"from main.mApplication.houdini.cfx_pipeline import {module}\n"
        f"{module}.{func}()"
    )


# (name, label, module, factory, icon)
_TOOLS = [
    ("cfx_asset_setup", "CFX Asset", "ui_asset", "create_asset_tool", "SOP_subnet"),
    ("cfx_shot_setup", "CFX Shot", "ui_shot", "create_shot_tool", "SOP_subnet"),
    ("cfx_collision_rules", "Collision Rules", "sop_tools",
     "create_collision_rules", "SOP_attribwrangle"),
    ("cfx_vellum_friction", "Vellum Friction", "sop_tools",
     "create_friction", "SOP_attribwrangle"),
]


def install(shelf_name: str = "cinematic2", shelf_label: str = "cinematic2") -> dict[str, Any]:
    """Create/refresh the local ``cinematic2`` shelf with the CFX tools."""

    import os
    import hou

    toolbar = hou.expandString("$HOUDINI_USER_PREF_DIR/toolbar")
    if not os.path.isdir(toolbar):
        os.makedirs(toolbar)
    fpath = os.path.join(toolbar, "cfx_cinematic2.shelf").replace("\\", "/")

    existing = hou.shelves.tools()
    tools = []
    for name, label, module, func, icon in _TOOLS:
        script = _tool_script(module, func)
        tool = existing.get(name)
        if tool is None:
            try:
                tool = hou.shelves.newTool(
                    file_path=fpath, name=name, label=label, script=script,
                    language=hou.scriptLanguage.Python, icon=icon)
            except Exception:   # icon may be rejected on some builds
                tool = hou.shelves.newTool(
                    file_path=fpath, name=name, label=label, script=script,
                    language=hou.scriptLanguage.Python)
        else:
            tool.setLabel(label)
            tool.setScript(script)
            tool.setLanguage(hou.scriptLanguage.Python)
            try:
                tool.setIcon(icon)
            except Exception:
                pass
        tools.append(tool)

    shelf = hou.shelves.shelves().get(shelf_name)
    if shelf is None:
        shelf = hou.shelves.newShelf(file_path=fpath, name=shelf_name, label=shelf_label)
    else:
        shelf.setLabel(shelf_label)
    # keep any pre-existing tools on the shelf, append ours (dedupe by identity)
    current = list(shelf.tools())
    for t in tools:
        if t not in current:
            current.append(t)
    shelf.setTools(current)

    return {"shelf": shelf.name(), "label": shelf.label(), "file": fpath,
            "tools": [t.name() for t in tools]}
