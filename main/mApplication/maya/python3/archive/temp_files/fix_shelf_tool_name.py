#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fix CFX Assets Manager tool name and remove duplicates
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Fixing CFX Assets Manager Tool")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Removing old/empty tools and keeping the working one...")
print("-" * 80)

code = """
import hou

try:
    shelves = hou.shelves.shelves()
    shelf = shelves['cinematic2_tool']
    tools = list(shelf.tools())
    
    print("[INFO] Current tools: {}".format(len(tools)))
    for tool in tools:
        print("  - {} (script: {} chars)".format(tool.name(), len(tool.script())))
    print()
    
    # Find all CFX tools
    cfx_tools = []
    other_tools = []
    
    for tool in tools:
        if 'cfx_assets_manager' in tool.name():
            cfx_tools.append(tool)
        else:
            other_tools.append(tool)
    
    print("[INFO] Found {} CFX tool(s)".format(len(cfx_tools)))
    print()
    
    # Find the one with script
    working_tool = None
    for tool in cfx_tools:
        script = tool.script()
        if script and script.strip():
            working_tool = tool
            print("[OK] Found working CFX tool: {}".format(tool.name()))
            print("    Script length: {} chars".format(len(script)))
            break
    
    if working_tool:
        # Create new tool with correct name
        new_tool = hou.shelves.newTool(
            file_path=None,
            name="cfx_assets_manager",
            label="CFX Assets Manager",
            script=working_tool.script(),
            language=hou.scriptLanguage.Python,
            icon="MISC_python",
            help_url="",
            help="Launch CFX Assets Manager UI"
        )
        
        # Rebuild tools list: other tools + new CFX tool
        new_tools = other_tools + [new_tool]
        
        # Update shelf
        shelf.setTools(tuple(new_tools))
        
        print()
        print("[OK] Shelf updated")
        print("    Removed {} old CFX tool(s)".format(len(cfx_tools)))
        print("    Added 1 new CFX tool with correct name")
        print()
        print("Final tools: {}".format(len(new_tools)))
        for tool in new_tools:
            print("  - {}".format(tool.name()))
    else:
        print("[ERROR] No working CFX tool found")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[2] Saving shelf to file...")
print("-" * 80)

code = """
import hou
import os

try:
    shelves = hou.shelves.shelves()
    shelf = shelves['cinematic2_tool']
    tools = shelf.tools()
    
    # Get shelf file path
    houdini_prefs = hou.homeHoudiniDirectory()
    shelf_file = os.path.join(houdini_prefs, "toolbar", "cinematic2_tool.shelf")
    
    # Build XML
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\\n'
    xml_content += '<shelfDocument>\\n'
    xml_content += '  <!-- This file contains definitions of shelves, toolbars, and tools. -->\\n\\n'
    
    for tool in tools:
        xml_content += '  <tool name="{}" label="{}" icon="{}">\\n'.format(
            tool.name(), tool.label(), tool.icon())
        
        script = tool.script()
        if script:
            xml_content += '    <script scriptType="python"><![CDATA[{}]]></script>\\n'.format(script)
        
        xml_content += '  </tool>\\n\\n'
    
    xml_content += '</shelfDocument>\\n'
    
    # Write file
    with open(shelf_file, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    
    print("[OK] Shelf file saved: {}".format(shelf_file))
    print("    Size: {} bytes".format(os.path.getsize(shelf_file)))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[3] Final verification...")
print("-" * 80)

code = """
import hou

try:
    shelves = hou.shelves.shelves()
    shelf = shelves['cinematic2_tool']
    tools = shelf.tools()
    
    print("="*70)
    print(" Final Tool List")
    print("="*70)
    print()
    
    for tool in tools:
        script = tool.script()
        script_status = "[OK]" if (script and script.strip()) else "[EMPTY]"
        print("{} {} - {}".format(script_status, tool.name(), tool.label()))
    
    print()
    
    # Check CFX tool specifically
    cfx_tool = None
    for tool in tools:
        if tool.name() == "cfx_assets_manager":
            cfx_tool = tool
            break
    
    if cfx_tool:
        script = cfx_tool.script()
        if script and script.strip():
            print("="*70)
            print(" [SUCCESS] CFX Assets Manager is ready!")
            print("="*70)
            print()
            print("Tool name: {}".format(cfx_tool.name()))
            print("Tool label: {}".format(cfx_tool.label()))
            print("Script length: {} chars".format(len(script)))
            print()
            print("You can now click the button in the shelf to launch the UI")
        else:
            print("[ERROR] CFX tool script is still empty")
    else:
        print("[ERROR] CFX Assets Manager tool not found")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Tool fix finished!")
print("="*80)

connector.disconnect()





