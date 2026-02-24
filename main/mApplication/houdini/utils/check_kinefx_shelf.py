# -*- coding: utf-8 -*-
"""
KineFX Shelf 상태 확인 및 수정 스크립트
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from houdini_integration.houdini_mcp_connector import HoudiniMCPConnector


def check_kinefx_shelf():
    """KineFX Shelf 상태 확인"""
    connector = HoudiniMCPConnector()
    
    if not connector.connect():
        print("[ERROR] Houdini 연결 실패!")
        return
    
    print("="*70)
    print(" KineFX Shelf 진단")
    print("="*70)
    
    connector.execute_code("""
import hou

print("\\n[1] Houdini 버전 확인")
print("-" * 60)
version = hou.applicationVersion()
print("Version: {}".format(hou.applicationVersionString()))
print("Major: {}, Minor: {}".format(version[0], version[1]))

if version[0] < 18 or (version[0] == 18 and version[1] < 5):
    print("\\n[WARNING] KineFX는 Houdini 18.5 이상에서 사용 가능합니다.")
else:
    print("[OK] KineFX 지원 버전입니다.")

print("\\n[2] 사용 가능한 Shelf 목록")
print("-" * 60)
shelves = hou.shelves.shelves()
kinefx_shelves = [name for name in shelves.keys() if 'kinefx' in name.lower() or 'character' in name.lower()]

print("KineFX 관련 Shelf:")
for shelf_name in kinefx_shelves:
    shelf = shelves[shelf_name]
    tools = shelf.tools()
    print("  - {} ({} tools)".format(shelf_name, len(tools)))

print("\\n전체 Shelf 수: {}".format(len(shelves)))
print("\\nKineFX 관련 Shelf 찾기:")
for name in sorted(shelves.keys()):
    if any(keyword in name.lower() for keyword in ['kinefx', 'character', 'rig', 'skeleton']):
        print("  - {}".format(name))

print("\\n[3] Shelf Sets 확인")
print("-" * 60)
shelf_sets = hou.shelves.shelfSets()
print("Shelf Sets 수: {}".format(len(shelf_sets)))
for name in sorted(shelf_sets.keys()):
    if any(keyword in name.lower() for keyword in ['kinefx', 'character', 'rig']):
        print("  - {}".format(name))

print("\\n[4] 현재 Desktop의 Shelf 확인")
print("-" * 60)
try:
    desktop = hou.ui.curDesktop()
    shelf_dock = desktop.shelfDock()
    
    if shelf_dock:
        current_shelf_set = shelf_dock.shelfSet()
        if current_shelf_set:
            print("Current Shelf Set: {}".format(current_shelf_set.name()))
            shelves_in_set = current_shelf_set.shelves()
            print("Shelves in current set: {}".format(len(shelves_in_set)))
            for shelf in shelves_in_set:
                print("  - {} ({} tools)".format(shelf.name(), len(shelf.tools())))
        else:
            print("[WARNING] No shelf set is currently active")
    else:
        print("[WARNING] Shelf dock not found")
except Exception as e:
    print("[ERROR] {}".format(str(e)))

print("\\n[5] KineFX 노드 타입 확인 (KineFX가 설치되어 있는지)")
print("-" * 60)
kinefx_nodes = []
try:
    # SOP 카테고리에서 KineFX 노드 찾기
    sop_category = hou.sopNodeTypeCategory()
    for node_type in sop_category.nodeTypes().values():
        type_name = node_type.name()
        if any(keyword in type_name.lower() for keyword in ['rig', 'skeleton', 'capture', 'deform', 'joint', 'bone']):
            kinefx_nodes.append(type_name)
    
    print("KineFX 관련 노드 타입 (일부):")
    for node_name in sorted(kinefx_nodes)[:20]:
        print("  - {}".format(node_name))
    
    if len(kinefx_nodes) > 20:
        print("  ... 외 {} 개".format(len(kinefx_nodes) - 20))
        
    print("\\n총 {} 개의 KineFX 관련 노드 타입 발견".format(len(kinefx_nodes)))
    
except Exception as e:
    print("[ERROR] {}".format(str(e)))

print("\\n" + "="*70)
print(" 해결 방법")
print("="*70)
print("""
1. Shelf 표시 확인:
   - 상단 Shelf 영역에서 우클릭
   - 'Shelves' 메뉴에서 'KineFX' 체크 확인

2. Shelf Set 변경:
   - Shelf 영역 왼쪽의 드롭다운 메뉴
   - 다른 Shelf Set 선택 후 다시 원래대로

3. Shelf 새로고침:
   - Windows > Shelf Editor
   - 'Shelves' 탭에서 'kinefx' 찾아서 활성화

4. Houdini 재시작

5. 환경 변수 확인:
   - Edit > Preferences > Shelves
   - 'Use custom shelf definitions' 확인
""")
    """)
    
    connector.disconnect()


if __name__ == "__main__":
    check_kinefx_shelf()




