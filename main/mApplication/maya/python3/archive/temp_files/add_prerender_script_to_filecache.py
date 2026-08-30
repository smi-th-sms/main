#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sim_filecache 노드에 Pre-Render Script 추가
save_to_disk 실행 전에 Parts_Deform 동기화
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def add_prerender_script():
    """sim_filecache에 Pre-Render Script 추가"""
    print("\n" + "="*80)
    print(" Add Pre-Render Script to sim_filecache")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Finding sim_filecache node...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou

filecache_node = hou.node("/obj/assets/Constraint/sim_filecache")

if not filecache_node:
    print("[ERROR] sim_filecache node not found")
else:
    print("[OK] Found: {}".format(filecache_node.path()))
    print("  Type: {}".format(filecache_node.type().name()))
    
    # Pre-Render Script 파라미터 찾기
    prerender_parm = filecache_node.parm("prerender")
    postrender_parm = filecache_node.parm("postrender")
    
    if prerender_parm:
        print("[OK] Found prerender parameter")
        
        # 현재 스크립트 확인
        current_script = prerender_parm.eval()
        if current_script:
            print("  Current script: {}...".format(current_script[:100]))
        else:
            print("  Current script: (empty)")
    else:
        print("[WARNING] prerender parameter not found")
        
        # 사용 가능한 script 관련 파라미터 찾기
        print("")
        print("  Available script parameters:")
        for parm in filecache_node.parms():
            if 'script' in parm.name().lower() or 'python' in parm.name().lower():
                print("    - {}".format(parm.name()))
""", print_output=False)
        
        if result and result.get('stdout'):
            try:
                print(result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[OK] Node found")
        
        print("\n[2] Adding Pre-Render Script...")
        print("-"*80)
        
        script_result = h.connector.execute_code("""
import hou

filecache_node = hou.node("/obj/assets/Constraint/sim_filecache")

if filecache_node:
    # Pre-Render Script 파라미터
    prerender_parm = filecache_node.parm("prerender")
    
    if prerender_parm:
        # 동기화 스크립트
        sync_script = '''# Parts_Deform Auto Sync
import sys
if r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3" not in sys.path:
    sys.path.append(r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3")

try:
    import parts_deform_sync_callback
    parts_deform_sync_callback.sync_parts_deform_nodes()
except Exception as e:
    print("Parts_Deform sync error: {}".format(str(e)))
'''
        
        # 기존 스크립트 백업
        old_script = prerender_parm.eval()
        if old_script:
            print("[INFO] Backing up existing prerender script...")
            hou.session.sim_filecache_prerender_backup = old_script
            print("  Backup saved to hou.session.sim_filecache_prerender_backup")
            
            # 기존 스크립트와 결합
            combined_script = old_script + "\\n\\n" + sync_script
            prerender_parm.set(combined_script)
            print("[OK] Appended sync script to existing prerender script")
        else:
            # 새로운 스크립트 설정
            prerender_parm.set(sync_script)
            print("[OK] Set new prerender script")
        
        # 확인
        final_script = prerender_parm.eval()
        print("")
        print("Final prerender script ({} chars):".format(len(final_script)))
        print("=" * 60)
        print(final_script)
        print("=" * 60)
    else:
        print("[ERROR] prerender parameter not found")
        print("Cannot add auto-sync to this node type")
else:
    print("[ERROR] sim_filecache node not found")
""", print_output=False)
        
        if script_result and script_result.get('stdout'):
            try:
                safe_output = script_result['stdout'].encode('ascii', errors='ignore').decode('ascii')
                print(safe_output)
            except:
                print("[OK] Script added")
        
        print("\n[3] Verification...")
        print("-"*80)
        
        verify_result = h.connector.execute_code("""
import hou

filecache_node = hou.node("/obj/assets/Constraint/sim_filecache")

if filecache_node:
    prerender_parm = filecache_node.parm("prerender")
    
    if prerender_parm:
        script = prerender_parm.eval()
        
        if "parts_deform_sync_callback" in script:
            print("[OK] Sync script is present in prerender")
            print("  Script length: {} characters".format(len(script)))
            print("")
            print("Now when you click 'Save to Disk' on sim_filecache:")
            print("  1. Parts_Deform nodes will automatically sync")
            print("  2. Then the cache will be saved")
        else:
            print("[WARNING] Sync script not found in prerender")
    else:
        print("[ERROR] prerender parameter not available")
""", print_output=False)
        
        if verify_result and verify_result.get('stdout'):
            try:
                print(verify_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[OK] Verification complete")
        
        print("\n" + "="*80)
        print("[OK] Pre-Render Script setup completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        add_prerender_script()
        
        print("\n" + "="*80)
        print(" Setup Complete!")
        print("="*80)
        print("""
Pre-Render Script가 sim_filecache에 추가되었습니다!

동작 방식:
=========
1. sim_filecache 노드의 'Save to Disk' 버튼 클릭
2. Pre-Render Script 자동 실행:
   - proxy_path에서 @proxy_path 어트리뷰트 분석
   - Parts_Deform_* 노드 동기화 (생성/수정/삭제)
   - 각 노드의 group 및 blast2 파라미터 업데이트
3. 캐시 저장 진행

확인 방법:
=========
1. sim_filecache 노드 선택
2. Parameters 패널에서 Scripts 탭 확인
3. Pre-Render Script에 sync 코드 확인

수동 실행:
=========
언제든지 Python Shell에서 실행 가능:
  hou.session.run_parts_deform_sync()

주의사항:
========
- 기존 Pre-Render Script가 있었다면 백업됨:
  hou.session.sim_filecache_prerender_backup
- 동기화 중 UI 메시지가 표시됨
- 작업 내역이 콘솔에 출력됨
""")
        print("="*80)
        
    except Exception as e:
        print("\n[ERROR] Setup failed: {}".format(e))
        import traceback
        traceback.print_exc()





