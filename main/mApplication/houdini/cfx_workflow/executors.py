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


# When validate runs right after an out-of-process sim, the freshly written
# frames can lag in becoming visible to this process. Retry a few times — but
# only on the "incomplete flush" signature below, never on a genuinely empty
# cache — so a real failure still fails fast.
VALIDATE_FLUSH_RETRIES = 3
VALIDATE_FLUSH_DELAY = 0.5


def _incomplete_flush(report) -> bool:
    """True when caches are partially present (some frames found, set incomplete).

    That is the signature of a sim still flushing files; a genuinely missing
    cache (``cache_exists`` fails) returns False so we don't sleep on real
    failures.
    """

    for asset in report.as_dict()["assets"]:
        checks = {c["name"]: c["status"] for c in asset["checks"]}
        if checks.get("cache_exists") == "pass" and (
            checks.get("frame_range_coverage") == "fail"
            or checks.get("frame_sequence_continuity") == "fail"
        ):
            return True
    return False


def run_validate(shot: ShotConfig, task: WorkflowTask) -> ExecutionResult:
    import time

    from .validator import validate_shot_caches

    report = validate_shot_caches(shot)
    retries = 0
    while (
        report.status == "fail"
        and _incomplete_flush(report)
        and retries < VALIDATE_FLUSH_RETRIES
    ):
        time.sleep(VALIDATE_FLUSH_DELAY)
        report = validate_shot_caches(shot)
        retries += 1

    payload = report.as_dict()
    if report.status == "fail":
        return _result(
            task,
            "failed",
            "Cache validation failed",
            {"report": payload, "flush_retries": retries},
        )
    warnings = (
        ["Validation passed with warnings; inspect the report details"]
        if report.status == "warning"
        else []
    )
    details = {"report": payload}
    if retries:
        warnings = warnings + [f"Cache validated after {retries} flush retr(ies)"]
        details["flush_retries"] = retries
    return _result(task, "done", "Cache validation passed", details, warnings)


def _node_errors(node) -> list[str]:
    """Return a node's cook errors as plain strings (empty if none/unavailable)."""

    try:
        return [str(err) for err in node.errors()]
    except Exception:
        return []


def _shot_output_bbox(hou, shot: ShotConfig):
    """Combined bounding box of the shot's OUT_CFX_CACHE outputs, or None."""

    bbox = None
    for asset in shot.assets:
        node = hou.node(f"{_container_path(shot, asset)}/OUT_CFX_CACHE")
        if node is None:
            continue
        geo = node.geometry()
        if geo is None:
            continue
        b = geo.boundingBox()
        if bbox is None:
            bbox = b
        else:
            bbox.enlargeToContain(b)
    return bbox


def _frame_preview_camera(hou, cam, shot: ShotConfig) -> None:
    """Place the camera so it frames the shot geometry; sane default otherwise."""

    placement = {"tx": 0.0, "ty": 1.0, "tz": 10.0, "rx": -5.0}
    try:
        bbox = _shot_output_bbox(hou, shot)
        if bbox is not None:
            center = bbox.center()
            dist = max(bbox.sizevec()) * 2.5 + 5.0
            placement = {"tx": center[0], "ty": center[1], "tz": center[2] + dist, "rx": 0.0}
    except Exception:
        pass  # fall back to the default placement
    for name, value in placement.items():
        parm = cam.parm(name)
        if parm is not None:
            parm.set(value)


def _ensure_preview_camera(hou, shot: ShotConfig, warnings: list[str]):
    """Find or create a camera for the preview render (OpenGL needs one)."""

    obj = hou.node("/obj")
    if obj is None:
        warnings.append("Could not find /obj; cannot create a preview camera")
        return None
    cam_name = f"cfx_preview_cam_{shot.sequence}_{shot.shot}".replace(" ", "_")
    cam = obj.node(cam_name)
    if cam is not None:
        return cam
    try:
        cam = obj.createNode("cam", cam_name)
    except hou.OperationFailed as exc:
        warnings.append(f"Could not create a preview camera ({exc}); set one on the ROP manually")
        return None
    _frame_preview_camera(hou, cam, shot)
    return cam


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

    # An OpenGL ROP needs a camera; a headless/batch cook has no viewport to
    # fall back on (it errors "No camera specified for render"), so make sure
    # one exists and point the ROP at it.
    camera = _ensure_preview_camera(hou, shot, warnings)
    if camera is not None:
        cam_parm = rop.parm("camera")
        if cam_parm is None:
            warnings.append(f"Parameter 'camera' not found on {rop.path()}")
        else:
            cam_parm.set(camera.path())

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

    # Don't report success blindly: a render can fail (e.g. no camera, no
    # output path) without raising, so check the ROP's cook errors.
    render_errors = _node_errors(rop)
    if render_errors:
        return _result(
            task,
            "failed",
            f"Preview render failed: {render_errors[0]}",
            {"rop": rop.path(), "picture": picture, "errors": render_errors},
            warnings,
        )
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
