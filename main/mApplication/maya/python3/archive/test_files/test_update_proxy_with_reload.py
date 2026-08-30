#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
update_proxy 통합 테스트 (모듈 리로드 포함)
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing update_proxy with Blast Sync Integration")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Removing existing blast nodes for fresh test...")
print("-" * 80)

# 기존 blast 제거
code_clean = """
import hou

constraint = hou.node("/obj/assets/Constraint")
if constraint:
    blast_nodes = [c for c in constraint.children() if c.type().name() == "blast" and c.name().startswith("blast_")]
    
    if blast_nodes:
        for blast in blast_nodes:
            print("Removing: {}".format(blast.name()))
            blast.destroy()
        print("Removed {} blast node(s)".format(len(blast_nodes)))
    else:
        print("No blast nodes to remove")
"""

result = connector.execute_code(code_clean)
if result:
    print(result.get("output", ""))

print("\n[2] Running update_proxy_nodes() with module reload...")
print("-" * 80)

# 모듈 리로드 후 update_proxy 실행
code_update = """
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
else:
    import proxy_blast_sync

if 'proxy_manager' in sys.modules:
    import proxy_manager
    importlib.reload(proxy_manager)
else:
    import proxy_manager

print("[Executing proxy_manager.update_proxy_nodes()]")
print("="*70)

proxy_node = hou.node("/obj/assets/Proxy")
if proxy_node:
    proxy_manager.update_proxy_nodes(proxy_node)
else:
    print("[ERROR] Proxy node not found")

print("="*70)
"""

result = connector.execute_code(code_update)
if result:
    print(result.get("output", ""))

print("\n[3] Verifying results...")
print("-" * 80)

# 결과 확인
code_verify = """
import hou

print("[Verification Results]")
print("="*70)
print()

proxy = hou.node("/obj/assets/Proxy")
constraint = hou.node("/obj/assets/Constraint")

if proxy and constraint:
    # Proxy parts
    count = proxy.parm("cloth_parts").evalAsInt()
    part_names = []
    for i in range(1, count + 1):
        part_name = proxy.parm("part_name_{}".format(i)).evalAsString()
        if part_name:
            part_names.append(part_name)
    
    print("Proxy Cloth Parts: {}".format(len(part_names)))
    for name in part_names:
        print("  - {}".format(name))
    
    print()
    
    # Blast nodes
    blast_nodes = [c for c in constraint.children() if c.type().name() == "blast" and c.name().startswith("blast_")]
    
    print("Constraint Blast Nodes: {}".format(len(blast_nodes)))
    for blast in sorted(blast_nodes, key=lambda x: x.name()):
        group = blast.parm("group").evalAsString()
        print("  - {} (group: {})".format(blast.name(), group))
    
    print()
    print("="*70)
    
    # Match check
    expected = ["blast_{}".format(p) for p in part_names]
    actual = [b.name() for b in blast_nodes]
    
    if set(expected) == set(actual):
        print("[SUCCESS] Blast nodes match cloth parts perfectly!")
    else:
        print("[WARNING] Mismatch detected")
        missing = set(expected) - set(actual)
        extra = set(actual) - set(expected)
        if missing:
            print("Missing: {}".format(', '.join(missing)))
        if extra:
            print("Extra: {}".format(', '.join(extra)))
"""

result = connector.execute_code(code_verify)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Integration test completed!")
print("="*80)

connector.disconnect()

print("\n" + "="*80)
print(" Integration Summary")
print("="*80)
print()
print("Feature: Automatic Blast Sync in update_proxy")
print("=============================================")
print()
print("When you click 'Update Proxy Nodes' button:")
print("  1. Creates/updates geo_{part_name} nodes")
print("  2. Automatically syncs blast_{part_name} nodes in Constraint")
print("  3. Sets group parameters to @proxy_path patterns")
print("  4. Connects to proxy_path node")
print()
print("Benefits:")
print("  - No manual blast node creation needed")
print("  - Automatically keeps blast nodes in sync")
print("  - Removes orphaned blast nodes")
print()
print("="*80)





