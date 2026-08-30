# -*- coding: utf-8 -*-
"""Centralized show/sequence/shot path and version rules.

All studio path conventions live here so config files, the shot builder,
the validator, and future publish automation share one source of truth.

Path templates are plain ``str.format`` patterns. Override any of them via
the ``path_rules.templates`` block in a shot config; unspecified templates
fall back to the defaults below.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

DEFAULT_TEMPLATES: dict[str, str] = {
    "show_root": "{root}/{show}",
    "shot_root": "{root}/{show}/{sequence}/{shot}",
    "department_root": "{root}/{show}/{sequence}/{shot}/{department}",
    "scene_template": "{root}/{show}/_templates/{department}_shot_template.hip",
    "work_dir": "{department_root}/work",
    "work_scene": "{work_dir}/{shot}_{department}_{version}.hip",
    "input_cache": "{root}/{show}/{sequence}/{shot}/anim/cache/{asset}.abc",
    "cache_dir": "{department_root}/cache/{cfx_type}/{asset}/{version}",
    "cache_file": "{cache_dir}/{asset}.$F4.bgeo.sc",
    "review_dir": "{department_root}/review/{version}",
    "publish_dir": "{department_root}/publish/{version}",
}

_VERSION_RE = re.compile(r"^v(\d+)$")


@dataclass(frozen=True)
class PathRules:
    root: str
    templates: dict[str, str] = field(default_factory=dict)
    version_padding: int = 3

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PathRules":
        if "root" not in data:
            raise ValueError("path_rules requires a 'root' key")
        return cls(
            root=str(data["root"]).rstrip("/\\"),
            templates=dict(data.get("templates", {})),
            version_padding=int(data.get("version_padding", 3)),
        )

    def template(self, name: str) -> str:
        try:
            return self.templates.get(name) or DEFAULT_TEMPLATES[name]
        except KeyError:
            raise KeyError(f"Unknown path template: {name}") from None

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

    def _context(
        self,
        show: str,
        sequence: str,
        shot: str,
        department: str = "cfx",
        version: int | str = 1,
        **extra: str,
    ) -> dict[str, str]:
        ctx: dict[str, str] = {
            "root": self.root,
            "show": show,
            "sequence": sequence,
            "shot": shot,
            "department": department,
            "version": self.format_version(version),
        }
        ctx.update(extra)
        # Resolve composite templates in dependency order so later templates
        # can reference {department_root}, {work_dir}, and {cache_dir}.
        ctx["show_root"] = self.template("show_root").format(**ctx)
        ctx["shot_root"] = self.template("shot_root").format(**ctx)
        ctx["department_root"] = self.template("department_root").format(**ctx)
        ctx["work_dir"] = self.template("work_dir").format(**ctx)
        if "asset" in ctx and "cfx_type" in ctx:
            ctx["cache_dir"] = self.template("cache_dir").format(**ctx)
        return ctx

    def resolve(self, name: str, **kwargs: Any) -> str:
        """Resolve a named template, e.g. ``resolve("review_dir", show=..., ...)``."""
        ctx = self._context(**kwargs)
        return self.template(name).format(**ctx)

    def work_dir(self, show: str, sequence: str, shot: str, department: str = "cfx") -> str:
        return self.resolve("work_dir", show=show, sequence=sequence, shot=shot, department=department)

    def work_scene_path(
        self, show: str, sequence: str, shot: str, version: int | str, department: str = "cfx"
    ) -> str:
        return self.resolve(
            "work_scene", show=show, sequence=sequence, shot=shot, department=department, version=version
        )

    def scene_template_path(self, show: str, department: str = "cfx") -> str:
        # scene_template does not depend on sequence/shot; pass placeholders.
        return self.resolve("scene_template", show=show, sequence="", shot="", department=department)

    def input_cache_path(self, show: str, sequence: str, shot: str, asset: str) -> str:
        return self.resolve("input_cache", show=show, sequence=sequence, shot=shot, asset=asset)

    def cache_path(
        self,
        show: str,
        sequence: str,
        shot: str,
        asset: str,
        cfx_type: str,
        version: int | str,
        department: str = "cfx",
    ) -> str:
        return self.resolve(
            "cache_file",
            show=show,
            sequence=sequence,
            shot=shot,
            department=department,
            version=version,
            asset=asset,
            cfx_type=cfx_type,
        )

    def review_dir(
        self, show: str, sequence: str, shot: str, version: int | str, department: str = "cfx"
    ) -> str:
        return self.resolve(
            "review_dir", show=show, sequence=sequence, shot=shot, department=department, version=version
        )

    def publish_dir(
        self, show: str, sequence: str, shot: str, version: int | str, department: str = "cfx"
    ) -> str:
        return self.resolve(
            "publish_dir", show=show, sequence=sequence, shot=shot, department=department, version=version
        )


def existing_versions(directory: str | Path) -> list[int]:
    """Find ``v###`` entries (files or directories) in a directory, sorted ascending."""

    parent = Path(directory)
    if not parent.is_dir():
        return []
    versions = set()
    for entry in parent.iterdir():
        match = _VERSION_RE.match(entry.name)
        if match:
            versions.add(int(match.group(1)))
        else:
            # Also accept versioned file names such as shot020_cfx_v002.hip
            for token in re.findall(r"v(\d+)", entry.stem):
                versions.add(int(token))
    return sorted(versions)


def next_version(directory: str | Path) -> int:
    """Next version number based on what already exists on disk (1 when empty)."""

    versions = existing_versions(directory)
    return versions[-1] + 1 if versions else 1


def apply_path_rules(data: dict[str, Any]) -> dict[str, Any]:
    """Fill missing path fields in a raw shot config dict using its ``path_rules`` block.

    Explicitly configured paths always win; only absent fields are generated.
    Returns the input unchanged when no ``path_rules`` block is present.
    """

    rules_data = data.get("path_rules")
    if not rules_data:
        return data

    rules = PathRules.from_dict(rules_data)
    show = str(data["show"])
    sequence = str(data["sequence"])
    shot = str(data["shot"])
    department = str(data.get("department", "cfx"))
    version = str(data.get("metadata", {}).get("version", rules.format_version(1)))

    result = dict(data)
    result.setdefault("work_dir", rules.work_dir(show, sequence, shot, department))
    result.setdefault("scene_template", rules.scene_template_path(show, department))
    result.setdefault(
        "shot_scene_path", rules.work_scene_path(show, sequence, shot, version, department)
    )
    result.setdefault("review_dir", rules.review_dir(show, sequence, shot, version, department))

    assets = []
    for asset in data.get("assets", []):
        resolved = dict(asset)
        name = str(resolved.get("name", ""))
        cfx_type = str(resolved.get("cfx_type", ""))
        if name:
            resolved.setdefault("input_cache_path", rules.input_cache_path(show, sequence, shot, name))
            if cfx_type:
                resolved.setdefault(
                    "output_cache_path",
                    rules.cache_path(show, sequence, shot, name, cfx_type, version, department),
                )
        assets.append(resolved)
    result["assets"] = assets
    return result
