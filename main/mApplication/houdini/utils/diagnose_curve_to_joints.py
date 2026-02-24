# -*- coding: utf-8 -*-
"""
Curve에서 Joint까지 전체 파이프라인 진단
stem_curve → orientjoints0 → naming 과정 체크
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from houdini_integration.houdini_mcp_connector import HoudiniMCPConnector


def diagnose_curve_to_joints():
    """커브부터 조인트 생성까지 전체 과정 진단"""
    connector = HoudiniMCPConnector()
    
    if not connector.connect():
        print("[ERROR] Houdini 연결 실패!")
        print("Houdini에서 MCP 서버를 시작하세요:")
        print("""
import sys
sys.path.append(r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3")
from houdini_mcp_server import start_mcp_server
start_mcp_server()
""")
        return
    
    print("="*80)
    print(" Curve to Joints 파이프라인 진단")
    print("="*80)
    
    connector.execute_code("""
import hou

print("\\n" + "="*80)
print(" [1] stem_curve 노드 분석")
print("="*80)

# stem_curve 노드 찾기
stem_curve = None
all_nodes = hou.node("/obj").allSubChildren()

for node in all_nodes:
    if "stem_curve" in node.name().lower():
        stem_curve = node
        print("Found: {}".format(node.path()))
        break

if not stem_curve:
    print("[ERROR] stem_curve 노드를 찾을 수 없습니다.")
else:
    print("\\nNode Info:")
    print("  Path: {}".format(stem_curve.path()))
    print("  Type: {}".format(stem_curve.type().name()))
    
    # Geometry 분석
    geo = stem_curve.geometry()
    if geo:
        points = geo.points()
        prims = geo.prims()
        
        print("\\nGeometry:")
        print("  Points: {}".format(len(points)))
        print("  Primitives: {}".format(len(prims)))
        
        if len(points) > 0:
            # Point 0 (첫 번째 포인트) 위치
            pt0 = points[0]
            pos0 = pt0.position()
            
            # Point 마지막 위치
            pt_last = points[-1]
            pos_last = pt_last.position()
            
            print("\\nPoint Positions:")
            print("  Point 0 (첫번째):")
            print("    Position: ({:.3f}, {:.3f}, {:.3f})".format(pos0[0], pos0[1], pos0[2]))
            print("    Height Y: {:.3f}".format(pos0[1]))
            
            print("  Point {} (마지막):".format(len(points)-1))
            print("    Position: ({:.3f}, {:.3f}, {:.3f})".format(pos_last[0], pos_last[1], pos_last[2]))
            print("    Height Y: {:.3f}".format(pos_last[1]))
            
            # Base와 Tip 판단
            print("\\nCurve Direction Analysis:")
            if pos0[1] < pos_last[1]:
                print("  [OK] Point 0이 아래에 있음 (Base)")
                print("  [OK] Point {}이 위에 있음 (Tip)".format(len(points)-1))
                print("  => 커브 방향: 바닥(Base) → 위(Tip) ✓")
            else:
                print("  [WARNING] Point 0이 위에 있음 (Tip)")
                print("  [WARNING] Point {}이 아래에 있음 (Base)".format(len(points)-1))
                print("  => 커브 방향: 위(Tip) → 바닥(Base) ✗")
                print("  => REVERSE 필요!")
            
            # 중간 포인트 몇 개 샘플
            print("\\nPoint Samples (first 5):")
            for i in range(min(5, len(points))):
                pt = points[i]
                pos = pt.position()
                print("  Point {}: Y = {:.3f}".format(i, pos[1]))
        
        # Primitive 정보 (curve)
        if len(prims) > 0:
            prim = prims[0]
            print("\\nPrimitive Info:")
            print("  Type: {}".format(prim.type().name()))
            print("  Vertices: {}".format(len(prim.vertices())))
            print("  Is Closed: {}".format(prim.attribValue("closed") if prim.hasAttrib("closed") else "N/A"))
    else:
        print("[ERROR] Geometry가 없습니다.")

print("\\n" + "="*80)
print(" [2] orientjoints0 노드 분석")
print("="*80)

# orientjoints0 노드 찾기
orientjoints = None
for node in all_nodes:
    if "orientjoints" in node.name().lower() and "0" in node.name():
        orientjoints = node
        print("Found: {}".format(node.path()))
        break

if not orientjoints:
    print("[ERROR] orientjoints0 노드를 찾을 수 없습니다.")
else:
    print("\\nNode Info:")
    print("  Path: {}".format(orientjoints.path()))
    print("  Type: {}".format(orientjoints.type().name()))
    
    # 입력 연결 확인
    inputs = orientjoints.inputs()
    if inputs and inputs[0]:
        print("  Input: {} ({})".format(inputs[0].name(), inputs[0].type().name()))
    
    # 파라미터 확인
    print("\\nKey Parameters:")
    important_parms = [
        'group', 'method', 'upvector', 'forwarddir', 'updir'
    ]
    
    for parm_name in important_parms:
        parm = orientjoints.parm(parm_name)
        if parm:
            try:
                value = parm.eval()
                print("  {}: {}".format(parm_name, value))
            except:
                pass
    
    # Output geometry 분석
    geo = orientjoints.geometry()
    if geo:
        points = geo.points()
        
        print("\\nOutput Geometry:")
        print("  Points: {}".format(len(points)))
        
        # Attributes 확인
        print("\\nPoint Attributes:")
        for attrib in geo.pointAttribs():
            print("  - {} ({})".format(attrib.name(), attrib.dataType().name()))
        
        # Parent attribute 확인
        has_parent = geo.findPointAttrib("parent") is not None
        has_name = geo.findPointAttrib("name") is not None
        
        print("\\nKineFX Attributes:")
        print("  Has 'parent': {}".format(has_parent))
        print("  Has 'name': {}".format(has_name))
        
        if len(points) > 0:
            print("\\nJoint Hierarchy Check (first 10 points):")
            for i in range(min(10, len(points))):
                pt = points[i]
                pos = pt.position()
                
                parent_val = "N/A"
                name_val = "N/A"
                
                if has_parent:
                    parent_val = pt.attribValue("parent")
                if has_name:
                    name_val = pt.attribValue("name")
                
                print("  Point {}: Y={:.3f}, name='{}', parent={}".format(
                    i, pos[1], name_val, parent_val
                ))
            
            # Parent 관계 분석
            if has_parent:
                print("\\nParent Hierarchy Analysis:")
                root_points = []
                for i, pt in enumerate(points):
                    parent = pt.attribValue("parent")
                    if parent == -1 or parent == "" or parent is None:
                        root_points.append(i)
                
                if root_points:
                    print("  Root Points (parent=-1): {}".format(root_points))
                    
                    for root_idx in root_points[:3]:  # 최대 3개만
                        root_pt = points[root_idx]
                        root_pos = root_pt.position()
                        print("\\n  Root Point {}:".format(root_idx))
                        print("    Position Y: {:.3f}".format(root_pos[1]))
                        
                        # 이 root의 자식들 찾기
                        children = []
                        for j, pt in enumerate(points):
                            if pt.attribValue("parent") == root_idx:
                                children.append(j)
                        
                        if children:
                            print("    Children: {}".format(children[:5]))
                            child_pos = points[children[0]].position()
                            print("    First child Y: {:.3f}".format(child_pos[1]))
                            
                            # 방향 체크
                            if root_pos[1] < child_pos[1]:
                                print("    Direction: Root(아래) → Child(위) ✓")
                            else:
                                print("    Direction: Root(위) → Child(아래) ✗")
                else:
                    print("  [WARNING] Root point가 없습니다!")

print("\\n" + "="*80)
print(" [3] 이후 네이밍 노드 체크")
print("="*80)

# name, attribwrangle 등 네이밍 관련 노드 찾기
naming_nodes = []
for node in all_nodes:
    node_type = node.type().name()
    if node_type in ['name', 'attribwrangle'] or 'name' in node.name().lower():
        # orientjoints의 downstream인지 확인
        if orientjoints:
            try:
                dependent = node.dependents([orientjoints], include_self=False)
                if dependent:
                    naming_nodes.append(node)
            except:
                pass

if naming_nodes:
    print("\\nNaming Nodes Found:")
    for node in naming_nodes[:5]:
        print("  - {} ({})".format(node.path(), node.type().name()))
        
        # 최종 output 확인
        if node == naming_nodes[-1]:
            print("\\n  Final Output from {}:".format(node.name()))
            geo = node.geometry()
            if geo and len(geo.points()) > 0:
                print("  First 5 points:")
                for i in range(min(5, len(geo.points()))):
                    pt = geo.points()[i]
                    name_val = pt.attribValue("name") if pt.hasAttrib("name") else "N/A"
                    parent_val = pt.attribValue("parent") if pt.hasAttrib("parent") else "N/A"
                    print("    Point {}: name='{}', parent={}".format(i, name_val, parent_val))
else:
    print("\\n[INFO] 네이밍 노드가 없습니다.")

print("\\n" + "="*80)
print(" [4] 권장 사항")
print("="*80)
print(\"\"\"
올바른 설정:
  1. stem_curve: Point 0이 바닥(Base), 마지막 Point가 위(Tip)
  2. orientjoints0: Point 0의 parent = -1 (Root)
  3. Parent 관계: 0 ← 1 ← 2 ← 3 (아래에서 위로)
  4. 네이밍: Point 0 = "Root", Point 1 = "Bone_1", ...

만약 반대로 되어 있다면:
  - stem_curve 다음에 Reverse SOP 추가
  - 또는 Attribute Wrangle으로 parent 재설정
\"\"\")

print("="*80)
""")
    
    connector.disconnect()
    print("\n진단 완료!")


if __name__ == "__main__":
    diagnose_curve_to_joints()




