# Houdini MCP 빠른 사용 가이드

## 연결 완료! 🎉

후디니 MCP 서버와 성공적으로 연결되었습니다.

---

## 📝 빠른 시작

### 1. 기본 연결 테스트

```python
import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import test_houdini

# 연결 테스트
test_houdini()
```

### 2. 간단한 사용

```python
from connect_to_houdini import connect_houdini

# Context manager 사용 (권장)
with connect_houdini() as h:
    # 후디니 정보
    h.get_info()
    
    # 선택된 노드
    h.get_selected()
    
    # 코드 실행
    h.execute("print('Hello from Houdini!')")
```

---

## 🎯 주요 기능

### Geometry 노드 생성

```python
with connect_houdini() as h:
    # Geometry 노드 생성
    h.create_geo("my_geo")
    
    # Box 추가
    h.execute("""
geo = hou.node("/obj/my_geo")
box = geo.createNode("box", "my_box")
box.parm("sizex").set(2.0)
box.setDisplayFlag(True)
""")
```

### 노드 정보 조회

```python
with connect_houdini() as h:
    # 모든 obj 노드
    h.execute("""
for node in hou.node("/obj").children():
    print(f"{node.name()}: {node.type().name()}")
""")
```

### 파라미터 설정

```python
with connect_houdini() as h:
    h.execute("""
node = hou.node("/obj/geo1")
node.parm("tx").set(5.0)
node.parm("ty").set(3.0)
node.parm("tz").set(0.0)
""")
```

### 복잡한 작업

```python
with connect_houdini() as h:
    h.execute("""
# 여러 노드 생성
obj = hou.node("/obj")
for i in range(10):
    geo = obj.createNode("geo", f"sphere_{i}")
    geo.parm("tx").set(i * 2)
    
    sphere = geo.createNode("sphere")
    sphere.parm("rad").set(0.5 + i * 0.1)
    sphere.setDisplayFlag(True)

obj.layoutChildren()
print("Created 10 spheres!")
""")
```

---

## 🔧 고급 사용법

### 직접 커넥터 사용

```python
from houdini_mcp_connector import HoudiniMCPConnector

connector = HoudiniMCPConnector()
connector.connect()

# 코드 실행
result = connector.execute_code("""
import hou
print(hou.applicationVersionString())
""")

# 노드 생성
connector.create_node("/obj", "geo", "my_geometry")

# 파라미터 설정
connector.set_parameter("/obj/my_geometry", "ty", 5.0)

connector.disconnect()
```

### 선택 노드 처리

```python
with connect_houdini() as h:
    h.execute("""
# 선택된 노드의 파라미터 변경
for node in hou.selectedNodes():
    if node.parm("scale"):
        node.parm("scale").set(2.0)
    print(f"Modified: {node.path()}")
""")
```

### 애니메이션 키프레임

```python
with connect_houdini() as h:
    h.execute("""
node = hou.node("/obj/geo1")
parm = node.parm("ty")

# 키프레임 설정
parm.setKeyframe(hou.Keyframe(0, 1))    # Frame 1: y=0
parm.setKeyframe(hou.Keyframe(5, 50))   # Frame 50: y=5
parm.setKeyframe(hou.Keyframe(-5, 100)) # Frame 100: y=-5

print("Animation keys set!")
""")
```

---

## 📁 파일 구성

- **`connect_to_houdini.py`** - 간단한 인터페이스
- **`houdini_mcp_connector.py`** - 전체 기능 라이브러리
- **`demo_houdini_control.py`** - 데모 예제
- **`HOUDINI_MCP_README.md`** - 상세 문서

---

## 🚀 실용 예제

### 예제 1: 씬 정리

```python
with connect_houdini() as h:
    h.execute("""
# 모든 geo 노드 정리
obj = hou.node("/obj")
geo_nodes = [n for n in obj.children() if n.type().name() == "geo"]

print(f"Found {len(geo_nodes)} geometry nodes")

# Y축 간격으로 정렬
for i, geo in enumerate(geo_nodes):
    geo.parm("ty").set(i * 3)
    
obj.layoutChildren()
""")
```

### 예제 2: 벌크 생성

```python
with connect_houdini() as h:
    h.execute("""
# 그리드 형태로 노드 생성
obj = hou.node("/obj")
grid_size = 5

for x in range(grid_size):
    for z in range(grid_size):
        geo = obj.createNode("geo", f"grid_{x}_{z}")
        geo.parm("tx").set(x * 2)
        geo.parm("tz").set(z * 2)
        
        box = geo.createNode("box")
        box.parm("sizey").setExpression("rand($F) * 2 + 1")
        box.setDisplayFlag(True)

print(f"Created {grid_size * grid_size} nodes in grid pattern")
""")
```

### 예제 3: 씬 분석

```python
with connect_houdini() as h:
    h.execute("""
# 씬 통계
obj = hou.node("/obj")
stats = {
    "total": len(obj.children()),
    "geo": 0,
    "camera": 0,
    "light": 0,
    "subnet": 0,
    "other": 0
}

for node in obj.children():
    type_name = node.type().name()
    if type_name == "geo":
        stats["geo"] += 1
    elif type_name.startswith("cam"):
        stats["camera"] += 1
    elif "light" in type_name:
        stats["light"] += 1
    elif type_name == "subnet":
        stats["subnet"] += 1
    else:
        stats["other"] += 1

print("Scene Statistics:")
for key, value in stats.items():
    print(f"  {key}: {value}")
""")
```

---

## 💡 팁과 트릭

### 1. 에러 처리

```python
with connect_houdini() as h:
    result = h.execute("""
try:
    node = hou.node("/obj/nonexistent")
    if node:
        print(node.path())
    else:
        print("Node not found")
except Exception as e:
    print(f"Error: {e}")
""")
```

### 2. 성능 최적화

한 번의 `execute()` 호출에 여러 작업을 포함하는 것이 효율적입니다:

```python
# 좋음 - 한 번에 실행
with connect_houdini() as h:
    h.execute("""
for i in range(100):
    node = hou.node("/obj").createNode("geo", f"geo_{i}")
    node.parm("tx").set(i)
""")

# 나쁨 - 여러 번 실행 (느림)
with connect_houdini() as h:
    for i in range(100):
        h.execute(f"""
node = hou.node("/obj").createNode("geo", "geo_{i}")
node.parm("tx").set({i})
""")
```

### 3. 결과 캡처

```python
with connect_houdini() as h:
    result = h.connector.execute_code("""
import hou
nodes = [n.name() for n in hou.node("/obj").children()]
print("\\n".join(nodes))
""", print_output=False)
    
    # stdout에서 노드 이름 가져오기
    if result:
        node_names = result['stdout'].strip().split('\n')
        print(f"Found {len(node_names)} nodes")
```

---

## ❓ 문제 해결

### 연결 안 됨
```python
# 서버 상태 확인 (후디니에서)
import houdinimcp
houdinimcp.get_server_status()

# 서버 재시작
houdinimcp.stop_server()
houdinimcp.start_server()
```

### 명령 실행 안 됨
- `import hou` 포함 확인
- 노드 경로 확인
- stderr 출력 확인

---

## 📚 추가 리소스

- **전체 API 문서**: `HOUDINI_MCP_README.md`
- **데모 스크립트**: `demo_houdini_control.py`
- **Houdini Python 문서**: https://www.sidefx.com/docs/houdini/hom/

---

**작성일**: 2025-12-23  
**상태**: ✅ 연결 및 테스트 완료






