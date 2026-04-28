import maya.cmds as cmds


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
        
        bm_ = cmds.createNode('blendMatrix', n='{}_bm'.format(baselist[i]))
        mm_ = cmds.createNode('multMatrix', n='{}_mm'.format(baselist[i]))
        dm_ = cmds.createNode('decomposeMatrix', n='{}_dm'.format(baselist[i]))
        
        cmds.select(baselist[i])
        cmds.addAttr(ln="FKIK", at='double', min=0, max=1, dv=0, k=1)
        cmds.select(cl=1)
        cmds.connectAttr('{}.FKIK'.format(baselist[i]),'{}.envelope'.format(bm_))
        
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
        
        
sel = cmds.ls(sl=1,r=1,uid=1)
FKIKBlend(sel)
