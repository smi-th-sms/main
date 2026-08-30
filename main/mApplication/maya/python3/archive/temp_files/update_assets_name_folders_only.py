#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Assets Name 파라미터를 폴더만 표시하도록 수정
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def update_to_folders_only():
    """Assets Name 파라미터를 폴더만 표시하도록 업데이트"""
    print("\n" + "="*80)
    print(" Update Assets Name - Folders Only")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Updating menu script to show folders only...")
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
            # 파라미터 이름
            project_path_parm = 'project_path'
            subpath_parm = 'assets_subpath'
            asset_name_parm = 'assets_name'
            
            # 파라미터 템플릿 그룹 가져오기
            ptg = definition.parmTemplateGroup()
            
            # Assets Name 파라미터 템플릿 찾기
            old_template = ptg.find(asset_name_parm)
            
            if not old_template:
                print(f"[ERROR] Parameter '{asset_name_parm}' not found")
            else:
                print(f"[FOUND] Parameter: {asset_name_parm}")
                
                # 폴더만 표시하는 메뉴 스크립트
                menu_script = f'''import hou
import os

node = hou.pwd()

try:
    # 파라미터 값 가져오기
    project_path = node.parm("{project_path_parm}").eval()
    subpath = node.parm("{subpath_parm}").eval()
    
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
                # 숨김 폴더 제외 (선택사항)
                if not item.startswith('.'):
                    folders.append(item)
        
        # 메뉴 아이템 생성 (폴더만)
        if folders:
            menu_items = []
            for folder in sorted(folders):
                menu_items.append(folder)
                menu_items.append(folder)  # 라벨과 값 동일
            
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
                    asset_name_parm,
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
                ptg.replace(asset_name_parm, new_template)
                
                # HDA에 저장
                definition.setParmTemplateGroup(ptg)
                
                print("\\n[OK] Menu script updated - Folders only!")
                print(f"\\nMenu script length: {len(menu_script)} characters")
                print(f"\\nThe Assets Name menu will now show:")
                print(f"  - Only folders (directories)")
                print(f"  - Located in: [Project Path] + [Assets Subpath]")
                print(f"  - Files are excluded")
                print(f"  - Hidden folders (starting with .) are excluded")
                
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
    print(f"Node: {node.path()}")
    
    # 파라미터 확인
    project_path_parm = node.parm("project_path")
    subpath_parm = node.parm("assets_subpath")
    asset_name_parm = node.parm("assets_name")
    
    print(f"\\nCurrent parameter values:")
    
    if project_path_parm:
        project_path = project_path_parm.eval()
        print(f"  Project Path: {project_path}")
    else:
        project_path = ""
        print(f"  Project Path: (not set)")
    
    if subpath_parm:
        subpath = subpath_parm.eval()
        print(f"  Assets Subpath: {subpath}")
    else:
        subpath = ""
        print(f"  Assets Subpath: (not set)")
    
    if asset_name_parm:
        asset_name = asset_name_parm.eval()
        print(f"  Assets Name: {asset_name if asset_name else '(not set)'}")
    
    # 실제 경로 확인
    if project_path and subpath:
        full_path = os.path.join(project_path, subpath)
        full_path = os.path.normpath(full_path)
        
        print(f"\\nCombined path: {full_path}")
        
        if os.path.exists(full_path):
            print(f"  Status: Path exists")
            
            # 폴더 개수 확인
            try:
                items = os.listdir(full_path)
                folders = [item for item in items if os.path.isdir(os.path.join(full_path, item)) and not item.startswith('.')]
                
                print(f"  Folders found: {len(folders)}")
                
                if folders:
                    print(f"\\n  Available folders (first 10):")
                    for folder in sorted(folders)[:10]:
                        print(f"    - {folder}")
                    
                    if len(folders) > 10:
                        print(f"    ... and {len(folders) - 10} more")
                else:
                    print(f"  (No folders in this directory)")
                    
            except Exception as e:
                print(f"  Error reading directory: {e}")
        else:
            print(f"  Status: Path does not exist")
    else:
        print(f"\\n  Please set Project Path and Assets Subpath to test the menu")
""")
        
        print("\n" + "="*80)
        print("[OK] Update completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        update_to_folders_only()
        
        print("\n" + "="*80)
        print(" Usage Guide")
        print("="*80)
        print("""
Assets Name 파라미터가 폴더만 표시하도록 업데이트되었습니다!

사용 방법:
=========

1. 후디니에서 /obj/assets 노드 선택

2. Parameters 설정:

   [Project Path]
   예: Z:/show/PUBGOM
   
   [Assets Subpath]  
   예: assets/Character
   
   [Assets Name] (클릭)
   → 드롭다운에 폴더 목록만 표시됩니다
   예: Jake, Anna, Bob, etc.

표시 내용:
=========
✅ 표시됨:
  - 폴더 (디렉토리)만
  - 알파벳 순으로 정렬
  - 일반 폴더명

❌ 제외됨:
  - 파일 (모든 형식)
  - 숨김 폴더 (.으로 시작)

예제 시나리오:
=============

시나리오 1: 캐릭터 선택
  Project Path: Z:/show/PUBGOM
  Assets Subpath: assets/Character
  Assets Name: [Jake, Anna, Bob, ...]

시나리오 2: 샷 선택
  Project Path: Z:/show/PUBGOM
  Assets Subpath: sequences/SZERO
  Assets Name: [SZERO_0010, SZERO_0020, SZERO_0030, ...]

시나리오 3: 하위 경로 탐색
  Project Path: Z:/show/PUBGOM
  Assets Subpath: assets/Character/Jake
  Assets Name: [Geo, Rig, Texture, ...]

HDA 저장:
=========
⚠️ 중요: 변경사항을 유지하려면 HDA를 저장하세요!

1. /obj/assets 노드 우클릭
2. Type Properties...
3. Save 버튼 클릭

또는

1. Windows > Operator Type Manager
2. Cinematic::assets::1.0 찾기
3. 우클릭 > Save Type Definition
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Update failed: {e}")
        import traceback
        traceback.print_exc()






