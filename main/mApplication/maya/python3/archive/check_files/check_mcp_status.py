#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Houdini MCP 연결 상태 확인
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def check_mcp_status():
    """MCP 연결 상태 및 후디니 정보 확인"""
    print("\n" + "="*80)
    print(" Houdini MCP Connection Status")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[Connection]")
        print("-"*80)
        print("  Status: Connected")
        print("  Host: localhost")
        print("  Port: 9876")
        print("  Protocol: TCP/IP Socket")
        
        print("\n[Houdini Information]")
        print("-"*80)
        h.execute("""
import hou
import os

# 후디니 버전
version = hou.applicationVersionString()
print(f"  Version: {version}")

# 현재 파일
hip_file = hou.hipFile.path()
hip_name = os.path.basename(hip_file)
print(f"  File: {hip_name}")
print(f"  Path: {hip_file}")

# 수정 상태
modified = hou.hipFile.hasUnsavedChanges()
print(f"  Modified: {'Yes' if modified else 'No'}")

# 프레임 정보
current_frame = hou.frame()
start_frame, end_frame = hou.playbar.frameRange()
fps_val = hou.fps()
print(f"  Frame: {current_frame} / {start_frame}-{end_frame}")
print(f"  FPS: {fps_val}")
""")
        
        print("\n[Scene Information]")
        print("-"*80)
        h.execute("""
import hou

# OBJ 레벨 노드들
obj = hou.node("/obj")
children = obj.children()

print(f"  Nodes in /obj: {len(children)}")

# 노드 타입 통계
node_types = {}
for child in children:
    node_type = child.type().name()
    node_types[node_type] = node_types.get(node_type, 0) + 1

if node_types:
    print("\\n  Node Types:")
    for ntype, count in sorted(node_types.items()):
        print(f"    - {ntype}: {count}")

# 선택된 노드
selected = hou.selectedNodes()
print(f"\\n  Selected Nodes: {len(selected)}")
if selected:
    for node in selected[:5]:
        print(f"    - {node.path()}")
    if len(selected) > 5:
        print(f"    ... and {len(selected) - 5} more")
""")
        
        print("\n[Desktop Information]")
        print("-"*80)
        h.execute("""
import hou

try:
    desktop = hou.ui.curDesktop()
    print(f"  Desktop: {desktop.name()}")
    
    # 열린 패널들
    panes = desktop.paneTabs()
    print(f"  Open Panes: {len(panes)}")
    
    pane_types = {}
    for pane in panes:
        ptype = str(pane.type())
        pane_types[ptype] = pane_types.get(ptype, 0) + 1
    
    if pane_types:
        print("\\n  Pane Types:")
        for ptype, count in sorted(pane_types.items()):
            print(f"    - {ptype}: {count}")
            
except Exception as e:
    print(f"  Could not get desktop info: {e}")
""")
        
        print("\n[System Information]")
        print("-"*80)
        h.execute("""
import hou
import sys
import os

print(f"  Python: {sys.version.split()[0]}")
print(f"  OS: {os.name}")

# 메모리 사용량 (가능한 경우)
try:
    import psutil
    process = psutil.Process()
    mem_info = process.memory_info()
    mem_mb = mem_info.rss / 1024 / 1024
    print(f"  Memory Usage: {mem_mb:.1f} MB")
except:
    print(f"  Memory Usage: N/A")

# TEMP 디렉토리
temp_dir = hou.getenv("TEMP") or hou.getenv("TMP")
print(f"  TEMP: {temp_dir}")
""")
        
        print("\n" + "="*80)
        print("[OK] MCP Connection Active and Healthy!")
        print("="*80)


if __name__ == "__main__":
    try:
        check_mcp_status()
        
        print("\n" + "="*80)
        print(" Quick Commands")
        print("="*80)
        print("""
You can now control Houdini from Python!

Examples:
  # Execute code
  from connect_to_houdini import connect_houdini
  with connect_houdini() as h:
      h.execute("print('Hello from Houdini!')")
  
  # Create geometry
  with connect_houdini() as h:
      h.create_geo("my_geo")
  
  # Get scene info
  with connect_houdini() as h:
      h.get_info()

For more examples, see:
  - HOUDINI_MCP_QUICK_GUIDE.md
  - demo_houdini_control.py
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Connection check failed: {e}")
        print("\nMake sure:")
        print("  1. Houdini is running")
        print("  2. MCP server is started in Houdini")
        print("     (Run: import houdinimcp; houdinimcp.start_server())")
        import traceback
        traceback.print_exc()






