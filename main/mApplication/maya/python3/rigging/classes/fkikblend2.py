import maya.cmds as cmds
import maya.api.OpenMaya as om2

def NtoNMatrixConst(list_, mo=None):
    lists_ = cmds.ls(list_)
    num_ = int(len(list_)/2)
    itemlist_ = []
    targetlist_ = []
    for i,item in enumerate(lists_[:num_]):
        itemlist_.append(item)
        targetlist_.append(lists_[i+num_])
        
        mm_ = cmds.createNode('multMatrix', n='{}_mm'.format(itemlist_[i]))
        dm_ = cmds.createNode('decomposeMatrix', n='{}_dm'.format(itemlist_[i]))
        
        if mo==1:
            mat0 = om2.MMatrix()
            mat1 = om2.MMatrix(cmds.getAttr('{}.worldMatrix'.format(targetlist_[i])))
            mat2 = om2.MMatrix(cmds.getAttr('{}.worldInverseMatrix'.format(item)))
            
            cmds.setAttr('{}.matrixIn[0]'.format(mm_), list(mat0), type='matrix')
            cmds.setAttr('{}.matrixIn[1]'.format(mm_), list(mat1), type='matrix')
            cmds.setAttr('{}.matrixIn[2]'.format(mm_), list(mat2), type='matrix')
        
        cmds.connectAttr('{}.wm'.format(itemlist_[i]),'{}.matrixIn[3]'.format(mm_))
        cmds.connectAttr('{}.pim'.format(targetlist_[i]),'{}.matrixIn[4]'.format(mm_))
        cmds.connectAttr('{}.matrixSum'.format(mm_),'{}.inputMatrix'.format(dm_))
        
        # cmds.connectAttr('{}.ot'.format(dm_),'{}.t'.format(targetlist_[i]))
        # cmds.connectAttr('{}.os'.format(dm_),'{}.s'.format(targetlist_[i]))
        
        if cmds.nodeType(targetlist_[i])=='joint':
            etq_ = cmds.createNode('eulerToQuat', n='{}_etq'.format(itemlist_[i]))
            qi_ = cmds.createNode('quatInvert', n='{}_qi'.format(itemlist_[i]))
            qp_ = cmds.createNode('quatProd', n='{}_qp'.format(itemlist_[i]))
            qte_ = cmds.createNode('quatToEuler', n='{}_qte'.format(itemlist_[i]))
            
            cmds.connectAttr('{}.jointOrient'.format(targetlist_[i]),'{}.inputRotate'.format(etq_))
            cmds.connectAttr('{}.outputQuat'.format(etq_),'{}.inputQuat'.format(qi_))
            cmds.connectAttr('{}.outputQuat'.format(qi_),'{}.input2Quat'.format(qp_))
            cmds.connectAttr('{}.oq'.format(dm_),'{}.input1Quat'.format(qp_))
            cmds.connectAttr('{}.outputQuat'.format(qp_),'{}.inputQuat'.format(qte_))
            # cmds.connectAttr('{}.outputRotate'.format(qte_),'{}.r'.format(targetlist_[i]))
        else:
            cmds.connectAttr('{}.or'.format(dm_),'{}.r'.format(targetlist_[i]))
    
    return ['{}.ot'.format(dm_),'{}.outputRotate'.format(qte_), '{}.os'.format(dm_)]


def FKIKBlend(list_):
    joints = cmds.ls(list_)
    joinNum = int(len(list_)/3)
    fklist_ = []
    iklist_ = []
    baselist = []
    for i,item in enumerate(joints[:joinNum]):
        fklist_.append(item)
        iklist_.append(joints[i+joinNum])
        baselist.append(joints[i+joinNum*2])
        
        '''
        bm_ = cmds.createNode('blendMatrix', n='{}_bm'.format(baselist[i]))
        mm_ = cmds.createNode('multMatrix', n='{}_mm'.format(baselist[i]))
        dm_ = cmds.createNode('decomposeMatrix', n='{}_dm'.format(baselist[i]))
        '''
        
        pb_ = cmds.createNode('pairBlend', n='{}_pb'.format(baselist[i]))
        bc_ = cmds.createNode('blendColors', n='{}_bc'.format(baselist[i]))
        cmds.setAttr('{0}.rotInterpolation'.format(pb_),1)
        
        if not '{}_FKIK'.format(baselist[i]):
            cmds.select(baselist[i])
            cmds.addAttr(ln="FKIK", at='double', min=0, max=1, dv=0, k=1)
            cmds.select(cl=1)
        cmds.connectAttr('{}.FKIK'.format(baselist[i]),'{}.weight'.format(pb_))
        cmds.connectAttr('{}.FKIK'.format(baselist[i]),'{}.blender'.format(bc_))
        
        fkot_, fkor_, fkos_ = NtoNMatrixConst([fklist_[i], baselist[i]], mo=None)
        ikot_, ikor_, ikos_ = NtoNMatrixConst([iklist_[i], baselist[i]], mo=None)
        
        cmds.connectAttr(fkot_,'{}.inTranslate1'.format(pb_))
        cmds.connectAttr(ikot_,'{}.inTranslate2'.format(pb_))
        cmds.connectAttr(fkor_,'{}.inRotate1'.format(pb_))
        cmds.connectAttr(ikor_,'{}.inRotate2'.format(pb_))
        cmds.connectAttr(fkos_,'{}.color1'.format(bc_))
        cmds.connectAttr(ikos_,'{}.color2'.format(bc_))
        
        cmds.connectAttr('{}.ot'.format(pb_),'{}.t'.format(baselist[i]))
        cmds.connectAttr('{}.or'.format(pb_),'{}.r'.format(baselist[i]))
        cmds.connectAttr('{}.output'.format(bc_),'{}.s'.format(baselist[i]))
        
        '''
        cmds.connectAttr('{}.wm'.format(fklist_[i]),'{}.inputMatrix'.format(bm_))
        cmds.connectAttr('{}.wm'.format(iklist_[i]),'{}.target[0].targetMatrix'.format(bm_))
        cmds.connectAttr('{}.outputMatrix'.format(bm_),'{}.matrixIn[0]'.format(mm_))
        cmds.connectAttr('{}.pim'.format(baselist[i]),'{}.matrixIn[1]'.format(mm_))
        cmds.connectAttr('{}.matrixSum'.format(mm_),'{}.inputMatrix'.format(dm_))
        
        cmds.connectAttr('{}.ot'.format(dm_),'{}.t'.format(baselist[i]))
        cmds.connectAttr('{}.or'.format(dm_),'{}.r'.format(baselist[i]))
        cmds.connectAttr('{}.os'.format(dm_),'{}.s'.format(baselist[i]))
        
        cmds.setAttr('{}.jointOrientX'.format(baselist[i]),0)
        cmds.setAttr('{}.jointOrientY'.format(baselist[i]),0)
        cmds.setAttr('{}.jointOrientZ'.format(baselist[i]),0)
        '''
        
        
sel = cmds.ls(sl=1,r=1,uid=1)
FKIKBlend(sel)
