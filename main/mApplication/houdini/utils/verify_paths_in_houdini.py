#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verify object paths in Houdini scene
"""

import sys
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Verifying Paths in Houdini")
print("="*80)

connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

code = """
import hou

try:
    merge_node = hou.node("/obj/assets/Cache/object_merge2")
    if not merge_node:
        print("[ERROR] object_merge2 not found")
    else:
        print("[OK] object_merge2 found: {}".format(merge_node.path()))
        print()
        
        numobj = merge_node.parm("numobj").eval()
        print("[INFO] Number of objects: {}".format(numobj))
        print()
        
        print("Checking paths...")
        print("="*70)
        
        for i in range(1, numobj + 1):
            objpath_parm = merge_node.parm("objpath{}".format(i))
            if not objpath_parm:
                continue
            
            relative_path = objpath_parm.eval()
            print()
            print("[{}] Relative path: {}".format(i, relative_path))
            
            # Try to resolve the path from merge_node
            if relative_path:
                # Method 1: Using merge_node.node()
                target_node = merge_node.node(relative_path)
                if target_node:
                    print("    [OK] Resolved to: {}".format(target_node.path()))
                else:
                    print("    [ERROR] merge_node.node() failed")
                    
                    # Method 2: Try expanding the path
                    try:
                        abs_path = merge_node.relativePathTo(hou.node(relative_path))
                        print("    [INFO] Tried absolute resolution...")
                    except:
                        pass
                    
                    # Method 3: Manual construction
                    # From /obj/assets/Cache/object_merge2
                    # ../Proxy means /obj/assets/Proxy
                    merge_parent = merge_node.parent()  # /obj/assets/Cache
                    if merge_parent:
                        assets_node = merge_parent.parent()  # /obj/assets
                        if assets_node:
                            manual_path = relative_path.replace("..", assets_node.path())
                            print("    [INFO] Manual construction: {}".format(manual_path))
                            manual_node = hou.node(manual_path)
                            if manual_node:
                                print("    [OK] Manual resolve SUCCESS: {}".format(manual_node.path()))
                            else:
                                print("    [ERROR] Manual resolve FAILED")
            else:
                print("    [WARNING] Empty path")
        
        print()
        print("="*70)
        print()
        
        # Check if object_merge2 can actually merge the geometry
        print("Testing geometry merge...")
        try:
            geo = merge_node.geometry()
            if geo:
                num_points = len(geo.points())
                num_prims = len(geo.prims())
                print("[OK] Geometry merged successfully!")
                print("    Points: {}".format(num_points))
                print("    Primitives: {}".format(num_prims))
            else:
                print("[WARNING] No geometry output")
        except Exception as e:
            print("[ERROR] Failed to get geometry: {}".format(str(e)))
        
except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
connector.disconnect()





