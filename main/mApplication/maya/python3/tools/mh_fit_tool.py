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
4. Export & Reconnect → restore_structure() → export_dna_from_scene()
                        → reconnect_rl4()

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


def mirror_fit_chains(parts, across="yz", namespace=mhem.DEFAULT_NAMESPACE):
    """
    config 파트 리스트의 조인트에 대해 선택 없이 반대편으로 mirror 적용.

    Parameters
    ----------
    parts     : list[str]  미러 대상 파트 이름 목록
    across    : str        'yz' / 'xz' / 'xy'
    namespace : str        MetaHuman scene namespace
    """
    cfg       = _load_config()
    all_parts = cfg.get("parts", {})

    joints = []
    for part in parts:
        if part not in all_parts:
            continue
        part_joints = _resolve_joints(all_parts[part], namespace)
        # side suffix (_l/_r 등)가 하나라도 있는 파트만 포함
        if not any(fit_chain_tool._find_opposite_joint(j) for j in part_joints):
            print("[MHFit] Mirror skip (no side): {}".format(part))
            continue
        joints.extend(part_joints)

    if not joints:
        print("[MHFit] Mirror: 미러 가능한 파트가 없습니다.")
        return

    fit_chain_tool.mirror_to_opposite_side(joints, across)


def apply_and_remove_fit_chains(parts=None):
    """
    선택된 파트들의 fit null transform 을 joint 에 적용 후 시스템 제거.

    Parameters
    ----------
    parts : list[str] | None  None 이면 build 된 전체 파트 대상
    """
    if parts is None:
        parts = list(_fit_state.keys())

    applied = []
    for part in parts:
        if part not in _fit_state:
            cmds.warning("[MHFit] {} 는 build 되지 않았습니다.".format(part))
            continue
        info = _fit_state[part]
        # 1. null worldMatrix 를 aim system 이 살아있는 상태에서 미리 캡처
        captured = fit_chain_tool.collect_null_matrices(info["joints"])
        # 2. aim system 제거 (VP 노드 삭제 → joint 이동 시 zero-vector 재평가 없음)
        fit_chain_tool.remove_aim_system(info["grp"])
        # 3. 캡처된 matrix 로 joint 에 적용
        fit_chain_tool.apply_captured_matrices(captured)
        applied.append(part)
        print("[MHFit] Applied & Removed: {}".format(part))

    for part in applied:
        _fit_state.pop(part, None)

    print("[MHFit] Apply & Remove 완료: {} 파트".format(len(applied)))


def export_and_reconnect(
    output_path=None,
    input_dna_path=None,
    namespace=mhem.DEFAULT_NAMESPACE,
):
    """
    restore_structure → export_dna_from_scene → reconnect_rl4 를 순차 실행.

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

    print("[MHFit] restore_structure 실행 중...")
    mhem.restore_structure()

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


def _on_export(out_field, in_field, ns_field):
    out = cmds.textFieldButtonGrp(out_field, q=True, text=True).strip()
    src = cmds.textFieldButtonGrp(in_field,  q=True, text=True).strip()
    ns  = cmds.textFieldGrp(ns_field,        q=True, text=True).strip()
    export_and_reconnect(out or None, src or None, ns)


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
    "【 Step 3 : Apply & Remove Fit Chains 】\n\n"
    "Apply & Remove All Fit Chains :\n"
    "  · fit null 의 world transform 을 joint 에 반영합니다.\n"
    "  · 반영 완료 후 Aim 시스템 노드를 전부 제거합니다.\n"
    "  · Build 된 모든 파트에 일괄 적용됩니다.\n\n"
    "Mirror → Opposite Side :\n"
    "  · 선택된 파트의 fit 결과를 반대쪽(_r ↔ _l)으로 미러합니다.\n"
    "  · spine / neck 등 side 없는 파트는 자동으로 건너뜁니다.\n"
    "  · Mirror Plane : 미러 기준 평면 (기본값 YZ)"
)

_HELP_STEP4 = (
    "【 Step 4 : Export DNA & Reconnect 】\n\n"
    "아래 순서로 자동 실행됩니다 :\n"
    "  1. restore_structure : secondary joints 재연결 및 표시\n"
    "  2. export DNA        : 변경된 스켈레톤을 DNA 파일로 저장\n"
    "  3. reconnect rl4     : body_rl4Embedded 재연결 및 스킨 rebind\n\n"
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

    # ── Step 3 : Apply & Remove ────────────────────────────────
    cmds.frameLayout(
        label="  3.  Apply & Remove Fit Chains",
        collapsable=False,
        marginWidth=6,
        marginHeight=6,
    )
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    cmds.text(
        label="fit 수정 완료 후 실행 — joint 에 transform 반영 후 시스템 제거",
        align="left",
        font="smallPlainLabelFont",
    )
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(322, 26), adjustableColumn=1)
    cmds.button(
        label="Apply & Remove All Fit Chains",
        height=30,
        backgroundColor=(0.52, 0.44, 0.28),
        command=lambda *_: apply_and_remove_fit_chains(),
    )
    cmds.button(
        label="?", width=26, height=30,
        backgroundColor=(0.25, 0.25, 0.35),
        command=lambda *_: _show_help("Apply & Remove Fit Chains", _HELP_STEP3),
    )
    cmds.setParent("..")   # rowLayout → columnLayout

    cmds.separator(h=6)
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
        command=lambda *_: _show_help("Apply & Remove Fit Chains", _HELP_STEP3),
    )
    cmds.setParent("..")   # rowLayout → columnLayout
    cmds.setParent("..")   # columnLayout → frameLayout
    cmds.setParent("..")   # frameLayout  → root_col

    # ── Step 4 : Export DNA & Reconnect ───────────────────────
    cmds.frameLayout(
        label="  4.  Export DNA & Reconnect",
        collapsable=False,
        marginWidth=6,
        marginHeight=6,
    )
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    cmds.text(
        label="restore_structure → export DNA → reconnect rl4 & rebind skins",
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
        command=lambda *_: _on_export(out_field, in_field, ns_field),
    )
    cmds.button(
        label="?", width=26, height=32,
        backgroundColor=(0.25, 0.25, 0.35),
        command=lambda *_: _show_help("Export DNA & Reconnect", _HELP_STEP4),
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
