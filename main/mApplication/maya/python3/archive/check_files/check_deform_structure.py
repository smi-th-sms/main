#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Deform 노드 구조 확인
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Checking Deform Node Structure")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Checking Deform node structure...")
print("-" * 80)

# Deform 노드 구조 확인
code = """
import hou

try:
    deform_node = hou.node("/obj/assets/Deform")
    
    if not deform_node:
        print("[ERROR] Deform node not found")
    else:
        print("[OK] Found Deform node")
        print()
        
        # Deform 하위 노드들
        print("="*70)
        print(" Deform Children")
        print("="*70)
        print()
        
        children = deform_node.children()
        print("Total children: {}\\n".format(len(children)))
        
        # Proxy_path와 geo_path 찾기
        proxy_path_node = None
        geo_path_node = None
        
        for child in children:
            name = child.name()
            node_type = child.type().name()
            
            if name == "Proxy_path" or name == "proxy_path":
                proxy_path_node = child
                print("[TARGET] {} ({}) - Found!".format(name, node_type))
            elif name == "geo_path":
                geo_path_node = child
                print("[TARGET] {} ({}) - Found!".format(name, node_type))
            elif child.type().name() in ['blast', 'null', 'subnet']:
                print("  - {} ({})".format(name, node_type))
        
        # Proxy_path 상세
        if proxy_path_node:
            print()
            print("="*70)
            print(" Deform/Proxy_path Details")
            print("="*70)
            print()
            print("Path: {}".format(proxy_path_node.path()))
            print("Type: {}".format(proxy_path_node.type().name()))
            
            # 하위 노드
            pp_children = proxy_path_node.children()
            if pp_children:
                print("\\nChildren: {}".format(len(pp_children)))
                for child in pp_children:
                    print("  - {} ({})".format(child.name(), child.type().name()))
            else:
                print("\\nChildren: (none)")
            
            # 입력 연결
            inputs = proxy_path_node.inputs()
            if inputs and inputs[0]:
                print("\\nInput: {}".format(inputs[0].path()))
        
        # geo_path 상세
        if geo_path_node:
            print()
            print("="*70)
            print(" Deform/geo_path Details")
            print("="*70)
            print()
            print("Path: {}".format(geo_path_node.path()))
            print("Type: {}".format(geo_path_node.type().name()))
            
            # 하위 노드
            gp_children = geo_path_node.children()
            if gp_children:
                print("\\nChildren: {}".format(len(gp_children)))
                for child in gp_children:
                    print("  - {} ({})".format(child.name(), child.type().name()))
            else:
                print("\\nChildren: (none)")
            
            # 입력 연결
            inputs = geo_path_node.inputs()
            if inputs and inputs[0]:
                print("\\nInput: {}".format(inputs[0].path()))
        
        # 요약
        print()
        print("="*70)
        print(" Summary")
        print("="*70)
        print()
        
        if proxy_path_node and geo_path_node:
            print("[OK] Both target nodes found")
            print()
            print("Blast nodes will be created under:")
            print("  1. /obj/assets/Constraint (already done)")
            print("  2. /obj/assets/Deform/Proxy_path (new)")
            print("  3. /obj/assets/Deform/geo_path (new, with @geo_path)")
        elif proxy_path_node:
            print("[WARNING] Only Proxy_path found")
        elif geo_path_node:
            print("[WARNING] Only geo_path found")
        else:
            print("[ERROR] Neither Proxy_path nor geo_path found")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Check completed!")
print("="*80)

connector.disconnect()





