from pymel.core import *

def halfList(object_):
    half = int(len(object_)/2)
    items = object_[:half]
    targets = object_[half:]
    return items,targets

def Grp_(object_, w=None):
    grps_ = []
    for i in object_:
        name_ = i.name()
        getTransform_ = i.getMatrix(worldSpace=True)
        node_ = createNode('transform', n='{0}_grp'.format(i))
        node_.setMatrix(getTransform_)
        if w == 0:
            getParent_ = i.getParent()
            parent(node_, getParent_)
        # parent(i, node_)
        grps_.append(node_)
    return grps_

def pivotMatch(sel):
    items,targets = halfList(sel)
    for i,item in enumerate(items):
        parent(targets[i],item)
        makeIdentity(targets[i], apply=True, t=1, r=1, s=1)
        targets[i].rotatePivot.set(0,0,0)
        targets[i].scalePivot.set(0,0,0)
        parent(targets[i],w=1)

def sets_(sel):
    for i in sel:
        name_ = i.split('C130J_')[-1].split('_geo')[0]
        sets(i, n=f'{name_}_static_SK')

def jointOrientSet(sel):
    items,targets = halfList(sel)
    for i,item in enumerate(items):
        jo = item.jointOrient.get()
        targets[i].jointOrient.set(jo)

sel = ls(sl=1,r=1,fl=1)        
# grps_ = Grp_(sel, w=1)
# pivotMatch(sel)
# sets_(sel)
jointOrientSet(sel)