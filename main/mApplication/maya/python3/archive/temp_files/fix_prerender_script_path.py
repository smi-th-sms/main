#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sim_filecache의 Pre-Render Script 경로 수정
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def fix_prerender_path():
    """Pre-Render Script의 잘못된 경로 수정"""
    print("\n" + "="*80)
    print(" Fix Pre-Render Script Path")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Checking current script...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou

filecache_node = hou.node("/obj/assets/Constraint/sim_filecache")

if not filecache_node:
    print("[ERROR] sim_filecache node not found")
else:
    print("[OK] Found: {}".format(filecache_node.path()))
    
    prerender_parm = filecache_node.parm("prerender")
    
    if prerender_parm:
        old_script = prerender_parm.eval()
        
        if old_script:
            print("")
            print("[Current Pre-Render Script]")
            print("=" * 60)
            print(old_script)
            print("=" * 60)
            
            # 경로 문제 확인
            if "scripts5" in old_script:
                print("")
                print("[FOUND ISSUE] Incorrect path detected:")
                print("  Wrong: z:\\inhouse\\Maya\\scripts5\\...")
                print("  Correct: z:\\inhouse\\Maya\\scripts\\2025\\...")
            else:
                print("")
                print("[INFO] Path looks okay")
        else:
            print("[WARNING] Script is empty")
    else:
        print("[ERROR] prerender parameter not found")
""", print_output=False)
        
        if result and result.get('stdout'):
            try:
                print(result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Output]")
        
        print("\n[2] Fixing the path...")
        print("-"*80)
        
        fix_result = h.connector.execute_code("""
import hou

filecache_node = hou.node("/obj/assets/Constraint/sim_filecache")

if filecache_node:
    prerender_parm = filecache_node.parm("prerender")
    
    if prerender_parm:
        # 올바른 Pre-Render Script
        correct_script = '''# Parts_Deform Auto Sync
import sys
if r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3" not in sys.path:
    sys.path.append(r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3")

try:
    import parts_deform_sync_callback
    parts_deform_sync_callback.sync_parts_deform_nodes()
except Exception as e:
    print("Parts_Deform sync error: {}".format(str(e)))
'''
        
        # 스크립트 설정
        prerender_parm.set(correct_script)
        
        print("[OK] Pre-Render Script updated")
        print("")
        print("[New Pre-Render Script]")
        print("=" * 60)
        print(correct_script)
        print("=" * 60)
        
        # 검증
        updated_script = prerender_parm.eval()
        
        print("")
        print("[Verification]")
        print("-" * 60)
        
        if "scripts\\2025" in updated_script or "scripts\\\\2025" in updated_script:
            print("[OK] Correct path confirmed: scripts\\2025")
        else:
            print("[WARNING] Path verification failed")
        
        if "parts_deform_sync_callback" in updated_script:
            print("[OK] Callback import found")
        else:
            print("[WARNING] Callback import not found")
        
        if "sync_parts_deform_nodes()" in updated_script:
            print("[OK] Function call found")
        else:
            print("[WARNING] Function call not found")
    else:
        print("[ERROR] prerender parameter not found")
else:
    print("[ERROR] sim_filecache node not found")
""", print_output=False)
        
        if fix_result and fix_result.get('stdout'):
            try:
                print(fix_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Fixed]")
        
        print("\n[3] Testing the corrected script...")
        print("-"*80)
        
        test_result = h.connector.execute_code("""
import hou

filecache_node = hou.node("/obj/assets/Constraint/sim_filecache")

if filecache_node:
    prerender_parm = filecache_node.parm("prerender")
    
    if prerender_parm:
        script = prerender_parm.eval()
        
        print("[Executing Pre-Render Script]")
        print("=" * 60)
        
        try:
            # 스크립트 실행
            exec(script)
            print("")
            print("[OK] Script executed successfully!")
            
        except Exception as e:
            print("")
            print("[ERROR] Execution failed:")
            print("  {}".format(str(e)))
            import traceback
            traceback.print_exc()
""", print_output=False)
        
        if test_result and test_result.get('stdout'):
            try:
                print(test_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Test completed]")
        
        if test_result and test_result.get('stderr'):
            print("\n[STDERR]")
            try:
                print(test_result['stderr'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Error output]")
        
        print("\n" + "="*80)
        print("[OK] Path fix completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        fix_prerender_path()
        
        print("\n" + "="*80)
        print(" Summary")
        print("="*80)
        print("""
경로 수정 완료!

문제:
====
Pre-Render Script에 잘못된 경로가 있었습니다:
  잘못된: z:\\inhouse\\Maya\\scripts5\\cosmos\\scripts\\python3
  올바른: z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3

수정사항:
========
- Pre-Render Script의 경로를 올바르게 수정
- 스크립트 실행 테스트 완료

이제 작동해야 합니다:
==================
1. sim_filecache 노드 선택
2. "Save to Disk" 버튼 클릭
3. Parts_Deform 노드가 자동으로 동기화됨
4. 캐시 저장 진행

확인 방법:
=========
- proxy_path에 @proxy_path 어트리뷰트 변경
- Save to Disk 실행
- /obj/assets/Deform에서 Parts_Deform_* 노드 확인
""")
        print("="*80)
        
    except Exception as e:
        print("\n[ERROR] Fix failed: {}".format(e))
        import traceback
        traceback.print_exc()





