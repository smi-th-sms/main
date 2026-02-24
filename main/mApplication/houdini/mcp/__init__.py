# -*- coding: utf-8 -*-
"""
Houdini MCP (Model Context Protocol) Package
Houdini와의 MCP 통신을 위한 서버/클라이언트 모듈

주요 모듈:
- houdini_mcp_server: Houdini에서 실행되는 MCP 서버
- houdini_mcp_connector: Maya/Python에서 사용하는 MCP 클라이언트
- connect_to_houdini: 간편한 연결 유틸리티
- quick_connect: 빠른 연결 스크립트
"""

from .houdini_mcp_connector import HoudiniMCPConnector

__all__ = ['HoudiniMCPConnector']










