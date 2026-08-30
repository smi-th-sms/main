#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parts_Deform 동기화 수동 테스트
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def test_manual_sync():
    """동기화 수동 실행 테스트"""
    print("\n" + "="*80)
    print(" Manual Sync Test")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Executing sync function...")
        print("-"*80)
        
        # UI 메시지를 표시하지 않는 버전으로 실행
        result = h.connector.execute_code("""
import hou
import sys

# 경로 추가
if r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3" not in sys.path:
    sys.path.append(r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3")

# 모듈 임포트
import parts_deform_sync_callback

# proxy_path 노드에서 @proxy_path 어트리뷰트 값 추출
proxy_node = hou.node("/obj/assets/Deform/proxy_path")
if not proxy_node:
    print("[ERROR] proxy_path node not found")
else:
    geo = proxy_node.geometry()
    if geo:
        proxy_path_attrib = geo.findPrimAttrib("proxy_path")
        if proxy_path_attrib:
            # 고유한 경로 추출
            unique_paths = set()
            for prim in geo.prims():
                val = prim.attribValue("proxy_path")
                if val:
                    unique_paths.add(val)
            
            unique_paths = sorted(list(unique_paths))
            
            print("[CURRENT @proxy_path VALUES]")
            print("=" * 60)
            for i, path in enumerate(unique_paths, 1):
                short_name = path.split('/')[-1]
                print("  {}. {}".format(i, short_name))
                print("     {}".format(path))
            print("")
            
            # 기존 Parts_Deform 노드 확인
            deform_parent = hou.node("/obj/assets/Deform")
            if deform_parent:
                existing_nodes = {}
                for node in deform_parent.children():
                    if node.name().startswith("Parts_Deform_"):
                        group_parm = node.parm("group")
                        if group_parm:
                            group_val = group_parm.eval()
                            if "@proxy_path=" in group_val:
                                path = group_val.replace("@proxy_path=", "")
                                existing_nodes[path] = node
                
                print("[EXISTING Parts_Deform NODES]")
                print("=" * 60)
                if existing_nodes:
                    for path, node in sorted(existing_nodes.items(), key=lambda x: x[1].name()):
                        short_name = path.split('/')[-1]
                        print("  - {} -> {}".format(node.name(), short_name))
                else:
                    print("  (none)")
                print("")
                
                # 비교
                required_paths = set(unique_paths)
                current_paths = set(existing_nodes.keys())
                
                to_delete = current_paths - required_paths
                to_create = required_paths - current_paths
                to_keep = required_paths & current_paths
                
                print("[SYNC PLAN]")
                print("=" * 60)
                print("  To Create: {}".format(len(to_create)))
                if to_create:
                    for path in sorted(to_create):
                        print("    + {}".format(path.split('/')[-1]))
                
                print("")
                print("  To Keep: {}".format(len(to_keep)))
                if to_keep:
                    for path in sorted(to_keep):
                        print("    = {}".format(path.split('/')[-1]))
                
                print("")
                print("  To Delete: {}".format(len(to_delete)))
                if to_delete:
                    for path in sorted(to_delete):
                        node_name = existing_nodes[path].name()
                        print("    - {}".format(node_name))
                
                print("")
                print("=" * 60)
                print("[EXECUTING SYNC...]")
                print("=" * 60)
                
                # 실제 동기화 실행 (UI 메시지 없이)
                deleted_count = 0
                created_count = 0
                updated_count = 0
                
                original_node = deform_parent.node("Parts_Deform")
                
                if original_node:
                    # 삭제
                    for path in to_delete:
                        node = existing_nodes[path]
                        node_name = node.name()
                        node.destroy()
                        deleted_count += 1
                        print("[DELETE] {}".format(node_name))
                    
                    # 유지 및 업데이트
                    for path in to_keep:
                        node = existing_nodes[path]
                        blast2_node = node.node("blast2")
                        if blast2_node:
                            blast2_group_parm = blast2_node.parm("group")
                            if blast2_group_parm:
                                modified_value = "@geo_path={}".format(path)
                                blast2_group_parm.set(modified_value)
                                updated_count += 1
                                print("[UPDATE] {}".format(node.name()))
                    
                    # 생성
                    for i, path in enumerate(sorted(to_create)):
                        short_name = path.split('/')[-1]
                        new_name = "Parts_Deform_{}".format(short_name)
                        
                        copied = deform_parent.copyItems([original_node], channel_reference_originals=False)
                        node = copied[0]
                        node.setName(new_name, unique_name=True)
                        
                        # 위치
                        original_pos = original_node.position()
                        cols = 3
                        existing_count = len(to_keep) + i
                        x_offset = (existing_count % cols) * 4
                        y_offset = -(existing_count // cols) * 4
                        new_pos = hou.Vector2(original_pos.x() + x_offset, original_pos.y() + y_offset)
                        node.setPosition(new_pos)
                        
                        # group 파라미터
                        group_parm = node.parm("group")
                        if group_parm:
                            filter_value = "@proxy_path={}".format(path)
                            group_parm.set(filter_value)
                        
                        # blast2 group 파라미터
                        blast2_node = node.node("blast2")
                        if blast2_node:
                            blast2_group_parm = blast2_node.parm("group")
                            if blast2_group_parm:
                                modified_value = "@geo_path={}".format(path)
                                blast2_group_parm.set(modified_value)
                        
                        created_count += 1
                        print("[CREATE] {}".format(node.name()))
                    
                    # 레이아웃
                    if deleted_count > 0 or created_count > 0:
                        deform_parent.layoutChildren()
                        print("[LAYOUT] Updated")
                    
                    print("")
                    print("=" * 60)
                    print("[RESULT]")
                    print("  Created: {}".format(created_count))
                    print("  Updated: {}".format(updated_count))
                    print("  Deleted: {}".format(deleted_count))
                    print("  Total: {}".format(len(unique_paths)))
                    print("=" * 60)
                else:
                    print("[ERROR] Original Parts_Deform node not found")
""", print_output=False)
        
        if result and result.get('stdout'):
            try:
                print(result['stdout'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[OK] Sync completed (output contains non-ascii)")
        
        if result and result.get('stderr'):
            print("\n[STDERR]")
            try:
                print(result['stderr'].encode('ascii', errors='ignore').decode('ascii'))
            except:
                print("[Error output]")
        
        print("\n" + "="*80)
        print("[OK] Manual sync test completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        test_manual_sync()
        
    except Exception as e:
        print("\n[ERROR] Test failed: {}".format(e))
        import traceback
        traceback.print_exc()

