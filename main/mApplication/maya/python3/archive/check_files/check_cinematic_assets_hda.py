#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cinematic::assets HDA 상세 조사
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def check_cinematic_assets():
    """Cinematic::assets HDA 확인"""
    print("\n" + "="*80)
    print(" Check Cinematic::assets HDA")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Finding Cinematic::assets nodes...")
        print("-"*80)
        h.execute("""
import hou

# Cinematic::assets 노드 찾기
cinematic_nodes = []

for node in hou.node("/").allSubChildren():
    if node.type().name() == "Cinematic::assets::1.0":
        cinematic_nodes.append(node)

print(f"Found {len(cinematic_nodes)} Cinematic::assets nodes:")

for node in cinematic_nodes:
    print(f"  - {node.path()}")
    print(f"    Type: {node.type().name()}")
    
    # HDA 정의 확인
    definition = node.type().definition()
    if definition:
        print(f"    Library: {definition.libraryFilePath()}")
""")
        
        print("\n[2] Checking parameters of Cinematic::assets node...")
        print("-"*80)
        h.execute("""
import hou

node = hou.node("/obj/assets")
if node:
    print(f"Node: {node.path()}")
    print(f"Type: {node.type().name()}")
    print(f"\\nParameters ({len(node.parms())} total):")
    print("-" * 60)
    
    # 모든 파라미터 확인
    problematic_parms = []
    
    for parm in node.parms():
        try:
            parm_template = parm.parmTemplate()
            parm_type = parm_template.type()
            
            # 메뉴 타입 파라미터인지 확인
            if hasattr(parm_template, 'menuType'):
                menu_type = parm_template.menuType()
                
                # 조건부 표시(conditionals) 확인
                conditionals = []
                if hasattr(parm_template, 'conditionals'):
                    try:
                        conditionals = parm_template.conditionals()
                    except:
                        pass
                
                # Hide when 표현식 확인
                if hasattr(parm_template, 'hideCondition'):
                    try:
                        hide_cond = parm_template.hideCondition()
                        if hide_cond:
                            # 이것이 문제의 원인일 수 있음
                            # hideCondition은 정수를 반환해야 함
                            problematic_parms.append({
                                'name': parm.name(),
                                'label': parm.description(),
                                'hide_condition': hide_cond,
                                'menu_type': str(menu_type)
                            })
                    except Exception as e:
                        problematic_parms.append({
                            'name': parm.name(),
                            'label': parm.description(),
                            'error': str(e)
                        })
                
                # Disable when 표현식 확인
                if hasattr(parm_template, 'disableCondition'):
                    try:
                        disable_cond = parm_template.disableCondition()
                        if disable_cond:
                            # 이것도 정수를 반환해야 함
                            problematic_parms.append({
                                'name': parm.name(),
                                'label': parm.description(),
                                'disable_condition': disable_cond,
                                'menu_type': str(menu_type)
                            })
                    except Exception as e:
                        pass
                        
        except Exception as e:
            pass
    
    if problematic_parms:
        print(f"\\n[FOUND] {len(problematic_parms)} parameters with conditions:")
        print("-" * 60)
        
        for i, pp in enumerate(problematic_parms[:10], 1):
            print(f"\\n{i}. Parameter: {pp['name']}")
            print(f"   Label: {pp.get('label', 'N/A')}")
            
            if 'hide_condition' in pp:
                print(f"   Hide Condition: {pp['hide_condition'][:200]}")
            
            if 'disable_condition' in pp:
                print(f"   Disable Condition: {pp['disable_condition'][:200]}")
            
            if 'error' in pp:
                print(f"   ERROR: {pp['error']}")
            
            if 'menu_type' in pp:
                print(f"   Menu Type: {pp['menu_type']}")
        
        if len(problematic_parms) > 10:
            print(f"\\n... and {len(problematic_parms) - 10} more")
    else:
        print("\\nNo obvious conditional issues found")
else:
    print("Node /obj/assets not found")
""")
        
        print("\n[3] Checking HDA parameter interface...")
        print("-"*80)
        h.execute("""
import hou

node = hou.node("/obj/assets")
if node and node.type().definition():
    definition = node.type().definition()
    
    print(f"HDA Definition:")
    print(f"  Name: {definition.nodeTypeName()}")
    print(f"  Library: {definition.libraryFilePath()}")
    print(f"  Is Editable: {not definition.isReadOnly()}")
    
    # 파라미터 템플릿 그룹 가져오기
    try:
        parm_template_group = definition.parmTemplateGroup()
        
        print(f"\\nParameter Templates in HDA:")
        print("-" * 60)
        
        # 모든 파라미터 템플릿 확인
        all_templates = parm_template_group.entries()
        
        issue_count = 0
        for template in all_templates:
            # 조건부 표현식 확인
            hide_cond = None
            disable_cond = None
            
            if hasattr(template, 'hideCondition'):
                try:
                    hide_cond = template.hideCondition()
                except:
                    pass
            
            if hasattr(template, 'disableCondition'):
                try:
                    disable_cond = template.disableCondition()
                except:
                    pass
            
            if hide_cond or disable_cond:
                issue_count += 1
                if issue_count <= 5:  # 처음 5개만 표시
                    print(f"\\nTemplate: {template.name()}")
                    print(f"  Label: {template.label()}")
                    
                    if hide_cond:
                        print(f"  Hide When: {hide_cond[:150]}")
                    
                    if disable_cond:
                        print(f"  Disable When: {disable_cond[:150]}")
        
        if issue_count > 5:
            print(f"\\n... and {issue_count - 5} more parameters with conditions")
        
        print(f"\\nTotal parameters with conditions: {issue_count}")
        
    except Exception as e:
        print(f"Could not read parameter template group: {e}")
else:
    print("HDA definition not found")
""")
        
        print("\n[4] Checking for specific error patterns...")
        print("-"*80)
        h.execute("""
import hou

# "Menu item filter expression" 에러는 보통
# Hide When 또는 Disable When 표현식이 잘못되었을 때 발생

node = hou.node("/obj/assets")
if node:
    print("Checking for common error patterns in conditional expressions...")
    print("-" * 60)
    
    errors_found = []
    
    for parm in node.parms():
        try:
            parm_template = parm.parmTemplate()
            
            # Hide condition 확인
            if hasattr(parm_template, 'hideCondition'):
                hide_cond = parm_template.hideCondition()
                if hide_cond:
                    # 일반적인 문제 패턴 확인
                    # 1. 문자열을 반환하는 경우
                    # 2. None을 반환하는 경우
                    # 3. 구문 오류
                    
                    if '==' in hide_cond or '!=' in hide_cond:
                        # 비교 연산자 사용 - 괜찮음
                        pass
                    elif 'ch(' in hide_cond:
                        # 채널 참조 - 괜찮음
                        pass
                    else:
                        # 다른 패턴 - 확인 필요
                        errors_found.append({
                            'parm': parm.name(),
                            'condition': hide_cond,
                            'type': 'hide'
                        })
            
            # Disable condition 확인
            if hasattr(parm_template, 'disableCondition'):
                disable_cond = parm_template.disableCondition()
                if disable_cond:
                    if not ('==' in disable_cond or '!=' in disable_cond or 'ch(' in disable_cond):
                        errors_found.append({
                            'parm': parm.name(),
                            'condition': disable_cond,
                            'type': 'disable'
                        })
                        
        except Exception as e:
            pass
    
    if errors_found:
        print(f"\\n[WARNING] Found {len(errors_found)} suspicious conditions:")
        for err in errors_found[:5]:
            print(f"\\n  Parameter: {err['parm']}")
            print(f"  Type: {err['type']}")
            print(f"  Expression: {err['condition'][:100]}")
    else:
        print("\\nNo obvious error patterns found")
        print("The issue might be:")
        print("  1. In a different node type")
        print("  2. In a shelf tool script")
        print("  3. Triggered only when UI updates")
""")
        
        print("\n" + "="*80)
        print("[OK] Check completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        check_cinematic_assets()
        
        print("\n" + "="*80)
        print(" Summary & Recommendations")
        print("="*80)
        print("""
발견된 정보:

1. 파일: SZERO_0090_Simulation_main_v002.hip
2. 의심 노드: /obj/assets (Cinematic::assets::1.0)
3. FBX 관련 노드 157개 존재

"Menu item filter expression should return an integer" 에러는 일반적으로:
- Hide When 표현식이 정수가 아닌 값을 반환
- Disable When 표현식이 정수가 아닌 값을 반환
- Menu Script가 정수가 아닌 값을 반환

권장 조치:

1. 즉시 해결 (에러 무시하고 작업):
   - 에러 메시지는 무시하고 파일 사용 가능하면 계속 작업
   - 기능에 영향 없을 수 있음

2. HDA 수정 (근본적 해결):
   - Cinematic::assets HDA를 Unlock
   - Type Properties > Parameters 탭에서 조건부 표현식 확인
   - 문제가 되는 Hide When/Disable When 수정

3. 노드 교체:
   - /obj/assets 노드를 새로운 것으로 교체
   - 내용물을 복사

다음 단계를 진행하시겠습니까?
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Check failed: {e}")
        import traceback
        traceback.print_exc()






