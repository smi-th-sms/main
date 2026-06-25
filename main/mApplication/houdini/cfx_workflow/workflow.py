# -*- coding: utf-8 -*-
"""Build dynamic CFX workflow plans from shot configuration."""

from __future__ import annotations

from pathlib import Path

from .review import FixAction, route_issue
from .schema import AssetConfig, ShotConfig, WorkflowPlan, WorkflowStage, WorkflowTask
from .validator import collect_frame_files, split_frame_pattern


def _path_exists(path: str | None) -> bool:
    if not path:
        return False
    # Frame-sequence caches embed a token ($F4/####/%04d) that never matches a
    # literal file on disk, so a plain ``Path.exists()`` always reports False.
    # Resolve the token to the actual frame files before deciding.
    if split_frame_pattern(path) is not None:
        try:
            return bool(collect_frame_files(path))
        except ValueError:
            return False
    return Path(path).exists()


def _asset_task_id(prefix: str, asset: AssetConfig) -> str:
    safe_name = asset.name.replace(" ", "_").lower()
    return f"{prefix}_{safe_name}"


def _asset_resim_scope(
    shot: ShotConfig,
    actions: list[FixAction],
    cache_exists: bool,
) -> tuple[str, list[int] | None]:
    """Decide how much of an asset needs resimming based on its fix actions.

    A full resim wins over partial; partial ranges are merged into one span.
    With no fix actions targeting the asset, a missing cache or forced resim
    means a full pass over the shot range.
    """

    resim_actions = [action for action in actions if action.requires_resim]
    if resim_actions:
        if any(action.resim_scope == "full" for action in resim_actions):
            return "full", None
        partial_ranges = [
            action.frame_range for action in resim_actions if action.frame_range is not None
        ]
        if partial_ranges:
            return "partial", [
                min(start for start, _ in partial_ranges),
                max(end for _, end in partial_ranges),
            ]
        return "full", None

    if cache_exists and not shot.batch.force_resim:
        return "none", None
    return "full", None


def build_workflow_plan(shot: ShotConfig) -> WorkflowPlan:
    """Create a dynamic task plan for a CFX shot.

    The plan is intentionally declarative. TOPs/PDG, a farm submitter, or a
    Houdini Python runner can consume the same task data later.
    """

    tasks: list[WorkflowTask] = []

    for asset in shot.assets:
        tasks.append(
            WorkflowTask(
                task_id=_asset_task_id("hda_check", asset),
                stage=WorkflowStage.HDA_CHECK,
                label=f"Check HDA {asset.hda} for {asset.name}",
                metadata={
                    "asset": asset.name,
                    "cfx_type": asset.cfx_type,
                    "hda": asset.hda,
                    "preset": asset.preset,
                    "quality": asset.quality,
                },
            )
        )

    setup_deps = [_asset_task_id("hda_check", asset) for asset in shot.assets]
    setup_task = WorkflowTask(
        task_id="shot_setup",
        stage=WorkflowStage.SHOT_SETUP,
        label=f"Build CFX shot scene for {shot.sequence}/{shot.shot}",
        depends_on=setup_deps,
        metadata={
            "scene_template": shot.scene_template,
            "shot_scene_path": shot.shot_scene_path,
            "work_dir": shot.work_dir,
        },
    )
    tasks.append(setup_task)

    open_issues = [issue for issue in shot.review_issues if issue.is_open]
    fix_task_ids: list[str] = []
    asset_fix_actions: dict[str, list[FixAction]] = {}
    for index, issue in enumerate(open_issues, start=1):
        action = route_issue(issue, shot)
        task_id = f"fix_{index:02d}_{action.action_type}"
        fix_task_ids.append(task_id)
        if action.target_asset:
            asset_fix_actions.setdefault(action.target_asset, []).append(action)
        tasks.append(
            WorkflowTask(
                task_id=task_id,
                stage=WorkflowStage.FIX,
                label=action.label,
                depends_on=["shot_setup"],
                metadata={
                    "asset": issue.asset,
                    "issue_type": issue.issue_type,
                    "description": issue.description,
                    "frames": issue.frames,
                    "severity": issue.severity,
                    "fix_action": action.as_dict(),
                },
            )
        )

        if action.requires_hda_update and issue.asset:
            tasks.append(
                WorkflowTask(
                    task_id=f"hda_publish_{issue.asset}",
                    stage=WorkflowStage.HDA_PUBLISH,
                    label=f"Publish updated HDA or preset for {issue.asset}",
                    depends_on=[task_id],
                    metadata={"asset": issue.asset, "issue_type": issue.issue_type},
                )
            )

    sim_task_ids: list[str] = []
    for asset in shot.assets:
        cache_exists = _path_exists(asset.output_cache_path)
        should_skip_sim = cache_exists and not shot.batch.force_resim and not open_issues
        resim_scope, resim_frame_range = _asset_resim_scope(
            shot, asset_fix_actions.get(asset.name, []), cache_exists
        )
        sim_task_id = _asset_task_id("sim_cache", asset)
        sim_task_ids.append(sim_task_id)
        tasks.append(
            WorkflowTask(
                task_id=sim_task_id,
                stage=WorkflowStage.SIM_CACHE,
                label=f"Sim/cache {asset.cfx_type} for {asset.name}",
                depends_on=fix_task_ids or ["shot_setup"],
                status="skipped" if should_skip_sim else "pending",
                metadata={
                    "asset": asset.name,
                    "cfx_type": asset.cfx_type,
                    "input_cache_path": asset.input_cache_path,
                    "output_cache_path": asset.output_cache_path,
                    "cache_exists": cache_exists,
                    "force_resim": shot.batch.force_resim,
                    "frame_start": shot.frame_start,
                    "frame_end": shot.frame_end,
                    "frame_chunk": shot.batch.frame_chunk,
                    "quality": asset.quality,
                    "resim_scope": resim_scope,
                    "resim_frame_range": resim_frame_range,
                },
            )
        )

    validation_deps = [task_id for task_id in sim_task_ids]
    if shot.batch.validate_cache:
        tasks.append(
            WorkflowTask(
                task_id="validate_cache",
                stage=WorkflowStage.VALIDATE,
                label="Validate CFX caches",
                depends_on=validation_deps,
                metadata={
                    "checks": [
                        "cache_exists",
                        "frame_range",
                        "file_sequence_continuity",
                        "basic_motion_delta",
                    ],
                },
            )
        )
        preview_deps = ["validate_cache"]
    else:
        preview_deps = validation_deps

    if shot.batch.generate_preview:
        tasks.append(
            WorkflowTask(
                task_id="generate_preview",
                stage=WorkflowStage.PREVIEW,
                label="Generate flipbook or OpenGL preview",
                depends_on=preview_deps,
                metadata={
                    "review_dir": shot.review_dir,
                    "frame_start": shot.frame_start,
                    "frame_end": shot.frame_end,
                },
            )
        )
        review_deps = ["generate_preview"]
    else:
        review_deps = preview_deps

    tasks.append(
        WorkflowTask(
            task_id="review_result",
            stage=WorkflowStage.REVIEW,
            label="Collect review status and artist notes",
            depends_on=review_deps,
            metadata={
                "open_issue_count": len(open_issues),
                "review_dir": shot.review_dir,
            },
        )
    )

    publish_status = "pending" if shot.batch.publish_on_approved else "blocked"
    tasks.append(
        WorkflowTask(
            task_id="publish_final_cache",
            stage=WorkflowStage.PUBLISH,
            label="Publish final CFX cache",
            depends_on=["review_result"],
            status=publish_status,
            metadata={
                "publish_on_approved": shot.batch.publish_on_approved,
                "department": shot.department,
            },
        )
    )

    return WorkflowPlan(shot=shot, tasks=tasks)

