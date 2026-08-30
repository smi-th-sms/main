# -*- coding: utf-8 -*-
"""
Houdini MCP Server for Claude Code
Claude Code에서 Houdini를 제어하기 위한 MCP 서버

실행 방법:
    py -3.11 houdini_mcp_claude_server.py

사전 조건:
    1. Houdini Python Shell에서 houdini_mcp_server.py 실행 (포트 9876)
    2. 이 스크립트를 Claude Code MCP 설정에 등록
"""

import sys
import socket
import json
import traceback
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types


HOUDINI_HOST = 'localhost'
HOUDINI_PORT = 9876
TIMEOUT = 15


def send_to_houdini(command: dict) -> dict:
    """후디니 TCP 서버에 명령 전송"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            s.connect((HOUDINI_HOST, HOUDINI_PORT))
            s.sendall(json.dumps(command).encode('utf-8'))

            # 응답 수신 (큰 응답 처리)
            chunks = []
            while True:
                try:
                    chunk = s.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    # 완전한 JSON인지 확인
                    try:
                        json.loads(b''.join(chunks).decode('utf-8'))
                        break
                    except json.JSONDecodeError:
                        continue
                except socket.timeout:
                    break

            data = b''.join(chunks)
            return json.loads(data.decode('utf-8'))

    except ConnectionRefusedError:
        return {
            'status': 'error',
            'message': f'Houdini MCP 서버에 연결할 수 없습니다 (port {HOUDINI_PORT}). '
                       f'Houdini Python Shell에서 start_mcp_server()를 실행하세요.'
        }
    except socket.timeout:
        return {'status': 'error', 'message': '연결 타임아웃: Houdini가 응답하지 않습니다.'}
    except Exception as e:
        return {'status': 'error', 'message': f'오류: {str(e)}\n{traceback.format_exc()}'}


def format_response(response: dict) -> str:
    """응답 포맷 변환"""
    if response.get('status') == 'success':
        result = response.get('result', {})
        if isinstance(result, dict):
            stdout = result.get('stdout', '').strip()
            stderr = result.get('stderr', '').strip()
            parts = []
            if stdout:
                parts.append(stdout)
            if stderr:
                parts.append(f"[stderr]\n{stderr}")
            return '\n'.join(parts) if parts else '(출력 없음)'
        else:
            return str(result)
    else:
        msg = response.get('message', '알 수 없는 오류')
        tb = response.get('traceback', '')
        if tb:
            return f"오류: {msg}\n{tb}"
        return f"오류: {msg}"


# MCP 서버 생성
server = Server("houdini-mcp")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="houdini_execute_code",
            description="Houdini에서 Python 코드를 실행합니다. hou 모듈이 사용 가능합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "실행할 Python 코드 (hou 모듈 사용 가능)"
                    }
                },
                "required": ["code"]
            }
        ),
        types.Tool(
            name="houdini_get_info",
            description="Houdini 버전, 현재 hip 파일, 프레임 등 기본 정보를 가져옵니다.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="houdini_get_selection",
            description="현재 선택된 노드 목록을 가져옵니다.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="houdini_list_nodes",
            description="지정한 경로의 하위 노드 목록을 가져옵니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "노드 경로 (예: /obj, /stage)",
                        "default": "/obj"
                    }
                }
            }
        ),
        types.Tool(
            name="houdini_create_node",
            description="Houdini에서 새 노드를 생성합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "parent_path": {
                        "type": "string",
                        "description": "부모 노드 경로 (예: /obj)"
                    },
                    "node_type": {
                        "type": "string",
                        "description": "노드 타입 (예: geo, cam, box)"
                    },
                    "node_name": {
                        "type": "string",
                        "description": "노드 이름 (선택사항)"
                    }
                },
                "required": ["parent_path", "node_type"]
            }
        ),
        types.Tool(
            name="houdini_set_parameter",
            description="Houdini 노드의 파라미터 값을 설정합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_path": {
                        "type": "string",
                        "description": "노드 경로"
                    },
                    "parm_name": {
                        "type": "string",
                        "description": "파라미터 이름"
                    },
                    "value": {
                        "description": "설정할 값 (숫자 또는 문자열)"
                    }
                },
                "required": ["node_path", "parm_name", "value"]
            }
        ),
        types.Tool(
            name="houdini_get_parameter",
            description="Houdini 노드의 파라미터 값을 가져옵니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_path": {
                        "type": "string",
                        "description": "노드 경로"
                    },
                    "parm_name": {
                        "type": "string",
                        "description": "파라미터 이름"
                    }
                },
                "required": ["node_path", "parm_name"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:

    if name == "houdini_execute_code":
        code = arguments.get("code", "")
        response = send_to_houdini({"type": "execute_code", "params": {"code": code}})
        text = format_response(response)

    elif name == "houdini_get_info":
        response = send_to_houdini({"type": "get_info", "params": {}})
        if response.get('status') == 'success':
            info = response.get('result', {})
            text = (
                f"Houdini Version: {info.get('version', 'N/A')}\n"
                f"Hip File: {info.get('hip_file', 'N/A')}\n"
                f"Frame: {info.get('frame', 'N/A')}\n"
                f"FPS: {info.get('fps', 'N/A')}\n"
                f"Selected Nodes: {info.get('selected_nodes', [])}"
            )
        else:
            text = format_response(response)

    elif name == "houdini_get_selection":
        code = """
import hou
selected = hou.selectedNodes()
if selected:
    for node in selected:
        print(f"{node.path()} ({node.type().name()})")
else:
    print("(선택된 노드 없음)")
"""
        response = send_to_houdini({"type": "execute_code", "params": {"code": code}})
        text = format_response(response)

    elif name == "houdini_list_nodes":
        path = arguments.get("path", "/obj")
        code = f"""
import hou
node = hou.node("{path}")
if node:
    children = node.children()
    print(f"{{node.path()}} 하위 노드 ({{len(children)}}개):")
    for child in children:
        print(f"  - {{child.name()}} ({{child.type().name()}})")
else:
    print("노드를 찾을 수 없습니다: {path}")
"""
        response = send_to_houdini({"type": "execute_code", "params": {"code": code}})
        text = format_response(response)

    elif name == "houdini_create_node":
        parent_path = arguments["parent_path"]
        node_type = arguments["node_type"]
        node_name = arguments.get("node_name")
        name_str = f'"{node_name}"' if node_name else 'None'
        code = f"""
import hou
parent = hou.node("{parent_path}")
if parent:
    new_node = parent.createNode("{node_type}", {name_str})
    print(f"생성됨: {{new_node.path()}} ({{new_node.type().name()}})")
else:
    print("부모 노드를 찾을 수 없습니다: {parent_path}")
"""
        response = send_to_houdini({"type": "execute_code", "params": {"code": code}})
        text = format_response(response)

    elif name == "houdini_set_parameter":
        node_path = arguments["node_path"]
        parm_name = arguments["parm_name"]
        value = arguments["value"]
        value_str = f'"{value}"' if isinstance(value, str) else str(value)
        code = f"""
import hou
node = hou.node("{node_path}")
if node:
    parm = node.parm("{parm_name}")
    if parm:
        parm.set({value_str})
        print(f"설정됨: {{node.path()}}.{parm_name} = {value_str}")
    else:
        print("파라미터를 찾을 수 없습니다: {parm_name}")
else:
    print("노드를 찾을 수 없습니다: {node_path}")
"""
        response = send_to_houdini({"type": "execute_code", "params": {"code": code}})
        text = format_response(response)

    elif name == "houdini_get_parameter":
        node_path = arguments["node_path"]
        parm_name = arguments["parm_name"]
        code = f"""
import hou
node = hou.node("{node_path}")
if node:
    parm = node.parm("{parm_name}")
    if parm:
        value = parm.eval()
        print(f"{{node.path()}}.{parm_name} = {{value}}")
    else:
        print("파라미터를 찾을 수 없습니다: {parm_name}")
else:
    print("노드를 찾을 수 없습니다: {node_path}")
"""
        response = send_to_houdini({"type": "execute_code", "params": {"code": code}})
        text = format_response(response)

    else:
        text = f"알 수 없는 도구: {name}"

    return [types.TextContent(type="text", text=text)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
