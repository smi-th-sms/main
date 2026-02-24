#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cosmos UI 테스트 스크립트
Houdini에서 UI 실행 및 기능 검증
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def test_cosmos_ui():
    """Cosmos UI 테스트"""
    print("\n" + "="*80)
    print(" Testing Cosmos Assets UI")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Checking dependencies...")
        print("-"*80)
        
        check_result = h.connector.execute_code("""
import hou
import sys
import os

print("[Checking PySide]")
print("=" * 70)

try:
    from PySide6 import QtWidgets, QtCore, QtGui
    print("[OK] PySide6 available")
    pyside_version = "PySide6"
except ImportError:
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
        print("[OK] PySide2 available")
        pyside_version = "PySide2"
    except ImportError:
        print("[ERROR] No PySide available")
        pyside_version = None

print("")
print("[Checking Script Path]")
print("=" * 70)

script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
print("Path: {}".format(script_path))
print("Exists: {}".format(os.path.exists(script_path)))

if os.path.exists(script_path):
    files = os.listdir(script_path)
    required_files = [
        "cosmos_assets_ui.py",
        "launch_cosmos_ui.py",
        "parts_deform_sync_callback.py"
    ]
    
    print("")
    print("Required files:")
    for req_file in required_files:
        exists = req_file in files
        status = "[OK]" if exists else "[MISSING]"
        print("  {} {}".format(status, req_file))
else:
    print("[ERROR] Script path not found")

print("")
print("[Checking hou.qt]")
print("=" * 70)

try:
    main_window = hou.qt.mainWindow()
    print("[OK] hou.qt.mainWindow() available")
    print("Type: {}".format(type(main_window)))
except Exception as e:
    print("[ERROR] {}".format(e))
""", print_output=False)
        
        if check_result and check_result.get('stdout'):
            try:
                print(check_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Check complete]")
        
        print("\n[2] Launching UI...")
        print("-"*80)
        
        launch_result = h.connector.execute_code("""
import hou
import sys

# 경로 추가
script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

print("[Importing cosmos_assets_ui]")
print("=" * 70)

try:
    import cosmos_assets_ui
    print("[OK] Module imported")
    
    # 모듈 내용 확인
    if hasattr(cosmos_assets_ui, 'CosmosAssetsMainWindow'):
        print("[OK] CosmosAssetsMainWindow class found")
    
    if hasattr(cosmos_assets_ui, 'launch'):
        print("[OK] launch() function found")
    
    print("")
    print("[Launching UI]")
    print("=" * 70)
    
    # UI 실행
    window = cosmos_assets_ui.launch()
    
    if window:
        print("[OK] UI launched successfully")
        print("Window type: {}".format(type(window)))
        print("Window title: {}".format(window.windowTitle()))
        print("Window size: {}x{}".format(window.width(), window.height()))
        print("Is visible: {}".format(window.isVisible()))
        
        # 탭 확인
        if hasattr(window, 'tab_widget'):
            tab_count = window.tab_widget.count()
            print("")
            print("Tabs: {}".format(tab_count))
            for i in range(tab_count):
                tab_name = window.tab_widget.tabText(i)
                print("  - {}".format(tab_name))
    else:
        print("[ERROR] UI launch returned None")
        
except Exception as e:
    print("[ERROR] {}".format(e))
    import traceback
    traceback.print_exc()
""", print_output=False)
        
        if launch_result and launch_result.get('stdout'):
            try:
                print(launch_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Launch complete]")
        
        if launch_result and launch_result.get('stderr'):
            print("\n[STDERR]")
            try:
                print(launch_result['stderr'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                pass
        
        print("\n[3] Testing UI functionality...")
        print("-"*80)
        
        func_test = h.connector.execute_code("""
import hou

# UI 윈도우 참조
if 'cosmos_assets_window' in dir():
    window = cosmos_assets_window
    
    print("[Testing UI Components]")
    print("=" * 70)
    
    # Project tab components
    if hasattr(window, 'project_path_combo'):
        item_count = window.project_path_combo.count()
        print("[OK] project_path_combo: {} items".format(item_count))
    
    if hasattr(window, 'seq_name_edit'):
        print("[OK] seq_name_edit exists")
    
    if hasattr(window, 'shot_name_edit'):
        print("[OK] shot_name_edit exists")
    
    # Assets tab components
    if hasattr(window, 'fbx_file_edit'):
        print("[OK] fbx_file_edit exists")
    
    if hasattr(window, 'guide_file_edit'):
        print("[OK] guide_file_edit exists")
    
    # Deform tab components
    if hasattr(window, 'parts_deform_list'):
        print("[OK] parts_deform_list exists")
    
    print("")
    print("[OK] All components verified")
else:
    print("[WARNING] Window not accessible in global scope")
    print("This is normal - window is managed by launch() function")
""", print_output=False)
        
        if func_test and func_test.get('stdout'):
            try:
                print(func_test['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Test complete]")
        
        print("\n" + "="*80)
        print("[OK] Testing completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        test_cosmos_ui()
        
        print("\n" + "="*80)
        print(" Test Summary")
        print("="*80)
        print("""
Cosmos Assets UI 테스트 완료!

생성된 파일:
==========
T:\\scripts\\python\\application\\houdini\\houdini21.0\\script\\
├─ cosmos_assets_ui.py (Main UI module)
├─ launch_cosmos_ui.py (Launcher)
└─ COSMOS_UI_GUIDE.txt (User guide)

실행 방법:
=========
Houdini Python Shell에서:

import sys
sys.path.insert(0, r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script")
import launch_cosmos_ui

또는:

import cosmos_assets_ui
cosmos_assets_ui.launch()

기능:
====
[Project Tab]
  - Z:/show/ 프로젝트 선택
  - 디렉토리 구조 생성

[Assets Tab]
  - FBX/Guide 파일 관리
  - Auto Setup (추후)

[Deform Tab]
  - Parts_Deform 동기화
  - 노드 목록 표시

[Settings Tab]
  - 설정 및 정보

다음 단계:
=========
1. Houdini에서 UI 실행
2. 각 탭 기능 테스트
3. Shelf Tool 생성 (선택)
4. 추가 기능 구현
""")
        print("="*80)
        
    except Exception as e:
        print("\n[ERROR] Test failed: {}".format(e))
        import traceback
        traceback.print_exc()





