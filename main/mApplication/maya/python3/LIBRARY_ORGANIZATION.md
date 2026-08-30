# Python3 라이브러리 구조

정리 날짜: 2025-01-08
기준 날짜: 2025-12-08 이후 파일 백업

## 📁 디렉토리 구조

```
python3/
├── tools/                    # 운영 툴 (9개)
│   ├── mh_tools_integrated.py    # 통합 툴 (메인)
│   ├── fbx_import_tool.py
│   ├── namespace_manager_tool.py
│   ├── layer_manager_tool.py
│   ├── scene_cleanup_tool.py
│   ├── skin_copy_tool.py
│   ├── NToNSkinCopy.py
│   ├── oneToNSkinCopy.py
│   ├── createSets.py
│   └── reNamer.py
│
├── rigging/                  # 리깅 툴 (7개)
│   ├── FKIKSnapBakeTool.py
│   ├── customRiggingTool.py
│   ├── poseReaderV01_3.py
│   ├── ADVTwist.py
│   ├── jointSet.py
│   ├── vertex_reorder_tool.py
│   └── offset_.py
│
├── character/                # 캐릭터 툴 (7개)
│   ├── mh_body_transfer_manager.py
│   ├── MHADV3.py
│   ├── MHADV3_refactored.py
│   ├── CNTManager3.py
│   ├── CNTManager3_refactored.py
│   ├── CNTManager2_fixed.py
│   └── MconTool.py
│
├── houdini_integration/      # Houdini 연동 (10개)
│   ├── connect_to_houdini.py
│   ├── houdini_mcp_connector.py
│   ├── houdini_mcp_quick_start.py
│   ├── houdini_mcp_server.py
│   ├── houdini_multiparm_callback.py
│   ├── demo_houdini_control.py
│   ├── start_houdini_mcp_test.py
│   ├── parts_deform_sync_callback.py
│   ├── HOUDINI_MCP_QUICK_GUIDE.md
│   └── HOUDINI_MCP_README.md
│
├── archive/                  # 백업 파일 (121개)
│   ├── test_files/          # 테스트 파일 (28개)
│   ├── debug_files/         # 디버그 파일 (9개)
│   ├── check_files/         # 체크/검증 파일 (29개)
│   └── temp_files/          # 임시/설정 파일 (55개)
│
├── core/                     # 핵심 모듈 (유지)
├── utils/                    # 유틸리티 (유지)
├── icon/                     # 아이콘 (유지)
├── Json/                     # JSON 데이터 (유지)
├── MSTool/                   # MSTool (유지)
└── rigSupport/               # Rig Support (유지)
```

## 🔧 주요 툴 사용법

### 통합 툴 (MH Tools Suite)
```python
import importlib
import sys
sys.path.append('Z:/inhouse/Maya/scripts/2025/cosmos/scripts/python3/tools')

import mh_tools_integrated
importlib.reload(mh_tools_integrated)
mh_tools_integrated.show()
```

### 개별 툴 사용
```python
# FBX Import
from tools import fbx_import_tool
fbx_import_tool.show()

# Namespace Manager
from tools import namespace_manager_tool
namespace_manager_tool.show()

# Scene Cleanup
from tools import scene_cleanup_tool
scene_cleanup_tool.show()

# Skin Copy
from tools import skin_copy_tool
skin_copy_tool.show()
```

### 리깅 툴 사용
```python
from rigging import FKIKSnapBakeTool
from rigging import customRiggingTool
# 등등...
```

### 캐릭터 툴 사용
```python
from character import mh_body_transfer_manager
from character import MHADV3
# 등등...
```

## 📝 정리 내역

### 운영 툴 (tools/)
실제 작업에 사용하는 프로덕션 툴입니다.
- 통합 UI 툴
- FBX 관리
- 네임스페이스/레이어 관리
- 씬 정리
- 스킨 복사

### 리깅 툴 (rigging/)
리깅 작업에 필요한 툴들입니다.
- FK/IK 스냅/베이크
- 커스텀 리깅 툴
- 포즈 리더
- 조인트 관리
- 버텍스 리오더

### 캐릭터 툴 (character/)
캐릭터 관련 작업 툴들입니다.
- 바디 트랜스퍼 매니저
- MHADV (여러 버전)
- CNT 매니저 (여러 버전)
- MconTool

### Houdini 연동 (houdini_integration/)
Houdini와의 연동 관련 스크립트입니다.
- MCP 커넥터
- 멀티팜 콜백
- 파츠 디폼 싱크

### 백업 (archive/)
2025-12-08 이후 생성된 테스트/임시 파일들입니다.
- **test_files/** : test_*.py, final_test_*.py
- **debug_files/** : debug_*, diagnose_*, inspect_*, scan_*.py
- **check_files/** : check_*, verify_*, audit_*.py
- **temp_files/** : fix_*, update_*, setup_* 등 + 문서 파일

## 🔄 재정리가 필요할 때

```python
python organize_library.py
```

이 스크립트는:
1. 2025-12-08 이전 파일은 건드리지 않습니다
2. DRY RUN 모드로 먼저 시뮬레이션합니다
3. 확인 후 실제 이동을 실행할 수 있습니다

## 📌 주의사항

- `__init__.py`, `core/`, `utils/` 등 핵심 모듈은 그대로 유지됩니다
- MEL 스크립트(.mel)는 루트에 유지됩니다
- 2025-12-08 이전 생성/수정된 파일은 백업되지 않습니다
- 백업된 파일들은 필요시 archive/ 폴더에서 복구할 수 있습니다

## ✨ 정리 결과

- **총 154개 파일 정리**
  - Production Tools: 9개
  - Rigging Tools: 7개
  - Character Tools: 7개
  - Houdini Integration: 10개
  - Archive: 121개

이제 깔끔하게 정리된 라이브러리로 작업하실 수 있습니다!






