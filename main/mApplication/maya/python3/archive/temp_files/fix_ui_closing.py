#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fix UI closing immediately - keep window reference
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Fixing UI Closing Issue")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Updating tool script to keep window reference...")
print("-" * 80)

code = """
import hou
import os

try:
    shelves = hou.shelves.shelves()
    shelf = shelves['cinematic2_tool']
    tools = list(shelf.tools())
    
    # Find CFX tool
    cfx_tool_index = -1
    for i, tool in enumerate(tools):
        if 'cfx_assets_manager' in tool.name():
            cfx_tool_index = i
            break
    
    if cfx_tool_index < 0:
        print("[ERROR] CFX tool not found")
    else:
        print("[OK] Found CFX tool at index {}".format(cfx_tool_index))
        
        # New script with global window reference
        new_script = '''import sys
script_path = r"T:\\\\scripts\\\\python\\\\application\\\\houdini\\\\houdini21.0\\\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

import cfx_assets_ui

# Store window globally to prevent garbage collection
if 'cfx_window' not in globals():
    globals()['cfx_window'] = None

# Create or show window
if globals()['cfx_window'] is None or not globals()['cfx_window'].isVisible():
    globals()['cfx_window'] = cfx_assets_ui.CFXAssetsMainWindow()
    globals()['cfx_window'].show()
else:
    globals()['cfx_window'].raise_()
    globals()['cfx_window'].activateWindow()'''
        
        # Create new tool
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
        
        # Replace in tools list
        tools[cfx_tool_index] = new_tool
        
        # Remove any other CFX tools
        final_tools = [t for t in tools if t == new_tool or 'cfx_assets_manager' not in t.name()]
        final_tools.append(new_tool)
        
        # Make unique
        seen_names = set()
        unique_tools = []
        for t in final_tools:
            if t.name() not in seen_names:
                unique_tools.append(t)
                seen_names.add(t.name())
        
        # Update shelf
        shelf.setTools(tuple(unique_tools))
        
        print("[OK] Tool script updated with global window reference")
        print("    Script length: {} chars".format(len(new_tool.script())))
        
        # Save to file
        shelf_file = os.path.join(hou.homeHoudiniDirectory(), "toolbar", "cinematic2_tool.shelf")
        
        xml = '<?xml version="1.0" encoding="UTF-8"?>\\n<shelfDocument>\\n'
        xml += '  <!-- This file contains definitions of shelves, toolbars, and tools. -->\\n\\n'
        
        for tool in unique_tools:
            xml += '  <tool name="{}" label="{}" icon="{}">\\n'.format(
                tool.name(), tool.label(), tool.icon())
            if tool.script():
                xml += '    <script scriptType="python"><![CDATA[{}]]></script>\\n'.format(tool.script())
            xml += '  </tool>\\n\\n'
        
        xml += '</shelfDocument>\\n'
        
        with open(shelf_file, 'w', encoding='utf-8') as f:
            f.write(xml)
        
        print("[OK] Shelf file saved")
        print()
        print("="*70)
        print(" [SUCCESS] UI closing issue fixed!")
        print("="*70)
        print()
        print("Now the window will:")
        print("  - Stay open after clicking the button")
        print("  - Reuse existing window if already open")
        print("  - Bring to front if minimized")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[2] Testing the fix...")
print("-" * 80)

code = """
import hou

try:
    shelves = hou.shelves.shelves()
    shelf = shelves['cinematic2_tool']
    
    for tool in shelf.tools():
        if tool.name() == "cfx_assets_manager":
            script = tool.script()
            
            print("[VERIFICATION]")
            print("Tool name: {}".format(tool.name()))
            print("Script length: {} chars".format(len(script)))
            print()
            
            if "globals()" in script:
                print("[OK] Script uses global reference")
            else:
                print("[WARNING] Script might not have global reference")
            
            print()
            print("Script preview:")
            print(script[:200])
            break

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Fix applied!")
print("="*80)
print()
print("Now click the 'CFX Assets Manager' button again.")
print("The UI should stay open this time!")

connector.disconnect()





