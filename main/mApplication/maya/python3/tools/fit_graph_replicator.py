"""
Fit Graph Replicator
====================
fit_arm 리그의 FitController → FitInit 사이 전체 노드 그래프를
재귀적으로 분석하고 완전 복제.

새 그래프 (fit_arm 없이 독립 동작):
    testScapula/Shoulder/Elbow/Wrist
        → (복제된 math 노드 네트워크)
        → arm_r_fit_root / arm_r_fit_1 / arm_r_fit_2 / arm_r_fit_end

Usage:
    import importlib
    from python3.tools import fit_graph_replicator as fgr
    importlib.reload(fgr)
    fgr.build()
"""

import maya.cmds as cmds

# ─────────────────────────────────────────────────────────────
# 노드 매핑 정의
# ─────────────────────────────────────────────────────────────

# 기존 FitGuide → 새 컨트롤러 조인트
SRC_MAP = {
    "fit_arm:FitScapula":  "testScapula",
    "fit_arm:FitShoulder": "testShoulder",
    "fit_arm:FitElbow":    "testElbow",
    "fit_arm:FitWrist":    "testWrist",
}

# 기존 FitInit → 새 null 그룹
TGT_MAP = {
    "fit_arm:FitInitScapula":  "arm_r_fit_root",
    "fit_arm:FitInitShoulder": "arm_r_fit_1",
    "fit_arm:FitInitElbow":    "arm_r_fit_2",
    "fit_arm:FitInitWrist":    "arm_r_fit_end",
}

# 기존 rig 내부 DAG 노드 → 새 노드
#   FitArmSpace : FitScapula 위치를 그대로 쓰는 pass-through
#   FitArm / JntGrp : 루트 그룹 (FitChain_GRP 로 통일)
#   Scapula/Shoulder/Elbow/Wrist : 출력 조인트 → null 그룹으로 대체
DAG_MAP = {
    "fit_arm:FitArmSpace": "testScapula",
    "fit_arm:FitArm":      "FitChain_GRP",
    "fit_arm:JntGrp":      "FitChain_GRP",
    "fit_arm:Scapula":     "arm_r_fit_root",
    "fit_arm:Shoulder":    "arm_r_fit_1",
    "fit_arm:Elbow":       "arm_r_fit_2",
    "fit_arm:Wrist":       "arm_r_fit_end",
}

# JNT 체인: 실제 조인트 로컬 포지션을 계산하는 노드 — 새 그래프에서 불필요
# (null 그룹은 world space 로 바로 구동)
JNT_CHAIN = {
    "fit_arm:temp_scapula_MTMX",       "fit_arm:temp_scapula_DCMX",
    "fit_arm:shoulder_JNT_MTMX",       "fit_arm:shoulder_JNT_DCMX",
    "fit_arm:shoulder2elbow_JNT_MTMX", "fit_arm:shoulder2elbow_JNT_DCMX",
}

# 스킵할 어트리뷰트 패턴 (AS 트래킹 / 조인트 전용)
SKIP_ATTR_PATTERNS = ["fitControl", ".init[", "tempJoint", "inverseScale"]

# jointOrient → rotate 리매핑 (조인트 어트리뷰트 → transform 어트리뷰트)
ATTR_REMAP = {"jointOrient": "rotate"}

# 새 노드 이름 prefix
_PREFIX = "fc"


# ─────────────────────────────────────────────────────────────
# Step 1: 재귀 그래프 수집
# ─────────────────────────────────────────────────────────────

def collect_graph(sources, targets):
    """
    targets 에서 역방향 BFS 로 sources 까지 전체 노드/연결 수집.

    Returns
    -------
    intermediate : list[(node, type)]  – utility 중간 노드 목록
    all_conns    : list[(src_plug, dst_plug)]
    """
    sources_set = set(sources)
    visited = set(targets)
    queue = list(targets)
    intermediate = []
    all_conns = []

    while queue:
        node = queue.pop(0)
        conns = cmds.listConnections(node, s=True, d=False,
                                     plugs=True, c=True) or []
        for i in range(0, len(conns) - 1, 2):
            dst_plug = conns[i]
            src_plug = conns[i + 1]
            src_node = src_plug.split(".")[0]

            # fit_arm 네임스페이스 내 노드만 포함
            if "fit_arm:" not in src_node and src_node not in sources_set:
                continue

            all_conns.append((src_plug, dst_plug))

            if src_node not in visited:
                visited.add(src_node)
                if src_node not in sources_set:
                    queue.append(src_node)
                    intermediate.append((src_node, cmds.nodeType(src_node)))

    return intermediate, all_conns


# ─────────────────────────────────────────────────────────────
# Step 2: 노드 생성 + 어트리뷰트 복사
# ─────────────────────────────────────────────────────────────

def _copy_node_attrs(src, dst, node_type):
    """노드 타입별 operation / 파라미터 어트리뷰트 복사."""
    op_types = {
        "multiplyDivide":   ["operation"],
        "plusMinusAverage": ["operation"],
        "condition":        ["operation", "secondTerm"],
        "vectorProduct":    ["operation", "normalizeOutput"],
        "blendColors":      ["blender"],
    }
    for attr in op_types.get(node_type, []):
        try:
            val = cmds.getAttr("{}.{}".format(src, attr))
            cmds.setAttr("{}.{}".format(dst, attr), val)
        except Exception:
            pass

    # condition 컬러 값 복사 (colorIfTrue / colorIfFalse 의 static 값)
    if node_type == "condition":
        for ca in ["colorIfTrue", "colorIfFalse"]:
            try:
                conns = cmds.listConnections("{}.{}".format(src, ca),
                                             s=True, d=False, plugs=True) or []
                if not conns:  # 연결 없으면 static 값 복사
                    val = cmds.getAttr("{}.{}".format(src, ca))
                    if val:
                        r, g, b = val[0]
                        cmds.setAttr("{}.{}".format(dst, ca), r, g, b,
                                     type="double3")
            except Exception:
                pass


def create_utility_nodes(intermediate, prefix=_PREFIX):
    """
    중간 utility 노드를 생성하고 {old_name: new_name} 맵 반환.
    DAG 노드(transform/joint)는 생성하지 않음.
    """
    node_map = {}
    dag_types = {"transform", "joint"}

    for old_node, node_type in intermediate:
        if node_type in dag_types:
            continue  # DAG 노드는 매핑 테이블로 처리

        base  = old_node.split(":")[-1]
        new_name = "{}_{}".format(prefix, base)

        if cmds.objExists(new_name):
            cmds.delete(new_name)

        new_node = cmds.createNode(node_type, name=new_name)
        _copy_node_attrs(old_node, new_node, node_type)
        node_map[old_node] = new_node
        print("// Created: {} ({})".format(new_name, node_type))

    return node_map


# ─────────────────────────────────────────────────────────────
# Step 3: FitChain_GRP 커스텀 어트리뷰트 (미러 설정)
# ─────────────────────────────────────────────────────────────

def _setup_fitchain_grp_attrs(src_fitarm="fit_arm:FitArm",
                               dst_grp="FitChain_GRP"):
    """
    FitArm 의 mirror / leftDirect / rightDirect 커스텀 어트리뷰트를
    FitChain_GRP 에 복제.
    """
    if not cmds.objExists(dst_grp):
        return

    attr_defs = [
        ("mirror",      "long",    None),
        ("leftDirect",  "double3", ["leftDirectX","leftDirectY","leftDirectZ"]),
        ("rightDirect", "double3", ["rightDirectX","rightDirectY","rightDirectZ"]),
    ]

    for attr_name, attr_type, children in attr_defs:
        full = "{}.{}".format(dst_grp, attr_name)
        if cmds.attributeQuery(attr_name, node=dst_grp, exists=True):
            continue

        if attr_type == "long":
            cmds.addAttr(dst_grp, ln=attr_name, at="long", dv=0, k=True)
        elif attr_type == "double3":
            cmds.addAttr(dst_grp, ln=attr_name, at="double3", k=True)
            for child in children:
                cmds.addAttr(dst_grp, ln=child, at="double", parent=attr_name, k=True)

        # 기존 fit_arm:FitArm 값 복사
        if cmds.objExists(src_fitarm):
            try:
                src_attr = "{}.{}".format(src_fitarm, attr_name)
                conns = cmds.listConnections(src_attr, s=True, d=False,
                                              plugs=True) or []
                if not conns:
                    val = cmds.getAttr(src_attr)
                    if isinstance(val, list):
                        val = val[0]
                    if isinstance(val, (list, tuple)):
                        cmds.setAttr(full, *val, type="double3")
                    else:
                        cmds.setAttr(full, val)
            except Exception:
                pass

    print("// FitChain_GRP 커스텀 어트리뷰트 설정 완료")


# ─────────────────────────────────────────────────────────────
# Step 4: 연결 재배선
# ─────────────────────────────────────────────────────────────

def _should_skip(src_plug, dst_plug):
    """연결을 스킵해야 하면 True."""
    src_node = src_plug.split(".")[0]
    dst_node = dst_plug.split(".")[0]
    src_attr = src_plug.split(".", 1)[1]
    dst_attr = dst_plug.split(".", 1)[1]

    # JNT 체인 노드 포함 연결 제외
    if src_node in JNT_CHAIN or dst_node in JNT_CHAIN:
        return True

    # 트래킹/조인트 전용 어트리뷰트
    combined = src_attr + dst_attr
    for pat in SKIP_ATTR_PATTERNS:
        if pat in combined:
            return True

    return False


def _remap_plug(plug, full_node_map):
    """플러그(node.attr)의 노드 부분을 새 이름으로 치환."""
    dot = plug.index(".")
    node = plug[:dot]
    attr = plug[dot + 1:]

    new_node = full_node_map.get(node, node)

    # jointOrient → rotate 리매핑
    for old_a, new_a in ATTR_REMAP.items():
        if attr == old_a or attr.startswith(old_a + "["):
            attr = attr.replace(old_a, new_a, 1)
            break

    return new_node + "." + attr, new_node


def rewire_connections(all_conns, full_node_map):
    """수집된 연결 목록을 새 노드 맵으로 재배선."""
    success = 0
    skipped = 0
    failed  = []

    for src_plug, dst_plug in all_conns:
        if _should_skip(src_plug, dst_plug):
            skipped += 1
            continue

        new_src, new_src_node = _remap_plug(src_plug, full_node_map)
        new_dst, new_dst_node = _remap_plug(dst_plug, full_node_map)

        # 자기 참조 스킵
        if new_src_node == new_dst_node:
            skipped += 1
            continue

        # 노드 존재 확인
        if not cmds.objExists(new_src_node):
            failed.append("SRC NOT FOUND: " + new_src_node)
            continue
        if not cmds.objExists(new_dst_node):
            failed.append("DST NOT FOUND: " + new_dst_node)
            continue

        try:
            if not cmds.isConnected(new_src, new_dst):
                cmds.connectAttr(new_src, new_dst, force=True)
            success += 1
        except Exception as e:
            failed.append("FAIL {} >> {} : {}".format(new_src, new_dst, str(e)))

    print("// 연결 완료: {}  스킵: {}  실패: {}".format(success, skipped, len(failed)))
    for f in failed:
        print("  " + f)


# ─────────────────────────────────────────────────────────────
# Step 5: null 그룹 계층 구성
# ─────────────────────────────────────────────────────────────

def _setup_null_hierarchy():
    """
    TGT_MAP 순서대로 null 그룹을 체인 계층으로 배치.
    원본 FitInit 체인(FitInitScapula→…→FitInitWrist)과 동일한 구조.
    math 노드가 각 null 의 worldInverseMatrix 를 부모 기준으로 계산하므로
    계층이 맞아야 offset 값이 정상 적용됨.
    """
    nulls = list(TGT_MAP.values())   # [root, 1, 2, end] 순서
    for i in range(len(nulls) - 1, 0, -1):
        child  = nulls[i]
        parent = nulls[i - 1]
        current_parent = (cmds.listRelatives(child, parent=True) or [None])[0]
        if current_parent != parent:
            cmds.parent(child, parent)
            print("// Hierarchy: {} → {}".format(child, parent))
    print("// null 그룹 계층 구성 완료")


# ─────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────

def build(prefix=_PREFIX):
    """
    전체 그래프 복제 실행.

    1. fit_arm:FitScapula~FitWrist → fit_arm:FitInit* 사이 그래프 수집
    2. utility 노드 생성
    3. FitChain_GRP 커스텀 어트리뷰트 설정
    4. 연결 재배선
    5. null 그룹 체인 계층 구성
    """
    sources = list(SRC_MAP.keys())
    targets = list(TGT_MAP.keys())

    # 전제 조건 확인
    missing = [n for n in sources + targets + list(DAG_MAP.keys())
               if not cmds.objExists(n)]
    if missing:
        cmds.warning("Fit Graph Replicator: 다음 노드가 없습니다:\n" +
                     "\n".join(missing))
        return

    new_nulls = list(TGT_MAP.values())
    missing_nulls = [n for n in new_nulls if not cmds.objExists(n)]
    if missing_nulls:
        cmds.warning("Fit Graph Replicator: null 그룹이 없습니다:\n" +
                     "\n".join(missing_nulls))
        return

    print("// ── Fit Graph Replicator 시작 ──")

    # Step 1: 그래프 수집
    intermediate, all_conns = collect_graph(sources, targets)
    print("// 수집: 중간 노드 {}개, 연결 {}개".format(len(intermediate), len(all_conns)))

    # Step 2: utility 노드 생성
    util_map = create_utility_nodes(intermediate, prefix)

    # Step 3: FitChain_GRP 커스텀 어트리뷰트
    _setup_fitchain_grp_attrs()

    # Step 4: 전체 노드 맵 합성
    full_map = {}
    full_map.update(SRC_MAP)
    full_map.update(TGT_MAP)
    full_map.update(DAG_MAP)
    full_map.update(util_map)

    # Step 5: 연결 재배선
    rewire_connections(all_conns, full_map)

    # Step 6: null 그룹 계층 구성 (FitInit 체인과 동일하게)
    _setup_null_hierarchy()

    cmds.dgdirty(a=True)
    cmds.refresh()
    print("// ── Fit Graph Replicator 완료 ──")
    return full_map


def teardown(prefix=_PREFIX):
    """생성된 utility 노드 전체 삭제."""
    deleted = []
    for node in cmds.ls(prefix + "_*") or []:
        if cmds.objExists(node):
            try:
                cmds.delete(node)
                deleted.append(node)
            except Exception:
                pass
    print("// Teardown: {} 노드 삭제".format(len(deleted)))
