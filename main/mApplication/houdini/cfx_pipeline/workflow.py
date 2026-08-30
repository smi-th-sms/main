# -*- coding: utf-8 -*-
"""Top-level workflow orchestrator for the CFX pipeline.

Runs the asset and shot stages **in order** on a Houdini scene, one step at a
time, capturing a structured report so a full run can be driven (and verified)
from a single call. This is the "workflow tool" tying together
:mod:`asset_builder` and :mod:`shot_builder`.

User entry point (config files -> full run, fresh scene)::

    from main.mApplication.houdini.cfx_pipeline import workflow
    workflow.run("Z:/.../cfx_asset.json", "Z:/.../cfx_shot.json",
                 new_scene=True, cache_out=True)

:func:`run` accepts config **file paths or objects**, supports partial /
resumable runs (``from_stage`` / ``to_stage``), an asset-level drape test
(``asset_sim_test``), and the Stage 4 alembic export (``cache_out``). Each step
is ``(name, thunk)``; a step that raises is caught, marked failed and stops the
run (later steps depend on earlier outputs). ``hou`` is only touched inside the
build functions / the ``new_scene`` reset, so importing this module is
headless-safe.
"""

from __future__ import annotations

from typing import Any, Callable

from . import asset_builder as _asset
from . import shot_builder as _shot
from .schema import AssetSetupConfig, ShotSimConfig

Step = tuple[str, Callable[[], Any]]


# ---------------------------------------------------------------------------
# stage lists (single source of truth for order)
# ---------------------------------------------------------------------------
def _asset_stages(asset: AssetSetupConfig, parent: str, write_cache: bool,
                  asset_sim_test: bool) -> list[Step]:
    st: list[Step] = [
        ("asset:setup", lambda: _asset.build_asset_setup(asset, parent)),
        ("asset:corrective", lambda: _asset.build_corrective(asset, parent)),
        ("asset:collision", lambda: _asset.build_collision(asset, parent)),
        ("asset:proxy", lambda: _asset.build_proxy(asset, parent)),
        ("asset:hair_proxy", lambda: _asset.build_hair_proxy(asset, parent)),
        ("asset:constraint", lambda: _asset.build_constraint(asset, parent)),
        ("asset:rest_cache",
         lambda: _asset.build_rest_cache(asset, parent, execute=write_cache)),
    ]
    if asset_sim_test:
        # build the drape-test network (user scrubs the timeline to validate);
        # not force-cooked here to keep the run light.
        st.append(("asset:sim_test",
                   lambda: _asset.build_asset_sim_test(asset, parent, execute=False)))
    return st


def _shot_stages(shot: ShotSimConfig, asset: AssetSetupConfig, parent: str,
                 execute: bool, cache_out: bool) -> list[Step]:
    st: list[Step] = [
        ("shot:setup", lambda: _shot.build_shot_setup(shot, parent)),
        ("shot:timeline", lambda: _shot.set_shot_timeline(shot, apply=True, parent=parent)),
        ("shot:load_caches", lambda: _shot.load_asset_caches(shot, parent)),
        ("shot:anim", lambda: _shot.build_shot_anim(shot, parent)),
        ("shot:deform", lambda: _shot.build_shot_deform(shot, parent)),
        ("shot:collision", lambda: _shot.build_shot_collision(shot, parent)),
        ("shot:constraint", lambda: _shot.build_shot_constraint(shot, asset, parent)),
        ("shot:solve", lambda: _shot.build_shot_solve(shot, parent)),
        ("shot:sim_cache", lambda: _shot.build_shot_cache(shot, parent, execute=execute)),
    ]
    if cache_out:
        st.append(("shot:cache_out",
                   lambda: _shot.build_shot_cacheout(shot, asset, parent, execute=execute)))
    return st


# ---------------------------------------------------------------------------
# step runner
# ---------------------------------------------------------------------------
def _run_step(report: list[dict[str, Any]], name: str,
              thunk: Callable[[], Any]) -> dict[str, Any]:
    entry: dict[str, Any] = {"step": name, "ok": True}
    try:
        result = thunk()
        entry["result"] = result
        if isinstance(result, dict) and result.get("warnings"):
            entry["warnings"] = result["warnings"]
    except Exception as exc:  # keep the report going; the caller stops the run
        entry["ok"] = False
        entry["error"] = f"{type(exc).__name__}: {exc}"
    report.append(entry)
    mark = " OK " if entry["ok"] else "FAIL"
    warn = "  (%d warning(s))" % len(entry["warnings"]) if entry.get("warnings") else ""
    tail = "" if entry["ok"] else "  -> " + entry["error"]
    print(f"  [{mark}] {name}{warn}{tail}")
    return entry


def _run(stages: list[Step], from_stage: str | None,
         to_stage: str | None) -> list[dict[str, Any]]:
    names = [n for n, _ in stages]
    i0 = names.index(from_stage) if from_stage else 0
    i1 = names.index(to_stage) + 1 if to_stage else len(stages)
    report: list[dict[str, Any]] = []
    for name, thunk in stages[i0:i1]:
        if not _run_step(report, name, thunk)["ok"]:
            break
    return report


# ---------------------------------------------------------------------------
# config coercion (accept file paths or config objects)
# ---------------------------------------------------------------------------
def _as_asset(asset: Any) -> AssetSetupConfig:
    if isinstance(asset, AssetSetupConfig):
        return asset
    from .config_loader import load_asset_config
    return load_asset_config(asset)


def _as_shot(shot: Any, asset: AssetSetupConfig) -> ShotSimConfig | None:
    if shot is None or isinstance(shot, ShotSimConfig):
        return shot
    from .config_loader import load_shot_config
    return load_shot_config(shot, asset=asset)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------
def run(asset: Any, shot: Any = None, *, parent: str = "/obj",
        new_scene: bool = False, from_stage: str | None = None,
        to_stage: str | None = None, write_cache: bool = True,
        execute: bool = True, cache_out: bool = False,
        asset_sim_test: bool = False) -> dict[str, Any]:
    """Run the pipeline; the one entry point a user calls directly.

    ``asset`` / ``shot`` may be config **file paths or objects** (shot omitted =
    asset stage only). ``from_stage`` / ``to_stage`` (stage names like
    ``"shot:setup"``) slice the run for resume / partial execution — e.g.
    ``from_stage="shot:setup"`` reuses existing asset caches and only (re)builds
    the shot. ``asset_sim_test`` inserts the drape test after the asset stage;
    ``cache_out`` appends the Stage 4 UE alembic export. Returns
    ``{"stages": [...all names...], "ran": [...step reports...]}``.
    """

    asset = _as_asset(asset)
    shot = _as_shot(shot, asset)
    if new_scene:
        import hou  # lazy — headless-safe import of this module
        hou.hipFile.clear(suppress_save_prompt=True)

    stages = _asset_stages(asset, parent, write_cache, asset_sim_test)
    if shot is not None:
        stages += _shot_stages(shot, asset, parent, execute, cache_out)

    label = asset.asset + ("" if shot is None else f" -> {shot.shot_id}")
    span = ""
    if from_stage or to_stage:
        span = f"  [{from_stage or 'start'} .. {to_stage or 'end'}]"
    print(f"=== CFX pipeline: {label}{span} ===")
    ran = _run(stages, from_stage, to_stage)
    return {"stages": [n for n, _ in stages], "ran": ran}


# --- back-compat stage helpers (used by earlier callers / tests) -----------
def run_asset(asset: AssetSetupConfig, parent: str = "/obj",
              write_cache: bool = True,
              asset_sim_test: bool = False) -> list[dict[str, Any]]:
    """Run the asset stage (2.1–2.6) in order; ``write_cache`` cooks the rest
    caches to disk (the Asset→Shot handoff)."""

    return _run(_asset_stages(asset, parent, write_cache, asset_sim_test), None, None)


def run_shot(shot: ShotSimConfig, asset: AssetSetupConfig, parent: str = "/obj",
             execute: bool = True, cache_out: bool = False) -> list[dict[str, Any]]:
    """Run the shot stage (3.1–3.6, optionally Stage 4) in order."""

    return _run(_shot_stages(shot, asset, parent, execute, cache_out), None, None)


def run_pipeline(asset: AssetSetupConfig, shot: ShotSimConfig, parent: str = "/obj",
                 new_scene: bool = False, write_cache: bool = True,
                 execute: bool = True, cache_out: bool = False) -> dict[str, Any]:
    """Run asset stage then shot stage; skips the shot stage if the asset
    stage failed. Returns ``{"asset": [...], "shot": [...] | None, "stopped"?}``."""

    if new_scene:
        import hou
        hou.hipFile.clear(suppress_save_prompt=True)
    print("=== CFX pipeline: ASSET stage (%s) ===" % asset.asset)
    asset_report = run_asset(asset, parent, write_cache=write_cache)
    if any(not e["ok"] for e in asset_report):
        return {"asset": asset_report, "shot": None, "stopped": "asset stage failed"}
    print("=== CFX pipeline: SHOT stage (%s) ===" % shot.shot_id)
    shot_report = run_shot(shot, asset, parent, execute=execute, cache_out=cache_out)
    stopped = "shot stage failed" if any(not e["ok"] for e in shot_report) else None
    return {"asset": asset_report, "shot": shot_report, "stopped": stopped}


def summary(report: dict[str, Any]) -> str:
    """One-line-per-step text summary of a :func:`run` or :func:`run_pipeline`
    report (handles both shapes)."""

    lines: list[str] = []
    entries: list[dict[str, Any]]
    if "ran" in report:                      # run() shape
        entries = report["ran"]
    else:                                    # run_pipeline() shape
        entries = (report.get("asset") or []) + (report.get("shot") or [])
    for e in entries:
        mark = "OK" if e.get("ok") else "FAIL"
        lines.append(f"{mark:4} {e['step']}"
                     + (f"  {e.get('error','')}" if not e.get("ok") else ""))
    if report.get("stopped"):
        lines.append(f"STOPPED: {report['stopped']}")
    return "\n".join(lines)
