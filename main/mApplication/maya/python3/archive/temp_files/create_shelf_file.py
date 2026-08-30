#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Create/Update cinematic2_tool.shelf file with CFX Assets Manager tool
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Creating/Updating cinematic2_tool.shelf File")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Getting shelf file path...")
print("-" * 80)

code = """
import hou
import os

try:
    houdini_prefs = hou.homeHoudiniDirectory()
    toolbar_path = os.path.join(houdini_prefs, "toolbar")
    shelf_file = os.path.join(toolbar_path, "cinematic2_tool.shelf")
    
    print("[INFO] Houdini prefs: {}".format(houdini_prefs))
    print("[INFO] Toolbar path: {}".format(toolbar_path))
    print("[INFO] Shelf file: {}".format(shelf_file))
    print()
    
    # Check if file exists
    if os.path.exists(shelf_file):
        print("[INFO] Shelf file exists")
        size = os.path.getsize(shelf_file)
        print("      Size: {} bytes".format(size))
    else:
        print("[INFO] Shelf file does not exist - will be created")
    
    # Return path for external use
    print()
    print("SHELF_PATH={}".format(shelf_file))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    output = result.get("output", "")
    print(output)
    
    # Extract shelf path
    shelf_path = None
    for line in output.split('\n'):
        if line.startswith("SHELF_PATH="):
            shelf_path = line.split("=", 1)[1].strip()
            break

print("\n[2] Reading existing shelf file (if exists)...")
print("-" * 80)

code = """
import hou
import os

try:
    houdini_prefs = hou.homeHoudiniDirectory()
    shelf_file = os.path.join(houdini_prefs, "toolbar", "cinematic2_tool.shelf")
    
    if os.path.exists(shelf_file):
        with open(shelf_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("[OK] Read existing shelf file")
        print("    Lines: {}".format(len(content.split('\\n'))))
        
        # Check if cfx_assets_manager already exists
        if 'cfx_assets_manager' in content:
            print("[WARNING] 'cfx_assets_manager' tool already exists in shelf")
            print("           Will replace it")
        else:
            print("[INFO] 'cfx_assets_manager' not found - will add it")
    else:
        print("[INFO] No existing shelf file - will create new one")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[3] Creating new shelf XML content...")
print("-" * 80)

# CFX Assets Manager shelf XML
shelf_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<shelfDocument>
  <!-- This file contains definitions of shelves, toolbars, and tools.
 It should not be hand-edited when it is being used by the application.
 Note, that two definitions of the same element are not allowed in
 a single file. -->

  <tool name="blast_split" label="blast split" icon="PLASMA_App">
    <script scriptType="python"><![CDATA[import sys
sys.path.append(r'T:\\scripts\\python\\application\\houdini\\houdini20.0')

from houinhouse.handlers import blast_split

blast_split.run()]]></script>
  </tool>

  <tool name="cache_save" label="cache save" icon="PLASMA_App">
    <script scriptType="python"><![CDATA[import sys
sys.path.append(r'T:\\scripts\\python\\application\\houdini\\houdini20.0')

from houinhouse.handlers import cache_save

cache_save.run()]]></script>
  </tool>

  <tool name="cfx_assets_manager" label="CFX Assets Manager" icon="MISC_python">
    <helpText><![CDATA["""Launch CFX Assets Manager UI for managing cloth parts and assets."""]]></helpText>
    <script scriptType="python"><![CDATA[import sys

# Add script path
script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

# Import and show UI
try:
    import cfx_assets_ui
    
    # Create and show window
    window = cfx_assets_ui.CFXAssetsMainWindow()
    window.show()
    
except Exception as e:
    import hou
    hou.ui.displayMessage(
        "Error launching CFX Assets Manager:\\n\\n{}".format(str(e)),
        severity=hou.severityType.Error
    )
    import traceback
    traceback.print_exc()]]></script>
  </tool>
</shelfDocument>
'''

print("[OK] Shelf XML content prepared")
print(f"    Total length: {len(shelf_xml)} characters")

print("\n[4] Writing shelf file...")
print("-" * 80)

code = f'''
import hou
import os

try:
    houdini_prefs = hou.homeHoudiniDirectory()
    toolbar_path = os.path.join(houdini_prefs, "toolbar")
    shelf_file = os.path.join(toolbar_path, "cinematic2_tool.shelf")
    
    # Ensure toolbar directory exists
    if not os.path.exists(toolbar_path):
        os.makedirs(toolbar_path)
        print("[INFO] Created toolbar directory")
    
    # Shelf XML content
    shelf_content = """{shelf_xml}"""
    
    # Write file
    with open(shelf_file, 'w', encoding='utf-8') as f:
        f.write(shelf_content)
    
    print("[OK] Shelf file written successfully")
    print("    Path: {{}}".format(shelf_file))
    
    # Verify
    if os.path.exists(shelf_file):
        size = os.path.getsize(shelf_file)
        print("    Size: {{}} bytes".format(size))
    
    print()
    print("="*70)
    print(" [SUCCESS] Shelf file created/updated!")
    print("="*70)

except Exception as e:
    print("[ERROR] {{}}".format(str(e)))
    import traceback
    traceback.print_exc()
'''

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[5] Reloading shelf in Houdini...")
print("-" * 80)

code = """
import hou

try:
    # Reload shelves
    hou.shelves.loadShelvesFromFiles()
    
    print("[OK] Shelves reloaded")
    print()
    
    # Verify
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
            print("="*70)
            print(" [VERIFIED] CFX Assets Manager Tool Loaded")
            print("="*70)
            print()
            print("Tool: {}".format(cfx_tool.label()))
            print("Icon: {}".format(cfx_tool.icon()))
            print()
            print("All tools in cinematic2_tool shelf:")
            for tool in tools:
                print("  - {}".format(tool.label()))
        else:
            print("[WARNING] CFX Assets Manager tool not found after reload")
    else:
        print("[WARNING] cinematic2_tool shelf not found")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Shelf tool registration finished!")
print("="*80)
print()
print("✅ CFX Assets Manager added to cinematic2_tool shelf")
print()
print("To use:")
print("  1. Look for 'cinematic2_tool' shelf in Houdini")
print("  2. Click 'CFX Assets Manager' button (Python icon)")
print("  3. UI window will open")
print()
print("If you don't see it:")
print("  - Right-click shelf area → Shelves → cinematic2_tool")
print("  - Or restart Houdini")

connector.disconnect()





