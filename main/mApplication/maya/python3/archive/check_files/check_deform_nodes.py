#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Deform 노드 아래의 모든 노드 확인
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


with connect_houdini() as h:
    print("\n[1] Checking /obj/assets/Deform nodes...")
    print("="*80)
    
    h.execute("""
import hou

deform = hou.node("/obj/assets/Deform")

if deform:
    print(f"Found Deform network: {deform.path()}")
    print(f"Type: {deform.type().name()}")
    print(f"\\nAll child nodes:")
    print("-" * 80)
    
    children = deform.children()
    print(f"Total: {len(children)} nodes\\n")
    
    for i, node in enumerate(children, 1):
        print(f"{i:3}. {node.name():<40} ({node.type().name()})")
        
        # 특별히 관심있는 노드 표시
        name_lower = node.name().lower()
        if 'pants' in name_lower or 'deform' in name_lower or 'parts' in name_lower:
            print(f"      -> PATH: {node.path()}")
            print(f"      -> Type details: {node.type().description()}")
            
            # group 관련 파라미터 확인
            for parm_name in ['group', 'groupname', 'primgroup', 'group_name']:
                parm = node.parm(parm_name)
                if parm:
                    print(f"      -> Parameter '{parm_name}': {parm.eval()}")
else:
    print("[ERROR] /obj/assets/Deform not found")
    
    print("\\nTrying /obj/assets...")
    assets = hou.node("/obj/assets")
    if assets:
        print(f"Found: {assets.path()}")
        print("Children:")
        for node in assets.children():
            print(f"  - {node.name()} ({node.type().name()})")
""")






