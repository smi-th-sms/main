#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sim_filecache의 Pre-Render Script 진단
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def diagnose_prerender_script():
    """Pre-Render Script 상태 진단"""
    print("\n" + "="*80)
    print(" Diagnose sim_filecache Pre-Render Script")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Checking sim_filecache node...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou

filecache_node = hou.node("/obj/assets/Constraint/sim_filecache")

if not filecache_node:
    print("[ERROR] sim_filecache node not found")
else:
    print("[OK] Found: {}".format(filecache_node.path()))
    print("  Type: {}".format(filecache_node.type().name()))
    print("  Definition: {}".format(filecache_node.type().definition().libraryFilePath() if filecache_node.type().definition() else "N/A"))
    
    # Pre-Render Script 파라미터 확인
    print("")
    print("[Checking Pre-Render Script parameter]")
    print("-" * 60)
    
    prerender_parm = filecache_node.parm("prerender")
    
    if prerender_parm:
        print("[OK] prerender parameter exists")
        
        script = prerender_parm.eval()
        
        if script:
            print("  Script length: {} characters".format(len(script)))
            print("")
            print("  Script content:")
            print("  " + "=" * 58)
            for i, line in enumerate(script.split('\\n'), 1):
                print("  {:3d} | {}".format(i, line))
            print("  " + "=" * 58)
            
            # 스크립트 검증
            print("")
            print("[Script Validation]")
            print("-" * 60)
            
            if "parts_deform_sync_callback" in script:
                print("  [OK] Sync callback import found")
            else:
                print("  [WARNING] Sync callback import NOT found")
            
            if "sync_parts_deform_nodes()" in script:
                print("  [OK] Sync function call found")
            else:
                print("  [WARNING] Sync function call NOT found")
            
            # 경로 확인
            if "z:\\\\inhouse\\\\Maya\\\\scripts" in script or "z:\\inhouse\\Maya\\scripts" in script:
                print("  [OK] Path reference found")
                
                # 경로가 올바른지 확인
                if "2025\\\\cosmos\\\\scripts\\\\python3" in script or "2025\\cosmos\\scripts\\python3" in script:
                    print("  [OK] Correct path: 2025/cosmos/scripts/python3")
                else:
                    print("  [WARNING] Path might be incorrect")
                    print("  Expected: z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3")
            else:
                print("  [WARNING] Path reference NOT found or incorrect")
        else:
            print("  [WARNING] Script is EMPTY")
            print("")
            print("  The Pre-Render Script has no content!")
    else:
        print("[ERROR] prerender parameter NOT found")
        
        # 다른 스크립트 파라미터들 찾기
        print("")
        print("  Available script-related parameters:")
        for parm in filecache_node.parms():
            parm_name = parm.name().lower()
            if 'script' in parm_name or 'python' in parm_name or 'pre' in parm_name or 'post' in parm_name:
                print("    - {} = {}".format(parm.name(), parm.eval()[:50] if parm.eval() else "(empty)"))
""", print_output=False)
        
        if result and result.get('stdout'):
            try:
                print(result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Output contains non-ascii characters]")
        
        print("\n[2] Testing callback availability...")
        print("-"*80)
        
        test_result = h.connector.execute_code("""
import hou
import sys
import os

print("[Testing Python environment]")
print("-" * 60)

# 경로 확인
test_path = r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3"
print("Target path: {}".format(test_path))
print("Path exists: {}".format(os.path.exists(test_path)))

if os.path.exists(test_path):
    # 파일 확인
    callback_file = os.path.join(test_path, "parts_deform_sync_callback.py")
    print("Callback file: {}".format(callback_file))
    print("File exists: {}".format(os.path.exists(callback_file)))
    
    if os.path.exists(callback_file):
        print("File size: {} bytes".format(os.path.getsize(callback_file)))
    
    # sys.path 확인
    print("")
    print("Path in sys.path: {}".format(test_path in sys.path))
    
    # 임포트 테스트
    print("")
    print("[Testing import]")
    print("-" * 60)
    
    if test_path not in sys.path:
        sys.path.append(test_path)
        print("Added to sys.path")
    
    try:
        import parts_deform_sync_callback
        print("[OK] Module imported successfully")
        
        # 함수 확인
        if hasattr(parts_deform_sync_callback, 'sync_parts_deform_nodes'):
            print("[OK] sync_parts_deform_nodes function found")
            
            # 함수 시그니처 확인
            import inspect
            sig = inspect.signature(parts_deform_sync_callback.sync_parts_deform_nodes)
            print("Function signature: {}".format(sig))
        else:
            print("[ERROR] sync_parts_deform_nodes function NOT found")
            
    except ImportError as e:
        print("[ERROR] Failed to import: {}".format(e))
    except Exception as e:
        print("[ERROR] Import error: {}".format(e))
        import traceback
        traceback.print_exc()
else:
    print("[ERROR] Path does not exist!")
""", print_output=False)
        
        if test_result and test_result.get('stdout'):
            try:
                print(test_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Output contains non-ascii characters]")
        
        print("\n[3] Testing Pre-Render Script execution...")
        print("-"*80)
        
        exec_result = h.connector.execute_code("""
import hou

filecache_node = hou.node("/obj/assets/Constraint/sim_filecache")

if filecache_node:
    prerender_parm = filecache_node.parm("prerender")
    
    if prerender_parm:
        script = prerender_parm.eval()
        
        if script:
            print("[Attempting to execute Pre-Render Script]")
            print("=" * 60)
            
            try:
                # 스크립트 실행
                exec(script)
                print("")
                print("[OK] Script executed successfully")
                
            except Exception as e:
                print("")
                print("[ERROR] Script execution failed:")
                print("  {}".format(str(e)))
                print("")
                import traceback
                traceback.print_exc()
        else:
            print("[ERROR] Pre-Render Script is empty")
    else:
        print("[ERROR] prerender parameter not found")
else:
    print("[ERROR] sim_filecache node not found")
""", print_output=False)
        
        if exec_result and exec_result.get('stdout'):
            try:
                print(exec_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Output contains non-ascii characters]")
        
        if exec_result and exec_result.get('stderr'):
            print("\n[STDERR]")
            try:
                print(exec_result['stderr'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Error output]")
        
        print("\n" + "="*80)
        print("[Diagnosis completed]")
        print("="*80)


if __name__ == "__main__":
    try:
        diagnose_prerender_script()
        
    except Exception as e:
        print("\n[ERROR] Diagnosis failed: {}".format(e))
        import traceback
        traceback.print_exc()





