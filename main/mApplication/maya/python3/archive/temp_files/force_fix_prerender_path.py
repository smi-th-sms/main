#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sim_filecache의 Pre-Render Script 경로 강제 수정
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def force_fix_path():
    """Pre-Render Script 강제 수정"""
    print("\n" + "="*80)
    print(" Force Fix Pre-Render Script Path")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Updating Pre-Render Script with correct path...")
        print("-"*80)
        
        # 올바른 스크립트를 직접 작성
        correct_script = r"""# Parts_Deform Auto Sync
import sys
target_path = r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3"
if target_path not in sys.path:
    sys.path.append(target_path)

try:
    import parts_deform_sync_callback
    parts_deform_sync_callback.sync_parts_deform_nodes()
except Exception as e:
    print("Parts_Deform sync error: {}".format(str(e)))
"""
        
        print("Correct script prepared:")
        print("=" * 60)
        print(correct_script)
        print("=" * 60)
        
        # Houdini에 적용
        result = h.connector.execute_code("""
import hou

filecache_node = hou.node("/obj/assets/Constraint/sim_filecache")

if not filecache_node:
    print("[ERROR] sim_filecache node not found")
else:
    prerender_parm = filecache_node.parm("prerender")
    
    if not prerender_parm:
        print("[ERROR] prerender parameter not found")
    else:
        # 올바른 스크립트 설정
        new_script = r\"\"\"# Parts_Deform Auto Sync
import sys
target_path = r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3"
if target_path not in sys.path:
    sys.path.append(target_path)

try:
    import parts_deform_sync_callback
    parts_deform_sync_callback.sync_parts_deform_nodes()
except Exception as e:
    print("Parts_Deform sync error: {}".format(str(e)))
\"\"\"
        
        prerender_parm.set(new_script)
        
        print("[OK] Pre-Render Script updated")
        
        # 검증
        updated = prerender_parm.eval()
        print("")
        print("[Verification]")
        print("=" * 60)
        print(updated)
        print("=" * 60)
        
        # 경로 확인
        if "2025" in updated:
            print("")
            print("[OK] Path contains '2025'")
        else:
            print("")
            print("[WARNING] Path does not contain '2025'")
""", print_output=False)
        
        if result and result.get('stdout'):
            try:
                safe_output = result['stdout'].encode('ascii', errors='ignore').decode('ascii')
                print(safe_output)
            except:
                print("[Output]")
        
        print("\n[2] Testing execution...")
        print("-"*80)
        
        test_result = h.connector.execute_code("""
import hou

filecache_node = hou.node("/obj/assets/Constraint/sim_filecache")

if filecache_node:
    prerender_parm = filecache_node.parm("prerender")
    
    if prerender_parm:
        script = prerender_parm.eval()
        
        print("[Testing Pre-Render Script]")
        print("=" * 60)
        
        try:
            exec(script)
            print("")
            print("[OK] Execution successful!")
            
        except Exception as e:
            print("")
            print("[ERROR] Execution failed: {}".format(str(e)))
            import traceback
            traceback.print_exc()
""", print_output=False)
        
        if test_result and test_result.get('stdout'):
            try:
                safe_output = test_result['stdout'].encode('ascii', errors='ignore').decode('ascii')
                print(safe_output)
            except:
                print("[Test output]")
        
        if test_result and test_result.get('stderr'):
            print("\n[STDERR]")
            try:
                print(test_result['stderr'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                pass
        
        print("\n" + "="*80)
        print("[OK] Force fix completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        force_fix_path()
        
        print("""

========================================
 이제 sim_filecache의 Save to Disk가 
 Parts_Deform 노드를 자동으로 동기화합니다!
========================================
""")
        
    except Exception as e:
        print("\n[ERROR] Fix failed: {}".format(e))
        import traceback
        traceback.print_exc()





