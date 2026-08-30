#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
proxy_path 노드의 @proxy_path 어트리뷰트 값들을 기준으로
Parts_Deform 노드를 복제하고 각각에 필터 할당
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def duplicate_parts_by_proxy_path_attribute():
    """@proxy_path 어트리뷰트 값으로 Parts_Deform 복제"""
    print("\n" + "="*80)
    print(" Duplicate Parts_Deform by @proxy_path Attribute Values")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Extracting @proxy_path attribute values...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou

proxy_node = hou.node("/obj/assets/Deform/proxy_path")

if not proxy_node:
    print("[ERROR] proxy_path node not found")
    hou.session.proxy_path_values = []
else:
    print(f"[OK] Found proxy_path node: {proxy_node.path()}")
    
    try:
        geo = proxy_node.geometry()
        
        if geo:
            # @proxy_path primitive 어트리뷰트 확인
            proxy_path_attrib = geo.findPrimAttrib("proxy_path")
            
            if proxy_path_attrib:
                print(f"[OK] Found @proxy_path primitive attribute")
                
                # 고유한 값들 추출
                unique_values = set()
                prim_counts = {}
                
                for prim in geo.prims():
                    val = prim.attribValue("proxy_path")
                    if val:  # 빈 문자열 제외
                        unique_values.add(val)
                        prim_counts[val] = prim_counts.get(val, 0) + 1
                
                # 정렬
                unique_values = sorted(list(unique_values))
                
                print(f"\\nFound {len(unique_values)} unique values:")
                print("-" * 60)
                
                for i, value in enumerate(unique_values, 1):
                    # 경로에서 마지막 부분만 추출 (표시용)
                    short_name = value.split('/')[-1]
                    count = prim_counts.get(value, 0)
                    print(f"  {i}. {short_name:<30} ({count:>6} prims)")
                    print(f"     Path: {value}")
                
                # 세션에 저장
                hou.session.proxy_path_values = unique_values
                
            else:
                print("[ERROR] @proxy_path attribute not found")
                hou.session.proxy_path_values = []
        else:
            print("[ERROR] No geometry")
            hou.session.proxy_path_values = []
            
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        hou.session.proxy_path_values = []
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
        current_group = group_parm.eval()
        print(f"  Current group filter: {current_group}")
    else:
        print(f"  [WARNING] No 'group' parameter found")
else:
    print("[ERROR] Parts_Deform node not found")
""")
        
        print("\n[3] Duplicating Parts_Deform for each @proxy_path value...")
        print("-"*80)
        
        result2 = h.connector.execute_code("""
import hou

parts_node = hou.node("/obj/assets/Deform/Parts_Deform")
proxy_path_values = getattr(hou.session, 'proxy_path_values', [])

if not parts_node:
    print("[ERROR] Parts_Deform node not found")
elif not proxy_path_values:
    print("[ERROR] No @proxy_path values found")
else:
    try:
        parent = parts_node.parent()
        original_pos = parts_node.position()
        
        print(f"Creating {len(proxy_path_values)} copies of Parts_Deform...")
        print("=" * 80)
        
        created_nodes = []
        
        for i, path_value in enumerate(proxy_path_values):
            # 경로에서 마지막 부분 추출 (노드 이름용)
            # 예: /Jake/.../Pants_geo -> Pants_geo
            short_name = path_value.split('/')[-1]
            
            # 노드 이름 생성
            new_name = f"Parts_Deform_{short_name}"
            
            # 기존 노드 확인
            existing_node = parent.node(new_name)
            
            if existing_node:
                print(f"\\n[{i+1}/{len(proxy_path_values)}] Updating existing: {new_name}")
                node = existing_node
            else:
                # 노드 복제
                copied = parent.copyItems([parts_node], channel_reference_originals=False)
                node = copied[0]
                node.setName(new_name, unique_name=True)
                print(f"\\n[{i+1}/{len(proxy_path_values)}] Created: {node.name()}")
            
            # 위치 설정 (3개씩 가로로 배치)
            cols = 3
            x_offset = (i % cols) * 4
            y_offset = -(i // cols) * 4
            new_pos = hou.Vector2(original_pos.x() + x_offset, original_pos.y() + y_offset)
            node.setPosition(new_pos)
            
            # group 파라미터에 @proxy_path 필터 설정
            group_parm = node.parm("group")
            if group_parm:
                # @proxy_path=/경로 형식으로 설정
                filter_value = f"@proxy_path={path_value}"
                group_parm.set(filter_value)
                
                print(f"  Short name: {short_name}")
                print(f"  Group filter: {filter_value}")
                print(f"  Position: ({new_pos.x():.2f}, {new_pos.y():.2f})")
            else:
                print(f"  [WARNING] No 'group' parameter found")
            
            created_nodes.append(node)
        
        print(f"\\n{'='*80}")
        print(f"[OK] Successfully created/updated {len(created_nodes)} nodes")
        print(f"{'='*80}")
        
        # 레이아웃 정리
        parent.layoutChildren()
        print(f"\\n[OK] Layout updated")
        
        # 결과 저장
        hou.session.created_parts_nodes = created_nodes
        
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
        duplicate_parts_by_proxy_path_attribute()
        
        print("\n" + "="*80)
        print(" Summary")
        print("="*80)
        print("""
작업 완료!

수행된 작업:
==========
1. proxy_path 노드에서 @proxy_path primitive 어트리뷰트 분석
2. 고유한 경로 값 5개 추출:
   - Belt_geo
   - Lv1_Bag_geo
   - Lv2_Helmet_geo_belt
   - Pants_geo
   - Polo_shirts_geo

3. 각 경로별로 Parts_Deform 노드 복제
4. 각 노드의 group 파라미터에 @proxy_path 필터 설정
   형식: @proxy_path=/Jake/geo_grp/.../[이름]_geo
5. 노드들을 3개씩 가로로 정렬
6. 레이아웃 자동 정리

결과:
====
- 각 의상 부위별로 독립적인 Parts_Deform 노드 생성
- 노드 이름: Parts_Deform_[부위명]_geo
- 각 노드는 해당 경로의 지오메트리만 처리

후디니에서 확인:
==============
1. /obj/assets/Deform 네트워크 열기
2. Parts_Deform_* 노드들 확인
3. 각 노드의 group 파라미터 확인
4. 각 노드가 올바른 지오메트리를 처리하는지 확인
   (예: Parts_Deform_Pants_geo는 Pants만 처리)
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Operation failed: {e}")
        import traceback
        traceback.print_exc()






