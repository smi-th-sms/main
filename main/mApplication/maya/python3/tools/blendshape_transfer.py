"""
Blendshape Transfer Tool
동일한 토폴로지를 가진 src_mesh 의 blendShape targets 를 dst_mesh 로 복사.
target 이름(alias)과 weight 의 incoming connection 을 원본과 동일하게 유지.

Usage:
    transfer_blendshapes("meshA", "meshB")

    # 선택 기반: src 먼저, dst 나중에 선택
    run_from_selection()
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_blendshape_node(mesh):
    """mesh history 에서 첫 번째 blendShape 노드를 반환."""
    history = cmds.listHistory(mesh, pdo=True) or []
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            return node
    return None


def _get_target_map(bs_node):
    """blendShape 노드의 {weight_index: alias_name} 딕셔너리 반환."""
    aliases = cmds.aliasAttr(bs_node, q=True) or []
    result = {}
    for i in range(0, len(aliases), 2):
        alias_name = aliases[i]
        attr_name  = aliases[i + 1]          # e.g. "weight[3]"
        idx = int(attr_name.split('[')[1].rstrip(']'))
        result[idx] = alias_name
    return result


def _get_mesh_fn(node_name):
    """transform 또는 shape 이름으로 MFnMesh 반환."""
    sel = om.MSelectionList()
    sel.add(node_name)
    dag = sel.getDagPath(0)
    if dag.node().hasFn(om.MFn.kTransform):
        dag.extendToShape()
    if not dag.node().hasFn(om.MFn.kMesh):
        raise RuntimeError(f"'{node_name}' is not a mesh node.")
    return om.MFnMesh(dag)


def _get_points(node_name):
    return _get_mesh_fn(node_name).getPoints(om.MSpace.kObject)


def _set_points(node_name, pts):
    fn = _get_mesh_fn(node_name)
    fn.setPoints(pts, om.MSpace.kObject)
    fn.updateSurface()


# ─────────────────────────────────────────────────────────────────────────────
# Connection management
# ─────────────────────────────────────────────────────────────────────────────

def _redirect_connections_to_proxy(bs_node, target_map):
    """
    blendShape weight 의 incoming connection 을 null group(proxy) 으로 임시 리다이렉트.
    connection 이 없으면 None 반환.

    흐름: driver.attr → src_bs.w[idx]
           ↓ redirect
          driver.attr → null_grp.alias_name   (src_bs 는 자유로운 상태)

    Returns
    -------
    null_grp : str | None
    conn_map : {alias_name: [source_plug_str, ...]}
    locked_idxs : set  – 명시적으로 잠긴 weight index
    """
    conn_map    = {}
    locked_idxs = set()

    for idx, alias_name in target_map.items():
        w_attr = f"{bs_node}.w[{idx}]"

        if cmds.getAttr(w_attr, lock=True):
            locked_idxs.add(idx)
            cmds.setAttr(w_attr, lock=False)

        sources = cmds.listConnections(w_attr, s=True, d=False, p=True) or []
        if sources:
            conn_map[alias_name] = sources

    if not conn_map:
        return None, conn_map, locked_idxs

    null_grp = cmds.group(em=True, name="_bs_conn_proxy")

    for alias_name, sources in conn_map.items():
        cmds.addAttr(null_grp, ln=alias_name, at='double', dv=0, k=True)
        proxy_attr = f"{null_grp}.{alias_name}"

        idx = next(i for i, n in target_map.items() if n == alias_name)
        w_attr = f"{bs_node}.w[{idx}]"

        for src_plug in sources:
            if cmds.isConnected(src_plug, w_attr):
                cmds.disconnectAttr(src_plug, w_attr)
            cmds.connectAttr(src_plug, proxy_attr, f=True)

    return null_grp, conn_map, locked_idxs


def _restore_connections(src_bs, target_map, dst_bs, dst_target_names,
                         conn_map, null_grp, locked_idxs):
    """
    src_bs 의 connection 복원 + 동일 driver 를 dst_bs 에도 연결.
    null_grp 삭제.
    잠금 상태를 원래대로 복원.
    """
    alias_to_src_idx  = {v: k for k, v in target_map.items()}
    dst_alias_to_idx  = {name: i for i, name in enumerate(dst_target_names)}

    for alias_name, sources in conn_map.items():
        for src_plug in sources:
            # ① src_bs 복원
            if alias_name in alias_to_src_idx:
                attr = f"{src_bs}.w[{alias_to_src_idx[alias_name]}]"
                if not cmds.isConnected(src_plug, attr):
                    try:
                        cmds.connectAttr(src_plug, attr, f=True)
                    except Exception as e:
                        cmds.warning(f"[BS Transfer] src 복원 실패 ({alias_name}): {e}")

            # ② dst_bs 에 동일 driver 연결
            if alias_name in dst_alias_to_idx:
                attr = f"{dst_bs}.w[{dst_alias_to_idx[alias_name]}]"
                if not cmds.isConnected(src_plug, attr):
                    try:
                        cmds.connectAttr(src_plug, attr, f=True)
                    except Exception as e:
                        cmds.warning(f"[BS Transfer] dst 연결 실패 ({alias_name}): {e}")

    # null_grp 삭제 (연결은 Maya 가 자동 해제)
    if cmds.objExists(null_grp):
        cmds.delete(null_grp)

    # lock 상태 복원
    for idx in locked_idxs:
        attr = f"{src_bs}.w[{idx}]"
        if cmds.objExists(attr):
            cmds.setAttr(attr, lock=True)


def _restore_src_only(src_bs, target_map, conn_map, null_grp, locked_idxs):
    """전송 실패 시 src_bs connection 만 복원 (dst_bs 없음)."""
    alias_to_src_idx = {v: k for k, v in target_map.items()}
    for alias_name, sources in conn_map.items():
        if alias_name not in alias_to_src_idx:
            continue
        attr = f"{src_bs}.w[{alias_to_src_idx[alias_name]}]"
        for src_plug in sources:
            if not cmds.isConnected(src_plug, attr):
                try:
                    cmds.connectAttr(src_plug, attr, f=True)
                except Exception as e:
                    cmds.warning(f"[BS Transfer] src 복원 실패 ({alias_name}): {e}")

    if cmds.objExists(null_grp):
        cmds.delete(null_grp)

    for idx in locked_idxs:
        attr = f"{src_bs}.w[{idx}]"
        if cmds.objExists(attr):
            cmds.setAttr(attr, lock=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main function
# ─────────────────────────────────────────────────────────────────────────────

def transfer_blendshapes(src_mesh, dst_mesh):
    """
    src_mesh 의 모든 blendShape target 을 dst_mesh 로 이전.
    weight 에 연결된 driver 도 dst_mesh 의 새 blendShape 에 동일하게 연결.

    Parameters
    ----------
    src_mesh : str  blendShape 가 있는 소스 메쉬
    dst_mesh : str  타깃으로 삼을 동일 토폴로지 메쉬

    Returns
    -------
    str | None  생성된 blendShape 노드 이름, 실패 시 None
    """
    src_bs = _get_blendshape_node(src_mesh)
    if not src_bs:
        cmds.warning(f"transfer_blendshapes: '{src_mesh}' 에 blendShape 없음.")
        return None

    target_map = _get_target_map(src_bs)
    if not target_map:
        cmds.warning(f"transfer_blendshapes: '{src_bs}' 에 target 없음.")
        return None

    print(f"[BS Transfer] {src_mesh} → {dst_mesh}  /  targets: {len(target_map)}")

    # ── connection/lock 처리: weight 를 자유롭게 setAttr 할 수 있도록 ──────────
    null_grp, conn_map, locked_idxs = _redirect_connections_to_proxy(src_bs, target_map)

    if conn_map:
        print(f"[BS Transfer] connection 리다이렉트: {len(conn_map)} attrs → {null_grp}")
    if locked_idxs:
        print(f"[BS Transfer] unlock: {len(locked_idxs)} weights")

    # ── 소스 deformer 상태 저장 ───────────────────────────────────────────────
    orig_envelope = cmds.getAttr(f"{src_bs}.envelope")
    orig_weights  = {i: cmds.getAttr(f"{src_bs}.w[{i}]") for i in target_map}

    cmds.setAttr(f"{src_bs}.envelope", 1)
    for i in target_map:
        cmds.setAttr(f"{src_bs}.w[{i}]", 0)

    # ── neutral(base) 포지션 ──────────────────────────────────────────────────
    src_base = _get_points(src_mesh)
    dst_base = _get_points(dst_mesh)
    n_verts  = len(src_base)

    target_meshes = []
    target_names  = []
    dst_bs        = None

    try:
        for tgt_idx, tgt_name in sorted(target_map.items()):
            cmds.setAttr(f"{src_bs}.w[{tgt_idx}]", 1)
            src_def = _get_points(src_mesh)

            dup = cmds.duplicate(dst_mesh, name=f"_bst_{tgt_name}")[0]
            cmds.delete(dup, ch=True)

            dup_pts = _get_points(dup)
            for i in range(n_verts):
                dup_pts[i] = om.MPoint(
                    dst_base[i].x + (src_def[i].x - src_base[i].x),
                    dst_base[i].y + (src_def[i].y - src_base[i].y),
                    dst_base[i].z + (src_def[i].z - src_base[i].z),
                )
            _set_points(dup, dup_pts)

            target_meshes.append(dup)
            target_names.append(tgt_name)
            print(f"  OK  {tgt_name}")

            cmds.setAttr(f"{src_bs}.w[{tgt_idx}]", 0)

        # ── dst 에 blendShape 생성 ────────────────────────────────────────────
        dst_bs = cmds.blendShape(
            *target_meshes, dst_mesh,
            name=f"{dst_mesh}_blendShape",
            frontOfChain=True,
        )[0]

        for i, name in enumerate(target_names):
            cmds.aliasAttr(name, f"{dst_bs}.w[{i}]")

        cmds.delete(target_meshes)
        target_meshes = []

    finally:
        # 소스 deformer 상태 복원
        cmds.setAttr(f"{src_bs}.envelope", orig_envelope)
        for i, val in orig_weights.items():
            try:
                cmds.setAttr(f"{src_bs}.w[{i}]", val)
            except Exception:
                pass

        # connection 복원 / dst_bs 에 연결
        if null_grp and cmds.objExists(null_grp):
            if dst_bs and cmds.objExists(dst_bs):
                _restore_connections(
                    src_bs, target_map, dst_bs, target_names,
                    conn_map, null_grp, locked_idxs
                )
            else:
                _restore_src_only(src_bs, target_map, conn_map, null_grp, locked_idxs)
        elif locked_idxs:
            # null_grp 없이 unlock 만 했던 경우
            for idx in locked_idxs:
                attr = f"{src_bs}.w[{idx}]"
                if cmds.objExists(attr):
                    cmds.setAttr(attr, lock=True)

        if target_meshes:
            cmds.delete(target_meshes)

    if not dst_bs:
        return None

    print(f"[BS Transfer] 완료 → {dst_bs}")
    return dst_bs


# ─────────────────────────────────────────────────────────────────────────────
# 선택 기반 실행
# ─────────────────────────────────────────────────────────────────────────────

def run_from_selection():
    """
    선택 순서: src_mesh 먼저, dst_mesh 나중에.
    두 개의 mesh 를 선택 후 실행.
    """
    sel = cmds.ls(sl=True, tr=True)
    if len(sel) != 2:
        cmds.warning("run_from_selection: mesh 두 개를 순서대로 선택하세요 (src → dst).")
        return None
    return transfer_blendshapes(sel[0], sel[1])
