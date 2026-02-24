"""
Convert aiStandard to Lambert
Maya에서 aiStandard 셰이더를 Lambert로 변환하는 스크립트

사용법 1 (UI):
    import importlib
    from python3.tools import convert_aistandard_to_lambert
    importlib.reload(convert_aistandard_to_lambert)
    convert_aistandard_to_lambert.show_ui()

사용법 2 (직접 실행):
    import importlib
    from python3.tools import convert_aistandard_to_lambert
    importlib.reload(convert_aistandard_to_lambert)
    convert_aistandard_to_lambert.convert_all()

사용법 3 (리로드 포함):
    from python3.tools.convert_aistandard_to_lambert import reload_and_show
    reload_and_show()
"""

import maya.cmds as cmds
import maya.mel as mel
import sys
import importlib


def convert_aistandard_to_lambert():
    """aiStandard 셰이더를 Lambert로 변환"""
    
    print("\n" + "="*70)
    print("aiStandard to Lambert 변환 시작")
    print("="*70)
    
    # 모든 aiStandard 셰이더 찾기
    aistandard_shaders = cmds.ls(type='aiStandard')
    
    if not aistandard_shaders:
        print("⚠ aiStandard 셰이더를 찾을 수 없습니다.")
        return 0
    
    print(f"\n✓ {len(aistandard_shaders)}개의 aiStandard 셰이더 발견:")
    for shader in aistandard_shaders:
        print(f"  - {shader}")
    
    converted_count = 0
    failed_count = 0
    
    for ai_shader in aistandard_shaders:
        try:
            print(f"\n[처리 중] {ai_shader}")
            
            # 셰이더가 실제로 존재하는지 확인
            if not cmds.objExists(ai_shader):
                print(f"  ⚠ 셰이더가 존재하지 않습니다. 건너뜁니다.")
                failed_count += 1
                continue
            
            # 원본 이름 저장 (숫자 붙는 것 방지)
            original_name = ai_shader
            
            # 연결된 shading engine 찾기
            shading_engines = cmds.listConnections(ai_shader, type='shadingEngine')
            
            if not shading_engines:
                print(f"  ⚠ Shading Engine을 찾을 수 없습니다. 건너뜁니다.")
                failed_count += 1
                continue
            
            sg = shading_engines[0]
            print(f"  ✓ Shading Engine: {sg}")
            
            # aiStandard의 가능한 color 속성들 체크
            color_attrs = ['color', 'Kd_color', 'KsColor', 'baseColor']
            color_value = (0.5, 0.5, 0.5)  # 기본값
            color_attr_found = None
            
            for attr in color_attrs:
                if cmds.attributeQuery(attr, node=ai_shader, exists=True):
                    try:
                        color_value = cmds.getAttr(f"{ai_shader}.{attr}")[0]
                        color_attr_found = attr
                        print(f"  ✓ 기존 Color ({attr}): {color_value}")
                        break
                    except:
                        continue
            
            if not color_attr_found:
                print(f"  ℹ Color 속성을 찾을 수 없어 기본값 사용: {color_value}")
            
            # 연결된 텍스처 확인 (가능한 모든 color 속성 체크)
            color_connections = None
            for attr in color_attrs:
                if cmds.attributeQuery(attr, node=ai_shader, exists=True):
                    try:
                        connections = cmds.listConnections(f"{ai_shader}.{attr}", 
                                                          source=True, 
                                                          destination=False, 
                                                          plugs=True)
                        if connections:
                            color_connections = connections
                            print(f"  ✓ 텍스처 연결 발견 ({attr}): {connections[0]}")
                            break
                    except:
                        continue
            
            # 기존 aiStandard를 임시 이름으로 변경 (이름 충돌 방지)
            temp_name = f"{ai_shader}_TEMP_TO_DELETE"
            if cmds.objExists(ai_shader):
                cmds.rename(ai_shader, temp_name)
                print(f"  ✓ aiStandard 임시 이름 변경: {temp_name}")
            
            # Lambert 셰이더 생성 (원래 이름으로)
            lambert_shader = cmds.shadingNode('lambert', asShader=True, 
                                             name=original_name)
            
            # 만약 Maya가 숫자를 붙였다면, 다시 원래 이름으로 rename
            if lambert_shader != original_name:
                if cmds.objExists(original_name):
                    # 혹시 원래 이름이 이미 있으면 삭제
                    cmds.delete(original_name)
                lambert_shader = cmds.rename(lambert_shader, original_name)
            
            print(f"  ✓ Lambert 셰이더 생성: {lambert_shader}")
            
            # Color 값 복사
            if color_connections:
                # 텍스처 연결이 있는 경우
                try:
                    source_plug = color_connections[0]
                    cmds.connectAttr(source_plug, f"{lambert_shader}.color", force=True)
                    print(f"  ✓ 텍스처 연결 복사 완료")
                except Exception as e:
                    print(f"  ⚠ 텍스처 연결 실패, 단색으로 설정: {str(e)}")
                    cmds.setAttr(f"{lambert_shader}.color", 
                               color_value[0], color_value[1], color_value[2], 
                               type='double3')
            else:
                # 단색인 경우
                cmds.setAttr(f"{lambert_shader}.color", 
                           color_value[0], color_value[1], color_value[2], 
                           type='double3')
                print(f"  ✓ Color 값 설정 완료")
            
            # Lambert를 Shading Engine에 연결
            cmds.connectAttr(f"{lambert_shader}.outColor", 
                           f"{sg}.surfaceShader", 
                           force=True)
            print(f"  ✓ Lambert를 Shading Engine에 연결")
            
            # 임시 이름의 aiStandard 삭제
            try:
                if cmds.objExists(temp_name):
                    cmds.delete(temp_name)
                    print(f"  ✓ aiStandard 셰이더 삭제: {original_name}")
            except Exception as e:
                print(f"  ⚠ aiStandard 삭제 실패: {str(e)}")
            
            converted_count += 1
            print(f"  ✅ 변환 완료: {original_name} (aiStandard → Lambert)")
            
        except Exception as e:
            import traceback
            print(f"  ✗ 변환 실패: {ai_shader}")
            print(f"  ✗ 에러: {str(e)}")
            print(f"  ✗ 상세:\n{traceback.format_exc()}")
            failed_count += 1
    
    # 결과 출력
    print("\n" + "="*70)
    print("변환 완료!")
    print(f"  성공: {converted_count}개")
    print(f"  실패: {failed_count}개")
    print(f"  총: {len(aistandard_shaders)}개")
    print("="*70 + "\n")
    
    return converted_count


def convert_all():
    """모든 aiStandard를 Lambert로 변환 (대화상자 포함)"""
    
    # aiStandard 셰이더 개수 확인
    aistandard_shaders = cmds.ls(type='aiStandard')
    
    if not aistandard_shaders:
        result = cmds.confirmDialog(
            title="알림",
            message="aiStandard 셰이더를 찾을 수 없습니다.",
            button=["확인"],
            defaultButton="확인"
        )
        return 0
    
    # 확인 대화상자
    result = cmds.confirmDialog(
        title="aiStandard to Lambert 변환",
        message=f"{len(aistandard_shaders)}개의 aiStandard 셰이더를 Lambert로 변환하시겠습니까?",
        button=["변환", "취소"],
        defaultButton="변환",
        cancelButton="취소",
        dismissString="취소"
    )
    
    if result == "변환":
        converted_count = convert_aistandard_to_lambert()
        
        # 완료 메시지
        if converted_count > 0:
            cmds.confirmDialog(
                title="완료",
                message=f"{converted_count}개의 aiStandard 셰이더가 Lambert로 변환되었습니다!",
                button=["확인"],
                defaultButton="확인"
            )
        
        return converted_count
    
    return 0


def show_ui():
    """간단한 UI 생성"""
    window_name = "aiStandardToLambertWindow"
    
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)
    
    window = cmds.window(
        window_name,
        title="aiStandard to Lambert Converter",
        widthHeight=(450, 250),
        sizeable=True,
        resizeToFitChildren=True
    )
    
    main_layout = cmds.columnLayout(
        adjustableColumn=True, 
        rowSpacing=10, 
        columnAttach=('both', 20)
    )
    
    cmds.separator(height=20, style='none')
    
    # 타이틀
    cmds.text(
        label="aiStandard to Lambert Converter", 
        font="boldLabelFont", 
        height=30
    )
    
    cmds.separator(height=10, style='in')
    cmds.separator(height=10, style='none')
    
    # 정보 텍스트
    cmds.text(
        label="씬의 모든 aiStandard 셰이더를 Lambert로 변환합니다.",
        align='center',
        font="plainLabelFont",
        height=25
    )
    
    cmds.separator(height=10, style='none')
    
    # 현재 aiStandard 개수 표시
    aistandard_shaders = cmds.ls(type='aiStandard') or []
    aistandard_count = len(aistandard_shaders)
    
    cmds.text(
        label=f"현재 씬: {aistandard_count}개의 aiStandard 셰이더",
        align='center',
        font="plainLabelFont",
        backgroundColor=(0.3, 0.3, 0.3),
        height=30
    )
    
    cmds.separator(height=15, style='none')
    
    # 변환 버튼
    cmds.button(
        label="변환 시작",
        command=lambda x: convert_all(),
        height=45,
        backgroundColor=(0.3, 0.5, 0.3)
    )
    
    cmds.separator(height=20, style='none')
    
    cmds.setParent('..')  # columnLayout 종료
    
    cmds.showWindow(window)


def reload_and_show():
    """모듈 리로드 및 UI 표시"""
    module_name = __name__
    
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
        print(f"모듈 리로드 완료: {module_name}")
    
    show_ui()


# 직접 실행 시
if __name__ == "__main__":
    convert_all()

