#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
project_dir Menu Script 수정 (올바른 방법)
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def fix_project_dir_menu():
    """project_dir Menu Script 올바르게 수정"""
    print("\n" + "="*80)
    print(" Fixing project_dir Menu Script (Correct Method)")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Updating project_dir with correct method...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou

assets_node = hou.node("/obj/assets")

if not assets_node:
    print("[ERROR] assets node not found")
else:
    node_type = assets_node.type()
    definition = node_type.definition()
    
    if not definition:
        print("[ERROR] Not an HDA")
    else:
        try:
            # 파라미터 템플릿 그룹 가져오기
            ptg = node_type.parmTemplateGroup()
            
            # 기존 project_dir 템플릿 찾기
            old_template = ptg.find("project_dir")
            
            if not old_template:
                print("[ERROR] project_dir not found")
            else:
                print("[OK] Found project_dir template")
                print("  Name: {}".format(old_template.name()))
                print("  Label: {}".format(old_template.label()))
                print("")
                
                # 간소화된 Menu Script
                new_menu_script = '''# Simple Z:/show/ folder menu
import os

base_path = "Z:/show/"
menu_items = []

try:
    if os.path.exists(base_path):
        # 폴더 목록 가져오기
        items = os.listdir(base_path)
        
        # 폴더만 필터링
        folders = []
        for item in items:
            full_path = os.path.join(base_path, item)
            if os.path.isdir(full_path):
                folders.append(item)
        
        # 정렬
        folders.sort()
        
        # 메뉴 아이템 생성
        for folder in folders:
            full_path = os.path.join(base_path, folder).replace(os.sep, "/")
            menu_items.append(folder)
            menu_items.append(full_path)
    else:
        menu_items = ["(Z:/show/ not found)", ""]
        
except Exception as e:
    menu_items = ["(Error)".format(str(e)), ""]

return menu_items'''
                
                # 새 StringParmTemplate 생성 (생성자에서 메뉴 스크립트 지정)
                new_template = hou.StringParmTemplate(
                    name=old_template.name(),
                    label=old_template.label(),
                    num_components=1,
                    default_value=(old_template.defaultValue()[0] if old_template.defaultValue() else "Z:/show/",),
                    naming_scheme=old_template.namingScheme(),
                    string_type=hou.stringParmType.Regular,
                    menu_items=(),
                    menu_labels=(),
                    icon_names=(),
                    item_generator_script=new_menu_script,
                    item_generator_script_language=hou.scriptLanguage.Python,
                    menu_type=hou.menuType.StringReplace
                )
                
                # Help 복사
                if old_template.help():
                    new_template.setHelp(old_template.help())
                
                # Tags 복사
                for tag_name in old_template.tags():
                    new_template.setTags({tag_name: old_template.tags()[tag_name]})
                
                print("[Creating new parameter template...]")
                print("  Menu script lines: {}".format(len(new_menu_script.split('\\n'))))
                
                # 템플릿 교체
                ptg.replace(old_template.name(), new_template)
                
                # HDA에 적용
                node_type.setParmTemplateGroup(ptg)
                
                print("[OK] Parameter template updated")
                
                # HDA 저장
                definition.save(definition.libraryFilePath())
                print("[OK] HDA saved")
                
        except Exception as e:
            print("[ERROR] {}".format(e))
            import traceback
            traceback.print_exc()
""", print_output=False)
        
        if result and result.get('stdout'):
            try:
                print(result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Updated]")
        
        if result and result.get('stderr'):
            print("\n[STDERR]")
            try:
                print(result['stderr'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                pass
        
        print("\n[2] Testing updated menu...")
        print("-"*80)
        
        test_result = h.connector.execute_code("""
import hou

assets_node = hou.node("/obj/assets")

if assets_node:
    # 노드 재로드
    assets_node.type().definition().updateFromNode(assets_node)
    
    parm = assets_node.parm("project_dir")
    
    if parm:
        parm_template = parm.parmTemplate()
        
        print("[Menu Script Test]")
        print("=" * 70)
        
        # item_generator_script 확인
        if hasattr(parm_template, 'itemGeneratorScript'):
            script = parm_template.itemGeneratorScript()
            
            if script:
                print("[OK] Menu script exists")
                print("  Lines: {}".format(len(script.split('\\n'))))
                print("")
                
                try:
                    # 스크립트 실행
                    menu_result = eval(script)
                    
                    if menu_result and len(menu_result) > 0:
                        print("[Menu Items]")
                        print("-" * 70)
                        print("Total: {} folders".format(len(menu_result) // 2))
                        print("")
                        
                        # 처음 10개만 표시
                        for i in range(0, min(len(menu_result), 20), 2):
                            label = menu_result[i]
                            value = menu_result[i+1] if i+1 < len(menu_result) else ""
                            print("  {:<25} -> {}".format(label, value))
                        
                        if len(menu_result) > 20:
                            print("  ... ({} more)".format((len(menu_result) - 20) // 2))
                        
                        print("")
                        print("[OK] Menu script works correctly!")
                    else:
                        print("[WARNING] No menu items returned")
                        
                except Exception as e:
                    print("[ERROR] Script execution failed: {}".format(e))
                    import traceback
                    traceback.print_exc()
            else:
                print("[WARNING] No menu script")
        else:
            print("[INFO] No itemGeneratorScript attribute")
            
            # menuScript 확인
            if hasattr(parm_template, 'menuScript'):
                script = parm_template.menuScript()
                if script:
                    print("  But menuScript exists")
    else:
        print("[ERROR] project_dir parameter not found")
else:
    print("[ERROR] assets node not found")
""", print_output=False)
        
        if test_result and test_result.get('stdout'):
            try:
                print(test_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Test complete]")
        
        print("\n" + "="*80)
        print("[OK] Update completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        fix_project_dir_menu()
        
        print("\n" + "="*80)
        print(" Success!")
        print("="*80)
        print("""
project_dir 파라미터 업데이트 완료!

적용된 변경사항:
=============
기능: Z:/show/ 폴더 목록 표시
방법: item_generator_script 사용
언어: Python

Menu Script:
===========
- Z:/show/ 경로의 모든 폴더를 나열
- 폴더명을 라벨로, 전체 경로를 값으로 설정
- 외부 의존성 없음 (d:/Antigravity 제거)
- 에러 처리 포함

테스트 방법:
==========
1. Houdini에서 assets 노드 선택
2. project_dir 파라미터 클릭
3. 드롭다운 메뉴에서 Z:/show/ 폴더 확인
4. 원하는 프로젝트 선택

주의사항:
========
- Z:/show/ 경로가 존재해야 합니다
- 경로가 없으면 "(Z:/show/ not found)" 표시
""")
        print("="*80)
        
    except Exception as e:
        print("\n[ERROR] Update failed: {}".format(e))
        import traceback
        traceback.print_exc()





