"""
Controller Creator Tool  v3
범용 컨트롤러 생성 + 편집 도구.

생성: shape / offset groups / parent / attributes / color
편집: swap shape / scale / rotate / width / mirror / color set

사용:
    import importlib
    import ctrl_creator_tool
    importlib.reload(ctrl_creator_tool)
    ctrl_creator_tool.show()
"""

import os, math, json
import maya.cmds as cmds

# ---------------------------------------------------------------------------
# 경로
# ---------------------------------------------------------------------------
_TOOL_DIR    = os.path.dirname(os.path.abspath(__file__))
PRESETS_FILE = os.path.join(_TOOL_DIR, "ctrl_creator_presets.json")

# ---------------------------------------------------------------------------
# Maya override color index → RGB (0-1)
# ---------------------------------------------------------------------------
MAYA_COLOR_RGB = {
    0:  (0.47, 0.47, 0.47),  # None
    1:  (0.00, 0.00, 0.00),  2:  (0.25, 0.25, 0.25),  3:  (0.60, 0.60, 0.60),
    4:  (0.61, 0.00, 0.16),  5:  (0.00, 0.02, 0.38),  6:  (0.00, 0.00, 1.00),
    7:  (0.00, 0.28, 0.10),  8:  (0.15, 0.00, 0.26),  9:  (0.78, 0.00, 0.78),
    10: (0.54, 0.28, 0.20),  11: (0.25, 0.14, 0.12),  12: (0.60, 0.15, 0.00),
    13: (1.00, 0.00, 0.00),  14: (0.00, 1.00, 0.00),  15: (0.00, 0.26, 0.60),
    16: (1.00, 1.00, 1.00),  17: (1.00, 1.00, 0.00),  18: (0.39, 0.86, 1.00),
    19: (0.26, 1.00, 0.64),  20: (1.00, 0.69, 0.69),  21: (0.89, 0.68, 0.48),
    22: (1.00, 1.00, 0.39),  23: (0.00, 0.60, 0.33),  24: (0.63, 0.41, 0.19),
    25: (0.62, 0.63, 0.19),  26: (0.41, 0.63, 0.19),  27: (0.19, 0.63, 0.37),
    28: (0.19, 0.63, 0.63),  29: (0.19, 0.40, 0.63),  30: (0.44, 0.19, 0.63),
    31: (0.63, 0.19, 0.41),
}

# 이름 기반 색상 (프리셋 호환)
COLORS = {
    "None":6, "Black":1, "Grey":3, "DarkRed":4, "DarkBlue":5, "Blue":6,
    "DarkGreen":7, "Magenta":9, "DarkOrange":12, "Red":13, "Green":14,
    "White":16, "Yellow":17, "LightBlue":18, "LightGreen":19,
    "Pink":20, "Orange":25,
}

# ---------------------------------------------------------------------------
# 프리셋 I/O
# ---------------------------------------------------------------------------
def load_presets():
    if not os.path.exists(PRESETS_FILE):
        return {}
    try:
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        cmds.warning("ctrl_creator_tool: preset load error - " + str(e))
        return {}

def save_presets(presets):
    try:
        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)
        print("ctrl_creator_tool: presets saved -> " + PRESETS_FILE)
    except Exception as e:
        cmds.warning("ctrl_creator_tool: preset save error - " + str(e))

# ---------------------------------------------------------------------------
# 핵심 생성
# ---------------------------------------------------------------------------
_COMPOUND_CHILD = {"double3":"double","float3":"float",
                   "double2":"double","float2":"float"}

def _add_attr_to_node(node, ad):
    """
    attr 정의(dict)를 node에 추가하는 공통 헬퍼.
    keyable 체크박스 값을 정확히 반영한다.
    - compound 부모: keyable 플래그 없이 생성, 자식에만 keyable 적용
    - string: dataType 사용, keyable 미지원이므로 생성 후 channelBox만 설정
    - 그 외: keyable=k 로 생성
    """
    ln = ad.get("ln", "").strip()
    if not ln:
        return False
    if cmds.attributeQuery(ln, node=node, exists=True):
        cmds.warning("ctrl_creator_tool: '{}' already exists on {} - skipped.".format(ln, node))
        return False
    at = ad.get("at", "float")
    k  = bool(ad.get("k", True))
    try:
        if at == "enum":
            en_str = str(ad.get("min", "Option1:Option2")).strip() or "Option1:Option2"
            cmds.addAttr(node, ln=ln, at="enum", enumName=en_str, keyable=k)
        elif at in _COMPOUND_CHILD:
            child_at = _COMPOUND_CHILD[at]
            # 부모 compound는 keyable 플래그 없이 생성
            cmds.addAttr(node, ln=ln, at=at)
            for ch in (ad.get("ch") or [ln+"X", ln+"Y", ln+"Z"]):
                if not cmds.attributeQuery(ch, node=node, exists=True):
                    cmds.addAttr(node, ln=ch, at=child_at, parent=ln, keyable=k)
        elif at == "string":
            # string은 keyable 미지원 → 생성 후 channelBox로 표시
            cmds.addAttr(node, ln=ln, dataType="string")
            if k:
                try: cmds.setAttr(node+"."+ln, channelBox=True)
                except Exception: pass
        else:
            kw = {"longName": ln, "attributeType": at, "keyable": k}
            if at in ("float", "int", "double", "doubleAngle", "doubleLinear"):
                mn, mx, dv = ad.get("min",""), ad.get("max",""), ad.get("dv","")
                if str(mn) != "": kw["minValue"]     = float(mn)
                if str(mx) != "": kw["maxValue"]     = float(mx)
                if str(dv) != "": kw["defaultValue"] = float(dv)
            elif at == "bool":
                dv = ad.get("dv","")
                if str(dv) != "": kw["defaultValue"] = int(float(dv))
            cmds.addAttr(node, **kw)
        return True
    except Exception as e:
        cmds.warning("ctrl_creator_tool: failed to add '{}' on {} - {}".format(ln, node, e))
        return False

def create_controller(name, shape_data=None, size=8.0,
                      offset_suffixes=("OS","CS"), parent_node="",
                      attr_defs=None, color=0):
    if attr_defs is None:
        attr_defs = []
    if parent_node and not cmds.objExists(parent_node):
        cmds.warning("ctrl_creator_tool: parent '{}' not found.".format(parent_node))
        return None

    current_parent = parent_node or None
    group_nodes = []
    for suffix in offset_suffixes:
        gname = "{}_{}".format(name, suffix) if suffix else name + "_GRP"
        grp = cmds.group(empty=True, name=gname, parent=current_parent) \
              if current_parent else cmds.group(empty=True, name=gname)
        if current_parent:
            pos = cmds.xform(current_parent, q=True, ws=True, t=True)
            rot = cmds.xform(current_parent, q=True, ws=True, ro=True)
            cmds.xform(grp, ws=True, t=pos, ro=rot)
        group_nodes.append(grp)
        current_parent = grp

    if shape_data and shape_data.get("pts"):
        ctrl = cmds.curve(name=name, d=shape_data["degree"], p=shape_data["pts"])
        if shape_data.get("form", 0) == 2:
            sh = cmds.listRelatives(ctrl, shapes=True)[0]
            cmds.closeCurve(sh, ch=False, ps=True, rpo=True)
    else:
        ctrl = cmds.circle(name=name, radius=size,
                           normalX=0, normalY=1, normalZ=0, ch=False)[0]

    if current_parent:
        cmds.parent(ctrl, current_parent)
    # 이름 충돌 가능성이 있으므로 long path로 고정
    long = cmds.ls(ctrl, long=True)
    if long:
        ctrl = long[0]
    cmds.xform(ctrl, os=True, t=[0,0,0], ro=[0,0,0], s=[1,1,1])

    for sh in (cmds.listRelatives(ctrl, shapes=True) or []):
        cmds.rename(sh, name + "Shape")
    if color > 0:
        for sh in (cmds.listRelatives(ctrl, shapes=True) or []):
            cmds.setAttr(sh + ".overrideEnabled", 1)
            cmds.setAttr(sh + ".overrideColor", color)

    for ad in attr_defs:
        _add_attr_to_node(ctrl, ad)

    gnames = [g.split("|")[-1] for g in group_nodes]
    print("ctrl_creator: {} | groups: {}".format(
        ctrl, " > ".join(gnames) if gnames else "(none)"))
    return ctrl

# ---------------------------------------------------------------------------
# Shape 복사
# ---------------------------------------------------------------------------
def copy_shape_from_selection():
    sel = cmds.ls(selection=True)
    if not sel:
        cmds.warning("ctrl_creator_tool: select a controller first.")
        return None
    obj = sel[0]
    shapes = cmds.listRelatives(obj, shapes=True, type="nurbsCurve") or []
    if not shapes and cmds.nodeType(obj) == "nurbsCurve":
        shapes = [obj]
    if not shapes:
        cmds.warning("ctrl_creator_tool: no nurbsCurve on {}.".format(obj))
        return None
    sh     = shapes[0]
    degree = cmds.getAttr(sh + ".degree")
    form   = cmds.getAttr(sh + ".form")
    spans  = cmds.getAttr(sh + ".spans")
    pts    = [cmds.getAttr(sh + ".cv[{}]".format(i))[0]
              for i in range(degree + spans)]
    data   = {"degree": degree, "form": form, "pts": pts}
    print("ctrl_creator_tool: shape copied ({} CVs, deg {})".format(len(pts), degree))
    return data

# ---------------------------------------------------------------------------
# Swap Shape
# ---------------------------------------------------------------------------
def _remove_shapes(target):
    """target의 non-intermediate nurbsCurve shape 제거 (referenced면 숨김)."""
    old_shapes = cmds.listRelatives(target, shapes=True, type="nurbsCurve") or []
    for sh in old_shapes:
        if cmds.getAttr(sh + ".intermediateObject"):
            continue
        try:
            referenced = cmds.referenceQuery(sh, isNodeReferenced=True)
        except Exception:
            referenced = False
        if referenced:
            try: cmds.setAttr(sh + ".visibility", False)
            except Exception: pass
        else:
            cmds.delete(sh)


def _add_shape_copy(src_shape, target, index=0, flip_x=False):
    """
    src_shape을 duplicate해서 target에 shape으로 추가.
    flip_x=True이면 scaleX=-1 + makeIdentity 베이크 후 reverseCurve로 winding 복원.
    새로 추가된 shape 이름을 반환.
    """
    tgt_name = target.split("|")[-1].split(":")[-1]
    tmp_fp   = cmds.ls(cmds.duplicate(src_shape, returnRootsOnly=True)[0], long=True)[0]
    if not cmds.listRelatives(tmp_fp, shapes=True, fullPath=True):
        cmds.delete(tmp_fp)
        return None
    if flip_x:
        cmds.setAttr(tmp_fp + ".scaleX", -1)
        cmds.makeIdentity(tmp_fp, apply=True, scale=True)
        cmds.reverseCurve(tmp_fp, ch=False, replaceOriginal=True)
        # reverseCurve 후 tmp_fp 노드 이름이 바뀔 수 있으므로 재쿼리
        tmp_fp = cmds.ls(tmp_fp, long=True)
        if not tmp_fp:
            return None
        tmp_fp = tmp_fp[0]
    tmp_shs = cmds.listRelatives(tmp_fp, shapes=True, fullPath=True) or []
    if not tmp_shs:
        cmds.delete(tmp_fp)
        return None
    cmds.parent(tmp_shs[0], target, shape=True, relative=True)
    cmds.delete(tmp_fp)
    new_sh = cmds.listRelatives(target, shapes=True)[-1]
    new_name = tgt_name + "Shape" + ("" if index == 0 else str(index))
    return cmds.rename(new_sh, new_name)


def swap_shape():
    """
    첫 번째 선택 ctrl의 shape → 나머지 선택된 ctrl에 교체 적용.
    target의 기존 shape을 삭제(referenced면 숨김)하고 source shape 복사본으로 대체.
    """
    sel = cmds.ls(selection=True, type="transform")
    if len(sel) < 2:
        cmds.warning("ctrl_creator_tool: select source ctrl, then target ctrls (2+).")
        return
    source  = sel[0]
    targets = sel[1:]

    src_shapes = [s for s in (cmds.listRelatives(source, shapes=True, type="nurbsCurve") or [])
                  if not cmds.getAttr(s + ".intermediateObject")]
    if not src_shapes:
        cmds.warning("ctrl_creator_tool: no visible nurbsCurve shape on {}.".format(source))
        return

    for target in targets:
        _remove_shapes(target)
        for i, src_sh in enumerate(src_shapes):
            _add_shape_copy(src_sh, target, index=i)

    print("ctrl_creator_tool: shape swapped to {} target(s).".format(len(targets)))

# ---------------------------------------------------------------------------
# CV 편집 헬퍼
# ---------------------------------------------------------------------------
def _iter_shapes(ctrls):
    """선택된 transform 리스트에서 non-intermediate nurbsCurve shape 목록 반환."""
    result = []
    for ctrl in ctrls:
        shapes = cmds.listRelatives(ctrl, shapes=True, type="nurbsCurve") or []
        result += [s for s in shapes
                   if not cmds.getAttr(s + ".intermediateObject")]
    return result

def _get_cvs(shape):
    degree = cmds.getAttr(shape + ".degree")
    spans  = cmds.getAttr(shape + ".spans")
    count  = degree + spans
    return [cmds.getAttr(shape + ".cv[{}]".format(i))[0] for i in range(count)]

def _set_cvs(shape, cvs):
    for i, (x, y, z) in enumerate(cvs):
        cmds.setAttr(shape + ".cv[{}]".format(i), x, y, z, type="double3")

def _transform_cvs(cvs, sx=1, sy=1, sz=1, rx=0, ry=0, rz=0):
    """Scale 후 Rotate (XYZ 순) 적용."""
    rxr, ryr, rzr = math.radians(rx), math.radians(ry), math.radians(rz)
    cx, sx_ = math.cos(rxr), math.sin(rxr)
    cy, sy_ = math.cos(ryr), math.sin(ryr)
    cz, sz_ = math.cos(rzr), math.sin(rzr)
    result = []
    for x, y, z in cvs:
        # Scale
        x, y, z = x*sx, y*sy, z*sz
        # Rx
        y, z = y*cx - z*sx_, y*sx_ + z*cx
        # Ry
        x, z = x*cy + z*sy_, -x*sy_ + z*cy
        # Rz
        x, y = x*cz - y*sz_, x*sz_ + y*cz
        result.append((x, y, z))
    return result

# ---------------------------------------------------------------------------
# Shape 편집 함수 (선택 기반)
# ---------------------------------------------------------------------------
def scale_shape(sx=1.0, sy=1.0, sz=1.0):
    sel = cmds.ls(selection=True, type="transform")
    if not sel:
        cmds.warning("ctrl_creator_tool: select controllers to scale.")
        return
    for sh in _iter_shapes(sel):
        _set_cvs(sh, _transform_cvs(_get_cvs(sh), sx=sx, sy=sy, sz=sz))

def rotate_shape(rx=0.0, ry=0.0, rz=0.0):
    sel = cmds.ls(selection=True, type="transform")
    if not sel:
        cmds.warning("ctrl_creator_tool: select controllers to rotate.")
        return
    for sh in _iter_shapes(sel):
        _set_cvs(sh, _transform_cvs(_get_cvs(sh), rx=rx, ry=ry, rz=rz))

def set_line_width(width=1.0):
    sel = cmds.ls(selection=True, type="transform")
    if not sel:
        cmds.warning("ctrl_creator_tool: select controllers.")
        return
    for sh in _iter_shapes(sel):
        cmds.setAttr(sh + ".lineWidth", width)

def mirror_shape():
    """
    선택된 ctrl의 side 토큰 기반으로 반대쪽 ctrl에 X축 미러된 shape 적용.
    지원 패턴: Left/Right, left/right, _L_/_R_, _L/_R, L_/R_, _l/_r, l_/r_
    """
    # 긴 토큰을 먼저 검사해야 _L이 Left 안에서 오매칭되는 것을 방지
    _SIDE_PAIRS = [
        ("Left", "Right"), ("left", "right"),
        ("_L_",  "_R_"),   ("_l_",  "_r_"),
        ("_L",   "_R"),    ("_l",   "_r"),
        ("L_",   "R_"),    ("l_",   "r_"),
    ]
    sel = cmds.ls(selection=True, type="transform")
    if not sel:
        cmds.warning("ctrl_creator_tool: select controllers to mirror.")
        return
    mirrored = 0
    for ctrl in sel:
        # namespace와 short name 분리 (namespace 내 패턴 오매칭 방지)
        namespace = ""
        short = ctrl.split("|")[-1]
        if ":" in short:
            ns_part, short = short.rsplit(":", 1)
            namespace = ns_part + ":"

        mirror_short = None
        for l_tok, r_tok in _SIDE_PAIRS:
            if l_tok in short:
                mirror_short = short.replace(l_tok, r_tok, 1)
                break
            if r_tok in short:
                mirror_short = short.replace(r_tok, l_tok, 1)
                break

        if not mirror_short:
            cmds.warning("ctrl_creator_tool: no side token in '{}'.".format(short))
            continue

        # 같은 namespace 먼저 시도, 없으면 namespace 없이 시도
        mirror_ctrl = None
        for candidate in [namespace + mirror_short, mirror_short]:
            if cmds.objExists(candidate):
                mirror_ctrl = candidate
                break
        if not mirror_ctrl:
            cmds.warning("ctrl_creator_tool: mirror target '{}' not found.".format(namespace + mirror_short))
            continue

        # source shape → X 반전 복사 → target에 기존 shape 삭제 후 추가
        src_shapes = _iter_shapes([ctrl])
        if not src_shapes:
            cmds.warning("ctrl_creator_tool: no nurbsCurve shape on '{}'.".format(ctrl))
            continue

        # 색상 정보 미리 수집 (shape 삭제 전)
        src_colors = []
        for src_sh in src_shapes:
            src_colors.append({
                "enabled": cmds.getAttr(src_sh + ".overrideEnabled"),
                "color":   cmds.getAttr(src_sh + ".overrideColor"),
            })

        _remove_shapes(mirror_ctrl)
        new_shapes = []
        for i, src_sh in enumerate(src_shapes):
            new_sh = _add_shape_copy(src_sh, mirror_ctrl, index=i, flip_x=True)
            if new_sh:
                new_shapes.append(new_sh)

        # 반환된 shape 이름으로 색상 직접 적용 (숨겨진 old shape과 혼동 없음)
        for j, mir_sh in enumerate(new_shapes):
            if j < len(src_colors):
                try:
                    cmds.setAttr(mir_sh + ".overrideEnabled", src_colors[j]["enabled"])
                    cmds.setAttr(mir_sh + ".overrideColor",   src_colors[j]["color"])
                except Exception as e:
                    cmds.warning("ctrl_creator_tool: color copy failed - " + str(e))

        mirrored += 1

    cmds.select(sel)
    print("ctrl_creator_tool: mirrored {} controller(s).".format(mirrored))

def set_color_to_selection(color_idx):
    """선택한 컨트롤러들의 shape에 color 직접 적용."""
    sel = cmds.ls(selection=True, type="transform")
    if not sel:
        cmds.warning("ctrl_creator_tool: select controllers.")
        return
    for ctrl in sel:
        for sh in _iter_shapes([ctrl]):
            if color_idx > 0:
                cmds.setAttr(sh + ".overrideEnabled", 1)
                cmds.setAttr(sh + ".overrideColor", color_idx)
            else:
                cmds.setAttr(sh + ".overrideEnabled", 0)

# ---------------------------------------------------------------------------
# Attr 타입 맵
# ---------------------------------------------------------------------------
_ATTR_TYPE_MAP = {
    "double":"float","float":"float","doubleLinear":"float",
    "doubleAngle":"float","time":"float","distance":"float",
    "bool":"bool","long":"int","short":"int","byte":"int",
    "enum":"enum","double3":"double3","float3":"float3",
    "double2":"double2","float2":"float2","string":"string",
}
_COMPOUND_TYPES = {"double3","float3","double2","float2"}

def _query_attr_info(obj, attr):
    if not cmds.attributeQuery(attr, node=obj, exists=True):
        return None
    at_raw = cmds.getAttr("{}.{}".format(obj, attr), type=True) or "double"
    at = _ATTR_TYPE_MAP.get(at_raw)
    if at is None:
        cmds.warning("ctrl_creator_tool: unsupported type '{}' on {}.{} - skipped.".format(
            at_raw, obj, attr))
        return None
    k  = bool(cmds.attributeQuery(attr, node=obj, keyable=True))
    mn = mx = dv = en = ""
    ch = []
    if at == "enum":
        en_list = cmds.attributeQuery(attr, node=obj, listEnum=True) or []
        en = en_list[0] if en_list else "Option1:Option2"
    elif at in _COMPOUND_TYPES:
        nc = cmds.attributeQuery(attr, node=obj, numberOfChildren=True)
        if nc:
            ch = cmds.attributeQuery(attr, node=obj, listChildren=True) or []
    elif at not in ("string","bool"):
        try:
            if cmds.attributeQuery(attr, node=obj, minExists=True):
                mn = cmds.attributeQuery(attr, node=obj, minimum=True)[0]
        except Exception: pass
        try:
            if cmds.attributeQuery(attr, node=obj, maxExists=True):
                mx = cmds.attributeQuery(attr, node=obj, maximum=True)[0]
        except Exception: pass
        try:
            dd = cmds.attributeQuery(attr, node=obj, listDefault=True)
            if dd is not None: dv = dd[0]
        except Exception: pass
    elif at == "bool":
        try:
            dd = cmds.attributeQuery(attr, node=obj, listDefault=True)
            if dd is not None: dv = dd[0]
        except Exception: pass
    return {"ln":attr,"at":at,"min":mn,"max":mx,"dv":dv,"k":k,"en":en,"ch":ch}

# ============================================================================
# UI
# ============================================================================
WIN_ID = "ctrlCreatorWin"

_copied_shape     = None
_current_color_idx = 6
_offset_rows      = []
_attr_rows        = []
_offset_col       = None
_attr_col         = None
_preset_menu      = None
_name_field       = None
_size_field       = None
_parent_field     = None
_color_indicator  = None   # 현재 색상 표시 버튼
_shape_label      = None
# Shape Tools UI refs
_sc_x = _sc_y = _sc_z = None
_rt_x = _rt_y = _rt_z = None
_lw_f = None

# ---------------------------------------------------------------------------
# Color 관련
# ---------------------------------------------------------------------------
def _on_swatch_click(idx, *_):
    global _current_color_idx
    _current_color_idx = idx
    if _color_indicator and cmds.button(_color_indicator, exists=True):
        rgb = MAYA_COLOR_RGB.get(idx, (0.5,0.5,0.5))
        label = "None" if idx == 0 else str(idx)
        cmds.button(_color_indicator, e=True, bgc=rgb, label=label)

def _copy_color_from_selection(*_):
    sel = cmds.ls(selection=True)
    if not sel: return
    shapes = cmds.listRelatives(sel[0], shapes=True, type="nurbsCurve") or []
    if not shapes: return
    sh = shapes[0]
    if cmds.getAttr(sh + ".overrideEnabled"):
        idx = cmds.getAttr(sh + ".overrideColor")
        _on_swatch_click(idx)

def _on_set_color(*_):
    set_color_to_selection(_current_color_idx)

# ---------------------------------------------------------------------------
# Offset rows
# ---------------------------------------------------------------------------
def _rebuild_offset_rows():
    if not _offset_col or not cmds.columnLayout(_offset_col, exists=True):
        return
    for c in (cmds.columnLayout(_offset_col, q=True, childArray=True) or []):
        if cmds.layout(c, exists=True): cmds.deleteUI(c)
    cmds.setParent(_offset_col)
    for i, row in enumerate(_offset_rows):
        rl = cmds.rowLayout(nc=3, adjustableColumn=2,
                            columnWidth3=[28,200,28], parent=_offset_col)
        cmds.text(label="{}.".format(i+1))
        row["field"] = cmds.textField(text=row.get("suffix","GRP"))
        cmds.button(label="X", bgc=[0.5,0.2,0.2],
                    c=lambda *a, idx=i: _remove_offset_row(idx))
        row["layout"] = rl
        cmds.setParent("..")

def _add_offset_row(*_):
    defaults = ["OS","CS","Extra","Space","Auto"]
    default  = defaults[min(len(_offset_rows), len(defaults)-1)]
    _offset_rows.append({"suffix": default})
    _rebuild_offset_rows()

def _remove_offset_row(idx):
    if 0 <= idx < len(_offset_rows): _offset_rows.pop(idx)
    _rebuild_offset_rows()

def _get_offset_suffixes():
    result = []
    for row in _offset_rows:
        f = row.get("field")
        if f and cmds.textField(f, exists=True):
            v = cmds.textField(f, q=True, text=True).strip()
            if v: result.append(v)
    return result

# ---------------------------------------------------------------------------
# Attr rows
# ---------------------------------------------------------------------------
_ATTR_TYPES = ["float","bool","int","enum","double3","string"]
_COL_W      = [90, 62, 86, 38, 38, 22, 22]   # Name/Type/Min-Enum/Max/Def/Key/X

def _rebuild_attr_rows():
    if not _attr_col or not cmds.columnLayout(_attr_col, exists=True):
        return
    for c in (cmds.columnLayout(_attr_col, q=True, childArray=True) or []):
        if cmds.layout(c, exists=True): cmds.deleteUI(c)
    cmds.setParent(_attr_col)
    for i, row in enumerate(_attr_rows):
        rl = cmds.rowLayout(nc=7, parent=_attr_col)
        for col, w in enumerate(_COL_W, 1):
            cmds.rowLayout(rl, e=True, columnWidth=[col, w])
        row["ln_f"] = cmds.textField(text=row.get("ln",""), width=_COL_W[0]-2)
        row["at_m"] = cmds.optionMenu(width=_COL_W[1]-2)
        for t in _ATTR_TYPES: cmds.menuItem(label=t)
        at_val = row.get("at","float")
        items  = cmds.optionMenu(row["at_m"], q=True, itemListLong=True) or []
        for j, it in enumerate(items):
            if cmds.menuItem(it, q=True, label=True) == at_val:
                cmds.optionMenu(row["at_m"], e=True, select=j+1); break
        row["mn_f"] = cmds.textField(text=str(row.get("min","")), width=_COL_W[2]-2)
        row["mx_f"] = cmds.textField(text=str(row.get("max","")), width=_COL_W[3]-2)
        row["dv_f"] = cmds.textField(text=str(row.get("dv", "")), width=_COL_W[4]-2)
        row["k_cb"] = cmds.checkBox(label="", value=row.get("k",True), width=_COL_W[5])
        cmds.button(label="X", width=_COL_W[6], bgc=[0.5,0.2,0.2],
                    c=lambda *a, idx=i: _remove_attr_row(idx))
        row["layout"] = rl
        cmds.setParent("..")

def _add_attr_row(ln="",at="float",mn="",mx="",dv="",k=True,ch=None):
    _attr_rows.append({"ln":ln,"at":at,"min":mn,"max":mx,"dv":dv,"k":k,"ch":ch or []})
    _rebuild_attr_rows()

def _remove_attr_row(idx):
    if 0 <= idx < len(_attr_rows): _attr_rows.pop(idx)
    _rebuild_attr_rows()

def _get_attr_defs():
    result = []
    for row in _attr_rows:
        ln = cmds.textField(row["ln_f"],q=True,text=True).strip() \
             if row.get("ln_f") and cmds.textField(row["ln_f"],exists=True) else ""
        if not ln: continue
        result.append({
            "ln": ln,
            "at": cmds.optionMenu(row["at_m"],q=True,value=True) if row.get("at_m") else "float",
            "min": cmds.textField(row["mn_f"],q=True,text=True) if row.get("mn_f") else "",
            "max": cmds.textField(row["mx_f"],q=True,text=True) if row.get("mx_f") else "",
            "dv":  cmds.textField(row["dv_f"],q=True,text=True) if row.get("dv_f") else "",
            "k":   cmds.checkBox(row["k_cb"],q=True,value=True) if row.get("k_cb") else True,
            "ch":  row.get("ch", []),
        })
    return result

# ---------------------------------------------------------------------------
# Channel Box 복사
# ---------------------------------------------------------------------------
def _copy_attrs_from_channelbox(*_):
    sel = cmds.ls(selection=True)
    if not sel:
        cmds.warning("ctrl_creator_tool: select an object first.")
        return
    obj = sel[0]
    cb_attrs = cmds.channelBox("mainChannelBox", q=True,
                               selectedMainAttributes=True) or []
    if not cb_attrs:
        cmds.warning("ctrl_creator_tool: select attributes in the Channel Box.")
        return
    added = 0
    for attr in cb_attrs:
        info = _query_attr_info(obj, attr)
        if info is None: continue
        mn = info["en"] if info["at"] == "enum" else info["min"]
        _add_attr_row(ln=info["ln"], at=info["at"],
                      mn=mn, mx=info["max"], dv=info["dv"],
                      k=info["k"], ch=info.get("ch",[]))
        added += 1
    print("ctrl_creator_tool: {} attr(s) copied from channel box.".format(added))


def _set_attrs_to_selection(*_):
    """현재 attr 목록을 선택한 오브젝트(들)에 추가."""
    sel = cmds.ls(selection=True, type="transform")
    if not sel:
        cmds.warning("ctrl_creator_tool: select object(s) to add attrs.")
        return
    attr_defs = _get_attr_defs()
    if not attr_defs:
        cmds.warning("ctrl_creator_tool: no attributes in the list.")
        return
    total = 0
    for obj in sel:
        for ad in attr_defs:
            if _add_attr_to_node(obj, ad):
                total += 1
    print("ctrl_creator_tool: {} attr(s) added to {} object(s).".format(total, len(sel)))

# ---------------------------------------------------------------------------
# 프리셋 UI
# ---------------------------------------------------------------------------
def _refresh_preset_menu():
    if not _preset_menu or not cmds.optionMenu(_preset_menu, exists=True): return
    for it in (cmds.optionMenu(_preset_menu, q=True, itemListLong=True) or []):
        cmds.deleteUI(it)
    for name in load_presets().keys():
        cmds.menuItem(label=name, parent=_preset_menu)

def _on_load_preset(*_):
    global _copied_shape, _offset_rows, _attr_rows
    presets = load_presets()
    pname   = cmds.optionMenu(_preset_menu, q=True, value=True)
    data    = presets.get(pname, {})
    # name
    if _name_field and cmds.textField(_name_field, exists=True):
        n = data.get("name","")
        if n: cmds.textField(_name_field, e=True, text=n)
    # parent
    if _parent_field and cmds.textField(_parent_field, exists=True):
        cmds.textField(_parent_field, e=True, text=data.get("parent",""))
    # color
    c_name = data.get("color","None")
    c_idx  = COLORS.get(c_name, 0)
    _on_swatch_click(c_idx)
    # size
    if _size_field and cmds.floatField(_size_field, exists=True):
        cmds.floatField(_size_field, e=True, value=float(data.get("size",8.0)))
    # shape
    _copied_shape = data.get("shape") or None
    if _shape_label and cmds.text(_shape_label, exists=True):
        cmds.text(_shape_label, e=True,
                  label="Preset ({} CVs)".format(len((_copied_shape or {}).get("pts",[])))
                  if _copied_shape else "Circle (default)")
    # offset groups
    _offset_rows.clear()
    for s in data.get("offset_groups",["OS","CS"]):
        _offset_rows.append({"suffix": s})
    _rebuild_offset_rows()
    # attrs
    _attr_rows.clear()
    for ad in data.get("attrs",[]):
        _attr_rows.append({
            "ln": ad.get("ln",""), "at": ad.get("at","float"),
            "min": ad.get("min",""), "max": ad.get("max",""),
            "dv":  ad.get("dv",""),  "k":  ad.get("k",True),
            "ch":  ad.get("ch",[]),
        })
    _rebuild_attr_rows()
    print("ctrl_creator_tool: preset '{}' loaded.".format(pname))

def _on_save_preset(*_):
    result = cmds.promptDialog(title="Save Preset", message="Preset name:",
                               button=["Save","Cancel"], defaultButton="Save",
                               cancelButton="Cancel", dismissString="Cancel",
                               text="New Preset")
    if result != "Save": return
    pname = cmds.promptDialog(query=True, text=True).strip()
    if not pname: return
    c_name = next((k for k,v in COLORS.items() if v == _current_color_idx), "None")
    preset = {
        "name":   cmds.textField(_name_field,   q=True, text=True).strip() if _name_field else "",
        "parent": cmds.textField(_parent_field, q=True, text=True).strip() if _parent_field else "",
        "color":  c_name, "size": cmds.floatField(_size_field, q=True, value=True),
        "offset_groups": _get_offset_suffixes(),
        "shape": _copied_shape, "attrs": _get_attr_defs(),
    }
    presets = load_presets()
    presets[pname] = preset
    save_presets(presets)
    _refresh_preset_menu()
    try: cmds.optionMenu(_preset_menu, e=True, value=pname)
    except Exception: pass

def _on_delete_preset(*_):
    pname = cmds.optionMenu(_preset_menu, q=True, value=True) if _preset_menu else ""
    if not pname: return
    if cmds.confirmDialog(title="Delete", message="Delete '{}'?".format(pname),
                          button=["Delete","Cancel"], defaultButton="Cancel",
                          cancelButton="Cancel") != "Delete": return
    presets = load_presets()
    if pname in presets:
        del presets[pname]
        save_presets(presets)
        _refresh_preset_menu()

def _on_open_json(*_):
    try: os.startfile(PRESETS_FILE)
    except Exception:
        import subprocess
        try: subprocess.Popen(["notepad", PRESETS_FILE])
        except Exception as e:
            cmds.warning("ctrl_creator_tool: cannot open file - " + str(e))


def _reload_tool(*_):
    import sys
    [sys.modules.pop(k) for k in list(sys.modules.keys()) if "ctrl_creator_tool" in k]
    import ctrl_creator_tool
    ctrl_creator_tool.show()
    print("ctrl_creator_tool: reloaded.")

# ---------------------------------------------------------------------------
# Shape 콜백
# ---------------------------------------------------------------------------
def _on_copy_shape(*_):
    global _copied_shape
    data = copy_shape_from_selection()
    if data:
        _copied_shape = data
        if _shape_label:
            cmds.text(_shape_label, e=True,
                      label="Copied ({} CVs, deg {})".format(
                          len(data["pts"]), data["degree"]))

def _on_clear_shape(*_):
    global _copied_shape
    _copied_shape = None
    if _shape_label:
        cmds.text(_shape_label, e=True, label="Circle (default)")

def _on_set_parent(*_):
    sel = cmds.ls(selection=True)
    if sel and _parent_field:
        cmds.textField(_parent_field, e=True, text=sel[0])

# ---------------------------------------------------------------------------
# Create 콜백
# ---------------------------------------------------------------------------
def _on_create(*_):
    name   = cmds.textField(_name_field,  q=True, text=True).strip() if _name_field else ""
    size   = cmds.floatField(_size_field, q=True, value=True)         if _size_field else 8.0
    parent = cmds.textField(_parent_field,q=True, text=True).strip()  if _parent_field else ""
    if not name:
        cmds.warning("ctrl_creator_tool: enter a controller name.")
        return
    create_controller(
        name=name, shape_data=_copied_shape, size=size,
        offset_suffixes=_get_offset_suffixes(),
        parent_node=parent, attr_defs=_get_attr_defs(),
        color=_current_color_idx,
    )

# ---------------------------------------------------------------------------
# Shape Tools 콜백
# ---------------------------------------------------------------------------
def _on_scale(*_):
    sx = cmds.floatField(_sc_x, q=True, value=True) if _sc_x else 1.0
    sy = cmds.floatField(_sc_y, q=True, value=True) if _sc_y else 1.0
    sz = cmds.floatField(_sc_z, q=True, value=True) if _sc_z else 1.0
    scale_shape(sx, sy, sz)

def _on_rotate(*_):
    rx = cmds.floatField(_rt_x, q=True, value=True) if _rt_x else 0.0
    ry = cmds.floatField(_rt_y, q=True, value=True) if _rt_y else 0.0
    rz = cmds.floatField(_rt_z, q=True, value=True) if _rt_z else 0.0
    rotate_shape(rx, ry, rz)

def _on_set_width(*_):
    w = cmds.floatField(_lw_f, q=True, value=True) if _lw_f else 1.0
    set_line_width(w)

# ============================================================================
# show()
# ============================================================================
def show():
    global _offset_col, _attr_col, _offset_rows, _attr_rows
    global _preset_menu, _name_field, _size_field, _parent_field
    global _color_indicator, _shape_label, _copied_shape, _current_color_idx
    global _sc_x, _sc_y, _sc_z, _rt_x, _rt_y, _rt_z, _lw_f

    if cmds.window(WIN_ID, exists=True):
        cmds.deleteUI(WIN_ID)

    _copied_shape      = None
    _current_color_idx = 6
    _offset_rows       = [{"suffix":"OS"},{"suffix":"CS"}]
    _attr_rows         = []

    win = cmds.window(WIN_ID, title="Controller Creator  v3",
                      widthHeight=(375, 680), sizeable=True,
                      resizeToFitChildren=True)
    cmds.scrollLayout(childResizable=True)
    root = cmds.columnLayout(adj=True, rowSpacing=2)

    def sec(lbl):
        cmds.separator(h=4, style="none")
        cmds.frameLayout(label=lbl, collapsable=True, collapse=False,
                         marginWidth=6, marginHeight=4)
        cmds.columnLayout(adj=True, rowSpacing=3)

    def end():
        cmds.setParent(root)

    # ── Preset ──────────────────────────────────────────────────────────
    sec("  Preset")
    cmds.rowLayout(nc=2, adjustableColumn=2, columnWidth2=[60,285])
    cmds.text(label="Preset", align="right")
    _preset_menu = cmds.optionMenu()
    cmds.setParent("..")
    cmds.rowLayout(nc=4, columnWidth4=[80,80,80,80])
    cmds.button(label="Load",     bgc=[0.2,0.4,0.2], c=_on_load_preset)
    cmds.button(label="Save As",  bgc=[0.2,0.3,0.5], c=_on_save_preset)
    cmds.button(label="Delete",   bgc=[0.5,0.2,0.2], c=_on_delete_preset)
    cmds.button(label="Open JSON",                    c=_on_open_json)
    cmds.setParent("..")
    cmds.rowLayout(nc=2, columnWidth2=[172, 172])
    cmds.button(label="Reload JSON", h=20,
                c=lambda *_: [_refresh_preset_menu(),
                              print("ctrl_creator_tool: preset reloaded.")])
    cmds.button(label="Reload Tool", h=20, bgc=[0.35,0.3,0.2], c=_reload_tool)
    cmds.setParent("..")
    end()

    # ── Controller ──────────────────────────────────────────────────────
    sec("  Controller")
    cmds.rowLayout(nc=2, adjustableColumn=2, columnWidth2=[90,255])
    cmds.text(label="Name", align="right")
    _name_field = cmds.textField(text="ctrl_L")
    cmds.setParent("..")

    # 색상 스와치 그리드 (8×4 = indices 0-31)
    cmds.text(label="Color  (click to select)", align="left")
    grid = cmds.gridLayout(numberOfColumns=16, cellWidthHeight=(22,18))
    for idx in range(32):
        rgb   = MAYA_COLOR_RGB.get(idx, (0.5,0.5,0.5))
        label = "" if idx != 0 else "∅"
        cmds.button(label=label, bgc=rgb,
                    ann="Index {}".format(idx),
                    c=lambda *a, i=idx: _on_swatch_click(i))
    cmds.setParent("..")

    cmds.rowLayout(nc=3, columnWidth3=[90,80,170])
    cmds.text(label="Selected", align="right")
    _color_indicator = cmds.button(
        label="6", width=78, height=22,
        bgc=MAYA_COLOR_RGB.get(6,(0,0,1)),
        c=lambda *_: None)
    cmds.rowLayout(nc=2, columnWidth2=[85,85])
    cmds.button(label="From Sel", c=_copy_color_from_selection)
    cmds.button(label="Set to Sel", c=_on_set_color)
    cmds.setParent("..")
    cmds.setParent("..")
    end()

    # ── Shape ───────────────────────────────────────────────────────────
    sec("  Shape")
    cmds.rowLayout(nc=2, adjustableColumn=2, columnWidth2=[90,255])
    cmds.text(label="Size (circle)", align="right")
    _size_field = cmds.floatField(value=8.0, min=0.01, max=500)
    cmds.setParent("..")
    cmds.rowLayout(nc=2, adjustableColumn=2, columnWidth2=[90,255])
    cmds.text(label="Current", align="right")
    _shape_label = cmds.text(label="Circle (default)", align="left")
    cmds.setParent("..")
    cmds.rowLayout(nc=3, columnWidth3=[118,118,110])
    cmds.button(label="Copy from Sel",  c=_on_copy_shape)
    cmds.button(label="Swap to Sel",    c=lambda *_: swap_shape())
    cmds.button(label="Clear (Circle)", c=_on_clear_shape)
    cmds.setParent("..")
    end()

    # ── Shape Tools ─────────────────────────────────────────────────────
    sec("  Shape Tools  (edit selected ctrl CVs)")

    # Scale
    cmds.rowLayout(nc=5, columnWidth5=[50,75,75,75,90])
    cmds.text(label="Scale", align="right")
    _sc_x = cmds.floatField(value=1.0, pre=3, ann="X")
    _sc_y = cmds.floatField(value=1.0, pre=3, ann="Y")
    _sc_z = cmds.floatField(value=1.0, pre=3, ann="Z")
    cmds.button(label="Apply Scale", c=_on_scale)
    cmds.setParent("..")
    cmds.rowLayout(nc=4, columnWidth4=[50,75,75,75])
    cmds.text(label="")
    for lbl in ["X","Y","Z"]:
        cmds.text(label=lbl, align="center")
    cmds.setParent("..")

    # Rotate
    cmds.rowLayout(nc=5, columnWidth5=[50,75,75,75,90])
    cmds.text(label="Rotate", align="right")
    _rt_x = cmds.floatField(value=0.0, pre=1, ann="X deg")
    _rt_y = cmds.floatField(value=0.0, pre=1, ann="Y deg")
    _rt_z = cmds.floatField(value=0.0, pre=1, ann="Z deg")
    cmds.button(label="Apply Rotate", c=_on_rotate)
    cmds.setParent("..")

    # Line Width
    cmds.rowLayout(nc=3, columnWidth3=[50,100,120])
    cmds.text(label="Width", align="right")
    _lw_f = cmds.floatField(value=1.0, min=0.1, max=20.0, pre=1)
    cmds.button(label="Apply Width", c=_on_set_width)
    cmds.setParent("..")

    # Mirror
    cmds.button(label="Mirror Shape  (_L ↔ _R)", h=26,
                bgc=[0.3,0.3,0.5], c=lambda *_: mirror_shape())
    end()

    # ── Offset Groups ───────────────────────────────────────────────────
    sec("  Offset Groups  (outer → inner)")
    cmds.rowLayout(nc=2, columnWidth2=[30,200])
    cmds.text(label="#"); cmds.text(label="Suffix")
    cmds.setParent("..")
    _offset_col = cmds.columnLayout(adj=True, rowSpacing=1)
    cmds.setParent("..")
    cmds.button(label="+ Add Group", h=22, c=_add_offset_row)
    end()

    # ── Parent ──────────────────────────────────────────────────────────
    sec("  Parent Object")
    cmds.rowLayout(nc=3, adjustableColumn=2, columnWidth3=[90,185,80])
    cmds.text(label="Parent Node", align="right")
    _parent_field = cmds.textField(text="")
    cmds.button(label="From Sel", c=_on_set_parent)
    cmds.setParent("..")
    end()

    # ── Attributes ──────────────────────────────────────────────────────
    sec("  Attributes")
    hdr = cmds.rowLayout(nc=6)
    for col, (w, lbl) in enumerate(zip(_COL_W[:6],
                                       ["Name","Type","Min/Enum","Max","Def","Key"]), 1):
        cmds.rowLayout(hdr, e=True, columnWidth=[col, w])
    for lbl in ["Name","Type","Min/Enum","Max","Def","Key"]:
        cmds.text(label=lbl, align="center")
    cmds.setParent("..")
    _attr_col = cmds.columnLayout(adj=True, rowSpacing=1)
    cmds.setParent("..")
    cmds.rowLayout(nc=2, columnWidth2=[235,110])
    cmds.button(label="Copy Selected from Channel Box",
                h=24, bgc=[0.3,0.35,0.5], c=_copy_attrs_from_channelbox)
    cmds.button(label="Clear All", h=24, bgc=[0.45,0.25,0.25],
                c=lambda *_: [_attr_rows.clear(), _rebuild_attr_rows()])
    cmds.setParent("..")
    cmds.button(label="Set Attrs to Selection",
                h=24, bgc=[0.35,0.45,0.3], c=_set_attrs_to_selection)
    end()

    # ── Create ──────────────────────────────────────────────────────────
    cmds.separator(h=8, style="none")
    cmds.button(label="Create Controller", height=40,
                bgc=[0.2,0.45,0.2], c=_on_create)
    cmds.separator(h=8, style="none")
    cmds.setParent("..")

    cmds.showWindow(win)
    _refresh_preset_menu()
    _rebuild_offset_rows()
    _rebuild_attr_rows()


if __name__ == "__main__":
    show()
