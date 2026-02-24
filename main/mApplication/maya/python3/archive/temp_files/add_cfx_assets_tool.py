#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Add CFX Assets Manager tool to cinematic2_tool shelf
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Adding CFX Assets Manager to cinematic2_tool Shelf")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Creating CFX Assets Manager shelf tool...")
print("-" * 80)

code = """
import hou
import os

try:
    # cinematic2_tool shelf 가져오기
    shelves = hou.shelves.shelves()
    
    if 'cinematic2_tool' not in shelves:
        print("[ERROR] cinematic2_tool shelf not found")
        print("Available shelves: {}".format(list(shelves.keys())[:10]))
    else:
        shelf = shelves['cinematic2_tool']
        print("[OK] Found cinematic2_tool shelf")
        print("    Label: {}".format(shelf.label()))
        print()
        
        # 기존 tools 확인
        existing_tools = shelf.tools()
        print("Current tools in shelf: {}".format(len(existing_tools)))
        for tool in existing_tools:
            print("  - {}".format(tool.name()))
        print()
        
        # CFX Assets Manager tool 생성
        tool_name = "cfx_assets_manager"
        
        # 이미 존재하는지 확인
        tool_exists = any(t.name() == tool_name for t in existing_tools)
        
        if tool_exists:
            print("[WARNING] Tool '{}' already exists. Will update it.".format(tool_name))
        else:
            print("[INFO] Creating new tool '{}'".format(tool_name))
        
        # Tool script - CFX Assets Manager UI 실행
        tool_script = '''import sys

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
    traceback.print_exc()
'''
        
        # Tool 생성 (Houdini API 사용)
        # hou.shelves.newTool() 사용
        try:
            # Tool definition
            tool = hou.shelves.newTool(
                file_path=None,  # Don't save to file yet
                name=tool_name,
                label="CFX Assets Manager",
                script=tool_script,
                language=hou.scriptLanguage.Python,
                icon="MISC_python",  # Python icon
                help_url="",
                help="Launch CFX Assets Manager UI for managing cloth parts and assets."
            )
            
            print("[OK] Created tool object")
            print()
            
            # Tool을 shelf에 추가
            shelf.setTools(shelf.tools() + (tool,))
            
            print("="*70)
            print(" [SUCCESS] CFX Assets Manager added to shelf!")
            print("="*70)
            print()
            print("Tool Details:")
            print("  Name: {}".format(tool.name()))
            print("  Label: {}".format(tool.label()))
            print("  Icon: {}".format(tool.icon()))
            print()
            print("To save permanently:")
            print("  1. Right-click on shelf")
            print("  2. Choose 'Save Shelf...'")
            print("  3. Or use: shelf.saveToFile()")
            
        except Exception as e:
            print("[ERROR] Failed to create tool: {}".format(str(e)))
            import traceback
            traceback.print_exc()

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
    if 'cinematic2_tool' in shelves:
        shelf = shelves['cinematic2_tool']
        
        # Shelf 파일 경로
        houdini_prefs = hou.homeHoudiniDirectory()
        toolbar_path = os.path.join(houdini_prefs, "toolbar")
        
        # cinematic2_tool.shelf 파일로 저장
        shelf_file = os.path.join(toolbar_path, "cinematic2_tool.shelf")
        
        print("[INFO] Saving shelf to: {}".format(shelf_file))
        
        try:
            shelf.saveToFile(shelf_file)
            print("[OK] Shelf saved successfully")
            
            # 파일 크기 확인
            if os.path.exists(shelf_file):
                size = os.path.getsize(shelf_file)
                print("    File size: {} bytes".format(size))
        except Exception as e:
            print("[WARNING] Could not save shelf file: {}".format(str(e)))
            print("    You may need to save manually")
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

print("\n[3] Verifying tool addition...")
print("-" * 80)

code = """
import hou

try:
    shelves = hou.shelves.shelves()
    if 'cinematic2_tool' in shelves:
        shelf = shelves['cinematic2_tool']
        tools = shelf.tools()
        
        # CFX Assets Manager tool 찾기
        cfx_tool = None
        for tool in tools:
            if tool.name() == "cfx_assets_manager":
                cfx_tool = tool
                break
        
        if cfx_tool:
            print("="*70)
            print(" [VERIFIED] CFX Assets Manager Tool")
            print("="*70)
            print()
            print("Tool Name: {}".format(cfx_tool.name()))
            print("Tool Label: {}".format(cfx_tool.label()))
            print("Icon: {}".format(cfx_tool.icon()))
            print("Language: {}".format(cfx_tool.scriptLanguage()))
            print()
            print("To use:")
            print("  1. Look for 'cinematic2_tool' shelf in Houdini")
            print("  2. Click 'CFX Assets Manager' button")
            print("  3. UI window will open")
        else:
            print("[WARNING] CFX Assets Manager tool not found in shelf")
            print("Current tools:")
            for tool in tools:
                print("  - {}".format(tool.name()))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Tool added to shelf!")
print("="*80)
print()
print("NEXT STEPS:")
print("  1. Look for 'cinematic2_tool' shelf in Houdini UI")
print("  2. Find 'CFX Assets Manager' button (Python icon)")
print("  3. Click it to launch the UI")
print()
print("If shelf doesn't show the tool:")
print("  - Right-click shelf area → Shelves → cinematic2_tool")
print("  - Or restart Houdini to reload shelves")

connector.disconnect()





