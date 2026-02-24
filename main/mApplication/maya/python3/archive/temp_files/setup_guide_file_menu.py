#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
guide_file 파라미터에 동적 메뉴 설정
project_dir + assets_subdir + assets_name + guide_subdir 경로의 파일 선택
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def setup_guide_file_menu():
    """guide_file 파라미터에 동적 메뉴 설정"""
    print("\n" + "="*80)
    print(" Setup Guide File Dynamic Menu")
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
            print(f"  Found: {p.name()}")
        
        if 'assets' in pname and 'subdir' in pname:
            param_info['assets_subdir'] = p.name()
            print(f"  Found: {p.name()}")
        
        if 'assets' in pname and 'name' in pname:
            param_info['assets_name'] = p.name()
            print(f"  Found: {p.name()}")
        
        if 'guide' in pname and 'subdir' in pname:
            param_info['guide_subdir'] = p.name()
            print(f"  Found: {p.name()}")
        
        if 'guide' in pname and 'file' in pname:
            param_info['guide_file'] = p.name()
            print(f"  Found: {p.name()}")
    
    # 결과 저장
    hou.session.guide_param_info = param_info
    
    print(f"\\nParameter mapping:")
    for key, val in param_info.items():
        print(f"  {key}: {val}")
else:
    print("Node not found")
""")
        
        print("\n[2] Checking if guide_subdir parameter exists...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou

node = hou.node("/obj/assets")
if node:
    node_type = node.type()
    definition = node_type.definition()
    
    if definition:
        ptg = definition.parmTemplateGroup()
        
        # guide_subdir 파라미터 확인
        guide_subdir_exists = ptg.find("guide_subdir") is not None
        
        print(f"guide_subdir parameter exists: {guide_subdir_exists}")
        
        if not guide_subdir_exists:
            print("\\n[ADDING] guide_subdir parameter...")
            
            # guide_subdir 파라미터 추가
            guide_subdir_template = hou.StringParmTemplate(
                "guide_subdir",
                "Guide Subdirectory",
                1,
                default_value=("Geo",),
                string_type=hou.stringParmType.Regular,
                help="Subdirectory under Assets Name where guide files are located"
            )
            
            # guide_file 앞에 추가 (또는 assets_name 다음)
            if ptg.find("guide_file"):
                # guide_file이 있으면 그 앞에 추가
                guide_file_template = ptg.find("guide_file")
                # 부모 폴더 찾기
                parent_folder = None
                for entry in ptg.entries():
                    if hasattr(entry, 'containsFolder'):
                        try:
                            if entry.name() == ptg.containingFolder(guide_file_template):
                                parent_folder = entry
                                break
                        except:
                            pass
                
                # guide_file 직전에 추가
                try:
                    ptg.insertBefore(guide_file_template, guide_subdir_template)
                    print("[OK] guide_subdir parameter added before guide_file")
                except:
                    ptg.append(guide_subdir_template)
                    print("[OK] guide_subdir parameter appended")
            elif ptg.find("assets_name"):
                ptg.insertAfter("assets_name", guide_subdir_template)
                print("[OK] guide_subdir parameter added after assets_name")
            else:
                ptg.append(guide_subdir_template)
                print("[OK] guide_subdir parameter appended")
            
            definition.setParmTemplateGroup(ptg)
        else:
            print("[EXISTS] guide_subdir parameter already exists")
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
        
        print("\n[3] Setting up guide_file menu script...")
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
            guide_subdir_param = 'guide_subdir'
            guide_file_param = 'guide_file'
            
            # 파라미터 템플릿 그룹
            ptg = definition.parmTemplateGroup()
            
            # guide_file 파라미터 찾기
            old_template = ptg.find(guide_file_param)
            
            if not old_template:
                print(f"[ERROR] Parameter '{guide_file_param}' not found")
            else:
                print(f"[FOUND] Parameter: {guide_file_param}")
                
                # 가이드 파일 메뉴 스크립트 (전체 경로 저장)
                menu_script = f'''import hou
import os

node = hou.pwd()

try:
    # 파라미터 값 가져오기
    project_dir = node.parm("{project_param}").eval()
    assets_subdir = node.parm("{subdir_param}").eval()
    assets_name = node.parm("{asset_name_param}").eval()
    guide_subdir = node.parm("{guide_subdir_param}").eval()
    
    # 경로 조합
    full_path = os.path.join(project_dir, assets_subdir, assets_name, guide_subdir)
    full_path = os.path.normpath(full_path)
    
    # 경로 존재 확인
    if os.path.exists(full_path) and os.path.isdir(full_path):
        items = os.listdir(full_path)
        
        # 가이드 파일 필터링 (일반적인 지오메트리 파일 형식)
        guide_files = []
        valid_extensions = ['.bgeo', '.bgeo.sc', '.abc', '.usd', '.usda', '.usdc',
                           '.obj', '.fbx', '.geo', '.vdb', '.ply', '.stl']
        
        for item in items:
            item_path = os.path.join(full_path, item)
            
            # 파일인지 확인
            if os.path.isfile(item_path):
                # 확장자 확인 (복합 확장자 처리)
                item_lower = item.lower()
                is_valid = False
                
                for ext in valid_extensions:
                    if item_lower.endswith(ext):
                        is_valid = True
                        break
                
                if is_valid:
                    guide_files.append((item, item_path))
        
        # 메뉴 아이템 생성 (값: 전체 경로, 라벨: 파일명)
        if guide_files:
            menu_items = []
            for filename, filepath in sorted(guide_files):
                # 값: 전체 경로
                menu_items.append(filepath)
                # 라벨: 파일명만
                menu_items.append(filename)
            
            return menu_items
        else:
            return ["", "No guide files found"]
    else:
        return ["", f"Path not found: {{full_path}}"]
        
except Exception as e:
    return ["", f"Error: {{str(e)}}"]
'''
                
                # 새 StringParmTemplate 생성
                new_template = hou.StringParmTemplate(
                    guide_file_param,
                    old_template.label() if hasattr(old_template, 'label') else "Guide File",
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
                ptg.replace(guide_file_param, new_template)
                
                # HDA에 저장
                definition.setParmTemplateGroup(ptg)
                
                print(f"\\n[OK] Guide file menu script updated!")
                print(f"  Menu will show:")
                print(f"    - Files from: [project_dir]/[assets_subdir]/[assets_name]/[guide_subdir]")
                print(f"    - Supported formats: .bgeo, .abc, .usd, .obj, .fbx, .vdb, etc.")
                print(f"    - Display: filename (UI)")
                print(f"    - Store: full path (value)")
                
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
    guide_subdir = node.parm("guide_subdir").eval() if node.parm("guide_subdir") else ""
    
    print(f"Current parameter values:")
    print(f"  project_dir: {project_dir}")
    print(f"  assets_subdir: {assets_subdir}")
    print(f"  assets_name: {assets_name}")
    print(f"  guide_subdir: {guide_subdir}")
    
    if all([project_dir, assets_subdir, assets_name, guide_subdir]):
        # 경로 조합
        full_path = os.path.join(project_dir, assets_subdir, assets_name, guide_subdir)
        full_path = os.path.normpath(full_path)
        
        print(f"\\nCombined path: {full_path}")
        
        if os.path.exists(full_path):
            print(f"  Status: EXISTS")
            
            # 가이드 파일 찾기
            items = os.listdir(full_path)
            valid_extensions = ['.bgeo', '.bgeo.sc', '.abc', '.usd', '.usda', '.usdc',
                               '.obj', '.fbx', '.geo', '.vdb', '.ply', '.stl']
            
            guide_files = []
            for item in items:
                item_path = os.path.join(full_path, item)
                if os.path.isfile(item_path):
                    item_lower = item.lower()
                    for ext in valid_extensions:
                        if item_lower.endswith(ext):
                            guide_files.append((item, item_path))
                            break
            
            print(f"  Total guide files: {len(guide_files)}")
            
            if guide_files:
                print(f"\\n  Available guide files:")
                for i, (filename, filepath) in enumerate(sorted(guide_files)[:10], 1):
                    print(f"    {i}. {filename}")
                    print(f"       -> {filepath}")
                
                if len(guide_files) > 10:
                    print(f"    ... and {len(guide_files) - 10} more")
            else:
                print(f"  (No guide files found)")
        else:
            print(f"  Status: DOES NOT EXIST")
            print(f"  Try setting guide_subdir to an existing folder")
    else:
        print(f"\\n  Please set all parameters to test")
""")
        
        print("\n" + "="*80)
        print("[OK] Setup completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        setup_guide_file_menu()
        
        print("\n" + "="*80)
        print(" Usage Instructions")
        print("="*80)
        print("""
Guide File 파라미터 설정 완료!

사용 방법:
=========

1. /obj/assets 노드 선택

2. 파라미터를 순서대로 설정:

   [project_dir]
   예: Z:/show/PUBGOM
   
   [assets_subdir]
   예: assets/Character
   
   [assets_name] (드롭다운)
   예: Jake
   
   [guide_subdir]
   예: Geo (또는 Guide, Reference 등)
   
   [guide_file] (드롭다운 클릭)
   -> 해당 경로의 지오메트리 파일들이 표시됨

지원 파일 형식:
=============
- Houdini: .bgeo, .bgeo.sc, .geo
- Alembic: .abc
- USD: .usd, .usda, .usdc
- 3D: .obj, .fbx
- Volume: .vdb
- 기타: .ply, .stl

예시:
====

케이스 1: Jake 캐릭터 가이드 지오메트리
  project_dir: Z:/show/PUBGOM
  assets_subdir: assets/Character
  assets_name: Jake
  guide_subdir: Geo
  guide_file: [Jake_body.bgeo.sc, Jake_hair.abc, ...]

케이스 2: 레퍼런스 모델
  project_dir: Z:/show/PUBGOM
  assets_subdir: assets/Character
  assets_name: Jake
  guide_subdir: Reference
  guide_file: [Jake_ref_v001.usd, ...]

동작 방식:
=========
- UI: 파일명만 표시
- 값: 전체 경로 저장
- 다른 노드에서 바로 사용 가능

HDA 저장:
========
변경사항을 유지하려면:
  /obj/assets 우클릭 > Type Properties > Save
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Setup failed: {e}")
        import traceback
        traceback.print_exc()






