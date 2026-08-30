#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
들여쓰기 오류 수정 스크립트
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def fix_indentation():
    """들여쓰기 오류 수정"""
    print("\n" + "="*80)
    print(" Fix Indentation Error")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Restoring from backup and fixing properly...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import os

cache_save_path = r"T:\\scripts\\python\\application\\houdini\\houdini20.0\\houinhouse\\handlers\\cache_save.py"
backup_path = cache_save_path + ".backup"

# Read backup file
if os.path.exists(backup_path):
    with open(backup_path, 'r', encoding='utf-8') as f:
        content = f.read()
    print(f"[OK] Backup file read: {len(content)} bytes")
else:
    # If no backup, read current broken file
    with open(cache_save_path, 'r', encoding='utf-8') as f:
        content = f.read()
    print(f"[WARNING] No backup found, using current file")

# Fix the import properly
lines = content.split('\\n')
new_lines = []
fixed = False

for i, line in enumerate(lines):
    # Look for the problematic PySide2 import
    if not fixed and ('from PySide2 import' in line or 'try:' in line):
        # Check if this is the import line we need to fix
        if 'from PySide2 import QtWidgets, QtCore' in line:
            # Replace with proper try-except block
            new_lines.append('try:')
            new_lines.append('    from PySide2 import QtWidgets, QtCore')
            new_lines.append('except ImportError:')
            new_lines.append('    from PySide6 import QtWidgets, QtCore')
            fixed = True
            print(f"[OK] Fixed import at line {i+1}")
            continue
        elif line.strip() == 'try:' and i+1 < len(lines):
            # Check if next line is the import
            next_line = lines[i+1] if i+1 < len(lines) else ""
            if 'from PySide2 import' in next_line or 'try:' in next_line:
                # Skip this try and fix the import
                continue
    
    # Skip malformed lines
    if fixed and i <= len(lines) and any(x in line for x in ['except ImportError:', 'from PySide6 import']):
        if 'from PySide6 import QtWidgets, QtCore' in line:
            continue  # Already added
        if line.strip() == 'except ImportError:':
            continue  # Already added
    
    new_lines.append(line)

# Write fixed content
new_content = '\\n'.join(new_lines)
with open(cache_save_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"[OK] File written: {cache_save_path}")
print(f"\\nFirst 15 lines of fixed file:")
print("-" * 60)
fixed_lines = new_content.split('\\n')[:15]
for i, line in enumerate(fixed_lines, 1):
    print(f"{i:3d}| {line}")
""", print_output=False)
        
        if result:
            print(result['stdout'])
            if result['stderr']:
                print("\n[STDERR]")
                print(result['stderr'])
        
        print("\n[2] Fixing blast_split.py as well...")
        print("-"*80)
        
        h.execute("""
import os

blast_split_path = r"T:\\scripts\\python\\application\\houdini\\houdini20.0\\houinhouse\\handlers\\blast_split.py"
backup_path = blast_split_path + ".backup"

# Read backup
if os.path.exists(backup_path):
    with open(backup_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix import
    lines = content.split('\\n')
    new_lines = []
    fixed = False
    
    for i, line in enumerate(lines):
        if not fixed and 'from PySide2 import QtWidgets, QtCore' in line:
            # Replace with proper try-except block
            indent = len(line) - len(line.lstrip())
            indent_str = ' ' * indent
            new_lines.append(f'{indent_str}try:')
            new_lines.append(f'{indent_str}    from PySide2 import QtWidgets, QtCore')
            new_lines.append(f'{indent_str}except ImportError:')
            new_lines.append(f'{indent_str}    from PySide6 import QtWidgets, QtCore')
            fixed = True
            print(f"[OK] Fixed blast_split.py at line {i+1}")
            continue
        new_lines.append(line)
    
    # Write fixed content
    new_content = '\\n'.join(new_lines)
    with open(blast_split_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"[OK] blast_split.py fixed")
else:
    print(f"[INFO] No backup for blast_split.py, skipping")
""")
        
        print("\n[3] Verifying syntax...")
        print("-"*80)
        
        h.execute("""
import os
import sys

cache_save_path = r"T:\\scripts\\python\\application\\houdini\\houdini20.0\\houinhouse\\handlers\\cache_save.py"

# Try to compile the file to check syntax
try:
    with open(cache_save_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    compile(code, cache_save_path, 'exec')
    print("[OK] Syntax check passed for cache_save.py")
except SyntaxError as e:
    print(f"[ERROR] Syntax error still present:")
    print(f"  Line {e.lineno}: {e.msg}")
    print(f"  Text: {e.text}")
except Exception as e:
    print(f"[ERROR] Could not verify: {e}")

# Test import
print("\\n[Testing import...]")
try:
    # Test the import pattern
    test_code = '''
try:
    from PySide2 import QtWidgets, QtCore
except ImportError:
    from PySide6 import QtWidgets, QtCore
print("Import successful!")
'''
    exec(test_code)
except Exception as e:
    print(f"[ERROR] Import test failed: {e}")
""")
        
        print("\n" + "="*80)
        print("[OK] Fix completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        fix_indentation()
        
        print("\n" + "="*80)
        print(" Test the cache save tool now!")
        print("="*80)
        print("""
1. Go to Houdini
2. Open cinematic2 tool shelf
3. Click 'cache save' button
4. It should work without errors now!

If errors persist, the file might need manual editing.
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Fix failed: {e}")
        import traceback
        traceback.print_exc()






