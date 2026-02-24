# -*- coding: utf-8 -*-
"""
Houdini MCP (Model Context Protocol) Connector
후디니와 MCP 연결을 위한 통합 도구

Usage:
    from houdini_mcp_connector import HoudiniMCPConnector
    
    connector = HoudiniMCPConnector()
    connector.connect()
    result = connector.execute_code("print(hou.pwd())")
    print(result)
"""

import socket
import json
import time
from typing import Dict, Any, Optional, Union


class HoudiniMCPConnector:
    """후디니 MCP 연결 클래스"""
    
    DEFAULT_HOST = 'localhost'
    DEFAULT_PORT = 9876
    
    def __init__(self, host: str = None, port: int = None, timeout: int = 10):
        """
        Args:
            host: 호스트 주소 (기본값: localhost)
            port: 포트 번호 (기본값: 9876)
            timeout: 연결 타임아웃 (초)
        """
        self.host = host or self.DEFAULT_HOST
        self.port = port or self.DEFAULT_PORT
        self.timeout = timeout
        self.connected = False
        self._socket = None
        
    def connect(self) -> bool:
        """
        후디니 MCP 서버에 연결
        
        Returns:
            bool: 연결 성공 여부
        """
        try:
            if self._socket:
                self.disconnect()
                
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))
            self.connected = True
            print(f"[OK] Connected to Houdini MCP at {self.host}:{self.port}")
            return True
            
        except socket.timeout:
            print(f"[ERROR] Connection timeout: Houdini MCP server is not responding.")
            self.connected = False
            return False
            
        except ConnectionRefusedError:
            print(f"[ERROR] Connection refused: Houdini MCP server is not running on port {self.port}.")
            self.connected = False
            return False
            
        except Exception as e:
            print(f"[ERROR] Connection error: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """연결 종료"""
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            self._socket = None
        self.connected = False
        print("[OK] Disconnected from Houdini MCP")
    
    def send_command(self, command: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        명령을 후디니에 전송
        
        Args:
            command: 전송할 명령 딕셔너리
            
        Returns:
            응답 딕셔너리 또는 None
        """
        if not self.connected:
            if not self.connect():
                return None
        
        try:
            # 명령 전송
            command_json = json.dumps(command)
            self._socket.sendall(command_json.encode('utf-8'))
            
            # 응답 수신
            data = self._socket.recv(16384)
            response = json.loads(data.decode('utf-8'))
            
            return response
            
        except socket.timeout:
            print("[ERROR] Command execution timeout")
            self.connected = False
            return None
            
        except Exception as e:
            print(f"[ERROR] Command send error: {e}")
            self.connected = False
            return None
    
    def execute_code(self, code: str, print_output: bool = True) -> Optional[Dict[str, Any]]:
        """
        후디니에서 Python 코드 실행
        
        Args:
            code: 실행할 Python 코드
            print_output: 출력 결과를 자동으로 출력할지 여부
            
        Returns:
            실행 결과 딕셔너리
        """
        command = {
            "type": "execute_code",
            "params": {
                "code": code
            }
        }
        
        response = self.send_command(command)
        
        if response and response.get('status') == 'success':
            result = response.get('result', {})
            
            if print_output:
                stdout = result.get('stdout', '').strip()
                stderr = result.get('stderr', '').strip()
                
                if stdout:
                    print("=== Output ===")
                    print(stdout)
                    
                if stderr:
                    print("=== Error ===")
                    print(stderr)
            
            return result
        else:
            if response:
                print(f"[ERROR] Execution failed: {response.get('message', 'Unknown error')}")
            return None
    
    def get_node_info(self, node_path: str) -> Optional[Dict[str, Any]]:
        """
        노드 정보 가져오기
        
        Args:
            node_path: 노드 경로 (예: "/obj/geo1")
            
        Returns:
            노드 정보 딕셔너리
        """
        code = f"""
import hou
node = hou.node("{node_path}")
if node:
    info = {{
        "name": node.name(),
        "path": node.path(),
        "type": node.type().name(),
        "position": node.position(),
        "children_count": len(node.children())
    }}
    print(info)
else:
    print("Node not found: {node_path}")
"""
        return self.execute_code(code, print_output=True)
    
    def get_selection(self) -> Optional[list]:
        """
        현재 선택된 노드들 가져오기
        
        Returns:
            선택된 노드 경로 리스트
        """
        code = """
import hou
selected = hou.selectedNodes()
for node in selected:
    print(node.path())
"""
        result = self.execute_code(code, print_output=True)
        return result
    
    def create_node(self, parent_path: str, node_type: str, node_name: str = None) -> Optional[Dict[str, Any]]:
        """
        새 노드 생성
        
        Args:
            parent_path: 부모 노드 경로
            node_type: 노드 타입
            node_name: 노드 이름 (선택사항)
            
        Returns:
            생성된 노드 정보
        """
        name_param = f'"{node_name}"' if node_name else 'None'
        code = f"""
import hou
parent = hou.node("{parent_path}")
if parent:
    new_node = parent.createNode("{node_type}", {name_param})
    print(f"Created: {{new_node.path()}}")
else:
    print("Parent node not found: {parent_path}")
"""
        return self.execute_code(code, print_output=True)
    
    def set_parameter(self, node_path: str, parm_name: str, value: Union[str, int, float]) -> Optional[Dict[str, Any]]:
        """
        노드 파라미터 설정
        
        Args:
            node_path: 노드 경로
            parm_name: 파라미터 이름
            value: 설정할 값
            
        Returns:
            실행 결과
        """
        if isinstance(value, str):
            value_str = f'"{value}"'
        else:
            value_str = str(value)
            
        code = f"""
import hou
node = hou.node("{node_path}")
if node:
    parm = node.parm("{parm_name}")
    if parm:
        parm.set({value_str})
        print(f"Set {{node.path()}}.{parm_name} = {value_str}")
    else:
        print("Parameter not found: {parm_name}")
else:
    print("Node not found: {node_path}")
"""
        return self.execute_code(code, print_output=True)
    
    def get_parameter(self, node_path: str, parm_name: str) -> Optional[Dict[str, Any]]:
        """
        노드 파라미터 가져오기
        
        Args:
            node_path: 노드 경로
            parm_name: 파라미터 이름
            
        Returns:
            파라미터 값
        """
        code = f"""
import hou
node = hou.node("{node_path}")
if node:
    parm = node.parm("{parm_name}")
    if parm:
        value = parm.eval()
        print(f"{{node.path()}}.{parm_name} = {{value}}")
    else:
        print("Parameter not found: {parm_name}")
else:
    print("Node not found: {node_path}")
"""
        return self.execute_code(code, print_output=True)
    
    def test_connection(self) -> bool:
        """
        연결 테스트
        
        Returns:
            연결 성공 여부
        """
        code = """
import hou
print(f"Houdini Version: {hou.applicationVersionString()}")
print(f"Hip File: {hou.hipFile.path()}")
print("Connection test successful!")
"""
        result = self.execute_code(code, print_output=True)
        return result is not None
    
    def __enter__(self):
        """Context manager 지원"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 지원"""
        self.disconnect()
        return False
    
    def __del__(self):
        """소멸자"""
        self.disconnect()


# 편의 함수들
def quick_execute(code: str, host: str = None, port: int = None) -> Optional[Dict[str, Any]]:
    """
    빠른 코드 실행 (연결 후 자동 종료)
    
    Args:
        code: 실행할 코드
        host: 호스트 주소
        port: 포트 번호
        
    Returns:
        실행 결과
    """
    with HoudiniMCPConnector(host, port) as connector:
        return connector.execute_code(code)


def quick_connect_test(host: str = None, port: int = None) -> bool:
    """
    빠른 연결 테스트
    
    Args:
        host: 호스트 주소
        port: 포트 번호
        
    Returns:
        연결 성공 여부
    """
    with HoudiniMCPConnector(host, port) as connector:
        return connector.test_connection()


# 메인 실행 (테스트)
if __name__ == "__main__":
    print("=" * 60)
    print("Houdini MCP Connector Test")
    print("=" * 60)
    
    # 연결 테스트
    connector = HoudiniMCPConnector()
    
    if connector.connect():
        print("\n[1] 연결 테스트")
        connector.test_connection()
        
        print("\n[2] 선택된 노드 확인")
        connector.get_selection()
        
        print("\n[3] 커스텀 코드 실행")
        connector.execute_code("""
import hou
print("Current Desktop:", hou.ui.curDesktop().name())
print("Frame:", hou.frame())
""")
        
        connector.disconnect()
    else:
        print("\n후디니 MCP 서버 시작 방법:")
        print("1. 후디니를 실행합니다")
        print("2. Python Shell에서 다음 코드를 실행하세요:")
        print("""
# 후디니 MCP 서버 시작
import socket
import json
import threading

def mcp_server():
    HOST = 'localhost'
    PORT = 9876
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"MCP Server listening on {HOST}:{PORT}")
        
        while True:
            conn, addr = s.accept()
            with conn:
                data = conn.recv(16384)
                command = json.loads(data.decode('utf-8'))
                
                if command['type'] == 'execute_code':
                    code = command['params']['code']
                    try:
                        exec(code)
                        response = {'status': 'success', 'result': {'stdout': '', 'stderr': ''}}
                    except Exception as e:
                        response = {'status': 'error', 'message': str(e)}
                    
                    conn.sendall(json.dumps(response).encode('utf-8'))

threading.Thread(target=mcp_server, daemon=True).start()
""")

