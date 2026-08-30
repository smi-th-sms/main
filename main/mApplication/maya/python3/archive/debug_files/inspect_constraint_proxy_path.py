#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Constraint/proxy_path 노드 구조 확인
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Inspecting Constraint/proxy_path Node")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Checking Constraint/proxy_path structure...")
print("-" * 80)

# 노드 구조 확인
code = """
import hou

try:
    # assets 노드 찾기
    assets_node = hou.node("/obj/assets")
    if not assets_node:
        print("[ERROR] /obj/assets node not found")
    else:
        print("[OK] Found assets node")
        
        # Constraint 노드 찾기
        constraint_node = assets_node.node("Constraint")
        if not constraint_node:
            print("[ERROR] Constraint node not found")
        else:
            print("[OK] Found Constraint node")
            
            # proxy_path 노드 찾기
            proxy_path_node = constraint_node.node("proxy_path")
            if not proxy_path_node:
                print("[WARNING] proxy_path node not found")
            else:
                print("[OK] Found proxy_path node at: {}".format(proxy_path_node.path()))
                
                print("\\n" + "="*70)
                print(" proxy_path Node Children")
                print("="*70)
                
                children = proxy_path_node.children()
                if children:
                    print("\\nFound {} child node(s):\\n".format(len(children)))
                    
                    blast_nodes = []
                    other_nodes = []
                    
                    for child in children:
                        node_type = child.type().name()
                        if node_type == "blast":
                            blast_nodes.append(child)
                        else:
                            other_nodes.append(child)
                    
                    # Blast 노드들
                    if blast_nodes:
                        print("[Blast Nodes] ({})".format(len(blast_nodes)))
                        print("-"*70)
                        for blast in blast_nodes:
                            group_parm = blast.parm("group")
                            if group_parm:
                                group_value = group_parm.evalAsString()
                                print("  {} - Group: {}".format(blast.name(), group_value))
                            else:
                                print("  {}".format(blast.name()))
                    
                    # 기타 노드들
                    if other_nodes:
                        print("\\n[Other Nodes] ({})".format(len(other_nodes)))
                        print("-"*70)
                        for node in other_nodes:
                            print("  {} ({})".format(node.name(), node.type().name()))
                else:
                    print("\\n[INFO] No child nodes found")
                
                # Geometry 확인
                print("\\n" + "="*70)
                print(" @proxy_path Attribute Check")
                print("="*70)
                
                try:
                    geo = proxy_path_node.geometry()
                    if geo:
                        print("\\n[OK] Geometry available")
                        print("Primitives: {}".format(len(geo.prims())))
                        print("Points: {}".format(len(geo.points())))
                        
                        # @proxy_path 어트리뷰트 확인
                        proxy_path_attr = geo.findPrimAttrib("proxy_path")
                        if proxy_path_attr:
                            print("\\n[FOUND] @proxy_path attribute")
                            print("Type: {}".format(proxy_path_attr.dataType()))
                            
                            # 고유값 추출
                            unique_paths = set()
                            for prim in geo.prims():
                                path_val = prim.attribValue("proxy_path")
                                if path_val:
                                    unique_paths.add(path_val)
                            
                            print("\\nUnique @proxy_path values: {}\\n".format(len(unique_paths)))
                            
                            for i, path in enumerate(sorted(unique_paths), 1):
                                print("  {}. {}".format(i, path))
                        else:
                            print("\\n[WARNING] @proxy_path attribute not found")
                            
                            # 다른 어트리뷰트 확인
                            print("\\nAvailable primitive attributes:")
                            for attr in geo.primAttribs():
                                print("  - {} ({})".format(attr.name(), attr.dataType()))
                    else:
                        print("\\n[WARNING] No geometry available")
                except Exception as e:
                    print("\\n[ERROR] Cannot access geometry: {}".format(str(e)))
                
                # Display 노드 확인
                print("\\n" + "="*70)
                print(" Display Node")
                print("="*70)
                
                display_node = proxy_path_node.displayNode()
                if display_node:
                    print("\\nDisplay node: {}".format(display_node.name()))
                else:
                    print("\\n[INFO] No display node set")
        
        # Proxy 노드의 cloth_parts 확인
        print("\\n" + "="*70)
        print(" Proxy Node - Cloth Parts")
        print("="*70)
        
        proxy_node = assets_node.node("Proxy")
        if proxy_node:
            cloth_parts_parm = proxy_node.parm("cloth_parts")
            if cloth_parts_parm:
                count = cloth_parts_parm.evalAsInt()
                print("\\nCloth Parts count: {}".format(count))
                
                if count > 0:
                    print("\\nPart names:")
                    for i in range(1, count + 1):
                        part_name_parm = proxy_node.parm("part_name_{}".format(i))
                        if part_name_parm:
                            part_name = part_name_parm.evalAsString()
                            print("  {}. {}".format(i, part_name))

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





