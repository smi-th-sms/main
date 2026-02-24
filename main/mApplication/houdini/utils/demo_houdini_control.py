#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Houdini Control Demo
후디니를 Maya/Python에서 제어하는 데모
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")

from connect_to_houdini import connect_houdini


def demo_create_geometry():
    """Geometry 노드 생성 데모"""
    print("\n" + "="*80)
    print(" Demo: Create Geometry Node")
    print("="*80)
    
    with connect_houdini() as h:
        # 1. Geometry 노드 생성
        print("\n[1] Creating geometry node...")
        result = h.create_geo("demo_geo")
        print(f"    Created: {result}")
        
        # 2. Box 노드 생성
        print("\n[2] Creating box inside geometry...")
        h.execute("""
geo = hou.node("/obj/demo_geo")
if geo:
    box = geo.createNode("box", "demo_box")
    box.parm("sizex").set(2.0)
    box.parm("sizey").set(2.0)
    box.parm("sizez").set(2.0)
    box.setDisplayFlag(True)
    box.setRenderFlag(True)
    print(f"    Box created: {box.path()}")
else:
    print("    Geometry not found")
""")
        
        # 3. 위치 설정
        print("\n[3] Setting position...")
        h.execute("""
geo = hou.node("/obj/demo_geo")
if geo:
    geo.parm("ty").set(2.0)
    print(f"    Position set: y=2.0")
""")
        
        print("\n[OK] Demo completed!")
        print("="*80)


def demo_node_query():
    """노드 정보 조회 데모"""
    print("\n" + "="*80)
    print(" Demo: Query Scene Information")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] All /obj nodes:")
        h.execute("""
obj = hou.node("/obj")
for child in obj.children():
    print(f"  - {child.name():<20} ({child.type().name()})")
""")
        
        print("\n[2] Selected nodes:")
        h.get_selected()
        
        print("\n[OK] Query completed!")
        print("="*80)


def demo_execute_code():
    """커스텀 코드 실행 데모"""
    print("\n" + "="*80)
    print(" Demo: Execute Custom Code")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Creating multiple spheres...")
        h.execute("""
obj = hou.node("/obj")

# Create 5 spheres in a line
for i in range(5):
    geo = obj.createNode("geo", f"sphere_{i}")
    geo.parm("tx").set(i * 3)
    
    # Create sphere inside
    sphere = geo.createNode("sphere", "sphere1")
    sphere.parm("rad").setExpression("$T * 0.1 + 1")  # Animated radius
    sphere.setDisplayFlag(True)
    sphere.setRenderFlag(True)

obj.layoutChildren()
print("Created 5 animated spheres!")
""")
        
        print("\n[OK] Demo completed!")
        print("="*80)


def main_menu():
    """메인 메뉴"""
    demos = {
        '1': ('Create Geometry Demo', demo_create_geometry),
        '2': ('Query Scene Demo', demo_node_query),
        '3': ('Execute Code Demo', demo_execute_code),
    }
    
    print("\n" + "="*80)
    print(" Houdini Control Demo Menu")
    print("="*80)
    
    for key, (name, _) in demos.items():
        print(f"{key}. {name}")
    print("0. Exit")
    
    choice = input("\nSelect (0-3): ").strip()
    
    if choice == '0':
        print("\nExiting...")
        return False
    elif choice in demos:
        _, demo_func = demos[choice]
        demo_func()
        return True
    else:
        print("\nInvalid choice!")
        return True


if __name__ == "__main__":
    print("\n" + "="*80)
    print(" Houdini MCP Control Demo")
    print("="*80)
    print("\nRunning all demos...\n")
    
    # Run all demos
    try:
        demo_create_geometry()
        input("\nPress Enter to continue to next demo...")
        
        demo_node_query()
        input("\nPress Enter to continue to next demo...")
        
        demo_execute_code()
        
        print("\n" + "="*80)
        print("[OK] All demos completed successfully!")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Demo failed: {e}")






