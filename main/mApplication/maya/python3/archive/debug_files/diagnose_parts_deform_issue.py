#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parts_Deform 복제 문제 진단
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Diagnosing Parts_Deform Sync Issue")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Checking Proxy node cloth_parts...")
print("-" * 80)

code = """
import hou

try:
    proxy_node = hou.node("/obj/assets/Proxy")
    if not proxy_node:
        print("[ERROR] Proxy node not found")
    else:
        cloth_parts_parm = proxy_node.parm("cloth_parts")
        if cloth_parts_parm:
            count = cloth_parts_parm.evalAsInt()
            print("[INFO] cloth_parts count: {}".format(count))
            print()
            
            if count > 0:
                print("Part names:")
                for i in range(1, count + 1):
                    part_name_parm = proxy_node.parm("part_name_{}".format(i))
                    if part_name_parm:
                        part_name = part_name_parm.evalAsString()
                        print("  [{}] {}".format(i, part_name))
            else:
                print("[WARNING] No cloth parts defined!")
                print()
                print("To test Parts_Deform sync:")
                print("1. Add some parts in Proxy node (cloth_parts parameter)")
                print("2. Click update_proxy button")
        else:
            print("[ERROR] cloth_parts parameter not found")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[2] Checking which proxy_blast_sync module is loaded...")
print("-" * 80)

code = """
import sys

try:
    # proxy_blast_sync 모듈이 로드되어 있는지 확인
    if 'proxy_blast_sync' in sys.modules:
        module = sys.modules['proxy_blast_sync']
        module_file = getattr(module, '__file__', 'Unknown')
        print("[INFO] proxy_blast_sync is loaded from:")
        print("  {}".format(module_file))
        print()
        
        # sync_all_blast_locations 함수 확인
        if hasattr(module, 'sync_all_blast_locations'):
            func = getattr(module, 'sync_all_blast_locations')
            print("[OK] sync_all_blast_locations function exists")
            
            # 함수의 docstring으로 버전 확인
            doc = func.__doc__
            if doc:
                if 'Parts_Deform' in doc:
                    print("[OK] Function includes Parts_Deform sync (NEW VERSION)")
                else:
                    print("[WARNING] Function does NOT include Parts_Deform sync (OLD VERSION)")
            print()
        
        # sync_parts_deform_nodes 함수 확인
        if hasattr(module, 'sync_parts_deform_nodes'):
            print("[OK] sync_parts_deform_nodes function exists (NEW VERSION)")
        else:
            print("[WARNING] sync_parts_deform_nodes function NOT found (OLD VERSION)")
        print()
        
        # remove_all_parts_deform_nodes 함수 확인
        if hasattr(module, 'remove_all_parts_deform_nodes'):
            print("[OK] remove_all_parts_deform_nodes function exists (NEW VERSION)")
        else:
            print("[WARNING] remove_all_parts_deform_nodes function NOT found (OLD VERSION)")
        print()
        
        print("="*70)
        print(" Action Required")
        print("="*70)
        print()
        print("If OLD VERSION is detected:")
        print("1. Restart Houdini to reload modules")
        print("2. Or reload module manually with:")
        print("   import importlib")
        print("   importlib.reload(sys.modules['proxy_blast_sync'])")
    else:
        print("[INFO] proxy_blast_sync module not loaded yet")
        print("This is normal if update_proxy hasn't been executed yet.")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[3] Manually reloading proxy_blast_sync module...")
print("-" * 80)

code = """
import sys
import importlib

try:
    # 기존 모듈 언로드
    if 'proxy_blast_sync' in sys.modules:
        print("[INFO] Unloading old proxy_blast_sync module...")
        del sys.modules['proxy_blast_sync']
    
    # T:\scripts 경로 우선순위 설정
    script_path = r'T:\\scripts\\python\\application\\houdini\\houdini21.0\\script'
    if script_path not in sys.path:
        sys.path.insert(0, script_path)
        print("[INFO] Added {} to sys.path".format(script_path))
    else:
        # 이미 있다면 맨 앞으로 이동
        sys.path.remove(script_path)
        sys.path.insert(0, script_path)
        print("[INFO] Moved {} to front of sys.path".format(script_path))
    
    # 새로 import
    import proxy_blast_sync
    
    print("[OK] Reloaded proxy_blast_sync from:")
    print("  {}".format(proxy_blast_sync.__file__))
    print()
    
    # 함수 확인
    if hasattr(proxy_blast_sync, 'sync_parts_deform_nodes'):
        print("[OK] sync_parts_deform_nodes: Available")
    else:
        print("[ERROR] sync_parts_deform_nodes: NOT FOUND")
    
    if hasattr(proxy_blast_sync, 'remove_all_parts_deform_nodes'):
        print("[OK] remove_all_parts_deform_nodes: Available")
    else:
        print("[ERROR] remove_all_parts_deform_nodes: NOT FOUND")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Diagnosis completed!")
print("="*80)

connector.disconnect()





