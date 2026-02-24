#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fbx_file 파라미터에 동적 FBX 파일 메뉴 설정
project_dir + assets_subdir + assets_name + fbx_subdir 경로에서
Assets Name이 포함된 FBX 파일만 표시
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def setup_fbx_file_menu():
    """fbx_file 파라미터에 동적 메뉴 설정"""
    print("\n" + "="*80)
    print(" Setup FBX File Dynamic Menu")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Checking existing parameters...")
        print("-"*80)
        h.execute("""
import hou

node = hou.node("/obj/assets")
if node:
    print(f"Node: {node.path()}")
    
    # 관련 파라미터 확인
    param_info = {}
    
    for p in node.parms():
        pname = p.name().lower()
        
        if 'project' in pname and 'dir' in pname:
            param_info['project_dir'] = p.name()
            print(f"  Found: {p.name()} = {p.eval()}")
        
        if 'assets' in pname and 'subdir' in pname:
            param_info['assets_subdir'] = p.name()
            print(f"  Found: {p.name()} = {p.eval()}")
        
        if 'assets' in pname and 'name' in pname:
            param_info['assets_name'] = p.name()
            print(f"  Found: {p.name()} = {p.eval()}")
        
        if 'fbx' in pname and 'subdir' in pname:
            param_info['fbx_subdir'] = p.name()
            print(f"  Found: {p.name()} = {p.eval()}")
        
        if 'fbx' in pname and 'file' in pname:
            param_info['fbx_file'] = p.name()
            print(f"  Found: {p.name()} = {p.eval()}")
    
    # 결과 저장
    hou.session.fbx_param_info = param_info
    
    print(f"\\nParameter mapping:")
    for key, val in param_info.items():
        print(f"  {key}: {val}")
else:
    print("Node not found")
""")
        
        print("\n[2] Checking if fbx_subdir parameter exists...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou

node = hou.node("/obj/assets")
if node:
    node_type = node.type()
    definition = node_type.definition()
    
    if definition:
        ptg = definition.parmTemplateGroup()
        
        # fbx_subdir 파라미터 확인
        fbx_subdir_exists = ptg.find("fbx_subdir") is not None
        
        print(f"fbx_subdir parameter exists: {fbx_subdir_exists}")
        
        if not fbx_subdir_exists:
            print("\\n[ADDING] fbx_subdir parameter...")
            
            # fbx_subdir 파라미터 추가
            fbx_subdir_template = hou.StringParmTemplate(
                "fbx_subdir",
                "FBX Subdirectory",
                1,
                default_value=("Anim",),
                string_type=hou.stringParmType.Regular,
                help="Subdirectory under Assets Name where FBX files are located"
            )
            
            # assets_name 다음에 추가
            if ptg.find("assets_name"):
                ptg.insertAfter("assets_name", fbx_subdir_template)
            else:
                ptg.append(fbx_subdir_template)
            
            definition.setParmTemplateGroup(ptg)
            print("[OK] fbx_subdir parameter added")
        else:
            print("[EXISTS] fbx_subdir parameter already exists")
    else:
        print("Not an HDA")
else:
    print("Node not found")
""", print_output=False)
        
        if result:
            print(result['stdout'])
            if result['stderr']:
                print("\n[STDERR]")
                print(result['stderr'])
        
        print("\n[3] Setting up fbx_file menu script...")
        print("-"*80)
        
        result2 = h.connector.execute_code("""
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
                
                # FBX 파일 메뉴 스크립트
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
        
        # FBX 파일 필터링 + Assets Name 포함 필터
        fbx_files = []
        for item in items:
            item_path = os.path.join(full_path, item)
            
            # 파일이고 FBX 확장자인지 확인
            if os.path.isfile(item_path):
                ext = os.path.splitext(item)[1].lower()
                if ext == '.fbx':
                    # Assets Name이 파일명에 포함되어 있는지 확인
                    if assets_name and assets_name.lower() in item.lower():
                        fbx_files.append(item)
        
        # 메뉴 아이템 생성
        if fbx_files:
            menu_items = []
            for fbx_file in sorted(fbx_files):
                menu_items.append(fbx_file)
                menu_items.append(fbx_file)
            
            return menu_items
        else:
            if assets_name:
                return ["", f"No FBX files containing '{{assets_name}}'"]
            else:
                return ["", "Set Assets Name first"]
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
                print(f"  Menu will show:")
                print(f"    - FBX files from: [project_dir]/[assets_subdir]/[assets_name]/[fbx_subdir]")
                print(f"    - Only files containing Assets Name in filename")
                print(f"    - Example: Jake_walk.fbx, Jake_run.fbx (if Assets Name = 'Jake')")
                
        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()
""", print_output=False)
        
        if result2:
            print(result2['stdout'])
            if result2['stderr']:
                print("\n[STDERR]")
                print(result2['stderr'])
        
        print("\n[4] Testing the menu...")
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
    
    print(f"Current values:")
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
            
            # FBX 파일 찾기
            items = os.listdir(full_path)
            fbx_files = []
            
            for item in items:
                item_path = os.path.join(full_path, item)
                if os.path.isfile(item_path):
                    ext = os.path.splitext(item)[1].lower()
                    if ext == '.fbx':
                        # Assets Name 포함 여부 확인
                        if assets_name.lower() in item.lower():
                            fbx_files.append(item)
            
            print(f"  FBX files with '{assets_name}': {len(fbx_files)}")
            
            if fbx_files:
                print(f"\\n  Available FBX files:")
                for fbx in sorted(fbx_files)[:10]:
                    print(f"    - {fbx}")
                
                if len(fbx_files) > 10:
                    print(f"    ... and {len(fbx_files) - 10} more")
            else:
                print(f"  (No FBX files containing '{assets_name}' found)")
        else:
            print(f"  Status: DOES NOT EXIST")
            print(f"  Please check the path or set fbx_subdir")
    else:
        print(f"\\n  Please set all parameters to test")
""")
        
        print("\n" + "="*80)
        print("[OK] Setup completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        setup_fbx_file_menu()
        
        print("\n" + "="*80)
        print(" Usage Instructions")
        print("="*80)
        print("""
FBX File 파라미터 설정 완료!

사용 방법:
=========

1. /obj/assets 노드 선택

2. 파라미터를 순서대로 설정:

   [project_dir]
   예: Z:/show/PUBGOM
   
   [assets_subdir]
   예: assets/Character
   
   [assets_name]
   예: Jake (드롭다운에서 선택)
   
   [fbx_subdir]
   예: Anim (또는 FBX 파일이 있는 하위 폴더명)
   
   [fbx_file] (클릭)
   -> Assets Name이 포함된 FBX 파일만 표시됨

예시:
====

케이스 1: Jake 캐릭터 애니메이션
  project_dir: Z:/show/PUBGOM
  assets_subdir: assets/Character
  assets_name: Jake
  fbx_subdir: Anim
  fbx_file: [Jake_walk.fbx, Jake_run.fbx, ...]
  
  실제 경로: Z:/show/PUBGOM/assets/Character/Jake/Anim/
  표시 파일: Jake가 포함된 .fbx 파일만

케이스 2: 다른 폴더 구조
  project_dir: Z:/show/PUBGOM
  assets_subdir: sequences/SZERO/SZERO_0010
  assets_name: Jake
  fbx_subdir: Export
  fbx_file: [Jake_SZERO_0010_v001.fbx, ...]

필터링 규칙:
===========
✓ 표시됨:
  - .fbx 확장자 파일
  - Assets Name이 파일명에 포함된 파일
  - 대소문자 구분 안함

✗ 제외됨:
  - Assets Name이 없는 FBX 파일
  - 다른 확장자 파일
  - 폴더

HDA 저장:
========
⚠️ 중요: 변경사항을 유지하려면 HDA를 저장하세요!
  
  /obj/assets 우클릭 > Type Properties > Save
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Setup failed: {e}")
        import traceback
        traceback.print_exc()






