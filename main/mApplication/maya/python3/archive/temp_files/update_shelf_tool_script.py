#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Update CFX Assets Manager tool script directly in Houdini
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Updating CFX Assets Manager Tool Script")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Finding CFX Assets Manager tool...")
print("-" * 80)

code = """
import hou

try:
    shelves = hou.shelves.shelves()
    
    if 'cinematic2_tool' not in shelves:
        print("[ERROR] cinematic2_tool shelf not found")
    else:
        shelf = shelves['cinematic2_tool']
        tools = shelf.tools()
        
        cfx_tool = None
        for tool in tools:
            if tool.name() == "cfx_assets_manager":
                cfx_tool = tool
                break
        
        if cfx_tool:
            print("[OK] Found CFX Assets Manager tool")
            print("    Current script length: {} chars".format(len(cfx_tool.script())))
        else:
            print("[ERROR] CFX Assets Manager tool not found")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[2] Updating tool script...")
print("-" * 80)

code = """
import hou

try:
    # New script content
    new_script = '''import sys
script_path = r"T:\\\\scripts\\\\python\\\\application\\\\houdini\\\\houdini21.0\\\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

import cfx_assets_ui
window = cfx_assets_ui.CFXAssetsMainWindow()
window.show()'''
    
    shelves = hou.shelves.shelves()
    shelf = shelves['cinematic2_tool']
    tools = list(shelf.tools())
    
    # Find and update CFX tool
    cfx_tool_index = -1
    for i, tool in enumerate(tools):
        if tool.name() == "cfx_assets_manager":
            cfx_tool_index = i
            break
    
    if cfx_tool_index >= 0:
        old_tool = tools[cfx_tool_index]
        
        # Create new tool with updated script
        new_tool = hou.shelves.newTool(
            file_path=None,
            name="cfx_assets_manager",
            label="CFX Assets Manager",
            script=new_script,
            language=hou.scriptLanguage.Python,
            icon="MISC_python",
            help_url="",
            help="Launch CFX Assets Manager UI"
        )
        
        # Replace tool in list
        tools[cfx_tool_index] = new_tool
        
        # Update shelf
        shelf.setTools(tuple(tools))
        
        print("[OK] Tool script updated")
        print("    New script length: {} chars".format(len(new_tool.script())))
        print()
        print("Script content:")
        print("="*70)
        print(new_tool.script())
        print("="*70)
    else:
        print("[ERROR] CFX Assets Manager tool not found")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[3] Saving shelf to file...")
print("-" * 80)

code = """
import hou
import os

try:
    shelves = hou.shelves.shelves()
    shelf = shelves['cinematic2_tool']
    
    # Get shelf file path
    houdini_prefs = hou.homeHoudiniDirectory()
    toolbar_path = os.path.join(houdini_prefs, "toolbar")
    shelf_file = os.path.join(toolbar_path, "cinematic2_tool.shelf")
    
    print("[INFO] Saving shelf to: {}".format(shelf_file))
    
    # Manually write shelf XML
    tools = shelf.tools()
    
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
    
    print("[OK] Shelf file saved")
    
    if os.path.exists(shelf_file):
        size = os.path.getsize(shelf_file)
        print("    Size: {} bytes".format(size))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[4] Verifying tool script...")
print("-" * 80)

code = """
import hou

try:
    shelves = hou.shelves.shelves()
    shelf = shelves['cinematic2_tool']
    tools = shelf.tools()
    
    for tool in tools:
        if tool.name() == "cfx_assets_manager":
            script = tool.script()
            
            if script and script.strip():
                print("[OK] CFX Assets Manager tool has script")
                print("    Length: {} characters".format(len(script)))
                print()
                print("First 100 chars:")
                print(script[:100])
                print()
                print("="*70)
                print(" [SUCCESS] Tool is ready to use!")
                print("="*70)
            else:
                print("[ERROR] Script is still empty")
            break
    else:
        print("[ERROR] CFX Assets Manager tool not found")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Tool update finished!")
print("="*80)
print()
print("Now you can:")
print("  1. Click 'CFX Assets Manager' button in cinematic2_tool shelf")
print("  2. The UI should open")
print()
print("If it still doesn't work, try:")
print("  - Click the button and check Python Shell for errors")
print("  - Or run manually in Python Shell:")
print("    import sys")
print("    sys.path.insert(0, r'T:\\scripts\\python\\application\\houdini\\houdini21.0\\script')")
print("    import cfx_assets_ui")
print("    window = cfx_assets_ui.CFXAssetsMainWindow()")
print("    window.show()")

connector.disconnect()





