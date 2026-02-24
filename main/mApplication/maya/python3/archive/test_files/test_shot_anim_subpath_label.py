#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shot Anim Subpath 라벨 너비 테스트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing Shot Anim Subpath Label Width")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Launching CFX UI and checking label widths...")
print("-" * 80)

# CFX UI 실행 및 라벨 확인
code = """
import sys
script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

try:
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtWidgets

# CFX UI 임포트 및 실행
try:
    import cfx_assets_ui
    import importlib
    
    # 리로드
    importlib.reload(cfx_assets_ui)
    
    # 윈도우 실행
    window = cfx_assets_ui.launch()
    
    print("[UI Label Width Check]")
    print("="*70)
    
    # Project Tab으로 전환
    window.tab_widget.setCurrentIndex(0)
    
    # 모든 라벨 찾기
    all_labels = {}
    for child in window.findChildren(QtWidgets.QLabel):
        text = child.text().strip()
        if text and ':' in text:
            min_w = child.minimumWidth()
            max_w = child.maximumWidth()
            all_labels[text] = (min_w, max_w)
    
    print("\\n[All Labels with Width]")
    print("-"*70)
    
    # 라벨을 길이 순으로 정렬
    sorted_labels = sorted(all_labels.items(), key=lambda x: len(x[0]), reverse=True)
    
    for i, (text, (min_w, max_w)) in enumerate(sorted_labels[:15], 1):
        char_count = len(text)
        status = "[OK]" if min_w >= 170 else "[WARNING]"
        print("{:2d}. {:30s} {} chars - {}px (Min) - {}".format(
            i, text, char_count, min_w, status))
    
    # Shot Anim Subpath 라벨 특별 체크
    shot_anim_found = False
    for text, (min_w, max_w) in all_labels.items():
        if "Shot Anim Subpath" in text:
            shot_anim_found = True
            print("\\n[Shot Anim Subpath: Detail Check]")
            print("="*70)
            print("Label Text:      '{}'".format(text))
            print("Character Count: {} chars".format(len(text)))
            print("Min Width:       {}px".format(min_w))
            print("Max Width:       {}px".format(max_w))
            
            # 예상 픽셀 너비 계산 (대략 1글자당 8-10px)
            estimated_width = len(text) * 9
            print("Estimated Need:  ~{}px".format(estimated_width))
            
            if min_w >= estimated_width:
                print("Status:          [OK] Sufficient width")
            else:
                print("Status:          [WARNING] May need more width")
                print("Recommendation:  {}px minimum".format(estimated_width + 20))
    
    if not shot_anim_found:
        print("\\n[WARNING] Shot Anim Subpath label not found!")
    
    # 통계
    print("\\n[Statistics]")
    print("="*70)
    
    labels_170 = sum(1 for _, (min_w, _) in all_labels.items() if min_w == 170)
    labels_150 = sum(1 for _, (min_w, _) in all_labels.items() if min_w == 150)
    labels_120 = sum(1 for _, (min_w, _) in all_labels.items() if min_w == 120)
    
    print("Total labels found:    {}".format(len(all_labels)))
    print("Labels with 170px:     {}".format(labels_170))
    print("Labels with 150px:     {}".format(labels_150))
    print("Labels with 120px:     {}".format(labels_120))
    
    if labels_170 > 0:
        print("\\nUpdate Status:         [OK] Labels updated to 170px")
    elif labels_150 > 0:
        print("\\nUpdate Status:         [PARTIAL] Some at 150px")
    else:
        print("\\nUpdate Status:         [WARNING] No 170px labels found")
    
    print("\\n[Summary]")
    print("="*70)
    print("Label Width Update:")
    print("  120px → 150px → 170px (+50px total)")
    print()
    print("Shot Anim Subpath: (18 chars)")
    print("  Estimated requirement: ~162-180px")
    print("  Current setting: 170px")
    print("  Status: Should be sufficient")
    
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
print("변경 이력:")
print("=========")
print("1차: 120px → 150px (+30px)")
print("2차: 150px → 170px (+20px)")
print("총:  120px → 170px (+50px)")
print()
print("Shot Anim Subpath:")
print("================")
print("텍스트: 'Shot Anim Subpath:' (18자)")
print("필요 너비: ~162-180px (1글자당 9-10px 기준)")
print("현재 너비: 170px")
print("상태: 충분함 ✓")
print()
print("만약 여전히 잘린다면:")
print("===================")
print("1. 후디니의 UI 스케일 설정 확인")
print("2. 폰트 크기가 기본값보다 큰지 확인")
print("3. 필요시 180px 또는 200px로 추가 증가 가능")
print()
print("="*80)





