"""
Namespace Manager Tool for Maya
Maya 씬의 네임스페이스를 관리하는 UI 툴

사용법:
    # 첫 실행
    import namespace_manager_tool
    namespace_manager_tool.show()
    
    # 모듈 수정 후 리로드
    import importlib
    import namespace_manager_tool
    importlib.reload(namespace_manager_tool)
    namespace_manager_tool.show()
"""

import maya.cmds as cmds
import sys
import importlib


class NamespaceManagerTool:
    """네임스페이스를 관리하는 UI 툴"""
    
    def __init__(self):
        self.window_name = "namespaceManagerWindow"
        self.namespace_list = None
        
    def create_ui(self):
        """UI 생성"""
        # 기존 윈도우가 있으면 삭제
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)
        
        # 윈도우 생성
        window = cmds.window(
            self.window_name,
            title="Namespace Manager",
            widthHeight=(450, 500),
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
        cmds.text(label="Namespace Manager", font="boldLabelFont", height=30)
        
        cmds.separator(height=10, style='in')
        cmds.separator(height=10, style='none')
        
        # 설명 텍스트
        cmds.text(
            label="현재 씬의 네임스페이스 목록",
            align='left',
            font="plainLabelFont"
        )
        
        cmds.separator(height=5, style='none')
        
        # 네임스페이스 리스트
        cmds.frameLayout(
            label="Namespaces",
            borderStyle='in',
            collapsable=False,
            marginWidth=5,
            marginHeight=5
        )
        
        # 스크롤 가능한 리스트
        self.namespace_list = cmds.textScrollList(
            numberOfRows=15,
            allowMultiSelection=True,
            selectCommand=self.on_namespace_selected,
            height=300
        )
        
        cmds.setParent('..')  # frameLayout 종료
        
        cmds.separator(height=10, style='none')
        
        # 버튼 레이아웃
        cmds.rowLayout(
            numberOfColumns=3,
            adjustableColumn=1,
            columnAttach=[(1, 'both', 5), (2, 'both', 5), (3, 'both', 5)],
            height=35
        )
        
        cmds.button(
            label="새로고침",
            command=self.refresh_namespace_list,
            backgroundColor=(0.4, 0.4, 0.5)
        )
        
        cmds.button(
            label="선택 삭제",
            command=self.delete_selected_namespaces,
            backgroundColor=(0.6, 0.3, 0.3)
        )
        
        cmds.button(
            label="전체 삭제",
            command=self.delete_all_namespaces,
            backgroundColor=(0.7, 0.2, 0.2)
        )
        
        cmds.setParent('..')  # rowLayout 종료
        
        cmds.separator(height=5, style='none')
        
        # 정보 텍스트
        cmds.text(
            label="* 기본 네임스페이스(UI, shared)는 삭제되지 않습니다.",
            align='left',
            font="smallPlainLabelFont",
            backgroundColor=(0.2, 0.2, 0.2)
        )
        
        # 하단 여백
        cmds.separator(height=15, style='none')
        
        # 윈도우 표시
        cmds.showWindow(window)
        
        # 초기 네임스페이스 로드
        self.refresh_namespace_list()
        
    def get_namespaces(self):
        """씬의 모든 네임스페이스 가져오기 (기본 네임스페이스 제외)"""
        # 모든 네임스페이스 가져오기
        all_namespaces = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True)
        
        # 기본 네임스페이스 제외
        default_namespaces = ['UI', 'shared']
        
        if all_namespaces:
            filtered_namespaces = [
                ns for ns in all_namespaces 
                if ns not in default_namespaces
            ]
            return sorted(filtered_namespaces)
        
        return []
    
    def refresh_namespace_list(self, *args):
        """네임스페이스 리스트 새로고침"""
        # 기존 리스트 클리어
        cmds.textScrollList(self.namespace_list, edit=True, removeAll=True)
        
        # 네임스페이스 가져오기
        namespaces = self.get_namespaces()
        
        if namespaces:
            for ns in namespaces:
                cmds.textScrollList(self.namespace_list, edit=True, append=ns)
            print(f"네임스페이스 {len(namespaces)}개 로드됨")
        else:
            cmds.textScrollList(
                self.namespace_list, 
                edit=True, 
                append="(네임스페이스 없음)"
            )
            print("씬에 네임스페이스가 없습니다.")
    
    def on_namespace_selected(self):
        """네임스페이스 선택 시 호출"""
        selected = cmds.textScrollList(
            self.namespace_list, 
            query=True, 
            selectItem=True
        )
        if selected:
            print(f"선택된 네임스페이스: {', '.join(selected)}")
    
    def delete_namespace(self, namespace):
        """개별 네임스페이스 삭제"""
        try:
            # 네임스페이스가 존재하는지 확인
            if not cmds.namespace(exists=namespace):
                cmds.warning(f"네임스페이스가 존재하지 않습니다: {namespace}")
                return False
            
            # 네임스페이스의 모든 내용을 루트로 이동하고 삭제
            cmds.namespace(removeNamespace=namespace, mergeNamespaceWithRoot=True)
            print(f"네임스페이스 삭제 완료: {namespace}")
            return True
            
        except Exception as e:
            cmds.warning(f"네임스페이스 삭제 실패 ({namespace}): {str(e)}")
            return False
    
    def delete_selected_namespaces(self, *args):
        """선택된 네임스페이스 삭제"""
        selected = cmds.textScrollList(
            self.namespace_list, 
            query=True, 
            selectItem=True
        )
        
        if not selected or selected == ["(네임스페이스 없음)"]:
            cmds.confirmDialog(
                title="경고",
                message="삭제할 네임스페이스를 선택해주세요.",
                button=["확인"],
                defaultButton="확인"
            )
            return
        
        # 확인 대화상자
        confirm = cmds.confirmDialog(
            title="확인",
            message=f"선택한 {len(selected)}개의 네임스페이스를 삭제하시겠습니까?\n\n{', '.join(selected)}",
            button=["삭제", "취소"],
            defaultButton="취소",
            cancelButton="취소",
            dismissString="취소"
        )
        
        if confirm == "삭제":
            success_count = 0
            fail_count = 0
            
            for ns in selected:
                if self.delete_namespace(ns):
                    success_count += 1
                else:
                    fail_count += 1
            
            # 리스트 새로고침
            self.refresh_namespace_list()
            
            # 결과 메시지
            message = f"삭제 완료: {success_count}개"
            if fail_count > 0:
                message += f"\n실패: {fail_count}개"
            
            cmds.confirmDialog(
                title="완료",
                message=message,
                button=["확인"],
                defaultButton="확인"
            )
    
    def delete_all_namespaces(self, *args):
        """모든 네임스페이스 삭제 (기본 제외)"""
        namespaces = self.get_namespaces()
        
        if not namespaces:
            cmds.confirmDialog(
                title="알림",
                message="삭제할 네임스페이스가 없습니다.",
                button=["확인"],
                defaultButton="확인"
            )
            return
        
        # 확인 대화상자
        confirm = cmds.confirmDialog(
            title="경고",
            message=f"모든 네임스페이스({len(namespaces)}개)를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다!",
            button=["삭제", "취소"],
            defaultButton="취소",
            cancelButton="취소",
            dismissString="취소"
        )
        
        if confirm == "삭제":
            success_count = 0
            fail_count = 0
            
            for ns in namespaces:
                if self.delete_namespace(ns):
                    success_count += 1
                else:
                    fail_count += 1
            
            # 리스트 새로고침
            self.refresh_namespace_list()
            
            # 결과 메시지
            message = f"전체 삭제 완료: {success_count}개"
            if fail_count > 0:
                message += f"\n실패: {fail_count}개"
            
            cmds.confirmDialog(
                title="완료",
                message=message,
                button=["확인"],
                defaultButton="확인"
            )


def show():
    """UI 표시 함수"""
    tool = NamespaceManagerTool()
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

