# -*- coding: utf-8 -*-
"""
Houdini MCP Quick Start Guide
후디니 MCP 빠른 시작 가이드

이 스크립트는 Maya/Python 환경에서 실행하여 후디니와 연결을 테스트합니다.
"""

from houdini_mcp_connector import HoudiniMCPConnector, quick_connect_test, quick_execute


def print_guide():
    """사용 가이드 출력"""
    print("\n" + "=" * 80)
    print(" Houdini MCP 연결 가이드")
    print("=" * 80)
    
    print("\n[단계 1] 후디니에서 MCP 서버 시작")
    print("-" * 80)
    print("후디니를 실행하고 Python Shell 또는 Python Source Editor에서 다음을 실행하세요:")
    print("""
import sys
sys.path.append(r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3")
from houdini_mcp_server import start_mcp_server

# 서버 시작
start_mcp_server()
""")
    
    print("\n[단계 2] Maya/Python에서 후디니에 연결")
    print("-" * 80)
    print("Maya Script Editor 또는 Python에서 다음을 실행하세요:")
    print("""
import sys
sys.path.append(r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3")
from houdini_mcp_connector import HoudiniMCPConnector

# 연결 생성
connector = HoudiniMCPConnector()
connector.connect()

# 후디니에서 코드 실행
connector.execute_code('''
import hou
print("Hello from Houdini!")
print(f"Version: {hou.applicationVersionString()}")
''')
""")
    
    print("\n[단계 3] 다양한 기능 사용")
    print("-" * 80)
    print("""
# 선택된 노드 확인
connector.get_selection()

# 노드 정보 가져오기
connector.get_node_info("/obj")

# 새 노드 생성
connector.create_node("/obj", "geo", "my_geo")

# 파라미터 설정
connector.set_parameter("/obj/my_geo", "tz", 5.0)

# 파라미터 가져오기
connector.get_parameter("/obj/my_geo", "tz")

# 연결 종료
connector.disconnect()
""")
    
    print("\n" + "=" * 80)


def test_connection():
    """연결 테스트"""
    print("\n" + "=" * 80)
    print(" 후디니 MCP 연결 테스트")
    print("=" * 80)
    
    print("\n연결을 시도합니다...")
    
    connector = HoudiniMCPConnector()
    
    if connector.connect():
        print("\n✓ 연결 성공!")
        
        # 기본 정보 가져오기
        print("\n[1] 후디니 버전 정보")
        connector.execute_code("""
import hou
print(f"Houdini: {hou.applicationVersionString()}")
print(f"Hip File: {hou.hipFile.path()}")
print(f"Frame: {hou.frame()}")
print(f"FPS: {hou.fps()}")
""")
        
        # 선택된 노드 확인
        print("\n[2] 선택된 노드")
        connector.execute_code("""
import hou
selected = hou.selectedNodes()
if selected:
    for node in selected:
        print(f"  - {node.path()} ({node.type().name()})")
else:
    print("  (선택된 노드 없음)")
""")
        
        # /obj 하위 노드 확인
        print("\n[3] /obj 하위 노드")
        connector.execute_code("""
import hou
obj = hou.node("/obj")
children = obj.children()
if children:
    for child in children[:10]:  # 최대 10개만 표시
        print(f"  - {child.name()} ({child.type().name()})")
    if len(children) > 10:
        print(f"  ... 외 {len(children) - 10}개")
else:
    print("  (하위 노드 없음)")
""")
        
        connector.disconnect()
        
        print("\n" + "=" * 80)
        print("✓ 테스트 완료!")
        print("=" * 80)
        
        return True
        
    else:
        print("\n✗ 연결 실패!")
        print("\n후디니에서 MCP 서버를 시작했는지 확인하세요.")
        print_guide()
        return False


def example_workflow():
    """예제 워크플로우"""
    print("\n" + "=" * 80)
    print(" 후디니 MCP 예제 워크플로우")
    print("=" * 80)
    
    with HoudiniMCPConnector() as connector:
        if not connector.connected:
            print("✗ 후디니에 연결할 수 없습니다.")
            return
        
        print("\n[1] Geometry 노드 생성")
        connector.create_node("/obj", "geo", "test_geo")
        
        print("\n[2] 노드 위치 설정")
        connector.set_parameter("/obj/test_geo", "tx", 0)
        connector.set_parameter("/obj/test_geo", "ty", 0)
        connector.set_parameter("/obj/test_geo", "tz", 5)
        
        print("\n[3] Box 노드 생성")
        connector.create_node("/obj/test_geo", "box", "test_box")
        
        print("\n[4] Box 크기 설정")
        connector.set_parameter("/obj/test_geo/test_box", "sizex", 2.0)
        connector.set_parameter("/obj/test_geo/test_box", "sizey", 2.0)
        connector.set_parameter("/obj/test_geo/test_box", "sizez", 2.0)
        
        print("\n[5] 결과 확인")
        connector.get_node_info("/obj/test_geo")
        
        print("\n" + "=" * 80)
        print("✓ 워크플로우 완료!")
        print("=" * 80)


def main_menu():
    """메인 메뉴"""
    while True:
        print("\n" + "=" * 80)
        print(" Houdini MCP Quick Start Menu")
        print("=" * 80)
        print("\n1. 사용 가이드 보기")
        print("2. 연결 테스트")
        print("3. 예제 워크플로우 실행")
        print("0. 종료")
        
        choice = input("\n선택 (0-3): ").strip()
        
        if choice == '1':
            print_guide()
        elif choice == '2':
            test_connection()
        elif choice == '3':
            example_workflow()
        elif choice == '0':
            print("\n종료합니다.")
            break
        else:
            print("\n잘못된 선택입니다.")


if __name__ == "__main__":
    # 메뉴 대신 바로 테스트 실행
    print_guide()
    print("\n\n3초 후 연결 테스트를 시작합니다...")
    
    import time
    time.sleep(1)
    
    test_connection()






