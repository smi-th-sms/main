#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fbx_file 파라미터 값을 전체 경로로 표시하도록 수정
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def update_fbx_file_full_path():
    """fbx_file 파라미터 값을 전체 경로로 표시"""
    print("\n" + "="*80)
    print(" Update FBX File Menu - Show Full Paths")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Updating fbx_file menu script with full paths...")
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
        print("[ERROR] Not an HDA")
    else:
        try:
            # 파라미터 이름
            project_param = 'project_dir'
            subdir_param = 'assets_subdir'
            asset_name_param = 'assets_name'
            fbx_subdir_param = 'fbx_subdir'
            fbx_file_param = 'fbx_file'
            
            # 파라미터 템플릿 그룹
            ptg = definition.parmTemplateGroup()
            
            # fbx_file 파라미터 찾기
            old_template = ptg.find(fbx_file_param)
            
            if not old_template:
                print(f"[ERROR] Parameter '{fbx_file_param}' not found")
            else:
                print(f"[FOUND] Parameter: {fbx_file_param}")
                
                # 전체 경로를 반환하는 메뉴 스크립트
                menu_script = f'''import hou
import os

node = hou.pwd()

try:
    # 파라미터 값 가져오기
    project_dir = node.parm("{project_param}").eval()
    assets_subdir = node.parm("{subdir_param}").eval()
    assets_name = node.parm("{asset_name_param}").eval()
    fbx_subdir = node.parm("{fbx_subdir_param}").eval()
    
    # 경로 조합
    full_path = os.path.join(project_dir, assets_subdir, assets_name, fbx_subdir)
    full_path = os.path.normpath(full_path)
    
    # 경로 존재 확인
    if os.path.exists(full_path) and os.path.isdir(full_path):
        items = os.listdir(full_path)
        
        # 모든 FBX 파일 필터링
        fbx_files = []
        for item in items:
            item_path = os.path.join(full_path, item)
            
            # 파일이고 FBX 확장자인지 확인
            if os.path.isfile(item_path):
                ext = os.path.splitext(item)[1].lower()
                if ext == '.fbx':
                    # 전체 경로 저장
                    fbx_files.append((item, item_path))
        
        # 메뉴 아이템 생성 (값: 전체 경로, 라벨: 파일명)
        if fbx_files:
            menu_items = []
            for filename, filepath in sorted(fbx_files):
                # 값: 전체 경로
                menu_items.append(filepath)
                # 라벨: 파일명만 (UI에 표시)
                menu_items.append(filename)
            
            return menu_items
        else:
            return ["", "No FBX files found"]
    else:
        return ["", f"Path not found: {{full_path}}"]
        
except Exception as e:
    return ["", f"Error: {{str(e)}}"]
'''
                
                # 새 StringParmTemplate 생성
                new_template = hou.StringParmTemplate(
                    fbx_file_param,
                    old_template.label() if hasattr(old_template, 'label') else "FBX File",
                    1,
                    default_value=(old_template.defaultValue()[0] if hasattr(old_template, 'defaultValue') and old_template.defaultValue() else "",),
                    naming_scheme=hou.parmNamingScheme.Base1,
                    string_type=hou.stringParmType.FileReference,
                    file_type=hou.fileType.Geometry,
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
                ptg.replace(fbx_file_param, new_template)
                
                # HDA에 저장
                definition.setParmTemplateGroup(ptg)
                
                print(f"\\n[OK] FBX file menu script updated!")
                print(f"  Menu will now:")
                print(f"    - Display: filename (UI label)")
                print(f"    - Store: full path (parameter value)")
                print(f"    - Example: Jake_Sim_v001.fbx -> Z:/full/path/to/Jake_Sim_v001.fbx")
                
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
        
        print("\n[2] Testing with current values...")
        print("-"*80)
        h.execute("""
import hou
import os

node = hou.node("/obj/assets")
if node:
    # 현재 파라미터 값
    project_dir = node.parm("project_dir").eval() if node.parm("project_dir") else ""
    assets_subdir = node.parm("assets_subdir").eval() if node.parm("assets_subdir") else ""
    assets_name = node.parm("assets_name").eval() if node.parm("assets_name") else ""
    fbx_subdir = node.parm("fbx_subdir").eval() if node.parm("fbx_subdir") else ""
    
    print(f"Current parameter values:")
    print(f"  project_dir: {project_dir}")
    print(f"  assets_subdir: {assets_subdir}")
    print(f"  assets_name: {assets_name}")
    print(f"  fbx_subdir: {fbx_subdir}")
    
    if all([project_dir, assets_subdir, assets_name, fbx_subdir]):
        # 경로 조합
        full_path = os.path.join(project_dir, assets_subdir, assets_name, fbx_subdir)
        full_path = os.path.normpath(full_path)
        
        print(f"\\nCombined path: {full_path}")
        
        if os.path.exists(full_path):
            print(f"  Status: EXISTS")
            
            # 모든 FBX 파일과 전체 경로
            items = os.listdir(full_path)
            fbx_files = []
            
            for item in items:
                item_path = os.path.join(full_path, item)
                if os.path.isfile(item_path):
                    ext = os.path.splitext(item)[1].lower()
                    if ext == '.fbx':
                        fbx_files.append((item, item_path))
            
            print(f"  Total FBX files: {len(fbx_files)}")
            
            if fbx_files:
                print(f"\\n  Menu will show:")
                print(f"  " + "="*60)
                for i, (filename, filepath) in enumerate(sorted(fbx_files), 1):
                    print(f"  {i}. Label: {filename}")
                    print(f"     Value: {filepath}")
                    if i < len(fbx_files):
                        print()
            else:
                print(f"  (No FBX files found)")
        else:
            print(f"  Status: DOES NOT EXIST")
    else:
        print(f"\\n  Please set all parameters to test")
""")
        
        print("\n[3] Verifying the menu script...")
        print("-"*80)
        h.execute("""
import hou

node = hou.node("/obj/assets")
if node:
    fbx_file_parm = node.parm("fbx_file")
    
    if fbx_file_parm:
        print(f"Parameter: {fbx_file_parm.name()}")
        
        parm_template = fbx_file_parm.parmTemplate()
        
        if hasattr(parm_template, 'itemGeneratorScript'):
            script = parm_template.itemGeneratorScript()
            
            print(f"  Menu script length: {len(script)} characters")
            
            # 스크립트에 전체 경로 코드가 있는지 확인
            if 'item_path' in script and 'filepath' in script:
                print(f"  [OK] Script contains full path logic")
            
            if 'menu_items.append(filepath)' in script:
                print(f"  [OK] Script appends full path to menu items")
            
            print(f"\\n  When you click the dropdown:")
            print(f"    - UI shows: filename only")
            print(f"    - Value stored: full path")
    else:
        print("fbx_file parameter not found")
""")
        
        print("\n" + "="*80)
        print("[OK] Update completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        update_fbx_file_full_path()
        
        print("\n" + "="*80)
        print(" Usage Instructions")
        print("="*80)
        print("""
FBX File 파라미터 업데이트 완료!

변경사항:
========
- 메뉴에서 선택 시 전체 경로가 파라미터에 저장됨
- UI에는 파일명만 표시 (가독성)
- 실제 값은 전체 경로

동작 방식:
=========

1. 드롭다운 메뉴 클릭:
   표시: Jake_Sim_v001.fbx
   표시: Body_Export.fbx
   표시: Anna_Walk.fbx

2. 파일 선택 시:
   저장: Z:/show/PUBGOM/assets/Character/Jake/RIG/wip/maya/fbx/Jake_Sim_v001.fbx
   
3. 파라미터 값:
   전체 경로가 저장되어 다른 노드에서 바로 사용 가능

예시:
====

선택 전:
  fbx_file = ""

드롭다운에서 "Jake_Sim_v001.fbx" 선택:
  fbx_file = "Z:/show/PUBGOM/assets/Character/Jake/RIG/wip/maya/fbx/Jake_Sim_v001.fbx"

장점:
====
✓ 전체 경로가 저장되어 파일 참조가 명확
✓ 다른 노드에서 fbx_file 값을 그대로 사용 가능
✓ 경로 조합 불필요
✓ UI는 파일명만 표시하여 깔끔함

HDA 저장:
========
/obj/assets 우클릭 > Type Properties > Save
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Update failed: {e}")
        import traceback
        traceback.print_exc()






