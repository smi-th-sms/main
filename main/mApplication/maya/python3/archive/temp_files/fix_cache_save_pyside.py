#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cache_save.py PySide 호환성 자동 수정 스크립트
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def fix_cache_save_pyside():
    """cache_save.py 파일의 PySide import 수정"""
    print("\n" + "="*80)
    print(" Fix cache_save.py PySide Import")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Reading cache_save.py...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou
import os

cache_save_path = r"T:\\scripts\\python\\application\\houdini\\houdini20.0\\houinhouse\\handlers\\cache_save.py"

# Read original file
with open(cache_save_path, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"File size: {len(content)} bytes")
print(f"Original import line:")
print("  Line 2: from PySide2 import QtWidgets, QtCore")

# Create backup
backup_path = cache_save_path + ".backup"
with open(backup_path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"\\n[OK] Backup created: {backup_path}")

# Fix the import
old_import = "from PySide2 import QtWidgets, QtCore"
new_import = '''try:
    from PySide2 import QtWidgets, QtCore
except ImportError:
    from PySide6 import QtWidgets, QtCore'''

if old_import in content:
    new_content = content.replace(old_import, new_import)
    
    # Write fixed file
    with open(cache_save_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"\\n[OK] File updated successfully!")
    print(f"\\nNew import code:")
    print("  Line 2-5:")
    print("    try:")
    print("        from PySide2 import QtWidgets, QtCore")
    print("    except ImportError:")
    print("        from PySide6 import QtWidgets, QtCore")
else:
    print(f"\\n[WARNING] Original import line not found. File may already be modified.")
""", print_output=False)
        
        if result:
            print(result['stdout'])
            if result['stderr']:
                print("\n[STDERR]")
                print(result['stderr'])
        
        print("\n[2] Verifying the fix...")
        print("-"*80)
        
        h.execute("""
cache_save_path = r"T:\\scripts\\python\\application\\houdini\\houdini20.0\\houinhouse\\handlers\\cache_save.py"

print("First 10 lines of modified file:")
print("-" * 60)
with open(cache_save_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()[:10]
    for i, line in enumerate(lines, 1):
        print(f"{i:3d}| {line.rstrip()}")
""")
        
        print("\n[3] Testing the import...")
        print("-"*80)
        
        h.execute("""
import sys
import os

# Add the handlers directory to path
handlers_dir = r"T:\\scripts\\python\\application\\houdini\\houdini20.0\\houinhouse\\handlers"
if handlers_dir not in sys.path:
    sys.path.insert(0, handlers_dir)

try:
    # Try importing
    import cache_save
    print("[OK] cache_save module imported successfully!")
    print(f"     Module: {cache_save}")
    print(f"     File: {cache_save.__file__}")
except Exception as e:
    print(f"[ERROR] Failed to import cache_save: {e}")
    import traceback
    traceback.print_exc()
""")
        
        print("\n" + "="*80)
        print("[OK] Fix completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        fix_cache_save_pyside()
        
        print("\n" + "="*80)
        print(" Next Steps")
        print("="*80)
        print("""
1. Test the cache save tool in Houdini:
   - Go to cinematic2 tool shelf
   - Click 'cache save' button
   - It should now work without errors

2. If you encounter any issues:
   - The original file was backed up to:
     T:\\scripts\\python\\application\\houdini\\houdini20.0\\houinhouse\\handlers\\cache_save.py.backup
   - You can restore it if needed

3. Consider updating all similar scripts in the houinhouse directory
   to use the same PySide2/PySide6 compatibility pattern.
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Fix failed: {e}")
        import traceback
        traceback.print_exc()






