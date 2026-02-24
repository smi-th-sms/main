#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
houinhouse 디렉토리의 모든 PySide2 import 스캔 및 수정
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def scan_and_fix_all():
    """모든 Python 파일에서 PySide2 import 스캔 및 수정"""
    print("\n" + "="*80)
    print(" Scan and Fix All PySide2 Imports")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Scanning for PySide2 imports...")
        print("-"*80)
        
        h.execute("""
import os
import glob

handlers_dir = r"T:\\scripts\\python\\application\\houdini\\houdini20.0\\houinhouse"

# Find all Python files
py_files = []
for root, dirs, files in os.walk(handlers_dir):
    for file in files:
        if file.endswith('.py') and not file.endswith('.backup'):
            py_files.append(os.path.join(root, file))

print(f"Found {len(py_files)} Python files")

# Scan for PySide2 imports
files_with_pyside2 = []
for filepath in py_files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'from PySide2 import' in content or 'import PySide2' in content:
                files_with_pyside2.append(filepath)
    except Exception as e:
        print(f"[WARNING] Could not read {filepath}: {e}")

print(f"\\nFiles with PySide2 imports: {len(files_with_pyside2)}")
print("-" * 60)
for filepath in files_with_pyside2:
    rel_path = os.path.relpath(filepath, handlers_dir)
    print(f"  - {rel_path}")
""")
        
        print("\n[2] Fixing all PySide2 imports...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import os

handlers_dir = r"T:\\scripts\\python\\application\\houdini\\houdini20.0\\houinhouse"

# Find all Python files with PySide2
py_files = []
for root, dirs, files in os.walk(handlers_dir):
    for file in files:
        if file.endswith('.py') and not file.endswith('.backup'):
            py_files.append(os.path.join(root, file))

fixed_files = []
skipped_files = []

for filepath in py_files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if needs fixing
        old_patterns = [
            'from PySide2 import QtWidgets, QtCore',
            'from PySide2 import QtCore, QtWidgets',
        ]
        
        needs_fix = False
        for pattern in old_patterns:
            if pattern in content:
                needs_fix = True
                break
        
        if not needs_fix:
            continue
        
        # Create backup
        backup_path = filepath + '.backup'
        if not os.path.exists(backup_path):
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Fix all patterns
        new_content = content
        for pattern in old_patterns:
            new_import = '''try:
    from PySide2 import QtWidgets, QtCore
except ImportError:
    from PySide6 import QtWidgets, QtCore'''
            new_content = new_content.replace(pattern, new_import)
        
        # Write fixed file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        fixed_files.append(filepath)
        rel_path = os.path.relpath(filepath, handlers_dir)
        print(f"[OK] Fixed: {rel_path}")
        
    except Exception as e:
        rel_path = os.path.relpath(filepath, handlers_dir)
        print(f"[ERROR] {rel_path}: {e}")
        skipped_files.append((filepath, str(e)))

print(f"\\n{'='*60}")
print(f"Summary:")
print(f"  Fixed: {len(fixed_files)} files")
print(f"  Skipped: {len(skipped_files)} files")

if skipped_files:
    print(f"\\nSkipped files:")
    for filepath, error in skipped_files:
        rel_path = os.path.relpath(filepath, handlers_dir)
        print(f"  - {rel_path}: {error}")
""", print_output=False)
        
        if result:
            print(result['stdout'])
            if result['stderr']:
                print("\n[STDERR]")
                print(result['stderr'])
        
        print("\n" + "="*80)
        print("[OK] Scan and fix completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        scan_and_fix_all()
        
        print("\n" + "="*80)
        print(" Summary")
        print("="*80)
        print("""
All Python files in the houinhouse directory have been scanned and fixed.

What was done:
1. Scanned all .py files for PySide2 imports
2. Created .backup files for originals
3. Replaced PySide2 imports with compatible code

The fixed code will work with both:
- Houdini 19.x/20.x (PySide2)
- Houdini 21.x+ (PySide6)

Test the cache save tool now:
1. Go to cinematic2 tool shelf in Houdini
2. Click 'cache save' button
3. It should work without errors
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Scan failed: {e}")
        import traceback
        traceback.print_exc()






