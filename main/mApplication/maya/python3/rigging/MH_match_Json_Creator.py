import maya.cmds as cmds
import os
import json

def export_selected_joints_transforms_noName():
    selected_joints = cmds.ls(selection=True, type='joint')
    if not selected_joints:
        cmds.warning("No joints selected.")
        return

    first_joint = selected_joints[0]
    if not cmds.referenceQuery(first_joint, isNodeReferenced=True):
        cmds.warning("The selected joint is not referenced.")
        return

    ref_node = cmds.referenceQuery(first_joint, referenceNode=True)
    ref_path = cmds.referenceQuery(ref_node, filename=True)
    print("Original Reference Path:", ref_path)

    # 경로를 '/'를 기준으로 분리
    path_parts = ref_path.replace('\\', '/').split('/')
    print("Path Parts:", path_parts)

    if 'pub' in path_parts:
        pub_index = path_parts.index('pub')
        new_path_parts = path_parts[:pub_index] + ['MH_match_Json']
        export_dir = '/'.join(new_path_parts)
        print("New Export Directory:", export_dir)
    else:
        cmds.warning("Reference path does not contain 'pub' folder.")
        return

    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    # 사용자 입력 팝업 (기본 파일명 제공)
    result = cmds.promptDialog(
        title='Save JSON File',
        message='Enter the filename:',
        button=['OK', 'Cancel'],
        defaultButton='OK',
        cancelButton='Cancel',
        dismissString='Cancel'
    )

    if result == 'Cancel':  # 사용자가 취소를 누르면 종료
        cmds.warning("Export cancelled by user.")
        return

    filename = cmds.promptDialog(query=True, text=True).strip()
    if not filename:  # 사용자가 빈 값 입력 시 기본값 사용
        filename = "default_joint_transforms.json"

    # JSON 확장자 자동 추가
    if not filename.endswith(".json"):
        filename += ".json"

    file_path = os.path.join(export_dir, filename)
    print("Export File Path:", file_path)

    joints_data = {}
    for joint in selected_joints:
        joint_name = joint.split(':')[-1]  # 네임스페이스 제거하고 조인트 이름만 추출
        joint_data = {
            'translate': cmds.getAttr(joint + ".translate")[0],
            'rotate': cmds.getAttr(joint + ".rotate")[0],
            'scale': cmds.getAttr(joint + ".scale")[0]
        }
        joints_data[joint_name] = joint_data  # 네임스페이스 없는 이름으로 저장

    try:
        with open(file_path, 'w') as outfile:
            json.dump(joints_data, outfile, indent=4)
        cmds.confirmDialog(title='Success', message=f'Exported as {filename}', button=['OK'])
    except Exception as e:
        cmds.confirmDialog(title='Error', message=str(e), button=['OK'])

export_selected_joints_transforms_noName()