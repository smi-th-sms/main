"""
Fit Connector
=============
Null 그룹과 Base Joint 간의 Matrix 기반 노드 연결 생성.

연결 구조:
    null.worldMatrix
        × joint.parentInverseMatrix[0]
        → multMatrix
        → decomposeMatrix
        → joint.translate / joint.rotate / joint.scale

이렇게 하면:
  - null 이동 → joint 가 world space 동기화
  - joint 자체가 fit controller 역할 (worldMatrix 가 downstream 드라이브)
  - 기존 node network 연결은 정리 후 null 기반으로 재연결

Usage:
    import importlib
    from python3.tools import fit_connector
    importlib.reload(fit_connector)

    # null 4개와 joint 4개를 순서대로 매핑
    mapping = [
        ("arm_r_fit_root",  "fit_arm:Scapula"),
        ("arm_r_fit_1",     "fit_arm:Shoulder"),
        ("arm_r_fit_2",     "fit_arm:Elbow"),
        ("arm_r_fit_end",   "fit_arm:Wrist"),
    ]
    fit_connector.connect_all(mapping)
"""

import maya.cmds as cmds

# 노드 이름 suffix
_MM_SUFFIX   = "_fitCtrl_MM"
_DCMX_SUFFIX = "_fitCtrl_DCMX"

# 해제할 기존 연결 어트리뷰트 목록
_DRIVEN_ATTRS = [
    "translateX", "translateY", "translateZ",
    "rotateX",    "rotateY",    "rotateZ",
    "scaleX",     "scaleY",     "scaleZ",
]


# ─────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────

def _disconnect_inputs(node, attrs):
    """node 의 지정 어트리뷰트에 걸린 기존 incoming 연결 전부 해제."""
    disconnected = []
    for attr in attrs:
        plug = node + "." + attr
        if not cmds.attributeQuery(attr, node=node, exists=True):
            continue
        conns = cmds.listConnections(plug, source=True, destination=False, plugs=True) or []
        for src in conns:
            try:
                cmds.disconnectAttr(src, plug)
                disconnected.append((src, plug))
            except Exception as e:
                cmds.warning("Disconnect failed: {} -> {} : {}".format(src, plug, e))
    return disconnected


def _safe_node_name(raw):
    """네임스페이스 콜론(:)을 언더스코어로 치환해 노드 이름 안전하게 변환."""
    return raw.replace(":", "_").replace("|", "_")


# ─────────────────────────────────────────
# Core: 단일 null → joint 연결
# ─────────────────────────────────────────

def connect_null_to_joint(null_node, joint_node,
                           mm_suffix=_MM_SUFFIX,
                           dcmx_suffix=_DCMX_SUFFIX,
                           disconnect_existing=True,
                           connect_scale=False):
    """
    null 의 worldMatrix 를 joint 의 local 공간으로 변환해 translate/rotate 를 드라이브.

    Parameters
    ----------
    null_node  : str  – 소스 null (arm_r_fit_root 등)
    joint_node : str  – 타겟 base joint (fit controller 역할)
    disconnect_existing : bool
        True 이면 joint 의 기존 translate/rotate incoming 연결 해제 후 재연결
    connect_scale : bool
        True 이면 scale 도 함께 연결

    Returns
    -------
    (mm_node, dcmx_node) : 생성된 노드 이름 튜플

    연결 다이어그램:
        null.worldMatrix[0]          → MM.matrixIn[0]
        joint.parentInverseMatrix[0] → MM.matrixIn[1]
        MM.matrixSum                 → DCMX.inputMatrix
        DCMX.outputTranslate         → joint.translate
        DCMX.outputRotate            → joint.rotate
       (DCMX.outputScale             → joint.scale)   ← connect_scale=True 일 때
    """
    if not cmds.objExists(null_node):
        cmds.warning("Fit Connector: null '{}' 가 존재하지 않습니다.".format(null_node))
        return None, None
    if not cmds.objExists(joint_node):
        cmds.warning("Fit Connector: joint '{}' 가 존재하지 않습니다.".format(joint_node))
        return None, None

    base = _safe_node_name(null_node)

    # ── multMatrix ──────────────────────
    mm_name = base + mm_suffix
    if cmds.objExists(mm_name):
        cmds.delete(mm_name)
    mm = cmds.createNode("multMatrix", name=mm_name)

    # ── decomposeMatrix ──────────────────
    dcmx_name = base + dcmx_suffix
    if cmds.objExists(dcmx_name):
        cmds.delete(dcmx_name)
    dcmx = cmds.createNode("decomposeMatrix", name=dcmx_name)

    # ── 기존 연결 해제 ────────────────────
    if disconnect_existing:
        attrs = list(_DRIVEN_ATTRS)
        if not connect_scale:
            attrs = [a for a in attrs if not a.startswith("scale")]
        old = _disconnect_inputs(joint_node, attrs)
        if old:
            print("// Fit Connector: {} 개 기존 연결 해제 ({})".format(
                len(old), joint_node))

    # ── 연결 ─────────────────────────────
    cmds.connectAttr(null_node  + ".worldMatrix[0]",           mm + ".matrixIn[0]", f=True)
    cmds.connectAttr(joint_node + ".parentInverseMatrix[0]",   mm + ".matrixIn[1]", f=True)
    cmds.connectAttr(mm         + ".matrixSum",                dcmx + ".inputMatrix", f=True)
    cmds.connectAttr(dcmx       + ".outputTranslate",          joint_node + ".translate", f=True)
    cmds.connectAttr(dcmx       + ".outputRotate",             joint_node + ".rotate",    f=True)

    if connect_scale:
        cmds.connectAttr(dcmx + ".outputScale", joint_node + ".scale", f=True)

    print("// Fit Connector: {} → {} [MM:{} DCMX:{}]".format(
        null_node, joint_node, mm, dcmx))

    return mm, dcmx


# ─────────────────────────────────────────
# 일괄 연결
# ─────────────────────────────────────────

def connect_all(mapping, connect_scale=False):
    """
    null-joint 쌍 목록을 순서대로 연결.

    Parameters
    ----------
    mapping : list of (null_node, joint_node) tuple
        순서가 중요 — parentInverseMatrix 의존성 때문에
        계층 상위(root) 부터 하위(end) 순으로 전달
    connect_scale : bool

    Returns
    -------
    list of (mm, dcmx) 튜플

    예시:
        mapping = [
            ("arm_r_fit_root", "fit_arm:Scapula"),
            ("arm_r_fit_1",    "fit_arm:Shoulder"),
            ("arm_r_fit_2",    "fit_arm:Elbow"),
            ("arm_r_fit_end",  "fit_arm:Wrist"),
        ]
        fit_connector.connect_all(mapping)
    """
    results = []
    for i, (null_node, joint_node) in enumerate(mapping):
        print("// [{}/{}] 연결 중: {} → {}".format(
            i + 1, len(mapping), null_node, joint_node))
        mm, dcmx = connect_null_to_joint(
            null_node, joint_node,
            connect_scale=connect_scale
        )
        results.append((mm, dcmx))

    cmds.dgdirty(a=True)
    cmds.refresh()
    print("// Fit Connector: 전체 {} 쌍 연결 완료".format(len(mapping)))
    return results


# ─────────────────────────────────────────
# 연결 해제 (Disconnect)
# ─────────────────────────────────────────

def disconnect_null_from_joint(null_node, joint_node,
                                mm_suffix=_MM_SUFFIX,
                                dcmx_suffix=_DCMX_SUFFIX):
    """
    connect_null_to_joint 으로 생성된 노드 연결을 해제하고 노드 삭제.
    joint 의 translate/rotate 를 0으로 초기화.
    """
    base     = _safe_node_name(null_node)
    mm_name  = base + mm_suffix
    dcmx_name = base + dcmx_suffix

    for n in [mm_name, dcmx_name]:
        if cmds.objExists(n):
            cmds.delete(n)
            print("// Fit Connector: 노드 삭제 → " + n)

    # translate/rotate 초기화
    for attr in ["translate", "rotate"]:
        try:
            cmds.setAttr(joint_node + "." + attr, 0, 0, 0)
        except Exception:
            pass

    print("// Fit Connector: 연결 해제 완료 ({} ← {})".format(joint_node, null_node))


def disconnect_all(mapping, mm_suffix=_MM_SUFFIX, dcmx_suffix=_DCMX_SUFFIX):
    """connect_all 의 역방향 — 생성된 연결 전부 해제."""
    for null_node, joint_node in mapping:
        disconnect_null_from_joint(null_node, joint_node, mm_suffix, dcmx_suffix)


# ─────────────────────────────────────────
# 연결 상태 조회
# ─────────────────────────────────────────

def inspect_connections(joint_node):
    """joint 의 현재 translate/rotate 입력 연결을 출력."""
    print("=== {} 입력 연결 ===".format(joint_node))
    for attr in ["translateX","translateY","translateZ",
                 "rotateX","rotateY","rotateZ"]:
        conns = cmds.listConnections(
            joint_node + "." + attr,
            source=True, destination=False, plugs=True
        ) or []
        if conns:
            print("  .{} ← {}".format(attr, conns[0]))


def inspect_all(mapping):
    for _null, joint in mapping:
        inspect_connections(joint)
