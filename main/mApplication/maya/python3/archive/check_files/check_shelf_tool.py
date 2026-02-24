#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Check CFX Assets Manager tool in shelf
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Checking CFX Assets Manager Tool in Shelf")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Checking cinematic2_tool shelf...")
print("-" * 80)

code = """
import hou

try:
    shelves = hou.shelves.shelves()
    
    if 'cinematic2_tool' not in shelves:
        print("[ERROR] cinematic2_tool shelf not found")
        print("Available shelves:")
        for name in sorted(shelves.keys())[:20]:
            print("  - {}".format(name))
    else:
        shelf = shelves['cinematic2_tool']
        print("[OK] Found cinematic2_tool shelf")
        print()
        
        tools = shelf.tools()
        print("Tools in shelf: {}".format(len(tools)))
        print()
        
        for tool in tools:
            print("Tool: {}".format(tool.name()))
            print("  Label: {}".format(tool.label()))
            print("  Icon: {}".format(tool.icon()))
            
            # Get script
            try:
                script = tool.script()
                script_lines = script.split('\\n') if script else []
                
                if script and script.strip():
                    print("  Script: {} lines".format(len(script_lines)))
                    print("  First line: {}".format(script_lines[0][:50] if script_lines else ""))
                else:
                    print("  Script: [EMPTY]")
            except Exception as e:
                print("  Script: [ERROR] {}".format(str(e)))
            
            print()

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[2] Checking CFX Assets Manager tool specifically...")
print("-" * 80)

code = """
import hou

try:
    shelves = hou.shelves.shelves()
    
    if 'cinematic2_tool' in shelves:
        shelf = shelves['cinematic2_tool']
        tools = shelf.tools()
        
        cfx_tool = None
        for tool in tools:
            if tool.name() == "cfx_assets_manager":
                cfx_tool = tool
                break
        
        if cfx_tool:
            print("[OK] Found CFX Assets Manager tool")
            print()
            print("Name: {}".format(cfx_tool.name()))
            print("Label: {}".format(cfx_tool.label()))
            print("Icon: {}".format(cfx_tool.icon()))
            print()
            
            # Get script content
            script = cfx_tool.script()
            
            if script and script.strip():
                print("Script content:")
                print("="*70)
                print(script)
                print("="*70)
                print()
                print("[OK] Script exists ({} characters)".format(len(script)))
            else:
                print("[ERROR] Script is EMPTY!")
                print()
                print("This is the problem. The tool exists but has no script.")
        else:
            print("[ERROR] CFX Assets Manager tool not found in shelf")
    else:
        print("[ERROR] cinematic2_tool shelf not found")

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

connector.disconnect()





