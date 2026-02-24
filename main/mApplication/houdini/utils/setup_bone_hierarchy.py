# -*- coding: utf-8 -*-
"""
사용자 지정 Start/End Point로 Bone Tree 구조 및 네이밍 설정
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from houdini_integration.houdini_mcp_connector import HoudiniMCPConnector


def setup_bone_hierarchy(target_node="orientjoints0", start_point=None, end_point=None):
    """
    사용자가 지정한 start/end point로 bone 계층 구조 및 네이밍 설정
    
    Args:
        target_node: 대상 노드 이름
        start_point: Root가 될 포인트 번호 (None이면 입력 받음)
        end_point: 마지막 포인트 번호 (None이면 입력 받음)
    """
    connector = HoudiniMCPConnector()
    
    if not connector.connect():
        print("[ERROR] Houdini 연결 실패!")
        return
    
    print("="*80)
    print(" Bone Hierarchy Setup (사용자 지정)")
    print("="*80)
    
    # 1단계: 노드 찾기 및 정보 확인
    result = connector.execute_code(f"""
import hou

# 노드 찾기
target_node = None
all_nodes = hou.node("/obj").allSubChildren()

for node in all_nodes:
    if node.name() == "{target_node}":
        target_node = node
        break

if not target_node:
    # 선택된 노드 사용
    selected = hou.selectedNodes()
    if selected:
        target_node = selected[0]
        print("[INFO] 선택된 노드 사용: {{}}".format(target_node.path()))

if not target_node:
    print("[ERROR] '{{}}' 노드를 찾을 수 없습니다.".format("{target_node}"))
    print("\\n노드를 선택하거나 이름을 확인하세요.")
else:
    print("[OK] 대상 노드: {{}}".format(target_node.path()))
    
    geo = target_node.geometry()
    if geo:
        num_points = len(geo.points())
        print("\\n포인트 수: {{}}".format(num_points))
        print("포인트 범위: 0 ~ {{}}".format(num_points - 1))
        
        # 현재 포인트 위치 미리보기
        print("\\n현재 포인트 위치 (처음 5개, 마지막 1개):")
        points = geo.points()
        for i in range(min(5, num_points)):
            pt = points[i]
            pos = pt.position()
            print("  Point {{}}: Y={:.3f}".format(i, pos[1]))
        
        if num_points > 5:
            pt_last = points[-1]
            pos_last = pt_last.position()
            print("  ...")
            print("  Point {{}}: Y={:.3f}".format(num_points-1, pos_last[1]))
        
        # Global에 저장 (다음 단계에서 사용)
        hou.session.target_node_path = target_node.path()
        hou.session.num_points = num_points
    else:
        print("[ERROR] Geometry가 없습니다.")
""")
    
    if not result:
        connector.disconnect()
        return
    
    # 2단계: 사용자 입력 받기
    if start_point is None or end_point is None:
        print("\n" + "-"*80)
        print(" Start/End Point 지정")
        print("-"*80)
        
        # Start point 입력
        if start_point is None:
            start_input = input("\nRoot가 될 Start Point 번호 입력 (기본: 0): ").strip()
            start_point = int(start_input) if start_input else 0
        
        # End point 입력
        if end_point is None:
            end_input = input("마지막이 될 End Point 번호 입력 (기본: 마지막): ").strip()
            if end_input:
                end_point = int(end_input)
            else:
                end_point = None  # 자동으로 마지막 사용
    
    print("\n" + "="*80)
    print(" 설정 확인")
    print("="*80)
    print(f"Start Point (Root): {start_point}")
    print(f"End Point (Tip): {end_point if end_point is not None else '마지막'}")
    
    # 3단계: Attribute Wrangle 노드 생성 및 VEX 코드 설정
    print("\n" + "-"*80)
    print(" Attribute Wrangle 노드 생성 중...")
    print("-"*80)
    
    end_point_str = str(end_point) if end_point is not None else "num_points - 1"
    
    connector.execute_code(f"""
import hou

# 저장된 노드 경로 가져오기
target_path = hou.session.target_node_path
num_points = hou.session.num_points

target_node = hou.node(target_path)
parent = target_node.parent()

# End point 계산
end_pt = {end_point} if {end_point} is not None else num_points - 1

print("\\nStart Point: {start_point}")
print("End Point: {{}}".format(end_pt))
print("Direction: {start_point} → {{}}".format(end_pt))

# Attribute Wrangle 노드 생성
wrangle_name = "setup_bone_hierarchy"
wrangle = parent.createNode("attribwrangle", wrangle_name)
wrangle.setInput(0, target_node)

# 노드 위치 조정
pos = target_node.position()
wrangle.setPosition([pos[0], pos[1] - 1.5])

# VEX 코드 생성
start_pt = {start_point}
end_pt_calc = end_pt

# 방향 결정 (start에서 end로)
if start_pt < end_pt_calc:
    # 정방향: 0 → 마지막
    direction = "forward"
else:
    # 역방향: 마지막 → 0
    direction = "reverse"

print("\\nHierarchy Direction: {{}}".format(direction))

# VEX 코드 작성
vex_code = '''// Bone Hierarchy Setup
// Start: {start_pt}, End: {{end_pt}}

int start_pt = {start_point};
int end_pt = {{end_pt}};
int total_pts = npoints(0);

// 포인트 범위 확인
if (@ptnum < chi("start_pt") || @ptnum > chi("end_pt")) {{
    // 범위 밖의 포인트는 제거하거나 무시
    removepoint(0, @ptnum);
    return;
}}

// 인덱스 재계산 (start를 0으로)
int reindexed = @ptnum - start_pt;

// Parent 설정
if (@ptnum == start_pt) {{
    // Start point가 Root
    s@name = "Root";
    i@parent = -1;
}} else {{
    // Parent는 이전 포인트 (start → end 방향)
    if (start_pt < end_pt) {{
        // 정방향
        s@name = sprintf("Bone_%d", reindexed);
        i@parent = @ptnum - 1;
    }} else {{
        // 역방향
        s@name = sprintf("Bone_%d", start_pt - @ptnum);
        i@parent = @ptnum + 1;
    }}
}}
'''.format(start_pt=start_pt, end_pt=end_pt_calc)

wrangle.parm("snippet").set(vex_code)

# 파라미터 추가
wrangle.addSpareParmTuple(
    hou.IntParmTemplate("start_pt", "Start Point", 1, default_value=({start_point},))
)
wrangle.addSpareParmTuple(
    hou.IntParmTemplate("end_pt", "End Point", 1, default_value=(end_pt_calc,))
)

# Display 플래그 설정
wrangle.setDisplayFlag(True)
wrangle.setRenderFlag(True)

print("\\n[OK] Attribute Wrangle 노드 생성 완료!")
print("Node: {{}}".format(wrangle.path()))

# 결과 미리보기
print("\\nResult Preview:")
geo = wrangle.geometry()
if geo and len(geo.points()) > 0:
    points = geo.points()
    print("Total Points: {{}}".format(len(points)))
    print("\\nFirst 5 points:")
    for i in range(min(5, len(points))):
        pt = points[i]
        name_val = pt.attribValue("name") if pt.hasAttrib("name") else "N/A"
        parent_val = pt.attribValue("parent") if pt.hasAttrib("parent") else "N/A"
        print("  Point {{}}: name='{{}}', parent={{}}".format(i, name_val, parent_val))

print("\\n" + "="*60)
print("[OK] Bone Hierarchy 설정 완료!")
print("="*60)
print("\\nHoudini에서 확인:")
print("  - {{}} 노드가 생성되었습니다".format(wrangle.path()))
print("  - Geometry Spreadsheet (g)로 확인하세요")
print("  - Start Point/End Point는 파라미터로 수정 가능합니다")
""")
    
    connector.disconnect()


if __name__ == "__main__":
    # 기본값으로 실행 (사용자 입력 받음)
    print("\n" + "="*80)
    print(" Bone Hierarchy Setup Tool")
    print("="*80)
    print("\n대상 노드를 지정하거나 Houdini에서 선택하세요.")
    
    node_name = input("\n노드 이름 (기본: orientjoints0): ").strip()
    if not node_name:
        node_name = "orientjoints0"
    
    setup_bone_hierarchy(node_name)




