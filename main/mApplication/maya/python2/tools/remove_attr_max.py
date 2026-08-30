# -*- coding: utf-8 -*-
"""선택한 오브젝트의 특정 attribute에서 maxValue 제한을 제거한다."""

import maya.cmds as cmds


def remove_attr_max(attr_name, nodes=None):
    """attr_name의 max 제한을 해제한다.

    Args:
        attr_name (str): max를 해제할 attribute의 longName 또는 shortName.
        nodes (list, optional): 대상 노드 리스트. None이면 현재 선택된 오브젝트 사용.

    Returns:
        list: max가 실제로 해제된 'node.attr' 리스트.
    """
    if nodes is None:
        nodes = cmds.ls(selection=True)

    if not nodes:
        cmds.warning(u"오브젝트를 선택하세요.")
        return []

    result = []
    for node in nodes:
        plug = "{0}.{1}".format(node, attr_name)

        if not cmds.attributeQuery(attr_name, node=node, exists=True):
            cmds.warning(u"{0} 에 {1} attribute가 없습니다.".format(node, attr_name))
            continue

        if not cmds.attributeQuery(attr_name, node=node, maxExists=True):
            cmds.warning(u"{0} 은 maxValue가 설정되어 있지 않습니다.".format(plug))
            continue

        try:
            cmds.addAttr(plug, edit=True, hasMaxValue=False)
            result.append(plug)
        except RuntimeError:
            cmds.warning(u"{0} 의 max 제거에 실패했습니다.".format(plug))

    return result


if __name__ == "__main__":
    # 사용 예: 선택한 오브젝트들의 translateX max 제거
    remove_attr_max("translateX")
