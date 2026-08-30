# CFX Workflow 실행 테스트 가이드

현재까지 구현된 work process를 직접 실행하며 검증하기 위한 단계별 가이드입니다.
Step 1~3은 Houdini 없이, Step 4~7은 Houdini 세션 안에서 진행합니다.

## 테스트 체크리스트

| # | 항목 | 대상 모듈 | Houdini | 핵심 확인 포인트 |
|---|------|----------|:-------:|----------------|
| 1 | 자동 테스트 suite | 전체 | 불필요 | 101 tests OK |
| 2-1 | plan 생성 | config_loader, workflow | 불필요 | task 구조/의존성/메타데이터 |
| 2-2 | path_rules 경로 생성 | path_rules | 불필요 | 명시 config와 동일 경로 |
| 2-3 | 동적 분기 | workflow | 불필요 | force_resim/validate/preview/publish 분기 |
| 2-4 | dry-run report | batch_runner | 불필요 | planned status 변환 |
| 3-1 | cache 검증 (실패 케이스) | validator | 불필요 | fail report + exit 1 |
| 3-2 | cache 검증 (통과/경고 케이스) | validator | 불필요 | 더미 캐시로 pass/warning/gap 검출 |
| 4-1 | shot scene 빌드 | shot_builder | **필요** | subnet/체인/placeholder/warnings |
| 4-2 | 실제 HDA 연결 | shot_builder | **필요** | hda_found=True, parm 적용 |
| 4-3 | scene template load/merge | shot_builder | **필요** | 빈 세션=load, 작업 중=merge |
| 5-1 | TOP network 빌드 | top_builder | **필요** | 노드 타입/와이어링/bypass |
| 5-2 | TOP cook | top_builder, executors | **필요** | pythonscript가 executor 호출 |
| 6-1 | executor 단계별 실행 | executors | **필요** | 각 stage의 done/failed/manual |
| 6-2 | sim cook + validate | executors, validator | **필요** | 실제 캐시 파일 생성/검증 |
| 7 | review→fix→partial resim 루프 | 전체 | **필요** | issue 추가 후 fix/partial 동작 |

각 단계에서 발견한 문제(파라미터 이름 불일치, 노드 타입 차이 등)는 이 문서 맨 아래
"발견된 이슈" 섹션에 기록해 두면 다음 디벨롭 사이클의 백로그가 됩니다.

---

## 사전 준비

### A. 로컬 테스트 config

`E:/show` 같은 실제 show 경로를 건드리지 않도록 로컬 임시 경로를 쓰는 테스트 config가
준비되어 있습니다:

```text
main/mApplication/houdini/cfx_workflow/examples/shot_config_local_test.json
```

- `path_rules.root = "C:/temp/cfx_show"` — 모든 출력이 이 아래에 생성됩니다.
- frame range `1001-1020` — 빠른 cook을 위해 짧게 설정.
- review issue 없음 — Step 7에서 직접 추가하며 테스트합니다.

### B. Houdini에서 패키지 import 경로 (Step 4부터 필요)

Houdini Python Shell에서 매 세션 직접 추가하거나:

```python
import sys
sys.path.insert(0, r"E:\script\pythonWorkSpace")
```

또는 `houdini.env`에 영구 등록 (TOP pythonscript cook까지 쓰려면 이 방법 권장):

```text
PYTHONPATH = "E:/script/pythonWorkSpace;$PYTHONPATH"
```

> TOP pythonscript 노드는 별도 프로세스에서 실행될 수 있으므로, Step 5-2의
> executor 호출까지 확인하려면 `houdini.env` 방식이 필요합니다.
> 경로가 없으면 stub은 "executors not importable" 메시지만 출력합니다 (의도된 degrade).

---

## Step 1 — 자동 테스트 suite

Workspace root(`E:\script\pythonWorkSpace`)에서:

```powershell
python -B -m unittest discover -s main\mApplication\houdini\cfx_workflow\tests
```

**기대 결과**: `Ran 101 tests ... OK`

---

## Step 2 — Plan / Dry-run (CLI)

### 2-1. 기본 plan

```powershell
python -B -m main.mApplication.houdini.cfx_workflow.cli plan --config main\mApplication\houdini\cfx_workflow\examples\shot_config.json
```

**확인 포인트**:
- task 10개: `hda_check` x2 → `shot_setup` → `fix` → `sim_cache` x2 → `validate` → `preview` → `review` → `publish`
- `fix_01_collision_tuning.metadata.fix_action`: `resim_scope=partial`, `frame_range=[1032,1054]`, `parameter_patch` 2건
- `sim_cache_char_main.metadata`: `resim_scope=partial`, `resim_frame_range=[1032,1054]`
- `sim_cache_char_main_hair.metadata`: `resim_scope=full` (issue 없는 asset)
- `publish_final_cache.status = blocked`

### 2-2. path_rules 경로 생성

```powershell
python -B -m main.mApplication.houdini.cfx_workflow.cli plan --config main\mApplication\houdini\cfx_workflow\examples\shot_config_path_rules.json
```

**확인 포인트**: 출력의 cache/review/scene 경로가 2-1의 명시 config와 동일한지.

### 2-3. 동적 분기

`shot_config.json`을 복사해 임시 파일을 만들고 `batch` 값을 하나씩 바꿔 plan을 재실행:

| 변경 | 기대 결과 |
|------|----------|
| `"validate_cache": false` | `validate` task 사라짐, preview가 sim에 직접 연결 |
| `"generate_preview": false` | `preview` task 사라짐 |
| `"publish_on_approved": true` | publish status가 `pending` |
| issue의 `"status": "approved"` | `fix` task 사라짐 |
| issue type을 `"hda_change"`로 | `hda_publish_char_main` task 추가 |

### 2-4. dry-run report

```powershell
python -B -m main.mApplication.houdini.cfx_workflow.cli dry-run --config main\mApplication\houdini\cfx_workflow\examples\shot_config_local_test.json --output C:\temp\cfx_dry_run.json
```

**확인 포인트**: pending task들이 `planned`로 기록된 JSON report 생성.

---

## Step 3 — Validator (Houdini 불필요)

### 3-1. 실패 케이스 (캐시 없음)

```powershell
python -B -m main.mApplication.houdini.cfx_workflow.cli validate --config main\mApplication\houdini\cfx_workflow\examples\shot_config_local_test.json
echo $LASTEXITCODE
```

**기대 결과**: 모든 asset `cache_exists: fail`, 전체 status `fail`, exit code `1`.

### 3-2. 더미 캐시로 통과/검출 케이스

더미 프레임 파일 생성:

```powershell
$dir = "C:/temp/cfx_show/projectA/seq010/shot020/cfx/cache/cloth/char_main/v001"
New-Item -ItemType Directory -Force $dir | Out-Null
1001..1020 | ForEach-Object {
    Set-Content -Path ("$dir/char_main.{0:d4}.bgeo.sc" -f $_) -Value ("x" * 5000) -NoNewline -Encoding ascii
}
```

다시 validate → `char_main`은 4개 체크 모두 `pass`가 되어야 합니다.

이어서 검출 능력 확인:

```powershell
# frame gap: continuity fail + missing_frames=[1010]
Remove-Item "$dir/char_main.1010.bgeo.sc"

# 0 byte 파일: file_size_sanity fail + empty_frames=[1005]
Set-Content -Path "$dir/char_main.1005.bgeo.sc" -Value "" -NoNewline -Encoding ascii
```

각 변경 후 validate를 재실행해 해당 체크가 fail로 바뀌는지 확인합니다.
확인이 끝나면 `C:/temp/cfx_show`를 삭제하고 Step 4로 (sim cook이 새로 만들도록).

---

## Step 4 — Houdini: shot_builder

Houdini를 열고 Python Shell에서 (Windows > Python Shell):

```python
import sys
sys.path.insert(0, r"E:\script\pythonWorkSpace")

from main.mApplication.houdini.cfx_workflow.config_loader import load_shot_config
from main.mApplication.houdini.cfx_workflow.shot_builder import build_houdini_scene

shot = load_shot_config(r"E:\script\pythonWorkSpace\main\mApplication\houdini\cfx_workflow\examples\shot_config_local_test.json")
result = build_houdini_scene(shot)

import json
print(json.dumps(result, indent=2, ensure_ascii=False))
```

### 4-1. 기본 빌드 확인

- `/obj/cfx_seq010_shot020` subnet 생성
- asset마다 geo 컨테이너 안에 체인:
  `load_input_cache → IN_ANIM_CACHE → sim_<type> → write_cfx_cache → OUT_CFX_CACHE`
- HDA 미설치 → `sim_cloth`가 null placeholder + warnings에 "not installed"
- `write_cfx_cache`의 file 경로 / frame range(1001-1020)가 config와 일치
- 같은 코드를 **한 번 더 실행** → 노드가 중복 생성되지 않는지 (idempotency)

### 4-2. 실제 HDA 연결 (스튜디오에 cloth/hair HDA가 있는 경우)

config의 `"hda"` 값을 실제 설치된 SOP HDA type 이름으로 바꾸고 새 씬에서 재실행:

- `hda_found: true`, 실제 HDA 노드 생성
- `parameters`의 parm이 실제로 적용되는지 (없는 parm은 warning으로)

### 4-3. scene template

아무 .hip 파일을 template로 지정해 (`"scene_template": "..."`)
**빈 새 세션**에서 실행 → `action: "loaded"`,
**작업 중인 세션**에서 실행 → `action: "merged"` + warning 확인.

---

## Step 5 — Houdini: top_builder + TOP cook

### 5-1. TOP network 빌드

Step 4와 같은 세션에서 이어서:

```python
from main.mApplication.houdini.cfx_workflow.workflow import build_workflow_plan
from main.mApplication.houdini.cfx_workflow.top_builder import build_top_network

plan = build_workflow_plan(shot)
top_result = build_top_network(plan)
print(json.dumps(top_result, indent=2, ensure_ascii=False))
```

**확인 포인트**:
- `/obj/cfx_top_seq010_shot020` 안에 task당 노드 1개, `depends_on`대로 연결
- `sim_cache_*`는 `ropfetch`이고 `roppath`가 `write_cfx_cache`를 가리킴
- `publish_final_cache`는 bypass 상태 (노란색)
- ropfetch의 frame range가 1001-1020

> **이 단계에서 가장 확인이 필요한 부분**: `ropfetch`의 parm 이름
> (`roppath`/`framegeneration`/`range1`)이 사용 중인 Houdini 버전의 실제 parm과
> 일치하는지. warnings에 "parameter not found"가 나오면 버전 차이이므로 기록해 주세요.

### 5-2. TOP cook (executors 호출)

`houdini.env`에 PYTHONPATH가 등록된 상태에서:

1. topnet 안에서 `hda_check_char_main` 노드 선택 → 우클릭 → **Cook Selected Node**
2. work item을 middle-click → 로그에서 executor JSON 결과 확인

**기대 결과**:
- HDA 미설치 상태면 `status: failed` + work item 에러 (의도된 동작 — hda_check의 역할)
- `shot_setup` 노드 cook → `status: done` (단, TOP가 별도 프로세스로 돌면 그 프로세스의
  씬에 빌드되므로, 동작 검증은 Step 6의 직접 호출이 더 명확합니다)
- PYTHONPATH 미등록이면 "executors not importable" 출력 (degrade 확인도 의미 있음)

---

## Step 6 — Houdini: executors 단계별 직접 실행

TOP을 거치지 않고 executor를 순서대로 직접 호출하는 것이 동작 검증에 가장 명확합니다.
새 씬에서:

```python
import sys, json
sys.path.insert(0, r"E:\script\pythonWorkSpace")

from main.mApplication.houdini.cfx_workflow.config_loader import load_shot_config
from main.mApplication.houdini.cfx_workflow.workflow import build_workflow_plan
from main.mApplication.houdini.cfx_workflow.executors import execute_task

shot = load_shot_config(r"E:\script\pythonWorkSpace\main\mApplication\houdini\cfx_workflow\examples\shot_config_local_test.json")
plan = build_workflow_plan(shot)
tasks = {t.task_id: t for t in plan.tasks}

def run(task_id):
    result = execute_task(shot, tasks[task_id])
    print(json.dumps(result.as_dict(), indent=2, ensure_ascii=False))
    return result
```

### 6-1. 순서대로 실행

```python
run("hda_check_char_main")     # HDA 없으면 failed (정상), 있으면 done
run("shot_setup")              # done — /obj에 네트워크 생성
run("sim_cache_char_main")     # done — filecache cook, C:/temp/cfx_show에 파일 생성
run("validate_cache")          # 캐시가 실제로 생겼으면 done, 아니면 failed + report
run("generate_preview")        # done — /out/cfx_preview_* opengl ROP 생성/render
run("review_result")           # manual + open issue 요약
run("publish_final_cache")     # skipped (blocked 상태)
```

**확인 포인트**:
- `sim_cache` 후 `C:/temp/cfx_show/.../cache/cloth/char_main/v001/`에 `.bgeo.sc` 파일 생성
  - placeholder sim(null)이면 빈 geometry가 캐시되므로 파일이 매우 작음 →
    `validate`에서 `file_size_sanity` warning이 뜨는 것까지가 **정상 동작**
- `generate_preview` 후 review_dir에 .jpg 생성 (카메라 없는 씬이면 뷰포트 기본 렌더)
- 각 결과의 `warnings`에 실제 parm 이름 불일치가 있는지 — 있으면 기록

### 6-2. 실패 경로 확인

새 씬에서 `shot_setup` 없이 바로 `run("sim_cache_char_main")` →
`failed` + "run shot_setup first" 메시지가 나오는지.

---

## Step 7 — End-to-end: review → fix → partial resim

Step 6까지 완료된 상태(캐시 존재)에서 review issue를 추가하는 시나리오:

1. `shot_config_local_test.json`에 issue 추가:

```json
"review_issues": [
  {
    "issue_type": "penetration",
    "asset": "char_main",
    "frames": [1008, 1009, 1010],
    "severity": "high",
    "status": "open",
    "description": "Test penetration issue."
  }
]
```

2. config를 다시 로드하고 plan 재생성 → 변화 확인:

```python
shot = load_shot_config(r"...\shot_config_local_test.json")
plan = build_workflow_plan(shot)
tasks = {t.task_id: t for t in plan.tasks}
# fix_01_collision_tuning 생성됨
# sim_cache_char_main: resim_scope=partial, resim_frame_range=[1001,1020] (패딩 후 클램프)
```

3. fix → partial resim 실행:

```python
run("fix_01_collision_tuning")   # done — sim node parm에 patch 적용 (old/new 기록)
run("sim_cache_char_main")       # done — frame range가 partial range로 설정되어 cook
```

**확인 포인트**:
- fix 결과의 `applied`에 collision_thickness(×1.5), substeps(+1)의 old/new 값
- sim의 `details.frame_range`가 partial range인지
- placeholder sim이라 parm patch가 시각적 의미는 없지만, **실제 HDA로 바꾸면
  이 지점에서 실제 sim parm이 바뀌는지**가 최종 검증 포인트

4. issue의 `"status"`를 `"approved"`로 바꾸고 재-plan →
   fix task가 사라지고 sim이 `skipped`(캐시 존재)가 되는지.

---

## 발견된 이슈 (테스트하며 기록)

| 날짜 | 단계 | 증상 | 비고 |
|------|------|------|------|
| 2026-06-24 | 5-2 | ropfetch가 out-of-process로 cook될 때 untitled hip이면 전 work item 실패: `Failed to transfer file dependency: '.../untitled.hip' does not exist` | PDG cook 전 hip 저장 필요. (pythonscript는 in-process라 영향 없음) |
| 2026-06-24 | 5-2 | `framegeneration=1`(Frame Range)이 **프레임당 work item**을 생성 → sim이 순차 cook이 아니고, 하류가 이를 상속·곱해 폭증(validate 20개, preview 400개) | `top_builder._configure_ropfetch`에 `singletask=1`("Cook Frames as Single Work Item") 추가로 수정. sim=1, validate=1로 정상화 확인 |
| 2026-06-24 | 6 | sim cook 실패: `load_input_cache`(alembic SOP)가 입력 abc 미존재 시 빈 geo가 아니라 **하드 에러** → write_cfx_cache까지 전파 | **수정됨**: `_create_input_loader`가 alembic `missingfile`/file `missingframe`을 "No Geometry"(1)로 설정 + 부재 경고. 입력 없이도 sim CookedSuccess, 빈 geo 캐시 20프레임 확인 |
| 2026-06-24 | 5-1 | `generate_preview` ropfetch의 `roppath`가 비어 cook 시 `Unable to find ROP node ''` 경고 | **수정됨**: PREVIEW를 `_ROPFETCH_STAGES`에서 제외해 pythonscript로 전환(run_preview executor 호출). 재빌드 후 경고 0, work item 1개로 CookedSuccess 확인 |
| 2026-06-24 | 6 | preview opengl ROP이 `No camera specified for render.`로 실패 → jpg 미생성 (테스트 씬에 카메라 없음) | **수정됨**: `run_preview`가 `_ensure_preview_camera`로 카메라 생성·연결(geo bbox로 프레이밍). 직접/PDG 경로 모두 jpg 20프레임 렌더 확인 |
| 2026-06-24 | 6 | `run_preview`가 ROP render 에러를 확인하지 않고 무조건 `status=done` 반환 → **거짓 성공** | **수정됨**: execute 후 `rop.errors()` 확인해 에러 시 `failed` 반환 (`_node_errors`) |
| 2026-06-24 | 6 | placeholder 캐시(~1.5KB)가 `file_size_sanity` **pass** (가이드는 warning 예상) | validator 임계값이 1.5KB보다 낮음. task metadata의 `basic_motion_delta` 체크명도 validator 실제 체크(`file_size_sanity`)와 불일치 |
| 2026-06-24 | 7 | issue를 `approved`로 바꿔도 sim이 `skipped`가 안 되고 항상 `full` resim | **수정됨**: `workflow._path_exists`가 `$F4` 프레임 토큰을 리터럴로 검사해 캐시를 못 찾던 버그. validator의 `split_frame_pattern`/`collect_frame_files` 재사용으로 수정. open=partial / approved=skipped 확인 + 회귀 테스트 추가 |
| 2026-06-24 | 7 | `run_fix`가 placeholder null sim에 parm patch 적용 시 0건 + parm별 warning, status `manual` | **의도된 degrade** (HDA 미설치). 실제 HDA면 collision_thickness ×1.5 / substeps +1 적용됨. 로컬 config는 range가 1001–1020이라 partial range도 full과 동일하게 클램프됨(정상) |
| 2026-06-25 | 5-2 | 첫 cold cook에서 `validate_cache`가 `Cache validation failed`로 work item 실패 → 다운스트림 차단. 캐시 완비 후 재-cook하면 pass | **수정됨**: out-of-process sim이 프레임 flush를 끝내기 전 in-process validate가 읽는 레이스. `run_validate`가 "부분 캐시(일부 프레임만 존재)" 증상일 때만 짧게 재시도(`_incomplete_flush`, 캐시 0개는 즉시 fail). 회귀 테스트 추가 |
| 2026-06-25 | 7 | TOP `ropfetch`(sim_cache)의 frame range가 plan의 `resim_frame_range`(partial)를 반영하지 않고 항상 shot 풀레인지로 cook | **수정됨**: `top_builder._configure_ropfetch`가 task의 `resim_scope=="partial"`이면 `resim_frame_range`를 ropfetch range에 적용. `shot_config.json`(이슈 1042–1044)에서 range 1032–1054 확인 + 회귀 테스트 |
| 2026-06-25 | 4-2/7 | (B) 실제 HDA 검증: 테스트 HDA(`cfxtest::cloth_sim::1.0`, substeps/collision_thickness parm)로 end-to-end | `hda_found=true`, fix가 실제 parm 변경(collision_thickness 0.015→0.0225, substeps 4→5, status `done`), sim cook 20프레임 성공. placeholder의 `manual` degrade가 실제 HDA에선 정상 적용됨을 확인 |
| 2026-06-30 | 7 | (이전 백로그 해소) 로컬 range 1001–1020에선 partial이 full로 클램프돼 **distinct partial range를 못 보여줌** | **검증됨**: `shot_config_local.json`을 range 1001–1080으로 넓히고 내부 이슈([1040–1042]) 추가 → partial range `[1030,1052]`로 full과 구분 확인. `cfx_local_test_01.hip`(실제 HDA) 로드 후 fix(0.015→0.0225, 4→5) → partial resim 실행 시 **mtime 비교로 정확히 1030–1052(23프레임)만 재cook, 나머지 57프레임 불변** 증명. approved 전환 시 fix 소멸 + sim `skipped`(완전 캐시) 재확인 |

> 기록 예시: "Step 5-1 / H20.5에서 ropfetch에 framegeneration parm 없음 → 실제 이름 확인 필요"
