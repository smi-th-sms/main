#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parts_Deform 자동 복제 및 제거 기능 테스트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing Parts_Deform Auto Sync")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Executing Proxy.update_proxy to trigger blast and Parts_Deform sync...")
print("-" * 80)

# Proxy.update_proxy 실행 (blast 및 Parts_Deform 동기화)
code = """
import hou

try:
    proxy_node = hou.node("/obj/assets/Proxy")
    if not proxy_node:
        print("[ERROR] Proxy node not found")
    else:
        # update_proxy 버튼 클릭
        update_btn = proxy_node.parm("update_proxy")
        if update_btn:
            # 버튼 클릭 시뮬레이션 (callback 실행)
            callback = update_btn.pressButton()
            print("[OK] update_proxy executed")
        else:
            print("[ERROR] update_proxy button not found")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[2] Checking created Parts_Deform nodes...")
print("-" * 80)

# Parts_Deform 노드들 확인
code = """
import hou

try:
    deform_node = hou.node("/obj/assets/Deform")
    if not deform_node:
        print("[ERROR] Deform node not found")
    else:
        print("[OK] Checking Parts_Deform nodes:")
        print()
        
        parts_deform_nodes = []
        for child in deform_node.children():
            if child.type().name() == "subnet" and child.name().startswith("Parts_Deform_"):
                parts_deform_nodes.append(child)
        
        if not parts_deform_nodes:
            print("[WARNING] No Parts_Deform nodes found")
        else:
            print("Found {} Parts_Deform node(s):".format(len(parts_deform_nodes)))
            print()
            
            for node in parts_deform_nodes:
                print("="*70)
                print("Node: {}".format(node.name()))
                print("-"*70)
                
                # 입력 확인
                inputs = node.inputs()
                if len(inputs) >= 2:
                    input0 = inputs[0].path() if inputs[0] else "(not connected)"
                    input1 = inputs[1].path() if inputs[1] else "(not connected)"
                    print("  Input 0 (proxy_blast): {}".format(input0))
                    print("  Input 1 (geo_blast):   {}".format(input1))
                    
                    # 입력이 올바른지 확인
                    part_name = node.name().replace("Parts_Deform_", "")
                    expected_proxy = "/obj/assets/Deform/proxy_path_blast_{}".format(part_name)
                    expected_geo = "/obj/assets/Deform/geo_path_blast_{}".format(part_name)
                    
                    proxy_ok = (input0 == expected_proxy)
                    geo_ok = (input1 == expected_geo)
                    
                    print()
                    print("  Expected:")
                    print("    Input 0: {} {}".format(expected_proxy, "[OK]" if proxy_ok else "[MISMATCH]"))
                    print("    Input 1: {} {}".format(expected_geo, "[OK]" if geo_ok else "[MISMATCH]"))
                else:
                    print("  [WARNING] Not enough inputs connected")
                print()

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[3] Checking blast nodes in all locations...")
print("-" * 80)

code = """
import hou

try:
    # Constraint blast 확인
    constraint = hou.node("/obj/assets/Constraint")
    if constraint:
        blasts = [c for c in constraint.children() if c.type().name() == "blast" and c.name().startswith("blast_")]
        print("[Constraint] {} blast node(s)".format(len(blasts)))
        for blast in blasts:
            print("  - {}".format(blast.name()))
    
    print()
    
    # Deform proxy_path blast 확인
    deform = hou.node("/obj/assets/Deform")
    if deform:
        proxy_blasts = [c for c in deform.children() if c.type().name() == "blast" and c.name().startswith("proxy_path_blast_")]
        print("[Deform/proxy_path] {} blast node(s)".format(len(proxy_blasts)))
        for blast in proxy_blasts:
            print("  - {}".format(blast.name()))
        
        print()
        
        # Deform geo_path blast 확인
        geo_blasts = [c for c in deform.children() if c.type().name() == "blast" and c.name().startswith("geo_path_blast_")]
        print("[Deform/geo_path] {} blast node(s)".format(len(geo_blasts)))
        for blast in geo_blasts:
            print("  - {}".format(blast.name()))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[TEST] Now test clear_proxy to verify Parts_Deform removal...")
print("="*80)
print()
print("Please click Proxy.clear_proxy and check if Parts_Deform nodes are removed.")

connector.disconnect()





