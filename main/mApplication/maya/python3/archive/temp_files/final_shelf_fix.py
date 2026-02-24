#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Final fix for CFX Assets Manager shelf tool
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Final Fix for CFX Assets Manager")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[INFO] Applying complete fix...")
print("-" * 80)

code = """
import hou
import os

# Get the shelf
shelves = hou.shelves.shelves()
shelf = shelves['cinematic2_tool']

# Get current tools
all_tools = list(shelf.tools())

# Remove ALL CFX tools (including numbered ones)
other_tools = [t for t in all_tools if 'cfx_assets_manager' not in t.name()]

print("[INFO] Removing old CFX tools...")
print("      Keeping {} other tools".format(len(other_tools)))
print()

# Create new CFX tool with correct script
cfx_script = '''import sys
script_path = r"T:\\\\scripts\\\\python\\\\application\\\\houdini\\\\houdini21.0\\\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

import cfx_assets_ui
window = cfx_assets_ui.CFXAssetsMainWindow()
window.show()'''

new_cfx_tool = hou.shelves.newTool(
    file_path=None,
    name="cfx_assets_manager",
    label="CFX Assets Manager",
    script=cfx_script,
    language=hou.scriptLanguage.Python,
    icon="MISC_python",
    help_url="",
    help="Launch CFX Assets Manager UI"
)

# Update shelf with other tools + new CFX tool
new_tools = other_tools + [new_cfx_tool]
shelf.setTools(tuple(new_tools))

print("[OK] CFX Assets Manager tool added!")
print("    Total tools: {}".format(len(new_tools)))
print()

# Save to file
shelf_file = os.path.join(hou.homeHoudiniDirectory(), "toolbar", "cinematic2_tool.shelf")

xml = '<?xml version="1.0" encoding="UTF-8"?>\\n<shelfDocument>\\n'
xml += '  <!-- This file contains definitions of shelves, toolbars, and tools. -->\\n\\n'

for tool in new_tools:
    xml += '  <tool name="{}" label="{}" icon="{}">\\n'.format(tool.name(), tool.label(), tool.icon())
    if tool.script():
        xml += '    <script scriptType="python"><![CDATA[{}]]></script>\\n'.format(tool.script())
    xml += '  </tool>\\n\\n'

xml += '</shelfDocument>\\n'

with open(shelf_file, 'w', encoding='utf-8') as f:
    f.write(xml)

print("[OK] Shelf saved to: {}".format(shelf_file))
print("    Size: {} bytes".format(os.path.getsize(shelf_file)))
print()

# Verify
print("="*70)
print(" Verification")
print("="*70)
print()

for tool in shelf.tools():
    if tool.name() == "cfx_assets_manager":
        script = tool.script()
        print("[OK] CFX Assets Manager found!")
        print("    Name: {}".format(tool.name()))
        print("    Label: {}".format(tool.label()))
        print("    Script: {} chars".format(len(script)))
        print()
        print("Script preview:")
        print(script[:150])
        print()
        print("="*70)
        print(" [SUCCESS] Tool is ready to use!")
        print("="*70)
        print()
        print("Click 'CFX Assets Manager' button in cinematic2_tool shelf")
        break
else:
    print("[ERROR] CFX tool not found after update")
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Final fix applied!")
print("="*80)

connector.disconnect()





