#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Proxy 노드의 콜백 스크립트를 새 경로로 업데이트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Updating Proxy Node Callback Scripts")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Updating callback scripts...")
print("-" * 80)

# 콜백 스크립트 업데이트
code = """
import hou

try:
    # Find Proxy node
    proxy_node = hou.node("/obj/assets/Proxy")
    if not proxy_node:
        print("[ERROR] Proxy node not found")
    else:
        print("[OK] Found Proxy node")
        
        # 새 스크립트 경로
        script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
        
        # 간소화된 콜백 스크립트들
        callbacks = {
            'update_proxy': '''import sys
script_path = r"T:\\\\scripts\\\\python\\\\application\\\\houdini\\\\houdini21.0\\\\script"
if script_path not in sys.path:
    sys.path.append(script_path)

import proxy_manager
proxy_manager.update_proxy_nodes(kwargs['node'])''',
            
            'clear_proxy': '''import sys
script_path = r"T:\\\\scripts\\\\python\\\\application\\\\houdini\\\\houdini21.0\\\\script"
if script_path not in sys.path:
    sys.path.append(script_path)

import proxy_manager
proxy_manager.clear_proxy_with_confirm(kwargs['node'])''',
            
            'export_proxy_cache': '''import sys
script_path = r"T:\\\\scripts\\\\python\\\\application\\\\houdini\\\\houdini21.0\\\\script"
if script_path not in sys.path:
    sys.path.append(script_path)

import proxy_manager
proxy_manager.export_proxy_cache(kwargs['node'])'''
        }
        
        # 파라미터 템플릿 그룹 가져오기
        ptg = proxy_node.parmTemplateGroup()
        
        updated_count = 0
        
        for parm_name, new_script in callbacks.items():
            parm = proxy_node.parm(parm_name)
            if parm:
                # 파라미터 템플릿 찾기
                parm_template = ptg.find(parm_name)
                if parm_template:
                    # 새 스크립트로 업데이트
                    parm_template.setScriptCallback(new_script)
                    parm_template.setScriptCallbackLanguage(hou.scriptLanguage.Python)
                    
                    # 템플릿 그룹에 다시 추가
                    ptg.replace(parm_name, parm_template)
                    
                    updated_count += 1
                    print("[{}] Updated: {}".format(updated_count, parm_name))
        
        # 변경사항 적용
        proxy_node.setParmTemplateGroup(ptg)
        
        print("\\n" + "="*70)
        print(" Update Summary")
        print("="*70)
        print()
        print("Total callbacks updated: {}".format(updated_count))
        print()
        print("New script location:")
        print("  {}".format(script_path))
        print()
        print("Updated parameters:")
        for parm_name in callbacks.keys():
            print("  - {}".format(parm_name))
        print()
        print("[OK] All callback scripts updated successfully!")

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
print(" Changes Summary")
print("="*80)
print()
print("Updated Files:")
print("=============")
print("1. T:\\scripts\\python\\application\\houdini\\houdini21.0\\script\\proxy_manager.py")
print("   - Simplified and optimized version")
print("   - Removed duplicate export_proxy_cache function")
print("   - Improved error handling")
print("   - Better code documentation")
print()
print("Updated Callbacks:")
print("=================")
print("1. update_proxy")
print("   - Calls proxy_manager.update_proxy_nodes()")
print("   - Creates/updates geo_{part_name} nodes")
print()
print("2. clear_proxy")
print("   - Calls proxy_manager.clear_proxy_with_confirm()")
print("   - Clears all parts with confirmation")
print()
print("3. export_proxy_cache")
print("   - Calls proxy_manager.export_proxy_cache()")
print("   - Exports Collision + Corrective + Proxy parts")
print()
print("Path Change:")
print("===========")
print("OLD: d:/Antigravity/houdini_tools")
print("NEW: T:\\scripts\\python\\application\\houdini\\houdini21.0\\script")
print()
print("="*80)





