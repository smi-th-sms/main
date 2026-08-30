# 라이브러리 통합 정리 요약

## 날짜: 2026-01-30

## 개요
`ms_module/maya/python3/rigSupport/` 디렉토리의 스크립트들을 `maya/python3/`로 통합 정리했습니다.

---

## 통합된 구조

### 📁 새로 생성된 디렉토리

#### 1. `python3/libs/` - 저수준 리깅 라이브러리
rigSupport/lib/의 98개 파일을 기능별로 분류하여 정리

```
libs/
├── __init__.py
├── constraints/           # 컨스트레인트 관련 (5개)
│   ├── _matrix.py
│   ├── QuatMatrixConst.py
│   ├── pairblendRotate.py
│   ├── constToMCon.py
│   └── _offsetParentMatrix.py
│
├── rigging/              # 리깅 셋업 (28개)
│   ├── arm.py, spine.py, spine2_.py, spine_.py
│   ├── foot.py, finger.py, fingerAttr.py, fingerCnt.py, fingerSub.py
│   ├── QArm.py, FKCtrl.py, IKCtrl.py
│   ├── FKIKBlend.py, IKFKBlend.py, FKIKSnap.py
│   ├── IKStSq.py, IKStSq2.py
│   ├── hybridSet.py, mainSet.py, stretchSet.py, attachSet.py
│   ├── bendSetup.py, eyeRigIng.py, eyePoser.py
│   ├── Follow.py, Arc.py, rope.py
│   └── corrJointSet.py
│
├── skinning/             # 스킨 관련 (3개)
│   ├── MFnSkinCluster_.py
│   ├── 1ToNBind.py
│   └── uvMapTransfer.py
│
├── controls/             # 컨트롤 관련 (3개)
│   ├── buildCtrl.py
│   ├── _control.py
│   └── control__.py
│
├── joints/               # 조인트 관련 (9개)
│   ├── _joint.py, _jointLabel.py, _jointOrient.py
│   ├── jointAtSelection.py, linearJoint.py
│   ├── joint_transfer.py, joint_transfer2.py, joint_transfer3.py
│   └── CvToCrvParamJoint.py
│
├── transforms/           # 트랜스폼 관련 (4개)
│   ├── _transform.py
│   ├── reTransform.py
│   ├── resetOffsetParentMatrix_.py
│   └── duplicateTarget.py
│
├── curves/               # 커브 관련 (4개)
│   ├── _curve.py
│   ├── dynCrv_.py
│   ├── curl_lerp.py
│   └── flcOutCrvSort.py
│
├── metahuman/            # 메타휴먼 lib (3개)
│   ├── metahuman_adv_set.py
│   ├── metahuman_build.py
│   └── metahuman_head_rebind.py
│
└── [기타 유틸리티 파일들] (37개)
    ├── _attribute.py, _check.py, _config.py, _connect.py
    ├── _name.py, _node.py, _pole.py, _pole02.py, _pole03.py
    ├── _quaternion.py, _shapeChange.py, _mirror.py
    ├── _hair.py, _dir_.py
    ├── aimMatrix.py, aimSet.py, alembic_export.py
    ├── config.py, dna_viewer.py, groomAddAttr.py, hairDyn.py
    ├── insertRvs.py, ModuleConnection.py, mpIK.py
    ├── MVConvertQuadMesh.py, offsetGroup.py, rebuild.py
    ├── referenceDelete.py, reName.py, reNamer01.py
    ├── setdriven_.py, surfaceAtObject.py, surfaceParam.py
    ├── UERBFSolverNodeQuary.py, undoTest.py
    ├── vaccine_gene.py, Vector.py
    └── advTpose.py
```

#### 2. `python3/character/metahuman/` - 메타휴먼 도구
rigSupport/cinematic/의 메타휴먼 관련 스크립트 통합

```
character/
├── metahuman/
│   ├── __init__.py
│   ├── MHADV3.py                    # Advanced Rigging
│   ├── MHBuild_01.py                # Build Tools
│   ├── MHBodyRigReConst.py          # Body Rig Reconstruction
│   ├── advSpineFix.py               # Spine Fix
│   ├── bbtransfer.py                # Body Transfer
│   ├── ikfkHybridRig.py             # IK/FK Hybrid
│   ├── createSets.py                # Create Sets
│   ├── MHSkeletonFile.py            # Skeleton File
│   ├── transfer_vertex_reorder.py   # Vertex Reorder
│   └── tfjoint/                     # Transform Match Tools
│       ├── __init__.py
│       ├── MHBodyTFUI.py
│       ├── tfMatch_arm.py
│       ├── tfMatch_body.py
│       ├── tfMatch_arm_leg_spine.py
│       ├── tfMatch_final.py
│       ├── transMatchTool.py
│       ├── transMatchBakeTool.py
│       ├── Step1.py, Step2.py, Step3.py
│       └── Joint_Pca_Alignment00/01/02.py
│
└── MconTool.py                      # rigSupport/ui/deliver에서 이동
```

#### 3. `python3/rigging/classes/` - 리깅 클래스
rigSupport/class/의 리깅 클래스 파일들

```
rigging/classes/
├── __init__.py
├── classHardCording.py
├── renamer.py
├── rigClass01_ctrl_offset.py
├── rigClass01_fkik.py
└── rigClass01_jointOrieng_getset.py
```

#### 4. `python3/data/` - 데이터 및 설정
rigSupport/dictLib/와 JSON 파일들 통합

```
data/
├── __init__.py
└── dictionaries/
    ├── __init__.py
    ├── skeleton.py
    └── _shape_dic.py
```

---

## 기존 디렉토리에 통합된 파일

### `python3/Json/` - JSON 설정 파일 추가
- rigSupport/cinematic/Json/ → Json/
- rigSupport/lib/*.json → Json/
  - aim_dict.json
  - configDict.json
  - exclude_rules.json
  - MHADVJS.json
  - blendshapeDict.json
  - BuildInfo.json
  - ConnectionInfo.json
  - jointOrientDict.json

### `maya/rigLib/` - Maya 리깅 파일 통합
- rigSupport/rig/fits/*.ma → rigLib/
- rigSupport/rig/sets/*.ma, *.mb → rigLib/

---

## 중복 파일 처리

### 유지된 파일 (최신 버전 또는 사용 중)
1. **CNTManager3.py** - `character/` (20250101) ✅
   - rigSupport의 CNTManager2.py는 구버전

2. **MHADV3.py** - `character/` (20250101) ✅
   - rigSupport의 MHADV.py는 구버전 (20240206)

3. **mh_body_transfer_manager.py** - `character/` (최신) ✅
   - rigSupport의 동일 파일은 구버전

4. **reNamer.py** - `tools/` (20240827) ✅
   - rigSupport 버전도 동일하지만 tools에 유지

5. **jointSet.py** - `rigging/` (20210430) ✅
   - rigSupport 버전과 동일하지만 rigging에 유지

---

## 제거된 항목

### ❌ `rigSupport/cosmos/` - 삭제
- 34개의 Cosmos 액션 파일
- 사용하지 않음으로 확인되어 제거

### ❌ `rigSupport/ui/convert/` - 향후 archive 검토
- 구버전 UI 변환 파일들
- 필요시 archive로 이동

### ❌ `rigSupport/.qt_for_python/` - 삭제 검토
- Qt UI 임시 파일들

---

## 최종 python3 디렉토리 구조

```
python3/
├── archive/              # 구버전 코드
├── character/            # 캐릭터 도구
│   ├── CNTManager3.py
│   ├── MHADV3.py
│   ├── mh_body_transfer_manager.py
│   ├── MconTool.py       # 새로 추가 ✨
│   └── metahuman/        # 새로 추가 ✨
│       ├── MHADV3.py, MHBuild_01.py, etc.
│       └── tfjoint/
├── core/                 # 공통 베이스 클래스
├── cosmos/               # Cosmos 액션 (기존 유지)
├── data/                 # 새로 추가 ✨
│   └── dictionaries/
├── Json/                 # JSON 설정 (통합 완료)
├── libs/                 # 새로 추가 ✨ (98개 파일)
│   ├── constraints/
│   ├── rigging/
│   ├── skinning/
│   ├── controls/
│   ├── joints/
│   ├── transforms/
│   ├── curves/
│   └── metahuman/
├── logs/                 # 로그 파일
├── rigging/              # 리깅 도구
│   ├── classes/          # 새로 추가 ✨
│   └── ...
├── tools/                # 통합 도구
└── utils/                # 유틸리티
```

---

## 다음 단계

### ⚠️ 중요: Import 경로 수정 필요

이동된 파일들을 사용하는 스크립트의 import 경로를 업데이트해야 합니다:

**변경 전:**
```python
from rigSupport.lib import _matrix
from rigSupport.lib import buildCtrl
from rigSupport.cinematic import MHADV3
from rigSupport.ui.deliver import MconTool
```

**변경 후:**
```python
from python3.libs.constraints import _matrix
from python3.libs.controls import buildCtrl
from python3.character.metahuman import MHADV3
from python3.character import MconTool
```

### 테스트 필요 항목

1. ✅ CNTManager3.py - 이미 테스트 완료
2. ⏳ MconTool.py - import 경로 확인 필요
3. ⏳ character/metahuman/ 도구들
4. ⏳ libs/ 라이브러리 함수들

---

## 통계

- **이동된 Python 파일**: 약 174개
- **이동된 Maya 파일**: 약 30개 (.ma/.mb)
- **이동된 JSON 파일**: 약 8개
- **새로 생성된 디렉토리**: 13개
- **새로 생성된 __init__.py**: 13개

---

## 참고사항

1. **백업**: 원본 rigSupport 디렉토리는 유지 (삭제하지 않음)
2. **점진적 마이그레이션**: 기존 코드는 그대로 두고 새 경로로 점진적 이동
3. **하위 호환성**: 당분간 두 경로 모두 유지 가능
4. **문서화**: 각 디렉토리의 __init__.py에 용도 명시

---

## 작성자
- SUNGSEO (통합 작업)
- 날짜: 2026-01-30





