#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Proxy blast sync 기능 테스트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing Proxy Blast Sync Feature")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Current state before sync...")
print("-" * 80)

# 현재 상태 확인
code_before = """
import hou

constraint = hou.node("/obj/assets/Constraint")
if constraint:
    blast_nodes = [c for c in constraint.children() if c.type().name() == "blast" and c.name().startswith("blast_")]
    
    print("Current blast nodes: {}".format(len(blast_nodes)))
    if blast_nodes:
        for blast in blast_nodes:
            group = blast.parm("group").evalAsString()
            print("  - {} (group: {})".format(blast.name(), group))
    else:
        print("  (no blast nodes yet)")

proxy = hou.node("/obj/assets/Proxy")
if proxy:
    count = proxy.parm("cloth_parts").evalAsInt()
    print("\\nProxy cloth parts: {}".format(count))
    if count > 0:
        for i in range(1, count + 1):
            part_name = proxy.parm("part_name_{}".format(i)).evalAsString()
            print("  {}. {}".format(i, part_name))
"""

result = connector.execute_code(code_before)
if result:
    print(result.get("output", ""))

print("\n[2] Running update_proxy (with blast sync)...")
print("-" * 80)

# update_proxy 실행 (blast sync 포함)
code_update = """
import sys
script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
if script_path not in sys.path:
    sys.path.append(script_path)

import hou
import proxy_manager

proxy_node = hou.node("/obj/assets/Proxy")
if proxy_node:
    print("[Executing proxy_manager.update_proxy_nodes()]")
    print("="*70)
    proxy_manager.update_proxy_nodes(proxy_node)
    print("="*70)
else:
    print("[ERROR] Proxy node not found")
"""

result = connector.execute_code(code_update)
if result:
    print(result.get("output", ""))

print("\n[3] Checking results after sync...")
print("-" * 80)

# 결과 확인
code_after = """
import hou

constraint = hou.node("/obj/assets/Constraint")
if constraint:
    blast_nodes = [c for c in constraint.children() if c.type().name() == "blast" and c.name().startswith("blast_")]
    
    print("Blast nodes after sync: {}".format(len(blast_nodes)))
    print()
    
    if blast_nodes:
        print("Details:")
        for blast in sorted(blast_nodes, key=lambda x: x.name()):
            group = blast.parm("group").evalAsString()
            negate = blast.parm("negate").evalAsInt()
            inputs = blast.inputs()
            input_name = inputs[0].name() if inputs and inputs[0] else "(no input)"
            
            print("  - {}".format(blast.name()))
            print("      Group: {}".format(group))
            print("      Negate: {}".format("Delete Non-Selected" if negate else "Delete Selected"))
            print("      Input: {}".format(input_name))
            print()
    
    # Verification
    proxy = hou.node("/obj/assets/Proxy")
    if proxy:
        count = proxy.parm("cloth_parts").evalAsInt()
        expected_blasts = []
        for i in range(1, count + 1):
            part_name = proxy.parm("part_name_{}".format(i)).evalAsString()
            if part_name:
                expected_blasts.append("blast_{}".format(part_name))
        
        actual_blast_names = [b.name() for b in blast_nodes]
        
        print("="*70)
        print(" Verification")
        print("="*70)
        print()
        print("Expected blast nodes: {}".format(len(expected_blasts)))
        for name in expected_blasts:
            exists = name in actual_blast_names
            status = "[OK]" if exists else "[MISSING]"
            print("  {} {}".format(status, name))
        
        print()
        print("Actual blast nodes: {}".format(len(actual_blast_names)))
        for name in actual_blast_names:
            expected = name in expected_blasts
            status = "[OK]" if expected else "[EXTRA]"
            print("  {} {}".format(status, name))
        
        print()
        if set(expected_blasts) == set(actual_blast_names):
            print("[SUCCESS] Blast nodes match exactly!")
        else:
            print("[WARNING] Blast nodes do not match expected list")
"""

result = connector.execute_code(code_after)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Test completed!")
print("="*80)

connector.disconnect()

print("\n" + "="*80)
print(" Test Summary")
print("="*80)
print()
print("Feature Tested:")
print("==============")
print("update_proxy_nodes() now includes blast sync")
print()
print("Expected Behavior:")
print("=================")
print("1. Creates blast_{part_name} for each cloth part")
print("2. Sets group parameter to @proxy_path pattern")
print("3. Connects to proxy_path node as input")
print("4. Sets negate=1 (Delete Non-Selected)")
print("5. Removes blast nodes for deleted parts")
print()
print("Integration:")
print("===========")
print("- Runs automatically when update_proxy button is clicked")
print("- Runs when part_name_# is changed")
print("- Fallback to part names if @proxy_path not available")
print()
print("="*80)





