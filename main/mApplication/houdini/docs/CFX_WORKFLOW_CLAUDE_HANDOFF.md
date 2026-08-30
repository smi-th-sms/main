# Claude Handoff: Houdini CFX Dynamic Workflow

This document is a continuation brief for Claude or another coding assistant.
It summarizes the current Houdini CFX workflow scaffold and the recommended next steps.

## Project Goal

Build a dynamic Houdini CFX workflow that covers the full artist process:

```text
Digital Asset creation / update
  -> shot scene setup
  -> batch sim/cache/preview
  -> result validation
  -> review issue collection
  -> fix routing
  -> selective resim / republish
```

The workflow should eventually support cloth, hair, secondary motion, and other CFX tasks through reusable HDAs, shot configs, and automated batch/review loops.

## Current Workspace

Workspace root:

```text
E:/script/pythonWorkSpace
```

Main package path:

```text
E:/script/pythonWorkSpace/main/mApplication/houdini/cfx_workflow
```

Main docs path:

```text
E:/script/pythonWorkSpace/main/mApplication/houdini/docs
```

## Current Implementation Status

A first scaffold exists under `main/mApplication/houdini/cfx_workflow`.

Implemented files:

```text
cfx_workflow/
  __init__.py
  schema.py
  config_loader.py
  path_rules.py
  review.py
  workflow.py
  shot_builder.py
  top_builder.py
  executors.py
  validator.py
  batch_runner.py
  cli.py
  examples/
    shot_config.json
    shot_config_path_rules.json
  tests/
    fake_hou.py
    test_config_loader.py
    test_path_rules.py
    test_review.py
    test_workflow.py
    test_validator.py
    test_shot_builder.py
    test_top_builder.py
    test_executors.py
```

Additional overview doc:

```text
houdini/docs/CFX_WORKFLOW_OVERVIEW.md
```

This scaffold is currently a planning and dry-run layer. It does not yet submit real Houdini batch jobs or build production-ready HDA networks.

## What Each File Does

`schema.py`

- Defines the shared data model.
- Includes `AssetConfig`, `BatchConfig`, `ReviewIssue`, `ShotConfig`, `WorkflowTask`, and `WorkflowPlan`.
- Uses dataclasses and standard Python only.

`config_loader.py`

- Loads `shot_config.json`.
- Validates required shot and asset keys.
- Applies `path_rules` to fill missing path fields after validation.
- Raises `ConfigError` for malformed config or an invalid `path_rules` block.

`path_rules.py`

- Centralizes studio path and version conventions.
- `PathRules` resolves named `str.format` templates (`work_dir`, `work_scene`,
  `input_cache`, `cache_file`, `review_dir`, `publish_dir`, `scene_template`)
  from a `root` plus show/sequence/shot/department/version context.
- Templates can be overridden per config via `path_rules.templates`.
- Version helpers: `format_version` (`1 -> "v001"`), `parse_version`,
  `existing_versions(dir)` / `next_version(dir)` (scans `v###` dirs and
  versioned filenames on disk).
- `apply_path_rules(data)` fills missing config paths (`work_dir`,
  `scene_template`, `shot_scene_path`, `review_dir`, per-asset
  `input_cache_path` / `output_cache_path`) from the config's `path_rules`
  block. Explicit paths always win; no `path_rules` block means no change.
- Version comes from `metadata.version` (defaults to `v001`).
- See `examples/shot_config_path_rules.json` — same shot as the original
  example but with all paths generated.

`review.py`

- Maps review issue types to actionable fix actions.
- Issue types: `penetration`, `unstable_sim`, `wrong_input_cache`,
  `hda_change`, `preview_only` (unknown types fall back to `manual_review`).
- `route_issue(issue, shot)` returns a `FixAction` carrying:
  - `target_asset` — which asset to touch
  - `frame_range` — issue frames padded by 10 on each side, clamped to the shot range
  - `resim_scope` — `none` / `partial` / `full` (only partial-capable issue
    types like `penetration` produce `partial`; `unstable_sim` always forces full)
  - `parameter_patch` — suggested parm edits as
    `{"parm", "op": "scale"|"add"|"set", "value"}` entries
- `FixAction.as_dict()` produces the JSON-friendly form stored in task metadata.

`workflow.py`

- Builds a dynamic task plan from `ShotConfig`.
- Fix tasks store the full routed action under `metadata.fix_action`.
- Sim tasks carry `metadata.resim_scope` / `resim_frame_range`: a full-scope
  fix on the asset wins over partials, multiple partial ranges merge into one
  span, and an asset with no fixes gets `full` (no cache / forced) or `none`
  (cache exists, nothing to do).
- Current stages:
  - `hda_check`
  - `hda_publish`
  - `shot_setup`
  - `fix`
  - `sim_cache`
  - `validate`
  - `preview`
  - `review`
  - `publish`

`shot_builder.py`

- Contains `build_houdini_scene(shot)`.
- Must run inside Houdini because it imports `hou`.
- Loads the configured `scene_template` when the session is fresh, merges it otherwise, and warns when the template path is missing.
- Creates a `/obj/cfx_{sequence}_{shot}` subnet and, per asset, the chain:
  `load_input_cache -> IN_ANIM_CACHE -> sim_<cfx_type> -> write_cfx_cache -> OUT_CFX_CACHE`.
- Input loader picks `alembic` for `.abc` paths and `file` otherwise.
- The sim node uses the configured HDA type when `hou.nodeType` finds it; otherwise a null placeholder is created with a warning instead of failing.
- Applies `AssetConfig.parameters` to the sim node (missing parms become warnings).
- Configures `filecache` with explicit file method, output path, and the shot frame range.
- Idempotent: existing nodes are reused, never destroyed; a type mismatch on an existing sim node only warns.
- Returns a structured dict: `shot_id`, `scene_template` action, `container`, per-asset node paths plus `hda_found`/`applied_parameters`, and `warnings`.

`top_builder.py`

- Contains `build_top_network(plan)`.
- Must run inside Houdini because it imports `hou`.
- Creates `/obj/cfx_top_{sequence}_{shot}` (a `topnet`) with one TOP node per
  `WorkflowTask`, named after `task_id`, wired according to `depends_on`.
- `sim_cache`/`preview` tasks become `ropfetch` nodes; `sim_cache` ropfetch
  points at the shot builder's `write_cfx_cache` ROP and cooks the shot frame
  range (`framegeneration=1`, `range1`).
- All other stages become `pythonscript` nodes embedding the task and shot
  config payloads as JSON and calling `executors.execute_payload`; a `failed`
  result raises so the TOP work item errors visibly. When the package is not
  importable inside Houdini (workspace root missing from `sys.path`), the
  script degrades to printing the task info.
- Tasks with status `skipped` or `blocked` are created **bypassed** so the
  graph stays complete without cooking them.
- Idempotent (existing nodes are reused) and safe: unknown node types fall
  back to `null` with a warning; unresolved ROP targets and missing parms
  become warnings instead of failures.
- Returns `{shot_id, topnet, nodes: {task_id: {path, type, status, bypassed}}, warnings}`.

`executors.py`

- Per-stage executor functions keyed by `WorkflowStage` (`EXECUTORS` dict).
- `execute_task(shot, task)` dispatches and never raises — exceptions become
  a `failed` result. Statuses: `done` / `failed` / `manual` / `skipped`.
- Implemented behavior per stage:
  - `hda_check` — verifies the HDA type is installed (`failed` when missing)
  - `shot_setup` — delegates to `shot_builder.build_houdini_scene`
  - `fix` — applies `fix_action.parameter_patch` (`scale`/`add`/`set` ops,
    old/new values recorded) to the asset's sim node; `manual` when there is
    no patch, `failed` when the scene was not built yet
  - `sim_cache` — sets the cache ROP frame range (partial resim range when
    given) and presses its execute button; `skipped` when scope is `none`
  - `validate` — runs `validator.validate_shot_caches` (pure Python)
  - `preview` — creates/cooks an `opengl` ROP in `/out` writing to `review_dir`
  - `hda_publish` / `review` / `publish` — `manual` (studio-specific), with
    publish `skipped` while the task is `blocked`
- `execute_payload(task_dict, shot_dict)` is the JSON entry point used by the
  TOP pythonscript stubs; it rebuilds the dataclasses via
  `WorkflowTask.from_dict` / `ShotConfig.from_dict`.

`validator.py`

- Pure-Python cache validation, no `hou` dependency.
- `validate_shot_caches(shot)` returns a `ValidationReport` with per-asset checks:
  - `cache_exists` — files matching the frame pattern (supports `$F4`, `####`, `%04d`; static paths like `.abc` are checked as single files)
  - `frame_range_coverage` — found frame bounds cover the shot range
  - `frame_sequence_continuity` — no missing frames inside the shot range
  - `file_size_sanity` — empty files fail, files under 10% of the median size warn
- Statuses aggregate as `fail > warning > pass > skipped` per asset and per report.

`batch_runner.py`

- Provides a dry-run report layer.
- Converts pending workflow tasks to planned dry-run report tasks.

`cli.py`

- Provides three commands:
  - `plan`
  - `dry-run`
  - `validate` (exits 1 when the report status is `fail`)

`examples/shot_config.json`

- Example shot config for `projectA_seq010_shot020`.
- Contains cloth and hair assets plus one open penetration issue.

## Validation Already Run

Primary check — the unit test suite (no Houdini required; builders run
against the fake `hou` harness in `tests/fake_hou.py`):

```powershell
python -B -m unittest discover -s main\mApplication\houdini\cfx_workflow\tests
```

Expected output:

```text
Ran 101 tests in ...s

OK
```

The `tests` directory is intentionally not a package (no `__init__.py`);
`unittest discover` adds it to `sys.path` so tests import `fake_hou`
directly, and the workspace root on `sys.path` provides the
`main.mApplication...` imports. Run from the workspace root.

Syntax check with bytecode generation disabled:

```powershell
python -B -c "import pathlib; paths=list(pathlib.Path(r'main/mApplication/houdini/cfx_workflow').glob('*.py')); [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in paths]; print('syntax ok', len(paths))"
```

Expected output:

```text
syntax ok 12
```

Workflow plan smoke test:

```powershell
python -B -c "from main.mApplication.houdini.cfx_workflow.config_loader import load_shot_config; from main.mApplication.houdini.cfx_workflow.workflow import build_workflow_plan; shot=load_shot_config(r'main\mApplication\houdini\cfx_workflow\examples\shot_config.json'); plan=build_workflow_plan(shot); print(shot.shot_id, len(plan.tasks)); print(','.join(task.stage.value for task in plan.tasks))"
```

Expected output:

```text
projectA_seq010_shot020 10
hda_check,hda_check,shot_setup,fix,sim_cache,sim_cache,validate,preview,review,publish
```

## CLI Usage

From workspace root:

```powershell
python -B -m main.mApplication.houdini.cfx_workflow.cli plan --config main\mApplication\houdini\cfx_workflow\examples\shot_config.json
```

Dry-run report:

```powershell
python -B -m main.mApplication.houdini.cfx_workflow.cli dry-run --config main\mApplication\houdini\cfx_workflow\examples\shot_config.json --output main\mApplication\houdini\cfx_workflow\examples\dry_run_report.json
```

Cache validation report:

```powershell
python -B -m main.mApplication.houdini.cfx_workflow.cli validate --config main\mApplication\houdini\cfx_workflow\examples\shot_config.json
```

Note: the example config points at non-existent cache paths, so `validate` is
expected to print a `fail` report and exit with code 1.

If creating report files during testing, clean generated reports before finalizing unless they are intentionally committed as fixtures.

## Dynamic Behavior Currently Supported

- If `batch.force_resim` is true, sim tasks remain pending even when cache exists.
- If output cache exists, `force_resim` is false, and there are no open review issues, sim task status becomes `skipped`.
- Open review issues add fix tasks after `shot_setup`.
- `hda_change` issues add an HDA publish task.
- If `batch.validate_cache` is false, validation is skipped.
- If `batch.generate_preview` is false, preview is skipped.
- If `batch.publish_on_approved` is false, publish task remains `blocked`.

## Important Design Direction

Keep the workflow declarative.

The task graph should remain usable by multiple executors:

```text
WorkflowPlan
  -> dry-run report
  -> Houdini Python runner
  -> TOPs/PDG graph builder
  -> farm submitter
  -> review/publish automation
```

Avoid putting real farm/Houdini side effects directly into `workflow.py`.
`workflow.py` should decide what needs to happen, not execute it.

## Recommended Next Task

Completed so far:

- `shot_builder.py` expansion (scene template handling, per-asset input/HDA/cache
  chain, parameter application, missing-HDA placeholders, structured result).
- `validator.py` (cache existence, frame coverage, frame continuity, file size
  sanity) plus the CLI `validate` command.
- `path_rules.py` (centralized path/version templates, version scanning,
  `apply_path_rules` config fill-in wired into `config_loader`).
- `top_builder.py` (WorkflowPlan -> TOPs/PDG network with dependency wiring,
  ropfetch targets, pythonscript stubs, bypassed skipped/blocked tasks).
- `review.py` expansion (issue-aware `FixAction` with target asset, padded
  frame range, parameter patch, none/partial/full resim scope) wired into fix
  and sim task metadata in `workflow.py`.
- `tests/` suite (101 unittest cases: config loading + path_rules, workflow
  plan branches, review routing, validator against temp cache files, and
  fake-`hou` tests for `shot_builder` / `top_builder` / `executors`). Run it
  after every change; add cases alongside new features.
- `executors.py` (per-stage execution: hda_check, shot_setup, fix patch
  application, sim cook with partial ranges, validate, preview ROP) wired
  into the TOP pythonscript stubs via `execute_payload`.

The remaining work connects the package to a real studio pipeline — pick by
what the team needs first:

## Follow-Up Tasks

1. Expand validation rules.

   Add geometry-level checks to `validator.py`: point/prim counts per frame,
   collision markers, velocity spikes. These need `hou` or a geometry
   library, so keep them behind the same warning-not-failure pattern.

3. Connect review reporting.

   Bridge `review_issues` to the studio's actual review system
   (ShotGrid/Ftrack/CSV/JSON import-export) so issues flow in and fix
   status flows back without hand-editing the shot config.

4. Add a farm submitter.

   A `batch_runner` mode that submits the TOP network (or per-task hython
   jobs) to the render farm instead of dry-running.

## Suggested Code Style

- Use standard Python libraries where possible.
- Keep Houdini `hou` imports inside functions that must run inside Houdini.
- Keep config parsing separate from workflow planning.
- Keep workflow planning separate from execution.
- Return structured dictionaries for generated scene/build results.
- Preserve user changes outside the CFX workflow package.

## Known Workspace Notes

- The repository may report dubious ownership with normal `git status`.
- Use this form if needed:

```powershell
git -c safe.directory=E:/script/pythonWorkSpace status --short
```

- Some existing Houdini docs may display mojibake in PowerShell because of console encoding. Prefer a UTF-8 aware editor when reviewing Markdown files.
- Existing untracked files outside the CFX workflow scope may already be present. Do not remove or revert unrelated files.

## Suggested Prompt For Claude

```text
Continue the Houdini CFX dynamic workflow scaffold in:
E:/script/pythonWorkSpace/main/mApplication/houdini/cfx_workflow

Read:
E:/script/pythonWorkSpace/main/mApplication/houdini/docs/CFX_WORKFLOW_CLAUDE_HANDOFF.md
E:/script/pythonWorkSpace/main/mApplication/houdini/docs/CFX_WORKFLOW_OVERVIEW.md

Current goal:
Pick the next pipeline-connection task from "Follow-Up Tasks" in the handoff
doc (validation rule expansion, review system bridge, or farm submitter) —
ask the user which one if not specified. The core scaffold and per-stage
executors are complete and covered by the test suite.

Please keep workflow.py declarative and avoid putting Houdini side effects there.
Run the test suite after editing:
python -B -m unittest discover -s main\mApplication\houdini\cfx_workflow\tests
```

