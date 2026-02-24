#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parts_Deform 복제 기능 테스트 (테스트 데이터 포함)
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing Parts_Deform Sync with Test Data")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[STEP 1] Reload modules and add test cloth parts...")
print("-" * 80)

code = """
import sys
import hou

try:
    # 모듈 리로드
    if 'proxy_blast_sync' in sys.modules:
        del sys.modules['proxy_blast_sync']
    if 'proxy_manager' in sys.modules:
        del sys.modules['proxy_manager']
    
    # T:\scripts 경로 우선순위
    script_path = r'T:\\scripts\\python\\application\\houdini\\houdini21.0\\script'
    if script_path in sys.path:
        sys.path.remove(script_path)
    sys.path.insert(0, script_path)
    
    print("[OK] Modules reloaded")
    print()
    
    # Proxy 노드에 테스트 파트 추가
    proxy_node = hou.node("/obj/assets/Proxy")
    if not proxy_node:
        print("[ERROR] Proxy node not found")
    else:
        # cloth_parts 설정
        cloth_parts_parm = proxy_node.parm("cloth_parts")
        if cloth_parts_parm:
            current_count = cloth_parts_parm.evalAsInt()
            
            if current_count == 0:
                # 테스트용 파트 2개 추가
                cloth_parts_parm.set(2)
                
                # Part 1
                part1_parm = proxy_node.parm("part_name_1")
                if part1_parm:
                    part1_parm.set("pants")
                
                # Part 2
                part2_parm = proxy_node.parm("part_name_2")
                if part2_parm:
                    part2_parm.set("shirt")
                
                print("[OK] Added 2 test cloth parts:")
                print("  1. pants")
                print("  2. shirt")
            else:
                print("[INFO] Using existing {} cloth part(s)".format(current_count))
                for i in range(1, current_count + 1):
                    part_name_parm = proxy_node.parm("part_name_{}".format(i))
                    if part_name_parm:
                        print("  {}. {}".format(i, part_name_parm.evalAsString()))
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

print("\n[STEP 2] Execute update_proxy to create blasts and Parts_Deform...")
print("-" * 80)

code = """
import sys
import hou

try:
    # T:\scripts 경로 우선순위
    script_path = r'T:\\scripts\\python\\application\\houdini\\houdini21.0\\script'
    if script_path in sys.path:
        sys.path.remove(script_path)
    sys.path.insert(0, script_path)
    
    import proxy_manager
    
    proxy_node = hou.node("/obj/assets/Proxy")
    if proxy_node:
        print("[INFO] Calling proxy_manager.update_proxy_nodes()...")
        print()
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

print("\n[STEP 3] Verify created Parts_Deform nodes...")
print("-" * 80)

code = """
import hou

try:
    deform_node = hou.node("/obj/assets/Deform")
    if not deform_node:
        print("[ERROR] Deform node not found")
    else:
        print("="*70)
        print(" Parts_Deform Nodes")
        print("="*70)
        print()
        
        parts_deform_nodes = []
        for child in deform_node.children():
            if child.type().name() == "subnet" and child.name().startswith("Parts_Deform_"):
                parts_deform_nodes.append(child)
        
        if not parts_deform_nodes:
            print("[ERROR] No Parts_Deform nodes created!")
        else:
            print("Found {} Parts_Deform node(s):".format(len(parts_deform_nodes)))
            print()
            
            for node in parts_deform_nodes:
                part_name = node.name().replace("Parts_Deform_", "")
                print("-"*70)
                print("Node: {} (for part '{}')".format(node.name(), part_name))
                print("-"*70)
                
                # 입력 확인
                inputs = node.inputs()
                if len(inputs) >= 2:
                    input0 = inputs[0].path() if inputs[0] else "(not connected)"
                    input1 = inputs[1].path() if inputs[1] else "(not connected)"
                    
                    print("  Input 0: {}".format(input0))
                    print("  Input 1: {}".format(input1))
                    
                    # 검증
                    expected_proxy = "/obj/assets/Deform/proxy_path_blast_{}".format(part_name)
                    expected_geo = "/obj/assets/Deform/geo_path_blast_{}".format(part_name)
                    
                    proxy_ok = (input0 == expected_proxy)
                    geo_ok = (input1 == expected_geo)
                    
                    if proxy_ok and geo_ok:
                        print("  Status: [OK] Correctly connected")
                    else:
                        print("  Status: [ERROR] Connection mismatch!")
                        print("    Expected Input 0: {}".format(expected_proxy))
                        print("    Expected Input 1: {}".format(expected_geo))
                else:
                    print("  [ERROR] Not enough inputs")
                print()

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[STEP 4] Verify blast nodes...")
print("-" * 80)

code = """
import hou

try:
    deform_node = hou.node("/obj/assets/Deform")
    if deform_node:
        proxy_blasts = [c for c in deform_node.children() 
                       if c.type().name() == "blast" and c.name().startswith("proxy_path_blast_")]
        geo_blasts = [c for c in deform_node.children() 
                     if c.type().name() == "blast" and c.name().startswith("geo_path_blast_")]
        
        print("[Deform/proxy_path] {} blast node(s):".format(len(proxy_blasts)))
        for blast in proxy_blasts:
            group = blast.parm("group").evalAsString()
            print("  - {} (group: {})".format(blast.name(), group))
        
        print()
        
        print("[Deform/geo_path] {} blast node(s):".format(len(geo_blasts)))
        for blast in geo_blasts:
            group = blast.parm("group").evalAsString()
            print("  - {} (group: {})".format(blast.name(), group))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[SUCCESS] Parts_Deform sync test completed!")
print("="*80)
print()
print("Next steps:")
print("1. Verify Parts_Deform nodes are correctly created in Houdini UI")
print("2. Test clear_proxy to verify auto-deletion of Parts_Deform")

connector.disconnect()





