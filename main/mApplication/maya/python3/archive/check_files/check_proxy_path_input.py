#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
proxy_path 노드의 입력 및 상위 노드 확인
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Checking proxy_path Input and Parent Structure")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Analyzing proxy_path node structure...")
print("-" * 80)

# 상세 구조 확인
code = """
import hou

try:
    proxy_path_node = hou.node("/obj/assets/Constraint/proxy_path")
    
    if not proxy_path_node:
        print("[ERROR] proxy_path node not found")
    else:
        print("[OK] Found proxy_path node")
        print("Type: {}".format(proxy_path_node.type().name()))
        print("Path: {}".format(proxy_path_node.path()))
        
        # 입력 연결 확인
        print("\\n" + "="*70)
        print(" Input Connections")
        print("="*70)
        
        inputs = proxy_path_node.inputs()
        if inputs:
            print("\\nFound {} input(s):\\n".format(len(inputs)))
            for i, input_node in enumerate(inputs):
                if input_node:
                    print("  Input {}: {}".format(i, input_node.path()))
                    
                    # 입력 노드의 geometry 확인
                    try:
                        input_geo = input_node.geometry()
                        if input_geo:
                            print("    - Prims: {}, Points: {}".format(
                                len(input_geo.prims()), len(input_geo.points())))
                            
                            # @proxy_path 확인
                            proxy_path_attr = input_geo.findPrimAttrib("proxy_path")
                            if proxy_path_attr:
                                unique_paths = set()
                                for prim in input_geo.prims():
                                    val = prim.attribValue("proxy_path")
                                    if val:
                                        unique_paths.add(val)
                                
                                print("    - Has @proxy_path: {} unique value(s)".format(
                                    len(unique_paths)))
                                
                                if unique_paths:
                                    print("\\n    Unique @proxy_path values:")
                                    for path in sorted(unique_paths):
                                        print("      - {}".format(path))
                    except:
                        pass
                else:
                    print("  Input {}: (not connected)".format(i))
        else:
            print("\\n[INFO] No input connections")
        
        # 출력 연결 확인
        print("\\n" + "="*70)
        print(" Output Connections")
        print("="*70)
        
        outputs = proxy_path_node.outputs()
        if outputs:
            print("\\nFound {} output(s):\\n".format(len(outputs)))
            for output_node in outputs:
                print("  -> {}".format(output_node.path()))
        else:
            print("\\n[INFO] No output connections")
        
        # 부모 노드 (Constraint) 구조 확인
        print("\\n" + "="*70)
        print(" Parent (Constraint) Node Structure")
        print("="*70)
        
        constraint_node = proxy_path_node.parent()
        if constraint_node:
            print("\\nParent: {}".format(constraint_node.path()))
            print("Type: {}".format(constraint_node.type().name()))
            
            print("\\nAll children of Constraint:")
            children = constraint_node.children()
            for child in children:
                marker = " <-- TARGET" if child.name() == "proxy_path" else ""
                print("  - {} ({}){}".format(
                    child.name(), child.type().name(), marker))
        
        # Deform 노드의 proxy_path 확인 (비교용)
        print("\\n" + "="*70)
        print(" Comparison: Deform/proxy_path")
        print("="*70)
        
        deform_node = hou.node("/obj/assets/Deform")
        if deform_node:
            deform_proxy_path = deform_node.node("proxy_path")
            if deform_proxy_path:
                print("\\n[OK] Found Deform/proxy_path")
                
                try:
                    deform_geo = deform_proxy_path.geometry()
                    if deform_geo:
                        print("Geometry: {} prims, {} points".format(
                            len(deform_geo.prims()), len(deform_geo.points())))
                        
                        # @proxy_path 확인
                        attr = deform_geo.findPrimAttrib("proxy_path")
                        if attr:
                            unique = set()
                            for prim in deform_geo.prims():
                                val = prim.attribValue("proxy_path")
                                if val:
                                    unique.add(val)
                            
                            print("@proxy_path values: {}\\n".format(len(unique)))
                            for path in sorted(unique):
                                print("  - {}".format(path))
                except:
                    print("No geometry available")
            else:
                print("\\n[INFO] Deform/proxy_path not found")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Analysis completed!")
print("="*80)

connector.disconnect()





