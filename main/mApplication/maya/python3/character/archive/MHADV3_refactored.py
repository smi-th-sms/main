# -*- coding: utf-8 -*-
"""
Metahuman Advanced Rigging Tool - Refactored Version
메타휴먼 리깅 작업을 위한 리팩토링된 스크립트

__AUTHOR__ = 'minsung'
__UPDATE__ = 20250101

Major improvements:
1. Refactored to use core modules
2. Improved error handling and logging
3. Better code organization
4. Enhanced maintainability
"""

import sys
import os
import json
from PySide6.QtCore import * 
from PySide6.QtGui import * 
from PySide6.QtWidgets import *
from PySide6 import __version__
from shiboken6 import wrapInstance
from maya import cmds
import maya.OpenMayaUI as omui

# Core modules import
from ..core.base_ui import BaseMayaUI
from ..core.maya_utils import MayaUtils
from ..core.config_manager import ConfigManager
from ..core.logger import ToolLogger


class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(480, 500)
        Form.setLayoutDirection(Qt.LeftToRight)
        self.gridLayout_3 = QGridLayout(Form)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.toolBox = QToolBox(Form)
        self.toolBox.setObjectName(u"toolBox")
        self.toolBox.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.toolBox.setLayoutDirection(Qt.LeftToRight)
        self.toolBox.setAutoFillBackground(False)
        self.toolBox.setStyleSheet(u"")
        self.page = QWidget()
        self.page.setObjectName(u"page")
        self.page.setGeometry(QRect(0, 0, 302, 281))
        self.formLayout = QFormLayout(self.page)
        self.formLayout.setObjectName(u"formLayout")
        self.formLayout.setLabelAlignment(Qt.AlignCenter)
        self.formLayout.setFormAlignment(Qt.AlignHCenter|Qt.AlignTop)
        self.widget = QWidget(self.page)
        self.widget.setObjectName(u"widget")
        self.gridLayout = QGridLayout(self.widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_4 = QLabel(self.widget)
        self.label_4.setObjectName(u"label_4")
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.label_4, 0, 0, 1, 1)

        self.line = QFrame(self.widget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.gridLayout.addWidget(self.line, 1, 0, 1, 1)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.horizontalLayout.setContentsMargins(0, 0, 0, -1)
        self.label_3 = QLabel(self.widget)
        self.label_3.setObjectName(u"label_3")
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.label_3)

        self.JsonOpenPB = QPushButton(self.widget)
        self.JsonOpenPB.setObjectName(u"JsonOpenPB")
        self.JsonOpenPB.setMaximumSize(QSize(20, 30))
        self.JsonOpenPB.setStyleSheet(u"background-color: rgb(81, 81, 81);")
        self.JsonOpenPB.setFlat(False)

        self.horizontalLayout.addWidget(self.JsonOpenPB)

        self.verticalLayout.addLayout(self.horizontalLayout)

        self.SubAddCB = QCheckBox(self.widget)
        self.SubAddCB.setObjectName(u"SubAddCB")
        self.SubAddCB.setChecked(True)

        self.verticalLayout.addWidget(self.SubAddCB)

        self.SpineIKAxisCB = QCheckBox(self.widget)
        self.SpineIKAxisCB.setObjectName(u"SpineIKAxisCB")
        self.SpineIKAxisCB.setChecked(True)

        self.verticalLayout.addWidget(self.SpineIKAxisCB)

        self.OneRootCB = QCheckBox(self.widget)
        self.OneRootCB.setObjectName(u"OneRootCB")
        self.OneRootCB.setChecked(True)

        self.verticalLayout.addWidget(self.OneRootCB)

        self.GroupCB = QCheckBox(self.widget)
        self.GroupCB.setObjectName(u"GroupCB")
        self.GroupCB.setChecked(True)

        self.verticalLayout.addWidget(self.GroupCB)

        self.SetsCB = QCheckBox(self.widget)
        self.SetsCB.setObjectName(u"SetsCB")
        self.SetsCB.setChecked(True)

        self.verticalLayout.addWidget(self.SetsCB)

        self.OLColorCB = QCheckBox(self.widget)
        self.OLColorCB.setObjectName(u"OLColorCB")
        self.OLColorCB.setChecked(True)

        self.verticalLayout.addWidget(self.OLColorCB)

        self.AddAttrCB = QCheckBox(self.widget)
        self.AddAttrCB.setObjectName(u"AddAttrCB")
        self.AddAttrCB.setChecked(True)

        self.verticalLayout.addWidget(self.AddAttrCB)

        self.ArrangementPB = QPushButton(self.widget)
        self.ArrangementPB.setObjectName(u"ArrangementPB")
        self.ArrangementPB.setStyleSheet(u"background-color: rgb(81, 81, 81);")

        self.verticalLayout.addWidget(self.ArrangementPB)

        self.gridLayout.addLayout(self.verticalLayout, 2, 0, 1, 1)

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.widget)

        self.toolBox.addItem(self.page, u"Arrangement")
        self.page_2 = QWidget()
        self.page_2.setObjectName(u"page_2")
        self.page_2.setGeometry(QRect(0, 0, 312, 268))
        self.formLayout_2 = QFormLayout(self.page_2)
        self.formLayout_2.setObjectName(u"formLayout_2")
        self.widget_2 = QWidget(self.page_2)
        self.widget_2.setObjectName(u"widget_2")
        self.gridLayout_2 = QGridLayout(self.widget_2)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label = QLabel(self.widget_2)
        self.label.setObjectName(u"label")
        self.label.setEnabled(True)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setFrameShadow(QFrame.Plain)
        self.label.setLineWidth(1)
        self.label.setTextFormat(Qt.AutoText)
        self.label.setScaledContents(False)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(False)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.label_2 = QLabel(self.widget_2)
        self.label_2.setObjectName(u"label_2")
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        font = QFont()
        font.setFamily(u"\uad74\ub9bc")
        font.setPointSize(7)
        self.label_2.setFont(font)
        self.label_2.setLayoutDirection(Qt.LeftToRight)
        self.label_2.setAutoFillBackground(False)
        self.label_2.setInputMethodHints(Qt.ImhNone)
        self.label_2.setMidLineWidth(0)
        self.label_2.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label_2, 1, 0, 1, 1)

        self.DuplicateBindPB = QPushButton(self.widget_2)
        self.DuplicateBindPB.setObjectName(u"DuplicateBindPB")
        sizePolicy1 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.DuplicateBindPB.sizePolicy().hasHeightForWidth())
        self.DuplicateBindPB.setSizePolicy(sizePolicy1)
        self.DuplicateBindPB.setStyleSheet(u"background-color: rgb(81, 81, 81);")

        self.gridLayout_2.addWidget(self.DuplicateBindPB, 2, 0, 1, 1)

        self.formLayout_2.setWidget(0, QFormLayout.LabelRole, self.widget_2)

        self.toolBox.addItem(self.page_2, u"MeshDuplicateBind")

        self.gridLayout_3.addWidget(self.toolBox, 0, 0, 1, 1)

        self.retranslateUi(Form)

        self.toolBox.setCurrentIndex(0)

        QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"MHADV3 - Refactored", None))
        self.label_4.setText(QCoreApplication.translate("Form", u"Metahuman Advanced Rigging Arrangement..", None))
        self.label_3.setText(QCoreApplication.translate("Form", u"MH JSON", None))
        self.JsonOpenPB.setText(QCoreApplication.translate("Form", u"?", None))
        self.SubAddCB.setText(QCoreApplication.translate("Form", u"ADV IKArmSub Add", None))
        self.SpineIKAxisCB.setText(QCoreApplication.translate("Form", u"ADV IKSpine Twist Axis", None))
        self.OneRootCB.setText(QCoreApplication.translate("Form", u"One Root", None))
        self.GroupCB.setText(QCoreApplication.translate("Form", u"Group Construction", None))
        self.SetsCB.setText(QCoreApplication.translate("Form", u"Sets", None))
        self.OLColorCB.setText(QCoreApplication.translate("Form", u"Outliner Color", None))
        self.AddAttrCB.setText(QCoreApplication.translate("Form", u"Main Add Attr", None))
        self.ArrangementPB.setText(QCoreApplication.translate("Form", u"MH ADV Arrangement", None))
        self.toolBox.setItemText(self.toolBox.indexOf(self.page), 
                                 QCoreApplication.translate("Form", u"Arrangement", None))
        self.label.setText(QCoreApplication.translate("Form", u"**Please select the objects before execution**", None))
        self.label_2.setText(QCoreApplication.translate("Form", u"ex) \"head_lod0_grp\" hierarchy, \"m_med_nrw_body_lod0_mesh\"..", None))
        self.DuplicateBindPB.setText(QCoreApplication.translate("Form", u"MH Mesh Duplicate Bind", None))
        self.toolBox.setItemText(self.toolBox.indexOf(self.page_2), QCoreApplication.translate("Form", u"MeshDuplicateBind", None))


class MyError(Exception):
    pass


class MHADV3(BaseMayaUI):
    """리팩토링된 MHADV3 클래스"""
    
    def __init__(self, parent=None, *args, **kwargs):
        super(MHADV3, self).__init__(parent, *args, **kwargs)
        
        # 로거 초기화
        self.logger = ToolLogger("MHADV3")
        
        # 설정 관리자 초기화
        self.config_manager = ConfigManager()
        
        # UI 설정
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        
        # 설정 로드
        self._load_config()
        
        # 이벤트 연결
        self._connect_signals()
        
        self.logger.info("MHADV3 initialized")
    
    def _load_config(self):
        """설정 파일 로드"""
        try:
            config_data = self.config_manager.load_json("MHADVJS.json")
            self.name_config = config_data["NAME"]
            self.ctrl_pos = config_data["CTRLPOS"]
            self.color_config = config_data["COLOR"]
            self.ol_color = config_data["OLCOLOR"]
            
            # 네임스페이스 설정
            self.head_r = f'{self.name_config["ns"][0]}:{self.name_config["headR"]}'
            self.body_r = f'{self.name_config["ns"][1]}:{self.name_config["bodyR"]}'
            
            self.logger.info("Configuration loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            # 기본값 설정
            self.name_config = {}
            self.ctrl_pos = {}
            self.color_config = {}
            self.ol_color = {}
            self.head_r = ""
            self.body_r = ""
    
    def _connect_signals(self):
        """시그널 연결"""
        self.ui.ArrangementPB.clicked.connect(self.mh_adv_arrangement)
        self.ui.DuplicateBindPB.clicked.connect(self.duplicate_bind)
        self.ui.JsonOpenPB.clicked.connect(self.show_json_info)
    
    def show_json_info(self):
        """JSON 정보 표시"""
        self.logger.log_ui_action("Show JSON info")
        # JSON 파일 정보를 표시하는 다이얼로그 구현
        pass
    
    def mh_adv_arrangement(self):
        """MH ADV Arrangement 실행"""
        self.logger.log_operation_start("MH ADV Arrangement")
        
        cmds.undoInfo(openChunk=True)
        try:
            # 변수 초기화
            root_ = None
            top_group = None
            geo_grp_ = None
            geo_pub_grp_ = None
            geo_wip_grp_ = None
            rig_grp_ = None
            
            if self.ui.SubAddCB.isChecked():
                self._setup_sub_controls()
            
            if self.ui.SpineIKAxisCB.isChecked():
                self._setup_spine_ik_axis()
            
            if self.ui.OneRootCB.isChecked():
                root_ = self._create_one_root()
            
            if self.ui.GroupCB.isChecked():
                top_group, geo_grp_, geo_pub_grp_, geo_wip_grp_, rig_grp_ = self._setup_groups(root_)
            
            if self.ui.OLColorCB.isChecked():
                self._setup_outliner_colors(top_group, geo_pub_grp_, root_)
            
            if self.ui.AddAttrCB.isChecked():
                self._add_main_attributes(geo_grp_)
            
            if self.ui.SetsCB.isChecked():
                self._setup_sets(geo_pub_grp_, root_, top_group)
            
            self.logger.log_operation_end("MH ADV Arrangement", True)
            
        except Exception as e:
            self.logger.error(f"Error in MH ADV Arrangement: {e}")
        finally:
            cmds.undoInfo(closeChunk=True)
    
    def _setup_sub_controls(self):
        """서브 컨트롤러 설정"""
        self.logger.info("Setting up sub controls")
        objects = []
        for control_name in self.name_config.get('sub', []):
            obj = MayaUtils.has_object(control_name)
            if obj:
                objects.append(obj)
            else:
                self.logger.warning(f"Sub control object not found: {control_name}")
        
        for i, ik in enumerate(objects):
            if ik:
                children = MayaUtils.get_children(ik)[1:]  # 첫 번째 자식 제외
                sub_ctrl = self._create_control_shape(ik, self.ctrl_pos.get('sub', []))
                if sub_ctrl:
                    shape_node = MayaUtils.get_children(sub_ctrl, 'nurbsCurve')[0]
                    if shape_node:
                        color_index = list(self.color_config.values())[i] if i < len(self.color_config) else 0
                        MayaUtils.set_override_color(shape_node, int(color_index))
                    
                    cmds.parent(sub_ctrl, ik)
                    MayaUtils.transform_reset(sub_ctrl)
                    if children:
                        cmds.parent(children, sub_ctrl)
    
    def _setup_spine_ik_axis(self):
        """Spine IK Axis 설정"""
        self.logger.info("Setting up Spine IK Axis")
        ik_spine = MayaUtils.has_object(self.name_config.get('adbIKSpine', ''))
        if ik_spine:
            cmds.setAttr(f"{ik_spine}.dForwardAxis", 2)
        else:
            self.logger.warning("adbIKSpine object not found")
    
    def _create_one_root(self):
        """One Root 생성"""
        self.logger.info("Creating one root")
        mh_body_root = MayaUtils.has_object(self.body_r)
        if mh_body_root:
            children = MayaUtils.get_children(mh_body_root)
            if children:
                MayaUtils.clear_selection()
                root_ = cmds.joint(n='root')
                cmds.parent(children[0], root_)
                return root_
        else:
            self.logger.warning(f"Body root object not found: {self.body_r}")
        return None
    
    def _setup_groups(self, root_):
        """그룹 구조 설정"""
        self.logger.info("Setting up groups")
        
        # 사용하지 않는 노드 삭제
        self._cleanup_unused_nodes()
        
        # 그룹 생성
        top_group = cmds.createNode('transform', n='name_')
        geo_grp_ = cmds.createNode('transform', n='geo_grp')
        geo_pub_grp_ = cmds.createNode('transform', n='geoPub_grp')
        geo_wip_grp_ = cmds.createNode('transform', n='geoWip_grp')
        rig_grp_ = cmds.createNode('transform', n='rig_grp')
        
        # 그룹 계층 구조 설정
        cmds.parent(geo_grp_, top_group)
        cmds.parent(rig_grp_, top_group)
        if root_:
            cmds.parent(root_, top_group)
        cmds.parent(geo_pub_grp_, geo_grp_)
        
        # 리그 오브젝트들 페어런팅
        self._parent_rig_objects(rig_grp_)
        
        # 지오메트리 오브젝트들 페어런팅
        self._parent_geometry_objects(geo_pub_grp_)
        
        cmds.parent(geo_wip_grp_, geo_grp_)
        
        # 메인 오브젝트들 이름 변경
        self._rename_main_objects()
        
        return top_group, geo_grp_, geo_pub_grp_, geo_wip_grp_, rig_grp_
    
    def _cleanup_unused_nodes(self):
        """사용하지 않는 노드들 정리"""
        layer_manager = MayaUtils.has_object('layerManager')
        if layer_manager:
            connections = cmds.listConnections(layer_manager)
            if connections:
                del_list = []
                for node_name in self.name_config.get('deleteNode', []):
                    obj = MayaUtils.has_object(node_name)
                    if obj:
                        del_list.append(obj)
                if del_list:
                    cmds.delete(del_list + connections[1:])
        else:
            del_list = []
            for node_name in self.name_config.get('deleteNode', []):
                obj = MayaUtils.has_object(node_name)
                if obj:
                    del_list.append(obj)
            if del_list:
                cmds.delete(del_list)
    
    def _parent_rig_objects(self, rig_grp_):
        """리그 오브젝트들 페어런팅"""
        rig_objects = []
        
        # 각 리그 오브젝트 확인 및 추가
        rig_object_names = ['advRig', 'drvR', 'MHRig']
        for obj_name in rig_object_names:
            obj = MayaUtils.has_object(self.name_config.get(obj_name, ''))
            if obj:
                rig_objects.append(obj)
            else:
                self.logger.warning(f"{obj_name} not found")
        
        # bodyR, headR 추가
        if self.body_r:
            body_obj = MayaUtils.has_object(self.body_r)
            if body_obj:
                rig_objects.append(body_obj)
        
        if self.head_r:
            head_obj = MayaUtils.has_object(self.head_r)
            if head_obj:
                rig_objects.append(head_obj)
        
        if rig_objects:
            cmds.parent(rig_objects, rig_grp_)
        else:
            self.logger.warning("No rig objects found for parenting")
    
    def _parent_geometry_objects(self, geo_pub_grp_):
        """지오메트리 오브젝트들 페어런팅"""
        geo_objects = []
        
        head_gro = MayaUtils.has_object(self.name_config.get('headGro', ''))
        body_geo = MayaUtils.has_object(self.name_config.get('bodyGeo', ''))
        
        if head_gro:
            geo_objects.append(head_gro)
        if body_geo:
            geo_objects.append(body_geo)
        
        if geo_objects:
            cmds.parent(geo_objects, geo_pub_grp_)
        else:
            self.logger.warning("No geometry objects found for parenting")
    
    def _rename_main_objects(self):
        """메인 오브젝트들 이름 변경"""
        for old_name, new_name in self.name_config.get('mainExtra', {}).items():
            obj = MayaUtils.has_object(old_name)
            if obj:
                cmds.rename(obj, new_name)
            else:
                self.logger.warning(f"Object not found for renaming: {old_name}")
    
    def _setup_outliner_colors(self, top_group, geo_pub_grp_, root_):
        """아웃라이너 컬러 설정"""
        self.logger.info("Setting up outliner colors")
        
        if top_group:
            MayaUtils.set_outliner_color(top_group, self.ol_color.get('top', [0, 0, 0]))
        if geo_pub_grp_:
            MayaUtils.set_outliner_color(geo_pub_grp_, self.ol_color.get('geometry', [0, 0, 0]))
        if root_:
            MayaUtils.set_outliner_color(root_, self.ol_color.get('root', [0, 0, 0]))
    
    def _add_main_attributes(self, geo_grp_):
        """메인 속성 추가"""
        self.logger.info("Adding main attributes")
        
        main_obj = MayaUtils.has_object('Main')
        if main_obj:
            cmds.addAttr(main_obj, ln="inGame", at='bool', k=1)
            cmds.addAttr(main_obj, ln="model", at='enum', k=1, en='None:HI')
            cmds.addAttr(main_obj, ln="facial", at='bool', k=1)
            
            if geo_grp_:
                self._setup_display_type_connection(main_obj, geo_grp_)
        else:
            self.logger.warning("Main object not found")
    
    def _setup_display_type_connection(self, main_obj, geo_grp_):
        """디스플레이 타입 연결 설정"""
        cmds.setAttr(f"{main_obj}.inGame", channelBox=True)
        cmds.setAttr(f"{main_obj}.model", channelBox=True)
        cmds.setAttr(f"{main_obj}.overrideDisplayType", channelBox=True)
        cmds.connectAttr(f"{main_obj}.overrideDisplayType", f"{geo_grp_}.overrideDisplayType")
        
        cmds.setAttr(f"{geo_grp_}.overrideEnabled", 1)
        children = MayaUtils.get_children(geo_grp_)
        for child in children:
            cmds.setAttr(f"{child}.overrideEnabled", 0)
    
    def _setup_sets(self, geo_pub_grp_, root_, top_group):
        """셋 설정"""
        self.logger.info("Setting up sets")
        
        sets_obj = MayaUtils.has_object('Sets')
        if sets_obj:
            anim_mesh_set = cmds.sets(n='AnimMeshSet')
            export_set = cmds.sets(n='ExportSet')
            
            if geo_pub_grp_:
                cmds.sets(anim_mesh_set, edit=1, fe=geo_pub_grp_)
            if root_ and top_group:
                cmds.sets(export_set, edit=1, fe=[root_, top_group])
            cmds.sets(sets_obj, edit=1, fe=[anim_mesh_set, export_set])
        else:
            self.logger.warning("Sets object not found")
    
    def _create_control_shape(self, obj, cvs):
        """컨트롤 셰이프 생성"""
        circle_shape = cmds.circle(nr=(1,0,0), n=f'{obj}Sub')
        if circle_shape and cvs:
            for i, cp in enumerate(cvs):
                if i < len(circle_shape[0]):
                    cmds.setAttr(f"{circle_shape[0]}.controlPoints[{i}]", cp[0], cp[1], cp[2])
        return circle_shape[0] if circle_shape else None
    
    def duplicate_bind(self):
        """메쉬 복제 및 재바인드"""
        self.logger.log_operation_start("Mesh Duplicate Bind")
        
        selection = MayaUtils.get_selection()
        if not selection:
            self.logger.warning("No objects selected")
            return
        
        # 페이스 리그 딕셔너리 생성
        face_rig_dict = {}
        for face_name in self.name_config.get('faceR', []):
            name = f'{self.name_config["ns"][0]}:{face_name}'
            obj = MayaUtils.has_object(name)
            if obj:
                face_rig_dict[face_name] = obj
            else:
                self.logger.warning(f"Face rig object not found: {name}")
        
        if face_rig_dict:
            self._parent_change(face_rig_dict.values(), self.name_config['ns'])
            self._metahuman_head_rebind(self.name_config['ns'][1], selection)
        
        self.logger.log_operation_end("Mesh Duplicate Bind", True)
    
    def _parent_change(self, obj_list, ns_list):
        """부모 변경"""
        for obj in obj_list:
            try:
                parent = MayaUtils.get_children(obj)[0] if MayaUtils.get_children(obj) else None
                if parent:
                    replace_name = parent.replace(ns_list[0], ns_list[1])
                    if MayaUtils.has_object(replace_name):
                        cmds.parent(obj, replace_name)
            except Exception as e:
                self.logger.warning(f"Failed to parent object {obj}: {e}")
    
    def _metahuman_head_rebind(self, ns, objects):
        """메타휴먼 헤드 재바인드"""
        for obj in objects:
            name = obj
            target = cmds.duplicate(obj)[0]
            MayaUtils.object_clean(target)
            
            bind_joints = MayaUtils.get_bind_joints(obj)
            if bind_joints:
                body_joints, face_joints = self._re_joint_set(bind_joints, ns)
                re_joints = body_joints + face_joints
                
                if re_joints:
                    sc = MayaUtils.copy_skin_weights(obj, target, re_joints)
                    
                    # BlendShape 처리
                    if cmds.listHistory(obj, type='blendShape'):
                        bs = cmds.listHistory(obj, type='blendShape')[0]
                        origin = cmds.listHistory(target, type='mesh')[-1]
                        cmds.connectAttr(f"{origin}.outMesh", f"{bs}.originalGeometry[0]")
                        cmds.connectAttr(f"{origin}.worldMesh[0]", f"{bs}.input[0].inputGeometry")
                        cmds.connectAttr(f"{bs}.outputGeometry[0]", f"{sc}.input[0].inputGeometry")
                    
                    cmds.delete(obj)
                    cmds.rename(target, name)
                    cmds.rename(sc, f'{name}_SkinCluster')
                else:
                    self.logger.warning(f"No joints found for skinning object: {name}")
                    cmds.delete(target)
            else:
                self.logger.warning(f"No bind joints found for object: {name}")
                cmds.delete(target)
    
    def _re_joint_set(self, joints, find_name):
        """조인트 세트 재구성"""
        body_joints = []
        face_joints = []
        
        for j in joints:
            basename = j.split(':')[-1]
            if basename == 'root':
                continue
            else:
                try:
                    body_joint = f'{find_name}:{basename}'
                    if MayaUtils.has_object(body_joint):
                        body_joints.append(body_joint)
                    else:
                        face_joints.append(j)
                except:
                    face_joints.append(j)
        
        self.logger.debug(f"Body joints: {body_joints}, Face joints: {face_joints}")
        return body_joints, face_joints
    
    def _cleanup(self):
        """정리 작업"""
        self.logger.info("MHADV3 cleanup completed")


def runWin():
    """윈도우 실행"""
    global myWin
    try:
        if 'myWin' in globals() and myWin:
            myWin.close()
    except:
        pass
    
    try:
        myWin = MHADV3(parent=MHADV3.maya_main_window())
        myWin.show()
        print("MHADV3 Refactored - Loaded successfully!")
        return myWin
    except Exception as e:
        print(f"Error creating MHADV3 window: {e}")
        return None


if __name__ == "__main__":
    runWin()






