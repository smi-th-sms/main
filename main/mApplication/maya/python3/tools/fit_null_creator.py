"""
Fit Null Creator
================
선택한 N개의 조인트 트랜스폼 기준으로 Fit Null 그룹을 생성.

- 선택 순서: fit_root(0) → fit_1(1) → fit_2(2) → fit_end(N-1)
- 각 null은 선택 조인트의 world position + rotation 을 그대로 복사
- 생성된 null은 FitChain_GRP 아래 계층 없이 flat 하게 배치

Usage:
    import importlib
    from python3.tools import fit_null_creator
    importlib.reload(fit_null_creator)
    fit_null_creator.create_from_selection()
"""

import maya.cmds as cmds

_FIT_ROOT_NAME = "FitChain_GRP"

_NULL_LABELS = ["fit_root", "fit_1", "fit_2", "fit_end"]


def _null_name(index, total, source_joint, prefix=""):
    """
    인덱스 기반 null 이름 결정.
      0        → fit_root
      total-1  → fit_end
      나머지    → fit_1, fit_2 ...
    prefix 가 있으면 앞에 붙임.
    """
    if index == 0:
        base = "fit_root"
    elif index == total - 1:
        base = "fit_end"
    else:
        base = "fit_{}".format(index)

    return (prefix + "_" + base) if prefix else base


def create_from_selection(prefix="", group_name=_FIT_ROOT_NAME):
    """
    현재 선택된 조인트(또는 트랜스폼) 순서대로 Fit Null 을 생성.

    Parameters
    ----------
    prefix : str
        null 이름 앞에 붙을 접두사. 예) "arm_r" → "arm_r_fit_root"
    group_name : str
        생성된 null 들을 담을 최상위 그룹 이름.

    Returns
    -------
    list[str]
        생성된 null 노드 이름 목록
    """
    sel = cmds.ls(sl=True, long=False) or []
    if len(sel) < 2:
        cmds.warning("Fit Null Creator: 조인트를 2개 이상 선택하세요. (권장: 4개)")
        return []

    total = len(sel)
    print("// Fit Null Creator: {} 개 소스 → {} 개 null 생성".format(total, total))

    # FitChain_GRP 생성 또는 재사용
    if cmds.objExists(group_name):
        # 기존 null 정리
        old_children = cmds.listRelatives(group_name, children=True) or []
        if old_children:
            cmds.delete(old_children)
        print("// Fit Null Creator: 기존 '{}' 내용 삭제 후 재생성".format(group_name))
    else:
        cmds.group(empty=True, name=group_name, world=True)

    created = []

    for i, src in enumerate(sel):
        null_name = _null_name(i, total, src, prefix)

        # 이미 존재하면 삭제
        if cmds.objExists(null_name):
            cmds.delete(null_name)

        # null (빈 transform) 생성
        null = cmds.group(empty=True, name=null_name, world=True)

        # 소스 조인트의 world matrix 복사 (position + rotation)
        ws_pos = cmds.xform(src, q=True, ws=True, t=True)
        ws_rot = cmds.xform(src, q=True, ws=True, ro=True)

        cmds.xform(null, ws=True, t=ws_pos)
        cmds.xform(null, ws=True, ro=ws_rot)

        # 그룹 아래로 이동
        cmds.parent(null, group_name)

        created.append(null)
        print("// [{}/{}] {} → {} pos:{} rot:{}".format(
            i + 1, total, src, null_name,
            [round(v, 3) for v in ws_pos],
            [round(v, 3) for v in ws_rot]
        ))

    cmds.select(created, r=True)
    print("// Fit Null Creator: 완료 → " + str(created))
    return created


def show():
    """선택 기반으로 바로 실행."""
    sel = cmds.ls(sl=True) or []
    if len(sel) != 4:
        cmds.confirmDialog(
            title="Fit Null Creator",
            message="조인트 4개를 순서대로 선택 후 실행하세요.\n(현재 선택: {}개)".format(len(sel)),
            button=["OK"]
        )
        return
    return create_from_selection()
