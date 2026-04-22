"""
MH Tools Integrated - Maya Tools Suite
Maya 작업을 위한 통합 툴

사용법 1 (권장 - 런처 사용):
    from python3 import launch_mh_tools
    launch_mh_tools.launch()
    
    # 또는
    import python3
    python3.launch_tools()

사용법 2 (직접 import):
    import importlib
    from python3.tools import mh_tools_integrated
    importlib.reload(mh_tools_integrated)
    mh_tools_integrated.show()

사용법 3 (경로 추가가 필요한 경우):
    import sys
    import importlib
    sys.path.append('E:/script/pythonWorkSpace/main/mApplication/maya')
    from python3.tools import mh_tools_integrated
    importlib.reload(mh_tools_integrated)
    mh_tools_integrated.show()
"""

import maya.cmds as cmds
import maya.mel as mel
import sys
import importlib
import os


class MHToolsIntegrated:
    """통합 Maya 툴"""
    
    def __init__(self):
        self.window_name = "mhToolsIntegratedWindow"
        
        # FBX Import Tool
        self.fbx_path_field = None
        
        # Namespace Manager
        self.namespace_list = None
        
        # Layer Manager
        self.layer_list = None
        
        # Scene Cleanup Tool
        self.cleanup_task_checkboxes = {}
        self.cleanup_asset_name_field = None
        self.cleanup_log_field = None
        
        # Skin Copy Tool
        self.skin_object_list = None
        self.skin_mode_radio = None
        self.skin_loaded_objects = []
        self.skin_log_field = None
        
    def create_ui(self):
        """통합 UI 생성"""
        # 기존 윈도우가 있으면 삭제
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)
        
        # 윈도우 생성
        window = cmds.window(
            self.window_name,
            title="MH Tools Suite",
            widthHeight=(650, 700),
            sizeable=True,
            resizeToFitChildren=True
        )
        
        # 메인 레이아웃
        main_layout = cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=5,
            columnAttach=('both', 10)
        )
        
        # 상단 여백
        cmds.separator(height=10, style='none')
        
        # 타이틀
        cmds.text(label="MH Tools Suite", font="boldLabelFont", height=30)
        cmds.separator(height=10, style='in')
        cmds.separator(height=5, style='none')
        
        # 탭 레이아웃 생성
        tab_layout = cmds.tabLayout(innerMarginWidth=5, innerMarginHeight=5)
        
        # Tab 1: FBX Import
        self.create_fbx_import_tab()
        
        # Tab 2: Managers (Namespace & Layer)
        self.create_managers_tab()
        
        # Tab 3: Scene Cleanup
        self.create_cleanup_tab()
        
        # Tab 4: Skin Copy
        self.create_skin_copy_tab()
        
        # 탭 이름 설정
        cmds.tabLayout(tab_layout, edit=True, 
                      tabLabel=[
                          (cmds.tabLayout(tab_layout, query=True, childArray=True)[0], 'FBX Import'),
                          (cmds.tabLayout(tab_layout, query=True, childArray=True)[1], 'Managers'),
                          (cmds.tabLayout(tab_layout, query=True, childArray=True)[2], 'MHC Cleanup'),
                          (cmds.tabLayout(tab_layout, query=True, childArray=True)[3], 'Skin Copy')
                      ])
        
        # 하단 여백
        cmds.setParent('..')
        cmds.separator(height=10, style='none')
        
        # 윈도우 표시
        cmds.showWindow(window)
    
    # ========================================
    # Tab 1: FBX Import Tool
    # ========================================
    def create_fbx_import_tab(self):
        """FBX Import 탭 생성"""
        tab_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnAttach=('both', 15))
        
        cmds.separator(height=15, style='none')
        cmds.text(label="FBX Import Tool", font="boldLabelFont", height=25)
        cmds.separator(height=10, style='in')
        cmds.separator(height=10, style='none')
        
        # 파일 경로 선택
        cmds.rowLayout(
            numberOfColumns=3,
            adjustableColumn=2,
            columnAttach=[(1, 'right', 5), (2, 'both', 5), (3, 'left', 5)],
            columnWidth3=(70, 100, 80),
            height=30
        )
        cmds.text(label="FBX 파일:", align='right')
        self.fbx_path_field = cmds.textField(text="", editable=True, placeholderText="FBX 파일 경로를 선택하세요...")
        cmds.button(label="찾아보기", command=self.fbx_browse_file, backgroundColor=(0.4, 0.4, 0.4), width=80)
        cmds.setParent('..')
        
        cmds.separator(height=15, style='none')
        
        # Import 버튼
        cmds.button(label="Import", command=self.fbx_import, height=40, backgroundColor=(0.3, 0.5, 0.3))
        
        cmds.separator(height=15, style='none')
        cmds.setParent('..')
    
    def fbx_browse_file(self, *args):
        """FBX 파일 브라우저"""
        file_path = cmds.fileDialog2(fileMode=1, caption="FBX 파일 선택", 
                                     fileFilter="FBX Files (*.fbx);;All Files (*.*)", dialogStyle=2)
        if file_path:
            cmds.textField(self.fbx_path_field, edit=True, text=file_path[0])
    
    def fbx_import(self, *args):
        """FBX 파일 임포트"""
        file_path = cmds.textField(self.fbx_path_field, query=True, text=True)
        
        if not file_path:
            cmds.confirmDialog(title="경고", message="FBX 파일 경로를 선택해주세요.", button=["확인"])
            return
        
        if not os.path.exists(file_path):
            cmds.confirmDialog(title="오류", message=f"파일을 찾을 수 없습니다:\n{file_path}", button=["확인"])
            return
        
        if not file_path.lower().endswith('.fbx'):
            cmds.confirmDialog(title="경고", message="FBX 파일만 임포트 가능합니다.", button=["확인"])
            return
        
        try:
            if not cmds.pluginInfo('fbxmaya', query=True, loaded=True):
                cmds.loadPlugin('fbxmaya')
            
            cmds.file(file_path, i=True, type="FBX", ignoreVersion=True, mergeNamespacesOnClash=False, options="fbx")
            print(f"FBX 파일 임포트 완료: {file_path}")
            cmds.confirmDialog(title="완료", message=f"FBX 파일 임포트 완료!\n\n{os.path.basename(file_path)}", button=["확인"])
        except Exception as e:
            cmds.confirmDialog(title="오류", message=f"FBX 임포트 중 오류 발생: {str(e)}", button=["확인"])
    
    # ========================================
    # Tab 2: Namespace & Layer Managers
    # ========================================
    def create_managers_tab(self):
        """Namespace & Layer Manager 탭 생성"""
        tab_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=5, columnAttach=('both', 15))
        
        cmds.separator(height=10, style='none')
        
        # Namespace Manager
        cmds.frameLayout(label="Namespace Manager", collapsable=True, 
                        collapse=False, marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        cmds.separator(height=5, style='none')
        cmds.text(label="현재 씬의 네임스페이스 목록", align='left', font="plainLabelFont")
        cmds.separator(height=5, style='none')
        
        self.namespace_list = cmds.textScrollList(numberOfRows=8, allowMultiSelection=True, height=180)
        
        cmds.separator(height=5, style='none')
        cmds.rowLayout(numberOfColumns=3, adjustableColumn=1, 
                      columnAttach=[(1, 'both', 5), (2, 'both', 5), (3, 'both', 5)], height=30)
        cmds.button(label="새로고침", command=self.refresh_namespaces, backgroundColor=(0.4, 0.4, 0.5))
        cmds.button(label="선택 삭제", command=self.delete_selected_namespaces, backgroundColor=(0.6, 0.3, 0.3))
        cmds.button(label="전체 삭제", command=self.delete_all_namespaces, backgroundColor=(0.7, 0.2, 0.2))
        cmds.setParent('..')
        
        cmds.text(label="* 기본 네임스페이스(UI, shared)는 삭제되지 않습니다.", 
                 align='left', font="smallPlainLabelFont", backgroundColor=(0.2, 0.2, 0.2))
        cmds.separator(height=5, style='none')
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.separator(height=10, style='none')
        
        # Layer Manager
        cmds.frameLayout(label="Layer Manager", collapsable=True, 
                        collapse=False, marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        cmds.separator(height=5, style='none')
        cmds.text(label="현재 씬의 Display & Animation Layer 목록", align='left', font="plainLabelFont")
        cmds.separator(height=5, style='none')
        
        self.layer_list = cmds.textScrollList(numberOfRows=8, allowMultiSelection=True, height=180)
        
        cmds.separator(height=5, style='none')
        cmds.rowLayout(numberOfColumns=3, adjustableColumn=1, 
                      columnAttach=[(1, 'both', 5), (2, 'both', 5), (3, 'both', 5)], height=30)
        cmds.button(label="새로고침", command=self.refresh_layers, backgroundColor=(0.4, 0.4, 0.5))
        cmds.button(label="선택 삭제", command=self.delete_selected_layers, backgroundColor=(0.6, 0.3, 0.3))
        cmds.button(label="전체 삭제", command=self.delete_all_layers, backgroundColor=(0.7, 0.2, 0.2))
        cmds.setParent('..')
        
        cmds.text(label="* 기본 레이어(defaultLayer)는 삭제되지 않습니다. BaseAnimation은 삭제 가능합니다.", 
                 align='left', font="smallPlainLabelFont", backgroundColor=(0.2, 0.2, 0.2))
        cmds.separator(height=5, style='none')
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.separator(height=10, style='none')
        cmds.setParent('..')
        
        # 초기 로드
        self.refresh_namespaces()
        self.refresh_layers()
    
    # Namespace Manager 메서드들
    def get_namespaces(self):
        """네임스페이스 가져오기"""
        all_namespaces = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True)
        default_namespaces = ['UI', 'shared']
        if all_namespaces:
            return sorted([ns for ns in all_namespaces if ns not in default_namespaces])
        return []
    
    def refresh_namespaces(self, *args):
        """네임스페이스 새로고침"""
        cmds.textScrollList(self.namespace_list, edit=True, removeAll=True)
        namespaces = self.get_namespaces()
        if namespaces:
            for ns in namespaces:
                cmds.textScrollList(self.namespace_list, edit=True, append=ns)
        else:
            cmds.textScrollList(self.namespace_list, edit=True, append="(네임스페이스 없음)")
    
    def delete_selected_namespaces(self, *args):
        """선택된 네임스페이스 삭제"""
        selected = cmds.textScrollList(self.namespace_list, query=True, selectItem=True)
        if not selected or selected == ["(네임스페이스 없음)"]:
            cmds.confirmDialog(title="경고", message="삭제할 네임스페이스를 선택해주세요.", button=["확인"])
            return
        
        confirm = cmds.confirmDialog(title="확인", 
                                     message=f"선택한 {len(selected)}개의 네임스페이스를 삭제하시겠습니까?\n\n{', '.join(selected)}", 
                                     button=["삭제", "취소"], defaultButton="취소", cancelButton="취소")
        
        if confirm == "삭제":
            success = 0
            for ns in selected:
                try:
                    if cmds.namespace(exists=ns):
                        cmds.namespace(removeNamespace=ns, mergeNamespaceWithRoot=True)
                        success += 1
                except:
                    pass
            self.refresh_namespaces()
            cmds.confirmDialog(title="완료", message=f"삭제 완료: {success}개", button=["확인"])
    
    def delete_all_namespaces(self, *args):
        """모든 네임스페이스 삭제"""
        namespaces = self.get_namespaces()
        if not namespaces:
            cmds.confirmDialog(title="알림", message="삭제할 네임스페이스가 없습니다.", button=["확인"])
            return
        
        confirm = cmds.confirmDialog(title="경고", 
                                     message=f"모든 네임스페이스({len(namespaces)}개)를 삭제하시겠습니까?", 
                                     button=["삭제", "취소"], defaultButton="취소", cancelButton="취소")
        
        if confirm == "삭제":
            success = 0
            for ns in namespaces:
                try:
                    if cmds.namespace(exists=ns):
                        cmds.namespace(removeNamespace=ns, mergeNamespaceWithRoot=True)
                        success += 1
                except:
                    pass
            self.refresh_namespaces()
            cmds.confirmDialog(title="완료", message=f"전체 삭제 완료: {success}개", button=["확인"])
    
    # Layer Manager 메서드들
    def get_layers(self):
        """Display Layer와 Animation Layer 가져오기"""
        layers = []
        
        # Display Layers 가져오기 (defaultLayer 제외)
        display_layers = cmds.ls(type='displayLayer') or []
        for layer in display_layers:
            if layer != 'defaultLayer':
                layers.append(('display', layer))
        
        # Animation Layers 가져오기 (BaseAnimation 포함)
        anim_layers = cmds.ls(type='animLayer') or []
        for layer in anim_layers:
            layers.append(('anim', layer))
        
        # 타입별로 정렬 (display 먼저, 그 다음 anim)
        layers.sort(key=lambda x: (x[0], x[1]))
        
        return layers
    
    def refresh_layers(self, *args):
        """레이어 새로고침"""
        cmds.textScrollList(self.layer_list, edit=True, removeAll=True)
        layers = self.get_layers()
        if layers:
            for layer_type, layer_name in layers:
                if layer_type == 'display':
                    display_text = f"[Display] {layer_name}"
                else:  # anim
                    display_text = f"[Anim] {layer_name}"
                cmds.textScrollList(self.layer_list, edit=True, append=display_text)
        else:
            cmds.textScrollList(self.layer_list, edit=True, append="(레이어 없음)")
    
    def delete_selected_layers(self, *args):
        """선택된 레이어 삭제"""
        selected = cmds.textScrollList(self.layer_list, query=True, selectItem=True)
        if not selected or selected == ["(레이어 없음)"]:
            cmds.confirmDialog(title="경고", message="삭제할 레이어를 선택해주세요.", button=["확인"])
            return
        
        # 표시 텍스트에서 실제 레이어 이름 추출
        layer_names = []
        for item in selected:
            # "[Display] layerName" 또는 "[Anim] layerName" 형식에서 이름 추출
            if item.startswith("[Display] ") or item.startswith("[Anim] "):
                layer_name = item.split("] ", 1)[1]
                layer_names.append(layer_name)
        
        if not layer_names:
            return
        
        confirm = cmds.confirmDialog(title="확인", 
                                     message=f"선택한 {len(layer_names)}개의 레이어를 삭제하시겠습니까?\n\n{', '.join(layer_names)}", 
                                     button=["삭제", "취소"], defaultButton="취소", cancelButton="취소")
        
        if confirm == "삭제":
            success = 0
            failed = []
            for layer in layer_names:
                try:
                    if cmds.objExists(layer) and layer != 'defaultLayer':
                        cmds.delete(layer)
                        success += 1
                except Exception as e:
                    failed.append(f"{layer}: {str(e)}")
            
            self.refresh_layers()
            
            if failed:
                cmds.confirmDialog(title="완료", 
                                 message=f"삭제 완료: {success}개\n실패: {len(failed)}개", 
                                 button=["확인"])
            else:
                cmds.confirmDialog(title="완료", message=f"삭제 완료: {success}개", button=["확인"])
    
    def delete_all_layers(self, *args):
        """모든 레이어 삭제"""
        layers = self.get_layers()
        if not layers:
            cmds.confirmDialog(title="알림", message="삭제할 레이어가 없습니다.", button=["확인"])
            return
        
        # Display와 Anim 레이어 개수 세기
        display_count = sum(1 for t, _ in layers if t == 'display')
        anim_count = sum(1 for t, _ in layers if t == 'anim')
        
        confirm = cmds.confirmDialog(title="경고", 
                                     message=f"모든 레이어를 삭제하시겠습니까?\n\nDisplay: {display_count}개\nAnimation: {anim_count}개\n총: {len(layers)}개", 
                                     button=["삭제", "취소"], defaultButton="취소", cancelButton="취소")
        
        if confirm == "삭제":
            success = 0
            failed = []
            for layer_type, layer_name in layers:
                try:
                    if cmds.objExists(layer_name) and layer_name != 'defaultLayer':
                        cmds.delete(layer_name)
                        success += 1
                except Exception as e:
                    failed.append(f"{layer_name}: {str(e)}")
            
            self.refresh_layers()
            
            if failed:
                cmds.confirmDialog(title="완료", 
                                 message=f"삭제 완료: {success}개\n실패: {len(failed)}개", 
                                 button=["확인"])
            else:
                cmds.confirmDialog(title="완료", message=f"전체 삭제 완료: {success}개", button=["확인"])
    
    # ========================================
    # Tab 3: Scene Cleanup Tool (MHC Cleanup)
    # ========================================
    def create_cleanup_tab(self):
        """MHC Cleanup 탭 생성"""
        tab_layout = cmds.scrollLayout(childResizable=True)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5, columnAttach=('both', 15))
        
        cmds.separator(height=10, style='none')
        cmds.text(label="MHC Cleanup Tool", font="boldLabelFont", height=25)
        cmds.separator(height=10, style='in')
        cmds.separator(height=5, style='none')
        
        # Asset Name 입력
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnAttach=[(1, 'right', 5), (2, 'both', 5)], 
                      columnWidth2=(100, 100), height=30)
        cmds.text(label="Asset Name:", align='right')
        self.cleanup_asset_name_field = cmds.textField(text="", placeholderText="head_grp을 리네임할 이름 입력...")
        cmds.setParent('..')
        
        cmds.separator(height=10, style='none')
        
        # 작업 목록
        cmds.frameLayout(label="작업 목록", collapsable=False, marginWidth=10, marginHeight=10)
        tasks_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
        
        self._create_cleanup_task_row("task1", "1. Joints 및 그룹 정리 (joints_grp/geometry_grp/head_grp)", self.execute_cleanup_task1)
        self._create_cleanup_task_row("task2", "2. Head LOD 정리 (head_lod0_grp 제외 삭제)", self.execute_cleanup_task2)
        self._create_cleanup_task_row("task_body_match", "3. Body Joint Transform Match", self.execute_cleanup_task_body_match)
        self._create_cleanup_task_row("task3", "4. Facial 조인트 Constraint 및 그룹핑", self.execute_cleanup_task3)
        self._create_cleanup_task_row("task4", "5. Lights 그룹 제거", self.execute_cleanup_task4)
        self._create_cleanup_task_row("task5", "6. Delete Unused Nodes & Plugins", self.execute_cleanup_task5)
        self._create_cleanup_task_row("task6", "7. Create Animation Sets", self.execute_cleanup_task6)
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.separator(height=10, style='none')
        
        # 실행 버튼
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnAttach=[(1, 'both', 5), (2, 'both', 5)], height=35)
        cmds.button(label="선택한 작업 실행", command=self.execute_selected_cleanup_tasks, backgroundColor=(0.3, 0.5, 0.4))
        cmds.button(label="전체 작업 실행", command=self.execute_all_cleanup_tasks, backgroundColor=(0.4, 0.5, 0.6))
        cmds.setParent('..')
        
        cmds.separator(height=10, style='none')
        
        # 로그
        cmds.frameLayout(label="실행 로그", collapsable=True, collapse=False, marginWidth=5, marginHeight=5)
        self.cleanup_log_field = cmds.scrollField(editable=False, wordWrap=True, height=150, 
                                                  font="smallPlainLabelFont", backgroundColor=(0.2, 0.2, 0.2))
        cmds.setParent('..')
        
        cmds.separator(height=10, style='none')
        cmds.setParent('..')
        cmds.setParent('..')
        
        self.cleanup_log("MHC Cleanup Tool이 준비되었습니다.")
    
    def _create_cleanup_task_row(self, task_id, label, command):
        """작업 행 생성"""
        cmds.rowLayout(numberOfColumns=3, adjustableColumn=2, 
                      columnAttach=[(1, 'left', 5), (2, 'both', 10), (3, 'right', 5)], 
                      columnWidth3=(30, 100, 100), height=30)
        checkbox = cmds.checkBox(label="", value=True)
        self.cleanup_task_checkboxes[task_id] = checkbox
        cmds.text(label=label, align='left')
        cmds.button(label="실행", command=lambda x: command(), backgroundColor=(0.4, 0.4, 0.5), width=100)
        cmds.setParent('..')
    
    def cleanup_log(self, message):
        """로그 추가"""
        current_text = cmds.scrollField(self.cleanup_log_field, query=True, text=True)
        new_text = current_text + "\n" + message if current_text else message
        cmds.scrollField(self.cleanup_log_field, edit=True, text=new_text)
        print(message)
    
    # Scene Cleanup 작업들
    def execute_cleanup_task1(self):
        """작업 1: Joints 및 그룹 정리"""
        self.cleanup_log("\n[작업 1] Joints 및 그룹 정리 시작...")
        
        try:
            # Step 1: joints_grp 하위의 조인트들을 unparent
            unparented_joints = []
            joints_grp_exists = False
            
            if cmds.objExists('joints_grp'):
                joints_grp_exists = True
                children = cmds.listRelatives('joints_grp', children=True, fullPath=True) or []
                
                if children:
                    self.cleanup_log(f"  ✓ joints_grp에서 {len(children)}개 오브젝트 발견")
                    
                    for child in children:
                        try:
                            cmds.parent(child, world=True)
                            short_name = child.split('|')[-1]
                            unparented_joints.append(short_name)
                            self.cleanup_log(f"  ✓ Unparent: {short_name}")
                        except Exception as e:
                            self.cleanup_log(f"  ✗ Unparent 실패: {child} - {str(e)}")
                else:
                    self.cleanup_log("  ℹ 'joints_grp' 하위에 오브젝트가 없습니다.")
            
            # Step 2: root로 시작하는 조인트 트리 찾기 및 spine_03에 parent
            if unparented_joints:
                all_joints = cmds.ls(type='joint')
                root_joints = []
                
                for joint in all_joints:
                    if joint.lower().startswith('root'):
                        parent = cmds.listRelatives(joint, parent=True)
                        if not parent:
                            root_joints.append(joint)
                
                if root_joints:
                    self.cleanup_log(f"  ✓ 'root'로 시작하는 조인트 트리 발견: {len(root_joints)}개")
                    
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
                        self.cleanup_log(f"  ✓ spine_03 조인트 발견: {spine_joint.split('|')[-1]}")
                        
                        success_count = 0
                        for joint_name in unparented_joints:
                            try:
                                found_joints = cmds.ls(joint_name)
                                if found_joints:
                                    cmds.parent(found_joints[0], spine_joint)
                                    self.cleanup_log(f"  ✓ Parent: {joint_name} → {spine_joint.split('|')[-1]}")
                                    success_count += 1
                            except Exception as e:
                                self.cleanup_log(f"  ✗ Parent 실패: {joint_name} - {str(e)}")
                        
                        self.cleanup_log(f"  ✓ 조인트 parent 완료: {success_count}/{len(unparented_joints)}개")
                    else:
                        self.cleanup_log("  ⚠ spine_03 조인트를 찾을 수 없습니다.")
                else:
                    self.cleanup_log("  ⚠ root 조인트 트리를 찾을 수 없습니다.")
            
            # Step 3: joints_grp 빈 그룹 제거
            if joints_grp_exists and cmds.objExists('joints_grp'):
                try:
                    cmds.delete('joints_grp')
                    self.cleanup_log("  ✓ 빈 joints_grp 제거 완료")
                except Exception as e:
                    self.cleanup_log(f"  ✗ joints_grp 제거 실패: {str(e)}")
            
            # Step 4: geometry_grp를 geo_grp으로 리네임
            if cmds.objExists('geometry_grp'):
                try:
                    cmds.rename('geometry_grp', 'geo_grp')
                    self.cleanup_log("  ✓ geometry_grp → geo_grp 리네임 완료")
                except Exception as e:
                    self.cleanup_log(f"  ✗ geometry_grp 리네임 실패: {str(e)}")
            else:
                self.cleanup_log("  ℹ geometry_grp이 존재하지 않습니다.")
            
            # Step 5: head_grp를 AssetName으로 리네임하고 unparent
            asset_name = cmds.textField(self.cleanup_asset_name_field, query=True, text=True).strip()
            
            if cmds.objExists('head_grp'):
                head_parent = cmds.listRelatives('head_grp', parent=True, fullPath=True)
                
                try:
                    cmds.parent('head_grp', world=True)
                    self.cleanup_log("  ✓ head_grp unparent 완료")
                    
                    if asset_name:
                        new_name = cmds.rename('head_grp', asset_name)
                        self.cleanup_log(f"  ✓ head_grp → {new_name} 리네임 완료")
                        
                        try:
                            cmds.setAttr(f"{new_name}.useOutlinerColor", 1)
                            cmds.setAttr(f"{new_name}.outlinerColor", 0, 0.849, 0, type='double3')
                            self.cleanup_log(f"  ✓ {new_name} 아웃라이너 색상 설정 완료 (녹색)")
                        except Exception as e:
                            self.cleanup_log(f"  ✗ 아웃라이너 색상 설정 실패: {str(e)}")
                    else:
                        self.cleanup_log("  ℹ Asset Name이 입력되지 않아 head_grp 리네임을 건너뜁니다.")
                    
                    if head_parent:
                        parent_name = head_parent[0].split('|')[-1]
                        if cmds.objExists(parent_name):
                            children = cmds.listRelatives(parent_name, children=True) or []
                            if not children:
                                try:
                                    cmds.delete(parent_name)
                                    self.cleanup_log(f"  ✓ 빈 상위 그룹 제거: {parent_name}")
                                except Exception as e:
                                    self.cleanup_log(f"  ✗ 상위 그룹 제거 실패: {str(e)}")
                            else:
                                self.cleanup_log(f"  ℹ 상위 그룹 '{parent_name}'이 비어있지 않아 제거하지 않습니다.")
                    
                except Exception as e:
                    self.cleanup_log(f"  ✗ head_grp 처리 실패: {str(e)}")
            else:
                self.cleanup_log("  ℹ head_grp이 존재하지 않습니다.")
            
            self.cleanup_log("[작업 1] 완료!")
            
        except Exception as e:
            self.cleanup_log(f"[작업 1] 오류: {str(e)}")
    
    def execute_cleanup_task2(self):
        """작업 2: Head LOD 정리"""
        self.cleanup_log("\n[작업 2] Head LOD 정리 시작...")
        
        try:
            all_head_lod_grps = cmds.ls('head_lod*_grp', type='transform')
            
            if not all_head_lod_grps:
                self.cleanup_log("  ⚠ 'head_lod*_grp' 그룹을 찾을 수 없습니다.")
                return
            
            grps_to_delete = [grp for grp in all_head_lod_grps if grp != 'head_lod0_grp']
            
            if not grps_to_delete:
                self.cleanup_log("  ℹ 삭제할 그룹이 없습니다. (head_lod0_grp만 존재)")
                return
            
            deleted_count = 0
            for grp in grps_to_delete:
                try:
                    cmds.delete(grp)
                    self.cleanup_log(f"  ✓ 삭제: {grp}")
                    deleted_count += 1
                except Exception as e:
                    self.cleanup_log(f"  ✗ 삭제 실패: {grp} - {str(e)}")
            
            self.cleanup_log(f"[작업 2] 완료! ({deleted_count}개 그룹 삭제)")
            
        except Exception as e:
            self.cleanup_log(f"[작업 2] 오류: {str(e)}")
    
    def execute_cleanup_task_body_match(self):
        """작업 3. Body Joint Transform Match"""
        self.cleanup_log(u"\n[작업 3. Body Joint Transform Match] 시작...")

        try:
            # Step 1: Reference 파일 선택
            file_path_result = cmds.fileDialog2(
                fileMode=1,
                caption="Reference 파일 선택",
                fileFilter="Maya Files (*.ma *.mb);;All Files (*.*)",
                dialogStyle=2
            )

            if not file_path_result:
                self.cleanup_log(u"  ⚠ 파일 선택이 취소되었습니다.")
                return

            file_path = file_path_result[0]
            base_name = os.path.splitext(os.path.basename(file_path))[0]

            # Namespace 입력
            ns_result = cmds.promptDialog(
                title="Namespace 입력",
                message="레퍼런스에 사용할 Namespace:",
                text=base_name,
                button=["OK", "Cancel"],
                defaultButton="OK",
                cancelButton="Cancel",
                dismissString="Cancel"
            )

            if ns_result != "OK":
                self.cleanup_log(u"  ⚠ 취소되었습니다.")
                return

            namespace = cmds.promptDialog(query=True, text=True).strip()
            if not namespace:
                namespace = base_name

            # Reference 로드
            self.cleanup_log(u"  레퍼런스 로드: {} (ns: {})".format(os.path.basename(file_path), namespace))
            cmds.file(file_path, reference=True, namespace=namespace)
            self.cleanup_log(u"  ✓ 레퍼런스 로드 완료")

            # Step 2: Joint 구조 파악
            all_joints = cmds.ls(type='joint')
            scene_joints = [j for j in all_joints if ':' not in j]

            root_joint = None
            for j in scene_joints:
                if j.lower().startswith('root'):
                    parent = cmds.listRelatives(j, parent=True)
                    if not parent:
                        root_joint = j
                        break

            if not root_joint:
                self.cleanup_log(u"  ⚠ root 조인트를 찾을 수 없습니다. 레퍼런스를 제거합니다.")
                self._remove_reference_by_namespace(namespace)
                return

            self.cleanup_log(u"  ✓ root 조인트: {}".format(root_joint))

            # 하이라키 전체 조인트 (fullPath 기준 depth 정렬 → parent-first)
            hier_fp = cmds.listRelatives(root_joint, allDescendents=True, type='joint', fullPath=True) or []
            hier_fp_sorted = sorted(hier_fp, key=lambda x: x.count('|'))

            # Facial 최상위 조인트 식별 (FACIAL_ 포함, 부모는 비-FACIAL)
            facial_joint_set = set()
            facial_top_joints = []

            for fp in hier_fp_sorted:
                short = fp.split('|')[-1]
                if 'FACIAL_' in short:
                    facial_joint_set.add(short)
                    parent_nodes = cmds.listRelatives(fp, parent=True, fullPath=True)
                    if parent_nodes:
                        parent_short = parent_nodes[0].split('|')[-1]
                        if 'FACIAL_' not in parent_short:
                            facial_top_joints.append(short)

            self.cleanup_log(u"  ✓ Facial 조인트: {}개 (최상위 {}개)".format(len(facial_joint_set), len(facial_top_joints)))

            # Facial 최상위 조인트 임시 분리
            facial_parent_map = {}
            for fj in facial_top_joints:
                parent = cmds.listRelatives(fj, parent=True)
                if parent:
                    facial_parent_map[fj] = parent[0]
                    try:
                        cmds.parent(fj, world=True)
                    except Exception as e:
                        self.cleanup_log(u"  ✗ Unparent 실패: {} - {}".format(fj, str(e)))

            self.cleanup_log(u"  ✓ Facial 조인트 임시 분리: {}개".format(len(facial_parent_map)))

            # 레퍼런스 조인트 맵 구성 (short_name → full_name)
            ref_prefix = namespace + ':'
            ref_joints = [j for j in cmds.ls(type='joint') if j.startswith(ref_prefix)]
            ref_joint_map = {j[len(ref_prefix):]: j for j in ref_joints}

            self.cleanup_log(u"  ✓ 레퍼런스 조인트: {}개".format(len(ref_joints)))

            # Body 조인트 Transform Match (parent-first 순서)
            body_joints = [root_joint]
            for fp in hier_fp_sorted:
                short = fp.split('|')[-1]
                if short not in facial_joint_set:
                    body_joints.append(short)

            matched = 0
            skipped = 0

            for j in body_joints:
                if j in ref_joint_map:
                    ref_j = ref_joint_map[j]
                    try:
                        ws_matrix = cmds.xform(ref_j, q=True, ws=True, matrix=True)
                        cmds.xform(j, ws=True, matrix=ws_matrix)
                        matched += 1
                    except Exception as e:
                        self.cleanup_log(u"  ✗ Match 실패: {} - {}".format(j, str(e)))
                else:
                    skipped += 1

            self.cleanup_log(u"  ✓ Transform Match: {}개 완료, {}개 미매치".format(matched, skipped))

            # Facial 조인트 복원
            for fj, orig_parent in facial_parent_map.items():
                try:
                    cmds.parent(fj, orig_parent)
                except Exception as e:
                    self.cleanup_log(u"  ✗ Re-parent 실패: {} → {} - {}".format(fj, orig_parent, str(e)))

            self.cleanup_log(u"  ✓ Facial 조인트 복원 완료")

            # Step 3: Set Bind Default
            self.cleanup_log(u"  Set Bind Default 실행 중...")
            self._execute_set_bind_default()

            # Step 4: 레퍼런스 제거
            self.cleanup_log(u"  레퍼런스 제거 중...")
            self._remove_reference_by_namespace(namespace)

            self.cleanup_log(u"[작업 3. Body Joint Transform Match] 완료!")

        except Exception as e:
            import traceback
            self.cleanup_log(u"[작업 3. Body Joint Transform Match] 오류: {}".format(str(e)))
            self.cleanup_log(traceback.format_exc())

    def _execute_set_bind_default(self):
        """모든 skinCluster에 현재 조인트 위치를 bind pose로 설정"""
        import maya.OpenMaya as om

        def get_mobj(node_name):
            sel_list = om.MSelectionList()
            sel_list.add(node_name)
            mobj = om.MObject()
            sel_list.getDependNode(0, mobj)
            return mobj

        skin_clusters = cmds.ls(type='skinCluster') or []

        if not skin_clusters:
            self.cleanup_log(u"  ⚠ skinCluster를 찾을 수 없습니다.")
            return

        success = 0
        failed = 0

        for skin_node in skin_clusters:
            try:
                fn_skin = om.MFnDependencyNode(get_mobj(skin_node))
                plug_matrix = fn_skin.findPlug('matrix')
                plug_bind_pre = fn_skin.findPlug('bindPreMatrix')

                for i in range(plug_matrix.numElements()):
                    lo_idx = plug_matrix[i].logicalIndex()
                    o_mtx = plug_matrix[i].asMObject()
                    mtx_data = om.MFnMatrixData(o_mtx)
                    mtx = mtx_data.matrix()
                    inv_data = om.MFnMatrixData()
                    o_inv = inv_data.create(mtx.inverse())
                    plug_bind_pre.elementByLogicalIndex(lo_idx).setMObject(o_inv)

                self.cleanup_log(u"  ✓ {}".format(skin_node))
                success += 1
            except Exception as e:
                self.cleanup_log(u"  ✗ {} - {}".format(skin_node, str(e)))
                failed += 1

        self.cleanup_log(u"  ✓ Set Bind Default 완료: {}개 성공, {}개 실패".format(success, failed))

    def _remove_reference_by_namespace(self, namespace):
        """지정된 namespace의 reference를 제거"""
        try:
            ref_nodes = cmds.ls(type='reference') or []
            for rn in ref_nodes:
                if rn == 'sharedReferenceNode':
                    continue
                try:
                    ns = cmds.referenceQuery(rn, namespace=True).lstrip(':')
                    if ns == namespace:
                        fname = cmds.referenceQuery(rn, filename=True)
                        cmds.file(fname, removeReference=True)
                        self.cleanup_log(u"  ✓ 레퍼런스 제거: {}".format(os.path.basename(fname)))
                        return
                except Exception:
                    continue
            self.cleanup_log(u"  ⚠ namespace '{}' 레퍼런스를 찾을 수 없습니다.".format(namespace))
        except Exception as e:
            self.cleanup_log(u"  ✗ 레퍼런스 제거 실패: {}".format(str(e)))

    def execute_cleanup_task3(self):
        """작업 4: Facial 조인트 처리"""
        self.cleanup_log("\n[작업 3] Facial 조인트 처리 시작...")
        
        try:
            neck_joints = cmds.ls('neck_0*', type='joint') or []
            head_joints = cmds.ls('head', type='joint') or []
            
            parent_joints = neck_joints + head_joints
            
            if not parent_joints:
                self.cleanup_log("  ⚠ 'neck_0*' 또는 'head' 조인트를 찾을 수 없습니다.")
                return
            
            self.cleanup_log(f"  ✓ 부모 조인트 발견: neck({len(neck_joints)}개), head({len(head_joints)}개)")
            
            facial_top_joints = []
            constraint_count = 0
            
            for parent_joint in parent_joints:
                direct_children = cmds.listRelatives(parent_joint, children=True, type='joint', fullPath=True) or []
                facial_root_joints = [j for j in direct_children if 'FACIAL_C_' in j]
                
                if not facial_root_joints:
                    self.cleanup_log(f"  ℹ {parent_joint}에 FACIAL 루트 조인트가 없습니다.")
                    continue
                
                self.cleanup_log(f"  ✓ {parent_joint}에서 {len(facial_root_joints)}개 FACIAL 루트 조인트 발견")
                
                for facial_root in facial_root_joints:
                    try:
                        short_parent = parent_joint.split('|')[-1]
                        short_facial = facial_root.split('|')[-1]
                        
                        cmds.parentConstraint(parent_joint, facial_root, maintainOffset=True)
                        cmds.scaleConstraint(parent_joint, facial_root, maintainOffset=True)
                        
                        self.cleanup_log(f"  ✓ Constraint: {short_parent} → {short_facial}")
                        constraint_count += 1
                        
                        facial_top_joints.append(facial_root)
                        
                    except Exception as e:
                        short_facial = facial_root.split('|')[-1]
                        self.cleanup_log(f"  ✗ Constraint 실패: {short_facial} - {str(e)}")
            
            self.cleanup_log(f"  ✓ Constraint 적용 완료: {constraint_count}개")
            
            if facial_top_joints:
                facial_top_joints = list(set(facial_top_joints))
                self.cleanup_log(f"  ✓ 최상위 FACIAL 조인트: {len(facial_top_joints)}개")
                
                if cmds.objExists('headjoint_grp'):
                    cmds.delete('headjoint_grp')
                
                headjoint_grp = cmds.group(empty=True, name='headjoint_grp')
                self.cleanup_log(f"  ✓ 그룹 생성: {headjoint_grp}")
                
                for facial_joint in facial_top_joints:
                    try:
                        short_name = facial_joint.split('|')[-1]
                        cmds.parent(facial_joint, headjoint_grp)
                        self.cleanup_log(f"  ✓ Parent: {short_name} → headjoint_grp")
                    except Exception as e:
                        short_name = facial_joint.split('|')[-1]
                        self.cleanup_log(f"  ✗ Parent 실패: {short_name} - {str(e)}")
                
                if cmds.objExists('headRig_grp'):
                    try:
                        cmds.parent(headjoint_grp, 'headRig_grp')
                        self.cleanup_log(f"  ✓ Parent: headjoint_grp → headRig_grp")
                    except Exception as e:
                        self.cleanup_log(f"  ✗ Parent 실패: {str(e)}")
                else:
                    self.cleanup_log("  ⚠ 'headRig_grp'을 찾을 수 없습니다. headjoint_grp이 루트에 있습니다.")
            else:
                self.cleanup_log("  ⚠ 그룹핑할 최상위 FACIAL 조인트가 없습니다.")
            
            self.cleanup_log("[작업 3] 완료!")
            
        except Exception as e:
            self.cleanup_log(f"[작업 3] 오류: {str(e)}")
    
    def execute_cleanup_task4(self):
        """작업 4: Lights 그룹 제거"""
        self.cleanup_log("\n[작업 4] Lights 그룹 제거 시작...")
        
        try:
            lights_grps = cmds.ls('Lights', type='transform')
            
            if not lights_grps:
                self.cleanup_log("  ⚠ 'Lights' 그룹을 찾을 수 없습니다.")
                return
            
            deleted_count = 0
            for lights_grp in lights_grps:
                try:
                    cmds.delete(lights_grp)
                    self.cleanup_log(f"  ✓ 삭제: {lights_grp}")
                    deleted_count += 1
                except Exception as e:
                    self.cleanup_log(f"  ✗ 삭제 실패: {lights_grp} - {str(e)}")
            
            self.cleanup_log(f"[작업 4] 완료! ({deleted_count}개 그룹 삭제)")
            
        except Exception as e:
            self.cleanup_log(f"[작업 4] 오류: {str(e)}")
    
    def execute_cleanup_task5(self):
        """작업 5: Delete Unused Nodes & Plugins"""
        self.cleanup_log("\n[작업 5] Delete Unused Nodes & Plugins 시작...")
        
        try:
            # 1. Hypershade의 Delete Unused Nodes 기능 실행
            mel.eval('MLdeleteUnused;')
            self.cleanup_log("  ✓ Unused nodes 삭제 완료")
            
            # 2. Unknown/Unused Plugins 제거
            unknown_plugins = cmds.unknownPlugin(query=True, list=True) or []
            
            if unknown_plugins:
                removed_count = 0
                for plugin in unknown_plugins:
                    try:
                        cmds.unknownPlugin(plugin, remove=True)
                        self.cleanup_log(f"  ✓ Unknown plugin 제거: {plugin}")
                        removed_count += 1
                    except Exception as e:
                        self.cleanup_log(f"  ✗ Plugin 제거 실패: {plugin} - {str(e)}")
                
                self.cleanup_log(f"  ✓ Unused plugins 제거 완료 ({removed_count}개)")
            else:
                self.cleanup_log("  ℹ 제거할 unknown plugin 없음")
            
            self.cleanup_log("[작업 5] 완료!")
            
        except Exception as e:
            self.cleanup_log(f"[작업 5] 오류: {str(e)}")
    
    def execute_cleanup_task6(self):
        """작업 6: Create Animation Sets"""
        self.cleanup_log("\n[작업 6] Animation Sets 생성 시작...")
        
        try:
            created_count = 0
            
            # 최상위 셋 'Sets' 생성
            if not cmds.objExists('Sets'):
                cmds.sets(name='Sets', empty=True)
                self.cleanup_log("  ✓ 'Sets' 생성")
                created_count += 1
            else:
                self.cleanup_log("  ℹ 'Sets' 이미 존재")
            
            # 'AniFBXSet' 생성 및 'Sets'에 추가
            if not cmds.objExists('AniFBXSet'):
                ani_fbx_set = cmds.sets(name='AniFBXSet', empty=True)
                cmds.sets(ani_fbx_set, add='Sets')
                self.cleanup_log("  ✓ 'AniFBXSet' 생성")
                created_count += 1
            else:
                self.cleanup_log("  ℹ 'AniFBXSet' 이미 존재")
                ani_fbx_set = 'AniFBXSet'
            
            # 'AssetFBX_Set' 생성 및 'Sets'에 추가
            if not cmds.objExists('AssetFBX_Set'):
                asset_fbx_set = cmds.sets(name='AssetFBX_Set', empty=True)
                cmds.sets(asset_fbx_set, add='Sets')
                self.cleanup_log("  ✓ 'AssetFBX_Set' 생성")
                created_count += 1
            else:
                self.cleanup_log("  ℹ 'AssetFBX_Set' 이미 존재")
            
            # 'AniOutSet' 생성 및 'AniFBXSet'에 추가
            if not cmds.objExists('AniOutSet'):
                ani_out_set = cmds.sets(name='AniOutSet', empty=True)
                cmds.sets(ani_out_set, add=ani_fbx_set)
                self.cleanup_log("  ✓ 'AniOutSet' 생성 (AniFBXSet 하위)")
                created_count += 1
            else:
                self.cleanup_log("  ℹ 'AniOutSet' 이미 존재")
            
            # 'AnimControlSet' 생성 및 'Sets'에 추가
            if not cmds.objExists('AnimControlSet'):
                anim_control_set = cmds.sets(name='AnimControlSet', empty=True)
                cmds.sets(anim_control_set, add='Sets')
                self.cleanup_log("  ✓ 'AnimControlSet' 생성")
                created_count += 1
            else:
                self.cleanup_log("  ℹ 'AnimControlSet' 이미 존재")
            
            if created_count > 0:
                self.cleanup_log(f"[작업 6] 완료! ({created_count}개 Sets 생성)")
            else:
                self.cleanup_log("[작업 6] 완료! (모든 Sets가 이미 존재함)")
            
        except Exception as e:
            self.cleanup_log(f"[작업 6] 오류: {str(e)}")
    
    def execute_selected_cleanup_tasks(self, *args):
        """선택한 작업 실행"""
        self.cleanup_log("\n" + "="*50)
        task_functions = {
            'task1': self.execute_cleanup_task1,
            'task2': self.execute_cleanup_task2,
            'task_body_match': self.execute_cleanup_task_body_match,
            'task3': self.execute_cleanup_task3,
            'task4': self.execute_cleanup_task4,
            'task5': self.execute_cleanup_task5,
            'task6': self.execute_cleanup_task6,
        }
        for task_id, checkbox in self.cleanup_task_checkboxes.items():
            if cmds.checkBox(checkbox, query=True, value=True):
                task_functions[task_id]()
        self.cleanup_log("="*50)
    
    def execute_all_cleanup_tasks(self, *args):
        """전체 작업 실행"""
        self.cleanup_log("\n" + "="*50)
        self.execute_cleanup_task1()
        self.execute_cleanup_task2()
        self.execute_cleanup_task_body_match()
        self.execute_cleanup_task3()
        self.execute_cleanup_task4()
        self.execute_cleanup_task5()
        self.execute_cleanup_task6()
        self.cleanup_log("="*50)
    
    # ========================================
    # Tab 4: Skin Copy Tool
    # ========================================
    def create_skin_copy_tab(self):
        """Skin Copy 탭 생성"""
        tab_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=5, columnAttach=('both', 15))
        
        cmds.separator(height=10, style='none')
        cmds.text(label="Skin Copy Tool", font="boldLabelFont", height=25)
        cmds.separator(height=10, style='in')
        cmds.separator(height=5, style='none')
        
        # 모드 선택
        cmds.frameLayout(label="복사 모드", collapsable=False, marginWidth=10, marginHeight=10)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        self.skin_mode_radio = cmds.radioCollection()
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(250, 200))
        cmds.radioButton('mode_1toN', label="1:N 모드 (첫번째 → 나머지)", select=True)
        cmds.text(label="[Source 1개 → Target N개]", align='left', font='smallPlainLabelFont')
        cmds.setParent('..')
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(250, 200))
        cmds.radioButton('mode_NtoN', label="N:N 모드 (앞쪽 절반 → 뒤쪽 절반)")
        cmds.text(label="[앞 N개 → 뒤 N개]", align='left', font='smallPlainLabelFont')
        cmds.setParent('..')
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.separator(height=10, style='none')
        
        # 오브젝트 리스트
        cmds.frameLayout(label="선택된 오브젝트", collapsable=False, marginWidth=5, marginHeight=5)
        self.skin_object_list = cmds.textScrollList(numberOfRows=10, allowMultiSelection=True, 
                                                    selectCommand=self.on_skin_list_selected, height=200)
        cmds.setParent('..')
        
        cmds.separator(height=10, style='none')
        
        # 버튼
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnAttach=[(1, 'both', 5), (2, 'both', 5)], height=35)
        cmds.button(label="선택 오브젝트 로드", command=self.load_skin_objects, backgroundColor=(0.4, 0.4, 0.5))
        cmds.button(label="스킨 복사 실행", command=self.execute_skin_copy, backgroundColor=(0.3, 0.5, 0.4))
        cmds.setParent('..')
        
        cmds.separator(height=10, style='none')
        
        # 로그
        cmds.frameLayout(label="실행 로그", collapsable=True, collapse=False, marginWidth=5, marginHeight=5)
        self.skin_log_field = cmds.scrollField(editable=False, wordWrap=True, height=120, 
                                              font="smallPlainLabelFont", backgroundColor=(0.2, 0.2, 0.2))
        cmds.setParent('..')
        
        cmds.separator(height=10, style='none')
        cmds.setParent('..')
        
        self.skin_log("Skin Copy Tool이 준비되었습니다.")
    
    def skin_log(self, message):
        """스킨 로그 추가"""
        current_text = cmds.scrollField(self.skin_log_field, query=True, text=True)
        new_text = current_text + "\n" + message if current_text else message
        cmds.scrollField(self.skin_log_field, edit=True, text=new_text)
        print(message)
    
    def on_skin_list_selected(self):
        """리스트 선택 시 아웃라이너 동기화"""
        selected_indices = cmds.textScrollList(self.skin_object_list, query=True, selectIndexedItem=True) or []
        if selected_indices and self.skin_loaded_objects:
            objects_to_select = [self.skin_loaded_objects[i-1] for i in selected_indices if i-1 < len(self.skin_loaded_objects)]
            if objects_to_select:
                try:
                    cmds.select(objects_to_select, replace=True)
                except:
                    pass
    
    def load_skin_objects(self, *args):
        """오브젝트 로드"""
        selected = cmds.ls(selection=True, fl=True) or []
        cmds.textScrollList(self.skin_object_list, edit=True, removeAll=True)
        self.skin_loaded_objects = []
        
        if not selected:
            self.skin_log("⚠ 선택된 오브젝트가 없습니다.")
            return
        
        self.skin_loaded_objects = selected
        mode = cmds.radioCollection(self.skin_mode_radio, query=True, select=True)
        
        for i, obj in enumerate(selected):
            cmds.textScrollList(self.skin_object_list, edit=True, append=f"{i+1}. {obj}")
        
        self.skin_log(f"\n✓ {len(selected)}개 오브젝트 로드됨")
        
        if mode == 'mode_1toN':
            if len(selected) >= 2:
                self.skin_log(f"  Source: {selected[0]}")
                self.skin_log(f"  Targets: {len(selected)-1}개")
        elif mode == 'mode_NtoN':
            if len(selected) >= 2 and len(selected) % 2 == 0:
                half = len(selected) // 2
                self.skin_log(f"  Sources: {half}개")
                self.skin_log(f"  Targets: {half}개")
    
    def _get_shape(self, node):
        """노드의 shape 노드 가져오기"""
        shapes = cmds.listRelatives(node, s=True, ni=True, pa=True) or []
        return shapes[0] if shapes else node
    
    def _find_skin_cluster(self, node):
        """skinCluster 노드 찾기"""
        history = cmds.listHistory(node, pdo=True) or []
        for n in history:
            if cmds.nodeType(n) == 'skinCluster':
                return n
        return None
    
    def _get_bind_joints(self, obj):
        """오브젝트의 바인드 조인트 가져오기"""
        shape = self._get_shape(obj)
        skin_cluster = self._find_skin_cluster(shape)
        if not skin_cluster:
            return []
        conns = cmds.listConnections(skin_cluster + '.matrix', s=True, d=False) or []
        return [n for n in conns if cmds.nodeType(n) == 'joint']
    
    def _copy_skin_1toN(self, source, targets):
        """1:N 모드 - 하나의 소스에서 여러 타겟으로 복사"""
        self.skin_log(f"\n[1:N 모드] 스킨 복사 시작")
        self.skin_log(f"Source: {source}")
        
        bind_joints = self._get_bind_joints(source)
        if not bind_joints:
            self.skin_log(f"✗ Source에 skinCluster가 없습니다: {source}")
            return 0
        
        self.skin_log(f"✓ 바인드 조인트: {len(bind_joints)}개")
        
        src_skin = self._find_skin_cluster(self._get_shape(source))
        success_count = 0
        
        for target in targets:
            try:
                dest_skin = cmds.skinCluster(
                    bind_joints, target,
                    tsb=True, bm=1, mi=3, rui=False, dr=3
                )[0]
                
                cmds.copySkinWeights(
                    ss=src_skin,
                    ds=dest_skin,
                    nm=True,
                    sa='closestPoint',
                    ia='oneToOne'
                )
                
                self.skin_log(f"✓ {target}")
                success_count += 1
                
            except Exception as e:
                self.skin_log(f"✗ {target} - {str(e)}")
        
        return success_count
    
    def _copy_skin_NtoN(self, sources, targets):
        """N:N 모드 - 여러 소스에서 여러 타겟으로 순서대로 복사"""
        self.skin_log(f"\n[N:N 모드] 스킨 복사 시작")
        self.skin_log(f"Sources: {len(sources)}개")
        self.skin_log(f"Targets: {len(targets)}개")
        
        success_count = 0
        
        for idx, source in enumerate(sources):
            target = targets[idx]
            
            try:
                src_shape = self._get_shape(source)
                src_skin = self._find_skin_cluster(src_shape)
                
                if not src_skin:
                    self.skin_log(f"✗ [{idx+1}] {source} - skinCluster 없음")
                    continue
                
                conns = cmds.listConnections(src_skin + '.matrix', s=True, d=False) or []
                joints = [n for n in conns if cmds.nodeType(n) == 'joint']
                
                if not joints:
                    self.skin_log(f"✗ [{idx+1}] {source} - 조인트 없음")
                    continue
                
                dest_skin = cmds.skinCluster(
                    joints, target,
                    tsb=True, bm=1, mi=3, rui=False, dr=3
                )[0]
                
                cmds.copySkinWeights(
                    ss=src_skin,
                    ds=dest_skin,
                    nm=True,
                    sa='closestPoint',
                    ia=['closestJoint', 'oneToOne']
                )
                
                self.skin_log(f"✓ [{idx+1}] {source} → {target}")
                success_count += 1
                
            except Exception as e:
                self.skin_log(f"✗ [{idx+1}] {source} → {target} - {str(e)}")
        
        return success_count
    
    def execute_skin_copy(self, *args):
        """스킨 복사 실행"""
        if not self.skin_loaded_objects:
            cmds.confirmDialog(title="경고", message="먼저 '선택 오브젝트 로드' 버튼을 클릭하여 오브젝트를 로드해주세요.", button=["확인"])
            return
        
        mode = cmds.radioCollection(self.skin_mode_radio, query=True, select=True)
        success_count = 0
        
        try:
            if mode == 'mode_1toN':
                if len(self.skin_loaded_objects) < 2:
                    self.skin_log("\n⚠ 1:N 모드는 최소 2개의 오브젝트가 필요합니다.")
                    cmds.confirmDialog(title="경고", message="1:N 모드는 최소 2개의 오브젝트가 필요합니다.", button=["확인"])
                    return
                
                source = self.skin_loaded_objects[0]
                targets = self.skin_loaded_objects[1:]
                success_count = self._copy_skin_1toN(source, targets)
                
            elif mode == 'mode_NtoN':
                if len(self.skin_loaded_objects) < 2 or len(self.skin_loaded_objects) % 2 != 0:
                    self.skin_log("\n⚠ N:N 모드는 짝수 개의 오브젝트가 필요합니다.")
                    cmds.confirmDialog(title="경고", message="N:N 모드는 짝수 개의 오브젝트가 필요합니다.", button=["확인"])
                    return
                
                half = len(self.skin_loaded_objects) // 2
                sources = self.skin_loaded_objects[:half]
                targets = self.skin_loaded_objects[half:]
                success_count = self._copy_skin_NtoN(sources, targets)
            
            self.skin_log(f"\n{'='*40}")
            self.skin_log(f"완료! 성공: {success_count}개")
            self.skin_log(f"{'='*40}")
            
            cmds.confirmDialog(title="완료", message=f"스킨 복사 완료!\n\n성공: {success_count}개", button=["확인"])
            
        except Exception as e:
            error_msg = f"스킨 복사 중 오류 발생: {str(e)}"
            self.skin_log(f"\n✗ {error_msg}")
            cmds.confirmDialog(title="오류", message=error_msg, button=["확인"])


def show():
    """통합 UI 표시"""
    tool = MHToolsIntegrated()
    tool.create_ui()


def reload_and_show():
    """모듈 리로드 및 UI 표시"""
    module_name = __name__
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
        print(f"모듈 리로드 완료: {module_name}")
    show()


if __name__ == "__main__":
    show()

