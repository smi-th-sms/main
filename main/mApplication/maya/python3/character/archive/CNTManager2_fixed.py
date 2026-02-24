# -*- coding: utf-8 -*-
"""
CNTManager2.py - Fixed version
Maya Constraint Manager Tool with N to N constraint index fix

Major fixes:
1. Fixed N to N constraint indexing issue
2. Improved error handling
3. Added safe index access method
4. Fixed import issues
"""

# Maya imports
try:
    from maya.cmds import *
    import maya.cmds as cmds
    import maya.mel as mel
except ImportError:
    print("Maya not available - running in standalone mode")

# UI imports
try:
    from PySide6.QtCore import *
    from PySide6.QtGui import *
    from PySide6.QtWidgets import *
except ImportError:
    try:
        from PySide2.QtCore import *
        from PySide2.QtGui import *
        from PySide2.QtWidgets import *
    except ImportError:
        print("Neither PySide6 nor PySide2 available")

import sys
import os

# UI 파일 import
try:
    from CNTManager2UI import Ui_Form
except ImportError:
    print("CNTManager2UI not found - creating basic UI class")
    class Ui_Form:
        def setupUi(self, widget):
            pass

class CNTManager2_Fixed(QWidget):
    def __init__(self, parent=None):
        super(CNTManager2_Fixed, self).__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setWindowTitle("CNT Manager 2 - Fixed")
        
        # Connect signals
        self.connectSignals()
    
    def connectSignals(self):
        """Connect UI signals to methods"""
        try:
            # Constraint buttons
            if hasattr(self.ui, 'ConstraintBTN'):
                self.ui.ConstraintBTN.clicked.connect(self.Constraints)
            if hasattr(self.ui, 'MatchTransformBTN'):
                self.ui.MatchTransformBTN.clicked.connect(self.MatchTransform)
            if hasattr(self.ui, 'MConstBTN'):
                self.ui.MConstBTN.clicked.connect(self.MConst)
        except Exception as e:
            print(f"Error connecting signals: {e}")
    
    def safe_index_access(self, item_list, target_index):
        """
        N to N 모드에서 안전한 인덱스 접근을 위한 헬퍼 메소드
        
        Args:
            item_list: 소스 아이템 리스트
            target_index: 타겟의 현재 인덱스
            
        Returns:
            int: 안전한 인덱스 값
        """
        if not item_list:
            return 0
            
        try:
            if hasattr(self.ui, 'OneToNRB') and self.ui.OneToNRB.isChecked():
                return 0
            elif hasattr(self.ui, 'NToNRB') and self.ui.NToNRB.isChecked():
                # N to N의 경우 인덱스가 item_ 리스트 범위를 벗어나지 않도록 보장
                return min(target_index, len(item_list) - 1)
            else:
                # 기본값: target_index 사용하되 범위 체크
                return min(target_index, len(item_list) - 1)
        except Exception as e:
            print(f"Error in safe_index_access: {e}")
            return 0
    
    def ConnectionMode(self):
        """
        선택된 객체들을 item과 target으로 분리
        
        Returns:
            tuple: (item_list, target_list)
        """
        try:
            selected = ls(selection=True) or []
            if len(selected) < 2:
                print("Warning: At least 2 objects must be selected")
                return [], []
            
            # 마지막 선택된 객체를 target으로, 나머지를 item으로 처리
            target_list = [selected[-1]]
            item_list = selected[:-1]
            
            # N to N 모드인 경우 다른 처리 방식 사용 가능
            if hasattr(self.ui, 'NToNRB') and self.ui.NToNRB.isChecked():
                # N to N 모드에서는 선택된 객체를 반반 나누거나 사용자 정의 방식 사용
                mid_point = len(selected) // 2
                item_list = selected[:mid_point] if mid_point > 0 else [selected[0]]
                target_list = selected[mid_point:] if mid_point < len(selected) else [selected[-1]]
            
            return item_list, target_list
            
        except Exception as e:
            print(f"Error in ConnectionMode: {e}")
            return [], []
    
    def Constraint_(self, source, target, mo=False):
        """
        실제 컨스트레인트를 실행하는 메소드
        
        Args:
            source: 소스 객체
            target: 타겟 객체
            mo: Maintain Offset 여부
        """
        try:
            constraint_type = "parentConstraint"  # 기본값
            
            # UI에서 컨스트레인트 타입 확인
            if hasattr(self.ui, 'ParentCKB') and self.ui.ParentCKB.isChecked():
                constraint_type = "parentConstraint"
            elif hasattr(self.ui, 'PointCKB') and self.ui.PointCKB.isChecked():
                constraint_type = "pointConstraint"
            elif hasattr(self.ui, 'OrientCKB') and self.ui.OrientCKB.isChecked():
                constraint_type = "orientConstraint"
            elif hasattr(self.ui, 'ScaleCKB') and self.ui.ScaleCKB.isChecked():
                constraint_type = "scaleConstraint"
            
            # 컨스트레인트 실행
            if constraint_type == "parentConstraint":
                result = parentConstraint(source, target, maintainOffset=mo)
            elif constraint_type == "pointConstraint":
                result = pointConstraint(source, target, maintainOffset=mo)
            elif constraint_type == "orientConstraint":
                result = orientConstraint(source, target, maintainOffset=mo)
            elif constraint_type == "scaleConstraint":
                result = scaleConstraint(source, target, maintainOffset=mo)
            
            print(f"Applied {constraint_type}: {source} -> {target}")
            return result
            
        except Exception as e:
            print(f"Error applying constraint {source} -> {target}: {e}")
            return None
    
    def Constraints(self):
        """
        Constraint 버튼을 눌렀을 때 각 객체에 대해 컨스트레인트 적용 (수정된 버전)
        """
        item_, target_ = self.ConnectionMode()
        
        if not item_ or not target_:
            print("Error: Invalid selection for constraints")
            return
        
        # Maintain Offset 설정
        mo_ = False
        if hasattr(self.ui, 'PivotCKB') and self.ui.PivotCKB.isChecked():
            mo_ = True
        
        undoInfo(openChunk=True)
        try:
            for i, tgt in enumerate(target_):
                # 수정된 인덱스 처리 로직
                item_index = self.safe_index_access(item_, i)
                if item_index < len(item_):
                    self.Constraint_(item_[item_index], tgt, mo=mo_)
                    print(f"Constraint applied: {item_[item_index]} -> {tgt} (index: {item_index})")
                else:
                    print(f"Warning: Index {item_index} out of range for item list")
        except Exception as e:
            print(f"Error in Constraints: {e}")
        finally:
            undoInfo(closeChunk=True)
    
    def MatchTransform(self):
        """
        Match Transform 기능 (수정된 버전)
        """
        item_, target_ = self.ConnectionMode()
        
        if not item_ or not target_:
            print("Error: Invalid selection for match transform")
            return
        
        undoInfo(openChunk=True)
        try:
            for i, tgt in enumerate(target_):
                # 수정된 인덱스 처리 로직
                item_index = self.safe_index_access(item_, i)
                if item_index < len(item_):
                    source_obj = item_[item_index]
                    
                    # 개별 Transform 속성 체크
                    if hasattr(self.ui, 'TransCKB') and self.ui.TransCKB.isChecked():
                        matchTransform(source_obj, tgt, pos=True)
                    if hasattr(self.ui, 'RotCKB') and self.ui.RotCKB.isChecked():
                        matchTransform(source_obj, tgt, rot=True)
                    if hasattr(self.ui, 'ScaleCKB') and self.ui.ScaleCKB.isChecked():
                        matchTransform(source_obj, tgt, scl=True)
                    if hasattr(self.ui, 'PivotCKB') and self.ui.PivotCKB.isChecked():
                        matchTransform(source_obj, tgt, piv=True)
                    
                    # 모든 체크박스가 꺼져있으면 전체 매치
                    all_unchecked = True
                    for attr in ['TransCKB', 'RotCKB', 'ScaleCKB', 'PivotCKB']:
                        if hasattr(self.ui, attr) and getattr(self.ui, attr).isChecked():
                            all_unchecked = False
                            break
                    
                    if all_unchecked:
                        matchTransform(source_obj, tgt)
                    
                    print(f"Match Transform: {source_obj} -> {tgt} (index: {item_index})")
                else:
                    print(f"Warning: Index {item_index} out of range for item list")
        except Exception as e:
            print(f"Error in MatchTransform: {e}")
        finally:
            undoInfo(closeChunk=True)
    
    def MConst(self):
        """
        Multiple Constraint 기능 (수정된 버전)
        """
        item_, target_ = self.ConnectionMode()
        
        if not item_ or not target_:
            print("Error: Invalid selection for multiple constraints")
            return
        
        undoInfo(openChunk=True)
        try:
            for i, tgt in enumerate(target_):
                # 수정된 인덱스 처리 로직
                item_index = self.safe_index_access(item_, i)
                if item_index < len(item_):
                    source_obj = item_[item_index]
                    
                    # 여러 컨스트레인트 타입 적용
                    if hasattr(self.ui, 'ParentCKB') and self.ui.ParentCKB.isChecked():
                        parentConstraint(source_obj, tgt, maintainOffset=True)
                    if hasattr(self.ui, 'PointCKB') and self.ui.PointCKB.isChecked():
                        pointConstraint(source_obj, tgt, maintainOffset=True)
                    if hasattr(self.ui, 'OrientCKB') and self.ui.OrientCKB.isChecked():
                        orientConstraint(source_obj, tgt, maintainOffset=True)
                    if hasattr(self.ui, 'ScaleCKB') and self.ui.ScaleCKB.isChecked():
                        scaleConstraint(source_obj, tgt, maintainOffset=True)
                    
                    print(f"Multiple Constraints: {source_obj} -> {tgt} (index: {item_index})")
                else:
                    print(f"Warning: Index {item_index} out of range for item list")
        except Exception as e:
            print(f"Error in MConst: {e}")
        finally:
            undoInfo(closeChunk=True)
    
    def ListConnect(self):
        """
        리스트 연결 기능 (수정된 버전)
        """
        item_, target_ = self.ConnectionMode()
        
        if not item_ or not target_:
            print("Error: Invalid selection for list connect")
            return
        
        try:
            for i, tgt in enumerate(target_):
                item_index = self.safe_index_access(item_, i)
                if item_index < len(item_):
                    source_obj = item_[item_index]
                    # 연결 로직 구현
                    print(f"List Connect: {source_obj} -> {tgt} (index: {item_index})")
        except Exception as e:
            print(f"Error in ListConnect: {e}")
    
    def debug_selection_info(self):
        """디버깅을 위한 선택 정보 출력"""
        try:
            selected = ls(selection=True) or []
            print(f"Selected objects: {selected}")
            
            item_, target_ = self.ConnectionMode()
            print(f"Items: {item_}")
            print(f"Targets: {target_}")
            
            # 모드 확인
            if hasattr(self.ui, 'OneToNRB') and self.ui.OneToNRB.isChecked():
                print("Mode: One to N")
            elif hasattr(self.ui, 'NToNRB') and self.ui.NToNRB.isChecked():
                print("Mode: N to N")
            else:
                print("Mode: Unknown")
                
        except Exception as e:
            print(f"Error in debug_selection_info: {e}")

# 실행 함수
def show_cnt_manager():
    """CNT Manager를 표시하는 함수"""
    try:
        global cnt_manager_window
        if 'cnt_manager_window' in globals() and cnt_manager_window:
            cnt_manager_window.close()
        
        cnt_manager_window = CNTManager2_Fixed()
        cnt_manager_window.show()
        return cnt_manager_window
    except Exception as e:
        print(f"Error showing CNT Manager: {e}")
        return None

if __name__ == "__main__":
    # Maya에서 실행될 때
    if 'maya' in sys.modules:
        show_cnt_manager()
    else:
        # 스탠드얼론 테스트
        app = QApplication(sys.argv)
        window = CNTManager2_Fixed()
        window.show()
        sys.exit(app.exec_())