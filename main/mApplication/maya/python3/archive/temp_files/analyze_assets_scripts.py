#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
assets 노드의 모든 파라미터와 스크립트 분석
"""

import sys
import os
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def analyze_assets_scripts():
    """assets 노드의 모든 스크립트 분석"""
    print("\n" + "="*80)
    print(" Analyzing assets Node Scripts")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Finding assets node...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou

assets_node = hou.node("/obj/assets")

if not assets_node:
    print("[ERROR] /obj/assets node not found")
else:
    print("[OK] Found: {}".format(assets_node.path()))
    print("  Type: {}".format(assets_node.type().name()))
    
    # HDA 확인
    node_type = assets_node.type()
    if node_type.definition():
        print("  HDA: {}".format(node_type.name()))
        print("  Library: {}".format(node_type.definition().libraryFilePath()))
    else:
        print("  Not an HDA")
""", print_output=False)
        
        if result and result.get('stdout'):
            try:
                print(result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[OK] Node found")
        
        print("\n[2] Analyzing assets node parameters...")
        print("-"*80)
        
        assets_result = h.connector.execute_code("""
import hou

assets_node = hou.node("/obj/assets")

if assets_node:
    print("[Assets Node Parameter Analysis]")
    print("=" * 70)
    
    # 모든 파라미터 분석
    script_count = 0
    expression_count = 0
    menu_script_count = 0
    callback_count = 0
    
    for parm in assets_node.parms():
        parm_template = parm.parmTemplate()
        has_script = False
        
        # 표현식 확인
        try:
            expr = parm.expression()
            if expr:
                expression_count += 1
                has_script = True
                print("")
                print("[EXPRESSION] {}".format(parm.name()))
                print("  Label: {}".format(parm_template.label()))
                print("  Language: {}".format(parm.expressionLanguage()))
                print("  Expression: {}".format(expr[:100]))
                if len(expr) > 100:
                    print("    ... ({} more chars)".format(len(expr) - 100))
        except:
            pass
        
        # Menu Script 확인
        if hasattr(parm_template, 'menuType'):
            menu_type = parm_template.menuType()
            if menu_type == hou.menuType.StringReplace:
                # Menu script가 있을 수 있음
                if hasattr(parm_template, 'menuItems'):
                    menu_items = parm_template.menuItems()
                    if menu_items and len(menu_items) > 0:
                        # 정적 메뉴
                        pass
                
                # Script Menu 확인
                if hasattr(parm_template, 'scriptCallbackLanguage'):
                    script_lang = parm_template.scriptCallbackLanguage()
                    if script_lang == hou.scriptLanguage.Python:
                        if hasattr(parm_template, 'scriptCallback'):
                            script = parm_template.scriptCallback()
                            if script:
                                menu_script_count += 1
                                has_script = True
                                print("")
                                print("[MENU SCRIPT] {}".format(parm.name()))
                                print("  Label: {}".format(parm_template.label()))
                                print("  Script: {}".format(script[:100]))
                                if len(script) > 100:
                                    print("    ... ({} more chars)".format(len(script) - 100))
        
        # Menu Script (다른 방식)
        if hasattr(parm_template, 'menuScriptLanguage'):
            menu_lang = parm_template.menuScriptLanguage()
            if menu_lang == hou.scriptLanguage.Python:
                if hasattr(parm_template, 'menuScript'):
                    menu_script = parm_template.menuScript()
                    if menu_script:
                        menu_script_count += 1
                        has_script = True
                        print("")
                        print("[MENU SCRIPT] {}".format(parm.name()))
                        print("  Label: {}".format(parm_template.label()))
                        print("  Script: {}".format(menu_script[:100]))
                        if len(menu_script) > 100:
                            print("    ... ({} more chars)".format(len(menu_script) - 100))
        
        # Button Callback 확인
        if parm_template.type() == hou.parmTemplateType.Button:
            if hasattr(parm_template, 'scriptCallback'):
                callback = parm_template.scriptCallback()
                if callback:
                    callback_count += 1
                    has_script = True
                    print("")
                    print("[BUTTON CALLBACK] {}".format(parm.name()))
                    print("  Label: {}".format(parm_template.label()))
                    print("  Callback: {}".format(callback[:100]))
                    if len(callback) > 100:
                        print("    ... ({} more chars)".format(len(callback) - 100))
        
        # Hide When 확인
        if hasattr(parm_template, 'hideCondition'):
            hide_cond = parm_template.hideCondition()
            if hide_cond:
                has_script = True
                script_count += 1
        
        # Disable When 확인
        if hasattr(parm_template, 'disableCondition'):
            disable_cond = parm_template.disableCondition()
            if disable_cond:
                has_script = True
                script_count += 1
    
    print("")
    print("=" * 70)
    print("[SUMMARY]")
    print("  Expressions: {}".format(expression_count))
    print("  Menu Scripts: {}".format(menu_script_count))
    print("  Button Callbacks: {}".format(callback_count))
    print("  Conditional Scripts: {}".format(script_count))
""", print_output=False)
        
        if assets_result and assets_result.get('stdout'):
            try:
                print(assets_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Analysis complete]")
        
        print("\n[3] Analyzing child nodes...")
        print("-"*80)
        
        children_result = h.connector.execute_code("""
import hou

assets_node = hou.node("/obj/assets")

if assets_node:
    children = assets_node.allSubChildren()
    
    print("[Child Nodes Analysis]")
    print("=" * 70)
    print("Total child nodes: {}".format(len(children)))
    print("")
    
    nodes_with_scripts = []
    
    for child in children:
        has_script = False
        script_info = {
            'node': child,
            'expressions': [],
            'menu_scripts': [],
            'callbacks': [],
            'hide_when': [],
            'disable_when': []
        }
        
        for parm in child.parms():
            parm_template = parm.parmTemplate()
            
            # 표현식
            try:
                expr = parm.expression()
                if expr:
                    has_script = True
                    script_info['expressions'].append({
                        'parm': parm.name(),
                        'expr': expr
                    })
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
                            script_info['menu_scripts'].append({
                                'parm': parm.name(),
                                'script': menu_script
                            })
            
            # Button Callback
            if parm_template.type() == hou.parmTemplateType.Button:
                if hasattr(parm_template, 'scriptCallback'):
                    callback = parm_template.scriptCallback()
                    if callback:
                        has_script = True
                        script_info['callbacks'].append({
                            'parm': parm.name(),
                            'callback': callback
                        })
            
            # Hide When
            if hasattr(parm_template, 'hideCondition'):
                hide_cond = parm_template.hideCondition()
                if hide_cond:
                    has_script = True
                    script_info['hide_when'].append({
                        'parm': parm.name(),
                        'condition': str(hide_cond)
                    })
            
            # Disable When
            if hasattr(parm_template, 'disableCondition'):
                disable_cond = parm_template.disableCondition()
                if disable_cond:
                    has_script = True
                    script_info['disable_when'].append({
                        'parm': parm.name(),
                        'condition': str(disable_cond)
                    })
        
        if has_script:
            nodes_with_scripts.append(script_info)
    
    print("Nodes with scripts: {}".format(len(nodes_with_scripts)))
    print("")
    
    # 스크립트가 많은 노드들만 출력
    for info in nodes_with_scripts[:10]:  # 처음 10개만
        node = info['node']
        total_scripts = (len(info['expressions']) + 
                        len(info['menu_scripts']) + 
                        len(info['callbacks']) +
                        len(info['hide_when']) +
                        len(info['disable_when']))
        
        print("{} ({})".format(node.path(), node.type().name()))
        print("  Expressions: {}".format(len(info['expressions'])))
        print("  Menu Scripts: {}".format(len(info['menu_scripts'])))
        print("  Callbacks: {}".format(len(info['callbacks'])))
        print("  Hide Conditions: {}".format(len(info['hide_when'])))
        print("  Disable Conditions: {}".format(len(info['disable_when'])))
        print("")
    
    if len(nodes_with_scripts) > 10:
        print("... and {} more nodes with scripts".format(len(nodes_with_scripts) - 10))
    
    # 세션에 저장
    hou.session.assets_script_analysis = nodes_with_scripts
    print("")
    print("[OK] Analysis saved to hou.session.assets_script_analysis")
""", print_output=False)
        
        if children_result and children_result.get('stdout'):
            try:
                print(children_result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Analysis complete]")
        
        print("\n" + "="*80)
        print("[OK] Analysis completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        analyze_assets_scripts()
        
    except Exception as e:
        print("\n[ERROR] Analysis failed: {}".format(e))
        import traceback
        traceback.print_exc()





