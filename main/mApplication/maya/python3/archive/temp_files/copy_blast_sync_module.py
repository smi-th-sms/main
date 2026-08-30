#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
proxy_blast_sync.py 모듈도 복사
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Copying proxy_blast_sync.py Module")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Copying proxy_blast_sync.py...")
print("-" * 80)

code = """
import shutil
import os

old_dir = r"d:\\Antigravity\\houdini_tools"
new_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script\\proxy_blast_sync.py"
old_path = os.path.join(old_dir, "proxy_blast_sync.py")

if os.path.exists(new_path):
    # 디렉토리 확인
    if not os.path.exists(old_dir):
        os.makedirs(old_dir)
        print("[CREATED] Directory: {}".format(old_dir))
    
    # 복사
    shutil.copy2(new_path, old_path)
    print("[COPIED] proxy_blast_sync.py copied to: {}".format(old_path))
else:
    print("[ERROR] Source file not found at: {}".format(new_path))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Module copied!")
print("="*80)

connector.disconnect()





