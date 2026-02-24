# -*- coding: utf-8 -*-

################################################################################
## 메타휴먼 리깅 작업시 필요한 스크립트
## Form generated from reading UI file 'MHADVvzdMHm.ui'
##
## __AUTHOR__ = 'minsung'
## __UPDATE__ = 20240206
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################
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
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
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
    # retranslateUi

class MyError(Exception):
    pass

class myUIClass(QWidget):
    def __init__(self, *args, **kwargs):
        super(myUIClass, self).__init__(*args, **kwargs)
        self.setWindowFlags(Qt.Window)
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        filePath_ = self.path_("Json/MHADVJS.json")
        with open(filePath_)as json_file:
            json_data = json.load(json_file)
        self.name_ = json_data["NAME"]
        self.ctrlPos_ = json_data["CTRLPOS"]
        self.color_ = json_data["COLOR"]
        self.olcolor_ = json_data["OLCOLOR"]
        self.headR_ = '{0}:{1}'.format(self.name_['ns'][0],self.name_['headR'])
        self.bodyR_ = '{0}:{1}'.format(self.name_['ns'][1],self.name_['bodyR'])

        self.ui.ArrangementPB.clicked.connect(self.MHADVArrangementPB_)
        self.ui.DuplicateBindPB.clicked.connect(self.duplicatebind_)
        

    def MHADVArrangementPB_(self):
        cmds.undoInfo(openChunk=True)
        try:
            # 변수 초기화
            root_ = None
            topGroup = None
            geo_grp_ = None
            geoPub_grp_ = None
            geoWip_grp_ = None
            rig_grp_ = None
            
            if self.ui.SubAddCB.isChecked():
                # sub controler setup
                self.subControl_()
            
            if self.ui.SpineIKAxisCB.isChecked():
                # Spine IK Advanced Twist Forward Axis Edit
                IKSpine = self.hasObject_(self.name_['adbIKSpine'])
                if IKSpine is not None:
                    cmds.setAttr(f"{IKSpine}.dForwardAxis", 2)
                else:
                    print("Warning: adbIKSpine object not found")
            
            if self.ui.OneRootCB.isChecked():
                MHbodyRoot = self.hasObject_(self.bodyR_)
                if MHbodyRoot is not None:
                    MHbodyRootChild_ = cmds.listRelatives(MHbodyRoot, c=True)[0]
                    cmds.select(cl=1)
                    root_ = cmds.joint(n='root')
                    cmds.parent(MHbodyRootChild_, root_)
                else:
                    print("Warning: bodyR_ object not found: {}".format(self.bodyR_))
            
            if self.ui.GroupCB.isChecked():
                # unused node delete
                layerManager_ = self.hasObject_('layerManager')
                if layerManager_ is not None:
                    layerManager_connections = cmds.listConnections(layerManager_)
                    delList = [self.hasObject_(i) for i in self.name_['deleteNode']]
                    delList = [item for item in delList if item is not None]  # None 값 제거
                    cmds.delete(delList + layerManager_connections[1:])
                else:
                    print("Warning: layerManager not found")
                    delList = [self.hasObject_(i) for i in self.name_['deleteNode']]
                    delList = [item for item in delList if item is not None]  # None 값 제거
                    cmds.delete(delList)

                # group construction
                topGroup = cmds.createNode('transform', n='name_')
                geo_grp_ = cmds.createNode('transform', n='geo_grp')
                geoPub_grp_ = cmds.createNode('transform', n='geoPub_grp')
                geoWip_grp_ = cmds.createNode('transform', n='geoWip_grp')
                rig_grp_ = cmds.createNode('transform', n='rig_grp')

                # parents
                cmds.parent(geo_grp_, topGroup)
                cmds.parent(rig_grp_, topGroup)
                if root_ is not None:
                    cmds.parent(root_, topGroup)
                cmds.parent(geoPub_grp_, geo_grp_)
                # headRig을 MHRig에 페어런팅
                headRig_obj = self.hasObject_(self.name_['headRig'])
                MHRig_obj = self.hasObject_(self.name_['MHRig'])
                if headRig_obj is not None and MHRig_obj is not None:
                    cmds.parent(headRig_obj, MHRig_obj)
                else:
                    print("Warning: headRig or MHRig not found")
                
                # geometry를 geoPub_grp_에 페어런팅
                headGro_obj = self.hasObject_(self.name_['headGro'])
                bodyGeo_obj = self.hasObject_(self.name_['bodyGeo'])
                geo_objects = []
                if headGro_obj is not None:
                    geo_objects.append(headGro_obj)
                if bodyGeo_obj is not None:
                    geo_objects.append(bodyGeo_obj)
                if geo_objects:
                    cmds.parent(geo_objects, geoPub_grp_)
                else:
                    print("Warning: No geometry objects found for parenting")
                
                cmds.parent(geoWip_grp_, geo_grp_)
                
                # rig objects를 rig_grp_에 페어런팅
                rig_objects = []
                
                advRig_obj = self.hasObject_(self.name_['advRig'])
                if advRig_obj is not None:
                    rig_objects.append(advRig_obj)
                else:
                    print("Warning: advRig not found")
                
                drvR_obj = self.hasObject_(self.name_['drvR'])
                if drvR_obj is not None:
                    rig_objects.append(drvR_obj)
                else:
                    print("Warning: drvR not found")
                
                bodyR_obj = self.hasObject_(self.bodyR_)
                if bodyR_obj is not None:
                    rig_objects.append(bodyR_obj)
                else:
                    print("Warning: bodyR not found")
                
                headR_obj = self.hasObject_(self.headR_)
                if headR_obj is not None:
                    rig_objects.append(headR_obj)
                else:
                    print("Warning: headR not found")
                
                MHRig_obj = self.hasObject_(self.name_['MHRig'])
                if MHRig_obj is not None:
                    rig_objects.append(MHRig_obj)
                else:
                    print("Warning: MHRig not found")
                
                if rig_objects:
                    cmds.parent(rig_objects, rig_grp_)
                else:
                    print("Warning: No rig objects found for parenting")

                # Mains Rename
                for i in self.name_['mainExtra']:
                    obj = self.hasObject_(i)
                    if obj is not None:
                        cmds.rename(obj, self.name_['mainExtra'][i])
                    else:
                        print("Warning: Object not found for renaming: {}".format(i))

            if self.ui.OLColorCB.isChecked():
                # change outliner
                if topGroup is not None:
                    self.outlinerColorSet_(topGroup, self.olcolor_['top'])
                if geoPub_grp_ is not None:
                    self.outlinerColorSet_(geoPub_grp_, self.olcolor_['geometry'])
                if root_ is not None:
                    self.outlinerColorSet_(root_, self.olcolor_['root'])

            if self.ui.AddAttrCB.isChecked():
                # Add Attrs
                main_ = self.hasObject_('Main')
                if main_ is not None:
                    cmds.addAttr(main_, ln="inGame", at='bool', k=1)
                    cmds.addAttr(main_, ln="model", at='enum', k=1, en='None:HI')
                    cmds.addAttr(main_, ln="facial", at='bool', k=1)
                    if geo_grp_ is not None:
                        self.displayType(main_, geo_grp_)
                else:
                    print("Warning: Main object not found")

                # sets
                sets_ = self.hasObject_('Sets')
                if sets_ is not None:
                    AnimMeshSet_ = cmds.sets(n='AnimMeshSet')
                    ExportSet_ = cmds.sets(n='ExportSet')
                    if geoPub_grp_ is not None:
                        cmds.sets(AnimMeshSet_, edit=1, fe=geoPub_grp_)
                    if root_ is not None and topGroup is not None:
                        cmds.sets(ExportSet_, edit=1, fe=[root_,topGroup])
                    cmds.sets(sets_, edit=1, fe=[AnimMeshSet_,ExportSet_])
                else:
                    print("Warning: Sets object not found")

        finally:
            cmds.undoInfo(closeChunk=True)

    def duplicatebind_(self):
        # 선택한 메쉬 복제 및 재 바인드
        sel = cmds.ls(sl=1,r=1,fl=1)
        dict_ = {}
        for i in self.name_['faceR']:
            name_ = '{0}:{1}'.format(self.name_['ns'][0],i)
            obj = self.hasObject_(name_)
            if obj is not None:
                dict_[i] = obj
            else:
                print("Warning: Face rig object not found: {}".format(name_))
        
        if dict_:  # dict_가 비어있지 않을 때만 실행
            self.parentChange(dict_.values(),self.name_['ns'])
            self.metahumanHeadRebind(self.name_['ns'][1], sel)
        # cmds.parent(dict_['faceR'][0], self.bodyR_)

    # circle 생성 및 cvs list포지션에 맞게 수정하여 컨트롤러 생성
    def createControl_(self, object_, cvs):
        circleShape_ = cmds.circle(nr=(1,0,0), n='{0}Sub'.format(object_))
        for i,cp in enumerate(cvs):
            cmds.setAttr(f"{circleShape_[0]}.controlPoints[{i}]", cp[0], cp[1], cp[2])
        return circleShape_[0]

    def overrideColorChange_(self, shape_, num):
        cmds.setAttr(f"{shape_}.overrideEnabled", 1)
        cmds.setAttr(f"{shape_}.overrideColor", num)

    def transformReset(self, object_):
        cmds.setAttr(f"{object_}.translate", 0, 0, 0)
        cmds.setAttr(f"{object_}.rotate", 0, 0, 0)
        cmds.setAttr(f"{object_}.scale", 1, 1, 1)

    # 서브 컨트롤러 생성 및 컬러 지정
    def subControl_(self):
        object_ = []
        for i in self.name_['sub']:
            obj = self.hasObject_(i)
            if obj is not None:
                object_.append(obj)
            else:
                print("Warning: Sub control object not found: {}".format(i))

        for i,ik in enumerate(object_):
            if ik is not None:
                getChildren = cmds.listRelatives(ik, c=True)[1:]
                subctrl = self.createControl_(ik,self.ctrlPos_['sub'])
                shape_node = cmds.listRelatives(subctrl, s=True)[0]
                self.overrideColorChange_(shape_node, 
                                          int(list(self.color_.values())[i]))
                cmds.parent(subctrl,ik)
                self.transformReset(subctrl)
                cmds.parent(getChildren, subctrl)

    # 오브젝트의 아웃라이너 컬러를 color list value 적용
    def outlinerColorSet_(self, object_, color):
        cmds.setAttr(f"{object_}.useOutlinerColor", 1)
        cmds.setAttr(f"{object_}.outlinerColor", color[0], color[1], color[2])

    # 오브젝트의 바인드 된 조인트들을 리턴
    def bindJoint(self, object_):
        shape_ = cmds.listRelatives(object_, s=True)[0]
        connectionList_ = cmds.listHistory(shape_, gl=1, pdo=1)
        scls_ = None
        for cnt_ in connectionList_:
            if cmds.nodeType(cnt_) == 'skinCluster':
                scls_ = cnt_
                break
        
        if scls_ is not None:
            return cmds.listConnections(f"{scls_}.matrix", d=0, s=1, type='joint')
        else:
            print("Warning: No skinCluster found for object: {}".format(object_))
            return []

    # joints의 베이스 네임을 기준으로 findNameSpace가 붙은 joint들을 리턴
    def reJointSet(self, joints, findName):
        bodyjoints_ = []
        facejoints_ = []
        for j in joints:
            basename_ = j.split(':')[-1]
            if basename_ == 'root':
                pass
            else:
                try:
                    bodyjoint_ = '{0}:{1}'.format(findName,basename_)
                    if cmds.objExists(bodyjoint_):
                        bodyjoints_.append(bodyjoint_)
                    else:
                        facejoints_.append(j)
                except:
                    facejoints_.append(j)
        print(bodyjoints_, facejoints_)
        return bodyjoints_, facejoints_

    # 바인드 하고 item_스킨 웨이트를 target_으로 카피
    def skinCopy(self, item_, target_, joints):
        sc_ = cmds.skinCluster(joints, target_, bm=1, mi=3, rui=0, dr=3)
        cmds.copySkinWeights(item_, target_, nm=1, sa='closestPoint', ia='oneToOne', nr=1)
        return sc_

    # 복사한 오브젝트의 attribute unlock 및 ShapeOrigin 정리 
    def objectClean(self, object_):
        attrs = cmds.listAttr(object_, k=1)
        for attr in attrs:
            try:
                cmds.setAttr(f"{object_}.{attr}", lock=False)
            except:
                pass
        try:
            cmds.delete('{}ShapeOrig'.format(object_))
        except:
            pass

    # 오브젝트가 있는지 확인하고 이름을 리턴
    def hasObject_(self, name_):
        if cmds.objExists(name_):
            return name_
        else:
            return None

    # list_의 상위 노드 네임스페이스를 교체 후, list_를 교체한 상위 노드에 페어런츠
    def parentChange(self, list_,ns_):
        for i in list_:
            try:
                p_ = cmds.listRelatives(i, p=True)[0]
                replaceName = p_.replace(ns_[0], ns_[1])
                if cmds.objExists(replaceName):
                    cmds.parent(i, replaceName)
            except Exception as e:
                print("Warning: Failed to parent object {}: {}".format(i, str(e)))

    # 다시 바인드 할 메타휴먼 헤드 메쉬 잡고 실행
    def metahumanHeadRebind(self, ns_, object_):
        for i in object_:
            name_ = i
            target = cmds.duplicate(i)[0]
            self.objectClean(target)
            bindjoints = self.bindJoint(i)
            
            if bindjoints:  # bindjoints가 비어있지 않을 때만 실행
                bodyjoints_, facejoints_ = self.reJointSet(bindjoints, ns_)
                rejoints = bodyjoints_ + facejoints_
                if rejoints:  # rejoints가 비어있지 않을 때만 스킨클러스터 생성
                    sc_ = self.skinCopy(i, target, rejoints)
                    if cmds.listHistory(i, type='blendShape'):
                        bs_ = cmds.listHistory(i, type='blendShape')[0]
                        origin_ = cmds.listHistory(target, type='mesh')[-1]
                        cmds.connectAttr(f"{origin_}.outMesh", f"{bs_}.originalGeometry[0]")
                        cmds.connectAttr(f"{origin_}.worldMesh[0]", f"{bs_}.input[0].inputGeometry")
                        cmds.connectAttr(f"{bs_}.outputGeometry[0]", f"{sc_}.input[0].inputGeometry")
                    cmds.delete(i)
                    cmds.rename(target, name_)
                    cmds.rename(sc_, '{}_SkinCluster'.format(name_))
                else:
                    print("Warning: No joints found for skinning object: {}".format(name_))
                    cmds.delete(target)
            else:
                print("Warning: No bind joints found for object: {}".format(name_))
                cmds.delete(target)

    def displayType(self, item_, target_):
        cmds.setAttr(f"{item_}.inGame", channelBox=True)
        cmds.setAttr(f"{item_}.model", channelBox=True)
        cmds.setAttr(f"{item_}.overrideDisplayType", channelBox=True)
        cmds.connectAttr(f"{item_}.overrideDisplayType", f"{target_}.overrideDisplayType")

        cmds.setAttr(f"{target_}.overrideEnabled", 1)
        list_ = cmds.listRelatives(target_, ad=1)
        for i in list_:
            cmds.setAttr(f"{i}.overrideEnabled", 0)

    def path_(self, dir_=None):
        fileDir = os.path.dirname(__file__)
        currentDir = os.path.abspath(fileDir)
        if dir_:
            joinDir = os.path.join(currentDir, dir_)
            currentDir = os.path.abspath(joinDir)
        if not currentDir in sys.path:
            sys.path.append(currentDir)
    
        return currentDir

def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QWidget)
    
def runWin():
    global myWin
    try:
        myWin.close()
    except:
        pass
    myWin = myUIClass(parent=maya_main_window())
    myWin.show()

runWin()
