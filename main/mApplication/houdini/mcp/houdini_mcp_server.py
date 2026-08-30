# -*- coding: utf-8 -*-
"""
Houdini MCP Server
후디니 내부에서 실행되는 MCP 서버

이 스크립트를 후디니의 Python Shell에서 실행하세요.

Usage (후디니 Python Shell):
    import sys
    sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
    from houdini_mcp_server import start_mcp_server
    
    start_mcp_server()
"""

import socket
import json
import threading
import traceback
import sys
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr


class HoudiniMCPServer:
    """후디니 MCP 서버"""
    
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.server_thread = None
        
    def start(self):
        """서버 시작"""
        if self.running:
            print("MCP Server is already running")
            return False
        
        try:
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            print(f"✓ Houdini MCP Server started on {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ Failed to start MCP Server: {e}")
            return False
    
    def stop(self):
        """서버 중지"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        print("✓ Houdini MCP Server stopped")
    
    def _run_server(self):
        """서버 실행 (별도 스레드)"""
        self.running = True
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            print(f"MCP Server listening on {self.host}:{self.port}")
            
            while self.running:
                try:
                    self.server_socket.settimeout(1.0)
                    conn, addr = self.server_socket.accept()
                    
                    # 각 연결을 별도 스레드에서 처리
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(conn, addr),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"Accept error: {e}")
                    break
                    
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
            self.running = False
    
    def _handle_client(self, conn, addr):
        """클라이언트 요청 처리"""
        try:
            # 데이터 수신
            data = conn.recv(16384)
            if not data:
                return
            
            # 명령 파싱
            command = json.loads(data.decode('utf-8'))
            
            # 명령 처리
            response = self._process_command(command)
            
            # 응답 전송
            conn.sendall(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            error_response = {
                'status': 'error',
                'message': f'Server error: {str(e)}'
            }
            try:
                conn.sendall(json.dumps(error_response).encode('utf-8'))
            except:
                pass
        finally:
            conn.close()
    
    def _process_command(self, command):
        """명령 처리"""
        cmd_type = command.get('type')
        
        if cmd_type == 'execute_code':
            return self._execute_code(command.get('params', {}))
        elif cmd_type == 'get_info':
            return self._get_info(command.get('params', {}))
        else:
            return {
                'status': 'error',
                'message': f'Unknown command type: {cmd_type}'
            }
    
    def _execute_code(self, params):
        """코드 실행"""
        code = params.get('code', '')
        
        if not code:
            return {
                'status': 'error',
                'message': 'No code provided'
            }
        
        try:
            # stdout/stderr 캡처
            stdout_capture = StringIO()
            stderr_capture = StringIO()
            
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # 코드 실행
                exec(code, globals())
            
            return {
                'status': 'success',
                'result': {
                    'stdout': stdout_capture.getvalue(),
                    'stderr': stderr_capture.getvalue()
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'traceback': traceback.format_exc()
            }
    
    def _get_info(self, params):
        """정보 가져오기"""
        try:
            import hou
            
            info = {
                'version': hou.applicationVersionString(),
                'hip_file': hou.hipFile.path(),
                'frame': hou.frame(),
                'fps': hou.fps(),
                'selected_nodes': [n.path() for n in hou.selectedNodes()]
            }
            
            return {
                'status': 'success',
                'result': info
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'traceback': traceback.format_exc()
            }


# 글로벌 서버 인스턴스
_mcp_server_instance = None


def start_mcp_server(host='localhost', port=9876):
    """
    MCP 서버 시작
    
    Args:
        host: 호스트 주소
        port: 포트 번호
        
    Returns:
        HoudiniMCPServer 인스턴스
    """
    global _mcp_server_instance
    
    if _mcp_server_instance and _mcp_server_instance.running:
        print("MCP Server is already running")
        return _mcp_server_instance
    
    _mcp_server_instance = HoudiniMCPServer(host, port)
    _mcp_server_instance.start()
    
    return _mcp_server_instance


def stop_mcp_server():
    """MCP 서버 중지"""
    global _mcp_server_instance
    
    if _mcp_server_instance:
        _mcp_server_instance.stop()
        _mcp_server_instance = None
    else:
        print("No MCP Server is running")


def get_server_status():
    """서버 상태 확인"""
    global _mcp_server_instance
    
    if _mcp_server_instance and _mcp_server_instance.running:
        print(f"✓ MCP Server is running on {_mcp_server_instance.host}:{_mcp_server_instance.port}")
        return True
    else:
        print("✗ MCP Server is not running")
        return False


# 메인 실행 (후디니에서 직접 실행 시)
if __name__ == "__main__":
    print("=" * 60)
    print("Houdini MCP Server")
    print("=" * 60)
    print("\n이 스크립트는 후디니 Python Shell에서 실행해야 합니다.")
    print("\n사용법:")
    print(">>> from houdini_mcp_server import start_mcp_server")
    print(">>> start_mcp_server()")
    print("\n서버 중지:")
    print(">>> from houdini_mcp_server import stop_mcp_server")
    print(">>> stop_mcp_server()")
    print("=" * 60)






