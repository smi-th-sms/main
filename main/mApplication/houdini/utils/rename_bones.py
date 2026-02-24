# -*- coding: utf-8 -*-
"""
Attribute Wrangle에서 Bone 이름 변경
첫 번째: Root, 나머지: Bone_1, Bone_2, ...
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from houdini_integration.houdini_mcp_connector import HoudiniMCPConnector


def rename_bones_in_wrangle(wrangle_node_name="attribwrangle9"):
    """
    Attribute Wrangle 노드에 bone 이름 변경 VEX 코드 설정
    
    Args:
        wrangle_node_name: Attribute Wrangle 노드 이름
    """
    connector = HoudiniMCPConnector()
    
    if not connector.connect():
        print("[ERROR] Houdini 연결 실패!")
        return
    
    print("="*70)
    print(" Bone Rename in Attribute Wrangle")
    print("="*70)
    
    # VEX 코드 생성
    vex_code = """// Rename bones: First = Root, Rest = Bone_1, Bone_2, ...

if (@ptnum == 0) {
    s@name = "Root";
} else {
    s@name = sprintf("Bone_%d", @ptnum);
}
"""
    
    print("\nVEX Code:")
    print("-"*70)
    print(vex_code)
    print("-"*70)
    
    # Houdini에서 노드 찾기 및 코드 적용
    connector.execute_code(f"""
import hou

# 노드 찾기
target_node = None

# 1. 선택된 노드 확인
selected = hou.selectedNodes()
if selected:
    for node in selected:
        if node.name() == "{wrangle_node_name}" or node.type().name() == "attribwrangle":
            target_node = node
            print("[OK] Selected node: {{}}".format(node.path()))
            break

# 2. 전체에서 검색
if not target_node:
    all_nodes = hou.node("/obj").allSubChildren()
    for node in all_nodes:
        if node.name() == "{wrangle_node_name}":
            target_node = node
            print("[OK] Found node: {{}}".format(node.path()))
            break

if not target_node:
    print("[ERROR] '{{}}' 노드를 찾을 수 없습니다.".format("{wrangle_node_name}"))
    print("\\n사용 가능한 Attribute Wrangle 노드:")
    all_nodes = hou.node("/obj").allSubChildren()
    for node in all_nodes:
        if node.type().name() == "attribwrangle":
            print("  - {{}}".format(node.path()))
else:
    # VEX 코드 설정
    vex_code = '''// Rename bones: First = Root, Rest = Bone_1, Bone_2, ...

if (@ptnum == 0) {{
    s@name = "Root";
}} else {{
    s@name = sprintf("Bone_%d", @ptnum);
}}
'''
    
    try:
        # snippet 파라미터에 코드 설정
        snippet_parm = target_node.parm("snippet")
        if snippet_parm:
            snippet_parm.set(vex_code)
            print("\\n[OK] VEX 코드가 {{}} 노드에 설정되었습니다!".format(target_node.path()))
            
            # 현재 설정 확인
            print("\\nNode Info:")
            print("  Path: {{}}".format(target_node.path()))
            print("  Type: {{}}".format(target_node.type().name()))
            print("  Class: {{}}".format(target_node.parm("class").eval() if target_node.parm("class") else "N/A"))
            
            # 결과 미리보기 (첫 5개 포인트)
            print("\\nPreview (first 5 points):")
            geo = target_node.geometry()
            if geo:
                points = geo.points()
                for i, pt in enumerate(points[:5]):
                    name_attrib = pt.attribValue("name") if pt.hasAttrib("name") else "N/A"
                    print("  Point {{}}: name = {{}}".format(i, name_attrib))
                
                if len(points) > 5:
                    print("  ... (total {{}} points)".format(len(points)))
            
        else:
            print("[ERROR] 'snippet' 파라미터를 찾을 수 없습니다.")
            print("이 노드가 Attribute Wrangle인지 확인하세요.")
            
    except Exception as e:
        print("[ERROR] VEX 코드 설정 실패: {{}}".format(str(e)))
""")
    
    print("\n" + "="*70)
    print(" 완료!")
    print("="*70)
    print("\nBone 이름 규칙:")
    print("  Point 0: Root")
    print("  Point 1: Bone_1")
    print("  Point 2: Bone_2")
    print("  Point 3: Bone_3")
    print("  ...")
    
    connector.disconnect()


if __name__ == "__main__":
    rename_bones_in_wrangle("attribwrangle9")




