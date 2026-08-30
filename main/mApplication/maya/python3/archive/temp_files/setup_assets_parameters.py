#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Assets 노드 파라미터 설정 스크립트
Project Path + Assets Subpath 조합으로 Assets Name 동적 메뉴 구성
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def setup_assets_parameters():
    """Assets Name 파라미터에 동적 메뉴 스크립트 설정"""
    print("\n" + "="*80)
    print(" Setup Assets Parameters - Dynamic Menu")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Checking current parameters...")
        print("-"*80)
        h.execute("""
import hou

node = hou.node("/obj/assets")
if node:
    print(f"Node: {node.path()}")
    print(f"Type: {node.type().name()}")
    
    # 현재 파라미터 확인
    param_names = [p.name() for p in node.parms()]
    
    print(f"\\nCurrent parameters ({len(param_names)} total):")
    
    # 관련 파라미터 찾기
    project_path_found = False
    assets_subpath_found = False
    assets_name_found = False
    
    for pname in param_names:
        if 'project' in pname.lower() and 'path' in pname.lower():
            print(f"  - {pname} (Project Path)")
            project_path_found = True
        elif 'subpath' in pname.lower():
            print(f"  - {pname} (Assets Subpath)")
            assets_subpath_found = True
        elif 'name' in pname.lower() and 'asset' in pname.lower():
            print(f"  - {pname} (Assets Name)")
            assets_name_found = True
    
    if not project_path_found:
        print("  [WARNING] Project Path parameter not found")
    if not assets_subpath_found:
        print("  [WARNING] Assets Subpath parameter not found")
    if not assets_name_found:
        print("  [WARNING] Assets Name parameter not found")
else:
    print("Node /obj/assets not found")
""")
        
        print("\n[2] Unlocking HDA for editing...")
        print("-"*80)
        h.execute("""
import hou

node = hou.node("/obj/assets")
if node:
    node_type = node.type()
    definition = node_type.definition()
    
    if definition:
        # HDA 라이브러리 경로
        lib_path = definition.libraryFilePath()
        print(f"HDA Library: {lib_path}")
        
        # 편집 가능 여부 확인
        try:
            # HDA가 잠겨있는지 확인
            is_locked = definition.hasSection("EditableNodes") == False
            print(f"Is Locked: {is_locked}")
            
            # HDA를 편집 가능하도록 설정
            print("\\nAttempting to allow editing...")
            node.allowEditingOfContents()
            print("[OK] HDA is now editable")
            
        except Exception as e:
            print(f"[INFO] {e}")
            print("You may need to manually unlock the HDA")
    else:
        print("[INFO] Node is not an HDA")
else:
    print("Node not found")
""")
        
        print("\n[3] Creating menu script for Assets Name parameter...")
        print("-"*80)
        
        # 동적 메뉴 스크립트 생성
        menu_script = '''
import hou
import os

# 현재 노드 가져오기
node = hou.pwd()

# Project Path 파라미터 값 가져오기
project_path_parm = node.parm("project_path")
if not project_path_parm:
    # 다른 이름일 수 있음
    for p in node.parms():
        if 'project' in p.name().lower() and 'path' in p.name().lower():
            project_path_parm = p
            break

# Assets Subpath 파라미터 값 가져오기
subpath_parm = node.parm("assets_subpath")
if not subpath_parm:
    # 다른 이름 시도
    for p in node.parms():
        if 'subpath' in p.name().lower():
            subpath_parm = p
            break

# 경로 조합
if project_path_parm and subpath_parm:
    project_path = project_path_parm.eval()
    subpath = subpath_parm.eval()
    
    # 경로 조합
    full_path = os.path.join(project_path, subpath)
    full_path = os.path.normpath(full_path)
    
    # 경로가 존재하는지 확인
    if os.path.exists(full_path) and os.path.isdir(full_path):
        # 디렉토리 내용 읽기
        try:
            items = os.listdir(full_path)
            
            # 디렉토리와 파일 분리
            dirs = []
            files = []
            
            for item in items:
                item_path = os.path.join(full_path, item)
                if os.path.isdir(item_path):
                    dirs.append(item)
                else:
                    # 특정 파일 확장자만 필터링 (예: .hip, .hda, .bgeo, .abc 등)
                    ext = os.path.splitext(item)[1].lower()
                    if ext in ['.hip', '.hiplc', '.hipnc', '.hda', '.otl', 
                               '.bgeo', '.bgeo.sc', '.abc', '.usd', '.usda', '.usdc',
                               '.fbx', '.obj', '.geo']:
                        files.append(item)
            
            # 메뉴 아이템 생성 (이름, 라벨 쌍)
            menu_items = []
            
            # 디렉토리 먼저
            for d in sorted(dirs):
                menu_items.append(d)
                menu_items.append(f"[DIR] {d}")
            
            # 파일
            for f in sorted(files):
                menu_items.append(f)
                menu_items.append(f)
            
            if menu_items:
                return menu_items
            else:
                return ["", "No items found"]
        except Exception as e:
            return ["", f"Error: {str(e)}"]
    else:
        return ["", f"Path not found: {full_path}"]
else:
    return ["", "Parameters not configured"]
'''
        
        print("Menu Script Created:")
        print("-"*60)
        print(menu_script[:500] + "...")
        
        print("\n[4] Applying menu script to HDA parameter template...")
        print("-"*80)
        
        result = h.connector.execute_code(f"""
import hou
import os

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
            # 파라미터 템플릿 그룹 가져오기
            ptg = definition.parmTemplateGroup()
            
            # Assets Name 파라미터 찾기
            assets_name_template = None
            assets_name_parm_name = None
            
            # 가능한 파라미터 이름들
            possible_names = ['assets_name', 'asset_name', 'assetname', 'name']
            
            for pname in possible_names:
                template = ptg.find(pname)
                if template:
                    assets_name_template = template
                    assets_name_parm_name = pname
                    break
            
            if not assets_name_template:
                # 모든 파라미터 검색
                for entry in ptg.entries():
                    if hasattr(entry, 'name'):
                        pname = entry.name()
                        if 'name' in pname.lower() and 'asset' in pname.lower():
                            assets_name_template = entry
                            assets_name_parm_name = pname
                            break
            
            if assets_name_template:
                print(f"[FOUND] Parameter: {{assets_name_parm_name}}")
                print(f"  Label: {{assets_name_template.label()}}")
                print(f"  Type: {{assets_name_template.type()}}")
                
                # 새로운 파라미터 템플릿 생성 (메뉴 스크립트 포함)
                new_template = hou.StringParmTemplate(
                    assets_name_parm_name,
                    assets_name_template.label(),
                    1,
                    default_value=assets_name_template.defaultValue() if hasattr(assets_name_template, 'defaultValue') else ("",),
                    naming_scheme=hou.parmNamingScheme.Base1,
                    string_type=hou.stringParmType.Regular,
                    menu_type=hou.menuType.StringReplace,
                    menu_items=([]),  # 빈 메뉴 아이템
                    menu_labels=([]),
                    icon_names=([]),
                    item_generator_script='''{menu_script}''',
                    item_generator_script_language=hou.scriptLanguage.Python,
                    menu_use_token=False
                )
                
                # Help와 Tags 복사 (있다면)
                if hasattr(assets_name_template, 'help'):
                    try:
                        new_template.setHelp(assets_name_template.help())
                    except:
                        pass
                
                if hasattr(assets_name_template, 'tags'):
                    try:
                        new_template.setTags(assets_name_template.tags())
                    except:
                        pass
                
                # 기존 템플릿 교체
                ptg.replace(assets_name_parm_name, new_template)
                
                # 변경사항 저장
                definition.setParmTemplateGroup(ptg)
                
                print("\\n[OK] Menu script applied successfully!")
                print(f"  Parameter '{{assets_name_parm_name}}' now has dynamic menu")
                print(f"  Menu will populate based on:")
                print(f"    Project Path + Assets Subpath")
                
            else:
                print("[ERROR] Assets Name parameter not found")
                print("\\nAvailable parameters:")
                for entry in ptg.entries():
                    if hasattr(entry, 'name'):
                        print(f"  - {{entry.name()}}")
                        
        except Exception as e:
            print(f"[ERROR] Failed to apply menu script: {{e}}")
            import traceback
            traceback.print_exc()
""", print_output=False)
        
        if result:
            print(result['stdout'])
            if result['stderr']:
                print("\n[STDERR]")
                print(result['stderr'])
        
        print("\n[5] Testing the dynamic menu...")
        print("-"*80)
        h.execute("""
import hou

node = hou.node("/obj/assets")
if node:
    # Assets Name 파라미터 찾기
    assets_name_parm = None
    
    for p in node.parms():
        if 'name' in p.name().lower() and 'asset' in p.name().lower():
            assets_name_parm = p
            break
    
    if assets_name_parm:
        print(f"Testing parameter: {assets_name_parm.name()}")
        
        try:
            # 메뉴 아이템 가져오기
            parm_template = assets_name_parm.parmTemplate()
            
            # 스크립트가 있는지 확인
            if hasattr(parm_template, 'menuType'):
                menu_type = parm_template.menuType()
                print(f"  Menu Type: {menu_type}")
            
            if hasattr(parm_template, 'itemGeneratorScript'):
                script = parm_template.itemGeneratorScript()
                if script:
                    print(f"  Menu Script: {len(script)} characters")
                    print(f"  Script (first 100 chars): {script[:100]}...")
                else:
                    print(f"  Menu Script: Not set")
            
            # 현재 메뉴 아이템 가져오기 시도
            try:
                menu_items = parm_template.menuItems()
                menu_labels = parm_template.menuLabels()
                print(f"\\n  Current menu has {len(menu_items)} items")
                
                if menu_items:
                    print(f"\\n  First few menu items:")
                    for i in range(min(5, len(menu_items))):
                        print(f"    - {menu_items[i]}: {menu_labels[i] if i < len(menu_labels) else 'N/A'}")
                    
                    if len(menu_items) > 5:
                        print(f"    ... and {len(menu_items) - 5} more")
            except Exception as e:
                print(f"  Could not get menu items: {e}")
                
        except Exception as e:
            print(f"  [ERROR] {e}")
    else:
        print("  Assets Name parameter not found")
""")
        
        print("\n" + "="*80)
        print("[OK] Setup completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        setup_assets_parameters()
        
        print("\n" + "="*80)
        print(" Usage Instructions")
        print("="*80)
        print("""
설정 완료!

사용 방법:
1. 후디니에서 /obj/assets 노드를 선택
2. Parameter 패널에서:
   - Project Path: 프로젝트 기본 경로 설정
     예: Z:/show/PUBGOM
   
   - Assets Subpath: 애셋 하위 경로 설정
     예: assets/Character/Jake/Geo
   
   - Assets Name: 드롭다운 메뉴에서 선택
     (Project Path + Assets Subpath 경로의 파일/폴더 목록이 표시됨)

동작 방식:
- Assets Name 파라미터를 클릭하면
- Project Path와 Assets Subpath를 조합한 경로에서
- 존재하는 파일과 폴더 목록을 자동으로 로드
- 지원 파일 형식:
  .hip, .hda, .otl, .bgeo, .abc, .usd, .fbx, .obj, .geo 등

참고:
- 경로가 존재하지 않으면 "Path not found" 메시지 표시
- 빈 폴더인 경우 "No items found" 표시
- 디렉토리는 [DIR] 접두사와 함께 표시

HDA 저장:
- 변경사항을 유지하려면 HDA를 저장해야 합니다
- Type Properties > Save 또는
- RMB on node > Type Properties > Save
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Setup failed: {e}")
        import traceback
        traceback.print_exc()






