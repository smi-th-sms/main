#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
정확한 메뉴 필터 에러 위치 찾기
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def find_exact_error():
    """정확한 에러 위치 찾기"""
    print("\n" + "="*80)
    print(" Find Exact Menu Filter Error Location")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Checking FBX nodes specifically...")
        print("-"*80)
        h.execute("""
import hou

# FBX 관련 노드들 확인
fbx_nodes = []
obj = hou.node("/obj")

if obj:
    for node in obj.allSubChildren():
        if 'fbx' in node.name().lower() or 'FBX' in node.path():
            fbx_nodes.append(node)

print(f"Found {len(fbx_nodes)} FBX-related nodes")

if fbx_nodes:
    print("\\nFBX nodes:")
    for node in fbx_nodes[:20]:
        print(f"  - {node.path()} ({node.type().name()})")
    
    if len(fbx_nodes) > 20:
        print(f"  ... and {len(fbx_nodes) - 20} more")
""")
        
        print("\n[2] Testing parameter evaluation on suspect nodes...")
        print("-"*80)
        h.execute("""
import hou

# 문제가 될 수 있는 노드들 테스트
test_paths = [
    "/obj/assets/FBX",
    "/obj/assets/FBX/fbxcharacterimport",
    "/obj/assets",
]

for path in test_paths:
    node = hou.node(path)
    if node:
        print(f"\\nTesting node: {path}")
        print("-" * 60)
        
        # 각 파라미터 테스트
        error_parms = []
        for parm in node.parms():
            try:
                parm_template = parm.parmTemplate()
                
                # 메뉴 타입인지 확인
                if hasattr(parm_template, 'menuType'):
                    menu_type = parm_template.menuType()
                    
                    # 동적 메뉴인 경우
                    if menu_type != hou.menuType.Normal:
                        # 메뉴 스크립트 확인
                        if hasattr(parm_template, 'menuScript'):
                            script = parm_template.menuScript()
                            if script:
                                # 스크립트 실행 시도
                                try:
                                    # 테스트 실행
                                    result = eval(script)
                                    # 정수 반환 여부 확인
                                    if not isinstance(result, (int, bool)):
                                        error_parms.append({
                                            'name': parm.name(),
                                            'label': parm.description(),
                                            'script': script[:100],
                                            'result_type': type(result).__name__
                                        })
                                except Exception as e:
                                    error_parms.append({
                                        'name': parm.name(),
                                        'label': parm.description(),
                                        'script': script[:100] if script else 'None',
                                        'error': str(e)[:100]
                                    })
            except Exception as e:
                pass
        
        if error_parms:
            print(f"  [FOUND] {len(error_parms)} problematic parameters:")
            for ep in error_parms[:5]:
                print(f"\\n  Parameter: {ep['name']} ({ep.get('label', 'N/A')})")
                if 'error' in ep:
                    print(f"    Error: {ep['error']}")
                if 'result_type' in ep:
                    print(f"    Returns: {ep['result_type']} (should be int)")
                if 'script' in ep and ep['script'] != 'None':
                    print(f"    Script: {ep['script']}")
        else:
            print("  [OK] No obvious issues found")
    else:
        print(f"\\nNode not found: {path}")
""")
        
        print("\n[3] Checking HDA definitions for menu filter issues...")
        print("-"*80)
        h.execute("""
import hou

print("Checking HDA definitions in scene...")

# 씬에서 사용 중인 HDA 타입 찾기
hda_types = set()

for node in hou.node("/").allSubChildren():
    if node.type().definition():
        hda_types.add(node.type().name())

print(f"Found {len(hda_types)} HDA types in use")

if hda_types:
    print("\\nHDA types:")
    for hda_type in sorted(hda_types)[:20]:
        print(f"  - {hda_type}")
    
    if len(hda_types) > 20:
        print(f"  ... and {len(hda_types) - 20} more")

# 특히 문제가 될 수 있는 custom HDA 찾기
print("\\nChecking for custom/inhouse HDAs...")
custom_hdas = [h for h in hda_types if 'fbx' in h.lower() or 'import' in h.lower()]

if custom_hdas:
    print("\\nSuspect HDAs (FBX/Import related):")
    for hda in custom_hdas:
        print(f"  - {hda}")
        
        # HDA 정의 찾기
        try:
            # 해당 타입의 노드 찾기
            for node in hou.node("/").allSubChildren():
                if node.type().name() == hda:
                    definition = node.type().definition()
                    if definition:
                        print(f"    Library: {definition.libraryFilePath()}")
                    break
        except:
            pass
""")
        
        print("\n[4] Attempting to reproduce the error...")
        print("-"*80)
        h.execute("""
import hou

print("Trying to trigger the error by accessing node parameters...")

# FBX 노드의 파라미터 메뉴 접근 시도
fbx_node = hou.node("/obj/assets/FBX")
if fbx_node:
    print(f"\\nNode: {fbx_node.path()}")
    
    # 파라미터 메뉴 아이템 가져오기 시도
    for parm in fbx_node.parms():
        try:
            parm_template = parm.parmTemplate()
            if hasattr(parm_template, 'menuItems'):
                menu_items = parm_template.menuItems()
                if menu_items:
                    # 메뉴 라벨도 가져와보기
                    if hasattr(parm_template, 'menuLabels'):
                        menu_labels = parm_template.menuLabels()
                        
                        # Filter 표현식이 있는지 확인
                        if hasattr(parm_template, 'conditionals'):
                            # 이것이 문제의 원인일 수 있음
                            pass
        except Exception as e:
            if 'Menu item filter' in str(e):
                print(f"\\n[FOUND ERROR] Parameter: {parm.name()}")
                print(f"  Error: {e}")
                print(f"  This is likely the source of the error!")
                
                # 파라미터 템플릿 정보
                print(f"\\n  Parameter details:")
                print(f"    Name: {parm.name()}")
                print(f"    Label: {parm.description()}")
                print(f"    Type: {parm.parmTemplate().type()}")
else:
    print("FBX node not found")
""")
        
        print("\n" + "="*80)
        print("[OK] Search completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        find_exact_error()
        
        print("\n" + "="*80)
        print(" Analysis & Next Steps")
        print("="*80)
        print("""
Based on the diagnostics:

파일: Z:/show/PUBGOM/sequences/SZERO/SZERO_0090/SIM/wip/houdini/
      SZERO_0090_Simulation_main_v002.hip

의심되는 위치:
1. /obj/assets/FBX - FBX 관련 노드들
2. fbxcharacterimport - custom HDA
3. 동적 메뉴 (StringReplace type) 파라미터들

해결 방법:

A. 임시 해결 (빠른 방법):
   1. 문제가 되는 노드를 삭제
   2. 또는 해당 노드의 파라미터를 기본값으로 리셋

B. 근본적 해결:
   1. 해당 HDA 파일을 열어서 파라미터 인터페이스 수정
   2. 메뉴 필터 표현식이 항상 정수(0 또는 1)를 반환하도록 수정

C. 우회 방법:
   1. hip 파일을 텍스트 에디터로 열기
   2. 문제가 되는 섹션 찾아서 수정
   3. 또는 새 파일에 깨끗한 노드만 복사

다음 단계를 실행하시겠습니까?
- 문제 노드 식별 및 자동 수정
- HDA 파라미터 인터페이스 검사
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Search failed: {e}")
        import traceback
        traceback.print_exc()






