"""
선택한 커브 transform 하위의 curve shape들을 각각 독립적인 커브로 분리.
"""
import maya.cmds as cmds


def unparent_curve_shapes(transforms=None):
    """
    transform 하위에 여러 curveShape가 있을 경우, 각 shape를 독립적인 커브로 분리.

    Args:
        transforms: 처리할 transform 노드 리스트. None이면 현재 선택된 오브젝트 사용.

    Returns:
        새로 생성된 커브 transform 노드 리스트.
    """
    if transforms is None:
        transforms = cmds.ls(selection=True, type="transform") or []

    if not transforms:
        cmds.warning("처리할 transform이 없습니다. 커브를 선택하세요.")
        return []

    result_curves = []

    for transform in transforms:
        shapes = cmds.listRelatives(transform, shapes=True, type="nurbsCurve", fullPath=True) or []

        if len(shapes) <= 1:
            continue

        parent = cmds.listRelatives(transform, parent=True, fullPath=True)
        base_name = transform.split("|")[-1]

        for i, shape in enumerate(shapes):
            new_transform = cmds.createNode("transform", name="{}_{}".format(base_name, i + 1))

            if parent:
                new_transform = cmds.parent(new_transform, parent[0])[0]

            cmds.parent(shape, new_transform, shape=True, relative=True)
            cmds.matchTransform(new_transform, transform)

            result_curves.append(new_transform)

        remaining = cmds.listRelatives(transform, shapes=True, fullPath=True) or []
        if not remaining:
            cmds.delete(transform)

    if result_curves:
        cmds.select(result_curves)
        print("{} 개의 커브로 분리 완료.".format(len(result_curves)))
    else:
        print("분리할 shape가 없습니다. (각 transform에 shape가 2개 이상이어야 합니다)")

    return result_curves


if __name__ == "__main__":
    import importlib
    import sys

    module_path = r"E:/script/pythonWorkSpace/main/mApplication/maya/python3/tools"
    if module_path not in sys.path:
        sys.path.append(module_path)

    import unparent_curve_shapes as _m
    importlib.reload(_m)
    _m.unparent_curve_shapes()
