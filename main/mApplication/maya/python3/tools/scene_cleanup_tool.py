"""
MHC Cleanup Tool for Maya
씬 정리 자동화 툴

사용법:
    import importlib
    import scene_cleanup_tool
    importlib.reload(scene_cleanup_tool)
    scene_cleanup_tool.show()
"""

import maya.cmds as cmds
import sys
import importlib


class SceneCleanupTool:
    """MHC 정리 자동화 툴"""
    
    def __init__(self):
        self.window_name = "mhcCleanupToolWindow"
        self.task_checkboxes = {}
        self.asset_name_field = None
        
    def create_ui(self):
        """UI 생성"""
        # 기존 윈도우가 있으면 삭제
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)
        
        # 윈도우 생성
        window = cmds.window(
            self.window_name,
            title="MHC Cleanup Tool",
            widthHeight=(600, 600),
            sizeable=True,
            resizeToFitChildren=True
        )
        
        # 메인 레이아웃
        main_layout = cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=5,
            columnAttach=('both', 15)
        )
        
        # 상단 여백
        cmds.separator(height=15, style='none')
        
        # 타이틀
        cmds.text(label="MHC Cleanup Tool", font="boldLabelFont", height=30)
        
        cmds.separator(height=10, style='in')
        cmds.separator(height=10, style='none')
        
        # 설명
        cmds.text(
            label="실행할 작업을 선택하고 개별 실행하거나 전체 실행하세요",
            align='left',
            font="plainLabelFont"
        )
        
        cmds.separator(height=10, style='none')
        
        # Asset Name 입력 필드
        cmds.rowLayout(
            numberOfColumns=2,
            adjustableColumn=2,
            columnAttach=[(1, 'right', 5), (2, 'both', 5)],
            columnWidth2=(100, 100),
            height=30
        )
        
        cmds.text(label="Asset Name:", align='right')
        self.asset_name_field = cmds.textField(
            text="",
            placeholderText="head_grp을 리네임할 이름 입력..."
        )
        
        cmds.setParent('..')  # rowLayout
        
        cmds.separator(height=10, style='none')
        
        # 작업 목록 프레임
        cmds.frameLayout(
            label="작업 목록",
            borderStyle='in',
            collapsable=False,
            marginWidth=10,
            marginHeight=10
        )
        
        tasks_layout = cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=8
        )
        
        # 작업 1
        self._create_task_row(
            "task1",
            "1. Joints 및 그룹 정리 (joints_grp/geometry_grp/head_grp)",
            self.execute_task1
        )
        
        # 작업 2
        self._create_task_row(
            "task2",
            "2. Head LOD 정리 (head_lod0_grp 제외 삭제)",
            self.execute_task2
        )
        
        # 작업 3
        self._create_task_row(
            "task3",
            "3. Facial 조인트 Constraint 및 그룹핑",
            self.execute_task3
        )
        
        # 작업 4
        self._create_task_row(
            "task4",
            "4. Lights 그룹 제거",
            self.execute_task4
        )
        
        cmds.setParent('..')  # tasks_layout
        cmds.setParent('..')  # frameLayout
        
        cmds.separator(height=15, style='none')
        
        # 전체 실행 버튼
        cmds.rowLayout(
            numberOfColumns=2,
            adjustableColumn=1,
            columnAttach=[(1, 'both', 5), (2, 'both', 5)],
            height=40
        )
        
        cmds.button(
            label="선택한 작업 실행",
            command=self.execute_selected_tasks,
            backgroundColor=(0.3, 0.5, 0.4)
        )
        
        cmds.button(
            label="전체 작업 실행",
            command=self.execute_all_tasks,
            backgroundColor=(0.4, 0.5, 0.6)
        )
        
        cmds.setParent('..')  # rowLayout
        
        cmds.separator(height=10, style='none')
        
        # 로그 프레임
        cmds.frameLayout(
            label="실행 로그",
            borderStyle='in',
            collapsable=True,
            collapse=False,
            marginWidth=5,
            marginHeight=5
        )
        
        self.log_field = cmds.scrollField(
            editable=False,
            wordWrap=True,
            height=120,
            font="smallPlainLabelFont",
            backgroundColor=(0.2, 0.2, 0.2)
        )
        
        cmds.setParent('..')  # frameLayout
        
        # 하단 여백
        cmds.separator(height=15, style='none')
        
        # 윈도우 표시
        cmds.showWindow(window)
        
        self.log("툴이 준비되었습니다.")
    
    def _create_task_row(self, task_id, label, command):
        """작업 행 생성"""
        cmds.rowLayout(
            numberOfColumns=3,
            adjustableColumn=2,
            columnAttach=[(1, 'left', 5), (2, 'both', 10), (3, 'right', 5)],
            columnWidth3=(30, 100, 100),
            height=30
        )
        
        # 체크박스
        checkbox = cmds.checkBox(label="", value=True)
        self.task_checkboxes[task_id] = checkbox
        
        # 작업 설명
        cmds.text(label=label, align='left')
        
        # 개별 실행 버튼
        cmds.button(
            label="실행",
            command=lambda x: command(),
            backgroundColor=(0.4, 0.4, 0.5),
            width=100
        )
        
        cmds.setParent('..')  # rowLayout
    
    def log(self, message):
        """로그 메시지 추가"""
        current_text = cmds.scrollField(self.log_field, query=True, text=True)
        new_text = current_text + "\n" + message if current_text else message
        cmds.scrollField(self.log_field, edit=True, text=new_text)
        print(message)
    
    def execute_task1(self):
        """작업 1: joints_grp 하위 조인트를 unparent하고 root 트리의 spine_03에 parent"""
        self.log("\n[작업 1] Joints 및 그룹 정리 시작...")
        
        try:
            # Step 1: joints_grp 하위의 조인트들을 unparent
            unparented_joints = []
            joints_grp_exists = False
            
            if cmds.objExists('joints_grp'):
                joints_grp_exists = True
                # joints_grp 하위의 모든 자식 가져오기
                children = cmds.listRelatives('joints_grp', children=True, fullPath=True) or []
                
                if children:
                    self.log(f"  ✓ joints_grp에서 {len(children)}개 오브젝트 발견")
                    
                    # 자식들을 world로 unparent
                    for child in children:
                        try:
                            cmds.parent(child, world=True)
                            short_name = child.split('|')[-1]
                            unparented_joints.append(short_name)
                            self.log(f"  ✓ Unparent: {short_name}")
                        except Exception as e:
                            self.log(f"  ✗ Unparent 실패: {child} - {str(e)}")
                else:
                    self.log("  ℹ 'joints_grp' 하위에 오브젝트가 없습니다.")
            
            # Step 2: root로 시작하는 조인트 트리 찾기 및 spine_03에 parent
            if unparented_joints:
                all_joints = cmds.ls(type='joint')
                root_joints = []
                
                for joint in all_joints:
                    # 조인트 이름이 root로 시작하는지 확인 (대소문자 무관)
                    if joint.lower().startswith('root'):
                        # 최상위 조인트인지 확인 (부모가 world인지)
                        parent = cmds.listRelatives(joint, parent=True)
                        if not parent:  # 부모가 없으면 최상위 조인트
                            root_joints.append(joint)
                
                if root_joints:
                    self.log(f"  ✓ 'root'로 시작하는 조인트 트리 발견: {len(root_joints)}개")
                    
                    # root 트리 내에서 spine_03 조인트 찾기
                    spine_joint = None
                    for root_joint in root_joints:
                        descendants = cmds.listRelatives(root_joint, allDescendents=True, type='joint', fullPath=True) or []
                        
                        for desc in descendants:
                            if 'spine_03' in desc.lower():
                                spine_joint = desc
                                break
                        
                        if spine_joint:
                            break
                    
                    if spine_joint:
                        self.log(f"  ✓ spine_03 조인트 발견: {spine_joint.split('|')[-1]}")
                        
                        # unparent한 조인트들을 spine_03에 parent
                        success_count = 0
                        for joint_name in unparented_joints:
                            try:
                                found_joints = cmds.ls(joint_name)
                                if found_joints:
                                    cmds.parent(found_joints[0], spine_joint)
                                    self.log(f"  ✓ Parent: {joint_name} → {spine_joint.split('|')[-1]}")
                                    success_count += 1
                            except Exception as e:
                                self.log(f"  ✗ Parent 실패: {joint_name} - {str(e)}")
                        
                        self.log(f"  ✓ 조인트 parent 완료: {success_count}/{len(unparented_joints)}개")
                    else:
                        self.log("  ⚠ spine_03 조인트를 찾을 수 없습니다.")
                else:
                    self.log("  ⚠ root 조인트 트리를 찾을 수 없습니다.")
            
            # Step 3: joints_grp 빈 그룹 제거
            if joints_grp_exists and cmds.objExists('joints_grp'):
                try:
                    cmds.delete('joints_grp')
                    self.log("  ✓ 빈 joints_grp 제거 완료")
                except Exception as e:
                    self.log(f"  ✗ joints_grp 제거 실패: {str(e)}")
            
            # Step 4: geometry_grp를 geo_grp으로 리네임
            if cmds.objExists('geometry_grp'):
                try:
                    cmds.rename('geometry_grp', 'geo_grp')
                    self.log("  ✓ geometry_grp → geo_grp 리네임 완료")
                except Exception as e:
                    self.log(f"  ✗ geometry_grp 리네임 실패: {str(e)}")
            else:
                self.log("  ℹ geometry_grp이 존재하지 않습니다.")
            
            # Step 5: head_grp를 AssetName으로 리네임하고 unparent
            asset_name = cmds.textField(self.asset_name_field, query=True, text=True).strip()
            
            if cmds.objExists('head_grp'):
                # head_grp의 부모 저장
                head_parent = cmds.listRelatives('head_grp', parent=True, fullPath=True)
                
                try:
                    # head_grp을 world로 unparent
                    cmds.parent('head_grp', world=True)
                    self.log("  ✓ head_grp unparent 완료")
                    
                    # AssetName이 입력되었으면 리네임 및 색상 설정
                    if asset_name:
                        new_name = cmds.rename('head_grp', asset_name)
                        self.log(f"  ✓ head_grp → {new_name} 리네임 완료")
                        
                        # Outliner 색상 설정 (HSV: 120, 1.0, 0.849 -> RGB: 0, 0.849, 0)
                        try:
                            # Use outliner color 활성화
                            cmds.setAttr(f"{new_name}.useOutlinerColor", 1)
                            # RGB 색상 설정 (HSV 120, 1.0, 0.849 = 녹색)
                            cmds.setAttr(f"{new_name}.outlinerColor", 0, 0.849, 0, type='double3')
                            self.log(f"  ✓ {new_name} 아웃라이너 색상 설정 완료 (녹색)")
                        except Exception as e:
                            self.log(f"  ✗ 아웃라이너 색상 설정 실패: {str(e)}")
                    else:
                        self.log("  ℹ Asset Name이 입력되지 않아 head_grp 리네임을 건너뜁니다.")
                    
                    # 상위 그룹이 비어있으면 삭제
                    if head_parent:
                        parent_name = head_parent[0].split('|')[-1]
                        if cmds.objExists(parent_name):
                            children = cmds.listRelatives(parent_name, children=True) or []
                            if not children:
                                try:
                                    cmds.delete(parent_name)
                                    self.log(f"  ✓ 빈 상위 그룹 제거: {parent_name}")
                                except Exception as e:
                                    self.log(f"  ✗ 상위 그룹 제거 실패: {str(e)}")
                            else:
                                self.log(f"  ℹ 상위 그룹 '{parent_name}'이 비어있지 않아 제거하지 않습니다.")
                    
                except Exception as e:
                    self.log(f"  ✗ head_grp 처리 실패: {str(e)}")
            else:
                self.log("  ℹ head_grp이 존재하지 않습니다.")
            
            self.log("[작업 1] 완료!")
            
        except Exception as e:
            self.log(f"[작업 1] 오류: {str(e)}")
    
    def execute_task2(self):
        """작업 2: head_lod0_grp을 제외한 head_lod*_grp 삭제"""
        self.log("\n[작업 2] Head LOD 정리 시작...")
        
        try:
            # head_lod*_grp 패턴으로 검색
            all_head_lod_grps = cmds.ls('head_lod*_grp', type='transform')
            
            if not all_head_lod_grps:
                self.log("  ⚠ 'head_lod*_grp' 그룹을 찾을 수 없습니다.")
                return
            
            # head_lod0_grp 제외
            grps_to_delete = [grp for grp in all_head_lod_grps if grp != 'head_lod0_grp']
            
            if not grps_to_delete:
                self.log("  ℹ 삭제할 그룹이 없습니다. (head_lod0_grp만 존재)")
                return
            
            # 그룹 삭제
            deleted_count = 0
            for grp in grps_to_delete:
                try:
                    cmds.delete(grp)
                    self.log(f"  ✓ 삭제: {grp}")
                    deleted_count += 1
                except Exception as e:
                    self.log(f"  ✗ 삭제 실패: {grp} - {str(e)}")
            
            self.log(f"[작업 2] 완료! ({deleted_count}개 그룹 삭제)")
            
        except Exception as e:
            self.log(f"[작업 2] 오류: {str(e)}")
    
    def execute_task3(self):
        """작업 3: Facial 조인트 Constraint 및 그룹핑"""
        self.log("\n[작업 3] Facial 조인트 처리 시작...")
        
        try:
            # neck_0* 조인트와 head 조인트 찾기
            neck_joints = cmds.ls('neck_0*', type='joint') or []
            head_joints = cmds.ls('head', type='joint') or []
            
            # 두 리스트 합치기
            parent_joints = neck_joints + head_joints
            
            if not parent_joints:
                self.log("  ⚠ 'neck_0*' 또는 'head' 조인트를 찾을 수 없습니다.")
                return
            
            self.log(f"  ✓ 부모 조인트 발견: neck({len(neck_joints)}개), head({len(head_joints)}개)")
            
            facial_top_joints = []
            constraint_count = 0
            
            # 각 부모 조인트의 직계 자식 중 FACIAL_C_ 조인트만 찾아서 constraint 걸기
            for parent_joint in parent_joints:
                # 부모 조인트의 직계 자식만 가져오기
                direct_children = cmds.listRelatives(parent_joint, children=True, type='joint', fullPath=True) or []
                
                # 직계 자식 중 FACIAL_C_가 포함된 조인트만 필터링 (이것이 FACIAL 루트)
                facial_root_joints = [j for j in direct_children if 'FACIAL_C_' in j]
                
                if not facial_root_joints:
                    self.log(f"  ℹ {parent_joint}에 FACIAL 루트 조인트가 없습니다.")
                    continue
                
                self.log(f"  ✓ {parent_joint}에서 {len(facial_root_joints)}개 FACIAL 루트 조인트 발견")
                
                # 각 FACIAL 루트 조인트에 부모 조인트로부터 Constraint 적용
                for facial_root in facial_root_joints:
                    try:
                        short_parent = parent_joint.split('|')[-1]
                        short_facial = facial_root.split('|')[-1]
                        
                        # parentConstraint
                        cmds.parentConstraint(parent_joint, facial_root, maintainOffset=True)
                        # scaleConstraint
                        cmds.scaleConstraint(parent_joint, facial_root, maintainOffset=True)
                        
                        self.log(f"  ✓ Constraint: {short_parent} → {short_facial}")
                        constraint_count += 1
                        
                        # 그룹핑을 위해 저장
                        facial_top_joints.append(facial_root)
                        
                    except Exception as e:
                        short_facial = facial_root.split('|')[-1]
                        self.log(f"  ✗ Constraint 실패: {short_facial} - {str(e)}")
            
            self.log(f"  ✓ Constraint 적용 완료: {constraint_count}개")
            
            # facial_top_joints가 있으면 그룹핑
            if facial_top_joints:
                # 중복 제거
                facial_top_joints = list(set(facial_top_joints))
                self.log(f"  ✓ 최상위 FACIAL 조인트: {len(facial_top_joints)}개")
                
                # headjoint_grp 생성 (이미 있으면 삭제하고 다시 생성)
                if cmds.objExists('headjoint_grp'):
                    cmds.delete('headjoint_grp')
                
                headjoint_grp = cmds.group(empty=True, name='headjoint_grp')
                self.log(f"  ✓ 그룹 생성: {headjoint_grp}")
                
                # 최상위 조인트들을 그룹에 parent
                for facial_joint in facial_top_joints:
                    try:
                        short_name = facial_joint.split('|')[-1]
                        cmds.parent(facial_joint, headjoint_grp)
                        self.log(f"  ✓ Parent: {short_name} → headjoint_grp")
                    except Exception as e:
                        short_name = facial_joint.split('|')[-1]
                        self.log(f"  ✗ Parent 실패: {short_name} - {str(e)}")
                
                # headRig_grp 찾기
                if cmds.objExists('headRig_grp'):
                    try:
                        cmds.parent(headjoint_grp, 'headRig_grp')
                        self.log(f"  ✓ Parent: headjoint_grp → headRig_grp")
                    except Exception as e:
                        self.log(f"  ✗ Parent 실패: {str(e)}")
                else:
                    self.log("  ⚠ 'headRig_grp'을 찾을 수 없습니다. headjoint_grp이 루트에 있습니다.")
            else:
                self.log("  ⚠ 그룹핑할 최상위 FACIAL 조인트가 없습니다.")
            
            self.log("[작업 3] 완료!")
            
        except Exception as e:
            self.log(f"[작업 3] 오류: {str(e)}")
    
    def execute_task4(self):
        """작업 4: Lights 그룹 제거"""
        self.log("\n[작업 4] Lights 그룹 제거 시작...")
        
        try:
            # Lights 그룹 찾기
            lights_grps = cmds.ls('Lights', type='transform')
            
            if not lights_grps:
                self.log("  ⚠ 'Lights' 그룹을 찾을 수 없습니다.")
                return
            
            # 모든 Lights 그룹 삭제
            deleted_count = 0
            for lights_grp in lights_grps:
                try:
                    cmds.delete(lights_grp)
                    self.log(f"  ✓ 삭제: {lights_grp}")
                    deleted_count += 1
                except Exception as e:
                    self.log(f"  ✗ 삭제 실패: {lights_grp} - {str(e)}")
            
            self.log(f"[작업 4] 완료! ({deleted_count}개 그룹 삭제)")
            
        except Exception as e:
            self.log(f"[작업 4] 오류: {str(e)}")
    
    def execute_selected_tasks(self, *args):
        """선택한 작업만 실행"""
        self.log("\n" + "="*50)
        self.log("선택한 작업 실행 시작")
        self.log("="*50)
        
        task_functions = {
            'task1': self.execute_task1,
            'task2': self.execute_task2,
            'task3': self.execute_task3,
            'task4': self.execute_task4,
        }
        
        executed = False
        for task_id, checkbox in self.task_checkboxes.items():
            if cmds.checkBox(checkbox, query=True, value=True):
                task_functions[task_id]()
                executed = True
        
        if not executed:
            self.log("⚠ 선택된 작업이 없습니다.")
        else:
            self.log("\n" + "="*50)
            self.log("선택한 작업 실행 완료!")
            self.log("="*50)
    
    def execute_all_tasks(self, *args):
        """모든 작업 실행"""
        self.log("\n" + "="*50)
        self.log("전체 작업 실행 시작")
        self.log("="*50)
        
        self.execute_task1()
        self.execute_task2()
        self.execute_task3()
        self.execute_task4()
        
        self.log("\n" + "="*50)
        self.log("전체 작업 실행 완료!")
        self.log("="*50)


def show():
    """UI 표시 함수"""
    tool = SceneCleanupTool()
    tool.create_ui()


def reload_and_show():
    """모듈을 다시 로드하고 UI 표시"""
    module_name = __name__
    
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
        print(f"모듈 리로드 완료: {module_name}")
    
    show()


# 스크립트 직접 실행 시
if __name__ == "__main__":
    show()

