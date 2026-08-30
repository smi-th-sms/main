# -*- coding: utf-8 -*-
"""Cache validation for CFX workflow results.

Pure-Python checks over written cache files. No ``hou`` dependency, so this
can run from the CLI, a farm post-task, or inside Houdini.
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .schema import AssetConfig, ShotConfig

# Matches Houdini ($F, $F4), padded (####) and printf (%04d) frame tokens.
_FRAME_TOKEN = re.compile(r"\$F\d*|#+|%0?\d*d")

# A frame file smaller than this fraction of the median size is suspicious.
_SMALL_FILE_RATIO = 0.1


@dataclass
class ValidationCheck:
    name: str
    status: str  # "pass" | "warning" | "fail" | "skipped"
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass
class AssetValidation:
    asset: str
    cache_path: str | None
    checks: list[ValidationCheck] = field(default_factory=list)

    @property
    def status(self) -> str:
        return _worst_status(check.status for check in self.checks)

    def as_dict(self) -> dict[str, Any]:
        return {
            "asset": self.asset,
            "cache_path": self.cache_path,
            "status": self.status,
            "checks": [check.as_dict() for check in self.checks],
        }


@dataclass
class ValidationReport:
    shot_id: str
    frame_start: int
    frame_end: int
    generated_at: str
    assets: list[AssetValidation] = field(default_factory=list)

    @property
    def status(self) -> str:
        return _worst_status(asset.status for asset in self.assets)

    def as_dict(self) -> dict[str, Any]:
        return {
            "shot_id": self.shot_id,
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
            "generated_at": self.generated_at,
            "status": self.status,
            "assets": [asset.as_dict() for asset in self.assets],
        }

    def write_json(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.as_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path


_STATUS_ORDER = {"skipped": 0, "pass": 1, "warning": 2, "fail": 3}


def _worst_status(statuses) -> str:
    worst = "pass"
    seen_any = False
    for status in statuses:
        seen_any = True
        if _STATUS_ORDER.get(status, 0) > _STATUS_ORDER[worst]:
            worst = status
    return worst if seen_any else "skipped"


def split_frame_pattern(path: str) -> tuple[str, str] | None:
    """Split a cache path around its frame token.

    Returns ``(prefix, suffix)`` or ``None`` when the path has no frame token
    (a static file such as a single .abc).
    """

    match = _FRAME_TOKEN.search(path)
    if match is None:
        return None
    return path[: match.start()], path[match.end() :]


def collect_frame_files(cache_path: str) -> dict[int, Path]:
    """Find existing files matching the cache path frame pattern.

    Returns a mapping of frame number to file path. Empty when the directory
    does not exist or nothing matches.
    """

    split = split_frame_pattern(cache_path)
    if split is None:
        raise ValueError(f"Cache path has no frame token: {cache_path}")

    prefix, suffix = split
    prefix_path = Path(prefix)
    directory = prefix_path.parent
    name_re = re.compile(
        re.escape(prefix_path.name) + r"(\d+)" + re.escape(suffix) + r"$"
    )

    frames: dict[int, Path] = {}
    if directory.is_dir():
        for entry in directory.iterdir():
            match = name_re.match(entry.name)
            if match and entry.is_file():
                frames[int(match.group(1))] = entry
    return frames


def validate_asset_cache(shot: ShotConfig, asset: AssetConfig) -> AssetValidation:
    result = AssetValidation(asset=asset.name, cache_path=asset.output_cache_path)

    if not asset.output_cache_path:
        result.checks.append(
            ValidationCheck(
                name="cache_exists",
                status="fail",
                message="No output_cache_path configured for this asset.",
            )
        )
        return result

    split = split_frame_pattern(asset.output_cache_path)
    if split is None:
        result.checks.extend(_check_static_file(asset.output_cache_path))
        return result

    frames = collect_frame_files(asset.output_cache_path)
    result.checks.append(_check_cache_exists(asset.output_cache_path, frames))
    if not frames:
        return result

    result.checks.append(_check_frame_coverage(shot, frames))
    result.checks.append(_check_frame_continuity(shot, frames))
    result.checks.append(_check_file_sizes(frames))
    return result


def validate_shot_caches(shot: ShotConfig) -> ValidationReport:
    """Run all cache checks for every asset in the shot."""

    return ValidationReport(
        shot_id=shot.shot_id,
        frame_start=shot.frame_start,
        frame_end=shot.frame_end,
        generated_at=datetime.now().isoformat(timespec="seconds"),
        assets=[validate_asset_cache(shot, asset) for asset in shot.assets],
    )


def _check_static_file(cache_path: str) -> list[ValidationCheck]:
    path = Path(cache_path)
    if not path.is_file():
        return [
            ValidationCheck(
                name="cache_exists",
                status="fail",
                message=f"Static cache file does not exist: {cache_path}",
            )
        ]
    checks = [
        ValidationCheck(
            name="cache_exists",
            status="pass",
            message="Static cache file exists.",
            details={"path": str(path)},
        )
    ]
    size = path.stat().st_size
    checks.append(
        ValidationCheck(
            name="file_size_sanity",
            status="fail" if size == 0 else "pass",
            message="Static cache file is empty." if size == 0 else "File size looks sane.",
            details={"size_bytes": size},
        )
    )
    return checks


def _check_cache_exists(cache_path: str, frames: dict[int, Path]) -> ValidationCheck:
    if not frames:
        return ValidationCheck(
            name="cache_exists",
            status="fail",
            message=f"No cache files match the pattern: {cache_path}",
        )
    return ValidationCheck(
        name="cache_exists",
        status="pass",
        message=f"Found {len(frames)} cache files.",
        details={"file_count": len(frames)},
    )


def _check_frame_coverage(shot: ShotConfig, frames: dict[int, Path]) -> ValidationCheck:
    first, last = min(frames), max(frames)
    covered = first <= shot.frame_start and last >= shot.frame_end
    details = {
        "expected": [shot.frame_start, shot.frame_end],
        "found": [first, last],
    }
    if covered:
        return ValidationCheck(
            name="frame_range_coverage",
            status="pass",
            message="Cache covers the full shot frame range.",
            details=details,
        )
    return ValidationCheck(
        name="frame_range_coverage",
        status="fail",
        message=(
            f"Cache frames {first}-{last} do not cover the shot range "
            f"{shot.frame_start}-{shot.frame_end}."
        ),
        details=details,
    )


def _check_frame_continuity(shot: ShotConfig, frames: dict[int, Path]) -> ValidationCheck:
    expected = set(range(shot.frame_start, shot.frame_end + 1))
    missing = sorted(expected - set(frames))
    if not missing:
        return ValidationCheck(
            name="frame_sequence_continuity",
            status="pass",
            message="No missing frames inside the shot range.",
        )
    return ValidationCheck(
        name="frame_sequence_continuity",
        status="fail",
        message=f"{len(missing)} frames are missing inside the shot range.",
        details={"missing_frames": _summarize_frames(missing)},
    )


def _check_file_sizes(frames: dict[int, Path]) -> ValidationCheck:
    sizes = {frame: path.stat().st_size for frame, path in frames.items()}
    empty = sorted(frame for frame, size in sizes.items() if size == 0)
    if empty:
        return ValidationCheck(
            name="file_size_sanity",
            status="fail",
            message=f"{len(empty)} cache files are empty (0 bytes).",
            details={"empty_frames": _summarize_frames(empty)},
        )

    median_size = statistics.median(sizes.values())
    small = sorted(
        frame
        for frame, size in sizes.items()
        if median_size > 0 and size < median_size * _SMALL_FILE_RATIO
    )
    if small:
        return ValidationCheck(
            name="file_size_sanity",
            status="warning",
            message=(
                f"{len(small)} cache files are much smaller than the median size "
                f"({int(median_size)} bytes)."
            ),
            details={
                "median_size_bytes": int(median_size),
                "small_frames": _summarize_frames(small),
            },
        )
    return ValidationCheck(
        name="file_size_sanity",
        status="pass",
        message="File sizes look sane.",
        details={"median_size_bytes": int(median_size)},
    )


def _summarize_frames(frames: list[int], limit: int = 20) -> list[int] | dict[str, Any]:
    """Keep report payloads small when many frames are listed."""

    if len(frames) <= limit:
        return frames
    return {
        "count": len(frames),
        "first": frames[:limit],
        "last": frames[-1],
    }
