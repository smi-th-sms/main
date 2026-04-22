"""
Rig Develop Tool
================
Advanced Skeleton 빌드 이후 디벨롭/리빌드용 툴.

Feature 1 - IK Settings Controller
    IKLeg_*, IKArm_* 의 transform 제외 custom attrs를
    하위 settings 컨트롤러에 복사 후 dst.attr -> src.attr 연결.

Feature 2 - Weapon Offset Controller
    Fingers_L / Fingers_R 하위에 weapon_offset 계층 생성.
    구조: Fingers_* > *_weapon_offset_OS > *_weapon_offset_CS > *_weapon_offset

Feature 7 - Constraint to Joints
    AS DeformationSystem 조인트 → MH(커스텀) 조인트 parentConstraint + scaleConstraint.
    기본 매핑: MetaHuman 기준 (AS FitJoint base → MH joint base).

Usage:
    import importlib
    import rig_develop_tool
    importlib.reload(rig_develop_tool)
    rig_develop_tool.show()
"""

import os
import sys
import maya.cmds as cmds
import maya.mel as mel

# 패키지 루트를 sys.path 에 등록 – rig_tool_hub 없이 단독 실행해도
# ctrl_creator_tool 등 동일 폴더의 모듈을 바로 import 할 수 있도록 보장
_TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOL_DIR not in sys.path:
    sys.path.insert(0, _TOOL_DIR)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_TRANSFORM_ATTRS = frozenset([
    "translateX", "translateY", "translateZ",
    "rotateX", "rotateY", "rotateZ",
    "scaleX", "scaleY", "scaleZ",
    "visibility",
])

_IK_TARGETS = ["IKLeg_L", "IKLeg_R", "IKArm_L", "IKArm_R"]

# Maya index color
_COLOR_L = 18   # light blue
_COLOR_R = 20   # pink
_COLOR_DEFAULT = 17  # yellow

_WEAPON_COLOR_L = 6   # blue
_WEAPON_COLOR_R = 13  # red

_SETTINGS_SUFFIX = "_Settings"
_SETTINGS_OS_SUFFIX = "_Settings_OS"

# Feature 7 – Constraint to Joints: AS→MH 기본 매핑 (MetaHuman 기준)
_CONSTRAINT_DEFAULT_MAPPING = {
    "Root":          "pelvis",
    "Spine1":        "spine_02",
    "Spine2":        "spine_03",
    "Chest_M":       "spine_04",
    "ChestExtra_M":  "spine_05",
    "Neck0":         "neck_01",
    "Neck1":         "neck_02",
    "Head":          "head",
    "Scapula":       "clavicle",
    "Shoulder":      "upperarm",
    "Elbow":         "lowerarm",
    "Wrist":         "hand",
    "ThumbFinger1":  "thumb_01",
    "ThumbFinger2":  "thumb_02",
    "ThumbFinger3":  "thumb_03",
    "IndexFinger0":  "index_metacarpal",
    "IndexFinger1":  "index_01",
    "IndexFinger2":  "index_02",
    "IndexFinger3":  "index_03",
    "MiddleFinger0": "middle_metacarpal",
    "MiddleFinger1": "middle_01",
    "MiddleFinger2": "middle_02",
    "MiddleFinger3": "middle_03",
    "RingFinger0":   "ring_metacarpal",
    "RingFinger1":   "ring_01",
    "RingFinger2":   "ring_02",
    "RingFinger3":   "ring_03",
    "PinkyFinger0":  "pinky_metacarpal",
    "PinkyFinger1":  "pinky_01",
    "PinkyFinger2":  "pinky_02",
    "PinkyFinger3":  "pinky_03",
    "Hip":           "thigh",
    "Knee":          "calf",
    "Ankle":         "foot",
    "Toes":          "ball",
}

_COMMON_SIDE_PAIRS = [
    ("_r", "_l"), ("_R", "_L"),
    ("Right", "Left"), ("right", "left"),
    ("R_", "L_"),
]

# Feature 7 – Namespace 자동 감지 힌트
_NS_NONE_LABEL = "(없음)"
_AS_NS_HINTS = {"DeformationSystem", "FitSkeleton", "AdvancedSkeleton"}
_MH_NS_HINTS = {"pelvis", "spine_01", "thigh_r", "thigh_l"}


# ===========================================================================
# Utilities
# ===========================================================================

def _ns_prefix(namespace):
    return (namespace + ":") if namespace else ""


def _scene_namespaces():
    """씬 내 사용자 namespace 목록 반환 (UI/shared 제외)."""
    try:
        all_ns = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
    except Exception:
        all_ns = []
    return [ns for ns in all_ns if ns not in ("UI", "shared", ":")]


def _guess_ns(namespaces, hints):
    """hints 노드가 존재하는 첫 번째 namespace 반환."""
    for ns in namespaces:
        for hint in hints:
            if cmds.objExists(ns + ":" + hint):
                return ns
    return None


def _detect_namespace_from_selection():
    """선택된 오브젝트에서 namespace 추출. 선택이 없으면 씬 전체 탐색."""
    sel = cmds.ls(selection=True, long=False) or []
    for node in sel:
        if ":" in node:
            # 마지막 "|" 이후의 short name에서 namespace 추출
            short = node.rsplit("|", 1)[-1]
            ns = ":".join(short.split(":")[:-1])
            if ns:
                return ns
    # 선택 없거나 namespace 없으면 씬 전체에서 Fingers_L 기준 탐색
    for ns in (cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []):
        if cmds.objExists(ns + ":Fingers_L"):
            return ns
    return ""


def _detect_namespace():
    return _detect_namespace_from_selection()


def _get_custom_attrs(node):
    """keyable 속성 중 transform 제외한 user-defined attrs 반환."""
    all_attrs = cmds.listAttr(node, keyable=True) or []
    return [a for a in all_attrs if a not in _TRANSFORM_ATTRS]


def _get_attr_def(node, attr):
    """
    attr 정의 정보 dict 반환.
    keys: type, default, has_min, has_max, min, max, enum_names
    """
    attr_type = cmds.getAttr(node + "." + attr, type=True)
    default_val = cmds.getAttr(node + "." + attr)
    has_min = cmds.attributeQuery(attr, node=node, minExists=True)
    has_max = cmds.attributeQuery(attr, node=node, maxExists=True)
    mn = cmds.attributeQuery(attr, node=node, minimum=True)[0] if has_min else None
    mx = cmds.attributeQuery(attr, node=node, maximum=True)[0] if has_max else None
    enum_names = None
    if attr_type == "enum":
        enum_list = cmds.attributeQuery(attr, node=node, listEnum=True)
        enum_names = enum_list[0] if enum_list else "off:on"
    return {
        "type": attr_type,
        "default": default_val,
        "has_min": has_min,
        "has_max": has_max,
        "min": mn,
        "max": mx,
        "enum_names": enum_names,
    }


def _add_attr_from_def(node, attr, attr_def):
    """attr_def 기반으로 node에 attr 추가."""
    if cmds.attributeQuery(attr, node=node, exists=True):
        return  # 이미 존재하면 스킵
    attr_type = attr_def["type"]
    kwargs = dict(longName=attr, keyable=True)

    if attr_type == "enum":
        kwargs["attributeType"] = "enum"
        kwargs["enumName"] = attr_def["enum_names"]
        kwargs["defaultValue"] = int(attr_def["default"])
    elif attr_type in ("double", "float", "long", "short", "bool", "byte"):
        kwargs["attributeType"] = attr_type
        kwargs["defaultValue"] = attr_def["default"]
        if attr_def["has_min"]:
            kwargs["minValue"] = attr_def["min"]
        if attr_def["has_max"]:
            kwargs["maxValue"] = attr_def["max"]
    else:
        # 지원하지 않는 타입은 경고 후 스킵
        cmds.warning("rig_develop_tool: unsupported attr type '{}' for '{}.{}', skipped.".format(
            attr_type, node, attr))
        return

    cmds.addAttr(node, **kwargs)
    cmds.setAttr(node + "." + attr, attr_def["default"])


def _make_circle_ctrl(name, radius=1.0, normal=(0, 1, 0), color=_COLOR_DEFAULT):
    """NURBS circle 컨트롤러 생성 후 이름/색상 설정."""
    ctrl = cmds.circle(
        name=name, radius=radius,
        normalX=normal[0], normalY=normal[1], normalZ=normal[2],
        ch=False
    )[0]
    for sh in (cmds.listRelatives(ctrl, shapes=True) or []):
        cmds.setAttr(sh + ".overrideEnabled", 1)
        cmds.setAttr(sh + ".overrideColor", color)
        cmds.rename(sh, name + "Shape")
    return ctrl


def _safe_delete(node):
    if cmds.objExists(node):
        cmds.delete(node)


# ===========================================================================
# Feature 1 – IK Settings Controller
# ===========================================================================

def build_ik_settings_ctrls(namespace="", ik_targets=None, ctrl_size=3.0):
    """
    IKLeg_*/IKArm_* 각각의 하위에 Settings 컨트롤러 생성.

    Parameters
    ----------
    namespace : str
        리그 네임스페이스 (없으면 "")
    ik_targets : list[str] or None
        대상 IK ctrl 베이스 이름 리스트. None이면 기본 4개 사용.
    ctrl_size : float
        Settings ctrl 반지름

    Returns
    -------
    list[str]  생성된 settings ctrl 이름 리스트
    """
    if ik_targets is None:
        ik_targets = list(_IK_TARGETS)

    ns = _ns_prefix(namespace)
    created = []

    for base in ik_targets:
        ik_ctrl = ns + base
        if not cmds.objExists(ik_ctrl):
            cmds.warning("rig_develop_tool: IK ctrl not found – " + ik_ctrl)
            continue

        side = "L" if base.endswith("_L") else "R"
        color = _COLOR_L if side == "L" else _COLOR_R

        settings_name = base + _SETTINGS_SUFFIX
        os_name = base + _SETTINGS_OS_SUFFIX

        # --- Rebuild: 기존 offset group 삭제 (자식 포함 정리) ---
        _safe_delete(ns + os_name)

        # --- custom attrs 수집 (삭제 전에) ---
        custom_attrs = _get_custom_attrs(ik_ctrl)
        if not custom_attrs:
            cmds.warning("rig_develop_tool: no custom attrs on " + ik_ctrl)
            continue

        attr_defs = {}
        for a in custom_attrs:
            attr_defs[a] = _get_attr_def(ik_ctrl, a)

        # --- Offset Group ---
        os_grp = cmds.group(empty=True, name=os_name, parent=ik_ctrl)
        cmds.xform(os_grp, objectSpace=True,
                   translation=[0, 0, 0], rotation=[0, 0, 0], scale=[1, 1, 1])

        # R side 반전: IKArm_R → rx=180, IKLeg_R → ry=180
        if side == "R":
            if "IKArm" in base:
                cmds.setAttr(os_grp + ".rotateX", 180)
            elif "IKLeg" in base:
                cmds.setAttr(os_grp + ".rotateY", 180)

        # --- Settings Ctrl ---
        ctrl = _make_circle_ctrl(settings_name, radius=ctrl_size,
                                 normal=(0, 1, 0), color=color)
        cmds.parent(ctrl, os_grp)
        cmds.xform(ctrl, objectSpace=True,
                   translation=[0, 0, 0], rotation=[0, 0, 0], scale=[1, 1, 1])

        # transform 채널 lock & hide
        for at in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v"):
            cmds.setAttr(ctrl + "." + at, lock=True, keyable=False, channelBox=False)

        # --- Attrs 복사 및 연결 (ctrl.attr -> ik_ctrl.attr) ---
        for a in custom_attrs:
            _add_attr_from_def(ctrl, a, attr_defs[a])

            src_plug = ctrl + "." + a
            dst_plug = ik_ctrl + "." + a

            # dst에 이미 incoming connection이 있으면 경고 후 스킵
            existing_in = cmds.listConnections(
                dst_plug, source=True, destination=False, plugs=True) or []
            if existing_in:
                cmds.warning(
                    "rig_develop_tool: {}.{} already has incoming connection ({}), skipped.".format(
                        ik_ctrl, a, existing_in[0]))
                continue

            if not cmds.isConnected(src_plug, dst_plug):
                cmds.connectAttr(src_plug, dst_plug)

            # IK ctrl의 연결된 attr lock & hide
            cmds.setAttr(dst_plug, lock=True, keyable=False, channelBox=False)

        print("rig_develop_tool: built settings ctrl – " + settings_name)
        created.append(ctrl)

    return created


# ===========================================================================
# Feature 2 – Weapon Offset Controller
# ===========================================================================

def build_weapon_offset(namespace="", side="L", size=8.0):
    """
    Fingers_L/R 하위에 weapon_offset 계층 생성.

    Parameters
    ----------
    namespace : str
    side : str  "L" or "R"
    size : float  ctrl 반지름

    Returns
    -------
    str or None  생성된 ctrl 이름
    """
    ns = _ns_prefix(namespace)
    fingers = ns + "Fingers_" + side
    color = _WEAPON_COLOR_L if side == "L" else _WEAPON_COLOR_R

    if not cmds.objExists(fingers):
        cmds.warning("rig_develop_tool: {} not found.".format(fingers))
        return None

    os_name = side + "_weapon_offset_OS"
    cs_name = side + "_weapon_offset_CS"
    ctrl_name = side + "_weapon_offset"

    # Rebuild
    _safe_delete(ns + os_name)

    ref_pos = cmds.xform(fingers, query=True, worldSpace=True, translation=True)
    ref_rot = cmds.xform(fingers, query=True, worldSpace=True, rotation=True)

    os_grp = cmds.group(empty=True, name=os_name, parent=fingers)
    cmds.xform(os_grp, worldSpace=True, translation=ref_pos, rotation=ref_rot)

    cs_grp = cmds.group(empty=True, name=cs_name, parent=os_grp)

    ctrl = cmds.circle(name=ctrl_name, radius=size,
                       normalX=0, normalY=1, normalZ=0, ch=False)[0]
    cmds.parent(ctrl, cs_grp)
    cmds.xform(ctrl, objectSpace=True,
               translation=[0, 0, 0], rotation=[0, 0, 0], scale=[1, 1, 1])

    for sh in (cmds.listRelatives(ctrl, shapes=True) or []):
        cmds.setAttr(sh + ".overrideEnabled", 1)
        cmds.setAttr(sh + ".overrideColor", color)
        cmds.rename(sh, side + "_weapon_offsetShape")

    print("rig_develop_tool: built weapon offset – " + ctrl_name)
    return ctrl


def build_weapon_offsets(namespace="", size=8.0):
    """L/R 양쪽 weapon_offset 생성."""
    results = []
    for side in ("L", "R"):
        c = build_weapon_offset(namespace=namespace, side=side, size=size)
        if c:
            results.append(c)
    return results


# ===========================================================================
# Feature 3 – Main Hierarchy (Master / Global / MainHip)
# ===========================================================================

# ctrl name : (color index, default radius)
_MAIN_CTRL_DEFAULTS = {
    "Global":  (16,             120.0),  # white
    "Master":  (_COLOR_DEFAULT, 100.0),  # yellow
    "MainHip": (18,              40.0),  # cyan
}


def build_main_hierarchy(namespace="",
                         master_size=100.0,
                         global_size=120.0,
                         mainhip_size=40.0):
    """
    MainSystem 내에 Global > Master > MainHip_OS > MainHip > Main_OS > Main 계층 구성.

    - Global, Master : world zero
    - MainHip_OS, MainHip : Root_M 월드 위치
    - Main_OS : 기존 Main 월드 위치
    - 기존 Main 은 Main_OS 하위로 재배치

    Parameters
    ----------
    namespace : str
    master_size, global_size, mainhip_size : float  각 ctrl 반지름

    Returns
    -------
    dict  {"Global": node, "Master": node, "MainHip": node, "Main_OS": node}
    """
    ns = _ns_prefix(namespace)

    main_system = ns + "MainSystem"
    main_ctrl   = ns + "Main"
    root_m      = ns + "Root_M"

    for node in (main_system, main_ctrl):
        if not cmds.objExists(node):
            cmds.warning("rig_develop_tool: not found – " + node)
            return {}

    global_name    = ns + "Global"
    master_name    = ns + "Master"
    mainhip_os_name = ns + "MainHip_OS"
    mainhip_name   = ns + "MainHip"
    main_os_name   = ns + "Main_OS"

    # ── Rebuild safety: Main 을 MainSystem 바로 아래로 이동 ──────────────
    cur_parent = (cmds.listRelatives(main_ctrl, parent=True, fullPath=False) or [""])[0]
    if cur_parent != "MainSystem":
        cmds.parent(main_ctrl, main_system)

    # ── 기존 Global 트리 삭제 (cascade) ──────────────────────────────────
    if cmds.objExists(global_name):
        cmds.delete(global_name)

    # ── Root_M 위치 ───────────────────────────────────────────────────────
    if cmds.objExists(root_m):
        hip_pos = cmds.xform(root_m, query=True, worldSpace=True, translation=True)
    else:
        cmds.warning("rig_develop_tool: Root_M not found, MainHip placed at origin.")
        hip_pos = [0.0, 0.0, 0.0]

    # ── Global (world zero, under MainSystem) ────────────────────────────
    global_ctrl = _make_circle_ctrl(global_name, radius=global_size,
                                    normal=(0, 1, 0), color=16)
    cmds.parent(global_ctrl, main_system)
    cmds.xform(global_ctrl, worldSpace=True,
               translation=[0, 0, 0], rotation=[0, 0, 0], scale=[1, 1, 1])

    # ── Master (world zero, under Global) ────────────────────────────────
    master = _make_circle_ctrl(master_name, radius=master_size,
                               normal=(0, 1, 0), color=_COLOR_DEFAULT)
    cmds.parent(master, global_ctrl)
    cmds.xform(master, objectSpace=True,
               translation=[0, 0, 0], rotation=[0, 0, 0], scale=[1, 1, 1])

    # ── MainHip_OS (Root_M 위치, under Master) ───────────────────────────
    mainhip_os = cmds.group(empty=True, name=mainhip_os_name, parent=master)
    cmds.xform(mainhip_os, worldSpace=True,
               translation=hip_pos, rotation=[0, 0, 0], scale=[1, 1, 1])

    # ── MainHip (under MainHip_OS) ────────────────────────────────────────
    mainhip = _make_circle_ctrl(mainhip_name, radius=mainhip_size,
                                normal=(0, 1, 0), color=18)
    cmds.parent(mainhip, mainhip_os)
    cmds.xform(mainhip, objectSpace=True,
               translation=[0, 0, 0], rotation=[0, 0, 0], scale=[1, 1, 1])

    # ── Main 월드 트랜스폼 기록 (parent 변경 전) ──────────────────────────
    main_ws_t = cmds.xform(main_ctrl, query=True, worldSpace=True, translation=True)
    main_ws_r = cmds.xform(main_ctrl, query=True, worldSpace=True, rotation=True)

    # ── Main_OS (Main 월드 위치에 배치, under MainHip) ────────────────────
    main_os = cmds.group(empty=True, name=main_os_name, parent=mainhip)
    cmds.xform(main_os, worldSpace=True,
               translation=main_ws_t, rotation=main_ws_r)

    # ── Main → Main_OS 하위로 재배치 ──────────────────────────────────────
    cmds.parent(main_ctrl, main_os)

    # ── Main → metahuman root parentConstraint ────────────────────────────
    mh_root = ns + "root"
    if not cmds.objExists(mh_root):
        # namespace 없는 경우도 탐색
        mh_root_candidates = cmds.ls("root", type="joint") or []
        mh_root = mh_root_candidates[0] if mh_root_candidates else ""

    if mh_root and cmds.objExists(mh_root):
        # rebuild 시: root 에 걸린 parentConstraint 중 Main 이 타겟인 것만 제거
        for pc in (cmds.listRelatives(mh_root, type="parentConstraint") or []):
            try:
                targets = cmds.parentConstraint(pc, query=True, targetList=True) or []
                if main_ctrl in targets or main_ctrl.split(":")[-1] in [t.split(":")[-1] for t in targets]:
                    cmds.parentConstraint(main_ctrl, mh_root, edit=True, remove=True)
                    if not (cmds.parentConstraint(pc, query=True, targetList=True) or []):
                        _safe_delete(pc)
            except Exception:
                pass
        try:
            cmds.parentConstraint(main_ctrl, mh_root, maintainOffset=True)
            print("rig_develop_tool: parentConstraint Main -> {}".format(mh_root))
        except RuntimeError as e:
            cmds.warning("rig_develop_tool: parentConstraint failed – " + str(e))
    else:
        cmds.warning("rig_develop_tool: metahuman root joint not found – parentConstraint skipped.")

    print("rig_develop_tool: built  MainSystem > Global > Master > MainHip_OS > MainHip > Main_OS > Main")
    return {"Global": global_ctrl, "Master": master, "MainHip": mainhip, "Main_OS": main_os}


# ===========================================================================
# Feature 4 – correctiveRoot rx Mute Setup
# ===========================================================================

def build_corrective_root_rx_mute(namespace=""):
    """
    *correctiveRoot_* 조인트들에 rx Mute 셋업 구성.

    조인트에 rxLock(long, 0/1) 추가 후:
      rl4Embedded[INDEX] ──→ condition.colorIfFalseR  (rxLock=0: pass-through)
                             condition.colorIfTrueR = 0  (rxLock=1: mute)
      rxLock ──────────────→ condition.firstTerm (== 1?)
                             condition.outColorR ──→ joint.rx

    rxLock=1: joint.rx = 0        (mute)
    rxLock=0: joint.rx = original (pass-through)

    이미 rxLock 이 있는 조인트는 스킵.

    Parameters
    ----------
    namespace : str

    Returns
    -------
    list[str]  셋업 완료된 조인트 목록
    """
    pattern = "*:*correctiveRoot*" if not namespace else namespace + ":*correctiveRoot*"
    all_corr = cmds.ls(pattern, type="joint") or []
    # namespace 없는 경우도 포함
    all_corr += [j for j in (cmds.ls("*correctiveRoot*", type="joint") or [])
                 if j not in all_corr]

    if not all_corr:
        cmds.warning("rig_develop_tool: no *correctiveRoot* joints found.")
        return []

    done = []
    for jnt in all_corr:
        short = jnt.rsplit(":", 1)[-1]

        # 이미 셋업된 경우 스킵
        if cmds.attributeQuery("rxLock", node=jnt, exists=True):
            print("rig_develop_tool: {} already has rxLock – skipped.".format(short))
            continue

        # 현재 rx 소스 확인
        rx_srcs = cmds.listConnections(jnt + ".rx", source=True, destination=False, plugs=True) or []
        if not rx_srcs:
            cmds.warning("rig_develop_tool: {}.rx has no source – skipped.".format(short))
            continue
        rx_src = rx_srcs[0]

        # rxLock attr 추가 (long, 0/1) – 기본값 0 으로 생성 후 즉시 1(mute) 로 활성화
        cmds.addAttr(jnt, longName="rxLock", attributeType="long",
                     minValue=0, maxValue=1, defaultValue=0, keyable=True)
        cmds.setAttr(jnt + ".rxLock", 1)

        # ── condition 노드 생성 ────────────────────────────────────────────
        cond = cmds.createNode("condition", name=short + "_rxMute_cond")

        # rxLock == 1 → colorIfTrue(0)  /  rxLock != 1 → colorIfFalse(original)
        cmds.setAttr(cond + ".operation",    0)     # equal
        cmds.setAttr(cond + ".secondTerm", 1.0)
        cmds.setAttr(cond + ".colorIfTrueR",  0.0)  # mute → 0
        cmds.setAttr(cond + ".colorIfTrueG",  0.0)
        cmds.setAttr(cond + ".colorIfTrueB",  0.0)
        cmds.connectAttr(jnt + ".rxLock", cond + ".firstTerm")
        cmds.connectAttr(rx_src,          cond + ".colorIfFalseR")  # pass-through

        # ── joint.rx 재연결 ────────────────────────────────────────────────
        cmds.disconnectAttr(rx_src, jnt + ".rx")
        cmds.connectAttr(cond + ".outColorR", jnt + ".rx")

        print("rig_develop_tool: built rxMute – " + short)
        done.append(jnt)

    return done


# ===========================================================================
# Feature 5 – IKSpine Handle Fix
# ===========================================================================

_IKSPINE_CONSTRAINTS = [
    "IKXRoot_M_parentConstraint1",
    "IKXSpine1_M_parentConstraint1",
    "IKXSpine2_M_parentConstraint1",
]


def fix_ikspine_handle(namespace=""):
    """
    FitSkeleton Root 조인트에 worldOrientForward attr 가 있으면:
      1. IKSpineHandle_M.dForwardAxis = 2
      2. IKXRoot_M / IKXSpine1_M / IKXSpine2_M parentConstraint 의
         constraintRotate 값을 target[0].targetOffsetRotate 에 set

    Parameters
    ----------
    namespace : str

    Returns
    -------
    bool  실행 여부
    """
    ns = _ns_prefix(namespace)

    # FitSkeleton Root 조인트 탐색
    fit_root = None
    for candidate in (ns + "Root", "Root"):
        if cmds.objExists(candidate) and cmds.nodeType(candidate) == "joint":
            fit_root = candidate
            break
    # FitSkeleton 하위에서도 탐색
    if fit_root is None:
        fit_sk = ns + "FitSkeleton"
        if cmds.objExists(fit_sk):
            descendants = cmds.listRelatives(fit_sk, allDescendents=True, type="joint") or []
            for j in descendants:
                short = j.rsplit("|", 1)[-1].rsplit(":", 1)[-1]
                if short == "Root":
                    fit_root = j
                    break

    if fit_root is None:
        cmds.warning("rig_develop_tool: FitSkeleton Root joint not found.")
        return False

    has_attr = cmds.attributeQuery("worldOrientForward", node=fit_root, exists=True)
    if not has_attr:
        cmds.warning("rig_develop_tool: {}.worldOrientForward not found. Skipped.".format(fit_root))
        return False

    print("rig_develop_tool: worldOrientForward detected on " + fit_root)

    # 1. IKSpineHandle_M.dForwardAxis = 2
    spine_handle = ns + "IKSpineHandle_M"
    if cmds.objExists(spine_handle):
        cmds.setAttr(spine_handle + ".dForwardAxis", 2)
        print("rig_develop_tool: set {}.dForwardAxis = 2".format(spine_handle))
    else:
        cmds.warning("rig_develop_tool: {} not found.".format(spine_handle))

    # 2. constraintRotate → target[0].targetOffsetRotate
    for con_base in _IKSPINE_CONSTRAINTS:
        con = ns + con_base
        if not cmds.objExists(con):
            cmds.warning("rig_develop_tool: constraint not found – " + con)
            continue

        _TOLERANCE = 1e-4
        _MAX_ITER  = 10

        axes = ("X", "Y", "Z")
        plugs = ["{}.target[0].targetOffsetRotate{}".format(con, ax) for ax in axes]

        # lock 상태 저장 후 해제
        locks = [cmds.getAttr(p, lock=True) for p in plugs]
        for p in plugs:
            cmds.setAttr(p, lock=False)

        zeroed = False
        for iteration in range(_MAX_ITER):
            cr = cmds.getAttr(con + ".constraintRotate")[0]   # (rx, ry, rz)

            # constraintRotate 가 이미 0 에 가까우면 종료
            if all(abs(v) < _TOLERANCE for v in cr):
                zeroed = True
                break

            # 현재 targetOffsetRotate 에 cr * -1 누적
            for i, p in enumerate(plugs):
                current = cmds.getAttr(p)
                cmds.setAttr(p, current + cr[i] * -1.0)

        # lock 복원
        for p, lk in zip(plugs, locks):
            if lk:
                cmds.setAttr(p, lock=True)

        final_tor = cmds.getAttr(con + ".target[0].targetOffsetRotate")[0]
        final_cr  = cmds.getAttr(con + ".constraintRotate")[0]
        status = "zeroed" if zeroed else "max_iter reached"
        print("rig_develop_tool: {} [{}] constraintRotate={} targetOffsetRotate={}".format(
            con_base, status,
            tuple(round(v, 6) for v in final_cr),
            tuple(round(v, 6) for v in final_tor)))

    return True


# ===========================================================================
# Feature 6 – Shape / Color 적용 + ControlSet 등록
# ===========================================================================

# ctrl 베이스 이름 → preset 키 매핑
_CTRL_PRESET_MAP = [
    ("IKLeg_L_Settings",  "IKLeg_side_switch_ANI"),
    ("IKLeg_R_Settings",  "IKLeg_side_switch_ANI"),
    ("IKArm_L_Settings",  "IKArm_side_switch_ANI"),
    ("IKArm_R_Settings",  "IKArm_side_switch_ANI"),
    ("L_weapon_offset",   "side_weapon_offset"),
    ("R_weapon_offset",   "side_weapon_offset"),
    ("Master",            "Master"),
    ("Global",            "Global"),
    ("MainHip",           "MainHip"),
    # FK Spine / Chest
    ("FKRoot_M",          "FKRoot_side"),
    ("FKSpine1_M",        "FKRoot_side"),
    ("FKSpine2_M",        "FKRoot_side"),
    ("FKChest_M",         "FKRoot_side"),
    ("FKChestExtra_M",    "FKRoot_side"),
    # FK Neck / Head
    ("FKNeck0_M",         "FKNeck_M"),
    ("FKHead_M",          "FKHead_M"),
]

_CONTROL_SET_NAME = "ControlSet"

# Shape 적용 후 CV 회전이 필요한 컨트롤러 목록
# (ctrl_base, axis, degrees)  – 90도 1회 = 90
_CV_ROTATE_MAP = [
    ("FKNeck1_M",        "z", 90),
    ("HipSwinger_M",     "x", 90),
    ("IKSpine3_M",       "z", 90),
    ("IKhybridSpine3_M", "z", 90),
    ("IKhybridSpine1_M", "z", 90),
    ("IKSpine1_M",       "z", 90),
]


def _apply_shape_from_data(ctrl, shape_data, color_idx):
    """
    preset shape_data 를 ctrl 에 적용.
    ctrl_creator_tool 의 _remove_shapes 를 재사용하여 기존 shape 제거 후 교체.
    """
    import ctrl_creator_tool as _cct

    pts    = shape_data.get("pts", [])
    degree = shape_data.get("degree", 1)
    form   = shape_data.get("form", 0)

    if not pts:
        cmds.warning("rig_develop_tool: empty pts in shape_data for " + ctrl)
        return

    # 기존 shape 제거 (referenced 면 숨김)
    _cct._remove_shapes(ctrl)

    # 임시 커브 생성
    tmp = cmds.curve(d=degree, p=pts)

    # periodic 커브 처리
    if form == 2:
        tmp_sh = cmds.listRelatives(tmp, shapes=True)[0]
        cmds.closeCurve(tmp_sh, ch=False, ps=True, rpo=True)

    # long path 재확인
    tmp_fp = cmds.ls(tmp, long=True)[0]
    tmp_shapes = cmds.listRelatives(tmp_fp, shapes=True, fullPath=True) or []
    if not tmp_shapes:
        cmds.delete(tmp_fp)
        cmds.warning("rig_develop_tool: failed to create shape for " + ctrl)
        return

    # shape 을 ctrl 하위로 이동 (relative=True → ctrl 의 local space 유지)
    cmds.parent(tmp_shapes[0], ctrl, shape=True, relative=True)
    cmds.delete(tmp_fp)

    # shape 이름 정리 (intermediate 제외 → 새로 추가된 shape 만 타겟)
    ctrl_short = ctrl.split("|")[-1].split(":")[-1]
    target_name = ctrl_short + "Shape"
    vis_shs = cmds.listRelatives(ctrl, shapes=True, noIntermediate=True) or []
    if vis_shs:
        new_sh = vis_shs[-1]
        if new_sh.split(":")[-1] != target_name:
            cmds.rename(new_sh, target_name)

    # 색상 적용
    for sh in (cmds.listRelatives(ctrl, shapes=True, noIntermediate=True) or []):
        cmds.setAttr(sh + ".overrideEnabled", 1)
        cmds.setAttr(sh + ".overrideColor", color_idx if color_idx else 0)


def _rotate_shape_cvs(ctrl, axis, degrees):
    """컨트롤러 shape 의 CV 를 object space 기준으로 지정 축 회전."""
    if not cmds.objExists(ctrl):
        cmds.warning("rig_develop_tool: ctrl not found for CV rotate – " + ctrl)
        return
    rx = degrees if axis == "x" else 0
    ry = degrees if axis == "y" else 0
    rz = degrees if axis == "z" else 0
    try:
        cmds.rotate(rx, ry, rz, ctrl + ".cv[*]", r=True, os=True)
        print("rig_develop_tool: CV rotated [{}  {}deg] -> {}".format(
            axis, degrees, ctrl.split(":")[-1]))
    except Exception as e:
        cmds.warning("rig_develop_tool: CV rotate failed for {} – {}".format(
            ctrl, str(e)))


def _add_to_control_set(ctrls, namespace=""):
    """ctrls 를 ControlSet 에 추가 (중복 방지)."""
    ns = _ns_prefix(namespace)
    set_name = ns + _CONTROL_SET_NAME
    if not cmds.objExists(set_name):
        cmds.warning("rig_develop_tool: ControlSet not found – " + set_name)
        return
    for ctrl in ctrls:
        if cmds.objExists(ctrl):
            already = cmds.sets(ctrl, isMember=set_name)
            if not already:
                cmds.sets(ctrl, addElement=set_name)
                print("rig_develop_tool: ControlSet += " + ctrl.split(":")[-1])


def build_shape_and_controlset(namespace=""):
    """
    rig_develop_tool 에서 생성된 컨트롤러에 preset shape/color 적용 후 ControlSet 등록.

    ctrl_creator_tool 의 load_presets / COLORS / _remove_shapes 를 재사용.

    Parameters
    ----------
    namespace : str

    Returns
    -------
    list[str]  처리된 ctrl 목록
    """
    import ctrl_creator_tool as _cct

    presets = _cct.load_presets()
    colors  = _cct.COLORS
    ns      = _ns_prefix(namespace)

    applied = []
    for ctrl_base, preset_key in _CTRL_PRESET_MAP:
        ctrl = ns + ctrl_base
        if not cmds.objExists(ctrl):
            cmds.warning("rig_develop_tool: ctrl not found – " + ctrl_base)
            continue

        preset = presets.get(preset_key)
        if not preset:
            cmds.warning("rig_develop_tool: preset not found – " + preset_key)
            continue

        shape_data  = preset.get("shape", {})
        color_name  = preset.get("color", "None")
        color_idx   = colors.get(color_name, 0)

        _apply_shape_from_data(ctrl, shape_data, color_idx)
        applied.append(ctrl)
        print("rig_develop_tool: shape applied [{preset}] -> {ctrl}".format(
            preset=preset_key, ctrl=ctrl_base))

    # ControlSet 등록
    _add_to_control_set(applied, namespace=namespace)

    # CV 회전 적용 (shape 교체 여부와 무관하게 독립 실행)
    for ctrl_base, axis, degrees in _CV_ROTATE_MAP:
        _rotate_shape_cvs(ns + ctrl_base, axis, degrees)

    return applied


# ===========================================================================
# Feature 7 – Constraint to Joints
# ===========================================================================

def _resolve_target_joint(base_mh, as_side, ns_b,
                           side_right, side_left):
    """
    AS side (_R / _L / _M) 기준으로 타겟 조인트 이름 결정.

    우선순위:
      1. side suffix 설정값 적용 이름 → 씬 존재 확인
      2. 이름 내 공통 side 패턴 자동 감지 후 치환 → 존재 확인
      3. base_mh 그대로 (side 없는 중립 조인트)

    namespace 포함 full name 반환.
    """
    def _apply(name, s):
        return (name + "_" + s) if s else name

    def _full(name):
        return (ns_b + ":" + name) if ns_b else name

    if as_side == "_M":
        return _full(base_mh)

    if as_side == "_R":
        cand = _apply(base_mh, side_right) if side_right else base_mh
        if cmds.objExists(_full(cand)):
            return _full(cand)
        return _full(base_mh)

    # _L
    if side_left:
        cand = _apply(base_mh, side_left)
        if cmds.objExists(_full(cand)):
            return _full(cand)

    # 이름 내 side 패턴 자동 감지 → 치환
    for r_pat, l_pat in _COMMON_SIDE_PAIRS:
        if r_pat in base_mh:
            resolved = base_mh.replace(r_pat, l_pat, 1)
            if cmds.objExists(_full(resolved)):
                return _full(resolved)

    return _full(base_mh)


def constraint_to_joints(ns_as="", ns_mh="",
                         side_right="r", side_left="l",
                         mapping=None):
    """
    AS DeformationSystem 조인트 → 커스텀(MH) 조인트 parentConstraint + scaleConstraint.

    Parameters
    ----------
    ns_as      : str   AS 리그 namespace
    ns_mh      : str   MH(타겟) 스켈레톤 namespace
    side_right : str   MH 오른쪽 side suffix (예: "r" → "_r", "R" → "_R")
    side_left  : str   MH 왼쪽 side suffix  (예: "l" → "_l", "L" → "_L")
    mapping    : dict or None  {AS base → MH base}. None이면 기본 MetaHuman 매핑 사용.

    Returns
    -------
    int  constraint 적용된 조인트 수
    """
    if mapping is None:
        mapping = _CONSTRAINT_DEFAULT_MAPPING

    deform_top = (ns_as + ":" if ns_as else "") + "DeformationSystem"
    if not cmds.objExists(deform_top):
        cmds.warning("rig_develop_tool: DeformationSystem 없음 – " + deform_top)
        return 0

    deform_joints = cmds.listRelatives(deform_top, ad=True, type="joint") or []
    count = 0

    for dj in deform_joints:
        if   dj.endswith("_R"): as_side, base = "_R", dj[:-2]
        elif dj.endswith("_L"): as_side, base = "_L", dj[:-2]
        elif dj.endswith("_M"): as_side, base = "_M", dj[:-2]
        else: continue

        if ns_as:
            base = base.replace(ns_as + ":", "", 1)

        if base not in mapping:
            continue

        target = _resolve_target_joint(
            mapping[base], as_side, ns_mh, side_right, side_left
        )

        if not cmds.objExists(target):
            cmds.warning("rig_develop_tool: 타겟 없음, 스킵 – " + target)
            continue

        print("{} -> {}".format(dj, target))

        existing_cons = (
            (cmds.listRelatives(target, type="parentConstraint", children=True) or []) +
            (cmds.listRelatives(target, type="scaleConstraint",  children=True) or [])
        )
        if existing_cons:
            cmds.delete(existing_cons)

        for attr in ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]:
            try:
                cmds.setAttr(target + "." + attr, lock=False)
            except Exception:
                pass

        # AS 조인트 rotateOrder 를 MH 조인트에 동기화 (constraint 전에 설정)
        try:
            ro = cmds.getAttr(dj + ".rotateOrder")
            cmds.setAttr(target + ".rotateOrder", ro)
        except Exception:
            pass

        cmds.parentConstraint(dj, target, mo=True)
        cmds.scaleConstraint(dj, target, mo=True)
        count += 1

    print("rig_develop_tool: Constraint 완료 ({} 조인트)".format(count))
    return count


def revert_constraint_to_joints(ns_as="", ns_mh="",
                                 side_right="r", side_left="l",
                                 mapping=None):
    """
    constraint_to_joints 로 적용된 parentConstraint + scaleConstraint 제거.

    Parameters
    ----------
    ns_as, ns_mh, side_right, side_left, mapping
        constraint_to_joints 와 동일한 파라미터.

    Returns
    -------
    int  constraint 제거된 조인트 수
    """
    if mapping is None:
        mapping = _CONSTRAINT_DEFAULT_MAPPING

    deform_top = (ns_as + ":" if ns_as else "") + "DeformationSystem"
    if not cmds.objExists(deform_top):
        cmds.warning("rig_develop_tool: DeformationSystem 없음 – " + deform_top)
        return 0

    deform_joints = cmds.listRelatives(deform_top, ad=True, type="joint") or []
    count = 0

    for dj in deform_joints:
        if   dj.endswith("_R"): as_side, base = "_R", dj[:-2]
        elif dj.endswith("_L"): as_side, base = "_L", dj[:-2]
        elif dj.endswith("_M"): as_side, base = "_M", dj[:-2]
        else: continue

        if ns_as:
            base = base.replace(ns_as + ":", "", 1)

        if base not in mapping:
            continue

        target = _resolve_target_joint(
            mapping[base], as_side, ns_mh, side_right, side_left
        )

        if not cmds.objExists(target):
            continue

        cons = (
            (cmds.listRelatives(target, type="parentConstraint", children=True) or []) +
            (cmds.listRelatives(target, type="scaleConstraint",  children=True) or [])
        )
        if cons:
            cmds.delete(cons)
            # rotateOrder → XYZ (0) 복원 (MetaHuman 기본값)
            try:
                cmds.setAttr(target + ".rotateOrder", 0)
            except Exception:
                pass
            print("rig_develop_tool: constraint 제거 – " + target)
            count += 1

    print("rig_develop_tool: Constraint Revert 완료 ({} 조인트)".format(count))
    return count


# ===========================================================================
# Revert
# ===========================================================================

def revert_ik_settings_ctrls(namespace=""):
    """
    Feature 1 원상 복구.
    - IK ctrl 의 locked user attrs 연결 해제 + unlock/keyable 복원
    - {base}_Settings_OS group 삭제 (cascade: Settings ctrl 포함)
    """
    ns = _ns_prefix(namespace)
    for base in _IK_TARGETS:
        ik_ctrl = ns + base
        if cmds.objExists(ik_ctrl):
            user_attrs = cmds.listAttr(ik_ctrl, userDefined=True) or []
            for a in user_attrs:
                plug = ik_ctrl + "." + a
                # 1. unlock (locked 상태에서는 disconnectAttr 불가)
                try:
                    cmds.setAttr(plug, lock=False)
                except Exception:
                    pass
                # 2. incoming connection 끊기
                for sp in (cmds.listConnections(plug, source=True,
                                                destination=False, plugs=True) or []):
                    cmds.disconnectAttr(sp, plug)
                # 3. keyable 복원 (연결 해제 후에 적용해야 정상 반영)
                try:
                    cmds.setAttr(plug, keyable=True)
                except Exception:
                    pass

        os_node = ns + base + _SETTINGS_OS_SUFFIX
        _safe_delete(os_node)
        print("rig_develop_tool: revert IK settings – " + base)


def revert_weapon_offsets(namespace=""):
    """Feature 2 원상 복구 – *_weapon_offset_OS group 삭제 (cascade)."""
    ns = _ns_prefix(namespace)
    for side in ("L", "R"):
        os_node = ns + side + "_weapon_offset_OS"
        _safe_delete(os_node)
        print("rig_develop_tool: revert weapon offset – " + side)


def revert_main_hierarchy(namespace=""):
    """
    Feature 3 원상 복구.
    - Main 을 MainSystem 직속으로 이동
    - Global 삭제 (cascade: Master, MainHip 포함)
    """
    ns = _ns_prefix(namespace)
    main_ctrl   = ns + "Main"
    global_name = ns + "Global"
    main_system = ns + "MainSystem"

    # metahuman root joint 의 parentConstraint 중 Main 타겟만 제거
    mh_root = ns + "root"
    if not cmds.objExists(mh_root):
        mh_root_candidates = cmds.ls("root", type="joint") or []
        mh_root = mh_root_candidates[0] if mh_root_candidates else ""

    if mh_root and cmds.objExists(mh_root):
        for pc in (cmds.listRelatives(mh_root, type="parentConstraint") or []):
            try:
                targets = cmds.parentConstraint(pc, query=True, targetList=True) or []
                if main_ctrl in targets or main_ctrl.split(":")[-1] in [t.split(":")[-1] for t in targets]:
                    cmds.parentConstraint(main_ctrl, mh_root, edit=True, remove=True)
                    if not (cmds.parentConstraint(pc, query=True, targetList=True) or []):
                        _safe_delete(pc)
            except Exception:
                pass
        print("rig_develop_tool: revert parentConstraint Main -> root")

    # Main → MainSystem 직속으로
    if cmds.objExists(main_ctrl) and cmds.objExists(main_system):
        cmds.parent(main_ctrl, main_system)
        print("rig_develop_tool: revert Main parent -> MainSystem")

    # Global cascade 삭제
    _safe_delete(global_name)
    print("rig_develop_tool: revert main hierarchy – Global cascade deleted")


def revert_corrective_root_rx_mute(namespace=""):
    """
    Feature 4 원상 복구.
    - condition 노드 + Maya 자동생성 unitConversion 제거
    - 원래 rx 소스 재연결
    - rxLock attr 삭제

    연결 경로 (빌드 후):
      orig_src → condition.colorIfFalseR
      condition.outColorR → [unitConversion] → joint.rx
    """
    pattern = "*:*correctiveRoot*" if not namespace else namespace + ":*correctiveRoot*"
    all_corr = cmds.ls(pattern, type="joint") or []
    all_corr += [j for j in (cmds.ls("*correctiveRoot*", type="joint") or [])
                 if j not in all_corr]

    for jnt in all_corr:
        short = jnt.rsplit(":", 1)[-1]

        # joint.rx 의 직접 소스 탐색
        rx_src_plugs = cmds.listConnections(
            jnt + ".rx", source=True, destination=False, plugs=True) or []

        for plug in rx_src_plugs:
            node = plug.split(".")[0]
            node_type = cmds.nodeType(node)

            cond_node = None
            uc_after_cond = None  # condition 뒤 unitConversion (삭제 대상)

            if node_type == "condition":
                cond_node = node

            elif node_type == "unitConversion":
                # unitConversion.input 의 소스가 condition.outColorR 인지 확인
                uc_in_srcs = cmds.listConnections(
                    node + ".input", source=True,
                    destination=False, plugs=True) or []
                for uc_src in uc_in_srcs:
                    src_node = uc_src.split(".")[0]
                    if cmds.nodeType(src_node) == "condition":
                        cond_node = src_node
                        uc_after_cond = node
                        break

            if cond_node is None:
                continue

            # condition.colorIfFalseR → 원래 소스
            orig_srcs = cmds.listConnections(
                cond_node + ".colorIfFalseR", source=True,
                destination=False, plugs=True) or []

            # jnt.rx 연결 끊기
            cmds.disconnectAttr(plug, jnt + ".rx")

            # 원래 소스 재연결
            if orig_srcs:
                cmds.connectAttr(orig_srcs[0], jnt + ".rx", force=True)

            # condition 삭제 → condition 뒤 unitConversion 도 삭제
            if cmds.objExists(cond_node):
                cmds.delete(cond_node)
            if uc_after_cond and cmds.objExists(uc_after_cond):
                cmds.delete(uc_after_cond)

            print("rig_develop_tool: revert rxMute – " + short)

        # rxLock attr 삭제
        if cmds.attributeQuery("rxLock", node=jnt, exists=True):
            cmds.deleteAttr(jnt + ".rxLock")


def revert_ikspine_handle(namespace=""):
    """
    Feature 5 원상 복구.
    - IKSpineHandle_M.dForwardAxis = 0
    - parentConstraint targetOffsetRotate 를 0 으로 초기화
    """
    ns = _ns_prefix(namespace)

    handle = ns + "IKSpineHandle_M"
    if cmds.objExists(handle):
        cmds.setAttr(handle + ".dForwardAxis", 0)
        print("rig_develop_tool: revert dForwardAxis = 0")

    for cname in _IKSPINE_CONSTRAINTS:
        con = ns + cname
        if cmds.objExists(con):
            for ax in ("X", "Y", "Z"):
                cmds.setAttr(
                    con + ".target[0].targetOffsetRotate" + ax, 0)
            print("rig_develop_tool: revert targetOffsetRotate -> 0 : " + cname)


def revert_shape_and_controlset(namespace=""):
    """
    Feature 6 원상 복구.
    AS 리빌드 전에 반드시 실행해야 함.

    - _CTRL_PRESET_MAP 에 포함된 AS 생성 컨트롤러의 커스텀 shape 삭제
      (referenced shape 은 visibility 복원, non-referenced 는 삭제)
    - 이름 충돌 방지: AS 리빌드 시 동일 이름 shape 재생성 오류 예방
    - 툴이 생성한 컨트롤러(Settings, weapon, Master 등) 는 Feature 1~3
      revert 에서 이미 삭제되므로 스킵

    ControlSet 에서 제거는 별도로 하지 않음
    (AS 리빌드 후 ControlSet 자체가 갱신됨)
    """
    ns = _ns_prefix(namespace)

    # AS 가 재생성하는 컨트롤러만 대상 (툴 생성 컨트롤러 제외)
    _TOOL_CREATED = {
        "IKLeg_L_Settings", "IKLeg_R_Settings",
        "IKArm_L_Settings", "IKArm_R_Settings",
        "L_weapon_offset",  "R_weapon_offset",
        "Master", "Global", "MainHip",
    }

    for ctrl_base, _ in _CTRL_PRESET_MAP:
        if ctrl_base in _TOOL_CREATED:
            continue  # Feature 1~3 revert 에서 처리됨

        ctrl = ns + ctrl_base
        if not cmds.objExists(ctrl):
            continue

        shapes = cmds.listRelatives(ctrl, shapes=True, noIntermediate=True) or []
        for sh in shapes:
            try:
                is_ref = cmds.referenceQuery(sh, isNodeReferenced=True)
            except Exception:
                is_ref = False

            if is_ref:
                # referenced shape: 원래 visibility 복원
                try:
                    cmds.setAttr(sh + ".visibility", True)
                except Exception:
                    pass
                print("rig_develop_tool: revert shape (vis restore) – " + sh.split(":")[-1])
            else:
                cmds.delete(sh)
                print("rig_develop_tool: revert shape (deleted) – " + ctrl_base)


def revert_all(namespace=""):
    """Feature 1~6 전체 원상 복구. (AS 리빌드 전 실행)"""
    revert_ik_settings_ctrls(namespace=namespace)
    revert_weapon_offsets(namespace=namespace)
    revert_main_hierarchy(namespace=namespace)
    revert_corrective_root_rx_mute(namespace=namespace)
    revert_ikspine_handle(namespace=namespace)
    revert_shape_and_controlset(namespace=namespace)
    print("rig_develop_tool: revert ALL done.")


# ===========================================================================
# Feature 8 – Rig Cleanup
# ===========================================================================

def cleanup_delete_namespaces_and_layers():
    """1. 씬 내 namespace 및 display/anim layer 전체 제거."""
    # Namespaces – 깊은 계층부터 삭제
    ns_count = 0
    try:
        all_ns = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
        user_ns = [ns for ns in all_ns if ns not in ("UI", "shared")]
        for ns in reversed(sorted(user_ns)):
            try:
                if cmds.namespace(exists=ns):
                    cmds.namespace(removeNamespace=ns, mergeNamespaceWithRoot=True)
                    ns_count += 1
                    print("rig_develop_tool: namespace 제거 – " + ns)
            except Exception as e:
                cmds.warning("rig_develop_tool: namespace 제거 실패 – {} : {}".format(ns, e))
    except Exception as e:
        cmds.warning("rig_develop_tool: namespace 목록 조회 실패 – " + str(e))

    # Display Layers
    layer_count = 0
    for layer in (cmds.ls(type="displayLayer") or []):
        if layer != "defaultLayer":
            try:
                cmds.delete(layer)
                layer_count += 1
                print("rig_develop_tool: displayLayer 제거 – " + layer)
            except Exception as e:
                cmds.warning("rig_develop_tool: displayLayer 제거 실패 – {} : {}".format(layer, e))

    # Anim Layers
    for layer in (cmds.ls(type="animLayer") or []):
        try:
            cmds.delete(layer)
            layer_count += 1
            print("rig_develop_tool: animLayer 제거 – " + layer)
        except Exception as e:
            cmds.warning("rig_develop_tool: animLayer 제거 실패 – {} : {}".format(layer, e))

    print("rig_develop_tool: cleanup NS/Layer 완료 – NS:{} Layer:{}".format(ns_count, layer_count))


def cleanup_delete_unused():
    """2. Delete Unused Nodes & unknown Plugins."""
    mel.eval("MLdeleteUnused;")
    print("rig_develop_tool: unused nodes 삭제 완료")

    removed = 0
    for plugin in (cmds.unknownPlugin(query=True, list=True) or []):
        try:
            cmds.unknownPlugin(plugin, remove=True)
            removed += 1
            print("rig_develop_tool: unknown plugin 제거 – " + plugin)
        except Exception as e:
            cmds.warning("rig_develop_tool: plugin 제거 실패 – {} : {}".format(plugin, e))

    print("rig_develop_tool: unknown plugins 제거 {}개".format(removed))


def cleanup_build_hierarchy(ch_name, namespace=""):
    """
    3. ch_name > geo_grp / rig_grp 계층 구성.

    - ch_name 그룹 생성 (이미 있으면 재사용)
    - geo_grp, rig_grp을 ch_name 하위에 생성
    - 기존 'Group' (AS 리그 최상위) → rig_grp 하위
    - body_grp / head_grp → geo_grp 하위 (존재 시)
    - ch_name outliner color yellow + useOutlinerColor=True

    Parameters
    ----------
    ch_name   : str  캐릭터 그룹 이름
    namespace : str  AS 리그 namespace
    """
    if not ch_name:
        cmds.warning("rig_develop_tool: ch_name 을 입력하세요.")
        return

    ns = _ns_prefix(namespace)

    # ch_name 그룹
    if not cmds.objExists(ch_name):
        ch_grp = cmds.group(empty=True, name=ch_name, world=True)
    else:
        ch_grp = ch_name

    # outliner color: yellow
    cmds.setAttr(ch_grp + ".useOutlinerColor", 1)
    cmds.setAttr(ch_grp + ".outlinerColor", 1.0, 1.0, 0.0, type="double3")
    print("rig_develop_tool: {} outliner color = yellow".format(ch_grp))

    # geo_grp
    if not cmds.objExists("geo_grp"):
        geo_grp = cmds.group(empty=True, name="geo_grp", parent=ch_grp)
    else:
        geo_grp = "geo_grp"
        cur_p = (cmds.listRelatives(geo_grp, parent=True, fullPath=False) or [""])[0]
        if cur_p != ch_grp:
            try:
                cmds.parent(geo_grp, ch_grp)
            except Exception:
                pass

    # rig_grp
    if not cmds.objExists("rig_grp"):
        rig_grp = cmds.group(empty=True, name="rig_grp", parent=ch_grp)
    else:
        rig_grp = "rig_grp"
        cur_p = (cmds.listRelatives(rig_grp, parent=True, fullPath=False) or [""])[0]
        if cur_p != ch_grp:
            try:
                cmds.parent(rig_grp, ch_grp)
            except Exception:
                pass

    # 기존 'Group' → rig_grp
    as_group = ns + "Group"
    if cmds.objExists(as_group):
        try:
            cmds.parent(as_group, rig_grp)
            print("rig_develop_tool: {} → rig_grp".format(as_group))
        except Exception as e:
            cmds.warning("rig_develop_tool: Group parent 실패 – " + str(e))
    else:
        cmds.warning("rig_develop_tool: '{}' not found – rig_grp 에 수동으로 추가하세요.".format(as_group))

    # body_grp / head_grp → geo_grp
    for grp_name in ("body_grp", "head_grp"):
        if cmds.objExists(grp_name):
            try:
                cmds.parent(grp_name, geo_grp)
                print("rig_develop_tool: {} → geo_grp".format(grp_name))
            except Exception as e:
                cmds.warning("rig_develop_tool: {} parent 실패 – {}".format(grp_name, str(e)))

    # 빈 'rig' 그룹 제거
    if cmds.objExists("rig"):
        if not (cmds.listRelatives("rig", children=True) or []):
            try:
                cmds.delete("rig")
                print("rig_develop_tool: 빈 'rig' 그룹 삭제 완료")
            except Exception as e:
                cmds.warning("rig_develop_tool: 'rig' 그룹 삭제 실패 – " + str(e))
        else:
            cmds.warning("rig_develop_tool: 'rig' 그룹이 비어있지 않아 삭제하지 않습니다.")

    print("rig_develop_tool: hierarchy 구성 완료 – {}  (geo_grp / rig_grp)".format(ch_name))


def cleanup_root_joint(namespace=""):
    """
    4. 'root' 조인트를 world 로 unparent 하고 Main.jointVis → root.visibility 연결.

    Parameters
    ----------
    namespace : str  AS 리그 namespace
    """
    ns = _ns_prefix(namespace)

    # root 조인트 탐색
    root_jnt = None
    for candidate in (ns + "root", "root"):
        if cmds.objExists(candidate) and cmds.nodeType(candidate) == "joint":
            root_jnt = candidate
            break

    if root_jnt is None:
        cmds.warning("rig_develop_tool: 'root' joint not found.")
        return

    # world 로 unparent
    if cmds.listRelatives(root_jnt, parent=True):
        cmds.parent(root_jnt, world=True)
        print("rig_develop_tool: root joint → world")
    else:
        print("rig_develop_tool: root joint 이미 world level")

    # Main 컨트롤러 jointVis 연결
    main_ctrl = ns + "Main"
    if not cmds.objExists(main_ctrl):
        cmds.warning("rig_develop_tool: 'Main' controller not found – " + main_ctrl)
        return

    joint_vis_attr = None
    for cand in ("jointVis", "JointVis", "joint_Vis", "jointsVis", "JointsVis"):
        if cmds.attributeQuery(cand, node=main_ctrl, exists=True):
            joint_vis_attr = cand
            break

    if joint_vis_attr is None:
        cmds.warning("rig_develop_tool: jointVis attr not found on " + main_ctrl)
        return

    src = main_ctrl + "." + joint_vis_attr
    dst = root_jnt + ".visibility"

    for plug in (cmds.listConnections(dst, source=True, destination=False, plugs=True) or []):
        cmds.disconnectAttr(plug, dst)
    try:
        cmds.setAttr(dst, lock=False)
    except Exception:
        pass

    cmds.connectAttr(src, dst, force=True)
    print("rig_develop_tool: {} → {}.visibility 연결 완료".format(src, root_jnt))


def cleanup_lights_and_rig_group():
    """5. 'Lights' 그룹 제거."""
    lights_deleted = False
    for node in (cmds.ls("Lights", type="transform") or []):
        try:
            cmds.delete(node)
            lights_deleted = True
            print("rig_develop_tool: Lights 그룹 삭제 완료")
        except Exception as e:
            cmds.warning("rig_develop_tool: Lights 삭제 실패 – " + str(e))
    if not lights_deleted:
        print("rig_develop_tool: Lights 그룹 없음 – 스킵")


def cleanup_create_animation_sets():
    """
    6. Animation Sets 계층 생성.
    Sets
    ├─ AniFBXSet
    │   └─ AniOutSet
    ├─ AssetFBX_Set
    └─ AnimControlSet
    """
    created = []

    if not cmds.objExists("Sets"):
        cmds.sets(name="Sets", empty=True)
        created.append("Sets")

    if not cmds.objExists("AniFBXSet"):
        ani_fbx = cmds.sets(name="AniFBXSet", empty=True)
        cmds.sets(ani_fbx, add="Sets")
        created.append("AniFBXSet")

    if not cmds.objExists("AssetFBX_Set"):
        asset_fbx = cmds.sets(name="AssetFBX_Set", empty=True)
        cmds.sets(asset_fbx, add="Sets")
        created.append("AssetFBX_Set")

    if not cmds.objExists("AniOutSet"):
        ani_out = cmds.sets(name="AniOutSet", empty=True)
        cmds.sets(ani_out, add="AniFBXSet")
        created.append("AniOutSet")

    if not cmds.objExists("AnimControlSet"):
        anim_ctrl = cmds.sets(name="AnimControlSet", empty=True)
        cmds.sets(anim_ctrl, add="Sets")
        created.append("AnimControlSet")

    if created:
        print("rig_develop_tool: Sets 생성 완료 – " + ", ".join(created))
    else:
        print("rig_develop_tool: 모든 Sets 이미 존재")


def cleanup_tag_controllers(namespace=""):
    """
    ControlSet 의 모든 멤버를 Maya 'Tag As Controller' 로 등록.
    이미 태깅된 컨트롤러는 건너뜁니다.
    """
    ns = _ns_prefix(namespace)
    set_name = ns + _CONTROL_SET_NAME
    if not cmds.objExists(set_name):
        cmds.warning("rig_develop_tool: ControlSet 없음 – " + set_name)
        return

    members = cmds.sets(set_name, q=True) or []
    tagged = []
    for member in members:
        if not cmds.objExists(member):
            continue
        try:
            if cmds.controller(member, q=True, isController=True):
                continue  # 이미 태깅됨
            cmds.controller(member)
            tagged.append(member)
        except Exception as e:
            cmds.warning("rig_develop_tool: Tag As Controller 실패 – {}: {}".format(
                member, str(e)))

    if tagged:
        print("rig_develop_tool: Tag As Controller 완료 – {} 개".format(len(tagged)))
    else:
        print("rig_develop_tool: 모든 컨트롤러 이미 태깅됨")


def revert_cleanup_tag_controllers(namespace=""):
    """cleanup_tag_controllers 원상 복구 – Controller Tag 노드 삭제."""
    ns = _ns_prefix(namespace)
    set_name = ns + _CONTROL_SET_NAME
    if not cmds.objExists(set_name):
        return

    members = cmds.sets(set_name, q=True) or []
    removed = 0
    for member in members:
        if not cmds.objExists(member):
            continue
        # transform.message → controller.controllerObject 연결로 태그 노드 탐색
        tag_nodes = cmds.listConnections(
            member + ".message", type="controller") or []
        for tag in tag_nodes:
            try:
                cmds.delete(tag)
                removed += 1
            except Exception as e:
                cmds.warning("rig_develop_tool: controller tag 삭제 실패 – {}: {}".format(
                    member, str(e)))

    if removed:
        print("rig_develop_tool: Controller Tag 제거 완료 – {} 개".format(removed))
    else:
        print("rig_develop_tool: 제거할 Controller Tag 없음")


def cleanup_clean_scene():
    """Namespace & Layer 제거 + Unused Nodes & Plugins 제거 (비가역)."""
    cleanup_delete_namespaces_and_layers()
    cleanup_delete_unused()
    print("rig_develop_tool: Clean Scene 완료")


def cleanup_rig_structure(ch_name, namespace=""):
    """Hierarchy + Root Joint + Lights + Animation Sets 한번에 빌드."""
    # 1. root를 world로 꺼내고 joints_grp 를 비움
    cleanup_root_joint(namespace=namespace)
    # 2. 이제 joints_grp 가 비어 있으므로 삭제
    ns = _ns_prefix(namespace)
    joints_grp = ns + "joints_grp"
    if cmds.objExists(joints_grp):
        children = cmds.listRelatives(joints_grp, children=True) or []
        if not children:
            try:
                cmds.delete(joints_grp)
                print("rig_develop_tool: joints_grp 삭제")
            except Exception as e:
                cmds.warning("rig_develop_tool: joints_grp 삭제 실패 – " + str(e))
        else:
            cmds.warning("rig_develop_tool: joints_grp 가 비어있지 않아 삭제하지 않습니다.")
    # 3. ch_name 계층 빌드 (빈 rig 그룹도 여기서 제거됨)
    cleanup_build_hierarchy(ch_name, namespace=namespace)
    # 4. Lights 제거
    cleanup_lights_and_rig_group()
    # 5. Animation Sets 생성
    cleanup_create_animation_sets()
    # 6. ControlSet 멤버 전체 Tag As Controller 등록
    cleanup_tag_controllers(namespace=namespace)
    print("rig_develop_tool: Build Rig Structure 완료")


def revert_cleanup_rig_structure(ch_name, namespace=""):
    """
    cleanup_rig_structure 전체 원상 복구.

    복구 순서:
    1. Controller Tag 노드 삭제
    2. Animation Sets 삭제
    3. root.visibility 연결 해제
    4. Group / body_grp / head_grp 를 world 로 꺼냄
    5. 빈 geo_grp / rig_grp / ch_name 삭제
    6. rig 그룹 재생성 (world)
    7. joints_grp 재생성 (rig 하위)
    8. root → joints_grp 로 이동
    9. body_grp / head_grp → rig 로 이동
    """
    if not ch_name:
        cmds.warning("rig_develop_tool: ch_name 을 입력하세요.")
        return

    ns = _ns_prefix(namespace)

    # 1. Controller Tag 제거
    revert_cleanup_tag_controllers(namespace=namespace)

    # 2. Animation Sets 삭제
    revert_cleanup_animation_sets()

    # 3. root.visibility 연결 해제
    revert_cleanup_root_joint(namespace=namespace)

    # 4. Group / body_grp / head_grp → world
    as_group = ns + "Group"
    if cmds.objExists(as_group):
        try:
            cmds.parent(as_group, world=True)
            print("rig_develop_tool: {} → world".format(as_group))
        except Exception as e:
            cmds.warning("rig_develop_tool: Group unparent 실패 – " + str(e))

    for grp_name in ("body_grp", "head_grp"):
        if cmds.objExists(grp_name):
            try:
                cmds.parent(grp_name, world=True)
                print("rig_develop_tool: {} → world".format(grp_name))
            except Exception as e:
                cmds.warning("rig_develop_tool: {} unparent 실패 – {}".format(grp_name, str(e)))

    # 5. 빈 geo_grp / rig_grp / ch_name 삭제
    for grp_name in ("geo_grp", "rig_grp", ch_name):
        if cmds.objExists(grp_name):
            children = cmds.listRelatives(grp_name, children=True) or []
            if not children:
                try:
                    cmds.delete(grp_name)
                    print("rig_develop_tool: {} 삭제".format(grp_name))
                except Exception as e:
                    cmds.warning("rig_develop_tool: {} 삭제 실패 – {}".format(grp_name, str(e)))
            else:
                cmds.warning("rig_develop_tool: {} 비어있지 않아 유지".format(grp_name))

    # 6. rig 그룹 재생성 (world)
    rig_grp = ns + "rig"
    if not cmds.objExists(rig_grp):
        cmds.group(empty=True, name="rig")
        print("rig_develop_tool: rig 그룹 재생성")

    # 7. joints_grp 재생성 (rig 하위)
    joints_grp = ns + "joints_grp"
    if not cmds.objExists(joints_grp):
        cmds.group(empty=True, name="joints_grp", parent=rig_grp)
        print("rig_develop_tool: joints_grp 재생성 (rig 하위)")

    # 7. root → joints_grp
    root_jnt = None
    for candidate in (ns + "root", "root"):
        if cmds.objExists(candidate) and cmds.nodeType(candidate) == "joint":
            root_jnt = candidate
            break

    if root_jnt:
        try:
            cmds.parent(root_jnt, joints_grp)
            print("rig_develop_tool: {} → {}".format(root_jnt, joints_grp))
        except Exception as e:
            cmds.warning("rig_develop_tool: root → joints_grp 이동 실패 – " + str(e))
    else:
        cmds.warning("rig_develop_tool: root joint 없음 – joints_grp 는 비어 있음")

    # 8. body_grp / head_grp → rig
    for grp_name in ("body_grp", "head_grp"):
        if cmds.objExists(grp_name):
            try:
                cmds.parent(grp_name, rig_grp)
                print("rig_develop_tool: {} → {}".format(grp_name, rig_grp))
            except Exception as e:
                cmds.warning("rig_develop_tool: {} → rig 이동 실패 – {}".format(grp_name, str(e)))

    print("rig_develop_tool: Revert Rig Structure 완료")


# ---------------------------------------------------------------------------
# Feature 8 – Revert
# ---------------------------------------------------------------------------

def revert_cleanup_hierarchy(ch_name, namespace=""):
    """
    cleanup_build_hierarchy 원상 복구.
    - Group / body_grp / head_grp → world unparent
    - 빈 geo_grp / rig_grp / ch_name 삭제

    Parameters
    ----------
    ch_name   : str
    namespace : str
    """
    if not ch_name:
        cmds.warning("rig_develop_tool: ch_name 을 입력하세요.")
        return

    ns = _ns_prefix(namespace)

    # Group → world
    as_group = ns + "Group"
    if cmds.objExists(as_group):
        try:
            cmds.parent(as_group, world=True)
            print("rig_develop_tool: {} → world".format(as_group))
        except Exception as e:
            cmds.warning("rig_develop_tool: Group unparent 실패 – " + str(e))

    # body_grp / head_grp → world
    for grp_name in ("body_grp", "head_grp"):
        if cmds.objExists(grp_name):
            try:
                cmds.parent(grp_name, world=True)
                print("rig_develop_tool: {} → world".format(grp_name))
            except Exception as e:
                cmds.warning("rig_develop_tool: {} unparent 실패 – {}".format(grp_name, str(e)))

    # 빈 geo_grp / rig_grp 삭제
    for grp_name in ("geo_grp", "rig_grp"):
        if cmds.objExists(grp_name):
            if not (cmds.listRelatives(grp_name, children=True) or []):
                try:
                    cmds.delete(grp_name)
                    print("rig_develop_tool: {} 삭제".format(grp_name))
                except Exception as e:
                    cmds.warning("rig_develop_tool: {} 삭제 실패 – {}".format(grp_name, str(e)))
            else:
                cmds.warning("rig_develop_tool: {} 비어있지 않아 유지".format(grp_name))

    # 빈 ch_name 삭제
    if cmds.objExists(ch_name):
        if not (cmds.listRelatives(ch_name, children=True) or []):
            try:
                cmds.delete(ch_name)
                print("rig_develop_tool: {} 삭제".format(ch_name))
            except Exception as e:
                cmds.warning("rig_develop_tool: {} 삭제 실패 – {}".format(ch_name, str(e)))
        else:
            cmds.warning("rig_develop_tool: {} 비어있지 않아 유지".format(ch_name))

    print("rig_develop_tool: hierarchy revert 완료")


def revert_cleanup_root_joint(namespace=""):
    """
    cleanup_root_joint 원상 복구.
    - Main.jointVis → root.visibility 연결 해제

    Parameters
    ----------
    namespace : str
    """
    ns = _ns_prefix(namespace)

    root_jnt = None
    for candidate in (ns + "root", "root"):
        if cmds.objExists(candidate) and cmds.nodeType(candidate) == "joint":
            root_jnt = candidate
            break

    if root_jnt is None:
        cmds.warning("rig_develop_tool: 'root' joint not found.")
        return

    main_ctrl = ns + "Main"
    if not cmds.objExists(main_ctrl):
        cmds.warning("rig_develop_tool: 'Main' controller not found.")
        return

    joint_vis_attr = None
    for cand in ("jointVis", "JointVis", "joint_Vis", "jointsVis", "JointsVis"):
        if cmds.attributeQuery(cand, node=main_ctrl, exists=True):
            joint_vis_attr = cand
            break

    if joint_vis_attr is None:
        cmds.warning("rig_develop_tool: jointVis attr not found on " + main_ctrl)
        return

    src = main_ctrl + "." + joint_vis_attr
    dst = root_jnt + ".visibility"

    if cmds.isConnected(src, dst):
        cmds.disconnectAttr(src, dst)
        print("rig_develop_tool: {} → {}.visibility 연결 해제".format(src, root_jnt))
    else:
        print("rig_develop_tool: 연결 없음 – 스킵")


def revert_cleanup_animation_sets():
    """
    cleanup_create_animation_sets 원상 복구.

    - AniOutSet / AnimControlSet / AssetFBX_Set / AniFBXSet 은 삭제
    - Sets 는 AdvancedSkeleton 빌드 시 생성되는 경우가 있으므로
      AllSet 이 존재하면 AS 원본으로 간주하여 삭제하지 않고 유지
    """
    # 우리가 추가한 자식 Sets 먼저 삭제
    for set_name in ("AniOutSet", "AnimControlSet", "AssetFBX_Set", "AniFBXSet"):
        if cmds.objExists(set_name):
            try:
                cmds.delete(set_name)
                print("rig_develop_tool: {} 삭제".format(set_name))
            except Exception as e:
                cmds.warning("rig_develop_tool: {} 삭제 실패 – {}".format(set_name, str(e)))

    # Sets: AllSet 이 존재하면 AS 원본이므로 유지
    if cmds.objExists("Sets"):
        if cmds.objExists("AllSet"):
            print("rig_develop_tool: AllSet 감지 – Sets 는 AdvancedSkeleton 원본이므로 유지")
        else:
            try:
                cmds.delete("Sets")
                print("rig_develop_tool: Sets 삭제")
            except Exception as e:
                cmds.warning("rig_develop_tool: Sets 삭제 실패 – " + str(e))

    print("rig_develop_tool: animation sets revert 완료")


# ===========================================================================
# Build All
# ===========================================================================

def build_all(namespace="", ik_size=3.0, weapon_size=8.0,
              global_size=120.0, master_size=100.0, mainhip_size=40.0):
    """Feature 1~6 한번에 빌드."""
    build_ik_settings_ctrls(namespace=namespace, ctrl_size=ik_size)
    build_weapon_offsets(namespace=namespace, size=weapon_size)
    build_main_hierarchy(namespace=namespace,
                         master_size=master_size,
                         global_size=global_size,
                         mainhip_size=mainhip_size)
    build_corrective_root_rx_mute(namespace=namespace)
    fix_ikspine_handle(namespace=namespace)
    build_shape_and_controlset(namespace=namespace)


# ===========================================================================
# UI
# ===========================================================================

def _show_help(title, msg):
    """도움말 팝업."""
    cmds.confirmDialog(title="Help  –  " + title, message=msg,
                       button=["확인"], defaultButton="확인")


_WIN_ID = "rigDevelopToolWin"


class _UI(object):
    def __init__(self):
        self._tf_ns = None
        self._ff_ik_size = None
        self._ff_wp_size = None
        self._ff_master_size = None
        self._ff_global_size = None
        self._ff_mainhip_size = None
        # Feature 7
        self._om_ns_as = None
        self._om_ns_mh = None
        self._tf_side_r = None
        self._tf_side_l = None
        # Feature 8
        self._tf_ch_name = None

    def build_tab_ui(self, parent):
        """parent 레이아웃 내에 UI 구성. tab hub 및 standalone window 공용."""
        scroll = cmds.scrollLayout(childResizable=True, parent=parent)
        main = cmds.columnLayout(adj=True, rowSpacing=6, columnOffset=["both", 8])
        cmds.separator(h=8, style="none")

        # Namespace row
        cmds.rowLayout(nc=4, adjustableColumn=2, columnWidth4=[80, 158, 60, 22])
        cmds.text(label="Namespace")
        self._tf_ns = cmds.textField(
            text="",
            annotation="오브젝트 선택 후 Enter: 선택 오브젝트에서 namespace 감지",
            enterCommand=lambda *_: self._auto_detect_ns(),
            alwaysInvokeEnterCommandOnReturn=True,
        )
        cmds.button(label="Detect",
                    annotation="선택한 오브젝트에서 namespace 감지",
                    c=lambda *_: self._auto_detect_ns())
        cmds.button(label="?", width=22,
                    backgroundColor=[0.25, 0.25, 0.35],
                    c=lambda *_: _show_help("Namespace",
                        "리그 오브젝트의 네임스페이스를 지정합니다.\n\n"
                        "Detect : 선택한 오브젝트에서 네임스페이스를 자동 감지합니다.\n"
                        "빈칸    : 네임스페이스 없이 동작합니다."))
        cmds.setParent("..")

        cmds.separator(h=4)

        # ── Feature 1 ──────────────────────────────────────────────────────
        cmds.frameLayout(label="IK Settings Controller",
                         collapsable=True, collapse=False,
                         marginHeight=6, marginWidth=4)
        cmds.columnLayout(adj=True, rowSpacing=4)

        cmds.rowLayout(nc=2, adjustableColumn=2, columnWidth2=[80, 200])
        cmds.text(label="Ctrl Size")
        self._ff_ik_size = cmds.floatField(value=3.0, minValue=0.1, maxValue=100.0)
        cmds.setParent("..")

        cmds.rowLayout(nc=3, adjustableColumn=1, columnWidth3=[188, 100, 22])
        cmds.button(label="Build IK Settings Ctrls", height=30,
                    backgroundColor=[0.2, 0.35, 0.5],
                    c=lambda *_: self._on_build_ik())
        cmds.button(label="Revert", height=30,
                    backgroundColor=[0.45, 0.25, 0.25],
                    c=lambda *_: revert_ik_settings_ctrls(namespace=self._ns()))
        cmds.button(label="?", width=22, height=30,
                    backgroundColor=[0.25, 0.25, 0.35],
                    c=lambda *_: _show_help("IK Settings Controller",
                        "IK/FK 전환, Stretch 등을 제어하는\n"
                        "IK Settings 컨트롤러를 생성합니다.\n\n"
                        "DeformationSystem 하위의 각 IKSettings 노드에\n"
                        "NURBS 커브 컨트롤러를 연결합니다.\n\n"
                        "Revert : 생성된 컨트롤러를 삭제하고 원래 상태로 복구합니다."))
        cmds.setParent("..")  # rowLayout
        cmds.setParent("..")  # columnLayout
        cmds.setParent("..")  # frameLayout

        # ── Feature 2 ──────────────────────────────────────────────────────
        cmds.frameLayout(label="Weapon Offset Controller",
                         collapsable=True, collapse=False,
                         marginHeight=6, marginWidth=4)
        cmds.columnLayout(adj=True, rowSpacing=4)

        cmds.rowLayout(nc=2, adjustableColumn=2, columnWidth2=[80, 200])
        cmds.text(label="Ctrl Size")
        self._ff_wp_size = cmds.floatField(value=8.0, minValue=0.1, maxValue=100.0)
        cmds.setParent("..")

        cmds.rowLayout(nc=3, adjustableColumn=1, columnWidth3=[188, 100, 22])
        cmds.button(label="Build Weapon Offset  L + R", height=30,
                    backgroundColor=[0.25, 0.45, 0.25],
                    c=lambda *_: self._on_build_weapon())
        cmds.button(label="Revert", height=30,
                    backgroundColor=[0.45, 0.25, 0.25],
                    c=lambda *_: revert_weapon_offsets(namespace=self._ns()))
        cmds.button(label="?", width=22, height=30,
                    backgroundColor=[0.25, 0.25, 0.35],
                    c=lambda *_: _show_help("Weapon Offset Controller",
                        "왼손/오른손 Wrist 조인트에\n"
                        "Weapon Offset 컨트롤러를 생성합니다.\n\n"
                        "무기 오프셋 애니메이션을 위해 사용됩니다.\n\n"
                        "Revert : Weapon Offset 컨트롤러를 삭제합니다."))
        cmds.setParent("..")  # rowLayout
        cmds.setParent("..")
        cmds.setParent("..")

        # ── Feature 3 ──────────────────────────────────────────────────────
        cmds.frameLayout(label="Main Hierarchy  (Global / Master / MainHip / Main)",
                         collapsable=True, collapse=False,
                         marginHeight=6, marginWidth=4)
        cmds.columnLayout(adj=True, rowSpacing=4)

        cmds.rowLayout(nc=2, adjustableColumn=2, columnWidth2=[90, 190])
        cmds.text(label="Global Size")
        self._ff_global_size = cmds.floatField(value=120.0, minValue=0.1, maxValue=1000.0)
        cmds.setParent("..")

        cmds.rowLayout(nc=2, adjustableColumn=2, columnWidth2=[90, 190])
        cmds.text(label="Master Size")
        self._ff_master_size = cmds.floatField(value=100.0, minValue=0.1, maxValue=1000.0)
        cmds.setParent("..")

        cmds.rowLayout(nc=2, adjustableColumn=2, columnWidth2=[90, 190])
        cmds.text(label="MainHip Size")
        self._ff_mainhip_size = cmds.floatField(value=40.0, minValue=0.1, maxValue=1000.0)
        cmds.setParent("..")

        cmds.rowLayout(nc=3, adjustableColumn=1, columnWidth3=[188, 100, 22])
        cmds.button(label="Build Main Hierarchy", height=30,
                    backgroundColor=[0.35, 0.25, 0.45],
                    c=lambda *_: self._on_build_main_hierarchy())
        cmds.button(label="Revert", height=30,
                    backgroundColor=[0.45, 0.25, 0.25],
                    c=lambda *_: revert_main_hierarchy(namespace=self._ns()))
        cmds.button(label="?", width=22, height=30,
                    backgroundColor=[0.25, 0.25, 0.35],
                    c=lambda *_: _show_help("Main Hierarchy",
                        "Global > Master > MainHip > Main 계층을 생성합니다.\n\n"
                        "· Global  : 씬 최상위 컨트롤러\n"
                        "· Master  : 전체 이동/회전/스케일 컨트롤러\n"
                        "· MainHip : 허리 오프셋 컨트롤러\n"
                        "· Main    : 기존 메인 컨트롤러 (재배치)\n\n"
                        "Revert : 생성된 계층을 삭제하고 원래 상태로 복구합니다."))
        cmds.setParent("..")  # rowLayout
        cmds.setParent("..")
        cmds.setParent("..")

        # ── Feature 4 ──────────────────────────────────────────────────────
        cmds.frameLayout(label="correctiveRoot rx Mute",
                         collapsable=True, collapse=False,
                         marginHeight=6, marginWidth=4)
        cmds.columnLayout(adj=True, rowSpacing=4)

        cmds.text(label="*correctiveRoot_*  rxLock attr 추가 + condition 노드 구성",
                  align="left")
        cmds.text(label="  rxLock=1 : rx=0 (mute)   rxLock=0 : rx=pass-through",
                  align="left", font="smallPlainLabelFont")
        cmds.rowLayout(nc=3, adjustableColumn=1, columnWidth3=[188, 100, 22])
        cmds.button(label="Build correctiveRoot rx Mute", height=30,
                    backgroundColor=[0.3, 0.4, 0.35],
                    c=lambda *_: build_corrective_root_rx_mute(namespace=self._ns()))
        cmds.button(label="Revert", height=30,
                    backgroundColor=[0.45, 0.25, 0.25],
                    c=lambda *_: revert_corrective_root_rx_mute(namespace=self._ns()))
        cmds.button(label="?", width=22, height=30,
                    backgroundColor=[0.25, 0.25, 0.35],
                    c=lambda *_: _show_help("correctiveRoot rx Mute",
                        "correctiveRoot_* 조인트에 rxLock 속성을 추가하고\n"
                        "Condition 노드로 rx 뮤트 구조를 구성합니다.\n\n"
                        "rxLock = 1 : rx = 0 (뮤트)\n"
                        "rxLock = 0 : rx = 원래 값 그대로 통과\n\n"
                        "Revert : rxLock 속성과 Condition 노드를 삭제합니다."))
        cmds.setParent("..")  # rowLayout
        cmds.setParent("..")
        cmds.setParent("..")

        # ── Feature 5 ──────────────────────────────────────────────────────
        cmds.frameLayout(label="IKSpine Handle Fix",
                         collapsable=True, collapse=False,
                         marginHeight=6, marginWidth=4)
        cmds.columnLayout(adj=True, rowSpacing=4)

        cmds.text(label="Root.worldOrientForward 존재 시 실행", align="left")
        cmds.text(label="  dForwardAxis=2  /  constraintRotate -> targetOffsetRotate",
                  align="left", font="smallPlainLabelFont")
        cmds.rowLayout(nc=3, adjustableColumn=1, columnWidth3=[188, 100, 22])
        cmds.button(label="Fix IKSpine Handle", height=30,
                    backgroundColor=[0.45, 0.35, 0.2],
                    c=lambda *_: fix_ikspine_handle(namespace=self._ns()))
        cmds.button(label="Revert", height=30,
                    backgroundColor=[0.45, 0.25, 0.25],
                    c=lambda *_: revert_ikspine_handle(namespace=self._ns()))
        cmds.button(label="?", width=22, height=30,
                    backgroundColor=[0.25, 0.25, 0.35],
                    c=lambda *_: _show_help("IKSpine Handle Fix",
                        "IKSpine 핸들의 방향 축을 보정합니다.\n\n"
                        "· dForwardAxis = 2 로 설정\n"
                        "· constraintRotate 값을 targetOffsetRotate에 연결\n\n"
                        "Root.worldOrientForward 속성이 존재할 때 실행하세요.\n\n"
                        "Revert : 변경 사항을 원래 상태로 복구합니다."))
        cmds.setParent("..")  # rowLayout
        cmds.setParent("..")
        cmds.setParent("..")

        # ── Feature 6 ──────────────────────────────────────────────────────
        cmds.frameLayout(label="Shape / Color  +  ControlSet",
                         collapsable=True, collapse=False,
                         marginHeight=6, marginWidth=4)
        cmds.columnLayout(adj=True, rowSpacing=4)

        cmds.text(label="preset shape/color 적용  +  ControlSet 등록",
                  align="left")
        cmds.text(label="  (ctrl_creator_presets.json 참조)",
                  align="left", font="smallPlainLabelFont")
        cmds.rowLayout(nc=2, adjustableColumn=1, columnWidth2=[288, 22])
        cmds.button(label="Apply Shape + ControlSet", height=30,
                    backgroundColor=[0.3, 0.3, 0.45],
                    c=lambda *_: build_shape_and_controlset(namespace=self._ns()))
        cmds.button(label="?", width=22, height=30,
                    backgroundColor=[0.25, 0.25, 0.35],
                    c=lambda *_: _show_help("Shape / Color + ControlSet",
                        "ctrl_creator_presets.json 기반으로\n"
                        "컨트롤러의 모양과 색상을 설정하고\n"
                        "ControlSet에 등록합니다.\n\n"
                        "presets 파일 경로 :\n"
                        "  tools/ctrl_creator_presets.json"))
        cmds.setParent("..")  # rowLayout
        cmds.setParent("..")
        cmds.setParent("..")

        # ── Feature 7 ──────────────────────────────────────────────────────
        cmds.frameLayout(label="Constraint to Joints  (AS → MH)",
                         collapsable=True, collapse=False,
                         marginHeight=6, marginWidth=4)
        cmds.columnLayout(adj=True, rowSpacing=4)

        # AS Namespace
        cmds.rowLayout(nc=2, adjustableColumn=2, columnWidth2=[100, 180])
        cmds.text(label="AS Namespace", align="right")
        self._om_ns_as = cmds.optionMenu()
        cmds.menuItem(label=_NS_NONE_LABEL)
        cmds.setParent("..")

        # MH Namespace
        cmds.rowLayout(nc=2, adjustableColumn=2, columnWidth2=[100, 180])
        cmds.text(label="MH Namespace", align="right")
        self._om_ns_mh = cmds.optionMenu()
        cmds.menuItem(label=_NS_NONE_LABEL)
        cmds.setParent("..")

        cmds.rowLayout(nc=2, adjustableColumn=1, columnWidth2=[288, 22])
        cmds.button(label="Refresh  /  Auto-Detect Namespaces", height=24,
                    backgroundColor=[0.3, 0.3, 0.3],
                    c=lambda *_: self._refresh_constraint_ns())
        cmds.button(label="?", width=22, height=24,
                    backgroundColor=[0.25, 0.25, 0.35],
                    c=lambda *_: _show_help("Constraint to Joints – Namespace",
                        "씬에 존재하는 네임스페이스를 스캔하여\n"
                        "AS / MH 드롭다운을 자동으로 채웁니다.\n\n"
                        "AS Namespace : AdvancedSkeleton 네임스페이스\n"
                        "MH Namespace : MetaHuman 네임스페이스\n\n"
                        "Build ALL 실행 시 자동으로 호출됩니다."))
        cmds.setParent("..")

        cmds.separator(h=4, style="in")

        # Side Suffix
        cmds.rowLayout(nc=4, columnWidth4=[100, 50, 50, 80])
        cmds.text(label="Side Suffix", align="right")
        cmds.text(label="Right:", align="right")
        self._tf_side_r = cmds.textField(text="r", width=45)
        cmds.setParent("..")

        cmds.rowLayout(nc=4, columnWidth4=[100, 50, 50, 80])
        cmds.text(label="", align="right")
        cmds.text(label="Left:", align="right")
        self._tf_side_l = cmds.textField(text="l", width=45)
        cmds.setParent("..")

        cmds.separator(h=4, style="none")
        cmds.text(label="  DeformationSystem 조인트 → MH 조인트  parentConstraint + scaleConstraint",
                  align="left", font="smallPlainLabelFont")
        cmds.rowLayout(nc=3, adjustableColumn=1, columnWidth3=[188, 100, 22])
        cmds.button(label="Constraint to Joints", height=30,
                    backgroundColor=[0.3, 0.4, 0.6],
                    c=lambda *_: self._on_constraint_to_joints())
        cmds.button(label="Revert", height=30,
                    backgroundColor=[0.45, 0.25, 0.25],
                    c=lambda *_: self._on_revert_constraint_to_joints())
        cmds.button(label="?", width=22, height=30,
                    backgroundColor=[0.25, 0.25, 0.35],
                    c=lambda *_: _show_help("Constraint to Joints",
                        "AS DeformationSystem 조인트를 MH 조인트에\n"
                        "parentConstraint + scaleConstraint로 연결합니다.\n\n"
                        "Joint Mapping은 상단의 AS/MH Namespace와\n"
                        "Side Suffix 설정을 기준으로 동작합니다.\n\n"
                        "Revert : 연결된 모든 constraint를 삭제합니다."))
        cmds.setParent("..")  # rowLayout
        cmds.setParent("..")  # columnLayout
        cmds.setParent("..")  # frameLayout

        # ── Feature 8 ──────────────────────────────────────────────────────
        cmds.frameLayout(label="Rig Cleanup",
                         collapsable=True, collapse=False,
                         marginHeight=6, marginWidth=4)
        cmds.columnLayout(adj=True, rowSpacing=4)

        # Ch Name 입력
        cmds.rowLayout(nc=2, adjustableColumn=2, columnWidth2=[80, 190])
        cmds.text(label="Ch Name", align="right")
        self._tf_ch_name = cmds.textField(text="CH_NAME")
        cmds.setParent("..")

        cmds.separator(h=4, style="in")

        # Clean Scene – 비가역 (NS & Layer + Unused)
        cmds.text(label="  NS & Layer 제거  +  Unused Nodes & Plugins 제거  (비가역)",
                  align="left", font="smallPlainLabelFont")
        cmds.rowLayout(nc=2, adjustableColumn=1, columnWidth2=[288, 22])
        cmds.button(label="Clean Scene", height=28,
                    backgroundColor=[0.35, 0.28, 0.28],
                    c=lambda *_: cleanup_clean_scene())
        cmds.button(label="?", width=22, height=28,
                    backgroundColor=[0.25, 0.25, 0.35],
                    c=lambda *_: _show_help("Clean Scene",
                        "씬의 불필요한 요소를 정리합니다. (비가역)\n\n"
                        "① Namespace 제거 (AdvancedSkeleton 네임스페이스 제외)\n"
                        "   Display Layer / Anim Layer 제거\n\n"
                        "② Unused Nodes 삭제 (MLdeleteUnused)\n"
                        "   Unknown Plugin 제거"))
        cmds.setParent("..")

        cmds.separator(h=3, style="none")

        # Rig Structure – Build + Revert
        cmds.text(label="  Hierarchy  +  Root Joint  +  Lights  +  Animation Sets",
                  align="left", font="smallPlainLabelFont")
        cmds.rowLayout(nc=3, adjustableColumn=1, columnWidth3=[188, 100, 22])
        cmds.button(label="Build Rig Structure", height=28,
                    backgroundColor=[0.28, 0.38, 0.3],
                    c=lambda *_: cleanup_rig_structure(
                        self._ch_name(), namespace=self._ns()))
        cmds.button(label="Revert", height=28,
                    backgroundColor=[0.45, 0.25, 0.25],
                    c=lambda *_: revert_cleanup_rig_structure(
                        self._ch_name(), namespace=self._ns()))
        cmds.button(label="?", width=22, height=28,
                    backgroundColor=[0.25, 0.25, 0.35],
                    c=lambda *_: _show_help("Build Rig Structure",
                        "리그 최종 계층을 구성합니다.\n\n"
                        "① root 조인트를 world로 이동\n"
                        "② 빈 joints_grp 삭제\n"
                        "③ Ch Name > geo_grp / rig_grp 계층 생성\n"
                        "   body_grp/head_grp → geo_grp\n"
                        "   Group → rig_grp\n"
                        "   Ch Name outliner 색상 노란색 설정\n"
                        "④ Lights 그룹 제거\n"
                        "⑤ Animation Sets 계층 생성\n"
                        "⑥ ControlSet 멤버 전체 Tag As Controller 등록\n\n"
                        "Revert : 구조를 빌드 이전 상태로 복구합니다.\n"
                        "         Controller Tag 노드도 함께 제거됩니다."))
        cmds.setParent("..")

        cmds.setParent("..")  # columnLayout
        cmds.setParent("..")  # frameLayout

        cmds.separator(h=4)

        # Build All / Revert All
        cmds.rowLayout(nc=3, adjustableColumn=1, columnWidth3=[188, 100, 22])
        cmds.button(label="Build ALL", height=36,
                    backgroundColor=[0.45, 0.3, 0.1],
                    c=lambda *_: self._on_build_all())
        cmds.button(label="Revert ALL", height=36,
                    backgroundColor=[0.5, 0.18, 0.18],
                    c=lambda *_: self._on_revert_all())
        cmds.button(label="?", width=22, height=36,
                    backgroundColor=[0.25, 0.25, 0.35],
                    c=lambda *_: _show_help("Build ALL / Revert ALL",
                        "Build ALL : Feature 1~8 전체를 순서대로 실행합니다.\n"
                        "  1. IK Settings Ctrls\n"
                        "  2. Weapon Offset\n"
                        "  3. Main Hierarchy\n"
                        "  4. correctiveRoot rx Mute\n"
                        "  5. IKSpine Handle Fix\n"
                        "  6. Apply Shape + ControlSet\n"
                        "  7. Constraint to Joints (NS 자동 감지)\n"
                        "  8. Clean Scene + Build Rig Structure\n\n"
                        "Revert ALL : Feature 8~1 역순으로 전체 복구합니다."))
        cmds.setParent("..")  # rowLayout

        cmds.separator(h=8, style="none")
        cmds.setParent("..")  # main
        return scroll

    def show(self):
        if cmds.window(_WIN_ID, exists=True):
            cmds.deleteUI(_WIN_ID)
        win = cmds.window(_WIN_ID, title="Rig Develop Tool",
                          widthHeight=(340, 700), sizeable=True)
        self.build_tab_ui(win)
        cmds.showWindow(win)

    # ── helpers ──────────────────────────────────────────────────────────
    def _auto_detect_ns(self):
        ns = _detect_namespace_from_selection()
        cmds.textField(self._tf_ns, e=True, text=ns)

    def _ns(self):
        return cmds.textField(self._tf_ns, q=True, text=True).strip()

    def _ik_size(self):
        return cmds.floatField(self._ff_ik_size, q=True, value=True)

    def _wp_size(self):
        return cmds.floatField(self._ff_wp_size, q=True, value=True)

    def _on_build_ik(self):
        build_ik_settings_ctrls(namespace=self._ns(), ctrl_size=self._ik_size())

    def _on_build_weapon(self):
        build_weapon_offsets(namespace=self._ns(), size=self._wp_size())

    def _master_size(self):
        return cmds.floatField(self._ff_master_size, q=True, value=True)

    def _global_size(self):
        return cmds.floatField(self._ff_global_size, q=True, value=True)

    def _mainhip_size(self):
        return cmds.floatField(self._ff_mainhip_size, q=True, value=True)

    def _on_build_main_hierarchy(self):
        build_main_hierarchy(namespace=self._ns(),
                             master_size=self._master_size(),
                             global_size=self._global_size(),
                             mainhip_size=self._mainhip_size())

    def _on_build_all(self):
        # Feature 1–6
        build_all(namespace=self._ns(),
                  ik_size=self._ik_size(),
                  weapon_size=self._wp_size(),
                  master_size=self._master_size(),
                  global_size=self._global_size(),
                  mainhip_size=self._mainhip_size())
        # Feature 7: namespace 자동 감지 후 constraint 적용
        self._refresh_constraint_ns()
        constraint_to_joints(
            ns_as=self._get_om_ns(self._om_ns_as),
            ns_mh=self._get_om_ns(self._om_ns_mh),
            side_right=self._side_r(),
            side_left=self._side_l(),
        )
        # Feature 8: Scene 정리 → Rig Structure 빌드
        cleanup_clean_scene()
        cleanup_rig_structure(self._ch_name(), namespace=self._ns())

    def _ch_name(self):
        return cmds.textField(self._tf_ch_name, q=True, text=True).strip()

    def _on_revert_all(self):
        # Feature 8: Rig Structure 먼저 복구
        revert_cleanup_rig_structure(self._ch_name(), namespace=self._ns())
        # Feature 7: constraint 제거
        self._refresh_constraint_ns()
        revert_constraint_to_joints(
            ns_as=self._get_om_ns(self._om_ns_as),
            ns_mh=self._get_om_ns(self._om_ns_mh),
            side_right=self._side_r(),
            side_left=self._side_l(),
        )
        # Feature 1–6
        revert_all(namespace=self._ns())

    def _get_om_ns(self, om):
        """optionMenu에서 namespace 값 반환. (없음) 이면 빈 문자열."""
        val = cmds.optionMenu(om, q=True, v=True)
        return "" if val == _NS_NONE_LABEL else val

    def _refresh_constraint_ns(self):
        """씬 namespace 목록으로 AS/MH optionMenu 갱신 후 자동 감지."""
        namespaces = _scene_namespaces()
        for om in (self._om_ns_as, self._om_ns_mh):
            for item in (cmds.optionMenu(om, q=True, ill=True) or []):
                cmds.deleteUI(item)
            cmds.menuItem(label=_NS_NONE_LABEL, parent=om)
            for ns in namespaces:
                cmds.menuItem(label=ns, parent=om)

        as_g = _guess_ns(namespaces, _AS_NS_HINTS)
        mh_g = _guess_ns(namespaces, _MH_NS_HINTS)

        def _set(om, val):
            if val is None:
                return
            labels = [cmds.menuItem(i, q=True, l=True)
                      for i in (cmds.optionMenu(om, q=True, ill=True) or [])]
            if val in labels:
                cmds.optionMenu(om, e=True, v=val)

        _set(self._om_ns_as, as_g)
        _set(self._om_ns_mh, mh_g)

        detected = []
        if as_g: detected.append("AS=" + as_g)
        if mh_g: detected.append("MH=" + mh_g)
        print("rig_develop_tool: NS 감지 - " + (", ".join(detected) if detected else "없음"))

    def _side_r(self):
        return cmds.textField(self._tf_side_r, q=True, text=True).strip()

    def _side_l(self):
        return cmds.textField(self._tf_side_l, q=True, text=True).strip()

    def _on_constraint_to_joints(self):
        constraint_to_joints(
            ns_as=self._get_om_ns(self._om_ns_as),
            ns_mh=self._get_om_ns(self._om_ns_mh),
            side_right=self._side_r(),
            side_left=self._side_l(),
        )

    def _on_revert_constraint_to_joints(self):
        revert_constraint_to_joints(
            ns_as=self._get_om_ns(self._om_ns_as),
            ns_mh=self._get_om_ns(self._om_ns_mh),
            side_right=self._side_r(),
            side_left=self._side_l(),
        )


def show():
    _UI().show()


if __name__ == "__main__":
    show()
