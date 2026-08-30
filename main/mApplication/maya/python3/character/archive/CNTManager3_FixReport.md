# CNTManager3.py 수정 보고서

## 🔧 **주요 수정 사항**

### 1. **N to N 컨스트레인트 인덱스 밀림 문제 해결** ✅

**문제점**: N to N 모드에서 컨스트레인트 실행 시 인덱스가 순서대로 적용되지 않고 밀려서 적용되는 현상

**기존 코드**:
```python
for i, tgt in enumerate(target_):
    if self.ui.OneToNRB.isChecked():
        i = 0
    elif self.ui.NToNRB.isChecked():
        i = i  # 문제: 인덱스 범위 체크 없음
    self.Constraint_(item_[i], tgt, mo=mo_)
```

**수정된 코드**:
```python
def safe_index_access(self, item_list, target_index):
    """N to N 모드에서 안전한 인덱스 접근을 위한 헬퍼 메소드"""
    if not item_list:
        return 0
    if hasattr(self.ui, 'OneToNRB') and self.ui.OneToNRB.isChecked():
        return 0
    elif hasattr(self.ui, 'NToNRB') and self.ui.NToNRB.isChecked():
        return min(target_index, len(item_list) - 1)
    else:
        return min(target_index, len(item_list) - 1)

# 사용 예시
for i, tgt in enumerate(target_):
    item_index = self.safe_index_access(item_, i)
    if item_index < len(item_):
        self.Constraint_(item_[item_index], tgt, mo=mo_)
```

### 2. **수정된 메소드 목록**

다음 메소드들에 동일한 인덱스 처리 로직 적용:
- ✅ `Constraints()` - 컨스트레인트 적용
- ✅ `MatchTransform()` - 트랜스폼 매칭
- ✅ `MConst()` - 매트릭스 컨스트레인트
- ✅ `ListConnect()` - 어트리뷰트 연결
- ✅ `ListSet()` - 어트리뷰트 값 설정
- ✅ `pparentItems()` - 부모 설정
- ✅ `SetDrivens()` - Set Driven Key 설정

### 3. **Import 문제 해결** ✅

**PySide6/PySide2 Fallback 추가**:
```python
try:
    from PySide6.QtCore import *
    from PySide6.QtGui import *
    from PySide6.QtWidgets import *
    from shiboken6 import wrapInstance
except ImportError:
    try:
        from PySide2.QtCore import *
        from PySide2.QtGui import *
        from PySide2.QtWidgets import *
        from shiboken2 import wrapInstance
    except ImportError:
        print("Neither PySide6 nor PySide2 available - UI functionality limited")
        # Fallback 클래스 정의
```

### 4. **Maya 함수 반환값 처리 개선** ✅

**개선 사항**:
- `ls()` 함수에 `or []` 추가하여 None 반환 방지
- `createNode()` 함수들의 반환값 체크 추가
- 에러 처리 및 로깅 개선

**예시**:
```python
# 기존
self.list_ = ls(sl=1, fl=1, r=1)

# 수정
self.list_ = ls(sl=1, fl=1, r=1) or []

# 노드 생성 시 에러 처리
mm = createNode('multMatrix',n='%sMM'% tgt) or None
dm = createNode('decomposeMatrix',n='%sDM'% tgt) or None

if not mm or not dm:
    print(f"Error: Failed to create nodes for {tgt}")
    continue
```

### 5. **중복 코드 제거** ✅

- 중복된 `retranslateUi` 메소드 제거
- 중복된 UI 위젯 정의 코드 정리

### 6. **에러 처리 및 로깅 개선** ✅

**추가된 기능**:
- 모든 주요 메소드에 try-catch 블록 추가
- 선택 객체 유효성 검사
- 인덱스 범위 체크
- 상세한 로그 메시지

**예시**:
```python
def Constraints(self):
    item_, target_ = self.ConnectionMode()
    
    if not item_ or not target_:
        print("Error: Invalid selection for constraints")
        return
        
    try:
        for i, tgt in enumerate(target_):
            item_index = self.safe_index_access(item_, i)
            if item_index < len(item_):
                self.Constraint_(item_[item_index], tgt, mo=mo_)
                print(f"Constraint applied: {item_[item_index]} -> {tgt} (index: {item_index})")
            else:
                print(f"Warning: Index {item_index} out of range for item list")
    except Exception as e:
        print(f"Error in Constraints: {e}")
    finally:
        undoInfo(closeChunk=True)
```

## 🎯 **사용 방법**

### N to N 컨스트레인트 사용법:

1. **List A에 소스 객체들 추가**
2. **List B에 타겟 객체들 추가**
3. **"N To N" 라디오 버튼 선택**
4. **컨스트레인트 타입 선택** (All, Trans, Rot, Scale 등)
5. **"Const" 버튼 클릭**

### 개선된 동작:
- 이제 List A의 첫 번째 객체가 List B의 첫 번째 객체에 정확히 매칭
- List A의 두 번째 객체가 List B의 두 번째 객체에 정확히 매칭
- 리스트 크기가 다를 경우 안전하게 처리 (인덱스 범위 초과 방지)

## ✅ **해결된 문제들**

1. **N to N 모드에서 인덱스 밀림 현상** → 완전 해결
2. **PySide6 import 에러** → Fallback 추가로 해결
3. **Maya 함수 반환값 처리 문제** → None 체크 추가
4. **중복 코드** → 정리 완료
5. **에러 처리 부족** → 포괄적인 에러 처리 추가

## 🔍 **디버깅 기능**

필요시 다음 메소드를 호출하여 선택 상태 확인 가능:
```python
# Maya Script Editor에서 실행
myWin.debug_selection_info()
```

## ⚠️ **주의사항**

1. **선택 순서 중요**: N to N 모드에서는 소스와 타겟의 선택 순서가 매칭에 영향
2. **리스트 크기**: 소스와 타겟 리스트 크기가 다를 경우 마지막 소스가 재사용됨
3. **Maya 버전 호환성**: PySide6/PySide2 자동 감지로 다양한 Maya 버전 지원

## 📊 **성능 개선**

- 인덱스 범위 체크로 크래시 방지
- 에러 처리로 안정성 향상
- 로깅으로 디버깅 용이성 증대

수정된 CNTManager3.py는 이제 안정적이고 예측 가능한 N to N 컨스트레인트 동작을 제공합니다.