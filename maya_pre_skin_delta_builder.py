import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma


NODE = "blendShape4"
BASE = "gotoKey_finger_base_MESH"
TARGET = "gotoKey_gotoKey_base_MESH"
SKIN = "skinCluster1"
TARGET_INDEX = 0
TARGET_ITEM = 6000
FORMULA_TOLERANCE = 1.0e-4


def dag_path(node):
    selection = om.MSelectionList()
    selection.add(node)
    return selection.getDagPath(0)


def matrix_from_attr(node, attribute):
    values = cmds.getAttr("{}.{}".format(node, attribute))
    return om.MMatrix(values)


def matrix_from_influence(influence):
    return om.MMatrix(cmds.xform(influence, query=True, matrix=True, worldSpace=True))


def max_error(left, right):
    return max(((a - b).length() for a, b in zip(left, right)), default=0.0)


def get_mesh_data_from_plug(plug):
    return om.MFnMesh(plug.asMDataHandle().data())


def get_skin_data(base_path):
    skin_selection = om.MSelectionList()
    skin_selection.add(SKIN)
    skin_fn = oma.MFnSkinCluster(skin_selection.getDependNode(0))
    input_plug = skin_fn.findPlug("input", False).elementByLogicalIndex(0).child(0)
    input_mesh_fn = get_mesh_data_from_plug(input_plug)
    input_points = input_mesh_fn.getPoints(om.MSpace.kObject)

    component_fn = om.MFnSingleIndexedComponent()
    component = component_fn.create(om.MFn.kMeshVertComponent)
    component_fn.addElements(range(len(input_points)))
    weights, influence_count = skin_fn.getWeights(base_path, component)
    influences = skin_fn.influenceObjects()

    geom_matrix = matrix_from_attr(SKIN, "geomMatrix")
    bind_matrices = []
    influence_matrices = []
    for influence_index, influence in enumerate(influences):
        bind_values = cmds.getAttr("{}.bindPreMatrix[{}]".format(SKIN, influence_index))
        bind_matrices.append(om.MMatrix(bind_values))
        influence_matrices.append(matrix_from_influence(influence.partialPathName()))

    blended_matrices = []
    for vertex_index in range(len(input_points)):
        blended = om.MMatrix([[0.0] * 4 for _ in range(4)])
        for influence_index in range(len(influences)):
            weight = weights[vertex_index * influence_count + influence_index]
            if weight:
                blended += (
                    bind_matrices[influence_index]
                    * influence_matrices[influence_index]
                ) * weight
        blended_matrices.append(blended)

    return input_points, geom_matrix, blended_matrices


def set_target_delta(geometry_index, delta_points):
    selection = om.MSelectionList()
    selection.add(NODE)
    node_fn = om.MFnDependencyNode(selection.getDependNode(0))
    input_target = node_fn.findPlug("inputTarget", False)
    target_item = (
        input_target.elementByLogicalIndex(geometry_index)
        .child(0)
        .elementByLogicalIndex(TARGET_INDEX)
        .child(0)
        .elementByLogicalIndex(TARGET_ITEM)
    )
    points_plug = target_item.child(3)
    point_data = om.MFnPointArrayData()
    points_object = point_data.create(delta_points)
    points_plug.setMObject(points_object)


def main():
    required = (NODE, BASE, TARGET, SKIN)
    missing = [node for node in required if not cmds.objExists(node)]
    if missing:
        raise RuntimeError("Missing nodes: {}".format(", ".join(missing)))

    base_path = dag_path(BASE)
    target_path = dag_path(TARGET)
    base_fn = om.MFnMesh(base_path)
    target_fn = om.MFnMesh(target_path)
    target_world_points = target_fn.getPoints(om.MSpace.kWorld)
    input_points, geom_matrix, blended_matrices = get_skin_data(base_path)
    if len(input_points) != len(target_world_points):
        raise RuntimeError("Vertex count mismatch.")

    base_inverse_geom = geom_matrix.inverse()
    desired_input_points = om.MPointArray()
    for target_world_point, blended_matrix in zip(target_world_points, blended_matrices):
        desired_input_points.append(target_world_point * blended_matrix.inverse() * base_inverse_geom)

    current_output_points = base_fn.getPoints(om.MSpace.kWorld)
    predicted_output_points = om.MPointArray()
    for input_point, blended_matrix in zip(desired_input_points, blended_matrices):
        predicted_output_points.append(input_point * geom_matrix * blended_matrix)
    formula_error = max_error(predicted_output_points, target_world_points)
    if formula_error > FORMULA_TOLERANCE:
        raise RuntimeError(
            "Skin inverse validation failed: max error {:.9f}".format(formula_error)
        )

    geometry_indices = cmds.getAttr(NODE + ".inputTarget", multiIndices=True) or [0]
    geometry_index = geometry_indices[0]
    delta_points = om.MPointArray()
    for desired_point, input_point in zip(desired_input_points, input_points):
        delta_points.append(desired_point - input_point)

    cmds.undoInfo(openChunk=True, chunkName="Build pre-skin target delta")
    try:
        cmds.setAttr("{}.weight[{}]".format(NODE, TARGET_INDEX), 0.0)
        set_target_delta(geometry_index, delta_points)
        cmds.refresh(force=True)
    finally:
        cmds.setAttr("{}.weight[{}]".format(NODE, TARGET_INDEX), 0.0)
        cmds.undoInfo(closeChunk=True)

    print(
        "Pre-skin delta written: {} vertices, validation error {:.9f}".format(
            len(delta_points), formula_error
        )
    )


main()
