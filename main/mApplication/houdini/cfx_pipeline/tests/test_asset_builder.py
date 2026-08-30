# -*- coding: utf-8 -*-
"""Stage 2 asset_builder — import-safety + field-map integrity (no Houdini).

The hou-dependent behaviour (apply/read/detect against a live FBX node) is
verified interactively in a Houdini session; here we guard the static field
maps against schema drift so a renamed config field fails loudly.
"""

from __future__ import annotations

import dataclasses
import unittest

from main.mApplication.houdini.cfx_pipeline import asset_builder as AB
from main.mApplication.houdini.cfx_pipeline.schema import FbxSetup


class FieldMapTest(unittest.TestCase):
    def test_maps_reference_real_fbxsetup_fields(self):
        fields = {f.name for f in dataclasses.fields(FbxSetup)}
        for attr, parm_name, kind in AB.FBX_STRUCTURAL + AB.FBX_TUNING:
            self.assertIn(attr, fields, f"{attr} is not a FbxSetup field")
            self.assertIn(kind, ("s", "i", "f", "v3"), f"bad kind {kind}")

    def test_structural_and_tuning_disjoint(self):
        s = {a for a, _, _ in AB.FBX_STRUCTURAL}
        t = {a for a, _, _ in AB.FBX_TUNING}
        self.assertEqual(s & t, set(), "a field cannot be both structural and tuning")

    def test_authority_split_matches_design(self):
        # imports + identity are config-authoritative (pushed)
        structural = {a for a, _, _ in AB.FBX_STRUCTURAL}
        self.assertLessEqual(
            {"asset_name", "root_name", "pelvis_name", "character_import",
             "hair_import", "animation_import"},
            structural,
        )
        # interactive tuning is read-back only
        tuning = {a for a, _, _ in AB.FBX_TUNING}
        self.assertLessEqual(
            {"t_pos", "position_mult", "rotate_mult", "pelvis_rotate"}, tuning
        )

    def test_hou_dependent_helpers_require_houdini(self):
        # module imports without hou; hou-dependent helpers fail loudly
        try:
            import hou  # noqa: F401
        except ImportError:
            with self.assertRaises(RuntimeError):
                AB.skeleton_joint_names(object())
            with self.assertRaises(RuntimeError):
                AB.build_asset_setup(object())


if __name__ == "__main__":
    unittest.main()
