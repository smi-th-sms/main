#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CFX Assets UI 테스트 스크립트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing CFX Assets UI")
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
    
    # 위젯 확인
    print("\\n[UI Widgets]")
    print("-"*70)
    print("[OK] project_base_path_edit:", window.project_base_path_edit.text())
    print("[OK] project_name_combo:", window.project_name_combo.count(), "items")
    print("[OK] seq_name_combo:", window.seq_name_combo.count(), "items")
    print("[OK] shot_name_combo:", window.shot_name_combo.count(), "items")
    print("[OK] full_path_label:", window.full_path_label.text())
    
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
print(" Summary")
print("="*80)
print()
print("CFX Assets UI 업데이트 완료!")
print()
print("변경 사항:")
print("=========")
print("1. cosmos_assets_ui.py → cfx_assets_ui.py")
print("2. launch_cosmos_ui.py → launch_cfx_ui.py")
print("3. COSMOS_UI_GUIDE.txt → CFX_UI_GUIDE.txt")
print()
print("새로운 실행 방법:")
print("===============")
print("import sys")
print('sys.path.append(r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script")')
print("import launch_cfx_ui")
print()
print("또는:")
print("====")
print("import cfx_assets_ui")
print("cfx_assets_ui.launch()")
print()
print("="*80)





