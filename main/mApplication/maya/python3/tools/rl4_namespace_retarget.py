"""
RL4 Embedded Joint Namespace Retarget
========================================
body_rl4Embedded / head_rl4Embedded 등 embeddedNodeRL4 노드에 연결된
"joint" input / output 연결만 골라 다른 네임스페이스의 동일 이름 조인트로
재연결합니다.

- embeddedNodeRL4 의 input 은 대부분 unitConversion 을 경유하므로
  unitConversion.input 의 실제 소스(joint)까지 추적합니다.
  (head_rl4Embedded 의 ".inputs"(transform 컨트롤) 처럼 joint 가 아닌
  input 은 대상에서 제외됩니다.)
- output 은 목적지 노드 타입이 "joint" 인 연결만 대상으로 하며,
  blendShape / transform(amOutputs) 등 다른 타입 출력은 건드리지 않습니다.
- 같은 short name(네임스페이스 제거 후 이름)을 가진 대상 네임스페이스
  조인트로 동일한 어트리뷰트에 재연결합니다.
- 재실행해도 안전합니다 (이미 대상 네임스페이스로 연결되어 있으면
  동일한 연결을 다시 맺을 뿐 상태가 바뀌지 않습니다).

사용 예
-------
    import rl4_namespace_retarget as rl4rt

    # 1) dry-run (기본값) - 실제 변경 없이 검증 리포트만 출력
    rl4rt.retarget_rl4_joints("body_rl4Embedded", "Floyd_Rigging_main_v001:")

    # 2) 문제 없으면 실행
    rl4rt.retarget_rl4_joints(
        "body_rl4Embedded", "Floyd_Rigging_main_v001:", dry_run=False
    )

    # 여러 노드를 한 번에
    rl4rt.retarget_multiple(
        ["body_rl4Embedded", "head_rl4Embedded"],
        "Floyd_Rigging_main_v001:",
        dry_run=False,
    )
"""

import math

import maya.cmds as cmds
import maya.api.OpenMaya as om2


def _short_name(node):
    """네임스페이스를 제거한 short node 이름 반환 ('a:b:jnt' -> 'jnt')."""
    return node.rsplit(":", 1)[-1]


def _normalize_namespace(namespace):
    """콜론이 없으면 붙여서 반환."""
    return namespace if namespace.endswith(":") else namespace + ":"


def _target_plug(plug, namespace):
    """plug('joint.attr' 또는 'ns:joint.attr') 를 다른 namespace 의 동일 조인트로 치환."""
    node, attr = plug.split(".", 1)
    return namespace + _short_name(node) + "." + attr


def collect_joint_links(rl4_node):
    """
    rl4_node 의 input / output 연결 중 실제 joint 를 대상으로 하는 것만 수집합니다.
    amOutputs(FRM_WMmultipliers 등 non-joint 대상)는 별도로 "output_am" 에 수집됩니다.

    Returns
    -------
    dict:
        "input"     : [(srcJointPlug, sinkPlug), ...]
            srcJointPlug 는 실제 joint 어트리뷰트, sinkPlug 는 그것을 받는
            unitConversion.input (unitConversion 이 없으면 rl4_node.inputJoints 자체)
        "output"    : [(rl4OutPlug, dstJointPlug), ...]  (joint 대상만)
        "output_am" : [(rl4AmOutputPlug, dstPlug), ...]  (amOutputs, joint 여부 무관)
    """
    if not cmds.objExists(rl4_node):
        raise RuntimeError("node not found: {}".format(rl4_node))

    input_links = []
    inc = cmds.listConnections(
        rl4_node, source=True, destination=False, plugs=True, connections=True
    ) or []
    for i in range(0, len(inc), 2):
        dst_attr, src_plug = inc[i], inc[i + 1]
        if ".inputJoints" not in dst_attr:
            continue
        src_node = src_plug.split(".")[0]
        if cmds.nodeType(src_node) == "unitConversion":
            feeder = cmds.listConnections(
                src_node + ".input", source=True, destination=False, plugs=True
            ) or []
            if not feeder:
                continue
            feed_plug, sink_plug = feeder[0], src_node + ".input"
        else:
            feed_plug, sink_plug = src_plug, dst_attr
        if cmds.nodeType(feed_plug.split(".")[0]) == "joint":
            input_links.append((feed_plug, sink_plug))

    output_links = []
    output_am_links = []
    out = cmds.listConnections(
        rl4_node, source=False, destination=True, plugs=True, connections=True
    ) or []
    for i in range(0, len(out), 2):
        src_plug, dst_plug = out[i], out[i + 1]
        if cmds.nodeType(dst_plug.split(".")[0]) == "joint":
            output_links.append((src_plug, dst_plug))
        elif src_plug.split(".", 1)[1].startswith("amOutputs"):
            output_am_links.append((src_plug, dst_plug))

    return {"input": input_links, "output": output_links, "output_am": output_am_links}


def validate_retarget(rl4_node, target_namespace):
    """
    재연결 전 사전 검증.

    Returns
    -------
    dict: links(collect_joint_links 결과), namespace,
          "missing"(대상 조인트 없음 - 실행을 막음),
          "locked"(대상 attr locked), "occupied"(대상 attr 이 다른 소스에 이미 연결됨),
          "am_missing"(amOutputs 대상이 네임스페이스 기준으로 존재하지 않음 -
                       실행을 막지 않고 로그만 남기고 그대로 둠) 리스트
    """
    ns = _normalize_namespace(target_namespace)
    links = collect_joint_links(rl4_node)

    joints = set()
    for feed_plug, _ in links["input"]:
        joints.add(feed_plug.split(".")[0])
    for _, dst_plug in links["output"]:
        joints.add(dst_plug.split(".")[0])

    missing = sorted(
        _short_name(j) for j in joints if not cmds.objExists(ns + _short_name(j))
    )

    locked = []
    occupied = []
    for src_plug, dst_plug in links["output"]:
        tgt = _target_plug(dst_plug, ns)
        if not cmds.objExists(tgt):
            continue
        if cmds.getAttr(tgt, lock=True):
            locked.append(tgt)
        existing = cmds.listConnections(
            tgt, source=True, destination=False, plugs=True
        ) or []
        # 이미 동일한 소스로 연결되어 있으면(재실행) 충돌이 아님
        if existing and existing[0] != src_plug:
            occupied.append((tgt, existing[0]))

    # output_missing / am_missing : 조인트(노드) 는 존재하지만 그 위의 커스텀
    # attribute 가 네임스페이스 쪽에는 없는 경우. 실행을 막지 않고 로그만 남긴다.
    output_missing = []
    for _, dst_plug in links["output"]:
        tgt = _target_plug(dst_plug, ns)
        if not cmds.objExists(tgt):
            output_missing.append(dst_plug)

    am_missing = []
    for _, dst_plug in links["output_am"]:
        tgt = _target_plug(dst_plug, ns)
        if not cmds.objExists(tgt):
            am_missing.append(dst_plug)

    return {
        "links": links,
        "namespace": ns,
        "missing": missing,
        "locked": locked,
        "occupied": occupied,
        "output_missing": sorted(output_missing),
        "am_missing": sorted(am_missing),
    }


def _retarget_output_link(src_plug, dst_plug, ns, unlock_old):
    """
    output 연결 하나를 재연결한다. 대상 attribute 가 네임스페이스 쪽에
    존재하지 않으면(노드는 있지만 커스텀 attribute 가 없는 경우 포함)
    아무것도 하지 않고 그대로 둔다.

    Returns
    -------
    tuple: ("skipped", None) | ("done", old_retained_bool) | ("error", message)
    """
    new_dst = _target_plug(dst_plug, ns)
    if not cmds.objExists(new_dst):
        return ("skipped", None)

    old_retained = False
    try:
        if cmds.isConnected(src_plug, dst_plug):
            was_locked = cmds.getAttr(dst_plug, lock=True)
            if was_locked and unlock_old:
                cmds.setAttr(dst_plug, lock=False)
            try:
                cmds.disconnectAttr(src_plug, dst_plug)
            finally:
                if was_locked and unlock_old:
                    cmds.setAttr(dst_plug, lock=True)
    except Exception:
        old_retained = True

    try:
        cmds.connectAttr(src_plug, new_dst, force=True)
        return ("done", old_retained)
    except Exception as e:
        return ("error", str(e))


def retarget_rl4_joints(
    rl4_node, target_namespace, dry_run=True, force=False, unlock_old=True
):
    """
    rl4_node 의 joint input/output 연결을 target_namespace 의 동일 이름
    조인트로 재연결합니다.

    Parameters
    ----------
    rl4_node : str            예: "body_rl4Embedded"
    target_namespace : str    예: "Floyd_Rigging_main_v001:" (콜론 생략 가능)
    dry_run : bool            True(기본값) - 검증/리포트만 수행, 실제 연결 변경 없음
    force : bool              True - locked/occupied 경고가 있어도 강행
    unlock_old : bool         True(기본값) - output 의 기존(old) 목적지 어트리뷰트가
                              locked 라서 disconnect 가 실패하면, 임시로 잠금을 풀어
                              끊어낸 뒤 원래 lock 상태로 복원한다.
                              False 면 locked 인 기존 연결은 그대로 두고
                              (fan-out) report["old_retained"] 에 기록만 한다.

    Returns
    -------
    dict: validate_retarget() 결과 + (dry_run=False 이고 진행됐다면)
          "input_done" / "output_done" / "old_retained" / "errors"
    """
    report = validate_retarget(rl4_node, target_namespace)
    links = report["links"]
    ns = report["namespace"]

    print("[RL4Retarget] {} -> {}".format(rl4_node, ns))
    print("[RL4Retarget]   input joint links : {}".format(len(links["input"])))
    print("[RL4Retarget]   output joint links: {}".format(len(links["output"])))
    print("[RL4Retarget]   output amOutputs links: {}".format(len(links["output_am"])))

    if report["output_missing"]:
        print("[RL4Retarget]   output target attr not found in namespace ({}건) - 그대로 두고 건너뜀:".format(
            len(report["output_missing"])))
        for d in report["output_missing"][:20]:
            print("     -", d)

    if report["am_missing"]:
        print("[RL4Retarget]   amOutputs target not found in namespace ({}건) - 그대로 두고 건너뜀:".format(
            len(report["am_missing"])))
        for d in report["am_missing"][:20]:
            print("     -", d)

    if report["missing"]:
        print("[RL4Retarget]   MISSING targets ({}):".format(len(report["missing"])))
        for j in report["missing"][:20]:
            print("     -", ns + j)

    if report["locked"]:
        print("[RL4Retarget]   LOCKED targets ({}):".format(len(report["locked"])))
        for t in report["locked"][:20]:
            print("     -", t)

    if report["occupied"]:
        print("[RL4Retarget]   OCCUPIED targets ({}):".format(len(report["occupied"])))
        for t, s in report["occupied"][:20]:
            print("     -", t, "<--", s)

    blocking = bool(report["missing"]) or (
        not force and (report["locked"] or report["occupied"])
    )

    if dry_run:
        print("[RL4Retarget]   dry_run=True - 실제 연결 변경 없음.")
        return report

    if blocking:
        print("[RL4Retarget]   BLOCKED - 위 문제를 해결하거나 force=True 로 실행하세요.")
        return report

    errors = []
    old_retained = []
    output_skipped = []
    am_skipped = []
    input_done = 0
    output_done = 0
    am_done = 0

    cmds.undoInfo(openChunk=True, chunkName="RL4Retarget_{}".format(rl4_node))
    try:
        for feed_plug, sink_plug in links["input"]:
            # sink_plug 는 입력 하나만 받을 수 있는 destination 이므로
            # force=True 가 기존 연결을 자동으로 대체한다 (별도 disconnect 불필요).
            new_src = _target_plug(feed_plug, ns)
            try:
                cmds.connectAttr(new_src, sink_plug, force=True)
                input_done += 1
            except Exception as e:
                errors.append((new_src, sink_plug, str(e)))

        for src_plug, dst_plug in links["output"]:
            status, info = _retarget_output_link(src_plug, dst_plug, ns, unlock_old)
            if status == "skipped":
                output_skipped.append(dst_plug)
            elif status == "done":
                output_done += 1
                if info:
                    old_retained.append(dst_plug)
            else:
                errors.append((src_plug, _target_plug(dst_plug, ns), info))

        for src_plug, dst_plug in links["output_am"]:
            status, info = _retarget_output_link(src_plug, dst_plug, ns, unlock_old)
            if status == "skipped":
                am_skipped.append(dst_plug)
            elif status == "done":
                am_done += 1
                if info:
                    old_retained.append(dst_plug)
            else:
                errors.append((src_plug, _target_plug(dst_plug, ns), info))
    finally:
        cmds.undoInfo(closeChunk=True)

    print("[RL4Retarget]   input reconnected : {}/{}".format(input_done, len(links["input"])))
    print("[RL4Retarget]   output reconnected: {}/{}".format(output_done, len(links["output"])))
    print("[RL4Retarget]   amOutputs reconnected: {}/{}".format(am_done, len(links["output_am"])))
    if output_skipped:
        print("[RL4Retarget]   output target attr not found - 그대로 둠 ({}건):".format(len(output_skipped)))
        for d in output_skipped[:20]:
            print("     -", d)
    if am_skipped:
        print("[RL4Retarget]   amOutputs target not found - 그대로 둠 ({}건):".format(len(am_skipped)))
        for d in am_skipped[:20]:
            print("     -", d)
    if old_retained:
        print("[RL4Retarget]   OLD connection retained (locked, {}건) - 새 연결은 정상 추가됨:".format(
            len(old_retained)))
        for t in old_retained[:20]:
            print("     -", t)
    if errors:
        print("[RL4Retarget]   ERRORS ({}):".format(len(errors)))
        for e in errors[:20]:
            print("     -", e)

    report["old_retained"] = old_retained
    report["output_skipped"] = output_skipped
    report["am_skipped"] = am_skipped
    report["input_done"] = input_done
    report["output_done"] = output_done
    report["am_done"] = am_done
    report["errors"] = errors
    return report


def retarget_multiple(rl4_nodes, target_namespace, dry_run=True, force=False):
    """여러 rl4 노드에 대해 retarget_rl4_joints 를 순차 실행합니다."""
    results = {}
    for node in rl4_nodes:
        results[node] = retarget_rl4_joints(
            node, target_namespace, dry_run=dry_run, force=force
        )
    return results


# ══════════════════════════════════════════════════════════════
#  Transform 검증  (offsetParentMatrix 를 포함해 world 기준으로 비교)
# ══════════════════════════════════════════════════════════════

def _joint_nodes_from_links(rl4_node):
    """rl4_node 의 input/output joint 연결에 관련된 모든 joint 노드 이름 집합."""
    links = collect_joint_links(rl4_node)
    nodes = set()
    for feed_plug, _ in links["input"]:
        nodes.add(feed_plug.split(".")[0])
    for _, dst_plug in links["output"]:
        nodes.add(dst_plug.split(".")[0])
    return nodes


def _world_quaternion(node):
    m = om2.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))
    return om2.MTransformationMatrix(m).rotation(asQuaternion=True)


def _angle_between_quaternions(q1, q2):
    dot = abs(q1.x * q2.x + q1.y * q2.y + q1.z * q2.z + q1.w * q2.w)
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(2.0 * math.acos(dot))


def verify_transform_match(rl4_node, target_namespace, tolerance=0.01, angle_tolerance=0.1):
    """
    rl4_node 에 연결된 조인트들과 target_namespace 의 동일 이름 조인트가
    world 상에서 실질적으로 같은 위치/방향에 있는지 검증합니다.

    worldMatrix 를 그대로 비교하므로 offsetParentMatrix 로 표현된 transform 도
    자동으로 올바르게 반영됩니다 — channel box 의 translate/rotate 값만 비교하면
    offsetParentMatrix 를 쓰는 조인트(예: 일부 게임 리그)에서 오탐(false positive)이
    발생하므로 world 비교가 필수입니다.

    Parameters
    ----------
    rl4_node        : str    예: "body_rl4Embedded"
    target_namespace: str    예: "Floyd:" (콜론 생략 가능)
    tolerance       : float  위치 허용 오차 (cm)
    angle_tolerance : float  방향 허용 오차 (degree)

    Returns
    -------
    dict: {"checked": int,
           "matched"       : [(short_name, pos_diff, angle_diff), ...],
           "mismatched"    : [(short_name, pos_diff, angle_diff), ...],
           "missing_target": [short_name, ...]}
    """
    ns = _normalize_namespace(target_namespace)
    current_nodes = sorted(_joint_nodes_from_links(rl4_node))

    matched, mismatched, missing = [], [], []
    for node in current_nodes:
        short  = _short_name(node)
        target = ns + short
        if not cmds.objExists(target):
            missing.append(short)
            continue

        p1 = cmds.xform(node,   query=True, worldSpace=True, translation=True)
        p2 = cmds.xform(target, query=True, worldSpace=True, translation=True)
        pos_diff = sum((a - b) ** 2 for a, b in zip(p1, p2)) ** 0.5
        angle_diff = _angle_between_quaternions(_world_quaternion(node), _world_quaternion(target))

        entry = (short, pos_diff, angle_diff)
        if pos_diff <= tolerance and angle_diff <= angle_tolerance:
            matched.append(entry)
        else:
            mismatched.append(entry)

    print("[RL4Retarget] verify_transform_match: checked={} matched={} mismatched={} missing={}".format(
        len(current_nodes), len(matched), len(mismatched), len(missing)))
    if mismatched:
        print("[RL4Retarget]   MISMATCHED ({}):".format(len(mismatched)))
        for short, pos_diff, angle_diff in mismatched[:20]:
            print("     - {}  pos_diff={:.3f}  angle_diff={:.3f}".format(short, pos_diff, angle_diff))
    if missing:
        print("[RL4Retarget]   target 없음 ({}): {}".format(len(missing), ", ".join(missing[:20])))

    return {
        "checked": len(current_nodes),
        "matched": matched,
        "mismatched": mismatched,
        "missing_target": missing,
    }


# ══════════════════════════════════════════════════════════════
#  offsetParentMatrix Bake  (숨겨진 transform 을 channel box 로 노출)
# ══════════════════════════════════════════════════════════════

_IDENTITY_MATRIX = [
    1.0, 0.0, 0.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 1.0, 0.0,
    0.0, 0.0, 0.0, 1.0,
]


def _is_identity_matrix(values, tolerance=1e-6):
    return all(abs(a - b) <= tolerance for a, b in zip(values, _IDENTITY_MATRIX))


def _is_zeroed_transform(node, tolerance=1e-6):
    """translate=(0,0,0), rotate=(0,0,0), scale=(1,1,1) 인지 (channel box 상 '제로화' 상태)."""
    t = cmds.getAttr(node + ".translate")[0]
    r = cmds.getAttr(node + ".rotate")[0]
    s = cmds.getAttr(node + ".scale")[0]
    return (
        all(abs(v) <= tolerance for v in t)
        and all(abs(v) <= tolerance for v in r)
        and all(abs(v - 1.0) <= tolerance for v in s)
    )


def _locked_or_connected(node, attrs):
    """attrs 중 하나라도 locked 이거나 incoming connection 이 있으면 True."""
    for attr in attrs:
        full = node + attr
        if cmds.getAttr(full, lock=True):
            return True
        if cmds.listConnections(full, source=True, destination=False):
            return True
    return False


_CONSTRAINT_TYPES = (
    "parentConstraint", "pointConstraint", "orientConstraint",
    "scaleConstraint", "aimConstraint",
)

_BAKE_ATTRS = (".translate", ".rotate", ".scale", ".offsetParentMatrix")


def _is_locked(node, attrs):
    return any(cmds.getAttr(node + attr, lock=True) for attr in attrs)


def _find_constraint_drive_connections(node, attrs=_BAKE_ATTRS):
    """attrs 를 구동하는 constraint 노드의 출력 연결을 (src_plug, dst_plug) 목록으로 반환."""
    result = []
    for attr in attrs:
        full = node + attr
        srcs = cmds.listConnections(full, source=True, destination=False, plugs=True) or []
        for src in srcs:
            src_node = src.split(".")[0]
            if cmds.nodeType(src_node) in _CONSTRAINT_TYPES:
                result.append((src, full))
    return result


def _has_non_constraint_connection(node, attrs=_BAKE_ATTRS):
    """attrs 에 constraint 가 아닌 다른 노드로부터의 incoming connection 이 있으면 True."""
    for attr in attrs:
        full = node + attr
        srcs = cmds.listConnections(full, source=True, destination=False, plugs=True) or []
        for src in srcs:
            src_node = src.split(".")[0]
            if cmds.nodeType(src_node) not in _CONSTRAINT_TYPES:
                return True
    return False


def _disconnect_all(connections):
    for src, dst in connections:
        try:
            if cmds.isConnected(src, dst):
                cmds.disconnectAttr(src, dst)
        except Exception as e:
            print("[RL4Retarget] WARN disconnect {} -> {}: {}".format(src, dst, e))


def _reconnect_all(connections):
    for src, dst in connections:
        try:
            if not cmds.isConnected(src, dst):
                cmds.connectAttr(src, dst, force=True)
        except Exception as e:
            print("[RL4Retarget] WARN reconnect {} -> {}: {}".format(src, dst, e))


def _values_close(a, b, tolerance):
    return all(abs(x - y) <= tolerance for x, y in zip(a, b))


def _bake_one(node, force, tolerance, handle_constraints=True):
    """
    단일 node 에 offsetParentMatrix bake 를 1회 시도하고 즉시 재조회하여
    실제로 반영됐는지 검증합니다 (Maya 가 대량의 연속 setAttr 상황에서 간헐적으로
    쓰기를 누락하는 경우가 관찰되어, "설정했다"와 "실제로 반영됐다"를 분리 확인).

    handle_constraints=True 이면, translate/rotate/scale/offsetParentMatrix 를
    구동하는 constraint 가 있을 경우 잠시 disconnect 하고 setAttr 한 뒤 다시
    connect 합니다. 단, constraint 는 자신의 target 을 기준으로 값을 다시
    계산해서 밀어넣으므로, 재연결 직후 값이 baked 값과 달라지면(=constraint 가
    되돌려놓으면) "reverted_by_constraint" 로 별도 보고합니다 — 이 경우 해당
    채널은 baked 라고 볼 수 없습니다.

    Returns
    -------
    ("baked", None) | ("verify_failed", detail) | ("reverted_by_constraint", detail)
    | ("error", message)
    """
    opm_values = cmds.getAttr(node + ".offsetParentMatrix")

    if force:
        full = om2.MMatrix(cmds.getAttr(node + ".matrix")) * om2.MMatrix(opm_values)
    else:
        full = om2.MMatrix(opm_values)

    tm = om2.MTransformationMatrix(full)
    t  = tm.translation(om2.MSpace.kTransform)
    ro = cmds.getAttr(node + ".rotateOrder")
    rot = tm.rotation(asQuaternion=False)
    rot.reorderIt(ro)
    scale = tm.scale(om2.MSpace.kTransform)

    target_translate = (t.x, t.y, t.z)
    target_rotate    = (math.degrees(rot.x), math.degrees(rot.y), math.degrees(rot.z))
    target_scale     = tuple(scale)

    constraint_conns = _find_constraint_drive_connections(node) if handle_constraints else []

    try:
        if constraint_conns:
            _disconnect_all(constraint_conns)
        cmds.setAttr(node + ".offsetParentMatrix", *_IDENTITY_MATRIX, type="matrix")
        cmds.setAttr(node + ".translate", *target_translate, type="double3")
        cmds.setAttr(node + ".rotate", *target_rotate, type="double3")
        cmds.setAttr(node + ".scale", *target_scale, type="double3")
    except Exception as e:
        if constraint_conns:
            _reconnect_all(constraint_conns)
        return ("error", str(e))

    ok_before_reconnect = (
        _is_identity_matrix(cmds.getAttr(node + ".offsetParentMatrix"), 1e-5)
        and _values_close(cmds.getAttr(node + ".translate")[0], target_translate, 1e-4)
        and _values_close(cmds.getAttr(node + ".rotate")[0], target_rotate, 1e-3)
        and _values_close(cmds.getAttr(node + ".scale")[0], target_scale, 1e-4)
    )

    if constraint_conns:
        _reconnect_all(constraint_conns)
        ok_after_reconnect = (
            _values_close(cmds.getAttr(node + ".translate")[0], target_translate, 1e-4)
            and _values_close(cmds.getAttr(node + ".rotate")[0], target_rotate, 1e-3)
            and _values_close(cmds.getAttr(node + ".scale")[0], target_scale, 1e-4)
        )
        if not ok_after_reconnect:
            return (
                "reverted_by_constraint",
                "constraint 재연결 후 값이 되돌아감 (constraint 가 자신의 target 기준으로 "
                "채널을 다시 구동함 — 이 채널은 disconnect 상태를 유지해야 baked 값이 보존됨)",
            )

    if not ok_before_reconnect:
        return ("verify_failed", "setAttr 후 재조회 값이 기대값과 다름")
    return ("baked", None)


def bake_offset_parent_matrix(nodes, tolerance=1e-6, force=False, max_retries=2, handle_constraints=True):
    """
    offsetParentMatrix 에 transform 값이 들어있는데 channel box(translate/rotate/scale)가
    제로화(identity)되어 있는 노드에 대해:

        1) offsetParentMatrix 를 translate / rotate(자신의 rotateOrder 기준) / scale 로 분해
        2) (constraint 로 구동되는 채널이 있으면) constraint 출력을 잠시 disconnect
        3) offsetParentMatrix 를 identity 로 초기화, 분해한 값을 채널에 설정
        4) constraint 를 다시 connect
        5) 즉시 재조회하여 실제로 반영됐는지 검증 — 특히 constraint 가 있던 채널은
           재연결 후 값이 유지되는지 별도로 확인 (검증 실패 시 최대 max_retries 회 재시도)

    world 위치·방향은 그대로 유지되면서, offsetParentMatrix 안에 숨어 있던 값이
    channel box 에 그대로 드러나게 됩니다 (이후 다른 스켈레톤과 채널 값만으로
    비교/매칭하기 쉬워짐).

    주의: constraint 가 구동하는 채널은, constraint 가 자신의 target 을 기준으로
    값을 다시 계산해 밀어넣기 때문에 재연결 직후 baked 값이 유실될 수 있습니다.
    이 경우 "reverted_by_constraint" 로 별도 보고되며 "baked" 에 포함되지 않습니다
    (재시도해도 결과가 같으므로 재시도하지 않습니다 — constraint 를 영구적으로
    끄거나 offset 을 갱신해야 해결됩니다).

    Parameters
    ----------
    nodes              : list[str]
    tolerance          : float  identity / zero 판정 허용 오차
    force              : bool   False(기본값) — channel box 가 이미 0/identity 가 아니면
                                 건드리지 않고 skipped_not_zeroed 에 기록합니다 (안전).
                                 True  — 현재 channel box 값(translate/rotate/scale)까지
                                 포함한 .matrix 를 offsetParentMatrix 와 합성하여 baked
                                 값을 만듭니다 (constraint 로 구동되는 채널처럼 이미
                                 값이 있는 노드도 처리하려면 보통 True 가 필요합니다).
    max_retries        : int   setAttr 후 재조회 검증이 실패했을 때 재시도할 횟수.
    handle_constraints : bool  True(기본값) — constraint 가 구동하는 채널을 disconnect
                                 → set → reconnect 로 처리. False 면 constraint 연결이
                                 있는 노드는 skipped_locked 로 건너뜁니다.

    Returns
    -------
    dict: {"baked": [...], "skipped_identity": [...], "skipped_not_zeroed": [...],
           "skipped_locked": [...], "reverted_by_constraint": [(node, reason), ...],
           "failed": [(node, reason), ...]}
    """
    baked                   = []
    skipped_identity        = []
    skipped_not_zeroed      = []
    skipped_locked          = []
    reverted_by_constraint  = []
    failed                  = []

    cmds.undoInfo(openChunk=True, chunkName="BakeOffsetParentMatrix")
    try:
        for node in nodes:
            if not cmds.objExists(node):
                continue

            opm_values = cmds.getAttr(node + ".offsetParentMatrix")
            if _is_identity_matrix(opm_values, tolerance):
                skipped_identity.append(node)
                continue

            if not force and not _is_zeroed_transform(node, tolerance):
                skipped_not_zeroed.append(node)
                continue

            if _is_locked(node, _BAKE_ATTRS):
                skipped_locked.append(node)
                continue

            if _has_non_constraint_connection(node, _BAKE_ATTRS):
                skipped_locked.append(node)
                continue

            if not handle_constraints and _find_constraint_drive_connections(node):
                skipped_locked.append(node)
                continue

            status, detail = _bake_one(node, force, tolerance, handle_constraints=handle_constraints)
            attempt = 0
            while status == "verify_failed" and attempt < max_retries:
                attempt += 1
                status, detail = _bake_one(node, force, tolerance, handle_constraints=handle_constraints)

            if status == "baked":
                baked.append(node)
            elif status == "reverted_by_constraint":
                reverted_by_constraint.append((node, detail))
            else:
                failed.append((node, detail))
    finally:
        cmds.undoInfo(closeChunk=True)

    print("[RL4Retarget] bake_offset_parent_matrix: baked={} skipped_identity={} skipped_not_zeroed={} "
          "skipped_locked={} reverted_by_constraint={} failed={}".format(
              len(baked), len(skipped_identity), len(skipped_not_zeroed), len(skipped_locked),
              len(reverted_by_constraint), len(failed)))
    if skipped_not_zeroed:
        print("[RL4Retarget]   channel box 가 이미 0/identity 가 아니어서 건너뜀 ({}, force=True 로 강행 가능):".format(
            len(skipped_not_zeroed)))
        for n in skipped_not_zeroed[:20]:
            print("     -", n)
    if skipped_locked:
        print("[RL4Retarget]   locked/connected(constraint 아님) 라서 건너뜀 ({}):".format(len(skipped_locked)))
        for n in skipped_locked[:20]:
            print("     -", n)
    if reverted_by_constraint:
        print("[RL4Retarget]   REVERTED BY CONSTRAINT - 재연결 후 값이 되돌아감 ({}):".format(
            len(reverted_by_constraint)))
        for n, reason in reverted_by_constraint[:20]:
            print("     - {}: {}".format(n, reason))
    if failed:
        print("[RL4Retarget]   FAILED - setAttr 이 반영되지 않음 ({}):".format(len(failed)))
        for n, reason in failed[:20]:
            print("     - {}: {}".format(n, reason))

    return {
        "baked": baked,
        "skipped_identity": skipped_identity,
        "skipped_not_zeroed": skipped_not_zeroed,
        "skipped_locked": skipped_locked,
        "reverted_by_constraint": reverted_by_constraint,
        "failed": failed,
    }


def bake_offset_parent_matrix_for_namespace(rl4_node, target_namespace, tolerance=1e-6, force=False):
    """
    rl4_node 에 연결된 조인트들의 target_namespace 대응 조인트들을 대상으로
    bake_offset_parent_matrix() 를 실행하는 편의 함수.
    """
    ns = _normalize_namespace(target_namespace)
    current_nodes = _joint_nodes_from_links(rl4_node)
    target_nodes = sorted({
        ns + _short_name(n) for n in current_nodes if cmds.objExists(ns + _short_name(n))
    })
    return bake_offset_parent_matrix(target_nodes, tolerance=tolerance, force=force)
