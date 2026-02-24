#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Proxy 노드의 Multiparm 콜백 스크립트 검사
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Inspecting Proxy Multiparm Callbacks")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Checking multiparm parameter callbacks...")
print("-" * 80)

# Multiparm 파라미터 콜백 검사
code = """
import hou

try:
    proxy_node = hou.node("/obj/assets/Proxy")
    if not proxy_node:
        print("[ERROR] Proxy node not found")
    else:
        print("[OK] Found Proxy node")
        
        print("\\n" + "="*70)
        print(" Multiparm Parameter Templates")
        print("="*70)
        
        ptg = proxy_node.parmTemplateGroup()
        
        # cloth_parts multiparm 찾기
        cloth_parts_template = ptg.find("cloth_parts")
        if cloth_parts_template and cloth_parts_template.type() == hou.parmTemplateType.FolderSet:
            print("\\n[Found Multiparm: cloth_parts]")
            print("-"*70)
            
            # Multiparm의 하위 템플릿들 확인
            parm_templates = cloth_parts_template.parmTemplates()
            
            callbacks_found = []
            
            for parm_template in parm_templates:
                parm_name = parm_template.name()
                parm_label = parm_template.label()
                
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
                        'type': str(parm_template.type()),
                        'language': script_language,
                        'callback': callback_script
                    })
            
            if callbacks_found:
                print("\\nFound {} parameter(s) with callbacks in multiparm:\\n".format(
                    len(callbacks_found)))
                
                for i, parm_info in enumerate(callbacks_found, 1):
                    print("{}. Parameter: {}".format(i, parm_info['name']))
                    print("   Label: {}".format(parm_info['label']))
                    print("   Type: {}".format(parm_info['type']))
                    print("   Language: {}".format(parm_info['language']))
                    print("   Callback Script:")
                    print("   " + "-"*66)
                    
                    # 스크립트 출력
                    callback_lines = parm_info['callback'].split('\\n')
                    for line in callback_lines:
                        print("   {}".format(line))
                    print("   " + "-"*66)
                    
                    # 경로 체크
                    if 'd:/Antigravity' in parm_info['callback'] or 'd:\\\\Antigravity' in parm_info['callback']:
                        print("   [WARNING] Uses old path: d:/Antigravity/houdini_tools")
                    elif 'T:\\\\\\\\scripts' in parm_info['callback'] or 'T:\\\\scripts' in parm_info['callback']:
                        print("   [OK] Uses new path")
                    else:
                        print("   [INFO] Custom script (not using external path)")
                    
                    print()
            else:
                print("\\n[INFO] No callbacks found in multiparm parameters")
        else:
            print("\\n[WARNING] cloth_parts multiparm not found")
        
        # 실제 인스턴스 확인 (cloth_parts가 1 이상인 경우)
        try:
            count = proxy_node.parm("cloth_parts").evalAsInt()
            if count > 0:
                print("\\n" + "="*70)
                print(" Current Multiparm Instances")
                print("="*70)
                print("\\nCloth Parts Count: {}\\n".format(count))
                
                for i in range(1, min(count + 1, 4)):  # 최대 3개만 출력
                    print("Part {}:".format(i))
                    
                    # part_name
                    part_name_parm = proxy_node.parm("part_name_{}".format(i))
                    if part_name_parm:
                        print("  part_name_{}: {}".format(i, part_name_parm.evalAsString()))
                    
                    # delete_part 버튼 확인
                    delete_parm = proxy_node.parm("delete_part_{}".format(i))
                    if delete_parm:
                        print("  delete_part_{}: exists".format(i))
                
                if count > 3:
                    print("  ... ({} more)".format(count - 3))
        except:
            print("\\n[INFO] No multiparm instances currently")

except Exception as e:
    print("[ERROR] {}".format(str(e)))
    import traceback
    traceback.print_exc()
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[OK] Inspection completed!")
print("="*80)

connector.disconnect()





