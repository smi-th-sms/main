#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parts_Deform 노드의 group 파라미터 확인
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


with connect_houdini() as h:
    print("\n" + "="*80)
    print(" Checking Parts_Deform group parameter")
    print("="*80)
    
    h.execute("""
import hou

parts_node = hou.node("/obj/assets/Deform/Parts_Deform")

if parts_node:
    print(f"\\n[OK] Found: {parts_node.path()}")
    print(f"Type: {parts_node.type().name()}")
    print("-" * 80)
    
    # 모든 파라미터 확인
    print("\\n[All Parameters]:")
    print("-" * 80)
    
    for parm in parts_node.parms():
        parm_name = parm.name()
        
        # group 관련 파라미터만 출력
        if 'group' in parm_name.lower() or 'path' in parm_name.lower():
            try:
                value = parm.eval()
                if value:  # 값이 있는 경우만
                    print(f"  {parm_name:<30} = {value}")
                    
                    # 표현식인지 확인
                    try:
                        expr = parm.expression()
                        if expr:
                            print(f"    -> Expression: {expr}")
                    except:
                        pass
            except:
                pass
    
    # 특별히 group 파라미터 상세 확인
    print("\\n" + "="*80)
    print("[Detailed Group Parameter Info]:")
    print("-" * 80)
    
    group_parm = parts_node.parm("group")
    if group_parm:
        raw_value = group_parm.unexpandedString()
        eval_value = group_parm.eval()
        
        print(f"  Parameter name: {group_parm.name()}")
        print(f"  Raw value (unexpanded): {raw_value}")
        print(f"  Evaluated value: {eval_value}")
        
        # 표현식 확인
        try:
            expr = group_parm.expression()
            if expr:
                print(f"  Expression: {expr}")
                print(f"  Expression language: {group_parm.expressionLanguage()}")
        except:
            print(f"  No expression")
        
        # 참조하는 노드가 있는지 확인
        if raw_value and ('/' in raw_value or '..' in raw_value):
            print(f"\\n  -> This looks like a node reference!")
            print(f"  -> Trying to resolve the path...")
            
            # 경로에서 노드 경로 추출 시도
            if '../' in raw_value or './' in raw_value:
                # 상대 경로인 경우
                print(f"  -> Relative path detected")
            elif raw_value.startswith('/'):
                # 절대 경로인 경우
                print(f"  -> Absolute path detected")
                
    else:
        print("  [ERROR] No 'group' parameter found")
        
    # 서브넷 내부 확인
    if parts_node.type().name() == 'subnet':
        print("\\n" + "="*80)
        print("[Subnet Children - Looking for relevant nodes]:")
        print("-" * 80)
        
        children = parts_node.children()
        print(f"Total children: {len(children)}\\n")
        
        for child in children:
            print(f"  - {child.name():<30} ({child.type().name()})")
            
            # 이 노드가 proxy_path 데이터를 가지고 있는지 확인
            if 'proxy' in child.name().lower() or 'group' in child.name().lower():
                print(f"      -> Interesting node! Checking details...")
                
                # group 파라미터 확인
                for pname in ['group', 'groupname', 'primgroup']:
                    parm = child.parm(pname)
                    if parm:
                        val = parm.eval()
                        if val:
                            print(f"      -> {pname}: {val}")
                
                # 지오메트리의 그룹 확인
                try:
                    geo = child.geometry()
                    if geo:
                        prim_groups = [g.name() for g in geo.primGroups()]
                        if prim_groups:
                            print(f"      -> Primitive groups: {prim_groups}")
                except:
                    pass
    
else:
    print("[ERROR] Parts_Deform node not found")
""")






