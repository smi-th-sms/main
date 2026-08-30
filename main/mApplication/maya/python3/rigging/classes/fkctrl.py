import maya.cmds as cmds


shape_dict = {}
shape_dict['square'] = {'p':[[-1,0,-1],[-1,0,1],[1,0,1],[1,0,-1],[-1,0,-1]], 'k':[0,1,2,3,4]}
shape_dict['cube'] = {'p':[[0.5,0.5,-0.5],[0.5,-0.5,-0.5],[-0.5,-0.5,-0.5],[-0.5,0.5,-0.5],
[-0.5,0.5,0.5],[-0.5,-0.5,0.5],[0.5,-0.5,0.5],[0.5,0.5,0.5],[-0.5,0.5,0.5],
[-0.5,-0.5,0.5],[-0.5,-0.5,-0.5],[-0.5,0.5,-0.5],[0.5,0.5,-0.5],[0.5,-0.5,-0.5],
[0.5,-0.5,0.5],[0.5,0.5,0.5],[0.5,0.5,-0.5]], 'k':[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]}

def controlShape(sel, shape_):
    ctrls=[]
    for i,item in enumerate(sel):
        item_ = cmds.ls(item)[0]
        if not shape_=='circle':
            ctrl_ = cmds.curve(d=1, p=shape_dict[shape_]['p'],k=shape_dict[shape_]['k'])
        else:
            ctrl_ = cmds.circle(c=(0,0,0), nr=(0,1,0), sw=360, r=1, d=3, ch=0, n='{0}_ctrl'.format(item_))
        offset_ = cmds.createNode('transform', n='{0}_offset'.format(item_))
        cmds.parent(ctrl_,offset_)
        cmds.matchTransform(offset_,item_)
        ctrls.append(ctrl_)
        if i>0:
            cmds.parent(offset_, ctrls[i-1])


def offset(sel):
    for i,item in enumerate(sel):
        item_ = cmds.ls(item)[0]
        parent_ = cmds.listRelatives(item_, p=1)
        offset_ = cmds.createNode('transform',n='{0}_offset'.format(item_))
        cmds.matchTransform(offset_,item_)
        cmds.parent(item_,offset_)
        cmds.parent(offset_,parent_)

sel = cmds.ls(sl=1,r=1,uid=1)
# controlShape(sel, 'cube')
# offset(sel)
