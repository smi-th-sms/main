import maya.cmds as cmds
import maya.api.OpenMaya as om2
import numpy as np

def get_dag_path(node):
    sel = om2.MSelectionList()
    sel.add(node)
    return sel.getDagPath(0)

def find_duplicate_points(points, threshold=1e-4):
    arr = np.asarray([(p.x, p.y, p.z) for p in points])
    unique, indices, counts = np.unique(arr.round(decimals=6), axis=0, return_inverse=True, return_counts=True)
    duplicates = np.where(counts > 1)[0]
    result = []
    for dup in duplicates:
        dup_idx = np.where(indices == dup)[0]
        if len(dup_idx) > 1:
            result.append(list(dup_idx))
    return result

def get_face_and_vertices_from_selection():
    sel = cmds.ls(sl=True, fl=True)
    if len(sel) != 3:
        raise RuntimeError("정확히 3개의 버텍스를 선택하세요.")
    meshes = list(set(s.split(".vtx[")[0] for s in sel))
    if len(meshes) != 1:
        raise RuntimeError("모든 버텍스가 같은 mesh에 있어야 합니다.")
    mesh = meshes[0]
    indices = [int(s.split("[")[-1].rstrip("]")) for s in sel]
    dag = get_dag_path(mesh)
    face_sets = []
    for vtx_id in indices:
        it = om2.MItMeshVertex(dag)
        it.setIndex(vtx_id)
        face_sets.append(set(it.getConnectedFaces()))
    common_faces = set.intersection(*face_sets)
    if len(common_faces) != 1:
        raise RuntimeError("3버텍스가 정확히 1개의 face를 정의해야 합니다.")
    return dag, indices, list(common_faces)[0]

def traverse_face_iterative(dag, start_face, v0, v1, face_visited, cv_map, cv_map_inv, new_poly_counts, new_poly_connects, orig_vertices, new_vertices):
    fn = om2.MFnMesh(dag)
    poly_it = om2.MItMeshPolygon(dag)
    edge_it = om2.MItMeshEdge(dag)
    stack = [(start_face, v0, v1)]
    while stack:
        face_idx, v0, v1 = stack.pop()
        if face_visited[face_idx]: continue
        poly_it.setIndex(face_idx)
        vtx_ids = poly_it.getVertices()
        edge_ids = poly_it.getEdges()
        vtx_cnt = len(vtx_ids)
        def idx(i): return (i + vtx_cnt) % vtx_cnt
        dir = 0
        start_idx = -1
        for i in range(vtx_cnt):
            if vtx_ids[i] == v0:
                start_idx = i
                if vtx_ids[idx(i+1)] == v1: dir = 1
                elif vtx_ids[idx(i-1)] == v1: dir = -1
                break
        if dir == 0: continue
        vtx_sorted = [vtx_ids[idx(start_idx + i * dir)] for i in range(vtx_cnt)]
        edge_sorted = [edge_ids[idx(start_idx + i * dir if dir == 1 else start_idx - 1 + i * dir)] for i in range(vtx_cnt)]
        for vtx_id in vtx_sorted:
            if cv_map[vtx_id] == -1:
                new_vertices.append(orig_vertices[vtx_id])
                new_idx = len(new_vertices) - 1
                cv_map[vtx_id] = new_idx
                cv_map_inv[new_idx] = vtx_id
        new_poly_counts.append(vtx_cnt)
        for vtx_id in vtx_sorted:
            new_poly_connects.append(cv_map[vtx_id])
        face_visited[face_idx] = True
        for edge_id in edge_sorted:
            edge_it.setIndex(edge_id)
            vtx_pair = edge_it.vertexId(0), edge_it.vertexId(1)
            faces = edge_it.getConnectedFaces()
            if len(faces) > 1:
                neighbor = faces[1] if faces[0] == face_idx else faces[0]
                if face_visited[neighbor]: continue
                stack.append((neighbor, vtx_pair[1], vtx_pair[0]))

def mesh_reorder_from_face(with_map=False):
    dag, ref_indices, face_idx = get_face_and_vertices_from_selection()
    fn = om2.MFnMesh(dag)
    num_verts = fn.numVertices
    num_faces = fn.numPolygons
    face_visited = [False] * num_faces
    cv_map = [-1] * num_verts
    cv_map_inv = [-1] * num_verts
    new_poly_counts = om2.MIntArray()
    new_poly_connects = om2.MIntArray()
    new_vertices = om2.MFloatPointArray()
    orig_vertices = fn.getPoints(om2.MSpace.kObject)
    traverse_face_iterative(dag, face_idx, ref_indices[0], ref_indices[1],
        face_visited, cv_map, cv_map_inv,
        new_poly_counts, new_poly_connects,
        orig_vertices, new_vertices)
    if with_map:
        return cv_map, fn, dag
    fn_new = om2.MFnMesh()
    new_mesh = fn_new.create(new_vertices, new_poly_counts, new_poly_connects)
    new_name = cmds.rename(om2.MDagPath.getAPathTo(new_mesh).fullPathName(), "ReorderedMesh")
    return new_name

def transfer_vertex_order_via_resultmesh_ui():
    sel = cmds.ls(sl=True, fl=True)
    if len(sel) != 6:
        set_status("src와 tgt로 각 3개, 총 6개 버텍스를 선택하세요.")
        return
    cmds.select(sel[:3])
    src_map, src_fn, _ = mesh_reorder_from_face(with_map=True)
    cmds.select(sel[3:])
    tgt_map, tgt_fn, _ = mesh_reorder_from_face(with_map=True)
    src_inv = {v: k for k, v in enumerate(src_map) if v != -1}
    tgt_inv = {v: k for k, v in enumerate(tgt_map) if v != -1}

    if src_fn.numVertices != tgt_fn.numVertices:
        set_status(f"버텍스 수가 다릅니다: src={src_fn.numVertices}, tgt={tgt_fn.numVertices}")
        return
    missing = [new_id for new_id in src_inv if new_id not in tgt_inv]
    if missing:
        set_status(f"tgt 메쉬에서 순회되지 않은 버텍스 {len(missing)}개 존재 (disconnected shell 의심). 중단합니다.")
        return

    tgt_points = tgt_fn.getPoints(om2.MSpace.kWorld)
    new_points = src_fn.getPoints(om2.MSpace.kObject)
    for new_id in src_inv:
        old_id = src_inv[new_id]
        tgt_id = tgt_inv[new_id]
        new_points[old_id] = tgt_points[tgt_id]
    src_path = src_fn.fullPathName()
    duplicated = cmds.duplicate(src_path, name="TransferredViaResultMesh")[0]
    dup_dag = get_dag_path(duplicated)
    fn_dup = om2.MFnMesh(dup_dag)
    fn_dup.setPoints(new_points, om2.MSpace.kObject)
    if cmds.listRelatives(duplicated, p=1):
        cmds.parent(duplicated, world=True)
    tgt_name = sel[3].split(".vtx")[0]
    cmds.delete(tgt_name)
    new_name = cmds.rename(duplicated, tgt_name)
    set_status(f"Transferred via reorder remapping: {new_name}")

def check_duplicate_vertices_ui():
    try:
        sel = cmds.ls(sl=True, o=True)[0]
        dag = get_dag_path(sel)
        fn = om2.MFnMesh(dag)
        points = fn.getPoints(om2.MSpace.kWorld)
        duplicates = find_duplicate_points(points)
        if duplicates:
            set_status(f"중복점 {len(duplicates)} 그룹: {duplicates}")
        else:
            set_status("중복점 없음")
    except Exception as e:
        set_status(str(e))

def set_status(msg):
    cmds.textField("vertexReorderStatus", e=True, text=msg)

def mesh_reorder_from_face_ui():
    try:
        name = mesh_reorder_from_face()
        set_status(f"버텍스 순서 재정렬 결과: {name}")
    except Exception as e:
        set_status(str(e))

def refresh_buttons():
    sel = cmds.ls(sl=True, fl=True)
    bt_reorder = "vertexReorderBtn"
    bt_remap = "vertexRemapBtn"
    valid_reorder = len(sel) == 3 and all(".vtx[" in s for s in sel)
    valid_remap = len(sel) == 6 and all(".vtx[" in s for s in sel)
    cmds.button(bt_reorder, e=True, enable=valid_reorder)
    cmds.button(bt_remap, e=True, enable=valid_remap)

def show_vertex_reorder_ui():
    if cmds.window("vertexReorderWin", exists=True):
        cmds.deleteUI("vertexReorderWin")
    win = cmds.window("vertexReorderWin", title="Vertex Reorder Tool", sizeable=False)
    cmds.columnLayout(adjustableColumn=True)
    cmds.text(label="1. 3/6개의 버텍스를 선택 후 기능 버튼 활성화")
    cmds.button("vertexReorderBtn", label="버텍스 순서 재정렬 (3버텍스)", command=lambda x: mesh_reorder_from_face_ui(), enable=False)
    cmds.button("vertexRemapBtn", label="타겟 쉐입에 버텍스 리맵핑 (6버텍스)", command=lambda x: transfer_vertex_order_via_resultmesh_ui(), enable=False)
    cmds.button(label="중복점 검사", command=lambda x: check_duplicate_vertices_ui())
    cmds.textField("vertexReorderStatus", editable=False, text="")
    cmds.separator(h=10)
    cmds.button(label="UI 새로고침", command=lambda x: refresh_buttons())
    cmds.showWindow(win)
    refresh_buttons()

show_vertex_reorder_ui()
