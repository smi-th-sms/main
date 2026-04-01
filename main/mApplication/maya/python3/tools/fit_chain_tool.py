"""
Fit Chain Tool
==============
선택 조인트 체인에 Fit 시스템(aim 구동 null + fitting ctrl + vis 커브)을 생성하고,
완료 후 null 위치/방향을 조인트에 적용한다.

노드 구조 (per null pair)
  Position : ctrl.worldMatrix × GRP.worldInverseMatrix → DC → null.translate
  Aim      : fwd_PMA (ctrl[i+1] - ctrl[i]) → side_VP → up_VP → fwd_VP → FBFM
             FBFM × GRP.worldInverseMatrix → orient_DC → null.rotate
  Up hint  : side_VP.input2 에 static 벡터 또는 dynamic VP 연결

Public API
----------
  build_aim_system(joints, settings)  -> list[str]   null 이름 목록
  remove_aim_system(grp)
  apply_fit_to_joints(joints=None)
  show()                                              debug/setup UI 진입점
"""

import math
import maya.cmds as cmds
import maya.api.OpenMaya as om


# ═══════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════

# Vis 화살표 CV (+Z 방향, length=5)
_VIS_PTS = [
    (0,0,0),(-1,0,1),(0,0,5),(0,1,1),(-1,0,1),(0,-1,1),
    (0,0,0),(1,0,1),(0,-1,1),(0,0,5),(1,0,1),(0,1,1),(0,0,0),
]
_VIS_KNOTS = list(range(13))

# Fitting ctrl CV (sphere)
_CTRL_PTS = [
    (0,1,0),(0.353553,0.707107,0.612372),(0.5,0,0.866025),
    (0.353553,-0.707107,0.612372),(0,-1,0),(-0.353553,-0.707107,0.612372),
    (-0.5,0,0.866025),(-0.353553,0.707107,0.612372),(0,1,0),
    (-0.707107,0.707107,0),(-1,0,0),(-0.707107,-0.707107,0),
    (0,-1,0),(-0.353553,-0.707107,-0.612373),(-0.5,0,-0.866026),
    (-0.353553,0.707107,-0.612373),(0,1,0),(0.353554,0.707107,-0.612372),
    (0.5,0,-0.866025),(0.353554,-0.707107,-0.612372),(0,-1,0),
    (0.707107,-0.707107,0),(0.353553,-0.707107,0.612372),
    (-0.353553,-0.707107,0.612372),(-0.707107,-0.707107,0),
    (-0.353553,-0.707107,-0.612373),(0.353554,-0.707107,-0.612372),
    (0.707107,-0.707107,0),(1,0,0),(0.5,0,-0.866025),(-0.5,0,-0.866026),
    (-1,0,0),(-0.5,0,0.866025),(0.5,0,0.866025),(1,0,0),
    (0.707107,0.707107,0),(0.353553,0.707107,0.612372),
    (-0.353553,0.707107,0.612372),(-0.707107,0.707107,0),
    (-0.353553,0.707107,-0.612373),(0.353554,0.707107,-0.612372),
    (0.707107,0.707107,0),(0,1,0),
]
_CTRL_KNOTS = list(range(43))

# Vis CV 재배치: +Z → aim 방향으로 변환
_AIM_REMAP = {
    "+X": lambda x, y, z: ( z,  y, -x),
    "-X": lambda x, y, z: (-z,  y,  x),
    "+Y": lambda x, y, z: ( x,  z, -y),
    "-Y": lambda x, y, z: ( x, -z,  y),
    "+Z": lambda x, y, z: ( x,  y,  z),
    "-Z": lambda x, y, z: (-x,  y, -z),
}

_WORLD_AXES = {
    "+X":(1,0,0), "-X":(-1,0,0),
    "+Y":(0,1,0), "-Y":(0,-1,0),
    "+Z":(0,0,1), "-Z":(0,0,-1),
}
_AX_ROW  = {"+X":0, "-X":0, "+Y":1, "-Y":1, "+Z":2, "-Z":2}
_AX_SIGN = {"+X":1, "-X":-1, "+Y":1, "-Y":-1, "+Z":1, "-Z":-1}
_AX_VEC  = {"X":(1,0,0), "Y":(0,1,0), "Z":(0,0,1)}


# ═══════════════════════════════════════════════
# Math / String Helpers
# ═══════════════════════════════════════════════

def _v3(m, row):
    b = row * 4
    return (m[b], m[b+1], m[b+2])

def _norm(v):
    mg = math.sqrt(sum(x*x for x in v))
    return tuple(x/mg for x in v) if mg > 1e-8 else (0., 1., 0.)

def _dot(a, b):
    return sum(a[i]*b[i] for i in range(3))

def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])

def _ang(a, b):
    d = max(-1., min(1., _dot(_norm(a), _norm(b))))
    return math.degrees(math.acos(d))

def _fmt(v, d=3):
    return "({:>7.{p}f}, {:>7.{p}f}, {:>7.{p}f})".format(v[0], v[1], v[2], p=d)

def _safe(s):
    """Maya 노드 이름으로 안전한 문자열 반환 (콜론/파이프 제거)."""
    return s.replace(":", "_").replace("|", "_")

def _del(n):
    if cmds.objExists(n):
        try: cmds.delete(n)
        except: pass

def _make_curve(name, pts, knots, degree=1):
    return cmds.curve(d=degree, p=list(pts), k=list(knots), name=name)


# ═══════════════════════════════════════════════
# Joint Info
# ═══════════════════════════════════════════════

def _jnt_info(j):
    wm = cmds.getAttr(j + ".worldMatrix[0]")
    ro = cmds.getAttr(j + ".rotate")[0]
    jo = (cmds.getAttr(j + ".jointOrient")[0]
          if cmds.attributeQuery("jointOrient", node=j, exists=True) else (0., 0., 0.))
    return dict(
        name      = j,
        world_pos = (wm[12], wm[13], wm[14]),
        lx        = _v3(wm, 0),
        ly        = _v3(wm, 1),
        lz        = _v3(wm, 2),
        rotate    = (round(ro[0],3), round(ro[1],3), round(ro[2],3)),
        joint_orient = (round(jo[0],3), round(jo[1],3), round(jo[2],3)),
    )

def _local_ax(info, axis_name):
    return {"X": info["lx"], "Y": info["ly"], "Z": info["lz"]}[axis_name]


# ═══════════════════════════════════════════════
# Debug Text
# ═══════════════════════════════════════════════

def _build_debug_text(joints):
    infos = [_jnt_info(j) for j in joints]
    W = 58
    lines = ["="*W, "  Fit Chain  ({} joints)".format(len(joints)), "="*W]

    for idx, info in enumerate(infos):
        lines.append("  [{:>2}] {:30s}  {}".format(
            idx, info["name"].split(":")[-1], _fmt(info["world_pos"], 2)))

    for idx in range(len(infos) - 1):
        info = infos[idx]
        nxt  = infos[idx + 1]
        aim_v = tuple(nxt["world_pos"][k] - info["world_pos"][k] for k in range(3))
        aim_n = _norm(aim_v)

        lines += ["", "  ─ pair {0}→{1} ".format(idx, idx+1) + "─"*(W-14)]

        ax_data = [("X", info["lx"]), ("Y", info["ly"]), ("Z", info["lz"])]
        aim_ax, aim_ang = min(
            [(n, _ang(v, aim_n)) for n, v in ax_data],
            key=lambda t: min(t[1], 180. - t[1]))
        sign = "+" if aim_ang < 90. else "-"
        lines.append("  Aim axis : {}{} ({:.1f}°)".format(
            sign, aim_ax, aim_ang if aim_ang < 90. else 180. - aim_ang))

        up_cands = [(n, v) for n, v in ax_data if n != aim_ax]
        lines.append("  Up candidates:")
        for ax_name, ax_vec in up_cands:
            best_w = min(_WORLD_AXES.items(), key=lambda kv: _ang(ax_vec, kv[1]))
            lines.append("    local {:1s}  ({:.1f}° from aim)  → world closest: {:>3} ({:.1f}°)".format(
                ax_name, _ang(ax_vec, aim_n), best_w[0], _ang(ax_vec, best_w[1])))

    lines += ["", "="*W]
    return "\n".join(lines)


# ═══════════════════════════════════════════════
# Up Hint (Aim System 내부)
# ═══════════════════════════════════════════════

def _up_hint_static(method, info, aim_n, settings):
    """Method B/C 의 정적 hint 벡터 반환. A/D 는 None 반환."""
    if method == "B":
        return _WORLD_AXES[settings["up_world_vec"]]
    if method == "C":
        ax_vec   = _local_ax(info, settings["up_local_axis"])
        best_ref = min(
            [(lbl, _WORLD_AXES[lbl]) for lbl in ("+X", "+Y", "+Z")],
            key=lambda kv: _ang(ax_vec, _norm(_cross(_norm(_cross(aim_n, kv[1])), aim_n)))
        )[0]
        return _WORLD_AXES[best_ref]
    return None


def _make_dynamic_hint_vp(method, ctrl, settings, all_nodes):
    """Method A/D: local axis → world 방향 추출 vectorProduct 노드 생성."""
    if method == "A":
        obj      = ctrl
        ax_name  = settings["up_local_axis"]
    elif method == "D":
        obj     = settings.get("up_object", "")
        ax_name = settings.get("up_object_axis", "Y")
        if not obj or not cmds.objExists(obj):
            return None
    else:
        return None

    vp = cmds.createNode("vectorProduct", name="{}_upHint_VP".format(_safe(ctrl)))
    cmds.setAttr(vp + ".operation", 3)
    cmds.setAttr(vp + ".normalizeOutput", True)
    cmds.setAttr(vp + ".input1", *_AX_VEC[ax_name], type="double3")
    cmds.connectAttr(obj + ".worldMatrix[0]", vp + ".matrix", f=True)
    all_nodes.append(vp)
    return vp


def _pick_fallback(primary_vec, aim_n):
    """primary_vec 및 aim_n 과 가장 수직에 가까운 world 축 반환."""
    pn   = _norm(primary_vec)
    best, best_score = (0, 0, 1), -1.
    for c in [(0,1,0), (0,0,1), (1,0,0)]:
        score = (1. - abs(_dot(c, pn))) + (1. - abs(_dot(c, aim_n)))
        if score > best_score:
            best, best_score = c, score
    return best


def _add_parallel_guard(prefix, vp_s, pma_node,
                        hint_static, hint_dyn_node,
                        fallback_vec, all_nodes):
    """
    vp_s.input2 에 평행 감지 → fallback 전환 네트워크 연결.
    threshold 0.98 (≈11.5°): hint 와 aim 이 이보다 가까우면 fallback 사용.
    """
    p = prefix

    # ── aim 벡터 zero-length 가드 ──────────────────────────────────────────
    # |aim|² = dot(pma, pma).  normalizeOutput=False — 크기만 측정, 정규화 없음
    aim_sq_vp = cmds.createNode("vectorProduct", name="{}_aimSq_VP".format(p))
    cmds.setAttr(aim_sq_vp + ".operation",       1)    # dot product
    cmds.setAttr(aim_sq_vp + ".normalizeOutput", False)
    cmds.connectAttr(pma_node + ".output3D", aim_sq_vp + ".input1", f=True)
    cmds.connectAttr(pma_node + ".output3D", aim_sq_vp + ".input2", f=True)

    # |aim|² < 1e-4 → (1,0,0) 대체, else → pma 그대로 통과
    aim_g_cond = cmds.createNode("condition", name="{}_aimG_COND".format(p))
    cmds.setAttr(aim_g_cond + ".operation",   5)        # less than
    cmds.setAttr(aim_g_cond + ".secondTerm",  1e-4)
    cmds.connectAttr(aim_sq_vp + ".outputX",  aim_g_cond + ".firstTerm", f=True)
    cmds.setAttr(aim_g_cond + ".colorIfTrue", 1.0, 0.0, 0.0, type="double3")
    for ch, ax in zip("RGB", ["output3Dx", "output3Dy", "output3Dz"]):
        cmds.connectAttr("{}.{}".format(pma_node, ax),
                         "{}.colorIfFalse{}".format(aim_g_cond, ch), f=True)

    # ── dot(guarded_aim, hint) ─────────────────────────────────────────────
    dot_vp = cmds.createNode("vectorProduct", name="{}_hintDot_VP".format(p))
    cmds.setAttr(dot_vp + ".operation",       1)
    cmds.setAttr(dot_vp + ".normalizeOutput", True)
    # pma 대신 가드된 벡터를 input1 에 연결 (zero-length 에러 방지)
    for ax, ch in zip("XYZ", "RGB"):
        cmds.connectAttr("{}.outColor{}".format(aim_g_cond, ch),
                         "{}.input1{}".format(dot_vp, ax), f=True)
    if hint_static is not None:
        cmds.setAttr(dot_vp + ".input2", *hint_static, type="double3")
    else:
        cmds.connectAttr(hint_dyn_node + ".output", dot_vp + ".input2", f=True)

    # abs(dot)
    abs_c = cmds.createNode("condition",      name="{}_absD_COND".format(p))
    neg_md = cmds.createNode("multiplyDivide", name="{}_negD_MD".format(p))
    cmds.setAttr(abs_c  + ".operation",   3)   # >=
    cmds.setAttr(abs_c  + ".secondTerm",  0.0)
    cmds.setAttr(neg_md + ".operation",   1)
    cmds.setAttr(neg_md + ".input2X",    -1.0)
    cmds.connectAttr(dot_vp + ".outputX", abs_c  + ".firstTerm",     f=True)
    cmds.connectAttr(dot_vp + ".outputX", abs_c  + ".colorIfTrueR",  f=True)
    cmds.connectAttr(dot_vp + ".outputX", neg_md + ".input1X",       f=True)
    cmds.connectAttr(neg_md + ".outputX", abs_c  + ".colorIfFalseR", f=True)

    # switch: abs_dot > 0.98 → fallback, else → hint
    sw = cmds.createNode("condition", name="{}_hintSw_COND".format(p))
    cmds.setAttr(sw + ".operation",   2)   # >
    cmds.setAttr(sw + ".secondTerm",  0.98)
    cmds.connectAttr(abs_c + ".outColorR", sw + ".firstTerm", f=True)
    cmds.setAttr(sw + ".colorIfTrue", *fallback_vec, type="double3")
    if hint_static is not None:
        cmds.setAttr(sw + ".colorIfFalse", *hint_static, type="double3")
    else:
        for rgb, xyz in zip("RGB", "XYZ"):
            cmds.connectAttr("{}.output{}".format(hint_dyn_node, xyz),
                             "{}.colorIfFalse{}".format(sw, rgb), f=True)

    for rgb, xyz in zip("RGB", "XYZ"):
        cmds.connectAttr("{}.outColor{}".format(sw, rgb),
                         "{}.input2{}".format(vp_s, xyz), f=True)

    all_nodes += [aim_sq_vp, aim_g_cond, dot_vp, abs_c, neg_md, sw]


def _make_neg_md(name, src_node, all_nodes):
    """src_node.output 을 -1 배하는 multiplyDivide 노드 생성."""
    md = cmds.createNode("multiplyDivide", name=name)
    cmds.setAttr(md + ".operation", 1)
    cmds.setAttr(md + ".input2", -1., -1., -1., type="double3")
    cmds.connectAttr(src_node + ".output", md + ".input1", f=True)
    all_nodes.append(md)
    return md


# ═══════════════════════════════════════════════
# Pole Vector Visualization
# ═══════════════════════════════════════════════

def _build_pv_visualization(grp, joints, ctrls, nulls):
    """
    3개 연속 ctrl (A, B, C) 조합마다 PV 시각화 노드 네트워크 생성.

    수식 (as_fit_tool._calc_pv_data 동일):
        ac   = C - A
        ab   = B - A
        proj = dot(ab, ac) / dot(ac, ac)  × ac
        perp = ab - proj
        pv   = B + normalize(perp) × (|AC| × 0.3)

    생성 오브젝트 (모두 grp 하위):
        {mid}_pv_null  — PV 위치 transform  (pvLocal_VP.output → translate)
        {mid}_pv_line  — 3CV linear curve V자 (CV0=null[A], CV1=pv_null, CV2=null[C])

    반환: 생성된 모든 노드 이름 리스트 (all_nodes 에 합산용)
    """
    count    = len(joints)
    pv_nodes = []

    for i in range(count - 2):
        jA, jB, jC   = joints[i], joints[i + 1], joints[i + 2]
        cA, cB, cC   = ctrls[i],  ctrls[i + 1],  ctrls[i + 2]
        null_A        = nulls[i]
        null_B        = nulls[i + 1]
        null_C        = nulls[i + 2]
        mid_name      = _safe(jB.split(":")[-1])
        p             = mid_name + "_pv"

        # ── 1. world position decompose ──
        def _wdc(ctrl, tag):
            dc = cmds.createNode("decomposeMatrix", name="{}_{}_wDC".format(p, tag))
            cmds.connectAttr(ctrl + ".worldMatrix[0]", dc + ".inputMatrix", f=True)
            return dc

        wA = _wdc(cA, "A")
        wB = _wdc(cB, "B")
        wC = _wdc(cC, "C")

        # ── 2. |AC| via distanceBetween ──
        ac_db = cmds.createNode("distanceBetween", name="{}_ac_DB".format(p))
        cmds.connectAttr(cA + ".worldMatrix[0]", ac_db + ".inMatrix1", f=True)
        cmds.connectAttr(cC + ".worldMatrix[0]", ac_db + ".inMatrix2", f=True)

        # ── 3. ac = C - A ──
        ac_pma = cmds.createNode("plusMinusAverage", name="{}_ac_PMA".format(p))
        cmds.setAttr(ac_pma + ".operation", 2)
        cmds.connectAttr(wC + ".outputTranslate", ac_pma + ".input3D[0]", f=True)
        cmds.connectAttr(wA + ".outputTranslate", ac_pma + ".input3D[1]", f=True)

        # ── 4. ab = B - A ──
        ab_pma = cmds.createNode("plusMinusAverage", name="{}_ab_PMA".format(p))
        cmds.setAttr(ab_pma + ".operation", 2)
        cmds.connectAttr(wB + ".outputTranslate", ab_pma + ".input3D[0]", f=True)
        cmds.connectAttr(wA + ".outputTranslate", ab_pma + ".input3D[1]", f=True)

        # ── 5. dot(ac, ac) = |ac|² ──
        acSq_vp = cmds.createNode("vectorProduct", name="{}_acSq_VP".format(p))
        cmds.setAttr(acSq_vp + ".operation", 1)
        cmds.connectAttr(ac_pma + ".output3D", acSq_vp + ".input1", f=True)
        cmds.connectAttr(ac_pma + ".output3D", acSq_vp + ".input2", f=True)

        # ── 6. dot(ab, ac) ──
        abac_vp = cmds.createNode("vectorProduct", name="{}_abac_VP".format(p))
        cmds.setAttr(abac_vp + ".operation", 1)
        cmds.connectAttr(ab_pma + ".output3D", abac_vp + ".input1", f=True)
        cmds.connectAttr(ac_pma + ".output3D", abac_vp + ".input2", f=True)

        # ── 7. proj_scalar = dot(ab,ac) / |ac|² ──
        proj_md = cmds.createNode("multiplyDivide", name="{}_proj_MD".format(p))
        cmds.setAttr(proj_md + ".operation", 2)   # divide
        cmds.connectAttr(abac_vp + ".outputX", proj_md + ".input1X", f=True)
        cmds.connectAttr(acSq_vp + ".outputX", proj_md + ".input2X", f=True)

        # ── 8. proj_vec = proj_scalar × ac  (scalar→ X,Y,Z 동일 연결) ──
        projVec_md = cmds.createNode("multiplyDivide", name="{}_projVec_MD".format(p))
        cmds.setAttr(projVec_md + ".operation", 1)  # multiply
        cmds.connectAttr(ac_pma + ".output3Dx", projVec_md + ".input1X", f=True)
        cmds.connectAttr(ac_pma + ".output3Dy", projVec_md + ".input1Y", f=True)
        cmds.connectAttr(ac_pma + ".output3Dz", projVec_md + ".input1Z", f=True)
        for ax in ("X", "Y", "Z"):
            cmds.connectAttr(proj_md + ".outputX", projVec_md + ".input2" + ax, f=True)

        # ── 9. perp = ab - proj_vec ──
        perp_pma = cmds.createNode("plusMinusAverage", name="{}_perp_PMA".format(p))
        cmds.setAttr(perp_pma + ".operation", 2)
        cmds.connectAttr(ab_pma   + ".output3D", perp_pma + ".input3D[0]", f=True)
        cmds.connectAttr(projVec_md + ".output", perp_pma + ".input3D[1]", f=True)

        # ── 10. normalize(perp) ─ VP op=0 + normalizeOutput ──
        perpNorm_vp = cmds.createNode("vectorProduct", name="{}_perpNorm_VP".format(p))
        cmds.setAttr(perpNorm_vp + ".operation", 0)
        cmds.setAttr(perpNorm_vp + ".normalizeOutput", True)
        cmds.connectAttr(perp_pma + ".output3D", perpNorm_vp + ".input1", f=True)

        # ── 11. pv_dist = |AC| × 0.3 ──
        scale_md = cmds.createNode("multiplyDivide", name="{}_scale_MD".format(p))
        cmds.setAttr(scale_md + ".operation", 1)
        cmds.setAttr(scale_md + ".input2X", 0.3)
        cmds.connectAttr(ac_db + ".distance", scale_md + ".input1X", f=True)

        # ── 12. pv_offset = perpNorm × pv_dist ──
        pvOff_md = cmds.createNode("multiplyDivide", name="{}_pvOff_MD".format(p))
        cmds.setAttr(pvOff_md + ".operation", 1)
        cmds.connectAttr(perpNorm_vp + ".outputX", pvOff_md + ".input1X", f=True)
        cmds.connectAttr(perpNorm_vp + ".outputY", pvOff_md + ".input1Y", f=True)
        cmds.connectAttr(perpNorm_vp + ".outputZ", pvOff_md + ".input1Z", f=True)
        for ax in ("X", "Y", "Z"):
            cmds.connectAttr(scale_md + ".outputX", pvOff_md + ".input2" + ax, f=True)

        # ── 13. pv_world = wB + pv_offset ──
        pvWorld_pma = cmds.createNode("plusMinusAverage", name="{}_pvWorld_PMA".format(p))
        cmds.setAttr(pvWorld_pma + ".operation", 1)
        cmds.connectAttr(wB       + ".outputTranslate", pvWorld_pma + ".input3D[0]", f=True)
        cmds.connectAttr(pvOff_md + ".output",          pvWorld_pma + ".input3D[1]", f=True)

        # ── 14. pv_local = pv_world × GRP.worldInverseMatrix (pointMatrixProduct) ──
        pvLocal_vp = cmds.createNode("vectorProduct", name="{}_pvLocal_VP".format(p))
        cmds.setAttr(pvLocal_vp + ".operation", 4)   # point matrix product
        cmds.setAttr(pvLocal_vp + ".normalizeOutput", False)
        cmds.connectAttr(pvWorld_pma + ".output3Dx", pvLocal_vp + ".input1X", f=True)
        cmds.connectAttr(pvWorld_pma + ".output3Dy", pvLocal_vp + ".input1Y", f=True)
        cmds.connectAttr(pvWorld_pma + ".output3Dz", pvLocal_vp + ".input1Z", f=True)
        cmds.connectAttr(grp + ".worldInverseMatrix[0]", pvLocal_vp + ".matrix", f=True)

        # ── 15. pv_null: GRP 하위 transform ──
        pv_null = mid_name + "_pv_null"
        _del(pv_null)
        pv_null = cmds.group(empty=True, name=pv_null, world=True)
        cmds.parent(pv_null, grp)
        cmds.connectAttr(pvLocal_vp + ".outputX", pv_null + ".translateX", f=True)
        cmds.connectAttr(pvLocal_vp + ".outputY", pv_null + ".translateY", f=True)
        cmds.connectAttr(pvLocal_vp + ".outputZ", pv_null + ".translateZ", f=True)

        # ── 16. 두 개의 2CV 라인: lineA (A→PV), lineC (C→PV) ──
        def _make_pv_curve(name, src_null, src_vp):
            """src_null → PV 로 이어지는 2CV linear curve 생성 (GRP 하위, 숨김)."""
            _del(name)
            crv     = cmds.curve(d=1, p=[(0,0,0),(1,0,0)], k=[0,1], name=name)
            cmds.parent(crv, grp)
            cmds.setAttr(crv + ".translate", 0, 0, 0, type="double3")
            cmds.setAttr(crv + ".rotate",    0, 0, 0, type="double3")
            cmds.setAttr(crv + ".visibility", False)          # loft 입력용, 뷰포트 숨김
            shp = cmds.listRelatives(crv, shapes=True)[0]
            cmds.setAttr(shp + ".overrideEnabled",     1)
            cmds.setAttr(shp + ".overrideDisplayType",  2)   # reference
            cmds.setAttr(shp + ".alwaysDrawOnTop",     1)
            # CV[0] ← joint null (A or C)
            cmds.connectAttr(src_null + ".translateX", shp + ".controlPoints[0].xValue", f=True)
            cmds.connectAttr(src_null + ".translateY", shp + ".controlPoints[0].yValue", f=True)
            cmds.connectAttr(src_null + ".translateZ", shp + ".controlPoints[0].zValue", f=True)
            # CV[1] ← PV local position
            cmds.connectAttr(src_vp + ".outputX", shp + ".controlPoints[1].xValue", f=True)
            cmds.connectAttr(src_vp + ".outputY", shp + ".controlPoints[1].yValue", f=True)
            cmds.connectAttr(src_vp + ".outputZ", shp + ".controlPoints[1].zValue", f=True)
            return crv

        lineA = _make_pv_curve(mid_name + "_pvA_line", null_A, pvLocal_vp)
        lineC = _make_pv_curve(mid_name + "_pvC_line", null_C, pvLocal_vp)

        # ── 17. Loft: lineA × lineC → 삼각 surface ──
        surf_name = mid_name + "_pv_surf"
        _del(surf_name)
        loft_result = cmds.loft(lineA, lineC,
                                ch=True, d=1, u=True,
                                c=False, ar=True, name=surf_name)
        pv_surf    = loft_result[0]
        loft_node  = loft_result[1]

        # surface → GRP 하이라키로 이동
        cmds.parent(pv_surf, grp)

        # draw override: reference 모드 — 뷰포트에서 선택 불가
        surf_shp = cmds.listRelatives(pv_surf, shapes=True)[0]
        cmds.setAttr(surf_shp + ".overrideEnabled",     1)
        cmds.setAttr(surf_shp + ".overrideDisplayType", 2)   # 2 = reference

        # ── 18. 머티리얼: opacity 10% 노란색 Lambert (공유, 없으면 생성) ──
        _MAT = "fitChain_pvSurf_MAT"
        _SG  = "fitChain_pvSurf_SG"
        if not cmds.objExists(_MAT):
            _m = cmds.shadingNode("lambert", asShader=True, name=_MAT)
            _s = cmds.sets(renderable=True, noSurfaceShader=True,
                           empty=True, name=_SG)
            cmds.connectAttr(_m + ".outColor", _s + ".surfaceShader", f=True)
            cmds.setAttr(_m + ".color",        1.0, 0.85, 0.0, type="double3")
            cmds.setAttr(_m + ".transparency", 0.9, 0.9,  0.9, type="double3")
        cmds.sets(pv_surf, edit=True, forceElement=_SG)

        pv_nodes += [wA, wB, wC, ac_db, ac_pma, ab_pma,
                     acSq_vp, abac_vp, proj_md, projVec_md,
                     perp_pma, perpNorm_vp, scale_md, pvOff_md,
                     pvWorld_pma, pvLocal_vp, pv_null,
                     lineA, lineC, loft_node, pv_surf]

    return pv_nodes


# ═══════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════

def build_aim_system(joints, settings):
    """
    조인트 체인에 Fit 시스템 생성.

    Parameters
    ----------
    joints   : list[str]   소스 조인트 (순서대로)
    settings : dict
        aim_axis       '+X'/'-X'/'+Y'/'-Y'/'+Z'/'-Z'
        up_axis        '+X'/'-X'/'+Y'/'-Y'/'+Z'/'-Z'
        up_method      'A'(joint axis) / 'B'(world vec) / 'C'(auto) / 'D'(object)
        up_local_axis  'X'/'Y'/'Z'   (method A/C 공용)
        up_world_vec   '+X'…'-Z'     (method B)
        up_object      str           (method D)
        up_object_axis 'X'/'Y'/'Z'   (method D)
        grp_name       str

    Returns
    -------
    list[str]  생성된 null 이름 목록 (실패 시 [])
    """
    aim_axis = settings["aim_axis"]
    up_axis  = settings["up_axis"]
    method   = settings["up_method"]
    grp      = settings["grp_name"]

    aim_row = _AX_ROW[aim_axis]
    up_row  = _AX_ROW[up_axis]
    if aim_row == up_row:
        cmds.warning("FitChain: aim_axis 와 up_axis 가 같은 행(row)입니다. 다른 축 조합을 선택하세요.")
        return []

    count = len(joints)
    if count < 2:
        cmds.warning("FitChain: 최소 2개의 조인트가 필요합니다.")
        return []

    side_row  = ({0, 1, 2} - {aim_row, up_row}).pop()
    aim_sign  = float(_AX_SIGN[aim_axis])
    up_sign   = float(_AX_SIGN[up_axis])
    # det(FBFM) = perm_sign × aim_sign × up_sign × side_sign = +1 이 되도록
    perm_sign = 1. if (up_row - aim_row) % 3 == 1 else -1.
    side_sign = perm_sign * aim_sign * up_sign

    if not cmds.objExists(grp):
        cmds.group(empty=True, name=grp, world=True)

    infos     = [_jnt_info(j) for j in joints]
    all_nodes = []
    nulls     = []

    # ── Fitting Controllers (degree-3 sphere) + Offset Group ──
    ctrls = []
    for i, jnt in enumerate(joints):
        wp0 = infos[i]["world_pos"]
        wp1 = infos[i+1]["world_pos"] if i < count-1 else infos[i-1]["world_pos"]
        dist = math.sqrt(sum((wp1[k]-wp0[k])**2 for k in range(3)))

        vis_scale  = (dist / 5.0) if dist > 1e-6 else 1.0
        ctrl_scale = vis_scale / 2.0

        jnt_name  = jnt.split(":")[-1]
        ctrl_name = "{}_ctrl".format(jnt_name)
        off_name  = "{}_ctrl_offset".format(jnt_name)
        _del(off_name)
        _del(ctrl_name)

        ctrl = _make_curve(ctrl_name, _CTRL_PTS, _CTRL_KNOTS, degree=1)
        cmds.setAttr(ctrl + ".scale", ctrl_scale, ctrl_scale, ctrl_scale, type="double3")
        cmds.makeIdentity(ctrl, apply=True, s=True)
        cmds.setAttr(ctrl + ".displayHandle", 1)
        for sh in cmds.listRelatives(ctrl, shapes=True) or []:
            cmds.setAttr(sh + ".alwaysDrawOnTop", 1)
            cmds.setAttr(sh + ".overrideEnabled", 1)
            cmds.setAttr(sh + ".overrideColor",   13)   # red

        off_grp = cmds.group(empty=True, name=off_name, world=True)
        cmds.matchTransform(off_grp, jnt)
        cmds.parent(ctrl, off_grp, r=True)
        cmds.parent(off_grp, grp)

        ctrls.append(ctrl)
        all_nodes += [off_grp, ctrl]

    # ── Null + Position chain (ctrl → GRP 공간 translate) ──
    def _null_name(i):
        return "{}_fit".format(joints[i].split(":")[-1])

    pos_dcs = []
    for i, ctrl in enumerate(ctrls):
        nn = _null_name(i)
        _del(nn)
        null = cmds.group(empty=True, name=nn, world=True)
        cmds.parent(null, grp)

        pos_mm = cmds.createNode("multMatrix",      name="{}_pos_MM".format(_safe(nn)))
        pos_dc = cmds.createNode("decomposeMatrix", name="{}_pos_DC".format(_safe(nn)))
        cmds.connectAttr(ctrl + ".worldMatrix[0]",        pos_mm + ".matrixIn[0]", f=True)
        cmds.connectAttr(grp  + ".worldInverseMatrix[0]", pos_mm + ".matrixIn[1]", f=True)
        cmds.connectAttr(pos_mm + ".matrixSum",     pos_dc + ".inputMatrix",    f=True)
        cmds.connectAttr(pos_dc + ".outputTranslate", null + ".translate",      f=True)

        all_nodes += [pos_mm, pos_dc]
        pos_dcs.append(pos_dc)
        nulls.append(null)

    # ── World position DC (aim 방향 계산용 — ctrl world 좌표) ──
    wpos_dcs = []
    for ctrl in ctrls:
        dc = cmds.createNode("decomposeMatrix", name="{}_wpos_DC".format(_safe(ctrl)))
        cmds.connectAttr(ctrl + ".worldMatrix[0]", dc + ".inputMatrix", f=True)
        wpos_dcs.append(dc)
        all_nodes.append(dc)

    # 오리엔테이션 계산 전 world position 강제 평가 (새 연결이므로 자동 dirty — global dirty 불필요)
    for dc in wpos_dcs:
        cmds.getAttr(dc + ".outputTranslate")

    # ── Orientation chain (pair i → i+1) ──
    null_to_orient_mm = {}

    for i in range(count - 1):
        null = nulls[i]
        ctrl = ctrls[i]
        info = infos[i]
        p    = _safe(null)

        raw = tuple(infos[i+1]["world_pos"][k] - info["world_pos"][k] for k in range(3))
        if math.sqrt(sum(x*x for x in raw)) < 1e-6:
            cmds.warning("FitChain: [{}]→[{}] 거리 0, aim 건너뜀.".format(joints[i], joints[i+1]))
            continue
        aim_n = _norm(raw)

        # 1. PMA: delta = pos[i+1] - pos[i]
        pma = cmds.createNode("plusMinusAverage", name="{}_fwd_PMA".format(p))
        cmds.setAttr(pma + ".operation", 2)
        cmds.connectAttr(wpos_dcs[i+1] + ".outputTranslate", pma + ".input3D[0]", f=True)
        cmds.connectAttr(wpos_dcs[i]   + ".outputTranslate", pma + ".input3D[1]", f=True)

        # 2. VP_S: side = normalize(delta × up_hint)
        vp_s = cmds.createNode("vectorProduct", name="{}_side_VP".format(p))
        cmds.setAttr(vp_s + ".operation", 2)
        cmds.setAttr(vp_s + ".normalizeOutput", True)
        cmds.connectAttr(pma + ".output3D", vp_s + ".input1", f=True)

        hint_static = _up_hint_static(method, info, aim_n, settings)
        if hint_static is not None:
            fallback = _pick_fallback(hint_static, aim_n)
            _add_parallel_guard(p, vp_s, pma, hint_static, None, fallback, all_nodes)
        else:
            hint_dyn = _make_dynamic_hint_vp(method, ctrl, settings, all_nodes)
            if hint_dyn:
                wm      = cmds.getAttr(ctrl + ".worldMatrix[0]")
                ax_row  = {"X":0, "Y":1, "Z":2}[settings.get("up_local_axis", "Y")]
                fallback = _pick_fallback(_v3(wm, ax_row), aim_n)
                _add_parallel_guard(p, vp_s, pma, None, hint_dyn, fallback, all_nodes)
            else:
                safe = (0,1,0) if abs(_dot(aim_n, (0,1,0))) < 0.98 else (0,0,1)
                cmds.setAttr(vp_s + ".input2", *safe, type="double3")

        # 3. VP_U: up = normalize(side × delta)  — reorthogonalized
        vp_u = cmds.createNode("vectorProduct", name="{}_up_VP".format(p))
        cmds.setAttr(vp_u + ".operation", 2)
        cmds.setAttr(vp_u + ".normalizeOutput", True)
        cmds.connectAttr(vp_s + ".output",  vp_u + ".input1", f=True)
        cmds.connectAttr(pma  + ".output3D", vp_u + ".input2", f=True)

        # 4. VP_F: fwd = normalize(up × side)  — normalized aim direction
        vp_f = cmds.createNode("vectorProduct", name="{}_fwd_VP".format(p))
        cmds.setAttr(vp_f + ".operation", 2)
        cmds.setAttr(vp_f + ".normalizeOutput", True)
        cmds.connectAttr(vp_u + ".output", vp_f + ".input1", f=True)
        cmds.connectAttr(vp_s + ".output", vp_f + ".input2", f=True)

        # 5. 음수 축 부호 보정
        fwd_src  = _make_neg_md("{}_negFwd_MD".format(p),  vp_f, all_nodes) if aim_sign  < 0 else vp_f
        up_src   = _make_neg_md("{}_negUp_MD".format(p),   vp_u, all_nodes) if up_sign   < 0 else vp_u
        side_src = _make_neg_md("{}_negSide_MD".format(p), vp_s, all_nodes) if side_sign < 0 else vp_s

        # 6. FBFM: 행 조립
        fbfm = cmds.createNode("fourByFourMatrix", name="{}_FBFM".format(p))
        cmds.setAttr(fbfm + ".in33", 1.0)
        for row_idx, src in ((aim_row, fwd_src), (up_row, up_src), (side_row, side_src)):
            for col_idx, comp in enumerate("XYZ"):
                cmds.connectAttr("{}.output{}".format(src, comp),
                                 "{}.in{}{}".format(fbfm, row_idx, col_idx), f=True)

        # 7. orient: FBFM × GRP_inv → decompose → null.rotate
        orient_mm = cmds.createNode("multMatrix",      name="{}_orient_MM".format(p))
        orient_dc = cmds.createNode("decomposeMatrix", name="{}_orient_DC".format(p))
        cmds.connectAttr(fbfm + ".output",               orient_mm + ".matrixIn[0]", f=True)
        cmds.connectAttr(grp  + ".worldInverseMatrix[0]", orient_mm + ".matrixIn[1]", f=True)
        cmds.connectAttr(orient_mm + ".matrixSum",  orient_dc + ".inputMatrix",  f=True)
        cmds.connectAttr(orient_dc + ".outputRotate", null + ".rotate",          f=True)

        null_to_orient_mm[null] = orient_mm
        all_nodes += [pma, vp_s, vp_u, vp_f, fbfm, orient_mm, orient_dc]

    # ── 마지막 null: ctrl world rotation 직접 사용 (aim 독립) ──
    last_null = nulls[-1]
    for src in cmds.listConnections(last_null + ".rotate", s=True, d=False, plugs=True) or []:
        try: cmds.disconnectAttr(src, last_null + ".rotate")
        except: pass
    cmds.connectAttr(pos_dcs[-1] + ".outputRotate", last_null + ".rotate", f=True)

    # ── Vis Curves (arrow, null 하위) ──
    _remap = _AIM_REMAP[aim_axis]
    for i, null in enumerate(nulls):
        wp0 = infos[i]["world_pos"]
        wp1 = infos[i+1]["world_pos"] if i < count-1 else infos[i-1]["world_pos"]
        dist      = math.sqrt(sum((wp1[k]-wp0[k])**2 for k in range(3)))
        scale_val = (dist / 5.0) if dist > 1e-6 else 1.0

        jnt_name = joints[i].split(":")[-1]
        vis_name = "{}_vis".format(jnt_name)
        _del(vis_name)

        vis = _make_curve(vis_name, [_remap(*pt) for pt in _VIS_PTS], _VIS_KNOTS)
        cmds.setAttr(vis + ".scale", scale_val, scale_val, scale_val, type="double3")
        for sh in cmds.listRelatives(vis, shapes=True) or []:
            cmds.setAttr(sh + ".overrideEnabled",     1)
            cmds.setAttr(sh + ".overrideDisplayType",  2)   # reference
            cmds.setAttr(sh + ".alwaysDrawOnTop",      1)
        cmds.parent(vis, null, r=True)    # r=True: transform 제로 유지
        cmds.makeIdentity(vis, apply=True, s=True)

        # 동적 scale (aim 축): ctrl 간 거리 / 초기 거리
        if i < count - 1 and dist > 1e-6:
            scale_attr = "scale" + aim_axis[-1]
            db = cmds.createNode("distanceBetween",  name="{}_vis_DB".format(jnt_name))
            md = cmds.createNode("multiplyDivide",   name="{}_vis_scl_MD".format(jnt_name))
            cmds.connectAttr(ctrls[i]   + ".worldMatrix[0]", db + ".inMatrix1", f=True)
            cmds.connectAttr(ctrls[i+1] + ".worldMatrix[0]", db + ".inMatrix2", f=True)
            cmds.setAttr(md + ".operation", 2)   # divide
            cmds.connectAttr(db + ".distance", md + ".input1X", f=True)
            cmds.setAttr(md + ".input2X", dist)
            cmds.connectAttr(md + ".outputX", vis + "." + scale_attr, f=True)
            all_nodes += [db, md]

        all_nodes.append(vis)

    # ── Auto Rotate Offset (matrix 기반) ──
    # M_off = R_aim_in_GRP⁻¹ × R_joint_in_GRP
    # orient_MM × M_off → rotOff_DC → null.rotate
    def _rot_only(m16):
        rows = []
        for row in range(3):
            v  = [m16[row*4+col] for col in range(3)]
            ln = math.sqrt(sum(x*x for x in v))
            if ln > 1e-8:
                v = [x/ln for x in v]
            rows.extend(v + [0.0])
        rows.extend([0.0, 0.0, 0.0, 1.0])
        return om.MMatrix(rows)

    # orient_MM 노드만 타겟 평가 — global dgdirty/refresh 불필요
    for _om_node in null_to_orient_mm.values():
        cmds.getAttr(_om_node + ".matrixSum")

    identity16 = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]

    for jnt, null in zip(joints, nulls):
        orient_mm_node = null_to_orient_mm.get(null)
        if not orient_mm_node:
            continue

        R_aim = _rot_only(cmds.getAttr(orient_mm_node + ".matrixSum"))
        R_jnt = _rot_only(list(
            om.MMatrix(cmds.getAttr(jnt + ".worldMatrix[0]")) *
            om.MMatrix(cmds.getAttr(grp + ".worldInverseMatrix[0]"))
        ))
        M_off   = R_aim.inverse() * R_jnt
        M_off16 = [M_off[i] for i in range(16)]
        if all(abs(M_off16[k] - identity16[k]) < 1e-4 for k in range(16)):
            continue

        p = _safe(null)
        for src in cmds.listConnections(null + ".rotate", s=True, d=False, plugs=True) or []:
            try: cmds.disconnectAttr(src, null + ".rotate")
            except: pass

        rot_mm = cmds.createNode("multMatrix",      name="{}_rotOff_MM".format(p))
        rot_dc = cmds.createNode("decomposeMatrix", name="{}_rotOff_DC".format(p))
        cmds.connectAttr(orient_mm_node + ".matrixSum", rot_mm + ".matrixIn[0]", f=True)
        cmds.setAttr(rot_mm + ".matrixIn[1]", M_off16, type="matrix")
        cmds.connectAttr(rot_mm + ".matrixSum",   rot_dc + ".inputMatrix",   f=True)
        cmds.connectAttr(rot_dc + ".outputRotate", null  + ".rotate",         f=True)
        all_nodes += [rot_mm, rot_dc]

    # ── Pole Vector Visualization ──
    pv_nodes = _build_pv_visualization(grp, joints, ctrls, nulls)
    all_nodes += pv_nodes

    # 생성된 노드 목록 GRP 에 저장 (remove 용)
    if not cmds.attributeQuery("_fit_nodes", node=grp, exists=True):
        cmds.addAttr(grp, ln="_fit_nodes", dt="string")
    cmds.setAttr(grp + "._fit_nodes", " ".join(all_nodes), type="string")

    cmds.refresh()
    print("// FitChain: {} nulls 생성  grp={}  aim={}  up={}  method={}".format(
        count, grp, aim_axis, up_axis, method))
    return nulls


def remove_aim_system(grp="FitChain_GRP"):
    """build_aim_system 으로 생성한 모든 노드와 GRP 를 삭제.

    노드를 한 개씩 삭제하면 VP 입력이 mid-delete 시점에 zero 로 평가돼
    zero-length vector 에러가 발생한다.
    삭제 대상 전체를 수집한 뒤 단일 cmds.delete() 로 한 번에 제거한다.
    """
    if not cmds.objExists(grp):
        return

    to_delete = []
    if cmds.attributeQuery("_fit_nodes", node=grp, exists=True):
        stored = cmds.getAttr(grp + "._fit_nodes") or ""
        to_delete.extend(n for n in stored.split() if cmds.objExists(n))

    children = cmds.listRelatives(grp, children=True, fullPath=True) or []
    to_delete.extend(ch for ch in children if cmds.objExists(ch))

    if cmds.objExists(grp):
        to_delete.append(grp)

    if to_delete:
        # normalizeOutput=True 인 VP 노드는 batch delete 중 연결이 끊기는 순간
        # zero 입력으로 재평가돼 zero-vector 에러를 유발한다.
        # 어차피 삭제할 노드이므로 삭제 전에 normalizeOutput 을 끄면 에러가 사라진다.
        for n in to_delete:
            if cmds.objExists(n) and cmds.nodeType(n) == "vectorProduct":
                try:
                    cmds.setAttr(n + ".normalizeOutput", False)
                except Exception:
                    pass
        cmds.delete(to_delete)

    print("// FitChain: 시스템 제거 완료")


def apply_fit_to_joints(joints=None):
    """
    fit null 의 world transform → joint.translate + joint.jointOrient.

    단일 패스 (root → tip 순):
      local_m = null_worldMatrix * parent_worldMatrix_inv
      → translate / rotation 모두 local_m 에서 분해 → jointOrient 설정
      → DG 강제 평가 후 다음 child 처리
    """
    _RO = {
        0: om.MEulerRotation.kXYZ, 1: om.MEulerRotation.kYZX,
        2: om.MEulerRotation.kZXY, 3: om.MEulerRotation.kXZY,
        4: om.MEulerRotation.kYXZ, 5: om.MEulerRotation.kZYX,
    }

    if joints is None:
        joints = [n for n in (cmds.ls(sl=True) or []) if cmds.nodeType(n) == "joint"]
    if not joints:
        cmds.confirmDialog(title="Apply Fit", message="조인트를 선택하세요.", button=["OK"])
        return

    pairs = []
    for jnt in joints:
        null = "{}_fit".format(jnt.split(":")[-1])
        if cmds.objExists(null):
            pairs.append((jnt, null))
        else:
            cmds.warning("FitChain apply: null 없음 — {}".format(null))

    if not pairs:
        cmds.confirmDialog(title="Apply Fit", message="대응하는 fit null 이 없습니다.", button=["OK"])
        return

    cmds.dgdirty(a=True)
    cmds.refresh()

    for jnt, null in pairs:
        null_wm = om.MMatrix(cmds.getAttr(null + ".worldMatrix[0]"))

        par = (cmds.listRelatives(jnt, parent=True, fullPath=True) or [None])[0]
        par_wm_inv = om.MMatrix(cmds.getAttr(par + ".worldMatrix[0]")).inverse() \
                     if par else om.MMatrix()

        # local_m = null_world * parent_world_inv
        # (Maya row-major: world = local * parent_world)
        local_tm = om.MTransformationMatrix(null_wm * par_wm_inv)

        t = local_tm.translation(om.MSpace.kTransform)
        cmds.setAttr(jnt + ".translate", t.x, t.y, t.z)
        cmds.setAttr(jnt + ".rotate",    0,   0,   0)

        ro    = cmds.getAttr(jnt + ".rotateOrder")
        euler = local_tm.rotation(asQuaternion=False)
        euler.reorderIt(_RO[ro])
        cmds.setAttr(jnt + ".jointOrient",
                     math.degrees(euler.x),
                     math.degrees(euler.y),
                     math.degrees(euler.z))

        cmds.getAttr(jnt + ".worldMatrix[0]")   # 다음 child 를 위해 강제 평가

    print("// FitChain: {} 조인트에 fit 적용 완료".format(len(pairs)))


def collect_null_matrices(joints):
    """각 joint 의 fit null worldMatrix 를 미리 캡처.

    dgdirty(a=True) 는 사용하지 않는다.
    전체 그래프를 dirty 마킹하면 wpos_dc 등이 기본값(0,0,0)으로
    평가되는 타이밍이 생겨 VP 노드에 zero-vector 에러가 발생한다.
    DG 연결이 유지된 상태에서 getAttr 만으로 충분히 정확한 값을 얻는다.

    Returns
    -------
    list[(jnt_name, m16_list)]  — null 이 존재하는 joint 만 포함
    """
    result = []
    for jnt in joints:
        null = "{}_fit".format(jnt.split(":")[-1])
        if cmds.objExists(null):
            result.append((jnt, list(cmds.getAttr(null + ".worldMatrix[0]"))))
        else:
            cmds.warning("FitChain collect: null 없음 — {}".format(null))
    return result


def apply_captured_matrices(joint_m16_pairs):
    """캡처된 worldMatrix 를 joint 에 적용 (null 노드 불필요).

    Parameters
    ----------
    joint_m16_pairs : list[(jnt_name, m16_list)]
        collect_null_matrices() 의 반환값을 그대로 전달.
    """
    _RO = {
        0: om.MEulerRotation.kXYZ, 1: om.MEulerRotation.kYZX,
        2: om.MEulerRotation.kZXY, 3: om.MEulerRotation.kXZY,
        4: om.MEulerRotation.kYXZ, 5: om.MEulerRotation.kZYX,
    }
    for jnt, m16 in joint_m16_pairs:
        null_wm = om.MMatrix(m16)
        par = (cmds.listRelatives(jnt, parent=True, fullPath=True) or [None])[0]
        par_wm_inv = (om.MMatrix(cmds.getAttr(par + ".worldMatrix[0]")).inverse()
                      if par else om.MMatrix())
        local_tm = om.MTransformationMatrix(null_wm * par_wm_inv)
        t = local_tm.translation(om.MSpace.kTransform)
        cmds.setAttr(jnt + ".translate", t.x, t.y, t.z)
        cmds.setAttr(jnt + ".rotate",    0,   0,   0)
        ro    = cmds.getAttr(jnt + ".rotateOrder")
        euler = local_tm.rotation(asQuaternion=False)
        euler.reorderIt(_RO[ro])
        cmds.setAttr(jnt + ".jointOrient",
                     math.degrees(euler.x),
                     math.degrees(euler.y),
                     math.degrees(euler.z))
        cmds.getAttr(jnt + ".worldMatrix[0]")   # 다음 child 를 위해 강제 평가
    print("// FitChain: {} 조인트에 fit 적용 완료".format(len(joint_m16_pairs)))


# ═══════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════

def _sel_joints():
    """현재 선택에서 joint 만 반환. 없으면 [] 와 함께 경고 다이얼로그."""
    sel = [n for n in (cmds.ls(sl=True) or []) if cmds.nodeType(n) == "joint"]
    if not sel:
        cmds.confirmDialog(title="Fit Chain Tool",
                           message="조인트를 먼저 선택하세요.", button=["OK"])
    return sel


def _show_settings_popup(joints):
    """Axis 설정 팝업 — Create 시 build_aim_system 실행."""
    WIN = "fitChainSetupWin"
    if cmds.window(WIN, exists=True):
        cmds.deleteUI(WIN)

    # Aim axis 자동 감지 (joint local 축 기준)
    if len(joints) >= 2:
        info0  = _jnt_info(joints[0])
        info1  = _jnt_info(joints[1])
        aim_v  = tuple(info1["world_pos"][k] - info0["world_pos"][k] for k in range(3))
        aim_n  = _norm(aim_v)
        ax_data = [("X", info0["lx"]), ("Y", info0["ly"]), ("Z", info0["lz"])]
        aim_ax, aim_ang = min(
            [(n, _ang(v, aim_n)) for n, v in ax_data],
            key=lambda t: min(t[1], 180. - t[1]))
        detected_aim = ("+" if aim_ang < 90. else "-") + aim_ax
    else:
        detected_aim = "+X"

    auto_grp = joints[0].split(":")[-1] + "_grp" if joints else "fit_grp"

    win = cmds.window(WIN, title="Fit Chain — Axis Setup",
                      widthHeight=(370, 320), sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6, margins=10)

    cmds.text(label="{} joints  |  {} → {}".format(
              len(joints), joints[0].split(":")[-1], joints[-1].split(":")[-1]),
              font="boldLabelFont", al="left")
    cmds.separator(h=6, st="in")

    # Aim / Up Axis
    cmds.rowLayout(nc=4, cw4=(60,80,60,80))
    cmds.text(label="Aim Axis:", al="right")
    aim_menu = cmds.optionMenu(w=75)
    for lbl in ("+X","-X","+Y","-Y","+Z","-Z"): cmds.menuItem(label=lbl)
    cmds.optionMenu(aim_menu, edit=True, value=detected_aim)
    cmds.text(label="Up Axis:", al="right")
    up_ax_menu = cmds.optionMenu(w=75)
    for lbl in ("+X","-X","+Y","-Y","+Z","-Z"): cmds.menuItem(label=lbl)
    cmds.optionMenu(up_ax_menu, edit=True, value="+Z")
    cmds.setParent("..")
    cmds.separator(h=6, st="in")

    # Up Method
    cmds.text(label="Up Method", font="smallBoldLabelFont", al="left")
    method_rbg = cmds.radioButtonGrp(
        numberOfRadioButtons=4,
        labelArray4=["A: Joint axis", "B: World vec", "C: Auto", "D: Object"],
        select=1, cw4=(88,80,68,72))
    cmds.separator(h=4, st="none")

    sub = cmds.columnLayout(adjustableColumn=True, rowSpacing=2)

    frA = cmds.rowLayout(nc=3, cw3=(120,120,120), parent=sub)
    cmds.text(label="  Joint local axis:", parent=frA)
    ax_A_menu = cmds.optionMenu(w=70, parent=frA)
    for lbl in ("X","Y","Z"): cmds.menuItem(label=lbl)
    cmds.optionMenu(ax_A_menu, edit=True, value="Z")
    cmds.text(label="", parent=frA)

    frB = cmds.rowLayout(nc=3, cw3=(120,120,120), parent=sub)
    cmds.text(label="  World direction:", parent=frB)
    ax_B_menu = cmds.optionMenu(w=70, parent=frB)
    for lbl in ("+X","-X","+Y","-Y","+Z","-Z"): cmds.menuItem(label=lbl)
    cmds.optionMenu(ax_B_menu, edit=True, value="+Y")
    cmds.text(label="", parent=frB)

    frC = cmds.rowLayout(nc=3, cw3=(120,120,120), parent=sub)
    cmds.text(label="  Joint axis ref:", parent=frC)
    ax_C_menu = cmds.optionMenu(w=70, parent=frC)
    for lbl in ("X","Y","Z"): cmds.menuItem(label=lbl)
    cmds.optionMenu(ax_C_menu, edit=True, value="Z")
    cmds.text(label="", parent=frC)

    frD = cmds.rowLayout(nc=4, cw4=(120,110,30,70), parent=sub)
    cmds.text(label="  Object:", parent=frD)
    obj_field = cmds.textField(w=105, parent=frD)
    cmds.button(label="<<", h=20, w=26, parent=frD,
                c=lambda *_: _pick_object(obj_field))
    ax_D_menu = cmds.optionMenu(w=65, parent=frD)
    for lbl in ("X","Y","Z"): cmds.menuItem(label=lbl)

    cmds.setParent("..")  # sub

    method_rows = {1: frA, 2: frB, 3: frC, 4: frD}
    def _set_method_vis(idx):
        for k, row in method_rows.items():
            try: cmds.rowLayout(row, edit=True, visible=(k == idx))
            except: pass

    _set_method_vis(1)
    cmds.radioButtonGrp(method_rbg, edit=True,
                        changeCommand=lambda *_: _set_method_vis(
                            cmds.radioButtonGrp(method_rbg, q=True, select=True)))

    cmds.separator(h=6, st="in")

    # Group
    cmds.rowLayout(nc=2, cw2=(50,280))
    cmds.text(label="Group:", al="right")
    grp_field = cmds.textField(text=auto_grp, w=275)
    cmds.setParent("..")
    cmds.separator(h=6, st="in")

    # Buttons
    cmds.rowLayout(nc=2, cw2=(180,180))
    cmds.button(label="Cancel", h=28, c=lambda *_: cmds.deleteUI(WIN))
    cmds.button(label="Create",  h=28, bgc=(0.2,0.45,0.2),
                c=lambda *_: _on_create(joints, WIN, method_rbg,
                                        aim_menu, up_ax_menu,
                                        ax_A_menu, ax_B_menu, ax_C_menu,
                                        ax_D_menu, obj_field, grp_field))
    cmds.setParent("..")
    cmds.showWindow(win)


def _pick_object(field):
    sel = cmds.ls(sl=True)
    if sel:
        cmds.textField(field, edit=True, text=sel[0])


def _on_create(joints, win_id, method_rbg,
               aim_menu, up_ax_menu,
               ax_A_menu, ax_B_menu, ax_C_menu,
               ax_D_menu, obj_field, grp_field):
    method_idx = cmds.radioButtonGrp(method_rbg, q=True, select=True)
    method     = ("A","B","C","D")[method_idx - 1]

    # method A/C 모두 up_local_axis 키 사용 (C 는 ax_C_menu)
    up_local = cmds.optionMenu(ax_C_menu if method == "C" else ax_A_menu, q=True, v=True)

    settings = dict(
        aim_axis       = cmds.optionMenu(aim_menu,    q=True, v=True),
        up_axis        = cmds.optionMenu(up_ax_menu,  q=True, v=True),
        up_method      = method,
        up_local_axis  = up_local,
        up_world_vec   = cmds.optionMenu(ax_B_menu,   q=True, v=True),
        up_object      = cmds.textField(obj_field,    q=True, tx=True).strip(),
        up_object_axis = cmds.optionMenu(ax_D_menu,   q=True, v=True),
        grp_name       = cmds.textField(grp_field,    q=True, tx=True).strip(),
    )
    cmds.deleteUI(win_id)
    nulls = build_aim_system(joints, settings)
    if nulls:
        cmds.select(nulls)


def _find_fit_grps():
    """씬에서 _fit_nodes 속성을 가진 GRP 노드 목록 반환."""
    return [n for n in (cmds.ls(type="transform") or [])
            if cmds.attributeQuery("_fit_nodes", node=n, exists=True)]


def _on_remove_fit():
    """선택 또는 씬 내 fit GRP 를 감지해 제거."""
    # 선택 노드 중 _fit_nodes 속성 보유한 것 우선
    sel_grps = [n for n in (cmds.ls(sl=True, type="transform") or [])
                if cmds.attributeQuery("_fit_nodes", node=n, exists=True)]
    if sel_grps:
        for grp in sel_grps:
            remove_aim_system(grp)
        return

    # 씬 전체 검색
    all_grps = _find_fit_grps()
    if not all_grps:
        cmds.confirmDialog(title="Remove Fit", button=["OK"],
                           message="제거할 Fit 시스템을 찾을 수 없습니다.\n"
                                   "GRP 노드를 선택하거나 씬에 Fit 시스템이 있는지 확인하세요.")
        return

    if len(all_grps) == 1:
        result = cmds.confirmDialog(
            title="Remove Fit",
            message="Fit 시스템을 제거합니다:\n  {}".format(all_grps[0]),
            button=["Remove", "Cancel"], defaultButton="Remove", cancelButton="Cancel")
        if result == "Remove":
            remove_aim_system(all_grps[0])
        return

    # 여러 개 → 선택 팝업
    WIN = "fitChainRemoveWin"
    if cmds.window(WIN, exists=True):
        cmds.deleteUI(WIN)
    w = cmds.window(WIN, title="Remove Fit System", widthHeight=(300, 160), sizeable=False)
    cmds.columnLayout(adjustableColumn=True, margins=10, rowSpacing=6)
    cmds.text(label="제거할 GRP 를 선택하세요:", al="left")
    grp_menu = cmds.optionMenu(w=280)
    for g in all_grps:
        cmds.menuItem(label=g)
    cmds.separator(h=6, st="in")
    cmds.rowLayout(nc=2, cw2=(140,140))
    cmds.button(label="Cancel", h=28, c=lambda *_: cmds.deleteUI(WIN))
    cmds.button(label="Remove", h=28, bgc=(0.5,0.2,0.2),
                c=lambda *_: (_do_remove(cmds.optionMenu(grp_menu, q=True, v=True)),
                               cmds.deleteUI(WIN)))
    cmds.setParent("..")
    cmds.showWindow(w)


def _do_remove(grp):
    remove_aim_system(grp)


def show():
    """Joint Axis Debug 창 열기 (메인 진입점)."""
    sel = _sel_joints()
    if not sel:
        return

    WIN = "fitChainDebugWin"
    if cmds.window(WIN, exists=True):
        cmds.deleteUI(WIN)

    win = cmds.window(WIN, title="Joint Axis Debug",
                      widthHeight=(620, 630), sizeable=True)
    cmds.columnLayout(adjustableColumn=True)
    sf = cmds.scrollField(text=_build_debug_text(sel),
                          editable=False, wordWrap=False,
                          font="fixedWidthFont", width=610, height=540)
    cmds.rowLayout(nc=4, cw4=(150,150,150,150))
    cmds.button(label="Close",              h=28,
                c=lambda *_: cmds.deleteUI(WIN))
    cmds.button(label="Refresh",            h=28, bgc=(0.25,0.38,0.25),
                c=lambda *_: _on_refresh(sf))
    cmds.button(label="Next: Axis Setup ▶",  h=28, bgc=(0.22,0.32,0.50),
                c=lambda *_: _on_open_setup(sf))
    cmds.button(label="Apply Fit → Joints",  h=28, bgc=(0.45,0.25,0.25),
                c=lambda *_: apply_fit_to_joints(None))
    cmds.setParent("..")
    cmds.rowLayout(nc=2, cw2=(300,300))
    cmds.button(label="Mirror → Opposite Side (YZ)",  h=28, bgc=(0.25,0.35,0.50),
                c=lambda *_: _on_mirror_fit(None))
    cmds.button(label="Remove Fit System",            h=28, bgc=(0.35,0.18,0.18),
                c=lambda *_: _on_remove_fit())
    cmds.setParent("..")
    cmds.showWindow(win)


def _on_refresh(sf):
    sel = _sel_joints()
    if sel:
        cmds.scrollField(sf, edit=True, text=_build_debug_text(sel))


def _on_open_setup(sf):
    sel = _sel_joints()
    if sel:
        cmds.scrollField(sf, edit=True, text=_build_debug_text(sel))
        _show_settings_popup(sel)


# ═══════════════════════════════════════════════
# Mirror
# ═══════════════════════════════════════════════

# across 평면 → (flip 컬럼, rot row1, rot row2) 매핑
# _mirror.py setMatrixAxis_/setMatrixRot_ 로직과 동일
_MIRROR_ACROSS = {
    "yz": (0, 0, 1),   # YZ 평면 (X 반전): flip col0, negate row0, negate row1
    "xz": (1, 1, 0),   # XZ 평면 (Y 반전): flip col1, negate row1, negate row0
    "xy": (2, 2, 0),   # XY 평면 (Z 반전): flip col2, negate row2, negate row0
}


def _find_opposite_joint(name):
    """joint 이름에서 side suffix/infix 를 감지해 반대편 전체 이름 반환.
    _l / _r  |  _L / _R  |  _l_ / _r_  패턴 지원.
    반환: 반대편 전체 이름(str) 또는 None."""
    short = name.split(":")[-1]
    if   short.endswith("_l"):  opp = short[:-2] + "_r"
    elif short.endswith("_r"):  opp = short[:-2] + "_l"
    elif short.endswith("_L"):  opp = short[:-2] + "_R"
    elif short.endswith("_R"):  opp = short[:-2] + "_L"
    elif "_l_" in short: opp = short.replace("_l_", "_r_", 1)
    elif "_r_" in short: opp = short.replace("_r_", "_l_", 1)
    else: return None
    ns = name.split(":")[0] if ":" in name else None
    return (ns + ":" + opp) if ns else opp


_RO_OM = {
    0: om.MEulerRotation.kXYZ, 1: om.MEulerRotation.kYZX,
    2: om.MEulerRotation.kZXY, 3: om.MEulerRotation.kXZY,
    4: om.MEulerRotation.kYXZ, 5: om.MEulerRotation.kZYX,
}


def _flip_col(m16, col):
    """setMatrixAxis_ 등가: 월드 매트릭스 우측 곱 (col 반전) → 새 리스트 반환."""
    result = list(m16)
    for row in range(4):
        result[row * 4 + col] *= -1.0
    return result


def _negate_row(m16, row):
    """setMatrixRot_ 등가: rotation row 부호 반전 (in-place 수정 후 반환)."""
    for col in range(3):
        m16[row * 4 + col] *= -1.0
    return m16


def _apply_world_m16_to_joint(jnt, m16, par_path):
    """월드 매트릭스(리스트) → joint translate / jointOrient 적용."""
    wm = om.MMatrix(m16)
    par_inv = (om.MMatrix(cmds.getAttr(par_path + ".worldMatrix[0]")).inverse()
               if par_path else om.MMatrix())
    local_tm = om.MTransformationMatrix(wm * par_inv)
    t = local_tm.translation(om.MSpace.kTransform)
    cmds.setAttr(jnt + ".translate", t.x, t.y, t.z)
    cmds.setAttr(jnt + ".rotate",    0,   0,   0)
    ro    = cmds.getAttr(jnt + ".rotateOrder")
    euler = local_tm.rotation(asQuaternion=False)
    euler.reorderIt(_RO_OM[ro])
    cmds.setAttr(jnt + ".jointOrient",
                 math.degrees(euler.x),
                 math.degrees(euler.y),
                 math.degrees(euler.z))
    cmds.getAttr(jnt + ".worldMatrix[0]")   # 강제 DG 평가


def mirror_to_opposite_side(joints=None, across="yz"):
    """
    _mirror.py topSelectMirror_ 와 동일한 3단계 알고리즘으로
    반대편 side 조인트에 mirror 값 적용.

    across : 'yz'(기본, YZ 평면·X 반전) / 'xz'(XZ 평면) / 'xy'(XY 평면)

    Step 1  setMatrixAxis_ 등가 — 소스 월드 매트릭스 컬럼 반전 (위치 포함)
    Step 2  setMatrixRot_  등가 — 결과 월드 매트릭스 rot_row1 부호 반전 (in-place)
    Step 3  setMatrixRot_  등가 — 동일 매트릭스에 rot_row2 추가 부호 반전
    """
    if joints is None:
        joints = [n for n in (cmds.ls(sl=True) or []) if cmds.nodeType(n) == "joint"]
    if not joints:
        cmds.confirmDialog(title="Mirror Fit",
                           message="조인트를 선택하세요.", button=["OK"])
        return

    flip_col, rot_row1, rot_row2 = _MIRROR_ACROSS[across]
    cmds.dgdirty(a=True)
    cmds.refresh()

    done, skipped = [], []
    for jnt in joints:
        opp = _find_opposite_joint(jnt)
        if not opp or not cmds.objExists(opp):
            skipped.append(jnt)
            continue

        par = (cmds.listRelatives(opp, parent=True, fullPath=True) or [None])[0]

        # Step 1: flip col (setMatrixAxis_ 등가) — 새 리스트
        W1 = _flip_col(cmds.getAttr(jnt + ".worldMatrix[0]"), flip_col)
        _apply_world_m16_to_joint(opp, W1, par)
        cmds.dgdirty(a=True)

        # Step 2: 현재 월드 매트릭스 취득 후 rot_row1 반전 (in-place)
        W2 = list(cmds.getAttr(opp + ".worldMatrix[0]"))
        _negate_row(W2, rot_row1)
        _apply_world_m16_to_joint(opp, W2, par)
        cmds.dgdirty(a=True)

        # Step 3: 동일 W2 (이미 rot_row1 반전됨)에 rot_row2 추가 반전
        _negate_row(W2, rot_row2)
        _apply_world_m16_to_joint(opp, W2, par)

        done.append((jnt, opp))

    print("// FitChain Mirror ({}): {} pairs applied".format(across.upper(), len(done)))
    for s, d in done:
        print("   {} -> {}".format(s, d))
    if skipped:
        cmds.warning("FitChain Mirror: opposite not found — " + ", ".join(skipped))


def _on_mirror_fit(joints):
    """UI Mirror 버튼 콜백."""
    mirror_to_opposite_side(joints, across="yz")


if __name__ == "__main__":
    show()
