#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
part_name_# 및 delete_part_# 파라미터의 콜백 스크립트 찾기
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Finding part_name_# and delete_part_# Callbacks")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Searching for all parameter callbacks...")
print("-" * 80)

# 모든 파라미터 콜백 검사
code = """
import hou

try:
    proxy_node = hou.node("/obj/assets/Proxy")
    if not proxy_node:
        print("[ERROR] Proxy node not found")
    else:
        print("[OK] Found Proxy node")
        
        print("\\n" + "="*70)
        print(" All Parameter Callbacks")
        print("="*70)
        
        ptg = proxy_node.parmTemplateGroup()
        
        # 모든 파라미터 템플릿을 재귀적으로 검사
        def check_templates(templates, indent=0):
            callbacks_found = []
            
            for parm_template in templates:
                parm_name = parm_template.name()
                parm_label = parm_template.label()
                parm_type = parm_template.type()
                
                # Folder나 FolderSet인 경우 하위 템플릿 체크
                if parm_type == hou.parmTemplateType.Folder:
                    callbacks_found.extend(check_templates(parm_template.parmTemplates(), indent + 2))
                elif parm_type == hou.parmTemplateType.FolderSet:
                    callbacks_found.extend(check_templates(parm_template.parmTemplates(), indent + 2))
                
                # Callback 확인
                callback_script = ""
                script_language = ""
                
                try:
                    if hasattr(parm_template, 'scriptCallbackLanguage'):
                        script_language = str(parm_template.scriptCallbackLanguage())
                    
                    if hasattr(parm_template, 'scriptCallback'):
                        callback_script = parm_template.scriptCallback()
                except:
                    pass
                
                if callback_script:
                    callbacks_found.append({
                        'name': parm_name,
                        'label': parm_label,
                        'type': str(parm_type),
                        'language': script_language,
                        'callback': callback_script,
                        'indent': indent
                    })
            
            return callbacks_found
        
        all_callbacks = check_templates(ptg.entries())
        
        if all_callbacks:
            print("\\nFound {} parameter(s) with callbacks:\\n".format(len(all_callbacks)))
            
            part_callbacks = []
            delete_callbacks = []
            other_callbacks = []
            
            for parm_info in all_callbacks:
                if 'part_name' in parm_info['name']:
                    part_callbacks.append(parm_info)
                elif 'delete_part' in parm_info['name']:
                    delete_callbacks.append(parm_info)
                else:
                    other_callbacks.append(parm_info)
            
            # part_name 콜백들
            if part_callbacks:
                print("="*70)
                print(" part_name_# Callbacks ({})".format(len(part_callbacks)))
                print("="*70)
                
                for parm_info in part_callbacks:
                    print("\\nParameter: {}".format(parm_info['name']))
                    print("Label: {}".format(parm_info['label']))
                    print("Language: {}".format(parm_info['language']))
                    print("Callback Script:")
                    print("-"*70)
                    print(parm_info['callback'])
                    print("-"*70)
                    
                    # 경로 체크
                    if 'd:/Antigravity' in parm_info['callback'] or 'd:\\\\Antigravity' in parm_info['callback']:
                        print("[WARNING] Uses old path: d:/Antigravity/houdini_tools")
                    elif 'T:\\\\\\\\scripts' in parm_info['callback'] or 'T:\\\\scripts' in parm_info['callback']:
                        print("[OK] Uses new path")
                    else:
                        print("[INFO] No external path reference")
            
            # delete_part 콜백들
            if delete_callbacks:
                print("\\n" + "="*70)
                print(" delete_part_# Callbacks ({})".format(len(delete_callbacks)))
                print("="*70)
                
                for parm_info in delete_callbacks:
                    print("\\nParameter: {}".format(parm_info['name']))
                    print("Label: {}".format(parm_info['label']))
                    print("Language: {}".format(parm_info['language']))
                    print("Callback Script:")
                    print("-"*70)
                    print(parm_info['callback'])
                    print("-"*70)
                    
                    # 경로 체크
                    if 'd:/Antigravity' in parm_info['callback'] or 'd:\\\\Antigravity' in parm_info['callback']:
                        print("[WARNING] Uses old path: d:/Antigravity/houdini_tools")
                    elif 'T:\\\\\\\\scripts' in parm_info['callback'] or 'T:\\\\scripts' in parm_info['callback']:
                        print("[OK] Uses new path")
                    else:
                        print("[INFO] No external path reference")
            
            # 기타 콜백들 (이미 업데이트된 것들)
            if other_callbacks:
                print("\\n" + "="*70)
                print(" Other Callbacks (Already Updated)")
                print("="*70)
                
                for parm_info in other_callbacks:
                    status = "OK" if ('T:\\\\\\\\scripts' in parm_info['callback'] or 'T:\\\\scripts' in parm_info['callback']) else "OLD"
                    print("  [{}] {}".format(status, parm_info['name']))
            
            # 요약
            print("\\n" + "="*70)
            print(" Summary")
            print("="*70)
            print("Total callbacks: {}".format(len(all_callbacks)))
            print("  - part_name_# : {}".format(len(part_callbacks)))
            print("  - delete_part_#: {}".format(len(delete_callbacks)))
            print("  - other: {}".format(len(other_callbacks)))
            
        else:
            print("\\n[INFO] No callbacks found")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Search completed!")
print("="*80)

connector.disconnect()





