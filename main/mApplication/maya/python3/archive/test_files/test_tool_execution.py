#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test CFX Assets Manager tool execution
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing CFX Assets Manager Tool")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[INFO] Finding and testing CFX tool...")
print("-" * 80)

code = """
import hou

try:
    shelves = hou.shelves.shelves()
    shelf = shelves['cinematic2_tool']
    tools = shelf.tools()
    
    # Find CFX tool (any name with cfx_assets_manager)
    cfx_tool = None
    for tool in tools:
        if 'cfx_assets_manager' in tool.name():
            cfx_tool = tool
            break
    
    if not cfx_tool:
        print("[ERROR] No CFX tool found")
    else:
        print("[OK] Found CFX tool: {}".format(cfx_tool.name()))
        print()
        
        script = cfx_tool.script()
        if script and script.strip():
            print("[OK] Tool has script ({} chars)".format(len(script)))
            print()
            print("Script content:")
            print("="*70)
            print(script)
            print("="*70)
            print()
            
            # Test the script (without showing UI)
            print("[TEST] Checking if cfx_assets_ui can be imported...")
            print()
            
            import sys
            script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
            if script_path not in sys.path:
                sys.path.insert(0, script_path)
            
            try:
                import cfx_assets_ui
                print("[OK] cfx_assets_ui module imported successfully")
                print("     Module location: {}".format(cfx_assets_ui.__file__))
                print()
                print("="*70)
                print(" [SUCCESS] Tool script is working!")
                print("="*70)
                print()
                print("You can now:")
                print("  1. Click the '{}' button in cinematic2_tool shelf".format(cfx_tool.label()))
                print("  2. The CFX Assets Manager UI will open")
                print()
                print("Note: Tool name is '{}' (the number doesn't matter)".format(cfx_tool.name()))
            except Exception as e:
                print("[ERROR] Cannot import cfx_assets_ui: {}".format(str(e)))
                import traceback
                traceback.print_exc()
        else:
            print("[ERROR] Tool has no script")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Test finished!")
print("="*80)

connector.disconnect()





