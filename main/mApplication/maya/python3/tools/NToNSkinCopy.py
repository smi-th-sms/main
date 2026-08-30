import maya.cmds as cmds

def halfList(object_):
    half = int(len(object_) / 2)
    items = object_[:half]
    targets = object_[half:]
    return items, targets


def _get_shape(node):
    shapes = cmds.listRelatives(node, s=True, ni=True, pa=True) or []
    return shapes[0] if shapes else node


def _find_skin_cluster(node):
    history = cmds.listHistory(node, pdo=True) or []
    for n in history:
        if cmds.nodeType(n) == 'skinCluster':
            return n
    return None

sel = cmds.ls(sl=True) or []
src_items, dst_targets = halfList(sel)

for idx, src_item in enumerate(src_items):
    src_shape = _get_shape(src_item)
    src_skin = _find_skin_cluster(src_shape)
    if not src_skin:
        continue
    conns = cmds.listConnections(src_skin + '.matrix', s=True, d=False) or []
    joints_ = [n for n in conns if cmds.nodeType(n) == 'joint']
    if not joints_:
        continue
    dest_skin = cmds.skinCluster(joints_, dst_targets[idx], tsb=True, bm=1, mi=3, rui=False, dr=3)[0]
    cmds.copySkinWeights(ss=src_skin, ds=dest_skin,
                         nm=True,
                         sa='closestPoint',
                         ia=['closestJoint', 'oneToOne'])
