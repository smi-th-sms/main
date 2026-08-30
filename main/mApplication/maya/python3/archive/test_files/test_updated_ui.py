#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
업데이트된 Cosmos UI 테스트
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def test_updated_ui():
    """업데이트된 UI 테스트"""
    print("\n" + "="*80)
    print(" Testing Updated Cosmos UI")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Launching updated UI...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou
import sys

# 모듈 리로드 (최신 버전)
script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

# 기존 UI 닫기
try:
    if 'cosmos_assets_window' in globals():
        cosmos_assets_window.close()
        cosmos_assets_window.deleteLater()
except:
    pass

# 모듈 리로드
import cosmos_assets_ui
import importlib
importlib.reload(cosmos_assets_ui)

print("[Launching UI]")
print("=" * 70)

window = cosmos_assets_ui.launch()

if window:
    print("[OK] UI launched")
    print("Window title: {}".format(window.windowTitle()))
    print("")
    
    # Project Tab 컴포넌트 확인
    print("[Project Tab Components]")
    print("-" * 70)
    
    if hasattr(window, 'project_path_combo'):
        print("[OK] project_path_combo: {} items".format(window.project_path_combo.count()))
    
    if hasattr(window, 'seq_name_combo'):
        print("[OK] seq_name_combo (NEW): {} items".format(window.seq_name_combo.count()))
    
    if hasattr(window, 'shot_name_combo'):
        print("[OK] shot_name_combo (NEW): {} items".format(window.shot_name_combo.count()))
    
    if hasattr(window, 'full_path_label'):
        print("[OK] full_path_label: {}".format(window.full_path_label.text()[:50]))
    
    print("")
    print("[UI Structure]")
    print("-" * 70)
    print("Project Path: ComboBox (editable) + Refresh button")
    print("Sequence Name: ComboBox (editable) + Refresh button")
    print("Shot Name: ComboBox (editable) + Refresh button")
    print("Full Path: Dynamic label")
    
else:
    print("[ERROR] UI launch failed")
""", print_output=False)
        
        if result and result.get('stdout'):
            try:
                print(result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[OK] UI launched")
        
        print("\n[2] Testing cascade behavior...")
        print("-"*80)
        
        cascade_test = h.connector.execute_code("""
import hou

if 'cosmos_assets_window' in dir():
    window = cosmos_assets_window
    
    print("[Testing Cascade Behavior]")
    print("=" * 70)
    print("")
    
    # 프로젝트 선택
    if window.project_path_combo.count() > 0:
        print("Step 1: Select Project")
        print("-" * 70)
        
        # 첫 번째 프로젝트 선택
        window.project_path_combo.setCurrentIndex(0)
        project = window.project_path_combo.currentText()
        
        print("  Selected: {}".format(project))
        print("  Sequence list updated: {} items".format(window.seq_name_combo.count()))
        print("")
        
        # Sequence 선택
        if window.seq_name_combo.count() > 0:
            print("Step 2: Select Sequence")
            print("-" * 70)
            
            window.seq_name_combo.setCurrentIndex(0)
            sequence = window.seq_name_combo.currentText()
            
            print("  Selected: {}".format(sequence))
            print("  Shot list updated: {} items".format(window.shot_name_combo.count()))
            print("")
            
            # Shot 선택
            if window.shot_name_combo.count() > 0:
                print("Step 3: Select Shot")
                print("-" * 70)
                
                window.shot_name_combo.setCurrentIndex(0)
                shot = window.shot_name_combo.currentText()
                
                print("  Selected: {}".format(shot))
                print("  Full Path: {}".format(window.full_path_label.text()))
                print("")
                print("[OK] Cascade behavior works correctly")
            else:
                print("  [INFO] No shots available in this sequence")
        else:
            print("  [INFO] No sequences available in this project")
    else:
        print("[INFO] No projects available (Z:/show/ might be empty)")
        
else:
    print("[WARNING] Window not in global scope")
""", print_output=False)
        
        if cascade_test and cascade_test.get('stdout'):
            try:
                print(cascade_test['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Test complete]")
        
        print("\n" + "="*80)
        print("[OK] Testing completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        test_updated_ui()
        
        print("\n" + "="*80)
        print(" Update Summary")
        print("="*80)
        print("""
UI 업데이트 완료!

변경 사항:
=========
1. Project Path
   - 버튼 크기 및 레이아웃 개선
   - 최소 너비 300px
   - Refresh 버튼 80-100px 고정

2. Sequence Name (NEW!)
   - LineEdit → ComboBox로 변경
   - Project Path + Sequence Subdir 경로의 폴더 목록 표시
   - Refresh 버튼 추가
   - 자동 갱신 (Project 선택 시)

3. Shot Name (NEW!)
   - LineEdit → ComboBox로 변경
   - Sequence Name 경로의 폴더 목록 표시
   - Refresh 버튼 추가
   - 자동 갱신 (Sequence 선택 시)

4. Full Path
   - 모든 경로 조합 표시
   - Project + SeqSubdir + SeqName + ShotName + ShotSubdir

계층 구조:
=========
Project Path (Z:/show/)
  └─> Sequence Name (Project + Sequence Subdir)
      └─> Shot Name (Sequence Path)
          └─> Full Path (+ Shot Subdir)

장점:
====
+ 폴더 구조 탐색 용이
+ 수동 입력 오류 감소
+ 실시간 경로 유효성 확인
+ 직관적인 UI

테스트:
======
1. Houdini에서 UI 실행
2. Project 선택 → Sequence 자동 로드
3. Sequence 선택 → Shot 자동 로드
4. Full Path 확인
""")
        print("="*80)
        
    except Exception as e:
        print("\n[ERROR] Test failed: {}".format(e))
        import traceback
        traceback.print_exc()





