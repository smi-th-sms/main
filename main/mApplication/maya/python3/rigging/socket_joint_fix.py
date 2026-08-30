# -*- coding: utf-8 -*-
"""
Socket Joint Fix Tool
local_socket, world_socket 조인트 수정 도구

사용법:
import socket_joint_fix
socket_joint_fix.run()
"""

import maya.cmds as cmds


def delete_constraints_on_object(obj_name):
    """오브젝트에 연결된 모든 constraint 삭제"""
    if not cmds.objExists(obj_name):
        return
    
    constraint_types = ["pointConstraint", "orientConstraint", "parentConstraint"]
    
    # 방법 1: listConnections로 찾기
    for const_type in constraint_types:
        connections = cmds.listConnections(obj_name, type=const_type)
        if connections:
            for const in list(set(connections)):
                if cmds.objExists(const):
                    try:
                        cmds.delete(const)
                        print(f"  🗑️ 삭제: {const}")
                    except:
                        pass
    
    # 방법 2: 자식 노드에서 constraint 찾기
    children = cmds.listRelatives(obj_name, children=True, fullPath=True) or []
    for child in children:
        if cmds.objExists(child):
            node_type = cmds.nodeType(child)
            if node_type in constraint_types:
                try:
                    cmds.delete(child)
                    print(f"  🗑️ 삭제 (자식): {child}")
                except:
                    pass
    
    # 방법 3: 이름 패턴으로 찾기 (obj_name_*Constraint*)
    pattern_constraints = cmds.ls(f"{obj_name}*Constraint*", type="constraint") or []
    for const in pattern_constraints:
        if cmds.objExists(const):
            try:
                cmds.delete(const)
                print(f"  🗑️ 삭제 (패턴): {const}")
            except:
                pass


def cleanup_existing():
    """기존에 생성된 것들 정리 (삭제)"""
    print("\n🧹 기존 설정 정리 중...")
    
    # 1. 먼저 모든 constraint 삭제 (순서 중요!)
    objects_to_clean = [
        "local_socket",
        "local_socket_target",
        "chest_M_target",
        "camera_socket",
        "camera_center_ctl_grp"
    ]
    
    for obj in objects_to_clean:
        delete_constraints_on_object(obj)
    
    # 2. multiplyDivide 노드 삭제
    md_nodes = ["md_local_cns_value", "md_world_cns_value", "md_chest_cns_value"]
    for md in md_nodes:
        if cmds.objExists(md):
            try:
                cmds.delete(md)
                print(f"  🗑️ 삭제: {md}")
            except:
                pass
    
    # 3. 컨트롤러 그룹 삭제 (constraint 삭제 후!)
    if cmds.objExists("camera_center_ctl_grp1"):
        try:
            cmds.delete("camera_center_ctl_grp1")
            print(f"  🗑️ 삭제: camera_center_ctl_grp1")
        except:
            pass
    
    # 4. local_socket_target 조인트 삭제 (constraint 삭제 후!)
    if cmds.objExists("local_socket_target"):
        # 혹시 남아있는 constraint 한 번 더 삭제
        delete_constraints_on_object("local_socket_target")
        
        # 직접 이름으로 constraint 삭제 시도
        direct_constraints = [
            "local_socket_target_pointConstraint1",
            "local_socket_target_orientConstraint1",
            "local_socket_target_parentConstraint1"
        ]
        for const in direct_constraints:
            if cmds.objExists(const):
                try:
                    cmds.delete(const)
                    print(f"  🗑️ 직접 삭제: {const}")
                except:
                    pass
        
        # 자식 노드 전부 삭제 후 조인트 삭제
        children = cmds.listRelatives("local_socket_target", children=True, fullPath=True) or []
        for child in children:
            if cmds.objExists(child):
                try:
                    cmds.delete(child)
                    print(f"  🗑️ 자식 삭제: {child}")
                except:
                    pass
        
        try:
            cmds.delete("local_socket_target")
            print(f"  🗑️ 삭제: local_socket_target")
        except:
            pass
    
    # 5. chest_M_target 조인트 삭제
    if cmds.objExists("chest_M_target"):
        delete_constraints_on_object("chest_M_target")
        try:
            cmds.delete("chest_M_target")
            print(f"  🗑️ 삭제: chest_M_target")
        except:
            pass
    
    # 6. camera_socket 조인트 삭제
    if cmds.objExists("camera_socket"):
        try:
            cmds.delete("camera_socket")
            print(f"  🗑️ 삭제: camera_socket")
        except:
            pass
    
    # 마지막으로 ls로 찾아서 강제 삭제
    # local_socket_target 관련 constraint 모두 찾기
    found_constraints = cmds.ls("*local_socket_target*Constraint*", long=True) or []
    for item in found_constraints:
        if cmds.objExists(item):
            try:
                # 연결 끊기
                disconnect_all_connections(item)
                # 잠금 해제
                cmds.lockNode(item, lock=False)
                cmds.delete(item)
                print(f"  🗑️ 최종 삭제: {item}")
            except Exception as e:
                print(f"  ⚠️ 삭제 실패: {item} - {e}")
    
    # local_socket_target 다시 한번 삭제 시도
    found_targets = cmds.ls("*local_socket_target", long=True) or []
    for item in found_targets:
        if cmds.objExists(item):
            try:
                # 연결 끊기
                disconnect_all_connections(item)
                # 잠금 해제
                cmds.lockNode(item, lock=False)
                cmds.delete(item)
                print(f"  🗑️ 최종 삭제: {item}")
            except Exception as e:
                print(f"  ⚠️ 삭제 실패: {item} - {e}")
    
    print("  ✅ 정리 완료!\n")


def disconnect_all_connections(joint_name):
    """조인트의 모든 커넥션을 끊음 (incoming 위주)"""
    if not cmds.objExists(joint_name):
        print(f"⚠️ {joint_name} 존재하지 않음. 스킵.")
        return False
    
    disconnected_count = 0
    
    # 조인트의 모든 어트리뷰트 가져오기
    attrs = cmds.listAttr(joint_name, connectable=True) or []
    
    for attr in attrs:
        full_attr = f"{joint_name}.{attr}"
        
        try:
            # incoming connection 확인
            incoming = cmds.listConnections(full_attr, source=True, destination=False, plugs=True)
            if incoming:
                for src in incoming:
                    try:
                        cmds.disconnectAttr(src, full_attr)
                        print(f"  ✂️ 끊음: {src} → {full_attr}")
                        disconnected_count += 1
                    except:
                        pass
            
            # outgoing connection도 끊기
            outgoing = cmds.listConnections(full_attr, source=False, destination=True, plugs=True)
            if outgoing:
                for dest in outgoing:
                    try:
                        cmds.disconnectAttr(full_attr, dest)
                        print(f"  ✂️ 끊음: {full_attr} → {dest}")
                        disconnected_count += 1
                    except:
                        pass
        except:
            pass
    
    print(f"  총 {disconnected_count}개 커넥션 끊음")
    return True


def unlock_attributes(joint_name):
    """조인트의 transform 관련 어트리뷰트 잠금 해제"""
    if not cmds.objExists(joint_name):
        return False
    
    attrs_to_unlock = [
        'translateX', 'translateY', 'translateZ',
        'rotateX', 'rotateY', 'rotateZ',
        'jointOrientX', 'jointOrientY', 'jointOrientZ'
    ]
    
    for attr in attrs_to_unlock:
        full_attr = f"{joint_name}.{attr}"
        try:
            if cmds.objExists(full_attr):
                cmds.setAttr(full_attr, lock=False)
        except:
            pass
    
    print(f"  🔓 어트리뷰트 잠금 해제")
    return True


def set_rotation_zero(joint_name):
    """조인트의 rotation 값을 0, 0, 0으로 설정"""
    if not cmds.objExists(joint_name):
        return False
    
    try:
        cmds.setAttr(f"{joint_name}.rotateX", 0)
        cmds.setAttr(f"{joint_name}.rotateY", 0)
        cmds.setAttr(f"{joint_name}.rotateZ", 0)
        print(f"  ✅ Rotation → (0, 0, 0)")
        return True
    except Exception as e:
        print(f"  ❌ Rotation 설정 실패: {e}")
        return False


def match_position(source_joint, target_joint):
    """source_joint의 위치를 target_joint와 동일하게 맞춤"""
    if not cmds.objExists(source_joint):
        print(f"  ⚠️ {source_joint} 존재하지 않음")
        return False
    
    if not cmds.objExists(target_joint):
        print(f"  ⚠️ {target_joint} 존재하지 않음")
        return False
    
    try:
        # 타겟의 월드 위치 가져오기
        pos = cmds.xform(target_joint, query=True, worldSpace=True, translation=True)
        
        # 소스에 위치 적용
        cmds.xform(source_joint, worldSpace=True, translation=pos)
        print(f"  ✅ 위치 맞춤: {source_joint} → {target_joint} ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")
        return True
    except Exception as e:
        print(f"  ❌ 위치 맞춤 실패: {e}")
        return False


def set_joint_orient(joint_name, orient_x, orient_y, orient_z):
    """조인트의 Joint Orient 값 설정"""
    if not cmds.objExists(joint_name):
        return False
    
    try:
        cmds.setAttr(f"{joint_name}.jointOrientX", orient_x)
        cmds.setAttr(f"{joint_name}.jointOrientY", orient_y)
        cmds.setAttr(f"{joint_name}.jointOrientZ", orient_z)
        print(f"  ✅ Joint Orient → ({orient_x}, {orient_y}, {orient_z})")
        return True
    except Exception as e:
        print(f"  ❌ Joint Orient 설정 실패: {e}")
        return False


def import_socket_controllers():
    """컨트롤러 파일 임포트"""
    file_path = "Z:/show/CORND/sequences/RND/YONGJIN_0000/RND/wip/maya/data/camera_ctl_temp.ma"
    
    # 기존 컨트롤러 있으면 삭제 후 재임포트
    if cmds.objExists("camera_center_ctl_grp1"):
        delete_constraints_on_object("camera_center_ctl_grp")
        cmds.delete("camera_center_ctl_grp1")
        print(f"  🗑️ 기존 컨트롤러 삭제: camera_center_ctl_grp1")
    
    # 파일 존재 확인
    import os
    if not os.path.exists(file_path):
        print(f"  ❌ 파일을 찾을 수 없습니다: {file_path}")
        return False
    
    try:
        # 파일 임포트
        cmds.file(file_path, i=True, type="mayaAscii", 
                 ignoreVersion=True, mergeNamespacesOnClash=False,
                 namespace=":", options="v=0;", preserveReferences=True)
        
        print(f"  ✅ 컨트롤러 임포트 완료: {file_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ 컨트롤러 임포트 실패: {e}")
        return False


def add_chest_ori_attribute():
    """camera_socket_ctl에 Chest_ori_cns_value 어트리뷰트 추가"""
    ctrl = "camera_socket_ctl"
    attr_name = "Chest_ori_cns_value"
    
    if not cmds.objExists(ctrl):
        print(f"  ❌ {ctrl} 존재하지 않음")
        return False
    
    # 이미 어트리뷰트가 있으면 삭제 후 재생성
    if cmds.attributeQuery(attr_name, node=ctrl, exists=True):
        cmds.deleteAttr(f"{ctrl}.{attr_name}")
        print(f"  🗑️ 기존 어트리뷰트 삭제: {attr_name}")
    
    try:
        # 어트리뷰트 추가 (0-10 범위, 기본값 10)
        cmds.addAttr(ctrl, longName=attr_name, attributeType="float", 
                    min=0, max=10, defaultValue=10, keyable=True)
        cmds.setAttr(f"{ctrl}.{attr_name}", 10)
        print(f"  ✅ 어트리뷰트 추가: {ctrl}.{attr_name} (기본값 10)")
        return True
        
    except Exception as e:
        print(f"  ❌ 어트리뷰트 추가 실패: {e}")
        return False


def connect_chest_ori_constraint():
    """Chest_ori_cns_value를 chest_M_target Orient Constraint의 2개 weight에 연결
    - 10일 때: Chest_M 따라감 (weight 1), local_socket_target 안 따라감 (weight 0)
    - 0일 때: Chest_M 안 따라감 (weight 0), local_socket_target 따라감 (weight 1)
    """
    ctrl = "camera_socket_ctl"
    attr_name = "Chest_ori_cns_value"
    orient_const = "chest_M_target_orientConstraint1"
    
    if not cmds.objExists(ctrl):
        print(f"  ❌ {ctrl} 존재하지 않음")
        return False
    
    if not cmds.objExists(orient_const):
        print(f"  ❌ {orient_const} 존재하지 않음")
        return False
    
    # 기존 노드들 삭제
    nodes_to_delete = ["md_Chest_ori_cns_value", "reverse_Chest_ori_cns_value"]
    for node in nodes_to_delete:
        if cmds.objExists(node):
            cmds.delete(node)
            print(f"  🗑️ 기존 노드 삭제: {node}")
    
    try:
        # Orient Constraint의 weight alias 가져오기
        weight_aliases = cmds.orientConstraint(orient_const, query=True, weightAliasList=True)
        if not weight_aliases or len(weight_aliases) < 2:
            print(f"  ❌ {orient_const}에 weight alias가 2개 미만")
            return False
        
        # weight aliases (Chest_M, local_socket_target)
        chest_weight = weight_aliases[0]  # Chest_M
        local_weight = weight_aliases[1]  # local_socket_target
        
        print(f"  📌 Weight Aliases: {weight_aliases}")
        
        # multiplyDivide 노드 생성 (0-10 → 0-1 변환)
        md_node = cmds.createNode("multiplyDivide", name="md_Chest_ori_cns_value")
        cmds.setAttr(f"{md_node}.operation", 2)  # Divide
        cmds.setAttr(f"{md_node}.input2X", 10)   # 10으로 나누기
        
        # reverse 노드 생성 (1에서 빼기)
        reverse_node = cmds.createNode("reverse", name="reverse_Chest_ori_cns_value")
        
        # 연결 설정
        # ctrl attr → multiplyDivide
        cmds.connectAttr(f"{ctrl}.{attr_name}", f"{md_node}.input1X", force=True)
        
        # multiplyDivide → Chest_M weight (10일 때 1)
        cmds.connectAttr(f"{md_node}.outputX", f"{orient_const}.{chest_weight}", force=True)
        
        # multiplyDivide → reverse → local_socket_target weight (10일 때 0, 0일 때 1)
        cmds.connectAttr(f"{md_node}.outputX", f"{reverse_node}.inputX", force=True)
        cmds.connectAttr(f"{reverse_node}.outputX", f"{orient_const}.{local_weight}", force=True)
        
        print(f"  ✅ 연결: {ctrl}.{attr_name} → {md_node} (÷10) → {chest_weight}")
        print(f"  ✅ 연결: {md_node} → {reverse_node} (반전) → {local_weight}")
        return True
        
    except Exception as e:
        print(f"  ❌ 연결 실패: {e}")
        return False


def position_single_controller(ctrl_grp, target_joint):
    """단일 컨트롤러 그룹을 조인트 위치로 이동 (임시 constraint 방식)"""
    
    if not cmds.objExists(ctrl_grp):
        print(f"  ⚠️ {ctrl_grp} 존재하지 않음. 스킵.")
        return False
    
    if not cmds.objExists(target_joint):
        print(f"  ⚠️ {target_joint} 존재하지 않음. 스킵.")
        return False
    
    try:
        # 임시 Parent Constraint로 위치/회전 맞추기
        temp_const = cmds.parentConstraint(target_joint, ctrl_grp, maintainOffset=False)[0]
        
        # constraint 삭제 (위치는 유지됨)
        cmds.delete(temp_const)
        
        print(f"  ✅ {ctrl_grp} → {target_joint} 위치/회전 맞춤")
        return True
        
    except Exception as e:
        print(f"  ❌ {ctrl_grp} 위치 설정 실패: {e}")
        return False


def setup_camera_socket_constraint():
    """camera_socket 조인트가 camera_socket_ctl을 따라가도록 Parent Constraint 설정"""
    driver = "camera_socket_ctl"
    driven = "camera_socket"
    
    if not cmds.objExists(driver):
        print(f"  ❌ {driver} 존재하지 않음")
        return False
    
    if not cmds.objExists(driven):
        print(f"  ❌ {driven} 존재하지 않음")
        return False
    
    # 기존 constraint 있으면 삭제 후 재생성
    existing = cmds.listConnections(driven, type="parentConstraint")
    if existing:
        for const in existing:
            if cmds.objExists(const):
                cmds.delete(const)
                print(f"  🗑️ 기존 Parent Constraint 삭제: {const}")
    
    try:
        # Parent Constraint (maintainOffset=True로 현재 위치 유지)
        parent_const = cmds.parentConstraint(driver, driven, maintainOffset=True)
        print(f"  ✅ Parent Constraint 생성: {driver} → {driven}")
        return True
        
    except Exception as e:
        print(f"  ❌ Parent Constraint 설정 실패: {e}")
        return False


def setup_camera_center_constraint():
    """camera_center_ctl_grp에 3개 타겟(local_socket, world_socket, chest_M_target)으로 Parent Constraint 설정"""
    targets = ["local_socket", "world_socket", "chest_M_target"]
    driven = "camera_center_ctl_grp"
    
    if not cmds.objExists(driven):
        print(f"  ❌ {driven} 존재하지 않음")
        return False
    
    # 기존 constraint 있으면 삭제 후 재생성
    existing = cmds.listConnections(driven, type="parentConstraint")
    if existing:
        for const in existing:
            if cmds.objExists(const):
                cmds.delete(const)
                print(f"  🗑️ 기존 Parent Constraint 삭제: {const}")
    
    # 타겟 존재 확인
    valid_targets = []
    for target in targets:
        if cmds.objExists(target):
            valid_targets.append(target)
        else:
            print(f"  ⚠️ {target} 존재하지 않음. 스킵.")
    
    if not valid_targets:
        print(f"  ❌ 유효한 타겟이 없음")
        return False
    
    try:
        # 3개 타겟으로 Parent Constraint
        parent_const = cmds.parentConstraint(valid_targets, driven, maintainOffset=True)
        print(f"  ✅ Parent Constraint 생성: {valid_targets} → {driven}")
        return True
        
    except Exception as e:
        print(f"  ❌ Parent Constraint 설정 실패: {e}")
        return False


def parent_to_motion_system():
    """camera_center_ctl_grp1을 MotionSystem 하위로 이동"""
    child = "camera_center_ctl_grp1"
    parent = "MotionSystem"
    
    if not cmds.objExists(child):
        print(f"  ❌ {child} 존재하지 않음")
        return False
    
    if not cmds.objExists(parent):
        print(f"  ❌ {parent} 존재하지 않음")
        return False
    
    # 이미 MotionSystem 하위에 있는지 체크
    current_parent = cmds.listRelatives(child, parent=True)
    if current_parent and current_parent[0] == parent:
        print(f"  ⚠️ {child}이 이미 {parent} 하위에 있음. 스킵.")
        return True
    
    try:
        cmds.parent(child, parent)
        print(f"  ✅ {child} → {parent} 하위로 이동 완료")
        return True
        
    except Exception as e:
        print(f"  ❌ Parent 설정 실패: {e}")
        return False


def connect_constraint_weights():
    """camera_socket_ctl의 어트리뷰트를 camera_center_ctl_grp의 Parent Constraint weight에 연결
    (0-10 범위를 0-1로 변환하여 연결)"""
    ctrl = "camera_socket_ctl"
    driven = "camera_center_ctl_grp"
    
    if not cmds.objExists(ctrl):
        print(f"  ❌ {ctrl} 존재하지 않음")
        return False
    
    # 기존 multiplyDivide 노드 있으면 삭제 후 재생성
    md_nodes = ["md_local_cns_value", "md_world_cns_value", "md_chest_cns_value"]
    for md in md_nodes:
        if cmds.objExists(md):
            cmds.delete(md)
            print(f"  🗑️ 기존 md 노드 삭제: {md}")
    
    # Parent Constraint 찾기
    constraints = cmds.listConnections(driven, type="parentConstraint")
    if not constraints:
        print(f"  ❌ {driven}에 Parent Constraint 없음")
        return False
    
    parent_const = constraints[0]
    print(f"  📌 Parent Constraint: {parent_const}")
    
    # Constraint의 weight alias 목록 가져오기
    weight_aliases = cmds.parentConstraint(parent_const, query=True, weightAliasList=True)
    print(f"  📌 Weight Aliases: {weight_aliases}")
    
    # 연결 정의: (컨트롤러 어트리뷰트, 타겟 키워드)
    # 타겟 키워드로 weight alias에서 매칭
    attr_mapping = [
        ("local_cns_value", "local"),
        ("world_cns_value", "world"),
        ("chest_cns_value", "Chest"),
    ]
    
    for ctrl_attr, keyword in attr_mapping:
        src = f"{ctrl}.{ctrl_attr}"
        
        if not cmds.objExists(src):
            print(f"  ⚠️ {src} 존재하지 않음. 스킵.")
            continue
        
        # 키워드로 매칭되는 weight alias 찾기
        matched_alias = None
        for alias in weight_aliases:
            if keyword.lower() in alias.lower():
                matched_alias = alias
                break
        
        if not matched_alias:
            print(f"  ⚠️ '{keyword}' 매칭되는 weight alias 없음. 스킵.")
            continue
        
        const_attr = f"{parent_const}.{matched_alias}"
        
        try:
            # multiplyDivide 노드 생성 (0-10 → 0-1 변환)
            md_node = cmds.createNode("multiplyDivide", name=f"md_{ctrl_attr}")
            cmds.setAttr(f"{md_node}.operation", 2)  # Divide
            cmds.setAttr(f"{md_node}.input2X", 10)   # 10으로 나누기
            
            # 연결: ctrl attr → multiplyDivide → constraint weight
            cmds.connectAttr(src, f"{md_node}.input1X", force=True)
            cmds.connectAttr(f"{md_node}.outputX", const_attr, force=True)
            
            print(f"  ✅ 연결: {src} → {md_node} (÷10) → {const_attr}")
        except Exception as e:
            print(f"  ❌ 연결 실패: {src} → {const_attr}: {e}")


def create_local_socket_target():
    """local_socket을 복사해서 local_socket_target 생성 후 RootX_M 하위로 이동"""
    source_joint = "local_socket"
    new_joint_name = "local_socket_target"
    parent_joint = "RootX_M"
    
    # 기존에 존재하면 삭제 후 재생성
    if cmds.objExists(new_joint_name):
        delete_constraints_on_object(new_joint_name)
        cmds.delete(new_joint_name)
        print(f"  🗑️ 기존 {new_joint_name} 삭제")
    
    if not cmds.objExists(source_joint):
        print(f"  ❌ {source_joint} 존재하지 않음")
        return False
    
    if not cmds.objExists(parent_joint):
        print(f"  ❌ {parent_joint} 존재하지 않음")
        return False
    
    try:
        # local_socket 복사
        cmds.select(source_joint, replace=True)
        duplicated = cmds.duplicate(name=new_joint_name, parentOnly=True)[0]
        
        # RootX_M 하위로 이동
        cmds.parent(duplicated, parent_joint)
        
        print(f"  ✅ {new_joint_name} 생성 완료 (→ {parent_joint} 하위)")
        cmds.select(clear=True)
        return True
        
    except Exception as e:
        print(f"  ❌ {new_joint_name} 생성 실패: {e}")
        return False


def create_chest_M_target():
    """local_socket_target을 복사해서 chest_M_target 생성 후 RootX_M 하위로 이동"""
    source_joint = "local_socket_target"
    new_joint_name = "chest_M_target"
    parent_joint = "RootX_M"
    
    # 기존에 존재하면 삭제 후 재생성
    if cmds.objExists(new_joint_name):
        delete_constraints_on_object(new_joint_name)
        cmds.delete(new_joint_name)
        print(f"  🗑️ 기존 {new_joint_name} 삭제")
    
    if not cmds.objExists(source_joint):
        print(f"  ❌ {source_joint} 존재하지 않음")
        return False
    
    if not cmds.objExists(parent_joint):
        print(f"  ❌ {parent_joint} 존재하지 않음")
        return False
    
    try:
        # local_socket_target 복사
        cmds.select(source_joint, replace=True)
        duplicated = cmds.duplicate(name=new_joint_name, parentOnly=True)[0]
        
        # RootX_M 하위로 이동
        cmds.parent(duplicated, parent_joint)
        
        print(f"  ✅ {new_joint_name} 생성 완료 (→ {parent_joint} 하위)")
        cmds.select(clear=True)
        return True
        
    except Exception as e:
        print(f"  ❌ {new_joint_name} 생성 실패: {e}")
        return False


def setup_chest_M_target_constraint():
    """chest_M_target에 Point(Chest_M) + Orient(Chest_M, local_socket_target 2타겟) constraint 설정"""
    source = "chest_M_target"
    point_target = "Chest_M"
    orient_targets = ["Chest_M", "local_socket_target"]
    
    if not cmds.objExists(source):
        print(f"  ❌ {source} 존재하지 않음")
        return False
    
    if not cmds.objExists(point_target):
        print(f"  ❌ {point_target} 존재하지 않음")
        return False
    
    # 기존 constraint 있으면 삭제 후 재생성
    existing_point = cmds.listConnections(source, type="pointConstraint")
    existing_orient = cmds.listConnections(source, type="orientConstraint")
    if existing_point:
        for const in existing_point:
            if cmds.objExists(const):
                cmds.delete(const)
                print(f"  🗑️ 기존 Point Constraint 삭제: {const}")
    if existing_orient:
        for const in existing_orient:
            if cmds.objExists(const):
                cmds.delete(const)
                print(f"  🗑️ 기존 Orient Constraint 삭제: {const}")
    
    # Orient 타겟 존재 확인
    valid_orient_targets = []
    for target in orient_targets:
        if cmds.objExists(target):
            valid_orient_targets.append(target)
        else:
            print(f"  ⚠️ {target} 존재하지 않음. Orient 타겟에서 제외.")
    
    try:
        # Point Constraint (Chest_M만)
        point_const = cmds.pointConstraint(point_target, source, maintainOffset=False)
        print(f"  ✅ Point Constraint 생성: {point_target} → {source}")
        
        # Orient Constraint (2타겟: Chest_M, local_socket_target)
        orient_const = cmds.orientConstraint(valid_orient_targets, source, maintainOffset=False)
        print(f"  ✅ Orient Constraint 생성: {valid_orient_targets} → {source}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Constraint 설정 실패: {e}")
        return False


def setup_local_socket_target_constraint():
    """local_socket_target에 Pelvis_M을 따라가는 constraint 설정"""
    source = "local_socket_target"
    target = "Pelvis_M"
    
    if not cmds.objExists(source):
        print(f"  ❌ {source} 존재하지 않음")
        return False
    
    if not cmds.objExists(target):
        print(f"  ❌ {target} 존재하지 않음")
        return False
    
    # 기존 constraint 있으면 삭제 후 재생성
    existing_point = cmds.listConnections(source, type="pointConstraint")
    existing_orient = cmds.listConnections(source, type="orientConstraint")
    if existing_point:
        for const in existing_point:
            if cmds.objExists(const):
                cmds.delete(const)
                print(f"  🗑️ 기존 Point Constraint 삭제: {const}")
    if existing_orient:
        for const in existing_orient:
            if cmds.objExists(const):
                cmds.delete(const)
                print(f"  🗑️ 기존 Orient Constraint 삭제: {const}")
    
    try:
        # Point Constraint (Translation 전체 따라감)
        point_const = cmds.pointConstraint(target, source, maintainOffset=False)
        print(f"  ✅ Point Constraint 생성: {target} → {source}")
        
        # Orient Constraint (X축만 따라감, Y/Z는 skip)
        orient_const = cmds.orientConstraint(target, source, maintainOffset=False, skip=["y", "z"])
        print(f"  ✅ Orient Constraint 생성 (X축만): {target} → {source}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Constraint 설정 실패: {e}")
        return False


def setup_local_socket_constraint():
    """local_socket에 local_socket_target을 따라가는 constraint 설정"""
    source = "local_socket"
    target = "local_socket_target"
    
    if not cmds.objExists(source):
        print(f"  ❌ {source} 존재하지 않음")
        return False
    
    if not cmds.objExists(target):
        print(f"  ❌ {target} 존재하지 않음")
        return False
    
    # 기존 constraint 있으면 삭제 후 재생성
    existing_point = cmds.listConnections(source, type="pointConstraint")
    existing_orient = cmds.listConnections(source, type="orientConstraint")
    if existing_point:
        for const in existing_point:
            if cmds.objExists(const):
                cmds.delete(const)
                print(f"  🗑️ 기존 Point Constraint 삭제: {const}")
    if existing_orient:
        for const in existing_orient:
            if cmds.objExists(const):
                cmds.delete(const)
                print(f"  🗑️ 기존 Orient Constraint 삭제: {const}")
    
    try:
        # Point Constraint (Translation 전체 따라감)
        point_const = cmds.pointConstraint(target, source, maintainOffset=False)
        print(f"  ✅ Point Constraint 생성: {target} → {source}")
        
        # Orient Constraint (X축만 따라감, Y/Z는 skip)
        orient_const = cmds.orientConstraint(target, source, maintainOffset=False, skip=["y", "z"])
        print(f"  ✅ Orient Constraint 생성 (X축만): {target} → {source}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Constraint 설정 실패: {e}")
        return False


def create_socket_joints_if_missing():
    """local_socket, world_socket 조인트가 없으면 생성"""
    parent_joint = "root"
    
    if not cmds.objExists(parent_joint):
        print(f"  ❌ {parent_joint} 존재하지 않음. 생성 불가.")
        return False
    
    # local_socket 생성 (없으면)
    if not cmds.objExists("local_socket"):
        print(f"  📦 local_socket 생성 중...")
        try:
            cmds.select(parent_joint)
            cmds.joint(name="local_socket")
            
            # Pelvis_M 위치로 이동
            if cmds.objExists("Pelvis_M"):
                pos = cmds.xform("Pelvis_M", query=True, worldSpace=True, translation=True)
                cmds.xform("local_socket", worldSpace=True, translation=pos)
            
            # Rotation 0
            cmds.setAttr("local_socket.rotateX", 0)
            cmds.setAttr("local_socket.rotateY", 0)
            cmds.setAttr("local_socket.rotateZ", 0)
            
            # Joint Orient (90, 0, 90)
            cmds.setAttr("local_socket.jointOrientX", 90)
            cmds.setAttr("local_socket.jointOrientY", 0)
            cmds.setAttr("local_socket.jointOrientZ", 90)
            
            cmds.select(clear=True)
            print(f"  ✅ local_socket 생성 완료")
        except Exception as e:
            print(f"  ❌ local_socket 생성 실패: {e}")
    else:
        print(f"  ⚠️ local_socket 이미 존재함. 스킵.")
    
    # world_socket 생성 (없으면)
    if not cmds.objExists("world_socket"):
        print(f"  📦 world_socket 생성 중...")
        try:
            cmds.select(parent_joint)
            cmds.joint(name="world_socket")
            
            # root 위치로 이동
            pos = cmds.xform(parent_joint, query=True, worldSpace=True, translation=True)
            cmds.xform("world_socket", worldSpace=True, translation=pos)
            
            # Rotation 0
            cmds.setAttr("world_socket.rotateX", 0)
            cmds.setAttr("world_socket.rotateY", 0)
            cmds.setAttr("world_socket.rotateZ", 0)
            
            # Joint Orient (90, 0, 90)
            cmds.setAttr("world_socket.jointOrientX", 90)
            cmds.setAttr("world_socket.jointOrientY", 0)
            cmds.setAttr("world_socket.jointOrientZ", 90)
            
            cmds.select(clear=True)
            print(f"  ✅ world_socket 생성 완료")
        except Exception as e:
            print(f"  ❌ world_socket 생성 실패: {e}")
    else:
        print(f"  ⚠️ world_socket 이미 존재함. 스킵.")
    
    return True


def create_camera_socket():
    """camera_socket 조인트 생성"""
    joint_name = "camera_socket"
    parent_joint = "root"
    
    # 기존에 존재하면 삭제 후 재생성
    if cmds.objExists(joint_name):
        delete_constraints_on_object(joint_name)
        cmds.delete(joint_name)
        print(f"  🗑️ 기존 {joint_name} 삭제")
    
    # 부모 조인트 확인
    if not cmds.objExists(parent_joint):
        print(f"  ❌ {parent_joint} 존재하지 않음. 생성 실패.")
        return False
    
    try:
        # 선택 해제
        cmds.select(clear=True)
        
        # 조인트 생성
        cmds.select(parent_joint)
        new_joint = cmds.joint(name=joint_name)
        
        # 위치 설정 (Y=150, Z=-150)
        cmds.setAttr(f"{joint_name}.translateX", 0)
        cmds.setAttr(f"{joint_name}.translateY", 150)
        cmds.setAttr(f"{joint_name}.translateZ", -150)
        print(f"  ✅ 위치 → (0, 150, -150)")
        
        # Rotation 설정 (0, 0, 0)
        cmds.setAttr(f"{joint_name}.rotateX", 0)
        cmds.setAttr(f"{joint_name}.rotateY", 0)
        cmds.setAttr(f"{joint_name}.rotateZ", 0)
        print(f"  ✅ Rotation → (0, 0, 0)")
        
        # Joint Orient 설정 (90, 0, 90)
        cmds.setAttr(f"{joint_name}.jointOrientX", 90)
        cmds.setAttr(f"{joint_name}.jointOrientY", 0)
        cmds.setAttr(f"{joint_name}.jointOrientZ", 90)
        print(f"  ✅ Joint Orient → (90, 0, 90)")
        
        cmds.select(clear=True)
        return True
        
    except Exception as e:
        print(f"  ❌ camera_socket 생성 실패: {e}")
        return False


def run_character_socket_fix():
    """캐릭터용 Socket Fix 실행"""
    print("\n" + "=" * 50)
    print("캐릭터 Socket Fix 시작")
    print("=" * 50)
    
    # 0. 기존 설정 정리 (삭제 후 새로 만들기)
    cleanup_existing()
    
    # 0.5. local_socket, world_socket 없으면 생성
    print(f"\n▶ Socket 조인트 확인/생성 중...")
    create_socket_joints_if_missing()
    
    # 타겟 조인트 정의
    socket_joints = {
        "local_socket": "Pelvis_M",   # local_socket → Pelvis_M 위치로
        "world_socket": "root"         # world_socket → root 위치로
    }
    
    for socket_joint, position_target in socket_joints.items():
        print(f"\n▶ {socket_joint} 처리 중...")
        
        if not cmds.objExists(socket_joint):
            print(f"  ❌ {socket_joint} 존재하지 않음. 스킵.")
            continue
        
        # 1. 모든 커넥션 끊기
        print("  [1] 커넥션 끊기...")
        disconnect_all_connections(socket_joint)
        
        # 1.5. 어트리뷰트 잠금 해제
        print("  [1.5] 어트리뷰트 잠금 해제...")
        unlock_attributes(socket_joint)
        
        # 2. Rotation 0으로 설정
        print("  [2] Rotation 초기화...")
        set_rotation_zero(socket_joint)
        
        # 3. 위치 맞추기
        print(f"  [3] {position_target} 위치로 이동...")
        match_position(socket_joint, position_target)
        
        # 4. Joint Orient 설정 (90, 0, 90)
        print("  [4] Joint Orient 설정...")
        set_joint_orient(socket_joint, 90, 0, 90)
    
    # 5. camera_socket 조인트 생성
    print(f"\n▶ camera_socket 생성 중...")
    create_camera_socket()
    
    # 6. local_socket_target 조인트 생성
    print(f"\n▶ local_socket_target 생성 중...")
    create_local_socket_target()
    
    # 7. local_socket에 local_socket_target constraint 설정
    print(f"\n▶ local_socket constraint 설정 중...")
    setup_local_socket_constraint()
    
    # 7-1. chest_M_target 조인트 생성
    print(f"\n▶ chest_M_target 생성 중...")
    create_chest_M_target()
    
    # 7-2. chest_M_target에 Chest_M constraint 설정
    print(f"\n▶ chest_M_target constraint 설정 중...")
    setup_chest_M_target_constraint()
    
    # 8. 컨트롤러 임포트
    print(f"\n▶ 컨트롤러 임포트 중...")
    import_socket_controllers()
    
    # 8-1. Chest_ori_cns_value 어트리뷰트 추가
    print(f"\n▶ Chest_ori_cns_value 어트리뷰트 추가 중...")
    add_chest_ori_attribute()
    
    # 8-2. Chest_ori_cns_value를 chest_M_target Orient Constraint에 연결
    print(f"\n▶ Chest_ori_cns_value → Orient Constraint 연결 중...")
    connect_chest_ori_constraint()
    
    # 9. camera_center_ctl_grp1 위치 맞추기 (먼저!)
    print(f"\n▶ camera_center_ctl_grp1 위치 맞추기...")
    position_single_controller("camera_center_ctl_grp1", "local_socket")
    
    # 9. camera_center_ctl_grp에 3타겟 Parent Constraint 설정 (먼저!)
    print(f"\n▶ camera_center_ctl_grp Parent Constraint 설정 중...")
    setup_camera_center_constraint()
    
    # 10. camera_socket_ctl_grp1 위치 맞추기 (constraint 후에!)
    print(f"\n▶ camera_socket_ctl_grp1 위치 맞추기...")
    position_single_controller("camera_socket_ctl_grp1", "camera_socket")
    
    # 11. camera_socket 조인트에 Parent Constraint 설정
    print(f"\n▶ camera_socket Parent Constraint 설정 중...")
    setup_camera_socket_constraint()
    
    # 12. camera_socket_ctl 어트리뷰트를 Constraint weight에 연결
    print(f"\n▶ Constraint weight 연결 중...")
    connect_constraint_weights()
    
    # 13. camera_center_ctl_grp1을 MotionSystem 하위로 이동
    print(f"\n▶ camera_center_ctl_grp1 → MotionSystem 하위로 이동...")
    parent_to_motion_system()
    
    print("\n" + "=" * 50)
    print("✅ Socket Joint Fix 완료!")
    print("=" * 50)
    
    cmds.confirmDialog(title="완료", message="Socket Joint Fix 완료!", button=["확인"])


def run_vehicle_socket_fix():
    """차량용 Socket Fix 실행"""
    print("\n" + "=" * 50)
    print("차량 Socket Fix 시작")
    print("=" * 50)
    
    # 1. Local_socket, World_socket 커넥션/컨스트레인 정리 (대문자 네이밍)
    socket_joints = ["Local_socket", "World_socket"]
    position_target = "Pelvis_ctrl"
    
    for socket_joint in socket_joints:
        print(f"\n▶ {socket_joint} 처리 중...")
        
        if not cmds.objExists(socket_joint):
            print(f"  ❌ {socket_joint} 존재하지 않음. 스킵.")
            continue
        
        # 커넥션 끊기
        print("  [1] 커넥션 끊기...")
        disconnect_all_connections(socket_joint)
        
        # 어트리뷰트 잠금 해제
        print("  [2] 어트리뷰트 잠금 해제...")
        unlock_attributes(socket_joint)
        
        # constraint 삭제
        print("  [3] Constraint 삭제...")
        delete_constraints_on_object(socket_joint)
        
        # Rotation 0으로 설정
        print("  [4] Rotation 초기화...")
        set_rotation_zero(socket_joint)
        
        # Pelvis_ctrl 위치로 이동
        print(f"  [5] {position_target} 위치로 이동...")
        match_position(socket_joint, position_target)
    
    # 2. camera_socket 조인트 생성
    print(f"\n▶ camera_socket 생성 중...")
    create_vehicle_camera_socket()
    
    # 3. 컨트롤러 임포트 (차량용)
    print(f"\n▶ 컨트롤러 임포트 중...")
    import_vehicle_socket_controllers()
    
    # 4. camera_socket 조인트를 camera_socket_ctl 위치로 이동 (matchTransform 사용)
    print(f"\n▶ camera_socket 위치 맞추기...")
    if cmds.objExists("camera_socket") and cmds.objExists("camera_socket_ctl"):
        # matchTransform 사용 (위치만, 회전은 빼고)
        cmds.matchTransform("camera_socket", "camera_socket_ctl", pos=True, rot=False, scl=False)
        print(f"  ✅ camera_socket → camera_socket_ctl 위치로 이동 (matchTransform)")
    else:
        print(f"  ⚠️ camera_socket 또는 camera_socket_ctl 존재하지 않음")
    
    # 5. camera_socket이 camera_socket_ctl을 따라가도록 Parent Constraint
    print(f"\n▶ camera_socket constraint 설정 중...")
    if cmds.objExists("camera_socket") and cmds.objExists("camera_socket_ctl"):
        # 기존 constraint 있으면 삭제 후 재생성
        existing = cmds.listConnections("camera_socket", type="parentConstraint")
        if existing:
            for const in existing:
                if cmds.objExists(const):
                    cmds.delete(const)
                    print(f"  🗑️ 기존 Parent Constraint 삭제: {const}")
        
        cmds.parentConstraint("camera_socket_ctl", "camera_socket", maintainOffset=True)
        print(f"  ✅ Parent Constraint 생성: camera_socket_ctl → camera_socket")
    else:
        print(f"  ⚠️ camera_socket 또는 camera_socket_ctl 존재하지 않음")
    
    # 6. body_socket 생성 (Local_socket 복사 → body_ctrl 하위로)
    print(f"\n▶ body_socket 생성 중...")
    create_vehicle_body_socket()
    
    # 7. Local_socket이 Pelvis_ctrl을 따라가도록 constraint
    print(f"\n▶ Local_socket constraint 설정 중...")
    if cmds.objExists("Local_socket") and cmds.objExists("Pelvis_ctrl"):
        # 기존 constraint 있으면 삭제 후 재생성
        existing_point = cmds.listConnections("Local_socket", type="pointConstraint")
        existing_orient = cmds.listConnections("Local_socket", type="orientConstraint")
        
        if existing_point:
            for const in existing_point:
                if cmds.objExists(const):
                    cmds.delete(const)
                    print(f"  🗑️ 기존 Point Constraint 삭제: {const}")
        if existing_orient:
            for const in existing_orient:
                if cmds.objExists(const):
                    cmds.delete(const)
                    print(f"  🗑️ 기존 Orient Constraint 삭제: {const}")
        
        # Point Constraint (Translation 전체)
        cmds.pointConstraint("Pelvis_ctrl", "Local_socket", maintainOffset=False)
        print(f"  ✅ Point Constraint 생성: Pelvis_ctrl → Local_socket")
        
        # Orient Constraint (Y축만, X/Z는 skip)
        cmds.orientConstraint("Pelvis_ctrl", "Local_socket", maintainOffset=False, skip=["x", "z"])
        print(f"  ✅ Orient Constraint 생성 (Y축만): Pelvis_ctrl → Local_socket")
    else:
        print(f"  ⚠️ Local_socket 또는 Pelvis_ctrl 존재하지 않음")
    
    # 8. camera_center_ctl_grp에 3타겟 Parent Constraint (World_socket, Local_socket, body_socket)
    print(f"\n▶ camera_center_ctl_grp Parent Constraint 설정 중...")
    setup_vehicle_camera_center_constraint()
    
    # 9. camera_socket_ctl 어트리뷰트를 Constraint weight에 연결
    print(f"\n▶ Constraint weight 연결 중...")
    connect_vehicle_constraint_weights()
    
    # 10. camera_center_ctl_grp1을 Main 하위로 이동
    print(f"\n▶ camera_center_ctl_grp1 → Main 하위로 이동...")
    if cmds.objExists("camera_center_ctl_grp1") and cmds.objExists("Main"):
        # 이미 Main 하위에 있는지 체크
        current_parent = cmds.listRelatives("camera_center_ctl_grp1", parent=True)
        if current_parent and current_parent[0] == "Main":
            print(f"  ⚠️ camera_center_ctl_grp1이 이미 Main 하위에 있음. 스킵.")
        else:
            cmds.parent("camera_center_ctl_grp1", "Main")
            print(f"  ✅ camera_center_ctl_grp1 → Main 하위로 이동 완료")
    else:
        print(f"  ⚠️ camera_center_ctl_grp1 또는 Main 존재하지 않음")
    
    print("\n" + "=" * 50)
    print("✅ 차량 Socket Fix 완료!")
    print("=" * 50)
    
    cmds.confirmDialog(title="완료", message="차량 Socket Fix 완료!", button=["확인"])


def import_vehicle_socket_controllers():
    """차량용 컨트롤러 파일 임포트"""
    file_path = "Z:/show/CORND/sequences/RND/YONGJIN_0000/RND/wip/maya/data/camera_ctl_Vehicle.ma"
    
    # 기존 컨트롤러 있으면 삭제 후 재임포트
    if cmds.objExists("camera_center_ctl_grp1"):
        delete_constraints_on_object("camera_center_ctl_grp")
        cmds.delete("camera_center_ctl_grp1")
        print(f"  🗑️ 기존 컨트롤러 삭제: camera_center_ctl_grp1")
    
    # 파일 존재 확인
    import os
    if not os.path.exists(file_path):
        print(f"  ❌ 파일을 찾을 수 없습니다: {file_path}")
        return False
    
    try:
        # 파일 임포트
        cmds.file(file_path, i=True, type="mayaAscii", 
                 ignoreVersion=True, mergeNamespacesOnClash=False,
                 namespace=":", options="v=0;", preserveReferences=True)
        
        print(f"  ✅ 컨트롤러 임포트 완료: {file_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ 컨트롤러 임포트 실패: {e}")
        return False


def connect_vehicle_constraint_weights():
    """차량용: camera_socket_ctl의 어트리뷰트를 camera_center_ctl_grp의 Parent Constraint weight에 연결
    (0-10 범위를 0-1로 변환하여 연결)"""
    ctrl = "camera_socket_ctl"
    driven = "camera_center_ctl_grp"
    
    if not cmds.objExists(ctrl):
        print(f"  ❌ {ctrl} 존재하지 않음")
        return False
    
    # 기존 multiplyDivide 노드 있으면 삭제 후 재생성
    md_nodes = ["md_world_cns_value", "md_local_cns_value", "md_chest_cns_value"]
    for md in md_nodes:
        if cmds.objExists(md):
            cmds.delete(md)
            print(f"  🗑️ 기존 md 노드 삭제: {md}")
    
    # Parent Constraint 찾기
    constraints = cmds.listConnections(driven, type="parentConstraint")
    if not constraints:
        print(f"  ❌ {driven}에 Parent Constraint 없음")
        return False
    
    parent_const = constraints[0]
    print(f"  📌 Parent Constraint: {parent_const}")
    
    # Constraint의 weight alias 목록 가져오기
    weight_aliases = cmds.parentConstraint(parent_const, query=True, weightAliasList=True)
    print(f"  📌 Weight Aliases: {weight_aliases}")
    
    # 연결 정의: (컨트롤러 어트리뷰트, 타겟 키워드)
    attr_mapping = [
        ("world_cns_value", "World"),
        ("local_cns_value", "Local"),
        ("chest_cns_value", "body"),
    ]
    
    for ctrl_attr, keyword in attr_mapping:
        src = f"{ctrl}.{ctrl_attr}"
        
        if not cmds.objExists(src):
            print(f"  ⚠️ {src} 존재하지 않음. 스킵.")
            continue
        
        # 키워드로 매칭되는 weight alias 찾기
        matched_alias = None
        for alias in weight_aliases:
            if keyword.lower() in alias.lower():
                matched_alias = alias
                break
        
        if not matched_alias:
            print(f"  ⚠️ '{keyword}' 매칭되는 weight alias 없음. 스킵.")
            continue
        
        const_attr = f"{parent_const}.{matched_alias}"
        
        try:
            # multiplyDivide 노드 생성 (0-10 → 0-1 변환)
            md_node = cmds.createNode("multiplyDivide", name=f"md_{ctrl_attr}")
            cmds.setAttr(f"{md_node}.operation", 2)  # Divide
            cmds.setAttr(f"{md_node}.input2X", 10)   # 10으로 나누기
            
            # 연결: ctrl attr → multiplyDivide → constraint weight
            cmds.connectAttr(src, f"{md_node}.input1X", force=True)
            cmds.connectAttr(f"{md_node}.outputX", const_attr, force=True)
            
            print(f"  ✅ 연결: {src} → {md_node} (÷10) → {const_attr}")
        except Exception as e:
            print(f"  ❌ 연결 실패: {src} → {const_attr}: {e}")


def setup_vehicle_camera_center_constraint():
    """차량용: camera_center_ctl_grp에 3개 타겟(World_socket, Local_socket, body_socket)으로 Parent Constraint 설정"""
    targets = ["World_socket", "Local_socket", "body_socket"]
    driven = "camera_center_ctl_grp"
    
    if not cmds.objExists(driven):
        print(f"  ❌ {driven} 존재하지 않음")
        return False
    
    # 기존 constraint 있으면 삭제 후 재생성
    existing = cmds.listConnections(driven, type="parentConstraint")
    if existing:
        for const in existing:
            if cmds.objExists(const):
                cmds.delete(const)
                print(f"  🗑️ 기존 Parent Constraint 삭제: {const}")
    
    # 타겟 존재 확인
    valid_targets = []
    for target in targets:
        if cmds.objExists(target):
            valid_targets.append(target)
        else:
            print(f"  ⚠️ {target} 존재하지 않음. 스킵.")
    
    if not valid_targets:
        print(f"  ❌ 유효한 타겟이 없음")
        return False
    
    try:
        # 3개 타겟으로 Parent Constraint
        parent_const = cmds.parentConstraint(valid_targets, driven, maintainOffset=True)
        print(f"  ✅ Parent Constraint 생성: {valid_targets} → {driven}")
        return True
        
    except Exception as e:
        print(f"  ❌ Parent Constraint 설정 실패: {e}")
        return False


def create_vehicle_body_socket():
    """Local_socket을 복사해서 body_socket 생성 후 body_ctrl 하위로 이동"""
    source_joint = "Local_socket"
    new_joint_name = "body_socket"
    parent_node = "body_ctrl"
    
    # 기존에 존재하면 삭제 후 재생성
    if cmds.objExists(new_joint_name):
        delete_constraints_on_object(new_joint_name)
        cmds.delete(new_joint_name)
        print(f"  🗑️ 기존 {new_joint_name} 삭제")
    
    if not cmds.objExists(source_joint):
        print(f"  ❌ {source_joint} 존재하지 않음")
        return False
    
    if not cmds.objExists(parent_node):
        print(f"  ❌ {parent_node} 존재하지 않음")
        return False
    
    try:
        # Local_socket 복사
        cmds.select(source_joint, replace=True)
        duplicated = cmds.duplicate(name=new_joint_name, parentOnly=True)[0]
        
        # body_ctrl 하위로 이동
        cmds.parent(duplicated, parent_node)
        
        # Draw Style을 None으로 설정 (2 = None)
        cmds.setAttr(f"{new_joint_name}.drawStyle", 2)
        print(f"  ✅ Draw Style → None")
        
        print(f"  ✅ {new_joint_name} 생성 완료 (→ {parent_node} 하위)")
        cmds.select(clear=True)
        return True
        
    except Exception as e:
        print(f"  ❌ {new_joint_name} 생성 실패: {e}")
        return False


def create_vehicle_camera_socket():
    """차량용 camera_socket 조인트 생성"""
    joint_name = "camera_socket"
    parent_joint = "root"
    
    # 기존에 존재하면 삭제 후 재생성
    if cmds.objExists(joint_name):
        delete_constraints_on_object(joint_name)
        cmds.delete(joint_name)
        print(f"  🗑️ 기존 {joint_name} 삭제")
    
    # 부모 조인트 확인
    if not cmds.objExists(parent_joint):
        print(f"  ❌ {parent_joint} 존재하지 않음. 생성 실패.")
        return False
    
    try:
        # 선택 해제
        cmds.select(clear=True)
        
        # 조인트 생성 (위치는 나중에 camera_socket_ctl로 맞춤)
        cmds.select(parent_joint)
        new_joint = cmds.joint(name=joint_name)
        
        # Rotation 설정 (0, 0, 0)
        cmds.setAttr(f"{joint_name}.rotateX", 0)
        cmds.setAttr(f"{joint_name}.rotateY", 0)
        cmds.setAttr(f"{joint_name}.rotateZ", 0)
        print(f"  ✅ Rotation → (0, 0, 0)")
        
        # Joint Orient 설정 (90, 0, 0)
        cmds.setAttr(f"{joint_name}.jointOrientX", 90)
        cmds.setAttr(f"{joint_name}.jointOrientY", 0)
        cmds.setAttr(f"{joint_name}.jointOrientZ", 0)
        print(f"  ✅ Joint Orient → (90, 0, 0)")
        
        cmds.select(clear=True)
        print(f"  ✅ {joint_name} 생성 완료")
        return True
        
    except Exception as e:
        print(f"  ❌ camera_socket 생성 실패: {e}")
        return False


# ========================================
# UI
# ========================================
WINDOW_NAME = "socketFixToolWindow"


def create_ui():
    """Socket Fix Tool UI 생성"""
    # 기존 윈도우 닫기
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)
    
    # 윈도우 생성
    window = cmds.window(WINDOW_NAME, title="Socket Fix Tool", widthHeight=(300, 150), sizeable=True)
    
    # 메인 레이아웃
    cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnAlign="center")
    cmds.separator(height=10, style="none")
    
    # 타이틀
    cmds.text(label="Socket Fix Tool", font="boldLabelFont", height=30)
    cmds.separator(height=10, style="in")
    
    # 버튼들
    cmds.button(
        label="캐릭터 Socket Fix",
        command=lambda x: run_character_socket_fix(),
        height=40,
        backgroundColor=[0.4, 0.6, 0.8]
    )
    
    cmds.button(
        label="차량 Socket Fix",
        command=lambda x: run_vehicle_socket_fix(),
        height=40,
        backgroundColor=[0.6, 0.5, 0.4]
    )
    
    cmds.separator(height=10, style="none")
    cmds.setParent('..')
    
    cmds.showWindow(window)


def run():
    """도구 실행 (UI 표시)"""
    create_ui()


if __name__ == "__main__":
    run()

