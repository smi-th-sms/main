# -*- coding: utf-8 -*-
"""
Bone Dynamics Node Tool
========================
boneDynamicsNode.mll (커스텀 다이나믹스 플러그인) 기반 조인트체인
다이나믹스 리그 설치 도구.

Plugin:
    원본: main/utils/boneDynamicsNode.mll
    로컬에 플러그인이 없으면 현재 Maya 버전의 사용자 plug-ins 폴더로
    자동 복사한 뒤 로드한다. (플러그인 바이너리 자체는 수정하지 않음)

Usage (Maya Script Editor):
    import importlib
    from python3.tools import bone_dynamics_tool
    importlib.reload(bone_dynamics_tool)
    bone_dynamics_tool.show()
"""

import os
import shutil
import sys
import traceback

import maya.cmds as cmds

try:
    from PySide2 import QtWidgets, QtCore, QtGui
    from shiboken2 import wrapInstance
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui
    from shiboken6 import wrapInstance

import maya.OpenMayaUI as omui


# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# tools/ -> python3/ -> maya/ -> mApplication/ -> main/ -> utils/
PLUGIN_SOURCE = os.path.normpath(
    os.path.join(_SCRIPT_DIR, "../../../../utils/boneDynamicsNode.mll")
)
PLUGIN_NAME = "boneDynamicsNode.mll"

SET_NAME = "boneDynamicsNodeSet"


def get_maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)


# ---------------------------------------------------------------------------
# 플러그인 설치 / 로드
# ---------------------------------------------------------------------------
def _user_plugin_dir():
    """현재 Maya 버전의 사용자 plug-ins 폴더 경로 (버전 하드코딩 없음)"""
    user_dir = cmds.internalVar(userAppDir=True)  # .../Documents/maya/
    version = cmds.about(version=True).split(".")[0]  # "2025.1" -> "2025"
    return os.path.join(user_dir, version, "plug-ins")


def ensure_plugin(log=print):
    """boneDynamicsNode 플러그인이 로드되어 있는지 확인.
    없으면 main/utils에서 사용자 plug-ins 폴더로 복사한 뒤 로드한다."""
    if cmds.pluginInfo(PLUGIN_NAME, q=True, loaded=True):
        return True

    try:
        cmds.loadPlugin(PLUGIN_NAME, quiet=True)
        return True
    except RuntimeError:
        pass

    if not os.path.isfile(PLUGIN_SOURCE):
        raise FileNotFoundError(
            "플러그인 원본을 찾을 수 없습니다: {}".format(PLUGIN_SOURCE)
        )

    dst_dir = _user_plugin_dir()
    os.makedirs(dst_dir, exist_ok=True)
    dst_path = os.path.join(dst_dir, PLUGIN_NAME)

    if not os.path.isfile(dst_path):
        log("[INFO] 플러그인 미설치 -> 복사: {} -> {}".format(PLUGIN_SOURCE, dst_path))
        shutil.copy2(PLUGIN_SOURCE, dst_path)

    cmds.loadPlugin(dst_path, quiet=True)
    return True


# ---------------------------------------------------------------------------
# 코어 로직
# ---------------------------------------------------------------------------
def create_dynamics_node(
        bone,
        end,
        scalable=False,
        target_bone=None,
        offset_node=None,
        colliders=None,
        visualize=True,
        additional_force_node=None,
        additional_force_init_vec=(0, 0, -1),
        log=print,
):
    colliders = colliders or []

    if bone not in (cmds.listRelatives(end, p=True) or []):
        log("Skip: {} is not {}'s parent.".format(bone, end))
        return None

    boneDynamicsNode = cmds.createNode("boneDynamicsNode")

    cmds.connectAttr('time1.outTime', boneDynamicsNode + '.time', force=True)
    cmds.connectAttr(bone + '.translate', boneDynamicsNode + '.boneTranslate', f=True)
    cmds.connectAttr(bone + '.parentMatrix[0]', boneDynamicsNode + '.boneParentMatrix', f=True)
    cmds.connectAttr(bone + '.parentInverseMatrix[0]', boneDynamicsNode + '.boneParentInverseMatrix', f=True)
    cmds.connectAttr(bone + '.jointOrient', boneDynamicsNode + '.boneJointOrient', f=True)
    cmds.connectAttr(end + '.translate', boneDynamicsNode + '.endTranslate', f=True)

    cmds.connectAttr(boneDynamicsNode + '.outputRotate', bone + '.rotate', f=True)

    if scalable:
        cmds.connectAttr(bone + '.scale', boneDynamicsNode + '.boneScale', f=True)
        cmds.connectAttr(bone + '.inverseScale', boneDynamicsNode + '.boneInverseScale', f=True)
        cmds.connectAttr(end + '.scale', boneDynamicsNode + '.endScale', f=True)

    if target_bone and cmds.objExists(target_bone):
        cmds.connectAttr(target_bone + '.rotate', boneDynamicsNode + '.rotationOffset', f=True)

    if offset_node and cmds.objExists(offset_node):
        cmds.connectAttr(offset_node + '.worldMatrix[0]', boneDynamicsNode + '.offsetMatrix', f=True)

    if additional_force_node and cmds.objExists(additional_force_node):
        vp = cmds.listConnections(additional_force_node + '.worldMatrix[0]', s=False, d=True, type='vectorProduct')
        if vp:
            vp = vp[0]
        else:
            vp = cmds.createNode('vectorProduct')
            cmds.setAttr(vp + '.operation', 3)
            cmds.setAttr(vp + '.input1', additional_force_init_vec[0], additional_force_init_vec[1],
                         additional_force_init_vec[2], type='double3')
            cmds.setAttr(vp + '.normalizeOutput', 1)
            cmds.connectAttr(additional_force_node + '.worldMatrix[0]', vp + '.matrix', f=True)
        cmds.connectAttr(vp + '.output', boneDynamicsNode + '.additionalForce', f=True)

    if visualize:
        _build_visualizers(bone, end, boneDynamicsNode)

    _connect_colliders(boneDynamicsNode, colliders, log=log)

    return boneDynamicsNode


def _build_visualizers(bone, end, boneDynamicsNode):
    # angle limit
    angle_cone = cmds.createNode("implicitCone")
    angle_cone_tm = cmds.listRelatives(angle_cone, p=True)[0]
    angle_cone_ro = cmds.createNode("transform", n="{}_cone_ro".format(bone))
    angle_cone_root = cmds.createNode("transform", n="{}_cone_root".format(bone))
    cmds.setAttr(angle_cone_tm + '.ry', -90)
    cmds.parent(angle_cone_tm, angle_cone_ro, r=True)
    cmds.parent(angle_cone_ro, angle_cone_root, r=True)
    bone_parent = cmds.listRelatives(bone, p=True)
    if bone_parent:
        cmds.parent(angle_cone_root, bone_parent[0], r=True)
    cmds.connectAttr(boneDynamicsNode + '.boneTranslate', angle_cone_root + '.translate', f=True)
    cmds.connectAttr(boneDynamicsNode + '.boneJointOrient', angle_cone_root + '.rotate', f=True)
    cmds.connectAttr(boneDynamicsNode + '.rotationOffset', angle_cone_ro + '.rotate', f=True)
    cmds.connectAttr(boneDynamicsNode + '.enableAngleLimit', angle_cone_root + '.v', f=True)
    cmds.connectAttr(boneDynamicsNode + '.angleLimit', angle_cone + '.coneAngle', f=True)
    cmds.setAttr(angle_cone + '.coneCap', 2)
    cmds.setAttr(angle_cone_tm + '.overrideEnabled', 1)
    cmds.setAttr(angle_cone_tm + '.overrideDisplayType', 2)

    # collision radius
    radius_sphere = cmds.createNode("implicitSphere")
    cmds.connectAttr(boneDynamicsNode + '.radius', radius_sphere + '.radius', f=True)
    radius_sphere_tm = cmds.listRelatives(radius_sphere, p=True)[0]
    cmds.parent(radius_sphere_tm, end, r=True)
    cmds.setAttr(radius_sphere_tm + '.overrideEnabled', 1)
    cmds.setAttr(radius_sphere_tm + '.overrideDisplayType', 2)
    cmds.connectAttr(boneDynamicsNode + '.iterations', radius_sphere_tm + '.v', f=True)


def _connect_colliders(boneDynamicsNode, colliders, log=print):
    sphere_col_idx = 0
    capsule_col_idx = 0
    iplane_col_idx = 0
    mesh_col_idx = 0

    for col in colliders:

        if not cmds.objExists(col):
            log("Skip: {} is not found.".format(col))
            continue

        if not cmds.attributeQuery('colliderType', n=col, ex=True):
            col_shape = cmds.listRelatives(col, s=True, f=True)
            if col_shape and cmds.nodeType(col_shape[0]) == 'mesh':
                cmds.connectAttr(col_shape[0] + '.worldMesh[0]',
                                  boneDynamicsNode + '.meshCollider[{}]'.format(mesh_col_idx), f=True)
                mesh_col_idx += 1
                continue
            log("Skip: {} has no 'colliderType' attribute.".format(col))
            continue

        colliderType = cmds.getAttr(col + '.colliderType')

        if colliderType == 'sphere':
            cmds.connectAttr(col + ".worldMatrix[0]",
                              boneDynamicsNode + ".sphereCollider[{}].sphereColMatrix".format(sphere_col_idx), f=True)
            cmds.connectAttr(col + ".radius",
                              boneDynamicsNode + ".sphereCollider[{}].sphereColRadius".format(sphere_col_idx), f=True)
            sphere_col_idx += 1

        elif colliderType in ['capsule', 'capsule2']:
            radius_attr_a = ".radius" if colliderType == 'capsule' else ".radiusA"
            radius_attr_b = ".radius" if colliderType == 'capsule' else ".radiusB"
            a = cmds.listConnections(col + '.sphereA', d=0)[0]
            b = cmds.listConnections(col + '.sphereB', d=0)[0]
            cmds.connectAttr(a + ".worldMatrix[0]",
                              boneDynamicsNode + ".capsuleCollider[{}].capsuleColMatrixA".format(capsule_col_idx),
                              f=True)
            cmds.connectAttr(b + ".worldMatrix[0]",
                              boneDynamicsNode + ".capsuleCollider[{}].capsuleColMatrixB".format(capsule_col_idx),
                              f=True)
            cmds.connectAttr(col + radius_attr_a,
                              boneDynamicsNode + ".capsuleCollider[{}].capsuleColRadiusA".format(capsule_col_idx),
                              f=True)
            cmds.connectAttr(col + radius_attr_b,
                              boneDynamicsNode + ".capsuleCollider[{}].capsuleColRadiusB".format(capsule_col_idx),
                              f=True)
            capsule_col_idx += 1

        elif colliderType == 'infinitePlane':
            cmds.connectAttr(col + ".worldMatrix[0]",
                              boneDynamicsNode + ".infinitePlaneCollider[{}].infinitePlaneColMatrix".format(
                                  iplane_col_idx), f=True)
            iplane_col_idx += 1


# ---------------------------------------------------------------------------
# 자동화 헬퍼 (target chain / offset node / collider group)
# ---------------------------------------------------------------------------
def create_target_chain(joints, postfix="_target", log=print):
    """조인트 체인을 복제해서 postfix가 붙은 독립적인 타겟 체인을 만든다.
    타겟 체인은 다이나믹스가 적용되는 원본 체인과 분리되어 있어
    애니메이터가 나중에 별도로 포즈를 잡아 rotationOffset 기준으로 쓸 수 있다."""
    target_joints = []
    prev_target = None

    for jnt in joints:
        tgt_name = "{}{}".format(jnt, postfix)

        if cmds.objExists(tgt_name):
            # 이미 생성된 타겟은 재사용만 하고 부모는 다시 손대지 않는다.
            # (원본 루트 조인트는 이후 offset 노드 하위로 재배치되므로,
            #  재실행 시 '현재' 부모를 기준으로 판단하면 잘못 재파렌팅될 수 있다)
            log("[INFO] 기존 타겟 조인트 재사용: {}".format(tgt_name))
            target_joints.append(tgt_name)
            prev_target = tgt_name
            continue

        dup = cmds.duplicate(jnt, name=tgt_name, parentOnly=True)[0]
        log("[INFO] 타겟 조인트 생성: {}".format(dup))

        if prev_target:
            if (cmds.listRelatives(dup, parent=True) or []) != [prev_target]:
                cmds.parent(dup, prev_target)
        else:
            orig_parent = cmds.listRelatives(jnt, parent=True) or []
            if orig_parent and (cmds.listRelatives(dup, parent=True) or []) != orig_parent:
                cmds.parent(dup, orig_parent[0])

        target_joints.append(dup)
        prev_target = dup

    return target_joints


def create_offset_node(root_joint, log=print):
    """루트 조인트의 위치/방향에 맞춰 offset 그룹을 생성한다.
    루트의 부모 아래에 배치되어 원본 체인과 동일한 공간을 공유한다."""
    offset_name = "{}_offset".format(root_joint)

    if cmds.objExists(offset_name):
        log("[INFO] 기존 offset 노드 재사용: {}".format(offset_name))
        return offset_name

    grp = cmds.group(empty=True, name=offset_name)
    cmds.delete(cmds.parentConstraint(root_joint, grp, maintainOffset=False))

    root_parent = cmds.listRelatives(root_joint, parent=True) or []
    if root_parent:
        cmds.parent(grp, root_parent[0])

    log("[INFO] offset 노드 생성: {}".format(grp))
    return grp


def attach_offset_to_target(offset_node, target_root, log=print):
    """offset 노드를 target 체인의 첫 번째 조인트로 parentConstraint 한다."""
    for pc in (cmds.listRelatives(offset_node, type="parentConstraint") or []):
        drivers = cmds.parentConstraint(pc, q=True, targetList=True) or []
        if target_root in drivers:
            log("[INFO] 이미 constraint 되어 있음: {} -> {}".format(target_root, offset_node))
            return pc

    pc = cmds.parentConstraint(target_root, offset_node, maintainOffset=True)[0]
    log("[INFO] offset constraint: {} -> {}".format(target_root, offset_node))
    return pc


def parent_root_under_offset(root_joint, offset_node, log=print):
    """다이나믹스 조인트 체인의 루트를 offset 노드 하위로 이동한다."""
    current_parent = cmds.listRelatives(root_joint, parent=True) or []
    if current_parent == [offset_node]:
        log("[INFO] {} 는 이미 {} 하위에 있습니다.".format(root_joint, offset_node))
        return

    cmds.parent(root_joint, offset_node)
    log("[INFO] {} -> {} 하위로 이동".format(root_joint, offset_node))


def create_collider_group(colliders, group_name, log=print):
    """선택한 오브젝트들을 각각 복제하고, 원본이 복제본을 블렌드쉐입으로
    드라이브하도록 연결한 뒤, 복제본들을 group_name 그룹으로 묶어 반환한다."""
    dup_nodes = []

    for col in colliders:
        if not cmds.objExists(col):
            log("Skip: {} is not found.".format(col))
            continue

        dup_name = "{}_collider".format(col)
        if cmds.objExists(dup_name):
            log("[INFO] 기존 콜라이더 복제본 재사용: {}".format(dup_name))
            dup_nodes.append(dup_name)
            continue

        dup = cmds.duplicate(col, name=dup_name)[0]

        shapes = cmds.listRelatives(dup, shapes=True, type="mesh") or []
        if shapes:
            try:
                bs = cmds.blendShape(col, dup, name="{}_bs".format(dup))[0]
                cmds.setAttr("{}.w[0]".format(bs), 1)
            except Exception as e:
                log("[WARNING] blendShape 생성 실패 ({}): {}".format(dup, e))

        log("[INFO] 콜라이더 복제 + blendShape: {} -> {}".format(col, dup))
        dup_nodes.append(dup)

    if not dup_nodes:
        return None

    if cmds.objExists(group_name):
        cmds.parent(dup_nodes, group_name)
        grp = group_name
    else:
        grp = cmds.group(dup_nodes, name=group_name)

    return grp


def create_wind_force_ctrl(name="wind_force_ctrl", log=print):
    """씬에 wind 방향 컨트롤러가 없으면 생성한다.
    additional_force_node로 연결되어 컨트롤러의 회전이 바람 방향을 결정한다
    (위치는 무관 - vectorProduct가 회전/스케일만 반영하는 매트릭스 연산이라서)."""
    if cmds.objExists(name):
        log("[INFO] 기존 wind 컨트롤러 재사용: {}".format(name))
        return name

    if _SCRIPT_DIR not in sys.path:
        sys.path.insert(0, _SCRIPT_DIR)

    try:
        import ctrl_creator_tool
        ctrl = ctrl_creator_tool.create_controller(
            name=name,
            size=15.0,
            offset_suffixes=("OS",),
            color=ctrl_creator_tool.COLORS.get("LightBlue", 18),
        )
    except Exception as e:
        log("[WARNING] ctrl_creator_tool 사용 실패, 기본 로케이터로 대체: {}".format(e))
        ctrl = cmds.spaceLocator(name=name)[0]

    log("[INFO] wind 컨트롤러 생성: {}".format(ctrl))
    return ctrl


def resolve_force_node(name, log=print):
    """지정한 이름의 노드가 씬에 없으면 wind 컨트롤러로 자동 생성한다."""
    if not name:
        return None
    if cmds.objExists(name):
        return name
    return create_wind_force_ctrl(name, log=log)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
class BoneDynamicsTool(QtWidgets.QDialog):
    WINDOW_TITLE = "Bone Dynamics Node Tool"
    WINDOW_OBJ = "BoneDynamicsNodeToolUI"

    def __init__(self, parent=None):
        if parent is None:
            parent = get_maya_main_window()
        super(BoneDynamicsTool, self).__init__(parent)

        self.setObjectName(self.WINDOW_OBJ)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumWidth(480)
        self.setWindowFlags(
            self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
        )

        self._build_widgets()
        self._build_layouts()
        self._build_connections()
        self._check_plugin_status()

    # ------------------------------------------------------------------
    # UI 구성
    # ------------------------------------------------------------------
    def _build_widgets(self):
        self.plugin_status_label = QtWidgets.QLabel()
        self.plugin_install_btn = QtWidgets.QPushButton("플러그인 확인/설치")

        # ── 조인트 체인 ────────────────────────────────────────────────
        self.joint_list = QtWidgets.QListWidget()
        self.joint_list.setMaximumHeight(110)
        self.joint_add_btn = QtWidgets.QPushButton("선택 추가 (순서대로)")
        self.joint_clear_btn = QtWidgets.QPushButton("초기화")

        # ── 옵션 ──────────────────────────────────────────────────────
        self.scalable_chk = QtWidgets.QCheckBox("Scalable (per-section scaling)")
        self.scalable_chk.setChecked(True)
        self.visualize_chk = QtWidgets.QCheckBox("Visualize (angle cone / radius sphere)")
        self.visualize_chk.setChecked(True)

        self.target_postfix_field = QtWidgets.QLineEdit("_target")

        # ── 콜라이더 오브젝트 리스트 ────────────────────────────────────
        self.collider_list = QtWidgets.QListWidget()
        self.collider_list.setMaximumHeight(90)
        self.collider_add_btn = QtWidgets.QPushButton("선택 추가")
        self.collider_clear_btn = QtWidgets.QPushButton("초기화")

        self.force_node_field = QtWidgets.QLineEdit("wind_force_ctrl")
        self.force_pick_btn = QtWidgets.QPushButton("<<")
        self.force_pick_btn.setFixedWidth(32)

        self.force_x_spin = QtWidgets.QDoubleSpinBox()
        self.force_y_spin = QtWidgets.QDoubleSpinBox()
        self.force_z_spin = QtWidgets.QDoubleSpinBox()
        for spin in (self.force_x_spin, self.force_y_spin, self.force_z_spin):
            spin.setRange(-1.0, 1.0)
            spin.setDecimals(2)
        self.force_z_spin.setValue(-1.0)

        # ── 실행 ──────────────────────────────────────────────────────
        self.run_btn = QtWidgets.QPushButton("Create Dynamics Nodes")
        self.run_btn.setFixedHeight(36)
        self.run_btn.setStyleSheet(
            "background-color: #4a7a4a; color: white; "
            "font-weight: bold; font-size: 13px;"
        )

        self.undo_btn = QtWidgets.QPushButton("Undo Last Run")
        self.undo_btn.setFixedHeight(36)
        self.undo_btn.setEnabled(False)
        self.undo_btn.setToolTip("마지막 실행을 하나의 undo 청크로 되돌립니다.")

        # ── 로그 ──────────────────────────────────────────────────────
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(120)
        self.log_text.setStyleSheet(
            "background-color: #1e1e1e; color: #cccccc; "
            "font-family: Consolas, monospace; font-size: 11px;"
        )
        self.clear_log_btn = QtWidgets.QPushButton("Log 지우기")
        self.clear_log_btn.setFixedHeight(22)

    def _build_layouts(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(6)

        plugin_row = QtWidgets.QHBoxLayout()
        plugin_row.addWidget(self.plugin_status_label)
        plugin_row.addStretch()
        plugin_row.addWidget(self.plugin_install_btn)
        main_layout.addLayout(plugin_row)

        # ── 조인트 체인 그룹 ──────────────────────────────────────────
        joint_group = QtWidgets.QGroupBox("Joint Chain (root -> tip 순서로 선택)")
        joint_layout = QtWidgets.QVBoxLayout(joint_group)
        joint_layout.addWidget(self.joint_list)
        joint_btn_row = QtWidgets.QHBoxLayout()
        joint_btn_row.addWidget(self.joint_add_btn)
        joint_btn_row.addWidget(self.joint_clear_btn)
        joint_layout.addLayout(joint_btn_row)
        main_layout.addWidget(joint_group)

        # ── 옵션 그룹 ─────────────────────────────────────────────────
        opt_group = QtWidgets.QGroupBox("Options")
        form = QtWidgets.QFormLayout(opt_group)
        form.setSpacing(6)
        form.addRow(self.scalable_chk)
        form.addRow(self.visualize_chk)
        form.addRow(QtWidgets.QLabel("Target Chain Postfix:"), self.target_postfix_field)

        collider_box = QtWidgets.QVBoxLayout()
        collider_box.addWidget(self.collider_list)
        collider_btn_row = QtWidgets.QHBoxLayout()
        collider_btn_row.addWidget(self.collider_add_btn)
        collider_btn_row.addWidget(self.collider_clear_btn)
        collider_box.addLayout(collider_btn_row)
        form.addRow(QtWidgets.QLabel("Collider Objects:"), collider_box)

        force_row = QtWidgets.QHBoxLayout()
        force_row.addWidget(self.force_node_field)
        force_row.addWidget(self.force_pick_btn)
        form.addRow(QtWidgets.QLabel("Additional Force Node:"), force_row)

        force_vec_row = QtWidgets.QHBoxLayout()
        force_vec_row.addWidget(QtWidgets.QLabel("X"))
        force_vec_row.addWidget(self.force_x_spin)
        force_vec_row.addWidget(QtWidgets.QLabel("Y"))
        force_vec_row.addWidget(self.force_y_spin)
        force_vec_row.addWidget(QtWidgets.QLabel("Z"))
        force_vec_row.addWidget(self.force_z_spin)
        form.addRow(QtWidgets.QLabel("Force Init Vector:"), force_vec_row)

        main_layout.addWidget(opt_group)

        run_row = QtWidgets.QHBoxLayout()
        run_row.addWidget(self.run_btn)
        run_row.addWidget(self.undo_btn)
        main_layout.addLayout(run_row)

        # ── 로그 ─────────────────────────────────────────────────────
        log_header = QtWidgets.QHBoxLayout()
        log_header.addWidget(QtWidgets.QLabel("Log:"))
        log_header.addStretch()
        log_header.addWidget(self.clear_log_btn)
        main_layout.addLayout(log_header)
        main_layout.addWidget(self.log_text)

    def _build_connections(self):
        self.plugin_install_btn.clicked.connect(self._check_plugin_status)
        self.joint_add_btn.clicked.connect(self._add_selected_joints)
        self.joint_clear_btn.clicked.connect(self.joint_list.clear)
        self.collider_add_btn.clicked.connect(self._add_selected_colliders)
        self.collider_clear_btn.clicked.connect(self.collider_list.clear)
        self.force_pick_btn.clicked.connect(lambda: self._pick_single(self.force_node_field))
        self.run_btn.clicked.connect(self._run)
        self.undo_btn.clicked.connect(self._undo_last)
        self.clear_log_btn.clicked.connect(self.log_text.clear)

    # ------------------------------------------------------------------
    # 콜백
    # ------------------------------------------------------------------
    def _check_plugin_status(self):
        try:
            ensure_plugin(log=self._log)
            self.plugin_status_label.setText("Plugin: 로드됨 (boneDynamicsNode)")
            self.plugin_status_label.setStyleSheet("color: #6fbf6f;")
        except Exception as e:
            self.plugin_status_label.setText(f"Plugin: 로드 실패 - {e}")
            self.plugin_status_label.setStyleSheet("color: #d9534f;")
            self._log(f"[ERROR] {e}")

    def _add_selected_joints(self):
        sel = cmds.ls(sl=True, type="joint") or []
        if not sel:
            self._log("[WARNING] 조인트가 선택되지 않았습니다.")
            return
        for jnt in sel:
            self.joint_list.addItem(jnt)
        self._log(f"[INFO] {len(sel)}개 조인트 추가됨.")

    def _add_selected_colliders(self):
        sel = cmds.ls(sl=True) or []
        if not sel:
            self._log("[WARNING] 콜라이더로 사용할 오브젝트가 선택되지 않았습니다.")
            return
        for obj in sel:
            self.collider_list.addItem(obj)
        self._log(f"[INFO] {len(sel)}개 콜라이더 오브젝트 추가됨.")

    def _pick_single(self, field):
        sel = cmds.ls(sl=True) or []
        if not sel:
            self._log("[WARNING] 선택된 오브젝트가 없습니다.")
            return
        field.setText(sel[0])

    def _find_child_path(self, start, target):
        """start 조인트 하위 계층에서 target까지의 경로를 찾는다 (DFS)."""
        if start == target:
            return [start]
        children = cmds.listRelatives(start, children=True, type="joint") or []
        for child in children:
            sub_path = self._find_child_path(child, target)
            if sub_path:
                return [start] + sub_path
        return None

    def _expand_joint_chain(self, joints):
        """리스트에 있는 조인트들 사이가 직접 부모-자식이 아니면
        계층을 따라가며 중간 조인트를 자동으로 채운다."""
        if len(joints) < 2:
            return joints

        expanded = [joints[0]]
        for next_joint in joints[1:]:
            current = expanded[-1]
            if (cmds.listRelatives(next_joint, parent=True) or []) == [current]:
                expanded.append(next_joint)
                continue

            path = self._find_child_path(current, next_joint)
            if not path:
                self._log(
                    f"[WARNING] {current} -> {next_joint} 사이의 경로를 찾을 수 없습니다. 그대로 이어붙입니다."
                )
                expanded.append(next_joint)
                continue

            filled = path[1:]
            if len(filled) > 1:
                self._log(
                    "[INFO] 중간 조인트 자동 보완: {} -> {} ({}개)".format(
                        current, next_joint, len(filled)
                    )
                )
            expanded.extend(filled)

        return expanded

    # ------------------------------------------------------------------
    # 메인 실행 흐름
    # ------------------------------------------------------------------
    def _run(self):
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Running...")
        QtWidgets.QApplication.processEvents()
        cmds.undoInfo(openChunk=True, chunkName="boneDynamicsTool_run")
        try:
            self._execute()
        except Exception as e:
            self._log(f"[ERROR] {e}")
            self._log(traceback.format_exc())
        finally:
            cmds.undoInfo(closeChunk=True)
            self.undo_btn.setEnabled(True)
            self.run_btn.setEnabled(True)
            self.run_btn.setText("Create Dynamics Nodes")

    def _undo_last(self):
        """마지막 실행(전체 청크)을 한 번에 되돌린다."""
        try:
            cmds.undo()
            self._log("[INFO] 마지막 실행을 Undo 했습니다.")
        except Exception as e:
            self._log(f"[ERROR] Undo 실패: {e}")
        finally:
            self.undo_btn.setEnabled(False)

    def _execute(self):
        ensure_plugin(log=self._log)

        joints = [self.joint_list.item(i).text() for i in range(self.joint_list.count())]
        if len(joints) < 2:
            raise ValueError("조인트 체인을 2개 이상 추가해주세요 (root -> tip).")

        joints = self._expand_joint_chain(joints)

        scalable = self.scalable_chk.isChecked()
        visualize = self.visualize_chk.isChecked()
        target_postfix = self.target_postfix_field.text().strip() or "_target"
        collider_objs = [self.collider_list.item(i).text() for i in range(self.collider_list.count())]
        force_node_name = self.force_node_field.text().strip() or "wind_force_ctrl"
        force_vec = (
            self.force_x_spin.value(),
            self.force_y_spin.value(),
            self.force_z_spin.value(),
        )

        if not cmds.objExists(SET_NAME):
            cmds.select(cl=True)
            cmds.sets(name=SET_NAME)

        self._log("=" * 52)
        self._log(f"[START] Bone Dynamics ({len(joints) - 1}개 세그먼트)")
        self._log(f"  Joints   : {' -> '.join(joints)}")
        self._log("=" * 52)

        # ── 타겟 체인 자동 생성 ────────────────────────────────────────
        self._log("[1/4] 타겟 체인 생성...")
        target_joints = create_target_chain(joints, target_postfix, log=self._log)

        # ── offset 노드 자동 생성 (루트 조인트 기준) ───────────────────
        self._log("[2/4] Offset 노드 생성...")
        offset_node = create_offset_node(joints[0], log=self._log)
        attach_offset_to_target(offset_node, target_joints[0], log=self._log)
        parent_root_under_offset(joints[0], offset_node, log=self._log)

        # ── 콜라이더 그룹 자동 생성 (복제 + blendShape) ────────────────
        self._log("[3/4] 콜라이더 그룹 생성...")
        colliders = []
        if collider_objs:
            collider_grp_name = "{}_colliderGrp".format(joints[0])
            collider_grp = create_collider_group(collider_objs, collider_grp_name, log=self._log)
            if collider_grp:
                colliders = cmds.ls(cmds.listRelatives(collider_grp, c=True) or [], tr=True) or []
        else:
            self._log("[INFO] 콜라이더 오브젝트가 없어 스킵합니다.")

        # ── wind 컨트롤러 자동 생성 ────────────────────────────────────
        self._log("[4/4] Wind 컨트롤러 확인/생성...")
        force_node = resolve_force_node(force_node_name, log=self._log)

        self._log("=" * 52)

        created = 0
        for bone, end, target_bone in zip(joints[:-1], joints[1:], target_joints[:-1]):
            node = create_dynamics_node(
                bone, end,
                scalable=scalable,
                target_bone=target_bone,
                offset_node=offset_node,
                colliders=colliders,
                visualize=visualize,
                additional_force_node=force_node,
                additional_force_init_vec=force_vec,
                log=self._log,
            )
            if node:
                cmds.sets(node, addElement=SET_NAME)
                self._log(f"  -> {bone} : {node}")
                created += 1

        self._log("=" * 52)
        self._log(f"[DONE] {created}/{len(joints) - 1}개 노드 생성 완료. (Set: {SET_NAME})")
        self._log("=" * 52)

    # ------------------------------------------------------------------
    # 로그 헬퍼
    # ------------------------------------------------------------------
    def _log(self, msg):
        self.log_text.append(str(msg))
        QtWidgets.QApplication.processEvents()


# ---------------------------------------------------------------------------
# 글로벌 인스턴스 관리
# ---------------------------------------------------------------------------
_instance = None


def show():
    global _instance
    try:
        _instance.close()
        _instance.deleteLater()
    except Exception:
        pass
    _instance = BoneDynamicsTool()
    _instance.show()
    return _instance


if __name__ == "__main__":
    show()
