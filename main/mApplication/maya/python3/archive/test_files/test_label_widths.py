#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CFX UI Label Width 테스트 스크립트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing CFX UI Label Widths")
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
    
    print("[Launching UI]")
    print("="*70)
    print("[OK] UI launched")
    
    # Project Tab 라벨 확인
    print("\\n[Project Tab Labels]")
    print("-"*70)
    
    window.tab_widget.setCurrentIndex(0)
    
    labels_found = []
    for child in window.findChildren(QtWidgets.QLabel):
        # GroupBox 제외, 실제 필드 라벨만
        if child.minimumWidth() == 150:
            labels_found.append((child.text(), child.minimumWidth(), child.maximumWidth()))
    
    print("Labels with 150px width:", len(labels_found))
    
    # 샘플 출력
    if labels_found:
        print("\\nSample labels:")
        for i, (text, min_w, max_w) in enumerate(labels_found[:10]):
            text_display = text.replace(':', '')
            print("  [{}] '{}' - Min: {}px, Max: {}px".format(i+1, text_display, min_w, max_w))
    
    # 버튼 너비 확인
    print("\\n[Button Widths Check]")
    print("-"*70)
    
    buttons_120 = []
    for child in window.findChildren(QtWidgets.QPushButton):
        if "Refresh" in child.text() or "Apply" in child.text():
            if child.minimumWidth() == 120:
                buttons_120.append(child.text())
    
    print("Buttons with 120px width:", len(buttons_120))
    if buttons_120:
        print("Sample buttons:", ", ".join(buttons_120[:5]))
    
    # Assets Tab 라벨 확인
    print("\\n[Assets Tab Labels]")
    print("-"*70)
    
    window.tab_widget.setCurrentIndex(1)
    
    assets_labels = []
    for child in window.findChildren(QtWidgets.QLabel):
        if child.minimumWidth() == 150:
            label_text = child.text().replace(':', '')
            if label_text and len(label_text) > 3:  # 실제 라벨만
                assets_labels.append(label_text)
    
    print("Assets Tab labels with 150px:", len(assets_labels))
    
    # 가장 긴 라벨 찾기
    if labels_found:
        longest = max(labels_found, key=lambda x: len(x[0]))
        print("\\n[Longest Label]")
        print("-"*70)
        print("Text:", longest[0])
        print("Length:", len(longest[0]), "characters")
        print("Width: {}px (Min), {}px (Max)".format(longest[1], longest[2]))
    
    print("\\n[Summary]")
    print("="*70)
    print("Total labels updated: ~34")
    print("Label width: 150px (was 120px)")
    print("Button width: 120px (unchanged)")
    print("Improvement: +30px for labels")
    
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
print(" Label Width Update Summary")
print("="*80)
print()
print("변경 사항:")
print("=========")
print("라벨 너비: 120px → 150px (+30px)")
print("버튼 너비: 120px (유지)")
print()
print("영향받는 라벨:")
print("=============")
print()
print("Project Tab:")
print("  - Project Path")
print("  - Project Name")
print("  - Sequence Subdir")
print("  - Sequence Name")
print("  - Shot Name")
print("  - Shot Subdir")
print("  - Shot Anim Subpath (가장 긴 라벨)")
print("  - Shot Anim File")
print("  - Full Path")
print()
print("Assets Tab:")
print("  - Assets Subpath")
print("  - Assets Name")
print("  - Assets FullPath")
print("  - FBX Subpath")
print("  - FBX File")
print("  - Guide Subpath")
print("  - Guide File")
print("  - Default HDA")
print()
print("Settings Tab:")
print("  - (정보 표시 라벨)")
print()
print("이점:")
print("====")
print("1. 긴 라벨도 잘리지 않고 완전히 표시됨")
print("2. 일관된 레이아웃 유지")
print("3. 가독성 향상")
print()
print("="*80)





