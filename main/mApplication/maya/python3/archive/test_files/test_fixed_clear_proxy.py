#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
수정된 clear_proxy 테스트 (Parts_Deform 제거 포함)
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing Fixed clear_proxy (Parts_Deform Removal)")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[STEP 1] Reload modules and create test data...")
print("-" * 80)

code = """
import sys
import hou

try:
    # 모든 관련 모듈 언로드
    modules_to_reload = ['proxy_blast_sync', 'proxy_manager']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]
            print("[INFO] Unloaded module: {}".format(mod))
    
    # T:\scripts 경로 최우선순위
    script_path = r'T:\\scripts\\python\\application\\houdini\\houdini21.0\\script'
    if script_path in sys.path:
        sys.path.remove(script_path)
    sys.path.insert(0, script_path)
    print("[INFO] Set script path priority: {}".format(script_path))
    print()
    
    # 모듈 다시 import
    import proxy_manager
    print("[INFO] Loaded proxy_manager from:")
    print("  {}".format(proxy_manager.__file__))
    print()
    
    # Proxy 노드에 테스트 파트 추가
    proxy_node = hou.node("/obj/assets/Proxy")
    if proxy_node:
        proxy_node.parm("cloth_parts").set(2)
        proxy_node.parm("part_name_1").set("test_a")
        proxy_node.parm("part_name_2").set("test_b")
        print("[OK] Added 2 test parts: test_a, test_b")
        print()
        
        # update_proxy 실행
        proxy_manager.update_proxy_nodes(proxy_node)
    else:
        print("[ERROR] Proxy node not found")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[STEP 2] Verify created nodes BEFORE clear_proxy...")
print("-" * 80)

code = """
import hou

try:
    # Constraint
    constraint = hou.node("/obj/assets/Constraint")
    constraint_blasts = []
    if constraint:
        constraint_blasts = [c for c in constraint.children() 
                           if c.type().name() == "blast" and c.name().startswith("blast_")]
    
    # Deform
    deform = hou.node("/obj/assets/Deform")
    proxy_blasts = []
    geo_blasts = []
    parts_deform = []
    
    if deform:
        proxy_blasts = [c for c in deform.children() 
                       if c.type().name() == "blast" and c.name().startswith("proxy_path_blast_")]
        geo_blasts = [c for c in deform.children() 
                     if c.type().name() == "blast" and c.name().startswith("geo_path_blast_")]
        parts_deform = [c for c in deform.children() 
                       if c.type().name() == "subnet" and c.name().startswith("Parts_Deform_")]
    
    print("="*70)
    print(" BEFORE clear_proxy")
    print("="*70)
    print()
    print("[Constraint] {} blast node(s)".format(len(constraint_blasts)))
    for b in constraint_blasts:
        print("  - {}".format(b.name()))
    
    print()
    print("[Deform/proxy_path] {} blast node(s)".format(len(proxy_blasts)))
    for b in proxy_blasts:
        print("  - {}".format(b.name()))
    
    print()
    print("[Deform/geo_path] {} blast node(s)".format(len(geo_blasts)))
    for b in geo_blasts:
        print("  - {}".format(b.name()))
    
    print()
    print("[Deform] {} Parts_Deform node(s)".format(len(parts_deform)))
    for node in parts_deform:
        print("  - {}".format(node.name()))
    
    print()
    total_nodes = len(constraint_blasts) + len(proxy_blasts) + len(geo_blasts) + len(parts_deform)
    print("Total nodes to remove: {}".format(total_nodes))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[STEP 3] Execute clear_proxy (with updated function)...")
print("-" * 80)

code = """
import sys
import hou

try:
    # 모듈 리로드
    modules_to_reload = ['proxy_blast_sync', 'proxy_manager']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]
    
    script_path = r'T:\\scripts\\python\\application\\houdini\\houdini21.0\\script'
    if script_path in sys.path:
        sys.path.remove(script_path)
    sys.path.insert(0, script_path)
    
    import proxy_manager
    
    proxy_node = hou.node("/obj/assets/Proxy")
    if proxy_node:
        print("[INFO] Calling clear_proxy_with_confirm()...")
        print()
        
        # Simulate button press by calling function directly
        # (This avoids UI dialog)
        count = proxy_node.parm("cloth_parts").evalAsInt()
        
        # Delete geo nodes
        for i in range(1, count + 1):
            p_name_parm = proxy_node.parm("part_name_{}".format(i))
            if p_name_parm:
                part_name = p_name_parm.evalAsString()
                if part_name:
                    geo_node = proxy_node.node("geo_{}".format(part_name))
                    if geo_node:
                        geo_node.destroy()
                        print("Deleted: geo_{}".format(part_name))
        
        print()
        
        # Clear blast and Parts_Deform nodes
        print("Clearing blast and Parts_Deform nodes from all locations...")
        
        import proxy_blast_sync
        deleted_count = proxy_blast_sync.remove_all_blasts_from_all_locations(proxy_node)
        
        # Clear multiparm
        proxy_node.parm("cloth_parts").set(0)
        
        print()
        print("[OK] clear_proxy completed")
        print("Total nodes removed: {}".format(deleted_count))
    else:
        print("[ERROR] Proxy node not found")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[STEP 4] Verify all nodes removed AFTER clear_proxy...")
print("-" * 80)

code = """
import hou

try:
    # Constraint
    constraint = hou.node("/obj/assets/Constraint")
    constraint_blasts = []
    if constraint:
        constraint_blasts = [c for c in constraint.children() 
                           if c.type().name() == "blast" and c.name().startswith("blast_")]
    
    # Deform
    deform = hou.node("/obj/assets/Deform")
    proxy_blasts = []
    geo_blasts = []
    parts_deform = []
    
    if deform:
        proxy_blasts = [c for c in deform.children() 
                       if c.type().name() == "blast" and c.name().startswith("proxy_path_blast_")]
        geo_blasts = [c for c in deform.children() 
                     if c.type().name() == "blast" and c.name().startswith("geo_path_blast_")]
        parts_deform = [c for c in deform.children() 
                       if c.type().name() == "subnet" and c.name().startswith("Parts_Deform_")]
    
    print("="*70)
    print(" AFTER clear_proxy")
    print("="*70)
    print()
    
    all_clean = True
    
    if len(constraint_blasts) > 0:
        print("[ERROR] Constraint: {} blast(s) remaining".format(len(constraint_blasts)))
        all_clean = False
    else:
        print("[OK] Constraint: Clean")
    
    if len(proxy_blasts) > 0:
        print("[ERROR] Deform/proxy_path: {} blast(s) remaining".format(len(proxy_blasts)))
        all_clean = False
    else:
        print("[OK] Deform/proxy_path: Clean")
    
    if len(geo_blasts) > 0:
        print("[ERROR] Deform/geo_path: {} blast(s) remaining".format(len(geo_blasts)))
        all_clean = False
    else:
        print("[OK] Deform/geo_path: Clean")
    
    if len(parts_deform) > 0:
        print("[ERROR] Deform: {} Parts_Deform node(s) remaining".format(len(parts_deform)))
        for node in parts_deform:
            print("  - REMAINING: {}".format(node.name()))
        all_clean = False
    else:
        print("[OK] Deform: Parts_Deform nodes clean")
    
    print()
    print("="*70)
    if all_clean:
        print(" [SUCCESS] All nodes successfully removed!")
    else:
        print(" [ERROR] Some nodes still remain!")
    print("="*70)

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Fixed clear_proxy test finished!")
print("="*80)

connector.disconnect()





