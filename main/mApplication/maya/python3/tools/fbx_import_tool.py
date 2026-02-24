"""
FBX Import Tool for Maya
간단한 FBX 파일 임포트 UI 툴

사용법:
    # 첫 실행
    import fbx_import_tool
    fbx_import_tool.show()
    
    # 모듈 수정 후 리로드
    import fbx_import_tool
    fbx_import_tool.reload_and_show()
"""

import maya.cmds as cmds
import os
import sys
import importlib


class FBXImportTool:
    """FBX 파일을 임포트하는 간단한 UI 툴"""
    
    def __init__(self):
        self.window_name = "fbxImportToolWindow"
        self.file_path = ""
        
    def create_ui(self):
        """UI 생성"""
        # 기존 윈도우가 있으면 삭제
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)
        
        # 윈도우 생성
        window = cmds.window(
            self.window_name,
            title="FBX Import Tool",
            widthHeight=(600, 180),
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
        cmds.text(label="FBX Import Tool", font="boldLabelFont", height=30)
        
        cmds.separator(height=10, style='in')
        cmds.separator(height=10, style='none')
        
        # 파일 경로 선택 섹션
        cmds.rowLayout(
            numberOfColumns=3,
            adjustableColumn=2,
            columnAttach=[(1, 'right', 5), (2, 'both', 5), (3, 'left', 5)],
            columnWidth3=(70, 100, 80),
            height=30
        )
        
        cmds.text(label="FBX 파일:", align='right')
        self.path_field = cmds.textField(
            text="",
            editable=True,
            placeholderText="FBX 파일 경로를 선택하세요..."
        )
        cmds.button(
            label="찾아보기",
            command=self.browse_file,
            backgroundColor=(0.4, 0.4, 0.4),
            width=80
        )
        
        cmds.setParent('..')  # rowLayout 종료
        
        cmds.separator(height=15, style='none')
        
        # Import 버튼
        cmds.button(
            label="Import",
            command=self.import_fbx,
            height=40,
            backgroundColor=(0.3, 0.5, 0.3)
        )
        
        # 하단 여백
        cmds.separator(height=15, style='none')
        
        # 윈도우 표시
        cmds.showWindow(window)
        
    def browse_file(self, *args):
        """파일 브라우저를 열어 FBX 파일 선택"""
        file_path = cmds.fileDialog2(
            fileMode=1,  # 단일 파일 선택
            caption="FBX 파일 선택",
            fileFilter="FBX Files (*.fbx);;All Files (*.*)",
            dialogStyle=2
        )
        
        if file_path:
            self.file_path = file_path[0]
            cmds.textField(self.path_field, edit=True, text=self.file_path)
            
    def import_fbx(self, *args):
        """FBX 파일 임포트"""
        # 텍스트 필드에서 경로 가져오기
        file_path = cmds.textField(self.path_field, query=True, text=True)
        
        if not file_path:
            cmds.warning("FBX 파일 경로를 선택해주세요.")
            cmds.confirmDialog(
                title="경고",
                message="FBX 파일 경로를 선택해주세요.",
                button=["확인"],
                defaultButton="확인"
            )
            return
        
        if not os.path.exists(file_path):
            cmds.warning(f"파일을 찾을 수 없습니다: {file_path}")
            cmds.confirmDialog(
                title="오류",
                message=f"파일을 찾을 수 없습니다:\n{file_path}",
                button=["확인"],
                defaultButton="확인"
            )
            return
        
        if not file_path.lower().endswith('.fbx'):
            cmds.warning("FBX 파일만 임포트 가능합니다.")
            cmds.confirmDialog(
                title="경고",
                message="FBX 파일만 임포트 가능합니다.",
                button=["확인"],
                defaultButton="확인"
            )
            return
        
        try:
            # FBX 플러그인 로드
            if not cmds.pluginInfo('fbxmaya', query=True, loaded=True):
                cmds.loadPlugin('fbxmaya')
            
            # FBX 임포트
            cmds.file(
                file_path,
                i=True,  # import
                type="FBX",
                ignoreVersion=True,
                mergeNamespacesOnClash=False,
                options="fbx"
            )
            
            print(f"FBX 파일 임포트 완료: {file_path}")
            cmds.confirmDialog(
                title="완료",
                message=f"FBX 파일 임포트 완료!\n\n{os.path.basename(file_path)}",
                button=["확인"],
                defaultButton="확인"
            )
            
        except Exception as e:
            error_msg = f"FBX 임포트 중 오류 발생: {str(e)}"
            cmds.warning(error_msg)
            cmds.confirmDialog(
                title="오류",
                message=error_msg,
                button=["확인"],
                defaultButton="확인"
            )


def show():
    """UI 표시 함수"""
    tool = FBXImportTool()
    tool.create_ui()


def reload_and_show():
    """모듈을 다시 로드하고 UI 표시"""
    # 현재 모듈 이름 가져오기
    module_name = __name__
    
    # 모듈이 이미 로드되어 있으면 리로드
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
        print(f"모듈 리로드 완료: {module_name}")
    
    # UI 표시
    show()


# 스크립트 직접 실행 시
if __name__ == "__main__":
    show()

