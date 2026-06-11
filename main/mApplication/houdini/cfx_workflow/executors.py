# -*- coding: utf-8 -*-
"""Per-stage executors for CFX workflow tasks.

``workflow.py`` decides *what* needs to happen; this module is the layer
that actually *does* it. Each executor takes the shot config and one task
and returns a structured ``ExecutionResult`` — never raising into the
caller, so a TOP graph or batch loop can keep cooking and report failures.

Statuses:

- ``done``    — the executor performed the work.
- ``failed``  — the work was attempted and did not succeed.
- ``manual``  — this step needs an artist or studio-specific tooling.
- ``skipped`` — nothing to do (cache up to date, publish blocked, ...).

Stages that touch a Houdini scene import ``hou`` inside the function;
``validate`` is pure Python and runs anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .schema import AssetConfig, ShotConfig, WorkflowStage, WorkflowTask


@dataclass
class ExecutionResult:
    task_id: str
    stage: str
    status: str  # "done" | "failed" | "manual" | "skipped"
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "stage": self.stage,
            "status": self.status,
            "message": self.message,
            "details": dict(self.details),
            "warnings": list(self.warnings),
        }


def _require_hou():
    try:
        import hou  # type: ignore
    except ImportError as exc:
        raise RuntimeError("This executor must run inside Houdini") from exc
    return hou


def _result(
    task: WorkflowTask,
    status: str,
    message: str = "",
    details: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> ExecutionResult:
    return ExecutionResult(
        task_id=task.task_id,
        stage=task.stage.value,
        status=status,
        message=message,
        details=details or {},
        warnings=warnings or [],
    )


def _find_asset(shot: ShotConfig, name: str | None) -> AssetConfig | None:
    for asset in shot.assets:
        if asset.name == name:
            return asset
    return None


def _container_path(shot: ShotConfig, asset: AssetConfig) -> str:
    container = f"{asset.cfx_type}_{asset.name}".replace(" ", "_")
    return f"/obj/cfx_{shot.sequence}_{shot.shot}/{container}"


def run_hda_check(shot: ShotConfig, task: WorkflowTask) -> ExecutionResult:
    hou = _require_hou()
    hda = str(task.metadata.get("hda", ""))
    installed = hou.nodeType(hou.sopNodeTypeCategory(), hda) is not None
    if installed:
        return _result(task, "done", f"HDA installed: {hda}", {"hda": hda, "installed": True})
    return _result(
        task,
        "failed",
        f"HDA not installed: {hda}",
        {"hda": hda, "installed": False},
        [f"Install or publish '{hda}' before shot setup"],
    )


def run_hda_publish(shot: ShotConfig, task: WorkflowTask) -> ExecutionResult:
    return _result(
        task,
        "manual",
        "HDA publish is studio-specific; publish the updated definition/preset manually",
        {"asset": task.metadata.get("asset"), "issue_type": task.metadata.get("issue_type")},
    )


def run_shot_setup(shot: ShotConfig, task: WorkflowTask) -> ExecutionResult:
    from .shot_builder import build_houdini_scene

    build = build_houdini_scene(shot)
    return _result(
        task,
        "done",
        f"Built CFX network: {build['container']}",
        {"build": build},
        list(build.get("warnings", [])),
    )


def run_fix(shot: ShotConfig, task: WorkflowTask) -> ExecutionResult:
    action = dict(task.metadata.get("fix_action", {}))
    patch = list(action.get("parameter_patch") or [])
    asset = _find_asset(shot, action.get("target_asset"))
    if not patch or asset is None:
        return _result(
            task,
            "manual",
            task.label or "Manual fix required",
            {"fix_action": action},
        )

    hou = _require_hou()
    sim_path = f"{_container_path(shot, asset)}/sim_{asset.cfx_type}"
    node = hou.node(sim_path)
    if node is None:
        return _result(
            task, "failed", "Sim node not found; run shot_setup first", {"node": sim_path}
        )

    applied: list[dict[str, Any]] = []
    warnings: list[str] = []
    for entry in patch:
        parm_name = str(entry.get("parm", ""))
        parm = node.parm(parm_name)
        if parm is None:
            warnings.append(f"Parameter '{parm_name}' not found on {node.path()}")
            continue
        op = entry.get("op", "set")
        value = entry.get("value")
        old = parm.eval()
        if op == "scale":
            new = old * value
        elif op == "add":
            new = old + value
        else:
            new = value
        parm.set(new)
        applied.append({"parm": parm_name, "op": op, "old": old, "new": new})

    status = "done" if applied else "manual"
    return _result(
        task,
        status,
        f"Applied {len(applied)} parameter patch(es) on {sim_path}",
        {"applied": applied, "fix_action": action},
        warnings,
    )


def run_sim_cache(shot: ShotConfig, task: WorkflowTask) -> ExecutionResult:
    scope = str(task.metadata.get("resim_scope", "full"))
    if task.status == "skipped" or scope == "none":
        return _result(
            task, "skipped", "Cache is up to date; no resim needed", {"resim_scope": scope}
        )

    hou = _require_hou()
    asset = _find_asset(shot, task.metadata.get("asset"))
    if asset is None:
        return _result(task, "failed", f"Unknown asset: {task.metadata.get('asset')}")
    cache_path = f"{_container_path(shot, asset)}/write_cfx_cache"
    node = hou.node(cache_path)
    if node is None:
        return _result(
            task, "failed", "Cache node not found; run shot_setup first", {"node": cache_path}
        )

    frame_range = list(
        task.metadata.get("resim_frame_range") or (shot.frame_start, shot.frame_end)
    )
    warnings: list[str] = []
    for parm_name, value in zip(("f1", "f2"), frame_range):
        parm = node.parm(parm_name)
        if parm is None:
            warnings.append(f"Parameter '{parm_name}' not found on {node.path()}")
            continue
        parm.deleteAllKeyframes()
        parm.set(value)

    execute = node.parm("execute")
    if execute is None:
        return _result(
            task,
            "manual",
            f"No execute button on {node.path()}; cook it manually",
            {"rop": cache_path, "frame_range": frame_range, "resim_scope": scope},
            warnings,
        )
    execute.pressButton()
    return _result(
        task,
        "done",
        f"Cooked {cache_path} over frames {frame_range[0]}-{frame_range[1]}",
        {"rop": cache_path, "frame_range": frame_range, "resim_scope": scope},
        warnings,
    )


def run_validate(shot: ShotConfig, task: WorkflowTask) -> ExecutionResult:
    from .validator import validate_shot_caches

    report = validate_shot_caches(shot)
    payload = report.as_dict()
    if report.status == "fail":
        return _result(task, "failed", "Cache validation failed", {"report": payload})
    warnings = (
        ["Validation passed with warnings; inspect the report details"]
        if report.status == "warning"
        else []
    )
    return _result(task, "done", "Cache validation passed", {"report": payload}, warnings)


def run_preview(shot: ShotConfig, task: WorkflowTask) -> ExecutionResult:
    hou = _require_hou()
    out = hou.node("/out")
    if out is None:
        return _result(
            task, "manual", "Could not find /out; create a preview ROP manually"
        )

    rop_name = f"cfx_preview_{shot.sequence}_{shot.shot}"
    rop = out.node(rop_name)
    if rop is None:
        try:
            rop = out.createNode("opengl", rop_name)
        except hou.OperationFailed as exc:
            return _result(
                task,
                "manual",
                f"Could not create an OpenGL ROP ({exc}); generate the preview manually",
            )

    warnings: list[str] = []
    picture = None
    if shot.review_dir:
        picture = f"{shot.review_dir}/{shot.shot_id}.$F4.jpg"
        parm = rop.parm("picture")
        if parm is None:
            warnings.append(f"Parameter 'picture' not found on {rop.path()}")
        else:
            parm.set(picture)
    else:
        warnings.append("No review_dir configured; ROP keeps its default output path")

    trange = rop.parm("trange")
    if trange is not None:
        trange.set(1)
    frame_parms = rop.parmTuple("f")
    if frame_parms is not None:
        for parm, value in zip(frame_parms, (shot.frame_start, shot.frame_end)):
            parm.deleteAllKeyframes()
            parm.set(value)

    execute = rop.parm("execute")
    if execute is None:
        return _result(
            task,
            "manual",
            f"No execute button on {rop.path()}; render the preview manually",
            {"rop": rop.path(), "picture": picture},
            warnings,
        )
    execute.pressButton()
    return _result(
        task,
        "done",
        f"Rendered preview via {rop.path()}",
        {"rop": rop.path(), "picture": picture},
        warnings,
    )


def run_review(shot: ShotConfig, task: WorkflowTask) -> ExecutionResult:
    open_issues = [issue.as_dict() for issue in shot.review_issues if issue.is_open]
    return _result(
        task,
        "manual",
        "Collect review feedback and update review_issues in the shot config",
        {
            "open_issue_count": len(open_issues),
            "open_issues": open_issues,
            "review_dir": shot.review_dir,
        },
    )


def run_publish(shot: ShotConfig, task: WorkflowTask) -> ExecutionResult:
    if task.status == "blocked":
        return _result(
            task, "skipped", "Publish blocked: batch.publish_on_approved is false"
        )
    caches = {asset.name: asset.output_cache_path for asset in shot.assets}
    return _result(
        task,
        "manual",
        "Publish is studio-specific; copy the caches below to the publish area",
        {"caches": caches},
    )


EXECUTORS: dict[WorkflowStage, Callable[[ShotConfig, WorkflowTask], ExecutionResult]] = {
    WorkflowStage.HDA_CHECK: run_hda_check,
    WorkflowStage.HDA_PUBLISH: run_hda_publish,
    WorkflowStage.SHOT_SETUP: run_shot_setup,
    WorkflowStage.FIX: run_fix,
    WorkflowStage.SIM_CACHE: run_sim_cache,
    WorkflowStage.VALIDATE: run_validate,
    WorkflowStage.PREVIEW: run_preview,
    WorkflowStage.REVIEW: run_review,
    WorkflowStage.PUBLISH: run_publish,
}


def execute_task(shot: ShotConfig, task: WorkflowTask) -> ExecutionResult:
    """Run the executor for one task; failures become results, not raises."""

    executor = EXECUTORS.get(task.stage)
    if executor is None:
        return _result(task, "manual", f"No executor for stage: {task.stage.value}")
    try:
        return executor(shot, task)
    except Exception as exc:
        return _result(task, "failed", f"Executor raised: {exc}")


def execute_payload(task_data: dict[str, Any], shot_data: dict[str, Any]) -> dict[str, Any]:
    """JSON-friendly entry point used by the TOP pythonscript stubs."""

    shot = ShotConfig.from_dict(shot_data)
    task = WorkflowTask.from_dict(task_data)
    return execute_task(shot, task).as_dict()
