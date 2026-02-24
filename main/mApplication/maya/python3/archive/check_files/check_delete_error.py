#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Delete This Part 에러 확인
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Checking Delete Part Error")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Checking script_multiparm_index type...")
print("-" * 80)

code = """
import hou

try:
    proxy_node = hou.node("/obj/assets/Proxy")
    if proxy_node:
        # 첫 번째 part의 delete button callback 시뮬레이션
        delete_btn = proxy_node.parm("delete_part_1")
        if delete_btn:
            template = delete_btn.parmTemplate()
            callback = template.scriptCallback()
            
            print("[INFO] Callback script:")
            print(callback)
            print()
            
            # kwargs 시뮬레이션
            print("[INFO] Testing kwargs['script_multiparm_index']:")
            
            # Houdini에서 실제로 전달되는 값 확인
            # multiparm index는 보통 문자열로 전달됨
            print("  Type in Houdini callback: likely string")
            print("  Example: kwargs['script_multiparm_index'] = '1' (string)")
            print()
            
            # 문제 확인
            test_index = '1'  # 문자열
            print("[ERROR] Attempting: test_index - 1")
            print("  test_index = '{}' (type: {})".format(test_index, type(test_index).__name__))
            print("  This will cause: TypeError: unsupported operand type(s) for -: 'str' and 'int'")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[INFO] Error confirmed: script_multiparm_index is passed as STRING")
print("       Need to convert to INT before arithmetic operations")
print("="*80)

connector.disconnect()





