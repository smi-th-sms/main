#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parts_Deform 노드 구조 확인
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Inspecting Parts_Deform Node")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Checking Parts_Deform structure...")
print("-" * 80)

# Parts_Deform 노드 구조 확인
code = """
import hou

try:
    parts_deform = hou.node("/obj/assets/Deform/Parts_Deform")
    
    if not parts_deform:
        print("[ERROR] Parts_Deform node not found")
    else:
        print("[OK] Found Parts_Deform node")
        print()
        print("Path: {}".format(parts_deform.path()))
        print("Type: {}".format(parts_deform.type().name()))
        print()
        
        # 입력 연결 확인
        print("="*70)
        print(" Inputs")
        print("="*70)
        print()
        
        inputs = parts_deform.inputs()
        print("Number of inputs: {}".format(len(inputs)))
        print()
        
        for i, input_node in enumerate(inputs):
            if input_node:
                print("Input {}: {}".format(i, input_node.path()))
            else:
                print("Input {}: (not connected)".format(i))
        
        # 출력 연결 확인
        print()
        print("="*70)
        print(" Outputs")
        print("="*70)
        print()
        
        outputs = parts_deform.outputs()
        print("Number of outputs: {}".format(len(outputs)))
        print()
        
        for output_node in outputs:
            print("  -> {}".format(output_node.path()))
        
        # 내부 노드 확인
        print()
        print("="*70)
        print(" Internal Structure")
        print("="*70)
        print()
        
        if parts_deform.type().name() in ['subnet', 'geo']:
            children = parts_deform.children()
            print("Children: {}".format(len(children)))
            print()
            
            for child in children:
                print("  - {} ({})".format(child.name(), child.type().name()))
        else:
            print("Not a subnet/geo node")
        
        # 파라미터 확인
        print()
        print("="*70)
        print(" Parameters")
        print("="*70)
        print()
        
        # 'Parts' 또는 이름 관련 파라미터 찾기
        parms = parts_deform.parms()
        name_parms = []
        
        for parm in parms:
            parm_name = parm.name()
            if 'name' in parm_name.lower() or 'part' in parm_name.lower():
                try:
                    value = parm.eval()
                    name_parms.append((parm_name, value))
                except:
                    pass
        
        if name_parms:
            print("Name-related parameters:")
            for parm_name, value in name_parms:
                print("  {} = {}".format(parm_name, repr(value)))
        else:
            print("No name-related parameters found")
        
        # 복제를 위한 정보
        print()
        print("="*70)
        print(" Clone Information")
        print("="*70)
        print()
        
        print("Node to clone: {}".format(parts_deform.name()))
        print("Node type: {}".format(parts_deform.type().name()))
        print("Parent: {}".format(parts_deform.parent().path()))
        print()
        print("For new clones:")
        print("  - Name format: Parts_Deform_{part_name}")
        print("  - Input 0 (or 1): proxy_path_blast_{part_name}")
        print("  - Input 1 (or 2): geo_path_blast_{part_name}")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Inspection completed!")
print("="*80)

connector.disconnect()





