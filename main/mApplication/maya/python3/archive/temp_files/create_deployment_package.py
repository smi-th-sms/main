#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Create CFX Assets Manager deployment package
"""

import os
import shutil
from datetime import datetime

print("\n" + "="*80)
print(" Creating CFX Assets Manager Deployment Package")
print("="*80)

# Paths
source_dir = r"T:\scripts\python\application\houdini\houdini21.0\script"
deploy_base = r"T:\scripts\python\application\houdini\houdini21.0"
deploy_dir = os.path.join(deploy_base, "CFX_Assets_Manager_Deploy")
archive_dir = os.path.join(source_dir, "archive_dev_docs")

# Core runtime scripts (essential for operation)
core_scripts = [
    'cfx_assets_ui.py',
    'launch_cfx_ui.py',
    'proxy_manager.py',
    'proxy_blast_sync.py',
    'parts_deform_sync_callback.py',
    'project_dir_simple_menu.py',
]

# Important user documentation to keep
important_docs = [
    'README.txt',
    'CFX_UI_GUIDE.txt',
]

print("\n[1] Creating deployment directory structure...")
print("-" * 80)

# Create deployment directory
if os.path.exists(deploy_dir):
    print("[INFO] Removing existing deployment directory...")
    shutil.rmtree(deploy_dir)

os.makedirs(deploy_dir, exist_ok=True)
os.makedirs(os.path.join(deploy_dir, "scripts"), exist_ok=True)
os.makedirs(os.path.join(deploy_dir, "shelf"), exist_ok=True)
os.makedirs(os.path.join(deploy_dir, "docs"), exist_ok=True)

print("[OK] Created directory structure:")
print("    {}".format(deploy_dir))
print("    {}/scripts/".format(os.path.basename(deploy_dir)))
print("    {}/shelf/".format(os.path.basename(deploy_dir)))
print("    {}/docs/".format(os.path.basename(deploy_dir)))

print("\n[2] Copying core runtime scripts...")
print("-" * 80)

scripts_dest = os.path.join(deploy_dir, "scripts")
copied_count = 0

for script in core_scripts:
    src = os.path.join(source_dir, script)
    dst = os.path.join(scripts_dest, script)
    
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print("[OK] Copied: {}".format(script))
        copied_count += 1
    else:
        print("[ERROR] Not found: {}".format(script))

print("\nCopied {} of {} core scripts".format(copied_count, len(core_scripts)))

print("\n[3] Copying shelf tool...")
print("-" * 80)

shelf_src = r"C:\Users\smi_th\Documents\houdini21.0\toolbar\cinematic2_tool.shelf"
shelf_dest = os.path.join(deploy_dir, "shelf", "cinematic2_tool.shelf")

if os.path.exists(shelf_src):
    shutil.copy2(shelf_src, shelf_dest)
    print("[OK] Copied: cinematic2_tool.shelf")
else:
    print("[WARNING] Shelf file not found: {}".format(shelf_src))

print("\n[4] Creating archive for development documentation...")
print("-" * 80)

# Create archive directory if it doesn't exist
if not os.path.exists(archive_dir):
    os.makedirs(archive_dir)
    print("[OK] Created archive directory: {}".format(archive_dir))
else:
    print("[INFO] Archive directory already exists")

# Move development docs to archive
moved_count = 0
for filename in os.listdir(source_dir):
    if filename.endswith('.txt') and filename not in important_docs:
        src = os.path.join(source_dir, filename)
        dst = os.path.join(archive_dir, filename)
        
        if os.path.isfile(src):
            shutil.move(src, dst)
            moved_count += 1

print("[OK] Archived {} development documentation files".format(moved_count))
print("    Location: {}".format(archive_dir))

print("\n[5] Copying important documentation...")
print("-" * 80)

docs_dest = os.path.join(deploy_dir, "docs")

for doc in important_docs:
    src = os.path.join(source_dir, doc)
    dst = os.path.join(docs_dest, doc)
    
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print("[OK] Copied: {}".format(doc))
    else:
        print("[WARNING] Not found: {}".format(doc))

print("\n[6] Generating package information...")
print("-" * 80)

# Package info
package_info = """================================================================================
 CFX ASSETS MANAGER - Deployment Package
================================================================================

Version: 2.3
Date: {}
Package Contents:

1. SCRIPTS (6 files)
   - cfx_assets_ui.py              : Main UI window
   - launch_cfx_ui.py              : UI launcher
   - proxy_manager.py              : Proxy node management
   - proxy_blast_sync.py           : Blast synchronization
   - parts_deform_sync_callback.py : Parts Deform auto-sync
   - project_dir_simple_menu.py    : Project directory menu

2. SHELF
   - cinematic2_tool.shelf         : Houdini shelf tool definition

3. DOCUMENTATION
   - README.txt                    : General information
   - CFX_UI_GUIDE.txt             : User guide
   - INSTALLATION_GUIDE.txt       : Installation instructions

================================================================================
 PACKAGE STRUCTURE
================================================================================

CFX_Assets_Manager_Deploy/
├── scripts/                      (Copy these to target location)
│   ├── cfx_assets_ui.py
│   ├── launch_cfx_ui.py
│   ├── proxy_manager.py
│   ├── proxy_blast_sync.py
│   ├── parts_deform_sync_callback.py
│   └── project_dir_simple_menu.py
│
├── shelf/                        (Copy to Houdini toolbar folder)
│   └── cinematic2_tool.shelf
│
├── docs/                         (Reference documentation)
│   ├── README.txt
│   ├── CFX_UI_GUIDE.txt
│   └── INSTALLATION_GUIDE.txt
│
└── PACKAGE_INFO.txt             (This file)

================================================================================
 QUICK INSTALLATION
================================================================================

1. Copy scripts/ folder contents to:
   T:\\scripts\\python\\application\\houdini\\houdini21.0\\script

2. Copy shelf/cinematic2_tool.shelf to:
   C:\\Users\\[USERNAME]\\Documents\\houdini21.0\\toolbar\\

3. Restart Houdini

4. Find "CFX Assets Manager" tool in cinematic2 shelf

================================================================================
 REQUIREMENTS
================================================================================

- Houdini 21.0 or later (uses PySide6)
- Project directory structure: Z:/show/[project]/
- HDA: Cinematic::assets::1.0 (or compatible)

================================================================================
 SUPPORT
================================================================================

For issues or questions, contact the CFX team.

Package created: {}
================================================================================
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
           datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

package_info_path = os.path.join(deploy_dir, "PACKAGE_INFO.txt")
with open(package_info_path, 'w', encoding='utf-8') as f:
    f.write(package_info)

print("[OK] Created: PACKAGE_INFO.txt")

print("\n" + "="*80)
print("[COMPLETE] Deployment package created successfully!")
print("="*80)
print()
print("Package location:")
print("  {}".format(deploy_dir))
print()
print("Next steps:")
print("  1. Review PACKAGE_INFO.txt")
print("  2. Create INSTALLATION_GUIDE.txt")
print("  3. Test installation on clean machine")
print("  4. Zip/compress for distribution")
print()
print("Development docs archived to:")
print("  {}".format(archive_dir))





