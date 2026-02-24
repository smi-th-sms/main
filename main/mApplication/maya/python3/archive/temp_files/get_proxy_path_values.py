#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@proxy_path 어트리뷰트 값 가져오기 (모든 가능한 소스에서)
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Getting @proxy_path Values from All Sources")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Trying all possible sources...")
print("-" * 80)

# 모든 소스 시도
code = """
import hou

def get_proxy_path_values(node):
    \"\"\"노드에서 @proxy_path 고유값 추출\"\"\"
    try:
        geo = node.geometry()
        if not geo:
            return None
        
        attr = geo.findPrimAttrib("proxy_path")
        if not attr:
            return None
        
        unique = set()
        for prim in geo.prims():
            val = prim.attribValue("proxy_path")
            if val:
                unique.add(val)
        
        return sorted(unique) if unique else None
    except:
        return None

try:
    constraint = hou.node("/obj/assets/Constraint")
    
    print("="*70)
    print(" Searching for @proxy_path attribute")
    print("="*70)
    print()
    
    sources_to_check = [
        "/obj/assets/Constraint/rescale/timeshift1",
        "/obj/assets/Constraint/rescale",
        "/obj/assets/Constraint/proxy_path",
        "/obj/assets/Deform/proxy_path",
        "/obj/assets/Proxy/geo_pants/OUT_pants_PROXY",
        "/obj/assets/Proxy/geo_shirts/OUT_shirts_PROXY",
    ]
    
    found_values = None
    source_node = None
    
    for node_path in sources_to_check:
        node = hou.node(node_path)
        if node:
            values = get_proxy_path_values(node)
            if values:
                print("[FOUND] @proxy_path in: {}".format(node_path))
                print("Unique values: {}\\n".format(len(values)))
                
                for i, val in enumerate(values, 1):
                    print("  {}. {}".format(i, val))
                
                if not found_values:
                    found_values = values
                    source_node = node_path
                
                print()
    
    if not found_values:
        print("[INFO] @proxy_path attribute not found in standard locations")
        print("\\nLet's check Constraint node children more thoroughly...")
        print()
        
        if constraint:
            for child in constraint.children():
                values = get_proxy_path_values(child)
                if values:
                    print("[FOUND] @proxy_path in: {}".format(child.path()))
                    print("Values: {}\\n".format(len(values)))
                    for val in values[:5]:  # 처음 5개만
                        print("  - {}".format(val))
                    if len(values) > 5:
                        print("  ... ({} more)".format(len(values) - 5))
                    print()
                    
                    if not found_values:
                        found_values = values
                        source_node = child.path()
                        break
    
    # 최종 결과
    print("="*70)
    print(" Final Result")
    print("="*70)
    print()
    
    if found_values:
        print("[SUCCESS] Found @proxy_path attribute")
        print("Source: {}".format(source_node))
        print("Unique values: {}\\n".format(len(found_values)))
        
        print("@proxy_path values:")
        for i, val in enumerate(found_values, 1):
            # Blast 노드 이름 제안
            parts = val.split('/')
            last_part = parts[-1] if parts else val
            clean_name = last_part.replace(':', '_').replace('|', '_').replace(' ', '_')
            blast_name = "blast_{}".format(clean_name)
            
            print("  {}. {}".format(i, val))
            print("      -> {}".format(blast_name))
        
        print("\\n[NOTE] Blast nodes will be created under /obj/assets/Constraint")
    else:
        print("[WARNING] Could not find @proxy_path attribute")
        print("\\nThis attribute should exist on geometry that has proxy paths.")
        print("Please check if:")
        print("  1. Simulation has been cooked")
        print("  2. Proxy geometry has proxy_path attribute")
        print("  3. Constraint network is properly connected")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Search completed!")
print("="*80)

connector.disconnect()





