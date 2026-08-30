#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analyze scripts usage and prepare for packaging
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" CFX Scripts Analysis & Packaging Preparation")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Analyzing script dependencies...")
print("-" * 80)

code = """
import os

script_dir = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"

# Core runtime scripts (essential for operation)
core_scripts = {
    'cfx_assets_ui.py': 'Main UI window for CFX Assets Manager',
    'launch_cfx_ui.py': 'UI launcher script',
    'proxy_manager.py': 'Proxy node management (update_proxy, clear_proxy, etc)',
    'proxy_blast_sync.py': 'Blast node synchronization across locations',
    'parts_deform_sync_callback.py': 'Parts_Deform node auto-sync (used by sim_filecache)',
    'project_dir_simple_menu.py': 'Project directory menu script (used by HDA)',
}

# Development/Testing scripts (not needed for deployment)
dev_scripts = {
    'houdini_mcp_connector.py': 'MCP connector - development only',
    'connect_to_houdini.py': 'MCP helper - development only',
}

# Documentation files
doc_files = []
other_files = []

if os.path.exists(script_dir):
    for filename in os.listdir(script_dir):
        filepath = os.path.join(script_dir, filename)
        
        if os.path.isfile(filepath):
            if filename.endswith('.txt'):
                doc_files.append(filename)
            elif filename not in core_scripts and filename not in dev_scripts:
                if not filename.endswith('.pyc') and filename != '__pycache__':
                    other_files.append(filename)

print("="*70)
print(" CORE RUNTIME SCRIPTS (Essential for deployment)")
print("="*70)
for script, desc in core_scripts.items():
    exists = os.path.exists(os.path.join(script_dir, script))
    status = "[OK]" if exists else "[MISSING]"
    print("{} {}".format(status, script))
    print("    {}".format(desc))
print()

print("="*70)
print(" DEVELOPMENT SCRIPTS (Optional - can be excluded)")
print("="*70)
for script, desc in dev_scripts.items():
    exists = os.path.exists(os.path.join(script_dir, script))
    status = "[OK]" if exists else "[MISSING]"
    print("{} {}".format(status, script))
    print("    {}".format(desc))
print()

print("="*70)
print(" DOCUMENTATION FILES ({} files)".format(len(doc_files)))
print("="*70)
print("These are development notes and can be consolidated/archived:")
for doc in sorted(doc_files):
    print("  - {}".format(doc))
print()

if other_files:
    print("="*70)
    print(" OTHER FILES")
    print("="*70)
    for f in other_files:
        print("  - {}".format(f))
    print()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[2] Checking HDA parameter callbacks...")
print("-" * 80)

code = """
import hou

try:
    assets_node = hou.node("/obj/assets")
    if not assets_node:
        print("[INFO] No /obj/assets node found in current scene")
    else:
        print("[OK] Found assets node: {}".format(assets_node.path()))
        print()
        
        # Check Proxy node callbacks
        proxy_node = hou.node("/obj/assets/Proxy")
        if proxy_node:
            print("Proxy node callbacks:")
            
            # update_proxy button
            update_parm = proxy_node.parm("update_proxy")
            if update_parm:
                pt = update_parm.parmTemplate()
                script = pt.scriptCallback()
                if 'proxy_manager' in script:
                    print("  [OK] update_proxy uses proxy_manager.py")
                    
            # clear_proxy button  
            clear_parm = proxy_node.parm("clear_proxy")
            if clear_parm:
                pt = clear_parm.parmTemplate()
                script = pt.scriptCallback()
                if 'proxy_manager' in script:
                    print("  [OK] clear_proxy uses proxy_manager.py")
            
            # export_proxy_cache button
            export_parm = proxy_node.parm("export_proxy_cache")
            if export_parm:
                pt = export_parm.parmTemplate()
                script = pt.scriptCallback()
                if 'proxy_manager' in script:
                    print("  [OK] export_proxy_cache uses proxy_manager.py")
                    
            print()
        
        # Check sim_filecache Pre-Render Script
        filecache_node = hou.node("/obj/assets/Constraint/sim_filecache")
        if filecache_node:
            prerender = filecache_node.parm("prerender")
            if prerender:
                script = prerender.eval()
                if 'parts_deform_sync_callback' in script:
                    print("sim_filecache Pre-Render Script:")
                    print("  [OK] Uses parts_deform_sync_callback.py")
                    print()

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[3] Checking external dependencies...")
print("-" * 80)

code = """
import os

# Check d:/Antigravity path
antigravity_path = r"d:/Antigravity/houdini_tools"
if os.path.exists(antigravity_path):
    print("[INFO] External dependency path exists:")
    print("      {}".format(antigravity_path))
    print()
    print("      Scripts copied for compatibility:")
    
    for script in ['proxy_manager.py', 'proxy_blast_sync.py']:
        script_path = os.path.join(antigravity_path, script)
        if os.path.exists(script_path):
            print("      [OK] {}".format(script))
        else:
            print("      [MISSING] {}".format(script))
    print()
    print("      NOTE: For deployment, users may need to set up this path")
    print("            OR HDA callbacks should be updated to use only T:\\scripts")
else:
    print("[INFO] External dependency path not found (OK for new installations)")
    print("      {}".format(antigravity_path))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Analysis finished")
print("="*80)

connector.disconnect()





