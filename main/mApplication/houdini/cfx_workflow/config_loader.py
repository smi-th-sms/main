# -*- coding: utf-8 -*-
"""Load and validate CFX workflow configuration files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .path_rules import apply_path_rules
from .schema import ShotConfig


REQUIRED_SHOT_KEYS = {
    "show",
    "sequence",
    "shot",
    "frame_start",
    "frame_end",
    "assets",
}

REQUIRED_ASSET_KEYS = {
    "name",
    "cfx_type",
    "hda",
    "preset",
}


class ConfigError(ValueError):
    """Raised when a CFX workflow config is incomplete or malformed."""


def load_json(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config does not exist: {config_path}")
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {config_path}: {exc}") from exc


def validate_shot_config(data: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_SHOT_KEYS - data.keys())
    if missing:
        raise ConfigError(f"Missing shot config keys: {', '.join(missing)}")

    if int(data["frame_end"]) < int(data["frame_start"]):
        raise ConfigError("frame_end must be greater than or equal to frame_start")

    assets = data.get("assets", [])
    if not isinstance(assets, list) or not assets:
        raise ConfigError("assets must contain at least one CFX asset")

    for index, asset in enumerate(assets):
        missing_asset_keys = sorted(REQUIRED_ASSET_KEYS - asset.keys())
        if missing_asset_keys:
            raise ConfigError(
                f"Asset #{index} is missing keys: {', '.join(missing_asset_keys)}"
            )


def load_shot_config(path: str | Path) -> ShotConfig:
    data = load_json(path)
    validate_shot_config(data)
    try:
        data = apply_path_rules(data)
    except (KeyError, ValueError) as exc:
        raise ConfigError(f"Invalid path_rules block: {exc}") from exc
    return ShotConfig.from_dict(data)

