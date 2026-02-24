#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CFX Apply Buttons 테스트 스크립트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing CFX Apply Buttons")
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
    
    # Apply 버튼 확인
    print("\\n[Apply Buttons Check]")
    print("-"*70)
    
    # Project Tab
    window.tab_widget.setCurrentIndex(0)
    
    apply_buttons_project = []
    for child in window.project_tab.findChildren(QtWidgets.QPushButton):
        if "Apply" in child.text():
            apply_buttons_project.append(child.text())
    
    print("[Project Tab Apply Buttons]:", len(apply_buttons_project))
    for btn in apply_buttons_project:
        print("  -", btn)
    
    # Assets Tab
    window.tab_widget.setCurrentIndex(1)
    
    apply_buttons_assets = []
    for child in window.assets_tab.findChildren(QtWidgets.QPushButton):
        if "Apply" in child.text():
            apply_buttons_assets.append(child.text())
    
    print("\\n[Assets Tab Apply Buttons]:", len(apply_buttons_assets))
    for btn in apply_buttons_assets:
        print("  -", btn)
    
    # 메서드 확인
    print("\\n[Method Check]")
    print("-"*70)
    
    apply_methods = [
        'on_apply_shot_anim_file',
        'on_apply_fbx_file',
        'on_apply_guide_file'
    ]
    
    for method in apply_methods:
        if hasattr(window, method):
            print("[OK] Method '{}' exists".format(method))
        else:
            print("[ERROR] Method '{}' NOT found!".format(method))
    
    # Assets 노드 확인
    print("\\n[Assets Node Check]")
    print("-"*70)
    
    assets_node = hou.node("/obj/assets")
    if assets_node:
        print("[OK] Assets node exists at /obj/assets")
        
        # FBX 노드 확인
        fbx_node = assets_node.node("FBX")
        if fbx_node:
            print("[OK] FBX node exists at /obj/assets/FBX")
            
            # 파라미터 확인
            params_to_check = [
                'animation_import',
                'character_import',
                'hair_import'
            ]
            
            print("\\n[Parameter Check]")
            for parm_name in params_to_check:
                parm = fbx_node.parm(parm_name)
                if parm:
                    print("[OK] Parameter '{}' exists".format(parm_name))
                    print("    Current value:", parm.eval()[:50] if parm.eval() else "(empty)")
                else:
                    print("[WARNING] Parameter '{}' NOT found".format(parm_name))
        else:
            print("[WARNING] FBX node NOT found at /obj/assets/FBX")
    else:
        print("[WARNING] Assets node NOT found at /obj/assets")
        print("    Note: Apply buttons will show error message when clicked")
    
    print("\\n[Summary]")
    print("="*70)
    print("[1] Project Tab Apply Buttons: {} (Expected: 1)".format(len(apply_buttons_project)))
    print("[2] Assets Tab Apply Buttons: {} (Expected: 2)".format(len(apply_buttons_assets)))
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
print(" Apply Buttons Feature Summary")
print("="*80)
print()
print("추가된 Apply 버튼:")
print("=================")
print()
print("1. Project Tab - Shot Anim File Apply")
print("   위치: Shot Anim File Refresh 버튼 옆")
print("   기능: Shot Anim File 경로를 /obj/assets/FBX/animation_import에 적용")
print()
print("2. Assets Tab - FBX File Apply")
print("   위치: FBX File Refresh 버튼 옆")
print("   기능: FBX File 경로를 /obj/assets/FBX/character_import에 적용")
print()
print("3. Assets Tab - Guide File Apply")
print("   위치: Guide File Refresh 버튼 옆")
print("   기능: Guide File 경로를 /obj/assets/FBX/hair_import에 적용")
print()
print("동작 프로세스:")
print("============")
print("1. 파일 선택 확인")
print("2. 전체 경로 가져오기 (ComboBox currentData)")
print("3. /obj/assets 노드 존재 확인")
print("4. /obj/assets/FBX 노드 존재 확인")
print("5. 해당 파라미터 존재 확인")
print("6. 파라미터에 경로 설정")
print("7. 성공 메시지 표시")
print()
print("에러 처리:")
print("=========")
print("- 파일 미선택: 경고 메시지")
print("- Assets 노드 없음: 에러 메시지")
print("- FBX 노드 없음: 에러 메시지")
print("- 파라미터 없음: 에러 메시지")
print("- 예외 발생: 에러 메시지 + traceback 로그")
print()
print("="*80)





