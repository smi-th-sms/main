"""
Rig Controller Batch Creator
프리셋 기반으로 캐릭터 리깅용 컨트롤러를 일괄 처리.

Action 별 동작:
  Create     : 새 컨트롤러 생성 (name / parent / preset 전체 적용)
  Add Attrs  : 기존 컨트롤러에 preset 의 attrs 추가 (name = 대상 노드명)
  Swap Shape : 기존 컨트롤러의 shape 교체 (name = 대상 노드명, preset shape 사용)

- Sided 체크 시 L/R 양쪽 자동 처리 (name / parent 의 side 토큰 자동 교체)
- 배치 설정은 rig_ctrl_batch_config.json 으로 저장/로드

사용:
    import importlib
    import rig_ctrl_batch_tool
    importlib.reload(rig_ctrl_batch_tool)
    rig_ctrl_batch_tool.show()
"""

import os, json
import maya.cmds as cmds

_TOOL_DIR     = os.path.dirname(os.path.abspath(__file__))
_BATCH_FILE   = os.path.join(_TOOL_DIR, "rig_ctrl_batch_config.json")
_PRESETS_FILE = os.path.join(_TOOL_DIR, "ctrl_creator_presets.json")

_ACTIONS = ["Create", "Add Attrs", "Swap Shape"]

# side 치환 쌍 (긴 토큰 우선)
_SIDE_PAIRS = [
    ("Left", "Right"), ("left", "right"),
    ("_L_",  "_R_"),   ("_l_",  "_r_"),
    ("_L",   "_R"),    ("_l",   "_r"),
    ("L_",   "R_"),    ("l_",   "r_"),
]


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------
def _load_presets():
    if not os.path.exists(_PRESETS_FILE):
        return {}
    try:
        with open(_PRESETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _preset_names():
    return list(_load_presets().keys())


def _flip_side(text):
    for l_tok, r_tok in _SIDE_PAIRS:
        if l_tok in text:
            return text.replace(l_tok, r_tok, 1), "R"
        if r_tok in text:
            return text.replace(r_tok, l_tok, 1), "L"
    return None, None


def _detect_side(text):
    for l_tok, r_tok in _SIDE_PAIRS:
        if l_tok in text:
            return "L"
        if r_tok in text:
            return "R"
    return None


def _resolve_node(name, ns_p):
    """ns_p:name 또는 name 으로 씬에서 노드 찾기. 없으면 None."""
    for candidate in [ns_p + name, name]:
        if cmds.objExists(candidate):
            return candidate
    return None


# ---------------------------------------------------------------------------
# 배치 I/O
# ---------------------------------------------------------------------------
def load_batch():
    if not os.path.exists(_BATCH_FILE):
        return []
    try:
        with open(_BATCH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        cmds.warning("rig_ctrl_batch_tool: load error - " + str(e))
        return []


def save_batch(entries):
    try:
        with open(_BATCH_FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        print("rig_ctrl_batch_tool: saved -> " + _BATCH_FILE)
    except Exception as e:
        cmds.warning("rig_ctrl_batch_tool: save error - " + str(e))


# ---------------------------------------------------------------------------
# 액션 실행 헬퍼
# ---------------------------------------------------------------------------
def _do_add_attrs(node, attr_defs):
    """ctrl_creator_tool._add_attr_to_node 으로 attrs 추가."""
    try:
        import ctrl_creator_tool
    except ImportError:
        cmds.error("ctrl_creator_tool 을 찾을 수 없습니다.")
        return 0
    count = 0
    for ad in attr_defs:
        if ctrl_creator_tool._add_attr_to_node(node, ad):
            count += 1
    return count


def _flip_shapes_on_ctrl(ctrl):
    """ctrl 의 nurbsCurve shape 을 X축 기준으로 mirror (scaleX=-1 + reverseCurve)."""
    try:
        import ctrl_creator_tool
    except ImportError:
        return

    src_shapes = [s for s in (cmds.listRelatives(ctrl, shapes=True, type="nurbsCurve") or [])
                  if not cmds.getAttr(s + ".intermediateObject")]
    if not src_shapes:
        return

    tgt_name = ctrl.split("|")[-1].split(":")[-1]

    # 1. 원본 shapes 를 임시 transform 으로 복제
    temp_fps = []
    for src_sh in src_shapes:
        tmp = cmds.duplicate(src_sh, returnRootsOnly=True)[0]
        temp_fps.append(cmds.ls(tmp, long=True)[0])

    # 2. 원본 shapes 제거
    ctrl_creator_tool._remove_shapes(ctrl)

    # 3. 임시본을 X flip 후 ctrl 에 추가
    for i, tmp_fp in enumerate(temp_fps):
        cmds.setAttr(tmp_fp + ".scaleX", -1)
        cmds.makeIdentity(tmp_fp, apply=True, scale=True)
        cmds.reverseCurve(tmp_fp, ch=False, replaceOriginal=True)
        tmp_fp_ls = cmds.ls(tmp_fp, long=True)
        if not tmp_fp_ls:
            continue
        tmp_fp = tmp_fp_ls[0]
        tmp_shs = cmds.listRelatives(tmp_fp, shapes=True, fullPath=True) or []
        if tmp_shs:
            cmds.parent(tmp_shs[0], ctrl, shape=True, relative=True)
        cmds.delete(tmp_fp)
        cur_shs = cmds.listRelatives(ctrl, shapes=True) or []
        if cur_shs:
            new_name = tgt_name + "Shape" + ("" if i == 0 else str(i))
            try:
                cmds.rename(cur_shs[-1], new_name)
            except Exception:
                pass


def _do_swap_shape(node, shape_data, size, color_idx, flip_x=False):
    """
    node 의 shape 을 교체.
    shape_data 가 있으면 preset shape, 없으면 circle(size) 로 대체.
    flip_x=True 이면 shape 을 X축 기준으로 mirror.
    """
    try:
        import ctrl_creator_tool
    except ImportError:
        cmds.error("ctrl_creator_tool 을 찾을 수 없습니다.")
        return

    tgt_name = node.split("|")[-1].split(":")[-1]

    # 임시 커브 생성
    if shape_data and shape_data.get("pts"):
        tmp = cmds.curve(d=shape_data["degree"], p=shape_data["pts"])
        if shape_data.get("form", 0) == 2:
            sh = cmds.listRelatives(tmp, shapes=True)[0]
            cmds.closeCurve(sh, ch=False, ps=True, rpo=True)
    else:
        tmp = cmds.circle(radius=size, normalX=0, normalY=1, normalZ=0, ch=False)[0]

    tmp_fp  = cmds.ls(tmp, long=True)[0]
    tmp_shs = cmds.listRelatives(tmp_fp, shapes=True, type="nurbsCurve", fullPath=True) or []
    if not tmp_shs:
        cmds.delete(tmp_fp)
        cmds.warning("rig_ctrl_batch_tool: swap_shape 임시 커브 shape 없음 - " + tgt_name)
        return

    # X flip 적용
    if flip_x:
        cmds.setAttr(tmp_fp + ".scaleX", -1)
        cmds.makeIdentity(tmp_fp, apply=True, scale=True)
        cmds.reverseCurve(tmp_fp, ch=False, replaceOriginal=True)
        tmp_fp_ls = cmds.ls(tmp_fp, long=True)
        if not tmp_fp_ls:
            return
        tmp_fp  = tmp_fp_ls[0]
        tmp_shs = cmds.listRelatives(tmp_fp, shapes=True, type="nurbsCurve", fullPath=True) or []
        if not tmp_shs:
            cmds.delete(tmp_fp)
            return

    # 기존 shape 제거
    ctrl_creator_tool._remove_shapes(node)

    # 새 shape 추가
    cmds.parent(tmp_shs[0], node, shape=True, relative=True)
    cmds.delete(tmp_fp)
    new_sh = cmds.listRelatives(node, shapes=True)[-1]
    cmds.rename(new_sh, tgt_name + "Shape")

    # 색상 적용
    if color_idx > 0:
        sh = cmds.listRelatives(node, shapes=True, type="nurbsCurve")
        for s in (sh or []):
            try:
                cmds.setAttr(s + ".overrideEnabled", 1)
                cmds.setAttr(s + ".overrideColor", color_idx)
            except Exception:
                pass

    print("rig_ctrl_batch_tool: shape swapped on '{}'.".format(tgt_name))


# ---------------------------------------------------------------------------
# 배치 실행
# ---------------------------------------------------------------------------
def execute_batch(entries, namespace=""):
    """
    entries 리스트를 순서대로 처리.
    entry: {"name", "preset", "parent", "sided", "action"}
      action: "Create" | "Add Attrs" | "Swap Shape"
    namespace: 기존 리그 네임스페이스 (parent / target 앞에 붙임)
    """
    try:
        import ctrl_creator_tool
    except ImportError:
        cmds.error("rig_ctrl_batch_tool: ctrl_creator_tool 을 찾을 수 없습니다.")
        return

    presets   = _load_presets()
    ns_p      = namespace + ":" if namespace else ""
    total_ok  = 0

    for entry in entries:
        name   = entry.get("name",   "").strip()
        pname  = entry.get("preset", "")
        parent = entry.get("parent", "").strip()
        sided  = entry.get("sided",  False)
        action = entry.get("action", "Create")

        if not name:
            continue

        data       = presets.get(pname, {})
        color_name = data.get("color", "None")
        color_idx  = ctrl_creator_tool.COLORS.get(color_name, 0)
        size       = float(data.get("size", 8.0))
        offsets    = data.get("offset_groups", ["OS", "CS"])
        shape_data = data.get("shape") or None
        attr_defs  = data.get("attrs", [])

        # ------------------------------------------------------------------
        def _run_action(n, par, flip_shape=False):
            nonlocal total_ok
            if action == "Create":
                full_par = (ns_p + par) if par else ""
                ctrl = ctrl_creator_tool.create_controller(
                    name=n, shape_data=shape_data, size=size,
                    offset_suffixes=offsets, parent_node=full_par,
                    attr_defs=attr_defs, color=color_idx,
                )
                if ctrl:
                    if flip_shape:
                        _flip_shapes_on_ctrl(ctrl)
                    total_ok += 1

            elif action == "Add Attrs":
                node = _resolve_node(n, ns_p)
                if not node:
                    cmds.warning("rig_ctrl_batch_tool: '{}' 노드를 찾을 수 없음 - 스킵.".format(ns_p + n))
                    return
                added = _do_add_attrs(node, attr_defs)
                print("rig_ctrl_batch_tool: Add Attrs '{}' → {} attr(s) added.".format(node, added))
                total_ok += 1

            elif action == "Swap Shape":
                node = _resolve_node(n, ns_p)
                if not node:
                    cmds.warning("rig_ctrl_batch_tool: '{}' 노드를 찾을 수 없음 - 스킵.".format(ns_p + n))
                    return
                _do_swap_shape(node, shape_data, size, color_idx, flip_x=flip_shape)
                total_ok += 1
        # ------------------------------------------------------------------

        if sided:
            side = _detect_side(name)
            if side is None:
                cmds.warning("rig_ctrl_batch_tool: '{}' side 토큰 없음 - 단일 처리.".format(name))
                _run_action(name, parent)
            else:
                _run_action(name, parent, flip_shape=False)
                flipped_name, _ = _flip_side(name)
                flipped_par,  _ = _flip_side(parent) if parent and _detect_side(parent) else (parent, None)
                if flipped_name:
                    _run_action(flipped_name, flipped_par or parent, flip_shape=True)
        else:
            _run_action(name, parent)

    print("rig_ctrl_batch_tool: {} item(s) processed.".format(total_ok))


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
WIN_ID = "rigCtrlBatchWin"

_batch_rows = []
_rows_col   = None
_ns_field   = None
# Name / Preset / Action / Parent / L+R / X
_COL_W = [140, 110, 90, 130, 38, 22]


def _get_entries():
    result = []
    for row in _batch_rows:
        n  = cmds.textField(row["nf"],   q=True, text=True).strip() if row.get("nf")  else ""
        pr = cmds.optionMenu(row["pm"],  q=True, value=True)         if row.get("pm")  else ""
        ac = cmds.optionMenu(row["am"],  q=True, value=True)         if row.get("am")  else "Create"
        pa = cmds.textField(row["paf"],  q=True, text=True).strip()  if row.get("paf") else ""
        sd = cmds.checkBox(row["sd"],    q=True, value=True)         if row.get("sd")  else False
        if n:
            result.append({"name": n, "preset": pr, "action": ac, "parent": pa, "sided": sd})
    return result


def _rebuild_rows():
    if not _rows_col or not cmds.columnLayout(_rows_col, exists=True):
        return
    for c in (cmds.columnLayout(_rows_col, q=True, childArray=True) or []):
        if cmds.layout(c, exists=True):
            cmds.deleteUI(c)
    cmds.setParent(_rows_col)
    pnames = _preset_names() or ["(no presets)"]
    for i, row in enumerate(_batch_rows):
        rl = cmds.rowLayout(nc=6, parent=_rows_col)
        for col, w in enumerate(_COL_W, 1):
            cmds.rowLayout(rl, e=True, columnWidth=[col, w])

        row["nf"]  = cmds.textField(text=row.get("name",""), width=_COL_W[0]-2)

        # Preset optionMenu
        row["pm"]  = cmds.optionMenu(width=_COL_W[1]-2)
        for p in pnames:
            cmds.menuItem(label=p)
        saved_p = row.get("preset","")
        for it in (cmds.optionMenu(row["pm"], q=True, itemListLong=True) or []):
            if cmds.menuItem(it, q=True, label=True) == saved_p:
                try: cmds.optionMenu(row["pm"], e=True, value=saved_p)
                except Exception: pass
                break

        # Action optionMenu
        row["am"]  = cmds.optionMenu(width=_COL_W[2]-2)
        for a in _ACTIONS:
            cmds.menuItem(label=a)
        saved_a = row.get("action", "Create")
        try: cmds.optionMenu(row["am"], e=True, value=saved_a)
        except Exception: pass

        row["paf"] = cmds.textField(text=row.get("parent",""), width=_COL_W[3]-2)
        row["sd"]  = cmds.checkBox(label="", value=row.get("sided", True), width=_COL_W[4])
        cmds.button(label="X", width=_COL_W[5], bgc=[0.5,0.2,0.2],
                    c=lambda *a, idx=i: _remove_row(idx))
        row["layout"] = rl
        cmds.setParent("..")


def _sync_rows_from_ui():
    """현재 UI 위젯 값을 _batch_rows 에 반영."""
    for row in _batch_rows:
        if row.get("nf") and cmds.textField(row["nf"], exists=True):
            row["name"]   = cmds.textField(row["nf"],  q=True, text=True).strip()
        if row.get("pm") and cmds.optionMenu(row["pm"], exists=True):
            row["preset"] = cmds.optionMenu(row["pm"], q=True, value=True)
        if row.get("am") and cmds.optionMenu(row["am"], exists=True):
            row["action"] = cmds.optionMenu(row["am"], q=True, value=True)
        if row.get("paf") and cmds.textField(row["paf"], exists=True):
            row["parent"] = cmds.textField(row["paf"], q=True, text=True).strip()
        if row.get("sd") and cmds.checkBox(row["sd"], exists=True):
            row["sided"]  = cmds.checkBox(row["sd"], q=True, value=True)


def _add_row(*_):
    _sync_rows_from_ui()
    _batch_rows.append({"name":"","preset":"Default","action":"Create","parent":"","sided":True})
    _rebuild_rows()


def _remove_row(idx):
    _sync_rows_from_ui()
    if 0 <= idx < len(_batch_rows):
        _batch_rows.pop(idx)
    _rebuild_rows()


def _on_execute(*_):
    entries = _get_entries()
    if not entries:
        cmds.warning("rig_ctrl_batch_tool: 처리할 항목이 없습니다.")
        return
    ns = cmds.textField(_ns_field, q=True, text=True).strip() if _ns_field else ""
    execute_batch(entries, namespace=ns)


def _on_save(*_):
    save_batch(_get_entries())


def _on_load(*_):
    global _batch_rows
    data = load_batch()
    if not data:
        cmds.warning("rig_ctrl_batch_tool: 불러올 데이터가 없습니다.")
        return
    _batch_rows.clear()
    for e in data:
        _batch_rows.append({
            "name":   e.get("name",""),
            "preset": e.get("preset","Default"),
            "action": e.get("action","Create"),
            "parent": e.get("parent",""),
            "sided":  e.get("sided", True),
        })
    _rebuild_rows()
    print("rig_ctrl_batch_tool: {} 항목 로드됨.".format(len(_batch_rows)))


def _on_open_json(*_):
    import subprocess
    if os.path.exists(_BATCH_FILE):
        subprocess.Popen(["notepad", _BATCH_FILE])
    else:
        cmds.warning("rig_ctrl_batch_tool: 저장된 파일이 없습니다. 먼저 Save 하세요.")


def _reload_tool(*_):
    import sys
    for mod in ["ctrl_creator_tool", "rig_ctrl_batch_tool"]:
        [sys.modules.pop(k) for k in list(sys.modules.keys()) if mod in k]
    import rig_ctrl_batch_tool
    rig_ctrl_batch_tool.show()
    print("rig_ctrl_batch_tool: reloaded.")


def _detect_ns(*_):
    for ns in (cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []):
        if cmds.objExists(ns + ":Root") or cmds.objExists(ns + ":root_ctrl"):
            if _ns_field and cmds.textField(_ns_field, exists=True):
                cmds.textField(_ns_field, e=True, text=ns)
            return ns
    cmds.warning("rig_ctrl_batch_tool: namespace 자동감지 실패 - 직접 입력하세요.")


# ---------------------------------------------------------------------------
def show():
    global _batch_rows, _rows_col, _ns_field

    if cmds.window(WIN_ID, exists=True):
        cmds.deleteUI(WIN_ID)

    _batch_rows = []

    win = cmds.window(WIN_ID, title="Rig Ctrl Batch Creator",
                      widthHeight=(545, 560), sizeable=True,
                      resizeToFitChildren=True)
    cmds.scrollLayout(childResizable=True)
    root = cmds.columnLayout(adj=True, rowSpacing=4)

    # ── Namespace ────────────────────────────────────────────────────────
    cmds.frameLayout(label="  Namespace", collapsable=True, collapse=False,
                     marginWidth=6, marginHeight=4)
    cmds.columnLayout(adj=True, rowSpacing=3)
    cmds.rowLayout(nc=3, adjustableColumn=2, columnWidth3=[80, 340, 80])
    cmds.text(label="Namespace", align="right")
    _ns_field = cmds.textField(text="")
    cmds.button(label="Detect", c=_detect_ns)
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setParent(root)

    # ── Batch List ───────────────────────────────────────────────────────
    cmds.frameLayout(label="  Controller List", collapsable=True, collapse=False,
                     marginWidth=6, marginHeight=4)
    cmds.columnLayout(adj=True, rowSpacing=2)

    # 헤더
    hdr = cmds.rowLayout(nc=6)
    for col, w in enumerate(_COL_W, 1):
        cmds.rowLayout(hdr, e=True, columnWidth=[col, w])
    for lbl in ["Name", "Preset", "Action", "Parent (Create)", "L+R", ""]:
        cmds.text(label=lbl, align="center")
    cmds.setParent("..")

    _rows_col = cmds.columnLayout(adj=True, rowSpacing=1)
    cmds.setParent("..")

    cmds.rowLayout(nc=2, columnWidth2=[272, 272])
    cmds.button(label="+ Add Row",  h=24, bgc=[0.25,0.4,0.25], c=_add_row)
    cmds.button(label="Clear All",  h=24, bgc=[0.45,0.25,0.25],
                c=lambda *_: [_batch_rows.clear(), _rebuild_rows()])
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setParent(root)

    # ── Config I/O ───────────────────────────────────────────────────────
    cmds.frameLayout(label="  Config  ({})".format(os.path.basename(_BATCH_FILE)),
                     collapsable=True, collapse=False,
                     marginWidth=6, marginHeight=4)
    cmds.columnLayout(adj=True, rowSpacing=3)
    cmds.rowLayout(nc=4, columnWidth4=[136, 136, 136, 107])
    cmds.button(label="Load JSON", h=28, bgc=[0.2,0.35,0.5],  c=_on_load)
    cmds.button(label="Save JSON", h=28, bgc=[0.25,0.4,0.25], c=_on_save)
    cmds.button(label="Open JSON", h=28, c=_on_open_json)
    cmds.button(label="Reload Tool", h=28, bgc=[0.35,0.3,0.2],
                c=lambda *_: _reload_tool())
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setParent(root)

    # ── Execute ──────────────────────────────────────────────────────────
    cmds.separator(h=6, style="none")
    cmds.button(label="Execute", height=44, bgc=[0.2,0.5,0.2], c=_on_execute)
    cmds.separator(h=6, style="none")
    cmds.setParent("..")

    cmds.showWindow(win)
    _rebuild_rows()


if __name__ == "__main__":
    show()
