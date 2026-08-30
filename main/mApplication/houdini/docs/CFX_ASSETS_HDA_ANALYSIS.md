# CFX Assets HDA 워크플로우 분석 & PDG 최적화 설계

> 실무 CFX 파이프라인(`Cinematic::assets::1.0` HDA + CFX Assets Manager)을 라이브로 해부하고,
> `cfx_workflow` 패키지가 이를 config-driven + PDG 흐름으로 흡수하기 위한 분석 문서.
> 작성: 2026-07-01, 라이브 세션 = Houdini 21.0.440 / `E:/rnd/houdini/test01/cfx_local_test_01.hip`의 `/obj/assets1`.
>
> 관련: [`CFX_WORKFLOW_OVERVIEW.md`](CFX_WORKFLOW_OVERVIEW.md), [`CFX_WORKFLOW_TEST_GUIDE.md`](CFX_WORKFLOW_TEST_GUIDE.md)

---

## 0. 외부 의존성 (repo 밖)

| 구분 | 경로 |
|------|------|
| Manager 스크립트 | `T:\scripts\python\application\houdini\houdini21.0\script\` |
| Assets HDA (인스턴스용) | `Z:/inhouse/Houdini/otls/base/Assets.hda` |
| Assets HDA (기본 install) | `Z:/inhouse/Houdini/otls/object_Cinematic.assets.1.0.hda` |
| show root | `Z:/show/{project}/` |

Manager 주요 파일: `cfx_assets_ui.py`(메인 `CFXAssetsMainWindow`), `proxy_manager.py`,
`proxy_blast_sync.py`, `parts_deform_sync_callback.py`, `object_merge_sync.py`,
`handlers.py`, `launch_cfx_ui.py`, `project_dir_simple_menu.py`.

---

## 1. 3계층 구조

1. **매니저 UI** — shelf → `CFXAssetsMainWindow`. project/seq/shot/asset 선택 → FBX/anim/hair 적용 →
   HDA install/instantiate → parts/blast/deform 동기화.
2. **Assets HDA** — `Cinematic::assets::1.0` (OBJ 레벨), 인스턴스 `/obj/assets`. 내부 8개 sub-geo.
3. **캐시 출력** — filecache(`.bgeo.sc`) + rop_alembic(`.abc`).

---

## 2. 노드별 분석 (파라미터 / Python / 연결)

`/obj/assets1` 내부 8개 노드. **노드 간 연결은 hard-wire가 아니라 `object_merge`(소프트 참조)** 로 이뤄진다.

### 2.1 FBX (`geo`) — 초기 데이터 셋업
커스텀 인터페이스 폴더:
- **Load Name**: `asset_name`, `root_name`(기본 `root`), `pelvis_name`(기본 `pelvis`)
- **FBX Import**: `character_import`, `hair_import`, `animation_import` (파일 경로)
- **Duration**: `start_duration`, `end_duration`, `timeline_set`(버튼)
- **T Pose**: `T_pose_start_position`, `T_pos`, `T_pos_ofs_translate`, `T_pos_ofs_rotate`
- **Transform Mult**: `position_mult`, `rotate_mul`, `pelvis_Rotate`

**Python 로직 — `timeline_set` 버튼 콜백**: 임시 `fbxanimimport` 노드를 만들어
FBX take의 `clipinfo`(`source_rate`, `source_range`)를 원본 그대로 읽고
(`useanimation*`/`useplayback*` 토글 OFF로 현재 타임라인 오염 방지),
`start/end_duration` 오프셋을 적용해 `hou.setFps` + `playbar` 설정. (Manager `handlers.timeline_setting`과 동일 로직)

내부: `fbxcharacterimport`, `anim_subnet1`(character_TPos 포함 — skeleton 감지 소스),
`fbx_anim`/`fbx_rootActor`(kinefx fbxanimimport). **출력 3개**:
`output0`=animation_mesh, `output1`=setting_animation_skeleton, `output2`=original_animation_skeleton.

### 2.2 Corrective (`geo`) — 관통/근접 수정 ✋수동
`object_merge1 ← FBX/output0` → `connectivity1` → `split3`(BODY/CLOTH) → `BODY`,
`edit1`(**수동 편집 SOP** — 캐릭터·의상 겹침/근접 지점 editting) → `CLOTH` → `merge1` → `OUT_CORRECTIVE`(display).

### 2.3 Collision (`geo`) — 충돌 바디
`object_merge_cloth ← Corrective/OUT_CORRECTIVE` → `transform1` → `blast1` →
`collision_subnet` → `collision_group`(groupcreate) → `collision` → `transform2/3` → `output0`.

### 2.4 Proxy (`subnet`) — parts별 프록시 ✋수동
- 파라미터: `cloth_parts`(개수), `part_name_{i}`, `export_proxy_cache`(← 상위 토글).
- 템플릿 노드: `geo_template01`(merge_source→blast→timeshift→remesh→scatter→vdbfromparticles→vdbsmoothsdf→convertvdb→attribcopy→`OUT_parts_PROXY`), `geo_hair_template01`.
- **Manager `proxy_manager`가 asset별로 `geo_{part}` 복제 생성**(예: geo_pants/geo_outer/geo_hair/geo_hairbend). 제네릭 인스턴스엔 템플릿만 존재.

### 2.5 Cache (`geo`) — ProxyCache 생성 ⬤cook
- `collision_filecache`(`filecache::2.0`) ← `object_merge1`(Collision/output0 + Proxy parts) → `COLLISION`
- `proxy_filecache`(`filecache::2.0`) ← `object_merge2`(Proxy parts) → `PROXY`(display)

### 2.6 Constraint (`geo`) — Vellum sim ⬤cook (50노드, 다수 bypass=실험용)
활성 체인: `object_merge1 ← Cache/PROXY`, `object_merge4 ← Cache/COLLISION`, `object_merge2 ← Corrective` →
vellumconstraints → `vellumsolver1` → `vellumpostprocess1` → **`sim_filecache`**(`filecache::2.0`) →
`merge4` → `attribdelete1` → `split1` → `OUT_CLOTH`(display) / `OUT_HAIR`. (`hair_filecache` bypass)

### 2.7 Deform (`geo`) — 원본 결합
`object_merge1 ← Constraint/OUT_CLOTH`, `4 ← Constraint/OUT_HAIR`, `3 ← Proxy/geo_hair/follow_hair`,
`2 ← Corrective/OUT_CORRECTIVE`. `Parts_Deform` subnet(기본 bypass)이 시뮬 결과에 원본 디테일 부착.
Manager `parts_deform_sync_callback`이 `@proxy_path` 속성값에 맞춰 `Parts_Deform_*` 노드 생성/삭제.

**part별 pointDeform 페어링 (deform 효율 핵심, 코드 확인):**
`Parts_Deform` 내부 = `blast1 ← proxy_path`(@proxy_path=… 로 part 프록시 격리),
`blast2 ← geo_path`(@geo_path=… 로 part 원본 격리), `pointdeform1 ←`(원본 geo, rest 프록시, 애니 프록시).
즉 **원본 hi-res를 저해상 시뮬 프록시로 pointDeform**. part마다 두 그룹으로 격리하므로 전역탐색 없이
매칭 포인트만 처리 + part 독립 재cook. `geo_path` 속성은 `FBX/deform_subnet/attribwrangle10`이
원본 FBX 지오의 `path`를 읽어 심고, 한 part가 여러 `@geo_path`를 묶을 수도 있음(예: head+cloth).
→ config의 `ProxyPart`가 `geo_path`(원본, list)와 `proxy_path`(프록시 그룹)로 분리 저장하는 근거.

### 2.8 Out (`geo`) — UE용 최종 alembic ⬤cook (34노드)
`object_merge_cloth2 ← Deform/output0`, `object_merge_cloth7 ← Deform/output1`, +FBX skeletons.
`kinefx::skeletonblend` → transform(UE import 정렬) → `Cloth_Cache`/`Hair_Cache`(`rop_alembic`).
filename 표현식 = `hou.expandString("$HIP") + "/" + hou.node("../../FBX").evalParm("asset_name") + "_Cloth_Cache.abc"`.

---

## 3. 실제 의존성 DAG

`object_merge` 소스 경로에서 도출한 실제 데이터 흐름 (사용자 기술 순서와 일치):

```
FBX ──output0──> Corrective(edit ✋) ──┬─> Collision ──────────────┐
                                        │                          ├──► Cache/collision_filecache ⬤
                                        └─> Proxy(parts ✋) ────────┴──► Cache/proxy_filecache ⬤
                                                                          │  (export_proxy_cache)
                    Cache/COLLISION + Cache/PROXY ───────────────────────► Constraint/sim_filecache ⬤ (Sim_FileCache)
                                                                          │
                        Constraint/OUT_CLOTH, OUT_HAIR ──> Deform ───────► Out/Cloth_Cache ⬤ (Cloth_Alembic)
                                                                          └► Out/Hair_Cache  ⬤ (Hair_Alembic)
```
- ⬤ = cook 타깃(filecache / rop_alembic), ✋ = 아티스트 수동 게이트
- FBX outputs: `output0`(anim mesh)→Corrective/Constraint, `output1`/`output2`(skeletons)→Out/Proxy

### cook 타깃 & top-level 토글 배선
| cook 노드 | 타입 | execute 게이트 |
|-----------|------|----------------|
| `Cache/collision_filecache` | filecache::2.0 | (항상) |
| `Cache/proxy_filecache` | filecache::2.0 | `Proxy.export_proxy_cache ← export_proxy_cache` |
| `Constraint/sim_filecache` | filecache::2.0 | `.execute ← ch("../../Sim_FileCache")` |
| `Constraint/hair_filecache` | filecache::2.0 | (bypass) |
| `Out/Cloth_Cache` | rop_alembic | `.execute ← ch("../../Cloth_Alembic")` |
| `Out/Hair_Cache` | rop_alembic | `.execute ← ch("../../Hair_Alembic")` |

---

## 4. Manager의 config 생성 로직 (경로 규칙)

`cfx_assets_ui.py`가 조립하는 경로 (파일:라인):

**Shot**
- working dir: `{project}/{seq_subdir}/{seq}/{shot}/SIM/wip/houdini` (기본 `seq_subdir="sequences/"`) — 677-702
- anim fbx: `{...}/{shot}/ANM/pub/fbx/*.fbx` — 205-206, 732-734
- rootActor 변형: `anim.fbx → anim_rootActor.fbx` (있으면 그걸 사용) — 855-858

**Asset**
- full path: `{project}/{assets_subpath}/{asset}/Sim/wip/houdini` (기본 `assets_subpath="assets/Character"`) — 952-957
- character fbx: `{asset}/RIG/wip/maya/fbx/*.fbx` — 319, 383
- hair guide: `{asset}/RIG/wip/maya/cache/alembic/*.{obj,fbx,abc,bgeo,vdb}` — 428

**HDA 셋업** (1305-1477): `{asset_fullpath}/asset/{AssetName}.hda` 있으면 로컬, 없으면 기본 HDA install →
`createNode("assets")` → `allowEditingOfContents()`.

**FBX parm 주입** (787-870, 1056-1210):
`asset_name`, `character_import`, `animation_import`, `hair_import` 값을 UI 선택에서 주입.
**skeleton 자동 감지**(1138-1178): `FBX/anim_subnet1/character_TPos` 지오메트리에서
`fbx_node_type=="Skeleton"`인 point의 `name` 수집 → `root_name=[0]`, `pelvis_name=[1]`.

**동기화 콜백** (parts가 동적이라 필요):
- `object_merge_sync.sync_object_merge2` — `Cache/object_merge2`의 `numobj`/`objpathX`를 cloth_parts에 맞춤
- `proxy_blast_sync` — `Constraint`/`Deform`의 `blast_{part}` group(`@proxy_path=*{part}*`) 동기화
- `parts_deform_sync_callback` — `Deform/Parts_Deform_*` 노드 생성/삭제 (`sim_filecache` Pre-Render 트리거)

---

## 5. "반복 수정" 원인 & 최적화 포인트

| # | 문제 | 근거 | 최적화 |
|---|------|------|--------|
| 1 | **baked 캐시 경로 불일치** | `collision/proxy_filecache.file` = `Z:/show/PUBGOM/assets/Character/Jake/...` (이전 프로젝트 하드코딩), `sim/hair_filecache` = `$HIP/geo/...` 상대 | config `path_rules`로 `basedir` 일괄 설정 → 프로젝트 교체 시 재지정 불필요 |
| 2 | **soft object_merge + 수동 sync 버튼** | parts 동적 → 3개 sync 스크립트를 버튼으로 실행. `Cache/object_merge1`에 `OUT_Collective` 오타 깨진 레퍼런스 존재 | parts 리스트를 config로 받아 sync를 결정론적으로 생성/검증 |
| 3 | **cook 순서·토글 수동 관리** | 4 filecache + 2 alembic을 순서대로 토글·cook | PDG DAG로 의존성/순서/partial resim 자동화 |

---

## 6. PDG 적용 설계

| 계층 | PDG 적합성 | 방식 |
|------|-----------|------|
| HDA install + FBX parm + skeleton 감지 + timeline | ✗ 사전 스크립트 | config-driven setup (Manager 로직 재사용) |
| Corrective 편집 / Proxy parts 정의 | ✋ 수동 게이트 | 셋업 자동 → 아티스트 작업 → "approve" work item |
| collision → proxy → sim → alembic cook | ✓ **PDG 최적** | TOP `ropfetch`/`filecache`로 DAG 그대로, asset별 wedge fan-out, partial resim range |

**재사용**: `cfx_workflow.top_builder`/`executors`의 검증된 패턴
(ropfetch + `singletask` + partial resim range + validate flush retry — [`CFX_WORKFLOW_TEST_GUIDE.md`](CFX_WORKFLOW_TEST_GUIDE.md))을
실제 Assets HDA의 6개 cook 타깃에 매핑하면 그대로 적용 가능.

권장 TOP 구조 (asset당):
```
[approve gate] → collision_filecache ─┐
                 proxy_filecache ──────┴→ sim_filecache → (Deform) → Cloth_Cache / Hair_Cache
```
multi-asset shot은 asset 리스트로 partition/wedge fan-out.

---

## 7. config 스키마 브리지 (제안, 미구현)

Manager가 이미 산출하는 값 → `cfx_workflow` asset config JSON → setup이 HDA parm 주입 → PDG cook.

```jsonc
{
  "show": "PUBGOM", "asset": "Jake", "asset_type": "Character",
  "path_rules": {                         // §4의 Manager 규칙을 그대로 반영
    "show_root": "Z:/show",
    "asset_subpath": "assets/Character",
    "asset_work": "Sim/wip/houdini",
    "character_fbx": "RIG/wip/maya/fbx",
    "hair_guide": "RIG/wip/maya/cache/alembic",
    "shot_seq_subdir": "sequences", "shot_work": "SIM/wip/houdini",
    "shot_anim": "ANM/pub/fbx"
  },
  "hda": { "type": "Cinematic::assets::1.0", "lib": "Z:/inhouse/Houdini/otls/base/Assets.hda" },
  "fbx": {                                 // FBX 노드 parm 주입값
    "asset_name": "Jake", "root_name": "root", "pelvis_name": "pelvis",
    "character_import": "...", "animation_import": "...", "hair_import": "...",
    "start_duration": 0, "end_duration": 0
  },
  "proxy_parts": ["pants", "outer", "hair", "hairbend"],  // sync 결정론적 생성
  "cook": {                                // top-level 토글 → PDG 타깃 게이트
    "export_proxy_cache": true, "Sim_FileCache": true,
    "Cloth_Alembic": true, "Hair_Alembic": false
  }
}
```

이 스키마가 setup 단계에서 §2의 parm과 §3의 cook 타깃을 채우고, `path_rules`가 filecache `basedir`를
통일하면 **프로젝트마다 config만 교체**하는 흐름이 된다.

---

## 8. 미해결 백로그 (구현 시 처리)

- `Cache/object_merge1`의 `../../Corrective/OUT_Collective` **오타 레퍼런스** → 실제 `OUT_CORRECTIVE`로 수정 필요
- filecache `basedir`가 `$HIP/geo`라 작업 hip 위치에 종속 → path_rules 기반 절대경로로 전환
- `hair_filecache` 기본 bypass — hair 파이프라인 사용 여부에 따라 cook 타깃 포함/제외 결정
- multi-asset shot에서 asset별 `/obj/assets`, `/obj/assets1`... 네이밍/인스턴싱 규칙 확정 필요
- Corrective edit / Proxy parts의 "수동 게이트"를 PDG work item으로 표현하는 방식(승인 대기) 설계
