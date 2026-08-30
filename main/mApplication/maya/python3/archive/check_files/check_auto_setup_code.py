#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Check Auto Setup code in loaded module
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Checking Auto Setup Code")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Checking loaded cfx_assets_ui module...")
print("-" * 80)

code = """
import sys

try:
    if 'cfx_assets_ui' in sys.modules:
        import cfx_assets_ui
        
        print("[INFO] cfx_assets_ui module is loaded")
        print("      Module file: {}".format(cfx_assets_ui.__file__))
        print()
        
        # Get on_auto_setup method
        if hasattr(cfx_assets_ui, 'CFXAssetsMainWindow'):
            cls = cfx_assets_ui.CFXAssetsMainWindow
            if hasattr(cls, 'on_auto_setup'):
                method = cls.on_auto_setup
                
                # Get source code
                import inspect
                source = inspect.getsource(method)
                
                print("[INFO] Checking on_auto_setup method...")
                print()
                
                # Check for node_name assignment
                if 'node_name = "assets"' in source:
                    print("[OK] Code has 'node_name = \\"assets\\"'")
                    print("    Code is CORRECT")
                elif 'node_name = assets_name' in source:
                    print("[ERROR] Code still has 'node_name = assets_name'")
                    print("    Code is OLD VERSION")
                else:
                    print("[WARNING] Cannot find node_name assignment")
                
                print()
                print("Relevant code section:")
                print("="*70)
                
                # Extract relevant lines
                lines = source.split('\\n')
                for i, line in enumerate(lines):
                    if 'node_name' in line and '=' in line:
                        # Print context (3 lines before and after)
                        start = max(0, i-3)
                        end = min(len(lines), i+4)
                        for j in range(start, end):
                            marker = ">>> " if j == i else "    "
                            print("{}{}".format(marker, lines[j]))
                        print()
                        break
                
                print("="*70)
            else:
                print("[ERROR] CFXAssetsMainWindow has no on_auto_setup method")
        else:
            print("[ERROR] cfx_assets_ui has no CFXAssetsMainWindow class")
    else:
        print("[INFO] cfx_assets_ui module not loaded yet")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[2] Checking file on disk...")
print("-" * 80)

code = """
import os

try:
    file_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script\\cfx_assets_ui.py"
    
    if os.path.exists(file_path):
        print("[OK] File exists: {}".format(file_path))
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Search for node_name assignment
        if 'node_name = "assets"' in content:
            print("[OK] File contains 'node_name = \\"assets\\"'")
        elif 'node_name = assets_name' in content:
            print("[ERROR] File contains OLD CODE: 'node_name = assets_name'")
        
        # Find the exact line
        lines = content.split('\\n')
        for i, line in enumerate(lines, 1):
            if 'node_name =' in line and ('assets' in line or 'hda_node' in line):
                print()
                print("Line {}: {}".format(i, line.strip()))
    else:
        print("[ERROR] File not found: {}".format(file_path))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[3] Reloading module...")
print("-" * 80)

code = """
import sys
import importlib

try:
    # Force reload
    if 'cfx_assets_ui' in sys.modules:
        print("[INFO] Unloading cfx_assets_ui module...")
        del sys.modules['cfx_assets_ui']
    
    # Clear path and re-add
    script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
    if script_path in sys.path:
        sys.path.remove(script_path)
    sys.path.insert(0, script_path)
    
    # Import fresh
    import cfx_assets_ui
    
    print("[OK] Module reloaded from: {}".format(cfx_assets_ui.__file__))
    print()
    
    # Verify the change
    import inspect
    method = cfx_assets_ui.CFXAssetsMainWindow.on_auto_setup
    source = inspect.getsource(method)
    
    if 'node_name = "assets"' in source:
        print("="*70)
        print(" [SUCCESS] Module has correct code!")
        print("="*70)
        print()
        print('node_name = "assets" found in on_auto_setup method')
        print()
        print("The UI needs to be restarted to use the new code.")
        print("Close the CFX Assets Manager window and reopen it.")
    else:
        print("[ERROR] Module still has old code")
        print("The file may not have been saved correctly")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Check finished")
print("="*80)
print()
print("NEXT STEPS:")
print("  1. If module has correct code:")
print("     - Close CFX Assets Manager window")
print("     - Reopen it from shelf")
print("     - Try Auto Setup again")
print()
print("  2. If module has old code:")
print("     - File was not saved correctly")
print("     - Will apply fix again")

connector.disconnect()





