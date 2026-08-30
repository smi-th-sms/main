import maya.cmds as cmds


def _get_shape(node):
    shapes = cmds.listRelatives(node, s=True, ni=True, pa=True) or []
    return shapes[0] if shapes else node


def _find_skin_cluster(node):
    history = cmds.listHistory(node, pdo=True) or []
    for n in history:
        if cmds.nodeType(n) == 'skinCluster':
            return n
    return None


def bindJoint(object_):
    shape = _get_shape(object_)
    scls = _find_skin_cluster(shape)
    if not scls:
        return []
    # Query influence joints via skinCluster.matrix connections and filter joints
    conns = cmds.listConnections(scls + '.matrix', s=True, d=False) or []
    return [n for n in conns if cmds.nodeType(n) == 'joint']


def skinCopy(item_, target_):
    bindJoints = bindJoint(item_)
    if not bindJoints:
        return
    # Bind destination to the same influences
    dest_skin = cmds.skinCluster(bindJoints, target_, tsb=True, bm=1, mi=3, rui=False, dr=3)[0]
    # Copy weights from source skin to destination skin
    src_skin = _find_skin_cluster(_get_shape(item_))
    if src_skin:
        cmds.copySkinWeights(ss=src_skin, ds=dest_skin,
                             nm=True,
                             sa='closestPoint',
                             ia='oneToOne')


sel = cmds.ls(sl=True, fl=True) or []

if len(sel) >= 2:
    src_item = sel[0]
    for dst_target in sel[1:]:
        skinCopy(src_item, dst_target)