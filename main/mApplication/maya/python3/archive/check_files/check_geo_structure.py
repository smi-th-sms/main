#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Check geo_ nodes internal structure
"""

import sys
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Checking geo_ Nodes Internal Structure")
print("="*80)

connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

code = """
import hou

try:
    proxy_node = hou.node("/obj/assets/Proxy")
    if not proxy_node:
        print("[ERROR] Proxy node not found")
    else:
        cloth_parts = proxy_node.parm("cloth_parts").eval()
        print("[INFO] Checking {} cloth parts...".format(cloth_parts))
        print()
        
        for i in range(1, cloth_parts + 1):
            part_name_parm = proxy_node.parm("part_name_{}".format(i))
            if part_name_parm:
                part_name = part_name_parm.eval()
                geo_node_path = "/obj/assets/Proxy/geo_{}".format(part_name)
                geo_node = hou.node(geo_node_path)
                
                print("[{}] Part: {}".format(i, part_name))
                print("    Geo node: {}".format(geo_node_path))
                
                if geo_node:
                    print("    [OK] Geo node exists")
                    
                    # List all children
                    children = geo_node.children()
                    if children:
                        print("    Children nodes ({} total):".format(len(children)))
                        for child in children:
                            child_type = child.type().name()
                            print("      - {} ({})".format(child.name(), child_type))
                        
                        # Look for output nodes
                        print()
                        print("    Looking for output nodes:")
                        output_candidates = []
                        
                        for child in children:
                            name = child.name()
                            if name.startswith("OUT") or name.startswith("out") or name == "output1":
                                output_candidates.append(child)
                                print("      [FOUND] {} ({})".format(name, child.type().name()))
                        
                        if not output_candidates:
                            # Check last node in network
                            print("      [INFO] No explicit output node found")
                            print("      [INFO] Checking for typical output nodes...")
                            
                            # Common output node types
                            for child in children:
                                node_type = child.type().name()
                                if node_type in ['null', 'output']:
                                    print("      [CANDIDATE] {} ({})".format(child.name(), node_type))
                    else:
                        print("    [WARNING] No children nodes found")
                else:
                    print("    [ERROR] Geo node not found")
                
                print()
                
except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("="*80)
connector.disconnect()





