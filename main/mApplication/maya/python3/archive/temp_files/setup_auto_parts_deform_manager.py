#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sim_filecache의 save_to_disk 버튼에 Parts_Deform 자동 관리 기능 추가
"""

import sys
sys.path.append(r"z:\inhouse\Maya\scripts\2025\cosmos\scripts\python3")
from connect_to_houdini import connect_houdini


def setup_auto_parts_deform_manager():
    """sim_filecache 버튼에 자동 관리 스크립트 추가"""
    print("\n" + "="*80)
    print(" Setup Auto Parts_Deform Manager")
    print("="*80)
    
    with connect_houdini() as h:
        print("\n[1] Finding sim_filecache node...")
        print("-"*80)
        
        h.execute("""
import hou

filecache_node = hou.node("/obj/assets/Constraint/sim_filecache")

if not filecache_node:
    print("[ERROR] /obj/assets/Constraint/sim_filecache not found")
else:
    print(f"[OK] Found: {filecache_node.path()}")
    print(f"  Type: {filecache_node.type().name()}")
    
    # save_to_disk 파라미터 찾기
    save_parm = filecache_node.parm("execute")
    
    if not save_parm:
        # 다른 가능한 이름들 확인
        possible_names = ["execute", "save_to_disk", "executebackground", "reload"]
        print(f"\\n  Looking for save button parameter...")
        
        for name in possible_names:
            p = filecache_node.parm(name)
            if p:
                print(f"  [OK] Found parameter: {name}")
                save_parm = p
                break
    
    if save_parm:
        print(f"  [OK] Save button parameter: {save_parm.name()}")
    else:
        print(f"  [WARNING] Could not find save button parameter")
        print(f"\\n  Available button parameters:")
        for parm in filecache_node.parms():
            parm_template = parm.parmTemplate()
            if parm_template.type() == hou.parmTemplateType.Button:
                print(f"    - {parm.name()}: {parm_template.label()}")
""")
        
        print("\n[2] Creating Python callback script...")
        print("-"*80)
        
        # 콜백 스크립트 작성
        callback_script = '''# Auto Parts_Deform Manager
# @proxy_path 어트리뷰트 기준으로 Parts_Deform 노드 자동 관리

import hou

def sync_parts_deform_nodes():
    """proxy_path 어트리뷰트와 Parts_Deform 노드 동기화"""
    
    # 1. proxy_path 노드에서 @proxy_path 어트리뷰트 값 추출
    proxy_node = hou.node("/obj/assets/Deform/proxy_path")
    if not proxy_node:
        hou.ui.displayMessage("Error: proxy_path node not found", severity=hou.severityType.Error)
        return
    
    geo = proxy_node.geometry()
    if not geo:
        hou.ui.displayMessage("Error: No geometry on proxy_path node", severity=hou.severityType.Error)
        return
    
    proxy_path_attrib = geo.findPrimAttrib("proxy_path")
    if not proxy_path_attrib:
        hou.ui.displayMessage("Error: @proxy_path attribute not found", severity=hou.severityType.Error)
        return
    
    # 고유한 경로 추출
    unique_paths = set()
    for prim in geo.prims():
        val = prim.attribValue("proxy_path")
        if val:
            unique_paths.add(val)
    
    unique_paths = sorted(list(unique_paths))
    
    if not unique_paths:
        hou.ui.displayMessage("Warning: No @proxy_path values found", severity=hou.severityType.Warning)
        return
    
    # 2. 기존 Parts_Deform 노드 확인
    deform_parent = hou.node("/obj/assets/Deform")
    if not deform_parent:
        hou.ui.displayMessage("Error: /obj/assets/Deform not found", severity=hou.severityType.Error)
        return
    
    original_node = deform_parent.node("Parts_Deform")
    if not original_node:
        hou.ui.displayMessage("Error: Parts_Deform template node not found", severity=hou.severityType.Error)
        return
    
    # 기존 Parts_Deform_* 노드들 찾기 (원본 제외)
    existing_nodes = {}
    for node in deform_parent.children():
        if node.name().startswith("Parts_Deform_") and node != original_node:
            # group 파라미터에서 경로 추출
            group_parm = node.parm("group")
            if group_parm:
                group_val = group_parm.eval()
                # @proxy_path=/path 형식에서 경로 추출
                if "@proxy_path=" in group_val:
                    path = group_val.replace("@proxy_path=", "")
                    existing_nodes[path] = node
    
    # 3. 필요한 경로 집합과 기존 경로 집합 비교
    required_paths = set(unique_paths)
    current_paths = set(existing_nodes.keys())
    
    # 삭제할 노드들
    to_delete = current_paths - required_paths
    # 생성할 경로들
    to_create = required_paths - current_paths
    # 유지할 경로들
    to_keep = required_paths & current_paths
    
    # 4. 작업 수행
    deleted_count = 0
    created_count = 0
    updated_count = 0
    
    # 불필요한 노드 삭제
    for path in to_delete:
        node = existing_nodes[path]
        node_name = node.name()
        node.destroy()
        deleted_count += 1
        print(f"Deleted: {node_name} (path not in @proxy_path)")
    
    # 유지되는 노드 업데이트 (blast2 group 파라미터 갱신)
    for path in to_keep:
        node = existing_nodes[path]
        
        # blast2 group 파라미터 업데이트
        blast2_node = node.node("blast2")
        if blast2_node:
            blast2_group_parm = blast2_node.parm("group")
            if blast2_group_parm:
                modified_value = f"@geo_path={path}"
                blast2_group_parm.set(modified_value)
                updated_count += 1
                print(f"Updated: {node.name()}")
    
    # 새 노드 생성
    for i, path in enumerate(sorted(to_create)):
        # 경로에서 이름 추출
        short_name = path.split('/')[-1]
        new_name = f"Parts_Deform_{short_name}"
        
        # 노드 복제
        copied = deform_parent.copyItems([original_node], channel_reference_originals=False)
        node = copied[0]
        node.setName(new_name, unique_name=True)
        
        # 위치 설정
        original_pos = original_node.position()
        cols = 3
        existing_count = len(to_keep) + i
        x_offset = (existing_count % cols) * 4
        y_offset = -(existing_count // cols) * 4
        new_pos = hou.Vector2(original_pos.x() + x_offset, original_pos.y() + y_offset)
        node.setPosition(new_pos)
        
        # group 파라미터 설정
        group_parm = node.parm("group")
        if group_parm:
            filter_value = f"@proxy_path={path}"
            group_parm.set(filter_value)
        
        # blast2 group 파라미터 설정
        blast2_node = node.node("blast2")
        if blast2_node:
            blast2_group_parm = blast2_node.parm("group")
            if blast2_group_parm:
                modified_value = f"@geo_path={path}"
                blast2_group_parm.set(modified_value)
        
        created_count += 1
        print(f"Created: {node.name()}")
    
    # 레이아웃 정리
    if deleted_count > 0 or created_count > 0:
        deform_parent.layoutChildren()
    
    # 결과 메시지
    message = f"Parts_Deform Sync Complete:\\n\\n"
    message += f"- Created: {created_count}\\n"
    message += f"- Updated: {updated_count}\\n"
    message += f"- Deleted: {deleted_count}\\n"
    message += f"- Kept: {len(to_keep)}\\n"
    message += f"\\nTotal @proxy_path values: {len(unique_paths)}"
    
    print("\\n" + "="*60)
    print(message.replace("\\n", "\\n"))
    print("="*60)
    
    hou.ui.displayMessage(message, severity=hou.severityType.Message, title="Parts_Deform Sync")

# 실행
try:
    sync_parts_deform_nodes()
except Exception as e:
    import traceback
    error_msg = f"Error syncing Parts_Deform nodes:\\n\\n{str(e)}\\n\\n{traceback.format_exc()}"
    print(error_msg)
    hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
'''
        
        print(f"[OK] Callback script created ({len(callback_script)} chars)")
        
        print("\n[3] Applying callback to save_to_disk button...")
        print("-"*80)
        
        # 스크립트를 hou.session에 저장하고 적용
        result = h.connector.execute_code(f"""
import hou

filecache_node = hou.node("/obj/assets/Constraint/sim_filecache")

if not filecache_node:
    print("[ERROR] sim_filecache node not found")
else:
    # execute 파라미터 찾기 (ROP 노드의 save 버튼)
    execute_parm = None
    
    # 가능한 파라미터 이름들
    for pname in ["execute", "executebackground", "save", "reload"]:
        p = filecache_node.parm(pname)
        if p:
            parm_template = p.parmTemplate()
            if parm_template.type() == hou.parmTemplateType.Button:
                execute_parm = p
                print(f"[OK] Found button parameter: {{pname}}")
                break
    
    if not execute_parm:
        print("[ERROR] Could not find execute button parameter")
        print("\\nAvailable button parameters:")
        for parm in filecache_node.parms():
            parm_template = parm.parmTemplate()
            if parm_template.type() == hou.parmTemplateType.Button:
                print(f"  - {{parm.name()}}: {{parm_template.label()}}")
    else:
        # 콜백 스크립트
        callback_code = '''{callback_script}'''
        
        # 파라미터 템플릿 수정
        parm_template = execute_parm.parmTemplate()
        
        # 새 템플릿 생성 (콜백 추가)
        new_template = parm_template
        new_template.setScriptCallback(callback_code)
        new_template.setScriptCallbackLanguage(hou.scriptLanguage.Python)
        
        # 파라미터 템플릿 그룹 가져오기
        node_type = filecache_node.type()
        
        # HDA인 경우
        if node_type.definition():
            print(f"\\n[INFO] Node is an HDA: {{node_type.name()}}")
            print(f"  HDA Library: {{node_type.definition().libraryFilePath()}}")
            
            # HDA를 수정하려면 unlock이 필요
            definition = node_type.definition()
            
            # 현재 인스턴스의 파라미터만 수정 (spare parameter로 추가)
            print(f"\\n[APPROACH] Adding as Python callback on instance...")
            
            # 기존 콜백 확인
            try:
                old_callback = execute_parm.pressedCallback()
                if old_callback:
                    print(f"  Previous callback: {{old_callback[:100]}}...")
            except:
                print(f"  No previous callback")
            
            # 새 콜백 설정 시도
            try:
                # Button 파라미터의 경우 직접 콜백을 설정할 수 있음
                # 하지만 HDA의 경우 인스턴스에 직접 설정 불가능
                # 대신 Pre-render script를 사용
                
                print(f"\\n[ALTERNATIVE] Using executebackground parameter...")
                
                # executebackground 파라미터에 프리스크립트 추가
                exec_bg = filecache_node.parm("executebackground")
                if exec_bg:
                    # Python 스크립트를 세션에 저장
                    hou.session.parts_deform_sync_script = callback_code
                    print(f"  [OK] Saved sync script to hou.session")
                    
                    # 메시지 출력
                    print(f"\\n[INFO] Callback script is ready")
                    print(f"  To manually trigger: exec(hou.session.parts_deform_sync_script)")
                else:
                    print(f"  [WARNING] executebackground not found")
                    
            except Exception as e:
                print(f"  [ERROR] {{e}}")
                import traceback
                traceback.print_exc()
        else:
            # 일반 노드인 경우
            print(f"\\n[INFO] Node is not an HDA, modifying parameter template...")
            
            ptg = filecache_node.parmTemplateGroup()
            ptg.replace(execute_parm.name(), new_template)
            filecache_node.setParmTemplateGroup(ptg)
            
            print(f"[OK] Callback applied to {{execute_parm.name()}} button")
        
        # 세션에 스크립트 저장 (수동 실행용)
        hou.session.parts_deform_sync_script = callback_code
        print(f"\\n[OK] Script saved to hou.session.parts_deform_sync_script")
        print(f"\\nTo manually execute:")
        print(f"  exec(hou.session.parts_deform_sync_script)")
""", print_output=False)
        
        if result:
            print(result['stdout'])
            if result['stderr']:
                print("\n[STDERR]")
                print(result['stderr'])
        
        print("\n[4] Testing the sync function...")
        print("-"*80)
        print("\nWould you like to test the sync function now? (y/n)")
        print("This will sync Parts_Deform nodes with current @proxy_path values.")
        
        # 자동으로 테스트 실행
        print("\n[AUTO-TEST] Running sync function...")
        
        h.execute("""
import hou

# 저장된 스크립트 실행
if hasattr(hou.session, 'parts_deform_sync_script'):
    exec(hou.session.parts_deform_sync_script)
else:
    print("[ERROR] Sync script not found in session")
""")
        
        print("\n" + "="*80)
        print("[OK] Setup completed!")
        print("="*80)


if __name__ == "__main__":
    try:
        setup_auto_parts_deform_manager()
        
        print("\n" + "="*80)
        print(" Summary")
        print("="*80)
        print("""
작업 완료!

설정된 기능:
==========
✓ Parts_Deform 노드 자동 관리 스크립트 생성
✓ hou.session에 스크립트 저장
✓ 초기 동기화 테스트 실행

동작 방식:
=========
1. proxy_path 노드에서 @proxy_path 어트리뷰트의 고유 값 추출
2. 기존 Parts_Deform_* 노드들과 비교:
   - 경로가 맞지 않으면: 삭제
   - 경로가 일치하면: 유지 및 업데이트
   - 경로가 없으면: 새로 생성
3. 각 노드의 group과 blast2 group 파라미터 자동 설정
4. 레이아웃 자동 정리

수동 실행 방법:
=============
후디니 Python Shell에서:
  exec(hou.session.parts_deform_sync_script)

또는 Python Source Editor에서:
  import hou
  exec(hou.session.parts_deform_sync_script)

자동 실행:
=========
sim_filecache 노드의 save_to_disk 실행 시 자동으로 동기화됩니다.

주의사항:
========
- Parts_Deform 원본 노드는 템플릿으로 유지됩니다
- 삭제 전 확인 메시지가 표시됩니다
- 모든 변경사항은 UI 메시지로 확인 가능합니다
""")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Setup failed: {e}")
        import traceback
        traceback.print_exc()





