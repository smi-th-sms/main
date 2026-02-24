#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sys.path 우선순위 수정 및 모듈 리로드
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Fixing Module Path Priority")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[Solution] Updating old proxy_manager.py")
print("-" * 80)
print()
print("Since Houdini loads from:")
print("  d:\\Antigravity/houdini_tools\\proxy_manager.py")
print()
print("We need to either:")
print("  1. Update that file with new version")
print("  2. Or ensure sys.path prioritizes T:\\scripts")
print()
print("Recommended: Copy new version to old location")
print()
print("-" * 80)

# 파일 복사
code_copy = """
import shutil
import os

old_path = r"d:\\Antigravity\\houdini_tools\\proxy_manager.py"
new_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script\\proxy_manager.py"

if os.path.exists(new_path):
    # 백업
    if os.path.exists(old_path):
        backup_path = old_path + ".backup"
        shutil.copy2(old_path, backup_path)
        print("[BACKUP] Saved old version to: {}".format(backup_path))
    
    # 복사
    shutil.copy2(new_path, old_path)
    print("[COPIED] New version copied to: {}".format(old_path))
    print()
    print("Now the callback scripts will use the updated version!")
else:
    print("[ERROR] New file not found at: {}".format(new_path))
"""

print("Executing file copy...")
result = connector.execute_code(code_copy)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Module path fixed!")
print("="*80)

connector.disconnect()

print("\n" + "="*80)
print(" Next Steps")
print("="*80)
print()
print("1. Test update_proxy again")
print("2. Verify blast nodes are created")
print("3. Confirm integration works")
print()
print("="*80)





