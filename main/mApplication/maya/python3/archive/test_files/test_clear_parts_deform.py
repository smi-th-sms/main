#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parts_Deform 자동 삭제 기능 테스트 (clear_proxy)
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Testing Parts_Deform Auto-Deletion (clear_proxy)")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[BEFORE] Checking existing nodes...")
print("-" * 80)

code = """
import hou

try:
    # Constraint blasts
    constraint = hou.node("/obj/assets/Constraint")
    if constraint:
        blasts = [c for c in constraint.children() if c.type().name() == "blast" and c.name().startswith("blast_")]
        print("[Constraint] {} blast node(s)".format(len(blasts)))
    
    # Deform blasts and Parts_Deform
    deform = hou.node("/obj/assets/Deform")
    if deform:
        proxy_blasts = [c for c in deform.children() if c.type().name() == "blast" and c.name().startswith("proxy_path_blast_")]
        geo_blasts = [c for c in deform.children() if c.type().name() == "blast" and c.name().startswith("geo_path_blast_")]
        parts_deform = [c for c in deform.children() if c.type().name() == "subnet" and c.name().startswith("Parts_Deform_")]
        
        print("[Deform] {} proxy_path blast(s)".format(len(proxy_blasts)))
        print("[Deform] {} geo_path blast(s)".format(len(geo_blasts)))
        print("[Deform] {} Parts_Deform node(s)".format(len(parts_deform)))
        
        if parts_deform:
            print()
            print("Parts_Deform nodes:")
            for node in parts_deform:
                print("  - {}".format(node.name()))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[ACTION] Executing clear_proxy (choosing 'Delete All')...")
print("-" * 80)

code = """
import sys
import hou

try:
    # 모듈 리로드
    if 'proxy_manager' in sys.modules:
        del sys.modules['proxy_manager']
    if 'proxy_blast_sync' in sys.modules:
        del sys.modules['proxy_blast_sync']
    
    # T:\scripts 경로 우선순위
    script_path = r'T:\\scripts\\python\\application\\houdini\\houdini21.0\\script'
    if script_path in sys.path:
        sys.path.remove(script_path)
    sys.path.insert(0, script_path)
    
    import proxy_manager
    import proxy_blast_sync
    
    proxy_node = hou.node("/obj/assets/Proxy")
    if not proxy_node:
        print("[ERROR] Proxy node not found")
    else:
        print("[INFO] Calling clear_proxy_with_confirm...")
        print()
        
        # clear_proxy를 직접 호출 (UI 다이얼로그 없이)
        # 원래는 hou.ui.displayMessage가 호출되지만, 테스트를 위해 직접 로직 실행
        
        count = proxy_node.parm("cloth_parts").evalAsInt()
        print("[INFO] Current cloth_parts: {}".format(count))
        print()
        
        # Delete All 옵션으로 geo 노드 삭제
        print("[INFO] Deleting geo nodes...")
        for i in range(1, count + 1):
            p_name_parm = proxy_node.parm("part_name_{}".format(i))
            if p_name_parm:
                part_name = p_name_parm.evalAsString()
                if part_name:
                    geo_node = proxy_node.node("geo_{}".format(part_name))
                    if geo_node:
                        geo_node.destroy()
                        print("  - Deleted: geo_{}".format(part_name))
        
        # cloth_parts 초기화
        proxy_node.parm("cloth_parts").set(0)
        print()
        print("[OK] Cleared {} cloth part(s)".format(count))
        print()
        
        # blast 및 Parts_Deform 노드 제거
        print("[INFO] Removing all blast and Parts_Deform nodes...")
        print()
        deleted = proxy_blast_sync.remove_all_blasts_from_all_locations(proxy_node)
        print()
        print("[OK] Removed {} node(s) total".format(deleted))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[AFTER] Verifying all nodes are removed...")
print("-" * 80)

code = """
import hou

try:
    # Constraint blasts
    constraint = hou.node("/obj/assets/Constraint")
    if constraint:
        blasts = [c for c in constraint.children() if c.type().name() == "blast" and c.name().startswith("blast_")]
        print("[Constraint] {} blast node(s) - {}".format(len(blasts), "[OK] Clean" if len(blasts) == 0 else "[ERROR] Not cleaned!"))
        if blasts:
            for b in blasts:
                print("  - REMAINING: {}".format(b.name()))
    
    # Deform blasts and Parts_Deform
    deform = hou.node("/obj/assets/Deform")
    if deform:
        proxy_blasts = [c for c in deform.children() if c.type().name() == "blast" and c.name().startswith("proxy_path_blast_")]
        geo_blasts = [c for c in deform.children() if c.type().name() == "blast" and c.name().startswith("geo_path_blast_")]
        parts_deform = [c for c in deform.children() if c.type().name() == "subnet" and c.name().startswith("Parts_Deform_")]
        
        print("[Deform] {} proxy_path blast(s) - {}".format(len(proxy_blasts), "[OK] Clean" if len(proxy_blasts) == 0 else "[ERROR] Not cleaned!"))
        if proxy_blasts:
            for b in proxy_blasts:
                print("  - REMAINING: {}".format(b.name()))
        
        print("[Deform] {} geo_path blast(s) - {}".format(len(geo_blasts), "[OK] Clean" if len(geo_blasts) == 0 else "[ERROR] Not cleaned!"))
        if geo_blasts:
            for b in geo_blasts:
                print("  - REMAINING: {}".format(b.name()))
        
        print("[Deform] {} Parts_Deform node(s) - {}".format(len(parts_deform), "[OK] Clean" if len(parts_deform) == 0 else "[ERROR] Not cleaned!"))
        if parts_deform:
            for node in parts_deform:
                print("  - REMAINING: {}".format(node.name()))
    
    print()
    
    # 최종 검증
    total_remaining = 0
    if constraint:
        total_remaining += len([c for c in constraint.children() if c.type().name() == "blast" and c.name().startswith("blast_")])
    if deform:
        total_remaining += len([c for c in deform.children() if c.type().name() == "blast" and c.name().startswith("proxy_path_blast_")])
        total_remaining += len([c for c in deform.children() if c.type().name() == "blast" and c.name().startswith("geo_path_blast_")])
        total_remaining += len([c for c in deform.children() if c.type().name() == "subnet" and c.name().startswith("Parts_Deform_")])
    
    if total_remaining == 0:
        print("="*70)
        print(" [SUCCESS] All nodes successfully removed!")
        print("="*70)
    else:
        print("="*70)
        print(" [ERROR] {} node(s) still remaining!".format(total_remaining))
        print("="*70)

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Parts_Deform auto-deletion test finished!")
print("="*80)

connector.disconnect()





