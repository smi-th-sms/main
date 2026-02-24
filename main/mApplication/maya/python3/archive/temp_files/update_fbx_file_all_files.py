#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fbx_file 파라미터를 모든 FBX 파일 표시하도록 수정
(Assets Name 필터링 제거)
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def update_fbx_file_all():
    """fbx_file 파라미터를 모든 FBX 파일 표시하도록 업데이트"""
    print("\n" + "="*80)
    print(" Update FBX File Menu - Show All FBX Files")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Updating fbx_file menu script...")
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
                
                # 모든 FBX 파일을 표시하는 메뉴 스크립트
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
                    fbx_files.append(item)
        
        # 메뉴 아이템 생성
        if fbx_files:
            menu_items = []
            for fbx_file in sorted(fbx_files):
                menu_items.append(fbx_file)
                menu_items.append(fbx_file)
            
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
                print(f"  Menu will now show:")
                print(f"    - ALL FBX files in the directory")
                print(f"    - No filtering by Assets Name")
                print(f"    - Sorted alphabetically")
                
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
        
        print("\n[2] Testing the updated menu...")
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
            
            # 모든 FBX 파일 찾기
            items = os.listdir(full_path)
            fbx_files = []
            
            for item in items:
                item_path = os.path.join(full_path, item)
                if os.path.isfile(item_path):
                    ext = os.path.splitext(item)[1].lower()
                    if ext == '.fbx':
                        fbx_files.append(item)
            
            print(f"  Total FBX files: {len(fbx_files)}")
            
            if fbx_files:
                print(f"\\n  All FBX files in directory:")
                for i, fbx in enumerate(sorted(fbx_files), 1):
                    print(f"    {i}. {fbx}")
            else:
                print(f"  (No FBX files found)")
        else:
            print(f"  Status: DOES NOT EXIST")
    else:
        print(f"\\n  Please set all parameters to test")
""")
        
        print("\n[3] Checking guide_file parameter for comparison...")
        print("-"*80)
        h.execute("""
import hou

node = hou.node("/obj/assets")
if node:
    # guide_file 파라미터 찾기
    guide_file_parm = None
    
    for p in node.parms():
        if 'guide' in p.name().lower() and 'file' in p.name().lower():
            guide_file_parm = p
            break
    
    if guide_file_parm:
        print(f"Found: {guide_file_parm.name()}")
        
        # 파라미터 템플릿 확인
        parm_template = guide_file_parm.parmTemplate()
        
        print(f"  Type: {parm_template.type()}")
        print(f"  Menu Type: {parm_template.menuType()}")
        
        if hasattr(parm_template, 'itemGeneratorScript'):
            script = parm_template.itemGeneratorScript()
            if script:
                print(f"  Has menu script: Yes ({len(script)} chars)")
            else:
                print(f"  Has menu script: No")
    else:
        print("guide_file parameter not found")
        print("\\nAvailable file-related parameters:")
        for p in node.parms():
            if 'file' in p.name().lower():
                print(f"  - {p.name()}")
""")
        
        print("\n" + "="*80)
        print("[OK] Update completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        update_fbx_file_all()
        
        print("\n" + "="*80)
        print(" Usage Instructions")
        print("="*80)
        print("""
FBX File 파라미터 업데이트 완료!

변경사항:
========
- Assets Name 필터링 제거
- 폴더 내의 모든 FBX 파일 표시
- guide_file 처럼 작동

사용 방법:
=========

1. /obj/assets 노드 선택

2. 파라미터 설정:

   [project_dir]
   예: Z:/show/PUBGOM
   
   [assets_subdir]
   예: assets/Character
   
   [assets_name]
   예: Jake (폴더 선택)
   
   [fbx_subdir]
   예: RIG/wip/maya/fbx
   
   [fbx_file] (클릭)
   -> 해당 폴더의 모든 FBX 파일 표시

표시 규칙:
=========
- 지정된 경로의 모든 .fbx 파일
- 알파벳 순 정렬
- 파일명 필터링 없음

예시:
====
경로: Z:/show/PUBGOM/assets/Character/Jake/RIG/wip/maya/fbx/

표시되는 파일:
  1. Jake_Sim_v001.fbx
  2. Jake_Sim_v002.fbx
  3. Anna_Sim_v001.fbx    <- 이제 표시됨
  4. Body_v001.fbx        <- 이제 표시됨
  5. ...모든 FBX 파일

guide_file과 동일한 방식으로 작동합니다.

HDA 저장:
========
/obj/assets 우클릭 > Type Properties > Save
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Update failed: {e}")
        import traceback
        traceback.print_exc()






