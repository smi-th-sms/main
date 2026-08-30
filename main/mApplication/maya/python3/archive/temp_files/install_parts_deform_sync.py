#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parts_Deform 동기화 스크립트를 Houdini 세션에 설치
"""

import sys
import os
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def install_sync_script():
    """동기화 스크립트를 Houdini 세션에 설치"""
    print("\n" + "="*80)
    print(" Install Parts_Deform Sync Script")
    print("="*80)
    
    # 콜백 스크립트 파일 읽기
    callback_file = r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3\parts_deform_sync_callback.py"
    
    print("\n[1] Reading callback script...")
    print("-"*80)
    
    if not os.path.exists(callback_file):
        print("[ERROR] Callback file not found: {}".format(callback_file))
        return
    
    with open(callback_file, 'r', encoding='utf-8') as f:
        callback_code = f.read()
    
    print("[OK] Read {} characters from callback file".format(len(callback_code)))
    
    with connect_houdini() as h:
        print("\n[2] Installing script to Houdini session...")
        print("-"*80)
        
        # hou.session에 스크립트 저장
        result = h.connector.execute_code("""
import hou

# 스크립트 경로를 세션에 저장
hou.session.parts_deform_sync_script_path = r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3\\parts_deform_sync_callback.py"

print("[OK] Script path saved to hou.session.parts_deform_sync_script_path")
print("")
print("To execute the sync:")
print("  import sys")
print("  sys.path.append(r'z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3')")
print("  import parts_deform_sync_callback")
print("  parts_deform_sync_callback.sync_parts_deform_nodes()")
""", print_output=False)
        
        if result and result.get('stdout'):
            try:
                # 안전한 출력을 위해 ascii로 변환
                safe_output = result['stdout'].encode('ascii', errors='ignore').decode('ascii')
                if safe_output.strip():
                    print(safe_output)
                else:
                    print("[OK] Script installed (output contains non-ascii characters)")
            except Exception as e:
                print("[OK] Script installed (output error: {})".format(str(e)))
        
        print("\n[3] Testing the sync function...")
        print("-"*80)
        
        # 테스트 실행
        test_result = h.connector.execute_code("""
import hou
import sys

# 경로 추가
sys.path.append(r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3")

# 모듈 임포트
import parts_deform_sync_callback

# 실행
parts_deform_sync_callback.sync_parts_deform_nodes()
""", print_output=False)
        
        if test_result:
            if test_result.get('stdout'):
                try:
                    safe_output = test_result['stdout'].encode('ascii', errors='ignore').decode('ascii')
                    if safe_output.strip():
                        print(safe_output)
                    else:
                        print("[OK] Test executed (output contains non-ascii characters)")
                except Exception as e:
                    print("[OK] Test executed (output error: {})".format(str(e)))
            if test_result.get('stderr'):
                print("\n[STDERR]")
                try:
                    safe_err = test_result['stderr'].encode('ascii', errors='ignore').decode('ascii')
                    print(safe_err)
                except Exception:
                    print("[Error output contains non-ascii characters]")
        
        print("\n[4] Creating shelf tool...")
        print("-"*80)
        
        # Shelf Tool 생성
        shelf_result = h.connector.execute_code("""
import hou

# Shelf 찾기 또는 생성
shelf_name = "cosmos"
shelf = hou.shelves.shelves().get(shelf_name)

if not shelf:
    print("[INFO] Creating new shelf: {}".format(shelf_name))
    # 새 shelf 생성은 복잡하므로 기본 shelf 사용
    shelf_name = "custom"
    shelf = hou.shelves.shelves().get(shelf_name)

if shelf:
    print("[OK] Using shelf: {}".format(shelf_name))
    
    # Tool 이름
    tool_name = "sync_parts_deform"
    
    # Tool 스크립트
    tool_script = '''import sys
sys.path.append(r"z:\\\\inhouse\\\\Maya\\\\scripts\\\\2025\\\\cosmos\\\\scripts\\\\python3")
import parts_deform_sync_callback
parts_deform_sync_callback.sync_parts_deform_nodes()'''
    
    # Tool 생성 정보 출력
    print("")
    print("Shelf Tool Info:")
    print("  Name: {}".format(tool_name))
    print("  Label: Sync Parts_Deform")
    print("  Shelf: {}".format(shelf_name))
    print("")
    print("To create manually:")
    print("1. Right-click on a shelf")
    print("2. Select 'New Tool...'")
    print("3. Name: sync_parts_deform")
    print("4. Label: Sync Parts_Deform")
    print("5. Script: (paste the tool_script above)")
else:
    print("[WARNING] Could not find shelf")
    print("You can manually create a shelf tool with the script")

# 세션 정보 저장
hou.session.sync_tool_script = '''import sys
sys.path.append(r"z:\\\\inhouse\\\\Maya\\\\scripts\\\\2025\\\\cosmos\\\\scripts\\\\python3")
import parts_deform_sync_callback
parts_deform_sync_callback.sync_parts_deform_nodes()'''

print("")
print("[OK] Tool script saved to hou.session.sync_tool_script")
""", print_output=False)
        
        if shelf_result and shelf_result.get('stdout'):
            try:
                safe_output = shelf_result['stdout'].encode('ascii', errors='ignore').decode('ascii')
                if safe_output.strip():
                    print(safe_output)
            except Exception as e:
                print("[OK] Shelf info prepared (output error: {})".format(str(e)))
        
        print("\n[5] Setting up button callback (Python Panel approach)...")
        print("-"*80)
        
        # Python Panel에서 실행할 수 있는 함수 등록
        panel_result = h.connector.execute_code("""
import hou

# hou.session에 함수 등록
def run_parts_deform_sync():
    import sys
    sys.path.append(r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3")
    import parts_deform_sync_callback
    parts_deform_sync_callback.sync_parts_deform_nodes()

hou.session.run_parts_deform_sync = run_parts_deform_sync

print("[OK] Registered hou.session.run_parts_deform_sync()")
print("")
print("You can now call this function from anywhere:")
print("  hou.session.run_parts_deform_sync()")
""", print_output=False)
        
        if panel_result and panel_result.get('stdout'):
            try:
                safe_output = panel_result['stdout'].encode('ascii', errors='ignore').decode('ascii')
                if safe_output.strip():
                    print(safe_output)
            except Exception as e:
                print("[OK] Panel function registered (output error: {})".format(str(e)))
        
        print("\n" + "="*80)
        print("[OK] Installation completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        install_sync_script()
        
        print("\n" + "="*80)
        print(" Usage Instructions")
        print("="*80)
        print("""
설치 완료!

동기화 스크립트 실행 방법:
========================

방법 1: Python Shell에서 직접 실행
----------------------------------
hou.session.run_parts_deform_sync()


방법 2: Python Source Editor에서 실행
-----------------------------------
import sys
sys.path.append(r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3")
import parts_deform_sync_callback
parts_deform_sync_callback.sync_parts_deform_nodes()


방법 3: Shelf Tool 생성 (권장)
-----------------------------
1. 원하는 shelf를 우클릭
2. "New Tool..." 선택
3. 다음 내용 입력:
   - Name: sync_parts_deform
   - Label: Sync Parts_Deform
   - Script: hou.session.sync_tool_script에 저장된 스크립트 사용
   
4. 버튼 클릭으로 실행


방법 4: sim_filecache의 Pre-Render Script
---------------------------------------
sim_filecache 노드의 파라미터에서:
1. Scripts 탭 열기
2. Pre-Render Script에 다음 추가:
   hou.session.run_parts_deform_sync()


동작 설명:
=========
- proxy_path 노드의 @proxy_path 어트리뷰트 분석
- 필요 없는 Parts_Deform_* 노드 삭제
- 필요한 Parts_Deform_* 노드 생성
- 기존 노드는 유지 및 업데이트
- 각 노드의 group 및 blast2 파라미터 자동 설정


테스트 결과:
===========
위에서 자동으로 한 번 실행되었습니다.
결과 메시지를 확인하세요.
""")
        print("="*80)
        
    except Exception as e:
        print("\n[ERROR] Installation failed: {}".format(e))
        import traceback
        traceback.print_exc()

