# -*- coding: utf-8 -*-
"""Stage 3 shot_builder — import-safety + timeline math (no Houdini).

The hou-dependent network building is verified interactively in a Houdini
session; here we guard that the module imports without ``hou`` and that the
hou-dependent entry points fail loudly when it is absent.
"""

from __future__ import annotations

import unittest

from main.mApplication.houdini.cfx_pipeline import shot_builder as SB
from main.mApplication.houdini.cfx_pipeline.schema import AssetSetupConfig, ShotSimConfig


def _shot(**over) -> ShotSimConfig:
    data = {
        "show": "S", "sequence": "q", "shot": "h", "asset": "A",
        "frame_start": 1001, "frame_end": 1080,
    }
    data.update(over)
    return ShotSimConfig.from_dict(data)


class ContainerNameTest(unittest.TestCase):
    def test_container_scoped_by_asset(self):
        self.assertEqual(SB._shot_container_name(_shot()), "A_shot_setup")
        self.assertEqual(
            SB._shot_container_name(_shot(asset="Jake")), "Jake_shot_setup"
        )

    def test_hair_uv_export_vex_uses_rop_selection_without_swapping(self):
        copy_vex = SB._hair_uv_export_copy_vex("/out/hair")
        filter_vex = SB._hair_uv_export_filter_vex("/out/hair")
        self.assertIn('chs("/out/hair/hair_uv0_source")', copy_vex)
        self.assertIn("v@uv = value0;", copy_vex)
        self.assertNotIn("original_uv", copy_vex)
        self.assertIn('removeattrib(0, "detail", "varmap")', filter_vex)


class ImportSafetyTest(unittest.TestCase):
    def test_hou_dependent_entry_points_require_houdini(self):
        try:
            import hou  # noqa: F401
        except ImportError:
            shot = _shot()
            with self.assertRaises(RuntimeError):
                SB.build_shot_setup(shot)
            with self.assertRaises(RuntimeError):
                SB.clip_range(shot)
            with self.assertRaises(RuntimeError):
                SB.set_shot_timeline(shot)
            with self.assertRaises(RuntimeError):
                SB.load_asset_caches(shot)
            with self.assertRaises(RuntimeError):
                SB.build_shot_anim(shot)
            with self.assertRaises(RuntimeError):
                SB.build_shot_deform(shot)
            with self.assertRaises(RuntimeError):
                SB.build_shot_collision(shot)
            with self.assertRaises(RuntimeError):
                SB.build_shot_constraint(shot, AssetSetupConfig.from_dict(
                    {"show": "S", "asset": "A"}))
            with self.assertRaises(RuntimeError):
                SB.build_shot_solve(shot)
            with self.assertRaises(RuntimeError):
                SB.build_shot_cache(shot)
            with self.assertRaises(RuntimeError):
                SB.build_shot_cacheout(shot, AssetSetupConfig.from_dict(
                    {"show": "S", "asset": "A"}))


if __name__ == "__main__":
    unittest.main()
