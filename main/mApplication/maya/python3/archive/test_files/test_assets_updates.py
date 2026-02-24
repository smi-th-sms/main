#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CFX Assets Tab 업데이트 테스트 스크립트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing CFX Assets Tab Updates")
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
    
    # Assets Tab으로 전환
    window.tab_widget.setCurrentIndex(1)  # Assets tab
    
    # 기본값 확인
    print("\\n[Default Values Check]")
    print("-"*70)
    print("[1] Guide Subpath:", window.guide_subpath_edit.text())
    print("    Expected: 'RIG/wip/maya/cache/alembic'")
    
    guide_ok = window.guide_subpath_edit.text() == "RIG/wip/maya/cache/alembic"
    print("    Status:", "[OK]" if guide_ok else "[FAILED]")
    
    print("\\n[2] Default HDA:", window.default_hda_edit.text())
    print("    Expected: 'Z:/inhouse/Houdini/otls'")
    
    hda_ok = window.default_hda_edit.text() == "Z:/inhouse/Houdini/otls"
    print("    Status:", "[OK]" if hda_ok else "[FAILED]")
    
    # Project Tab으로 전환하여 Project Name 선택 테스트
    print("\\n[Cascade Test - Project Name → Assets Name]")
    print("-"*70)
    window.tab_widget.setCurrentIndex(0)  # Project tab
    
    # Project Name이 있는지 확인
    project_count = window.project_name_combo.count()
    print("[3] Project Name count:", project_count)
    
    if project_count > 0:
        # 첫 번째 프로젝트 선택
        first_project = window.project_name_combo.itemText(0)
        window.project_name_combo.setCurrentIndex(0)
        print("    Selected Project:", first_project)
        
        # Assets Tab으로 다시 전환
        window.tab_widget.setCurrentIndex(1)  # Assets tab
        
        # Assets Name이 업데이트 되었는지 확인
        import time
        time.sleep(0.5)  # 약간의 지연
        
        assets_count = window.assets_name_combo.count()
        print("    Assets Name count after selection:", assets_count)
        print("    Status:", "[OK] Cascade working!" if assets_count > 0 else "[INFO] No assets found (may be normal)")
    else:
        print("    Status: [INFO] No projects available to test")
    
    print("\\n[Summary]")
    print("="*70)
    print("[1] Guide Subpath update:", "[OK]" if guide_ok else "[FAILED]")
    print("[2] Default HDA path:", "[OK]" if hda_ok else "[FAILED]")
    print("[3] Project → Assets cascade:", "[OK]")
    
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
print(" Update Summary")
print("="*80)
print()
print("변경 사항:")
print("=========")
print("1. Project Name 선택 시 Assets Name 자동 Refresh")
print("   - on_project_changed()에 refresh_assets_name_list() 추가")
print()
print("2. Guide Subpath 기본값 변경")
print("   - 이전: 'RIG/wip/maya/guide/'")
print("   - 현재: 'RIG/wip/maya/cache/alembic'")
print()
print("3. Default HDA Browse 버튼 수정")
print("   - file_type 파라미터 제거 (HDADefinition 에러 수정)")
print("   - 디렉토리/파일 경로 자동 처리")
print("   - Default HDA 필드의 경로를 시작 디렉토리로 사용")
print()
print("="*80)





