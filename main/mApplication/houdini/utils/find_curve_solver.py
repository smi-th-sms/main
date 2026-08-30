# -*- coding: utf-8 -*-
"""
Curve Solver 노드 찾기 스크립트
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from houdini_integration.houdini_mcp_connector import HoudiniMCPConnector


def find_curve_solver():
    """Curve Solver 노드 검색"""
    connector = HoudiniMCPConnector()
    
    if not connector.connect():
        print("[ERROR] Houdini 연결 실패!")
        return
    
    print("="*70)
    print(" Curve Solver 노드 검색")
    print("="*70)
    
    connector.execute_code("""
import hou

print("\\n[1] 'curve solver' 관련 노드 타입 검색")
print("-" * 60)

found_nodes = []

# 모든 카테고리에서 검색
categories = [
    ('SOP', hou.sopNodeTypeCategory()),
    ('VOP', hou.vopNodeTypeCategory()),
    ('CHOP', hou.chopNodeTypeCategory()),
    ('DOP', hou.dopNodeTypeCategory()),
    ('ROP', hou.ropNodeTypeCategory()),
    ('TOP', hou.topNodeTypeCategory()),
]

for cat_name, category in categories:
    if category:
        for node_type_name, node_type in category.nodeTypes().items():
            if 'curve' in node_type_name.lower() and 'solv' in node_type_name.lower():
                found_nodes.append((cat_name, node_type_name, node_type))
                print("[{}] {}".format(cat_name, node_type_name))

print("\\n[2] 'solver' 관련 KineFX 노드")
print("-" * 60)

# VOP 카테고리에서 더 자세히 검색
vop_category = hou.vopNodeTypeCategory()
kinefx_vop_nodes = []

for node_type_name, node_type in vop_category.nodeTypes().items():
    if 'solv' in node_type_name.lower() or 'curve' in node_type_name.lower():
        kinefx_vop_nodes.append(node_type_name)

print("VOP에서 발견된 solver/curve 관련 노드:")
for node_name in sorted(kinefx_vop_nodes):
    print("  - {}".format(node_name))

print("\\n[3] 전체 'curve' 관련 노드 (모든 카테고리)")
print("-" * 60)

all_curve_nodes = {}
for cat_name, category in categories:
    if category:
        curve_nodes = []
        for node_type_name in category.nodeTypes().keys():
            if 'curve' in node_type_name.lower():
                curve_nodes.append(node_type_name)
        
        if curve_nodes:
            all_curve_nodes[cat_name] = sorted(curve_nodes)

for cat_name, nodes in all_curve_nodes.items():
    print("\\n[{}] {} nodes:".format(cat_name, len(nodes)))
    for node in nodes[:10]:  # 최대 10개만 표시
        print("  - {}".format(node))
    if len(nodes) > 10:
        print("  ... 외 {} 개".format(len(nodes) - 10))

print("\\n[4] VOP 컨텍스트에서 사용 가능한 노드 확인")
print("-" * 60)

# VOP 네트워크를 생성해서 그 안에서 사용 가능한 노드 확인
try:
    # 임시 geo 노드 생성
    obj = hou.node('/obj')
    temp_geo = obj.createNode('geo', 'temp_check_vop')
    
    # VOP SOP 생성
    vopsop = temp_geo.createNode('attribvop', 'check_vop_nodes')
    
    # VOP 내부로 들어가기
    print("VOP 컨텍스트 생성 완료: {}".format(vopsop.path()))
    
    # VOP 내부에서 생성 가능한 노드 타입 확인
    vop_context = vopsop.type().category()
    
    print("\\nVOP 내부에서 'curve' 또는 'solver' 검색:")
    vop_internal_nodes = []
    
    for node_type_name in vop_context.nodeTypes().keys():
        if 'curve' in node_type_name.lower() or 'solv' in node_type_name.lower():
            vop_internal_nodes.append(node_type_name)
    
    for node in sorted(vop_internal_nodes):
        print("  - {}".format(node))
    
    # 임시 노드 삭제
    temp_geo.destroy()
    
except Exception as e:
    print("[ERROR] VOP 검사 중 오류: {}".format(str(e)))

print("\\n[5] 'curvesolver' (한 단어) 검색")
print("-" * 60)

single_word_found = []
for cat_name, category in categories:
    if category:
        for node_type_name in category.nodeTypes().keys():
            if 'curvesolver' in node_type_name.lower() or 'curvesolve' in node_type_name.lower():
                single_word_found.append("[{}] {}".format(cat_name, node_type_name))
                print("[{}] {}".format(cat_name, node_type_name))

if not single_word_found:
    print("(발견되지 않음)")

print("\\n" + "="*70)
print(" KineFX VOP 노드 사용 방법")
print("="*70)
print(\"\"\"
KineFX VOP 노드는 특정 컨텍스트에서만 접근 가능합니다:

1. Attribute VOP 노드 생성:
   - Tab > 'attribvop' 입력
   
2. Attribute VOP 내부로 들어가기:
   - 더블클릭 또는 'i' 키
   
3. 내부에서 Tab 키:
   - 'curve solver' 검색
   - 'kinefx' 검색
   
또는:

1. SOP Solver 사용:
   - Tab > 'solver'
   - SOP Solver 내부에서 작업
   
2. Labs 노드 확인:
   - Tab > 'labs curve'
   - SideFX Labs 플러그인 설치 필요할 수 있음
\"\"\")

print("\\n[6] Houdini 버전 및 플러그인 확인")
print("-" * 60)
print("Houdini: {}".format(hou.applicationVersionString()))

# 설치된 플러그인 확인
try:
    import subprocess
    # hython -c로 설치된 패키지 확인은 복잡하므로 간단히 버전만
    print("\\n현재 Houdini 버전에서 KineFX Curve Solver가")
    print("지원되는지 매뉴얼을 확인하세요:")
    print("https://www.sidefx.com/docs/houdini/nodes/")
except:
    pass
    """)
    
    print("\n" + "="*70)
    print(" 추가 확인 사항")
    print("="*70)
    print("""
만약 'curve solver' 노드가 여전히 없다면:

1. Houdini 버전 확인:
   - KineFX Curve Solver는 특정 버전부터 지원
   - Houdini 19.5 이상 권장
   
2. SideFX Labs 설치:
   - 일부 고급 KineFX 노드는 Labs에 포함
   - Help > Install SideFX Labs
   
3. 대체 노드:
   - 'rig doctor' - 리그 수정
   - 'rig pose' - 포즈 설정
   - 'rbdsolver' - RBD 시뮬레이션 솔버
   
4. 노드 이름 변경 가능성:
   - 최신 버전에서 이름이 변경되었을 수 있음
   - 'rig'로 시작하는 노드들 확인
""")
    
    connector.disconnect()


if __name__ == "__main__":
    find_curve_solver()




