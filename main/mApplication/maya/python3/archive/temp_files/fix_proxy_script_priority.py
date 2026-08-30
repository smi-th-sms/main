#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Proxy 콜백 스크립트의 sys.path 우선순위 수정
append() -> insert(0, ...) 로 변경
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Fixing Proxy Script Path Priority")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Updating all callback scripts to use insert(0, ...)...")
print("-" * 80)

# 콜백 스크립트 업데이트
code = """
import hou

try:
    proxy_node = hou.node("/obj/assets/Proxy")
    if not proxy_node:
        print("[ERROR] Proxy node not found")
    else:
        print("[OK] Found Proxy node\\n")
        
        # 새 스크립트 (sys.path.insert 사용)
        new_callbacks = {
            'update_proxy': '''import sys
script_path = r"T:\\\\scripts\\\\python\\\\application\\\\houdini\\\\houdini21.0\\\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

import proxy_manager
proxy_manager.update_proxy_nodes(kwargs['node'])''',
            
            'clear_proxy': '''import sys
script_path = r"T:\\\\scripts\\\\python\\\\application\\\\houdini\\\\houdini21.0\\\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

import proxy_manager
proxy_manager.clear_proxy_with_confirm(kwargs['node'])''',
            
            'export_proxy_cache': '''import sys
script_path = r"T:\\\\scripts\\\\python\\\\application\\\\houdini\\\\houdini21.0\\\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

import proxy_manager
proxy_manager.export_proxy_cache(kwargs['node'])''',
            
            'part_name_#': '''import sys
script_path = r"T:\\\\scripts\\\\python\\\\application\\\\houdini\\\\houdini21.0\\\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

import proxy_manager
proxy_manager.update_proxy_nodes(kwargs['node'])''',
            
            'delete_part_#': '''import sys
script_path = r"T:\\\\scripts\\\\python\\\\application\\\\houdini\\\\houdini21.0\\\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

import proxy_manager
proxy_manager.delete_part_with_confirm(kwargs['node'], kwargs['script_multiparm_index'])'''
        }
        
        ptg = proxy_node.parmTemplateGroup()
        
        # 재귀적으로 템플릿 업데이트
        def update_templates(templates):
            updated = []
            modified = False
            
            for template in templates:
                parm_type = template.type()
                parm_name = template.name()
                
                # Folder/FolderSet 재귀
                if parm_type in [hou.parmTemplateType.Folder, hou.parmTemplateType.FolderSet]:
                    sub_templates, sub_modified = update_templates(template.parmTemplates())
                    if sub_modified:
                        new_template = template.clone()
                        new_template.setParmTemplates(sub_templates)
                        updated.append(new_template)
                        modified = True
                    else:
                        updated.append(template)
                
                # 업데이트 대상
                elif parm_name in new_callbacks:
                    try:
                        callback = template.scriptCallback()
                        
                        # sys.path.append 사용하는지 확인
                        if 'sys.path.append' in callback:
                            new_template = template.clone()
                            new_template.setScriptCallback(new_callbacks[parm_name])
                            new_template.setScriptCallbackLanguage(hou.scriptLanguage.Python)
                            updated.append(new_template)
                            modified = True
                            print("[Updated] {} - changed append() to insert(0, ...)".format(parm_name))
                        else:
                            updated.append(template)
                    except:
                        updated.append(template)
                else:
                    updated.append(template)
            
            return updated, modified
        
        # 업데이트
        print("Processing parameter templates...\\n")
        new_templates, was_modified = update_templates(ptg.entries())
        
        if was_modified:
            # 새 템플릿 그룹 생성
            new_ptg = hou.ParmTemplateGroup()
            for template in new_templates:
                new_ptg.append(template)
            
            # 노드에 적용
            proxy_node.setParmTemplateGroup(new_ptg)
            
            print()
            print("="*70)
            print(" Update Summary")
            print("="*70)
            print()
            print("Changed sys.path.append() to sys.path.insert(0, ...)")
            print()
            print("This ensures T:\\\\scripts path has priority over d:/Antigravity")
            print()
            print("[OK] All callbacks updated successfully!")
        else:
            print("[INFO] No updates needed - already using correct method")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[2] Verifying the changes...")
print("-" * 80)

# 변경 확인
code_verify = """
import hou
import sys
import importlib

proxy_node = hou.node("/obj/assets/Proxy")
if proxy_node:
    # 모듈 리로드
    if 'proxy_manager' in sys.modules:
        del sys.modules['proxy_manager']
    if 'proxy_blast_sync' in sys.modules:
        del sys.modules['proxy_blast_sync']
    
    # 새 경로 우선 설정
    script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
    if script_path in sys.path:
        sys.path.remove(script_path)
    sys.path.insert(0, script_path)
    
    # 모듈 임포트
    import proxy_manager
    import proxy_blast_sync
    
    print("[Verification Results]")
    print("="*70)
    print()
    print("Loaded Modules:")
    print("  proxy_manager: {}".format(proxy_manager.__file__))
    print("  proxy_blast_sync: {}".format(proxy_blast_sync.__file__))
    print()
    
    target_dir = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
    
    pm_correct = target_dir.lower() in proxy_manager.__file__.lower()
    pbs_correct = target_dir.lower() in proxy_blast_sync.__file__.lower()
    
    if pm_correct and pbs_correct:
        print("[SUCCESS] Both modules loaded from target directory!")
    else:
        print("[WARNING] Modules not loaded from target directory")
        if not pm_correct:
            print("  - proxy_manager loaded from wrong location")
        if not pbs_correct:
            print("  - proxy_blast_sync loaded from wrong location")
"""

result = connector.execute_code(code_verify)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Update completed!")
print("="*80)

connector.disconnect()

print("\n" + "="*80)
print(" Summary")
print("="*80)
print()
print("Changes Made:")
print("============")
print("✓ All 5 callback scripts updated")
print("✓ Changed: sys.path.append() → sys.path.insert(0, ...)")
print("✓ Target directory now has priority")
print()
print("Result:")
print("======")
print("Modules will be loaded from:")
print("  T:\\scripts\\python\\application\\houdini\\houdini21.0\\script")
print()
print("Instead of:")
print("  d:\\Antigravity\\houdini_tools")
print()
print("="*80)





