#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test object_merge2 synchronization
"""

import sys
import shutil
import os

sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing object_merge2 Synchronization")
print("="*80)

# Step 1: Copy files to d:\Antigravity
print("\n[1] Copying files to d:\\Antigravity\\houdini_tools...")
print("-" * 80)

source_dir = r"T:\scripts\python\application\houdini\houdini21.0\script"
target_dir = r"d:\Antigravity\houdini_tools"

files_to_copy = [
    "proxy_manager.py",
    "object_merge_sync.py"
]

if os.path.exists(target_dir):
    for filename in files_to_copy:
        src = os.path.join(source_dir, filename)
        dst = os.path.join(target_dir, filename)
        
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print("[OK] Copied: {}".format(filename))
        else:
            print("[ERROR] Source not found: {}".format(src))
else:
    print("[INFO] d:\\Antigravity\\houdini_tools not found, skipping copy")

# Step 2: Connect to Houdini and test
print("\n[2] Connecting to Houdini...")
print("-" * 80)

connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

# Step 3: Test object_merge2 sync
print("\n[3] Testing object_merge2 synchronization...")
print("-" * 80)

code = """
import sys
import hou

# Ensure module path
script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

try:
    # Import module
    import object_merge_sync
    print("[OK] object_merge_sync module imported")
    print()
    
    # Get proxy node
    proxy_node = hou.node("/obj/assets/Proxy")
    if not proxy_node:
        print("[ERROR] Proxy node not found")
    else:
        print("[OK] Proxy node found")
        print()
        
        # Run sync
        print("="*70)
        print(" EXECUTING SYNC")
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
            print()
            print("[ERROR] Sync failed")
            
except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

# Step 4: Test via Proxy update_proxy button
print("\n[4] Testing via Proxy.update_proxy button...")
print("-" * 80)
print("[INFO] Please click the 'Update Proxy' button in Houdini to test")
print("[INFO] The object_merge2 should be automatically synced")

print("\n" + "="*80)
print("[COMPLETE] Test finished")
print("="*80)

connector.disconnect()





