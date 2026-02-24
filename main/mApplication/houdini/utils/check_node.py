# -*- coding: utf-8 -*-
"""
특정 노드의 역할 및 파라미터 확인
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from houdini_integration.houdini_mcp_connector import HoudiniMCPConnector


def check_node(node_name="name1"):
    """노드 정보 확인"""
    connector = HoudiniMCPConnector()
    
    if not connector.connect():
        print("[ERROR] Houdini 연결 실패!")
        return
    
    print("="*70)
    print(f" '{node_name}' 노드 분석")
    print("="*70)
    
    connector.execute_code(f"""
import hou

# 노드 찾기
target_node = None

# 선택된 노드 확인
selected = hou.selectedNodes()
for node in selected:
    if node.name() == "{node_name}":
        target_node = node
        break

# 전체에서 검색
if not target_node:
    all_nodes = hou.node("/obj").allSubChildren()
    for node in all_nodes:
        if node.name() == "{node_name}":
            target_node = node
            break

if not target_node:
    print("[ERROR] '{{}}' 노드를 찾을 수 없습니다.".format("{node_name}"))
else:
    print("="*70)
    print(" 노드 정보")
    print("="*70)
    print("Name: {{}}".format(target_node.name()))
    print("Path: {{}}".format(target_node.path()))
    print("Type: {{}}".format(target_node.type().name()))
    print("Label: {{}}".format(target_node.comment()))
    
    # 입력 노드
    print("\\n" + "-"*70)
    print(" 입력 연결")
    print("-"*70)
    inputs = target_node.inputs()
    if inputs:
        for i, input_node in enumerate(inputs):
            if input_node:
                print("Input {{}}: {{}} ({{}})".format(i, input_node.name(), input_node.type().name()))
    else:
        print("(입력 없음)")
    
    # 출력 노드
    print("\\n" + "-"*70)
    print(" 출력 연결")
    print("-"*70)
    outputs = target_node.outputs()
    if outputs:
        for output_node in outputs:
            print("Output: {{}} ({{}})".format(output_node.name(), output_node.type().name()))
    else:
        print("(출력 없음)")
    
    # 주요 파라미터
    print("\\n" + "-"*70)
    print(" 주요 파라미터")
    print("-"*70)
    
    parms = target_node.parms()
    important_parms = []
    
    for parm in parms:
        parm_template = parm.parmTemplate()
        # 기본값과 다르거나 중요한 파라미터만
        if not parm.isAtDefault() or parm.name() in ['group', 'class', 'name', 'attribname', 'method']:
            try:
                value = parm.eval()
                important_parms.append((parm.name(), value, parm_template.label()))
            except:
                pass
    
    if important_parms:
        for parm_name, value, label in important_parms[:20]:  # 최대 20개
            print("  {{}} ({{}}): {{}}".format(label, parm_name, value))
    else:
        print("(모든 파라미터가 기본값)")
    
    # Geometry 정보
    print("\\n" + "-"*70)
    print(" Geometry 정보")
    print("-"*70)
    
    try:
        geo = target_node.geometry()
        if geo:
            print("Points: {{}}".format(len(geo.points())))
            print("Primitives: {{}}".format(len(geo.prims())))
            
            # Attributes
            print("\\nPoint Attributes:")
            for attrib in geo.pointAttribs():
                print("  - {{}} ({{}}, size: {{}})".format(
                    attrib.name(), 
                    attrib.dataType().name(),
                    attrib.size()
                ))
            
            # Name attribute 샘플 (있으면)
            if geo.findPointAttrib("name"):
                print("\\nName Attribute 샘플 (처음 5개):")
                for i, pt in enumerate(geo.points()[:5]):
                    name_val = pt.attribValue("name")
                    parent_val = pt.attribValue("parent") if pt.hasAttrib("parent") else "N/A"
                    print("  Point {{}}: name='{{}}', parent='{{}}'".format(i, name_val, parent_val))
        else:
            print("(Geometry 없음)")
    except Exception as e:
        print("Geometry 정보 가져오기 실패: {{}}".format(str(e)))
    
    # 노드 타입 설명
    print("\\n" + "="*70)
    print(" 노드 타입 설명")
    print("="*70)
    
    node_type = target_node.type().name()
    
    descriptions = {{
        'name': 'Name SOP - Point/Primitive에 name attribute 생성 또는 수정',
        'attribwrangle': 'Attribute Wrangle - VEX 코드로 attribute 생성/수정',
        'sort': 'Sort - Point/Primitive 순서 재정렬',
        'orientjoints': 'Orient Joints - Joint orientation 설정',
        'reverse': 'Reverse - Curve point 순서 반전',
    }}
    
    desc = descriptions.get(node_type, '(설명 없음)')
    print(desc)
    
    print("\\n" + "="*70)
    print(" 이 노드의 역할")
    print("="*70)
    
    if node_type == 'name':
        print(\"\"\"
Name 노드는 주로 다음 작업을 수행합니다:

1. Point 또는 Primitive에 'name' attribute 생성
2. 기존 name attribute 수정
3. 패턴이나 표현식으로 이름 자동 생성
4. KineFX 리깅에서 bone 이름 설정에 자주 사용

현재 파라미터를 확인해서 어떤 naming 규칙이 적용되고 있는지
확인하세요!
\"\"\")
    elif node_type == 'attribwrangle':
        print("VEX 코드로 attribute를 직접 수정하는 노드입니다.")
    
    print("="*70)
""")
    
    connector.disconnect()


if __name__ == "__main__":
    import sys
    node_name = sys.argv[1] if len(sys.argv) > 1 else "name1"
    check_node(node_name)




