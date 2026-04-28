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
        
        cmds.connectAttr('{}.ot'.format(dm_),'{}.t'.format(targetlist_[i]))
        cmds.connectAttr('{}.os'.format(dm_),'{}.s'.format(targetlist_[i]))
        
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
            cmds.connectAttr('{}.outputRotate'.format(qte_),'{}.r'.format(targetlist_[i]))
        else:
            cmds.connectAttr('{}.or'.format(dm_),'{}.r'.format(targetlist_[i]))
        
        if cmds.ls(targetlist_[i],type='joint'):
            cmds.setAttr('{}.jointOrientX'.format(targetlist_[i]),0)
            cmds.setAttr('{}.jointOrientY'.format(targetlist_[i]),0)
            cmds.setAttr('{}.jointOrientZ'.format(targetlist_[i]),0)
        
        
sel = cmds.ls(sl=1,r=1,uid=1)
NtoNMatrixConst(sel, mo=1)















