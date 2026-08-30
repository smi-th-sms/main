#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CFX UI Cleanup 테스트 스크립트
Deform Tab 제거 및 Settings Tab 정리
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing CFX UI Cleanup")
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
    
    # 탭 개수 확인
    print("\\n[Tab Count Check]")
    print("-"*70)
    tab_count = window.tab_widget.count()
    print("Total tabs:", tab_count)
    print("Expected: 3 (Project, Assets, Settings)")
    
    # 각 탭 이름 확인
    print("\\n[Tab Names]")
    print("-"*70)
    for i in range(tab_count):
        tab_name = window.tab_widget.tabText(i)
        print("Tab {}: {}".format(i, tab_name))
    
    # Settings Tab으로 전환
    print("\\n[Settings Tab Check]")
    print("-"*70)
    window.tab_widget.setCurrentIndex(tab_count - 1)  # Last tab
    
    # Settings Tab 내용 확인
    settings_tab = window.tab_widget.currentWidget()
    
    # GroupBox 확인
    group_boxes = settings_tab.findChildren(QtWidgets.QGroupBox)
    print("GroupBoxes in Settings:")
    for gb in group_boxes:
        print("  -", gb.title())
    
    expected_groups = ["Script Paths", "About"]
    removed_group = "Node Paths"
    
    group_titles = [gb.title() for gb in group_boxes]
    
    if removed_group in group_titles:
        print("\\n[ERROR] '{}' still exists!".format(removed_group))
    else:
        print("\\n[OK] '{}' successfully removed".format(removed_group))
    
    # Deform Tab 확인
    print("\\n[Deform Tab Check]")
    print("-"*70)
    deform_found = False
    for i in range(tab_count):
        if "Deform" in window.tab_widget.tabText(i):
            deform_found = True
            break
    
    if deform_found:
        print("[ERROR] Deform Tab still exists!")
    else:
        print("[OK] Deform Tab successfully removed")
    
    # 메서드 확인
    print("\\n[Method Check]")
    print("-"*70)
    removed_methods = [
        'create_deform_tab',
        'on_sync_parts_deform',
        'refresh_parts_deform_list',
        'log_deform'
    ]
    
    for method in removed_methods:
        if hasattr(window, method):
            print("[ERROR] Method '{}' still exists!".format(method))
        else:
            print("[OK] Method '{}' removed".format(method))
    
    print("\\n[Summary]")
    print("="*70)
    print("Tab Count: {} (Expected: 3)".format(tab_count))
    print("Deform Tab: {}".format("REMOVED" if not deform_found else "STILL EXISTS"))
    print("Node Paths: {}".format("REMOVED" if removed_group not in group_titles else "STILL EXISTS"))
    
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
print(" UI Cleanup Summary")
print("="*80)
print()
print("제거된 기능:")
print("===========")
print("1. Deform Tab (전체)")
print("   - Parts_Deform 동기화 UI")
print("   - 노드 목록 표시")
print("   - Sync 버튼")
print()
print("2. Settings Tab의 Node Paths")
print("   - Assets Node 경로 설정")
print()
print("제거된 메서드:")
print("=============")
print("- create_deform_tab()")
print("- on_sync_parts_deform()")
print("- refresh_parts_deform_list()")
print("- log_deform()")
print()
print("남은 탭:")
print("=======")
print("1. Project Tab")
print("   - 프로젝트, 시퀀스, 샷 경로 관리")
print()
print("2. Assets Tab")
print("   - Assets 설정")
print("   - FBX/Guide 파일 선택")
print("   - HDA Install & Create")
print()
print("3. Settings Tab")
print("   - Script Paths (정보)")
print("   - About (버전 정보)")
print()
print("이유:")
print("====")
print("- Deform 기능은 HDA 내부에서 구현 예정")
print("- Node Paths는 더 이상 필요 없음")
print()
print("="*80)





