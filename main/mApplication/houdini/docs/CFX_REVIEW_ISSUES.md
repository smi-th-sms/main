# CFX `review_issues` 작성 레퍼런스

shot config의 `review_issues` 배열에 리뷰 피드백을 기록하면, `build_workflow_plan`이
이를 읽어 **fix task 생성 / 부분(partial) 재시뮬 / preview 재생성** 등으로 자동 분기합니다.

- 스키마: `cfx_workflow/schema.py` → `ReviewIssue`
- 라우팅 로직: `cfx_workflow/review.py` → `route_issue`, `ISSUE_FIX_MAP`
- 분기 결정: `cfx_workflow/workflow.py` → `build_workflow_plan`, `_asset_resim_scope`

---

## 1. 필드 구조

```json
{
  "issue_type": "penetration",      // 필수 — 라우팅 키 (2번 표)
  "asset": "char_main",             // 대상 asset 이름 (config assets[].name과 일치)
  "frames": [1008, 1009, 1010],     // 문제 프레임 → partial resim 범위 산출
  "severity": "high",               // low|medium|high (현재 정보용, 라우팅엔 미사용)
  "status": "open",                 // 열림 vs 해결됨 (3번)
  "description": "설명 텍스트",
  "metadata": {}                    // 자유 추가 필드 (선택)
}
```

필수는 `issue_type` 하나뿐. 나머지는 생략 시 기본값을 사용합니다:
`asset=null`, `frames=[]`, `severity="medium"`, `status="open"`, `metadata={}`.

---

## 2. `issue_type` 별 동작 (가장 중요)

| issue_type | action_type | resim scope | 씬 재빌드 | 자동 parameter_patch |
|------------|-------------|:-----------:|:--------:|----------------------|
| `penetration` | collision_tuning | **partial** (frames 있을 때) | — | `collision_thickness ×1.5`, `substeps +1` |
| `unstable_sim` | solver_tuning | **full** (불안정은 전체 무효화) | — | `substeps +2` |
| `wrong_input_cache` | refresh_inputs | full | ✅ | — |
| `hda_change` | hda_iteration | full | ✅ (+ `hda_publish` task 추가) | — |
| `preview_only` | preview_regen | **none** (sim 없이 preview만) | — | — |
| (그 외 모든 값) | manual_review | full (수동) | — | — |

> `parameter_patch` 항목 형식: `{"parm": <이름>, "op": "scale"|"add"|"set", "value": <숫자>}`
> — `scale`=곱, `add`=더하기, `set`=대입. fix executor가 sim 노드 parm에 적용합니다.

---

## 3. `status` 의미

`is_open` 판정 기준 (`schema.py:ReviewIssue.is_open`):

- **열린 이슈 → fix task 생성**: `approved` / `closed` / `done` / `resolved` **이외 전부**.
  즉 `open`, `new`, `wip`, `rejected` 등은 모두 "열림"으로 취급됩니다.
- **해결됨 → fix task 사라지고 sim이 skip 가능**: `approved`, `closed`, `done`, `resolved`
  (대소문자 무관).

> sim이 실제로 `skipped`가 되려면 **출력 캐시가 디스크에 존재**해야 합니다
> (`force_resim=false` 전제). 캐시 경로의 `$F4` 프레임 토큰은 자동으로 해석됩니다.

---

## 4. `frames` → resim 범위

- 문제 프레임 양쪽으로 **±10프레임 패딩** 후 shot 범위로 클램프
  (`review.py:DEFAULT_FRAME_PADDING = 10`).
  - 예: `frames=[1050]`, shot `1001–1120` → resim range `[1040, 1060]`
  - 예: `frames=[1005]`, shot `1001–1020` → `[1001, 1015]` (시작은 1001로 클램프)
- **`partial`을 허용하는 타입(`penetration`)에서만** 범위가 의미를 가집니다.
  `frames`가 비어 있으면 partial 타입이라도 `full`로 떨어집니다.
- 같은 asset에 이슈가 여러 개면 partial 범위는 **병합**(min start ~ max end),
  하나라도 full이 있으면 **full 우선**.

---

## 5. 실전 예시

### (a) 관통 — 부분 재시뮬
```json
"review_issues": [
  {
    "issue_type": "penetration",
    "asset": "char_main",
    "frames": [1032, 1054],
    "severity": "high",
    "status": "open",
    "description": "Coat penetrates torso around the turn."
  }
]
```

### (b) 프리뷰만 다시 (sim 유지)
```json
{
  "issue_type": "preview_only",
  "asset": "char_main",
  "status": "open",
  "description": "Cache fine, preview encode failed."
}
```

### (c) HDA 수정 필요 (hda_publish task 추가)
```json
{
  "issue_type": "hda_change",
  "asset": "char_main",
  "status": "open",
  "description": "Cloth preset needs stiffer collar."
}
```

### (d) 이슈 여러 개 → `fix_01`, `fix_02` … 순서로 생성
```json
"review_issues": [
  { "issue_type": "penetration",  "asset": "char_main",      "frames": [1010], "status": "open", "description": "..." },
  { "issue_type": "unstable_sim", "asset": "char_main_hair",                   "status": "open", "description": "..." }
]
```

### (e) 해결 처리 → fix 사라지고 sim skip
```json
{ "issue_type": "penetration", "asset": "char_main", "frames": [1010], "status": "approved", "description": "..." }
```

---

## 6. 주의점

- **`asset` 값은 config의 asset 이름과 정확히 일치**해야 합니다. 일치하지 않으면
  fix executor가 sim 노드를 못 찾아 `manual`(미적용)로 빠집니다.
- `parameter_patch`는 **HDA가 실제로 설치된 경우에만** sim parm에 반영됩니다.
  placeholder null(HDA 미설치) 상태에선 적용 0건 + "parameter not found" 경고로 degrade.
- `severity`는 현재 **기록용**이며 라우팅/우선순위를 바꾸지 않습니다
  (향후 정렬·필터 확장 지점).
- PDG(TOP) 경로의 `ropfetch`는 현재 partial resim 범위를 반영하지 않고 shot 풀레인지로
  cook합니다. partial 범위는 `run_sim_cache` executor 직접 호출 경로에서 적용됩니다.
  (자세한 내용은 `CFX_WORKFLOW_TEST_GUIDE.md`의 "발견된 이슈" 참고)
