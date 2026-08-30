#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Check object_merge2 node current state
"""

import sys
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Checking object_merge2 Node Configuration")
print("="*80)

connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Checking Proxy node Cloth Parts...")
print("-" * 80)

code = """
import hou

try:
    # Check Proxy node
    proxy_node = hou.node("/obj/assets/Proxy")
    if not proxy_node:
        print("[ERROR] Proxy node not found")
    else:
        print("[OK] Proxy node found: {}".format(proxy_node.path()))
        
        # Get cloth_parts count
        cloth_parts_parm = proxy_node.parm("cloth_parts")
        if cloth_parts_parm:
            cloth_parts_count = cloth_parts_parm.eval()
            print("[INFO] Cloth Parts count: {}".format(cloth_parts_count))
            print()
            
            # List all parts
            if cloth_parts_count > 0:
                print("Parts list:")
                for i in range(1, cloth_parts_count + 1):
                    part_name_parm = proxy_node.parm("part_name_{}".format(i))
                    if part_name_parm:
                        part_name = part_name_parm.eval()
                        print("  [{}] {}".format(i, part_name))
                        
                        # Check if geo_ node exists
                        geo_node_path = "/obj/assets/Proxy/geo_{}".format(part_name)
                        geo_node = hou.node(geo_node_path)
                        if geo_node:
                            print("      -> geo node: {}".format(geo_node_path))
                            
                            # Check for OUT_ node
                            out_node_path = "{}/OUT_{}".format(geo_node_path, part_name)
                            out_node = hou.node(out_node_path)
                            if out_node:
                                print("      -> OUT node: {}".format(out_node_path))
                            else:
                                print("      -> [WARNING] OUT node not found: {}".format(out_node_path))
                        else:
                            print("      -> [WARNING] geo node not found")
                print()
            else:
                print("[INFO] No cloth parts defined")
                print()
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

print("\n[2] Checking object_merge2 node...")
print("-" * 80)

code = """
import hou

try:
    # Check object_merge2 node
    merge_node = hou.node("/obj/assets/Cache/object_merge2")
    if not merge_node:
        print("[ERROR] object_merge2 node not found")
        print("       Expected path: /obj/assets/Cache/object_merge2")
    else:
        print("[OK] object_merge2 node found: {}".format(merge_node.path()))
        print()
        
        # Get numobj parameter (number of objects)
        numobj_parm = merge_node.parm("numobj")
        if numobj_parm:
            numobj = numobj_parm.eval()
            print("[INFO] Number of Objects: {}".format(numobj))
            print()
            
            # List all object paths
            if numobj > 0:
                print("Current object paths:")
                for i in range(1, numobj + 1):
                    obj_parm = merge_node.parm("objpath{}".format(i))
                    if obj_parm:
                        obj_path = obj_parm.eval()
                        print("  [{}] {}".format(i, obj_path if obj_path else "(empty)"))
                        
                        # Check if path is valid
                        if obj_path:
                            target_node = hou.node(obj_path)
                            if target_node:
                                print("      -> [OK] Node exists")
                            else:
                                print("      -> [ERROR] Node not found")
                print()
            else:
                print("[INFO] No objects to merge")
                print()
        else:
            print("[ERROR] numobj parameter not found")
            
        # Check if it's a multiparm
        ptg = merge_node.parmTemplateGroup()
        numobj_template = ptg.find("numobj")
        if numobj_template:
            print("[INFO] Parameter type: {}".format(numobj_template.type().name()))
            if hasattr(numobj_template, 'numComponents'):
                print("      Is multiparm folder: {}".format(isinstance(numobj_template, hou.FolderParmTemplate)))
            
except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[3] Comparing configurations...")
print("-" * 80)

code = """
import hou

try:
    proxy_node = hou.node("/obj/assets/Proxy")
    merge_node = hou.node("/obj/assets/Cache/object_merge2")
    
    if not proxy_node or not merge_node:
        print("[ERROR] One or both nodes not found")
    else:
        # Get counts
        cloth_parts = proxy_node.parm("cloth_parts").eval()
        numobj = merge_node.parm("numobj").eval()
        
        print("Configuration comparison:")
        print("  Proxy cloth_parts: {}".format(cloth_parts))
        print("  Merge numobj:      {}".format(numobj))
        print()
        
        if cloth_parts == numobj:
            print("[OK] Counts match!")
        else:
            print("[MISMATCH] Counts do not match")
            print("           Expected numobj to be: {}".format(cloth_parts))
        print()
        
        # Check if paths match expected pattern
        if cloth_parts > 0 and numobj > 0:
            print("Path validation:")
            all_match = True
            for i in range(1, min(cloth_parts, numobj) + 1):
                part_name_parm = proxy_node.parm("part_name_{}".format(i))
                obj_parm = merge_node.parm("objpath{}".format(i))
                
                if part_name_parm and obj_parm:
                    part_name = part_name_parm.eval()
                    obj_path = obj_parm.eval()
                    expected_path = "../Proxy/geo_{}/OUT_{}".format(part_name, part_name)
                    
                    if obj_path == expected_path:
                        print("  [{}] [OK] {}".format(i, part_name))
                    else:
                        print("  [{}] [MISMATCH] {}".format(i, part_name))
                        print("      Current:  {}".format(obj_path))
                        print("      Expected: {}".format(expected_path))
                        all_match = False
            
            if all_match and cloth_parts == numobj:
                print()
                print("[SUCCESS] All paths match expected pattern")
            else:
                print()
                print("[ACTION NEEDED] Synchronization required")
                
except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Check finished")
print("="*80)

connector.disconnect()





