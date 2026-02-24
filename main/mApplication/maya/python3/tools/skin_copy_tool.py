"""
Skin Copy Tool for Maya
스킨 웨이트를 복사하는 UI 툴

사용법:
    import importlib
    import skin_copy_tool
    importlib.reload(skin_copy_tool)
    skin_copy_tool.show()
"""

import maya.cmds as cmds
import sys
import importlib


class SkinCopyTool:
    """스킨 웨이트 복사 UI 툴"""
    
    def __init__(self):
        self.window_name = "skinCopyToolWindow"
        self.object_list = None
        self.mode_radio = None
        self.loaded_objects = []  # 로드된 오브젝트 저장
        
    def create_ui(self):
        """UI 생성"""
        # 기존 윈도우가 있으면 삭제
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)
        
        # 윈도우 생성
        window = cmds.window(
            self.window_name,
            title="Skin Copy Tool",
            widthHeight=(500, 600),
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
        cmds.text(label="Skin Copy Tool", font="boldLabelFont", height=30)
        
        cmds.separator(height=10, style='in')
        cmds.separator(height=10, style='none')
        
        # 모드 선택 프레임
        cmds.frameLayout(
            label="복사 모드",
            borderStyle='in',
            collapsable=False,
            marginWidth=10,
            marginHeight=10
        )
        
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        self.mode_radio = cmds.radioCollection()
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(250, 200))
        cmds.radioButton(
            'mode_1toN',
            label="1:N 모드 (첫번째 → 나머지)",
            select=True,
            annotation="첫 번째 선택 오브젝트의 스킨을 나머지 모든 오브젝트에 복사"
        )
        cmds.text(label="[Source 1개 → Target N개]", align='left', font='smallPlainLabelFont')
        cmds.setParent('..')
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(250, 200))
        cmds.radioButton(
            'mode_NtoN',
            label="N:N 모드 (앞쪽 절반 → 뒤쪽 절반)",
            annotation="선택한 오브젝트를 절반으로 나눠 앞쪽에서 뒤쪽으로 순서대로 복사"
        )
        cmds.text(label="[앞 N개 → 뒤 N개]", align='left', font='smallPlainLabelFont')
        cmds.setParent('..')
        
        cmds.setParent('..')  # columnLayout
        cmds.setParent('..')  # frameLayout
        
        cmds.separator(height=10, style='none')
        
        # 선택된 오브젝트 리스트
        cmds.frameLayout(
            label="선택된 오브젝트",
            borderStyle='in',
            collapsable=False,
            marginWidth=5,
            marginHeight=5
        )
        
        self.object_list = cmds.textScrollList(
            numberOfRows=12,
            allowMultiSelection=True,
            selectCommand=self.on_list_selected,
            height=250
        )
        
        cmds.setParent('..')  # frameLayout
        
        cmds.separator(height=10, style='none')
        
        # 버튼 레이아웃
        cmds.rowLayout(
            numberOfColumns=2,
            adjustableColumn=1,
            columnAttach=[(1, 'both', 5), (2, 'both', 5)],
            height=35
        )
        
        cmds.button(
            label="선택 오브젝트 로드",
            command=self.load_selected_objects,
            backgroundColor=(0.4, 0.4, 0.5)
        )
        
        cmds.button(
            label="스킨 복사 실행",
            command=self.execute_skin_copy,
            backgroundColor=(0.3, 0.5, 0.4)
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
            height=100,
            font="smallPlainLabelFont",
            backgroundColor=(0.2, 0.2, 0.2)
        )
        
        cmds.setParent('..')  # frameLayout
        
        # 하단 여백
        cmds.separator(height=15, style='none')
        
        # 윈도우 표시
        cmds.showWindow(window)
        
        self.log("툴이 준비되었습니다.")
        self.log("오브젝트를 선택하고 '선택 오브젝트 로드' 버튼을 클릭하세요.")
    
    def log(self, message):
        """로그 메시지 추가"""
        current_text = cmds.scrollField(self.log_field, query=True, text=True)
        new_text = current_text + "\n" + message if current_text else message
        cmds.scrollField(self.log_field, edit=True, text=new_text)
        print(message)
    
    def on_list_selected(self):
        """리스트 선택 시 아웃라이너에서도 선택"""
        selected_indices = cmds.textScrollList(self.object_list, query=True, selectIndexedItem=True) or []
        
        if not selected_indices or not self.loaded_objects:
            return
        
        # 인덱스는 1부터 시작하므로 -1 해줌
        objects_to_select = [self.loaded_objects[i-1] for i in selected_indices if i-1 < len(self.loaded_objects)]
        
        if objects_to_select:
            try:
                cmds.select(objects_to_select, replace=True)
            except:
                pass
    
    def load_selected_objects(self, *args):
        """선택된 오브젝트 로드"""
        selected = cmds.ls(selection=True, fl=True) or []
        
        # 리스트 클리어
        cmds.textScrollList(self.object_list, edit=True, removeAll=True)
        self.loaded_objects = []
        
        if not selected:
            self.log("⚠ 선택된 오브젝트가 없습니다.")
            return
        
        # 오브젝트 저장
        self.loaded_objects = selected
        
        # 선택된 모드 확인
        mode = cmds.radioCollection(self.mode_radio, query=True, select=True)
        
        # 리스트에 추가
        for i, obj in enumerate(selected):
            cmds.textScrollList(self.object_list, edit=True, append=f"{i+1}. {obj}")
        
        self.log(f"\n✓ {len(selected)}개 오브젝트 로드됨")
        
        # 모드에 따른 안내 메시지
        if mode == 'mode_1toN':
            if len(selected) < 2:
                self.log("⚠ 1:N 모드는 최소 2개의 오브젝트가 필요합니다.")
            else:
                self.log(f"  Source: {selected[0]}")
                self.log(f"  Targets: {len(selected)-1}개")
        elif mode == 'mode_NtoN':
            if len(selected) < 2 or len(selected) % 2 != 0:
                self.log("⚠ N:N 모드는 짝수 개의 오브젝트가 필요합니다.")
            else:
                half = len(selected) // 2
                self.log(f"  Sources: {half}개 (1~{half})")
                self.log(f"  Targets: {half}개 ({half+1}~{len(selected)})")
    
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
        # skinCluster.matrix 연결에서 조인트 필터링
        conns = cmds.listConnections(skin_cluster + '.matrix', s=True, d=False) or []
        return [n for n in conns if cmds.nodeType(n) == 'joint']
    
    def _copy_skin_1toN(self, source, targets):
        """1:N 모드 - 하나의 소스에서 여러 타겟으로 복사"""
        self.log(f"\n[1:N 모드] 스킨 복사 시작")
        self.log(f"Source: {source}")
        
        # 소스의 바인드 조인트 가져오기
        bind_joints = self._get_bind_joints(source)
        if not bind_joints:
            self.log(f"✗ Source에 skinCluster가 없습니다: {source}")
            return 0
        
        self.log(f"✓ 바인드 조인트: {len(bind_joints)}개")
        
        src_skin = self._find_skin_cluster(self._get_shape(source))
        success_count = 0
        
        # 각 타겟에 복사
        for target in targets:
            try:
                # 타겟에 skinCluster 생성
                dest_skin = cmds.skinCluster(
                    bind_joints, target,
                    tsb=True, bm=1, mi=3, rui=False, dr=3
                )[0]
                
                # 웨이트 복사
                cmds.copySkinWeights(
                    ss=src_skin,
                    ds=dest_skin,
                    nm=True,
                    sa='closestPoint',
                    ia='oneToOne'
                )
                
                self.log(f"✓ {target}")
                success_count += 1
                
            except Exception as e:
                self.log(f"✗ {target} - {str(e)}")
        
        return success_count
    
    def _copy_skin_NtoN(self, sources, targets):
        """N:N 모드 - 여러 소스에서 여러 타겟으로 순서대로 복사"""
        self.log(f"\n[N:N 모드] 스킨 복사 시작")
        self.log(f"Sources: {len(sources)}개")
        self.log(f"Targets: {len(targets)}개")
        
        success_count = 0
        
        for idx, source in enumerate(sources):
            target = targets[idx]
            
            try:
                # 소스의 바인드 조인트 가져오기
                src_shape = self._get_shape(source)
                src_skin = self._find_skin_cluster(src_shape)
                
                if not src_skin:
                    self.log(f"✗ [{idx+1}] {source} - skinCluster 없음")
                    continue
                
                # 바인드 조인트 가져오기
                conns = cmds.listConnections(src_skin + '.matrix', s=True, d=False) or []
                joints = [n for n in conns if cmds.nodeType(n) == 'joint']
                
                if not joints:
                    self.log(f"✗ [{idx+1}] {source} - 조인트 없음")
                    continue
                
                # 타겟에 skinCluster 생성
                dest_skin = cmds.skinCluster(
                    joints, target,
                    tsb=True, bm=1, mi=3, rui=False, dr=3
                )[0]
                
                # 웨이트 복사
                cmds.copySkinWeights(
                    ss=src_skin,
                    ds=dest_skin,
                    nm=True,
                    sa='closestPoint',
                    ia=['closestJoint', 'oneToOne']
                )
                
                self.log(f"✓ [{idx+1}] {source} → {target}")
                success_count += 1
                
            except Exception as e:
                self.log(f"✗ [{idx+1}] {source} → {target} - {str(e)}")
        
        return success_count
    
    def execute_skin_copy(self, *args):
        """스킨 복사 실행"""
        # 로드된 오브젝트 사용
        if not self.loaded_objects:
            self.log("\n⚠ 로드된 오브젝트가 없습니다.")
            cmds.confirmDialog(
                title="경고",
                message="먼저 '선택 오브젝트 로드' 버튼을 클릭하여 오브젝트를 로드해주세요.",
                button=["확인"]
            )
            return
        
        # 선택된 모드 확인
        mode = cmds.radioCollection(self.mode_radio, query=True, select=True)
        
        success_count = 0
        
        try:
            if mode == 'mode_1toN':
                # 1:N 모드
                if len(self.loaded_objects) < 2:
                    self.log("\n⚠ 1:N 모드는 최소 2개의 오브젝트가 필요합니다.")
                    cmds.confirmDialog(
                        title="경고",
                        message="1:N 모드는 최소 2개의 오브젝트가 필요합니다.",
                        button=["확인"]
                    )
                    return
                
                source = self.loaded_objects[0]
                targets = self.loaded_objects[1:]
                success_count = self._copy_skin_1toN(source, targets)
                
            elif mode == 'mode_NtoN':
                # N:N 모드
                if len(self.loaded_objects) < 2 or len(self.loaded_objects) % 2 != 0:
                    self.log("\n⚠ N:N 모드는 짝수 개의 오브젝트가 필요합니다.")
                    cmds.confirmDialog(
                        title="경고",
                        message="N:N 모드는 짝수 개의 오브젝트가 필요합니다.",
                        button=["확인"]
                    )
                    return
                
                half = len(self.loaded_objects) // 2
                sources = self.loaded_objects[:half]
                targets = self.loaded_objects[half:]
                success_count = self._copy_skin_NtoN(sources, targets)
            
            # 결과 메시지
            self.log(f"\n{'='*40}")
            self.log(f"완료! 성공: {success_count}개")
            self.log(f"{'='*40}")
            
            cmds.confirmDialog(
                title="완료",
                message=f"스킨 복사 완료!\n\n성공: {success_count}개",
                button=["확인"]
            )
            
        except Exception as e:
            error_msg = f"스킨 복사 중 오류 발생: {str(e)}"
            self.log(f"\n✗ {error_msg}")
            cmds.confirmDialog(
                title="오류",
                message=error_msg,
                button=["확인"]
            )


def show():
    """UI 표시 함수"""
    tool = SkinCopyTool()
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

