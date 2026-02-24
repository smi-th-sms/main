#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cinematic2 shelf 위치 확인
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Finding cinematic2 Shelf")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Checking shelf locations...")
print("-" * 80)

code = """
import hou
import os

try:
    # Houdini 설정 경로들
    houdini_user_prefs = hou.homeHoudiniDirectory()
    print("[INFO] Houdini User Preferences: {}".format(houdini_user_prefs))
    print()
    
    # Shelf 파일들 찾기
    toolbar_path = os.path.join(houdini_user_prefs, "toolbar")
    print("[INFO] Toolbar path: {}".format(toolbar_path))
    print()
    
    if os.path.exists(toolbar_path):
        print("[OK] Toolbar directory exists")
        print()
        
        # 모든 shelf 파일 나열
        shelf_files = [f for f in os.listdir(toolbar_path) if f.endswith('.shelf')]
        print("Shelf files found: {}".format(len(shelf_files)))
        for shelf_file in shelf_files:
            print("  - {}".format(shelf_file))
        print()
        
        # cinematic2.shelf 확인
        cinematic2_shelf = os.path.join(toolbar_path, "cinematic2.shelf")
        if os.path.exists(cinematic2_shelf):
            print("[OK] cinematic2.shelf found!")
            print("    Path: {}".format(cinematic2_shelf))
            print()
            
            # 파일 크기
            file_size = os.path.getsize(cinematic2_shelf)
            print("    Size: {} bytes".format(file_size))
        else:
            print("[WARNING] cinematic2.shelf not found")
            print("Available shelf files:")
            for shelf_file in shelf_files:
                print("  - {}".format(shelf_file))
    else:
        print("[ERROR] Toolbar directory does not exist")
    
    print()
    print("="*70)
    print(" Shelf Tools in cinematic2")
    print("="*70)
    print()
    
    # 현재 로드된 shelves 확인
    shelves = hou.shelves.shelves()
    if 'cinematic2' in shelves:
        shelf = shelves['cinematic2']
        print("[OK] cinematic2 shelf is loaded")
        print()
        print("Label: {}".format(shelf.label()))
        print("Name: {}".format(shelf.name()))
        print()
        
        # Tools 나열
        tools = shelf.tools()
        print("Number of tools: {}".format(len(tools)))
        print()
        print("Existing tools:")
        for tool in tools:
            print("  - {} ({})".format(tool.label(), tool.name()))
    else:
        print("[WARNING] cinematic2 shelf not loaded")
        print()
        print("Available shelves:")
        for shelf_name in sorted(shelves.keys()):
            print("  - {}".format(shelf_name))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Shelf check finished")
print("="*80)

connector.disconnect()





