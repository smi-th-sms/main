# -*- coding: utf-8 -*-
"""
Attribute Wrangle 노드 에러 확인
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from houdini_integration.houdini_mcp_connector import HoudiniMCPConnector


def check_wrangle_error():
    """Wrangle 에러 확인"""
    connector = HoudiniMCPConnector()
    
    if not connector.connect():
        print("[ERROR] Houdini 연결 실패!")
        return
    
    print("="*80)
    print(" Attribute Wrangle Error 확인")
    print("="*80)
    
    connector.execute_code("""
import hou

# attribwrangle11 찾기
wrangle11 = None
all_nodes = hou.node("/obj").allSubChildren()

for node in all_nodes:
    if node.name() == "attribwrangle11":
        wrangle11 = node
        break

if not wrangle11:
    print("[ERROR] attribwrangle11 노드를 찾을 수 없습니다.")
else:
    print("\\n[노드 정보]")
    print("Path:", wrangle11.path())
    
    # 에러 확인
    print("\\n[에러 체크]")
    if wrangle11.errors():
        print("Errors:")
        for error in wrangle11.errors():
            print("  -", error)
    else:
        print("  No errors")
    
    # 워닝 확인
    if wrangle11.warnings():
        print("\\nWarnings:")
        for warning in wrangle11.warnings():
            print("  -", warning)
    
    # VEX 코드
    print("\\n[VEX Code]")
    print("-" * 60)
    snippet = wrangle11.parm("snippet")
    if snippet:
        code = snippet.eval()
        # 줄 번호와 함께 출력
        lines = code.split('\\n')
        for i, line in enumerate(lines, 1):
            print("{:3d}: {}".format(i, line))
    print("-" * 60)
    
    # Cook 시도
    print("\\n[Cook Test]")
    try:
        wrangle11.cook(force=True)
        print("  [OK] Cook successful")
        
        # Geometry 확인
        geo = wrangle11.geometry()
        if geo:
            print("  Points:", len(geo.points()))
            print("  Primitives:", len(geo.prims()))
        
    except Exception as e:
        print("  [ERROR] Cook failed:")
        print("  ", str(e))
        
        # 상세 에러 정보
        if wrangle11.errors():
            print("\\n  Detailed errors:")
            for error in wrangle11.errors():
                print("   ", error)

print("\\n" + "="*80)
""")
    
    connector.disconnect()
    print("\n확인 완료!")


if __name__ == "__main__":
    check_wrangle_error()




