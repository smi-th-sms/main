"""Build a Houdini KineFX retarget test scene from a Kimodo NPZ and FBX rig.

The generated network keeps the original FBX import visible, converts the
Kimodo source skeleton to a MotionClip, and creates a first-pass target-name
KineFX skeleton suitable for inspecting retargeted motion in Houdini.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import numpy as np

from kimodo_npz_kinefx_importer import SOMA77_NAMES, _load_npz, _matrix3_flat


TARGET_TO_SOMA = {
    "pelvis": "Hips",
    "spine_01": "Spine1",
    "spine_02": "Spine2",
    "spine_03": "Chest",
    "spine_04": (("Chest", 0.65), ("Neck1", 0.35)),
    "spine_05": (("Chest", 0.25), ("Neck1", 0.75)),
    "neck_01": "Neck1",
    "neck_02": "Neck2",
    "head": "Head",
    "clavicle_l": "LeftShoulder",
    "upperarm_l": "LeftArm",
    "lowerarm_l": "LeftForeArm",
    "hand_l": "LeftHand",
    "clavicle_r": "RightShoulder",
    "upperarm_r": "RightArm",
    "lowerarm_r": "RightForeArm",
    "hand_r": "RightHand",
    "thigh_l": "LeftLeg",
    "calf_l": "LeftShin",
    "foot_l": "LeftFoot",
    "ball_l": "LeftToeBase",
    "thigh_r": "RightLeg",
    "calf_r": "RightShin",
    "foot_r": "RightFoot",
    "ball_r": "RightToeBase",
}


for _side, _prefix in (("l", "Left"), ("r", "Right")):
    for _target, _source in (
        ("thumb_01", "HandThumb1"),
        ("thumb_02", "HandThumb2"),
        ("thumb_03", "HandThumb3"),
        ("index_01", "HandIndex1"),
        ("index_02", "HandIndex2"),
        ("index_03", "HandIndex3"),
        ("middle_01", "HandMiddle1"),
        ("middle_02", "HandMiddle2"),
        ("middle_03", "HandMiddle3"),
        ("ring_01", "HandRing1"),
        ("ring_02", "HandRing2"),
        ("ring_03", "HandRing3"),
        ("pinky_01", "HandPinky1"),
        ("pinky_02", "HandPinky2"),
        ("pinky_03", "HandPinky3"),
    ):
        TARGET_TO_SOMA[f"{_target}_{_side}"] = f"{_prefix}{_source}"


PRIMARY_CHILD = {
    "root": "pelvis",
    "pelvis": "spine_01",
    "spine_01": "spine_02",
    "spine_02": "spine_03",
    "spine_03": "spine_04",
    "spine_04": "spine_05",
    "spine_05": "neck_01",
    "neck_01": "neck_02",
    "neck_02": "head",
    "clavicle_l": "upperarm_l",
    "upperarm_l": "lowerarm_l",
    "lowerarm_l": "hand_l",
    "clavicle_r": "upperarm_r",
    "upperarm_r": "lowerarm_r",
    "lowerarm_r": "hand_r",
    "thigh_l": "calf_l",
    "calf_l": "foot_l",
    "foot_l": "ball_l",
    "thigh_r": "calf_r",
    "calf_r": "foot_r",
    "foot_r": "ball_r",
}


_SOMA_INDEX = {name: index for index, name in enumerate(SOMA77_NAMES)}


def _as_path(path: str) -> str:
    return os.path.abspath(path).replace("\\", "/")


def _frame_index(frame: float, start_frame: float, frame_offset: int, frame_count: int) -> int:
    idx = int(round(frame - start_frame)) + int(frame_offset)
    return max(0, min(frame_count - 1, idx))


def _point_names(geo):
    name_attr = geo.findPointAttrib("name")
    if name_attr is None:
        raise ValueError("Target skeleton input has no point name attribute")
    return [str(point.attribValue(name_attr)) for point in geo.points()]


def _parents_from_geo(geo) -> list[int]:
    parent_attr = geo.findPointAttrib("parent_idx")
    if parent_attr is not None:
        return [int(point.attribValue(parent_attr)) for point in geo.points()]

    points = list(geo.points())
    parent = [-1] * len(points)
    for prim in geo.prims():
        verts = prim.vertices()
        if len(verts) == 2:
            parent[verts[1].point().number()] = verts[0].point().number()
    return parent


def _source_position(spec, positions: np.ndarray) -> np.ndarray:
    if isinstance(spec, str):
        return positions[_SOMA_INDEX[spec]]

    out = np.zeros(3, dtype=np.float64)
    total = 0.0
    for name, weight in spec:
        out += positions[_SOMA_INDEX[name]] * float(weight)
        total += float(weight)
    if not total:
        raise ValueError(f"Invalid zero-weight source mapping: {spec!r}")
    return out / total


def _estimate_source_height(rest_positions: np.ndarray) -> float:
    top = rest_positions[_SOMA_INDEX["Head"], 1]
    bottom = min(
        rest_positions[_SOMA_INDEX["LeftFoot"], 1],
        rest_positions[_SOMA_INDEX["LeftToeBase"], 1],
        rest_positions[_SOMA_INDEX["RightFoot"], 1],
        rest_positions[_SOMA_INDEX["RightToeBase"], 1],
    )
    return max(float(top - bottom), 1.0e-5)


def _estimate_target_height(names: list[str], rest_positions: np.ndarray) -> float:
    name_to_index = {name: index for index, name in enumerate(names)}
    if "head" not in name_to_index:
        return 1.0
    bottom_names = [name for name in ("ball_l", "ball_r", "foot_l", "foot_r") if name in name_to_index]
    if not bottom_names:
        return 1.0
    top = rest_positions[name_to_index["head"], 1]
    bottom = min(rest_positions[name_to_index[name], 1] for name in bottom_names)
    return max(float(top - bottom), 1.0e-5)


def _rotation_between(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    source_len = float(np.linalg.norm(source))
    target_len = float(np.linalg.norm(target))
    if source_len < 1.0e-8 or target_len < 1.0e-8:
        return np.identity(3, dtype=np.float64)

    a = source / source_len
    b = target / target_len
    dot = float(np.clip(np.dot(a, b), -1.0, 1.0))
    if dot > 0.99999:
        return np.identity(3, dtype=np.float64)

    if dot < -0.99999:
        axis = np.cross(a, np.array([1.0, 0.0, 0.0], dtype=np.float64))
        if np.linalg.norm(axis) < 1.0e-8:
            axis = np.cross(a, np.array([0.0, 1.0, 0.0], dtype=np.float64))
        axis /= np.linalg.norm(axis)
        return -np.identity(3, dtype=np.float64) + 2.0 * np.outer(axis, axis)

    axis = np.cross(a, b)
    skew = np.array(
        (
            (0.0, -axis[2], axis[1]),
            (axis[2], 0.0, -axis[0]),
            (-axis[1], axis[0], 0.0),
        ),
        dtype=np.float64,
    )
    return np.identity(3, dtype=np.float64) + skew + skew @ skew * (1.0 / (1.0 + dot))


def _matrix3_from_flat(values) -> np.ndarray:
    return np.asarray(values, dtype=np.float64).reshape(3, 3)


def _matrix4_from_flat(values) -> np.ndarray:
    return np.asarray(values, dtype=np.float64).reshape(4, 4)


def _orthonormalize(matrix: np.ndarray) -> tuple[np.ndarray, float]:
    scale = float(sum(np.linalg.norm(matrix[row]) for row in range(3)) / 3.0)
    if scale < 1.0e-8:
        return np.identity(3, dtype=np.float64), 1.0

    normalized = matrix / scale
    u, _, vt = np.linalg.svd(normalized)
    rotation = u @ vt
    if np.linalg.det(rotation) < 0.0:
        u[:, -1] *= -1.0
        rotation = u @ vt
    return rotation, scale


def _matrix4_flat_from_parts(rotation: np.ndarray, translation: np.ndarray) -> tuple[float, ...]:
    return (
        float(rotation[0, 0]),
        float(rotation[0, 1]),
        float(rotation[0, 2]),
        0.0,
        float(rotation[1, 0]),
        float(rotation[1, 1]),
        float(rotation[1, 2]),
        0.0,
        float(rotation[2, 0]),
        float(rotation[2, 1]),
        float(rotation[2, 2]),
        0.0,
        float(translation[0]),
        float(translation[1]),
        float(translation[2]),
        1.0,
    )


def _source_delta_for_target(
    target_name: str,
    source_rest: np.ndarray,
    source_pose: np.ndarray,
    source_global_rest: np.ndarray,
    source_global_pose: np.ndarray,
) -> np.ndarray:
    source_spec = TARGET_TO_SOMA.get(target_name)
    child_name = PRIMARY_CHILD.get(target_name)
    child_spec = TARGET_TO_SOMA.get(child_name) if child_name else None

    if source_spec is not None and child_spec is not None:
        rest_vec = _source_position(child_spec, source_rest) - _source_position(source_spec, source_rest)
        pose_vec = _source_position(child_spec, source_pose) - _source_position(source_spec, source_pose)
        if np.linalg.norm(rest_vec) > 1.0e-8 and np.linalg.norm(pose_vec) > 1.0e-8:
            # _rotation_between is column-vector style. KineFX FBX matrices here
            # compose as row-vector transforms, so transpose the delta.
            return _rotation_between(rest_vec, pose_vec).T

    if isinstance(source_spec, str):
        index = _SOMA_INDEX[source_spec]
        delta_col = source_global_pose[index] @ source_global_rest[index].T
        return delta_col.T

    return np.identity(3, dtype=np.float64)


def _topological_order(parents: list[int]) -> list[int]:
    remaining = set(range(len(parents)))
    order: list[int] = []
    while remaining:
        progressed = False
        for index in list(remaining):
            parent = parents[index]
            if parent < 0 or parent not in remaining:
                order.append(index)
                remaining.remove(index)
                progressed = True
        if not progressed:
            order.extend(sorted(remaining))
            break
    return order


def _add_point_attrib(geo, hou, name: str, default):
    return geo.addAttrib(hou.attribType.Point, name, default)


def _copy_optional_point_values(point, attr_name: str):
    attr = point.geometry().findPointAttrib(attr_name)
    if attr is None:
        return None
    return point.attribValue(attr)


def _python_retarget_sop_code(
    module_dir: str,
    npz_path: str,
    scale: float,
    start_frame: float,
    source_fps: float,
) -> str:
    module_dir = module_dir.replace("\\", "/")
    npz_path = npz_path.replace("\\", "/")
    return f"""import importlib, sys
module_dir = r"{module_dir}"
if module_dir not in sys.path:
    sys.path.insert(0, module_dir)
import kimodo_fbx_retarget_setup
importlib.reload(kimodo_fbx_retarget_setup)
kimodo_fbx_retarget_setup.cook_retarget_python_sop(
    hou.pwd(),
    r"{npz_path}",
    scale={float(scale)!r},
    start_frame={float(start_frame)!r},
    source_fps={float(source_fps)!r},
)
"""


def cook_retarget_python_sop(
    node,
    npz_path: str,
    *,
    scale: float = 1.0,
    start_frame: float = 1.0,
    frame_offset: int = 0,
    source_fps: float = 30.0,
) -> None:
    """Cook a target-name KineFX skeleton driven by the Kimodo NPZ motion."""
    import hou

    inputs = node.inputs()
    if not inputs:
        raise ValueError("Retarget Python SOP needs the FBX target skeleton/rest pose as input 0")

    target_geo = inputs[0].geometry()
    names = _point_names(target_geo)
    parents = _parents_from_geo(target_geo)
    name_to_index = {name: index for index, name in enumerate(names)}
    input_points = list(target_geo.points())
    rest_positions = np.array([tuple(point.position()) for point in target_geo.points()], dtype=np.float64)

    data = _load_npz(npz_path)
    positions_all = data["posed_joints"]
    global_rot_all = data["global_rot_mats"]
    frame_count = int(positions_all.shape[0])
    idx = _frame_index(hou.frame(), start_frame, frame_offset, frame_count)
    source_rest = positions_all[0].astype(np.float64)
    source_pose = positions_all[idx].astype(np.float64)
    source_global_rest = global_rot_all[0].astype(np.float64)
    source_global_pose = global_rot_all[idx].astype(np.float64)

    source_height = _estimate_source_height(source_rest)
    target_height = _estimate_target_height(names, rest_positions)
    retarget_scale = float(scale) * target_height / source_height

    source_hips = _SOMA_INDEX["Hips"]
    source_root_delta = (source_pose[source_hips] - source_rest[source_hips]) * retarget_scale

    mapped = np.zeros(len(names), dtype=np.int32)
    order = _topological_order(parents)

    target_transform_attr = target_geo.findPointAttrib("transform")
    target_localtransform_attr = target_geo.findPointAttrib("localtransform")
    if target_transform_attr is None or target_localtransform_attr is None:
        raise ValueError("Target skeleton must have transform and localtransform point attributes")

    rest_global_rot: list[np.ndarray] = []
    rest_global_scale: list[float] = []
    rest_local_rot: list[np.ndarray] = []
    rest_local_matrix: list[np.ndarray] = []
    rest_local_translation: list[np.ndarray] = []
    for point in input_points:
        global_rot, global_scale = _orthonormalize(_matrix3_from_flat(point.attribValue(target_transform_attr)))
        local_matrix = _matrix4_from_flat(point.attribValue(target_localtransform_attr))
        local_rot, _ = _orthonormalize(local_matrix[:3, :3])
        rest_global_rot.append(global_rot)
        rest_global_scale.append(global_scale)
        rest_local_rot.append(local_rot)
        rest_local_matrix.append(local_matrix)
        rest_local_translation.append(local_matrix[3, :3].astype(np.float64))

    anim_global_rot = [rest_global_rot[index].copy() for index in range(len(names))]
    for index in order:
        name = names[index]
        parent = parents[index]
        if name in TARGET_TO_SOMA:
            mapped[index] = 1
            delta_row = _source_delta_for_target(
                name,
                source_rest,
                source_pose,
                source_global_rest,
                source_global_pose,
            )
            anim_global_rot[index] = rest_global_rot[index] @ delta_row
        elif parent >= 0:
            anim_global_rot[index] = rest_local_rot[index] @ anim_global_rot[parent]

    root_index = name_to_index.get("root")
    if root_index is not None:
        mapped[root_index] = 1

    anim_positions = rest_positions.copy()
    if root_index is not None:
        anim_positions[root_index] = rest_positions[root_index] + source_root_delta

    for index in order:
        parent = parents[index]
        if parent < 0 or parent >= len(names):
            continue
        local_t = rest_local_translation[index]
        anim_positions[index] = anim_positions[parent] + (local_t @ anim_global_rot[parent]) / 100.0

    out = node.geometry()
    out.clear()
    point_attribs = {
        "name": _add_point_attrib(out, hou, "name", ""),
        "parent_idx": _add_point_attrib(out, hou, "parent_idx", -1),
        "retarget_mapped": _add_point_attrib(out, hou, "retarget_mapped", 0),
        "retarget_frame": _add_point_attrib(out, hou, "retarget_frame", 0),
        "transform": _add_point_attrib(out, hou, "transform", [1.0] * 9),
        "localtransform": _add_point_attrib(out, hou, "localtransform", [1.0] * 16),
    }
    for attr_name in ("path", "fbx_node_type", "fbx_custom_attributes"):
        if target_geo.findPointAttrib(attr_name) is not None:
            point_attribs[attr_name] = _add_point_attrib(out, hou, attr_name, "")
    if target_geo.findPointAttrib("Cd") is not None:
        point_attribs["Cd"] = _add_point_attrib(out, hou, "Cd", (1.0, 1.0, 1.0))

    detail_attribs = {
        "kimodo_npz": out.addAttrib(hou.attribType.Global, "kimodo_npz", ""),
        "retarget_source_fps": out.addAttrib(hou.attribType.Global, "retarget_source_fps", 30.0),
        "retarget_scale": out.addAttrib(hou.attribType.Global, "retarget_scale", 1.0),
        "retarget_mapped_count": out.addAttrib(hou.attribType.Global, "retarget_mapped_count", 0),
        "clip_frames": out.addAttrib(hou.attribType.Global, "clip_frames", 0),
    }
    out.setGlobalAttribValue(detail_attribs["kimodo_npz"], _as_path(npz_path))
    out.setGlobalAttribValue(detail_attribs["retarget_source_fps"], float(source_fps))
    out.setGlobalAttribValue(detail_attribs["retarget_scale"], float(retarget_scale))
    out.setGlobalAttribValue(detail_attribs["retarget_mapped_count"], int(mapped.sum()))
    out.setGlobalAttribValue(detail_attribs["clip_frames"], frame_count)

    points = []
    for index, name in enumerate(names):
        point = out.createPoint()
        point.setPosition(tuple(float(v) for v in anim_positions[index]))
        point.setAttribValue(point_attribs["name"], name)
        point.setAttribValue(point_attribs["parent_idx"], int(parents[index]))
        point.setAttribValue(point_attribs["retarget_mapped"], int(mapped[index]))
        point.setAttribValue(point_attribs["retarget_frame"], int(idx))

        point.setAttribValue(
            point_attribs["transform"],
            _matrix3_flat(anim_global_rot[index] * rest_global_scale[index]),
        )

        parent = parents[index]
        if 0 <= parent < len(names):
            local_rot = anim_global_rot[index] @ anim_global_rot[parent].T
            local_t = (anim_positions[index] - anim_positions[parent]) * 100.0
            local_t = local_t @ anim_global_rot[parent].T
        else:
            local_rot = rest_local_matrix[index][:3, :3]
            local_t = anim_positions[index] * 100.0

        point.setAttribValue(point_attribs["localtransform"], _matrix4_flat_from_parts(local_rot, local_t))

        for attr_name in ("path", "fbx_node_type", "fbx_custom_attributes"):
            if attr_name in point_attribs:
                value = _copy_optional_point_values(input_points[index], attr_name)
                point.setAttribValue(point_attribs[attr_name], "" if value is None else str(value))
        if "Cd" in point_attribs:
            value = _copy_optional_point_values(input_points[index], "Cd")
            point.setAttribValue(point_attribs["Cd"], (1.0, 0.75, 0.2) if value is None else tuple(value))
        points.append(point)

    for index, parent in enumerate(parents):
        if parent < 0 or parent >= len(points):
            continue
        poly = out.createPolygon()
        poly.setIsClosed(False)
        poly.addVertex(points[parent])
        poly.addVertex(points[index])


def _make_object_merge(parent, name: str, source_node, output_index: int = 0):
    node = parent.createNode("object_merge", name)
    node.parm("objpath1").set(source_node.path())
    if node.parm("xformtype") is not None:
        node.parm("xformtype").set(1)
    if output_index and node.parm("objpath1") is not None:
        node.setInput(0, source_node, output_index)
    return node


def _set_if_exists(node, parm_name: str, value) -> None:
    parm = node.parm(parm_name)
    if parm is not None:
        parm.set(value)


def build_retarget_scene(
    npz_path: str,
    fbx_path: str,
    hip_path: str | None = None,
    *,
    obj_name: str = "kimodo_scaglione_retarget",
    scale: float = 1.0,
    source_fps: float = 30.0,
    playback_fps: float = 15.0,
    start_frame: int = 1,
):
    """Create the Kimodo-to-FBX retarget test network in the current Houdini scene."""
    import hou

    npz_path = _as_path(npz_path)
    fbx_path = fbx_path.replace("\\", "/")
    frame_count = int(_load_npz(npz_path)["posed_joints"].shape[0])
    module_dir = str(Path(__file__).resolve().parent).replace("\\", "/")

    hou.hipFile.clear(suppress_save_prompt=True)
    obj = hou.node("/obj").createNode("geo", obj_name)
    for child in obj.children():
        child.destroy()

    import kimodo_npz_kinefx_importer

    importlib.reload(kimodo_npz_kinefx_importer)
    source_pose = obj.createNode("python", "KIMODO_NPZ_POSE")
    source_pose.parm("python").set(
        kimodo_npz_kinefx_importer._python_sop_code(module_dir, npz_path, scale, start_frame, source_fps)
    )
    source_doctor = obj.createNode("kinefx::rigdoctor", "KIMODO_RIGDOCTOR")
    source_doctor.setInput(0, source_pose)
    _set_if_exists(source_doctor, "outputparentidx", 1)
    _set_if_exists(source_doctor, "inittransforms", 0)

    source_out = obj.createNode("null", "OUT_KIMODO_SOURCE_POSE")
    source_out.setInput(0, source_doctor)

    source_motionclip = obj.createNode("kinefx::motionclip", "KIMODO_SOURCE_MOTIONCLIP")
    source_motionclip.setInput(0, source_out)
    _set_if_exists(source_motionclip, "useframerange", 1)
    _set_if_exists(source_motionclip, "framerange1", start_frame)
    _set_if_exists(source_motionclip, "framerange2", start_frame + frame_count - 1)
    _set_if_exists(source_motionclip, "usesamplerate", 1)
    _set_if_exists(source_motionclip, "samplerate", source_fps)
    _set_if_exists(source_motionclip, "attribs", "*")

    source_motionclip_eval = obj.createNode("kinefx::motionclipevaluate", "KIMODO_SOURCE_MOTIONCLIP_EVAL")
    source_motionclip_eval.setInput(0, source_motionclip)
    source_mc_out = obj.createNode("null", "OUT_KIMODO_SOURCE_MOTIONCLIP")
    source_mc_out.setInput(0, source_motionclip)

    fbx_import = obj.createNode("kinefx::fbxcharacterimport", "SCAGLIONE_FBX_IMPORT")
    fbx_import.parm("fbxfile").set(fbx_path)
    _set_if_exists(fbx_import, "removenamespaces", 1)

    skin_out = obj.createNode("null", "OUT_SCAGLIONE_SKIN")
    skin_out.setInput(0, fbx_import, 0)

    target_rest = obj.createNode("kinefx::rigdoctor", "SCAGLIONE_TARGET_REST")
    target_rest.setInput(0, fbx_import, 2)
    _set_if_exists(target_rest, "outputparentidx", 1)
    _set_if_exists(target_rest, "inittransforms", 1)

    target_rest_out = obj.createNode("null", "OUT_SCAGLIONE_TARGET_REST")
    target_rest_out.setInput(0, target_rest)

    retarget = obj.createNode("python", "RETARGET_SCAGLIONE_FROM_KIMODO")
    retarget.setInput(0, target_rest_out)
    retarget.parm("python").set(_python_retarget_sop_code(module_dir, npz_path, scale, start_frame, source_fps))

    retarget_doctor = obj.createNode("kinefx::rigdoctor", "RETARGET_RIGDOCTOR")
    retarget_doctor.setInput(0, retarget)
    _set_if_exists(retarget_doctor, "outputparentidx", 1)
    _set_if_exists(retarget_doctor, "inittransforms", 0)

    retarget_out = obj.createNode("null", "OUT_SCAGLIONE_RETARGET_POSE")
    retarget_out.setInput(0, retarget_doctor)
    retarget_out.setDisplayFlag(True)
    retarget_out.setRenderFlag(True)

    retarget_motionclip = obj.createNode("kinefx::motionclip", "SCAGLIONE_RETARGET_MOTIONCLIP")
    retarget_motionclip.setInput(0, retarget_out)
    _set_if_exists(retarget_motionclip, "useframerange", 1)
    _set_if_exists(retarget_motionclip, "framerange1", start_frame)
    _set_if_exists(retarget_motionclip, "framerange2", start_frame + frame_count - 1)
    _set_if_exists(retarget_motionclip, "usesamplerate", 1)
    _set_if_exists(retarget_motionclip, "samplerate", source_fps)
    _set_if_exists(retarget_motionclip, "attribs", "*")

    retarget_mc_out = obj.createNode("null", "OUT_SCAGLIONE_RETARGET_MOTIONCLIP")
    retarget_mc_out.setInput(0, retarget_motionclip)

    skin_preview = obj.createNode("kinefx::jointdeform", "SCAGLIONE_SKIN_DEFORM_PREVIEW")
    skin_preview.setInput(0, skin_out)
    skin_preview.setInput(1, target_rest_out)
    skin_preview.setInput(2, retarget_out)
    _set_if_exists(skin_preview, "deletecaptureattrib", 0)

    skin_preview_out = obj.createNode("null", "OUT_SCAGLIONE_SKIN_DEFORM_PREVIEW")
    skin_preview_out.setInput(0, skin_preview)

    note = obj.createStickyNote("NOTES")
    note.setText(
        "Kimodo NPZ -> KineFX MotionClip -> Scaglione FBX target-name retarget.\\n"
        "OUT_SCAGLIONE_RETARGET_POSE is the animated target skeleton.\\n"
        "OUT_SCAGLIONE_RETARGET_MOTIONCLIP stores the MotionClip version.\\n"
        "SCAGLIONE_SKIN_DEFORM_PREVIEW is a first-pass skin deformation check."
    )
    note.setColor(hou.Color((0.95, 0.78, 0.25)))
    note.setBounds(hou.BoundingRect(-6.0, 3.0, -0.5, 1.8))

    obj.layoutChildren()
    hou.setFps(playback_fps)
    end_frame = start_frame + frame_count - 1
    hou.playbar.setFrameRange(start_frame, end_frame)
    hou.playbar.setPlaybackRange(start_frame, end_frame)
    hou.setFrame(start_frame + min(59, frame_count - 1))
    retarget_out.setSelected(True, clear_all_selected=True)

    if hip_path:
        hou.hipFile.save(_as_path(hip_path))

    return {
        "object": obj,
        "source_pose": source_out,
        "source_motionclip": source_mc_out,
        "target_rest": target_rest_out,
        "retarget_pose": retarget_out,
        "retarget_motionclip": retarget_mc_out,
        "skin_preview": skin_preview_out,
    }


def build_scaglione_test_scene():
    """Convenience entry point for this workspace's current Scaglione test."""
    return build_retarget_scene(
        "E:/script/pythonWorkSpace/kimodo_test_outputs/walk_natural_6s_post.npz",
        "Z:/show/ZETA/assets/Character/Scaglione/RIG/wip/maya/fbx/Scaglione_sim_v003.fbx",
        "E:/script/pythonWorkSpace/kimodo_test_outputs/scaglione_kimodo_retarget_test.hip",
        obj_name="kimodo_scaglione_retarget",
        playback_fps=15.0,
    )


def reload_in_houdini():
    module = sys.modules.get(__name__)
    return importlib.reload(module) if module is not None else None
