#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pants_Deform 노드를 @proxy_path 그룹 리스트 개수만큼 복제하고
각 노드의 group 파라미터에 그룹 할당
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def duplicate_pants_deform_by_groups():
    """Pants_Deform 노드를 그룹별로 복제"""
    print("\n" + "="*80)
    print(" Duplicate Pants_Deform Nodes by Groups")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Checking Pants_Deform node...")
        print("-"*80)
        h.execute("""
import hou

# Pants_Deform 노드 찾기
pants_node = hou.node("/obj/assets/Deform/Pants_Deform")

if pants_node:
    print(f"[OK] Found node: {pants_node.path()}")
    print(f"  Type: {pants_node.type().name()}")
    print(f"  Position: {pants_node.position()}")
else:
    print("[ERROR] Pants_Deform node not found at /obj/assets/Deform/Pants_Deform")
""")
        
        print("\n[2] Getting @proxy_path groups...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou

pants_node = hou.node("/obj/assets/Deform/Pants_Deform")

if not pants_node:
    print("[ERROR] Node not found")
else:
    try:
        # 노드의 지오메트리 가져오기
        geo = pants_node.geometry()
        
        if geo:
            # proxy_path 프리미티브 그룹 찾기
            proxy_groups = []
            
            # 모든 프리미티브 그룹 확인
            for group in geo.primGroups():
                group_name = group.name()
                # proxy_path 관련 그룹 찾기
                if 'proxy' in group_name.lower() or 'path' in group_name.lower():
                    proxy_groups.append(group_name)
            
            # 또는 모든 프리미티브 그룹 사용
            if not proxy_groups:
                proxy_groups = [g.name() for g in geo.primGroups()]
            
            print(f"Found {len(proxy_groups)} groups:")
            for i, group_name in enumerate(proxy_groups, 1):
                group = geo.findPrimGroup(group_name)
                prim_count = len(group.prims()) if group else 0
                print(f"  {i}. {group_name} ({prim_count} prims)")
            
            # 결과 저장
            hou.session.proxy_groups = proxy_groups
            
        else:
            print("[WARNING] No geometry found on node")
            print("Checking if node needs to be cooked...")
            
            # 노드 쿡하기
            pants_node.cook(force=True)
            geo = pants_node.geometry()
            
            if geo:
                proxy_groups = [g.name() for g in geo.primGroups()]
                print(f"\\nAfter cooking, found {len(proxy_groups)} groups:")
                for i, group_name in enumerate(proxy_groups, 1):
                    print(f"  {i}. {group_name}")
                hou.session.proxy_groups = proxy_groups
            else:
                print("[ERROR] Still no geometry after cooking")
                hou.session.proxy_groups = []
                
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        hou.session.proxy_groups = []
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
proxy_groups = getattr(hou.session, 'proxy_groups', [])

if not pants_node:
    print("[ERROR] Pants_Deform node not found")
elif not proxy_groups:
    print("[ERROR] No groups found")
else:
    try:
        parent = pants_node.parent()
        original_pos = pants_node.position()
        
        print(f"Parent node: {parent.path()}")
        print(f"Creating {len(proxy_groups)} duplicate nodes...")
        print("-" * 60)
        
        created_nodes = []
        
        for i, group_name in enumerate(proxy_groups):
            # 새 노드 이름 생성
            new_name = f"Pants_Deform_{group_name}"
            
            # 기존 노드가 있는지 확인
            existing_node = parent.node(new_name)
            if existing_node:
                print(f"  {i+1}. [EXISTS] {new_name}")
                node = existing_node
            else:
                # 노드 복제
                node = parent.copyItems([pants_node], channel_reference_originals=False)[0]
                node.setName(new_name, unique_name=True)
                print(f"  {i+1}. [CREATED] {node.name()}")
            
            # 위치 설정 (아래로 배치)
            new_pos = hou.Vector2(original_pos.x(), original_pos.y() - (i + 1) * 2)
            node.setPosition(new_pos)
            
            # group 파라미터 설정
            group_parm = node.parm("group")
            if group_parm:
                group_parm.set(group_name)
                print(f"       Group set: {group_name}")
            else:
                print(f"       [WARNING] No 'group' parameter found")
                # 다른 가능한 파라미터 이름 시도
                for pname in ['groupname', 'primgroup', 'group_name']:
                    parm = node.parm(pname)
                    if parm:
                        parm.set(group_name)
                        print(f"       Group set via '{pname}': {group_name}")
                        break
            
            created_nodes.append(node)
        
        print(f"\\n[OK] Created/Updated {len(created_nodes)} nodes")
        
        # 레이아웃 정리
        parent.layoutChildren()
        print(f"[OK] Layout updated")
        
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
        
        print("\n[4] Verifying created nodes...")
        print("-"*80)
        h.execute("""
import hou

parent = hou.node("/obj/assets/Deform")
if parent:
    # Pants_Deform로 시작하는 모든 노드 찾기
    pants_nodes = [n for n in parent.children() if n.name().startswith("Pants_Deform")]
    
    print(f"Found {len(pants_nodes)} Pants_Deform nodes:")
    print("-" * 60)
    
    for node in sorted(pants_nodes, key=lambda n: n.name()):
        print(f"\\nNode: {node.name()}")
        print(f"  Path: {node.path()}")
        
        # group 파라미터 확인
        group_parm = node.parm("group")
        if group_parm:
            group_value = group_parm.eval()
            print(f"  Group: {group_value if group_value else '(empty)'}")
        else:
            # 다른 파라미터 확인
            for pname in ['groupname', 'primgroup', 'group_name']:
                parm = node.parm(pname)
                if parm:
                    print(f"  {pname}: {parm.eval()}")
                    break
            else:
                print(f"  [WARNING] No group parameter found")
        
        print(f"  Position: {node.position()}")
else:
    print("Deform folder not found")
""")
        
        print("\n" + "="*80)
        print("[OK] Duplication completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        duplicate_pants_deform_by_groups()
        
        print("\n" + "="*80)
        print(" Summary")
        print("="*80)
        print("""
작업 완료!

수행된 작업:
1. Pants_Deform 노드 확인
2. @proxy_path 관련 그룹 리스트 추출
3. 그룹 개수만큼 노드 복제
4. 각 노드의 group 파라미터에 그룹 이름 할당
5. 레이아웃 정리

결과:
- 각 그룹별로 Pants_Deform_[그룹명] 노드 생성됨
- 각 노드는 해당 그룹만 처리하도록 설정됨

후디니에서 확인:
- /obj/assets/Deform 폴더 확인
- Pants_Deform_* 노드들이 생성되어 있음
- 각 노드의 group 파라미터 확인
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Operation failed: {e}")
        import traceback
        traceback.print_exc()






