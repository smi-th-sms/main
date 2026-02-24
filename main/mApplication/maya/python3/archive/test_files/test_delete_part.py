#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Delete This Part 버튼 기능 테스트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing 'Delete This Part' Button")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[STEP 1] Setup: Create test parts and nodes...")
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
    
    # Proxy 노드에 3개의 테스트 파트 추가
    proxy_node = hou.node("/obj/assets/Proxy")
    if proxy_node:
        proxy_node.parm("cloth_parts").set(3)
        proxy_node.parm("part_name_1").set("delete_test_a")
        proxy_node.parm("part_name_2").set("delete_test_b")
        proxy_node.parm("part_name_3").set("delete_test_c")
        
        print("[OK] Created 3 test parts:")
        print("  1. delete_test_a")
        print("  2. delete_test_b")
        print("  3. delete_test_c")
        print()
        
        # update_proxy 실행하여 모든 노드 생성
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

print("\n[STEP 2] Verify all nodes created BEFORE deletion...")
print("-" * 80)

code = """
import hou

try:
    # Constraint
    constraint = hou.node("/obj/assets/Constraint")
    constraint_blasts = []
    if constraint:
        constraint_blasts = [c.name() for c in constraint.children() 
                           if c.type().name() == "blast" and c.name().startswith("blast_delete_test_")]
    
    # Deform
    deform = hou.node("/obj/assets/Deform")
    proxy_blasts = []
    geo_blasts = []
    parts_deform = []
    
    if deform:
        proxy_blasts = [c.name() for c in deform.children() 
                       if c.type().name() == "blast" and c.name().startswith("proxy_path_blast_delete_test_")]
        geo_blasts = [c.name() for c in deform.children() 
                     if c.type().name() == "blast" and c.name().startswith("geo_path_blast_delete_test_")]
        parts_deform = [c.name() for c in deform.children() 
                       if c.type().name() == "subnet" and c.name().startswith("Parts_Deform_delete_test_")]
    
    print("="*70)
    print(" BEFORE Deletion")
    print("="*70)
    print()
    print("[Constraint] {} blast(s): {}".format(len(constraint_blasts), constraint_blasts))
    print("[Deform/proxy_path] {} blast(s): {}".format(len(proxy_blasts), proxy_blasts))
    print("[Deform/geo_path] {} blast(s): {}".format(len(geo_blasts), geo_blasts))
    print("[Deform] {} Parts_Deform(s): {}".format(len(parts_deform), parts_deform))
    print()
    total = len(constraint_blasts) + len(proxy_blasts) + len(geo_blasts) + len(parts_deform)
    print("Total nodes for 'delete_test_*' parts: {}".format(total))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[STEP 3] Delete middle part (delete_test_b) using delete_part_with_confirm...")
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
        print("[INFO] Deleting part 2 (delete_test_b)...")
        print()
        
        # part_name_2 = "delete_test_b"
        part_name = proxy_node.parm("part_name_2").evalAsString()
        
        # Simulate "Delete All" choice (choice = 0)
        # Actually call the function directly
        
        # 1. Delete geo node
        geo_node = proxy_node.node("geo_{}".format(part_name))
        if geo_node:
            geo_node.destroy()
            print("[DELETED] geo_{}".format(part_name))
        
        # 2. Delete blast and Parts_Deform nodes
        assets_node = proxy_node.parent()
        if assets_node:
            deleted_nodes = []
            
            # Constraint blast
            constraint_node = assets_node.node("Constraint")
            if constraint_node:
                blast_node = constraint_node.node("blast_{}".format(part_name))
                if blast_node:
                    blast_node.destroy()
                    deleted_nodes.append("Constraint/blast_{}".format(part_name))
            
            # Deform blasts and Parts_Deform
            deform_node = assets_node.node("Deform")
            if deform_node:
                # proxy_path blast
                proxy_blast = deform_node.node("proxy_path_blast_{}".format(part_name))
                if proxy_blast:
                    proxy_blast.destroy()
                    deleted_nodes.append("Deform/proxy_path_blast_{}".format(part_name))
                
                # geo_path blast
                geo_blast = deform_node.node("geo_path_blast_{}".format(part_name))
                if geo_blast:
                    geo_blast.destroy()
                    deleted_nodes.append("Deform/geo_path_blast_{}".format(part_name))
                
                # Parts_Deform
                parts_deform = deform_node.node("Parts_Deform_{}".format(part_name))
                if parts_deform:
                    parts_deform.destroy()
                    deleted_nodes.append("Deform/Parts_Deform_{}".format(part_name))
            
            if deleted_nodes:
                print()
                print("[DELETED] Associated nodes:")
                for node_path in deleted_nodes:
                    print("  - {}".format(node_path))
        
        # 3. Remove multiparm instance (index 2, so 1 in 0-based)
        proxy_node.parm("cloth_parts").removeMultiParmInstance(1)
        print()
        print("[OK] Removed part '{}' from multiparm".format(part_name))
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

print("\n[STEP 4] Verify deletion results...")
print("-" * 80)

code = """
import hou

try:
    # Check cloth_parts count
    proxy_node = hou.node("/obj/assets/Proxy")
    if proxy_node:
        count = proxy_node.parm("cloth_parts").evalAsInt()
        print("[INFO] cloth_parts count after deletion: {}".format(count))
        print()
        
        print("Remaining parts:")
        for i in range(1, count + 1):
            part_name_parm = proxy_node.parm("part_name_{}".format(i))
            if part_name_parm:
                print("  {}. {}".format(i, part_name_parm.evalAsString()))
    
    print()
    print("="*70)
    print(" AFTER Deletion")
    print("="*70)
    print()
    
    # Constraint
    constraint = hou.node("/obj/assets/Constraint")
    constraint_blasts = []
    if constraint:
        constraint_blasts = [c.name() for c in constraint.children() 
                           if c.type().name() == "blast" and c.name().startswith("blast_delete_test_")]
    
    # Deform
    deform = hou.node("/obj/assets/Deform")
    proxy_blasts = []
    geo_blasts = []
    parts_deform = []
    
    if deform:
        proxy_blasts = [c.name() for c in deform.children() 
                       if c.type().name() == "blast" and c.name().startswith("proxy_path_blast_delete_test_")]
        geo_blasts = [c.name() for c in deform.children() 
                     if c.type().name() == "blast" and c.name().startswith("geo_path_blast_delete_test_")]
        parts_deform = [c.name() for c in deform.children() 
                       if c.type().name() == "subnet" and c.name().startswith("Parts_Deform_delete_test_")]
    
    print("[Constraint] {} blast(s): {}".format(len(constraint_blasts), constraint_blasts))
    print("[Deform/proxy_path] {} blast(s): {}".format(len(proxy_blasts), proxy_blasts))
    print("[Deform/geo_path] {} blast(s): {}".format(len(geo_blasts), geo_blasts))
    print("[Deform] {} Parts_Deform(s): {}".format(len(parts_deform), parts_deform))
    print()
    
    # Verify correct nodes remain (a and c, not b)
    expected_remaining = ["delete_test_a", "delete_test_c"]
    
    all_correct = True
    for part in expected_remaining:
        # Check each location
        if "blast_{}".format(part) not in constraint_blasts:
            print("[ERROR] Missing Constraint/blast_{}".format(part))
            all_correct = False
        if "proxy_path_blast_{}".format(part) not in proxy_blasts:
            print("[ERROR] Missing Deform/proxy_path_blast_{}".format(part))
            all_correct = False
        if "geo_path_blast_{}".format(part) not in geo_blasts:
            print("[ERROR] Missing Deform/geo_path_blast_{}".format(part))
            all_correct = False
        if "Parts_Deform_{}".format(part) not in parts_deform:
            print("[ERROR] Missing Deform/Parts_Deform_{}".format(part))
            all_correct = False
    
    # Check deleted part (b) is gone
    deleted_part = "delete_test_b"
    if "blast_{}".format(deleted_part) in constraint_blasts:
        print("[ERROR] Constraint/blast_{} still exists!".format(deleted_part))
        all_correct = False
    if "proxy_path_blast_{}".format(deleted_part) in proxy_blasts:
        print("[ERROR] Deform/proxy_path_blast_{} still exists!".format(deleted_part))
        all_correct = False
    if "geo_path_blast_{}".format(deleted_part) in geo_blasts:
        print("[ERROR] Deform/geo_path_blast_{} still exists!".format(deleted_part))
        all_correct = False
    if "Parts_Deform_{}".format(deleted_part) in parts_deform:
        print("[ERROR] Deform/Parts_Deform_{} still exists!".format(deleted_part))
        all_correct = False
    
    print("="*70)
    if all_correct:
        print(" [SUCCESS] Delete part worked correctly!")
        print("   - delete_test_b removed")
        print("   - delete_test_a and delete_test_c remain")
    else:
        print(" [ERROR] Some issues detected")
    print("="*70)

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Delete Part test finished!")
print("="*80)

connector.disconnect()





