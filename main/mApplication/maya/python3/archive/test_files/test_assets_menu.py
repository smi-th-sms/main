#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Assets Name 메뉴 테스트
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def test_assets_menu():
    """Assets Name 메뉴 테스트"""
    print("\n" + "="*80)
    print(" Test Assets Name Menu (Folders Only)")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Setting test paths...")
        print("-"*80)
        h.execute("""
import hou
import os

node = hou.node("/obj/assets")
if node:
    # 테스트 경로 설정
    test_project_path = "Z:/show/PUBGOM"
    test_subpath = "assets/Character"
    
    # 파라미터 설정
    project_parm = node.parm("project_path")
    subpath_parm = node.parm("assets_subpath")
    
    if project_parm:
        project_parm.set(test_project_path)
        print(f"  Project Path set to: {test_project_path}")
    else:
        print("  [WARNING] project_path parameter not found")
    
    if subpath_parm:
        subpath_parm.set(test_subpath)
        print(f"  Assets Subpath set to: {test_subpath}")
    else:
        print("  [WARNING] assets_subpath parameter not found")
    
    # 실제 경로 확인
    full_path = os.path.join(test_project_path, test_subpath)
    full_path = os.path.normpath(full_path)
    
    print(f"\\n  Combined path: {full_path}")
    
    if os.path.exists(full_path):
        print(f"  Status: Path exists!")
        
        # 폴더 목록
        items = os.listdir(full_path)
        folders = [item for item in items if os.path.isdir(os.path.join(full_path, item)) and not item.startswith('.')]
        
        print(f"  Folders: {len(folders)}")
        
        if folders:
            print(f"\\n  Available folders:")
            for folder in sorted(folders):
                print(f"    - {folder}")
        else:
            print(f"  (No folders found)")
    else:
        print(f"  Status: Path does not exist")
        print(f"  Please adjust the test paths in the script")
else:
    print("Node /obj/assets not found")
""")
        
        print("\n[2] Testing menu script directly...")
        print("-"*80)
        h.execute("""
import hou

node = hou.node("/obj/assets")
if node:
    asset_name_parm = node.parm("assets_name")
    
    if asset_name_parm:
        print(f"  Parameter: {asset_name_parm.name()}")
        
        # 메뉴 템플릿 확인
        parm_template = asset_name_parm.parmTemplate()
        
        print(f"  Menu Type: {parm_template.menuType()}")
        
        # 메뉴 스크립트 확인
        if hasattr(parm_template, 'itemGeneratorScript'):
            script = parm_template.itemGeneratorScript()
            print(f"  Menu Script: {len(script)} characters")
            
            # 스크립트 키워드 확인
            if 'isdir' in script:
                print(f"  [OK] Script filters for directories")
            if 'folders' in script.lower():
                print(f"  [OK] Script uses folder filtering")
        
        print(f"\\n  To see the menu in Houdini:")
        print(f"    1. Select /obj/assets node")
        print(f"    2. Find 'Assets Name' parameter")
        print(f"    3. Click the dropdown")
        print(f"    4. You should see folder names only")
    else:
        print("  assets_name parameter not found")
""")
        
        print("\n[3] Verifying menu contents...")
        print("-"*80)
        h.execute("""
import hou

node = hou.node("/obj/assets")
if node:
    asset_name_parm = node.parm("assets_name")
    
    if asset_name_parm:
        try:
            parm_template = asset_name_parm.parmTemplate()
            
            # 현재 메뉴 아이템
            menu_items = parm_template.menuItems()
            menu_labels = parm_template.menuLabels()
            
            print(f"  Current menu items: {len(menu_items)}")
            
            if menu_items:
                print(f"\\n  Menu contents:")
                for i in range(min(10, len(menu_items))):
                    print(f"    {i+1}. {menu_items[i]}")
                
                if len(menu_items) > 10:
                    print(f"    ... and {len(menu_items) - 10} more")
            else:
                print(f"  (Menu is dynamic - items appear when dropdown is clicked)")
                
        except Exception as e:
            print(f"  Note: {e}")
            print(f"  This is normal for dynamic menus")
""")
        
        print("\n" + "="*80)
        print("[OK] Test completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        test_assets_menu()
        
        print("\n" + "="*80)
        print(" Summary")
        print("="*80)
        print("""
Assets Name 파라미터 설정 완료!

기능:
- Project Path + Assets Subpath 경로의 폴더만 표시
- 파일은 제외
- 숨김 폴더 (. 시작) 제외
- 알파벳 순 정렬

후디니에서 확인:
1. /obj/assets 노드 선택
2. Project Path 설정 (예: Z:/show/PUBGOM)
3. Assets Subpath 설정 (예: assets/Character)
4. Assets Name 드롭다운 클릭
   -> 해당 경로의 폴더 목록 표시

HDA 저장 필수:
- /obj/assets 우클릭 > Type Properties > Save
- 저장하지 않으면 후디니 재시작 시 설정 초기화됨
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()






