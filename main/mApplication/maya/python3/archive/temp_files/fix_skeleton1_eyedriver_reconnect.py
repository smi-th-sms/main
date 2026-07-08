"""
skeleton1 참조 재연결 + eye driver 복구

Maya에서 수동으로 진행했던 아래 작업들을 정리한 스크립트.
Script Editor 로그 기준 (isolateSelect/단순 select 등 뷰포트 탐색 명령은 제외):

1. multMatrix40~45 의 matrixIn[1] 을 skeleton1:root / skeleton1:spine_05 /
   skeleton1:head 의 worldMatrix[0] 에 재연결
2. LOC_C_eyeDriver 를 skeleton1:head 에 parentConstraint(maintainOffset) 로 연결
3. head_rl4Embedded 노드를 다시 활성화 (nodeState = 0)

Usage:
    import importlib
    import fix_skeleton1_eyedriver_reconnect as fix
    importlib.reload(fix)
    fix.run()
"""

import maya.cmds as cmds

# (driver node, dst plug) – driver 는 .worldMatrix[0] 에서 가져온다
_MATRIX_CONNECTIONS = [
    ("skeleton1:root",     "multMatrix43.matrixIn[1]"),
    ("skeleton1:spine_05", "multMatrix44.matrixIn[1]"),
    ("skeleton1:head",     "multMatrix45.matrixIn[1]"),
    ("skeleton1:head",     "multMatrix42.matrixIn[1]"),
    ("skeleton1:root",     "multMatrix40.matrixIn[1]"),
    ("skeleton1:spine_05", "multMatrix41.matrixIn[1]"),
]

_EYE_DRIVER_CONSTRAINT = "LOC_C_eyeDriver_parentConstraint1"
_EYE_DRIVER_TARGET = "skeleton1:head"
_EYE_DRIVER_NODE = "LOC_C_eyeDriver"

_RL4_NODE = "head_rl4Embedded"


def _reconnect_matrices():
    for driver, dst_plug in _MATRIX_CONNECTIONS:
        src_plug = driver + ".worldMatrix[0]"
        dst_node = dst_plug.split(".")[0]

        if not cmds.objExists(driver):
            cmds.warning("fix_skeleton1: driver not found - " + driver)
            continue
        if not cmds.objExists(dst_node):
            cmds.warning("fix_skeleton1: dst node not found - " + dst_node)
            continue

        cmds.connectAttr(src_plug, dst_plug, force=True)
        print("fix_skeleton1: connected {} -> {}".format(src_plug, dst_plug))


def _rebuild_eye_driver_constraint():
    if cmds.objExists(_EYE_DRIVER_CONSTRAINT):
        print("fix_skeleton1: skip - " + _EYE_DRIVER_CONSTRAINT + " already exists")
        return
    if not cmds.objExists(_EYE_DRIVER_TARGET) or not cmds.objExists(_EYE_DRIVER_NODE):
        cmds.warning(
            "fix_skeleton1: skip eye driver constraint - missing {} or {}".format(
                _EYE_DRIVER_TARGET, _EYE_DRIVER_NODE))
        return

    cmds.parentConstraint(_EYE_DRIVER_TARGET, _EYE_DRIVER_NODE,
                          maintainOffset=True, weight=1,
                          name=_EYE_DRIVER_CONSTRAINT)
    print("fix_skeleton1: created " + _EYE_DRIVER_CONSTRAINT)


def _enable_rl4_node():
    if not cmds.objExists(_RL4_NODE):
        cmds.warning("fix_skeleton1: node not found - " + _RL4_NODE)
        return

    plug = _RL4_NODE + ".nodeState"
    if cmds.getAttr(plug) == 0:
        print("fix_skeleton1: skip - {} already 0".format(plug))
        return

    incoming = cmds.listConnections(plug, source=True, destination=False, plugs=True)
    if incoming:
        cmds.warning(
            "fix_skeleton1: skip - {} is driven by {}, not overriding".format(
                plug, incoming[0]))
        return
    if cmds.getAttr(plug, lock=True):
        cmds.warning("fix_skeleton1: skip - {} is locked".format(plug))
        return

    cmds.setAttr(plug, 0)
    print("fix_skeleton1: set {} = 0".format(plug))


def run():
    _reconnect_matrices()
    _rebuild_eye_driver_constraint()
    _enable_rl4_node()
    print("fix_skeleton1: done.")


if __name__ == "__main__":
    run()
