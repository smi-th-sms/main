# -*- coding: utf-8 -*-
"""
후디니 MCP 연결 테스트 스크립트
"""
import sys
import io

# UTF-8 출력 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3')

from houdini_integration.houdini_mcp_connector import HoudiniMCPConnector

print('=' * 80)
print(' 후디니 MCP 연결 테스트')
print('=' * 80)
print('\n연결을 시도합니다...')

connector = HoudiniMCPConnector()

if connector.connect():
    print('\n✓ 연결 성공!')
    
    # 기본 정보 가져오기
    print('\n[1] 후디니 버전 정보')
    connector.execute_code('''
import hou
print(f"Houdini: {hou.applicationVersionString()}")
print(f"Hip File: {hou.hipFile.path()}")
print(f"Frame: {hou.frame()}")
print(f"FPS: {hou.fps()}")
''')
    
    # 선택된 노드 확인
    print('\n[2] 선택된 노드')
    connector.execute_code('''
import hou
selected = hou.selectedNodes()
if selected:
    for node in selected:
        print(f"  - {node.path()} ({node.type().name()})")
else:
    print("  (선택된 노드 없음)")
''')
    
    # /obj 하위 노드 확인
    print('\n[3] /obj 하위 노드')
    connector.execute_code('''
import hou
obj = hou.node("/obj")
children = obj.children()
if children:
    for child in children[:10]:
        print(f"  - {child.name()} ({child.type().name()})")
    if len(children) > 10:
        print(f"  ... 외 {len(children) - 10}개")
else:
    print("  (하위 노드 없음)")
''')
    
    connector.disconnect()
    
    print('\n' + '=' * 80)
    print('✓ 테스트 완료! 후디니와 성공적으로 연결되었습니다!')
    print('=' * 80)
    
else:
    print('\n✗ 연결 실패!')
    print('후디니에서 MCP 서버가 실행 중인지 확인하세요.')
