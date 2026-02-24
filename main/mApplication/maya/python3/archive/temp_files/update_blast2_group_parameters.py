#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parts_Deform 노드들의 group 파라미터를 blast2 노드에 복사
@proxy_path -> @geo_path로 변경하여 적용
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def update_blast2_group_parameters():
    """Parts_Deform의 group을 blast2에 복사 (@proxy_path -> @geo_path)"""
    print("\n" + "="*80)
    print(" Update blast2 Group Parameters")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Finding all Parts_Deform nodes...")
        print("-"*80)
        
        h.execute("""
import hou

deform_parent = hou.node("/obj/assets/Deform")

if not deform_parent:
    print("[ERROR] /obj/assets/Deform not found")
else:
    # Parts_Deform로 시작하는 모든 노드 찾기
    parts_nodes = [n for n in deform_parent.children() 
                   if n.name().startswith("Parts_Deform")]
    
    print(f"[OK] Found {len(parts_nodes)} Parts_Deform nodes")
    print("-" * 80)
    
    for node in sorted(parts_nodes, key=lambda n: n.name()):
        print(f"  - {node.name()}")
    
    # 세션에 저장
    hou.session.parts_deform_nodes = parts_nodes
""")
        
        print("\n[2] Updating blast2 group parameters...")
        print("-"*80)
        
        result = h.connector.execute_code("""
import hou

parts_nodes = getattr(hou.session, 'parts_deform_nodes', [])

if not parts_nodes:
    print("[ERROR] No Parts_Deform nodes found")
else:
    print(f"Processing {len(parts_nodes)} nodes...")
    print("=" * 80)
    
    success_count = 0
    error_count = 0
    
    for i, parts_node in enumerate(parts_nodes, 1):
        print(f"\\n[{i}/{len(parts_nodes)}] {parts_node.name()}")
        print("-" * 80)
        
        try:
            # Parts_Deform의 group 파라미터 가져오기
            group_parm = parts_node.parm("group")
            
            if not group_parm:
                print(f"  [WARNING] No 'group' parameter found on {parts_node.name()}")
                error_count += 1
                continue
            
            # 현재 group 값
            original_value = group_parm.eval()
            print(f"  Original group: {original_value}")
            
            # @proxy_path를 @geo_path로 변경
            modified_value = original_value.replace("@proxy_path", "@geo_path")
            print(f"  Modified group: {modified_value}")
            
            # blast2 노드 찾기
            blast2_node = parts_node.node("blast2")
            
            if not blast2_node:
                print(f"  [WARNING] blast2 node not found in {parts_node.name()}")
                error_count += 1
                continue
            
            print(f"  [OK] Found blast2: {blast2_node.path()}")
            
            # blast2의 group 파라미터 설정
            blast2_group_parm = blast2_node.parm("group")
            
            if not blast2_group_parm:
                print(f"  [WARNING] No 'group' parameter on blast2")
                error_count += 1
                continue
            
            # 이전 값 확인
            old_blast2_value = blast2_group_parm.eval()
            if old_blast2_value:
                print(f"  Previous blast2 group: {old_blast2_value}")
            
            # 새 값 설정
            blast2_group_parm.set(modified_value)
            
            # 확인
            new_blast2_value = blast2_group_parm.eval()
            print(f"  New blast2 group: {new_blast2_value}")
            
            # 성공 확인
            if new_blast2_value == modified_value:
                print(f"  [OK] Successfully updated!")
                success_count += 1
            else:
                print(f"  [ERROR] Value mismatch!")
                error_count += 1
            
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()
            error_count += 1
    
    # 요약
    print(f"\\n{'='*80}")
    print(f"Summary:")
    print(f"  Total nodes: {len(parts_nodes)}")
    print(f"  Success: {success_count}")
    print(f"  Errors: {error_count}")
    print(f"{'='*80}")
""", print_output=False)
        
        if result:
            print(result['stdout'])
            if result['stderr']:
                print("\n[STDERR]")
                print(result['stderr'])
        
        print("\n[3] Verification - Comparing group parameters...")
        print("-"*80)
        
        h.execute("""
import hou

parts_nodes = getattr(hou.session, 'parts_deform_nodes', [])

if parts_nodes:
    print(f"{'Node Name':<45} | {'Parts_Deform group':<60} | {'blast2 group':<60}")
    print("=" * 170)
    
    for node in sorted(parts_nodes, key=lambda n: n.name()):
        # Parts_Deform의 group
        parts_group_parm = node.parm("group")
        parts_group = parts_group_parm.eval() if parts_group_parm else "N/A"
        
        # blast2의 group
        blast2_node = node.node("blast2")
        if blast2_node:
            blast2_group_parm = blast2_node.parm("group")
            blast2_group = blast2_group_parm.eval() if blast2_group_parm else "N/A"
        else:
            blast2_group = "blast2 not found"
        
        print(f"{node.name():<45} | {parts_group:<60} | {blast2_group:<60}")
        
        # 검증: @proxy_path가 @geo_path로 변경되었는지 확인
        if "@proxy_path" in parts_group and "@geo_path" in blast2_group:
            expected = parts_group.replace("@proxy_path", "@geo_path")
            if blast2_group == expected:
                print(f"{'':>45}   [OK] Correctly mapped")
            else:
                print(f"{'':>45}   [WARNING] Mismatch!")
else:
    print("[ERROR] No nodes to verify")
""")
        
        print("\n" + "="*80)
        print("[OK] Operation completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        update_blast2_group_parameters()
        
        print("\n" + "="*80)
        print(" Summary")
        print("="*80)
        print("""
작업 완료!

수행된 작업:
==========
1. 모든 Parts_Deform_* 노드 찾기
2. 각 Parts_Deform 노드의 group 파라미터 읽기
3. '@proxy_path'를 '@geo_path'로 문자열 변경
4. 각 노드 내부의 blast2 노드 찾기
5. blast2 노드의 group 파라미터에 변경된 값 설정

변경 예시:
=========
Parts_Deform group:  @proxy_path=/Jake/.../Pants_geo
                     ↓ replace
blast2 group:        @geo_path=/Jake/.../Pants_geo

결과:
====
- 각 Parts_Deform 노드의 필터가 blast2로 전달됨
- @proxy_path 어트리뷰트 대신 @geo_path 어트리뷰트 사용
- 각 blast2 노드가 올바른 지오메트리를 필터링

후디니에서 확인:
==============
1. 각 Parts_Deform_* 노드 열기
2. blast2 노드의 group 파라미터 확인
3. @geo_path 필터가 올바르게 설정되었는지 확인
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Operation failed: {e}")
        import traceback
        traceback.print_exc()





