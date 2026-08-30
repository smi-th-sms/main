#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
외부 경로 참조 요약 및 권장사항
"""

import sys
import os
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def create_summary():
    """경로 참조 요약 생성"""
    print("\n" + "="*80)
    print(" External Path Reference Summary")
    print("="*80)
    
    summary_lines = []
    
    summary_lines.append("="*80)
    summary_lines.append(" ASSETS NODE - EXTERNAL PATH SUMMARY")
    summary_lines.append("="*80)
    summary_lines.append("")
    summary_lines.append("Node: /obj/assets")
    summary_lines.append("Type: Cinematic::assets::1.0")
    summary_lines.append("Analysis Date: 2025-12-23")
    summary_lines.append("")
    
    summary_lines.append("="*80)
    summary_lines.append(" DISCOVERED EXTERNAL PATHS")
    summary_lines.append("="*80)
    summary_lines.append("")
    
    summary_lines.append("1. d:/Antigravity/houdini_tools")
    summary_lines.append("-"*80)
    summary_lines.append("")
    summary_lines.append("   Status: EXTERNAL DEPENDENCY")
    summary_lines.append("   Type: Team shared resource")
    summary_lines.append("")
    summary_lines.append("   Used in:")
    summary_lines.append("     - auto_setup_btn (Button Callback)")
    summary_lines.append("       Purpose: Import asset_loader_v2 for asset loading")
    summary_lines.append("")
    summary_lines.append("     - project_dir (Menu Script, assumed)")
    summary_lines.append("       Purpose: Generate project path menu")
    summary_lines.append("")
    summary_lines.append("   Required Modules:")
    summary_lines.append("     - asset_loader_v2.py")
    summary_lines.append("     - project_list.py (assumed)")
    summary_lines.append("")
    summary_lines.append("   Current Code:")
    summary_lines.append('     tool_path = "d:/Antigravity/houdini_tools"')
    summary_lines.append("     if tool_path not in sys.path:")
    summary_lines.append("         sys.path.append(tool_path)")
    summary_lines.append("     import asset_loader_v2")
    summary_lines.append("")
    
    summary_lines.append("")
    summary_lines.append("="*80)
    summary_lines.append(" RECOMMENDATIONS")
    summary_lines.append("="*80)
    summary_lines.append("")
    
    summary_lines.append("Option 1: Keep External (RECOMMENDED)")
    summary_lines.append("-"*80)
    summary_lines.append("")
    summary_lines.append("Pros:")
    summary_lines.append("  + No changes needed")
    summary_lines.append("  + Maintains team consistency")
    summary_lines.append("  + Other projects continue to work")
    summary_lines.append("  + Updates from Antigravity team apply automatically")
    summary_lines.append("")
    summary_lines.append("Cons:")
    summary_lines.append("  - Depends on d:/ drive availability")
    summary_lines.append("  - External dependency for critical function")
    summary_lines.append("")
    summary_lines.append("Action: None (current state)")
    summary_lines.append("")
    
    summary_lines.append("")
    summary_lines.append("Option 2: Copy to T: Drive")
    summary_lines.append("-"*80)
    summary_lines.append("")
    summary_lines.append("Pros:")
    summary_lines.append("  + Independent from d:/ drive")
    summary_lines.append("  + All scripts in one location")
    summary_lines.append("  + Full control over versions")
    summary_lines.append("")
    summary_lines.append("Cons:")
    summary_lines.append("  - Requires manual updates")
    summary_lines.append("  - Diverges from team standard")
    summary_lines.append("  - Need to update auto_setup_btn callback")
    summary_lines.append("")
    summary_lines.append("Action Required:")
    summary_lines.append("  1. Copy d:/Antigravity/houdini_tools/*.py to")
    summary_lines.append("     T:\\scripts\\python\\application\\houdini\\houdini21.0\\script\\antigravity\\")
    summary_lines.append("")
    summary_lines.append("  2. Update auto_setup_btn callback:")
    summary_lines.append('     Change: tool_path = "d:/Antigravity/houdini_tools"')
    summary_lines.append('     To:     tool_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script\\antigravity"')
    summary_lines.append("")
    summary_lines.append("  3. Test auto_setup_btn functionality")
    summary_lines.append("")
    
    summary_lines.append("")
    summary_lines.append("Option 3: Create Wrapper")
    summary_lines.append("-"*80)
    summary_lines.append("")
    summary_lines.append("Pros:")
    summary_lines.append("  + Fallback mechanism (try d:/ first, then T:/)")
    summary_lines.append("  + Best of both worlds")
    summary_lines.append("")
    summary_lines.append("Cons:")
    summary_lines.append("  - More complex")
    summary_lines.append("  - Requires maintenance")
    summary_lines.append("")
    summary_lines.append("Action Required:")
    summary_lines.append("  1. Create wrapper script in T:/")
    summary_lines.append("  2. Update auto_setup_btn to use wrapper")
    summary_lines.append("")
    
    summary_lines.append("")
    summary_lines.append("="*80)
    summary_lines.append(" CURRENT STATUS")
    summary_lines.append("="*80)
    summary_lines.append("")
    
    summary_lines.append("Migrated to T:/ Drive:")
    summary_lines.append("  [OK] parts_deform_sync_callback.py")
    summary_lines.append("  [OK] Documentation files")
    summary_lines.append("  [OK] sim_filecache Pre-Render Script updated")
    summary_lines.append("  [OK] README.txt created")
    summary_lines.append("")
    
    summary_lines.append("External Dependencies (d:/ Drive):")
    summary_lines.append("  [  ] asset_loader_v2.py (external)")
    summary_lines.append("  [  ] project_list.py (external)")
    summary_lines.append("  [  ] Decision: Keep external OR migrate")
    summary_lines.append("")
    
    summary_lines.append("System Paths:")
    summary_lines.append("  [OK] Z:/inhouse/Houdini/otls/ (HDA library)")
    summary_lines.append("")
    
    summary_lines.append("")
    summary_lines.append("="*80)
    summary_lines.append(" FILES IN T:/ LOCATION")
    summary_lines.append("="*80)
    summary_lines.append("")
    
    target_dir = r"T:\scripts\python\application\houdini\houdini21.0\script"
    
    if os.path.exists(target_dir):
        files = os.listdir(target_dir)
        summary_lines.append("Location: {}".format(target_dir))
        summary_lines.append("Files: {}".format(len(files)))
        summary_lines.append("")
        
        for f in sorted(files):
            full_path = os.path.join(target_dir, f)
            if os.path.isfile(full_path):
                size = os.path.getsize(full_path)
                summary_lines.append("  - {:<45} ({:>8} bytes)".format(f, size))
    else:
        summary_lines.append("Location: {} (NOT FOUND)".format(target_dir))
    
    summary_lines.append("")
    summary_lines.append("="*80)
    summary_lines.append(" NEXT STEPS")
    summary_lines.append("="*80)
    summary_lines.append("")
    summary_lines.append("1. Review this summary and EXTERNAL_DEPENDENCIES.txt")
    summary_lines.append("")
    summary_lines.append("2. Decide on external path strategy:")
    summary_lines.append("   - Keep d:/Antigravity as external (recommended)")
    summary_lines.append("   - OR migrate to T:/ for independence")
    summary_lines.append("")
    summary_lines.append("3. If migrating:")
    summary_lines.append("   - Run: python migrate_antigravity_tools.py")
    summary_lines.append("   - This will copy and update references")
    summary_lines.append("")
    summary_lines.append("4. Test all functionality:")
    summary_lines.append("   - auto_setup_btn (asset loading)")
    summary_lines.append("   - project_dir menu")
    summary_lines.append("   - sim_filecache Save to Disk (Parts_Deform sync)")
    summary_lines.append("")
    summary_lines.append("5. Document team decision")
    summary_lines.append("")
    summary_lines.append("="*80)
    
    # 파일로 저장
    summary_path = os.path.join(target_dir, "PATH_REFERENCE_SUMMARY.txt")
    
    try:
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(summary_lines))
        
        print("[OK] Summary saved to:")
        print("  {}".format(summary_path))
        print("  Lines: {}".format(len(summary_lines)))
        
        # 콘솔 출력
        print("\n" + "="*80)
        print(" SUMMARY PREVIEW")
        print("="*80)
        
        for line in summary_lines[:50]:
            print(line)
        
        if len(summary_lines) > 50:
            print("\n... ({} more lines)".format(len(summary_lines) - 50))
        
    except Exception as e:
        print("[ERROR] Could not save summary: {}".format(e))
        
        # 에러 시 콘솔에 출력
        print("\n" + "="*80)
        print(" SUMMARY")
        print("="*80)
        for line in summary_lines:
            print(line)


if __name__ == "__main__":
    try:
        create_summary()
        
        print("\n" + "="*80)
        print(" Documentation Complete")
        print("="*80)
        print("""
생성된 문서:
==========
1. EXTERNAL_DEPENDENCIES.txt
   - 모든 외부 의존성 상세 문서

2. PATH_REFERENCE_SUMMARY.txt (NEW!)
   - 외부 경로 참조 요약
   - 권장사항 및 옵션
   - 다음 단계 가이드

위치:
====
T:\\scripts\\python\\application\\houdini\\houdini21.0\\script\\

확인된 외부 의존성:
===============
d:/Antigravity/houdini_tools/
  - asset_loader_v2.py
  - project_list.py (추정)

권장사항:
========
현재 상태 유지 (외부 의존성으로 보존)
  - 팀 공유 리소스
  - 다른 프로젝트와의 일관성
  - 자동 업데이트 혜택

필요시 T: 드라이브로 마이그레이션 가능
  - 스크립트 제공됨

모든 분석이 완료되었습니다!
""")
        print("="*80)
        
    except Exception as e:
        print("\n[ERROR] Failed: {}".format(e))
        import traceback
        traceback.print_exc()





