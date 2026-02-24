#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parts_Deform 자동 동기화 콜백 스크립트
sim_filecache의 save_to_disk 버튼 실행 시 호출됨
"""

import hou


def sync_parts_deform_nodes():
    """proxy_path 어트리뷰트와 Parts_Deform 노드 동기화"""
    
    # 1. proxy_path 노드에서 @proxy_path 어트리뷰트 값 추출
    proxy_node = hou.node("/obj/assets/Deform/proxy_path")
    if not proxy_node:
        # proxy_path 노드가 없으면 조용히 종료
        print("Parts_Deform sync skipped: proxy_path node not found")
        return
    
    geo = proxy_node.geometry()
    if not geo:
        # 지오메트리가 없으면 조용히 종료
        print("Parts_Deform sync skipped: No geometry on proxy_path node")
        return
    
    proxy_path_attrib = geo.findPrimAttrib("proxy_path")
    if not proxy_path_attrib:
        # @proxy_path 어트리뷰트가 없으면 조용히 종료
        print("Parts_Deform sync skipped: @proxy_path attribute not found")
        return
    
    # 고유한 경로 추출
    unique_paths = set()
    for prim in geo.prims():
        val = prim.attribValue("proxy_path")
        if val:
            unique_paths.add(val)
    
    unique_paths = sorted(list(unique_paths))
    
    if not unique_paths:
        # @proxy_path 값이 없으면 조용히 종료
        print("Parts_Deform sync skipped: No @proxy_path values found")
        return
    
    # 2. 기존 Parts_Deform 노드 확인
    deform_parent = hou.node("/obj/assets/Deform")
    if not deform_parent:
        # Deform 노드가 없으면 조용히 종료
        print("Parts_Deform sync skipped: /obj/assets/Deform not found")
        return
    
    original_node = deform_parent.node("Parts_Deform")
    if not original_node:
        # Parts_Deform 템플릿 노드가 없으면 조용히 종료
        print("Parts_Deform sync skipped: Parts_Deform template node not found")
        return
    
    # 기존 Parts_Deform_* 노드들 찾기 (원본 제외)
    existing_nodes = {}
    for node in deform_parent.children():
        if node.name().startswith("Parts_Deform_") and node != original_node:
            # group 파라미터에서 경로 추출
            group_parm = node.parm("group")
            if group_parm:
                group_val = group_parm.eval()
                # @proxy_path=/path 형식에서 경로 추출
                if "@proxy_path=" in group_val:
                    path = group_val.replace("@proxy_path=", "")
                    existing_nodes[path] = node
    
    # 3. 필요한 경로 집합과 기존 경로 집합 비교
    required_paths = set(unique_paths)
    current_paths = set(existing_nodes.keys())
    
    # 삭제할 노드들
    to_delete = current_paths - required_paths
    # 생성할 경로들
    to_create = required_paths - current_paths
    # 유지할 경로들
    to_keep = required_paths & current_paths
    
    # 4. 작업 수행
    deleted_count = 0
    created_count = 0
    updated_count = 0
    
    # 불필요한 노드 삭제
    for path in to_delete:
        node = existing_nodes[path]
        node_name = node.name()
        node.destroy()
        deleted_count += 1
        print("Deleted: {} (path not in @proxy_path)".format(node_name))
    
    # 유지되는 노드 업데이트 (blast2 group 파라미터 갱신)
    for path in to_keep:
        node = existing_nodes[path]
        
        # blast2 group 파라미터 업데이트
        blast2_node = node.node("blast2")
        if blast2_node:
            blast2_group_parm = blast2_node.parm("group")
            if blast2_group_parm:
                modified_value = "@geo_path={}".format(path)
                blast2_group_parm.set(modified_value)
                updated_count += 1
                print("Updated: {}".format(node.name()))
    
    # 새 노드 생성
    for i, path in enumerate(sorted(to_create)):
        # 경로에서 이름 추출
        short_name = path.split('/')[-1]
        new_name = "Parts_Deform_{}".format(short_name)
        
        # 노드 복제
        copied = deform_parent.copyItems([original_node], channel_reference_originals=False)
        node = copied[0]
        node.setName(new_name, unique_name=True)
        
        # 위치 설정
        original_pos = original_node.position()
        cols = 3
        existing_count = len(to_keep) + i
        x_offset = (existing_count % cols) * 4
        y_offset = -(existing_count // cols) * 4
        new_pos = hou.Vector2(original_pos.x() + x_offset, original_pos.y() + y_offset)
        node.setPosition(new_pos)
        
        # group 파라미터 설정
        group_parm = node.parm("group")
        if group_parm:
            filter_value = "@proxy_path={}".format(path)
            group_parm.set(filter_value)
        
        # blast2 group 파라미터 설정
        blast2_node = node.node("blast2")
        if blast2_node:
            blast2_group_parm = blast2_node.parm("group")
            if blast2_group_parm:
                modified_value = "@geo_path={}".format(path)
                blast2_group_parm.set(modified_value)
        
        created_count += 1
        print("Created: {}".format(node.name()))
    
    # 레이아웃 정리
    if deleted_count > 0 or created_count > 0:
        deform_parent.layoutChildren()
    
    # 결과 메시지
    message_parts = [
        "Parts_Deform Sync Complete:",
        "",
        "- Created: {}".format(created_count),
        "- Updated: {}".format(updated_count),
        "- Deleted: {}".format(deleted_count),
        "- Kept: {}".format(len(to_keep)),
        "",
        "Total @proxy_path values: {}".format(len(unique_paths))
    ]
    message = "\n".join(message_parts)
    
    print("\n" + "="*60)
    print(message)
    print("="*60)
    
    hou.ui.displayMessage(message, 
                         severity=hou.severityType.Message, 
                         title="Parts_Deform Sync")


# 메인 실행
if __name__ == "__main__":
    try:
        sync_parts_deform_nodes()
    except Exception as e:
        import traceback
        error_msg = "Error syncing Parts_Deform nodes:\n\n{}\n\n{}".format(
            str(e), traceback.format_exc())
        print(error_msg)
        hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)

