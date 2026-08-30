# Maya Python3 Library - Refactored

Maya Python3 라이브러리의 리팩토링된 버전입니다. 범용성을 높이고 객체화가 가능한 요소들을 개선했습니다.

## 📁 구조

```
python3/
├── core/                    # 핵심 모듈
│   ├── __init__.py
│   ├── base_ui.py          # 베이스 UI 클래스
│   ├── maya_utils.py       # Maya 유틸리티 함수들
│   ├── config_manager.py   # 설정 관리자
│   └── logger.py           # 로깅 시스템
├── utils/                   # 유틸리티 모듈
│   ├── __init__.py
│   ├── naming_utils.py     # 네이밍 유틸리티
│   ├── transform_utils.py  # 트랜스폼 유틸리티
│   ├── constraint_utils.py # 컨스트레인트 유틸리티
│   └── skin_utils.py       # 스킨 유틸리티
├── refactored/              # 리팩토링된 스크립트들
│   ├── CNTManager3_refactored.py
│   └── MHADV3_refactored.py
└── logs/                    # 로그 파일들
```

## 🚀 주요 개선사항

### 1. **모듈화 및 재사용성**
- 공통 기능들을 `core` 모듈로 분리
- 중복 코드 제거 및 통합
- 객체지향 설계 적용

### 2. **베이스 클래스 시스템**
```python
# 상대 경로 import 사용 (python3 패키지 내부에서)
from ..core.base_ui import BaseMayaUI
from ..core.maya_utils import MayaUtils
from ..core.logger import ToolLogger

# 또는 절대 경로 import (외부에서)
from python3.core.base_ui import BaseMayaUI
from python3.core.maya_utils import MayaUtils
from python3.core.logger import ToolLogger

class MyTool(BaseMayaUI):
    def __init__(self, parent=None):
        super(MyTool, self).__init__(parent)
        self.logger = ToolLogger("MyTool")
        # 툴 초기화...
```

### 3. **통합 로깅 시스템**
```python
# 자동 로깅
self.logger.info("Operation started")
self.logger.log_operation_start("My Operation")
self.logger.log_operation_end("My Operation", success=True)
```

### 4. **설정 관리 시스템**
```python
from python3.core.config_manager import ConfigManager

config_manager = ConfigManager()
data = config_manager.load_json("config.json")
value = config_manager.get_config("config.json", "ui.size", default=100)
```

### 5. **유틸리티 함수들**
```python
from python3.utils.naming_utils import NamingUtils
from python3.utils.transform_utils import TransformUtils

# 네이밍 유틸리티
new_name = NamingUtils.generate_name_pattern("ctrl_##_L", 1)
unique_name = NamingUtils.get_unique_name("myObject")

# 트랜스폼 유틸리티
TransformUtils.reset_transform(obj)
TransformUtils.match_transform(source, target)
```

## 📋 사용법

### 기존 스크립트 업그레이드

1. **기존 코드:**
```python
import maya.cmds as cmds

def has_object(name):
    if cmds.objExists(name):
        return name
    return None

def transform_reset(obj):
    cmds.setAttr(f"{obj}.translate", 0, 0, 0)
    cmds.setAttr(f"{obj}.rotate", 0, 0, 0)
    cmds.setAttr(f"{obj}.scale", 1, 1, 1)
```

2. **리팩토링된 코드:**
```python
from python3.core.maya_utils import MayaUtils

# 간단한 사용
obj = MayaUtils.has_object(name)
MayaUtils.transform_reset(obj)
```

### 새로운 도구 개발

```python
from python3.core.base_ui import BaseMayaUI
from python3.core.maya_utils import MayaUtils
from python3.core.logger import ToolLogger
from python3.utils.naming_utils import NamingUtils

class MyNewTool(BaseMayaUI):
    def __init__(self, parent=None):
        super(MyNewTool, self).__init__(parent)
        self.logger = ToolLogger("MyNewTool")
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        # UI 설정
        pass
    
    def connect_signals(self):
        # 시그널 연결
        pass
    
    def my_operation(self):
        self.logger.log_operation_start("My Operation")
        try:
            # 작업 수행
            selection = MayaUtils.get_selection()
            for obj in selection:
                MayaUtils.transform_reset(obj)
            self.logger.log_operation_end("My Operation", True)
        except Exception as e:
            self.logger.error(f"Operation failed: {e}")
            self.logger.log_operation_end("My Operation", False)
```

## 🔧 설정 파일

### JSON 설정 파일 예시
```json
{
  "description": "MHADV3 Configuration",
  "NAME": {
    "ns": ["head", "body"],
    "headR": "head_rig",
    "bodyR": "body_rig"
  },
  "CTRLPOS": {
    "sub": [[0, 0, 0], [1, 0, 0]]
  },
  "COLOR": {
    "red": 13,
    "blue": 6
  }
}
```

## 📝 로깅

로그는 `logs/` 디렉토리에 자동으로 저장됩니다:
- 일별 로그 파일 생성
- 콘솔 및 파일 동시 출력
- 레벨별 로그 관리 (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## 🎯 주요 기능

### 1. **CNTManager3_refactored.py**
- 리팩토링된 컨스트레인트 매니저
- 개선된 에러 처리
- 통합 로깅 시스템
- 안전한 인덱스 접근

### 2. **MHADV3_refactored.py**
- 리팩토링된 메타휴먼 어드밴스드 도구
- 설정 관리 시스템 통합
- 모듈화된 기능들
- 향상된 에러 처리

### 3. **Core 모듈들**
- `BaseMayaUI`: 모든 UI 도구의 베이스 클래스
- `MayaUtils`: Maya 작업을 위한 공통 유틸리티
- `ConfigManager`: JSON 설정 파일 관리
- `MayaLogger`: 통합 로깅 시스템

### 4. **Utils 모듈들**
- `NamingUtils`: 네이밍 컨벤션 관리
- `TransformUtils`: 트랜스폼 관련 유틸리티
- `ConstraintUtils`: 컨스트레인트 유틸리티
- `SkinUtils`: 스킨 관련 유틸리티

## 🔄 마이그레이션 가이드

### 기존 스크립트를 리팩토링된 버전으로 업그레이드:

1. **Import 문 변경:**
```python
# 기존
import maya.cmds as cmds
from PySide2.QtWidgets import *

# 리팩토링된 버전
from python3.core.base_ui import BaseMayaUI
from python3.core.maya_utils import MayaUtils
from python3.core.logger import ToolLogger
```

2. **클래스 상속 변경:**
```python
# 기존
class MyTool(QWidget):
    def __init__(self):
        super(MyTool, self).__init__()

# 리팩토링된 버전
class MyTool(BaseMayaUI):
    def __init__(self, parent=None):
        super(MyTool, self).__init__(parent)
        self.logger = ToolLogger("MyTool")
```

3. **유틸리티 함수 사용:**
```python
# 기존
def has_object(name):
    if cmds.objExists(name):
        return name
    return None

# 리팩토링된 버전
obj = MayaUtils.has_object(name)
```

## 🚀 향후 계획

- [ ] 추가 유틸리티 모듈 개발
- [ ] 더 많은 기존 스크립트 리팩토링
- [ ] 단위 테스트 추가
- [ ] 문서화 개선
- [ ] 성능 최적화

## 📞 지원

문제가 발생하거나 개선 사항이 있으면 이슈를 등록해 주세요.






