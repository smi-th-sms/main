#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
문서와 스크립트를 새 경로로 이동
대상: T:\scripts\python\application\houdini\houdini21.0\script
"""

import sys
import os
import shutil
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def move_to_new_location():
    """파일 이동 및 경로 업데이트"""
    print("\n" + "="*80)
    print(" Moving Files to New Location")
    print("="*80)
    
    # 경로 정의
    source_dir = r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3"
    target_dir = r"T:\scripts\python\application\houdini\houdini21.0\script"
    
    print("\nSource: {}".format(source_dir))
    print("Target: {}".format(target_dir))
    print("")
    
    # 이동할 파일 목록
    files_to_move = [
        # 문서 파일
        "ASSETS_SCRIPTS_DOCUMENTATION.txt",
        "ASSETS_COMPLETE_SUMMARY.txt",
        "project_dir_menu_script.py",
        
        # 핵심 스크립트
        "parts_deform_sync_callback.py",
        
        # 유틸리티 스크립트 (선택적)
        "houdini_mcp_connector.py",
        "connect_to_houdini.py",
    ]
    
    print("[1] Checking target directory...")
    print("-"*80)
    
    if not os.path.exists(target_dir):
        print("[INFO] Target directory does not exist")
        print("Creating: {}".format(target_dir))
        try:
            os.makedirs(target_dir)
            print("[OK] Directory created")
        except Exception as e:
            print("[ERROR] Could not create directory: {}".format(e))
            return
    else:
        print("[OK] Target directory exists")
    
    print("\n[2] Copying files...")
    print("-"*80)
    
    copied_files = []
    failed_files = []
    
    for filename in files_to_move:
        source_path = os.path.join(source_dir, filename)
        target_path = os.path.join(target_dir, filename)
        
        if not os.path.exists(source_path):
            print("[SKIP] {} (not found)".format(filename))
            continue
        
        try:
            shutil.copy2(source_path, target_path)
            file_size = os.path.getsize(target_path)
            print("[OK] {} ({} bytes)".format(filename, file_size))
            copied_files.append(filename)
        except Exception as e:
            print("[ERROR] {} - {}".format(filename, e))
            failed_files.append(filename)
    
    print("\n[3] Summary...")
    print("-"*80)
    print("Copied: {} files".format(len(copied_files)))
    print("Failed: {} files".format(len(failed_files)))
    print("")
    
    if copied_files:
        print("Successfully copied:")
        for f in copied_files:
            print("  - {}".format(f))
    
    if failed_files:
        print("")
        print("Failed to copy:")
        for f in failed_files:
            print("  - {}".format(f))
    
    # README 파일 생성
    print("\n[4] Creating README file...")
    print("-"*80)
    
    readme_content = """================================================================================
 COSMOS HOUDINI SCRIPTS - README
================================================================================

Location: T:\\scripts\\python\\application\\houdini\\houdini21.0\\script
Date: 2025-12-23

================================================================================
 FILES IN THIS DIRECTORY
================================================================================

DOCUMENTATION:
-------------
1. ASSETS_SCRIPTS_DOCUMENTATION.txt
   - Complete code listing of all scripts in /obj/assets node
   - Includes button callbacks and menu scripts
   - Line-by-line code documentation

2. ASSETS_COMPLETE_SUMMARY.txt
   - Comprehensive overview of all scripts
   - Workflow descriptions
   - Dependencies and external references
   - Maintenance guide

3. project_dir_menu_script.py
   - Extracted menu script from project_dir parameter
   - Used for dynamic project path selection

CORE SCRIPTS:
------------
1. parts_deform_sync_callback.py
   - Parts_Deform node auto-synchronization
   - Called by sim_filecache Pre-Render Script
   - Syncs Parts_Deform_* nodes with @proxy_path attribute

UTILITY SCRIPTS:
---------------
1. houdini_mcp_connector.py (optional)
   - Houdini MCP client library
   - For remote control and automation

2. connect_to_houdini.py (optional)
   - Simple wrapper for MCP connection
   - Used by maintenance scripts

================================================================================
 USAGE
================================================================================

Parts_Deform Auto-Sync:
----------------------
This is automatically triggered when you click "Save to Disk" on:
  /obj/assets/Constraint/sim_filecache

The Pre-Render Script should reference:
  r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"

To manually execute:
  import sys
  sys.path.append(r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script")
  import parts_deform_sync_callback
  parts_deform_sync_callback.sync_parts_deform_nodes()

================================================================================
 DEPENDENCIES
================================================================================

External Modules:
  - None (parts_deform_sync_callback.py is standalone)

Required Houdini Nodes:
  - /obj/assets/Deform/proxy_path (with @proxy_path attribute)
  - /obj/assets/Deform/Parts_Deform (template node)
  - /obj/assets/Constraint/sim_filecache

Required Attributes:
  - @proxy_path (primitive, string) on proxy_path geometry
  - @geo_path (set automatically by script)

================================================================================
 MAINTENANCE
================================================================================

Updating parts_deform_sync_callback.py:
  1. Edit T:\\scripts\\python\\application\\houdini\\houdini21.0\\script\\parts_deform_sync_callback.py
  2. In Houdini, reload the module:
     import importlib
     import parts_deform_sync_callback
     importlib.reload(parts_deform_sync_callback)
  3. Test by running sim_filecache Save to Disk

Updating HDA Scripts:
  1. Open HDA in Type Properties
  2. Edit parameter callbacks
  3. Save and lock HDA
  4. Test in clean scene

================================================================================
 CONTACT
================================================================================

For issues or questions, refer to:
  - ASSETS_COMPLETE_SUMMARY.txt (workflow guide)
  - ASSETS_SCRIPTS_DOCUMENTATION.txt (detailed code)

Script Repository:
  - Original: z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3
  - Production: T:\\scripts\\python\\application\\houdini\\houdini21.0\\script

================================================================================
"""
    
    readme_path = os.path.join(target_dir, "README.txt")
    try:
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print("[OK] README.txt created")
    except Exception as e:
        print("[ERROR] Could not create README: {}".format(e))
    
    print("\n[5] Updating Houdini references...")
    print("-"*80)
    
    with connect_houdini() as h:
        result = h.connector.execute_code("""
import hou

# sim_filecache Pre-Render Script 업데이트
filecache = hou.node("/obj/assets/Constraint/sim_filecache")

if filecache:
    prerender_parm = filecache.parm("prerender")
    
    if prerender_parm:
        # 새 경로로 Pre-Render Script 업데이트
        new_script = '''# Parts_Deform Auto Sync
import sys
target_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
if target_path not in sys.path:
    sys.path.append(target_path)

try:
    import parts_deform_sync_callback
    parts_deform_sync_callback.sync_parts_deform_nodes()
except Exception as e:
    print("Parts_Deform sync error: {}".format(str(e)))
'''
        
        prerender_parm.set(new_script)
        
        print("[OK] sim_filecache Pre-Render Script updated")
        print("")
        print("New path: T:\\\\scripts\\\\python\\\\application\\\\houdini\\\\houdini21.0\\\\script")
        print("")
        print("Script content:")
        print("=" * 70)
        print(new_script)
        print("=" * 70)
    else:
        print("[ERROR] prerender parameter not found")
else:
    print("[ERROR] sim_filecache node not found")
""", print_output=False)
        
        if result and result.get('stdout'):
            try:
                print(result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Updated]")
        
        print("\n[6] Testing new path...")
        print("-"*80)
        
        test_result = h.connector.execute_code("""
import hou
import sys
import os

target_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"

print("[Testing new path]")
print("=" * 70)
print("Path: {}".format(target_path))
print("Exists: {}".format(os.path.exists(target_path)))
print("")

if os.path.exists(target_path):
    # 파일 목록
    files = os.listdir(target_path)
    print("Files in directory: {}".format(len(files)))
    print("")
    
    for f in sorted(files):
        full_path = os.path.join(target_path, f)
        if os.path.isfile(full_path):
            size = os.path.getsize(full_path)
            print("  - {} ({} bytes)".format(f, size))
    
    print("")
    print("[Testing module import]")
    print("-" * 70)
    
    if target_path not in sys.path:
        sys.path.append(target_path)
    
    try:
        import parts_deform_sync_callback
        print("[OK] parts_deform_sync_callback imported successfully")
        
        if hasattr(parts_deform_sync_callback, 'sync_parts_deform_nodes'):
            print("[OK] sync_parts_deform_nodes function found")
        else:
            print("[ERROR] sync_parts_deform_nodes function not found")
            
    except ImportError as e:
        print("[ERROR] Import failed: {}".format(e))
    except Exception as e:
        print("[ERROR] {}".format(e))
else:
    print("[ERROR] Path does not exist")
""", print_output=False)
        
        if test_result and test_result.get('stdout'):
            try:
                print(test_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Test complete]")
    
    print("\n" + "="*80)
    print("[OK] Move operation completed!")
    print("="*80)


if __name__ == "__main__":
    try:
        move_to_new_location()
        
        print("\n" + "="*80)
        print(" Migration Summary")
        print("="*80)
        print("""
파일 이동 완료!

새 위치:
=======
T:\\scripts\\python\\application\\houdini\\houdini21.0\\script\\

이동된 파일:
==========
- ASSETS_SCRIPTS_DOCUMENTATION.txt (문서)
- ASSETS_COMPLETE_SUMMARY.txt (요약)
- project_dir_menu_script.py (메뉴 스크립트)
- parts_deform_sync_callback.py (핵심 스크립트)
- houdini_mcp_connector.py (선택)
- connect_to_houdini.py (선택)
- README.txt (신규 생성)

업데이트된 참조:
=============
- sim_filecache Pre-Render Script
  → 새 경로로 변경됨

확인 사항:
=========
1. T:\\scripts\\python\\application\\houdini\\houdini21.0\\script\\ 디렉토리 확인
2. 모든 파일이 복사되었는지 확인
3. Houdini에서 sim_filecache Save to Disk 테스트
4. Parts_Deform 노드 자동 생성 확인

다음 단계:
=========
- 기존 경로(z:\\inhouse\\Maya\\...)는 백업으로 보관
- 새 경로를 팀원들과 공유
- README.txt 파일 참조
""")
        print("="*80)
        
    except Exception as e:
        print("\n[ERROR] Migration failed: {}".format(e))
        import traceback
        traceback.print_exc()





