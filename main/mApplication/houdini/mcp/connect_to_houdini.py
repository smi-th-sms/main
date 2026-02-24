# -*- coding: utf-8 -*-
"""
Maya/Python에서 Houdini MCP 서버에 간단하게 연결하는 스크립트

사용법 (Maya Script Editor 또는 Python):
    import sys
    sys.path.append(r"E:/script/pythonWorkSpace/main/mApplication")
    
    # 방법 1: 패키지 import
    from houdini import connect
    hou_connector = connect()
    
    # 방법 2: 모듈 직접 import
    from houdini.mcp import connect_to_houdini
    hou_connector = connect_to_houdini.connect()
"""

import sys
import os

# 경로 설정
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from .houdini_mcp_connector import HoudiniMCPConnector


# 글로벌 connector 인스턴스
_global_connector = None


def connect(host='localhost', port=9876, auto_info=True):
    """
    Houdini MCP 서버에 연결
    
    Args:
        host: 호스트 주소 (기본: localhost)
        port: 포트 번호 (기본: 9876)
        auto_info: 연결 후 자동으로 정보 출력 (기본: True)
    
    Returns:
        HoudiniMCPConnector 인스턴스
    """
    global _global_connector
    
    print("="*70)
    print(" Houdini MCP Connection")
    print("="*70)
    
    # 기존 연결이 있으면 재사용
    if _global_connector and _global_connector.connected:
        print("\n[OK] 이미 연결되어 있습니다.")
        return _global_connector
    
    # 새 연결 생성
    _global_connector = HoudiniMCPConnector(host, port)
    
    if _global_connector.connect():
        print("\n[OK] Houdini에 연결되었습니다!")
        
        if auto_info:
            print("\n" + "-"*70)
            print(" Houdini 정보")
            print("-"*70)
            _global_connector.execute_code("""
import hou
print("Version: {}".format(hou.applicationVersionString()))
print("Hip File: {}".format(hou.hipFile.path()))
print("Frame: {}".format(hou.frame()))
print("FPS: {}".format(hou.fps()))
""")
        
        print("\n" + "="*70)
        print(" 사용 가능한 함수:")
        print("="*70)
        print("  hou_connector.execute_code(code)    - Houdini에서 코드 실행")
        print("  hou_connector.get_selection()       - 선택된 노드 가져오기")
        print("  hou_connector.create_node()         - 노드 생성")
        print("  hou_connector.set_parameter()       - 파라미터 설정")
        print("  hou_connector.get_parameter()       - 파라미터 가져오기")
        print("  hou_connector.disconnect()          - 연결 종료")
        print("="*70 + "\n")
        
        return _global_connector
    else:
        print("\n[ERROR] Houdini 연결 실패!")
        print("Houdini에서 MCP 서버가 실행 중인지 확인하세요:")
        print("""
1. Houdini Python Shell에서 실행:
   import sys
   sys.path.append(r"z:\\inhouse\\Maya\\scripts\\2025\\cosmos\\scripts\\python3")
   from houdini_mcp_server import start_mcp_server
   start_mcp_server()
""")
        return None


def disconnect():
    """연결 종료"""
    global _global_connector
    
    if _global_connector:
        _global_connector.disconnect()
        _global_connector = None
        print("[OK] 연결이 종료되었습니다.")
    else:
        print("[INFO] 연결된 상태가 아닙니다.")


def get_connector():
    """현재 connector 인스턴스 반환"""
    return _global_connector


def execute(code):
    """
    간편한 코드 실행 함수
    
    Args:
        code: 실행할 Houdini Python 코드
    """
    if not _global_connector or not _global_connector.connected:
        print("[ERROR] Houdini에 연결되지 않았습니다. connect()를 먼저 실행하세요.")
        return None
    
    return _global_connector.execute_code(code)


# 편의 함수들
def get_hip_info():
    """Houdini 파일 정보 가져오기"""
    return execute("""
import hou
print("="*60)
print("Houdini File Information")
print("="*60)
print("Version: {}".format(hou.applicationVersionString()))
print("Hip File: {}".format(hou.hipFile.path()))
print("Hip Name: {}".format(hou.hipFile.name()))
print("Frame Range: {} - {}".format(hou.playbar.frameRange()[0], hou.playbar.frameRange()[1]))
print("Current Frame: {}".format(hou.frame()))
print("FPS: {}".format(hou.fps()))
print("="*60)
""")


def get_selected():
    """선택된 노드 정보"""
    return execute("""
import hou
selected = hou.selectedNodes()
if selected:
    print("="*60)
    print("Selected Nodes: {} node(s)".format(len(selected)))
    print("="*60)
    for node in selected:
        print("  - {} ({})".format(node.path(), node.type().name()))
        pos = node.position()
        print("    Position: ({:.2f}, {:.2f})".format(pos[0], pos[1]))
else:
    print("No nodes selected.")
""")


def list_obj_nodes():
    """Scene의 /obj 노드 목록"""
    return execute("""
import hou
obj = hou.node("/obj")
children = obj.children()

print("="*60)
print("/obj Network Nodes: {} node(s)".format(len(children)))
print("="*60)

if children:
    for child in children:
        print("  - {} ({})".format(child.name(), child.type().name()))
        if child.children():
            print("    Children: {}".format(len(child.children())))
else:
    print("  (No nodes)")
print("="*60)
""")


# 메인 실행 (스크립트를 직접 실행할 때)
if __name__ == "__main__":
    hou_connector = connect()
    
    if hou_connector:
        print("\n\n예제 명령어:")
        print("-" * 70)
        print("# 선택된 노드 확인")
        print("get_selected()")
        print("\n# Scene 노드 목록")
        print("list_obj_nodes()")
        print("\n# 커스텀 코드 실행")
        print('execute("import hou; print(hou.pwd())")')
        print("\n# 연결 종료")
        print("disconnect()")
        print("-" * 70)
