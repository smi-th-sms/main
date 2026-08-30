#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Delete This Part 버튼 callback 확인
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Checking 'Delete This Part' Button Callback")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Checking delete_part_# callback...")
print("-" * 80)

code = """
import hou

try:
    proxy_node = hou.node("/obj/assets/Proxy")
    if not proxy_node:
        print("[ERROR] Proxy node not found")
    else:
        # 첫 번째 part의 delete button 확인
        delete_btn = proxy_node.parm("delete_part_1")
        if not delete_btn:
            print("[ERROR] delete_part_1 button not found")
            print("[INFO] Checking available parameters...")
            
            # cloth_parts 관련 파라미터 찾기
            all_parms = proxy_node.parms()
            delete_parms = [p for p in all_parms if 'delete' in p.name().lower()]
            
            print("\\nParameters with 'delete' in name:")
            for p in delete_parms[:5]:  # 처음 5개만
                print("  - {}".format(p.name()))
        else:
            # Callback script 확인
            template = delete_btn.parmTemplate()
            script_callback = template.scriptCallback()
            script_callback_language = template.scriptCallbackLanguage()
            
            print("[INFO] delete_part_1 button found")
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

print("\n[2] Checking multiparm structure...")
print("-" * 80)

code = """
import hou

try:
    proxy_node = hou.node("/obj/assets/Proxy")
    if proxy_node:
        cloth_parts_parm = proxy_node.parm("cloth_parts")
        if cloth_parts_parm:
            count = cloth_parts_parm.evalAsInt()
            print("[INFO] cloth_parts count: {}".format(count))
            print()
            
            if count > 0:
                print("Checking first part parameters:")
                for i in range(1, min(count + 1, 3)):  # 처음 2개만
                    print()
                    print("Part {}:".format(i))
                    
                    # part_name
                    part_name_parm = proxy_node.parm("part_name_{}".format(i))
                    if part_name_parm:
                        print("  part_name_{}: {}".format(i, part_name_parm.evalAsString()))
                    
                    # delete button 찾기
                    possible_names = [
                        "delete_part_{}".format(i),
                        "delete_{}".format(i),
                        "remove_part_{}".format(i),
                    ]
                    
                    for pname in possible_names:
                        parm = proxy_node.parm(pname)
                        if parm:
                            print("  DELETE BUTTON: {}".format(pname))
                            template = parm.parmTemplate()
                            callback = template.scriptCallback()
                            if callback:
                                print("  Has callback: YES")
                            else:
                                print("  Has callback: NO")
                            break
                    else:
                        print("  DELETE BUTTON: Not found")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[COMPLETE] Check finished")
print("="*80)

connector.disconnect()





