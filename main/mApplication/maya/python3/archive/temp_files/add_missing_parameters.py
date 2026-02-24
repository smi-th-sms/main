#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
project_path와 assets_subpath 파라미터 추가
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def add_missing_parameters():
    """누락된 파라미터 추가"""
    print("\n" + "="*80)
    print(" Add Missing Parameters")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Checking existing parameters...")
        print("-"*80)
        h.execute("""
import hou

node = hou.node("/obj/assets")
if node:
    # 기존 파라미터 확인
    existing_parms = [p.name() for p in node.parms()]
    
    has_project_path = any('project' in p.lower() and 'path' in p.lower() for p in existing_parms)
    has_subpath = any('subpath' in p.lower() for p in existing_parms)
    has_asset_name = any('asset' in p.lower() and 'name' in p.lower() for p in existing_parms)
    
    print(f"  Total parameters: {len(existing_parms)}")
    print(f"  Has project_path: {has_project_path}")
    print(f"  Has assets_subpath: {has_subpath}")
    print(f"  Has assets_name: {has_asset_name}")
    
    # 관련 파라미터 표시
    print(f"\\n  Related parameters:")
    for p in existing_parms:
        if 'project' in p.lower() or 'path' in p.lower() or 'asset' in p.lower():
            print(f"    - {p}")
""")
        
        print("\n[2] Adding missing parameters to HDA...")
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
            ptg = definition.parmTemplateGroup()
            
            # 기존 파라미터 확인
            existing = [p.name() for p in ptg.entries()]
            
            added_count = 0
            
            # 1. project_path 파라미터 추가 (없는 경우)
            if 'project_path' not in existing:
                project_path_template = hou.StringParmTemplate(
                    "project_path",
                    "Project Path",
                    1,
                    default_value=("Z:/show/PUBGOM",),
                    string_type=hou.stringParmType.FileReference,
                    file_type=hou.fileType.Directory,
                    help="Base project directory path"
                )
                
                # 파라미터 그룹 앞쪽에 추가
                ptg.insertBefore(0, project_path_template)
                added_count += 1
                print("[ADDED] project_path parameter")
            else:
                print("[EXISTS] project_path parameter already exists")
            
            # 2. assets_subpath 파라미터 추가 (없는 경우)
            if 'assets_subpath' not in existing:
                subpath_template = hou.StringParmTemplate(
                    "assets_subpath",
                    "Assets Subpath",
                    1,
                    default_value=("assets/Character",),
                    string_type=hou.stringParmType.Regular,
                    help="Subdirectory path relative to Project Path"
                )
                
                # project_path 다음에 추가
                if 'project_path' in existing or added_count > 0:
                    ptg.insertAfter("project_path", subpath_template)
                else:
                    ptg.insertBefore(0, subpath_template)
                    
                added_count += 1
                print("[ADDED] assets_subpath parameter")
            else:
                print("[EXISTS] assets_subpath parameter already exists")
            
            if added_count > 0:
                # 변경사항 저장
                definition.setParmTemplateGroup(ptg)
                print(f"\\n[OK] Added {added_count} parameter(s) successfully!")
                print(f"\\nYou now have:")
                print(f"  - project_path (Project Path)")
                print(f"  - assets_subpath (Assets Subpath)")
                print(f"  - assets_name (Assets Name) - with dynamic folder menu")
            else:
                print(f"\\n[INFO] All required parameters already exist")
                
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
        
        print("\n[3] Verifying parameters...")
        print("-"*80)
        h.execute("""
import hou

node = hou.node("/obj/assets")
if node:
    print(f"Node: {node.path()}")
    print(f"\\nParameters:")
    
    # 주요 파라미터 확인
    for pname in ['project_path', 'assets_subpath', 'assets_name']:
        parm = node.parm(pname)
        if parm:
            print(f"  [{pname}]")
            print(f"    Label: {parm.description()}")
            print(f"    Value: {parm.eval()}")
        else:
            print(f"  [{pname}] NOT FOUND")
""")
        
        print("\n" + "="*80)
        print("[OK] Parameters setup completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        add_missing_parameters()
        
        print("\n" + "="*80)
        print(" Complete Usage Instructions")
        print("="*80)
        print("""
파라미터 설정 완료!

이제 후디니에서 사용할 수 있습니다:

단계별 사용법:
=============

1. /obj/assets 노드 선택

2. 파라미터 패널에서 다음 순서로 설정:

   [Project Path] (프로젝트 기본 경로)
   예: Z:/show/PUBGOM
   
   [Assets Subpath] (애셋 하위 경로)
   예: assets/Character
   
   [Assets Name] (폴더 선택)
   클릭하면 위 경로의 폴더 목록이 표시됩니다
   예: Jake, Anna, Bob, etc.

실제 경로 예시:
==============

케이스 1: 캐릭터 Geo
  Project Path: Z:/show/PUBGOM
  Assets Subpath: assets/Character/Jake/Geo
  Assets Name: [v001, v002, latest, ...]

케이스 2: 시퀀스 샷
  Project Path: Z:/show/PUBGOM
  Assets Subpath: sequences/SZERO
  Assets Name: [SZERO_0010, SZERO_0020, ...]

케이스 3: 캐릭터 선택
  Project Path: Z:/show/PUBGOM
  Assets Subpath: assets/Character
  Assets Name: [Jake, Anna, Bob, ...]

HDA 저장 필수!
=============
변경사항을 유지하려면:

방법 1:
  - /obj/assets 우클릭
  - Type Properties...
  - Save 버튼

방법 2:
  - Windows > Operator Type Manager
  - Cinematic::assets::1.0 찾기
  - 우클릭 > Save Type Definition

저장하지 않으면 후디니 재시작 시 초기화됩니다!
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Setup failed: {e}")
        import traceback
        traceback.print_exc()






