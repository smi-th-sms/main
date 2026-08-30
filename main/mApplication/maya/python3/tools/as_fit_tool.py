"""
AS Fit Tool - AdvancedSkeleton FitSkeleton Helper
NameMatcher 없이 FitSkeleton 배치 및 리깅 셋업을 위한 툴

기능:
  - Create + Place FitSkeleton  : FitSkeleton Import 후 조인트 위치에 자동 배치
  - Show / Straighten PoleVectors

사용법:
    import importlib
    from python3.tools import as_fit_tool
    importlib.reload(as_fit_tool)
    as_fit_tool.show()
"""

import maya.cmds as cmds
import maya.mel as mel
import os
import sys
import subprocess

_AS_PATH_OPTVAR = "asFitToolScriptPath"   # Maya optionVar 키 (세션 간 경로 유지)

# ──────────────────────────────────────────────────────────────
# MetaHuman 기본 매핑 - base name 기준 (side suffix 제외)
# Side Settings 기본값: Right=_r, Left=_l
# ──────────────────────────────────────────────────────────────
DEFAULT_MAPPING = [
    ("Root",            "pelvis"),
    ("Spine1",          "spine_01"),
    ("Spine2",          "spine_02"),
    ("Spine3",          "spine_03"),
    ("Spine4",          "spine_04"),
    ("Chest",           "spine_05"),
    ("Neck0",           "neck_01"),
    ("Neck1",           "neck_02"),
    ("Head",            "head"),
    ("Scapula",         "clavicle"),
    ("Shoulder",        "upperarm"),
    ("Elbow",           "lowerarm"),
    ("Wrist",           "hand"),
    ("ThumbFinger1",    "thumb_01"),
    ("ThumbFinger2",    "thumb_02"),
    ("ThumbFinger3",    "thumb_03"),
    ("IndexFinger0",    "index_metacarpal"),
    ("IndexFinger1",    "index_01"),
    ("IndexFinger2",    "index_02"),
    ("IndexFinger3",    "index_03"),
    ("MiddleFinger0",   "middle_metacarpal"),
    ("MiddleFinger1",   "middle_01"),
    ("MiddleFinger2",   "middle_02"),
    ("MiddleFinger3",   "middle_03"),
    ("RingFinger0",     "ring_metacarpal"),
    ("RingFinger1",     "ring_01"),
    ("RingFinger2",     "ring_02"),
    ("RingFinger3",     "ring_03"),
    ("PinkyFinger0",    "pinky_metacarpal"),
    ("PinkyFinger1",    "pinky_01"),
    ("PinkyFinger2",    "pinky_02"),
    ("PinkyFinger3",    "pinky_03"),
    ("Hip",             "thigh"),
    ("Knee",            "calf"),
    ("Ankle",           "foot"),
    ("Toes",            "ball"),
]

# 기본 Side 설정 (MetaHuman 기준)
DEFAULT_SIDE = {
    'sideRight':     '_r',
    'sideLeft':      '_l',
    'sideMiddle':    '',
    'sideBeforeName': False,
    'sideUnderScore': False,
}

# 자동 감지에 쓸 공통 side 패턴 (right, left 쌍)
_COMMON_SIDE_PAIRS = [
    ("_r", "_l"), ("_R", "_L"),
    ("Right", "Left"), ("right", "left"),
    ("R_", "L_"),
]

# ──────────────────────────────────────────────────────────────
# NameMatcher .txt 파서
# ──────────────────────────────────────────────────────────────

def _parse_namematcher_txt(path):
    """
    nameMatchers .txt 파일 파싱.
    반환: {
        'sideRight': str, 'sideLeft': str, 'sideMiddle': str,
        'sideBeforeName': bool, 'sideUnderScore': bool,
        'mapping': [(as_joint, mh_joint), ...]
    }
    """
    result = {
        'sideRight': '', 'sideLeft': '', 'sideMiddle': '',
        'sideBeforeName': False, 'sideUnderScore': False,
        'mapping': [],
    }
    if not os.path.isfile(path):
        return result

    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or '=' not in line:
                continue
            key, _, val = line.partition('=')
            key = key.strip()
            val = val.strip()
            if key == 'sideRight':
                result['sideRight'] = val
            elif key == 'sideLeft':
                result['sideLeft'] = val
            elif key == 'sideMiddle':
                result['sideMiddle'] = val
            elif key == 'sideBeforeName':
                result['sideBeforeName'] = (val == '1')
            elif key == 'sideUnderScore':
                result['sideUnderScore'] = (val == '1')
            else:
                result['mapping'].append((key, val))

    return result


# ──────────────────────────────────────────────────────────────
# MH 조인트 이름 해석 (side 설정 + 존재 체크)
# ──────────────────────────────────────────────────────────────

def _normalize_template_data(data):
    """
    .txt에서 sideRight/sideLeft가 비어 있지만 매핑 값에 side가 내포된 경우 정규화.

    예) MetaHuman.txt: sideRight="", Hip="thigh_r"
        → sideRight="_r", sideLeft="_l", Hip="thigh"  (base name으로 통일)

    이미 sideRight/sideLeft가 명시된 경우(Mixamo 등)는 변경 없음.
    """
    if data['sideRight'] or data['sideLeft']:
        return data  # 명시적 side 설정 있음 → 변경 불필요

    # 매핑 값에서 side 패턴 자동 감지
    for r_pat, l_pat in _COMMON_SIDE_PAIRS:
        if any(mh.endswith(r_pat) or mh.endswith(l_pat)
               for _, mh in data['mapping']):
            # side 제거하여 base name으로 정규화
            normalized = []
            for as_j, mh_j in data['mapping']:
                if mh_j.endswith(r_pat):
                    normalized.append((as_j, mh_j[:-len(r_pat)]))
                elif mh_j.endswith(l_pat):
                    normalized.append((as_j, mh_j[:-len(l_pat)]))
                else:
                    normalized.append((as_j, mh_j))
            data['sideRight'] = r_pat
            data['sideLeft']  = l_pat
            data['mapping']   = normalized
            return data

    return data


def _resolve_mh_joint(base_mh, as_side, ns_b,
                       side_right, side_left, side_middle,
                       before_name, use_underscore):
    """
    AS side (_R / _L / _M) 기준으로 MH 조인트 이름 결정.

    해석 우선순위 (_L 기준):
      1. sideLeft 설정값으로 이름 생성 → 씬 존재 확인
      2. 없으면 base_mh 이름 내 공통 side 패턴 자동 감지 후 치환 → 존재 확인
      3. 그래도 없으면 base_mh 그대로 (side 없는 중립 조인트)

    namespace 포함 full name 반환.
    """
    under = "_" if use_underscore else ""

    def _apply(name, s):
        if not s:
            return name
        return (s + under + name) if before_name else (name + under + s)

    def _full(name):
        return (ns_b + ":" + name) if ns_b else name

    # ── _M : 중립 조인트 ──
    if as_side == "_M":
        if side_middle:
            cand = _apply(base_mh, side_middle)
            if cmds.objExists(_full(cand)):
                return _full(cand)
        return _full(base_mh)

    # ── _R : 오른쪽 ──
    if as_side == "_R":
        cand = _apply(base_mh, side_right) if side_right else base_mh
        if cmds.objExists(_full(cand)):
            return _full(cand)
        # fallback: base_mh 그대로 (side 없는 조인트)
        return _full(base_mh)

    # ── _L : 왼쪽 ──
    # Step 1: sideLeft 설정 기반
    if side_left:
        cand = _apply(base_mh, side_left)
        if cmds.objExists(_full(cand)):
            return _full(cand)

    # Step 2: 이름 내 side 패턴 자동 감지 → 치환 시도
    for r_pat, l_pat in _COMMON_SIDE_PAIRS:
        if r_pat in base_mh:
            resolved = base_mh.replace(r_pat, l_pat, 1)
            if cmds.objExists(_full(resolved)):
                return _full(resolved)

    # Step 3: side 없는 조인트 → base_mh 그대로
    return _full(base_mh)


# ──────────────────────────────────────────────────────────────
# AS 스크립트 경로 / FitSkeleton 파일 목록
# ──────────────────────────────────────────────────────────────

def _load_saved_as_path():
    """Maya optionVar 에서 저장된 AS 경로 반환."""
    if cmds.optionVar(exists=_AS_PATH_OPTVAR):
        return cmds.optionVar(q=_AS_PATH_OPTVAR)
    return ""


def _save_as_path(path):
    """AS 경로를 Maya optionVar 에 저장."""
    cmds.optionVar(sv=(_AS_PATH_OPTVAR, path))


def _fit_mode_update():
    """FitSkeleton 배치 후 DG / 뷰포트 강제 갱신 (AS asFitModeManualUpdate 대체)."""
    cmds.dgdirty(a=True)
    cmds.refresh()


# FitSkeleton limb 체인 (AS biped 단일 셋 기준 — L/R 없음, AS가 미러링)
_LIMB_CHAINS = [
    ("Shoulder", "Elbow", "Wrist"),
    ("Hip",      "Knee",  "Ankle"),
]

# 자연스러운 bend 방향 (월드 Z축 기준)
# Knee: 앞쪽(+Z), Elbow: 뒤쪽(-Z)
_NATURAL_PV_DIR = {
    "Knee":  (0.0, 0.0,  1.0),
    "Elbow": (0.0, 0.0, -1.0),
}

# show_pole_vectors 로케이터 접두사
_PV_LOC_PREFIX = "_FitPV_"


def _calc_pv_data(root_j, mid_j, end_j):
    """limb chain 의 perp 벡터와 PV 로케이터 위치 계산.

    반환: (perp_vec, pv_world_pos) 각각 om.MVector
    """
    import maya.api.OpenMaya as om

    def _v(j):
        p = cmds.xform(j, q=True, ws=True, t=True)
        return om.MVector(*p)

    a, b, c = _v(root_j), _v(mid_j), _v(end_j)
    ac   = c - a
    ab   = b - a
    proj = (ab * ac.normal()) * ac.normal()
    perp = ab - proj

    nat = _NATURAL_PV_DIR.get(mid_j)
    if perp.length() < 0.0001:
        # 일직선 → 자연 방향 fallback
        perp = om.MVector(*nat) if nat else (ac.normal() ^ om.MVector(0, 1, 0))

    pv_pos = b + perp.normal() * (ac.length() * 0.3)
    return perp, pv_pos, a, proj


def _resolve_files_root(path):
    """주어진 경로에서 nameMatchers / fitSkeletons 폴더가 있는 위치를 자동 탐색.

    탐색 순서:
      1. path 자체에 nameMatchers 또는 fitSkeletons 존재
      2. path/AdvancedSkeletonFiles 에 존재 (AS 기본 설치 구조)
    반환: 발견된 폴더 경로 (str) 또는 None
    """
    if not path:
        return None
    path = path.strip().rstrip("/\\")
    if not os.path.isdir(path):
        return None

    def _has_targets(p):
        return os.path.isdir(p + "/nameMatchers") or os.path.isdir(p + "/fitSkeletons")

    if _has_targets(path):
        return path

    sub = path + "/AdvancedSkeletonFiles"
    if _has_targets(sub):
        return sub

    return None


def _apply_as_path(path):
    """경로 적용 + optionVar 저장 + Template/FitSkeleton 메뉴 갱신."""
    path = path.strip().rstrip("/\\")
    _save_as_path(path)
    if _as_path_field and cmds.textField(_as_path_field, q=True, ex=True):
        cmds.textField(_as_path_field, e=True, tx=path)
    resolved = _resolve_files_root(path)
    if resolved:
        print("// AS Fit Tool: nameMatchers/fitSkeletons 발견 → " + resolved)
    else:
        cmds.warning("AS Fit Tool: 지정 경로에서 nameMatchers / fitSkeletons 폴더를 찾을 수 없습니다.")
    if _template_menu and cmds.optionMenu(_template_menu, q=True, ex=True):
        _refresh_template_menu(_template_menu)
    if _fit_file_menu and _fit_path_field:
        _refresh_fit_skeleton_menu(_fit_file_menu, _fit_path_field)


def _browse_as_path():
    """폴더 선택 다이얼로그 → 경로 적용."""
    result = cmds.fileDialog2(fm=3, ds=2, cap="AS 스크립트 폴더 선택")
    if result:
        _apply_as_path(result[0])


def _init_as_path():
    """UI 초기화 시 저장된 경로 복원, 없으면 MEL 자동 감지."""
    saved = _load_saved_as_path()
    if saved and os.path.isdir(saved):
        if _as_path_field and cmds.textField(_as_path_field, q=True, ex=True):
            cmds.textField(_as_path_field, e=True, tx=saved)
        return
    # MEL 자동 감지 시도
    try:
        exists = mel.eval('exists "asGetScriptLocation"')
        if exists:
            path = mel.eval("asGetScriptLocation()")
            if path:
                path = path.rstrip("/")
                if _as_path_field and cmds.textField(_as_path_field, q=True, ex=True):
                    cmds.textField(_as_path_field, e=True, tx=path)
                _save_as_path(path)
    except Exception:
        pass


def _get_as_script_location():
    """nameMatchers / fitSkeletons 가 있는 폴더 경로 반환.

    탐색 순서: UI 필드 → optionVar → MEL asGetScriptLocation
    각 경로는 _resolve_files_root() 를 통해 실제 폴더 위치로 확정.
    """
    # 1순위: UI 필드
    if _as_path_field and cmds.textField(_as_path_field, q=True, ex=True):
        ui_path = cmds.textField(_as_path_field, q=True, tx=True).strip()
        resolved = _resolve_files_root(ui_path)
        if resolved:
            return resolved
    # 2순위: optionVar (UI 없이 호출된 경우)
    saved = _load_saved_as_path()
    resolved = _resolve_files_root(saved)
    if resolved:
        return resolved
    # 3순위: MEL 프로시저
    try:
        exists = mel.eval('exists "asGetScriptLocation"')
        if not exists:
            return None
        path = mel.eval("asGetScriptLocation()")
        if path:
            resolved = _resolve_files_root(path.rstrip("/"))
            if resolved:
                return resolved
    except Exception:
        pass
    return None


def _get_fit_skeleton_files():
    root = _get_as_script_location()
    if not root:
        return []
    folder = root + "/fitSkeletons"
    if not os.path.isdir(folder):
        return []
    return sorted(f for f in os.listdir(folder) if f.endswith(".ma"))


def _get_namematcher_templates():
    root = _get_as_script_location()
    if not root:
        return []
    folder = root + "/nameMatchers"
    if not os.path.isdir(folder):
        return []
    return sorted(f[:-4] for f in os.listdir(folder) if f.endswith(".txt"))


# ──────────────────────────────────────────────────────────────
# Scale 계산
# ──────────────────────────────────────────────────────────────

def _resolve_mh_full(base, ns_b, ss):
    """
    side 설정을 적용해 실제 씬에 존재하는 MH 조인트 full name 반환.
    sideRight 적용 이름 우선, 없으면 base 그대로.
    존재하지 않으면 None 반환.
    """
    under = "_" if ss['use_underscore'] else ""

    def _build(s):
        if not s:
            return base
        return (s + under + base) if ss['before_name'] else (base + under + s)

    sided = _build(ss['side_right'])
    full_sided = (ns_b + ":" + sided) if ns_b else sided
    if cmds.objExists(full_sided) and cmds.objectType(full_sided) == "joint":
        return full_sided

    full_base = (ns_b + ":" + base) if ns_b else base
    if cmds.objExists(full_base) and cmds.objectType(full_base) == "joint":
        return full_base

    return None


def _calc_fit_scale(mapping_dict, ns_b):
    """
    MH 매핑 조인트 높이 범위 vs FitSkeleton scale=1 기준 높이로 스케일 계산.
    반환: (scale, mh_height, fit_height, axis_label)
    """
    ss     = _get_side_settings_from_ui()
    up_axis = cmds.upAxis(q=True, ax=True) or "y"
    ax_idx  = 2 if up_axis == "z" else 1
    ax_lbl  = "Z" if up_axis == "z" else "Y"

    # MH 조인트 높이 범위 (sideRight 적용 이름으로 검색)
    mh_vals = []
    for mh_base in mapping_dict.values():
        full = _resolve_mh_full(mh_base, ns_b, ss)
        if full:
            pos = cmds.xform(full, q=True, ws=True, t=True)
            mh_vals.append(pos[ax_idx])

    if not mh_vals:
        return 1.0, 0.0, 0.0, ax_lbl

    mh_height = max(mh_vals) - min(mh_vals)

    if not cmds.objExists("FitSkeleton"):
        return 1.0, mh_height, 0.0, ax_lbl

    # FitSkeleton 높이: scale=1 기준으로 측정 (현재 scale 임시 제거)
    cur_scale = cmds.getAttr("FitSkeleton.sx")
    if cur_scale and cur_scale != 0:
        fit_vals = []
        for j in (cmds.listRelatives("FitSkeleton", ad=True, type="joint") or []):
            pos = cmds.xform(j, q=True, ws=True, t=True)
            # scale=1 기준으로 환산
            fit_vals.append(pos[ax_idx] / cur_scale)
    else:
        fit_vals = []
        for j in (cmds.listRelatives("FitSkeleton", ad=True, type="joint") or []):
            pos = cmds.xform(j, q=True, ws=True, t=True)
            fit_vals.append(pos[ax_idx])

    if not fit_vals:
        return 1.0, mh_height, 0.0, ax_lbl

    fit_height = max(fit_vals) - min(fit_vals)
    if fit_height <= 0:
        return 1.0, mh_height, 0.0, ax_lbl

    return mh_height / fit_height, mh_height, fit_height, ax_lbl


# ──────────────────────────────────────────────────────────────
# Mapping Check 창
# ──────────────────────────────────────────────────────────────

CHECK_WINDOW = "asFitCheckWindow"


def check_mapping(ui_rows, ns_b_menu):
    mapping = _get_mapping_from_ui(ui_rows)
    ns_b    = _get_ns(ns_b_menu)
    ss      = _get_side_settings_from_ui()

    if not mapping:
        cmds.warning("매핑이 비어 있습니다.")
        return

    def _sided(base, side_str):
        under = "_" if ss['use_underscore'] else ""
        if not side_str:
            return base
        return (side_str + under + base) if ss['before_name'] else (base + under + side_str)

    def _resolve(base):
        """sideRight 적용 이름 우선, 없으면 base 그대로. (resolved_name, found) 반환."""
        sided = _sided(base, ss['side_right'])
        full_sided = (ns_b + ":" + sided) if ns_b else sided
        if cmds.objExists(full_sided):
            return full_sided, True
        full_base = (ns_b + ":" + base) if ns_b else base
        if cmds.objExists(full_base):
            return full_base, True
        # 둘 다 없으면 sided 이름으로 missing 표시
        return full_sided, False

    ok_lines, miss_lines = [], []
    for as_j, mh_base in mapping.items():
        resolved, found = _resolve(mh_base)
        line = "{:<22} ->  {}".format(as_j, resolved)
        (ok_lines if found else miss_lines).append(line)

    total   = len(ok_lines) + len(miss_lines)
    summary = "Found {}/{}  |  Missing {}".format(len(ok_lines), total, len(miss_lines))

    if cmds.window(CHECK_WINDOW, q=True, ex=True):
        cmds.deleteUI(CHECK_WINDOW)

    cmds.window(CHECK_WINDOW, t="Mapping Check", w=420, h=500, sizeable=True)
    cmds.columnLayout(adj=True, rowSpacing=4)
    cmds.separator(h=6, st="none")
    cmds.text(l=summary, fn="boldLabelFont", al="center")
    cmds.separator(h=4, st="in")

    if ok_lines:
        cmds.frameLayout(l="  OK  ({})".format(len(ok_lines)),
                         cll=True, cl=False, bv=True, bgc=(0.25, 0.38, 0.25))
        cmds.scrollField(editable=False, wordWrap=False, tx="\n".join(ok_lines),
                         h=min(200, 18 * len(ok_lines) + 10), fn="fixedWidthFont")
        cmds.setParent("..")

    if miss_lines:
        cmds.frameLayout(l="  MISSING  ({})".format(len(miss_lines)),
                         cll=True, cl=False, bv=True, bgc=(0.45, 0.25, 0.25))
        cmds.scrollField(editable=False, wordWrap=False, tx="\n".join(miss_lines),
                         h=min(160, 18 * len(miss_lines) + 10), fn="fixedWidthFont")
        cmds.setParent("..")

    cmds.separator(h=6, st="none")
    cmds.showWindow(CHECK_WINDOW)


# ──────────────────────────────────────────────────────────────
# Tool Logic
# ──────────────────────────────────────────────────────────────

def _get_mapping_from_ui(ui_rows):
    mapping = {}
    for as_f, mh_f in ui_rows:
        a = cmds.textField(as_f, q=True, tx=True).strip()
        b = cmds.textField(mh_f, q=True, tx=True).strip()
        if a and b:
            mapping[a] = b
    return mapping


def _get_side_settings_from_ui():
    """UI side 설정 위젯에서 현재 값 반환."""
    return {
        'side_right':   cmds.textField(_side_right_field,  q=True, tx=True).strip() if _side_right_field else "",
        'side_left':    cmds.textField(_side_left_field,   q=True, tx=True).strip() if _side_left_field else "",
        'side_middle':  cmds.textField(_side_middle_field, q=True, tx=True).strip() if _side_middle_field else "",
        'before_name':  cmds.checkBox(_side_before_name_cb, q=True, v=True) if _side_before_name_cb else False,
        'use_underscore': cmds.checkBox(_side_underscore_cb, q=True, v=True) if _side_underscore_cb else False,
    }


def create_place_fit_skeleton(ui_rows, ns_b_menu,
                              fit_file_menu=None, fit_path_field=None,
                              scale_field=None):
    mapping = _get_mapping_from_ui(ui_rows)
    ns_b    = _get_ns(ns_b_menu)

    if not mapping:
        cmds.warning("매핑이 비어 있습니다.")
        return

    if cmds.objExists("|FitSkeleton"):
        cmds.delete("|FitSkeleton")

    for j in cmds.ls(type="joint"):
        cmds.setAttr(j + ".segmentScaleCompensate", 0)

    # FitSkeleton 파일 경로 결정
    fit_file    = "biped.ma"
    import_path = ""
    if fit_file_menu and cmds.optionMenu(fit_file_menu, q=True, ex=True):
        sel = cmds.optionMenu(fit_file_menu, q=True, v=True)
        if sel and not sel.startswith("("):
            fit_file = sel

    # 1순위: FitSkeleton Path 필드에 경로가 있으면 그대로 사용
    if fit_path_field and cmds.textField(fit_path_field, q=True, ex=True):
        candidate = cmds.textField(fit_path_field, q=True, tx=True).strip()
        if candidate and os.path.exists(candidate):
            import_path = candidate

    # 2순위: AS Files Path 기반으로 경로 조합
    if not import_path:
        root = _get_as_script_location()
        if root:
            candidate = root + "/fitSkeletons/" + fit_file
            if os.path.exists(candidate):
                import_path = candidate

    if not import_path:
        cmds.warning("AS Fit Tool: FitSkeleton .ma 파일을 찾을 수 없습니다. "
                     "AS Files Path 를 설정하거나 FitSkeleton File 을 확인하세요.")
        return

    # .ma 파일 직접 임포트 (AS MEL 불필요)
    cmds.file(import_path, i=True, type="mayaAscii",
              ignoreVersion=True, mergeNamespacesOnClash=False,
              rpr="FitSkeleton", options="v=0;")

    if not cmds.objExists("FitSkeleton"):
        cmds.warning("FitSkeleton 임포트 실패: " + import_path)
        return

    # 스케일 계산
    manual = 0.0
    if scale_field and cmds.floatField(scale_field, q=True, ex=True):
        manual = cmds.floatField(scale_field, q=True, v=True)

    if manual > 0.0001:
        scale = manual
        print("// AS Fit Tool: 수동 스케일 = {:.4f}".format(scale))
    else:
        scale, mh_h, fit_h, ax = _calc_fit_scale(mapping, ns_b)
        print("// AS Fit Tool: 자동 스케일 = {:.4f}  "
              "(MH {} {:.3f} / FitSkeleton {} {:.3f})".format(scale, ax, mh_h, ax, fit_h))
        if scale_field and cmds.floatField(scale_field, q=True, ex=True):
            cmds.floatField(scale_field, e=True, v=scale)

    cmds.setAttr("FitSkeleton.sx", scale)
    cmds.setAttr("FitSkeleton.sy", scale)
    cmds.setAttr("FitSkeleton.sz", scale)

    # BFS 계층 순서로 배치 (부모 → 자식)
    ordered, queue = [], ["|FitSkeleton"]
    while queue:
        node = queue.pop(0)
        children = cmds.listRelatives(node, c=True, type="joint", fullPath=True) or []
        for ch in children:
            ordered.append((ch.rsplit("|", 1)[-1], ch))
        queue.extend(children)

    ss = _get_side_settings_from_ui()

    def _build_mh_name(base, is_middle):
        """Side Settings + middle 여부로 MH 조인트 full name 생성."""
        side_str = ss['side_middle'] if is_middle else ss['side_right']
        under    = "_" if ss['use_underscore'] else ""
        if not side_str:
            return base
        return (side_str + under + base) if ss['before_name'] else (base + under + side_str)

    placed = 0
    for short, long_path in ordered:
        if short not in mapping:
            continue

        base_mh = mapping[short]

        # FitJoint X 위치로 middle/sided 판정 (AS NameMatcher 동일 로직)
        fit_pos   = cmds.xform(long_path, q=True, ws=True, t=True)
        is_middle = abs(fit_pos[0]) <= 0.001

        # Side 적용한 이름으로 조인트 검색
        sided_name = _build_mh_name(base_mh, is_middle)
        mh_full    = (ns_b + ":" + sided_name) if ns_b else sided_name

        # 없으면 base name 그대로 시도 (side 없는 조인트 대응)
        if not cmds.objExists(mh_full):
            mh_full_base = (ns_b + ":" + base_mh) if ns_b else base_mh
            if cmds.objExists(mh_full_base):
                mh_full = mh_full_base
            else:
                cmds.warning("MH 조인트 없음: {} (tried: {})".format(mh_full_base, mh_full))
                continue

        pos = cmds.xform(mh_full, q=True, ws=True, t=True)
        cmds.xform(long_path, ws=True, t=pos)
        placed += 1

    _fit_mode_update()
    cmds.select("FitSkeleton")
    print("// AS Fit Tool: FitSkeleton 배치 완료 ({} 조인트)".format(placed))


def show_pole_vectors():
    """PV 방향 시각화 로케이터 생성 / 제거 토글.

    로케이터가 없으면 생성, 하나라도 있으면 전체 삭제.
    """
    if not cmds.objExists("FitSkeleton"):
        cmds.warning("AS Fit Tool: FitSkeleton 이 없습니다.")
        return

    jnt_map = {j.split("|")[-1]: j
               for j in (cmds.ls(
                   cmds.listRelatives("FitSkeleton", ad=True, type="joint") or [],
                   l=True) or [])}

    loc_names = [_PV_LOC_PREFIX + mid for _, mid, _ in _LIMB_CHAINS
                 if mid in jnt_map]

    # 하나라도 존재하면 전체 삭제
    existing = [n for n in loc_names if cmds.objExists(n)]
    if existing:
        cmds.delete(existing)
        print("// AS Fit Tool: PoleVector 헬퍼 제거 ({} 개)".format(len(existing)))
        return

    # 없으면 생성
    created = 0
    for root_j, mid_j, end_j in _LIMB_CHAINS:
        if not all(j in jnt_map for j in (root_j, mid_j, end_j)):
            continue

        _, pv_pos, _, _ = _calc_pv_data(
            jnt_map[root_j], jnt_map[mid_j], jnt_map[end_j])

        loc_name = _PV_LOC_PREFIX + mid_j
        if cmds.objExists(loc_name):
            cmds.delete(loc_name)

        loc = cmds.spaceLocator(n=loc_name)[0]
        cmds.xform(loc, ws=True, t=[pv_pos.x, pv_pos.y, pv_pos.z])
        # 로케이터 크기: 팔다리 굵기에 맞게
        scale = 3.0
        for ax in ("X", "Y", "Z"):
            cmds.setAttr("{}.localScale{}".format(loc, ax), scale)
        created += 1
        print("// AS Fit Tool: PV 헬퍼 생성 {} → ({:.2f}, {:.2f}, {:.2f})".format(
            loc_name, pv_pos.x, pv_pos.y, pv_pos.z))

    print("// AS Fit Tool: PoleVector 헬퍼 생성 완료 ({} 개)".format(created))


def straighten_pole_vectors():
    """Elbow / Knee 를 자연스러운 bend 축(Z)으로 재배치.

    현재 perp 거리를 유지하면서 방향을 월드 Z 축(Knee=+Z, Elbow=-Z)에 정렬.
    IK 빌드 전 bend 방향이 명확하지 않을 때 사용.
    """
    if not cmds.objExists("FitSkeleton"):
        cmds.warning("AS Fit Tool: FitSkeleton 이 없습니다.")
        return

    import maya.api.OpenMaya as om

    jnt_map = {j.split("|")[-1]: j
               for j in (cmds.ls(
                   cmds.listRelatives("FitSkeleton", ad=True, type="joint") or [],
                   l=True) or [])}

    moved = 0
    for root_j, mid_j, end_j in _LIMB_CHAINS:
        if not all(j in jnt_map for j in (root_j, mid_j, end_j)):
            continue
        if mid_j not in _NATURAL_PV_DIR:
            continue

        perp, _, a, proj = _calc_pv_data(
            jnt_map[root_j], jnt_map[mid_j], jnt_map[end_j])

        # ac(root→end) 방향 계산
        def _v(j):
            p = cmds.xform(j, q=True, ws=True, t=True)
            return om.MVector(*p)
        ac_norm  = (_v(jnt_map[end_j]) - _v(jnt_map[root_j])).normal()

        # 자연 방향(Z축)을 ac 수직 평면에 투영 → idempotent 보장
        # (nat_dir에 ac 성분이 섞이면 호출마다 proj가 커져 팔 길이가 줄어드는 버그 발생)
        nat_dir  = om.MVector(*_NATURAL_PV_DIR[mid_j])
        nat_perp = nat_dir - (nat_dir * ac_norm) * ac_norm
        if nat_perp.length() < 0.0001:
            nat_perp = perp  # ac와 nat_dir이 평행한 극단적 경우 → 현재 방향 유지
        nat_perp_norm = nat_perp.normal()

        new_perp = nat_perp_norm * perp.length()
        new_pos  = a + proj + new_perp

        # end joint(Ankle/Wrist) 월드 포지션 저장 — mid 이동 시 계층 상속으로 함께 이동하므로 복원 필요
        end_ws = cmds.xform(jnt_map[end_j], q=True, ws=True, t=True)

        cmds.xform(jnt_map[mid_j], ws=True, t=[new_pos.x, new_pos.y, new_pos.z])

        # end joint 월드 포지션 복원 (하위 조인트는 로컬 유지되므로 자동 보정)
        cmds.xform(jnt_map[end_j], ws=True, t=end_ws)

        moved += 1
        print("// AS Fit Tool: {} 재배치 → ({:.3f}, {:.3f}, {:.3f})".format(
            mid_j, new_pos.x, new_pos.y, new_pos.z))

        # PV 헬퍼 로케이터가 있으면 함께 갱신
        loc_name = _PV_LOC_PREFIX + mid_j
        if cmds.objExists(loc_name):
            _, pv_pos, _, _ = _calc_pv_data(
                jnt_map[root_j], jnt_map[mid_j], jnt_map[end_j])
            cmds.xform(loc_name, ws=True, t=[pv_pos.x, pv_pos.y, pv_pos.z])

    if moved:
        _fit_mode_update()
    print("// AS Fit Tool: PoleVector 정렬 완료 ({} 개)".format(moved))


# ──────────────────────────────────────────────────────────────
# Namespace 자동 감지
# ──────────────────────────────────────────────────────────────

_NONE_LABEL = "(없음)"
_AS_HINTS   = {"DeformationSystem", "FitSkeleton", "AdvancedSkeleton"}
_MH_HINTS   = {"pelvis", "spine_01", "thigh_r", "thigh_l"}


def _scene_namespaces():
    try:
        all_ns = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
    except Exception:
        all_ns = []
    return [ns for ns in all_ns if ns not in ("UI", "shared", ":")]


def _guess_ns(namespaces, hints):
    for ns in namespaces:
        for hint in hints:
            if cmds.objExists(ns + ":" + hint):
                return ns
    return None


def _refresh_ns_menus(ns_a_menu, ns_b_menu):
    namespaces = _scene_namespaces()
    for menu in (ns_a_menu, ns_b_menu):
        for item in (cmds.optionMenu(menu, q=True, ill=True) or []):
            cmds.deleteUI(item)
        cmds.menuItem(l=_NONE_LABEL, p=menu)
        for ns in namespaces:
            cmds.menuItem(l=ns, p=menu)

    as_g = _guess_ns(namespaces, _AS_HINTS)
    mh_g = _guess_ns(namespaces, _MH_HINTS)

    def _set(menu, val):
        if val is None: return
        labels = [cmds.menuItem(i, q=True, l=True)
                  for i in (cmds.optionMenu(menu, q=True, ill=True) or [])]
        if val in labels:
            cmds.optionMenu(menu, e=True, v=val)

    _set(ns_a_menu, as_g)
    _set(ns_b_menu, mh_g)
    detected = []
    if as_g: detected.append("AS=" + as_g)
    if mh_g: detected.append("MH=" + mh_g)
    print("// AS Fit Tool: NS 감지 - " + (", ".join(detected) if detected else "없음"))


def _get_ns(menu):
    val = cmds.optionMenu(menu, q=True, v=True)
    return "" if val == _NONE_LABEL else val


# ──────────────────────────────────────────────────────────────
# FitSkeleton 파일 메뉴
# ──────────────────────────────────────────────────────────────

def _refresh_template_menu(menu):
    """nameMatchers 폴더를 다시 스캔해 Template 드롭다운 갱신. meta 항목을 기본 선택."""
    for item in (cmds.optionMenu(menu, q=True, ill=True) or []):
        cmds.deleteUI(item)
    cmds.menuItem(l="(선택)", p=menu)
    templates = _get_namematcher_templates()
    for tmpl in templates:
        cmds.menuItem(l=tmpl, p=menu)
    # "meta" 포함 항목 자동 선택, 없으면 "(선택)" 유지
    meta_tmpl = next((t for t in templates if t.lower() == "meta"), None)
    if meta_tmpl:
        try:
            cmds.optionMenu(menu, e=True, v=meta_tmpl)
        except Exception:
            pass
    print("// AS Fit Tool: Template 목록 갱신 ({} 개)".format(len(templates)))


_FIT_NONE_LABEL = "None"

def _refresh_fit_skeleton_menu(menu, path_field):
    """fitSkeletons 폴더를 다시 스캔해 File 드롭다운 갱신. meta 파일을 기본 선택, 없으면 None."""
    files = _get_fit_skeleton_files()
    for item in (cmds.optionMenu(menu, q=True, ill=True) or []):
        cmds.deleteUI(item)
    cmds.menuItem(l=_FIT_NONE_LABEL, p=menu)
    for f in files:
        cmds.menuItem(l=f, p=menu)
    # "meta" 포함 파일 자동 선택, 없으면 "None"
    meta_file = next((f for f in files if os.path.splitext(f)[0].lower() == "meta"), None)
    try:
        cmds.optionMenu(menu, e=True, v=meta_file if meta_file else _FIT_NONE_LABEL)
    except Exception:
        pass
    _update_fit_skeleton_path(menu, path_field)


def _update_fit_skeleton_path(menu, path_field):
    root = _get_as_script_location()
    sel  = cmds.optionMenu(menu, q=True, v=True) or ""
    if root and sel and not sel.startswith("(") and sel != _FIT_NONE_LABEL:
        cmds.textField(path_field, e=True,
                       tx=root + "/fitSkeletons/" + sel)
    else:
        cmds.textField(path_field, e=True, tx="")


# ──────────────────────────────────────────────────────────────
# Scale Preview
# ──────────────────────────────────────────────────────────────

def _preview_scale():
    mapping = _get_mapping_from_ui(_ui_rows)
    ns_b    = _get_ns(_ns_b_menu)
    ss      = _get_side_settings_from_ui()
    if not mapping:
        cmds.warning("매핑이 비어 있습니다.")
        return

    up_axis = cmds.upAxis(q=True, ax=True) or "y"
    ax_idx  = 2 if up_axis == "z" else 1
    ax_lbl  = "Z" if up_axis == "z" else "Y"

    # sideRight 적용 이름으로 MH 조인트 높이 수집
    mh_vals = []
    for mh_base in mapping.values():
        full = _resolve_mh_full(mh_base, ns_b, ss)
        if full:
            mh_vals.append(cmds.xform(full, q=True, ws=True, t=True)[ax_idx])

    if not mh_vals:
        cmds.warning("MH 조인트를 찾을 수 없습니다. Side 설정을 확인하세요.")
        return

    mh_height = max(mh_vals) - min(mh_vals)

    if cmds.objExists("FitSkeleton"):
        scale, _, fit_h, _ = _calc_fit_scale(mapping, ns_b)
        ref = "FitSkeleton scale=1 기준 {:.3f}".format(fit_h)
    else:
        fit_h = 17.0
        scale = mh_height / fit_h
        ref   = "biped 기준값 {:.3f} (FitSkeleton 미로드)".format(fit_h)

    cmds.floatField(_scale_field, e=True, v=scale)
    print("// AS Fit Tool: Scale Preview = {:.4f}  "
          "(MH {} {:.3f} / {})".format(scale, ax_lbl, mh_height, ref))


# ──────────────────────────────────────────────────────────────
# Template 로드
# ──────────────────────────────────────────────────────────────

def _load_template(template_name, map_col):
    """nameMatchers .txt 파일을 읽어 UI 갱신."""
    root = _get_as_script_location()
    if not root:
        cmds.warning("AS 스크립트 경로를 찾을 수 없습니다.")
        return

    txt_path = root + "/nameMatchers/" + template_name + ".txt"
    data = _normalize_template_data(_parse_namematcher_txt(txt_path))

    # Side Settings 갱신
    if _side_right_field:
        cmds.textField(_side_right_field,  e=True, tx=data['sideRight'])
    if _side_left_field:
        cmds.textField(_side_left_field,   e=True, tx=data['sideLeft'])
    if _side_middle_field:
        cmds.textField(_side_middle_field, e=True, tx=data['sideMiddle'])
    if _side_before_name_cb:
        cmds.checkBox(_side_before_name_cb, e=True, v=data['sideBeforeName'])
    if _side_underscore_cb:
        cmds.checkBox(_side_underscore_cb,  e=True, v=data['sideUnderScore'])

    # 매핑 테이블 재구성
    for as_f, mh_f in list(_ui_rows):
        row = cmds.textField(as_f, q=True, p=True)
        _remove_row(row, (as_f, mh_f))
    _ui_rows.clear()

    for as_val, mh_val in data['mapping']:
        pair = _build_mapping_row(map_col, as_val, mh_val)
        _ui_rows.append(pair)

    # 대응 .ma 파일이 nameMatchers 폴더에 있으면 FitSkeleton 경로 설정
    ma_path = root + "/nameMatchers/" + template_name + ".ma"
    if os.path.isfile(ma_path) and _fit_path_field:
        cmds.textField(_fit_path_field, e=True, tx=ma_path)
        print("// AS Fit Tool: FitSkeleton 경로 자동 설정 → " + ma_path)
    elif _fit_file_menu and _fit_path_field:
        _update_fit_skeleton_path(_fit_file_menu, _fit_path_field)

    print("// AS Fit Tool: 템플릿 로드 완료 - " + template_name +
          "  ({} 조인트)".format(len(data['mapping'])))


# ──────────────────────────────────────────────────────────────
# UI 헬퍼
# ──────────────────────────────────────────────────────────────

WINDOW_NAME     = "asFitToolWindow"
_ui_rows        = []
_ns_a_menu      = None
_ns_b_menu      = None
_fit_file_menu  = None
_fit_path_field = None
_scale_field    = None
_side_right_field    = None
_side_left_field     = None
_side_middle_field   = None
_side_before_name_cb = None
_side_underscore_cb  = None
_template_menu  = None
_map_col_ref    = None   # 매핑 테이블 columnLayout 참조 (템플릿 로드 시 필요)
_as_path_field  = None   # AS 스크립트 경로 텍스트 필드


def _build_mapping_row(parent, as_val, mh_val):
    row = cmds.rowLayout(parent=parent, nc=3, cw3=(130, 130, 20),
                         cal=[(1,"left"),(2,"left"),(3,"center")], adj=2)
    as_field = cmds.textField(w=130, tx=as_val)
    mh_field = cmds.textField(w=130, tx=mh_val)
    cmds.button(l="x", w=20, h=20,
                c=lambda *_: _remove_row(row, (as_field, mh_field)))
    cmds.setParent(parent)
    return as_field, mh_field


def _remove_row(row_layout, row_pair):
    if cmds.layout(row_layout, q=True, ex=True):
        cmds.deleteUI(row_layout)
    if row_pair in _ui_rows:
        _ui_rows.remove(row_pair)


# ──────────────────────────────────────────────────────────────
# Main UI
# ──────────────────────────────────────────────────────────────

def _save_mapping():
    """
    현재 Joint Mapping UI 내용을 nameMatchers .txt 형식으로 저장.
    Side Settings 도 함께 저장됩니다.
    """
    root = _get_as_script_location()
    start_dir = os.path.join(root, "nameMatchers") if root else ""

    result = cmds.fileDialog2(
        fm=0, ds=2,
        cap="Joint Mapping 저장",
        okc="저장",
        startingDirectory=start_dir,
        ff="NameMatcher (*.txt)(*.txt)",
    )
    if not result:
        return

    save_path = result[0]
    if not save_path.endswith(".txt"):
        save_path += ".txt"

    # Side Settings 읽기
    sr  = cmds.textField(_side_right_field,  q=True, tx=True) if _side_right_field  else ""
    sl  = cmds.textField(_side_left_field,   q=True, tx=True) if _side_left_field   else ""
    sm  = cmds.textField(_side_middle_field, q=True, tx=True) if _side_middle_field else ""
    sbn = cmds.checkBox(_side_before_name_cb, q=True, v=True) if _side_before_name_cb else False
    su  = cmds.checkBox(_side_underscore_cb,  q=True, v=True) if _side_underscore_cb  else False

    lines = [
        "sideRight="      + sr,
        "sideLeft="       + sl,
        "sideMiddle="     + sm,
        "sideBeforeName=" + ("1" if sbn else "0"),
        "sideUnderScore=" + ("1" if su  else "0"),
    ]

    for as_f, mh_f in _ui_rows:
        try:
            as_val = cmds.textField(as_f, q=True, tx=True) if cmds.textField(as_f, q=True, ex=True) else ""
            mh_val = cmds.textField(mh_f, q=True, tx=True) if cmds.textField(mh_f, q=True, ex=True) else ""
        except Exception:
            continue
        if as_val or mh_val:
            lines.append(as_val + "=" + mh_val)

    try:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print("// AS Fit Tool: Joint Mapping 저장 완료 → " + save_path)
        # 저장 후 Template 목록 갱신
        if _template_menu and cmds.optionMenu(_template_menu, q=True, ex=True):
            _refresh_template_menu(_template_menu)
    except Exception as e:
        cmds.warning("AS Fit Tool: 저장 실패 – " + str(e))


def _open_advanced_skeleton_tool():
    """
    AS Files Path 기준으로 AdvancedSkeleton.mel 을 소싱한 뒤 툴을 실행합니다.

    _get_as_script_location() 은 nameMatchers/fitSkeletons 가 있는 폴더
    (= AdvancedSkeletonFiles) 를 반환하므로 그 상위 디렉터리에서
    AdvancedSkeleton.mel 을 탐색합니다.
    """
    root = _get_as_script_location()
    if root:
        parent = os.path.dirname(root)
        mel_path = os.path.join(parent, "AdvancedSkeleton.mel")
        if os.path.isfile(mel_path):
            mel.eval('source "{}"'.format(mel_path.replace("\\", "/")))
            print("// AS Fit Tool: sourced → " + mel_path)
        else:
            cmds.warning(
                "AS Fit Tool: AdvancedSkeleton.mel 을 찾을 수 없습니다 – " + parent
            )
    else:
        cmds.warning(
            "AS Fit Tool: AS Files Path 가 설정되지 않았습니다. "
            "경로를 먼저 지정하세요."
        )
    try:
        mel.eval("AdvancedSkeleton")
    except Exception as e:
        cmds.warning("AS Fit Tool: AdvancedSkeleton 실행 실패 – " + str(e))


def _open_namematchers_folder():
    """nameMatchers 폴더를 OS 파일 탐색기에서 엽니다."""
    root = _get_as_script_location()
    if not root:
        cmds.warning("AS Fit Tool: AS Files Path 가 설정되지 않았습니다.")
        return
    folder = os.path.join(root, "nameMatchers")
    if not os.path.isdir(folder):
        cmds.warning("AS Fit Tool: nameMatchers 폴더를 찾을 수 없습니다 – " + folder)
        return
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", folder.replace("/", "\\")])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
    except Exception as e:
        cmds.warning("AS Fit Tool: 폴더 열기 실패 – " + str(e))


def _show_help(title, msg):
    """도움말 팝업."""
    cmds.confirmDialog(title="Help  –  " + title, message=msg,
                       button=["확인"], defaultButton="확인")


def build_tab_ui(parent):
    """parent 레이아웃 내에 UI 구성. tab hub 및 standalone window 공용."""
    global _ui_rows, _ns_a_menu, _ns_b_menu
    global _fit_file_menu, _fit_path_field, _scale_field
    global _side_right_field, _side_left_field, _side_middle_field
    global _side_before_name_cb, _side_underscore_cb
    global _template_menu, _map_col_ref, _as_path_field
    _ui_rows = []

    scroll = cmds.scrollLayout(childResizable=True, parent=parent)
    main_col = cmds.columnLayout(adj=True, rowSpacing=4)

    # ── AS Script Path ─────────────────────────────────────────
    cmds.frameLayout(l="AS Files Path  (nameMatchers / fitSkeletons)", cll=False, cl=False, bv=True, p=main_col)
    ap_col = cmds.columnLayout(adj=True, rowSpacing=4)

    cmds.rowLayout(nc=4, cw4=(50, 196, 58, 22), adj=2, p=ap_col)
    cmds.text(l="Path :", al="right", w=50)
    _as_path_field = cmds.textField(
        w=196, ed=True,
        pht="nameMatchers / fitSkeletons 가 있는 폴더 지정",
        cc=lambda val: _apply_as_path(val))
    cmds.button(l="Browse", w=56, h=22, c=lambda *_: _browse_as_path())
    cmds.button(l="?", w=22, h=22, bgc=(0.25, 0.25, 0.35),
                c=lambda *_: _show_help("Browse",
                    "AdvancedSkeleton 파일 경로를 설정합니다.\n"
                    "nameMatchers / fitSkeletons 폴더가 있는\n"
                    "루트 폴더를 선택하세요."))
    cmds.setParent(ap_col)

    cmds.separator(h=2, st="none", p=ap_col)
    cmds.setParent("..")   # ap_col
    cmds.setParent("..")   # frameLayout

    # 저장된 경로 복원
    _init_as_path()

    # ── Template ───────────────────────────────────────────────
    cmds.frameLayout(l="Template  (nameMatchers)", cll=False, cl=False, bv=True, p=main_col)
    t_col = cmds.columnLayout(adj=True, rowSpacing=4)

    cmds.rowLayout(nc=5, cw5=(60, 148, 52, 52, 22), adj=2, p=t_col)
    cmds.text(l="Template :", al="right", w=60)
    _template_menu = cmds.optionMenu(w=148, bgc=(0.28, 0.22, 0.1))
    cmds.menuItem(l="(선택)")
    _init_templates = _get_namematcher_templates()
    for tmpl in _init_templates:
        cmds.menuItem(l=tmpl)
    _meta_tmpl = next((t for t in _init_templates if t.lower() == "meta"), None)
    if _meta_tmpl:
        try:
            cmds.optionMenu(_template_menu, e=True, v=_meta_tmpl)
        except Exception:
            pass
    cmds.button(l="Refresh", w=50, h=22,
                c=lambda *_: _refresh_template_menu(_template_menu))
    cmds.button(l="Load", w=50, h=22, bgc=(0.65, 0.45, 0.1),
                c=lambda *_: _load_template(
                    cmds.optionMenu(_template_menu, q=True, v=True), _map_col_ref))
    cmds.button(l="?", w=22, h=22, bgc=(0.25, 0.25, 0.35),
                c=lambda *_: _show_help("Template",
                    "nameMatchers 폴더의 템플릿(.txt)을 선택합니다.\n\n"
                    "Refresh : 폴더를 다시 스캔하여 목록 갱신\n"
                    "Load    : 선택한 템플릿을 불러와 Joint Mapping 테이블을 자동으로 채웁니다.\n"
                    "          같은 이름의 .ma 파일이 있으면 FitSkeleton 경로도 자동 설정됩니다."))
    cmds.setParent(t_col)

    cmds.separator(h=2, st="none", p=t_col)
    cmds.setParent("..")   # t_col
    cmds.setParent("..")   # frameLayout

    # ── Side Settings ──────────────────────────────────────────
    cmds.frameLayout(l="Side Settings", cll=True, cl=False, bv=True, p=main_col)
    s_col = cmds.columnLayout(adj=True, rowSpacing=3)

    def _side_row(label, default):
        cmds.rowLayout(nc=2, cw2=(90, 220), adj=2, p=s_col)
        cmds.text(l=label, al="right", w=90)
        fld = cmds.textField(w=220, tx=default)
        cmds.setParent(s_col)
        return fld

    _side_right_field  = _side_row("Right :",  DEFAULT_SIDE['sideRight'])
    _side_left_field   = _side_row("Left :",   DEFAULT_SIDE['sideLeft'])
    _side_middle_field = _side_row("Middle :", DEFAULT_SIDE['sideMiddle'])

    cmds.rowLayout(nc=3, cw3=(90, 130, 100), p=s_col)
    cmds.text(l="", w=90)
    _side_before_name_cb = cmds.checkBox(l="Before Name",   v=DEFAULT_SIDE['sideBeforeName'])
    _side_underscore_cb  = cmds.checkBox(l="Underscore (_)", v=DEFAULT_SIDE['sideUnderScore'])
    cmds.setParent(s_col)

    cmds.separator(h=2, st="none", p=s_col)
    cmds.setParent("..")   # s_col
    cmds.setParent("..")   # frameLayout

    # ── Namespace ──────────────────────────────────────────────
    cmds.frameLayout(l="Namespace", cll=False, cl=False, bv=True, p=main_col)
    ns_col = cmds.columnLayout(adj=True, rowSpacing=4)

    cmds.rowLayout(nc=4, cw4=(80, 148, 60, 22), adj=2, p=ns_col)
    cmds.text(l="AS :", al="right", w=80)
    _ns_a_menu = cmds.optionMenu(w=148)
    cmds.menuItem(l=_NONE_LABEL)
    cmds.button(l="Detect", w=58, h=22,
                c=lambda *_: _refresh_ns_menus(_ns_a_menu, _ns_b_menu))
    cmds.button(l="?", w=22, h=22, bgc=(0.25, 0.25, 0.35),
                c=lambda *_: _show_help("Namespace",
                    "씬에 존재하는 네임스페이스를 스캔하여\n"
                    "AS / MH 드롭다운을 자동으로 채웁니다.\n\n"
                    "AS  : AdvancedSkeleton 네임스페이스\n"
                    "MH  : MetaHuman 네임스페이스"))
    cmds.setParent(ns_col)

    cmds.rowLayout(nc=4, cw4=(80, 148, 60, 22), adj=2, p=ns_col)
    cmds.text(l="MH :", al="right", w=80)
    _ns_b_menu = cmds.optionMenu(w=148)
    cmds.menuItem(l=_NONE_LABEL)
    cmds.button(l="Detect", w=58, h=22,
                c=lambda *_: _refresh_ns_menus(_ns_a_menu, _ns_b_menu))
    cmds.button(l="?", w=22, h=22, bgc=(0.25, 0.25, 0.35),
                c=lambda *_: _show_help("Namespace",
                    "씬에 존재하는 네임스페이스를 스캔하여\n"
                    "AS / MH 드롭다운을 자동으로 채웁니다.\n\n"
                    "AS  : AdvancedSkeleton 네임스페이스\n"
                    "MH  : MetaHuman 네임스페이스"))
    cmds.setParent(ns_col)

    cmds.separator(h=2, st="none", p=ns_col)
    cmds.setParent("..")
    cmds.setParent("..")

    _refresh_ns_menus(_ns_a_menu, _ns_b_menu)

    # ── FitSkeleton File ───────────────────────────────────────
    cmds.frameLayout(l="FitSkeleton File", cll=False, cl=False, bv=True, p=main_col)
    fs_col = cmds.columnLayout(adj=True, rowSpacing=4)

    cmds.rowLayout(nc=4, cw4=(60, 168, 58, 22), adj=2, p=fs_col)
    cmds.text(l="File :", al="right", w=60)
    _fit_file_menu = cmds.optionMenu(
        w=168, bgc=(0.12, 0.22, 0.3),
        cc=lambda _: _update_fit_skeleton_path(_fit_file_menu, _fit_path_field))
    cmds.menuItem(l="(로딩 중...)")
    cmds.button(l="Refresh", w=56, h=22,
                c=lambda *_: _refresh_fit_skeleton_menu(_fit_file_menu, _fit_path_field))
    cmds.button(l="?", w=22, h=22, bgc=(0.25, 0.25, 0.35),
                c=lambda *_: _show_help("FitSkeleton File",
                    "fitSkeletons 폴더에서 FitSkeleton .ma 파일을 선택합니다.\n\n"
                    "Refresh : 폴더를 다시 스캔하여 목록 갱신\n"
                    "None    : 파일 미지정 (AS Files Path의 기본 파일 사용)\n\n"
                    "Scale = 0 으로 설정 시 MH 조인트 높이 기준으로 자동 계산합니다."))
    cmds.setParent(fs_col)

    cmds.rowLayout(nc=2, cw2=(60, 255), adj=2, p=fs_col)
    cmds.text(l="Path :", al="right", w=60)
    _fit_path_field = cmds.textField(w=255, ed=False, bgc=(0.2, 0.2, 0.2))
    cmds.setParent(fs_col)

    cmds.separator(h=4, st="in", p=fs_col)
    cmds.rowLayout(nc=6, cw6=(60, 80, 60, 78, 48, 22), adj=4, p=fs_col)
    cmds.text(l="Scale :", al="right", w=60)
    _scale_field = cmds.floatField(w=80, v=0.0, pre=4, min=0.0, max=999.0,
                                   ann="0.0 = 자동계산")
    cmds.text(l="(0=auto)", al="left", w=60)
    cmds.button(l="Preview", w=78, h=20,
                c=lambda *_: _preview_scale())
    cmds.button(l="Reset", w=48, h=20,
                c=lambda *_: cmds.floatField(_scale_field, e=True, v=0.0))
    cmds.button(l="?", w=22, h=20, bgc=(0.25, 0.25, 0.35),
                c=lambda *_: _show_help("Scale",
                    "FitSkeleton 임포트 시 적용할 스케일 값입니다.\n\n"
                    "0 (auto) : MH 조인트 높이와 FitSkeleton 높이를\n"
                    "           비교하여 스케일을 자동 계산합니다.\n"
                    "Preview  : 현재 씬 기준 권장 스케일 값을 미리 계산합니다.\n"
                    "Reset    : 스케일 값을 0(자동)으로 초기화합니다."))
    cmds.setParent(fs_col)

    cmds.separator(h=2, st="none", p=fs_col)
    cmds.setParent("..")
    cmds.setParent("..")

    _refresh_fit_skeleton_menu(_fit_file_menu, _fit_path_field)

    # ── Joint Mapping ──────────────────────────────────────────
    cmds.frameLayout(l="Joint Mapping  (AS FitJoint  |  MH Joint)",
                     cll=True, cl=False, bv=True, p=main_col)
    _map_col_ref = cmds.columnLayout(adj=True, rowSpacing=1)

    cmds.rowLayout(nc=3, cw3=(130, 130, 20))
    cmds.text(l="  AS FitJoint", al="left", fn="boldLabelFont", w=130)
    cmds.text(l="  MH Joint",    al="left", fn="boldLabelFont", w=130)
    cmds.text(l="", w=20)
    cmds.setParent(_map_col_ref)

    for as_val, mh_val in DEFAULT_MAPPING:
        _ui_rows.append(_build_mapping_row(_map_col_ref, as_val, mh_val))

    cmds.separator(h=4, st="in", p=_map_col_ref)
    cmds.rowLayout(nc=4, adj=1, p=_map_col_ref)
    cmds.button(l="+ 행 추가", h=22,
                c=lambda *_: _ui_rows.append(_build_mapping_row(_map_col_ref, "", "")))
    cmds.button(l="Save", w=72, h=22, bgc=(0.25, 0.4, 0.25),
                c=lambda *_: _save_mapping())
    cmds.button(l="Open Folder", w=88, h=22, bgc=(0.28, 0.28, 0.38),
                c=lambda *_: _open_namematchers_folder())
    cmds.button(l="?", w=22, h=22, bgc=(0.25, 0.25, 0.35),
                c=lambda *_: _show_help("Joint Mapping",
                    "AS FitJoint 이름과 대응되는 MH 조인트 이름을 매핑합니다.\n"
                    "Side(L/R) 조인트는 base 이름만 입력하세요.\n"
                    "Side 설정은 상단 Side Settings 섹션에서 지정합니다.\n\n"
                    "+ 행 추가   : 빈 매핑 행을 추가합니다.\n\n"
                    "Save        : 현재 매핑 + Side Settings 를\n"
                    "              nameMatchers .txt 형식으로 저장합니다.\n"
                    "              저장 후 Template 목록이 자동 갱신됩니다.\n\n"
                    "Open Folder : nameMatchers 폴더를 탐색기에서 엽니다.\n"
                    "              .txt 파일을 직접 편집할 수 있습니다."))
    cmds.setParent(_map_col_ref)
    cmds.setParent("..")   # frameLayout

    # ── Functions ──────────────────────────────────────────────
    cmds.frameLayout(l="Functions", cll=False, cl=False, bv=True, p=main_col)
    cmds.columnLayout(adj=True, rowSpacing=6)
    cmds.separator(h=4, st="none")

    cmds.rowLayout(nc=3, cw3=(198, 100, 22), adj=1)
    cmds.button(l="Create + Place FitSkeleton", h=30, bgc=(0.3, 0.55, 0.3),
                c=lambda *_: create_place_fit_skeleton(
                    _ui_rows, _ns_b_menu, _fit_file_menu, _fit_path_field, _scale_field))
    cmds.button(l="Check Mapping", h=30, bgc=(0.45, 0.45, 0.2),
                c=lambda *_: check_mapping(_ui_rows, _ns_b_menu))
    cmds.button(l="?", w=22, h=30, bgc=(0.25, 0.25, 0.35),
                c=lambda *_: _show_help("Create + Place FitSkeleton / Check Mapping",
                    "Create + Place FitSkeleton :\n"
                    "  FitSkeleton을 임포트하고 MH 조인트 위치에 맞춰 자동 배치합니다.\n"
                    "  스케일=0이면 MH 높이 기준으로 자동 계산합니다.\n\n"
                    "Check Mapping :\n"
                    "  Joint Mapping 테이블에 입력된 MH 조인트의\n"
                    "  존재 여부를 씬에서 확인합니다."))
    cmds.setParent("..")

    cmds.rowLayout(nc=3, cw3=(138, 160, 22), adj=1)
    cmds.button(l="Show PoleVectors",      h=26, c=lambda *_: show_pole_vectors())
    cmds.button(l="Straighten PoleVectors",h=26, c=lambda *_: straighten_pole_vectors())
    cmds.button(l="?", w=22, h=26, bgc=(0.25, 0.25, 0.35),
                c=lambda *_: _show_help("PoleVectors",
                    "Show PoleVectors :\n"
                    "  FitSkeleton의 PoleVector 핸들을 보이게 합니다.\n\n"
                    "Straighten PoleVectors :\n"
                    "  FitSkeleton의 PoleVector를 기본(정렬된) 위치로 초기화합니다."))
    cmds.setParent("..")

    cmds.separator(h=4, st="in")
    cmds.rowLayout(nc=2, cw2=(300, 22), adj=1)
    cmds.button(l="Open AdvancedSkeleton Tool", h=26, bgc=(0.45, 0.3, 0.45),
                c=lambda *_: _open_advanced_skeleton_tool())
    cmds.button(l="?", w=22, h=26, bgc=(0.25, 0.25, 0.35),
                c=lambda *_: _show_help("Open AdvancedSkeleton Tool",
                    "AdvancedSkeleton 메인 툴을 엽니다.\n\n"
                    "AS Files Path 에 등록된 경로의 상위 폴더에서\n"
                    "AdvancedSkeleton.mel 을 자동으로 찾아 소싱한 뒤 실행합니다.\n\n"
                    "경로 구조 예시 :\n"
                    "  AdvancedSkeleton5/\n"
                    "  ├── AdvancedSkeleton.mel  ← 여기서 실행\n"
                    "  └── AdvancedSkeletonFiles/\n"
                    "      ├── nameMatchers/\n"
                    "      └── fitSkeletons/\n\n"
                    "AS Files Path 가 설정되지 않은 경우 실행이 제한됩니다."))
    cmds.setParent("..")
    cmds.separator(h=6, st="none")
    cmds.setParent("..")
    cmds.setParent("..")

    return scroll


def show():
    if cmds.window(WINDOW_NAME, q=True, ex=True):
        cmds.deleteUI(WINDOW_NAME)
    win = cmds.window(WINDOW_NAME, t="AS Fit Tool", w=340, sizeable=True, mxb=False)
    build_tab_ui(win)
    cmds.showWindow(win)
