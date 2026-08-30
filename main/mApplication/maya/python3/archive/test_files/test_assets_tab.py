#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CFX Assets Tab 테스트 스크립트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing CFX Assets Tab")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Launching CFX UI...")
print("-" * 80)

# CFX UI 실행
code = """
import sys
script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

# CFX UI 임포트 및 실행
try:
    import cfx_assets_ui
    import importlib
    
    # 리로드
    importlib.reload(cfx_assets_ui)
    
    # 윈도우 실행
    window = cfx_assets_ui.launch()
    
    print("[Launching UI]")
    print("="*70)
    print("[OK] UI launched")
    print("Window title:", window.windowTitle())
    
    # Assets Tab 위젯 확인
    print("\\n[Assets Tab Widgets]")
    print("-"*70)
    print("[OK] assets_subpath_edit:", window.assets_subpath_edit.text())
    print("[OK] assets_name_combo:", window.assets_name_combo.count(), "items")
    print("[OK] assets_fullpath_label:", window.assets_fullpath_label.text())
    print("[OK] fbx_subpath_edit:", window.fbx_subpath_edit.text())
    print("[OK] fbx_file_combo:", window.fbx_file_combo.count(), "items")
    print("[OK] guide_subpath_edit:", window.guide_subpath_edit.text())
    print("[OK] guide_file_combo:", window.guide_file_combo.count(), "items")
    print("[OK] default_hda_edit:", window.default_hda_edit.text())
    
    # Assets Tab으로 전환
    window.tab_widget.setCurrentIndex(1)  # Assets tab
    print("\\n[OK] Switched to Assets Tab")
    
except Exception as e:
    print("[ERROR]", str(e))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Testing completed!")
print("="*80)

connector.disconnect()

print("\n" + "="*80)
print(" Assets Tab Update Summary")
print("="*80)
print()
print("새로운 필드들:")
print("=============")
print("1. Assets Subpath (LineEdit)")
print("   - Default: 'assets/Character'")
print()
print("2. Assets Name (ComboBox + Refresh)")
print("   - Project 경로 + Assets Subpath의 폴더 목록")
print()
print("3. Assets FullPath (Label)")
print("   - Assets Name 경로 + 'Sim/wip/houdini'")
print()
print("4. FBX Subpath (LineEdit)")
print("   - Default: 'RIG/wip/maya/fbx/'")
print()
print("5. FBX File (ComboBox + Refresh)")
print("   - Assets Name 경로 + FBX Subpath의 .fbx 파일 목록")
print()
print("6. Guide Subpath (LineEdit)")
print("   - Default: 'RIG/wip/maya/guide/'")
print()
print("7. Guide File (ComboBox + Refresh)")
print("   - Assets Name 경로 + Guide Subpath의 파일 목록")
print()
print("8. Default HDA (LineEdit + Browse)")
print("   - Default: 'Z:/inhouse/Houdini/otls'")
print()
print("Auto Setup 버튼 기능:")
print("===================")
print("1. Assets FullPath + 'asset' 경로에서 Assets Name.hda 찾기")
print("2. 있으면 팝업으로 선택 물어보기")
print("3. Yes → Assets Name.hda 로드")
print("4. No → Default HDA 로드")
print("5. 없으면 → Default HDA 로드")
print()
print("="*80)





