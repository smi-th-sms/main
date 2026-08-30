#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Restart CFX Assets Manager UI with fresh module
"""

import sys
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Restarting CFX Assets Manager UI")
print("="*80)

connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Closing existing CFX window...")
print("-" * 80)

code = """
import hou

try:
    # Close existing window
    if hasattr(hou.session, 'cfx_window') and hou.session.cfx_window is not None:
        if hou.session.cfx_window.isVisible():
            hou.session.cfx_window.close()
            print("[OK] Closed existing CFX window")
        hou.session.cfx_window = None
    else:
        print("[INFO] No existing window to close")
except Exception as e:
    print("[ERROR] Closing window: {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[2] Reloading module...")
print("-" * 80)

code = """
import sys

try:
    # Remove module from cache
    if 'cfx_assets_ui' in sys.modules:
        del sys.modules['cfx_assets_ui']
        print("[OK] Unloaded cfx_assets_ui module")
    
    # Ensure correct path
    script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
    if script_path not in sys.path:
        sys.path.insert(0, script_path)
    
    print("[OK] Module ready to reload")
    
except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[3] Opening new CFX window...")
print("-" * 80)

code = """
import sys
import hou

try:
    # Import fresh module
    script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
    if script_path not in sys.path:
        sys.path.insert(0, script_path)
    
    import cfx_assets_ui
    
    print("[OK] Module imported: {}".format(cfx_assets_ui.__file__))
    
    # Create new window
    if not hasattr(hou.session, 'cfx_window'):
        hou.session.cfx_window = None
    
    hou.session.cfx_window = cfx_assets_ui.CFXAssetsMainWindow()
    hou.session.cfx_window.show()
    
    print("[OK] CFX Assets Manager window opened")
    print()
    print("="*70)
    print(" READY TO TEST")
    print("="*70)
    print()
    print("The window now uses the updated code.")
    print("When you click Auto Setup, the HDA node will be named 'assets'")
    
except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] UI Restarted")
print("="*80)
print()
print("The CFX Assets Manager window is now open with the updated code.")
print("Try Auto Setup - the node should be named 'assets'")

connector.disconnect()





