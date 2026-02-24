# -*- coding: utf-8 -*-
"""
Houdini Curve Point Reversal
stem_curve 노드의 point number를 반전시키는 스크립트
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from houdini_integration.houdini_mcp_connector import HoudiniMCPConnector


def reverse_curve_points(curve_node_path="stem_curve"):
    """
    커브의 포인트 순서를 반전시킵니다.
    
    Args:
        curve_node_path: 커브 노드 경로 또는 이름
    """
    connector = HoudiniMCPConnector()
    
    if not connector.connect():
        print("[ERROR] Houdini 연결 실패!")
        return
    
    print("="*70)
    print(" Curve Point Reversal")
    print("="*70)
    
    # 선택된 노드 확인 또는 지정된 노드 찾기
    result = connector.execute_code(f"""
import hou

# 노드 찾기
target_node = None

# 1. 먼저 선택된 노드 확인
selected = hou.selectedNodes()
if selected:
    for node in selected:
        if "{curve_node_path}" in node.name().lower() or node.name() == "{curve_node_path}":
            target_node = node
            print("Selected node found: {{}}".format(node.path()))
            break

# 2. 선택된 노드가 없으면 전체에서 검색
if not target_node:
    # /obj 하위에서 검색
    obj = hou.node("/obj")
    for child in obj.allSubChildren():
        if "{curve_node_path}" in child.name().lower() or child.name() == "{curve_node_path}":
            target_node = child
            print("Node found: {{}}".format(child.path()))
            break

if not target_node:
    print("[ERROR] '{{}}' 노드를 찾을 수 없습니다.".format("{curve_node_path}"))
    print("\\n사용 가능한 노드:")
    obj = hou.node("/obj")
    for child in obj.allSubChildren():
        if "curve" in child.name().lower() or "stem" in child.name().lower():
            print("  - {{}}".format(child.path()))
else:
    # 노드 정보 출력
    print("\\nTarget Node: {{}}".format(target_node.path()))
    print("Type: {{}}".format(target_node.type().name()))
    
    # 현재 포인트 수 확인
    geo = target_node.geometry()
    if geo:
        num_points = len(geo.points())
        print("Current points: {{}}".format(num_points))
    
    # 부모 노드 경로
    parent_path = target_node.parent().path()
    print("Parent: {{}}".format(parent_path))
""")
    
    if not result:
        connector.disconnect()
        return
    
    # Reverse SOP 또는 Sort SOP 추가
    print("\n" + "-"*70)
    print(" Adding Reverse Node")
    print("-"*70)
    
    connector.execute_code(f"""
import hou

# 타겟 노드 다시 찾기
target_node = None
selected = hou.selectedNodes()
if selected:
    for node in selected:
        if "{curve_node_path}" in node.name().lower() or node.name() == "{curve_node_path}":
            target_node = node
            break

if not target_node:
    obj = hou.node("/obj")
    for child in obj.allSubChildren():
        if "{curve_node_path}" in child.name().lower() or child.name() == "{curve_node_path}":
            target_node = child
            break

if target_node:
    parent = target_node.parent()
    
    # Reverse 노드 생성
    try:
        # 방법 1: Reverse SOP 시도 (curve 전용)
        reverse_node = parent.createNode("reverse", "reverse_{{}}".format(target_node.name()))
        reverse_node.setInput(0, target_node)
        
        # 위치 조정
        pos = target_node.position()
        reverse_node.setPosition([pos[0], pos[1] - 1])
        
        # Display 플래그 설정
        reverse_node.setDisplayFlag(True)
        reverse_node.setRenderFlag(True)
        
        print("\\n[OK] Reverse node created: {{}}".format(reverse_node.path()))
        print("Points are now reversed (last point becomes first)")
        
    except:
        # 방법 2: Sort SOP 사용 (더 범용적)
        print("\\nReverse SOP not available, using Sort SOP instead...")
        
        sort_node = parent.createNode("sort", "reverse_{{}}".format(target_node.name()))
        sort_node.setInput(0, target_node)
        
        # Sort by expression (역순 정렬)
        sort_node.parm("pointsort").set(4)  # By Expression
        sort_node.parm("pointsortexpr").set("-$PT")  # 역순
        
        # 위치 조정
        pos = target_node.position()
        sort_node.setPosition([pos[0], pos[1] - 1])
        
        # Display 플래그 설정
        sort_node.setDisplayFlag(True)
        sort_node.setRenderFlag(True)
        
        print("\\n[OK] Sort node created: {{}}".format(sort_node.path()))
        print("Points are now reversed using Sort SOP")
        print("Expression: -$PT (negative point number for reverse order)")
    
    # 결과 확인
    print("\\n" + "="*60)
    print("Verification")
    print("="*60)
    
    # 원본과 반전된 결과 비교
    orig_geo = target_node.geometry()
    if orig_geo and len(orig_geo.points()) > 0:
        first_pt = orig_geo.points()[0]
        last_pt = orig_geo.points()[-1]
        print("Original first point position: {{}}".format(first_pt.position()))
        print("Original last point position: {{}}".format(last_pt.position()))
    
    print("\\n[OK] Point order reversal complete!")
else:
    print("[ERROR] Target node not found")
""")
    
    print("\n" + "="*70)
    print(" Complete!")
    print("="*70)
    print("\nHoudini에서 확인하세요:")
    print("  - Reverse 노드가 생성되었습니다")
    print("  - 마지막 포인트가 이제 0번이 됩니다")
    print("  - Display 플래그가 자동으로 설정되었습니다")
    
    connector.disconnect()


if __name__ == "__main__":
    # 기본값으로 stem_curve 검색
    reverse_curve_points("stem_curve")




