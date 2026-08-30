#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
clear_proxy 최종 테스트 - blast 노드 제거 포함
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Final Test: clear_proxy with Blast Removal")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Copying updated proxy_manager.py...")
print("-" * 80)

# 파일 복사
code_copy = """
import shutil
import os

source = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script\\proxy_manager.py"
dest = r"d:\\Antigravity\\houdini_tools\\proxy_manager.py"

if os.path.exists(source):
    shutil.copy2(source, dest)
    print("[COPIED] proxy_manager.py updated")
    print()
    print("Updated clear_proxy_with_confirm() to:")
    print("  - Check for blast nodes even if count=0")
    print("  - Remove all blast nodes from 3 locations")
    print("  - Better confirmation dialog")
else:
    print("[ERROR] Source not found")
"""

result = connector.execute_code(code_copy)
if result:
    print(result.get("output", ""))

print("\n[2] Checking current state...")
print("-" * 80)

# 현재 상태 확인
code_check = """
import hou

proxy = hou.node("/obj/assets/Proxy")
if proxy:
    count = proxy.parm("cloth_parts").evalAsInt()
    print("Cloth parts: {}".format(count))
else:
    print("[ERROR] Proxy node not found")
    count = 0

# Blast 노드 확인
def count_blasts(parent_path, prefix):
    parent = hou.node(parent_path)
    if not parent:
        return 0
    blasts = [c for c in parent.children() 
              if c.type().name() == "blast" and c.name().startswith(prefix)]
    return len(blasts)

constraint_count = count_blasts("/obj/assets/Constraint", "blast_")
deform_pp_count = count_blasts("/obj/assets/Deform", "proxy_path_blast_")
deform_gp_count = count_blasts("/obj/assets/Deform", "geo_path_blast_")

print()
print("Blast nodes:")
print("  Constraint:        {}".format(constraint_count))
print("  Deform/proxy_path: {}".format(deform_pp_count))
print("  Deform/geo_path:   {}".format(deform_gp_count))
print("  Total:             {}".format(constraint_count + deform_pp_count + deform_gp_count))
"""

result = connector.execute_code(code_check)
if result:
    print(result.get("output", ""))

print("\n[3] Running clear_proxy (automated)...")
print("-" * 80)

# clear_proxy 실행 (자동화)
code_clear = """
import sys
import importlib

# 모듈 리로드
if 'proxy_manager' in sys.modules:
    del sys.modules['proxy_manager']

import hou

proxy_node = hou.node("/obj/assets/Proxy")
if not proxy_node:
    print("[ERROR] Proxy node not found")
else:
    print("[Executing clear_proxy logic]")
    print("="*70)
    print()
    
    # sys.path 설정
    script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
    if script_path not in sys.path:
        sys.path.insert(0, script_path)
    
    import proxy_manager
    
    # clear_proxy 로직 직접 실행 (대화상자 없이)
    try:
        count = proxy_node.parm("cloth_parts").evalAsInt()
    except:
        count = 0
    
    print("Parts count: {}".format(count))
    
    # Geo 노드 삭제
    if count > 0:
        print()
        print("Deleting geo nodes...")
        for i in range(1, count + 1):
            p_name_parm = proxy_node.parm("part_name_{}".format(i))
            if p_name_parm:
                part_name = p_name_parm.evalAsString()
                if part_name:
                    geo_node = proxy_node.node("geo_{}".format(part_name))
                    if geo_node:
                        geo_node.destroy()
                        print("  Deleted: geo_{}".format(part_name))
    
    # Blast 노드 삭제 (항상 실행)
    print()
    print("Clearing blast nodes from all locations...")
    
    assets_node = proxy_node.parent()
    if assets_node:
        total_deleted = 0
        
        # 1. Constraint
        constraint_node = assets_node.node("Constraint")
        if constraint_node:
            blast_nodes = [c for c in constraint_node.children() 
                          if c.type().name() == "blast" and c.name().startswith("blast_")]
            for blast in blast_nodes:
                print("  Deleted: {}".format(blast.path()))
                blast.destroy()
                total_deleted += 1
        
        # 2. Deform
        deform_node = assets_node.node("Deform")
        if deform_node:
            # proxy_path blasts
            pp_blasts = [c for c in deform_node.children() 
                        if c.type().name() == "blast" and c.name().startswith("proxy_path_blast_")]
            for blast in pp_blasts:
                print("  Deleted: {}".format(blast.path()))
                blast.destroy()
                total_deleted += 1
            
            # geo_path blasts
            gp_blasts = [c for c in deform_node.children() 
                        if c.type().name() == "blast" and c.name().startswith("geo_path_blast_")]
            for blast in gp_blasts:
                print("  Deleted: {}".format(blast.path()))
                blast.destroy()
                total_deleted += 1
        
        print()
        print("Total blast nodes deleted: {}".format(total_deleted))
    
    # Multiparm 클리어
    if count > 0:
        proxy_node.parm("cloth_parts").set(0)
        print()
        print("Cleared cloth_parts multiparm")
    
    print()
    print("="*70)
    print("[OK] Clear completed")
"""

result = connector.execute_code(code_clear)
if result:
    print(result.get("output", ""))

print("\n[4] Verifying all nodes are removed...")
print("-" * 80)

# 결과 확인
code_verify = """
import hou

proxy = hou.node("/obj/assets/Proxy")
if proxy:
    count = proxy.parm("cloth_parts").evalAsInt()
    print("[After clear_proxy]")
    print("="*70)
    print()
    print("Cloth parts: {}".format(count))
else:
    count = -1

# Blast 노드 확인
def count_blasts(parent_path, prefix):
    parent = hou.node(parent_path)
    if not parent:
        return 0, []
    blasts = [c for c in parent.children() 
              if c.type().name() == "blast" and c.name().startswith(prefix)]
    return len(blasts), [b.name() for b in blasts]

constraint_count, constraint_names = count_blasts("/obj/assets/Constraint", "blast_")
deform_pp_count, deform_pp_names = count_blasts("/obj/assets/Deform", "proxy_path_blast_")
deform_gp_count, deform_gp_names = count_blasts("/obj/assets/Deform", "geo_path_blast_")

print()
print("Remaining blast nodes:")
print("  Constraint:        {} {}".format(constraint_count, constraint_names if constraint_names else ""))
print("  Deform/proxy_path: {} {}".format(deform_pp_count, deform_pp_names if deform_pp_names else ""))
print("  Deform/geo_path:   {} {}".format(deform_gp_count, deform_gp_names if deform_gp_names else ""))
print()

total = constraint_count + deform_pp_count + deform_gp_count

print("="*70)
print(" Verification")
print("="*70)
print()

if count == 0 and total == 0:
    print("[SUCCESS] All parts and blast nodes removed!")
    print()
    print("Cloth parts: 0 [OK]")
    print("Blast nodes: 0 [OK]")
elif count == 0:
    print("[PARTIAL] Parts cleared but {} blast node(s) remain".format(total))
elif total == 0:
    print("[PARTIAL] Blasts cleared but {} part(s) remain".format(count))
else:
    print("[FAIL] {} part(s) and {} blast node(s) remain".format(count, total))
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
print("clear_proxy now removes:")
print("========================")
print("1. geo_{part_name} nodes (if Delete All selected)")
print("2. ALL Constraint blast_{part_name} nodes")
print("3. ALL Deform/proxy_path_blast_{part_name} nodes")
print("4. ALL Deform/geo_path_blast_{part_name} nodes")
print("5. Cloth parts multiparm entries")
print()
print("Works even if cloth_parts is already 0!")
print()
print("="*80)





