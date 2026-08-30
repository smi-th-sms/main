# -*- coding: utf-8 -*-
"""
빠른 Houdini MCP 연결 스크립트
MCP 서버가 실행 중일 때 이 스크립트를 실행하세요.
"""

import sys
import os

# 경로 설정
script_dir = r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3"
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from houdini_integration.houdini_mcp_connector import HoudiniMCPConnector


def main():
    """메인 실행 함수"""
    print("\n" + "="*80)
    print(" Houdini MCP 연결")
    print("="*80)
    
    # 연결 생성
    connector = HoudiniMCPConnector()
    
    print("\n[1] Houdini에 연결 중...")
    if not connector.connect():
        print("\n✗ 연결 실패!")
        print("Houdini에서 MCP 서버가 실행 중인지 확인하세요.")
        return
    
    print("\n[2] Houdini 정보 가져오기")
    print("-" * 80)
    connector.execute_code("""
import hou
print(f"Houdini Version: {hou.applicationVersionString()}")
print(f"Hip File: {hou.hipFile.path()}")
print(f"Current Frame: {hou.frame()}")
print(f"FPS: {hou.fps()}")
""")
    
    print("\n[3] 선택된 노드 확인")
    print("-" * 80)
    connector.execute_code("""
import hou
selected = hou.selectedNodes()
if selected:
    print(f"선택된 노드: {len(selected)}개")
    for node in selected:
        print(f"  - {node.path()} ({node.type().name()})")
else:
    print("선택된 노드가 없습니다.")
""")
    
    print("\n[4] Scene 노드 구조")
    print("-" * 80)
    connector.execute_code("""
import hou
obj = hou.node("/obj")
children = obj.children()
if children:
    print(f"/obj 하위 노드: {len(children)}개")
    for child in children[:10]:  # 최대 10개만 표시
        print(f"  - {child.name()} ({child.type().name()})")
    if len(children) > 10:
        print(f"  ... 외 {len(children) - 10}개")
else:
    print("/obj 하위에 노드가 없습니다.")
""")
    
    print("\n" + "="*80)
    print("[OK] 연결 테스트 완료!")
    print("="*80)
    print("\n이제 다음과 같이 Houdini를 제어할 수 있습니다:")
    print("""
# 노드 생성
connector.create_node("/obj", "geo", "my_geo")

# 파라미터 설정
connector.set_parameter("/obj/my_geo", "tz", 5.0)

# 커스텀 코드 실행
connector.execute_code('''
import hou
print("Hello from Houdini!")
# 여기에 원하는 Houdini Python 코드 작성
''')

# 연결 종료
connector.disconnect()
""")
    
    # 연결 유지 (사용자가 계속 사용할 수 있도록)
    print("\n연결을 유지합니다. 'connector' 변수로 계속 사용할 수 있습니다.")
    
    return connector


if __name__ == "__main__":
    connector = main()

