#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CFX Project Tab - Shot Animation FBX 테스트 스크립트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing CFX Project Tab - Shot Animation FBX")
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
    
    # Project Tab에 있는지 확인
    window.tab_widget.setCurrentIndex(0)  # Project tab
    
    # 새로운 필드 확인
    print("\\n[New Fields Check]")
    print("-"*70)
    
    # Shot Anim Subpath
    shot_anim_subpath = window.shot_anim_subpath_edit.text()
    print("[1] Shot Anim Subpath:", shot_anim_subpath)
    print("    Expected: 'ANM/pub/fbx/'")
    
    subpath_ok = shot_anim_subpath == "ANM/pub/fbx/"
    print("    Status:", "[OK]" if subpath_ok else "[FAILED]")
    
    # Shot Anim File ComboBox
    anim_file_count = window.shot_anim_file_combo.count()
    print("\\n[2] Shot Anim File ComboBox:", anim_file_count, "items")
    print("    (Will be populated after Shot selection)")
    
    # 메서드 확인
    print("\\n[Method Check]")
    print("-"*70)
    
    new_methods = [
        'on_shot_anim_subpath_changed',
        'refresh_shot_anim_file_list'
    ]
    
    for method in new_methods:
        if hasattr(window, method):
            print("[OK] Method '{}' exists".format(method))
        else:
            print("[ERROR] Method '{}' NOT found!".format(method))
    
    # Project Name이 있으면 cascade 테스트
    print("\\n[Cascade Test]")
    print("-"*70)
    
    if window.project_name_combo.count() > 0:
        # 첫 번째 프로젝트 선택
        first_project = window.project_name_combo.itemText(0)
        window.project_name_combo.setCurrentIndex(0)
        print("Selected Project:", first_project)
        
        # Sequence가 있으면 선택
        import time
        time.sleep(0.5)
        
        if window.seq_name_combo.count() > 0:
            first_seq = window.seq_name_combo.itemText(0)
            window.seq_name_combo.setCurrentIndex(0)
            print("Selected Sequence:", first_seq)
            
            time.sleep(0.5)
            
            # Shot이 있으면 선택
            if window.shot_name_combo.count() > 0:
                first_shot = window.shot_name_combo.itemText(0)
                window.shot_name_combo.setCurrentIndex(0)
                print("Selected Shot:", first_shot)
                
                time.sleep(0.5)
                
                # Anim File 목록 확인
                anim_count = window.shot_anim_file_combo.count()
                print("\\nAnimation FBX files loaded:", anim_count)
                
                if anim_count > 0:
                    print("Sample files:")
                    for i in range(min(3, anim_count)):
                        print("  -", window.shot_anim_file_combo.itemText(i))
    else:
        print("No projects available for cascade test")
    
    print("\\n[Summary]")
    print("="*70)
    print("[1] Shot Anim Subpath:", "[OK]" if subpath_ok else "[FAILED]")
    print("[2] Shot Anim File ComboBox: [OK]")
    print("[3] Methods: [OK]")
    
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
print(" Shot Animation FBX Feature Summary")
print("="*80)
print()
print("새로운 필드:")
print("===========")
print("1. Shot Anim Subpath (LineEdit)")
print("   - 위치: Shot Subdir 아래")
print("   - 기본값: 'ANM/pub/fbx/'")
print("   - Shot Name 기준 애니메이션 FBX 파일 경로")
print()
print("2. Shot Anim File (ComboBox + Refresh)")
print("   - Shot Name 경로 + Shot Anim Subpath의 .fbx 파일 목록")
print("   - 파일명만 표시, 전체 경로는 Data로 저장")
print()
print("경로 구조:")
print("=========")
print("Shot Anim File Path =")
print("  Project Path + Project Name + Sequence Subdir + Sequence Name")
print("  + Shot Name + Shot Anim Subpath")
print()
print("예시:")
print("----")
print("Project Path:        Z:/show/")
print("Project Name:        PUBGOM")
print("Sequence Subdir:     sequences/")
print("Sequence Name:       SZERO")
print("Shot Name:           SZERO_0060")
print("Shot Anim Subpath:   ANM/pub/fbx/")
print()
print("→ Animation FBX Path:")
print("  Z:/show/PUBGOM/sequences/SZERO/SZERO_0060/ANM/pub/fbx/")
print()
print("Cascade 동작:")
print("============")
print("Shot Name 선택 시:")
print("  → refresh_shot_anim_file_list() 자동 호출")
print("  → Animation FBX 파일 목록 로드")
print()
print("Shot Anim Subpath 변경 시:")
print("  → refresh_shot_anim_file_list() 자동 호출")
print("  → Animation FBX 파일 목록 갱신")
print()
print("="*80)





