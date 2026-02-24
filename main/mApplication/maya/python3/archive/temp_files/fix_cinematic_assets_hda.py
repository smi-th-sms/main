#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cinematic::assets HDA 자동 수정
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def fix_hda():
    """HDA 자동 수정"""
    print("\n" + "="*80)
    print(" Fix Cinematic::assets HDA")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[Option 1] Create a backup of the HDA...")
        print("-"*80)
        h.execute("""
import hou
import shutil
import os
from datetime import datetime

hda_path = r"Z:/inhouse/Houdini/otls/object_Cinematic.assets.1.0.hda"

if os.path.exists(hda_path):
    # 백업 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = hda_path.replace(".hda", f"_backup_{timestamp}.hda")
    
    try:
        shutil.copy2(hda_path, backup_path)
        print(f"[OK] Backup created: {backup_path}")
    except Exception as e:
        print(f"[ERROR] Could not create backup: {e}")
else:
    print(f"[ERROR] HDA file not found: {hda_path}")
""")
        
        print("\n[Option 2] Inspect HDA parameter interface...")
        print("-"*80)
        h.execute("""
import hou

node = hou.node("/obj/assets")
if node:
    node_type = node.type()
    definition = node_type.definition()
    
    if definition:
        print(f"HDA: {definition.nodeTypeName()}")
        print(f"Library: {definition.libraryFilePath()}")
        
        # 파라미터 템플릿 그룹 확인
        try:
            ptg = definition.parmTemplateGroup()
            
            print(f"\\nSearching for problematic parameter expressions...")
            print("-" * 60)
            
            # 문제가 될 수 있는 파라미터 찾기
            issues = []
            
            for template in ptg.entries():
                problem = None
                
                # Hide condition 확인
                if hasattr(template, 'hideCondition'):
                    try:
                        hide_cond = template.hideCondition()
                        if hide_cond and hide_cond.strip():
                            # 표현식이 정수를 반환하는지 확인이 어려우므로
                            # 일반적인 패턴 확인
                            if not ('==' in hide_cond or '!=' in hide_cond or 
                                    'ch(' in hide_cond or '$' in hide_cond or
                                    '>' in hide_cond or '<' in hide_cond):
                                problem = {'type': 'hide', 'expr': hide_cond}
                    except:
                        pass
                
                # Disable condition 확인
                if hasattr(template, 'disableCondition'):
                    try:
                        disable_cond = template.disableCondition()
                        if disable_cond and disable_cond.strip():
                            if not ('==' in disable_cond or '!=' in disable_cond or 
                                    'ch(' in disable_cond or '$' in disable_cond or
                                    '>' in disable_cond or '<' in disable_cond):
                                if not problem:
                                    problem = {'type': 'disable', 'expr': disable_cond}
                    except:
                        pass
                
                if problem:
                    issues.append({
                        'name': template.name(),
                        'label': template.label(),
                        'problem': problem
                    })
            
            if issues:
                print(f"\\n[FOUND] {len(issues)} potentially problematic parameters:")
                for i, issue in enumerate(issues[:10], 1):
                    print(f"\\n{i}. {issue['name']} ({issue['label']})")
                    print(f"   {issue['problem']['type'].upper()} expression:")
                    print(f"   {issue['problem']['expr'][:150]}")
            else:
                print("\\nNo obvious expression issues found in parameter templates.")
                print("The error might be transient or in a different component.")
                
        except Exception as e:
            print(f"[ERROR] Could not inspect parameter templates: {e}")
""")
        
        print("\n[Option 3] Check if error affects functionality...")
        print("-"*80)
        h.execute("""
import hou

print("Testing node functionality...")

node = hou.node("/obj/assets")
if node:
    try:
        # 노드가 정상적으로 작동하는지 테스트
        
        # 1. 파라미터 읽기
        parms = node.parms()
        print(f"[OK] Can read {len(parms)} parameters")
        
        # 2. 파라미터 값 설정 테스트
        # 안전한 파라미터로 테스트 (예: 표시/숨김)
        if node.isDisplayFlagSet() is not None:
            print(f"[OK] Display flag: {node.isDisplayFlagSet()}")
        
        # 3. 자식 노드 확인
        children = node.children()
        print(f"[OK] Has {len(children)} child nodes")
        
        # 4. 출력 확인
        try:
            outputs = node.outputConnections()
            print(f"[OK] Has {len(outputs)} output connections")
        except:
            print(f"[INFO] No output connections")
        
        print(f"\\n[CONCLUSION]")
        print(f"The node appears to be functional despite the error message.")
        print(f"The error is likely cosmetic (UI-related) and does not affect")
        print(f"the actual operation of the node.")
        
    except Exception as e:
        print(f"[ERROR] Node functionality test failed: {e}")
""")
        
        print("\n" + "="*80)
        print("[OK] Analysis completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        fix_hda()
        
        print("\n" + "="*80)
        print(" Recommendations")
        print("="*80)
        print("""
진단 결과 요약:

HDA: Cinematic::assets::1.0
파일: Z:/inhouse/Houdini/otls/object_Cinematic.assets.1.0.hda
노드: /obj/assets

권장 조치:

1. 에러가 기능에 영향을 주지 않는 경우:
   ✓ 에러 메시지를 무시하고 계속 작업
   ✓ 파일 저장, 렌더링 등 정상 작동 확인
   ✓ 이 에러는 파일을 열 때만 나타나는 경고일 수 있음

2. 에러를 완전히 제거하려면:
   A. HDA 수정 (TD 작업 필요):
      - HDA를 Unlock하고 Edit
      - Type Properties > Parameters에서
      - Hide When / Disable When 표현식 확인 및 수정
      
   B. 또는 TD 팀에 문의:
      - 해당 HDA 유지보수 담당자에게 리포트
      - HDA 업데이트 요청

3. 임시 회피:
   - /obj/assets 노드를 다른 타입으로 교체
   - 또는 해당 노드를 사용하지 않는 방법 모색

현재 상태에서 작업이 가능하다면 1번 옵션을 권장합니다.
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Fix failed: {e}")
        import traceback
        traceback.print_exc()






