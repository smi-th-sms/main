"""
SoftMod controller setup for Maya.

Usage:
    import importlib
    import softmod_ctrl_setup
    importlib.reload(softmod_ctrl_setup)

    # Create from the current object/component selection.
    softmod_ctrl_setup.create_softmod_ctrl()

    # Or open the small UI.
    softmod_ctrl_setup.show()
"""

import maya.cmds as cmds

try:
    from PySide2 import QtCore, QtWidgets
    from shiboken2 import wrapInstance
except ImportError:
    from PySide6 import QtCore, QtWidgets
    from shiboken6 import wrapInstance

import maya.OpenMayaUI as omui


WINDOW_NAME = "softModCtrlSetupWindow"


def _maya_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)


def _shape_or_transform_to_transform(node):
    if not cmds.objExists(node):
        return None

    if cmds.nodeType(node) in ("mesh", "nurbsSurface", "nurbsCurve"):
        parent = cmds.listRelatives(node, parent=True, fullPath=False) or []
        return parent[0] if parent else node

    return node


def _selection_info():
    selection = cmds.ls(selection=True, flatten=True) or []
    if not selection:
        cmds.error("Select one mesh/object or some components first.")

    first = selection[0]
    if "." in first:
        geo = first.split(".", 1)[0]
        target_items = selection
    else:
        geo = first
        target_items = [first]

    geo = _shape_or_transform_to_transform(geo)
    if not geo:
        cmds.error("Could not resolve the selected geometry.")

    shapes = cmds.listRelatives(geo, shapes=True, noIntermediate=True, fullPath=False) or []
    if not shapes and cmds.nodeType(geo) not in ("mesh", "nurbsSurface", "nurbsCurve"):
        cmds.error("Selection must be a deformable object or component.")

    bbox = cmds.exactWorldBoundingBox(target_items)
    center = (
        (bbox[0] + bbox[3]) * 0.5,
        (bbox[1] + bbox[4]) * 0.5,
        (bbox[2] + bbox[5]) * 0.5,
    )
    return geo, center


def _geometry_info(geometry):
    geo = _shape_or_transform_to_transform(geometry)
    if not geo:
        cmds.error("Could not resolve geometry: {0}".format(geometry))
    if not cmds.objExists(geo):
        cmds.error("Geometry does not exist: {0}".format(geometry))

    shapes = cmds.listRelatives(geo, shapes=True, noIntermediate=True, fullPath=False) or []
    if not shapes and cmds.nodeType(geo) not in ("mesh", "nurbsSurface", "nurbsCurve"):
        cmds.error("Geometry must be a deformable object: {0}".format(geometry))

    bbox = cmds.exactWorldBoundingBox(geo)
    center = (
        (bbox[0] + bbox[3]) * 0.5,
        (bbox[1] + bbox[4]) * 0.5,
        (bbox[2] + bbox[5]) * 0.5,
    )
    return geo, center


def _unique_name(name):
    if not cmds.objExists(name):
        return name

    index = 1
    while cmds.objExists("{0}_{1:02d}".format(name, index)):
        index += 1
    return "{0}_{1:02d}".format(name, index)


def _create_ctrl(name, radius, color_index):
    ctrl = cmds.circle(
        name=_unique_name(name),
        normal=(0, 1, 0),
        radius=radius,
        constructionHistory=False,
    )[0]

    for shape in cmds.listRelatives(ctrl, shapes=True, fullPath=False) or []:
        cmds.setAttr(shape + ".overrideEnabled", 1)
        cmds.setAttr(shape + ".overrideColor", color_index)
        cmds.setAttr(shape + ".lineWidth", 2.0)

    return ctrl


def _create_center_locator(name, display_scale, color_index):
    locator = cmds.spaceLocator(name=_unique_name(name))[0]
    shape = cmds.listRelatives(locator, shapes=True, fullPath=False)[0]
    cmds.setAttr(shape + ".localScaleX", display_scale)
    cmds.setAttr(shape + ".localScaleY", display_scale)
    cmds.setAttr(shape + ".localScaleZ", display_scale)
    cmds.setAttr(shape + ".overrideEnabled", 1)
    cmds.setAttr(shape + ".overrideColor", color_index)
    return locator


def _set_curve_color(node, color_index, line_width=1.5):
    for shape in cmds.listRelatives(node, shapes=True, fullPath=False) or []:
        cmds.setAttr(shape + ".overrideEnabled", 1)
        cmds.setAttr(shape + ".overrideColor", int(color_index))
        if cmds.objExists(shape + ".lineWidth"):
            cmds.setAttr(shape + ".lineWidth", float(line_width))


def _set_template_display(node, enabled=True):
    display_type = 1 if enabled else 0
    targets = [node] + (cmds.listRelatives(node, shapes=True, fullPath=False) or [])
    for target in targets:
        if cmds.objExists(target + ".overrideEnabled"):
            cmds.setAttr(target + ".overrideEnabled", 1)
        if cmds.objExists(target + ".overrideDisplayType"):
            cmds.setAttr(target + ".overrideDisplayType", display_type)


def _lock_attrs(node, attrs):
    for attr in attrs:
        plug = node + "." + attr
        if cmds.objExists(plug):
            cmds.setAttr(plug, lock=True, keyable=False, channelBox=False)


def _has_softmod_handle_shape(node):
    shapes = cmds.listRelatives(node, shapes=True, fullPath=False) or []
    return any(cmds.nodeType(shape) == "softModHandle" for shape in shapes)


def _resolve_softmod_nodes(result_nodes, geometry, softmod_name, handle_name):
    softmod = None
    handle = None

    for node in result_nodes:
        if not cmds.objExists(node):
            continue
        node_type = cmds.nodeType(node)
        if node_type == "softMod":
            softmod = node
        elif node_type == "transform" and _has_softmod_handle_shape(node):
            handle = node

    if handle and not softmod:
        shapes = cmds.listRelatives(handle, shapes=True, fullPath=False) or []
        for shape in shapes:
            connections = cmds.listConnections(shape, source=True, destination=True) or []
            for node in connections:
                if cmds.nodeType(node) == "softMod":
                    softmod = node
                    break
            if softmod:
                break

    if not softmod:
        history = cmds.listHistory(geometry, pruneDagObjects=True) or []
        softmods = [node for node in history if cmds.nodeType(node) == "softMod"]
        if softmods:
            softmod = softmods[0]

    if softmod and not handle:
        matrices = cmds.listConnections(softmod + ".matrix", source=True, destination=False) or []
        for node in matrices:
            transform = _shape_or_transform_to_transform(node)
            if transform and _has_softmod_handle_shape(transform):
                handle = transform
                break

    if not softmod or not handle:
        cmds.error("Could not resolve softMod deformer and handle from Maya result: {0}".format(result_nodes))

    softmod = cmds.rename(softmod, _unique_name(softmod_name))
    handle = cmds.rename(handle, _unique_name(handle_name))
    return softmod, handle


def _connect_center_locator(center_locator, geometry, softmod):
    center_shape = cmds.listRelatives(center_locator, shapes=True, fullPath=False)[0]
    point_matrix = cmds.createNode(
        "pointMatrixMult",
        name=_unique_name(center_locator.replace("_CENTER_LOC", "_centerToLocal_PMM")),
    )

    cmds.connectAttr(center_shape + ".worldPosition[0]", point_matrix + ".inPoint", force=True)
    cmds.connectAttr(geometry + ".worldInverseMatrix[0]", point_matrix + ".inMatrix", force=True)

    for axis in ("X", "Y", "Z"):
        destination = softmod + ".falloffCenter" + axis
        existing = cmds.listConnections(destination, source=True, destination=False, plugs=True) or []
        for source in existing:
            cmds.disconnectAttr(source, destination)
        cmds.connectAttr(point_matrix + ".output" + axis, destination, force=True)

    return point_matrix


def _connect_world_matrix_to_transform(source, target, name):
    decompose = cmds.createNode("decomposeMatrix", name=_unique_name(name))
    cmds.connectAttr(source + ".worldMatrix[0]", decompose + ".inputMatrix", force=True)

    for axis in ("X", "Y", "Z"):
        cmds.connectAttr(decompose + ".outputTranslate" + axis, target + ".translate" + axis, force=True)
        cmds.connectAttr(decompose + ".outputRotate" + axis, target + ".rotate" + axis, force=True)
        cmds.connectAttr(decompose + ".outputScale" + axis, target + ".scale" + axis, force=True)

    return decompose


def _connect_center_to_ctrl_group(center_locator, ctrl_group):
    return _connect_world_matrix_to_transform(
        center_locator,
        ctrl_group,
        center_locator.replace("_CENTER_LOC", "_centerToCtrlGrp_DCM"),
    )


def _connect_center_to_handle_pivots(center_locator, handle):
    """Drive the handle's rotate and scale pivots from its center locator."""
    mult_matrix_name = handle + "_MM"
    decompose_matrix_name = handle + "_DM"

    if cmds.objExists(mult_matrix_name):
        if cmds.nodeType(mult_matrix_name) != "multMatrix":
            cmds.error("Expected {0} to be a multMatrix node.".format(mult_matrix_name))
        mult_matrix = mult_matrix_name
    else:
        mult_matrix = cmds.createNode("multMatrix", name=mult_matrix_name)

    if cmds.objExists(decompose_matrix_name):
        if cmds.nodeType(decompose_matrix_name) != "decomposeMatrix":
            cmds.error("Expected {0} to be a decomposeMatrix node.".format(decompose_matrix_name))
        decompose_matrix = decompose_matrix_name
    else:
        decompose_matrix = cmds.createNode("decomposeMatrix", name=decompose_matrix_name)

    destinations = (
        mult_matrix + ".matrixIn[0]",
        mult_matrix + ".matrixIn[1]",
        decompose_matrix + ".inputMatrix",
        handle + ".scalePivot",
        handle + ".rotatePivot",
    )
    for destination in destinations:
        existing = cmds.listConnections(destination, source=True, destination=False, plugs=True) or []
        for source in existing:
            cmds.disconnectAttr(source, destination)

    cmds.connectAttr(handle + ".parentInverseMatrix[0]", mult_matrix + ".matrixIn[0]", force=True)
    cmds.connectAttr(center_locator + ".worldMatrix[0]", mult_matrix + ".matrixIn[1]", force=True)
    cmds.connectAttr(mult_matrix + ".matrixSum", decompose_matrix + ".inputMatrix", force=True)
    cmds.connectAttr(decompose_matrix + ".outputTranslate", handle + ".scalePivot", force=True)
    cmds.connectAttr(decompose_matrix + ".outputTranslate", handle + ".rotatePivot", force=True)

    return {
        "multMatrix": mult_matrix,
        "decomposeMatrix": decompose_matrix,
        "scalePivot": decompose_matrix + ".outputTranslate",
        "rotatePivot": decompose_matrix + ".outputTranslate",
    }


def _connect_ctrl_to_handle(ctrl, handle):
    connections = []
    for compound in ("translate", "rotate", "scale"):
        for axis in ("X", "Y", "Z"):
            source = ctrl + "." + compound + axis
            destination = handle + "." + compound + axis
            existing = cmds.listConnections(destination, source=True, destination=False, plugs=True) or []
            for plug in existing:
                cmds.disconnectAttr(plug, destination)
            cmds.connectAttr(source, destination, force=True)
            connections.append((source, destination))
    return connections


def _connect_ctrl_group_bind_pre_matrix(ctrl_group, softmod):
    existing = cmds.listConnections(
        softmod + ".bindPreMatrix",
        source=True,
        destination=False,
        plugs=True,
    ) or []
    for source in existing:
        cmds.disconnectAttr(source, softmod + ".bindPreMatrix")

    cmds.connectAttr(ctrl_group + ".worldInverseMatrix[0]", softmod + ".bindPreMatrix", force=True)
    return ctrl_group + ".worldInverseMatrix[0]"


def _reset_bind_pre_matrix(softmod):
    existing = cmds.listConnections(
        softmod + ".bindPreMatrix",
        source=True,
        destination=False,
        plugs=True,
    ) or []
    for source in existing:
        cmds.disconnectAttr(source, softmod + ".bindPreMatrix")

    cmds.setAttr(
        softmod + ".bindPreMatrix",
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
        type="matrix",
    )
    return softmod + ".bindPreMatrix"


def _connect_ctrl_deform_matrix(ctrl, softmod):
    existing = cmds.listConnections(
        softmod + ".matrix",
        source=True,
        destination=False,
        plugs=True,
    ) or []
    for source in existing:
        cmds.disconnectAttr(source, softmod + ".matrix")

    cmds.connectAttr(ctrl + ".matrix", softmod + ".matrix", force=True)
    _reset_bind_pre_matrix(softmod)
    return ctrl + ".matrix"


def _disconnect_softmod_handle_xforms(softmod):
    existing = cmds.listConnections(
        softmod + ".softModXforms",
        source=True,
        destination=False,
        plugs=True,
    ) or []
    for source in existing:
        cmds.disconnectAttr(source, softmod + ".softModXforms")
    return existing


def _parent_handle_under_ctrl_group(handle, ctrl_group):
    parent = cmds.listRelatives(handle, parent=True, fullPath=False) or []
    if not parent or parent[0] != ctrl_group:
        cmds.parent(handle, ctrl_group)

    for axis in ("X", "Y", "Z"):
        cmds.setAttr(handle + ".translate" + axis, 0.0)
        cmds.setAttr(handle + ".rotate" + axis, 0.0)
        cmds.setAttr(handle + ".scale" + axis, 1.0)


def _create_falloff_visual(name, ctrl, color_index=17):
    group = cmds.group(empty=True, name=_unique_name(name))
    cmds.parent(group, ctrl)
    for axis in ("X", "Y", "Z"):
        cmds.setAttr(group + ".translate" + axis, 0.0)
        cmds.setAttr(group + ".rotate" + axis, 0.0)
        cmds.setAttr(group + ".scale" + axis, 1.0)

    shapes = []
    circle_data = [
        ("XY", (0, 0, 1)),
        ("YZ", (1, 0, 0)),
        ("XZ", (0, 1, 0)),
    ]
    for suffix, normal in circle_data:
        temp = cmds.circle(
            name=_unique_name(name + "_" + suffix),
            normal=normal,
            radius=1.0,
            constructionHistory=False,
        )[0]
        for shape in cmds.listRelatives(temp, shapes=True, fullPath=False) or []:
            shape = cmds.rename(shape, _unique_name(name + "_" + suffix + "Shape"))
            cmds.parent(shape, group, shape=True, relative=True)
            shapes.append(shape)
        cmds.delete(temp)

    _set_curve_color(group, color_index, 1.25)
    _set_template_display(group, True)

    if not cmds.objExists(ctrl + ".falloffVisibility"):
        cmds.addAttr(ctrl, longName="falloffVisibility", attributeType="bool",
                     defaultValue=True, keyable=True)

    for axis in ("X", "Y", "Z"):
        cmds.connectAttr(ctrl + ".falloffRadius", group + ".scale" + axis, force=True)
    cmds.connectAttr(ctrl + ".falloffVisibility", group + ".visibility", force=True)

    return {
        "group": group,
        "shapes": shapes,
    }


def create_softmod_ctrl(
    name="softArea",
    falloff_radius=3.0,
    ctrl_size=1.0,
    color_index=17,
    hide_handle=True,
    geometry=None,
):
    """
    Create a softMod deformer controlled by a curve controller.

    Select a mesh/object, or select vertices/edges/faces on the mesh. Component
    selection is usually best because the setup center is taken from the
    selected region.
    """
    if geometry:
        geo, center = _geometry_info(geometry)
    else:
        geo, center = _selection_info()

    base = _unique_name(name)
    softmod_name = base + "_softMod"
    handle_name = base + "_softMod_HDL"
    ctrl_name = base + "_CTRL"
    group_name = base + "_CTRL_GRP"
    center_name = base + "_CENTER_LOC"
    falloff_visual_name = base + "_FALLOFF_VIS"

    result = cmds.softMod(
        geo,
        name=softmod_name,
        falloffCenter=center,
        falloffRadius=float(falloff_radius),
    )
    softmod, handle = _resolve_softmod_nodes(result, geo, softmod_name, handle_name)

    ctrl = _create_ctrl(ctrl_name, float(ctrl_size), int(color_index))
    group = cmds.group(ctrl, name=_unique_name(group_name))
    cmds.xform(group, worldSpace=True, translation=center)

    center_locator = _create_center_locator(center_name, float(ctrl_size) * 0.35, 18)
    cmds.xform(center_locator, worldSpace=True, translation=center)
    _parent_handle_under_ctrl_group(handle, group)

    cmds.addAttr(ctrl, longName="softMod", attributeType="enum", enumName="-----", keyable=True)
    cmds.setAttr(ctrl + ".softMod", lock=True)
    cmds.addAttr(ctrl, longName="falloffRadius", attributeType="double", minValue=0.001,
                 defaultValue=float(falloff_radius), keyable=True)
    cmds.addAttr(ctrl, longName="envelope", attributeType="double", minValue=0.0,
                 maxValue=1.0, defaultValue=1.0, keyable=True)
    cmds.addAttr(ctrl, longName="handleVisibility", attributeType="bool",
                 defaultValue=not hide_handle, keyable=True)
    cmds.addAttr(ctrl, longName="centerVisibility", attributeType="bool",
                 defaultValue=True, keyable=True)

    cmds.connectAttr(ctrl + ".falloffRadius", softmod + ".falloffRadius", force=True)
    cmds.connectAttr(ctrl + ".envelope", softmod + ".envelope", force=True)
    cmds.connectAttr(ctrl + ".handleVisibility", handle + ".visibility", force=True)
    cmds.connectAttr(ctrl + ".centerVisibility", center_locator + ".visibility", force=True)

    point_matrix = _connect_center_locator(center_locator, geo, softmod)
    center_to_group = _connect_center_to_ctrl_group(center_locator, group)
    ctrl_to_handle = _connect_ctrl_to_handle(ctrl, handle)
    handle_pivots = _connect_center_to_handle_pivots(center_locator, handle)
    bind_pre_matrix = _connect_ctrl_group_bind_pre_matrix(group, softmod)
    falloff_visual = _create_falloff_visual(falloff_visual_name, ctrl, 17)

    if hide_handle:
        cmds.setAttr(ctrl + ".handleVisibility", False)

    _lock_attrs(ctrl, ("sx", "sy", "sz", "v"))

    cmds.select(ctrl)
    return {
        "geometry": geo,
        "softMod": softmod,
        "handle": handle,
        "controller": ctrl,
        "group": group,
        "centerLocator": center_locator,
        "centerToLocal": point_matrix,
        "centerToGroup": center_to_group,
        "ctrlToHandle": ctrl_to_handle,
        "handlePivots": handle_pivots,
        "bindPreMatrix": bind_pre_matrix,
        "falloffVisual": falloff_visual["group"],
        "falloffVisualShapes": falloff_visual["shapes"],
    }


def set_center_from_selection(softmod_or_ctrl=None):
    """
    Move an existing setup's center locator to the current selection center.

    Select the setup controller plus the target components, or pass the
    controller/deformer name and select only the target components.
    """
    selection = cmds.ls(selection=True, flatten=True) or []
    if not selection:
        cmds.error("Select target components or an object first.")

    setup_node = softmod_or_ctrl
    if not setup_node:
        for item in selection:
            node = item.split(".", 1)[0]
            if cmds.objExists(node + ".centerVisibility") or cmds.nodeType(node) == "softMod":
                setup_node = node
                break

    if not setup_node:
        cmds.error("Select the softMod controller too, or pass its name.")

    center_locator = _find_center_locator(setup_node)
    target_items = []
    for item in selection:
        node = item.split(".", 1)[0]
        if node != setup_node and node != center_locator:
            target_items.append(item)

    if not target_items:
        cmds.error("Select the target components/object as well as the setup controller.")

    bbox = cmds.exactWorldBoundingBox(target_items)
    center = (
        (bbox[0] + bbox[3]) * 0.5,
        (bbox[1] + bbox[4]) * 0.5,
        (bbox[2] + bbox[5]) * 0.5,
    )
    cmds.xform(center_locator, worldSpace=True, translation=center)
    return center_locator


def _find_center_locator(setup_node):
    if cmds.objExists(setup_node + ".centerVisibility"):
        candidates = cmds.listConnections(setup_node + ".centerVisibility", destination=True,
                                          source=False) or []
        for candidate in candidates:
            if cmds.objExists(candidate):
                return candidate

    if cmds.nodeType(setup_node) == "softMod":
        source = cmds.listConnections(setup_node + ".falloffCenter", source=True,
                                      destination=False) or []
        for plug_node in source:
            if cmds.nodeType(plug_node) == "locator":
                parent = cmds.listRelatives(plug_node, parent=True, fullPath=False) or []
                if parent:
                    return parent[0]
            if cmds.objExists(plug_node):
                return plug_node

    cmds.error("Could not find this setup's center locator.")


def _ensure_falloff_visual(ctrl, center_locator=None):
    existing = cmds.listConnections(
        ctrl + ".falloffVisibility",
        source=False,
        destination=True,
    ) if cmds.objExists(ctrl + ".falloffVisibility") else []

    for node in existing or []:
        if cmds.objExists(node) and node.endswith("_FALLOFF_VIS"):
            return node

    base = ctrl.replace("_CTRL", "")
    visual = _create_falloff_visual(base + "_FALLOFF_VIS", ctrl, 17)
    return visual["group"]


def template_existing_falloff_visuals(enabled=True):
    visuals = cmds.ls("*_FALLOFF_VIS", type="transform") or []
    for visual in visuals:
        _set_template_display(visual, enabled)
    return visuals


def _find_softmod_from_ctrl(ctrl):
    for attr in ("envelope", "falloffRadius"):
        plug = ctrl + "." + attr
        if not cmds.objExists(plug):
            continue

        connections = cmds.listConnections(plug, destination=True, source=False) or []
        for node in connections:
            if cmds.nodeType(node) == "softMod":
                return node

    cmds.error("Could not find a softMod connected to {0}.".format(ctrl))


def _find_geometry_from_softmod(softmod):
    geometry = cmds.deformer(softmod, query=True, geometry=True) or []
    if not geometry:
        cmds.error("Could not find geometry affected by {0}.".format(softmod))
    return _shape_or_transform_to_transform(geometry[0])


def _find_handle_from_softmod(softmod):
    matrices = cmds.listConnections(softmod + ".matrix", source=True, destination=False) or []
    for node in matrices:
        transform = _shape_or_transform_to_transform(node)
        if transform and _has_softmod_handle_shape(transform):
            return transform
    cmds.error("Could not find handle affected by {0}.".format(softmod))


def _delete_constraints_on(node):
    constraints = []
    for attr in ("translate", "rotate", "scale"):
        connections = cmds.listConnections(node + "." + attr, source=True, destination=False) or []
        constraints.extend(
            connection for connection in connections
            if cmds.nodeType(connection).endswith("Constraint")
        )
    if constraints:
        cmds.delete(list(set(constraints)))
    return constraints


def _find_ctrl_group(ctrl):
    parent = cmds.listRelatives(ctrl, parent=True, fullPath=False) or []
    if parent:
        return parent[0]
    cmds.error("Could not find controller group for {0}.".format(ctrl))


def upgrade_selected_setup():
    """
    Add the editable center locator to an older controller setup.

    Select a controller made by the first version of this tool, then run this
    once. New setups already include this locator.
    """
    selection = cmds.ls(selection=True) or []
    if not selection:
        cmds.error("Select the old softMod controller first.")

    ctrl = selection[0]
    if not cmds.objExists(ctrl + ".envelope"):
        cmds.error("Select the softMod controller, not the handle or mesh.")

    softmod = _find_softmod_from_ctrl(ctrl)
    geo = _find_geometry_from_softmod(softmod)
    handle = _find_handle_from_softmod(softmod)

    if cmds.objExists(ctrl + ".centerVisibility"):
        try:
            return _find_center_locator(ctrl)
        except RuntimeError:
            pass
    else:
        cmds.addAttr(ctrl, longName="centerVisibility", attributeType="bool",
                     defaultValue=True, keyable=True)

    current_center = cmds.getAttr(softmod + ".falloffCenter")[0]
    center_locator = _create_center_locator(ctrl.replace("_CTRL", "_CENTER_LOC"), 0.35, 18)
    cmds.xform(center_locator, worldSpace=True, translation=current_center)

    cmds.connectAttr(ctrl + ".centerVisibility", center_locator + ".visibility", force=True)
    _connect_center_locator(center_locator, geo, softmod)
    ctrl_group = _find_ctrl_group(ctrl)
    _connect_center_to_ctrl_group(center_locator, ctrl_group)
    _connect_center_to_handle_pivots(center_locator, handle)
    _connect_ctrl_group_bind_pre_matrix(ctrl_group, softmod)
    _delete_constraints_on(handle)
    _parent_handle_under_ctrl_group(handle, ctrl_group)
    _connect_ctrl_to_handle(ctrl, handle)
    _ensure_falloff_visual(ctrl, center_locator)

    cmds.connectAttr(ctrl + ".envelope", softmod + ".envelope", force=True)
    cmds.select(center_locator)
    return center_locator


def _closest_vertex_to_point(geometry, point):
    count = cmds.polyEvaluate(geometry, vertex=True)
    if not count:
        cmds.error("Geometry has no vertices: {0}".format(geometry))

    best_vertex = None
    best_distance = None
    for index in range(count):
        vertex = "{0}.vtx[{1}]".format(geometry, index)
        pos = cmds.xform(vertex, query=True, worldSpace=True, translation=True)
        dist = (
            (pos[0] - point[0]) ** 2 +
            (pos[1] - point[1]) ** 2 +
            (pos[2] - point[2]) ** 2
        )
        if best_distance is None or dist < best_distance:
            best_vertex = vertex
            best_distance = dist

    return best_vertex


def _distance(a, b):
    return (
        (a[0] - b[0]) ** 2 +
        (a[1] - b[1]) ** 2 +
        (a[2] - b[2]) ** 2
    ) ** 0.5


def delete_setup_by_prefix(prefix="gotoHand_softArea"):
    nodes = cmds.ls(prefix + "*", long=False) or []
    if not nodes:
        return []

    protected = set(["gotoHand_hand_base_BS", "gotoHand_hand_base_BSShape"])
    delete_nodes = [node for node in nodes if node not in protected and cmds.objExists(node)]
    if delete_nodes:
        cmds.delete(delete_nodes)
    return delete_nodes


def create_and_test_on_goto_hand():
    """
    Create and verify a setup directly on gotoHand_hand_base_BS.

    The setup is left in a neutral pose after the test.
    """
    target = "gotoHand_hand_base_BS"
    if not cmds.objExists(target):
        cmds.error("{0} does not exist in the current scene.".format(target))

    deleted = delete_setup_by_prefix("gotoHand_softArea")
    setup = create_softmod_ctrl(
        name="gotoHand_softArea",
        falloff_radius=3.0,
        ctrl_size=0.35,
        color_index=17,
        hide_handle=True,
        geometry=target,
    )

    softmod = setup["softMod"]
    ctrl = setup["controller"]
    center_locator = setup["centerLocator"]
    geo = setup["geometry"]

    center = cmds.xform(center_locator, query=True, worldSpace=True, translation=True)
    vertex = _closest_vertex_to_point(geo, center)
    base_pos = cmds.xform(vertex, query=True, worldSpace=True, translation=True)
    visual = setup.get("falloffVisual")

    cmds.setAttr(ctrl + ".envelope", 1.0)
    visual_before_ctrl_move = cmds.xform(visual, query=True, worldSpace=True, translation=True) \
        if visual and cmds.objExists(visual) else None
    cmds.setAttr(ctrl + ".translateX", 0.25)
    cmds.refresh(force=True)
    on_pos = cmds.xform(vertex, query=True, worldSpace=True, translation=True)
    visual_after_ctrl_move = cmds.xform(visual, query=True, worldSpace=True, translation=True) \
        if visual and cmds.objExists(visual) else None

    cmds.setAttr(ctrl + ".envelope", 0.0)
    cmds.refresh(force=True)
    off_pos = cmds.xform(vertex, query=True, worldSpace=True, translation=True)

    original_falloff = cmds.getAttr(softmod + ".falloffCenter")[0]

    cmds.setAttr(ctrl + ".translateX", 0.0)
    cmds.setAttr(ctrl + ".envelope", 1.0)
    cmds.refresh(force=True)
    group_before = cmds.xform(setup["group"], query=True, worldSpace=True, translation=True)
    handle_before = cmds.xform(setup["handle"], query=True, worldSpace=True, translation=True)
    neutral_before_locator_move = cmds.xform(vertex, query=True, worldSpace=True, translation=True)

    cmds.setAttr(center_locator + ".translateX", cmds.getAttr(center_locator + ".translateX") + 0.5)
    cmds.refresh(force=True)
    moved_falloff = cmds.getAttr(softmod + ".falloffCenter")[0]
    group_after = cmds.xform(setup["group"], query=True, worldSpace=True, translation=True)
    handle_after = cmds.xform(setup["handle"], query=True, worldSpace=True, translation=True)
    neutral_after_locator_move = cmds.xform(vertex, query=True, worldSpace=True, translation=True)

    visual_before = cmds.getAttr(visual + ".scale")[0] if visual and cmds.objExists(visual) else None
    cmds.setAttr(ctrl + ".falloffRadius", 1.5)
    cmds.refresh(force=True)
    visual_after = cmds.getAttr(visual + ".scale")[0] if visual and cmds.objExists(visual) else None
    cmds.setAttr(ctrl + ".falloffRadius", 3.0)

    cmds.setAttr(center_locator + ".translateX", cmds.getAttr(center_locator + ".translateX") - 0.5)
    cmds.setAttr(ctrl + ".translateX", 0.0)
    cmds.setAttr(ctrl + ".envelope", 1.0)
    cmds.refresh(force=True)
    final_pos = cmds.xform(vertex, query=True, worldSpace=True, translation=True)

    result = {
        "geometry": geo,
        "softMod": softmod,
        "controller": ctrl,
        "handle": setup["handle"],
        "centerLocator": center_locator,
        "testedVertex": vertex,
        "deformDistanceEnvelope1": _distance(base_pos, on_pos),
        "deformDistanceEnvelope0": _distance(base_pos, off_pos),
        "finalNeutralDistance": _distance(base_pos, final_pos),
        "neutralDistanceFromLocatorOnlyMove": _distance(
            neutral_before_locator_move,
            neutral_after_locator_move,
        ),
        "falloffCenterBeforeMove": original_falloff,
        "falloffCenterAfterLocatorMove": moved_falloff,
        "ctrlGroupMoveDistanceFromLocator": _distance(group_before, group_after),
        "handleMoveDistanceFromLocator": _distance(handle_before, handle_after),
        "falloffVisual": visual,
        "falloffVisualScaleBefore": visual_before,
        "falloffVisualScaleAfterRadiusChange": visual_after,
        "falloffVisualMoveDistanceFromCtrl": _distance(
            visual_before_ctrl_move,
            visual_after_ctrl_move,
        ) if visual_before_ctrl_move and visual_after_ctrl_move else None,
        "falloffVisualParent": cmds.listRelatives(visual, parent=True, fullPath=False) or []
            if visual and cmds.objExists(visual) else None,
        "falloffVisualLocalTranslate": cmds.getAttr(visual + ".translate")[0]
            if visual and cmds.objExists(visual) else None,
        "falloffVisualLocalRotate": cmds.getAttr(visual + ".rotate")[0]
            if visual and cmds.objExists(visual) else None,
        "falloffVisualChildTransforms": cmds.listRelatives(visual, children=True, type="transform") or []
            if visual and cmds.objExists(visual) else None,
        "falloffVisualShapeCount": len(cmds.listRelatives(visual, shapes=True) or [])
            if visual and cmds.objExists(visual) else None,
        "falloffVisualTemplate": cmds.getAttr(visual + ".overrideDisplayType")
            if visual and cmds.objExists(visual) else None,
        "falloffVisualShapeTemplates": [
            cmds.getAttr(shape + ".overrideDisplayType")
            for shape in (cmds.listRelatives(visual, shapes=True, fullPath=False) or [])
        ] if visual and cmds.objExists(visual) else None,
        "deletedOldTestNodes": deleted,
    }
    cmds.select(ctrl)
    return result


class SoftModCtrlWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(SoftModCtrlWindow, self).__init__(parent or _maya_window())
        self.setObjectName(WINDOW_NAME)
        self.setWindowTitle("SoftMod Ctrl Setup")
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(320)
        self._build()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit("softArea")
        self.radius_spin = QtWidgets.QDoubleSpinBox()
        self.radius_spin.setRange(0.001, 100000.0)
        self.radius_spin.setValue(3.0)
        self.radius_spin.setDecimals(3)
        self.radius_spin.setSingleStep(0.25)

        self.size_spin = QtWidgets.QDoubleSpinBox()
        self.size_spin.setRange(0.001, 100000.0)
        self.size_spin.setValue(1.0)
        self.size_spin.setDecimals(3)
        self.size_spin.setSingleStep(0.25)

        self.color_spin = QtWidgets.QSpinBox()
        self.color_spin.setRange(0, 31)
        self.color_spin.setValue(17)

        self.hide_handle_check = QtWidgets.QCheckBox()
        self.hide_handle_check.setChecked(True)

        form.addRow("Name", self.name_edit)
        form.addRow("Falloff Radius", self.radius_spin)
        form.addRow("Ctrl Size", self.size_spin)
        form.addRow("Color Index", self.color_spin)
        form.addRow("Hide Handle", self.hide_handle_check)
        layout.addLayout(form)

        button = QtWidgets.QPushButton("Create SoftMod Ctrl")
        button.clicked.connect(self._create)
        layout.addWidget(button)

        upgrade_button = QtWidgets.QPushButton("Upgrade Selected Old Ctrl")
        upgrade_button.clicked.connect(upgrade_selected_setup)
        layout.addWidget(upgrade_button)

        center_button = QtWidgets.QPushButton("Set Center From Selection")
        center_button.clicked.connect(set_center_from_selection)
        layout.addWidget(center_button)

    def _create(self):
        create_softmod_ctrl(
            name=self.name_edit.text().strip() or "softArea",
            falloff_radius=self.radius_spin.value(),
            ctrl_size=self.size_spin.value(),
            color_index=self.color_spin.value(),
            hide_handle=self.hide_handle_check.isChecked(),
        )


def show():
    for widget in QtWidgets.QApplication.allWidgets():
        if widget.objectName() == WINDOW_NAME:
            widget.close()
            widget.deleteLater()

    window = SoftModCtrlWindow()
    window.show()
    return window
