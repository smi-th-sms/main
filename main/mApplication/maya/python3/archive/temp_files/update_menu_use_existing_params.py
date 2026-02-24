#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
기존 파라미터를 사용하도록 메뉴 스크립트 업데이트
project_dir + assets_subdir 사용
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def update_menu_existing_params():
    """기존 파라미터를 사용하도록 메뉴 업데이트"""
    print("\n" + "="*80)
    print(" Update Menu Script - Use Existing Parameters")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Using existing parameters: project_dir + assets_subdir...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou

node = hou.node("/obj/assets")
if not node:
    print("[ERROR] Node not found")
else:
    node_type = node.type()
    definition = node_type.definition()
    
    if not definition:
        print("[ERROR] Node is not an HDA")
    else:
        try:
            # 사용할 파라미터 이름
            project_param = 'project_dir'
            subpath_param = 'assets_subdir'
            asset_name_param = 'assets_name'
            
            print(f"Using parameters:")
            print(f"  Project: {project_param}")
            print(f"  Subpath: {subpath_param}")
            print(f"  Asset Name: {asset_name_param}")
            
            # 파라미터 템플릿 그룹 가져오기
            ptg = definition.parmTemplateGroup()
            
            # Assets Name 파라미터 템플릿 찾기
            old_template = ptg.find(asset_name_param)
            
            if not old_template:
                print(f"[ERROR] Parameter '{asset_name_param}' not found")
            else:
                print(f"\\n[FOUND] Parameter: {asset_name_param}")
                
                # 폴더만 표시하는 메뉴 스크립트 (기존 파라미터 사용)
                menu_script = f'''import hou
import os

node = hou.pwd()

try:
    # 기존 파라미터 사용
    project_path = node.parm("{project_param}").eval()
    subpath = node.parm("{subpath_param}").eval()
    
    # 경로 조합
    full_path = os.path.join(project_path, subpath)
    full_path = os.path.normpath(full_path)
    
    # 경로 존재 확인
    if os.path.exists(full_path) and os.path.isdir(full_path):
        items = os.listdir(full_path)
        
        # 폴더만 필터링
        folders = []
        for item in items:
            item_path = os.path.join(full_path, item)
            if os.path.isdir(item_path):
                # 숨김 폴더 제외
                if not item.startswith('.'):
                    folders.append(item)
        
        # 메뉴 아이템 생성
        if folders:
            menu_items = []
            for folder in sorted(folders):
                menu_items.append(folder)
                menu_items.append(folder)
            
            return menu_items
        else:
            return ["", "No folders found"]
    else:
        return ["", f"Path not found: {{full_path}}"]
        
except Exception as e:
    return ["", f"Error: {{str(e)}}"]
'''
                
                # 새 StringParmTemplate 생성
                new_template = hou.StringParmTemplate(
                    asset_name_param,
                    old_template.label(),
                    1,
                    default_value=(old_template.defaultValue()[0] if old_template.defaultValue() else "",),
                    naming_scheme=hou.parmNamingScheme.Base1,
                    string_type=hou.stringParmType.Regular,
                    menu_type=hou.menuType.StringReplace,
                    menu_items=([]),
                    menu_labels=([]),
                    icon_names=([]),
                    item_generator_script=menu_script,
                    item_generator_script_language=hou.scriptLanguage.Python
                )
                
                # 기존 속성 복사
                try:
                    if hasattr(old_template, 'help') and old_template.help():
                        new_template.setHelp(old_template.help())
                except:
                    pass
                
                try:
                    if hasattr(old_template, 'tags') and old_template.tags():
                        new_template.setTags(old_template.tags())
                except:
                    pass
                
                # 템플릿 교체
                ptg.replace(asset_name_param, new_template)
                
                # HDA에 저장
                definition.setParmTemplateGroup(ptg)
                
                print(f"\\n[OK] Menu script updated!")
                print(f"  Using: {project_param} + {subpath_param}")
                print(f"  Menu will show folders only")
                
        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()
""", print_output=False)
        
        if result:
            print(result['stdout'])
            if result['stderr']:
                print("\n[STDERR]")
                print(result['stderr'])
        
        print("\n[2] Testing with current parameter values...")
        print("-"*80)
        h.execute("""
import hou
import os

node = hou.node("/obj/assets")
if node:
    # 파라미터 값 확인
    project_parm = node.parm("project_dir")
    subpath_parm = node.parm("assets_subdir")
    asset_name_parm = node.parm("assets_name")
    
    print(f"Current parameter values:")
    
    if project_parm:
        project_val = project_parm.eval()
        print(f"  project_dir: {project_val}")
    else:
        project_val = ""
        print(f"  project_dir: NOT FOUND")
    
    if subpath_parm:
        subpath_val = subpath_parm.eval()
        print(f"  assets_subdir: {subpath_val}")
    else:
        subpath_val = ""
        print(f"  assets_subdir: NOT FOUND")
    
    if asset_name_parm:
        asset_name_val = asset_name_parm.eval()
        print(f"  assets_name: {asset_name_val if asset_name_val else '(empty)'}")
    
    # 경로 조합 및 확인
    if project_val and subpath_val:
        full_path = os.path.join(project_val, subpath_val)
        full_path = os.path.normpath(full_path)
        
        print(f"\\nCombined path: {full_path}")
        
        if os.path.exists(full_path):
            print(f"  Status: EXISTS")
            
            # 폴더 목록
            items = os.listdir(full_path)
            folders = [item for item in items if os.path.isdir(os.path.join(full_path, item)) and not item.startswith('.')]
            
            print(f"  Folders: {len(folders)}")
            
            if folders and len(folders) > 0:
                print(f"\\n  Available folders (first 10):")
                for folder in sorted(folders)[:10]:
                    print(f"    - {folder}")
                
                if len(folders) > 10:
                    print(f"    ... and {len(folders) - 10} more")
        else:
            print(f"  Status: DOES NOT EXIST")
    else:
        print(f"\\n  Please set project_dir and assets_subdir values")
""")
        
        print("\n" + "="*80)
        print("[OK] Update completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        update_menu_existing_params()
        
        print("\n" + "="*80)
        print(" Final Instructions")
        print("="*80)
        print("""
설정 완료!

사용할 파라미터:
- project_dir (기존 파라미터)
- assets_subdir (기존 파라미터)  
- assets_name (폴더 선택 메뉴)

후디니에서 사용:
1. /obj/assets 노드 선택

2. 파라미터 설정:
   [project_dir] 설정
   예: Z:/show/PUBGOM
   
   [assets_subdir] 설정
   예: assets/Character
   
   [assets_name] 클릭
   -> 폴더 목록이 드롭다운에 표시됨

HDA 저장:
- /obj/assets 우클릭 > Type Properties > Save
- 또는 Operator Type Manager에서 저장

주의:
저장하지 않으면 후디니 재시작 시 설정이 초기화됩니다!
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Update failed: {e}")
        import traceback
        traceback.print_exc()






