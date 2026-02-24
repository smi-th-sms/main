#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Proxy.clear_proxy callback 확인
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Checking Proxy.clear_proxy Callback")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Checking clear_proxy button callback...")
print("-" * 80)

code = """
import hou

try:
    proxy_node = hou.node("/obj/assets/Proxy")
    if not proxy_node:
        print("[ERROR] Proxy node not found")
    else:
        clear_btn = proxy_node.parm("clear_proxy")
        if not clear_btn:
            print("[ERROR] clear_proxy button not found")
        else:
            # Callback script 확인
            template = clear_btn.parmTemplate()
            script_callback = template.scriptCallback()
            script_callback_language = template.scriptCallbackLanguage()
            
            print("[INFO] clear_proxy button found")
            print()
            print("Callback Language: {}".format(script_callback_language))
            print()
            print("="*70)
            print(" Current Callback Script")
            print("="*70)
            print()
            print(script_callback)
            print()
            print("="*70)

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[2] Testing if clear_proxy removes Parts_Deform...")
print("-" * 80)

# 먼저 테스트 데이터 생성
code = """
import sys
import hou

try:
    # 모듈 리로드
    if 'proxy_blast_sync' in sys.modules:
        del sys.modules['proxy_blast_sync']
    if 'proxy_manager' in sys.modules:
        del sys.modules['proxy_manager']
    
    script_path = r'T:\\scripts\\python\\application\\houdini\\houdini21.0\\script'
    if script_path in sys.path:
        sys.path.remove(script_path)
    sys.path.insert(0, script_path)
    
    proxy_node = hou.node("/obj/assets/Proxy")
    if proxy_node:
        # 테스트 파트가 없으면 추가
        count = proxy_node.parm("cloth_parts").evalAsInt()
        if count == 0:
            proxy_node.parm("cloth_parts").set(2)
            proxy_node.parm("part_name_1").set("test_part1")
            proxy_node.parm("part_name_2").set("test_part2")
            print("[INFO] Added 2 test parts")
            
            # update_proxy 실행
            import proxy_manager
            proxy_manager.update_proxy_nodes(proxy_node)
            print("[INFO] Created blast and Parts_Deform nodes")
        else:
            print("[INFO] Using existing {} part(s)".format(count))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[3] Checking Parts_Deform nodes BEFORE clear_proxy...")
print("-" * 80)

code = """
import hou

try:
    deform = hou.node("/obj/assets/Deform")
    if deform:
        parts_deform = [c for c in deform.children() 
                       if c.type().name() == "subnet" and c.name().startswith("Parts_Deform_")]
        print("[INFO] Parts_Deform nodes: {}".format(len(parts_deform)))
        for node in parts_deform:
            print("  - {}".format(node.name()))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[4] Executing clear_proxy button...")
print("-" * 80)

code = """
import hou

try:
    proxy_node = hou.node("/obj/assets/Proxy")
    if proxy_node:
        clear_btn = proxy_node.parm("clear_proxy")
        if clear_btn:
            print("[INFO] Pressing clear_proxy button...")
            # 버튼 실행 (callback 실행됨)
            clear_btn.pressButton()
            print("[OK] Button pressed")
        else:
            print("[ERROR] clear_proxy button not found")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n[5] Checking Parts_Deform nodes AFTER clear_proxy...")
print("-" * 80)

code = """
import hou

try:
    deform = hou.node("/obj/assets/Deform")
    if deform:
        parts_deform = [c for c in deform.children() 
                       if c.type().name() == "subnet" and c.name().startswith("Parts_Deform_")]
        
        if len(parts_deform) == 0:
            print("[OK] All Parts_Deform nodes removed!")
        else:
            print("[ERROR] {} Parts_Deform node(s) still remain:".format(len(parts_deform)))
            for node in parts_deform:
                print("  - {}".format(node.name()))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Diagnosis finished")
print("="*80)

connector.disconnect()





