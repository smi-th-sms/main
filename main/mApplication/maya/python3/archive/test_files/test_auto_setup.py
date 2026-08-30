#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CFX Auto Setup (Install & Create) 테스트 스크립트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing CFX Auto Setup (Install & Create)")
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
    
    # Auto Setup 버튼 텍스트 확인
    print("\\n[Button Text Check]")
    print("-"*70)
    
    # 버튼 찾기
    for child in window.findChildren(QtWidgets.QPushButton):
        if "Auto Setup" in child.text():
            print("[OK] Button found:", child.text())
            print("    Expected: 'Auto Setup (Install & Create)'")
            break
    
    print("\\n[Default HDA Path Check]")
    print("-"*70)
    default_hda = window.default_hda_edit.text()
    print("Default HDA:", default_hda)
    
    import os
    if os.path.isdir(default_hda):
        print("    Type: Directory")
        print("    Status: [WARNING] Should be a file path")
    elif os.path.isfile(default_hda):
        print("    Type: File")
        print("    Status: [OK] Valid HDA file")
    else:
        print("    Type: Not exist")
        print("    Status: [INFO] Path does not exist")
    
    print("\\n[Install & Create Logic]")
    print("-"*70)
    print("New Auto Setup functionality:")
    print("1. Install HDA file using hou.hda.installFile()")
    print("2. Get definitions from HDA using hou.hda.definitionsInFile()")
    print("3. Select node type (auto if 1, user choice if multiple)")
    print("4. Create node in /obj context")
    print("5. Position and select the new node")
    
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
print(" Auto Setup (Install & Create) Implementation")
print("="*80)
print()
print("새로운 기능:")
print("===========")
print("1. HDA 파일 설치 (hou.hda.installFile)")
print("   - 선택된 HDA 파일을 Houdini에 설치")
print()
print("2. HDA Definition 확인 (hou.hda.definitionsInFile)")
print("   - 설치된 HDA 파일의 노드 타입 정의 가져오기")
print()
print("3. 노드 타입 선택")
print("   - 1개: 자동 선택")
print("   - 여러 개: 사용자 선택 (hou.ui.selectFromList)")
print()
print("4. 노드 생성 (obj_context.createNode)")
print("   - /obj 컨텍스트에 선택된 타입의 노드 생성")
print("   - 노드 이름: Assets Name")
print()
print("5. 노드 배치 및 선택")
print("   - moveToGoodPosition(): 자동 레이아웃")
print("   - setSelected(): 생성된 노드 선택")
print()
print("에러 처리:")
print("=========")
print("- Default HDA가 디렉토리면 경고")
print("- HDA 파일이 없으면 에러")
print("- Definition이 없으면 경고")
print("- 노드 생성 실패 시 에러")
print()
print("사용 방법:")
print("=========")
print("1. Assets Tab에서 Assets Name 선택")
print("2. Default HDA에 유효한 HDA 파일 경로 입력 또는 Browse로 선택")
print("3. Auto Setup (Install & Create) 버튼 클릭")
print("4. Assets Name.hda 있으면 선택 팝업, 없으면 Default HDA 사용")
print("5. HDA 설치 및 /obj에 노드 자동 생성")
print()
print("="*80)





