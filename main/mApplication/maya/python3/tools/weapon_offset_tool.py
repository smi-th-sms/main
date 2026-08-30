"""
Weapon Offset Controller Tool
Fingers_L / Fingers_R 아래에 weapon_offset 컨트롤러 계층 생성.

구조:
  Fingers_L
    └─ L_weapon_offset_OS   (offset group)
        └─ L_weapon_offset_CS  (constraint space)
            └─ L_weapon_offset  (controller)

사용:
    import weapon_offset_tool
    weapon_offset_tool.show()
"""

import maya.cmds as cmds

COLOR_L = 6    # 파랑
COLOR_R = 13   # 빨강
DEFAULT_SIZE = 8.0


# ---------------------------------------------------------------------------
def _detect_namespace():
    for ns in (cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []):
        if cmds.objExists(ns + ":Fingers_L"):
            return ns
    return ""


def build_weapon_offset(namespace="", side="L", size=DEFAULT_SIZE):
    """
    한쪽 weapon_offset 컨트롤러 계층 생성.
    이미 동일 이름이 있으면 Maya가 자동으로 넘버링(OS1, OS2...)함.
    """
    ns_p = namespace + ":" if namespace else ""
    fingers = ns_p + "Fingers_" + side
    color = COLOR_L if side == "L" else COLOR_R

    if not cmds.objExists(fingers):
        cmds.warning("weapon_offset_tool: {} not found.".format(fingers))
        return None

    ref_pos = cmds.xform(fingers, q=True, ws=True, t=True)
    ref_rot = cmds.xform(fingers, q=True, ws=True, ro=True)

    # ── Offset Group (OS) ──────────────────────────────────────────────────
    os_grp = cmds.group(empty=True, name=side + "_weapon_offset_OS",
                        parent=fingers)
    cmds.xform(os_grp, ws=True, t=ref_pos, ro=ref_rot)

    # ── Constraint Space Group (CS) ────────────────────────────────────────
    cs_grp = cmds.group(empty=True, name=side + "_weapon_offset_CS",
                        parent=os_grp)

    # ── Controller (nurbsCurve circle) ────────────────────────────────────
    ctrl = cmds.circle(name=side + "_weapon_offset", radius=size,
                       normalX=0, normalY=1, normalZ=0, ch=False)[0]
    cmds.parent(ctrl, cs_grp)
    cmds.xform(ctrl, os=True, t=[0, 0, 0], ro=[0, 0, 0], s=[1, 1, 1])

    # 색상 설정
    for sh in (cmds.listRelatives(ctrl, shapes=True) or []):
        cmds.setAttr(sh + ".overrideEnabled", 1)
        cmds.setAttr(sh + ".overrideColor", color)

    # shape 이름 정리
    for sh in (cmds.listRelatives(ctrl, shapes=True) or []):
        cmds.rename(sh, side + "_weapon_offsetShape")

    print("Created: {} > {} > {}".format(os_grp, cs_grp, ctrl))
    return ctrl


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
_WIN_ID = "weaponOffsetToolWin"
_tf_ns = None
_ff_size = None


def _on_build(*_):
    ns = cmds.textField(_tf_ns, q=True, text=True).strip()
    size = cmds.floatField(_ff_size, q=True, value=True)
    for side in ["L", "R"]:
        build_weapon_offset(namespace=ns, side=side, size=size)


def show():
    global _tf_ns, _ff_size

    if cmds.window(_WIN_ID, exists=True):
        cmds.deleteUI(_WIN_ID)

    win = cmds.window(_WIN_ID, title="Weapon Offset Tool",
                      widthHeight=(320, 150), resizeToFitChildren=True)
    cmds.columnLayout(adj=True, rowSpacing=4, columnOffset=["both", 8])
    cmds.separator(h=8, style="none")

    cmds.rowLayout(nc=3, adjustableColumn=2, columnWidth3=[80, 180, 55])
    cmds.text(label="Namespace")
    _tf_ns = cmds.textField(text=_detect_namespace())
    cmds.button(label="Detect",
                c=lambda *a: cmds.textField(_tf_ns, e=True,
                                            text=_detect_namespace()))
    cmds.setParent("..")

    cmds.rowLayout(nc=2, adjustableColumn=2, columnWidth2=[80, 200])
    cmds.text(label="Ctrl Size")
    _ff_size = cmds.floatField(value=DEFAULT_SIZE, min=0.1, max=100)
    cmds.setParent("..")

    cmds.separator(h=6)
    cmds.button(label="Build  L + R", height=36,
                bgc=[0.25, 0.45, 0.25], c=_on_build)
    cmds.separator(h=8, style="none")
    cmds.setParent("..")
    cmds.showWindow(win)


if __name__ == "__main__":
    show()
