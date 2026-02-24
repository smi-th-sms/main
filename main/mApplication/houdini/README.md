# Houdini Integration Package

Houdini와의 통합 및 연동을 위한 Python 패키지입니다.

## 📁 패키지 구조

```
houdini/
├── __init__.py              # 패키지 초기화 및 편의 함수
├── README.md                # 본 문서
│
├── mcp/                     # MCP (Model Context Protocol) 모듈
│   ├── __init__.py
│   ├── houdini_mcp_server.py          # Houdini에서 실행하는 서버
│   ├── houdini_mcp_connector.py       # Maya/Python 클라이언트
│   ├── connect_to_houdini.py          # 간편 연결 유틸리티
│   ├── quick_connect.py               # 빠른 연결 스크립트
│   ├── houdini_mcp_quick_start.py     # 빠른 시작 가이드
│   ├── houdini_multiparm_callback.py  # Multiparm 콜백
│   ├── parts_deform_sync_callback.py  # Parts Deform 동기화
│   └── start_houdini_mcp_test.py      # MCP 테스트
│
├── utils/                   # 유틸리티 스크립트
│   ├── __init__.py
│   ├── analyze_wrangle_nodes.py       # Wrangle 노드 분석
│   ├── check_kinefx_shelf.py          # KineFX Shelf 체크
│   ├── check_node.py                  # 노드 체크
│   ├── check_wrangle_error.py         # Wrangle 에러 체크
│   ├── demo_houdini_control.py        # Houdini 제어 데모
│   ├── diagnose_curve_to_joints.py    # Curve to Joints 진단
│   ├── diagnose_houdini_pyside.py     # PySide 진단
│   ├── find_curve_solver.py           # Curve Solver 찾기
│   ├── rename_bones.py                # Bone 이름 변경
│   ├── reverse_curve_points.py        # Curve Point 역순
│   ├── setup_bone_hierarchy.py        # Bone 계층 구조 설정
│   ├── test_connection.py             # 연결 테스트
│   └── verify_paths_in_houdini.py     # 경로 검증
│
└── docs/                    # 문서
    ├── HOUDINI_MCP_README.md          # MCP 상세 문서
    ├── HOUDINI_MCP_QUICK_GUIDE.md     # MCP 빠른 가이드
    ├── CURRENT_WORK_SUMMARY.md        # 작업 요약
    ├── add_connection_vertex.md       # Connection Vertex 추가
    ├── debug_reverse_issue.md         # Reverse 이슈 디버그
    ├── final_point_reorder_solution.md
    ├── point_reorder_solution.md
    ├── point_reorder_with_switch.md
    ├── reverse_with_both_groups.md
    ├── reverse_with_group_method.md
    ├── reverse_with_prim_group.md
    └── verify_point_order.md
```

---

## 🚀 빠른 시작

### 1. 경로 추가

```python
import sys
sys.path.append('E:/script/pythonWorkSpace/main/mApplication')
```

### 2. Houdini에서 MCP 서버 시작

Houdini Python Shell에서 실행:

```python
from houdini.mcp.houdini_mcp_server import start_mcp_server

# 서버 시작 (기본: localhost:9876)
server = start_mcp_server()
```

### 3. Maya/Python에서 연결

```python
# 방법 1: 간편 연결
from houdini import connect

hou = connect()
result = hou.execute_code("print(hou.pwd())")
print(result)

# 방법 2: 클래스 직접 사용
from houdini import HoudiniMCPConnector

connector = HoudiniMCPConnector()
connector.connect()
result = connector.execute_code("print(hou.node('/obj'))")
print(result)
```

---

## 📚 주요 기능

### MCP (Model Context Protocol)

Houdini와 Maya/Python 간의 실시간 통신을 제공합니다.

#### 주요 메서드:

```python
# 연결
connector.connect()

# Python 코드 실행
result = connector.execute_code("print(hou.pwd())")

# 노드 생성
connector.create_node('geo', 'my_geo')

# 파라미터 설정
connector.set_parameter('/obj/my_geo', 'tx', 5.0)

# 선택된 노드 조회
nodes = connector.get_selected_nodes()

# 연결 종료
connector.disconnect()
```

#### Context Manager 지원:

```python
from houdini import HoudiniMCPConnector

with HoudiniMCPConnector() as hou:
    result = hou.execute_code("print(hou.node('/obj'))")
    print(result)
# 자동으로 연결 종료됨
```

---

## 🔧 유틸리티 스크립트

### KineFX 관련

- `check_kinefx_shelf.py` - KineFX Shelf 도구 확인
- `setup_bone_hierarchy.py` - Bone 계층 구조 자동 설정
- `rename_bones.py` - Bone 이름 일괄 변경

### Curve 처리

- `diagnose_curve_to_joints.py` - Curve to Joints 변환 진단
- `reverse_curve_points.py` - Curve Point 순서 역전
- `find_curve_solver.py` - Curve Solver 노드 찾기

### Wrangle 노드

- `analyze_wrangle_nodes.py` - Wrangle 노드 코드 분석
- `check_wrangle_error.py` - Wrangle 에러 체크

### 기타

- `check_node.py` - 노드 상태 확인
- `test_connection.py` - MCP 연결 테스트
- `demo_houdini_control.py` - Houdini 원격 제어 데모

---

## 📖 상세 문서

- **[HOUDINI_MCP_README.md](docs/HOUDINI_MCP_README.md)** - MCP 상세 사용법
- **[HOUDINI_MCP_QUICK_GUIDE.md](docs/HOUDINI_MCP_QUICK_GUIDE.md)** - 빠른 시작 가이드
- **[CURRENT_WORK_SUMMARY.md](docs/CURRENT_WORK_SUMMARY.md)** - 최근 작업 내역

---

## 💡 사용 예제

### 예제 1: 노드 생성 및 파라미터 설정

```python
from houdini import connect

hou = connect()

# Geometry 노드 생성
hou.create_node('geo', 'my_geometry')

# Box 노드 생성
hou.execute_code("""
geo = hou.node('/obj/my_geometry')
box = geo.createNode('box', 'my_box')
box.parm('sizex').set(2.0)
box.parm('sizey').set(2.0)
box.parm('sizez').set(2.0)
""")

print("Box 노드 생성 완료!")
```

### 예제 2: 선택된 노드 정보 가져오기

```python
from houdini import connect

hou = connect()

# 선택된 노드 조회
nodes = hou.get_selected_nodes()
print(f"선택된 노드: {nodes}")

# 각 노드의 파라미터 출력
for node in nodes:
    result = hou.execute_code(f"""
node = hou.node('{node}')
parms = {{p.name(): p.eval() for p in node.parms()}}
print(parms)
""")
    print(f"{node} 파라미터: {result}")
```

### 예제 3: KineFX Bone 설정

```python
from houdini import connect

hou = connect()

# Bone 계층 구조 생성
hou.execute_code("""
import hou

# KineFX 노드 생성
obj = hou.node('/obj')
geo = obj.createNode('geo', 'rig')

# Bone 생성
bones = []
for i in range(5):
    bone = geo.createNode('null', f'bone_{i}')
    bone.parm('ty').set(i * 2)
    bones.append(bone)

# 계층 구조 설정
for i in range(1, len(bones)):
    bones[i].setInput(0, bones[i-1])

print("Bone 계층 구조 생성 완료!")
""")
```

---

## 🔗 관련 링크

- [Houdini Python Documentation](https://www.sidefx.com/docs/houdini/hom/)
- [KineFX Documentation](https://www.sidefx.com/docs/houdini/character/kinefx/)

---

## 📝 버전 정보

- **버전**: 1.0.0
- **작성자**: SUNGSEO
- **최종 업데이트**: 2026-01-28

---

## 🎯 주의사항

1. **Houdini 버전**: Houdini 19.0 이상 권장
2. **Python 버전**: Python 3.7 이상
3. **네트워크**: MCP 서버와 클라이언트는 같은 네트워크에 있어야 함
4. **포트**: 기본 포트 9876이 사용 중이면 다른 포트 사용

---

**🎉 Houdini Integration Package를 사용해 주셔서 감사합니다!**










