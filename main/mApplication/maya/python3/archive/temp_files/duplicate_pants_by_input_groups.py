#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pants_Deform 노드의 입력 지오메트리에서 그룹을 찾아서 복제
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def duplicate_pants_by_input_groups():
    """입력 지오메트리의 그룹을 기반으로 Pants_Deform 복제"""
    print("\n" + "="*80)
    print(" Duplicate Pants_Deform by Input Groups")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Analyzing Pants_Deform node structure...")
        print("-"*80)
        h.execute("""
import hou

pants_node = hou.node("/obj/assets/Deform/Pants_Deform")

if pants_node:
    print(f"Node: {pants_node.path()}")
    print(f"Type: {pants_node.type().name()}")
    print(f"Is subnet: {pants_node.type().name() in ['subnet', 'geo']}")
    
    # 현재 group 파라미터 값
    group_parm = pants_node.parm("group")
    if group_parm:
        current_group = group_parm.eval()
        print(f"\\nCurrent group parameter: {current_group}")
    
    # 입력 연결 확인
    inputs = pants_node.inputs()
    print(f"\\nInputs: {len(inputs)}")
    for i, inp in enumerate(inputs):
        if inp:
            print(f"  Input {i}: {inp.path()}")
    
    # 자식 노드 확인 (subnet인 경우)
    if pants_node.type().name() in ['subnet', 'geo']:
        children = pants_node.children()
        print(f"\\nChildren: {len(children)}")
        for child in children[:10]:
            print(f"  - {child.name()} ({child.type().name()})")
        if len(children) > 10:
            print(f"  ... and {len(children) - 10} more")
else:
    print("Node not found")
""")
        
        print("\n[2] Finding groups from input geometry...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou

pants_node = hou.node("/obj/assets/Deform/Pants_Deform")

if not pants_node:
    print("[ERROR] Node not found")
    hou.session.found_groups = []
else:
    try:
        # 입력에서 지오메트리 가져오기
        input_node = pants_node.inputs()[0] if pants_node.inputs() else None
        
        if input_node:
            print(f"Input node: {input_node.path()}")
            
            # 입력 노드의 지오메트리 가져오기
            try:
                input_geo = input_node.geometry()
                
                if input_geo:
                    # 프리미티브 그룹 찾기
                    prim_groups = [g.name() for g in input_geo.primGroups()]
                    
                    print(f"\\nFound {len(prim_groups)} primitive groups:")
                    for i, group_name in enumerate(prim_groups, 1):
                        group = input_geo.findPrimGroup(group_name)
                        prim_count = len(group.prims()) if group else 0
                        print(f"  {i}. {group_name} ({prim_count} prims)")
                    
                    hou.session.found_groups = prim_groups
                else:
                    print("[WARNING] No geometry on input node")
                    hou.session.found_groups = []
                    
            except Exception as e:
                print(f"[ERROR] Could not get geometry: {e}")
                hou.session.found_groups = []
        else:
            # 입력이 없으면 subnet 내부에서 찾기
            print("No direct input, checking subnet internals...")
            
            # 서브넷 내부의 output 또는 마지막 노드 찾기
            display_node = None
            for child in pants_node.children():
                if child.isDisplayFlagSet():
                    display_node = child
                    break
                elif child.name() in ['output0', 'OUT', 'OUT_0']:
                    display_node = child
                    break
            
            if not display_node and pants_node.children():
                # 첫 번째 출력 노드 사용
                for child in pants_node.children():
                    if child.type().name() == 'output':
                        display_node = child
                        break
            
            if display_node:
                print(f"Display node: {display_node.path()}")
                
                # 그 노드의 입력을 거슬러 올라가기
                geo_node = display_node
                while geo_node.inputs():
                    geo_node = geo_node.inputs()[0]
                
                print(f"Source node: {geo_node.path()}")
                
                try:
                    geo = geo_node.geometry()
                    if geo:
                        prim_groups = [g.name() for g in geo.primGroups()]
                        print(f"\\nFound {len(prim_groups)} groups:")
                        for i, group_name in enumerate(prim_groups, 1):
                            print(f"  {i}. {group_name}")
                        hou.session.found_groups = prim_groups
                    else:
                        print("[WARNING] No geometry")
                        hou.session.found_groups = []
                except:
                    hou.session.found_groups = []
            else:
                print("[WARNING] Could not find display node")
                hou.session.found_groups = []
                
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        hou.session.found_groups = []
""", print_output=False)
        
        if result:
            print(result['stdout'])
            if result['stderr']:
                print("\n[STDERR]")
                print(result['stderr'])
        
        print("\n[3] Duplicating nodes for each group...")
        print("-"*80)
        
        result2 = h.connector.execute_code("""
import hou

pants_node = hou.node("/obj/assets/Deform/Pants_Deform")
found_groups = getattr(hou.session, 'found_groups', [])

if not pants_node:
    print("[ERROR] Node not found")
elif not found_groups:
    print("[WARNING] No groups found to duplicate")
    print("\\nWould you like to:")
    print("1. Check if the input geometry has groups")
    print("2. Verify the node connections")
    print("3. Manually specify group names")
else:
    try:
        parent = pants_node.parent()
        original_pos = pants_node.position()
        
        print(f"Creating {len(found_groups)} duplicate nodes...")
        print("-" * 60)
        
        created_nodes = []
        
        for i, group_name in enumerate(found_groups):
            # 새 노드 이름 생성
            # 그룹명에서 특수문자 제거
            safe_name = group_name.replace('/', '_').replace('\\\\', '_').replace(':', '_')
            new_name = f"Pants_Deform_{safe_name}"
            
            # 기존 노드 확인
            existing_node = parent.node(new_name)
            if existing_node:
                print(f"  {i+1}. [EXISTS] {new_name}")
                node = existing_node
            else:
                # 노드 복제
                node = parent.copyItems([pants_node], channel_reference_originals=False)[0]
                node.setName(new_name, unique_name=True)
                print(f"  {i+1}. [CREATED] {node.name()}")
            
            # 위치 설정
            x_offset = (i % 5) * 3  # 5개씩 가로로 배치
            y_offset = -(i // 5) * 3  # 5개마다 아래로
            new_pos = hou.Vector2(original_pos.x() + x_offset, original_pos.y() + y_offset)
            node.setPosition(new_pos)
            
            # group 파라미터 설정
            group_parm = node.parm("group")
            if group_parm:
                group_parm.set(group_name)
                print(f"       Set group: {group_name}")
            else:
                print(f"       [WARNING] No 'group' parameter")
            
            created_nodes.append(node)
        
        print(f"\\n[OK] Created/Updated {len(created_nodes)} nodes")
        
        # 레이아웃 정리
        parent.layoutChildren()
        print(f"[OK] Layout updated")
        
        # 결과 저장
        hou.session.created_pants_nodes = created_nodes
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
""", print_output=False)
        
        if result2:
            print(result2['stdout'])
            if result2['stderr']:
                print("\n[STDERR]")
                print(result2['stderr'])
        
        print("\n[4] Verification...")
        print("-"*80)
        h.execute("""
import hou

parent = hou.node("/obj/assets/Deform")
if parent:
    pants_nodes = [n for n in parent.children() if n.name().startswith("Pants_Deform")]
    
    print(f"Total Pants_Deform nodes: {len(pants_nodes)}")
    print("-" * 60)
    
    for node in sorted(pants_nodes, key=lambda n: n.name()):
        group_parm = node.parm("group")
        group_val = group_parm.eval() if group_parm else "N/A"
        print(f"{node.name():<40} -> {group_val}")
""")
        
        print("\n" + "="*80)
        print("[OK] Operation completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        duplicate_pants_by_input_groups()
        
        print("\n" + "="*80)
        print(" Next Steps")
        print("="*80)
        print("""
작업 완료 또는 추가 정보 필요!

만약 그룹이 발견되지 않았다면:

1. 입력 노드 확인:
   - Pants_Deform 노드의 입력이 올바른지 확인
   - 입력 지오메트리에 프리미티브 그룹이 있는지 확인

2. 수동으로 그룹 지정:
   그룹 이름을 알고 있다면 직접 지정할 수 있습니다.

3. 서브넷 내부 확인:
   - Pants_Deform이 서브넷이면 내부 구조 확인
   - 어느 노드에서 지오메트리를 가져오는지 확인

추가 도움이 필요하시면 말씀해주세요!
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Operation failed: {e}")
        import traceback
        traceback.print_exc()






