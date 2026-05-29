# -*- coding: utf-8 -*-
"""Utilities for adding selected joint rotate values into jointOrient.

Usage in Maya when this folder is in sys.path:

import rotate_to_joint_orient
rotate_to_joint_orient.run()

Or import the library module directly:

from libs.joints import rotate_to_joint_orient
rotate_to_joint_orient.run()

# Common bake-style usage:
rotate_to_joint_orient.run(zero_rotate=True)
"""
from __future__ import print_function

import maya.cmds as cmds


ROTATE_ATTRS = ("rotateX", "rotateY", "rotateZ")
JOINT_ORIENT_ATTRS = ("jointOrientX", "jointOrientY", "jointOrientZ")


def _is_unlocked(node, attr):
    plug = "{0}.{1}".format(node, attr)
    return cmds.objExists(plug) and not cmds.getAttr(plug, lock=True)


def _has_unlocked_attrs(node, attrs):
    locked = [
        "{0}.{1}".format(node, attr)
        for attr in attrs
        if not _is_unlocked(node, attr)
    ]

    if locked:
        cmds.warning("Skipped {0}; locked or missing attrs: {1}".format(
            node,
            ", ".join(locked)
        ))
        return False

    return True


def _vector_attr(node, attr):
    values = cmds.getAttr("{0}.{1}".format(node, attr))
    return list(values[0])


def selected_joints():
    """Return selected joints in Maya's current selection order."""
    selection = cmds.ls(selection=True, long=True) or []
    return [
        node for node in selection
        if cmds.objExists(node) and cmds.objectType(node, isType="joint")
    ]


def add_rotate_to_joint_orient(joints=None, zero_rotate=False):
    """Add rotate XYZ values to jointOrient XYZ for each given joint.

    Args:
        joints (list[str] | None): Joint names. Uses selected joints if None.
        zero_rotate (bool): When True, resets rotate to 0 after setting
            jointOrient. The default keeps rotate untouched.

    Returns:
        list[dict]: Per-joint processing results.
    """
    joints = selected_joints() if joints is None else joints

    if not joints:
        cmds.warning("No joints selected.")
        return []

    results = []

    for joint in joints:
        if not cmds.objExists(joint) or not cmds.objectType(joint, isType="joint"):
            cmds.warning("Skipped non-joint node: {0}".format(joint))
            continue

        if not _has_unlocked_attrs(joint, JOINT_ORIENT_ATTRS):
            continue

        if zero_rotate and not _has_unlocked_attrs(joint, ROTATE_ATTRS):
            continue

        rotate = _vector_attr(joint, "rotate")
        joint_orient = _vector_attr(joint, "jointOrient")
        new_joint_orient = [
            joint_orient[index] + rotate[index]
            for index in range(3)
        ]

        cmds.setAttr(
            "{0}.jointOrient".format(joint),
            new_joint_orient[0],
            new_joint_orient[1],
            new_joint_orient[2]
        )

        if zero_rotate:
            cmds.setAttr("{0}.rotate".format(joint), 0, 0, 0)

        results.append({
            "joint": joint,
            "rotate": rotate,
            "jointOrient": joint_orient,
            "newJointOrient": new_joint_orient,
        })

    print("Updated {0} joint(s).".format(len(results)))
    return results


def run(zero_rotate=False):
    """Run on the current Maya joint selection."""
    return add_rotate_to_joint_orient(zero_rotate=zero_rotate)


if __name__ == "__main__":
    run()
