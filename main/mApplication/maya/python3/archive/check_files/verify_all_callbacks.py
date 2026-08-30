#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
모든 Proxy 콜백이 올바르게 업데이트되었는지 검증
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Verifying All Proxy Callbacks")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Verifying all callback scripts...")
print("-" * 80)

# 모든 콜백 검증
code = """
import hou

try:
    proxy_node = hou.node("/obj/assets/Proxy")
    if not proxy_node:
        print("[ERROR] Proxy node not found")
    else:
        print("[OK] Found Proxy node\\n")
        
        # 검증할 파라미터 목록
        check_params = [
            'update_proxy',
            'clear_proxy',
            'export_proxy_cache',
            'part_name_#',
            'delete_part_#'
        ]
        
        ptg = proxy_node.parmTemplateGroup()
        
        print("="*70)
        print(" Callback Verification Results")
        print("="*70)
        print()
        
        all_ok = True
        results = []
        
        # 재귀적으로 템플릿 검사
        def check_all_templates(templates):
            found = []
            for template in templates:
                if template.type() in [hou.parmTemplateType.Folder, hou.parmTemplateType.FolderSet]:
                    found.extend(check_all_templates(template.parmTemplates()))
                
                if template.name() in check_params:
                    try:
                        callback = template.scriptCallback()
                        found.append((template.name(), template.label(), callback))
                    except:
                        pass
            return found
        
        all_templates = check_all_templates(ptg.entries())
        
        for parm_name, parm_label, callback in all_templates:
            status = "FAIL"
            issue = ""
            
            # 새 경로 확인
            if 'T:\\\\\\\\scripts\\\\\\\\python' in callback or 'T:\\\\scripts\\\\python' in callback:
                # 구 경로가 없는지 확인
                if 'd:/Antigravity' in callback or 'd:\\\\Antigravity' in callback:
                    status = "MIXED"
                    issue = "Contains both old and new paths"
                else:
                    status = "OK"
            elif 'd:/Antigravity' in callback or 'd:\\\\Antigravity' in callback:
                status = "OLD"
                issue = "Still uses d:/Antigravity path"
            else:
                status = "UNKNOWN"
                issue = "No recognized path found"
            
            results.append({
                'name': parm_name,
                'label': parm_label,
                'status': status,
                'issue': issue
            })
            
            if status != "OK":
                all_ok = False
        
        # 결과 출력
        for i, result in enumerate(results, 1):
            status_marker = "[OK]" if result['status'] == "OK" else "[{}]".format(result['status'])
            print("{}. {:20s} {:30s} {}".format(
                i, 
                result['name'], 
                result['label'], 
                status_marker
            ))
            if result['issue']:
                print("   Issue: {}".format(result['issue']))
        
        # 요약
        print()
        print("="*70)
        print(" Verification Summary")
        print("="*70)
        print()
        print("Total callbacks checked: {}".format(len(results)))
        print()
        
        ok_count = sum(1 for r in results if r['status'] == 'OK')
        old_count = sum(1 for r in results if r['status'] == 'OLD')
        mixed_count = sum(1 for r in results if r['status'] == 'MIXED')
        unknown_count = sum(1 for r in results if r['status'] == 'UNKNOWN')
        
        print("Status breakdown:")
        print("  OK:      {} (using new path)".format(ok_count))
        if old_count > 0:
            print("  OLD:     {} (still using old path)".format(old_count))
        if mixed_count > 0:
            print("  MIXED:   {} (contains both paths)".format(mixed_count))
        if unknown_count > 0:
            print("  UNKNOWN: {} (no recognized path)".format(unknown_count))
        
        print()
        
        if all_ok:
            print("[SUCCESS] All callbacks are correctly updated!")
            print()
            print("New path in use:")
            print("  T:\\\\scripts\\\\python\\\\application\\\\houdini\\\\houdini21.0\\\\script")
        else:
            print("[WARNING] Some callbacks need attention")
            print()
            print("Please review the issues above.")
        
        # 추가 정보: proxy_manager 모듈 임포트 테스트
        print()
        print("="*70)
        print(" Module Import Test")
        print("="*70)
        print()
        
        try:
            import sys
            script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
            if script_path not in sys.path:
                sys.path.append(script_path)
            
            import proxy_manager
            
            # 함수 확인
            required_functions = [
                'get_source_groups',
                'get_part_groups',
                'update_proxy_nodes',
                'delete_part_with_confirm',
                'clear_proxy_with_confirm',
                'export_proxy_cache'
            ]
            
            missing = []
            for func_name in required_functions:
                if not hasattr(proxy_manager, func_name):
                    missing.append(func_name)
            
            if missing:
                print("[WARNING] Missing functions in proxy_manager:")
                for func in missing:
                    print("  - {}".format(func))
            else:
                print("[OK] proxy_manager module imported successfully")
                print("[OK] All {} required functions available".format(len(required_functions)))
        
        except ImportError as e:
            print("[ERROR] Failed to import proxy_manager")
            print("Error: {}".format(str(e)))

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Verification completed!")
print("="*80)

connector.disconnect()





