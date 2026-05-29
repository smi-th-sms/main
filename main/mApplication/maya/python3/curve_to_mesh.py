# -*- coding: utf-8 -*-
"""Shelf-friendly launcher for converting Maya curves to polygon meshes.

Usage in Maya:

    import curve_to_mesh
    curve_to_mesh.show()

    # Or convert selected curves directly:
    curve_to_mesh.run(radius=0.1, sides=8)
"""
from __future__ import print_function

from tools import curve_to_mesh_tool as _tool


def selected_curves(selection=None):
    return _tool.selected_curves(selection=selection)


def convert_curve_to_mesh(curve, radius=0.1, sides=8, segments=20,
                          caps=True, keep_history=False,
                          delete_curve=False, name_suffix="_mesh",
                          profile="Tube", width_ramp=None,
                          normal_object=None,
                          normal_source="Face / Mesh Normal"):
    return _tool.convert_curve_to_mesh(
        curve,
        radius=radius,
        sides=sides,
        segments=segments,
        caps=caps,
        keep_history=keep_history,
        delete_curve=delete_curve,
        name_suffix=name_suffix,
        profile=profile,
        width_ramp=width_ramp,
        normal_object=normal_object,
        normal_source=normal_source,
    )


def convert_selected(radius=0.1, sides=8, segments=20, caps=True,
                     keep_history=False, delete_curve=False,
                     name_suffix="_mesh", profile="Tube",
                     width_ramp=None, normal_object=None,
                     normal_source="Face / Mesh Normal"):
    return _tool.convert_selected(
        radius=radius,
        sides=sides,
        segments=segments,
        caps=caps,
        keep_history=keep_history,
        delete_curve=delete_curve,
        name_suffix=name_suffix,
        profile=profile,
        width_ramp=width_ramp,
        normal_object=normal_object,
        normal_source=normal_source,
    )


def show():
    return _tool.show()


def run(radius=0.1, sides=8, segments=20, caps=True,
        keep_history=False, delete_curve=False, profile="Tube",
        width_ramp=None, normal_object=None,
        normal_source="Face / Mesh Normal"):
    return _tool.run(
        radius=radius,
        sides=sides,
        segments=segments,
        caps=caps,
        keep_history=keep_history,
        delete_curve=delete_curve,
        profile=profile,
        width_ramp=width_ramp,
        normal_object=normal_object,
        normal_source=normal_source,
    )


if __name__ == "__main__":
    show()
