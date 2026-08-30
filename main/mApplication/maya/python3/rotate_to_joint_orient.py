# -*- coding: utf-8 -*-
"""Shelf-friendly launcher for adding rotate values into jointOrient.

Usage in Maya:

import rotate_to_joint_orient
rotate_to_joint_orient.run()
"""
from __future__ import print_function

from libs.joints import rotate_to_joint_orient as _tool


def selected_joints():
    return _tool.selected_joints()


def add_rotate_to_joint_orient(joints=None, zero_rotate=False):
    return _tool.add_rotate_to_joint_orient(
        joints=joints,
        zero_rotate=zero_rotate
    )


def run(zero_rotate=False):
    return _tool.run(zero_rotate=zero_rotate)


if __name__ == "__main__":
    run()
