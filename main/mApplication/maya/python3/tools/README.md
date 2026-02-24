# MH Tools Suite

Maya 작업을 위한 통합 툴 모음

## 🚀 빠른 시작

### 방법 1: 가장 간단한 방법 (권장)
```python
# Maya Script Editor에서
import importlib
from python3.tools import mh_tools_integrated
importlib.reload(mh_tools_integrated)
mh_tools_integrated.show()
```

### 방법 2: 런처 사용
```python
from python3 import launch_mh_tools
launch_mh_tools.launch()
```

### 방법 3: 한 줄 실행
```python
from python3.tools.mh_tools_integrated import show; show()
```

### 방법 4: 패키지 편의 함수 사용
```python
from python3 import tools
tools.show_integrated()  # 통합 툴
```

## 📦 포함된 툴

### 1. MH Tools Integrated (통합 툴) ⭐
**모든 툴을 하나의 UI에 통합**

#### Tab 1: FBX Import
- FBX 파일 브라우저
- 간편한 임포트

#### Tab 2: Managers
- **Namespace Manager**: 네임스페이스 관리 및 삭제
- **Layer Manager**: Display Layer 관리 및 삭제

#### Tab 3: MHC Cleanup
1. Joints 및 그룹 정리
2. Head LOD 정리
3. Facial 조인트 Constraint 및 그룹핑
4. Lights 그룹 제거
5. Delete Unused Nodes & Plugins
6. Create Animation Sets

#### Tab 4: Skin Copy
- 1:N 모드 (하나의 소스 → 여러 타겟)
- N:N 모드 (여러 소스 → 여러 타겟)
- 다중 선택 지원
- 아웃라이너 동기화

### 2. 개별 툴

각 기능을 독립적으로 사용할 수도 있습니다:

```python
from python3 import tools

# 개별 툴 실행
tools.show_fbx_import()         # FBX Import
tools.show_namespace_manager()  # Namespace Manager
tools.show_layer_manager()      # Layer Manager
tools.show_scene_cleanup()      # Scene Cleanup
tools.show_skin_copy()          # Skin Copy
```

## 🛠️ 개발자용

### 리로드
개발 중 변경사항을 반영하려면:

```python
import importlib
from python3.tools import mh_tools_integrated
importlib.reload(mh_tools_integrated)
mh_tools_integrated.show()
```

### 경로 설정
만약 경로가 설정되지 않았다면:

```python
import sys
sys.path.append('Z:/inhouse/Maya/scripts/2025/cosmos/scripts')
```

## 📋 요구사항

- Maya 2020 이상
- Python 3.x
- Maya scene에 경로 추가: `Z:/inhouse/Maya/scripts/2025/cosmos/scripts`

## 📁 파일 구조

```
python3/tools/
├── __init__.py                  # 패키지 초기화
├── mh_tools_integrated.py       # 통합 툴 (메인)
├── fbx_import_tool.py
├── namespace_manager_tool.py
├── layer_manager_tool.py
├── scene_cleanup_tool.py
├── skin_copy_tool.py
├── NToNSkinCopy.py
├── oneToNSkinCopy.py
├── createSets.py
├── reNamer.py
└── README.md                    # 이 파일
```

## 💡 팁

### 빠른 액세스를 위한 Maya Shelf 버튼 만들기

1. Maya Shelf에서 새 버튼 생성
2. Python 스크립트 입력:

```python
import importlib
from python3.tools import mh_tools_integrated
importlib.reload(mh_tools_integrated)
mh_tools_integrated.show()
```

3. 아이콘 설정: `icon/` 폴더에서 선택

### userSetup.py에 추가
Maya 시작 시 자동으로 경로 추가:

```python
# userSetup.py
import sys
if 'Z:/inhouse/Maya/scripts/2025/cosmos/scripts' not in sys.path:
    sys.path.append('Z:/inhouse/Maya/scripts/2025/cosmos/scripts')
```

## 🐛 문제 해결

### Import Error
```python
# 경로 확인
import sys
print(sys.path)

# 경로 추가
sys.path.append('Z:/inhouse/Maya/scripts/2025/cosmos/scripts')
```

### 변경사항이 반영되지 않음
```python
# 모듈 리로드 필수
import importlib
importlib.reload(mh_tools_integrated)
```

## 📞 지원

문제나 제안사항이 있으면 팀에 문의하세요.

---

**버전**: 1.0  
**마지막 업데이트**: 2025-01-08  
**제작**: MH Team


