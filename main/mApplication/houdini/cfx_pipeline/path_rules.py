# -*- coding: utf-8 -*-
"""Path & version rules for the stage-based CFX pipeline.

Mirrors the real CFX Assets Manager conventions (see
``docs/CFX_ASSETS_HDA_ANALYSIS.md`` §4). Templates are plain ``str.format``
patterns and may reference each other by name — ``asset_work`` can embed
``{asset_root}`` and the resolver expands it recursively. Any template can be
overridden via the ``path_rules.templates`` block in a config file.

Two path families:
  * asset-centric  — reusable character setup (FBX, rest proxy cache)
  * shot-centric   — per-shot animation, sim cache, alembic export
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

# Defaults reflect Manager code (cfx_assets_ui.py) and measured real caches.
# Note the studio uses "Sim" (asset) vs "SIM" (shot) casing; kept as authored.
DEFAULT_TEMPLATES: dict[str, str] = {
    "show_root": "{root}/{show}",
    # --- asset-centric (character, reusable across shots) -----------------
    "asset_root": "{root}/{show}/{asset_subpath}/{asset}",
    "asset_work": "{asset_root}/Sim/wip/houdini",
    "character_fbx_dir": "{asset_root}/RIG/wip/maya/fbx",
    "hair_guide_dir": "{asset_root}/RIG/wip/maya/cache/alembic",
    # rest caches (static, single frame) — the Asset→Shot handoff artifacts
    "asset_proxy_cache": "{asset_work}/geo/{asset}_proxy_rest/{version}/{asset}_proxy_rest.bgeo.sc",
    "asset_hair_cache": "{asset_work}/geo/{asset}_hair_rest/{version}/{asset}_hair_rest.bgeo.sc",
    "asset_collision_cache": "{asset_work}/geo/{asset}_collision_rest/{version}/{asset}_collision_rest.bgeo.sc",
    "asset_corrective_cache": "{asset_work}/geo/{asset}_corrective_rest/{version}/{asset}_corrective_rest.bgeo.sc",
    "asset_skel_cache": "{asset_work}/geo/{asset}_skel_rest/{version}/{asset}_skel_rest.bgeo.sc",
    "asset_constraint_cache": "{asset_work}/geo/{asset}_constraint/{version}/{asset}_constraint.bgeo.sc",
    "asset_hda": "{asset_work}/asset/{asset}.hda",
    # config file locations — asset config lives at the asset path, reused by
    # many shots; shot config lives next to the shot hip.
    "asset_config": "{asset_work}/cfx_asset.json",
    # --- shot-centric ------------------------------------------------------
    "shot_root": "{root}/{show}/{seq_subpath}/{sequence}/{shot}",
    "shot_work": "{shot_root}/SIM/wip/houdini",
    "shot_anim_dir": "{shot_root}/ANM/pub/fbx",
    "shot_sim_cache": "{shot_work}/geo/{asset}_sim/{version}/{asset}_sim.$F4.bgeo.sc",
    "shot_cloth_abc": "{shot_work}/abc/{version}/{asset}_Cloth_Cache.abc",
    "shot_hair_abc": "{shot_work}/abc/{version}/{asset}_Hair_Cache.abc",
    "shot_config": "{shot_work}/cfx_shot.json",
}

# Context keys with sensible studio defaults so callers need not repeat them.
DEFAULT_CONTEXT: dict[str, str] = {
    "asset_subpath": "assets/Character",
    "seq_subpath": "sequences",
}

_VERSION_RE = re.compile(r"^v(\d+)$")
_FORMATTER = string.Formatter()


def _placeholders(template: str) -> list[str]:
    """Field names referenced by a ``str.format`` template (skips literals)."""

    return [name for _, name, _, _ in _FORMATTER.parse(template) if name]


@dataclass(frozen=True)
class PipelinePathRules:
    root: str
    templates: dict[str, str] = field(default_factory=dict)
    context: dict[str, str] = field(default_factory=dict)
    version_padding: int = 3

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PipelinePathRules":
        if "root" not in data:
            raise ValueError("path_rules requires a 'root' key")
        return cls(
            root=str(data["root"]).rstrip("/\\"),
            templates=dict(data.get("templates", {})),
            context=dict(data.get("context", {})),
            version_padding=int(data.get("version_padding", 3)),
        )

    # --- template access ---------------------------------------------------
    def _template_names(self) -> set[str]:
        return set(DEFAULT_TEMPLATES) | set(self.templates)

    def template(self, name: str) -> str:
        value = self.templates.get(name) or DEFAULT_TEMPLATES.get(name)
        if value is None:
            raise KeyError(f"Unknown path template: {name}")
        return value

    # --- version helpers ---------------------------------------------------
    def format_version(self, version: int | str) -> str:
        if isinstance(version, str):
            if _VERSION_RE.match(version):
                return version
            version = int(version)
        return f"v{version:0{self.version_padding}d}"

    def parse_version(self, label: str) -> int:
        match = _VERSION_RE.match(label)
        if match is None:
            raise ValueError(f"Not a version label: {label}")
        return int(match.group(1))

    # --- resolution --------------------------------------------------------
    def _expand(self, template: str, ctx: dict[str, str], _seen: frozenset[str]) -> str:
        values = dict(ctx)
        for field_name in _placeholders(template):
            if field_name in values:
                continue
            # A placeholder that names another template is resolved recursively.
            if field_name in self._template_names():
                if field_name in _seen:
                    raise ValueError(f"Cyclic path template reference: {field_name}")
                values[field_name] = self._expand(
                    self.template(field_name), ctx, _seen | {field_name}
                )
            else:
                raise KeyError(
                    f"Missing context value '{field_name}' while resolving template"
                )
        return template.format(**values)

    def resolve(self, name: str, **ctx: Any) -> str:
        """Resolve a named template with the given context values.

        ``root`` and the studio defaults (``asset_subpath``/``seq_subpath``)
        are injected automatically; ``version`` is normalized to ``v###``.
        """

        merged: dict[str, str] = {"root": self.root}
        merged.update(DEFAULT_CONTEXT)
        merged.update(self.context)
        for key, value in ctx.items():
            if value is None:
                continue
            if key == "version":
                merged[key] = self.format_version(value)
            else:
                merged[key] = str(value)
        return self._expand(self.template(name), merged, frozenset({name}))


def existing_versions(directory: str | Path) -> list[int]:
    """Find ``v###`` entries (files or dirs) in a directory, ascending."""

    parent = Path(directory)
    if not parent.is_dir():
        return []
    versions: set[int] = set()
    for entry in parent.iterdir():
        match = _VERSION_RE.match(entry.name)
        if match:
            versions.add(int(match.group(1)))
        else:
            for token in re.findall(r"v(\d+)", entry.stem):
                versions.add(int(token))
    return sorted(versions)


def next_version(directory: str | Path) -> int:
    """Next version number based on what exists on disk (1 when empty)."""

    versions = existing_versions(directory)
    return versions[-1] + 1 if versions else 1
