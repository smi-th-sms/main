# -*- coding: utf-8 -*-
"""============================================================================
Module descriptions.
CNTManager3 - Fixed Version

__AUTHOR__ = 'SUNGSEO'
__UPDATE__ = 20220114

Major fixes:
1. Fixed N to N constraint indexing issue
2. Improved error handling
3. Added safe index access method
4. Fixed import issues

:Example:
Package is CNTManager3_fixed.py

from CNTManager3_fixed import *
CNTManager3_fixed.runWin()

============================================================================"""
#
# when start coding 3 empty lines.
#
import sys
import maya.OpenMayaUI as omui
from maya import cmds
import maya.api.OpenMaya as om

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

class Ui_CNTManager(object):
    def setupUi(self, CNTManager):
        CNTManager.setObjectName("CNTManager")
        CNTManager.resize(430, 650)
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
        CNTManager.setWindowTitle(QtWidgets.QApplication.translate("CNTManager", "CNTManager - Fixed", None, -1))
        self.AAddPB.setText(QtWidgets.QApplication.translate("CNTManager", "Add", None, -1))
        self.ARemovePB.setText(QtWidgets.QApplication.translate("CNTManager", "Remove", None, -1))
        self.SortPB.setText(QtWidgets.QApplication.translate("CNTManager", "Sort", None, -1))
        self.ChangePB.setText(QtWidgets.QApplication.translate("CNTManager", "Change", None, -1))
        self.OneToNRB.setText(QtWidgets.QApplication.translate("CNTManager", "One To N", None, -1))
        self.NToNRB.setText(QtWidgets.QApplication.translate("CNTManager", "N To N", None, -1))
        self.BAddPB.setText(QtWidgets.QApplication.translate("CNTManager", "Add", None, -1))
        self.BRemovePB.setText(QtWidgets.QApplication.translate("CNTManager", "Remove", None, -1))
        self.OutLE.setText(QtWidgets.QApplication.translate("CNTManager", "OutPut..", None, -1))
        self.ConnectionPB.setText(QtWidgets.QApplication.translate("CNTManager", ">>", None, -1))
        self.InLE.setText(QtWidgets.QApplication.translate("CNTManager", "InPut..", None, -1))
        self.GetSetPB.setText(QtWidgets.QApplication.translate("CNTManager", "Get Set", None, -1))
        self.PPPB.setText(QtWidgets.QApplication.translate("CNTManager", "PParent", None, -1))
        self.SetDrivenPB.setText(QtWidgets.QApplication.translate("CNTManager", "SetDriven", None, -1))
        self.AllCKB.setText(QtWidgets.QApplication.translate("CNTManager", "All", None, -1))
        self.TransCKB.setText(QtWidgets.QApplication.translate("CNTManager", "Trans", None, -1))
        self.RotCKB.setText(QtWidgets.QApplication.translate("CNTManager", "Rot", None, -1))
        self.ScaleCKB.setText(QtWidgets.QApplication.translate("CNTManager", "Scale", None, -1))
        self.ShearCKB.setText(QtWidgets.QApplication.translate("CNTManager", "Shear", None, -1))
        self.PivotCKB.setText(QtWidgets.QApplication.translate("CNTManager", "Pivot", None, -1))
        self.MatchPB.setText(QtWidgets.QApplication.translate("CNTManager", "Match", None, -1))
        self.MConPB.setText(QtWidgets.QApplication.translate("CNTManager", "MCon", None, -1))
        self.ConstPB.setText(QtWidgets.QApplication.translate("CNTManager", "Const", None, -1))
        self.AUTHORLB.setText(QtWidgets.QApplication.translate("CNTManager", "AUTHOR : MinSung", None, -1))
        self.UPDATALB.setText(QtWidgets.QApplication.translate("CNTManager", "UPDATE : 20220114 - Fixed", None, -1))

class myUIClass(QWidget):
    def __init__(self, *args, **kwargs):
        super(myUIClass, self).__init__(*args, **kwargs)
        self.setWindowFlags(Qt.Window)
        self.ui = Ui_CNTManager()
        self.ui.setupUi(self)
        
        self.Alist_ = self.ui.AlistWidget
        self.Blist_ = self.ui.BlistWidget
        self.ui.AAddPB.clicked.connect(self.addAListWidget)
        self.ui.BAddPB.clicked.connect(self.addBListWidget)
        self.ui.ARemovePB.clicked.connect(self.AremoveCurrentItem)
        self.ui.BRemovePB.clicked.connect(self.BremoveCurrentItem)
        self.ui.SortPB.clicked.connect(self.SortItems)
        self.ui.ChangePB.clicked.connect(self.ChangeItems)
        self.ui.PPPB.clicked.connect(self.pparentItems)
        self.ui.OneToNRB.clicked.connect(self.ConnectionMode)
        self.ui.NToNRB.clicked.connect(self.ConnectionMode)
        self.ui.ConnectionPB.clicked.connect(self.ListConnect)
        self.ui.GetSetPB.clicked.connect(self.ListSet)
        self.ui.ConstPB.clicked.connect(self.Constraints)
        self.ui.MatchPB.clicked.connect(self.MatchTransform)
        self.ui.SetDrivenPB.clicked.connect(self.SetDrivens)
        self.ui.MConPB.clicked.connect(self.MConst)
    
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
        
    # Pressing the AddItem button adds the selected items to the A list.
    def addAListWidget(self):
        self.Alist_.clear()
        self.list_ = cmds.ls(sl=1, fl=1, r=1) or []  # 반환값 처리 개선
        for i in self.list_:
            strName_ = str(i)
            self.Alist_.addItem(strName_)
        cmds.select(cl=1)
 
           
    def addBListWidget(self):
        self.Blist_.clear()
        self.list_ = cmds.ls(sl=1, fl=1, r=1) or []  # 반환값 처리 개선
        for i in self.list_:
            strName_ = str(i)
            self.Blist_.addItem(strName_)
        cmds.select(cl=1)

    
    # list query        
    def AprintMultiItems(self):
        self.selectList_ = []
        self.selectedList = self.Alist_.selectedItems()
        for i in self.selectedList:
            self.selectList_.append(i.text())
        return self.selectedList, self.selectList_


    def BprintMultiItems(self):
        self.selectList_ = []
        self.selectedList = self.Blist_.selectedItems()
        for i in self.selectedList:
            self.selectList_.append(i.text())
        return self.selectedList, self.selectList_            

    
    # Delete selections from the list       
    def AremoveCurrentItem(self):
        self.selectList_ = self.AprintMultiItems()[0]
        for i in self.selectList_:
            self.removeItemRow = self.Alist_.currentRow()
            self.Alist_.takeItem(self.removeItemRow)

            
    def BremoveCurrentItem(self):
        self.selectList_ = self.BprintMultiItems()[0]
        for i in self.selectList_:
            self.removeItemRow = self.Blist_.currentRow()
            self.Blist_.takeItem(self.removeItemRow)

    
    # All items in list A and B
    def AAllListItem(self):
        AAllList_ = [self.Alist_.item(i).text() for i in range(self.Alist_.count())]
        return AAllList_

        
    def BAllListItem(self):
        BAllList_ = [self.Blist_.item(i).text() for i in range(self.Blist_.count())]
        return BAllList_

        
    # Sort the contents of list A and list B        
    def SortItems(self):
        AAllList_ = self.AAllListItem()
        AAllList_.sort()
        BAllList_ = self.BAllListItem()
        BAllList_.sort()
        cmds.select(AAllList_)
        self.addAListWidget()
        cmds.select(BAllList_)
        self.addBListWidget()
        
    # Swap the contents of list A and list B
    def ChangeItems(self):
        AAllList_ = self.AAllListItem()
        BAllList_ = self.BAllListItem()
        cmds.select(BAllList_)
        self.addAListWidget()
        cmds.select(AAllList_)
        self.addBListWidget()

        
    # Connection mode of selected list A and list B    
    def ConnectionMode(self):
        self.ASelectList = self.AprintMultiItems()[1]
        self.BSelectList = self.BprintMultiItems()[1]
        return self.ASelectList, self.BSelectList

    
    # get attribbutes name    
    def PrintTextEdit(self) :
        outAttr = self.ui.OutLE.text()
        inAttr = self.ui.InLE.text()
        return outAttr, inAttr

                    
    def ListConnect(self):
        outAttr, inAttr = self.PrintTextEdit()
        item_, target_ = self.ConnectionMode()
        
        if not item_ or not target_:
            print("Error: Invalid selection for list connect")
            return
            
        cmds.undoInfo(openChunk=True)
        try:
            for i, tgt in enumerate(target_):
                item_index = self.safe_index_access(item_, i)
                if item_index < len(item_):
                    source_attr = f"{item_[item_index]}.{outAttr}"
                    target_attr = f"{tgt}.{inAttr}"
                    cmds.connectAttr(source_attr, target_attr, force=True)
                    print(f"Connected: {source_attr} -> {target_attr} (index: {item_index})")
                else:
                    print(f"Warning: Index {item_index} out of range for item list")
        except Exception as e:
            print(f"Error in ListConnect: {e}")
        finally:
            cmds.undoInfo(closeChunk=True)


    def ListSet(self):
        outAttr, inAttr = self.PrintTextEdit()
        item_, target_ = self.ConnectionMode()
        
        if not item_ or not target_:
            print("Error: Invalid selection for list set")
            return
            
        cmds.undoInfo(openChunk=True)
        try:
            for i, tgt in enumerate(target_):
                item_index = self.safe_index_access(item_, i)
                if item_index < len(item_):
                    source_attr = f"{item_[item_index]}.{outAttr}"
                    target_attr = f"{tgt}.{inAttr}"
                    getAttr_value = cmds.getAttr(source_attr)
                    cmds.setAttr(target_attr, getAttr_value)
                    print(f"Set: {target_attr} = {getAttr_value} from {item_[item_index]} (index: {item_index})")
                else:
                    print(f"Warning: Index {item_index} out of range for item list")
        except Exception as e:
            print(f"Error in ListSet: {e}")
        finally:
            cmds.undoInfo(closeChunk=True)
    

     # Pparent list A to list B
    def pparentItems(self):
        item_, target_ = self.ConnectionMode()
        
        if not item_ or not target_:
            print("Error: Invalid selection for parent")
            return
            
        cmds.undoInfo(openChunk=True)
        try:
            for i, tgt in enumerate(target_):
                item_index = self.safe_index_access(item_, i)
                if item_index < len(item_):
                    cmds.parent(item_[item_index], tgt)
                    print(f"Parented: {item_[item_index]} -> {tgt} (index: {item_index})")
                else:
                    print(f"Warning: Index {item_index} out of range for item list")
        except Exception as e:
            print(f"Error in pparentItems: {e}")
        finally:
            cmds.undoInfo(closeChunk=True)

    
    def SetDrivens(self):
        outAttr, inAttr = self.PrintTextEdit()
        item_, target_ = self.ConnectionMode()
        
        if not item_ or not target_:
            print("Error: Invalid selection for set driven")
            return
            
        cmds.undoInfo(openChunk=True)
        try:
            for i, tgt in enumerate(target_):
                item_index = self.safe_index_access(item_, i)
                if item_index < len(item_):
                    target_attr = f"{tgt}.{inAttr}"
                    driver_attr = f"{item_[item_index]}.{outAttr}"
                    cmds.setDrivenKeyframe(target_attr, cd=driver_attr)
                    print(f"Set Driven: {driver_attr} -> {target_attr} (index: {item_index})")
                else:
                    print(f"Warning: Index {item_index} out of range for item list")
        except Exception as e:
            print(f"Error in SetDrivens: {e}")
        finally:
            cmds.undoInfo(closeChunk=True)


    # Constraint Type
    def Constraint_(self, *args, **kwargs):
        if self.ui.AllCKB.isChecked():
            cmds.parentConstraint(*args, maintainOffset=kwargs['mo'])
        if self.ui.TransCKB.isChecked():
            cmds.pointConstraint(*args, maintainOffset=kwargs['mo'])
        if self.ui.RotCKB.isChecked():
            cmds.orientConstraint(*args, maintainOffset=kwargs['mo'])
        if self.ui.ScaleCKB.isChecked():
            cmds.scaleConstraint(*args, maintainOffset=kwargs['mo'])


    # Constraint for each object by pressing the Constraint button
    def Constraints(self):
        item_, target_ = self.ConnectionMode()
        
        if not item_ or not target_:
            print("Error: Invalid selection for constraints")
            return
            
        if self.ui.PivotCKB.isChecked():
            mo_=1
        else:
            mo_=0
        cmds.undoInfo(openChunk=True)
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
            cmds.undoInfo(closeChunk=True)
    

    def MatchTransform(self):
        item_, target_ = self.ConnectionMode()
        
        if not item_ or not target_:
            print("Error: Invalid selection for match transform")
            return
            
        cmds.undoInfo(openChunk=True)
        try:
            for i, tgt in enumerate(target_):
                # 수정된 인덱스 처리 로직
                item_index = self.safe_index_access(item_, i)
                if item_index < len(item_):
                    source_obj = item_[item_index]
                    
                    if self.ui.AllCKB.isChecked():
                        cmds.matchTransform(source_obj, tgt)
                    if self.ui.TransCKB.isChecked():
                        cmds.matchTransform(source_obj, tgt, pos=True)
                    if self.ui.RotCKB.isChecked():
                        cmds.matchTransform(source_obj, tgt, rot=True)
                    if self.ui.ScaleCKB.isChecked():
                        cmds.matchTransform(source_obj, tgt, scl=True)
                    if self.ui.PivotCKB.isChecked():
                        cmds.matchTransform(source_obj, tgt, piv=True)
                        
                    print(f"Match Transform: {source_obj} -> {tgt} (index: {item_index})")
                else:
                    print(f"Warning: Index {item_index} out of range for item list")
        except Exception as e:
            print(f"Error in MatchTransform: {e}")
        finally:
            cmds.undoInfo(closeChunk=True)

    
    def MConst(self):
        item_, target_ = self.ConnectionMode()
        
        if not item_ or not target_:
            print("Error: Invalid selection for matrix constraint")
            return
            
        if self.ui.PivotCKB.isChecked():
            piv_=1
        else:
            piv_=0
        cmds.undoInfo(openChunk=True)
        try:
            for i, tgt in enumerate(target_):
                # 수정된 인덱스 처리 로직
                item_index = self.safe_index_access(item_, i)
                if item_index >= len(item_):
                    print(f"Warning: Index {item_index} out of range for item list")
                    continue
                    
                source_obj = item_[item_index]
                mm = cmds.createNode('multMatrix', n='%sMM' % tgt)
                dm = cmds.createNode('decomposeMatrix', n='%sDM' % tgt)
                
                if not mm or not dm:
                    print(f"Error: Failed to create nodes for {tgt}")
                    continue
                    
                if piv_ == 1:
                    # Get scale pivot and create matrix
                    scale_pivot = cmds.xform(tgt, q=True, sp=True, ws=True)
                    tgScalePivotMtx = om.MMatrix()
                    tgScalePivotMtx.setToIdentity()
                    tgScalePivotMtx[3][0] = scale_pivot[0]
                    tgScalePivotMtx[3][1] = scale_pivot[1]
                    tgScalePivotMtx[3][2] = scale_pivot[2]
                    
                    # Set matrix inputs
                    cmds.setAttr(f"{mm}.matrixIn[0]", tgScalePivotMtx, type="matrix")
                    cmds.setAttr(f"{mm}.matrixIn[1]", cmds.xform(tgt, q=True, m=True, ws=True), type="matrix")
                    cmds.setAttr(f"{mm}.matrixIn[2]", cmds.xform(source_obj, q=True, m=True, ws=True), type="matrix")
                    cmds.connectAttr(f"{source_obj}.worldMatrix[0]", f"{mm}.matrixIn[3]")
                    cmds.connectAttr(f"{tgt}.parentInverseMatrix[0]", f"{mm}.matrixIn[4]")
                    
                    # Get translate minus rotate pivot
                    tmr_pivot = cmds.xform(tgt, q=True, rp=True, ws=True)
                    tgTMRPM = om.MMatrix()
                    tgTMRPM.setToIdentity()
                    tgTMRPM[3][0] = tmr_pivot[0]
                    tgTMRPM[3][1] = tmr_pivot[1]
                    tgTMRPM[3][2] = tmr_pivot[2]
                    cmds.setAttr(f"{mm}.matrixIn[5]", tgTMRPM, type="matrix")
                else:
                    cmds.setAttr(f"{mm}.matrixIn[0]", cmds.xform(tgt, q=True, m=True, ws=True), type="matrix")
                    cmds.setAttr(f"{mm}.matrixIn[1]", cmds.xform(source_obj, q=True, m=True, ws=True), type="matrix")
                    cmds.connectAttr(f"{source_obj}.worldMatrix[0]", f"{mm}.matrixIn[2]")
                    cmds.connectAttr(f"{tgt}.parentInverseMatrix[0]", f"{mm}.matrixIn[3]")
                    
                print(f"Matrix Constraint: {source_obj} -> {tgt} (index: {item_index})")
                cmds.connectAttr(f"{mm}.matrixSum", f"{dm}.inputMatrix")
                
                if self.ui.AllCKB.isChecked() or self.ui.TransCKB.isChecked():
                    cmds.connectAttr(f"{dm}.outputTranslate", f"{tgt}.translate")
                if self.ui.AllCKB.isChecked() or self.ui.RotCKB.isChecked():
                    if cmds.nodeType(tgt) == 'joint':
                        eq = cmds.createNode('eulerToQuat', n='%sEQ' % tgt)
                        qi = cmds.createNode('quatInvert', n='%sQI' % tgt)
                        qp = cmds.createNode('quatProd', n='%sQP' % tgt)
                        qe = cmds.createNode('quatToEuler', n='%sQE' % tgt)
                        
                        cmds.connectAttr(f"{tgt}.jointOrient", f"{eq}.inputRotate")
                        cmds.connectAttr(f"{eq}.outputQuat", f"{qi}.inputQuat")
                        cmds.connectAttr(f"{dm}.outputQuat", f"{qp}.input1Quat")
                        cmds.connectAttr(f"{qi}.outputQuat", f"{qp}.input2Quat")
                        cmds.connectAttr(f"{qp}.outputQuat", f"{qe}.inputQuat")
                        cmds.connectAttr(f"{qe}.outputRotate", f"{tgt}.rotate")
                    else:
                        cmds.connectAttr(f"{dm}.outputRotate", f"{tgt}.rotate")
                if self.ui.AllCKB.isChecked() or self.ui.ScaleCKB.isChecked():
                    cmds.connectAttr(f"{dm}.outputScale", f"{tgt}.scale")
                if self.ui.AllCKB.isChecked() or self.ui.ShearCKB.isChecked():
                    cmds.connectAttr(f"{dm}.outputShear", f"{tgt}.shear")
        except Exception as e:
            print(f"Error in MConst: {e}")
        finally:
            cmds.undoInfo(closeChunk=True)

    def debug_selection_info(self):
        """디버깅을 위한 선택 정보 출력"""
        try:
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


def maya_main_window():
    try:
        main_window_ptr = omui.MQtUtil.mainWindow()
        if main_window_ptr:
            return wrapInstance(int(main_window_ptr), QWidget)
        else:
            print("Warning: Could not get Maya main window")
            return None
    except Exception as e:
        print(f"Error getting Maya main window: {e}")
        return None
    

def runWin():
    global myWin
    try:
        if 'myWin' in globals() and myWin:
            myWin.close()
    except Exception as e:
        print(f"Error closing previous window: {e}")
        
    try:
        parent_window = maya_main_window()
        myWin = myUIClass(parent=parent_window)
        myWin.show()
        print("CNTManager3 Fixed - Loaded successfully!")
        print("N to N constraint indexing issue has been resolved.")
        return myWin
    except Exception as e:
        print(f"Error creating CNTManager window: {e}")
        return None

# 자동 실행
if __name__ == "__main__":
    runWin()