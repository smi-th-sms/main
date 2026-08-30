# -*- coding: utf-8 -*-
"""============================================================================
Module descriptions.
bend setup

__AUTHOR__ = 'SUNGSEO'
__UPDATE__ = 20240225

:Example:
from tool
try:
    from imp import *
except:
    pass
reload(tool)
============================================================================"""
import pymel.core as pm

def division(number,divNum):
    list_ = [0]
    div_ = float(divNum)/float(number)
    for i in range(number):
        i=i+1
        list_.append(i*div_)
    return list_

def offset_(object_, w=None):
    name_ = object_.name()
    getTransform_ = object_.getMatrix(worldSpace=True)
    node_ = pm.createNode('transform', n='%s_offset' % object_)
    node_.setMatrix(getTransform_)
    if w == 0:
        getParent_ = object_.getParent()
        pm.parent(node_, getParent_)
    pm.parent(object_, node_)
    return node_


num_ = 4
axis_ = 'x'
div_ = division(num_,1)
sel = pm.ls(sl=1,fl=1,r=1)
name_ = 'test'


# 선택한 오브젝트의 포지션값을 리스트로 저장
pos_ = [pm.xform(i, q=1, ws=1, rp=1) for i in sel]

# pos_ 기준으로 linear 커브 생성
linearCrv = pm.curve(n='%s_linearCrv' % name_, d=1, p=pos_)
pm.rebuildCurve(linearCrv,rt=0,d=3,kr=0,s=num_-2)

# linearCrv 기준으로 bendCrv생성 num_인수값으로 bend 갯수 설정.
bendPosCrv = pm.duplicate(linearCrv)[0]
bendPosCrv.rename('%s_bendPosCrv' % name_)
pm.rebuildCurve(bendPosCrv,rt=0,d=3,kr=2,s=num_-2)
bendDefCrv = pm.duplicate(linearCrv)[0]
bendDefCrv.rename('%s_bendDefCrv' % name_)
pm.rebuildCurve(bendDefCrv,rt=0,d=3,kr=2,s=num_-2)
pm.blendShape(bendPosCrv,bendDefCrv)

# bendCrv에 softModifier생성
bendOri = bendPosCrv.listRelatives()[-1]

ctrlList = []
centerOffsets = []
# center컨트롤러 생성 및 offset
for i,side in enumerate(['st','md','end']):
    ctrl = pm.circle(n='{0}_bend_{1}_ctrl'.format(name_,side))[0]
    ctrlList.append(ctrl)
    pm.addAttr(ctrl, ln='UVal', at='double', dv=float(i*0.5), k=1)
    cenmp_ = pm.createNode('motionPath',n='%s_mp' % (ctrl.name()))
    linearCrv.getShape().ws >> cenmp_.geometryPath
    ctrl.UVal >> cenmp_.uValue
    pm.select(bendDefCrv, r=1)
    sm_ = pm.softMod(n='%sSoftMod' % bendDefCrv.name())
    pm.select(cl=1)
    pm.matchTransform(ctrl, sm_[1], pos=1)
    pm.matchTransform(ctrl, sel[i*2], rot=1)
    pm.matchTransform(sm_[-1], sel[i*2], rot=1)

    centerOffset = offset_(ctrl, w=None)
    centerOffsets.append(centerOffset)
    pm.parent(sm_[-1],centerOffset)
    ctrl.t >> sm_[-1].t
    ctrl.r >> sm_[-1].r
    cenmp_.allCoordinates >> centerOffset.t
    cenmp_.rotate >> centerOffset.rotate

    # softModifier setup
    sm_[-1].getShape().origin.set(0,0,0)
    sm_[-1].pim >> sm_[0].bindPreMatrix
    sm_[-1].setPivots([0,0,0])
    sm_[0].falloffRadius.set(2.5)

    # softModifier 연결
    cendm_ = pm.createNode('decomposeMatrix',n='%s_dm'% ctrl.name())
    centerOffset.wm >> cendm_.inputMatrix
    cendm_.ot >> sm_[0].falloffCenter


# 선택한 오브젝트의 포지션 값을 linearCrv가 따라가게 셋팅
locs_ = []
for i,item in enumerate(sel):
    dm_ = pm.createNode('decomposeMatrix',n='%s_dm'% (name_))
    item.wm >> dm_.inputMatrix
    dm_.ot >> linearCrv.getShape().controlPoints[i]
    
for i in list(range(num_+1)):
    mp_ = pm.createNode('motionPath',n='%s_%s_mp' % (linearCrv.name(),i))
    linearCrv.getShape().ws >> mp_.geometryPath
    mp_.uValue.set(div_[i])
    mp_.allCoordinates >> bendOri.controlPoints[i]

addnum = 0
spcs_ = []
for i in list(range(num_+1)):
    mp_ = pm.createNode('motionPath',n='%s_%s_mp' % (bendDefCrv.name(),i))
    spc_ = pm.createNode('transform',n='%s_%s_space' % (bendDefCrv.name(),i))
    bendDefCrv.getShape().ws >> mp_.geometryPath
    sel[0].worldMatrix >> mp_.worldUpMatrix
    mp_.uValue.set(div_[i])
    inputnum = 0
    if (int(i)%2==1):
        bta_ = pm.createNode('blendTwoAttr',n='%s_%s_bta' % (bendDefCrv.name(),i))
        ctrlList[addnum].ry >> bta_.input[inputnum]
        addnum+=1
        inputnum+=1
        ctrlList[addnum].ry >> bta_.input[inputnum]
        bta_.attributesBlender.set(float(0.5))
        bta_.output >> mp_.frontTwist
    else:
        ctrlList[int(i/2)].ry >> mp_.frontTwist
        
    mp_.allCoordinates >> spc_.t
    mp_.r >> spc_.r
    mp_.fractionMode.set(1)
    mp_.worldUpType.set(2)
    mp_.frontAxis.set(0)
    mp_.upAxis.set(1)
    spcs_.append(spc_)

spaceGrp = pm.createNode('transform', n='%s_bendSpace_grp' % name_)
sysGrp = pm.createNode('transform', n='%s_bendSys_grp' % name_)

pm.parent(spcs_, spaceGrp)
pm.parent([linearCrv,bendDefCrv,bendPosCrv,spaceGrp,centerOffsets,sel], sysGrp)
