"""
MH Fit Tool
===========
MetaHuman 스켈레톤 피팅 통합 워크플로우 툴.

fit_chains_config.json 에 정의된 조인트 체인을 기반으로
fit_chain_tool 의 Aim 시스템을 일괄 생성/적용하고,
mh_body_edit_mode 를 통해 DNA 를 export 합니다.

Workflow
--------
1. Enter Edit Mode  → mhem.enter_edit_mode()
                      secondary joints unparent + hide
2. Build Fit Chains → config 기반 일괄 build_aim_system()
   (viewport 에서 fit controller 로 조인트 위치 조정)
3. Apply & Remove   → apply_fit_to_joints() + remove_aim_system()
4a. Restore Structure  → restore_structure()
    (viewport 에서 스켈레톤 상태 검수)
4b. Export DNA         → export_dna_from_scene() → reconnect_rl4()

Usage
-----
    import mh_fit_tool
    mh_fit_tool.show()
"""

import importlib
import os
import sys
import json
import maya.cmds as cmds

# 같은 디렉토리 sys.path 등록
_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import mh_body_edit_mode as mhem
import fit_chain_tool

# ═══════════════════════════════════════════════════════════
#  설정
# ═══════════════════════════════════════════════════════════

_CONFIG_PATH = os.path.join(_TOOLS_DIR, "fit_chains_config.json")

_DEFAULT_SETTINGS = {
    "aim_axis"      : "+X",   # build_fit_chains 에서 체인별 자동 계산으로 덮어씀
    "up_axis"       : "+Z",
    "up_method"     : "A",
    "up_local_axis" : "Z",
    "up_world_vec"  : "+Z",
    "up_object"     : "",
    "up_object_axis": "Z",
}

# ═══════════════════════════════════════════════════════════
#  내부 상태  {part_name: {"grp": str, "joints": [str]}}
# ═══════════════════════════════════════════════════════════

_fit_state = {}


# ═══════════════════════════════════════════════════════════
#  내부 유틸
# ═══════════════════════════════════════════════════════════

def _load_config():
    with open(_CONFIG_PATH, "r") as f:
        return json.load(f)


def _detect_aim_axis(joints):
    """
    첫 번째 조인트 쌍으로부터 aim axis 를 자동 감지.
    첫 번째 조인트의 로컬 축 중 체인 방향과 가장 가까운 축을 반환.
    예) "+X", "-Y", "+Z" 형태
    """
    info0 = fit_chain_tool._jnt_info(joints[0])
    info1 = fit_chain_tool._jnt_info(joints[1])
    aim_v = tuple(info1["world_pos"][k] - info0["world_pos"][k] for k in range(3))
    aim_n = fit_chain_tool._norm(aim_v)
    ax_data = [("X", info0["lx"]), ("Y", info0["ly"]), ("Z", info0["lz"])]
    ax_name, ang = min(
        [(n, fit_chain_tool._ang(v, aim_n)) for n, v in ax_data],
        key=lambda t: min(t[1], 180.0 - t[1]),
    )
    sign = "+" if ang < 90.0 else "-"
    return sign + ax_name


def _resolve_joints(joint_names, namespace):
    """
    joint 이름 목록에 namespace 를 붙여 씬 내 존재 여부 확인 후 반환.
    namespace 없이도 존재하면 그대로 사용.
    """
    result = []
    for j in joint_names:
        full = "{}:{}".format(namespace, j) if namespace else j
        if cmds.objExists(full):
            result.append(full)
        elif cmds.objExists(j):
            result.append(j)
        else:
            cmds.warning("[MHFit] joint 없음: {}".format(full))
    return result


def _strip_edit_suffix(path):
    """_edit 접미사를 모두 제거하여 원본 DNA 경로 반환."""
    base, ext = os.path.splitext(path)
    while base.endswith("_edit"):
        base = base[:-5]
    return base + ext


def _get_dna_source_path():
    """
    body_rl4Embedded.dnaFilePath 에서 _edit 접미사를 제거한 원본 경로 추론.
    예) .../body_edit_edit.dna  →  .../body.dna
    """
    rl4 = mhem.DEFAULT_RL4_NODE
    if not cmds.objExists(rl4):
        return ""
    try:
        dna_path = cmds.getAttr(rl4 + ".dnaFilePath") or ""
        return _strip_edit_suffix(dna_path) if dna_path else ""
    except Exception:
        return ""


def _get_dna_output_path():
    """
    body_rl4Embedded.dnaFilePath 로부터 출력 경로 추론.
    _edit 누적을 방지하기 위해 먼저 원본으로 정규화 후 _edit 한 번만 붙임.
    예) .../body_edit_edit.dna  →  .../body_edit.dna
    """
    rl4 = mhem.DEFAULT_RL4_NODE
    if not cmds.objExists(rl4):
        return ""
    try:
        dna_path = cmds.getAttr(rl4 + ".dnaFilePath") or ""
        if not dna_path:
            return ""
        base, ext = os.path.splitext(_strip_edit_suffix(dna_path))
        return base + "_edit" + ext
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════
#  Core API
# ═══════════════════════════════════════════════════════════

def build_fit_chains(parts, settings=None, namespace=mhem.DEFAULT_NAMESPACE):
    """
    선택된 파트들에 대해 fit_chain_tool.build_aim_system() 을 일괄 실행.

    Parameters
    ----------
    parts     : list[str]  config 의 part 이름 목록
    settings  : dict       build_aim_system 설정 (None 이면 _DEFAULT_SETTINGS 사용)
    namespace : str        MetaHuman scene namespace
    """
    cfg = _load_config()
    all_parts = cfg.get("parts", {})

    s = dict(_DEFAULT_SETTINGS)
    if settings:
        s.update(settings)

    built = []
    for part in parts:
        if part not in all_parts:
            cmds.warning("[MHFit] config 에 없는 파트: {}".format(part))
            continue

        joints = _resolve_joints(all_parts[part], namespace)
        if len(joints) < 2:
            cmds.warning("[MHFit] {} — 유효 조인트 부족 ({} 개)".format(part, len(joints)))
            continue

        # aim axis: 체인 방향으로 자동 계산
        aim_axis = _detect_aim_axis(joints)

        grp_name       = "{}_FitChain_GRP".format(part)
        s["grp_name"]  = grp_name
        s["aim_axis"]  = aim_axis
        nulls = fit_chain_tool.build_aim_system(joints, dict(s))

        if nulls:
            _fit_state[part] = {"grp": grp_name, "joints": joints}
            built.append(part)
            print("[MHFit] Built: {} ({} joints / {} nulls, aim={})".format(
                part, len(joints), len(nulls), aim_axis))
        else:
            cmds.warning("[MHFit] {} — build_aim_system 실패".format(part))

    print("[MHFit] Build 완료: {} / {} 파트".format(len(built), len(parts)))


def _collect_descendants(root):
    """root joint 의 전체 하위 joint 을 재귀적으로 수집 (root 포함)."""
    result = [root]
    children = cmds.listRelatives(root, children=True, type="joint") or []
    for c in children:
        result.extend(_collect_descendants(c))
    return result


def _hier_depth(j):
    """joint 의 hierarchy depth 를 반환."""
    d = 0
    p = cmds.listRelatives(j, parent=True, fullPath=False)
    while p:
        d += 1
        p = cmds.listRelatives(p[0], parent=True, fullPath=False)
    return d


def mirror_fit_chains(parts, across="yz", namespace=mhem.DEFAULT_NAMESPACE):
    """
    config 파트 리스트의 조인트 및 하위 secondary joints 전체를
    반대편으로 mirror 적용.  hierarchy 상위 → 하위 순서로 진행.

    Parameters
    ----------
    parts     : list[str]  미러 대상 파트 이름 목록
    across    : str        'yz' / 'xz' / 'xy'
    namespace : str        MetaHuman scene namespace
    """
    # rl4 output connection 이 있으면 차단
    rl4 = mhem.DEFAULT_RL4_NODE
    if cmds.objExists(rl4):
        conns = cmds.listConnections(
            rl4, source=False, destination=True, plugs=True,
        ) or []
        if conns:
            cmds.confirmDialog(
                title="MH Fit Tool",
                message=(
                    "{} 에 {} 개의 output connection 이 남아 있습니다.\n"
                    "rl4 가 연결된 상태에서는 Mirror 를 실행할 수 없습니다.\n"
                    "Edit Mode 상태에서 실행하세요."
                ).format(rl4, len(conns)),
                button=["확인"],
            )
            return

    cfg       = _load_config()
    all_parts = cfg.get("parts", {})

    # config 파트의 root joints 수집
    root_joints = []
    for part in parts:
        if part not in all_parts:
            continue
        part_joints = _resolve_joints(all_parts[part], namespace)
        if not any(fit_chain_tool._find_opposite_joint(j) for j in part_joints):
            print("[MHFit] Mirror skip (no side): {}".format(part))
            continue
        root_joints.extend(part_joints)

    if not root_joints:
        print("[MHFit] Mirror: 미러 가능한 파트가 없습니다.")
        return

    # root joints 의 전체 하위 계층 수집 (secondary 포함) + 중복 제거
    seen = set()
    all_joints = []
    for rj in root_joints:
        for j in _collect_descendants(rj):
            if j not in seen:
                # opposite 이 존재하는 joint 만 포함
                if fit_chain_tool._find_opposite_joint(j):
                    seen.add(j)
                    all_joints.append(j)

    if not all_joints:
        print("[MHFit] Mirror: 미러 가능한 조인트가 없습니다.")
        return

    # hierarchy 상위 → 하위 순으로 정렬
    all_joints.sort(key=_hier_depth)

    print("[MHFit] Mirror: {} joints (primary + secondary)".format(len(all_joints)))
    fit_chain_tool.mirror_to_opposite_side(all_joints, across)


def apply_and_remove_fit_chains(parts=None):
    """
    선택된 파트들의 fit null transform 을 joint 에 적용 후 시스템 제거.

    전체 파트의 null matrix 를 한 번에 캡처한 뒤,
    aim system 을 전부 제거하고,
    hierarchy 상위 joint 부터 순차 적용하여
    parent 이동에 의한 누적 오차를 방지합니다.

    Parameters
    ----------
    parts : list[str] | None  None 이면 build 된 전체 파트 대상
    """
    if parts is None:
        parts = list(_fit_state.keys())

    # ── 1) 전체 파트 null matrix 일괄 캡처 ─────────────────────
    all_captured = []   # [(jnt, m16), ...]
    grps = []
    applied = []

    for part in parts:
        if part not in _fit_state:
            cmds.warning("[MHFit] {} 는 build 되지 않았습니다.".format(part))
            continue
        info = _fit_state[part]
        captured = fit_chain_tool.collect_null_matrices(info["joints"])
        all_captured.extend(captured)
        grps.append(info["grp"])
        applied.append(part)

    if not all_captured:
        print("[MHFit] 캡처된 null matrix 가 없습니다.")
        return

    # ── 2) aim system 전체 제거 ────────────────────────────────
    for grp in grps:
        fit_chain_tool.remove_aim_system(grp)

    # ── 3) hierarchy 상위 → 하위 정렬 후 일괄 적용 ────────────
    def _depth(pair):
        j = pair[0]
        d = 0
        p = cmds.listRelatives(j, parent=True, fullPath=False)
        while p:
            d += 1
            p = cmds.listRelatives(p[0], parent=True, fullPath=False)
        return d

    all_captured.sort(key=_depth)
    fit_chain_tool.apply_captured_matrices(all_captured)

    for part in applied:
        _fit_state.pop(part, None)

    print("[MHFit] Apply & Remove 완료: {} 파트, {} joints".format(
        len(applied), len(all_captured)))


def restore_structure_only():
    """
    restore_structure 만 실행 — 작업자 뷰포트 검수용 단계.

    secondary joints 를 원래 parent 로 재연결하고 visible 로 복원합니다.
    이 시점에서 rl4 는 아직 미연결 상태이므로 스켈레톤을 자유롭게 확인할 수 있습니다.
    검수 완료 후 export_dna_and_reconnect() 를 호출하세요.
    """
    print("[MHFit] restore_structure 실행 중...")
    mhem.restore_structure()
    print("[MHFit] Restore 완료 — 씬을 검수한 뒤 'Export DNA & Reconnect' 를 실행하세요.")


def _enhanced_restore(follow_parent=False):
    """
    강화된 restore: twist positioning + correctiveRoot 순서 제어.

    Parameters
    ----------
    follow_parent : bool
        True  — secondary joints 가 상위 관절의 이동된 위치를 따름
                (correctiveRoot 제로화 전에 하위 조인트를 parent)
        False — 기존 위치 유지 (correctiveRoot 제로화 후 하위 조인트를 parent)
    """
    mhem.ensure_state()
    if not mhem._state["active"]:
        print("[MHFit] Not in edit mode.")
        return

    parent_map = mhem._state["parent_map"]
    if not parent_map:
        return

    # ── 분류 ─────────────────────────────────────────────────
    twist_joints = set()
    cr_joints = set()

    for j in parent_map:
        short = j.split(":")[-1]
        if "correctiveRoot" in short:
            cr_joints.add(j)
        elif "twist" in short and "twistCor" not in short:
            twist_joints.add(j)

    # twist 를 parent 별로 그룹핑
    twist_by_parent = {}
    for t in twist_joints:
        twist_by_parent.setdefault(parent_map[t], []).append(t)
    for v in twist_by_parent.values():
        v.sort()

    # twist 의 하위 조인트 (parent 가 twist 인 것 — twistCor 등)
    twist_children = {}
    for j, p in parent_map.items():
        if p in twist_joints and j not in twist_joints:
            twist_children.setdefault(p, []).append(j)

    # correctiveRoot 의 하위 조인트
    cr_child_map = {cr: [] for cr in cr_joints}
    for j, p in parent_map.items():
        if p in cr_joints and j not in cr_joints:
            cr_child_map[p].append(j)

    # 나머지 (other)
    all_twist_ch = set()
    for ch in twist_children.values():
        all_twist_ch.update(ch)
    all_cr_ch = set()
    for ch in cr_child_map.values():
        all_cr_ch.update(ch)

    other_joints = [
        j for j in parent_map
        if j not in twist_joints
        and j not in cr_joints
        and j not in all_twist_ch
        and j not in all_cr_ch
    ]
    other_sorted = mhem._sort_by_depth({j: parent_map[j] for j in other_joints})

    cmds.undoInfo(openChunk=True, chunkName="MHFit_enhancedRestore")
    try:
        # ── 기타 secondary 복원 ──────────────────────────────
        for j in other_sorted:
            orig_par = parent_map[j]
            if not cmds.objExists(j):
                continue
            if orig_par and cmds.objExists(orig_par):
                cmds.parent(j, orig_par)
            if mhem._is_snap(j):
                cmds.setAttr(j + ".translate", 0, 0, 0, type="double3")

        # ── twist joints 복원 ────────────────────────────────
        for parent_jnt, twists in twist_by_parent.items():
            if not parent_jnt or not cmds.objExists(parent_jnt):
                continue

            # 상위 관절의 primary child 찾기
            children = cmds.listRelatives(
                parent_jnt, children=True, type="joint",
            ) or []
            child_primary = None
            for c in children:
                if not mhem._is_secondary(c):
                    child_primary = c
                    break

            par_pos = cmds.xform(parent_jnt, q=True, ws=True, t=True)
            child_pos = (
                cmds.xform(child_primary, q=True, ws=True, t=True)
                if child_primary else None
            )

            n = len(twists)
            for i, t in enumerate(twists):
                if not cmds.objExists(t):
                    continue
                cmds.parent(t, parent_jnt)
                # jointOrient / rotate 제로화 (먼저 — 이후 position 설정이 정확)
                cmds.setAttr(t + ".jointOrient", 0, 0, 0, type="double3")
                cmds.setAttr(t + ".rotate", 0, 0, 0, type="double3")

                if child_pos:
                    frac = (i + 1.0) / (n + 1.0)
                    pos = [
                        par_pos[k] + (child_pos[k] - par_pos[k]) * frac
                        for k in range(3)
                    ]
                    cmds.xform(t, ws=True, t=pos)

                # twist 하위 조인트 transform 제로화
                for tc in twist_children.get(t, []):
                    if cmds.objExists(tc):
                        cmds.parent(tc, t)
                        cmds.setAttr(tc + ".translate", 0, 0, 0, type="double3")
                        cmds.setAttr(tc + ".rotate", 0, 0, 0, type="double3")
                        cmds.setAttr(tc + ".jointOrient", 0, 0, 0, type="double3")

        # ── correctiveRoot 복원 ──────────────────────────────
        for cr in cr_joints:
            orig_par = parent_map[cr]
            if not cmds.objExists(cr):
                continue
            if not (orig_par and cmds.objExists(orig_par)):
                continue

            cmds.parent(cr, orig_par)

            if follow_parent:
                # 하위 조인트 먼저 parent → correctiveRoot 제로화
                for child in cr_child_map.get(cr, []):
                    if cmds.objExists(child):
                        cmds.parent(child, cr)
                cmds.setAttr(cr + ".translate", 0, 0, 0, type="double3")
                cmds.setAttr(cr + ".rotate", 0, 0, 0, type="double3")
                cmds.setAttr(cr + ".jointOrient", 0, 0, 0, type="double3")
            else:
                # correctiveRoot 제로화 먼저 → DG 평가 → 하위 조인트 parent
                cmds.setAttr(cr + ".translate", 0, 0, 0, type="double3")
                cmds.setAttr(cr + ".rotate", 0, 0, 0, type="double3")
                cmds.setAttr(cr + ".jointOrient", 0, 0, 0, type="double3")
                cmds.getAttr(cr + ".worldMatrix[0]")  # DG 강제 평가
                for child in cr_child_map.get(cr, []):
                    if cmds.objExists(child):
                        cmds.parent(child, cr)

    finally:
        cmds.undoInfo(closeChunk=True)

    # visibility 복원
    for j in parent_map:
        if cmds.objExists(j):
            try:
                cmds.setAttr(j + ".visibility", 1)
            except Exception:
                pass

    print("[MHFit] Enhanced restore 완료 (follow_parent={})".format(follow_parent))


def apply_remove_and_restore(follow_parent=False):
    """
    Apply & Remove All Fit Chains + Enhanced Restore 를 한 번에 실행.
    _fit_state 가 비어 있으면 팝업 후 중단.
    """
    if not _fit_state:
        cmds.confirmDialog(
            title="MH Fit Tool",
            message="Build 된 Fit Chain 이 없습니다.\nStep 2 의 'Build Fit Chains' 를 먼저 실행하세요.",
            button=["확인"],
        )
        return

    apply_and_remove_fit_chains()
    _enhanced_restore(follow_parent)


def export_dna_and_reconnect(
    output_path=None,
    input_dna_path=None,
    namespace=mhem.DEFAULT_NAMESPACE,
):
    """
    export_dna_from_scene → reconnect_rl4 를 순차 실행.
    restore_structure_only() 로 씬 검수를 완료한 뒤 호출하세요.

    Parameters
    ----------
    output_path   : str | None  None 이면 rl4.dnaFilePath 기반 자동 추론
    input_dna_path: str | None  None 이면 mhem.DEFAULT_DNA_INPUT
    namespace     : str         MetaHuman scene namespace
    """
    if not output_path or not output_path.strip():
        output_path = _get_dna_output_path()
        if not output_path:
            cmds.confirmDialog(
                title="MH Fit Tool",
                message=(
                    "DNA 출력 경로를 결정할 수 없습니다.\n"
                    "body_rl4Embedded.dnaFilePath 가 설정되어 있는지 확인하거나\n"
                    "Output 필드에 경로를 직접 입력하세요."
                ),
                button=["확인"],
            )
            return

    if not input_dna_path or not input_dna_path.strip():
        input_dna_path = _get_dna_source_path() or mhem.DEFAULT_DNA_INPUT

    # rotate → jointOrient 베이크 (RL4 가 rotate 를 드라이빙하므로 reconnect 전에 실행)
    print("[MHFit] bake_rotate_to_joint_orient 실행 중...")
    mhem.bake_rotate_to_joint_orient(namespace)

    print("[MHFit] export_dna_from_scene 실행 중...")
    mhem.export_dna_from_scene(output_path, input_dna_path, namespace)

    print("[MHFit] reconnect_rl4 실행 중...")
    mhem.reconnect_rl4()

    print("[MHFit] Export & Reconnect 완료 → {}".format(output_path))


# ═══════════════════════════════════════════════════════════
#  UI
# ═══════════════════════════════════════════════════════════

_WIN = "MHFitToolWin"

# up_method 코드 ↔ 레이블 매핑  (A = Joint Axis 를 기본값으로 첫 번째에 배치)
_METHOD_ITEMS = [
    ("A", "A — Joint Axis"),
    ("B", "B — World Vector"),
    ("C", "C — Auto"),
]
def _set_all_checks(chk_map, value):
    for chk in chk_map.values():
        cmds.checkBox(chk, edit=True, value=value)


def _browse_dir(field_ctrl, caption="Select Folder"):
    result = cmds.fileDialog2(
        dialogStyle=2,
        fileMode=3,
        caption=caption,
    )
    if result:
        cmds.textFieldButtonGrp(field_ctrl, edit=True, text=result[0])
        mhem.set_mh_lib_root(result[0])


def _browse_file(field_ctrl, mode, caption="Select DNA File"):
    result = cmds.fileDialog2(
        fileFilter="DNA Files (*.dna);;All Files (*.*)",
        dialogStyle=2,
        fileMode=mode,
        caption=caption,
    )
    if result:
        cmds.textFieldButtonGrp(field_ctrl, edit=True, text=result[0])


def _on_build(chk_map, up_menu, method_menu, ns_field):
    if not mhem._state["active"]:
        cmds.confirmDialog(
            title="MH Fit Tool",
            message="Edit Mode 가 활성화되어 있지 않습니다.\nStep 1 의 'Enter Edit Mode' 를 먼저 실행하세요.",
            button=["확인"],
        )
        return

    selected = [p for p, chk in chk_map.items()
                if cmds.checkBox(chk, q=True, value=True)]
    if not selected:
        cmds.confirmDialog(
            title="MH Fit Tool",
            message="파트를 하나 이상 선택하세요.",
            button=["확인"],
        )
        return

    method_label = cmds.optionMenu(method_menu, q=True, value=True)
    method_code  = method_label[0]   # 첫 글자 "A" / "B" / "C"
    up_axis_val  = cmds.optionMenu(up_menu, q=True, value=True)
    up_ax_letter = up_axis_val[-1]   # "+Z" → "Z"

    settings = {
        # aim_axis 는 build_fit_chains 내부에서 체인별 자동 계산
        "up_axis"       : up_axis_val,
        "up_method"     : method_code,
        "up_local_axis" : up_ax_letter,
        "up_world_vec"  : up_axis_val,   # method B 일 때 사용
        "up_object"     : "",
        "up_object_axis": up_ax_letter,
    }
    namespace = cmds.textFieldGrp(ns_field, q=True, text=True).strip()
    build_fit_chains(selected, settings, namespace)


def _on_export_dna(out_field, in_field, ns_field):
    out = cmds.textFieldButtonGrp(out_field, q=True, text=True).strip()
    src = cmds.textFieldButtonGrp(in_field,  q=True, text=True).strip()
    ns  = cmds.textFieldGrp(ns_field,        q=True, text=True).strip()

    result = cmds.confirmDialog(
        title="Export DNA — 검수 확인",
        message=(
            "뷰포트에서 스켈레톤 상태를 검수했습니까?\n\n"
            "Output : {}\n\n"
            "확인을 누르면 DNA 를 내보내고 rl4 를 재연결합니다."
        ).format(out or "(자동 추론)"),
        button=["Export", "취소"],
        defaultButton="Export",
        cancelButton="취소",
        dismissString="취소",
    )
    if result == "Export":
        export_dna_and_reconnect(out or None, src or None, ns)


def _show_help(title, msg):
    """도움말 팝업."""
    cmds.confirmDialog(
        title="Help  —  " + title,
        message=msg,
        button=["확인"],
        defaultButton="확인",
    )


_HELP_STEP1 = (
    "【 Step 1 : Enter Edit Mode 】\n\n"
    "MetaHuman 스켈레톤 피팅 작업을 위한 준비 단계입니다.\n\n"
    "Enter Edit Mode :\n"
    "  · body_rl4Embedded 노드의 연결을 해제합니다.\n"
    "  · secondary joints 를 unparent 하고 숨깁니다.\n\n"
    "Namespace :\n"
    "  · MetaHuman 씬의 네임스페이스를 입력합니다.\n"
    "  · 기본값 : m_uhn_metahuman"
)

_HELP_STEP2 = (
    "【 Step 2 : Build Fit Chains 】\n\n"
    "fit_chains_config.json 에 정의된 파트 기반으로\n"
    "Aim 시스템(컨트롤러 + null)을 일괄 생성합니다.\n\n"
    "Aim Axis :\n"
    "  체인 방향을 자동 감지하여 설정합니다.\n\n"
    "Up Axis :\n"
    "  Aim 방향과 수직인 Up 벡터 방향을 지정합니다.\n\n"
    "Up Method :\n"
    "  A — Joint Axis  : 조인트 로컬 축을 Up 기준으로 사용합니다.\n"
    "                    가장 안정적이며 기본값입니다.\n"
    "  B — World Vector : 월드 벡터를 Up 기준으로 사용합니다.\n"
    "  C — Auto         : Aim 방향에 따라 Up 축을 자동 결정합니다.\n\n"
    "Parts :\n"
    "  · 빌드할 체인 파트를 선택합니다.\n"
    "  · All / None 버튼으로 전체 선택 / 해제합니다.\n"
    "  · 빌드 후 viewport 컨트롤러로 조인트 위치를 조정합니다."
)

_HELP_STEP3 = (
    "【 Step 3 : Apply & Restore 】\n\n"
    "Apply & Restore :\n"
    "  · fit null 의 world transform 을 joint 에 반영합니다.\n"
    "  · 반영 완료 후 Aim 시스템 노드를 전부 제거합니다.\n"
    "  · secondary joints 를 원래 hierarchy 로 복원합니다.\n\n"
    "Twist joints :\n"
    "  · 상위 관절 ~ 하위 관절 사이 1/3, 2/3 지점에 위치\n"
    "  · jointOrient / rotate 제로화\n\n"
    "correctiveRoot joints :\n"
    "  · 상위 관절에 parent 후 transform 제로화\n\n"
    "□ Follow Parent Transform :\n"
    "  OFF — correctiveRoot 제로화 후 하위 조인트 parent\n"
    "        (하위 조인트가 기존 월드 위치 유지)\n"
    "  ON  — 하위 조인트 parent 후 correctiveRoot 제로화\n"
    "        (하위 조인트가 상위 관절 이동을 따라감)\n\n"
    "이 시점에서 rl4 는 아직 미연결 상태입니다.\n"
    "뷰포트에서 스켈레톤을 검수한 뒤 Mirror / Export 를 진행하세요."
)

_HELP_MIRROR = (
    "【 Mirror → Opposite Side 】\n\n"
    "  · 선택된 파트의 fit 결과를 반대쪽(_r ↔ _l)으로 미러합니다.\n"
    "  · spine / neck 등 side 없는 파트는 자동으로 건너뜁니다.\n"
    "  · Mirror Plane : 미러 기준 평면 (기본값 YZ)\n\n"
    "Apply & Restore 실행 후, 뷰포트에서 스켈레톤을 검수한 뒤\n"
    "필요한 경우에만 실행하세요."
)

_HELP_STEP4B = (
    "【 Step 4 : Export DNA & Reconnect 】\n\n"
    "Apply & Restore 후 검수를 완료했을 때 실행합니다.\n"
    "확인 대화상자를 거친 뒤 아래 순서로 자동 실행됩니다 :\n"
    "  1. export DNA    : 변경된 스켈레톤을 DNA 파일로 저장\n"
    "  2. reconnect rl4 : body_rl4Embedded 재연결 및 스킨 rebind\n\n"
    "Output : 저장할 DNA 파일 경로\n"
    "  · 미입력 시 rl4.dnaFilePath 기반으로 자동 추론합니다.\n"
    "  · 예) body.dna  →  body_edit.dna\n\n"
    "Source : 원본(입력) DNA 파일 경로\n"
    "  · MetaHuman 기본 DNA 파일을 지정합니다."
)


def build_tab_ui(parent=None):
    """탭 또는 독립 윈도우에 UI 를 빌드. rig_tool_hub 통합용."""
    cfg        = _load_config()
    part_names = list(cfg.get("parts", {}).keys())

    scroll = cmds.scrollLayout(childResizable=True, parent=parent) if parent \
             else cmds.scrollLayout(childResizable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4, columnOffset=["both", 8])

    # ── Path Settings ──────────────────────────────────────────
    cmds.separator(h=6, style="none")
    cmds.frameLayout(
        label="  Path Settings",
        collapsable=True,
        collapse=bool(mhem.MH_LIB_ROOT),
        marginWidth=6,
        marginHeight=6,
    )
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    cmds.text(
        label="MetaHumanForMaya lib 경로  (자동 탐색됨 — 변경 시 폴더 선택)",
        align="left",
        font="smallPlainLabelFont",
    )
    lib_field = cmds.textFieldButtonGrp(
        label="MH Lib :",
        text=mhem.MH_LIB_ROOT,
        buttonLabel="...",
        columnWidth3=(58, 220, 36),
        adjustableColumn=2,
        buttonCommand=lambda *_: _browse_dir(lib_field, caption="Select MetaHumanForMaya/lib"),
    )
    cmds.textFieldButtonGrp(
        lib_field, edit=True,
        changeCommand=lambda val: mhem.set_mh_lib_root(val),
    )
    if not mhem.MH_LIB_ROOT:
        cmds.text(
            label="  !! 경로를 찾을 수 없습니다 — 직접 설정하세요",
            align="left",
            font="smallBoldLabelFont",
        )
    cmds.setParent("..")   # columnLayout → frameLayout
    cmds.setParent("..")   # frameLayout  → root_col

    # ── Step 1 : Enter Edit Mode ───────────────────────────────
    cmds.separator(h=6, style="none")
    cmds.frameLayout(
        label="  1.  Enter Edit Mode",
        collapsable=False,
        marginWidth=6,
        marginHeight=6,
    )
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    cmds.text(
        label="rl4 disconnect → secondary joints unparent & hide",
        align="left",
        font="smallPlainLabelFont",
    )
    ns_field = cmds.textFieldGrp(
        label="Namespace:",
        text=mhem.DEFAULT_NAMESPACE,
        columnWidth2=(72, 180),
        adjustableColumn=2,
    )
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(322, 26), adjustableColumn=1)
    cmds.button(
        label="Enter Edit Mode",
        height=30,
        backgroundColor=(0.28, 0.48, 0.32),
        command=lambda *_: mhem.enter_edit_mode(force=True),
    )
    cmds.button(
        label="?", width=26, height=30,
        backgroundColor=(0.25, 0.25, 0.35),
        command=lambda *_: _show_help("Enter Edit Mode", _HELP_STEP1),
    )
    cmds.setParent("..")   # rowLayout → columnLayout
    cmds.setParent("..")   # columnLayout → frameLayout
    cmds.setParent("..")   # frameLayout  → root_col

    # ── Step 2 : Build Fit Chains ─────────────────────────────
    cmds.frameLayout(
        label="  2.  Build Fit Chains",
        collapsable=False,
        marginWidth=6,
        marginHeight=6,
    )
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)

    # Up Axis / Up Method 설정  (Aim Axis 는 체인별 자동 계산)
    cmds.text(
        label="  * Aim Axis : 체인 방향 자동 계산",
        align="left",
        font="smallPlainLabelFont",
    )
    cmds.rowLayout(
        numberOfColumns=4,
        columnWidth4=(64, 74, 72, 200),
        columnAlign4=["right", "left", "right", "left"],
        adjustableColumn=4,
    )
    cmds.text(label="Up Axis :")
    up_menu = cmds.optionMenu()
    for ax in ["+Z", "-Z", "+Y", "-Y", "+X", "-X"]:   # +Z 기본값
        cmds.menuItem(label=ax)
    cmds.text(label="  Up Method :")
    method_menu = cmds.optionMenu()
    for code, lbl in _METHOD_ITEMS:                    # A — Joint Axis 기본값
        cmds.menuItem(label=lbl)
    cmds.setParent("..")

    cmds.separator(h=4)

    # Parts 체크리스트
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=1)
    cmds.text(label="Parts", align="left")
    cmds.button(
        label="All",
        width=46,
        command=lambda *_: _set_all_checks(chk_map, True),
    )
    cmds.button(
        label="None",
        width=46,
        command=lambda *_: _set_all_checks(chk_map, False),
    )
    cmds.setParent("..")

    chk_map = {}
    cmds.gridLayout(numberOfColumns=2, cellWidthHeight=(172, 22))
    for p in part_names:
        chk_map[p] = cmds.checkBox(label=p, value=True)
    cmds.setParent("..")   # gridLayout

    cmds.separator(h=4)
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(322, 26), adjustableColumn=1)
    cmds.button(
        label="Build Selected Fit Chains",
        height=30,
        backgroundColor=(0.28, 0.42, 0.58),
        command=lambda *_: _on_build(
            chk_map, up_menu, method_menu, ns_field
        ),
    )
    cmds.button(
        label="?", width=26, height=30,
        backgroundColor=(0.25, 0.25, 0.35),
        command=lambda *_: _show_help("Build Fit Chains", _HELP_STEP2),
    )
    cmds.setParent("..")   # rowLayout → columnLayout
    cmds.setParent("..")   # columnLayout → frameLayout
    cmds.setParent("..")   # frameLayout  → root_col

    # ── Step 3 : Apply & Restore ─────────────────────────────
    cmds.frameLayout(
        label="  3.  Apply & Restore",
        collapsable=False,
        marginWidth=6,
        marginHeight=6,
    )
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    cmds.text(
        label="fit 결과 반영 → aim system 제거 → secondary joints 복원",
        align="left",
        font="smallPlainLabelFont",
    )
    follow_chk = cmds.checkBox(
        label="Secondary joints 가 상위 관절의 이동을 따름",
        value=False,
    )
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(322, 26), adjustableColumn=1)
    cmds.button(
        label="Apply & Restore",
        height=30,
        backgroundColor=(0.52, 0.44, 0.28),
        command=lambda *_: apply_remove_and_restore(
            follow_parent=cmds.checkBox(follow_chk, q=True, value=True),
        ),
    )
    cmds.button(
        label="?", width=26, height=30,
        backgroundColor=(0.25, 0.25, 0.35),
        command=lambda *_: _show_help("Apply & Restore", _HELP_STEP3),
    )
    cmds.setParent("..")   # rowLayout → columnLayout

    cmds.separator(h=6)
    cmds.text(
        label="뷰포트에서 스켈레톤 검수 후 필요 시 Mirror 실행",
        align="left",
        font="smallPlainLabelFont",
    )
    cmds.rowLayout(
        numberOfColumns=4,
        columnWidth4=(70, 64, 192, 26),
        columnAlign4=["right", "left", "left", "left"],
        adjustableColumn=3,
    )
    cmds.text(label="Mirror Plane :")
    mirror_menu = cmds.optionMenu()
    for plane in ["YZ", "XZ", "XY"]:
        cmds.menuItem(label=plane)
    cmds.button(
        label="Mirror → Opposite Side",
        height=26,
        backgroundColor=(0.25, 0.35, 0.50),
        command=lambda *_: mirror_fit_chains(
            [p for p, chk in chk_map.items()
             if cmds.checkBox(chk, q=True, value=True)],
            cmds.optionMenu(mirror_menu, q=True, value=True).lower(),
            cmds.textFieldGrp(ns_field, q=True, text=True).strip(),
        ),
    )
    cmds.button(
        label="?", width=26, height=26,
        backgroundColor=(0.25, 0.25, 0.35),
        command=lambda *_: _show_help("Mirror", _HELP_MIRROR),
    )
    cmds.setParent("..")   # rowLayout → columnLayout
    cmds.setParent("..")   # columnLayout → frameLayout
    cmds.setParent("..")   # frameLayout  → root_col

    # ── Step 4 : Export DNA & Reconnect ────────────────────────
    cmds.frameLayout(
        label="  4.  Export DNA & Reconnect",
        collapsable=False,
        marginWidth=6,
        marginHeight=6,
    )
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    cmds.text(
        label="검수 완료 후 실행 — export DNA → reconnect rl4 & rebind skins",
        align="left",
        font="smallPlainLabelFont",
    )

    default_out = _get_dna_output_path()
    out_field = cmds.textFieldButtonGrp(
        label="Output :",
        text=default_out,
        buttonLabel="...",
        columnWidth3=(58, 220, 36),
        adjustableColumn=2,
        buttonCommand=lambda *_: _browse_file(out_field, mode=0, caption="Save DNA As"),
    )
    in_field = cmds.textFieldButtonGrp(
        label="Source :",
        text=_get_dna_source_path(),
        buttonLabel="...",
        columnWidth3=(58, 220, 36),
        adjustableColumn=2,
        buttonCommand=lambda *_: _browse_file(in_field, mode=1, caption="Select Source DNA"),
    )
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(322, 26), adjustableColumn=1)
    cmds.button(
        label="Export DNA & Reconnect",
        height=32,
        backgroundColor=(0.52, 0.28, 0.28),
        command=lambda *_: _on_export_dna(out_field, in_field, ns_field),
    )
    cmds.button(
        label="?", width=26, height=32,
        backgroundColor=(0.25, 0.25, 0.35),
        command=lambda *_: _show_help("Export DNA & Reconnect", _HELP_STEP4B),
    )
    cmds.setParent("..")   # rowLayout → columnLayout
    cmds.setParent("..")
    cmds.setParent("..")

    # ── 유틸리티 ────────────────────────────────────────────────
    cmds.separator(h=6)
    cmds.button(
        label="Full Exit  (DNA export 없이 원복)",
        height=26,
        backgroundColor=(0.36, 0.36, 0.36),
        command=lambda *_: mhem.full_exit(),
    )
    cmds.separator(h=6, style="none")
    cmds.setParent("..")   # columnLayout → scroll
    return scroll


def show():
    """MH Fit Tool 독립 윈도우 실행."""
    importlib.reload(fit_chain_tool)
    importlib.reload(mhem)

    if cmds.window(_WIN, exists=True):
        cmds.deleteUI(_WIN)

    win = cmds.window(
        _WIN,
        title="MH Fit Tool",
        widthHeight=(370, 640),
        sizeable=True,
    )
    build_tab_ui(win)
    cmds.showWindow(win)
