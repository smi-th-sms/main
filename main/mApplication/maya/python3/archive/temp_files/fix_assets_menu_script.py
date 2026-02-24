#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Assets Name 파라미터 메뉴 스크립트 수정 (Houdini 21 호환)
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def fix_menu_script():
    """Assets Name 메뉴 스크립트 수정"""
    print("\n" + "="*80)
    print(" Fix Assets Name Menu Script")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Finding parameter names...")
        print("-"*80)
        h.execute("""
import hou

node = hou.node("/obj/assets")
if node:
    # 파라미터 이름 확인
    param_info = {}
    
    for p in node.parms():
        pname = p.name().lower()
        
        if 'project' in pname and 'path' in pname:
            param_info['project_path'] = p.name()
            print(f"  Project Path parameter: {p.name()}")
        
        if 'subpath' in pname:
            param_info['subpath'] = p.name()
            print(f"  Subpath parameter: {p.name()}")
        
        if 'asset' in pname and 'name' in pname:
            param_info['asset_name'] = p.name()
            print(f"  Asset Name parameter: {p.name()}")
    
    # 결과 저장
    hou.session.asset_param_info = param_info
""")
        
        print("\n[2] Updating Assets Name parameter with menu script...")
        print("-"*80)
        
        result = h.connector.execute_code("""
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
            # 파라미터 정보 가져오기
            param_info = getattr(hou.session, 'asset_param_info', {})
            
            project_path_parm = param_info.get('project_path', 'project_path')
            subpath_parm = param_info.get('subpath', 'assets_subpath')
            asset_name_parm = param_info.get('asset_name', 'assets_name')
            
            print(f"Using parameter names:")
            print(f"  Project Path: {project_path_parm}")
            print(f"  Subpath: {subpath_parm}")
            print(f"  Asset Name: {asset_name_parm}")
            
            # 파라미터 템플릿 그룹 가져오기
            ptg = definition.parmTemplateGroup()
            
            # Assets Name 파라미터 템플릿 찾기
            old_template = ptg.find(asset_name_parm)
            
            if not old_template:
                print(f"[ERROR] Parameter '{asset_name_parm}' not found")
            else:
                print(f"\\n[FOUND] Parameter: {asset_name_parm}")
                print(f"  Label: {old_template.label()}")
                print(f"  Type: {old_template.type()}")
                
                # 메뉴 스크립트 생성
                menu_script = f'''import hou
import os

node = hou.pwd()

# 파라미터 값 가져오기
try:
    project_path = node.parm("{project_path_parm}").eval()
    subpath = node.parm("{subpath_parm}").eval()
    
    # 경로 조합
    full_path = os.path.join(project_path, subpath)
    full_path = os.path.normpath(full_path)
    
    # 경로 존재 확인
    if os.path.exists(full_path) and os.path.isdir(full_path):
        items = os.listdir(full_path)
        
        # 디렉토리와 파일 분리
        dirs = []
        files = []
        
        for item in items:
            item_path = os.path.join(full_path, item)
            if os.path.isdir(item_path):
                dirs.append(item)
            else:
                # 특정 확장자 필터링
                ext = os.path.splitext(item)[1].lower()
                if ext in ['.hip', '.hiplc', '.hipnc', '.hda', '.otl', 
                           '.bgeo', '.bgeo.sc', '.abc', '.usd', '.usda', '.usdc',
                           '.fbx', '.obj', '.geo', '.vdb']:
                    files.append(item)
        
        # 메뉴 아이템 생성
        menu_items = []
        
        # 디렉토리 먼저 (폴더 아이콘 표시)
        for d in sorted(dirs):
            menu_items.append(d)
            menu_items.append(f"[DIR] {{d}}")
        
        # 파일들
        for f in sorted(files):
            menu_items.append(f)
            menu_items.append(f)
        
        return menu_items if menu_items else ["", "Empty directory"]
    else:
        return ["", f"Path not found: {{full_path}}"]
        
except Exception as e:
    return ["", f"Error: {{str(e)}}"]
'''
                
                # 새 StringParmTemplate 생성 (Houdini 21 호환)
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
                
                try:
                    if hasattr(old_template, 'scriptCallbackLanguage'):
                        new_template.setScriptCallbackLanguage(old_template.scriptCallbackLanguage())
                except:
                    pass
                
                # 템플릿 교체
                ptg.replace(asset_name_parm, new_template)
                
                # HDA에 저장
                definition.setParmTemplateGroup(ptg)
                
                print("\\n[OK] Menu script updated successfully!")
                print(f"\\nMenu script length: {len(menu_script)} characters")
                print(f"\\nThe Assets Name menu will now show:")
                print(f"  - Contents of: [Project Path] + [Assets Subpath]")
                print(f"  - Directories with [DIR] prefix")
                print(f"  - Supported file types: .hip, .hda, .bgeo, .abc, .usd, .fbx, etc.")
                
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
        
        print("\n[3] Testing the updated menu...")
        print("-"*80)
        h.execute("""
import hou

node = hou.node("/obj/assets")
if node:
    # 파라미터 찾기
    asset_name_parm = None
    for p in node.parms():
        if 'asset' in p.name().lower() and 'name' in p.name().lower():
            asset_name_parm = p
            break
    
    if asset_name_parm:
        print(f"Testing: {asset_name_parm.name()}")
        
        try:
            parm_template = asset_name_parm.parmTemplate()
            
            # 스크립트 확인
            if hasattr(parm_template, 'itemGeneratorScript'):
                script = parm_template.itemGeneratorScript()
                print(f"  Menu script: {len(script)} characters")
                
                if script and len(script) > 200:
                    print(f"  [OK] Menu script is set")
                    
                    # 스크립트 일부 표시
                    lines = script.split('\\n')
                    print(f"\\n  First few lines:")
                    for i, line in enumerate(lines[:5], 1):
                        print(f"    {i}. {line[:70]}")
                else:
                    print(f"  [WARNING] Menu script seems short or empty")
            
            print(f"\\n  To test the menu:")
            print(f"    1. Set Project Path (e.g., Z:/show/PUBGOM)")
            print(f"    2. Set Assets Subpath (e.g., assets/Character)")
            print(f"    3. Click Assets Name dropdown to see contents")
            
        except Exception as e:
            print(f"  [ERROR] {e}")
""")
        
        print("\n" + "="*80)
        print("[OK] Menu script fix completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        fix_menu_script()
        
        print("\n" + "="*80)
        print(" Next Steps")
        print("="*80)
        print("""
Menu script가 성공적으로 설정되었습니다!

후디니에서 테스트:
1. /obj/assets 노드 선택
2. Parameters에서:
   
   [Project Path] 설정:
   예: Z:/show/PUBGOM
   
   [Assets Subpath] 설정:
   예: assets/Character/Jake/Geo
   
   [Assets Name] 클릭:
   → 드롭다운에 해당 경로의 파일/폴더 목록이 표시됩니다

동작 확인:
- 경로가 올바르면: 파일과 폴더 목록 표시
- 경로가 없으면: "Path not found" 메시지
- 빈 폴더: "Empty directory" 메시지

HDA 저장 (중요!):
이 변경사항을 유지하려면 HDA를 저장해야 합니다:

방법 1: Node에서 직접
- /obj/assets 노드에서 RMB
- Type Properties...
- Save 버튼 클릭

방법 2: Type Properties 창에서
- Windows > Operator Type Manager
- Cinematic::assets::1.0 찾기
- RMB > Save Type Definition

저장하지 않으면 후디니를 닫을 때 변경사항이 사라집니다!
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Fix failed: {e}")
        import traceback
        traceback.print_exc()






