"""Import Kimodo SOMA NPZ motion as Houdini KineFX-style SOP geometry.

This module is intentionally Houdini-only at runtime. It does not require the
Kimodo Python package inside Houdini; the SOMA77 joint order and hierarchy are
embedded from Kimodo's skeleton definition.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import numpy as np


SOMA77_NAMES = [
    "Hips",
    "Spine1",
    "Spine2",
    "Chest",
    "Neck1",
    "Neck2",
    "Head",
    "HeadEnd",
    "Jaw",
    "LeftEye",
    "RightEye",
    "LeftShoulder",
    "LeftArm",
    "LeftForeArm",
    "LeftHand",
    "LeftHandThumb1",
    "LeftHandThumb2",
    "LeftHandThumb3",
    "LeftHandThumbEnd",
    "LeftHandIndex1",
    "LeftHandIndex2",
    "LeftHandIndex3",
    "LeftHandIndex4",
    "LeftHandIndexEnd",
    "LeftHandMiddle1",
    "LeftHandMiddle2",
    "LeftHandMiddle3",
    "LeftHandMiddle4",
    "LeftHandMiddleEnd",
    "LeftHandRing1",
    "LeftHandRing2",
    "LeftHandRing3",
    "LeftHandRing4",
    "LeftHandRingEnd",
    "LeftHandPinky1",
    "LeftHandPinky2",
    "LeftHandPinky3",
    "LeftHandPinky4",
    "LeftHandPinkyEnd",
    "RightShoulder",
    "RightArm",
    "RightForeArm",
    "RightHand",
    "RightHandThumb1",
    "RightHandThumb2",
    "RightHandThumb3",
    "RightHandThumbEnd",
    "RightHandIndex1",
    "RightHandIndex2",
    "RightHandIndex3",
    "RightHandIndex4",
    "RightHandIndexEnd",
    "RightHandMiddle1",
    "RightHandMiddle2",
    "RightHandMiddle3",
    "RightHandMiddle4",
    "RightHandMiddleEnd",
    "RightHandRing1",
    "RightHandRing2",
    "RightHandRing3",
    "RightHandRing4",
    "RightHandRingEnd",
    "RightHandPinky1",
    "RightHandPinky2",
    "RightHandPinky3",
    "RightHandPinky4",
    "RightHandPinkyEnd",
    "LeftLeg",
    "LeftShin",
    "LeftFoot",
    "LeftToeBase",
    "LeftToeEnd",
    "RightLeg",
    "RightShin",
    "RightFoot",
    "RightToeBase",
    "RightToeEnd",
]

SOMA77_PARENTS = [
    -1,
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    6,
    6,
    6,
    3,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    14,
    19,
    20,
    21,
    22,
    14,
    24,
    25,
    26,
    27,
    14,
    29,
    30,
    31,
    32,
    14,
    34,
    35,
    36,
    37,
    3,
    39,
    40,
    41,
    42,
    43,
    44,
    45,
    42,
    47,
    48,
    49,
    50,
    42,
    52,
    53,
    54,
    55,
    42,
    57,
    58,
    59,
    60,
    42,
    62,
    63,
    64,
    65,
    0,
    67,
    68,
    69,
    70,
    0,
    72,
    73,
    74,
    75,
]

_NPZ_CACHE: dict[tuple[str, float], dict[str, np.ndarray]] = {}


def _load_npz(path: str) -> dict[str, np.ndarray]:
    norm = os.path.abspath(path)
    key = (norm, os.path.getmtime(norm))
    cached = _NPZ_CACHE.get(key)
    if cached is not None:
        return cached

    with np.load(norm, allow_pickle=False) as data:
        out = {name: np.asarray(data[name]) for name in data.files}

    required = ("posed_joints", "local_rot_mats", "global_rot_mats", "root_positions")
    missing = [name for name in required if name not in out]
    if missing:
        raise ValueError(f"Kimodo NPZ is missing required keys: {missing}")

    if out["posed_joints"].ndim != 3 or out["posed_joints"].shape[1:] != (77, 3):
        raise ValueError(f"posed_joints must be shaped (T, 77, 3), got {out['posed_joints'].shape}")
    if out["local_rot_mats"].shape[:2] != out["posed_joints"].shape[:2]:
        raise ValueError("local_rot_mats and posed_joints frame/joint dimensions do not match")
    if out["global_rot_mats"].shape[:2] != out["posed_joints"].shape[:2]:
        raise ValueError("global_rot_mats and posed_joints frame/joint dimensions do not match")

    _NPZ_CACHE.clear()
    _NPZ_CACHE[key] = out
    return out


def _add_attribs(geo):
    import hou

    return {
        "name": geo.addAttrib(hou.attribType.Point, "name", ""),
        "parent_idx": geo.addAttrib(hou.attribType.Point, "parent_idx", -1),
        "transform": geo.addAttrib(hou.attribType.Point, "transform", [1.0] * 9),
        "localtransform": geo.addAttrib(hou.attribType.Point, "localtransform", [1.0] * 16),
        "kimodo_frame": geo.addAttrib(hou.attribType.Point, "kimodo_frame", 0),
        "source": geo.addAttrib(hou.attribType.Global, "kimodo_source", ""),
        "clip_fps": geo.addAttrib(hou.attribType.Global, "clip_fps", 30.0),
        "clip_frames": geo.addAttrib(hou.attribType.Global, "clip_frames", 0),
    }


def _matrix3_flat(m: np.ndarray) -> tuple[float, ...]:
    return tuple(float(v) for v in m.reshape(-1))


def _matrix4_flat(rotation: np.ndarray, translation: np.ndarray) -> tuple[float, ...]:
    r = rotation
    t = translation
    return (
        float(r[0, 0]),
        float(r[0, 1]),
        float(r[0, 2]),
        0.0,
        float(r[1, 0]),
        float(r[1, 1]),
        float(r[1, 2]),
        0.0,
        float(r[2, 0]),
        float(r[2, 1]),
        float(r[2, 2]),
        0.0,
        float(t[0]),
        float(t[1]),
        float(t[2]),
        1.0,
    )


def _frame_index(frame: float, start_frame: float, frame_offset: int, frame_count: int) -> int:
    idx = int(round(frame - start_frame)) + int(frame_offset)
    return max(0, min(frame_count - 1, idx))


def cook_python_sop(
    node,
    npz_path: str,
    *,
    scale: float = 1.0,
    start_frame: float = 1.0,
    frame_offset: int = 0,
    source_fps: float = 30.0,
) -> None:
    """Cook a Python SOP into a frame-dependent KineFX skeleton pose."""
    import hou

    data = _load_npz(npz_path)
    positions_all = data["posed_joints"]
    local_rot_all = data["local_rot_mats"]
    global_rot_all = data["global_rot_mats"]
    frame_count = int(positions_all.shape[0])
    idx = _frame_index(hou.frame(), start_frame, frame_offset, frame_count)

    positions = positions_all[idx].astype(np.float64) * float(scale)
    local_rot = local_rot_all[idx].astype(np.float64)
    global_rot = global_rot_all[idx].astype(np.float64)

    geo = node.geometry()
    geo.clear()
    attribs = _add_attribs(geo)
    geo.setGlobalAttribValue(attribs["source"], os.path.abspath(npz_path).replace("\\", "/"))
    geo.setGlobalAttribValue(attribs["clip_fps"], float(source_fps))
    geo.setGlobalAttribValue(attribs["clip_frames"], frame_count)

    points = []
    for i, name in enumerate(SOMA77_NAMES):
        parent = SOMA77_PARENTS[i]
        point = geo.createPoint()
        point.setPosition(hou.Vector3(tuple(float(v) for v in positions[i])))
        point.setAttribValue(attribs["name"], name)
        point.setAttribValue(attribs["parent_idx"], int(parent))
        point.setAttribValue(attribs["kimodo_frame"], int(idx))
        point.setAttribValue(attribs["transform"], _matrix3_flat(global_rot[i]))

        if parent < 0:
            local_t = positions[i]
        else:
            local_t = global_rot[parent].T @ (positions[i] - positions[parent])
        point.setAttribValue(attribs["localtransform"], _matrix4_flat(local_rot[i], local_t))
        points.append(point)

    for i, parent in enumerate(SOMA77_PARENTS):
        if parent < 0:
            continue
        poly = geo.createPolygon()
        poly.setIsClosed(False)
        poly.addVertex(points[parent])
        poly.addVertex(points[i])


def _python_sop_code(module_dir: str, npz_path: str, scale: float, start_frame: float, source_fps: float) -> str:
    module_dir = module_dir.replace("\\", "/")
    npz_path = npz_path.replace("\\", "/")
    return f"""import importlib, sys
module_dir = r"{module_dir}"
if module_dir not in sys.path:
    sys.path.insert(0, module_dir)
import kimodo_npz_kinefx_importer
importlib.reload(kimodo_npz_kinefx_importer)
kimodo_npz_kinefx_importer.cook_python_sop(
    hou.pwd(),
    r"{npz_path}",
    scale={float(scale)!r},
    start_frame={float(start_frame)!r},
    source_fps={float(source_fps)!r},
)
"""


def create_import_network(
    npz_path: str,
    *,
    obj_name: str = "kimodo_npz_kinefx",
    scale: float = 1.0,
    source_fps: float = 30.0,
    playback_fps: float | None = None,
    start_frame: int = 1,
    hip_path: str | None = None,
):
    """Create a Houdini object network that imports a Kimodo NPZ as KineFX geometry."""
    import hou

    npz_path = os.path.abspath(npz_path)
    data = _load_npz(npz_path)
    frame_count = int(data["posed_joints"].shape[0])
    playback_fps = float(playback_fps if playback_fps is not None else source_fps)

    obj = hou.node("/obj").createNode("geo", obj_name)
    for child in obj.children():
        child.destroy()

    py = obj.createNode("python", "kimodo_npz_to_kinefx")
    py.parm("python").set(
        _python_sop_code(
            str(Path(__file__).resolve().parent),
            npz_path,
            scale,
            start_frame,
            source_fps,
        )
    )

    rigdoctor = obj.createNode("kinefx::rigdoctor", "kinefx_validate")
    rigdoctor.setInput(0, py)
    if rigdoctor.parm("outputparentidx") is not None:
        rigdoctor.parm("outputparentidx").set(1)
    if rigdoctor.parm("inittransforms") is not None:
        rigdoctor.parm("inittransforms").set(0)

    out = obj.createNode("null", "OUT_KIMODO_KINEFX")
    out.setInput(0, rigdoctor)
    out.setDisplayFlag(True)
    out.setRenderFlag(True)
    obj.layoutChildren()

    hou.setFps(playback_fps)
    end_frame = start_frame + frame_count - 1
    hou.playbar.setFrameRange(start_frame, end_frame)
    hou.playbar.setPlaybackRange(start_frame, end_frame)
    hou.setFrame(start_frame)
    obj.setSelected(True, clear_all_selected=True)

    if hip_path:
        hou.hipFile.save(hip_path)

    return obj, out


def create_scene_from_houdini(
    npz_path: str,
    hip_path: str,
    *,
    obj_name: str = "kimodo_npz_kinefx",
    scale: float = 1.0,
    source_fps: float = 30.0,
    playback_fps: float | None = None,
):
    import hou

    hou.hipFile.clear(suppress_save_prompt=True)
    return create_import_network(
        npz_path,
        obj_name=obj_name,
        scale=scale,
        source_fps=source_fps,
        playback_fps=playback_fps,
        hip_path=hip_path,
    )


def reload_in_houdini():
    """Convenience for a Houdini Python shell."""
    module = sys.modules.get(__name__)
    return importlib.reload(module) if module is not None else None
