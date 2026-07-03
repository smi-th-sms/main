# -*- coding: utf-8 -*-
"""Load pipeline config JSON and resolve paths via :mod:`path_rules`.

A config file may hold an ``asset`` block, a ``shot`` block, or both, plus a
shared ``path_rules`` block. Explicitly authored path fields always win; only
absent ones are generated — matching ``cfx_workflow``'s behaviour.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .path_rules import PipelinePathRules
from .schema import AssetSetupConfig, ShotSimConfig


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _version(block: dict[str, Any]) -> str:
    return str(block.get("metadata", {}).get("version", "v001"))


def resolve_asset_paths(
    data: dict[str, Any], rules: PipelinePathRules
) -> dict[str, Any]:
    """Fill an asset block's missing path fields from ``rules``."""

    show = str(data["show"])
    asset = str(data["asset"])
    version = _version(data)
    ctx = dict(show=show, asset=asset, version=version)

    result = dict(data)
    result.setdefault("character_fbx_dir", rules.resolve("character_fbx_dir", **ctx))
    result.setdefault("hair_guide_dir", rules.resolve("hair_guide_dir", **ctx))
    result.setdefault("asset_work", rules.resolve("asset_work", **ctx))
    result.setdefault("proxy_cache_path", rules.resolve("asset_proxy_cache", **ctx))
    result.setdefault("hair_cache_path", rules.resolve("asset_hair_cache", **ctx))
    result.setdefault("collision_cache_path", rules.resolve("asset_collision_cache", **ctx))
    result.setdefault("corrective_cache_path", rules.resolve("asset_corrective_cache", **ctx))
    result.setdefault("skel_cache_path", rules.resolve("asset_skel_cache", **ctx))
    result.setdefault(
        "constraint_cache_path", rules.resolve("asset_constraint_cache", **ctx)
    )
    return result


def resolve_shot_paths(
    data: dict[str, Any], rules: PipelinePathRules
) -> dict[str, Any]:
    """Fill a shot block's missing path fields from ``rules``."""

    show = str(data["show"])
    sequence = str(data["sequence"])
    shot = str(data["shot"])
    asset = str(data["asset"])
    version = _version(data)
    ctx = dict(show=show, sequence=sequence, shot=shot, asset=asset, version=version)

    result = dict(data)
    result.setdefault("shot_work", rules.resolve("shot_work", **ctx))
    result.setdefault("shot_anim_dir", rules.resolve("shot_anim_dir", **ctx))
    result.setdefault("sim_cache_path", rules.resolve("shot_sim_cache", **ctx))
    result.setdefault("cloth_abc_path", rules.resolve("shot_cloth_abc", **ctx))
    result.setdefault("hair_abc_path", rules.resolve("shot_hair_abc", **ctx))
    # The Asset->Shot handoff: shot reads the asset's static rest caches.
    # Uses the asset's own version if provided, else the shot's version.
    actx = dict(show=show, asset=asset, version=version)
    result.setdefault("asset_proxy_cache", rules.resolve("asset_proxy_cache", **actx))
    result.setdefault("asset_hair_cache", rules.resolve("asset_hair_cache", **actx))
    result.setdefault("asset_collision_cache", rules.resolve("asset_collision_cache", **actx))
    result.setdefault("asset_corrective_cache", rules.resolve("asset_corrective_cache", **actx))
    result.setdefault("asset_skel_cache", rules.resolve("asset_skel_cache", **actx))
    result.setdefault("asset_constraint_cache", rules.resolve("asset_constraint_cache", **actx))
    return result


def _link_asset_caches(resolved: dict[str, Any], asset: AssetSetupConfig) -> None:
    """Override the shot's handoff cache paths with the asset config's resolved
    ones (the asset's own version wins). Mutates ``resolved`` in place."""

    for shot_key, asset_attr in (
        ("asset_proxy_cache", "proxy_cache_path"),
        ("asset_hair_cache", "hair_cache_path"),
        ("asset_collision_cache", "collision_cache_path"),
        ("asset_corrective_cache", "corrective_cache_path"),
        ("asset_skel_cache", "skel_cache_path"),
        ("asset_constraint_cache", "constraint_cache_path"),
    ):
        value = getattr(asset, asset_attr, None)
        if value:
            resolved[shot_key] = value


def _rules_for(block: dict[str, Any], data: dict[str, Any]) -> PipelinePathRules:
    rules_data = block.get("path_rules") or data.get("path_rules")
    if not rules_data:
        raise ValueError("config requires a 'path_rules' block (at top level or in the block)")
    return PipelinePathRules.from_dict(rules_data)


def asset_config_path(show: str, asset: str, rules: PipelinePathRules) -> str:
    """Where the asset config file lives (``{asset_work}/cfx_asset.json``)."""

    return rules.resolve("asset_config", show=show, asset=asset)


def _block(data: dict[str, Any], key: str) -> dict[str, Any]:
    """Return the named sub-block if wrapped ({"asset": {...}}), else the
    bare top-level dict. Guards against a bare field of the same name
    (e.g. ``"asset": "Jake"``) being mistaken for the block."""

    value = data.get(key)
    return value if isinstance(value, dict) else data


def load_asset_config(path: str | Path) -> AssetSetupConfig:
    data = _read_json(path)
    block = _block(data, "asset")
    rules = _rules_for(block, data)
    return AssetSetupConfig.from_dict(resolve_asset_paths(block, rules))


def _try_load_sibling_asset(
    block: dict[str, Any], rules: PipelinePathRules
) -> AssetSetupConfig | None:
    """Locate + load the asset config referenced by a shot block, if present.

    The shot names its asset; the asset config lives at a rules-derived path,
    so a shot loads standalone and still gets the authoritative handoff cache.
    """

    show, asset = block.get("show"), block.get("asset")
    if not show or not asset:
        return None
    candidate = Path(asset_config_path(str(show), str(asset), rules))
    if candidate.is_file():
        return load_asset_config(candidate)
    return None


def load_shot_config(
    path: str | Path, asset: AssetSetupConfig | None = None
) -> ShotSimConfig:
    """Load a shot config; auto-links its asset's rest-proxy cache.

    ``asset`` may be passed explicitly; otherwise the sibling asset config is
    auto-discovered at its rules-derived path. If neither is available, the
    handoff cache path is still derived from ``path_rules`` (best-effort).
    """

    data = _read_json(path)
    block = _block(data, "shot")
    rules = _rules_for(block, data)
    resolved = resolve_shot_paths(block, rules)
    if asset is None:
        asset = _try_load_sibling_asset(block, rules)
    # An asset config's resolved rest caches are authoritative (its own version).
    if asset is not None:
        _link_asset_caches(resolved, asset)
    return ShotSimConfig.from_dict(resolved)


def load_pipeline_config(
    path: str | Path,
) -> tuple[AssetSetupConfig | None, ShotSimConfig | None]:
    """Load a combined file containing ``asset`` and/or ``shot`` blocks.

    The shot's ``asset_proxy_cache`` is linked to the asset block when both
    are present, so the handoff path stays consistent from a single file.
    """

    data = _read_json(path)
    asset_cfg: AssetSetupConfig | None = None
    shot_cfg: ShotSimConfig | None = None

    if isinstance(data.get("asset"), dict):
        rules = _rules_for(data["asset"], data)
        asset_cfg = AssetSetupConfig.from_dict(resolve_asset_paths(data["asset"], rules))
    if isinstance(data.get("shot"), dict):
        rules = _rules_for(data["shot"], data)
        resolved = resolve_shot_paths(data["shot"], rules)
        if asset_cfg is not None:
            _link_asset_caches(resolved, asset_cfg)
        shot_cfg = ShotSimConfig.from_dict(resolved)

    if asset_cfg is None and shot_cfg is None:
        raise ValueError("config must contain an 'asset' and/or 'shot' block")
    return asset_cfg, shot_cfg
