# Character 모듈 Import 가이드

## 📋 개요

Character 모듈(CNTManager3, MHADV3)을 Maya에서 올바르게 import하는 방법을 안내합니다.

---

## ✅ 올바른 Import 방법

### 방법 1: 권장 방법 (패키지를 통한 import)

```python
# Maya Script Editor
import sys
sys.path.append('E:/script/pythonWorkSpace/main/mApplication/maya')

import importlib
from python3.character import MHADV3
importlib.reload(MHADV3)
MHADV3.runWin()
```

```python
# CNTManager3의 경우
import sys
sys.path.append('E:/script/pythonWorkSpace/main/mApplication/maya')

import importlib
from python3.character import CNTManager3
importlib.reload(CNTManager3)
CNTManager3.runWin()
```

### 방법 2: 직접 클래스 import

```python
# Maya Script Editor
import sys
sys.path.append('E:/script/pythonWorkSpace/main/mApplication/maya')

from python3.character.MHADV3 import MHADV3
app = MHADV3()
app.runWin()
```

### 방법 3: 런처 사용 (가장 간단)

```python
# Maya Script Editor
import sys
sys.path.append('E:/script/pythonWorkSpace/main/mApplication/maya')

from python3 import launch_mh_tools
launch_mh_tools.launch()
```

---

## ❌ 잘못된 Import 방법

### 오류 1: 패키지 경로 누락
```python
# ❌ 잘못됨
from character import MHADV3
# ImportError: attempted relative import beyond top-level package

# ✅ 올바름
from python3.character import MHADV3
```

### 오류 2: 경로 설정 누락
```python
# ❌ 잘못됨 (경로 추가 안 함)
from python3.character import MHADV3
# ModuleNotFoundError: No module named 'python3'

# ✅ 올바름
import sys
sys.path.append('E:/script/pythonWorkSpace/main/mApplication/maya')
from python3.character import MHADV3
```

### 오류 3: 잘못된 경로
```python
# ❌ 잘못됨
sys.path.append('E:/script/pythonWorkSpace/main/mApplication/maya/python3')
from character import MHADV3  # 상대 import 문제 발생

# ✅ 올바름
sys.path.append('E:/script/pythonWorkSpace/main/mApplication/maya')
from python3.character import MHADV3
```

---

## 🔧 Import 문제 해결

### 문제: "attempted relative import beyond top-level package"

**원인**: 모듈이 상대 import(`..core`)를 사용하는데 top-level 패키지로 인식되지 않음

**해결책**: 
1. ✅ 올바른 패키지 경로 사용: `from python3.character import MHADV3`
2. ✅ 파일 수정 완료: try-except로 절대/상대 import 모두 지원

### 문제: "No module named 'python3'"

**원인**: sys.path에 올바른 경로가 추가되지 않음

**해결책**:
```python
import sys
sys.path.append('E:/script/pythonWorkSpace/main/mApplication/maya')
```

---

## 📝 Maya Shelf 버튼 스크립트

### MHADV3 Shelf 버튼
```python
import sys
import importlib

# 경로 추가
path = 'E:/script/pythonWorkSpace/main/mApplication/maya'
if path not in sys.path:
    sys.path.append(path)

# Import 및 실행
from python3.character import MHADV3
importlib.reload(MHADV3)
MHADV3.runWin()
```

### CNTManager3 Shelf 버튼
```python
import sys
import importlib

# 경로 추가
path = 'E:/script/pythonWorkSpace/main/mApplication/maya'
if path not in sys.path:
    sys.path.append(path)

# Import 및 실행
from python3.character import CNTManager3
importlib.reload(CNTManager3)
CNTManager3.runWin()
```

---

## 🚀 자동 경로 설정 (userSetup.py)

Maya 시작 시 자동으로 경로를 추가하려면:

**위치**: `Documents/maya/2024/scripts/userSetup.py` (버전에 맞게 수정)

```python
# userSetup.py
import sys

# Maya Python3 라이브러리 경로 추가
maya_lib_path = 'E:/script/pythonWorkSpace/main/mApplication/maya'
if maya_lib_path not in sys.path:
    sys.path.append(maya_lib_path)
    print(f"[Auto Setup] Maya 라이브러리 경로 추가: {maya_lib_path}")
```

이후 Maya 재시작 후 경로 추가 없이 바로 사용 가능:
```python
# userSetup.py로 경로가 추가되었으므로
from python3.character import MHADV3
MHADV3.runWin()
```

---

## 🔍 디버깅 팁

### 1. 경로 확인
```python
import sys
print(sys.path)
# 'E:/script/pythonWorkSpace/main/mApplication/maya'가 있는지 확인
```

### 2. 모듈 위치 확인
```python
from python3.character import MHADV3
print(MHADV3.__file__)
# 예상 출력: E:\script\pythonWorkSpace\main\mApplication\maya\python3\character\MHADV3.py
```

### 3. Import 에러 상세 확인
```python
import traceback
try:
    from python3.character import MHADV3
except Exception as e:
    print(traceback.format_exc())
```

---

## 📚 추가 정보

### 모듈 구조
```
python3/
├── __init__.py
├── character/
│   ├── __init__.py
│   ├── CNTManager3.py        # 상대/절대 import 모두 지원
│   ├── MHADV3.py             # 상대/절대 import 모두 지원
│   └── mh_body_transfer_manager.py
├── core/
│   ├── __init__.py
│   ├── base_ui.py
│   ├── maya_utils.py
│   ├── config_manager.py
│   └── logger.py
└── tools/
    └── ...
```

### Import 우선순위 (수정된 파일)

1. **절대 경로** 시도: `from python3.core import ...`
2. 실패 시 **상대 경로** 시도: `from ..core import ...`

이제 어떤 방식으로 import해도 작동합니다!

---

## ✨ 빠른 참조

| 상황 | 코드 |
|------|------|
| **스크립트 에디터** | `sys.path.append('...maya'); from python3.character import MHADV3` |
| **Shelf 버튼** | 위의 Shelf 버튼 스크립트 사용 |
| **userSetup.py** | 경로만 추가, 이후 `from python3.character import MHADV3` |
| **리로드** | `import importlib; importlib.reload(MHADV3)` |

---

## 🎉 문제 해결 완료!

- ✅ CNTManager3.py 수정 완료
- ✅ MHADV3.py 수정 완료
- ✅ 절대/상대 import 모두 지원
- ✅ Maya Script Editor에서 직접 실행 가능

**이제 `from python3.character import MHADV3`로 정상 작동합니다!** 🚀










