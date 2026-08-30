# Houdini MCP (Model Context Protocol) 연결 도구

Maya/Python 환경에서 후디니(Houdini)와 통신하기 위한 MCP 연결 도구입니다.

## 📋 목차

- [개요](#개요)
- [파일 구성](#파일-구성)
- [설치 및 설정](#설치-및-설정)
- [사용법](#사용법)
- [API 레퍼런스](#api-레퍼런스)
- [예제](#예제)
- [문제 해결](#문제-해결)

## 🎯 개요

이 도구는 소켓 통신을 통해 후디니와 Maya/Python 간의 실시간 통신을 가능하게 합니다.

**주요 기능:**
- 후디니에서 Python 코드 원격 실행
- 노드 생성, 수정, 조회
- 파라미터 설정 및 조회
- 선택된 노드 정보 가져오기
- Context Manager 지원

## 📁 파일 구성

```
python3/
├── houdini_mcp_server.py        # 후디니에서 실행하는 MCP 서버
├── houdini_mcp_connector.py     # Maya/Python에서 사용하는 클라이언트
├── houdini_mcp_quick_start.py   # 빠른 시작 가이드 및 테스트
└── HOUDINI_MCP_README.md        # 이 문서
```

## 🚀 설치 및 설정

### 1단계: 후디니에서 MCP 서버 시작

후디니를 실행하고 **Python Shell** 또는 **Python Source Editor**에서 다음을 실행하세요:

```python
import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from houdini_mcp_server import start_mcp_server

# 서버 시작 (기본: localhost:9876)
server = start_mcp_server()

# 또는 다른 포트 사용
# server = start_mcp_server(port=9999)
```

**서버 상태 확인:**
```python
from houdini_mcp_server import get_server_status
get_server_status()
```

**서버 중지:**
```python
from houdini_mcp_server import stop_mcp_server
stop_mcp_server()
```

### 2단계: Maya/Python에서 연결

Maya Script Editor 또는 Python 스크립트에서:

```python
import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from houdini_mcp_connector import HoudiniMCPConnector

# 연결 생성
connector = HoudiniMCPConnector()
connector.connect()

# 테스트
connector.test_connection()
```

## 💻 사용법

### 기본 사용

```python
from houdini_mcp_connector import HoudiniMCPConnector

# 연결 생성
connector = HoudiniMCPConnector()
connector.connect()

# 후디니에서 코드 실행
connector.execute_code("""
import hou
print(f"Houdini Version: {hou.applicationVersionString()}")
print(f"Current Frame: {hou.frame()}")
""")

# 연결 종료
connector.disconnect()
```

### Context Manager 사용

```python
from houdini_mcp_connector import HoudiniMCPConnector

with HoudiniMCPConnector() as connector:
    connector.execute_code("import hou; print(hou.hipFile.path())")
    # 자동으로 연결 종료됨
```

### 빠른 실행

```python
from houdini_mcp_connector import quick_execute

# 한 번의 호출로 실행 및 종료
result = quick_execute("""
import hou
for node in hou.selectedNodes():
    print(node.path())
""")
```

## 📚 API 레퍼런스

### HoudiniMCPConnector 클래스

#### 초기화

```python
connector = HoudiniMCPConnector(host='localhost', port=9876, timeout=10)
```

**파라미터:**
- `host` (str): 호스트 주소 (기본값: 'localhost')
- `port` (int): 포트 번호 (기본값: 9876)
- `timeout` (int): 연결 타임아웃 (초)

#### 주요 메서드

##### connect()
```python
success = connector.connect()
```
후디니 MCP 서버에 연결합니다.

**반환:** `bool` - 연결 성공 여부

---

##### disconnect()
```python
connector.disconnect()
```
연결을 종료합니다.

---

##### execute_code(code, print_output=True)
```python
result = connector.execute_code("""
import hou
print(hou.applicationVersionString())
""")
```

후디니에서 Python 코드를 실행합니다.

**파라미터:**
- `code` (str): 실행할 Python 코드
- `print_output` (bool): 출력을 자동으로 표시할지 여부

**반환:** `dict` - 실행 결과 (stdout, stderr 포함)

---

##### get_node_info(node_path)
```python
info = connector.get_node_info("/obj/geo1")
```

노드 정보를 가져옵니다.

**파라미터:**
- `node_path` (str): 노드 경로

**반환:** `dict` - 노드 정보

---

##### get_selection()
```python
selected = connector.get_selection()
```

현재 선택된 노드들을 가져옵니다.

**반환:** `list` - 선택된 노드 경로 리스트

---

##### create_node(parent_path, node_type, node_name=None)
```python
connector.create_node("/obj", "geo", "my_geometry")
```

새 노드를 생성합니다.

**파라미터:**
- `parent_path` (str): 부모 노드 경로
- `node_type` (str): 노드 타입
- `node_name` (str, optional): 노드 이름

**반환:** `dict` - 생성된 노드 정보

---

##### set_parameter(node_path, parm_name, value)
```python
connector.set_parameter("/obj/geo1", "tz", 5.0)
```

노드 파라미터를 설정합니다.

**파라미터:**
- `node_path` (str): 노드 경로
- `parm_name` (str): 파라미터 이름
- `value` (str/int/float): 설정할 값

**반환:** `dict` - 실행 결과

---

##### get_parameter(node_path, parm_name)
```python
value = connector.get_parameter("/obj/geo1", "tz")
```

노드 파라미터 값을 가져옵니다.

**파라미터:**
- `node_path` (str): 노드 경로
- `parm_name` (str): 파라미터 이름

**반환:** `dict` - 파라미터 값

---

##### test_connection()
```python
success = connector.test_connection()
```

연결을 테스트합니다.

**반환:** `bool` - 연결 성공 여부

---

### 편의 함수

##### quick_execute(code, host=None, port=None)
```python
from houdini_mcp_connector import quick_execute

result = quick_execute("import hou; print(hou.frame())")
```

빠른 코드 실행 (자동으로 연결 및 종료)

---

##### quick_connect_test(host=None, port=None)
```python
from houdini_mcp_connector import quick_connect_test

success = quick_connect_test()
```

빠른 연결 테스트

---

## 🔧 예제

### 예제 1: 기본 정보 가져오기

```python
from houdini_mcp_connector import HoudiniMCPConnector

with HoudiniMCPConnector() as connector:
    connector.execute_code("""
import hou

print(f"Houdini Version: {hou.applicationVersionString()}")
print(f"Hip File: {hou.hipFile.path()}")
print(f"Frame Range: {hou.playbar.frameRange()}")
print(f"Current Frame: {hou.frame()}")
print(f"FPS: {hou.fps()}")
""")
```

### 예제 2: 노드 생성 및 설정

```python
from houdini_mcp_connector import HoudiniMCPConnector

with HoudiniMCPConnector() as connector:
    # Geometry 노드 생성
    connector.create_node("/obj", "geo", "my_geo")
    
    # 위치 설정
    connector.set_parameter("/obj/my_geo", "tx", 0)
    connector.set_parameter("/obj/my_geo", "ty", 0)
    connector.set_parameter("/obj/my_geo", "tz", 5)
    
    # Box 노드 생성
    connector.create_node("/obj/my_geo", "box", "my_box")
    
    # Box 크기 설정
    connector.set_parameter("/obj/my_geo/my_box", "sizex", 2.0)
    connector.set_parameter("/obj/my_geo/my_box", "sizey", 2.0)
    connector.set_parameter("/obj/my_geo/my_box", "sizez", 2.0)
    
    print("✓ 노드 생성 완료!")
```

### 예제 3: 선택된 노드 처리

```python
from houdini_mcp_connector import HoudiniMCPConnector

with HoudiniMCPConnector() as connector:
    connector.execute_code("""
import hou

selected = hou.selectedNodes()

if not selected:
    print("선택된 노드가 없습니다.")
else:
    print(f"선택된 노드: {len(selected)}개")
    
    for node in selected:
        print(f"\\n노드: {node.path()}")
        print(f"  타입: {node.type().name()}")
        print(f"  위치: {node.position()}")
        
        # 파라미터 출력
        parms = node.parms()
        if parms:
            print(f"  파라미터: {len(parms)}개")
""")
```

### 예제 4: 네트워크 탐색

```python
from houdini_mcp_connector import HoudiniMCPConnector

with HoudiniMCPConnector() as connector:
    connector.execute_code("""
import hou

def print_node_tree(node, depth=0):
    indent = "  " * depth
    print(f"{indent}├─ {node.name()} ({node.type().name()})")
    
    for child in node.children():
        print_node_tree(child, depth + 1)

# /obj 하위 구조 출력
obj = hou.node("/obj")
print("Scene Network:")
print_node_tree(obj)
""")
```

### 예제 5: 파라미터 애니메이션

```python
from houdini_mcp_connector import HoudiniMCPConnector

with HoudiniMCPConnector() as connector:
    # 노드 생성
    connector.create_node("/obj", "geo", "animated_geo")
    
    # 애니메이션 키 설정
    connector.execute_code("""
import hou

node = hou.node("/obj/animated_geo")
parm = node.parm("ty")

# 키프레임 설정
parm.setKeyframe(hou.Keyframe(0, 1))   # 프레임 1에서 y=0
parm.setKeyframe(hou.Keyframe(5, 50))  # 프레임 50에서 y=5

print("✓ 애니메이션 키 설정 완료")
""")
```

### 예제 6: 일괄 노드 생성

```python
from houdini_mcp_connector import HoudiniMCPConnector

with HoudiniMCPConnector() as connector:
    # 여러 Geometry 노드 생성
    for i in range(5):
        node_name = f"geo_{i}"
        connector.create_node("/obj", "geo", node_name)
        connector.set_parameter(f"/obj/{node_name}", "tx", i * 3)
        print(f"✓ {node_name} 생성 완료")
```

## 🐛 문제 해결

### 연결 실패 (Connection Refused)

**증상:** `Connection refused` 에러 발생

**해결:**
1. 후디니가 실행 중인지 확인
2. 후디니에서 MCP 서버가 시작되었는지 확인
   ```python
   from houdini_mcp_server import get_server_status
   get_server_status()
   ```
3. 포트 번호가 일치하는지 확인 (기본: 9876)
4. 방화벽 설정 확인

---

### 타임아웃 에러

**증상:** `Connection timeout` 에러 발생

**해결:**
1. 후디니가 응답하는지 확인 (프로그램이 멈춰있지 않은지)
2. 타임아웃 시간 늘리기:
   ```python
   connector = HoudiniMCPConnector(timeout=30)
   ```
3. 네트워크 연결 확인

---

### 포트 충돌

**증상:** `Address already in use` 에러 발생

**해결:**
1. 다른 포트 사용:
   ```python
   # 후디니에서
   start_mcp_server(port=9999)
   
   # Maya/Python에서
   connector = HoudiniMCPConnector(port=9999)
   ```
2. 기존 서버 중지:
   ```python
   from houdini_mcp_server import stop_mcp_server
   stop_mcp_server()
   ```

---

### 코드 실행 오류

**증상:** 코드는 전송되지만 실행 오류 발생

**해결:**
1. 코드에 `import hou` 포함 확인
2. 노드 경로가 정확한지 확인
3. stderr 출력 확인:
   ```python
   result = connector.execute_code(code)
   if result:
       print("STDERR:", result.get('stderr'))
   ```

---

## 📝 추가 정보

### 지원 환경

- **후디니:** 18.5 이상
- **Python:** 3.7 이상
- **운영체제:** Windows, Linux, macOS

### 보안 고려사항

- MCP 서버는 localhost에서만 실행하는 것을 권장합니다
- 외부 네트워크에서 접근이 필요한 경우 방화벽 설정 필요
- 실행되는 코드는 제한 없이 실행되므로 주의 필요

### 성능 팁

- 대량의 데이터를 주고받을 때는 여러 번 호출보다 한 번에 처리
- Context Manager를 사용하여 자동 연결 종료
- 필요없는 출력은 `print_output=False` 설정

---

## 📞 문의

문제가 지속되거나 추가 기능이 필요한 경우 개발팀에 문의하세요.

---

**작성일:** 2025-12-23  
**버전:** 1.0.0  
**작성자:** SUNGSEO






