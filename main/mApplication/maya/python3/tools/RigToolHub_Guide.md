# Rig Tool Hub — 내부 공유 가이드

> 작성일 : 2026-03-26
> 대상 버전 : Maya 2022 이상 / Python 3
> 패키지 : `rig_tool_hub.py` + 동봉 파일 일체

---

## 1. 아젠다 및 제작 배경

MetaHuman 기반 캐릭터 리깅 파이프라인에서 반복적으로 수행하던 작업들을
**AdvancedSkeleton(AS) 빌드 전처리 → 빌드 이후 디벨롭 → 씬 최종 정리**
세 단계로 표준화하고, 각 단계를 하나의 UI에서 실행할 수 있도록 제작했습니다.

기존에는 각 작업자마다 개인 스크립트를 별도로 유지하면서 버전 불일치,
누락 작업, 신규 투입자의 온보딩 지연 등의 문제가 반복되었습니다.

---

## 2. 필요성

| 기존 방식 | 툴 도입 후 |
|-----------|-----------|
| 작업자별 개인 스크립트 파편화 | 팀 공통 단일 UI |
| FitSkeleton 배치 수작업 (조인트별 이동) | MH 조인트 기준 자동 배치 |
| 네임스페이스·레이어 정리 누락 잦음 | Clean Scene 버튼 한 번으로 처리 |
| 컨트롤러 계층 구성 순서 작업자마다 상이 | Build ALL로 순서 고정 |
| 신규 투입자 셋업 학습 비용 큼 | 각 버튼에 Help(?) 설명 내장 |

---

## 3. 효율성

- **AS Fit Tool** : FitSkeleton 수동 배치 대비 작업 시간 **80% 이상 단축**
  - MH 조인트 위치를 읽어 자동 배치 → 수십 개 조인트를 일일이 이동할 필요 없음
  - 스케일 자동 계산으로 비례 오류 방지

- **Rig Develop Tool** : AS 빌드 이후 반복 작업 자동화
  - Build ALL 한 번으로 Feature 1~8 전체 순서 실행
  - Revert ALL로 전체 롤백 → 재빌드 시 초기화 신속

- **패키지 배포** : `tools/` 폴더 복사만으로 셋업 완료, 경로 하드코딩 없음

---

## 4. 시작 방법

### 패키지 구성 (필수 파일)

```
tools/
├── rig_tool_hub.py            ← 진입점
├── as_fit_tool.py             ← AS Fit 탭
├── rig_develop_tool.py        ← Rig Develop 탭
├── ctrl_creator_tool.py       ← 컨트롤러 Shape/Color 처리
└── ctrl_creator_presets.json  ← 컨트롤러 프리셋 데이터
```

### Maya 셸프 버튼 등록

```python
import sys, os, importlib

_hub = r"팀공유경로\tools"   # 이 경로만 팀 환경에 맞게 수정
if _hub not in sys.path:
    sys.path.insert(0, _hub)

import rig_tool_hub
importlib.reload(rig_tool_hub)
rig_tool_hub.show()
```

> `userSetup.mel` 수정 불필요. `rig_tool_hub.py` 자체가 `__file__` 기준으로
> 나머지 모듈 경로를 자동 등록합니다.

---

## 5. AS Fit Tool

AdvancedSkeleton FitSkeleton을 MetaHuman 조인트 위치에 자동 배치하는 툴입니다.
AS NameMatcher 없이 커스텀 매핑으로 동작합니다.

### 5-1. AS Files Path

AdvancedSkeleton 설치 경로(또는 `nameMatchers` / `fitSkeletons` 폴더가 있는 경로)를 지정합니다.

- **Browse** : 폴더 선택 다이얼로그
- 경로는 Maya optionVar에 저장되어 다음 세션에도 유지됩니다.

### 5-2. Template

`nameMatchers/` 폴더의 `.txt` 파일을 불러와 Joint Mapping 테이블을 자동으로 채웁니다.

- 기본 선택값 : **meta** (파일 이름이 정확히 `meta.txt`인 항목)
- **Refresh** : 폴더를 다시 스캔하여 목록 갱신
- **Load** : 선택한 템플릿 적용. 같은 이름의 `.ma` 파일이 있으면 FitSkeleton 경로도 자동 설정

### 5-3. Side Settings

조인트 이름의 좌우 구분 방식을 설정합니다.
MetaHuman 기본값은 **Right = `_r` / Left = `_l`** (이름 뒤에 붙는 방식).

| 설정 | 설명 |
|------|------|
| Right / Left | 좌우 suffix/prefix 문자열 |
| Middle | 중립 조인트 suffix (보통 비워둠) |
| Before Name | 체크 시 prefix 방식 (`_r_upperarm`) |
| Underscore | 구분자 `_` 추가 여부 |

### 5-4. Namespace

씬의 네임스페이스를 자동 스캔하여 AS / MH 드롭다운을 채웁니다.

- **Detect** : 스캔 실행. AS와 MH 각각 힌트 키워드로 자동 분류

### 5-5. FitSkeleton File

임포트할 FitSkeleton `.ma` 파일을 선택합니다.

- 기본 선택값 : 파일명이 정확히 **`meta.ma`**인 파일. 없으면 **None**
- **Refresh** : 폴더 재스캔
- **Scale**
  - `0` (기본) : MH 조인트 높이 ÷ FitSkeleton 높이로 자동 계산
  - 수동 입력 시 해당 값 고정
  - **Preview** : 현재 씬 기준 권장 스케일 미리 계산

### 5-6. Joint Mapping

AS FitJoint 이름 ↔ MH Joint 이름을 매핑하는 테이블입니다.
Side(L/R) 조인트는 **base 이름만** 입력합니다. (side suffix는 Side Settings 참조)

| 버튼 | 동작 |
|------|------|
| + 행 추가 | 빈 행 추가 |
| Save | 현재 매핑 + Side Settings를 `.txt`로 저장. 저장 후 Template 목록 자동 갱신 |
| Open Folder | `nameMatchers/` 폴더를 탐색기로 열기. `.txt` 직접 편집 가능 |
| x (행) | 해당 매핑 행 삭제 |

### 5-7. Functions

| 버튼 | 동작 |
|------|------|
| **Create + Place FitSkeleton** | FitSkeleton 임포트 후 MH 조인트 위치에 자동 배치 |
| **Check Mapping** | 매핑 테이블의 MH 조인트 이름이 씬에 존재하는지 확인 |
| **Show PoleVectors** | FitSkeleton PoleVector 핸들 표시 |
| **Straighten PoleVectors** | PoleVector를 기본(정렬) 위치로 초기화 |
| **Open AdvancedSkeleton Tool** | AS 메인 툴 실행 (FitSkeleton 배치 후 Build 진행) |

---

## 6. Rig Develop Tool

AS Build 이후 리그 디벨롭 및 씬 최종 정리를 위한 툴입니다.
각 Feature는 독립 실행 가능하며, **Build ALL / Revert ALL**로 전체 일괄 처리도 지원합니다.

### Namespace

리그 오브젝트의 네임스페이스를 지정합니다.
**Detect** : 선택한 오브젝트에서 자동 감지. 비워두면 네임스페이스 없이 동작.

---

### Feature 1 — IK Settings Controller

IK/FK 전환, Stretch 등의 파라미터를 제어하는 Settings 컨트롤러를 생성합니다.

- `IKLeg_L`, `IKLeg_R`, `IKArm_L`, `IKArm_R` 각각의 custom attribute를
  하위 NURBS 컨트롤러에 복사 후 연결
- **Revert** : 생성된 컨트롤러 삭제 및 원복

---

### Feature 2 — Weapon Offset Controller

양손 Wrist 조인트에 무기 오프셋 컨트롤러 계층을 생성합니다.

```
Fingers_L/R
└── *_weapon_offset_OS
    └── *_weapon_offset_CS
        └── *_weapon_offset
```

- **Revert** : 생성된 계층 삭제

---

### Feature 3 — Main Hierarchy

씬 최상위에 리그 컨트롤러 계층을 구성합니다.

| 컨트롤러 | 역할 |
|----------|------|
| Master | 씬 전체 최상위 |
| Global | 전체 이동 / 회전 / 스케일 |
| MainHip | 허리 오프셋 |

- **Revert** : 생성된 계층 삭제 및 원복

---

### Feature 4 — correctiveRoot rx Mute

`correctiveRoot_*` 조인트의 X축 회전(rx)을 런타임에서 스위치로 제어합니다.

- 각 조인트에 `rxLock` 커스텀 attribute 추가
- Condition 노드 연결 : `rxLock=1` → rx 강제 0 (뮤트) / `rxLock=0` → 원래 값 통과
- **Revert** : `rxLock` attribute 및 Condition 노드 삭제

---

### Feature 5 — IKSpine Handle Fix

IKSpline 핸들의 방향 오류를 보정합니다.

- `dForwardAxis = 2` 설정
- `constraintRotate` 값을 `targetOffsetRotate`에 연결
- `Root.worldOrientForward` 속성이 존재하는 씬에서 실행
- **Revert** : 변경 사항 원복

---

### Feature 6 — Shape / Color + ControlSet

`ctrl_creator_presets.json` 기반으로 컨트롤러 모양과 색상을 일괄 적용하고
ControlSet에 등록합니다.

- 프리셋 파일 위치 : `tools/ctrl_creator_presets.json`

---

### Feature 7 — Constraint to Joints (AS → MH)

AS `DeformationSystem` 조인트를 MH 조인트에 Constraint로 연결합니다.

- **parentConstraint + scaleConstraint** 동시 적용
- 기존 constraint가 있으면 재적용 전 자동 삭제
- **AS Namespace / MH Namespace** : 드롭다운으로 선택, Refresh로 자동 감지
- **Side Suffix** : 좌우 구분 문자열 (기본 Right=`r` / Left=`l`)
- **Revert** : 연결된 모든 constraint 삭제

---

### Feature 8 — Rig Cleanup

리그 최종 납품/배포 전 씬 정리 기능입니다.

#### Clean Scene *(비가역)*

| 순서 | 작업 |
|------|------|
| ① | 불필요한 Namespace 제거 (AS 관련 제외) |
| ② | Display Layer / Anim Layer 제거 |
| ③ | Unused Nodes 삭제 (`MLdeleteUnused`) |
| ④ | Unknown Plugin 제거 |

#### Build Rig Structure

씬 최상위 계층을 최종 납품 구조로 재편성합니다.

| 순서 | 작업 |
|------|------|
| ① | `root` 조인트를 world로 이동 (`joints_grp` 비움) |
| ② | 빈 `joints_grp` 삭제 |
| ③ | `Ch Name` 그룹 생성 (Outliner 색상 노란색) |
| ④ | `geo_grp` 생성 → `body_grp` / `head_grp` 이동 |
| ⑤ | `rig_grp` 생성 → `Group` 이동 / 빈 `rig` 삭제 |
| ⑥ | `Lights` 그룹 제거 |
| ⑦ | Animation Sets 계층 생성 |

```
Ch Name  (노란색)
├── geo_grp
│   ├── body_grp
│   └── head_grp
└── rig_grp
    └── Group  (AS 리그)
root  (world)
Sets
└── AniFBXSet
    └── AniOutSet
├── AssetFBX_Set
└── AnimControlSet
```

- **Revert** : Animation Sets 삭제 → root / body_grp / head_grp 원위치 →
  `geo_grp` / `rig_grp` / `Ch Name` 삭제 → `rig` / `joints_grp` 재생성

> **참고** : `AllSet`이 존재하면 `Sets`는 AdvancedSkeleton 원본으로 판단하여 Revert 시 삭제하지 않습니다.

---

### Build ALL / Revert ALL

| | 실행 순서 |
|-|-----------|
| **Build ALL** | Feature 1 → 2 → 3 → 4 → 5 → 6 → 7(NS 자동 감지) → Clean Scene → Build Rig Structure |
| **Revert ALL** | Revert Rig Structure → Revert Constraint → Revert Feature 5 → … → Revert Feature 1 |

---

## 7. 주의 사항

- **Clean Scene은 비가역**입니다. 실행 전 씬을 별도 저장해두는 것을 권장합니다.
- Feature 7의 Namespace는 Build ALL 실행 시 자동으로 감지(Refresh)됩니다.
  별도로 Refresh를 누르지 않아도 됩니다.
- `Ch Name` 필드는 기본값 `CH_NAME`이며, 실제 캐릭터 이름으로 변경 후 실행하세요.
- Revert ALL은 Build ALL의 역순으로 동작하나, **Clean Scene은 비가역이므로 복구되지 않습니다.**

---

## 8. Help 기능

모든 주요 버튼 오른쪽의 **`?`** 버튼을 클릭하면 해당 기능에 대한 설명 팝업이 표시됩니다.
처음 사용하거나 기능이 불명확할 때 활용하세요.
