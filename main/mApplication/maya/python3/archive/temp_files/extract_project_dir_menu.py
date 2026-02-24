#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
project_dir Menu Script 추출 및 전체 스크립트 요약
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def extract_and_summarize():
    """project_dir Menu Script 추출 및 요약"""
    print("\n" + "="*80)
    print(" Extract project_dir Menu Script & Create Summary")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Extracting project_dir Menu Script...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou

assets_node = hou.node("/obj/assets")

if assets_node:
    parm = assets_node.parm("project_dir")
    
    if parm:
        parm_template = parm.parmTemplate()
        
        print("[project_dir Parameter]")
        print("=" * 70)
        print("Name: {}".format(parm.name()))
        print("Label: {}".format(parm_template.label()))
        print("Type: {}".format(parm_template.type()))
        print("")
        
        # Menu Script
        if hasattr(parm_template, 'menuScriptLanguage'):
            menu_lang = parm_template.menuScriptLanguage()
            if menu_lang == hou.scriptLanguage.Python:
                if hasattr(parm_template, 'menuScript'):
                    menu_script = parm_template.menuScript()
                    if menu_script:
                        print("[MENU SCRIPT]")
                        print("  Language: Python")
                        print("  Purpose: Dynamic project path menu generation")
                        print("")
                        print("  Code:")
                        print("  " + "-" * 66)
                        
                        lines = menu_script.split('\\n')
                        for i, line in enumerate(lines, 1):
                            print("  {:3d} | {}".format(i, line))
                        
                        print("  " + "-" * 66)
                        print("")
                        print("  Total lines: {}".format(len(lines)))
                        
                        # 세션에 저장
                        hou.session.project_dir_menu_script = menu_script
                    else:
                        print("[INFO] No menu script")
            else:
                print("[INFO] Menu language: {}".format(menu_lang))
        else:
            print("[INFO] No menu script language attribute")
    else:
        print("[ERROR] project_dir parameter not found")
else:
    print("[ERROR] assets node not found")
""", print_output=False)
        
        if result and result.get('stdout'):
            try:
                print(result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Script extracted]")
        
        print("\n[2] Creating comprehensive summary...")
        print("-"*80)
        
        summary_result = h.connector.execute_code("""
import hou

assets_node = hou.node("/obj/assets")

if assets_node:
    summary = []
    summary.append("=" * 80)
    summary.append(" ASSETS NODE - COMPLETE SCRIPT SUMMARY")
    summary.append("=" * 80)
    summary.append("")
    summary.append("Node: /obj/assets")
    summary.append("Type: Cinematic::assets::1.0")
    summary.append("HDA: Z:/inhouse/Houdini/otls/object_Cinematic.assets.1.0.hda")
    summary.append("")
    summary.append("=" * 80)
    summary.append(" IDENTIFIED SCRIPTS")
    summary.append("=" * 80)
    summary.append("")
    
    # 1. project_dir Menu Script
    summary.append("-" * 80)
    summary.append("1. project_dir (Menu Script)")
    summary.append("-" * 80)
    summary.append("")
    summary.append("Purpose:")
    summary.append("  - Dynamically generate project path menu")
    summary.append("  - Reference external tool path: d:/Antigravity/houdini_tools")
    summary.append("  - Load project list from external source")
    summary.append("")
    summary.append("Dependencies:")
    summary.append("  - External module: project_list (from houdini_tools)")
    summary.append("  - System path: d:/Antigravity/houdini_tools")
    summary.append("")
    summary.append("Usage:")
    summary.append("  - Provides list of available projects for selection")
    summary.append("  - Used as base path for all file operations")
    summary.append("")
    
    # 2. auto_setup_btn
    summary.append("-" * 80)
    summary.append("2. auto_setup_btn (Button Callback)")
    summary.append("-" * 80)
    summary.append("")
    summary.append("Purpose:")
    summary.append("  - Automated asset loading and setup")
    summary.append("  - FBX file processing")
    summary.append("  - Proxy geometry splitting")
    summary.append("")
    summary.append("Key Functions:")
    summary.append("  1) Standard Asset Load:")
    summary.append("     - Imports asset_loader_v2 module")
    summary.append("     - Calls load_assets(node)")
    summary.append("")
    summary.append("  2) FBX Setup:")
    summary.append("     - Extracts asset name from FBX filename")
    summary.append("     - Updates root/pelvis bone names")
    summary.append("     - Cooks FBX output nodes")
    summary.append("")
    summary.append("  3) Proxy Split:")
    summary.append("     - Reads @proxy_path attribute")
    summary.append("     - Creates blast nodes for each unique path")
    summary.append("     - Removes old blast nodes")
    summary.append("     - Filters geometry by proxy_path value")
    summary.append("")
    summary.append("Dependencies:")
    summary.append("  - asset_loader_v2 module")
    summary.append("  - d:/Antigravity/houdini_tools path")
    summary.append("  - FBX/output2 node")
    summary.append("  - Constraint/proxy_path node")
    summary.append("  - @proxy_path primitive attribute")
    summary.append("")
    summary.append("Related Workflow:")
    summary.append("  - This is the OLD workflow for proxy splitting")
    summary.append("  - NEW workflow: Parts_Deform auto-sync (via sim_filecache)")
    summary.append("")
    
    # 3. check_create_dir
    summary.append("-" * 80)
    summary.append("3. check_create_dir (Button Callback)")
    summary.append("-" * 80)
    summary.append("")
    summary.append("Purpose:")
    summary.append("  - Validate and create directory structure")
    summary.append("  - Construct full path from parameters")
    summary.append("")
    summary.append("Path Construction:")
    summary.append("  Project/SeqSub/SeqName/ShotName/ShotSub")
    summary.append("  Example: Z:/projects/sequences/SEQ01/SHOT_0010/SIM/wip/houdini")
    summary.append("")
    summary.append("Required Parameters:")
    summary.append("  - project_dir: Project root path")
    summary.append("  - seq_subdir: Sequence subdirectory (default: sequences/)")
    summary.append("  - seq_name: Sequence name")
    summary.append("  - shot_name: Shot name")
    summary.append("  - shot_subdir: Shot subdirectory (default: SIM/wip/houdini)")
    summary.append("")
    summary.append("Behavior:")
    summary.append("  - If path exists: Display message")
    summary.append("  - If path missing: Prompt to create")
    summary.append("")
    
    # 4. NEW: Parts_Deform Auto-Sync
    summary.append("-" * 80)
    summary.append("4. Parts_Deform Auto-Sync (NEW - sim_filecache Pre-Render)")
    summary.append("-" * 80)
    summary.append("")
    summary.append("Purpose:")
    summary.append("  - Automatically sync Parts_Deform nodes with @proxy_path")
    summary.append("  - Triggered before cache save")
    summary.append("")
    summary.append("Location:")
    summary.append("  /obj/assets/Constraint/sim_filecache")
    summary.append("  Pre-Render Script parameter")
    summary.append("")
    summary.append("Functionality:")
    summary.append("  1) Read @proxy_path attribute from proxy_path node")
    summary.append("  2) Compare with existing Parts_Deform_* nodes")
    summary.append("  3) Create missing nodes")
    summary.append("  4) Update existing nodes")
    summary.append("  5) Delete obsolete nodes")
    summary.append("  6) Set group parameters (@proxy_path)")
    summary.append("  7) Set blast2 parameters (@geo_path)")
    summary.append("")
    summary.append("Script Location:")
    summary.append("  z:\\\\inhouse\\\\Maya\\\\scripts\\\\2025\\\\cosmos\\\\scripts\\\\python3\\\\parts_deform_sync_callback.py")
    summary.append("")
    summary.append("Advantages over auto_setup_btn:")
    summary.append("  - Automatic execution (no manual button press)")
    summary.append("  - Incremental updates (not full recreation)")
    summary.append("  - Safe handling of missing attributes")
    summary.append("  - Integrated with cache workflow")
    summary.append("")
    
    summary.append("=" * 80)
    summary.append(" EXTERNAL DEPENDENCIES")
    summary.append("=" * 80)
    summary.append("")
    summary.append("Python Modules:")
    summary.append("  1. asset_loader_v2")
    summary.append("     Path: d:/Antigravity/houdini_tools")
    summary.append("     Used by: auto_setup_btn")
    summary.append("")
    summary.append("  2. project_list (assumed)")
    summary.append("     Path: d:/Antigravity/houdini_tools")
    summary.append("     Used by: project_dir menu script")
    summary.append("")
    summary.append("  3. parts_deform_sync_callback")
    summary.append("     Path: z:\\\\inhouse\\\\Maya\\\\scripts\\\\2025\\\\cosmos\\\\scripts\\\\python3")
    summary.append("     Used by: sim_filecache Pre-Render Script")
    summary.append("")
    summary.append("Required Nodes:")
    summary.append("  - /obj/assets/FBX (or /obj/assets/fbx_anim)")
    summary.append("  - /obj/assets/FBX/output2")
    summary.append("  - /obj/assets/Constraint")
    summary.append("  - /obj/assets/Constraint/proxy_path")
    summary.append("  - /obj/assets/Constraint/sim_filecache")
    summary.append("  - /obj/assets/Deform/Parts_Deform (template)")
    summary.append("")
    summary.append("Required Attributes:")
    summary.append("  - @proxy_path (primitive, string)")
    summary.append("  - @geo_path (primitive, string)")
    summary.append("  - name (point, string) - on FBX skeleton")
    summary.append("")
    
    summary.append("=" * 80)
    summary.append(" RECOMMENDED WORKFLOW")
    summary.append("=" * 80)
    summary.append("")
    summary.append("1. Initial Setup:")
    summary.append("   - Set project_dir from menu")
    summary.append("   - Set sequence and shot names")
    summary.append("   - Click 'Check/Create Dir' to create directory structure")
    summary.append("")
    summary.append("2. Asset Loading:")
    summary.append("   Option A (Automatic):")
    summary.append("     - Click 'Auto Setup (Load & Split)' button")
    summary.append("     - This runs asset_loader_v2 and creates blast nodes")
    summary.append("")
    summary.append("   Option B (Manual):")
    summary.append("     - Set FBX file paths manually")
    summary.append("     - Verify proxy_path node has @proxy_path attribute")
    summary.append("")
    summary.append("3. Parts_Deform Sync (NEW METHOD):")
    summary.append("   - Go to /obj/assets/Constraint/sim_filecache")
    summary.append("   - Click 'Save to Disk'")
    summary.append("   - Pre-Render Script automatically syncs Parts_Deform nodes")
    summary.append("   - Cache is saved")
    summary.append("")
    summary.append("4. Simulation:")
    summary.append("   - Each Parts_Deform_* node processes specific geometry")
    summary.append("   - blast2 filters by @geo_path")
    summary.append("   - Results are cached per-part")
    summary.append("")
    
    summary.append("=" * 80)
    summary.append(" SCRIPT MAINTENANCE")
    summary.append("=" * 80)
    summary.append("")
    summary.append("Key Files:")
    summary.append("  1. HDA Definition:")
    summary.append("     Z:/inhouse/Houdini/otls/object_Cinematic.assets.1.0.hda")
    summary.append("     - Contains all parameter definitions")
    summary.append("     - Contains button callback scripts")
    summary.append("")
    summary.append("  2. Python Callbacks:")
    summary.append("     z:\\\\inhouse\\\\Maya\\\\scripts\\\\2025\\\\cosmos\\\\scripts\\\\python3\\\\")
    summary.append("     - parts_deform_sync_callback.py (Parts_Deform sync)")
    summary.append("")
    summary.append("  3. External Tools:")
    summary.append("     d:/Antigravity/houdini_tools/")
    summary.append("     - asset_loader_v2.py (asset loading)")
    summary.append("     - project_list.py (project menu, assumed)")
    summary.append("")
    summary.append("Update Checklist:")
    summary.append("  - When modifying HDA:")
    summary.append("    1) Unlock HDA definition")
    summary.append("    2) Edit parameter callbacks")
    summary.append("    3) Save and lock HDA")
    summary.append("    4) Test in new scene")
    summary.append("")
    summary.append("  - When modifying Python callbacks:")
    summary.append("    1) Edit .py file")
    summary.append("    2) Reload module in Houdini (importlib.reload)")
    summary.append("    3) Test functionality")
    summary.append("")
    summary.append("=" * 80)
    
    summary_text = '\\n'.join(summary)
    
    # 세션에 저장
    hou.session.complete_summary = summary_text
    
    print("[OK] Summary created")
    print("Total lines: {}".format(len(summary)))
""", print_output=False)
        
        if summary_result and summary_result.get('stdout'):
            try:
                print(summary_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Summary created]")
        
        print("\n[3] Saving comprehensive summary...")
        print("-"*80)
        
        save_result = h.connector.execute_code("""
import hou

if hasattr(hou.session, 'complete_summary'):
    summary = hou.session.complete_summary
    
    try:
        summary_path = r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3\\ASSETS_COMPLETE_SUMMARY.txt"
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        print("[OK] Summary saved to:")
        print("  {}".format(summary_path))
        print("  Size: {} bytes".format(len(summary)))
        
    except Exception as e:
        print("[ERROR] Could not save: {}".format(e))
""", print_output=False)
        
        if save_result and save_result.get('stdout'):
            try:
                print(save_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Saved]")
        
        # project_dir 메뉴 스크립트도 별도 파일로 저장
        print("\n[4] Saving project_dir menu script...")
        print("-"*80)
        
        menu_save_result = h.connector.execute_code("""
import hou

if hasattr(hou.session, 'project_dir_menu_script'):
    script = hou.session.project_dir_menu_script
    
    try:
        script_path = r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3\\project_dir_menu_script.py"
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write("# project_dir Menu Script\\n")
            f.write("# From: /obj/assets parameter\\n")
            f.write("# Purpose: Dynamic project path menu generation\\n\\n")
            f.write(script)
        
        print("[OK] Menu script saved to:")
        print("  {}".format(script_path))
        
    except Exception as e:
        print("[ERROR] Could not save: {}".format(e))
""", print_output=False)
        
        if menu_save_result and menu_save_result.get('stdout'):
            try:
                print(menu_save_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Saved]")
        
        print("\n" + "="*80)
        print("[OK] All documentation completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        extract_and_summarize()
        
        print("\n" + "="*80)
        print(" Documentation Files Created")
        print("="*80)
        print("""
생성된 문서:
===========
1. ASSETS_SCRIPTS_DOCUMENTATION.txt
   - 모든 파라미터 스크립트 상세 코드

2. ASSETS_COMPLETE_SUMMARY.txt (NEW!)
   - 전체 스크립트 요약 및 분석
   - 워크플로우 설명
   - 의존성 정리
   - 유지보수 가이드

3. project_dir_menu_script.py (NEW!)
   - project_dir 메뉴 스크립트 단독 추출

주요 내용:
=========
- assets 노드의 3개 주요 스크립트 분석
- Parts_Deform 자동 동기화 워크플로우
- 외부 의존성 (asset_loader_v2 등)
- 권장 워크플로우
- 유지보수 체크리스트
""")
        print("="*80)
        
    except Exception as e:
        print("\n[ERROR] Failed: {}".format(e))
        import traceback
        traceback.print_exc()





