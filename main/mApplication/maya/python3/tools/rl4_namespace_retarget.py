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

import maya.cmds as cmds


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
