#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CFX Apply Buttons 진단 스크립트
"""

import sys
import os

# MCP Connector
sys.path.insert(0, r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
import houdini_mcp_connector

print("\n" + "="*80)
print(" Diagnosing CFX Apply Buttons")
print("="*80)

# 후디니 연결
connector = houdini_mcp_connector.HoudiniMCPConnector()
if not connector.connect():
    print("[ERROR] Failed to connect to Houdini")
    sys.exit(1)

print("\n[Step 1] Checking Houdini Scene Structure")
print("-" * 80)

# 씬 구조 확인
code = """
import hou

print("[1.1] Checking /obj/assets node...")
assets_node = hou.node("/obj/assets")
if assets_node:
    print("    [OK] /obj/assets exists")
    print("    Type:", assets_node.type().name())
    
    print("\\n[1.2] Checking /obj/assets/FBX node...")
    fbx_node = assets_node.node("FBX")
    if fbx_node:
        print("    [OK] /obj/assets/FBX exists")
        print("    Type:", fbx_node.type().name())
        
        print("\\n[1.3] Checking parameters on FBX node...")
        all_parms = fbx_node.parms()
        print("    Total parameters:", len(all_parms))
        
        # 필요한 파라미터 확인
        required_parms = ['animation_import', 'character_import', 'hair_import']
        for parm_name in required_parms:
            parm = fbx_node.parm(parm_name)
            if parm:
                print("    [OK] Parameter '{}' exists".format(parm_name))
                print("        Type:", parm.parmTemplate().type())
                print("        Current value:", repr(parm.eval()[:80] if parm.eval() else ''))
            else:
                print("    [ERROR] Parameter '{}' NOT FOUND".format(parm_name))
        
        # 파라미터 이름 리스트 (비슷한 이름 찾기)
        print("\\n[1.4] Searching for similar parameter names...")
        import_parms = [p.name() for p in all_parms if 'import' in p.name().lower()]
        if import_parms:
            print("    Parameters with 'import' in name:")
            for pname in import_parms[:10]:  # 처음 10개만
                print("        -", pname)
        else:
            print("    No parameters with 'import' found")
            
        anim_parms = [p.name() for p in all_parms if 'anim' in p.name().lower()]
        if anim_parms:
            print("    Parameters with 'anim' in name:")
            for pname in anim_parms[:10]:
                print("        -", pname)
        
        char_parms = [p.name() for p in all_parms if 'char' in p.name().lower()]
        if char_parms:
            print("    Parameters with 'char' in name:")
            for pname in char_parms[:10]:
                print("        -", pname)
                
        hair_parms = [p.name() for p in all_parms if 'hair' in p.name().lower()]
        if hair_parms:
            print("    Parameters with 'hair' in name:")
            for pname in hair_parms[:10]:
                print("        -", pname)
                
    else:
        print("    [ERROR] /obj/assets/FBX NOT found")
        print("\\n    Available nodes under /obj/assets:")
        for child in assets_node.children():
            print("        -", child.name(), "(type: {})".format(child.type().name()))
else:
    print("    [ERROR] /obj/assets NOT found")
    print("\\n    Available nodes in /obj:")
    obj_node = hou.node("/obj")
    if obj_node:
        for child in obj_node.children():
            print("        -", child.name(), "(type: {})".format(child.type().name()))
"""

result = connector.execute_code(code)
if result:
    print(result.get("output", ""))

print("\n" + "="*80)
print("[Step 2] Testing Parameter Set Operation")
print("-" * 80)

# 파라미터 설정 테스트
code2 = """
import hou

test_path = "/test/path/to/animation.fbx"

print("[2.1] Testing parameter.set() operation...")
assets_node = hou.node("/obj/assets")
if assets_node:
    fbx_node = assets_node.node("FBX")
    if fbx_node:
        # animation_import 파라미터 테스트
        anim_parm = fbx_node.parm("animation_import")
        if anim_parm:
            print("    Testing animation_import parameter...")
            print("    Before:", repr(anim_parm.eval()))
            
            try:
                anim_parm.set(test_path)
                print("    [OK] Set operation succeeded")
                print("    After:", repr(anim_parm.eval()))
                
                # 원래 값으로 복구 (빈 문자열)
                anim_parm.set("")
                print("    [OK] Reset to empty string")
            except Exception as e:
                print("    [ERROR] Set operation failed:", str(e))
        else:
            print("    [ERROR] animation_import parameter not found")
            print("    Cannot test set operation")
    else:
        print("    [ERROR] FBX node not found")
else:
    print("    [ERROR] Assets node not found")
"""

result2 = connector.execute_code(code2)
if result2:
    print(result2.get("output", ""))

print("\n" + "="*80)
print("[Step 3] Testing UI Apply Button")
print("-" * 80)

# UI에서 Apply 버튼 테스트
code3 = """
import sys
script_path = r"T:\\scripts\\python\\application\\houdini\\houdini21.0\\script"
if script_path not in sys.path:
    sys.path.insert(0, script_path)

import cfx_assets_ui
import importlib
importlib.reload(cfx_assets_ui)

# UI 생성
window = cfx_assets_ui.launch()

print("[3.1] UI launched successfully")

# 테스트 경로 설정
test_anim_path = "/test/animation/test_anim.fbx"

# Shot Anim File ComboBox에 테스트 데이터 추가
window.shot_anim_file_combo.clear()
window.shot_anim_file_combo.addItem("test_anim.fbx", test_anim_path)
window.shot_anim_file_combo.setCurrentIndex(0)

print("[3.2] Test data added to Shot Anim File ComboBox")
print("    File:", window.shot_anim_file_combo.currentText())
print("    Path:", window.shot_anim_file_combo.currentData())

# Apply 버튼 수동 호출
print("\\n[3.3] Calling on_apply_shot_anim_file()...")
try:
    window.on_apply_shot_anim_file()
    print("    [OK] Method executed without exception")
except Exception as e:
    print("    [ERROR] Exception:", str(e))
    import traceback
    traceback.print_exc()

# 파라미터 값 확인
print("\\n[3.4] Checking parameter value after Apply...")
assets_node = hou.node("/obj/assets")
if assets_node:
    fbx_node = assets_node.node("FBX")
    if fbx_node:
        anim_parm = fbx_node.parm("animation_import")
        if anim_parm:
            final_value = anim_parm.eval()
            print("    Parameter value:", repr(final_value))
            
            if final_value == test_anim_path:
                print("    [SUCCESS] Value matches expected path!")
            else:
                print("    [FAILED] Value does not match")
                print("    Expected:", test_anim_path)
                print("    Got:", final_value)
        else:
            print("    [ERROR] Parameter not found")
    else:
        print("    [ERROR] FBX node not found")
else:
    print("    [ERROR] Assets node not found")
"""

result3 = connector.execute_code(code3)
if result3:
    print(result3.get("output", ""))

print("\n" + "="*80)
print(" Diagnosis Summary")
print("="*80)

connector.disconnect()

print()
print("진단 완료!")
print()
print("확인 사항:")
print("=========")
print("1. /obj/assets 노드가 존재하는가?")
print("2. /obj/assets/FBX 노드가 존재하는가?")
print("3. FBX 노드에 필요한 파라미터가 있는가?")
print("   - animation_import")
print("   - character_import")
print("   - hair_import")
print("4. 파라미터 set() 동작이 정상인가?")
print("5. UI Apply 버튼이 정상 동작하는가?")
print()
print("문제 해결:")
print("=========")
print("1. 파라미터 이름이 다른 경우:")
print("   → 실제 파라미터 이름 확인 후 코드 수정")
print()
print("2. 파라미터가 없는 경우:")
print("   → HDA 정의에 파라미터 추가 필요")
print()
print("3. 노드가 없는 경우:")
print("   → Auto Setup으로 HDA 생성 먼저 실행")
print()
print("="*80)





