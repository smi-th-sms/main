#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
proxy_path 노드에서 @proxy_path 어트리뷰트의 고유한 값들 추출
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


with connect_houdini() as h:
    print("\n" + "="*80)
    print(" Extracting @proxy_path Attribute Values")
    print("="*80)
    
    h.execute("""
import hou

proxy_node = hou.node("/obj/assets/Deform/proxy_path")

if not proxy_node:
    print("[ERROR] proxy_path node not found")
else:
    print(f"\\n[OK] Found: {proxy_node.path()}")
    print(f"Type: {proxy_node.type().name()}")
    
    try:
        geo = proxy_node.geometry()
        
        if geo:
            print(f"\\n[Geometry Info]:")
            print(f"  Points: {len(geo.points())}")
            print(f"  Primitives: {len(geo.prims())}")
            
            # 모든 어트리뷰트 확인
            print(f"\\n[Point Attributes]:")
            for attrib in geo.pointAttribs():
                print(f"  - {attrib.name()} ({attrib.dataType().name()}, size={attrib.size()})")
            
            print(f"\\n[Primitive Attributes]:")
            for attrib in geo.primAttribs():
                print(f"  - {attrib.name()} ({attrib.dataType().name()}, size={attrib.size()})")
            
            # @proxy_path 어트리뷰트 찾기
            print(f"\\n" + "="*80)
            print("[Looking for proxy_path attribute]:")
            print("-" * 80)
            
            proxy_path_attrib = None
            attrib_type = None
            
            # Point attribute인지 확인
            if geo.findPointAttrib("proxy_path"):
                proxy_path_attrib = geo.findPointAttrib("proxy_path")
                attrib_type = "point"
                print(f"[OK] Found as POINT attribute")
            
            # Primitive attribute인지 확인
            elif geo.findPrimAttrib("proxy_path"):
                proxy_path_attrib = geo.findPrimAttrib("proxy_path")
                attrib_type = "primitive"
                print(f"[OK] Found as PRIMITIVE attribute")
            
            if proxy_path_attrib:
                print(f"  Data type: {proxy_path_attrib.dataType().name()}")
                print(f"  Size: {proxy_path_attrib.size()}")
                
                # 고유한 값들 추출
                print(f"\\n[Extracting unique values]:")
                print("-" * 80)
                
                unique_values = set()
                
                if attrib_type == "point":
                    for pt in geo.points():
                        val = pt.attribValue("proxy_path")
                        if val:  # 빈 문자열 제외
                            unique_values.add(val)
                
                elif attrib_type == "primitive":
                    for prim in geo.prims():
                        val = prim.attribValue("proxy_path")
                        if val:  # 빈 문자열 제외
                            unique_values.add(val)
                
                # 정렬해서 출력
                unique_values = sorted(list(unique_values))
                
                print(f"\\nFound {len(unique_values)} unique proxy_path values:")
                print("=" * 80)
                
                for i, value in enumerate(unique_values, 1):
                    # 각 값에 해당하는 프리미티브/포인트 개수 세기
                    if attrib_type == "point":
                        count = sum(1 for pt in geo.points() if pt.attribValue("proxy_path") == value)
                        print(f"  {i}. {value}")
                        print(f"     -> {count} points")
                    else:
                        count = sum(1 for prim in geo.prims() if prim.attribValue("proxy_path") == value)
                        print(f"  {i}. {value}")
                        print(f"     -> {count} primitives")
                
                # 세션에 저장
                hou.session.proxy_path_values = unique_values
                print(f"\\n[OK] Saved {len(unique_values)} values to session")
                
            else:
                print(f"[ERROR] 'proxy_path' attribute not found!")
                print(f"\\nAvailable point attributes:")
                for attrib in geo.pointAttribs():
                    print(f"  - {attrib.name()}")
                print(f"\\nAvailable primitive attributes:")
                for attrib in geo.primAttribs():
                    print(f"  - {attrib.name()}")
                
                hou.session.proxy_path_values = []
        else:
            print("[ERROR] No geometry on proxy_path node")
            hou.session.proxy_path_values = []
            
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        hou.session.proxy_path_values = []
""")






