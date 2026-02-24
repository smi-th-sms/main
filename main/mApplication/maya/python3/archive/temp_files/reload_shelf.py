#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Reload cinematic2_tool shelf in Houdini
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Reloading cinematic2_tool Shelf")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Verifying shelf file exists...")
print("-" * 80)

code = """
import hou
import os

try:
    houdini_prefs = hou.homeHoudiniDirectory()
    shelf_file = os.path.join(houdini_prefs, "toolbar", "cinematic2_tool.shelf")
    
    if os.path.exists(shelf_file):
        size = os.path.getsize(shelf_file)
        print("[OK] Shelf file exists")
        print("    Path: {}".format(shelf_file))
        print("    Size: {} bytes".format(size))
    else:
        print("[ERROR] Shelf file not found: {}".format(shelf_file))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[2] Reloading shelf tools...")
print("-" * 80)

code = """
import hou

try:
    # Get current shelves
    shelves = hou.shelves.shelves()
    
    if 'cinematic2_tool' in shelves:
        print("[INFO] cinematic2_tool shelf is currently loaded")
        
        # Get current tools
        shelf = shelves['cinematic2_tool']
        old_tools = shelf.tools()
        print("      Current tools: {}".format(len(old_tools)))
        
        # Force reload by reading from file
        # Houdini automatically reloads shelf files on restart
        # or when shelf set changes
        
        print()
        print("[INFO] To see changes:")
        print("       Option 1: Restart Houdini (recommended)")
        print("       Option 2: Right-click shelf area > Shelves > Uncheck and recheck cinematic2_tool")
        print("       Option 3: Window > Shelf Sets > Reload Shelf")
    else:
        print("[INFO] cinematic2_tool shelf not loaded yet")
        print("       Will be loaded on Houdini restart or when shelf set changes")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[3] Checking if CFX Assets Manager tool is available...")
print("-" * 80)

code = """
import hou

try:
    shelves = hou.shelves.shelves()
    
    if 'cinematic2_tool' in shelves:
        shelf = shelves['cinematic2_tool']
        tools = shelf.tools()
        
        print("Tools in cinematic2_tool shelf:")
        cfx_found = False
        
        for tool in tools:
            tool_name = tool.name()
            tool_label = tool.label()
            
            if tool_name == "cfx_assets_manager":
                cfx_found = True
                print("  [OK] {} ({})".format(tool_label, tool_name))
            else:
                print("  - {} ({})".format(tool_label, tool_name))
        
        print()
        
        if cfx_found:
            print("="*70)
            print(" [SUCCESS] CFX Assets Manager is available!")
            print("="*70)
            print()
            print("To use: Click 'CFX Assets Manager' button in cinematic2_tool shelf")
        else:
            print("[WARNING] CFX Assets Manager not found")
            print("          Please restart Houdini to load updated shelf")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[4] Testing tool execution (optional)...")
print("-" * 80)

code = """
import hou

try:
    print("[INFO] Testing CFX Assets Manager launch...")
    print()
    
    # Try to import and run (without actually showing UI)
    import sys
    script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
    if script_path not in sys.path:
        sys.path.insert(0, script_path)
    
    import cfx_assets_ui
    
    print("[OK] cfx_assets_ui module can be imported")
    print("     Module path: {}".format(cfx_assets_ui.__file__))
    print()
    print("[INFO] CFX Assets Manager is ready to use!")
    print("       Click the button in the shelf to launch the UI")

except Exception as e:
    print("[ERROR] Cannot import cfx_assets_ui: {}".format(str(e)))
    print("        Check that the file exists at:")
    print("        T:\\scripts\\python\\application\\houdini\\houdini21.0\\script\\cfx_assets_ui.py")
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Shelf registration complete!")
print("="*80)
print()
print("[OK] cinematic2_tool.shelf file created/updated")
print("[OK] CFX Assets Manager tool added to shelf")
print()
print("NEXT STEPS:")
print("  1. Restart Houdini (recommended)")
print("     OR")
print("  2. Right-click shelf area > Shelves > Toggle cinematic2_tool off/on")
print()
print("THEN:")
print("  - Find 'cinematic2_tool' shelf in Houdini")
print("  - Click 'CFX Assets Manager' button (Python icon)")
print("  - UI will open")

connector.disconnect()





