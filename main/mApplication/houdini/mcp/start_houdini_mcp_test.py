#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Houdini MCP 빠른 테스트 실행 스크립트

Maya Script Editor나 Python에서 이 파일을 실행하면
자동으로 후디니 MCP 연결을 테스트합니다.
"""

import sys
import os

# 경로 설정
script_dir = r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3"
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from houdini_mcp_quick_start import test_connection, print_guide


def main():
    """메인 실행 함수"""
    print("\n" + "="*80)
    print(" Houdini MCP 빠른 테스트")
    print("="*80)
    
    # 연결 테스트 시도
    if test_connection():
        print("\n✓ 모든 테스트가 성공했습니다!")
        print("\n더 많은 기능을 사용하려면 다음을 참고하세요:")
        print("  - HOUDINI_MCP_README.md")
        print("  - houdini_mcp_quick_start.py")
    else:
        print("\n✗ 연결 테스트 실패")
        print("\n가이드를 확인하세요:")
        print_guide()


if __name__ == "__main__":
    main()






