# -*- coding: utf-8 -*-
"""Review issue routing for the CFX workflow.

``route_issue`` maps a review issue to an actionable ``FixAction``: which
asset to touch, which frames to resim (with padding, clamped to the shot
range), a suggested parameter patch, and whether a partial resim is enough.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from .schema import ReviewIssue, ShotConfig

# Frames added on both sides of the reported issue frames so the resim
# blends back into the surrounding cached motion.
DEFAULT_FRAME_PADDING = 10


@dataclass(frozen=True)
class FixAction:
    action_type: str
    label: str
    requires_hda_update: bool = False
    requires_scene_rebuild: bool = False
    requires_resim: bool = True
    allows_partial_resim: bool = False
    resim_scope: str = "full"  # "none" | "partial" | "full"
    target_asset: str | None = None
    frame_range: tuple[int, int] | None = None
    # Patch entries: {"parm": str, "op": "scale" | "add" | "set", "value": number}
    parameter_patch: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "label": self.label,
            "requires_hda_update": self.requires_hda_update,
            "requires_scene_rebuild": self.requires_scene_rebuild,
            "requires_resim": self.requires_resim,
            "resim_scope": self.resim_scope,
            "target_asset": self.target_asset,
            "frame_range": list(self.frame_range) if self.frame_range else None,
            "parameter_patch": [dict(entry) for entry in self.parameter_patch],
        }


ISSUE_FIX_MAP = {
    "penetration": FixAction(
        action_type="collision_tuning",
        label="Adjust collision thickness and local constraints",
        requires_resim=True,
        allows_partial_resim=True,
        parameter_patch=[
            {"parm": "collision_thickness", "op": "scale", "value": 1.5},
            {"parm": "substeps", "op": "add", "value": 1},
        ],
    ),
    "unstable_sim": FixAction(
        action_type="solver_tuning",
        label="Increase substeps or reduce timestep",
        requires_resim=True,
        # Instability invalidates the whole cache; partial resim would pop.
        allows_partial_resim=False,
        parameter_patch=[
            {"parm": "substeps", "op": "add", "value": 2},
        ],
    ),
    "wrong_input_cache": FixAction(
        action_type="refresh_inputs",
        label="Refresh animation/input cache and rebuild shot scene",
        requires_scene_rebuild=True,
        requires_resim=True,
    ),
    "hda_change": FixAction(
        action_type="hda_iteration",
        label="Update HDA definition or preset before resim",
        requires_hda_update=True,
        requires_scene_rebuild=True,
        requires_resim=True,
    ),
    "preview_only": FixAction(
        action_type="preview_regen",
        label="Regenerate preview without simulation changes",
        requires_resim=False,
        resim_scope="none",
    ),
}

_MANUAL_REVIEW = FixAction(
    action_type="manual_review",
    label="Manual CFX artist review required",
    requires_resim=True,
)


def issue_frame_range(
    issue: ReviewIssue,
    shot: ShotConfig | None = None,
    frame_padding: int = DEFAULT_FRAME_PADDING,
) -> tuple[int, int] | None:
    """Padded frame range around the issue frames, clamped to the shot range."""

    if not issue.frames:
        return None
    start = min(issue.frames) - frame_padding
    end = max(issue.frames) + frame_padding
    if shot is not None:
        start = max(start, shot.frame_start)
        end = min(end, shot.frame_end)
    return start, end


def route_issue(
    issue: ReviewIssue,
    shot: ShotConfig | None = None,
    frame_padding: int = DEFAULT_FRAME_PADDING,
) -> FixAction:
    """Resolve a review issue to a concrete, issue-specific fix action."""

    base = ISSUE_FIX_MAP.get(issue.issue_type, _MANUAL_REVIEW)
    frame_range = issue_frame_range(issue, shot, frame_padding)

    if not base.requires_resim:
        scope = "none"
    elif base.allows_partial_resim and frame_range is not None:
        scope = "partial"
    else:
        scope = "full"

    return replace(
        base,
        target_asset=issue.asset,
        frame_range=frame_range,
        resim_scope=scope,
    )
