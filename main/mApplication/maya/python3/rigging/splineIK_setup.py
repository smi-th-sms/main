"""
Spline IK Setup Tool
선택한 joint tree에 대해 spline IK 셋업을 자동으로 구성합니다.

Usage:
    - joint chain의 root joint 하나 선택 후 실행
    - 또는 start joint, end joint 두 개 선택 후 실행
"""

import maya.cmds as cmds


def get_joint_chain(start_joint, end_joint=None):
    """
    start_joint부터 end_joint(또는 chain 끝)까지 순서대로 joint 리스트 반환.
    분기점(children > 1)에서 end_joint 미지정 시 첫 번째 child 경로로 진행.
    """
    joints = [start_joint]
    current = start_joint

    while True:
        children = cmds.listRelatives(current, children=True, type='joint') or []

        if not children:
            break

        # end_joint에 도달했으면 종료
        if current == end_joint:
            break

        if end_joint:
            # end_joint로 이어지는 child 탐색
            next_joint = None
            for child in children:
                if child == end_joint or _is_descendant(child, end_joint):
                    next_joint = child
                    break
            if next_joint is None:
                cmds.warning(f"{end_joint} 이 {start_joint} 의 하위 계층에 없습니다.")
                break
        else:
            next_joint = children[0]

        joints.append(next_joint)
        current = next_joint

        if current == end_joint:
            break

    return joints


def _is_descendant(node, target):
    """node가 target의 상위 계층(ancestor)인지 확인"""
    descendants = cmds.listRelatives(node, allDescendents=True, type='joint') or []
    return target in descendants


def setup_spline_ik():
    """
    선택한 joint tree에 spline IK 셋업 수행.

    Steps:
        1. spans = joint 개수 - 1, degree 3 EP curve 생성
        2. curve EP point를 joint 위치에 순서대로 매칭
        3. ikHandle 생성 (ikSplineSolver, ccv/scv/pcv off)
        4. IK handle world up type/axis 설정
        5. 시작·끝 위치에 up vector joint 각각 생성
        6. curve / ikHandle / upVec joints를 그룹으로 정리
    """
    selection = cmds.ls(sl=True, type='joint')

    if not selection:
        cmds.warning("joint를 1개(root) 또는 2개(start, end) 선택 후 실행하세요.")
        return None

    # joint chain 구성
    if len(selection) == 1:
        joints = get_joint_chain(selection[0])
    elif len(selection) == 2:
        joints = get_joint_chain(selection[0], selection[1])
    else:
        cmds.warning("joint를 1개(root) 또는 2개(start, end) 선택하세요.")
        return None

    joint_count = len(joints)
    if joint_count < 2:
        cmds.warning("joint chain에 최소 2개의 joint가 필요합니다.")
        return None

    prefix = joints[0]

    # joint world position 수집
    positions = [
        tuple(cmds.xform(jnt, q=True, ws=True, t=True))
        for jnt in joints
    ]

    # ------------------------------------------------------------------
    # 1 & 2. EP curve 생성 (spans = joint_count - 1, degree = 3)
    #         ep= 파라미터로 각 EP point가 joint 위치에 정확히 일치
    # ------------------------------------------------------------------
    curve_name = f"{prefix}_splineIK_crv"
    curve = cmds.curve(name=curve_name, ep=positions, d=3)

    # ------------------------------------------------------------------
    # 3. IK Handle 생성
    #    ikHandle -sol ikSplineSolver -ccv false -scv false -pcv false -ns 3
    # ------------------------------------------------------------------
    ik_handle_name = f"{prefix}_splineIK_hdl"
    ik_result = cmds.ikHandle(
        name=ik_handle_name,
        startJoint=joints[0],
        endEffector=joints[-1],
        solver='ikSplineSolver',
        createCurve=False,      # -ccv false
        simplifyCurve=False,    # -scv false
        parentCurve=False,      # -pcv false
        numSpans=3,             # -ns 3
        curve=curve
    )
    ik_handle = ik_result[0]

    # ------------------------------------------------------------------
    # 4. World Up Type 설정 (Object Rotation Up, +Z axis)
    #    dWorldUpType 4  : Object Rotation Up
    #    dWorldUpAxis  3  : +Z
    # ------------------------------------------------------------------
    cmds.setAttr(f"{ik_handle}.dWorldUpType", 4)
    cmds.setAttr(f"{ik_handle}.dWorldUpAxis", 3)
    cmds.setAttr(f"{ik_handle}.dWorldUpVectorZ", 1)
    cmds.setAttr(f"{ik_handle}.dWorldUpVectorEndZ", 1)
    cmds.setAttr(f"{ik_handle}.dWorldUpVectorY", 0)
    cmds.setAttr(f"{ik_handle}.dWorldUpVectorEndY", 0)

    # ------------------------------------------------------------------
    # 5. 시작·끝 위치에 up vector joint 생성
    # ------------------------------------------------------------------
    cmds.select(cl=True)
    start_up_jnt = cmds.joint(
        name=f"{joints[0]}_splineIK_upVec",
        position=positions[0]
    )
    cmds.select(cl=True)
    end_up_jnt = cmds.joint(
        name=f"{joints[-1]}_splineIK_upVec",
        position=positions[-1]
    )

    # up vector joint → IK handle worldMatrix 연결
    cmds.connectAttr(f"{start_up_jnt}.worldMatrix[0]", f"{ik_handle}.dWorldUpMatrix")
    cmds.connectAttr(f"{end_up_jnt}.worldMatrix[0]",   f"{ik_handle}.dWorldUpMatrixEnd")

    # ------------------------------------------------------------------
    # 6. 그룹화
    #    {prefix}_splineIK_grp
    #    ├── {prefix}_splineIK_upVec_grp
    #    │   ├── {start}_splineIK_upVec
    #    │   └── {end}_splineIK_upVec
    #    ├── {prefix}_splineIK_crv
    #    └── {prefix}_splineIK_hdl
    # ------------------------------------------------------------------
    upvec_grp = cmds.group(
        start_up_jnt, end_up_jnt,
        name=f"{prefix}_splineIK_upVec_grp"
    )
    top_grp = cmds.group(
        upvec_grp, curve, ik_handle,
        name=f"{prefix}_splineIK_grp"
    )

    # 결과 출력
    print("=" * 50)
    print("Spline IK Setup 완료")
    print(f"  Joint Chain  : {joints[0]} -> {joints[-1]}  ({joint_count} joints)")
    print(f"  Group        : {top_grp}")
    print(f"    Curve      : {curve}  (spans={joint_count - 1}, degree=3)")
    print(f"    IK Handle  : {ik_handle}")
    print(f"    UpVec Grp  : {upvec_grp}")
    print(f"      Start    : {start_up_jnt}")
    print(f"      End      : {end_up_jnt}")
    print("=" * 50)

    return {
        'ik_handle':   ik_handle,
        'curve':       curve,
        'up_start':    start_up_jnt,
        'up_end':      end_up_jnt,
        'upvec_grp':   upvec_grp,
        'top_grp':     top_grp,
        'joints':      joints,
    }


if __name__ == '__main__':
    setup_spline_ik()
