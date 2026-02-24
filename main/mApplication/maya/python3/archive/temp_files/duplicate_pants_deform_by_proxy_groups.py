#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
proxy_path 노드의 @proxy_path 그룹 리스트를 기준으로
Parts_Deform 노드를 복제하고 각각에 그룹 할당
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def duplicate_pants_by_proxy_groups():
    """proxy_path 노드의 그룹 리스트로 Parts_Deform 복제"""
    print("\n" + "="*80)
    print(" Duplicate Parts_Deform by proxy_path Groups")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Getting groups from proxy_path node...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou

# proxy_path 노드 찾기
proxy_node = hou.node("/obj/assets/Deform/proxy_path")

if not proxy_node:
    print("[ERROR] proxy_path node not found at /obj/assets/Deform/proxy_path")
    hou.session.proxy_groups = []
else:
    print(f"[OK] Found proxy_path node: {proxy_node.path()}")
    print(f"  Type: {proxy_node.type().name()}")
    
    try:
        # 노드의 지오메트리 가져오기
        geo = proxy_node.geometry()
        
        if geo:
            # 모든 프리미티브 그룹 가져오기
            all_groups = [g.name() for g in geo.primGroups()]
            
            print(f"\\nFound {len(all_groups)} primitive groups:")
            print("-" * 60)
            
            for i, group_name in enumerate(all_groups, 1):
                group = geo.findPrimGroup(group_name)
                prim_count = len(group.prims()) if group else 0
                print(f"  {i}. {group_name:<40} ({prim_count} prims)")
            
            # 세션에 저장
            hou.session.proxy_groups = all_groups
            
        else:
            print("[ERROR] No geometry on proxy_path node")
            hou.session.proxy_groups = []
            
    except Exception as e:
        print(f"[ERROR] Failed to get groups: {e}")
        import traceback
        traceback.print_exc()
        hou.session.proxy_groups = []
""", print_output=False)
        
        if result:
            print(result['stdout'])
            if result['stderr']:
                print("\n[STDERR]")
                print(result['stderr'])
        
        print("\n[2] Finding Parts_Deform node...")
        print("-"*80)
        h.execute("""
import hou

parts_node = hou.node("/obj/assets/Deform/Parts_Deform")

if parts_node:
    print(f"[OK] Found: {parts_node.path()}")
    print(f"  Type: {parts_node.type().name()}")
    print(f"  Position: {parts_node.position()}")
    
    # 현재 group 파라미터 확인
    group_parm = parts_node.parm("group")
    if group_parm:
        print(f"  Current group: {group_parm.eval()}")
    else:
        print(f"  [WARNING] No 'group' parameter found")
else:
    print("[ERROR] Parts_Deform node not found")
""")
        
        print("\n[3] Duplicating Parts_Deform for each group...")
        print("-"*80)
        
        result2 = h.connector.execute_code("""
import hou

parts_node = hou.node("/obj/assets/Deform/Parts_Deform")
proxy_groups = getattr(hou.session, 'proxy_groups', [])

if not parts_node:
    print("[ERROR] Parts_Deform node not found")
elif not proxy_groups:
    print("[ERROR] No groups found in proxy_path node")
else:
    try:
        parent = parts_node.parent()
        original_pos = parts_node.position()
        
        print(f"Creating {len(proxy_groups)} copies of Parts_Deform...")
        print("-" * 60)
        
        created_nodes = []
        
        for i, group_name in enumerate(proxy_groups):
            # 노드 이름 생성 (특수문자 제거)
            safe_name = group_name.replace('/', '_').replace('\\\\', '_').replace(':', '_').replace(' ', '_')
            new_name = f"Parts_Deform_{safe_name}"
            
            # 기존 노드 확인
            existing_node = parent.node(new_name)
            
            if existing_node:
                print(f"\\n[{i+1}/{len(proxy_groups)}] Node already exists: {new_name}")
                node = existing_node
            else:
                # 노드 복제
                copied = parent.copyItems([parts_node], channel_reference_originals=False)
                node = copied[0]
                node.setName(new_name, unique_name=True)
                print(f"\\n[{i+1}/{len(proxy_groups)}] Created: {node.name()}")
            
            # 위치 설정 (5개씩 가로로 배치)
            cols = 5
            x_offset = (i % cols) * 3
            y_offset = -(i // cols) * 3
            new_pos = hou.Vector2(original_pos.x() + x_offset, original_pos.y() + y_offset)
            node.setPosition(new_pos)
            
            # group 파라미터 설정
            group_parm = node.parm("group")
            if group_parm:
                group_parm.set(group_name)
                print(f"  Group parameter set: {group_name}")
            else:
                # 다른 가능한 파라미터 이름 시도
                found = False
                for pname in ['groupname', 'primgroup', 'group_name', 'grouplist']:
                    parm = node.parm(pname)
                    if parm:
                        parm.set(group_name)
                        print(f"  Group set via '{pname}': {group_name}")
                        found = True
                        break
                
                if not found:
                    print(f"  [WARNING] No group parameter found on node")
            
            print(f"  Position: ({new_pos.x():.2f}, {new_pos.y():.2f})")
            
            created_nodes.append(node)
        
        print(f"\\n{'='*60}")
        print(f"[OK] Successfully created/updated {len(created_nodes)} nodes")
        print(f"{'='*60}")
        
        # 레이아웃 정리
        parent.layoutChildren()
        print(f"\\n[OK] Layout updated")
        
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
        
        print("\n[4] Verification - Listing all Parts_Deform nodes...")
        print("-"*80)
        h.execute("""
import hou

parent = hou.node("/obj/assets/Deform")
if parent:
    # Parts_Deform로 시작하는 모든 노드
    parts_nodes = [n for n in parent.children() if n.name().startswith("Parts_Deform")]
    
    print(f"Total Parts_Deform nodes: {len(parts_nodes)}")
    print("=" * 80)
    
    for node in sorted(parts_nodes, key=lambda n: n.name()):
        # group 파라미터 값 가져오기
        group_parm = node.parm("group")
        if group_parm:
            group_val = group_parm.eval()
        else:
            group_val = "(no group parameter)"
        
        # 출력
        print(f"{node.name():<45} -> {group_val}")
else:
    print("[ERROR] /obj/assets/Deform not found")
""")
        
        print("\n" + "="*80)
        print("[OK] Operation completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        duplicate_pants_by_proxy_groups()
        
        print("\n" + "="*80)
        print(" Summary")
        print("="*80)
        print("""
작업 완료!

수행된 작업:
==========
1. proxy_path 노드에서 모든 프리미티브 그룹 추출
2. 그룹 개수만큼 Parts_Deform 노드 복제
3. 각 노드의 group 파라미터에 해당 그룹 이름 할당
4. 노드들을 5개씩 가로로 정렬
5. 레이아웃 자동 정리

결과:
====
- 각 그룹별로 독립적인 Parts_Deform 노드 생성됨
- 노드 이름: Parts_Deform_[그룹명]
- 각 노드는 해당 그룹만 처리

후디니에서 확인:
==============
1. /obj/assets/Deform 폴더 열기
2. Parts_Deform_* 노드들 확인
3. 각 노드의 group 파라미터 확인
4. 각 노드가 독립적으로 작동하는지 테스트
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Operation failed: {e}")
        import traceback
        traceback.print_exc()

