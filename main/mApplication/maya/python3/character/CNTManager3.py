# -*- coding: utf-8 -*-
"""============================================================================
Module descriptions.
CNTManager3 - Constraint Manager Tool

__AUTHOR__ = 'SUNGSEO'
__UPDATE__ = 20250101

Features:
1. Refactored to use core modules
2. Improved error handling and logging
3. Better code organization
4. Enhanced maintainability

:Example:
from python3.character.CNTManager3 import CNTManager3
CNTManager3.runWin()

============================================================================"""

import sys
import maya.OpenMayaUI as omui
from maya import cmds

# Core modules import - 동적 경로 설정으로 안정적인 import
import sys
import os

# 현재 파일의 상위 디렉토리(python3)를 sys.path에 추가
try:
    current_file = os.path.abspath(__file__)
except NameError:
    # Maya console에서 실행 시 __file__이 정의되지 않은 경우
    import inspect
    current_file = os.path.abspath(inspect.getfile(inspect.currentframe()))

current_dir = os.path.dirname(current_file)
python3_dir = os.path.dirname(current_dir)  # character -> python3
maya_dir = os.path.dirname(python3_dir)     # python3 -> maya

if maya_dir not in sys.path:
    sys.path.insert(0, maya_dir)
    
# python3 디렉토리도 추가 (상대 import를 위해)
if python3_dir not in sys.path:
    sys.path.insert(0, python3_dir)

# 이제 절대 import 사용 가능
from python3.core.base_ui import BaseMayaUI
from python3.core.maya_utils import MayaUtils
from python3.core.logger import ToolLogger

# UI imports with fallback
try:
    from PySide6.QtCore import *
    from PySide6.QtGui import *
    from PySide6.QtWidgets import *
    from PySide6 import __version__
    from shiboken6 import wrapInstance
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide2.QtCore import *
        from PySide2.QtGui import *
        from PySide2.QtWidgets import *
        from PySide2 import __version__
        from shiboken2 import wrapInstance
        from PySide2 import QtCore, QtGui, QtWidgets
    except ImportError:
        print("Neither PySide6 nor PySide2 available - UI functionality limited")
        # Fallback for basic functionality
        class QWidget:
            def __init__(self, parent=None):
                pass
            def setWindowFlags(self, flags):
                pass
            def show(self):
                pass
            def close(self):
                pass
                
        class Qt:
            Window = None


class AttrPickerDialog(QtWidgets.QDialog):
    """오브젝트의 모든 attribute를 검색/선택할 수 있는 다이얼로그"""

    def __init__(self, obj_name, parent=None):
        super(AttrPickerDialog, self).__init__(parent)
        self.setWindowTitle(f"Attributes  —  {obj_name}")
        self.setMinimumSize(260, 420)
        self.selected_attr = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self.filterLE = QtWidgets.QLineEdit()
        self.filterLE.setPlaceholderText("Filter attributes...")
        layout.addWidget(self.filterLE)

        self.attrList = QtWidgets.QListWidget()
        layout.addWidget(self.attrList)

        btn_layout = QtWidgets.QHBoxLayout()
        self.okBtn = QtWidgets.QPushButton("OK")
        self.cancelBtn = QtWidgets.QPushButton("Cancel")
        btn_layout.addWidget(self.okBtn)
        btn_layout.addWidget(self.cancelBtn)
        layout.addLayout(btn_layout)

        self._all_attrs = sorted(cmds.listAttr(obj_name) or [])
        self.attrList.addItems(self._all_attrs)

        self.filterLE.textChanged.connect(self._filter)
        self.attrList.itemDoubleClicked.connect(self._accept)
        self.okBtn.clicked.connect(self._accept)
        self.cancelBtn.clicked.connect(self.reject)

    def _filter(self, text):
        text = text.lower()
        for i in range(self.attrList.count()):
            item = self.attrList.item(i)
            item.setHidden(text not in item.text().lower())

    def _accept(self):
        current = self.attrList.currentItem()
        if current:
            self.selected_attr = current.text()
            self.accept()

    def get_selected(self):
        return self.selected_attr


class Ui_CNTManager(object):
    def setupUi(self, CNTManager):
        CNTManager.setObjectName("CNTManager")
        CNTManager.resize(430, 720)
        self.gridLayout_3 = QtWidgets.QGridLayout(CNTManager)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.AlistWidget = QtWidgets.QListWidget(CNTManager)
        self.AlistWidget.setDragEnabled(True)
        self.AlistWidget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.AlistWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.AlistWidget.setObjectName("AlistWidget")
        self.gridLayout.addWidget(self.AlistWidget, 0, 0, 1, 2)
        self.AAddPB = QtWidgets.QPushButton(CNTManager)
        self.AAddPB.setObjectName("AAddPB")
        self.gridLayout.addWidget(self.AAddPB, 1, 0, 1, 1)
        self.ARemovePB = QtWidgets.QPushButton(CNTManager)
        self.ARemovePB.setObjectName("ARemovePB")
        self.gridLayout.addWidget(self.ARemovePB, 1, 1, 1, 1)
        self.horizontalLayout_5.addLayout(self.gridLayout)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_3.addItem(spacerItem)
        self.SortPB = QtWidgets.QPushButton(CNTManager)
        self.SortPB.setFlat(True)
        self.SortPB.setObjectName("SortPB")
        self.verticalLayout_3.addWidget(self.SortPB)
        self.ChangePB = QtWidgets.QPushButton(CNTManager)
        self.ChangePB.setFlat(True)
        self.ChangePB.setObjectName("ChangePB")
        self.verticalLayout_3.addWidget(self.ChangePB)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.OneToNRB = QtWidgets.QRadioButton(CNTManager)
        self.OneToNRB.setChecked(False)
        self.OneToNRB.setObjectName("OneToNRB")
        self.verticalLayout.addWidget(self.OneToNRB)
        self.NToNRB = QtWidgets.QRadioButton(CNTManager)
        self.NToNRB.setChecked(True)
        self.NToNRB.setObjectName("NToNRB")
        self.verticalLayout.addWidget(self.NToNRB)
        self.verticalLayout_3.addLayout(self.verticalLayout)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_3.addItem(spacerItem1)
        self.horizontalLayout_5.addLayout(self.verticalLayout_3)
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.BlistWidget = QtWidgets.QListWidget(CNTManager)
        self.BlistWidget.setDragEnabled(True)
        self.BlistWidget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.BlistWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.BlistWidget.setObjectName("BlistWidget")
        self.gridLayout_2.addWidget(self.BlistWidget, 0, 0, 1, 2)
        self.BAddPB = QtWidgets.QPushButton(CNTManager)
        self.BAddPB.setObjectName("BAddPB")
        self.gridLayout_2.addWidget(self.BAddPB, 1, 0, 1, 1)
        self.BRemovePB = QtWidgets.QPushButton(CNTManager)
        self.BRemovePB.setObjectName("BRemovePB")
        self.gridLayout_2.addWidget(self.BRemovePB, 1, 1, 1, 1)
        self.horizontalLayout_5.addLayout(self.gridLayout_2)
        self.gridLayout_3.addLayout(self.horizontalLayout_5, 0, 0, 1, 1)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.OutLE = QtWidgets.QLineEdit(CNTManager)
        self.OutLE.setObjectName("OutLE")
        self.horizontalLayout_2.addWidget(self.OutLE)
        self.ConnectionPB = QtWidgets.QPushButton(CNTManager)
        self.ConnectionPB.setFlat(True)
        self.ConnectionPB.setObjectName("ConnectionPB")
        self.horizontalLayout_2.addWidget(self.ConnectionPB)
        self.InLE = QtWidgets.QLineEdit(CNTManager)
        self.InLE.setObjectName("InLE")
        self.horizontalLayout_2.addWidget(self.InLE)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.GetSetPB = QtWidgets.QPushButton(CNTManager)
        self.GetSetPB.setObjectName("GetSetPB")
        self.horizontalLayout_3.addWidget(self.GetSetPB)
        self.PPPB = QtWidgets.QPushButton(CNTManager)
        self.PPPB.setObjectName("PPPB")
        self.horizontalLayout_3.addWidget(self.PPPB)
        self.SetDrivenPB = QtWidgets.QPushButton(CNTManager)
        self.SetDrivenPB.setObjectName("SetDrivenPB")
        self.horizontalLayout_3.addWidget(self.SetDrivenPB)
        self.verticalLayout_2.addLayout(self.horizontalLayout_3)
        self.line = QtWidgets.QFrame(CNTManager)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.verticalLayout_2.addWidget(self.line)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.AllCKB = QtWidgets.QCheckBox(CNTManager)
        self.AllCKB.setChecked(True)
        self.AllCKB.setObjectName("AllCKB")
        self.horizontalLayout.addWidget(self.AllCKB)
        self.TransCKB = QtWidgets.QCheckBox(CNTManager)
        self.TransCKB.setChecked(False)
        self.TransCKB.setObjectName("TransCKB")
        self.horizontalLayout.addWidget(self.TransCKB)
        self.RotCKB = QtWidgets.QCheckBox(CNTManager)
        self.RotCKB.setObjectName("RotCKB")
        self.horizontalLayout.addWidget(self.RotCKB)
        self.ScaleCKB = QtWidgets.QCheckBox(CNTManager)
        self.ScaleCKB.setObjectName("ScaleCKB")
        self.horizontalLayout.addWidget(self.ScaleCKB)
        self.ShearCKB = QtWidgets.QCheckBox(CNTManager)
        self.ShearCKB.setObjectName("ShearCKB")
        self.horizontalLayout.addWidget(self.ShearCKB)
        self.PivotCKB = QtWidgets.QCheckBox(CNTManager)
        self.PivotCKB.setChecked(True)
        self.PivotCKB.setObjectName("PivotCKB")
        self.horizontalLayout.addWidget(self.PivotCKB)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.MatchPB = QtWidgets.QPushButton(CNTManager)
        self.MatchPB.setObjectName("MatchPB")
        self.horizontalLayout_4.addWidget(self.MatchPB)
        self.MConPB = QtWidgets.QPushButton(CNTManager)
        self.MConPB.setObjectName("MConPB")
        self.horizontalLayout_4.addWidget(self.MConPB)
        self.ConstPB = QtWidgets.QPushButton(CNTManager)
        self.ConstPB.setObjectName("ConstPB")
        self.horizontalLayout_4.addWidget(self.ConstPB)
        self.verticalLayout_2.addLayout(self.horizontalLayout_4)
        self.line2 = QtWidgets.QFrame(CNTManager)
        self.line2.setFrameShape(QtWidgets.QFrame.HLine)
        self.line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line2.setObjectName("line2")
        self.verticalLayout_2.addWidget(self.line2)
        self.batchAttrLayout = QtWidgets.QHBoxLayout()
        self.batchAttrLayout.setObjectName("batchAttrLayout")
        self.batchAttrLabel = QtWidgets.QLabel(CNTManager)
        self.batchAttrLabel.setObjectName("batchAttrLabel")
        self.batchAttrLayout.addWidget(self.batchAttrLabel)
        self.batchAttrLE = QtWidgets.QLineEdit(CNTManager)
        self.batchAttrLE.setObjectName("batchAttrLE")
        self.batchAttrLayout.addWidget(self.batchAttrLE)
        self.batchAttrPickPB = QtWidgets.QPushButton(CNTManager)
        self.batchAttrPickPB.setObjectName("batchAttrPickPB")
        self.batchAttrLayout.addWidget(self.batchAttrPickPB)
        self.verticalLayout_2.addLayout(self.batchAttrLayout)
        self.batchValueLayout = QtWidgets.QHBoxLayout()
        self.batchValueLayout.setObjectName("batchValueLayout")
        self.batchValueLabel = QtWidgets.QLabel(CNTManager)
        self.batchValueLabel.setObjectName("batchValueLabel")
        self.batchValueLayout.addWidget(self.batchValueLabel)
        self.batchValueLE = QtWidgets.QLineEdit(CNTManager)
        self.batchValueLE.setObjectName("batchValueLE")
        self.batchValueLayout.addWidget(self.batchValueLE)
        self.batchAttrGetPB = QtWidgets.QPushButton(CNTManager)
        self.batchAttrGetPB.setObjectName("batchAttrGetPB")
        self.batchValueLayout.addWidget(self.batchAttrGetPB)
        self.batchAttrSetPB = QtWidgets.QPushButton(CNTManager)
        self.batchAttrSetPB.setObjectName("batchAttrSetPB")
        self.batchValueLayout.addWidget(self.batchAttrSetPB)
        self.verticalLayout_2.addLayout(self.batchValueLayout)
        self.gridLayout_3.addLayout(self.verticalLayout_2, 1, 0, 1, 1)
        self.verticalLayout_4 = QtWidgets.QVBoxLayout()
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.AUTHORLB = QtWidgets.QLabel(CNTManager)
        self.AUTHORLB.setAlignment(QtCore.Qt.AlignCenter)
        self.AUTHORLB.setObjectName("AUTHORLB")
        self.verticalLayout_4.addWidget(self.AUTHORLB)
        self.UPDATALB = QtWidgets.QLabel(CNTManager)
        self.UPDATALB.setAlignment(QtCore.Qt.AlignCenter)
        self.UPDATALB.setObjectName("UPDATALB")
        self.verticalLayout_4.addWidget(self.UPDATALB)
        self.gridLayout_3.addLayout(self.verticalLayout_4, 2, 0, 1, 1)

        self.retranslateUi(CNTManager)
        QtCore.QMetaObject.connectSlotsByName(CNTManager)

    def retranslateUi(self, CNTManager):
        CNTManager.setWindowTitle(QtWidgets.QApplication.translate("CNTManager", "CNTManager - Refactored", None))
        self.AAddPB.setText(QtWidgets.QApplication.translate("CNTManager", "Add", None))
        self.ARemovePB.setText(QtWidgets.QApplication.translate("CNTManager", "Remove", None))
        self.SortPB.setText(QtWidgets.QApplication.translate("CNTManager", "Sort", None))
        self.ChangePB.setText(QtWidgets.QApplication.translate("CNTManager", "Change", None))
        self.OneToNRB.setText(QtWidgets.QApplication.translate("CNTManager", "One To N", None))
        self.NToNRB.setText(QtWidgets.QApplication.translate("CNTManager", "N To N", None))
        self.BAddPB.setText(QtWidgets.QApplication.translate("CNTManager", "Add", None))
        self.BRemovePB.setText(QtWidgets.QApplication.translate("CNTManager", "Remove", None))
        self.OutLE.setText(QtWidgets.QApplication.translate("CNTManager", "OutPut..", None))
        self.ConnectionPB.setText(QtWidgets.QApplication.translate("CNTManager", ">>", None))
        self.InLE.setText(QtWidgets.QApplication.translate("CNTManager", "InPut..", None))
        self.GetSetPB.setText(QtWidgets.QApplication.translate("CNTManager", "Get Set", None))
        self.PPPB.setText(QtWidgets.QApplication.translate("CNTManager", "PParent", None))
        self.SetDrivenPB.setText(QtWidgets.QApplication.translate("CNTManager", "SetDriven", None))
        self.AllCKB.setText(QtWidgets.QApplication.translate("CNTManager", "All", None))
        self.TransCKB.setText(QtWidgets.QApplication.translate("CNTManager", "Trans", None))
        self.RotCKB.setText(QtWidgets.QApplication.translate("CNTManager", "Rot", None))
        self.ScaleCKB.setText(QtWidgets.QApplication.translate("CNTManager", "Scale", None))
        self.ShearCKB.setText(QtWidgets.QApplication.translate("CNTManager", "Shear", None))
        self.PivotCKB.setText(QtWidgets.QApplication.translate("CNTManager", "Pivot", None))
        self.MatchPB.setText(QtWidgets.QApplication.translate("CNTManager", "Match", None))
        self.MConPB.setText(QtWidgets.QApplication.translate("CNTManager", "MCon", None))
        self.ConstPB.setText(QtWidgets.QApplication.translate("CNTManager", "Const", None))
        self.batchAttrLabel.setText(QtWidgets.QApplication.translate("CNTManager", "Attr :", None))
        self.batchAttrPickPB.setText(QtWidgets.QApplication.translate("CNTManager", "Pick", None))
        self.batchValueLabel.setText(QtWidgets.QApplication.translate("CNTManager", "Value:", None))
        self.batchAttrGetPB.setText(QtWidgets.QApplication.translate("CNTManager", "Get", None))
        self.batchAttrSetPB.setText(QtWidgets.QApplication.translate("CNTManager", "Set All", None))
        self.AUTHORLB.setText(QtWidgets.QApplication.translate("CNTManager", "AUTHOR : MinSung", None))
        self.UPDATALB.setText(QtWidgets.QApplication.translate("CNTManager", "UPDATE : 20250101 - Refactored", None))


class CNTManager3(BaseMayaUI):
    """리팩토링된 CNTManager3 클래스"""
    
    def __init__(self, parent=None, *args, **kwargs):
        super(CNTManager3, self).__init__(parent, *args, **kwargs)
        
        # 로거 초기화
        self.logger = ToolLogger("CNTManager3")
        
        # UI 설정
        self.ui = Ui_CNTManager()
        self.ui.setupUi(self)
        
        # 위젯 참조
        self.Alist_ = self.ui.AlistWidget
        self.Blist_ = self.ui.BlistWidget
        
        # 이벤트 연결
        self._connect_signals()
        
        self.logger.info("CNTManager3 initialized")
    
    def _connect_signals(self):
        """시그널 연결"""
        self.ui.AAddPB.clicked.connect(self.add_a_list_widget)
        self.ui.BAddPB.clicked.connect(self.add_b_list_widget)
        self.ui.ARemovePB.clicked.connect(self.a_remove_current_item)
        self.ui.BRemovePB.clicked.connect(self.b_remove_current_item)
        self.ui.SortPB.clicked.connect(self.sort_items)
        self.ui.ChangePB.clicked.connect(self.change_items)
        self.ui.PPPB.clicked.connect(self.pparent_items)
        self.ui.OneToNRB.clicked.connect(self.connection_mode)
        self.ui.NToNRB.clicked.connect(self.connection_mode)
        self.ui.ConnectionPB.clicked.connect(self.list_connect)
        self.ui.GetSetPB.clicked.connect(self.list_set)
        self.ui.ConstPB.clicked.connect(self.constraints)
        self.ui.MatchPB.clicked.connect(self.match_transform)
        self.ui.SetDrivenPB.clicked.connect(self.set_drivens)
        self.ui.MConPB.clicked.connect(self.m_const)
        self.ui.batchAttrPickPB.clicked.connect(self.batch_attr_pick)
        self.ui.batchAttrGetPB.clicked.connect(self.batch_attr_get)
        self.ui.batchAttrSetPB.clicked.connect(self.batch_attr_set)
    
    def safe_index_access(self, item_list, target_index):
        """OneToN / NToN 모드에 따른 안전한 인덱스 반환"""
        if not item_list:
            return 0
        if self.ui.OneToNRB.isChecked():
            return 0
        return min(target_index, len(item_list) - 1)
    
    def add_a_list_widget(self):
        """A 리스트에 아이템 추가"""
        self.logger.log_ui_action("Add items to A list")
        self.Alist_.clear()
        selection = MayaUtils.get_selection()
        for item in selection:
            self.Alist_.addItem(str(item))
        MayaUtils.clear_selection()
        self.logger.info(f"Added {len(selection)} items to A list")
    
    def add_b_list_widget(self):
        """B 리스트에 아이템 추가"""
        self.logger.log_ui_action("Add items to B list")
        self.Blist_.clear()
        selection = MayaUtils.get_selection()
        for item in selection:
            self.Blist_.addItem(str(item))
        MayaUtils.clear_selection()
        self.logger.info(f"Added {len(selection)} items to B list")
    
    def a_print_multi_items(self):
        """A 리스트에서 선택된 아이템들 반환"""
        select_list = []
        selected_items = self.Alist_.selectedItems()
        for item in selected_items:
            select_list.append(item.text())
        return selected_items, select_list
    
    def b_print_multi_items(self):
        """B 리스트에서 선택된 아이템들 반환"""
        select_list = []
        selected_items = self.Blist_.selectedItems()
        for item in selected_items:
            select_list.append(item.text())
        return selected_items, select_list
    
    def a_remove_current_item(self):
        """A 리스트에서 선택된 아이템 제거"""
        self.logger.log_ui_action("Remove items from A list")
        selected_items = self.a_print_multi_items()[0]
        for item in selected_items:
            row = self.Alist_.currentRow()
            self.Alist_.takeItem(row)
        self.logger.info(f"Removed {len(selected_items)} items from A list")
    
    def b_remove_current_item(self):
        """B 리스트에서 선택된 아이템 제거"""
        self.logger.log_ui_action("Remove items from B list")
        selected_items = self.b_print_multi_items()[0]
        for item in selected_items:
            row = self.Blist_.currentRow()
            self.Blist_.takeItem(row)
        self.logger.info(f"Removed {len(selected_items)} items from B list")
    
    def a_all_list_item(self):
        """A 리스트의 모든 아이템 반환"""
        return [self.Alist_.item(i).text() for i in range(self.Alist_.count())]
    
    def b_all_list_item(self):
        """B 리스트의 모든 아이템 반환"""
        return [self.Blist_.item(i).text() for i in range(self.Blist_.count())]
    
    def sort_items(self):
        """리스트 아이템 정렬"""
        self.logger.log_ui_action("Sort items")
        a_list = self.a_all_list_item()
        a_list.sort()
        b_list = self.b_all_list_item()
        b_list.sort()
        
        cmds.select(a_list)
        self.add_a_list_widget()
        cmds.select(b_list)
        self.add_b_list_widget()
        self.logger.info("Items sorted")
    
    def change_items(self):
        """A, B 리스트 내용 교체"""
        self.logger.log_ui_action("Swap A and B lists")
        a_list = self.a_all_list_item()
        b_list = self.b_all_list_item()
        
        cmds.select(b_list)
        self.add_a_list_widget()
        cmds.select(a_list)
        self.add_b_list_widget()
        self.logger.info("Lists swapped")
    
    def connection_mode(self):
        """연결 모드에 따른 선택된 아이템들 반환"""
        a_select = self.a_print_multi_items()[1]
        b_select = self.b_print_multi_items()[1]
        return a_select, b_select
    
    def print_text_edit(self):
        """텍스트 입력 필드 값 반환"""
        out_attr = self.ui.OutLE.text()
        in_attr = self.ui.InLE.text()
        return out_attr, in_attr
    
    def list_connect(self):
        """리스트 아이템들 연결"""
        self.logger.log_operation_start("List Connect")
        out_attr, in_attr = self.print_text_edit()
        items, targets = self.connection_mode()
        
        if not items or not targets:
            self.logger.error("Invalid selection for list connect")
            return
        
        cmds.undoInfo(openChunk=True)
        try:
            for i, target in enumerate(targets):
                item_index = self.safe_index_access(items, i)
                if item_index < len(items):
                    source_attr = f"{items[item_index]}.{out_attr}"
                    target_attr = f"{target}.{in_attr}"
                    cmds.connectAttr(source_attr, target_attr, force=True)
                    self.logger.debug(f"Connected: {source_attr} -> {target_attr}")
                else:
                    self.logger.warning(f"Index {item_index} out of range for item list")
        except Exception as e:
            self.logger.error(f"Error in list connect: {e}")
        finally:
            cmds.undoInfo(closeChunk=True)
        
        self.logger.log_operation_end("List Connect", True)
    
    def list_set(self):
        """리스트 아이템들 속성 설정"""
        self.logger.log_operation_start("List Set")
        out_attr, in_attr = self.print_text_edit()
        items, targets = self.connection_mode()
        
        if not items or not targets:
            self.logger.error("Invalid selection for list set")
            return
        
        cmds.undoInfo(openChunk=True)
        try:
            for i, target in enumerate(targets):
                item_index = self.safe_index_access(items, i)
                if item_index < len(items):
                    source_attr = f"{items[item_index]}.{out_attr}"
                    target_attr = f"{target}.{in_attr}"
                    get_attr_value = cmds.getAttr(source_attr)
                    cmds.setAttr(target_attr, get_attr_value)
                    self.logger.debug(f"Set: {target_attr} = {get_attr_value}")
                else:
                    self.logger.warning(f"Index {item_index} out of range for item list")
        except Exception as e:
            self.logger.error(f"Error in list set: {e}")
        finally:
            cmds.undoInfo(closeChunk=True)
        
        self.logger.log_operation_end("List Set", True)
    
    def pparent_items(self):
        """리스트 아이템들 페어런팅"""
        self.logger.log_operation_start("Parent Items")
        items, targets = self.connection_mode()
        
        if not items or not targets:
            self.logger.error("Invalid selection for parent")
            return
        
        cmds.undoInfo(openChunk=True)
        try:
            for i, target in enumerate(targets):
                item_index = self.safe_index_access(items, i)
                if item_index < len(items):
                    cmds.parent(items[item_index], target)
                    self.logger.debug(f"Parented: {items[item_index]} -> {target}")
                else:
                    self.logger.warning(f"Index {item_index} out of range for item list")
        except Exception as e:
            self.logger.error(f"Error in parent items: {e}")
        finally:
            cmds.undoInfo(closeChunk=True)
        
        self.logger.log_operation_end("Parent Items", True)
    
    def set_drivens(self):
        """Set Driven Key 설정"""
        self.logger.log_operation_start("Set Driven Keys")
        out_attr, in_attr = self.print_text_edit()
        items, targets = self.connection_mode()
        
        if not items or not targets:
            self.logger.error("Invalid selection for set driven")
            return
        
        cmds.undoInfo(openChunk=True)
        try:
            for i, target in enumerate(targets):
                item_index = self.safe_index_access(items, i)
                if item_index < len(items):
                    target_attr = f"{target}.{in_attr}"
                    driver_attr = f"{items[item_index]}.{out_attr}"
                    cmds.setDrivenKeyframe(target_attr, cd=driver_attr)
                    self.logger.debug(f"Set Driven: {driver_attr} -> {target_attr}")
                else:
                    self.logger.warning(f"Index {item_index} out of range for item list")
        except Exception as e:
            self.logger.error(f"Error in set driven keys: {e}")
        finally:
            cmds.undoInfo(closeChunk=True)
        
        self.logger.log_operation_end("Set Driven Keys", True)
    
    def constraint_(self, *args, **kwargs):
        """컨스트레인트 생성 헬퍼"""
        if self.ui.AllCKB.isChecked():
            cmds.parentConstraint(*args, maintainOffset=kwargs['mo'])
        if self.ui.TransCKB.isChecked():
            cmds.pointConstraint(*args, maintainOffset=kwargs['mo'])
        if self.ui.RotCKB.isChecked():
            cmds.orientConstraint(*args, maintainOffset=kwargs['mo'])
        if self.ui.ScaleCKB.isChecked():
            cmds.scaleConstraint(*args, maintainOffset=kwargs['mo'])
    
    def constraints(self):
        """컨스트레인트 적용"""
        self.logger.log_operation_start("Apply Constraints")
        items, targets = self.connection_mode()
        
        if not items or not targets:
            self.logger.error("Invalid selection for constraints")
            return
        
        mo = 1 if self.ui.PivotCKB.isChecked() else 0
        
        cmds.undoInfo(openChunk=True)
        try:
            for i, target in enumerate(targets):
                item_index = self.safe_index_access(items, i)
                if item_index < len(items):
                    self.constraint_(items[item_index], target, mo=mo)
                    self.logger.debug(f"Constraint applied: {items[item_index]} -> {target}")
                else:
                    self.logger.warning(f"Index {item_index} out of range for item list")
        except Exception as e:
            self.logger.error(f"Error in constraints: {e}")
        finally:
            cmds.undoInfo(closeChunk=True)
        
        self.logger.log_operation_end("Apply Constraints", True)
    
    def match_transform(self):
        """트랜스폼 매치"""
        self.logger.log_operation_start("Match Transform")
        items, targets = self.connection_mode()
        
        if not items or not targets:
            self.logger.error("Invalid selection for match transform")
            return
        
        cmds.undoInfo(openChunk=True)
        try:
            for i, target in enumerate(targets):
                item_index = self.safe_index_access(items, i)
                if item_index < len(items):
                    source_obj = items[item_index]
                    
                    if self.ui.AllCKB.isChecked():
                        MayaUtils.match_transform(source_obj, target)
                    if self.ui.TransCKB.isChecked():
                        MayaUtils.match_transform(source_obj, target, pos=True, rot=False, scl=False)
                    if self.ui.RotCKB.isChecked():
                        MayaUtils.match_transform(source_obj, target, pos=False, rot=True, scl=False)
                    if self.ui.ScaleCKB.isChecked():
                        MayaUtils.match_transform(source_obj, target, pos=False, rot=False, scl=True)
                    if self.ui.PivotCKB.isChecked():
                        MayaUtils.match_transform(source_obj, target, pos=False, rot=False, scl=False, piv=True)
                    
                    self.logger.debug(f"Match Transform: {source_obj} -> {target}")
                else:
                    self.logger.warning(f"Index {item_index} out of range for item list")
        except Exception as e:
            self.logger.error(f"Error in match transform: {e}")
        finally:
            cmds.undoInfo(closeChunk=True)
        
        self.logger.log_operation_end("Match Transform", True)
    
    def m_const(self):
        """매트릭스 컨스트레인트"""
        self.logger.log_operation_start("Matrix Constraint")
        items, targets = self.connection_mode()
        
        if not items or not targets:
            self.logger.error("Invalid selection for matrix constraint")
            return
        
        pivot_calc = self.ui.PivotCKB.isChecked()
        
        cmds.undoInfo(openChunk=True)
        try:
            for i, target in enumerate(targets):
                item_index = self.safe_index_access(items, i)
                if item_index >= len(items):
                    self.logger.warning(f"Index {item_index} out of range for item list")
                    continue
                
                source_obj = items[item_index]
                mm, dm = MayaUtils.create_matrix_constraint(source_obj, target, pivot_calc)
                
                if not mm or not dm:
                    self.logger.error(f"Failed to create matrix constraint nodes for {target}")
                    continue
                
                # 연결 설정
                if self.ui.AllCKB.isChecked() or self.ui.TransCKB.isChecked():
                    cmds.connectAttr(f"{dm}.outputTranslate", f"{target}.translate")
                if self.ui.AllCKB.isChecked() or self.ui.RotCKB.isChecked():
                    if cmds.nodeType(target) == 'joint':
                        # Joint의 경우 quaternion 처리
                        eq = cmds.createNode('eulerToQuat', n=f'{target}EQ')
                        qi = cmds.createNode('quatInvert', n=f'{target}QI')
                        qp = cmds.createNode('quatProd', n=f'{target}QP')
                        qe = cmds.createNode('quatToEuler', n=f'{target}QE')
                        
                        cmds.connectAttr(f"{target}.jointOrient", f"{eq}.inputRotate")
                        cmds.connectAttr(f"{eq}.outputQuat", f"{qi}.inputQuat")
                        cmds.connectAttr(f"{dm}.outputQuat", f"{qp}.input1Quat")
                        cmds.connectAttr(f"{qi}.outputQuat", f"{qp}.input2Quat")
                        cmds.connectAttr(f"{qp}.outputQuat", f"{qe}.inputQuat")
                        cmds.connectAttr(f"{qe}.outputRotate", f"{target}.rotate")
                    else:
                        cmds.connectAttr(f"{dm}.outputRotate", f"{target}.rotate")
                if self.ui.AllCKB.isChecked() or self.ui.ScaleCKB.isChecked():
                    cmds.connectAttr(f"{dm}.outputScale", f"{target}.scale")
                if self.ui.AllCKB.isChecked() or self.ui.ShearCKB.isChecked():
                    cmds.connectAttr(f"{dm}.outputShear", f"{target}.shear")
                
                self.logger.debug(f"Matrix Constraint: {source_obj} -> {target}")
        except Exception as e:
            self.logger.error(f"Error in matrix constraint: {e}")
        finally:
            cmds.undoInfo(closeChunk=True)
        
        self.logger.log_operation_end("Matrix Constraint", True)
    
    def batch_attr_pick(self):
        """전체 attribute 브라우저 다이얼로그를 열어 attr 선택"""
        a_list = self.a_all_list_item()
        if a_list:
            obj = a_list[0]
        else:
            sel = cmds.ls(selection=True)
            if not sel:
                self.logger.error("A 리스트에 오브젝트를 추가하거나 씬에서 오브젝트를 선택하세요")
                return
            obj = sel[0]

        if not cmds.objExists(obj):
            self.logger.error(f"오브젝트를 찾을 수 없습니다: {obj}")
            return

        dialog = AttrPickerDialog(obj, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            attr = dialog.get_selected()
            if attr:
                self.ui.batchAttrLE.setText(attr)
                self.logger.info(f"Selected attribute: {attr}")

    def batch_attr_get(self):
        """A 리스트 첫 번째 오브젝트의 현재 attribute 값을 Value 필드에 채움"""
        attr = self.ui.batchAttrLE.text().strip()
        if not attr:
            self.logger.error("Attr 필드를 먼저 입력하세요")
            return
        a_list = self.a_all_list_item()
        if not a_list:
            self.logger.error("A 리스트가 비어 있습니다")
            return
        try:
            value = cmds.getAttr(f"{a_list[0]}.{attr}")
            self.ui.batchValueLE.setText(str(value))
            self.logger.info(f"Got: {a_list[0]}.{attr} = {value}")
        except Exception as e:
            self.logger.error(f"attribute 읽기 실패: {e}")

    def batch_attr_set(self):
        """A 리스트의 모든 오브젝트에 attribute 값을 일괄 설정"""
        attr = self.ui.batchAttrLE.text().strip()
        value_str = self.ui.batchValueLE.text().strip()
        if not attr or not value_str:
            self.logger.error("Attr과 Value를 모두 입력하세요")
            return
        a_list = self.a_all_list_item()
        if not a_list:
            self.logger.error("A 리스트가 비어 있습니다")
            return

        # 값 타입 자동 변환: int → float → bool → string 순으로 시도
        try:
            value = int(value_str)
        except ValueError:
            try:
                value = float(value_str)
            except ValueError:
                if value_str.lower() in ('true', 'false'):
                    value = value_str.lower() == 'true'
                else:
                    value = value_str

        self.logger.log_operation_start("Batch Attr Set")
        cmds.undoInfo(openChunk=True)
        success_count = 0
        try:
            for obj in a_list:
                try:
                    cmds.setAttr(f"{obj}.{attr}", value)
                    success_count += 1
                    self.logger.debug(f"Set: {obj}.{attr} = {value}")
                except Exception as e:
                    self.logger.warning(f"실패 - {obj}.{attr}: {e}")
        finally:
            cmds.undoInfo(closeChunk=True)
        self.logger.log_operation_end("Batch Attr Set", True)
        self.logger.info(f"완료: {success_count}/{len(a_list)} 오브젝트 처리됨")

    def _cleanup(self):
        """정리 작업"""
        self.logger.info("CNTManager3 cleanup completed")


def runWin():
    """윈도우 실행"""
    global myWin
    try:
        if 'myWin' in globals() and myWin:
            myWin.close()
    except Exception as e:
        print(f"Error closing previous window: {e}")
    
    try:
        myWin = CNTManager3(parent=CNTManager3.maya_main_window())
        myWin.show()
        print("CNTManager3 Refactored - Loaded successfully!")
        return myWin
    except Exception as e:
        print(f"Error creating CNTManager window: {e}")
        return None


# 자동 실행
if __name__ == "__main__":
    runWin()






