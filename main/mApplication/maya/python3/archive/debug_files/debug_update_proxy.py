#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
update_proxy_nodes 디버깅
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Debugging update_proxy_nodes")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Checking proxy_manager.py current state...")
print("-" * 80)

# proxy_manager.py 파일 내용 확인
code = """
import sys

script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
if script_path not in sys.path:
    sys.path.append(script_path)

# 파일 직접 읽기
file_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script\\proxy_manager.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 라인 333-356 확인 (update_proxy_nodes 끝 부분)
print("[Lines 330-360 of proxy_manager.py]")
print("="*70)

for i in range(329, min(360, len(lines))):
    line_num = i + 1
    line = lines[i].rstrip()
    print("{:3d}: {}".format(line_num, line))

print("="*70)
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Check completed!")
print("="*80)

connector.disconnect()





