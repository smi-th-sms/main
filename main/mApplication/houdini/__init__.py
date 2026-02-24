# -*- coding: utf-8 -*-
"""
Houdini Integration Package
Houdini와의 통합 및 연동을 위한 패키지

주요 기능:
- MCP (Model Context Protocol) 서버/클라이언트
- Houdini Python 원격 실행
- 노드 생성 및 관리
- 파라미터 설정 및 조회
- KineFX 및 Rigging 도구

사용법:
    # Maya/Python 환경에서
    import sys
    sys.path.append('E:/script/pythonWorkSpace/main/mApplication')
    
    from houdini import HoudiniMCPConnector
    
    connector = HoudiniMCPConnector()
    connector.connect()
    result = connector.execute_code("print(hou.pwd())")
"""

# 주요 클래스 import
from .mcp.houdini_mcp_connector import HoudiniMCPConnector

# 편의 함수
def connect(host='localhost', port=9876):
    """
    Houdini MCP 서버에 빠르게 연결
    
    Args:
        host: 호스트 주소 (기본: localhost)
        port: 포트 번호 (기본: 9876)
    
    Returns:
        HoudiniMCPConnector 인스턴스
    
    Example:
        >>> from houdini import connect
        >>> hou = connect()
        >>> hou.execute_code("print(hou.pwd())")
    """
    connector = HoudiniMCPConnector(host=host, port=port)
    if connector.connect():
        print(f"✓ Houdini MCP 연결 성공: {host}:{port}")
        return connector
    else:
        print(f"✗ Houdini MCP 연결 실패: {host}:{port}")
        return None

def quick_start():
    """빠른 시작 가이드 출력"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                  Houdini Integration Quick Start                     ║
╚══════════════════════════════════════════════════════════════════════╝

1. Houdini에서 MCP 서버 시작:
   -------------------------------------------------------------------
   import sys
   sys.path.append('E:/script/pythonWorkSpace/main/mApplication')
   from houdini.houdini_mcp_server import start_mcp_server
   
   server = start_mcp_server()  # localhost:9876에서 시작
   -------------------------------------------------------------------

2. Maya/Python에서 연결:
   -------------------------------------------------------------------
   from houdini import connect
   
   hou = connect()
   result = hou.execute_code("print(hou.pwd())")
   print(result)
   -------------------------------------------------------------------

3. 주요 기능:
   - execute_code(code)          : Python 코드 실행
   - create_node(type, name)     : 노드 생성
   - set_parameter(node, parm, value) : 파라미터 설정
   - get_selected_nodes()        : 선택된 노드 조회
   - disconnect()                : 연결 종료

자세한 내용은 HOUDINI_MCP_README.md를 참조하세요.
""")

__all__ = [
    'HoudiniMCPConnector',
    'connect',
    'quick_start'
]

__version__ = '1.0.0'
__author__ = 'SUNGSEO'

