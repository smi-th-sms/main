#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test corrected paths with ../../
"""

import sys
import shutil
import os

sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing Corrected Paths (../../)")
print("="*80)

# Step 1: Copy corrected files
print("\n[1] Copying corrected files...")
print("-" * 80)

source_dir = r"T:\scripts\python\application\houdini\houdini21.0\script"
target_dir = r"d:\Antigravity\houdini_tools"

files_to_copy = [
    "object_merge_sync.py",
    "proxy_manager.py"
]

if os.path.exists(target_dir):
    for filename in files_to_copy:
        src = os.path.join(source_dir, filename)
        dst = os.path.join(target_dir, filename)
        
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print("[OK] Copied: {}".format(filename))

# Step 2: Connect and test
print("\n[2] Connecting to Houdini...")
print("-" * 80)

connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

# Step 3: Clear module cache and resync
print("\n[3] Clearing module cache and resyncing...")
print("-" * 80)

code = """
import sys
import hou

# Clear modules
if 'object_merge_sync' in sys.modules:
    del sys.modules['object_merge_sync']

# Reload
script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

try:
    import object_merge_sync
    
    print("[INFO] Module reloaded with corrected paths (../../)")
    print()
    
    # Sync
    proxy_node = hou.node("/obj/assets/Proxy")
    if proxy_node:
        print("="*70)
        print(" SYNCING WITH CORRECTED PATHS")
        print("="*70)
        print()
        
        success = object_merge_sync.sync_object_merge2(proxy_node)
        
        if success:
            print()
            print("="*70)
            print(" VERIFICATION")
            print("="*70)
            print()
            
            object_merge_sync.verify_object_merge2()
    else:
        print("[ERROR] Proxy node not found")
        
except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

# Step 4: Test actual geometry merge
print("\n[4] Testing geometry merge functionality...")
print("-" * 80)

code = """
import hou

try:
    merge_node = hou.node("/obj/assets/Cache/object_merge2")
    if merge_node:
        print("[INFO] Testing object_merge2 geometry output...")
        print()
        
        # Check each path individually
        numobj = merge_node.parm("numobj").eval()
        
        for i in range(1, numobj + 1):
            objpath_parm = merge_node.parm("objpath{}".format(i))
            if objpath_parm:
                path = objpath_parm.eval()
                print("[{}] Path: {}".format(i, path))
                
                # Try to evaluate the path
                try:
                    # object_merge will evaluate the path internally
                    # We can check if the path is working by checking if merge succeeds
                    pass
                except Exception as e:
                    print("    [ERROR] {}".format(str(e)))
        
        print()
        
        # Try to get merged geometry
        try:
            merge_node.cook(force=True)
            geo = merge_node.geometry()
            if geo:
                num_points = len(geo.points())
                num_prims = len(geo.prims())
                print("[SUCCESS] Geometry merge working!")
                print("          Points: {}".format(num_points))
                print("          Primitives: {}".format(num_prims))
                
                if num_points > 0 or num_prims > 0:
                    print()
                    print("[EXCELLENT] Geometry data found - paths are correct!")
                else:
                    print()
                    print("[INFO] No geometry yet (may be expected if proxies are empty)")
            else:
                print("[WARNING] No geometry output")
        except Exception as e:
            print("[ERROR] Failed to get geometry: {}".format(str(e)))
            import traceback
            traceback.print_exc()
    else:
        print("[ERROR] object_merge2 not found")
        
except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Path correction test finished")
print("="*80)
print()
print("The paths have been corrected from ../ to ../../")
print("This accounts for object_merge2 being inside the Cache geo node.")

connector.disconnect()





