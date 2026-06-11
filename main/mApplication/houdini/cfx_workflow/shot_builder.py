# -*- coding: utf-8 -*-
"""Houdini scene construction helpers for CFX shots."""

from __future__ import annotations

import os
from typing import Any

from .schema import AssetConfig, ShotConfig


def build_houdini_scene(shot: ShotConfig) -> dict[str, Any]:
    """Build a CFX shot network in the current Houdini session.

    This function must be called inside Houdini because it imports ``hou``.

    For each asset it creates the chain::

        load_input_cache -> IN_ANIM_CACHE -> sim_<cfx_type> -> write_cfx_cache -> OUT_CFX_CACHE

    The sim node uses the configured HDA type when it is installed, otherwise
    a null placeholder is created so shot setup never fails on a missing HDA.
    Problems are collected into the returned ``warnings`` list instead of
    raising, except for a broken Houdini session itself.

    Returns a structured result::

        {
            "shot_id": str,
            "scene_template": {"path": str | None, "action": "none|missing|loaded|merged"},
            "container": str,            # /obj subnet path
            "assets": {
                asset_name: {
                    "container": str,
                    "input": str | None,
                    "sim": str,
                    "hda_found": bool,
                    "applied_parameters": list[str],
                    "cache": str,
                    "output": str,
                },
            },
            "warnings": list[str],
        }
    """

    try:
        import hou  # type: ignore
    except ImportError as exc:
        raise RuntimeError("build_houdini_scene must run inside Houdini") from exc

    warnings: list[str] = []
    result: dict[str, Any] = {
        "shot_id": shot.shot_id,
        "scene_template": _load_scene_template(hou, shot, warnings),
        "container": None,
        "assets": {},
        "warnings": warnings,
    }

    obj = hou.node("/obj")
    if obj is None:
        raise RuntimeError("Could not find /obj in the current Houdini scene")

    subnet_name = f"cfx_{shot.sequence}_{shot.shot}"
    subnet = obj.node(subnet_name) or obj.createNode("subnet", subnet_name)
    subnet.setComment(f"CFX workflow container for {shot.shot_id}")
    subnet.setGenericFlag(hou.nodeFlag.DisplayComment, True)
    result["container"] = subnet.path()

    for asset in shot.assets:
        result["assets"][asset.name] = _build_asset_network(hou, subnet, shot, asset, warnings)

    subnet.layoutChildren()
    return result


def _load_scene_template(hou, shot: ShotConfig, warnings: list[str]) -> dict[str, Any]:
    """Load or merge the configured scene template without clobbering user work."""

    info: dict[str, Any] = {"path": shot.scene_template, "action": "none"}
    if not shot.scene_template:
        return info

    if not os.path.exists(shot.scene_template):
        warnings.append(f"Scene template not found: {shot.scene_template}")
        info["action"] = "missing"
        return info

    hip = hou.hipFile
    is_fresh_session = hip.basename() == "untitled.hip" and not hip.hasUnsavedChanges()
    if is_fresh_session:
        hip.load(shot.scene_template, suppress_save_prompt=True)
        info["action"] = "loaded"
    else:
        hip.merge(shot.scene_template)
        info["action"] = "merged"
        warnings.append(
            "Current session already has content; "
            f"merged scene template instead of loading it: {shot.scene_template}"
        )
    return info


def _build_asset_network(
    hou,
    subnet,
    shot: ShotConfig,
    asset: AssetConfig,
    warnings: list[str],
) -> dict[str, Any]:
    container_name = f"{asset.cfx_type}_{asset.name}".replace(" ", "_")
    geo = subnet.node(container_name) or subnet.createNode("geo", container_name)
    geo.setComment(f"{asset.hda} | preset={asset.preset} | quality={asset.quality}")
    geo.setGenericFlag(hou.nodeFlag.DisplayComment, True)

    input_node = _create_input_loader(hou, geo, asset, warnings)

    null_in = geo.node("IN_ANIM_CACHE") or geo.createNode("null", "IN_ANIM_CACHE")
    if input_node is not None:
        null_in.setInput(0, input_node)

    sim_node, hda_found = _create_sim_node(hou, geo, asset, warnings)
    sim_node.setInput(0, null_in)
    applied = _apply_parameters(sim_node, asset.parameters, asset.name, warnings)

    cache_node = _create_cache_node(hou, geo, shot, asset, warnings)
    cache_node.setInput(0, sim_node)

    null_out = geo.node("OUT_CFX_CACHE") or geo.createNode("null", "OUT_CFX_CACHE")
    null_out.setInput(0, cache_node)
    null_out.setDisplayFlag(True)
    null_out.setRenderFlag(True)

    geo.layoutChildren()
    return {
        "container": geo.path(),
        "input": input_node.path() if input_node is not None else None,
        "sim": sim_node.path(),
        "hda_found": hda_found,
        "applied_parameters": applied,
        "cache": cache_node.path(),
        "output": null_out.path(),
    }


def _create_input_loader(hou, geo, asset: AssetConfig, warnings: list[str]):
    node_name = "load_input_cache"
    existing = geo.node(node_name)
    if existing is not None:
        return existing

    if not asset.input_cache_path:
        warnings.append(
            f"{asset.name}: no input_cache_path configured; IN_ANIM_CACHE is left unconnected"
        )
        return None

    is_alembic = asset.input_cache_path.lower().endswith(".abc")
    type_name = "alembic" if is_alembic else "file"
    parm_name = "fileName" if is_alembic else "file"

    try:
        node = geo.createNode(type_name, node_name)
    except hou.OperationFailed as exc:
        warnings.append(
            f"{asset.name}: could not create '{type_name}' loader ({exc}); created placeholder null"
        )
        return geo.createNode("null", node_name)

    _set_parm(node, parm_name, asset.input_cache_path, asset.name, warnings)
    return node


def _create_sim_node(hou, geo, asset: AssetConfig, warnings: list[str]):
    node_name = f"sim_{asset.cfx_type}"
    node_type = hou.nodeType(hou.sopNodeTypeCategory(), asset.hda)

    existing = geo.node(node_name)
    if existing is not None:
        matches = node_type is not None and existing.type().name() == node_type.name()
        if node_type is not None and not matches:
            warnings.append(
                f"{asset.name}: existing sim node {existing.path()} is type "
                f"'{existing.type().name()}', expected '{asset.hda}'; left unchanged"
            )
        return existing, matches

    if node_type is None:
        warnings.append(
            f"{asset.name}: HDA type '{asset.hda}' not installed; created placeholder null instead"
        )
        node = geo.createNode("null", node_name)
        node.setComment(f"Placeholder for missing HDA {asset.hda}")
        node.setGenericFlag(hou.nodeFlag.DisplayComment, True)
        return node, False

    node = geo.createNode(node_type.name(), node_name)
    node.setComment(f"{asset.hda} | preset={asset.preset}")
    node.setGenericFlag(hou.nodeFlag.DisplayComment, True)
    return node, True


def _create_cache_node(hou, geo, shot: ShotConfig, asset: AssetConfig, warnings: list[str]):
    node_name = "write_cfx_cache"
    existing = geo.node(node_name)
    if existing is not None:
        return existing

    try:
        node = geo.createNode("filecache", node_name)
    except hou.OperationFailed as exc:
        warnings.append(
            f"{asset.name}: could not create 'filecache' node ({exc}); created placeholder null"
        )
        return geo.createNode("null", node_name)

    if asset.output_cache_path:
        # filecache 2.0 builds the path from pieces unless filemethod is explicit.
        if node.parm("filemethod") is not None:
            _set_parm(node, "filemethod", 1, asset.name, warnings)
        _set_parm(node, "file", asset.output_cache_path, asset.name, warnings)
    else:
        warnings.append(f"{asset.name}: no output_cache_path configured on {node.path()}")

    if node.parm("trange") is not None:
        _set_parm(node, "trange", 1, asset.name, warnings)
    frame_parms = node.parmTuple("f")
    if frame_parms is not None:
        for parm, value in zip(frame_parms, (shot.frame_start, shot.frame_end)):
            parm.deleteAllKeyframes()
            parm.set(value)
    else:
        warnings.append(
            f"{asset.name}: frame range parameter 'f' not found on {node.path()}"
        )
    return node


def _apply_parameters(node, parameters: dict[str, Any], asset_name: str, warnings: list[str]) -> list[str]:
    applied: list[str] = []
    for name, value in parameters.items():
        if isinstance(value, (list, tuple)):
            parm_tuple = node.parmTuple(name)
            if parm_tuple is None:
                warnings.append(f"{asset_name}: parameter '{name}' not found on {node.path()}")
                continue
            try:
                parm_tuple.set(tuple(value))
                applied.append(name)
            except Exception as exc:
                warnings.append(f"{asset_name}: failed to set '{name}' on {node.path()}: {exc}")
        elif _set_parm(node, name, value, asset_name, warnings):
            applied.append(name)
    return applied


def _set_parm(node, parm_name: str, value: Any, asset_name: str, warnings: list[str]) -> bool:
    parm = node.parm(parm_name)
    if parm is None:
        warnings.append(f"{asset_name}: parameter '{parm_name}' not found on {node.path()}")
        return False
    try:
        parm.deleteAllKeyframes()
        parm.set(value)
    except Exception as exc:
        warnings.append(f"{asset_name}: failed to set '{parm_name}' on {node.path()}: {exc}")
        return False
    return True
