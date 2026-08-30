import maya.cmds as cmds

sel = cmds.ls(sl=True)
jnt_ = cmds.listRelatives(sel, ad=True, type='joint') or []
cmds.select(jnt_)


import maya.cmds as cmds

def bindJoint(object_):
    shapes_ = cmds.listRelatives(object_, shapes=True, fullPath=True) or []
    scls_ = None
    if shapes_:
        shape_ = shapes_[0]
        connectionList_ = cmds.listHistory(shape_, groupLevels=True, pruneDagObjects=True) or []
        for cnt_ in connectionList_:
            if cmds.nodeType(cnt_) == 'skinCluster':
                scls_ = cnt_
                break
    if scls_ is None:
        return []
    return cmds.listConnections(scls_ + '.matrix', d=False, s=True, type='joint') or []

sel = cmds.ls(sl=True, r=True, fl=True)
cmds.select(bindJoint(sel[0]))
