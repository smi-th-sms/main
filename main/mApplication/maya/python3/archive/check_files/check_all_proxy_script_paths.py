#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Proxy 노드의 모든 스크립트 경로 확인
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Checking All Proxy Script Paths")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Checking all callback scripts...")
print("-" * 80)

# 모든 콜백 스크립트 확인
code = """
import hou

try:
    proxy_node = hou.node("/obj/assets/Proxy")
    if not proxy_node:
        print("[ERROR] Proxy node not found")
    else:
        print("[OK] Found Proxy node\\n")
        
        # 모든 파라미터의 콜백 확인
        ptg = proxy_node.parmTemplateGroup()
        
        def check_all_callbacks(templates, indent=0):
            results = []
            for template in templates:
                # Folder/FolderSet 재귀 처리
                if template.type() in [hou.parmTemplateType.Folder, hou.parmTemplateType.FolderSet]:
                    results.extend(check_all_callbacks(template.parmTemplates(), indent + 2))
                
                # Callback 확인
                try:
                    callback = template.scriptCallback()
                    if callback and callback.strip():
                        results.append({
                            'name': template.name(),
                            'label': template.label(),
                            'callback': callback
                        })
                except:
                    pass
            return results
        
        all_callbacks = check_all_callbacks(ptg.entries())
        
        print("="*70)
        print(" All Callbacks in Proxy Node")
        print("="*70)
        print()
        
        target_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
        old_path = "d:/Antigravity/houdini_tools"
        
        for i, cb in enumerate(all_callbacks, 1):
            print("{}. Parameter: {}".format(i, cb['name']))
            print("   Label: {}".format(cb['label']))
            print("   Script:")
            print("   " + "-"*66)
            
            # 스크립트 분석
            script_lines = cb['callback'].split('\\n')
            has_target = False
            has_old = False
            
            for line in script_lines:
                line_clean = line.strip()
                if line_clean:
                    print("   {}".format(line))
                    
                    # 경로 체크
                    if target_path.replace('\\\\\\\\', '\\\\') in line or target_path in line:
                        has_target = True
                    if old_path in line or old_path.replace('/', '\\\\') in line:
                        has_old = True
            
            print("   " + "-"*66)
            
            # 상태 표시
            if has_target and not has_old:
                print("   [OK] Uses target path: T:\\\\scripts")
            elif has_old:
                print("   [WARNING] Uses old path: d:/Antigravity")
            else:
                print("   [INFO] No external path reference")
            
            print()
        
        # 요약
        print("="*70)
        print(" Summary")
        print("="*70)
        print()
        print("Total callbacks: {}".format(len(all_callbacks)))
        
        target_count = sum(1 for cb in all_callbacks if target_path.replace('\\\\\\\\', '\\\\') in cb['callback'] or target_path in cb['callback'])
        old_count = sum(1 for cb in all_callbacks if old_path in cb['callback'])
        
        print("Using target path (T:\\\\scripts): {}".format(target_count))
        print("Using old path (d:/Antigravity): {}".format(old_count))
        print()
        
        if old_count > 0:
            print("[ACTION NEEDED] {} callback(s) still use old path".format(old_count))
        elif target_count == len(all_callbacks):
            print("[OK] All callbacks use target path")
        else:
            print("[INFO] Some callbacks have no external path")
        
        # sys.path 확인
        print()
        print("="*70)
        print(" Current sys.path Priority")
        print("="*70)
        print()
        
        import sys
        relevant_paths = []
        for i, path in enumerate(sys.path):
            path_lower = path.lower()
            if 'antigravity' in path_lower or 'houdini21.0' in path_lower or 'script' in path_lower:
                relevant_paths.append((i, path))
        
        if relevant_paths:
            print("Relevant paths in sys.path:")
            for idx, path in relevant_paths:
                print("  [{}] {}".format(idx, path))
        
        print()
        
        # 실제 로드된 모듈 확인
        print("="*70)
        print(" Currently Loaded Modules")
        print("="*70)
        print()
        
        if 'proxy_manager' in sys.modules:
            pm = sys.modules['proxy_manager']
            print("proxy_manager: {}".format(pm.__file__))
        else:
            print("proxy_manager: Not loaded")
        
        if 'proxy_blast_sync' in sys.modules:
            pbs = sys.modules['proxy_blast_sync']
            print("proxy_blast_sync: {}".format(pbs.__file__))
        else:
            print("proxy_blast_sync: Not loaded")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Check completed!")
print("="*80)

connector.disconnect()





