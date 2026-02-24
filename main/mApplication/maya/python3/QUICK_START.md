# MH Tools Suite - 빠른 시작 가이드

## ⚡ 초간단 실행 방법

Maya scene에 이미 경로(`E:\script\pythonWorkSpace\main\mApplication\maya`)가 추가되어 있다면:

### 🌟 방법 1: 가장 짧은 방법
```python
from python3.tools.mh_tools_integrated import show
show()
```

### 🌟 방법 2: 리로드 포함 (권장)
```python
import importlib
from python3.tools import mh_tools_integrated
importlib.reload(mh_tools_integrated)
mh_tools_integrated.show()
```

### 🌟 방법 3: 런처 사용
```python
import python3
python3.launch_tools()
```

### 🌟 방법 4: 패키지 함수
```python
from python3.tools import show_integrated
show_integrated()
```

## 📝 개별 툴 실행

```python
from python3 import tools

tools.show_integrated()        # 통합 툴 (모든 기능)
tools.show_fbx_import()        # FBX Import만
tools.show_namespace_manager() # Namespace Manager만
tools.show_layer_manager()     # Layer Manager만
tools.show_scene_cleanup()     # Scene Cleanup만
tools.show_skin_copy()         # Skin Copy만
```

## 🔧 경로가 설정되지 않은 경우

```python
import sys
sys.path.append('E:/script/pythonWorkSpace/main/mApplication/maya')

# 이후 위의 방법 중 하나 사용
from python3.tools.mh_tools_integrated import show
show()
```

## 🎯 Maya Shelf 버튼 스크립트

Shelf 버튼에 추가할 최적의 스크립트:

```python
import importlib
from python3.tools import mh_tools_integrated
importlib.reload(mh_tools_integrated)
mh_tools_integrated.show()
```

## 💡 자동 경로 설정 (userSetup.py)

Maya 시작 시 자동으로 경로를 추가하려면 `userSetup.py`에 추가:

```python
# userSetup.py
import sys
path = 'E:/script/pythonWorkSpace/main/mApplication/maya'
if path not in sys.path:
    sys.path.append(path)
    print(f"Maya 경로 추가됨: {path}")
```

## 📋 포함된 기능

### MH Tools Integrated (통합 툴)
- **Tab 1: FBX Import** - FBX 파일 임포트
- **Tab 2: Managers** - Namespace & Layer 관리
- **Tab 3: MHC Cleanup** - 6가지 씬 정리 작업
  1. Joints 및 그룹 정리
  2. Head LOD 정리
  3. Facial 조인트 Constraint
  4. Lights 그룹 제거
  5. Delete Unused Nodes
  6. Create Animation Sets
- **Tab 4: Skin Copy** - 1:N, N:N 스킨 복사

## ✨ 핵심 정리

| 상황 | 명령어 |
|------|--------|
| **가장 빠른 실행** | `from python3.tools.mh_tools_integrated import show; show()` |
| **개발 중 (리로드 필요)** | `import importlib; from python3.tools import mh_tools_integrated; importlib.reload(mh_tools_integrated); mh_tools_integrated.show()` |
| **Shelf 버튼** | 위의 "개발 중" 명령어 사용 |
| **경로 추가 필요** | `import sys; sys.path.append('E:/script/pythonWorkSpace/main/mApplication/maya')` |

---

**🎉 이제 Maya에서 MH Tools를 사용할 준비가 되었습니다!**






