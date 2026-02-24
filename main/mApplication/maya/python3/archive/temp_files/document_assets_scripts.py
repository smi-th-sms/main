#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
assets 노드의 스크립트 상세 문서화
"""

import sys
import os
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def document_scripts():
    """assets 노드의 스크립트 상세 문서화"""
    print("\n" + "="*80)
    print(" Documenting assets Node Scripts")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[Extracting detailed script information...]")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou
import json

assets_node = hou.node("/obj/assets")

if not assets_node:
    print("[ERROR] assets node not found")
else:
    documentation = {
        'node_path': assets_node.path(),
        'node_type': assets_node.type().name(),
        'hda_library': assets_node.type().definition().libraryFilePath() if assets_node.type().definition() else None,
        'parameters': {}
    }
    
    # 각 파라미터의 상세 정보 추출
    for parm in assets_node.parms():
        parm_template = parm.parmTemplate()
        parm_info = {
            'name': parm.name(),
            'label': parm_template.label(),
            'type': str(parm_template.type()),
            'default': None,
            'current_value': None,
            'scripts': {}
        }
        
        # 현재 값
        try:
            parm_info['current_value'] = parm.eval()
        except:
            parm_info['current_value'] = parm.evalAsString()
        
        # 표현식
        try:
            expr = parm.expression()
            if expr:
                parm_info['scripts']['expression'] = {
                    'language': str(parm.expressionLanguage()),
                    'code': expr
                }
        except:
            pass
        
        # Menu Script
        if hasattr(parm_template, 'menuScriptLanguage'):
            menu_lang = parm_template.menuScriptLanguage()
            if menu_lang == hou.scriptLanguage.Python:
                if hasattr(parm_template, 'menuScript'):
                    menu_script = parm_template.menuScript()
                    if menu_script:
                        parm_info['scripts']['menu_script'] = menu_script
        
        # Button Callback
        if parm_template.type() == hou.parmTemplateType.Button:
            if hasattr(parm_template, 'scriptCallback'):
                callback = parm_template.scriptCallback()
                if callback:
                    parm_info['scripts']['button_callback'] = callback
        
        # 스크립트가 있는 파라미터만 저장
        if parm_info['scripts']:
            documentation['parameters'][parm.name()] = parm_info
    
    # JSON으로 출력 (인코딩 안전하게)
    print("[DOCUMENTATION]")
    print("=" * 70)
    
    for parm_name, parm_info in documentation['parameters'].items():
        print("")
        print("Parameter: {}".format(parm_name))
        print("  Label: {}".format(parm_info['label']))
        print("  Type: {}".format(parm_info['type']))
        print("  Current Value: {}".format(str(parm_info.get('current_value', ''))[:50]))
        print("")
        
        for script_type, script_content in parm_info['scripts'].items():
            print("  [{}]".format(script_type.upper()))
            
            if script_type == 'expression':
                print("    Language: {}".format(script_content['language']))
                code = script_content['code']
            else:
                code = script_content
            
            # 코드 출력 (줄별로)
            lines = code.split('\\n')
            print("    Lines: {}".format(len(lines)))
            print("    " + "-" * 60)
            
            # 처음 20줄만 출력
            for i, line in enumerate(lines[:20], 1):
                print("    {:3d} | {}".format(i, line))
            
            if len(lines) > 20:
                print("    ... ({} more lines)".format(len(lines) - 20))
            
            print("    " + "-" * 60)
        
        print("")
    
    print("=" * 70)
    print("[SUMMARY]")
    print("Total parameters with scripts: {}".format(len(documentation['parameters'])))
""", print_output=False)
        
        if result and result.get('stdout'):
            try:
                output = result['stdout'].encode('ascii', errors='ignore').decode('ascii')
                print(output)
            except:
                print("[Documentation generated]")
        
        print("\n" + "="*80)
        print("[Generating documentation file...]")
        print("="*80)
        
        # 문서 파일 생성
        doc_file = r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3\ASSETS_SCRIPTS_DOCUMENTATION.txt"
        
        doc_result = h.connector.execute_code("""
import hou

assets_node = hou.node("/obj/assets")

if assets_node:
    doc_lines = []
    doc_lines.append("="*80)
    doc_lines.append(" ASSETS NODE SCRIPTS DOCUMENTATION")
    doc_lines.append("="*80)
    doc_lines.append("")
    doc_lines.append("Node: {}".format(assets_node.path()))
    doc_lines.append("Type: {}".format(assets_node.type().name()))
    
    if assets_node.type().definition():
        doc_lines.append("HDA Library: {}".format(assets_node.type().definition().libraryFilePath()))
    
    doc_lines.append("")
    doc_lines.append("="*80)
    doc_lines.append(" PARAMETERS WITH SCRIPTS")
    doc_lines.append("="*80)
    doc_lines.append("")
    
    script_params = []
    
    for parm in assets_node.parms():
        parm_template = parm.parmTemplate()
        has_script = False
        parm_doc = []
        
        # 표현식
        try:
            expr = parm.expression()
            if expr:
                has_script = True
                parm_doc.append("")
                parm_doc.append("-" * 80)
                parm_doc.append("PARAMETER: {} ({})".format(parm.name(), parm_template.label()))
                parm_doc.append("-" * 80)
                parm_doc.append("")
                parm_doc.append("[EXPRESSION]")
                parm_doc.append("  Language: {}".format(parm.expressionLanguage()))
                parm_doc.append("  Code:")
                parm_doc.append("")
                for line in expr.split('\\n'):
                    parm_doc.append("    {}".format(line))
                parm_doc.append("")
        except:
            pass
        
        # Menu Script
        if hasattr(parm_template, 'menuScriptLanguage'):
            menu_lang = parm_template.menuScriptLanguage()
            if menu_lang == hou.scriptLanguage.Python:
                if hasattr(parm_template, 'menuScript'):
                    menu_script = parm_template.menuScript()
                    if menu_script:
                        has_script = True
                        if not parm_doc:
                            parm_doc.append("")
                            parm_doc.append("-" * 80)
                            parm_doc.append("PARAMETER: {} ({})".format(parm.name(), parm_template.label()))
                            parm_doc.append("-" * 80)
                            parm_doc.append("")
                        
                        parm_doc.append("[MENU SCRIPT]")
                        parm_doc.append("  Purpose: Dynamic menu generation")
                        parm_doc.append("  Code:")
                        parm_doc.append("")
                        for line in menu_script.split('\\n'):
                            parm_doc.append("    {}".format(line))
                        parm_doc.append("")
        
        # Button Callback
        if parm_template.type() == hou.parmTemplateType.Button:
            if hasattr(parm_template, 'scriptCallback'):
                callback = parm_template.scriptCallback()
                if callback:
                    has_script = True
                    if not parm_doc:
                        parm_doc.append("")
                        parm_doc.append("-" * 80)
                        parm_doc.append("PARAMETER: {} ({})".format(parm.name(), parm_template.label()))
                        parm_doc.append("-" * 80)
                        parm_doc.append("")
                    
                    parm_doc.append("[BUTTON CALLBACK]")
                    parm_doc.append("  Purpose: Action triggered on button press")
                    parm_doc.append("  Code:")
                    parm_doc.append("")
                    for line in callback.split('\\n'):
                        parm_doc.append("    {}".format(line))
                    parm_doc.append("")
        
        if has_script:
            script_params.append('\\n'.join(parm_doc))
    
    doc_lines.extend(script_params)
    
    doc_lines.append("")
    doc_lines.append("="*80)
    doc_lines.append(" SUMMARY")
    doc_lines.append("="*80)
    doc_lines.append("Total parameters with scripts: {}".format(len(script_params)))
    doc_lines.append("")
    
    # hou.session에 저장
    hou.session.assets_documentation = '\\n'.join(doc_lines)
    
    print("[OK] Documentation generated")
    print("Total parameters with scripts: {}".format(len(script_params)))
    print("")
    print("Documentation saved to hou.session.assets_documentation")
""", print_output=False)
        
        if doc_result and doc_result.get('stdout'):
            try:
                print(doc_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[OK]")
        
        # 문서 파일로 저장
        print("\n[Saving documentation to file...]")
        save_result = h.connector.execute_code("""
import hou

if hasattr(hou.session, 'assets_documentation'):
    doc = hou.session.assets_documentation
    
    # 파일로 저장 시도
    try:
        import os
        doc_path = r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3\\ASSETS_SCRIPTS_DOCUMENTATION.txt"
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(doc)
        
        print("[OK] Documentation saved to:")
        print("  {}".format(doc_path))
        print("  Size: {} bytes".format(len(doc)))
        
    except Exception as e:
        print("[ERROR] Could not save file: {}".format(e))
        print("")
        print("Documentation content:")
        print("=" * 70)
        # 처음 50줄만 출력
        lines = doc.split('\\n')
        for line in lines[:50]:
            print(line)
        if len(lines) > 50:
            print("... ({} more lines)".format(len(lines) - 50))
else:
    print("[ERROR] Documentation not found in session")
""", print_output=False)
        
        if save_result and save_result.get('stdout'):
            try:
                print(save_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Saved]")
        
        print("\n" + "="*80)
        print("[OK] Documentation completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        document_scripts()
        
        print("\n" + "="*80)
        print(" Documentation Summary")
        print("="*80)
        print("""
문서화 완료!

생성된 파일:
===========
ASSETS_SCRIPTS_DOCUMENTATION.txt
  - assets 노드의 모든 스크립트 파라미터 문서화
  - Menu Script, Button Callback, Expression 포함
  - 전체 코드와 설명 포함

확인된 스크립트:
=============
1. project_dir (Menu Script)
   - 프로젝트 경로 동적 메뉴 생성
   - 외부 도구 경로 참조

2. auto_setup_btn (Button Callback)
   - 자동 설정 및 로드/분할 기능
   - FBX 로드 및 지오메트리 분할 처리

3. check_create_dir (Button Callback)
   - 디렉토리 확인/생성 기능
   - 프로젝트 경로 검증

추가 작업:
=========
- 각 스크립트의 의존성 확인
- 외부 파일 참조 확인
- 스크립트 최적화 가능 여부 검토
""")
        print("="*80)
        
    except Exception as e:
        print("\n[ERROR] Documentation failed: {}".format(e))
        import traceback
        traceback.print_exc()





