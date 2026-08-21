import importlib
import os
import sys


addon_dir = os.path.join(
    os.path.expanduser("~"),
    "AppData",
    "Roaming",
    "Blender Foundation",
    "Blender",
    "5.2",
    "scripts",
    "addons",
)
if addon_dir not in sys.path:
    sys.path.insert(0, addon_dir)

module = importlib.import_module("blender_mcp")
if not getattr(module, "_codex_registered", False):
    module.register()
    module._codex_registered = True
    print("Codex Blender MCP startup: server registered on port 9876")
