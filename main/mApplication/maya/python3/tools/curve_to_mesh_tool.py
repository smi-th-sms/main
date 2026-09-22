# -*- coding: utf-8 -*-
"""Convert selected NURBS curves to polygon sweep meshes.

Usage in Maya:

    import curve_to_mesh_tool
    curve_to_mesh_tool.show()

Or, for a shelf button:

    import curve_to_mesh_tool
    curve_to_mesh_tool.run(radius=0.1, sides=8)
"""
from __future__ import print_function

import math

import maya.cmds as cmds


WIN_ID = "curveToMeshToolWin"
PROFILE_TUBE = "Tube"
PROFILE_PLANE = "Plane"
DEFAULT_RAMP_STRING = "1,0,1,1,1,1"
NORMAL_FACE_MESH = "Face / Mesh Normal"
RAMP_INTERPS = {
    "None": 0,
    "Linear": 1,
    "Smooth": 2,
    "Spline": 3,
}
NORMAL_SOURCES = (
    NORMAL_FACE_MESH,
    "Mesh Average Normal",
    "Object X",
    "Object Y",
    "Object Z",
    "Object -X",
    "Object -Y",
    "Object -Z",
)


def _short_name(node):
    return node.split("|")[-1].split(":")[-1]


def _base_curve_name(curve):
    base = _short_name(curve)
    for suffix in ("_crv", "_curve", "Crv", "Curve", "_CRV", "_CURVE"):
        if base.endswith(suffix):
            return base[:-len(suffix)] or base
    return base


def _as_curve_transform(item):
    """Return a transform with a non-intermediate nurbsCurve shape, if any."""
    if not item:
        return None

    node = item.split(".", 1)[0]
    long_nodes = cmds.ls(node, long=True) or []
    if not long_nodes:
        return None
    node = long_nodes[0]

    node_type = cmds.nodeType(node)
    if node_type == "nurbsCurve":
        parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
        return parents[0] if parents else None

    if node_type != "transform":
        return None

    shapes = cmds.listRelatives(node, shapes=True, noIntermediate=True,
                                fullPath=True) or []
    for shape in shapes:
        if cmds.nodeType(shape) == "nurbsCurve":
            return node
    return None


def selected_curves(selection=None):
    """Return selected curve transforms in selection order."""
    if selection is None:
        selection = cmds.ls(selection=True, long=True, flatten=True) or []

    result = []
    seen = set()
    for item in selection:
        curve = _as_curve_transform(item)
        if curve and curve not in seen:
            result.append(curve)
            seen.add(curve)
    return result


def _safe_set_attr(node, attr, value):
    if not cmds.objExists(node):
        return False
    if not cmds.attributeQuery(attr, node=node, exists=True):
        return False
    try:
        cmds.setAttr("{}.{}".format(node, attr), value)
        return True
    except Exception as exc:
        cmds.warning("curve_to_mesh: could not set {}.{} - {}".format(
            node, attr, exc))
        return False


def _mesh_transforms_from_nodes(nodes):
    result = []
    seen = set()
    for node in nodes:
        if not cmds.objExists(node):
            continue

        transform = None
        if cmds.nodeType(node) == "mesh":
            parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
            transform = parents[0] if parents else None
        elif cmds.nodeType(node) == "transform":
            shapes = cmds.listRelatives(node, shapes=True, noIntermediate=True,
                                        fullPath=True) or []
            if any(cmds.nodeType(shape) == "mesh" for shape in shapes):
                transform = node

        if transform and transform not in seen:
            result.append(transform)
            seen.add(transform)
    return result


def _vector_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vector_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vector_scale(vector, scale):
    return (vector[0] * scale, vector[1] * scale, vector[2] * scale)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _length(vector):
    return math.sqrt(max(0.0, _dot(vector, vector)))


def _normalize(vector):
    length = _length(vector)
    if length < 0.000001:
        return None
    return _vector_scale(vector, 1.0 / length)


def _project_off_axis(vector, axis):
    return _vector_sub(vector, _vector_scale(axis, _dot(vector, axis)))


def _node_without_component(node):
    if not node:
        return node
    return node.split(".", 1)[0]


def _transform_from_node_or_component(node):
    nodes = cmds.ls(_node_without_component(node), long=True) or []
    if not nodes:
        return None

    node = nodes[0]
    try:
        node_type = cmds.nodeType(node)
    except Exception:
        return None

    if node_type == "transform":
        return node
    parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
    return parents[0] if parents else None


def _transform_axis_vector(transform, axis_label):
    obj = _transform_from_node_or_component(transform)
    if not obj:
        return None

    matrix = cmds.xform(obj, query=True, matrix=True, worldSpace=True)
    axis_label = axis_label.replace("Object ", "")
    sign = -1.0 if axis_label.startswith("-") else 1.0
    clean_axis = axis_label[-1].upper()
    if clean_axis == "X":
        vector = (matrix[0], matrix[1], matrix[2])
    elif clean_axis == "Y":
        vector = (matrix[4], matrix[5], matrix[6])
    else:
        vector = (matrix[8], matrix[9], matrix[10])
    return _normalize(_vector_scale(vector, sign))


def _mesh_shapes(node):
    if not node:
        return []

    nodes = cmds.ls(_node_without_component(node), long=True) or []
    if not nodes:
        return []
    node = nodes[0]

    if cmds.nodeType(node) == "mesh":
        return [node]
    if cmds.nodeType(node) != "transform":
        return []

    return [
        shape for shape in (
            cmds.listRelatives(node, shapes=True, noIntermediate=True,
                               fullPath=True) or [])
        if cmds.nodeType(shape) == "mesh"
    ]


def _face_components(item):
    if not item or "." not in item:
        return []

    try:
        faces = cmds.polyListComponentConversion(item, toFace=True) or []
        return cmds.filterExpand(faces, sm=34, fullPath=True) or []
    except Exception:
        return []


def _average_face_component_normal(face_component):
    faces = _face_components(face_component)
    if not faces:
        return None

    try:
        from maya.api import OpenMaya as om
        normal = om.MVector()
        count = 0
        for face in faces:
            selection = om.MSelectionList()
            selection.add(face)
            dag_path, component = selection.getComponent(0)
            mesh_fn = om.MFnMesh(dag_path)
            component_fn = om.MFnSingleIndexedComponent(component)
            for face_index in component_fn.getElements():
                normal += mesh_fn.getPolygonNormal(face_index, om.MSpace.kWorld)
                count += 1
        if count:
            normal /= float(count)
        return _normalize((normal.x, normal.y, normal.z))
    except Exception:
        return None


def _average_mesh_normal(mesh_or_transform):
    component_normal = _average_face_component_normal(mesh_or_transform)
    if component_normal:
        return component_normal

    shapes = _mesh_shapes(mesh_or_transform)
    if not shapes:
        return None

    try:
        from maya.api import OpenMaya as om
        selection = om.MSelectionList()
        selection.add(shapes[0])
        dag_path = selection.getDagPath(0)
        mesh_fn = om.MFnMesh(dag_path)
        normal = om.MVector()
        polygon_count = mesh_fn.numPolygons
        for index in range(polygon_count):
            normal += mesh_fn.getPolygonNormal(index, om.MSpace.kWorld)
        if polygon_count:
            normal /= float(polygon_count)
        return _normalize((normal.x, normal.y, normal.z))
    except Exception:
        return None


def _guide_normal_vector(normal_object, normal_source):
    if not normal_object:
        return None

    source = normal_source or NORMAL_SOURCES[0]
    if source in (NORMAL_FACE_MESH, "Mesh Average Normal"):
        normal = _average_mesh_normal(normal_object)
        if normal:
            return normal
        return _transform_axis_vector(normal_object, "Object Z")

    return _transform_axis_vector(normal_object, source)


def _curve_tangent_vector(curve):
    curve = _as_curve_transform(curve)
    if not curve:
        return None

    shapes = cmds.listRelatives(curve, shapes=True, noIntermediate=True,
                                fullPath=True) or []
    if not shapes:
        return None
    shape = shapes[0]

    try:
        count = cmds.getAttr(shape + ".controlPoints", size=True)
        if count >= 2:
            start = cmds.pointPosition("{}.cv[0]".format(shape), world=True)
            end = cmds.pointPosition("{}.cv[{}]".format(shape, count - 1),
                                     world=True)
            tangent = _normalize(_vector_sub(end, start))
            if tangent:
                return tangent
    except Exception:
        pass

    try:
        from maya.api import OpenMaya as om
        selection = om.MSelectionList()
        selection.add(shape)
        dag_path = selection.getDagPath(0)
        curve_fn = om.MFnNurbsCurve(dag_path)
        param_min, param_max = curve_fn.knotDomain
        tangent = curve_fn.tangent((param_min + param_max) * 0.5,
                                   om.MSpace.kWorld)
        return _normalize((tangent.x, tangent.y, tangent.z))
    except Exception:
        return None


def _force_mesh_evaluation(mesh):
    try:
        cmds.dgdirty(mesh)
    except Exception:
        pass
    try:
        cmds.polyEvaluate(mesh, face=True)
    except Exception:
        pass


def _align_plane_normal_to_guide(creator, mesh, curve, normal_object,
                                 normal_source):
    if not normal_object:
        return

    guide_normal = _guide_normal_vector(normal_object, normal_source)
    current_normal = _average_mesh_normal(mesh)
    tangent = _curve_tangent_vector(curve)
    if not guide_normal or not current_normal or not tangent:
        cmds.warning("curve_to_mesh: could not resolve plane normal guide.")
        return

    guide_normal = _normalize(_project_off_axis(guide_normal, tangent))
    current_normal = _normalize(_project_off_axis(current_normal, tangent))
    if not guide_normal or not current_normal:
        cmds.warning("curve_to_mesh: guide normal is parallel to the curve tangent.")
        return

    angle = math.degrees(math.atan2(
        _dot(tangent, _cross(current_normal, guide_normal)),
        _dot(current_normal, guide_normal),
    ))
    try:
        current_angle = cmds.getAttr(creator + ".rotateProfile")
    except Exception:
        current_angle = 0.0
    _safe_set_attr(creator, "rotateProfile", current_angle + angle)
    _force_mesh_evaluation(mesh)

    updated_normal = _average_mesh_normal(mesh)
    if not updated_normal:
        return

    updated_normal = _normalize(_project_off_axis(updated_normal, tangent))
    if not updated_normal:
        return

    refine_angle = math.degrees(math.atan2(
        _dot(tangent, _cross(updated_normal, guide_normal)),
        _dot(updated_normal, guide_normal),
    ))
    if abs(refine_angle) > 0.01:
        _safe_set_attr(creator, "rotateProfile", current_angle + angle + refine_angle)
        _force_mesh_evaluation(mesh)


def _normalize_profile(profile):
    profile = (profile or PROFILE_TUBE).strip().lower()
    if profile in ("plane", "ribbon", "line"):
        return PROFILE_PLANE
    return PROFILE_TUBE


def _default_width_ramp():
    return [(0.0, 1.0, 1), (1.0, 1.0, 1)]


def _clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def _parse_width_ramp_string(ramp_string):
    """Parse gradientControlNoAttr string into (position, value, interp)."""
    if not ramp_string:
        return _default_width_ramp()

    try:
        values = [float(part) for part in ramp_string.split(",") if part.strip()]
    except ValueError:
        return _default_width_ramp()

    points = []
    for index in range(0, len(values) - 2, 3):
        value = _clamp(values[index], 0.0, 10.0)
        position = _clamp(values[index + 1], 0.0, 1.0)
        interp = int(round(values[index + 2]))
        points.append((position, value, interp))

    if not points:
        return _default_width_ramp()

    return sorted(points, key=lambda item: item[0])


def _width_ramp_from_control(ramp_control):
    if not ramp_control or not cmds.control(ramp_control, exists=True):
        return _default_width_ramp()
    try:
        ramp_string = cmds.gradientControlNoAttr(
            ramp_control, query=True, asString=True)
    except Exception:
        return _default_width_ramp()
    return _parse_width_ramp_string(ramp_string)


def _apply_width_ramp(creator, width_ramp):
    points = width_ramp or _default_width_ramp()
    attr = "{}.taperCurve".format(creator)

    existing = cmds.getAttr(attr, multiIndices=True) or []
    for index in sorted(existing, reverse=True):
        if index >= len(points):
            try:
                cmds.removeMultiInstance("{}[{}]".format(attr, index), b=True)
            except Exception:
                pass

    for index, (position, value, interp) in enumerate(points):
        base = "{}.taperCurve[{}]".format(creator, index)
        _safe_set_attr(creator, "taper", 1.0)
        cmds.setAttr(base + ".taperCurve_Position", position)
        cmds.setAttr(base + ".taperCurve_FloatValue", value)
        cmds.setAttr(base + ".taperCurve_Interp", interp)


def _configure_sweep_creator(creator, radius, sides, segments, caps,
                             profile=PROFILE_TUBE, width_ramp=None):
    profile = _normalize_profile(profile)
    size = max(0.001, float(radius))

    if profile == PROFILE_PLANE:
        # Sweep Mesh "Line" profile creates a flat ribbon/plane along the curve.
        _safe_set_attr(creator, "sweepProfileType", 2)
        _safe_set_attr(creator, "scaleProfileUniform", True)
        _safe_set_attr(creator, "scaleProfileX", size)
        _safe_set_attr(creator, "scaleProfileY", size)
        _safe_set_attr(creator, "capsEnable", False)
    else:
        # Regular Polygon profile gives a tube-like mesh. Equal X/Y scale keeps it round.
        _safe_set_attr(creator, "sweepProfileType", 0)
        _safe_set_attr(creator, "profilePolyType", 0)
        _safe_set_attr(creator, "profilePolySides", max(3, int(sides)))
        _safe_set_attr(creator, "scaleProfileUniform", True)
        _safe_set_attr(creator, "scaleProfileX", size)
        _safe_set_attr(creator, "scaleProfileY", size)
        _safe_set_attr(creator, "capsEnable", bool(caps))

    _apply_width_ramp(creator, width_ramp)

    if segments is not None:
        _safe_set_attr(creator, "interpolationMode", 1)
        _safe_set_attr(creator, "interpolationSteps", max(1, int(segments)))


def convert_curve_to_mesh(curve, radius=0.1, sides=8, segments=20,
                          caps=True, keep_history=False,
                          delete_curve=False, name_suffix="_mesh",
                          profile=PROFILE_TUBE, width_ramp=None,
                          normal_object=None,
                          normal_source=NORMAL_SOURCES[0]):
    """Convert one NURBS curve transform to a polygon mesh.

    Returns:
        dict with keys: curve, mesh, creators
    """
    curve = _as_curve_transform(curve)
    if not curve:
        raise RuntimeError("Select a NURBS curve transform or shape.")
    if not hasattr(cmds, "sweepMeshFromCurve"):
        raise RuntimeError("cmds.sweepMeshFromCurve is not available in this Maya.")
    if delete_curve and keep_history:
        raise RuntimeError("delete_curve=True needs keep_history=False.")

    before = set(cmds.ls(long=True) or [])
    cmds.select(curve, replace=True)
    cmds.sweepMeshFromCurve(oneNodePerCurve=True)
    after = set(cmds.ls(long=True) or [])

    new_nodes = sorted(after - before)
    creators = [
        node for node in new_nodes
        if cmds.objExists(node) and cmds.nodeType(node) == "sweepMeshCreator"
    ]
    meshes = _mesh_transforms_from_nodes(new_nodes)

    if not meshes:
        raise RuntimeError("Sweep Mesh did not create a mesh for {}.".format(curve))

    for creator in creators:
        _configure_sweep_creator(
            creator,
            radius,
            sides,
            segments,
            caps,
            profile=profile,
            width_ramp=width_ramp,
        )

    mesh = meshes[0]
    mesh = cmds.rename(mesh, _base_curve_name(curve) + name_suffix)
    mesh = (cmds.ls(mesh, long=True) or [mesh])[0]

    if _normalize_profile(profile) == PROFILE_PLANE and normal_object:
        for creator in creators:
            if cmds.objExists(creator):
                _align_plane_normal_to_guide(
                    creator, mesh, curve, normal_object, normal_source)

    if not keep_history:
        _force_mesh_evaluation(mesh)
        cmds.delete(mesh, constructionHistory=True)

    if delete_curve and cmds.objExists(curve):
        cmds.delete(curve)

    return {
        "curve": curve,
        "mesh": mesh,
        "creators": [node for node in creators if cmds.objExists(node)],
    }


def convert_selected(radius=0.1, sides=8, segments=20, caps=True,
                     keep_history=False, delete_curve=False,
                     name_suffix="_mesh", profile=PROFILE_TUBE,
                     width_ramp=None, normal_object=None,
                     normal_source=NORMAL_SOURCES[0]):
    """Convert selected NURBS curves to polygon meshes."""
    curves = selected_curves()
    if not curves:
        cmds.warning("curve_to_mesh: select one or more NURBS curves.")
        return []

    results = []
    cmds.undoInfo(openChunk=True)
    try:
        for curve in curves:
            results.append(convert_curve_to_mesh(
                curve,
                radius=radius,
                sides=sides,
                segments=segments,
                caps=caps,
                keep_history=keep_history,
                delete_curve=delete_curve,
                name_suffix=name_suffix,
                profile=profile,
                width_ramp=width_ramp,
                normal_object=normal_object,
                normal_source=normal_source,
            ))
    finally:
        cmds.undoInfo(closeChunk=True)

    meshes = [result["mesh"] for result in results if cmds.objExists(result["mesh"])]
    if meshes:
        cmds.select(meshes, replace=True)
    print("curve_to_mesh: created {} mesh(es).".format(len(meshes)))
    return meshes


def _field_value(field, default):
    if not field:
        return default
    try:
        return cmds.floatField(field, query=True, value=True)
    except Exception:
        return default


def _int_field_value(field, default):
    if not field:
        return default
    try:
        return cmds.intField(field, query=True, value=True)
    except Exception:
        return default


def _check_value(check, default):
    if not check:
        return default
    try:
        return cmds.checkBox(check, query=True, value=True)
    except Exception:
        return default


def _menu_value(menu, default):
    if not menu:
        return default
    try:
        return cmds.optionMenu(menu, query=True, value=True)
    except Exception:
        return default


def _text_value(field, default=""):
    if not field:
        return default
    try:
        return cmds.textField(field, query=True, text=True).strip()
    except Exception:
        return default


def _set_field_from_selection(field, *_):
    selection = cmds.ls(selection=True, long=True) or []
    if not selection:
        cmds.warning("curve_to_mesh: select a normal guide object first.")
        return
    cmds.textField(field, edit=True, text=selection[-1])


def _clear_text_field(field, *_):
    if field:
        cmds.textField(field, edit=True, text="")


def _ramp_interp_label(value):
    for label, index in RAMP_INTERPS.items():
        if index == value:
            return label
    return "Linear"


def _set_ramp_selected_interp(ramp_control, interp_menu, *_):
    if not ramp_control or not interp_menu:
        return

    interp = RAMP_INTERPS.get(_menu_value(interp_menu, "Linear"), 1)
    try:
        cmds.gradientControlNoAttr(
            ramp_control, edit=True, currentKeyInterpValue=interp)
    except Exception as exc:
        cmds.warning("curve_to_mesh: select a ramp point first - {}".format(exc))


def _sync_ramp_interp_menu(ramp_control, interp_menu, *_):
    if not ramp_control or not interp_menu:
        return

    try:
        interp = cmds.gradientControlNoAttr(
            ramp_control, query=True, currentKeyInterpValue=True)
        cmds.optionMenu(
            interp_menu, edit=True, value=_ramp_interp_label(int(interp)))
    except Exception:
        pass


def _set_width_ramp_string(ramp_control, ramp_string, *_):
    if not ramp_control:
        return False
    try:
        cmds.gradientControlNoAttr(
            ramp_control, edit=True, asString=ramp_string)
        return True
    except Exception:
        return False


def _set_width_ramp_default(ramp_control, *_):
    if _set_width_ramp_string(ramp_control, DEFAULT_RAMP_STRING):
        return

    try:
        cmds.gradientControlNoAttr(
            ramp_control, edit=True, addEntry=(0.0, 1.0, 1.0, 1.0, 1))
        cmds.gradientControlNoAttr(
            ramp_control, edit=True, addEntry=(1.0, 1.0, 1.0, 1.0, 1))
    except Exception as exc:
        cmds.warning("curve_to_mesh: could not reset ramp - {}".format(exc))


def _on_profile_changed(profile_menu, sides_field, caps_check,
                        normal_field=None, normal_source_menu=None, *_):
    profile = _normalize_profile(_menu_value(profile_menu, PROFILE_TUBE))
    tube_enabled = profile == PROFILE_TUBE
    if sides_field:
        cmds.intField(sides_field, edit=True, enable=tube_enabled)
    if caps_check:
        cmds.checkBox(caps_check, edit=True, enable=tube_enabled)
    if normal_field:
        cmds.textField(normal_field, edit=True, enable=not tube_enabled)
    if normal_source_menu:
        cmds.optionMenu(normal_source_menu, edit=True, enable=not tube_enabled)


def _on_convert(profile_menu, radius_field, sides_field, segments_field,
                caps_check, history_check, delete_check, ramp_control,
                normal_field=None, normal_source_menu=None, *_):
    if not selected_curves():
        cmds.confirmDialog(
            title="Curve To Mesh",
            message="Select a NURBS curve transform or shape first.",
            button=["OK"],
            defaultButton="OK",
        )
        return

    profile = _normalize_profile(_menu_value(profile_menu, PROFILE_TUBE))
    keep_history = _check_value(history_check, False)
    delete_curve = _check_value(delete_check, False)
    if keep_history and delete_curve:
        keep_history = False
        cmds.checkBox(history_check, edit=True, value=False)
        cmds.warning("curve_to_mesh: source deletion requires baked mesh history.")

    try:
        meshes = convert_selected(
            radius=_field_value(radius_field, 0.1),
            sides=_int_field_value(sides_field, 8),
            segments=_int_field_value(segments_field, 20),
            caps=_check_value(caps_check, True),
            keep_history=keep_history,
            delete_curve=delete_curve,
            profile=profile,
            width_ramp=_width_ramp_from_control(ramp_control),
            normal_object=_text_value(normal_field),
            normal_source=_menu_value(normal_source_menu, NORMAL_SOURCES[0]),
        )
    except Exception as exc:
        cmds.confirmDialog(
            title="Curve To Mesh Error",
            message=str(exc),
            button=["OK"],
            defaultButton="OK",
        )
        raise

    if meshes:
        cmds.inViewMessage(
            amg="Curve To Mesh: <hl>{}</hl> mesh(es) created.".format(len(meshes)),
            pos="midCenter",
            fade=True,
        )


def show():
    """Show the Curve To Mesh window."""
    if cmds.window(WIN_ID, exists=True):
        cmds.deleteUI(WIN_ID)

    win = cmds.window(WIN_ID, title="Curve To Mesh",
                      widthHeight=(430, 640), sizeable=True)
    cmds.scrollLayout(childResizable=True)
    root = cmds.columnLayout(adjustableColumn=True, rowSpacing=8,
                             columnAttach=("both", 12))

    cmds.separator(height=8, style="none")
    cmds.text(label="Select NURBS curve(s)", align="left", font="boldLabelFont")

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                   columnWidth2=(95, 250), parent=root)
    cmds.text(label="Profile", align="right")
    profile_menu = cmds.optionMenu()
    cmds.menuItem(label=PROFILE_TUBE)
    cmds.menuItem(label=PROFILE_PLANE)
    cmds.setParent(root)

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                   columnWidth2=(95, 250), parent=root)
    cmds.text(label="Size / Width", align="right")
    radius_field = cmds.floatField(value=0.1, precision=3, minValue=0.001)
    cmds.setParent(root)

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                   columnWidth2=(95, 250), parent=root)
    cmds.text(label="Sides (Tube)", align="right")
    sides_field = cmds.intField(value=8, minValue=3)
    cmds.setParent(root)

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                   columnWidth2=(95, 250), parent=root)
    cmds.text(label="Segments", align="right")
    segments_field = cmds.intField(value=20, minValue=1)
    cmds.setParent(root)

    caps_check = cmds.checkBox(label="Caps", value=True, parent=root)
    history_check = cmds.checkBox(label="Keep live Sweep Mesh history",
                                  value=False, parent=root)
    delete_check = cmds.checkBox(label="Delete source curves after bake",
                                 value=False, parent=root)

    cmds.separator(height=8, style="in", parent=root)
    cmds.text(label="Plane Normal Guide", align="left",
              font="boldLabelFont", parent=root)
    cmds.rowLayout(numberOfColumns=4, adjustableColumn=2,
                   columnWidth4=(95, 150, 70, 55), parent=root)
    cmds.text(label="Object", align="right")
    normal_field = cmds.textField(text="", enable=False)
    cmds.button(label="From Sel",
                command=lambda *args: _set_field_from_selection(
                    normal_field, *args))
    cmds.button(label="Clear",
                command=lambda *args: _clear_text_field(normal_field, *args))
    cmds.setParent(root)

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                   columnWidth2=(95, 250), parent=root)
    cmds.text(label="Normal", align="right")
    normal_source_menu = cmds.optionMenu(enable=False)
    for source in NORMAL_SOURCES:
        cmds.menuItem(label=source)
    cmds.setParent(root)

    cmds.separator(height=8, style="in", parent=root)
    cmds.text(label="Width Ramp", align="left", font="boldLabelFont", parent=root)
    ramp_control = cmds.gradientControlNoAttr(
        "curveToMeshWidthRampControl",
        parent=root,
        height=110,
        rampAsColor=False,
        displayKeyInfo=True,
    )
    _set_width_ramp_default(ramp_control)

    cmds.rowLayout(numberOfColumns=3, adjustableColumn=2,
                   columnWidth3=(120, 120, 120), parent=root)
    cmds.text(label="Selected Interp", align="right")
    interp_menu = cmds.optionMenu()
    for label in ("Linear", "Smooth", "Spline", "None"):
        cmds.menuItem(label=label)
    cmds.button(label="Apply",
                command=lambda *args: _set_ramp_selected_interp(
                    ramp_control, interp_menu, *args))
    cmds.setParent(root)

    cmds.rowLayout(numberOfColumns=3, columnWidth3=(120, 120, 120), parent=root)
    cmds.button(label="Reset Ramp",
                command=lambda *args: _set_width_ramp_default(ramp_control))
    cmds.button(label="Pinch Center",
                command=lambda *args: _set_width_ramp_string(
                    ramp_control, "1,0,1,0.25,0.5,1,1,1,1"))
    cmds.button(label="Taper End",
                command=lambda *args: _set_width_ramp_string(
                    ramp_control, "1,0,1,0.2,1,1"))
    cmds.setParent(root)

    cmds.button(label="Create Mesh From Selected Curves", height=34,
                backgroundColor=(0.28, 0.45, 0.28),
                command=lambda *args: _on_convert(
                    profile_menu, radius_field, sides_field, segments_field,
                    caps_check, history_check, delete_check, ramp_control,
                    normal_field, normal_source_menu, *args))

    cmds.separator(height=8, style="none", parent=root)
    cmds.setParent("..")
    cmds.optionMenu(
        interp_menu,
        edit=True,
        changeCommand=lambda *args: _set_ramp_selected_interp(
            ramp_control, interp_menu, *args),
    )
    cmds.gradientControlNoAttr(
        ramp_control,
        edit=True,
        currentKeyChanged=lambda *args: _sync_ramp_interp_menu(
            ramp_control, interp_menu, *args),
    )
    cmds.optionMenu(
        profile_menu,
        edit=True,
        changeCommand=lambda *args: _on_profile_changed(
            profile_menu, sides_field, caps_check,
            normal_field, normal_source_menu, *args),
    )
    _on_profile_changed(profile_menu, sides_field, caps_check,
                        normal_field, normal_source_menu)
    cmds.showWindow(win)
    cmds.window(win, edit=True, widthHeight=(430, 640))
    return win


def run(radius=0.1, sides=8, segments=20, caps=True,
        keep_history=False, delete_curve=False, profile=PROFILE_TUBE,
        width_ramp=None, normal_object=None,
        normal_source=NORMAL_SOURCES[0]):
    return convert_selected(
        radius=radius,
        sides=sides,
        segments=segments,
        caps=caps,
        keep_history=keep_history,
        delete_curve=delete_curve,
        profile=profile,
        width_ramp=width_ramp,
        normal_object=normal_object,
        normal_source=normal_source,
    )


if __name__ == "__main__":
    show()
