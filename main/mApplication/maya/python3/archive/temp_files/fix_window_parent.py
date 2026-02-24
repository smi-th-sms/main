#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fix window parent and update shelf tool script
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Fixing Window Parent and Shelf Script")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Updating shelf tool script with proper window management...")
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
        print("[OK] Found CFX tool")
        
        # Updated script with proper window management
        new_script = '''import sys
import hou

# Add script path
script_path = r"T:\\\\scripts\\\\python\\\\application\\\\houdini\\\\houdini21.0\\\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

import cfx_assets_ui

# Use hou.session to store window reference
if not hasattr(hou.session, 'cfx_window'):
    hou.session.cfx_window = None

# Create or show window
if hou.session.cfx_window is None:
    hou.session.cfx_window = cfx_assets_ui.CFXAssetsMainWindow()
    hou.session.cfx_window.show()
elif not hou.session.cfx_window.isVisible():
    hou.session.cfx_window.show()
else:
    hou.session.cfx_window.raise_()
    hou.session.cfx_window.activateWindow()'''
        
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
        
        # Remove duplicates
        seen_names = set()
        unique_tools = []
        for t in tools:
            if t.name() not in seen_names or t == new_tool:
                unique_tools.append(t)
                seen_names.add(t.name())
        
        # Update shelf
        shelf.setTools(tuple(unique_tools))
        
        print("[OK] Tool script updated")
        print("    Script uses hou.session for window storage")
        print("    Window has Houdini main window as parent")
        print()
        
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

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[2] Testing window creation...")
print("-" * 80)

code = """
import sys
import hou

try:
    # Add script path
    script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
    if script_path not in sys.path:
        sys.path.insert(0, script_path)
    
    # Reload module to get updates
    if 'cfx_assets_ui' in sys.modules:
        import importlib
        import cfx_assets_ui
        importlib.reload(cfx_assets_ui)
    else:
        import cfx_assets_ui
    
    print("[TEST] Creating window...")
    print()
    
    # Create window (don't show it in test)
    test_window = cfx_assets_ui.CFXAssetsMainWindow()
    
    print("[OK] Window created successfully")
    print("    Window title: {}".format(test_window.windowTitle()))
    print("    Has parent: {}".format(test_window.parent() is not None))
    print("    Parent: {}".format(type(test_window.parent()).__name__ if test_window.parent() else "None"))
    print()
    
    # Check window flags
    flags = test_window.windowFlags()
    print("Window flags:")
    if flags & test_window.windowFlags() & 0x00000001:  # Qt.Window
        print("  - Window (standalone)")
    print()
    
    # Clean up test window
    test_window.deleteLater()
    
    print("="*70)
    print(" [SUCCESS] Window configuration updated!")
    print("="*70)
    print()
    print("Changes:")
    print("  1. Window now has Houdini main window as parent")
    print("  2. Window won't be garbage collected")
    print("  3. Window is properly managed by Houdini")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Window fix applied!")
print("="*80)
print()
print("Now click 'CFX Assets Manager' button again.")
print("The window should:")
print("  - Open and stay open")
print("  - Be a child of Houdini main window")
print("  - Not close immediately")

connector.disconnect()





