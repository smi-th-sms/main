#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Blast sync 직접 호출 테스트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing Direct Blast Sync")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Calling blast sync directly...")
print("-" * 80)

# 직접 blast sync 호출
code = """
import sys
import importlib

script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
if script_path not in sys.path:
    sys.path.append(script_path)

import hou

# 모듈 리로드
if 'proxy_blast_sync' in sys.modules:
    import proxy_blast_sync
    importlib.reload(proxy_blast_sync)
    print("[INFO] Reloaded proxy_blast_sync module")
else:
    import proxy_blast_sync
    print("[INFO] Imported proxy_blast_sync module")

if 'proxy_manager' in sys.modules:
    import proxy_manager
    importlib.reload(proxy_manager)
    print("[INFO] Reloaded proxy_manager module")
else:
    import proxy_manager
    print("[INFO] Imported proxy_manager module")

print()
print("="*70)
print(" Direct Blast Sync Test")
print("="*70)
print()

proxy_node = hou.node("/obj/assets/Proxy")
if not proxy_node:
    print("[ERROR] Proxy node not found")
else:
    print("[OK] Found Proxy node")
    
    # Method 1: sync_proxy_blasts (part names based)
    print("\\n[Method 1: Part Names Based]")
    print("-"*70)
    
    created, updated, deleted = proxy_blast_sync.sync_proxy_blasts(proxy_node)
    
    print("\\nResults:")
    print("  Created: {}".format(created))
    print("  Updated: {}".format(updated))
    print("  Deleted: {}".format(deleted))
    
    # Check results
    print("\\n[Verification]")
    print("-"*70)
    
    constraint = hou.node("/obj/assets/Constraint")
    if constraint:
        blast_nodes = [c for c in constraint.children() if c.type().name() == "blast" and c.name().startswith("blast_")]
        
        print("Blast nodes created: {}\\n".format(len(blast_nodes)))
        
        for blast in sorted(blast_nodes, key=lambda x: x.name()):
            group = blast.parm("group").evalAsString()
            inputs = blast.inputs()
            input_name = inputs[0].name() if inputs and inputs[0] else "(no input)"
            
            print("  - {}".format(blast.name()))
            print("      Group: {}".format(group))
            print("      Input: {}".format(input_name))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Test completed!")
print("="*80)

connector.disconnect()





