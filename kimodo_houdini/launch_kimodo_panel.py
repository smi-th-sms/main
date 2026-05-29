"""Launch the Kimodo Houdini panel from Houdini's Python Source Editor."""

import importlib
import sys

MODULE_DIR = "E:/script/pythonWorkSpace/kimodo_houdini"

if MODULE_DIR not in sys.path:
    sys.path.insert(0, MODULE_DIR)

import kimodo_houdini_panel

importlib.reload(kimodo_houdini_panel)
kimodo_houdini_panel.show_deferred()
