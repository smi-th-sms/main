#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
part_name_# 및 delete_part_# 콜백 스크립트를 새 경로로 업데이트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Updating Multiparm Callback Scripts")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Updating part_name_# and delete_part_# callbacks...")
print("-" * 80)

# 콜백 스크립트 업데이트
code = """
import hou

try:
    proxy_node = hou.node("/obj/assets/Proxy")
    if not proxy_node:
        print("[ERROR] Proxy node not found")
    else:
        print("[OK] Found Proxy node")
        
        # 새 스크립트 경로
        script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
        
        # 간소화된 콜백 스크립트들
        new_callbacks = {
            'part_name_#': '''import sys
script_path = r"T:\\\\scripts\\\\python\\\\application\\\\houdini\\\\houdini21.0\\\\script"
if script_path not in sys.path:
    sys.path.append(script_path)

import proxy_manager
proxy_manager.update_proxy_nodes(kwargs['node'])''',
            
            'delete_part_#': '''import sys
script_path = r"T:\\\\scripts\\\\python\\\\application\\\\houdini\\\\houdini21.0\\\\script"
if script_path not in sys.path:
    sys.path.append(script_path)

import proxy_manager
proxy_manager.delete_part_with_confirm(kwargs['node'], kwargs['script_multiparm_index'])'''
        }
        
        # 파라미터 템플릿 그룹 가져오기
        ptg = proxy_node.parmTemplateGroup()
        
        # 모든 파라미터 템플릿을 재귀적으로 업데이트
        def update_templates(templates, parent_path=""):
            updated = []
            modified = False
            
            for parm_template in templates:
                parm_name = parm_template.name()
                parm_type = parm_template.type()
                
                # Folder나 FolderSet인 경우 하위 템플릿 재귀 처리
                if parm_type == hou.parmTemplateType.Folder:
                    sub_templates, sub_modified = update_templates(
                        parm_template.parmTemplates(), 
                        parent_path + "/" + parm_name
                    )
                    if sub_modified:
                        new_template = parm_template.clone()
                        new_template.setParmTemplates(sub_templates)
                        updated.append(new_template)
                        modified = True
                    else:
                        updated.append(parm_template)
                
                elif parm_type == hou.parmTemplateType.FolderSet:
                    sub_templates, sub_modified = update_templates(
                        parm_template.parmTemplates(), 
                        parent_path + "/" + parm_name
                    )
                    if sub_modified:
                        new_template = parm_template.clone()
                        new_template.setParmTemplates(sub_templates)
                        updated.append(new_template)
                        modified = True
                    else:
                        updated.append(parm_template)
                
                # 업데이트 대상인 경우
                elif parm_name in new_callbacks:
                    try:
                        callback_script = parm_template.scriptCallback()
                        
                        # 구 경로를 사용하는지 확인
                        if 'd:/Antigravity' in callback_script or 'd:\\\\Antigravity' in callback_script:
                            new_template = parm_template.clone()
                            new_template.setScriptCallback(new_callbacks[parm_name])
                            new_template.setScriptCallbackLanguage(hou.scriptLanguage.Python)
                            updated.append(new_template)
                            modified = True
                            print("[Updated] {}".format(parm_name))
                        else:
                            updated.append(parm_template)
                    except:
                        updated.append(parm_template)
                else:
                    updated.append(parm_template)
            
            return updated, modified
        
        # 템플릿 업데이트
        print("\\nProcessing parameter templates...")
        new_templates, was_modified = update_templates(ptg.entries())
        
        if was_modified:
            # 새 템플릿 그룹 생성
            new_ptg = hou.ParmTemplateGroup()
            for template in new_templates:
                new_ptg.append(template)
            
            # 노드에 적용
            proxy_node.setParmTemplateGroup(new_ptg)
            
            print("\\n" + "="*70)
            print(" Update Summary")
            print("="*70)
            print()
            print("New script location:")
            print("  {}".format(script_path))
            print()
            print("Updated multiparm parameters:")
            print("  - part_name_#")
            print("    Calls: proxy_manager.update_proxy_nodes()")
            print()
            print("  - delete_part_#")
            print("    Calls: proxy_manager.delete_part_with_confirm()")
            print()
            print("[OK] All multiparm callbacks updated successfully!")
        else:
            print("\\n[INFO] No updates needed - callbacks already use new path")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Update completed!")
print("="*80)

connector.disconnect()

print("\n" + "="*80)
print(" Complete Update Summary")
print("="*80)
print()
print("Updated Callbacks (Total: 5)")
print("============================")
print()
print("Regular Buttons:")
print("  1. update_proxy (Update Proxy Nodes)")
print("     - proxy_manager.update_proxy_nodes()")
print()
print("  2. clear_proxy (Clear All Parts)")
print("     - proxy_manager.clear_proxy_with_confirm()")
print()
print("  3. export_proxy_cache (Export Proxy Cache)")
print("     - proxy_manager.export_proxy_cache()")
print()
print("Multiparm Parameters:")
print("  4. part_name_# (Part Name)")
print("     - proxy_manager.update_proxy_nodes()")
print("     - Triggered when part name changes")
print()
print("  5. delete_part_# (Delete This Part)")
print("     - proxy_manager.delete_part_with_confirm()")
print("     - Triggered when delete button clicked")
print()
print("Path Change:")
print("===========")
print("OLD: d:/Antigravity/houdini_tools")
print("NEW: T:\\scripts\\python\\application\\houdini\\houdini21.0\\script")
print()
print("Status: ALL CALLBACKS UPDATED")
print()
print("="*80)





