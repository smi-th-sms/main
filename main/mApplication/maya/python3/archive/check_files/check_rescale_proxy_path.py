#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
rescale 노드에서 @proxy_path 어트리뷰트 확인
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Checking @proxy_path from rescale Node")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Analyzing rescale node...")
print("-" * 80)

# rescale 노드의 @proxy_path 확인
code = """
import hou

try:
    rescale_node = hou.node("/obj/assets/Constraint/rescale")
    
    if not rescale_node:
        print("[ERROR] rescale node not found")
    else:
        print("[OK] Found rescale node")
        print("Type: {}".format(rescale_node.type().name()))
        
        # rescale이 subnet이면 display node 확인
        if rescale_node.type().name() == "subnet":
            display = rescale_node.displayNode()
            if display:
                print("Display node: {}".format(display.name()))
                
                # Display node의 geometry 확인
                try:
                    geo = display.geometry()
                    if geo:
                        print("\\n" + "="*70)
                        print(" Geometry from Display Node")
                        print("="*70)
                        print("\\nPrimitives: {}".format(len(geo.prims())))
                        print("Points: {}".format(len(geo.points())))
                        
                        # @proxy_path 확인
                        proxy_path_attr = geo.findPrimAttrib("proxy_path")
                        if proxy_path_attr:
                            print("\\n[FOUND] @proxy_path attribute")
                            
                            unique_paths = set()
                            for prim in geo.prims():
                                val = prim.attribValue("proxy_path")
                                if val:
                                    unique_paths.add(val)
                            
                            print("Unique values: {}\\n".format(len(unique_paths)))
                            
                            sorted_paths = sorted(unique_paths)
                            for i, path in enumerate(sorted_paths, 1):
                                print("  {}. {}".format(i, path))
                            
                            # 제안할 blast 노드 이름들
                            print("\\n" + "="*70)
                            print(" Suggested Blast Node Names")
                            print("="*70)
                            print()
                            
                            for path in sorted_paths:
                                # 경로에서 마지막 부분 추출
                                parts = path.split('/')
                                if parts:
                                    last_part = parts[-1]
                                    # 특수문자 제거 및 언더스코어로 변경
                                    clean_name = last_part.replace(':', '_').replace('|', '_')
                                    blast_name = "blast_{}".format(clean_name)
                                    print("  {} -> {}".format(path, blast_name))
                        else:
                            print("\\n[WARNING] @proxy_path attribute not found")
                            print("\\nAvailable prim attributes:")
                            for attr in geo.primAttribs():
                                print("  - {}".format(attr.name()))
                except Exception as e:
                    print("\\nCannot access geometry: {}".format(str(e)))
        else:
            # Subnet이 아니면 직접 geometry 확인
            try:
                geo = rescale_node.geometry()
                if geo:
                    print("\\n" + "="*70)
                    print(" Geometry from rescale")
                    print("="*70)
                    print("\\nPrimitives: {}".format(len(geo.prims())))
                    
                    proxy_path_attr = geo.findPrimAttrib("proxy_path")
                    if proxy_path_attr:
                        unique_paths = set()
                        for prim in geo.prims():
                            val = prim.attribValue("proxy_path")
                            if val:
                                unique_paths.add(val)
                        
                        print("@proxy_path unique values: {}\\n".format(len(unique_paths)))
                        for path in sorted(unique_paths):
                            print("  - {}".format(path))
            except Exception as e:
                print("Cannot access geometry: {}".format(str(e)))
        
        # Proxy cloth_parts와 비교
        print("\\n" + "="*70)
        print(" Comparison with Proxy Cloth Parts")
        print("="*70)
        
        proxy_node = hou.node("/obj/assets/Proxy")
        if proxy_node:
            count = proxy_node.parm("cloth_parts").evalAsInt()
            print("\\nProxy Cloth Parts: {}".format(count))
            
            if count > 0:
                print("\\nPart names:")
                for i in range(1, count + 1):
                    part_name = proxy_node.parm("part_name_{}".format(i)).evalAsString()
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
print("[OK] Analysis completed!")
print("="*80)

connector.disconnect()





