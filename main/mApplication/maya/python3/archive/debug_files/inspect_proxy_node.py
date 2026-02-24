#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
assets/Proxy 노드 파라미터 및 스크립트 검사
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Inspecting assets/Proxy Node Parameters")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[1] Checking Proxy node existence...")
print("-" * 80)

# Proxy 노드 확인 및 파라미터 검사
code = """
import hou

try:
    # assets 노드 찾기
    assets_node = hou.node("/obj/assets")
    if not assets_node:
        print("[ERROR] /obj/assets node not found")
    else:
        print("[OK] Found /obj/assets node")
        
        # Proxy 노드 찾기
        proxy_node = assets_node.node("Proxy")
        if not proxy_node:
            print("[ERROR] Proxy node not found under /obj/assets")
        else:
            print("[OK] Found Proxy node at: {}".format(proxy_node.path()))
            
            print("\\n" + "="*70)
            print(" Proxy Node Parameters with Callbacks")
            print("="*70)
            
            # 모든 파라미터 검사
            parm_templates = proxy_node.parmTemplateGroup()
            parms_with_callbacks = []
            
            for parm_template in parm_templates.entries():
                parm_name = parm_template.name()
                parm = proxy_node.parm(parm_name)
                
                if parm:
                    # Callback Script 확인
                    callback_script = ""
                    script_language = ""
                    
                    try:
                        # ParmTemplate에서 callback 정보 가져오기
                        if hasattr(parm_template, 'scriptCallbackLanguage'):
                            script_language = str(parm_template.scriptCallbackLanguage())
                        
                        if hasattr(parm_template, 'scriptCallback'):
                            callback_script = parm_template.scriptCallback()
                    except:
                        pass
                    
                    if callback_script:
                        parms_with_callbacks.append({
                            'name': parm_name,
                            'label': parm_template.label(),
                            'type': str(parm_template.type()),
                            'language': script_language,
                            'callback': callback_script
                        })
            
            if parms_with_callbacks:
                print("\\nFound {} parameter(s) with callback scripts:\\n".format(
                    len(parms_with_callbacks)))
                
                for i, parm_info in enumerate(parms_with_callbacks, 1):
                    print("{}. Parameter: {}".format(i, parm_info['name']))
                    print("   Label: {}".format(parm_info['label']))
                    print("   Type: {}".format(parm_info['type']))
                    print("   Language: {}".format(parm_info['language']))
                    print("   Callback Script:")
                    print("   " + "-"*66)
                    
                    # 스크립트 출력 (긴 경우 줄바꿈)
                    callback_lines = parm_info['callback'].split('\\n')
                    for line in callback_lines:
                        if line.strip():
                            print("   {}".format(line))
                    print("   " + "-"*66)
                    print()
            else:
                print("\\n[INFO] No parameters with callback scripts found")
            
            # 파라미터 목록 출력
            print("\\n" + "="*70)
            print(" All Proxy Node Parameters")
            print("="*70)
            print()
            
            all_parms = proxy_node.parms()
            print("Total parameters: {}\\n".format(len(all_parms)))
            
            # 파라미터를 폴더별로 그룹화
            for parm_template in parm_templates.entries():
                if parm_template.type() != hou.parmTemplateType.Folder:
                    parm_name = parm_template.name()
                    parm_label = parm_template.label()
                    parm = proxy_node.parm(parm_name)
                    
                    if parm:
                        try:
                            parm_value = parm.eval()
                            print("  [{:20s}] {:30s} = {}".format(
                                parm_name, parm_label, repr(parm_value)[:50]))
                        except:
                            print("  [{:20s}] {:30s}".format(parm_name, parm_label))
            
            # Python Module 확인
            print("\\n" + "="*70)
            print(" Checking for Python Module")
            print("="*70)
            
            try:
                node_type = proxy_node.type()
                if node_type.definition():
                    sections = node_type.definition().sections()
                    python_module = None
                    
                    for section_name in sections:
                        if section_name.lower() in ['pythonmodule', 'python module']:
                            python_module = sections[section_name].contents()
                            break
                    
                    if python_module:
                        print("\\n[FOUND] Python Module:")
                        print("-"*70)
                        print(python_module)
                        print("-"*70)
                    else:
                        print("\\n[INFO] No Python Module found")
                else:
                    print("\\n[INFO] Node is not an HDA")
            except Exception as e:
                print("\\n[INFO] Could not check Python Module: {}".format(str(e)))
            
            # OnCreated Script 확인
            print("\\n" + "="*70)
            print(" Checking Event Handlers")
            print("="*70)
            
            try:
                node_type = proxy_node.type()
                if node_type.definition():
                    sections = node_type.definition().sections()
                    
                    event_handlers = [
                        'OnCreated', 'OnDeleted', 'OnLoaded', 
                        'OnInputChanged', 'OnNameChanged'
                    ]
                    
                    for handler_name in event_handlers:
                        for section_name in sections:
                            if section_name.lower() == handler_name.lower():
                                handler_script = sections[section_name].contents()
                                if handler_script.strip():
                                    print("\\n[FOUND] {} Script:".format(handler_name))
                                    print("-"*70)
                                    print(handler_script)
                                    print("-"*70)
            except Exception as e:
                print("\\n[INFO] Could not check event handlers: {}".format(str(e)))

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





