# -*- coding: utf-8 -*-
"""
Attribute Wrangle 노드들 분석
attribwrangle11과 attribwrangle18의 설정 및 코드 확인
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from houdini_integration.houdini_mcp_connector import HoudiniMCPConnector


def analyze_wrangle_nodes():
    """Wrangle 노드들 분석"""
    connector = HoudiniMCPConnector()
    
    if not connector.connect():
        print("[ERROR] Houdini 연결 실패!")
        return
    
    print("="*80)
    print(" Attribute Wrangle 노드 분석")
    print("="*80)
    
    connector.execute_code("""
import hou

# 노드 찾기
wrangle11 = None
wrangle18 = None

all_nodes = hou.node("/obj").allSubChildren()

for node in all_nodes:
    if node.name() == "attribwrangle11":
        wrangle11 = node
    elif node.name() == "attribwrangle18":
        wrangle18 = node

print("\\n" + "="*80)
print(" attribwrangle11 분석")
print("="*80)

if wrangle11:
    print("\\n[기본 정보]")
    print("Path:", wrangle11.path())
    print("Type:", wrangle11.type().name())
    
    # 입력 확인
    print("\\n[입력 연결]")
    inputs = wrangle11.inputs()
    for i, inp in enumerate(inputs):
        if inp:
            print("  Input {}: {} ({})".format(i, inp.name(), inp.type().name()))
    
    # 출력 확인
    print("\\n[출력 연결]")
    outputs = wrangle11.outputs()
    for out in outputs:
        print("  Output: {} ({})".format(out.name(), out.type().name()))
    
    # Run Over 설정
    print("\\n[Run Over 설정]")
    runover = wrangle11.parm("class")
    if runover:
        runover_val = runover.eval()
        runover_menu = runover.menuLabels()
        print("  Class:", runover_val)
        print("  Label:", runover_menu[runover_val] if runover_val < len(runover_menu) else "Unknown")
    
    # VEX 코드
    print("\\n[VEX Code]")
    snippet = wrangle11.parm("snippet")
    if snippet:
        code = snippet.eval()
        print("-" * 60)
        print(code)
        print("-" * 60)
    
    # Geometry 정보
    print("\\n[Geometry 정보]")
    geo = wrangle11.geometry()
    if geo:
        print("  Points:", len(geo.points()))
        print("  Primitives:", len(geo.prims()))
        
        # Root 그룹 확인
        if geo.findPointGroup("root"):
            root_group = geo.findPointGroup("root")
            root_points = list(root_group.points())
            print("  Root group points:", [pt.number() for pt in root_points])
        else:
            print("  Root group: 없음")
else:
    print("\\n[ERROR] attribwrangle11 노드를 찾을 수 없습니다.")

print("\\n\\n" + "="*80)
print(" attribwrangle18 분석")
print("="*80)

if wrangle18:
    print("\\n[기본 정보]")
    print("Path:", wrangle18.path())
    print("Type:", wrangle18.type().name())
    
    # 입력 확인
    print("\\n[입력 연결]")
    inputs = wrangle18.inputs()
    for i, inp in enumerate(inputs):
        if inp:
            print("  Input {}: {} ({})".format(i, inp.name(), inp.type().name()))
            
            # Input의 geometry 정보
            inp_geo = inp.geometry()
            if inp_geo:
                print("    Points:", len(inp_geo.points()))
                
                # Root 그룹 확인
                if inp_geo.findPointGroup("root"):
                    root_group = inp_geo.findPointGroup("root")
                    root_points = list(root_group.points())
                    print("    Root group:", [pt.number() for pt in root_points])
    
    # 출력 확인
    print("\\n[출력 연결]")
    outputs = wrangle18.outputs()
    for out in outputs:
        print("  Output: {} ({})".format(out.name(), out.type().name()))
    
    # Run Over 설정
    print("\\n[Run Over 설정]")
    runover = wrangle18.parm("class")
    if runover:
        runover_val = runover.eval()
        runover_menu = runover.menuLabels()
        print("  Class:", runover_val)
        print("  Label:", runover_menu[runover_val] if runover_val < len(runover_menu) else "Unknown")
    
    # VEX 코드
    print("\\n[VEX Code]")
    snippet = wrangle18.parm("snippet")
    if snippet:
        code = snippet.eval()
        print("-" * 60)
        print(code)
        print("-" * 60)
    
    # Geometry 정보
    print("\\n[Output Geometry 정보]")
    geo = wrangle18.geometry()
    if geo:
        print("  Points:", len(geo.points()))
        print("  Primitives:", len(geo.prims()))
        
        # Vertex 순서 확인
        if len(geo.prims()) > 0:
            print("\\n  Vertex 순서:")
            prim = geo.prims()[0]
            vtxs = prim.vertices()
            for i, vtx in enumerate(vtxs):
                pt = vtx.point()
                pos = pt.position()
                root_grp = geo.findPointGroup("root")
                conn_grp = geo.findPointGroup("connection_point")
                is_root = (root_grp and pt in root_grp.points()) if root_grp else False
                is_conn = (conn_grp and pt in conn_grp.points()) if conn_grp else False
                
                print("    Vertex {}: Point {} at ({:.2f}, {:.2f}, {:.2f})".format(
                    i, pt.number(), pos[0], pos[1], pos[2]))
                
                if is_root:
                    print("      [ROOT]")
                if is_conn:
                    print("      [CONNECTION_POINT]")
        
        # Root 그룹 확인
        if geo.findPointGroup("root"):
            root_group = geo.findPointGroup("root")
            root_points = list(root_group.points())
            print("\\n  Root group points:", [pt.number() for pt in root_points])
            
            for pt in root_points:
                pos = pt.position()
                print("    Point {}: ({:.2f}, {:.2f}, {:.2f})".format(
                    pt.number(), pos[0], pos[1], pos[2]))
else:
    print("\\n[ERROR] attribwrangle18 노드를 찾을 수 없습니다.")

print("\\n\\n" + "="*80)
print(" 문제 분석")
print("="*80)

if wrangle11 and wrangle18:
    print("\\n1. Root 그룹 전파 확인:")
    
    # wrangle11의 output
    w11_geo = wrangle11.geometry()
    w11_root = None
    if w11_geo and w11_geo.findPointGroup("root"):
        w11_root = [pt.number() for pt in w11_geo.findPointGroup("root").points()]
    
    # wrangle18의 input 0
    w18_inp0 = wrangle18.inputs()[0] if wrangle18.inputs() else None
    w18_inp0_root = None
    if w18_inp0:
        inp0_geo = w18_inp0.geometry()
        if inp0_geo and inp0_geo.findPointGroup("root"):
            w18_inp0_root = [pt.number() for pt in inp0_geo.findPointGroup("root").points()]
    
    # wrangle18의 output
    w18_geo = wrangle18.geometry()
    w18_root = None
    if w18_geo and w18_geo.findPointGroup("root"):
        w18_root = [pt.number() for pt in w18_geo.findPointGroup("root").points()]
    
    print("  wrangle11 output root:", w11_root)
    print("  wrangle18 input 0 root:", w18_inp0_root)
    print("  wrangle18 output root:", w18_root)
    
    if w11_root != w18_inp0_root:
        print("\\n  [WARNING] Root가 wrangle11에서 wrangle18 input으로 제대로 전달되지 않음!")
    
    if w18_inp0_root and w18_root and w18_inp0_root != w18_root:
        print("\\n  [INFO] Root가 wrangle18에서 변경됨 (예상된 동작일 수 있음)")

print("\\n" + "="*80)
""")
    
    connector.disconnect()
    print("\n분석 완료!")


if __name__ == "__main__":
    analyze_wrangle_nodes()

