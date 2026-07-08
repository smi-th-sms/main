"""
MetaHuman Body Joint Edit Mode
================================
MetaHuman body rig 의 primary joint transform 을 수정하고
수정된 transform 을 DNA 로 export 하는 워크플로우 모듈입니다.

사용 순서
---------
    import mh_body_edit_mode as mhem

    mhem.enter_edit_mode()
    # → rl4 disconnect, secondary joints unparent, skinCluster envelope=0

    # viewport 에서 primary joint transform 수정

    mhem.restore_structure()
    # → secondary joints re-parent
    # → correctiveRoot / half : parent joint 위치로 snap (local t = 0)

    mhem.export_dna_from_scene("C:/.../body_custom.dna")
    # → 씬 joint transform → DNA 저장

    mhem.reconnect_rl4()
    # → dnaFilePath 설정, rl4 connections 재연결
    # → 각 LOD mesh: unbind skin (keep history) → rebind

    # DNA export 없이 원래 상태로 되돌리기:
    mhem.full_exit()

    # 현재 상태 확인:
    mhem.get_state()

Secondary joint 판별 기준
-------------------------
- _SECONDARY_PATTERNS 에 포함된 키워드를 short name 에 포함하는 joint
- *_in_l / *_in_r / *_out_l / *_out_r 로 끝나는 joint

Snap 대상 (_SNAP_PATTERNS)
--------------------------
correctiveRoot, half → re-parent 후 local translate = (0,0,0)
(원래 parent joint 위치에 정확히 겹치도록)

요구사항
--------
- Maya 2025 / Python 3.11
- MetaHumanForMaya 1.2.x 이상 (modules 에 설치)
- PyDNA 9.4.7 / PyDNACalib2 3.2.4
"""

import os
import sys
import glob
import json
import math
import maya.cmds as cmds
import maya.mel  as mel
import maya.api.OpenMaya as om2


# ══════════════════════════════════════════════════════════════
#  설정값  (환경에 맞게 수정)
# ══════════════════════════════════════════════════════════════

def _find_mh_lib_root():
    """Documents/maya/modules/MetaHumanForMaya/lib 경로를 자동 탐색."""
    # Windows: C:/Users/*/Documents/maya/modules/MetaHumanForMaya/lib
    pattern = os.path.join(
        os.path.expanduser("~"),
        "Documents/maya/modules/MetaHumanForMaya/lib",
    )
    if os.path.isdir(pattern):
        return pattern.replace("\\", "/")

    # fallback: 모든 사용자 폴더에서 탐색
    for match in glob.glob("C:/Users/*/Documents/maya/modules/MetaHumanForMaya/lib"):
        if os.path.isdir(match):
            return match.replace("\\", "/")

    return ""


# MetaHumanForMaya 라이브러리 루트 (자동 탐색, set_mh_lib_root() 로 변경 가능)
MH_LIB_ROOT = _find_mh_lib_root()


def set_mh_lib_root(path):
    """MH_LIB_ROOT 를 직접 설정한다.

    Parameters
    ----------
    path : str
        MetaHumanForMaya/lib 폴더의 절대 경로.
    """
    global MH_LIB_ROOT
    path = path.replace("\\", "/")
    if not os.path.isdir(path):
        cmds.warning("[MHEdit] 경로가 존재하지 않습니다: {}".format(path))
    MH_LIB_ROOT = path
    print("[MHEdit] MH_LIB_ROOT = {}".format(MH_LIB_ROOT))

# Maya Python 버전 (Maya 2025 = python-3.11 / Maya 2024 = python-3.10)
MH_PY_VER   = "python-3.11"

# 원본 body.dna 기본 경로 (export_dna_from_scene 의 input_dna_path 기본값)
DEFAULT_DNA_INPUT = (
    "C:/Users/smi_th/Documents/Megascans Library/Downloaded/DHI/aaMH/body.dna"
)

# MetaHuman scene namespace
DEFAULT_NAMESPACE = "MHBody"

# rl4 노드 이름
DEFAULT_RL4_NODE = "body_rl4Embedded"

# skinCluster 이름 패턴 및 개수 (body_lod{i}_mesh_skinCluster, i = 0..LOD_COUNT-1)
LOD_COUNT = 4

# rl4 connections JSON 파일 경로 (씬에서 연결을 캡처할 수 없을 때 fallback)
_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
RL4_CONNECTIONS_JSON = os.path.join(_TOOLS_DIR, "rl4_connections.json")


# ══════════════════════════════════════════════════════════════
#  패턴 정의
# ══════════════════════════════════════════════════════════════

# secondary joint 판별 키워드 (short name 에 포함 여부로 검사)
_SECONDARY_PATTERNS = [
    "correctiveRoot", "bulge",
    "side_out", "side_inn", "side_in",
    "half", "scap", "latissimus", "lat_", "pec",
    "_bck_", "_fwd_", "_pip_", "_dip_", "_mcp_", "_palm",
    "twist", "ankle_bck", "ankle_fwd", "_slide",
    "wrist_inner", "wrist_outer", "kneeBack",
]

# re-parent 후 local translate 를 (0,0,0) 으로 snap 할 패턴
_SNAP_PATTERNS = ["correctiveRoot", "half"]


# ══════════════════════════════════════════════════════════════
#  내부 상태
# ══════════════════════════════════════════════════════════════

_state = {
    "active"           : False,
    "rl4_node"         : DEFAULT_RL4_NODE,
    "rl4_connections"  : [],   # [(src_plug, dst_plug), ...]
    "parent_map"       : {},   # {joint_name: original_parent_or_None}
    "sc_info"          : {},   # {sc_name: {"mesh": str, "influences": [str]}}
    "last_exported_dna": "",
}


# ══════════════════════════════════════════════════════════════
#  씬 데이터 노드  (리로드 시에도 state 유지)
# ══════════════════════════════════════════════════════════════

_DATA_NODE = "MHEdit_stateData"


def _save_state_to_scene():
    """_state 를 씬 내 network 노드에 직렬화하여 저장."""
    if not cmds.objExists(_DATA_NODE):
        cmds.createNode("network", name=_DATA_NODE)

    for attr in [
        "parent_map_json", "rl4_connections_json", "sc_info_json",
        "rl4_node_str", "last_exported_dna_str",
    ]:
        if not cmds.attributeQuery(attr, node=_DATA_NODE, exists=True):
            cmds.addAttr(_DATA_NODE, longName=attr, dataType="string")

    n = _DATA_NODE
    cmds.setAttr(n + ".parent_map_json",
                 json.dumps(_state["parent_map"]), type="string")
    cmds.setAttr(n + ".rl4_connections_json",
                 json.dumps(_state["rl4_connections"]), type="string")
    cmds.setAttr(n + ".sc_info_json",
                 json.dumps(_state["sc_info"]), type="string")
    cmds.setAttr(n + ".rl4_node_str",
                 _state["rl4_node"], type="string")
    cmds.setAttr(n + ".last_exported_dna_str",
                 _state["last_exported_dna"], type="string")


def _load_state_from_scene():
    """씬 내 network 노드에서 _state 복원.  성공 시 True."""
    if not cmds.objExists(_DATA_NODE):
        return False
    n = _DATA_NODE
    try:
        _state["parent_map"]       = json.loads(cmds.getAttr(n + ".parent_map_json") or "{}")
        _state["rl4_connections"]  = json.loads(cmds.getAttr(n + ".rl4_connections_json") or "[]")
        _state["sc_info"]          = json.loads(cmds.getAttr(n + ".sc_info_json") or "{}")
        _state["rl4_node"]         = cmds.getAttr(n + ".rl4_node_str") or DEFAULT_RL4_NODE
        _state["last_exported_dna"]= cmds.getAttr(n + ".last_exported_dna_str") or ""
        _state["active"]           = True
        print("[MHEdit] State restored from scene node.")
        return True
    except Exception as e:
        print("[MHEdit] WARN load_state_from_scene: {}".format(e))
        return False


def _clear_scene_state():
    """씬 내 state 노드를 삭제."""
    if cmds.objExists(_DATA_NODE):
        cmds.delete(_DATA_NODE)
        print("[MHEdit] Scene state node deleted.")


def ensure_state():
    """_state 가 비어있으면 씬 노드에서 복원 시도."""
    if not _state["active"] and cmds.objExists(_DATA_NODE):
        _load_state_from_scene()


# ══════════════════════════════════════════════════════════════
#  내부 유틸
# ══════════════════════════════════════════════════════════════

def _is_secondary(name):
    """joint 이름이 secondary joint 패턴에 해당하면 True."""
    short = name.split(":")[-1]
    for pat in _SECONDARY_PATTERNS:
        if pat in short:
            return True
    if short.endswith("_in_l") or short.endswith("_in_r"):
        return True
    if short.endswith("_out_l") or short.endswith("_out_r"):
        return True
    return False


def _is_snap(name):
    """re-parent 후 local t=(0,0,0) snap 이 필요한 joint 이면 True."""
    short = name.split(":")[-1]
    return any(pat in short for pat in _SNAP_PATTERNS)


def _sort_by_depth(parent_map):
    """parent_map 내 joints 를 parent-before-child 순으로 정렬."""
    def depth(j, visited=None):
        if visited is None:
            visited = set()
        if j in visited:
            return 0
        visited.add(j)
        p = parent_map.get(j)
        return 1 + depth(p, visited) if (p and p in parent_map) else 0
    return sorted(parent_map.keys(), key=depth)


def _get_primary_joints():
    """씬의 모든 joint 중 secondary 가 아닌 것만 반환."""
    return [j for j in cmds.ls(type="joint") if not _is_secondary(j)]


def _collect_sc_info():
    """body_lod*_mesh_skinCluster 의 mesh 이름과 influence 목록을 수집."""
    info = {}
    for i in range(LOD_COUNT):
        sc   = "body_lod{}_mesh_skinCluster".format(i)
        mesh = "body_lod{}_mesh".format(i)
        if not cmds.objExists(sc):
            continue
        info[sc] = {
            "mesh"      : mesh,
            "influences": cmds.skinCluster(sc, q=True, influence=True) or [],
        }
    return info


def _get_sc_influences(sc_name):
    """
    sc 의 matrix 연결에서 influence joint 목록을 반환합니다.
    PyMEL 을 우선 사용하고, 실패 시 cmds.skinCluster 로 fallback.
    """
    try:
        import pymel.core as pm
        sc_node = pm.PyNode(sc_name)
        return [str(j) for j in sc_node.attr("matrix").listConnections(
            d=False, s=True, type="joint"
        )]
    except Exception:
        return cmds.skinCluster(sc_name, q=True, influence=True) or []


# ══════════════════════════════════════════════════════════════
#  1. Enter Edit Mode
# ══════════════════════════════════════════════════════════════

def enter_edit_mode(rl4_node=DEFAULT_RL4_NODE, force=False):
    """
    joint 편집 준비 단계.

    1) body_lod*_mesh_skinCluster 정보 저장 → envelope = 0  (mesh shape 고정)
    2) rl4 output connections 전체 저장 → disconnect
    3) secondary joints parent 저장 → world unparent

    Parameters
    ----------
    force : bool
        True 이면 active 상태 체크를 무시하고 강제 실행합니다.
        이전 실행이 중단되어 _state 가 꼬인 경우에 사용하세요.
    """
    if _state["active"] and not force:
        print("[MHEdit] Already in edit mode. (force=True 로 강제 실행 가능)")
        return
    if _state["active"] and force:
        print("[MHEdit] force=True: active 상태를 무시하고 재실행합니다.")
        reset_state()

    _state["rl4_node"] = rl4_node

    # ── 1) skinCluster envelope = 0 ─────────────────────────────
    sc_info = _collect_sc_info()
    _state["sc_info"] = sc_info

    cmds.undoInfo(openChunk=True, chunkName="MHEdit_envelopeOff")
    try:
        for sc in sc_info:
            try:
                cmds.setAttr(sc + ".envelope", 0.0)
            except Exception as e:
                print("[MHEdit] WARN envelope {}: {}".format(sc, e))
    finally:
        cmds.undoInfo(closeChunk=True)
    print("[MHEdit] Set envelope=0 on {} skinClusters.".format(len(sc_info)))

    # ── 2) rl4 connections 저장 & disconnect ────────────────────
    if not cmds.objExists(rl4_node):
        print("[MHEdit] WARNING: {} not found.".format(rl4_node))
        _state["rl4_connections"] = []
    else:
        out_conns = cmds.listConnections(
            rl4_node, source=False, destination=True,
            connections=True, plugs=True,
        ) or []
        saved = [[out_conns[i], out_conns[i + 1]] for i in range(0, len(out_conns), 2)]

        # 씬에서 연결이 없으면 JSON 파일에서 로드
        if not saved and os.path.isfile(RL4_CONNECTIONS_JSON):
            with open(RL4_CONNECTIONS_JSON, "r") as f:
                saved = json.load(f)
            print("[MHEdit] Loaded {} connections from {}.".format(
                len(saved), os.path.basename(RL4_CONNECTIONS_JSON)))

        cmds.undoInfo(openChunk=True, chunkName="MHEdit_disconnectRL4")
        try:
            for src, dst in saved:
                try:
                    if cmds.isConnected(src, dst):
                        cmds.disconnectAttr(src, dst)
                except Exception as e:
                    print("[MHEdit] WARN disconnect {}: {}".format(src, e))
        finally:
            cmds.undoInfo(closeChunk=True)

        _state["rl4_connections"] = saved
        print("[MHEdit] Disconnected / stored {} connections from {}.".format(len(saved), rl4_node))

    # ── 3) secondary joints unparent ────────────────────────────
    secondary  = [j for j in cmds.ls(type="joint") if _is_secondary(j)]
    sec_set    = set(secondary)

    # secondary 하위의 non-secondary joint 도 unparent 대상에 포함
    # (예: calf_knee → calf_correctiveRoot 하위, upperarm_bicep → twist 하위)
    all_joints = cmds.ls(type="joint")
    for j in all_joints:
        if j in sec_set:
            continue
        par = cmds.listRelatives(j, parent=True, type="joint", fullPath=False)
        if par and par[0] in sec_set:
            secondary.append(j)
            sec_set.add(j)

    parent_map = {}

    # child → parent 순서로 unparent (leaf 먼저)
    def _hier_depth(j):
        d = 0
        p = cmds.listRelatives(j, parent=True, fullPath=False)
        while p:
            d += 1
            p = cmds.listRelatives(p[0], parent=True, fullPath=False)
        return d

    secondary.sort(key=_hier_depth, reverse=True)

    cmds.undoInfo(openChunk=True, chunkName="MHEdit_unparent")
    try:
        for j in secondary:
            par = cmds.listRelatives(j, parent=True, fullPath=False)
            parent_map[j] = par[0] if par else None
            if par:
                try:
                    cmds.parent(j, world=True)
                except Exception as e:
                    print("[MHEdit] WARN unparent {}: {}".format(j, e))
    finally:
        cmds.undoInfo(closeChunk=True)

    _state["parent_map"] = parent_map
    _state["active"]     = True

    # ── 4) secondary joints hide ────────────────────────────────
    for j in secondary:
        if cmds.objExists(j):
            try:
                cmds.setAttr(j + ".visibility", 0)
            except Exception:
                pass

    # ── 5) state 를 씬 노드에 저장 ──────────────────────────────
    _save_state_to_scene()

    print("[MHEdit] Unparented {} secondary joints.".format(len(secondary)))
    print("[MHEdit] Primary joints in tree: {}.".format(len(_get_primary_joints())))
    print("[MHEdit] >>> EDIT MODE ACTIVE - modify primary joint transforms now. <<<")


# ══════════════════════════════════════════════════════════════
#  2. Restore Structure
# ══════════════════════════════════════════════════════════════

def restore_structure():
    """
    secondary joints 를 원래 parent 로 re-parent 합니다.
    - correctiveRoot / half : re-parent 후 local translate = (0,0,0) snap
    - 나머지               : re-parent 만 (Maya 가 world position 유지)

    이 시점에서 rl4 는 아직 미연결 상태입니다.
    다음 단계: export_dna_from_scene() → reconnect_rl4()
    """
    ensure_state()
    if not _state["active"]:
        print("[MHEdit] Not in edit mode.")
        return

    parent_map    = _state["parent_map"]
    sorted_joints = _sort_by_depth(parent_map)
    snap_count    = 0
    errors        = []

    cmds.undoInfo(openChunk=True, chunkName="MHEdit_restoreStructure")
    try:
        for j in sorted_joints:
            orig_par = parent_map[j]
            if not cmds.objExists(j):
                print("[MHEdit] WARN: {} missing.".format(j))
                continue
            try:
                if orig_par and cmds.objExists(orig_par):
                    cmds.parent(j, orig_par)
            except Exception as e:
                errors.append((j, str(e)))
                continue

            if _is_snap(j):
                try:
                    cmds.setAttr(j + ".translate", 0.0, 0.0, 0.0, type="double3")
                    snap_count += 1
                except Exception as e:
                    errors.append((j, "snap: " + str(e)))
            # else: re-parent 시 Maya 가 world position 을 유지하며 local translate 를 갱신함
            # → 변경된 local transform 이 그대로 새 DNA neutral 이 됩니다.
    finally:
        cmds.undoInfo(closeChunk=True)

    if errors:
        print("[MHEdit] Errors ({})".format(len(errors)))
        for j, msg in errors:
            print("  {}: {}".format(j, msg))

    # secondary joints visibility 복원
    for j in sorted_joints:
        if cmds.objExists(j):
            try:
                cmds.setAttr(j + ".visibility", 1)
            except Exception:
                pass

    print("[MHEdit] Restored {} joints (snap: {}).".format(len(parent_map), snap_count))
    print("[MHEdit] >>> Call export_dna_from_scene(), then reconnect_rl4(). <<<")


# ══════════════════════════════════════════════════════════════
#  3. Export DNA from Scene
# ══════════════════════════════════════════════════════════════

def export_dna_from_scene(
    output_dna_path,
    input_dna_path=DEFAULT_DNA_INPUT,
    namespace=DEFAULT_NAMESPACE,
):
    """
    씬의 joint translate / rotate 값을 읽어 DNA neutral joint 값으로 저장합니다.
    restore_structure() 후 (rl4 미연결 상태) 에 호출하세요.

    Parameters
    ----------
    output_dna_path : str   저장할 .dna 경로
    input_dna_path  : str   기준이 되는 원본 .dna 경로
    namespace       : str   씬의 MetaHuman namespace (기본값 "MHBody")

    저장 경로는 _state["last_exported_dna"] 에 기록되어
    reconnect_rl4() 에서 dnaFilePath 설정에 자동으로 사용됩니다.
    """
    # PyDNA / PyDNACalib2 경로 등록
    for p in [
        MH_LIB_ROOT + "/PyDNA/9.4.7/platform-windows/.sanitizers-off/.json-0/" + MH_PY_VER + "/lib",
        MH_LIB_ROOT + "/PyDNACalib2/3.2.4/platform-windows/.sanitizers-off/" + MH_PY_VER + "/lib",
    ]:
        if p not in sys.path:
            sys.path.insert(0, p)

    import dna
    import dnacalib2

    # DNA 읽기: FileStream → BinaryStreamReader → DNACalibDNAReader
    stream     = dna.FileStream(input_dna_path, dna.FileStream.AccessMode_Read,  dna.FileStream.OpenMode_Binary)
    bin_reader = dna.BinaryStreamReader(stream, dna.DataLayer_All)
    bin_reader.read()
    reader     = dnacalib2.DNACalibDNAReader(bin_reader)

    count = reader.getJointCount()
    xs  = list(reader.getNeutralJointTranslationXs())
    ys  = list(reader.getNeutralJointTranslationYs())
    zs  = list(reader.getNeutralJointTranslationZs())
    rxs = list(reader.getNeutralJointRotationXs())
    rys = list(reader.getNeutralJointRotationYs())
    rzs = list(reader.getNeutralJointRotationZs())

    updated = skipped = 0
    for i in range(count):
        joint_name = reader.getJointName(i)
        maya_name = (namespace + ":" + joint_name) if namespace else joint_name
        if not cmds.objExists(maya_name):
            skipped += 1
            continue
        t  = cmds.getAttr(maya_name + ".translate")[0]
        jo = cmds.getAttr(maya_name + ".jointOrient")[0]
        xs[i],  ys[i],  zs[i]  = t[0], t[1], t[2]
        # DNA neutralJointRotation = jointOrient (not .rotate)
        # .rotate 는 RL4 가 pose 를 드라이빙할 때 사용하는 animated 값이며
        # neutral pose 에서 항상 (0,0,0) 입니다.
        # jointOrient 는 조인트의 축 정렬 오프셋 (root = -90°X 등) 으로
        # Pose Editor 가 skeleton 을 재구성할 때 이 값을 사용합니다.
        rxs[i], rys[i], rzs[i] = jo[0], jo[1], jo[2]
        updated += 1

    # translation / rotation 커맨드 실행
    t_cmd = dnacalib2.SetNeutralJointTranslationsCommand()
    t_cmd.setTranslations(xs, ys, zs)
    t_cmd.run(reader)

    r_cmd = dnacalib2.SetNeutralJointRotationsCommand()
    r_cmd.setRotations(rxs, rys, rzs)
    r_cmd.run(reader)

    # DNA 저장: FileStream → BinaryStreamWriter
    out_stream = dna.FileStream(output_dna_path, dna.FileStream.AccessMode_Write, dna.FileStream.OpenMode_Binary)
    writer = dna.BinaryStreamWriter(out_stream)
    writer.setFrom(reader)
    writer.write()

    _state["last_exported_dna"] = output_dna_path
    # 씬 노드에도 갱신
    if cmds.objExists(_DATA_NODE):
        if not cmds.attributeQuery("last_exported_dna_str", node=_DATA_NODE, exists=True):
            cmds.addAttr(_DATA_NODE, longName="last_exported_dna_str", dataType="string")
        cmds.setAttr(_DATA_NODE + ".last_exported_dna_str", output_dna_path, type="string")
    print("[MHEdit] DNA export: updated={}, skipped={}.".format(updated, skipped))
    print("[MHEdit] Saved -> {} ({} bytes)".format(output_dna_path, os.path.getsize(output_dna_path)))


# ══════════════════════════════════════════════════════════════
#  4. Reconnect rl4
# ══════════════════════════════════════════════════════════════

def _rebuild_bind_pose_node(mesh, influences):
    """
    doDetachSkin 전에 dagPose 를 현재 계층 기준으로 재생성합니다.

    fit chain 과정에서 helper joint 의 부모가 변경되면
    기존 dagPose 에 저장된 parent 참조가 무효화됩니다.
    dagPose 를 삭제 후 현재 상태로 재저장하면
    doDetachSkin 내부의 'go to bind pose' 가 경고 없이 동작합니다.
    """
    try:
        bp_nodes = cmds.dagPose(mesh, q=True, bp=True) or []
        if bp_nodes:
            cmds.delete(bp_nodes)
    except Exception as e:
        print("[MHEdit] WARN dagPose delete {}: {}".format(mesh, e))

    try:
        valid = [n for n in influences + [mesh] if cmds.objExists(n)]
        if valid:
            cmds.dagPose(valid, save=True, bp=True)
            print("[MHEdit] dagPose rebuilt for {}.".format(mesh))
    except Exception as e:
        print("[MHEdit] WARN dagPose save {}: {}".format(mesh, e))


def _rebind_skin(sc_name, info):
    """
    단일 skinCluster 에 대해 unbind (keep history) → rebind 를 수행합니다.

    1) dagPose 재생성 (현재 계층 기준) → doDetachSkin 내 'go to bind pose' 오류 방지
    2) doDetachSkin 3 {"2","1","1"}
       → sc 노드가 유지된 채로 detach (weights 보존됨)
    3) 유지된 sc 의 matrix 연결에서 influence joints 쿼리
    4) joints + mesh 선택 후 skinCluster 재실행
       → 기존 sc 재활성화 (bindPose 경고는 무시)
    5) sc envelope = 1.0

    Bind settings
    -------------
    toSelectedBones=True / bindMethod=1 (Closest in hierarchy) /
    skinMethod=0 (Classic linear) / normalizeWeights=1 /
    maximumInfluences=1 / obeyMaxInfluences=False /
    rui=False / dropoffRate=4.0
    """
    mesh = info["mesh"]

    if not cmds.objExists(mesh):
        print("[MHEdit] WARN: mesh {} not found - skip.".format(mesh))
        return False
    if not cmds.objExists(sc_name):
        print("[MHEdit] WARN: sc {} not found - skip.".format(sc_name))
        return False

    # ── 1) dagPose 재생성 (doDetachSkin 전 - 현재 계층 기준) ────
    pre_influences = _get_sc_influences(sc_name) or info["influences"]
    _rebuild_bind_pose_node(mesh, pre_influences)

    # ── 2) doDetachSkin keep history ────────────────────────────
    cmds.select(mesh, replace=True)
    q = chr(34)
    try:
        mel.eval("doDetachSkin 3 { " + q+"2"+q + ", " + q+"1"+q + ", " + q+"1"+q + " }")
    except Exception as e:
        print("[MHEdit] WARN doDetachSkin {}: {}".format(mesh, e))
        return False

    # ── 3) sc 에서 influence joints 쿼리 ────────────────────────
    influences = _get_sc_influences(sc_name)
    if not influences:
        influences = info["influences"]

    # ── 4) joints + mesh 선택 → skinCluster 재실행 ──────────────
    cmds.select(influences, replace=True)
    cmds.select(mesh, add=True)   # select -tgl mesh 와 동일
    try:
        cmds.skinCluster(
            toSelectedBones=True,
            bindMethod=1,
            skinMethod=0,
            normalizeWeights=1,
            maximumInfluences=1,
            obeyMaxInfluences=False,
            rui=False,
            dropoffRate=4.0,
        )
    except Exception as e:
        if "bindPose" not in str(e):   # bindPose read-only 경고는 무시
            print("[MHEdit] WARN rebind {}: {}".format(mesh, e))
            return False

    # ── 5) envelope = 1.0 ───────────────────────────────────────
    if cmds.objExists(sc_name):
        cmds.setAttr(sc_name + ".envelope", 1.0)

    print("[MHEdit] Rebound {} ({} influences).".format(mesh, len(influences)))
    return True


def bake_rotate_to_joint_orient(namespace=DEFAULT_NAMESPACE, joints=None):
    """
    모든 joint 의 rotate 값을 jointOrient 에 합산하고 rotate 를 (0,0,0) 으로 만듭니다.
    worldMatrix 는 변경되지 않습니다.

    Maya joint 로컬 매트릭스 회전 순서(row-vector): R * JO
    → new_JO = R_matrix * JO_matrix  를 XYZ euler 로 분해하여 jointOrient 에 설정.

    RL4 reconnect 전에 호출해야 합니다 (RL4 가 rotate 를 드라이빙하므로).

    Parameters
    ----------
    joints : list[str] or None
        지정하면 이 목록만 처리합니다 (namespace 와일드카드 대신 명시적 대상 지정).
        네임스페이스가 없는 스켈레톤처럼 namespace="" 로는 대상을 좁힐 수 없는
        경우에 사용하세요.
    """
    if joints is None:
        prefix = (namespace + ":") if namespace else ""
        joints = cmds.ls(prefix + "*", type="joint", long=True) or []

    baked = 0
    skipped = 0

    for jnt in joints:
        r = cmds.getAttr(jnt + ".rotate")[0]
        if abs(r[0]) < 1e-6 and abs(r[1]) < 1e-6 and abs(r[2]) < 1e-6:
            continue

        # locked / connected 검사
        skip = False
        for attr in (".rx", ".ry", ".rz", ".jox", ".joy", ".joz"):
            full = jnt + attr
            if cmds.getAttr(full, lock=True):
                skip = True
                break
            if cmds.listConnections(full, source=True, destination=False):
                skip = True
                break
        if skip:
            skipped += 1
            continue

        wm_before = list(cmds.getAttr(jnt + ".worldMatrix[0]"))

        jo = cmds.getAttr(jnt + ".jointOrient")[0]
        ro = cmds.getAttr(jnt + ".rotateOrder")

        jo_euler = om2.MEulerRotation(
            math.radians(jo[0]), math.radians(jo[1]), math.radians(jo[2]), 0
        )
        r_euler = om2.MEulerRotation(
            math.radians(r[0]), math.radians(r[1]), math.radians(r[2]), ro
        )

        combined_mat = r_euler.asMatrix() * jo_euler.asMatrix()
        new_jo_e = om2.MTransformationMatrix(combined_mat).rotation(asQuaternion=False)
        new_jo_e.reorderIt(0)  # jointOrient 은 항상 XYZ

        cmds.setAttr(
            jnt + ".jointOrient",
            math.degrees(new_jo_e.x),
            math.degrees(new_jo_e.y),
            math.degrees(new_jo_e.z),
        )
        cmds.setAttr(jnt + ".rotate", 0, 0, 0)

        wm_after = list(cmds.getAttr(jnt + ".worldMatrix[0]"))
        max_diff = max(abs(a - b) for a, b in zip(wm_before, wm_after))
        if max_diff > 0.0001:
            print("[MHEdit] WARN bake {} worldMatrix diff={:.6f}".format(
                jnt.split("|")[-1], max_diff))

        baked += 1

    print("[MHEdit] bake_rotate_to_joint_orient: baked={}, skipped={}".format(
        baked, skipped))
    return baked, skipped


def reconnect_rl4():
    """
    편집 완료 후 rig 를 복원합니다.

    1) body_rl4Embedded.dnaFilePath = export 한 DNA 경로
    2) 각 LOD mesh: unbind skin (keep history) → rebind
       ※ RL4 reconnect 전에 수행 - body_rl4Embedded 가 joints 를 드라이빙하기 전
         dagPose 'go to bind pose' 를 실행해야 clavicle_out/scap 등 driven 조인트
         오류("Could not reach pose") 가 발생하지 않음
    3) rl4 output connections 재연결
    4) skinCluster envelope = 1.0
    """
    ensure_state()
    rl4_node    = _state["rl4_node"]
    exported    = _state.get("last_exported_dna", "")
    sc_info     = _state.get("sc_info", {})
    saved_conns = _state["rl4_connections"]

    # ── 1) dnaFilePath 설정 ──────────────────────────────────────
    if exported and cmds.objExists(rl4_node):
        try:
            cmds.setAttr(rl4_node + ".dnaFilePath", exported, type="string")
            print("[MHEdit] dnaFilePath -> {}".format(exported))
        except Exception as e:
            print("[MHEdit] WARN dnaFilePath: {}".format(e))

    # ── 2) unbind (keep history) → rebind ───────────────────────
    # RL4 reconnect 전에 수행: driven connection 간섭 없이 bind pose 복원
    for sc_name, info in sc_info.items():
        _rebind_skin(sc_name, info)

    # ── 3) rl4 connections 재연결 ────────────────────────────────
    reconn = 0
    cmds.undoInfo(openChunk=True, chunkName="MHEdit_reconnectRL4")
    try:
        for src, dst in saved_conns:
            try:
                if not cmds.isConnected(src, dst):
                    cmds.connectAttr(src, dst, force=True)
                    reconn += 1
            except Exception as e:
                print("[MHEdit] WARN reconnect {}: {}".format(src, e))
    finally:
        cmds.undoInfo(closeChunk=True)
    print("[MHEdit] Reconnected {} rl4 connections.".format(reconn))

    # ── 4) envelope = 1.0 (rebind 내부에서도 처리하지만 최종 보장) ─
    for sc_name in sc_info:
        if cmds.objExists(sc_name):
            cmds.setAttr(sc_name + ".envelope", 1.0)
    print("[MHEdit] Restored skinCluster envelopes to 1.0.")

    # ── 상태 초기화 + 씬 노드 삭제 ─────────────────────────────
    _state["active"]            = False
    _state["rl4_connections"]   = []
    _state["parent_map"]        = {}
    _state["sc_info"]           = {}
    _state["last_exported_dna"] = ""
    _clear_scene_state()
    print("[MHEdit] >>> Done. <<<")


# ══════════════════════════════════════════════════════════════
#  5. 편의 함수
# ══════════════════════════════════════════════════════════════

def full_exit():
    """DNA export 없이 씬을 원래 상태로 완전히 되돌립니다."""
    restore_structure()
    reconnect_rl4()


def get_state():
    """현재 _state 를 출력합니다."""
    ensure_state()
    print("[MHEdit] active            :", _state["active"])
    print("[MHEdit] rl4 node          :", _state["rl4_node"])
    print("[MHEdit] rl4 connections   :", len(_state["rl4_connections"]))
    print("[MHEdit] parent_map        :", len(_state["parent_map"]))
    print("[MHEdit] sc_info           :", list(_state["sc_info"].keys()))
    print("[MHEdit] last_exported_dna :", _state["last_exported_dna"])
    print("[MHEdit] scene node        :", cmds.objExists(_DATA_NODE))


def reset_state():
    """
    _state 를 강제로 초기화합니다.
    export / reconnect 중 오류로 active 플래그가 남아있을 때 사용합니다.
    씬 상태(joint parent, rl4 연결)는 건드리지 않으므로
    필요하면 full_exit() 를 먼저 호출하세요.
    """
    _state["active"]            = False
    _state["rl4_connections"]   = []
    _state["parent_map"]        = {}
    _state["sc_info"]           = {}
    _state["last_exported_dna"] = ""
    _clear_scene_state()
    print("[MHEdit] _state 초기화 완료.")
##########################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################################