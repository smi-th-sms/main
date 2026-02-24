#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
proxy_manager 모듈의 실제 경로 확인
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Checking proxy_manager Module Location")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Checking module location and function...")
print("-" * 80)

code = """
import sys
import importlib

script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
if script_path not in sys.path:
    sys.path.append(script_path)

# 모듈 리로드
if 'proxy_manager' in sys.modules:
    del sys.modules['proxy_manager']

import proxy_manager

print("[Module Information]")
print("="*70)
print("Module file: {}".format(proxy_manager.__file__))
print()

# update_proxy_nodes 함수 소스 확인
import inspect

print("[update_proxy_nodes Function Source - Last 30 Lines]")
print("="*70)

source = inspect.getsource(proxy_manager.update_proxy_nodes)
lines = source.split('\\n')

print("Total lines: {}".format(len(lines)))
print()

# 마지막 30줄 출력
start = max(0, len(lines) - 30)
for i, line in enumerate(lines[start:], start=start+1):
    print("{:3d}: {}".format(i, line))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Check completed!")
print("="*80)

connector.disconnect()





