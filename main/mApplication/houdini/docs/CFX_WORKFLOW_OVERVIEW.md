# Houdini CFX Dynamic Workflow

이 문서는 Houdini CFX 작업에서 HDA 생성, shot scene setup, batch, review, fix 반영까지 이어지는 전체 workflow의 1차 골격입니다.

## 목표

- Shot별 CFX 작업 정보를 `shot_config.json`으로 관리한다.
- Config를 기준으로 필요한 작업만 동적으로 plan한다.
- HDA, scene setup, sim/cache, validation, preview, review, publish 단계를 같은 데이터 구조로 다룬다.
- 초기 버전은 dry-run report까지 만들고, 이후 Houdini hython, TOPs/PDG, farm submitter로 확장한다.

## 기본 흐름

```text
shot_config.json
  -> load_shot_config()
  -> build_workflow_plan()
  -> dry-run report
  -> Houdini scene builder / TOPs / farm runner
```

## 생성된 패키지

```text
houdini/cfx_workflow/
  __init__.py
  schema.py          # Shot, Asset, Batch, Review, Task data model
  config_loader.py   # JSON load + validation + path_rules 적용
  path_rules.py      # Studio path/version 규칙 중앙화
  review.py          # Review issue -> fix action routing
  workflow.py        # Dynamic task plan builder
  shot_builder.py    # Houdini 내부 scene network 생성 helper
  top_builder.py     # WorkflowPlan -> TOPs/PDG network 변환
  executors.py       # Stage별 실제 실행 (TOP stub이 호출)
  validator.py       # Cache validation (존재/coverage/연속성/file size)
  batch_runner.py    # Dry-run report layer
  cli.py             # plan / dry-run / validate command
  examples/
    shot_config.json             # 모든 경로를 명시한 예제
    shot_config_path_rules.json  # path_rules로 경로를 생성하는 예제
  tests/                         # unittest suite (fake hou 포함, Houdini 불필요)
```

## 테스트 실행

Workspace root에서 (Houdini 없이 실행 가능):

```powershell
python -B -m unittest discover -s main\mApplication\houdini\cfx_workflow\tests
```

## CLI 사용 예

Workspace root에서:

```powershell
python -m main.mApplication.houdini.cfx_workflow.cli plan --config main/mApplication/houdini/cfx_workflow/examples/shot_config.json
```

Dry-run report 저장:

```powershell
python -m main.mApplication.houdini.cfx_workflow.cli dry-run --config main/mApplication/houdini/cfx_workflow/examples/shot_config.json --output E:/script/pythonWorkSpace/main/mApplication/houdini/cfx_workflow/examples/dry_run_report.json
```

## Dynamic 분기 기준

- `batch.force_resim=true`이면 cache 존재 여부와 관계없이 sim task를 유지한다.
- `output_cache_path`가 실제로 있고 open review issue가 없으면 sim task는 `skipped`가 된다.
- `review_issues`에 open issue가 있으면 fix task가 shot setup 뒤에 추가된다.
  fix task의 `metadata.fix_action`에는 target asset, 패딩된 frame range,
  parameter patch, resim scope(`none`/`partial`/`full`)가 담긴다.
- sim task의 `metadata.resim_scope`/`resim_frame_range`는 해당 asset의 fix action들로
  결정된다: full이 partial보다 우선하고, partial range들은 하나의 구간으로 병합된다.
- issue type이 `hda_change`이면 HDA publish task가 추가된다.
- `batch.validate_cache=false`이면 validation 단계를 건너뛰고 preview로 간다.
- `batch.generate_preview=false`이면 preview 단계를 건너뛰고 review로 간다.
- `batch.publish_on_approved=false`이면 publish task는 `blocked` 상태로 남긴다.

## Shot Builder 현재 동작

`shot_builder.build_houdini_scene(shot)`은 Houdini 세션 안에서 asset별로 다음 체인을 생성한다.

```text
load_input_cache -> IN_ANIM_CACHE -> sim_<cfx_type> -> write_cfx_cache -> OUT_CFX_CACHE
```

- `scene_template`이 있으면 새 세션에서는 load, 작업 중인 세션에서는 merge한다.
- input은 `.abc`면 `alembic`, 아니면 `file` SOP을 사용한다.
- HDA type이 설치되어 있으면 실제 node를 만들고 `AssetConfig.parameters`를 적용한다.
- HDA가 없으면 placeholder null을 만들고 warning으로 보고한다 (shot setup은 실패하지 않는다).
- `filecache`에 output path와 shot frame range를 설정한다.
- 기존 node는 재사용하며 삭제하지 않는다. 결과는 node path/warning이 담긴 dict로 반환된다.

## Validator 현재 동작

`validator.validate_shot_caches(shot)`은 `hou` 없이 동작하며 asset별로 다음을 검사한다.

- `cache_exists`: frame pattern(`$F4`, `####`, `%04d`)에 맞는 파일 존재 (`.abc` 같은 static path는 단일 파일로 검사)
- `frame_range_coverage`: 발견된 frame 범위가 shot frame range를 커버하는지
- `frame_sequence_continuity`: shot range 안에서 빠진 frame이 없는지
- `file_size_sanity`: 0 byte 파일은 fail, median 대비 10% 미만 파일은 warning

CLI에서 `validate` 명령으로 실행하며, report status가 `fail`이면 exit code 1을 반환한다.

```powershell
python -B -m main.mApplication.houdini.cfx_workflow.cli validate --config main/mApplication/houdini/cfx_workflow/examples/shot_config.json
```

## Path Rules 현재 동작

`path_rules.PathRules`는 `root` + show/sequence/shot/department/version으로
work/cache/review/publish 경로를 템플릿 기반으로 생성한다.

- config에 `path_rules` block(`root`, 선택적으로 `templates`/`version_padding`)이 있으면
  `load_shot_config()`가 누락된 경로 필드를 자동 생성한다. 명시된 경로가 항상 우선한다.
- version은 `metadata.version`(기본 `v001`)을 사용한다.
- `existing_versions(dir)` / `next_version(dir)`로 디스크의 `v###` 버전을 스캔할 수 있다.
- 템플릿은 config의 `path_rules.templates`로 스튜디오별로 override할 수 있다.

```powershell
python -B -m main.mApplication.houdini.cfx_workflow.cli plan --config main/mApplication/houdini/cfx_workflow/examples/shot_config_path_rules.json
```

## TOP Builder 현재 동작

`top_builder.build_top_network(plan)`은 Houdini 세션 안에서 `/obj/cfx_top_{seq}_{shot}`
topnet을 만들고 task당 TOP node 하나를 생성해 `depends_on`대로 와이어링한다.

- `sim_cache`/`preview` task는 `ropfetch`가 된다. `sim_cache`는 shot builder의
  `write_cfx_cache` ROP을 가리키고 shot frame range로 cook하도록 설정된다.
- 나머지 stage는 task + shot config payload(JSON)를 내장한 `pythonscript` node가 되어
  `executors.execute_payload`를 호출한다. 결과가 `failed`면 TOP work item이 에러로 표시된다.
- status가 `skipped`/`blocked`인 task는 bypass 상태로 생성된다 (그래프는 유지, cook 제외).
- 기존 node 재사용, 실패 대신 warning 수집, 결과는 node path가 담긴 dict로 반환된다.

## Executor 현재 동작

`executors.execute_task(shot, task)`는 stage별로 실제 작업을 수행하고
`done`/`failed`/`manual`/`skipped` 상태의 구조화된 결과를 반환한다 (예외는 `failed`로 변환).

- `hda_check`: HDA type 설치 여부 확인
- `shot_setup`: `shot_builder.build_houdini_scene` 호출
- `fix`: `fix_action.parameter_patch`(`scale`/`add`/`set`)를 sim node에 적용, old/new 값 기록
- `sim_cache`: cache ROP frame range 설정(partial resim range 반영) 후 execute
- `validate`: `validator.validate_shot_caches` 실행 (hou 불필요)
- `preview`: `/out`에 `opengl` ROP 생성, `review_dir`로 출력 설정 후 render
- `hda_publish`/`review`/`publish`: 스튜디오 종속 단계라 `manual` (blocked publish는 `skipped`)

## 다음 확장 순서

1. Validation rule을 geometry count, collision marker 등으로 확장한다.
2. Review report를 ShotGrid/Ftrack/CSV/JSON 중 실제 사용하는 review 시스템과 연결한다.
3. Farm submitter를 추가한다 (dry-run 대신 TOP network/hython job 제출).

