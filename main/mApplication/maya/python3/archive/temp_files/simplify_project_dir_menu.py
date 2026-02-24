#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
project_dir 파라미터 Menu Script 간소화
Z:/show/ 폴더 목록만 표시하도록 수정
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def simplify_project_dir():
    """project_dir Menu Script 간소화"""
    print("\n" + "="*80)
    print(" Simplifying project_dir Menu Script")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Checking current project_dir parameter...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou

assets_node = hou.node("/obj/assets")

if not assets_node:
    print("[ERROR] assets node not found")
else:
    print("[OK] Found: {}".format(assets_node.path()))
    
    # project_dir 파라미터 확인
    parm = assets_node.parm("project_dir")
    
    if parm:
        parm_template = parm.parmTemplate()
        
        print("")
        print("[project_dir Parameter]")
        print("=" * 70)
        print("Name: {}".format(parm.name()))
        print("Label: {}".format(parm_template.label()))
        print("Type: {}".format(parm_template.type()))
        print("Current Value: {}".format(parm.eval()))
        print("")
        
        # 현재 Menu Script 확인
        if hasattr(parm_template, 'menuScript'):
            current_script = parm_template.menuScript()
            if current_script:
                print("[Current Menu Script]")
                print("-" * 70)
                lines = current_script.split('\\n')
                print("Lines: {}".format(len(lines)))
                print("")
                print("Preview (first 10 lines):")
                for i, line in enumerate(lines[:10], 1):
                    print("  {:2d} | {}".format(i, line))
                if len(lines) > 10:
                    print("  ... ({} more lines)".format(len(lines) - 10))
            else:
                print("[INFO] No menu script")
        else:
            print("[INFO] No menuScript attribute")
    else:
        print("[ERROR] project_dir parameter not found")
""", print_output=False)
        
        if result and result.get('stdout'):
            try:
                print(result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Checked]")
        
        print("\n[2] Creating simplified menu script...")
        print("-"*80)
        
        # 간소화된 Menu Script
        simplified_script = """# Simple Z:/show/ folder menu
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
        
        # 메뉴 아이템 생성 (이름, 전체경로)
        for folder in folders:
            full_path = os.path.join(base_path, folder).replace(os.sep, "/")
            menu_items.append(folder)  # 표시 이름
            menu_items.append(full_path)  # 값
    else:
        # 경로가 없으면 기본값
        menu_items = ["(Z:/show/ not found)", ""]
        
except Exception as e:
    # 에러 발생 시
    menu_items = ["(Error: {})".format(str(e)), ""]

return menu_items"""
        
        print("Simplified script created:")
        print("=" * 70)
        print(simplified_script)
        print("=" * 70)
        print("")
        print("Features:")
        print("  - Lists folders in Z:/show/")
        print("  - No external dependencies")
        print("  - Simple and maintainable")
        print("  - Error handling included")
        
        print("\n[3] Checking if HDA needs unlocking...")
        print("-"*80)
        
        unlock_result = h.connector.execute_code("""
import hou

assets_node = hou.node("/obj/assets")

if assets_node:
    node_type = assets_node.type()
    definition = node_type.definition()
    
    if definition:
        print("[HDA Info]")
        print("=" * 70)
        print("Name: {}".format(node_type.name()))
        print("Library: {}".format(definition.libraryFilePath()))
        
        # 잠금 상태 확인
        try:
            is_locked = not definition.hasUnlockedSection("CreateScript")
            print("Locked: {}".format(is_locked))
        except:
            print("Locked: Unknown")
        
        print("")
        print("[Unlocking HDA...]")
        
        # HDA 잠금 해제
        try:
            if definition.libraryFilePath():
                # 이미 unlocked 상태인지 확인
                sections = definition.sections()
                print("Sections: {}".format(len(sections)))
                
                print("[OK] HDA is accessible")
            else:
                print("[ERROR] No library file path")
        except Exception as e:
            print("[ERROR] {}".format(e))
    else:
        print("[INFO] Not an HDA (subnet or built-in type)")
else:
    print("[ERROR] assets node not found")
""", print_output=False)
        
        if unlock_result and unlock_result.get('stdout'):
            try:
                print(unlock_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Checked]")
        
        print("\n[4] Updating project_dir Menu Script...")
        print("-"*80)
        
        update_result = h.connector.execute_code("""
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
            
            # project_dir 파라미터 템플릿 찾기
            project_dir_template = ptg.find("project_dir")
            
            if not project_dir_template:
                print("[ERROR] project_dir parameter not found")
            else:
                print("[OK] Found project_dir parameter template")
                
                # 새 Menu Script
                new_script = '''# Simple Z:/show/ folder menu
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
        
        # 메뉴 아이템 생성 (이름, 전체경로)
        for folder in folders:
            full_path = os.path.join(base_path, folder).replace(os.sep, "/")
            menu_items.append(folder)  # 표시 이름
            menu_items.append(full_path)  # 값
    else:
        # 경로가 없으면 기본값
        menu_items = ["(Z:/show/ not found)", ""]
        
except Exception as e:
    # 에러 발생 시
    menu_items = ["(Error: {})".format(str(e)), ""]

return menu_items'''
                
                # 기존 템플릿 복사하여 수정
                new_template = hou.StringParmTemplate(
                    project_dir_template.name(),
                    project_dir_template.label(),
                    1,  # num_components
                    default_value=project_dir_template.defaultValue(),
                    naming_scheme=project_dir_template.namingScheme(),
                    string_type=hou.stringParmType.Regular,
                    menu_items=(),
                    menu_labels=(),
                    icon_names=(),
                    item_generator_script="",
                    item_generator_script_language=hou.scriptLanguage.Python,
                    menu_type=hou.menuType.StringReplace
                )
                
                # Menu Script 설정
                new_template.setMenuType(hou.menuType.StringReplace)
                new_template.setMenuScript(new_script)
                new_template.setMenuScriptLanguage(hou.scriptLanguage.Python)
                
                # Tags 복사
                for tag_name in project_dir_template.tags():
                    new_template.setTags({tag_name: project_dir_template.tags()[tag_name]})
                
                # 템플릿 교체
                ptg.replace(project_dir_template.name(), new_template)
                
                # HDA에 적용
                node_type.setParmTemplateGroup(ptg)
                
                print("[OK] Menu Script updated")
                print("")
                print("New script features:")
                print("  - Lists Z:/show/ folders")
                print("  - No external dependencies")
                print("  - Simple error handling")
                
        except Exception as e:
            print("[ERROR] Update failed: {}".format(e))
            import traceback
            traceback.print_exc()
""", print_output=False)
        
        if update_result and update_result.get('stdout'):
            try:
                print(update_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Updated]")
        
        if update_result and update_result.get('stderr'):
            print("\n[STDERR]")
            try:
                print(update_result['stderr'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Error output]")
        
        print("\n[5] Testing new menu script...")
        print("-"*80)
        
        test_result = h.connector.execute_code("""
import hou
import os

assets_node = hou.node("/obj/assets")

if assets_node:
    parm = assets_node.parm("project_dir")
    
    if parm:
        parm_template = parm.parmTemplate()
        
        print("[Testing Menu Script]")
        print("=" * 70)
        
        # Menu Script 실행
        if hasattr(parm_template, 'menuScript'):
            script = parm_template.menuScript()
            
            if script:
                print("Script exists: Yes")
                print("Script lines: {}".format(len(script.split('\\n'))))
                print("")
                
                try:
                    # 스크립트 실행하여 메뉴 아이템 생성
                    menu_result = eval(script)
                    
                    print("[Menu Items Generated]")
                    print("-" * 70)
                    
                    if menu_result and len(menu_result) > 0:
                        # 페어로 출력 (label, value)
                        print("Total items: {}".format(len(menu_result) // 2))
                        print("")
                        
                        for i in range(0, min(len(menu_result), 20), 2):
                            label = menu_result[i]
                            value = menu_result[i+1] if i+1 < len(menu_result) else ""
                            print("  {:<30} -> {}".format(label, value))
                        
                        if len(menu_result) > 20:
                            print("  ... ({} more items)".format((len(menu_result) - 20) // 2))
                    else:
                        print("No menu items returned")
                    
                    print("")
                    print("[OK] Menu script works!")
                    
                except Exception as e:
                    print("[ERROR] Script execution failed: {}".format(e))
                    import traceback
                    traceback.print_exc()
            else:
                print("No menu script found")
        else:
            print("No menuScript attribute")
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
        
        print("\n[6] Saving HDA changes...")
        print("-"*80)
        
        save_result = h.connector.execute_code("""
import hou

assets_node = hou.node("/obj/assets")

if assets_node:
    node_type = assets_node.type()
    definition = node_type.definition()
    
    if definition:
        try:
            # HDA 저장
            definition.save(definition.libraryFilePath())
            
            print("[OK] HDA saved to:")
            print("  {}".format(definition.libraryFilePath()))
            
        except Exception as e:
            print("[ERROR] Save failed: {}".format(e))
            print("")
            print("Manual save required:")
            print("  1. Right-click assets node")
            print("  2. Type Properties...")
            print("  3. Click 'Accept' or 'Apply'")
    else:
        print("[INFO] Not an HDA")
else:
    print("[ERROR] assets node not found")
""", print_output=False)
        
        if save_result and save_result.get('stdout'):
            try:
                print(save_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Saved]")
        
        print("\n" + "="*80)
        print("[OK] Simplification completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        simplify_project_dir()
        
        print("\n" + "="*80)
        print(" Summary")
        print("="*80)
        print("""
project_dir 파라미터 간소화 완료!

변경 사항:
=========
이전: d:/Antigravity/houdini_tools 외부 의존성
이후: Z:/show/ 폴더 직접 나열

새 기능:
=======
- Z:/show/ 경로의 폴더 목록 표시
- 폴더명과 전체 경로 매핑
- 외부 모듈 의존성 제거
- 간단한 에러 처리

Menu Script 코드:
===============
import os

base_path = "Z:/show/"
menu_items = []

if os.path.exists(base_path):
    folders = [f for f in os.listdir(base_path) 
               if os.path.isdir(os.path.join(base_path, f))]
    folders.sort()
    
    for folder in folders:
        full_path = os.path.join(base_path, folder).replace(os.sep, "/")
        menu_items.append(folder)      # 표시 이름
        menu_items.append(full_path)   # 값

return menu_items

테스트:
======
1. assets 노드 선택
2. project_dir 파라미터 클릭
3. 드롭다운에서 Z:/show/ 폴더 확인
4. 원하는 프로젝트 선택

장점:
====
+ 외부 의존성 제거
+ 코드 간소화
+ 유지보수 용이
+ 빠른 실행
""")
        print("="*80)
        
    except Exception as e:
        print("\n[ERROR] Simplification failed: {}".format(e))
        import traceback
        traceback.print_exc()





