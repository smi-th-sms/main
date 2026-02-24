#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verify CFX Assets Manager deployment package
"""

import os
import sys

print("\n" + "="*80)
print(" Verifying CFX Assets Manager Deployment Package")
print("="*80)

deploy_dir = r"T:\scripts\python\application\houdini\houdini21.0\CFX_Assets_Manager_Deploy"

# Expected files
expected_structure = {
    'scripts': [
        'cfx_assets_ui.py',
        'launch_cfx_ui.py',
        'proxy_manager.py',
        'proxy_blast_sync.py',
        'parts_deform_sync_callback.py',
        'project_dir_simple_menu.py',
    ],
    'shelf': [
        'cinematic2_tool.shelf',
    ],
    'docs': [
        'README.txt',
        'INSTALLATION_GUIDE.txt',
        'USER_GUIDE.txt',
        'CFX_UI_GUIDE.txt',
    ],
    'root': [
        'PACKAGE_INFO.txt',
    ]
}

print("\n[1] Checking package structure...")
print("-" * 80)

if not os.path.exists(deploy_dir):
    print("[ERROR] Deployment directory not found!")
    print("       Expected: {}".format(deploy_dir))
    sys.exit(1)

print("[OK] Deployment directory exists")
print("    {}".format(deploy_dir))

# Check subdirectories
subdirs = ['scripts', 'shelf', 'docs']
missing_dirs = []

for subdir in subdirs:
    path = os.path.join(deploy_dir, subdir)
    if os.path.exists(path):
        print("[OK] {}/".format(subdir))
    else:
        print("[ERROR] Missing: {}/".format(subdir))
        missing_dirs.append(subdir)

if missing_dirs:
    print("\n[ERROR] Missing directories: {}".format(', '.join(missing_dirs)))
    sys.exit(1)

print("\n[2] Verifying core scripts...")
print("-" * 80)

scripts_dir = os.path.join(deploy_dir, 'scripts')
missing_scripts = []
script_sizes = {}

for script in expected_structure['scripts']:
    script_path = os.path.join(scripts_dir, script)
    if os.path.exists(script_path):
        size = os.path.getsize(script_path)
        script_sizes[script] = size
        size_kb = size / 1024
        print("[OK] {} ({:.1f} KB)".format(script, size_kb))
    else:
        print("[ERROR] Missing: {}".format(script))
        missing_scripts.append(script)

if missing_scripts:
    print("\n[ERROR] Missing scripts: {}".format(', '.join(missing_scripts)))
else:
    print("\n[OK] All {} core scripts present".format(len(expected_structure['scripts'])))

# Check for main UI
if 'cfx_assets_ui.py' in script_sizes:
    ui_size = script_sizes['cfx_assets_ui.py']
    if ui_size < 10000:  # Less than 10KB is suspicious
        print("[WARNING] cfx_assets_ui.py seems too small ({} bytes)".format(ui_size))
    else:
        print("[OK] cfx_assets_ui.py size looks reasonable")

print("\n[3] Verifying shelf file...")
print("-" * 80)

shelf_dir = os.path.join(deploy_dir, 'shelf')
shelf_file = os.path.join(shelf_dir, 'cinematic2_tool.shelf')

if os.path.exists(shelf_file):
    size = os.path.getsize(shelf_file)
    print("[OK] cinematic2_tool.shelf ({:.1f} KB)".format(size / 1024))
    
    # Check if shelf contains CFX tool
    with open(shelf_file, 'r', encoding='utf-8') as f:
        content = f.read()
        if 'cfx_assets_manager' in content.lower():
            print("[OK] Shelf contains CFX Assets Manager tool")
        else:
            print("[WARNING] CFX Assets Manager tool not found in shelf")
else:
    print("[ERROR] Shelf file not found")

print("\n[4] Verifying documentation...")
print("-" * 80)

docs_dir = os.path.join(deploy_dir, 'docs')
missing_docs = []

for doc in expected_structure['docs']:
    doc_path = os.path.join(docs_dir, doc)
    if os.path.exists(doc_path):
        size = os.path.getsize(doc_path)
        lines = 0
        with open(doc_path, 'r', encoding='utf-8') as f:
            lines = len(f.readlines())
        print("[OK] {} ({} lines, {:.1f} KB)".format(doc, lines, size / 1024))
    else:
        print("[ERROR] Missing: {}".format(doc))
        missing_docs.append(doc)

if missing_docs:
    print("\n[WARNING] Missing documentation: {}".format(', '.join(missing_docs)))
else:
    print("\n[OK] All {} documentation files present".format(len(expected_structure['docs'])))

print("\n[5] Verifying package info...")
print("-" * 80)

package_info = os.path.join(deploy_dir, 'PACKAGE_INFO.txt')
if os.path.exists(package_info):
    print("[OK] PACKAGE_INFO.txt exists")
    with open(package_info, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
        print("    {}".format(first_line))
else:
    print("[WARNING] PACKAGE_INFO.txt not found")

print("\n[6] Script syntax check...")
print("-" * 80)

syntax_errors = []
for script in expected_structure['scripts']:
    script_path = os.path.join(scripts_dir, script)
    if os.path.exists(script_path):
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                code = f.read()
            compile(code, script, 'exec')
            print("[OK] {} - No syntax errors".format(script))
        except SyntaxError as e:
            print("[ERROR] {} - Syntax error: {}".format(script, str(e)))
            syntax_errors.append(script)
        except Exception as e:
            print("[WARNING] {} - Could not verify: {}".format(script, str(e)))

if syntax_errors:
    print("\n[ERROR] Scripts with syntax errors: {}".format(', '.join(syntax_errors)))
else:
    print("\n[OK] All scripts pass syntax check")

print("\n[7] Checking archive of development docs...")
print("-" * 80)

source_dir = r"T:\scripts\python\application\houdini\houdini21.0\script"
archive_dir = os.path.join(source_dir, "archive_dev_docs")

if os.path.exists(archive_dir):
    archived_files = [f for f in os.listdir(archive_dir) if f.endswith('.txt')]
    print("[OK] Archive exists with {} files".format(len(archived_files)))
    print("    Location: {}".format(archive_dir))
else:
    print("[INFO] No archive directory (may not have been created)")

print("\n[8] Summary...")
print("-" * 80)

total_files = (
    len(expected_structure['scripts']) +
    len(expected_structure['shelf']) +
    len(expected_structure['docs']) +
    len(expected_structure['root'])
)

actual_files = 0
for subdir, files in expected_structure.items():
    if subdir == 'root':
        base_path = deploy_dir
    else:
        base_path = os.path.join(deploy_dir, subdir)
    
    for file in files:
        if os.path.exists(os.path.join(base_path, file)):
            actual_files += 1

print("\nPackage Completeness: {}/{}".format(actual_files, total_files))
print("\nCore Components:")
print("  Scripts:       {}/{}".format(
    len(expected_structure['scripts']) - len(missing_scripts),
    len(expected_structure['scripts'])
))
print("  Shelf:         1/1" if os.path.exists(shelf_file) else "  Shelf:         0/1")
print("  Documentation: {}/{}".format(
    len(expected_structure['docs']) - len(missing_docs),
    len(expected_structure['docs'])
))

print("\n" + "="*80)

if actual_files == total_files and not syntax_errors:
    print(" [SUCCESS] Deployment package is READY!")
    print("="*80)
    print("\nPackage location:")
    print("  {}".format(deploy_dir))
    print("\nNext steps:")
    print("  1. Review documentation in docs/ folder")
    print("  2. Test installation on a clean machine")
    print("  3. Zip/compress for distribution:")
    print("     - Create: CFX_Assets_Manager_v2.3.zip")
    print("     - Include entire CFX_Assets_Manager_Deploy folder")
    print("  4. Distribute to team")
else:
    print(" [WARNING] Package has issues - review errors above")
    print("="*80)
    print("\nIssues found:")
    if missing_scripts:
        print("  - Missing scripts: {}".format(len(missing_scripts)))
    if missing_docs:
        print("  - Missing docs: {}".format(len(missing_docs)))
    if syntax_errors:
        print("  - Syntax errors: {}".format(len(syntax_errors)))

print()





