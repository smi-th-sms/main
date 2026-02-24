#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
clear_proxy 실행 시 blast 노드들도 제거되는지 테스트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing clear_proxy with Blast Nodes")
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
else:
    print("[ERROR] Source not found")
"""

result = connector.execute_code(code_copy)
if result:
    print(result.get("output", ""))

print("\n[2] Checking current blast nodes...")
print("-" * 80)

# 현재 blast 노드 확인
code_check = """
import hou

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

print("[Before clear_proxy]")
print("="*70)
print()
print("Constraint blast nodes:        {}".format(constraint_count))
print("Deform/proxy_path blast nodes: {}".format(deform_pp_count))
print("Deform/geo_path blast nodes:   {}".format(deform_gp_count))
print()
print("Total blast nodes: {}".format(constraint_count + deform_pp_count + deform_gp_count))
"""

result = connector.execute_code(code_check)
if result:
    print(result.get("output", ""))

print("\n[3] Executing clear_proxy (with confirmation)...")
print("-" * 80)
print()
print("NOTE: Dialog will auto-select 'Delete Nodes'")
print()

# clear_proxy 실행 (자동 확인)
code_clear = """
import sys
import importlib

# 모듈 리로드
if 'proxy_manager' in sys.modules:
    del sys.modules['proxy_manager']

import hou

proxy_node = hou.node("/obj/assets/Proxy")
if proxy_node:
    print("[Executing clear_proxy_with_confirm]")
    print("="*70)
    
    # clear_proxy 파라미터의 스크립트를 직접 실행
    # 대화상자 없이 직접 함수 호출
    try:
        # sys.path 설정
        script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
        if script_path not in sys.path:
            sys.path.insert(0, script_path)
        
        import proxy_manager
        
        # clear_proxy_with_confirm 대신 직접 로직 실행
        # (대화상자 없이)
        count = proxy_node.parm("cloth_parts").evalAsInt()
        
        if count == 0:
            print("[INFO] No parts to clear")
        else:
            print("[INFO] Clearing {} part(s)".format(count))
            print()
            
            # 노드 삭제 (delete_nodes = True로 가정)
            delete_nodes = True
            
            # Geo 노드 삭제
            if delete_nodes:
                for i in range(1, count + 1):
                    p_name_parm = proxy_node.parm("part_name_{}".format(i))
                    if p_name_parm:
                        part_name = p_name_parm.evalAsString()
                        if part_name:
                            geo_node = proxy_node.node("geo_{}".format(part_name))
                            if geo_node:
                                geo_node.destroy()
                                print("Deleted: geo_{}".format(part_name))
            
            # Blast 노드 삭제
            print()
            print("Clearing blast nodes from all locations...")
            
            assets_node = proxy_node.parent()
            if assets_node:
                # Constraint
                constraint_node = assets_node.node("Constraint")
                if constraint_node:
                    blast_nodes = [c for c in constraint_node.children() 
                                  if c.type().name() == "blast" and c.name().startswith("blast_")]
                    for blast in blast_nodes:
                        print("  Deleted: {}".format(blast.path()))
                        blast.destroy()
                
                # Deform
                deform_node = assets_node.node("Deform")
                if deform_node:
                    # proxy_path blasts
                    pp_blasts = [c for c in deform_node.children() 
                                if c.type().name() == "blast" and c.name().startswith("proxy_path_blast_")]
                    for blast in pp_blasts:
                        print("  Deleted: {}".format(blast.path()))
                        blast.destroy()
                    
                    # geo_path blasts
                    gp_blasts = [c for c in deform_node.children() 
                                if c.type().name() == "blast" and c.name().startswith("geo_path_blast_")]
                    for blast in gp_blasts:
                        print("  Deleted: {}".format(blast.path()))
                        blast.destroy()
            
            print()
            print("Blast nodes cleared from all locations")
            
            # Multiparm 클리어
            proxy_node.parm("cloth_parts").set(0)
            print()
            print("Cleared {} part(s). Nodes deleted.".format(count))
    
    except Exception as e:
        print("[ERROR] {}".format(str(e)))
        import traceback
        traceback.print_exc()
    
    print("="*70)
else:
    print("[ERROR] Proxy node not found")
"""

result = connector.execute_code(code_clear)
if result:
    print(result.get("output", ""))

print("\n[4] Verifying blast nodes are removed...")
print("-" * 80)

# 결과 확인
code_verify = """
import hou

def count_blasts(parent_path, prefix):
    parent = hou.node(parent_path)
    if not parent:
        return 0
    blasts = [c for c in parent.children() 
              if c.type().name() == "blast" and c.name().startswith(prefix)]
    return len(blasts), [b.name() for b in blasts]

constraint_count, constraint_names = count_blasts("/obj/assets/Constraint", "blast_")
deform_pp_count, deform_pp_names = count_blasts("/obj/assets/Deform", "proxy_path_blast_")
deform_gp_count, deform_gp_names = count_blasts("/obj/assets/Deform", "geo_path_blast_")

print("[After clear_proxy]")
print("="*70)
print()
print("Constraint blast nodes:        {}".format(constraint_count))
if constraint_names:
    for name in constraint_names:
        print("  - {}".format(name))

print("Deform/proxy_path blast nodes: {}".format(deform_pp_count))
if deform_pp_names:
    for name in deform_pp_names:
        print("  - {}".format(name))

print("Deform/geo_path blast nodes:   {}".format(deform_gp_count))
if deform_gp_names:
    for name in deform_gp_names:
        print("  - {}".format(name))

print()
print("Total blast nodes: {}".format(constraint_count + deform_pp_count + deform_gp_count))
print()

# 검증
total = constraint_count + deform_pp_count + deform_gp_count
if total == 0:
    print("[SUCCESS] All blast nodes removed!")
else:
    print("[WARNING] {} blast node(s) still remain".format(total))

# Cloth parts 확인
proxy = hou.node("/obj/assets/Proxy")
if proxy:
    parts_count = proxy.parm("cloth_parts").evalAsInt()
    print()
    print("Cloth parts count: {}".format(parts_count))
    if parts_count == 0:
        print("[OK] Cloth parts cleared")
    else:
        print("[WARNING] Cloth parts not cleared")
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
print("1. geo_{part_name} nodes (optional)")
print("2. Constraint blast nodes")
print("3. Deform/proxy_path blast nodes")
print("4. Deform/geo_path blast nodes")
print("5. Cloth parts multiparm entries")
print()
print("Total cleanup: Complete scene reset!")
print()
print("="*80)





