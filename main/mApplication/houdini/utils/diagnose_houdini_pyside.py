#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Houdini PySide 진단 스크립트
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def diagnose_pyside():
    """PySide 상태 진단"""
    print("\n" + "="*80)
    print(" Houdini PySide Diagnostic")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Checking Qt modules availability...")
        print("-"*80)
        h.execute("""
import sys

# Check PySide2
try:
    import PySide2
    print(f"[OK] PySide2 found: {PySide2.__version__}")
    print(f"     Location: {PySide2.__file__}")
except ImportError as e:
    print(f"[ERROR] PySide2 not found: {e}")

# Check PySide6
try:
    import PySide6
    print(f"[OK] PySide6 found: {PySide6.__version__}")
    print(f"     Location: {PySide6.__file__}")
except ImportError as e:
    print(f"[ERROR] PySide6 not found: {e}")

# Check what Houdini uses
try:
    from hutil.Qt import QtCore, QtWidgets
    print(f"[OK] Houdini Qt wrapper found")
    print(f"     Qt version: {QtCore.qVersion()}")
except ImportError as e:
    print(f"[ERROR] Houdini Qt wrapper not found: {e}")
""")
        
        print("\n[2] Checking Python environment...")
        print("-"*80)
        h.execute("""
import sys
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"\\nPython path ({len(sys.path)} entries):")
for i, path in enumerate(sys.path[:10], 1):
    print(f"  {i}. {path}")
if len(sys.path) > 10:
    print(f"  ... and {len(sys.path) - 10} more")
""")
        
        print("\n[3] Checking cache_save.py file...")
        print("-"*80)
        h.execute("""
import os

cache_save_path = r"T:\\scripts\\python\\application\\houdini\\houdini20.0\\houinhouse\\handlers\\cache_save.py"

if os.path.exists(cache_save_path):
    print(f"[OK] File exists: {cache_save_path}")
    print(f"\\nFirst 20 lines:")
    print("-" * 60)
    try:
        with open(cache_save_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:20]
            for i, line in enumerate(lines, 1):
                print(f"{i:3d}| {line.rstrip()}")
    except Exception as e:
        print(f"[ERROR] Could not read file: {e}")
else:
    print(f"[ERROR] File not found: {cache_save_path}")
""")
        
        print("\n" + "="*80)
        print("[OK] Diagnostic completed!")
        print("="*80)


def suggest_fix():
    """수정 방법 제시"""
    print("\n" + "="*80)
    print(" Suggested Fixes")
    print("="*80)
    
    print("""
Option 1: Modify cache_save.py to use Houdini's Qt wrapper
------------------------------------------------------------------------
Replace:
    from PySide2 import QtWidgets, QtCore

With:
    try:
        from hutil.Qt import QtCore, QtWidgets
    except ImportError:
        try:
            from PySide6 import QtCore, QtWidgets
        except ImportError:
            from PySide2 import QtCore, QtWidgets

Option 2: Modify cache_save.py to support both PySide2 and PySide6
------------------------------------------------------------------------
Replace:
    from PySide2 import QtWidgets, QtCore

With:
    try:
        from PySide2 import QtWidgets, QtCore
    except ImportError:
        from PySide6 import QtWidgets, QtCore

Option 3: Check Houdini version compatibility
------------------------------------------------------------------------
Houdini 20.5 typically uses PySide6, not PySide2.
The script may need to be updated for your Houdini version.
""")
    print("="*80)


if __name__ == "__main__":
    try:
        diagnose_pyside()
        suggest_fix()
    except Exception as e:
        print(f"\n[ERROR] Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()






