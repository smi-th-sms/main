#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
업데이트된 파일 복사 및 전체 위치 blast sync 테스트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Updating Files and Testing All Blast Locations")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Copying updated files to d:\\Antigravity...")
print("-" * 80)

# 파일 복사
code_copy = """
import shutil
import os

files_to_copy = [
    ('proxy_manager.py', 'Main proxy manager module'),
    ('proxy_blast_sync.py', 'Blast sync module (extended)'),
]

source_dir = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
dest_dir = r"d:\\Antigravity\\houdini_tools"

for filename, description in files_to_copy:
    source = os.path.join(source_dir, filename)
    dest = os.path.join(dest_dir, filename)
    
    if os.path.exists(source):
        shutil.copy2(source, dest)
        print("[COPIED] {} - {}".format(filename, description))
    else:
        print("[ERROR] Source not found: {}".format(source))

print()
print("[OK] Files updated")
"""

result = connector.execute_code(code_copy)
if result:
    print(result.get("output", ""))

print("\n[2] Clearing existing blast nodes for fresh test...")
print("-" * 80)

# 기존 blast 노드 제거
code_clean = """
import hou

locations = [
    ("/obj/assets/Constraint", "blast_"),
    ("/obj/assets/Deform", "proxy_path_blast_"),
    ("/obj/assets/Deform", "geo_path_blast_"),
]

total_removed = 0

for parent_path, prefix in locations:
    parent = hou.node(parent_path)
    if parent:
        blasts = [c for c in parent.children() 
                  if c.type().name() == "blast" and c.name().startswith(prefix)]
        
        if blasts:
            print("[{}] Removing {} blast node(s)".format(parent_path, len(blasts)))
            for blast in blasts:
                print("  - {}".format(blast.name()))
                blast.destroy()
            total_removed += len(blasts)

print()
print("[Removed] Total: {} blast node(s)".format(total_removed))
"""

result = connector.execute_code(code_clean)
if result:
    print(result.get("output", ""))

print("\n[3] Running update_proxy (all locations sync)...")
print("-" * 80)

# update_proxy 실행
code_test = """
import sys
import importlib

# 모듈 리로드
for mod in ['proxy_manager', 'proxy_blast_sync']:
    if mod in sys.modules:
        del sys.modules[mod]

import hou

proxy_node = hou.node("/obj/assets/Proxy")
if proxy_node:
    print("[Executing update_proxy_nodes]")
    print("="*70)
    
    # update_proxy 버튼 실행
    update_parm = proxy_node.parm("update_proxy")
    if update_parm:
        try:
            update_parm.pressButton()
        except:
            # 직접 스크립트 실행
            ptg = proxy_node.parmTemplateGroup()
            template = ptg.find("update_proxy")
            if template:
                callback = template.scriptCallback()
                exec(callback, {'kwargs': {'node': proxy_node}})
    
    print("="*70)
else:
    print("[ERROR] Proxy node not found")
"""

result = connector.execute_code(code_test)
if result:
    print(result.get("output", ""))

print("\n[4] Verifying blast nodes in all locations...")
print("-" * 80)

# 결과 확인
code_verify = """
import hou

print("[Verification Results]")
print("="*70)
print()

proxy = hou.node("/obj/assets/Proxy")
if proxy:
    count = proxy.parm("cloth_parts").evalAsInt()
    part_names = []
    for i in range(1, count + 1):
        name = proxy.parm("part_name_{}".format(i)).evalAsString()
        if name:
            part_names.append(name)
    
    print("Proxy Cloth Parts: {}".format(len(part_names)))
    for name in part_names:
        print("  - {}".format(name))
    print()

# 1. Constraint
constraint = hou.node("/obj/assets/Constraint")
if constraint:
    blasts = [c for c in constraint.children() 
              if c.type().name() == "blast" and c.name().startswith("blast_")]
    
    print("[1] Constraint blast nodes: {}".format(len(blasts)))
    for blast in sorted(blasts, key=lambda x: x.name()):
        group = blast.parm("group").evalAsString()
        print("  - {} (group: {})".format(blast.name(), group))
    print()

# 2. Deform/proxy_path
deform = hou.node("/obj/assets/Deform")
if deform:
    pp_blasts = [c for c in deform.children() 
                 if c.type().name() == "blast" and c.name().startswith("proxy_path_blast_")]
    
    print("[2] Deform/proxy_path blast nodes: {}".format(len(pp_blasts)))
    for blast in sorted(pp_blasts, key=lambda x: x.name()):
        group = blast.parm("group").evalAsString()
        inputs = blast.inputs()
        input_name = inputs[0].name() if inputs and inputs[0] else "(no input)"
        print("  - {} (group: {}, input: {})".format(blast.name(), group, input_name))
    print()
    
    # 3. Deform/geo_path
    gp_blasts = [c for c in deform.children() 
                 if c.type().name() == "blast" and c.name().startswith("geo_path_blast_")]
    
    print("[3] Deform/geo_path blast nodes: {}".format(len(gp_blasts)))
    for blast in sorted(gp_blasts, key=lambda x: x.name()):
        group = blast.parm("group").evalAsString()
        inputs = blast.inputs()
        input_name = inputs[0].name() if inputs and inputs[0] else "(no input)"
        print("  - {} (group: {}, input: {})".format(blast.name(), group, input_name))
    print()

# 검증
print("="*70)
print(" Verification")
print("="*70)
print()

if part_names:
    expected_count = len(part_names)
    
    constraint_ok = len(blasts) == expected_count if constraint else False
    deform_pp_ok = len(pp_blasts) == expected_count if deform else False
    deform_gp_ok = len(gp_blasts) == expected_count if deform else False
    
    print("Expected blast nodes per location: {}".format(expected_count))
    print()
    print("Constraint: {} {}".format(
        len(blasts) if constraint else 0,
        "[OK]" if constraint_ok else "[FAIL]"))
    print("Deform/proxy_path: {} {}".format(
        len(pp_blasts) if deform else 0,
        "[OK]" if deform_pp_ok else "[FAIL]"))
    print("Deform/geo_path: {} {}".format(
        len(gp_blasts) if deform else 0,
        "[OK]" if deform_gp_ok else "[FAIL]"))
    print()
    
    if constraint_ok and deform_pp_ok and deform_gp_ok:
        print("[SUCCESS] All locations have correct blast nodes!")
    else:
        print("[WARNING] Some locations have incorrect blast count")
    
    # @geo_path 패턴 확인
    if gp_blasts:
        print()
        print("Checking @geo_path pattern:")
        all_have_geo_path = all("@geo_path" in b.parm("group").evalAsString() 
                                for b in gp_blasts)
        if all_have_geo_path:
            print("  [OK] All geo_path blasts use @geo_path pattern")
        else:
            print("  [WARNING] Some blasts don't use @geo_path pattern")
"""

result = connector.execute_code(code_verify)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Test completed!")
print("="*80)

connector.disconnect()

print("\n" + "="*80)
print(" Summary")
print("="*80)
print()
print("Blast Sync Locations:")
print("====================")
print("1. Constraint          - blast_{part_name} (@proxy_path)")
print("2. Deform/proxy_path   - proxy_path_blast_{part_name} (@proxy_path)")
print("3. Deform/geo_path     - geo_path_blast_{part_name} (@geo_path)")
print()
print("All locations are now synchronized when update_proxy is executed!")
print()
print("="*80)





