# -*- coding: utf-8 -*-
"""Stage-based CFX pipeline (Assets HDA -> config-driven + PDG).

Stages:
  1. Config      — this package's schema/loader/path_rules
  2. Asset Setup — character rig, corrective, collision, proxy, rest cache
  3. Shot Setup  — animation, deform, vellum solve, sim cache
  4. Cache Out   — detail-attach deform, pelvis/head inverse, UE alembic

See ``docs/CFX_ASSETS_HDA_ANALYSIS.md`` for the analysis this is built on.
"""

from __future__ import annotations

from .config_loader import (
    asset_config_path,
    load_asset_config,
    load_pipeline_config,
    load_shot_config,
)
from .path_rules import PipelinePathRules, next_version
from .schema import (
    AssetSetupConfig,
    CacheOutConfig,
    FbxSetup,
    ProxyPart,
    ShotSimConfig,
)

__all__ = [
    "PipelinePathRules",
    "next_version",
    "AssetSetupConfig",
    "ShotSimConfig",
    "FbxSetup",
    "ProxyPart",
    "CacheOutConfig",
    "asset_config_path",
    "load_asset_config",
    "load_shot_config",
    "load_pipeline_config",
]
