# -*- coding: utf-8 -*-
"""Tests for the Houdini shot scene builder, run against the fake hou harness."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import fake_hou
from main.mApplication.houdini.cfx_workflow.config_loader import load_shot_config
from main.mApplication.houdini.cfx_workflow.schema import ShotConfig
from main.mApplication.houdini.cfx_workflow.shot_builder import build_houdini_scene

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _shot(**overrides) -> ShotConfig:
    data = {
        "show": "projectA",
        "sequence": "seq010",
        "shot": "shot020",
        "frame_start": 1001,
        "frame_end": 1120,
        "assets": [
            {
                "name": "char_main",
                "cfx_type": "cloth",
                "hda": "studio::cloth_sim::1.0",
                "preset": "p",
                "input_cache_path": "E:/in/char_main.abc",
                "output_cache_path": "E:/out/char_main.$F4.bgeo.sc",
                "parameters": {"substeps": 4},
            }
        ],
    }
    data.update(overrides)
    return ShotConfig.from_dict(data)


class ShotBuilderTest(unittest.TestCase):
    def _install(self, **kwargs):
        module = fake_hou.create_fake_hou(**kwargs)
        fake_hou.install(module)
        self.addCleanup(fake_hou.uninstall)
        return module

    def test_requires_houdini(self):
        fake_hou.uninstall()
        with self.assertRaises(RuntimeError):
            build_houdini_scene(_shot())

    def test_example_config_builds_full_network(self):
        module = self._install()
        shot = load_shot_config(EXAMPLES / "shot_config.json")
        result = build_houdini_scene(shot)

        self.assertEqual(result["container"], "/obj/cfx_seq010_shot020")
        self.assertEqual(set(result["assets"]), {"char_main", "char_main_hair"})
        self.assertEqual(result["scene_template"]["action"], "missing")

        for info in result["assets"].values():
            self.assertFalse(info["hda_found"])  # studio HDAs not installed in fake
            self.assertTrue(info["applied_parameters"])

        # Chain wiring: input -> IN -> sim -> cache -> OUT
        geo = module.obj.children["cfx_seq010_shot020"].children["cloth_char_main"]
        self.assertIs(geo.children["IN_ANIM_CACHE"].indexed_inputs[0], geo.children["load_input_cache"])
        self.assertIs(geo.children["sim_cloth"].indexed_inputs[0], geo.children["IN_ANIM_CACHE"])
        self.assertIs(geo.children["write_cfx_cache"].indexed_inputs[0], geo.children["sim_cloth"])
        self.assertIs(geo.children["OUT_CFX_CACHE"].indexed_inputs[0], geo.children["write_cfx_cache"])
        self.assertTrue(geo.children["OUT_CFX_CACHE"].display)

        # Cache node config: explicit file method, output path, frame range
        cache = geo.children["write_cfx_cache"]
        self.assertEqual(cache.parms["filemethod"].value, 1)
        self.assertTrue(cache.parms["file"].value.endswith("char_main.$F4.bgeo.sc"))
        self.assertEqual(cache.parms["f1"].value, 1001)
        self.assertEqual(cache.parms["f2"].value, 1120)

        missing_hda = [w for w in result["warnings"] if "not installed" in w]
        self.assertEqual(len(missing_hda), 2)

    def test_installed_hda_creates_real_node_with_parameters(self):
        module = self._install(available_hda_types={"studio::cloth_sim::1.0"})
        result = build_houdini_scene(_shot())
        info = result["assets"]["char_main"]
        self.assertTrue(info["hda_found"])
        self.assertEqual(info["applied_parameters"], ["substeps"])
        sim = module.obj.children["cfx_seq010_shot020"].children["cloth_char_main"].children["sim_cloth"]
        self.assertEqual(sim.type().name(), "studio::cloth_sim::1.0")
        self.assertEqual(sim.parms["substeps"].value, 4)

    def test_alembic_input_for_abc_and_file_otherwise(self):
        module = self._install()
        assets = [
            {"name": "a", "cfx_type": "cloth", "hda": "h", "preset": "p",
             "input_cache_path": "E:/in/a.abc"},
            {"name": "b", "cfx_type": "hair", "hda": "h", "preset": "p",
             "input_cache_path": "E:/in/b.bgeo.sc"},
        ]
        build_houdini_scene(_shot(assets=assets))
        subnet = module.obj.children["cfx_seq010_shot020"]
        loader_a = subnet.children["cloth_a"].children["load_input_cache"]
        loader_b = subnet.children["hair_b"].children["load_input_cache"]
        self.assertEqual(loader_a.type().name(), "alembic")
        self.assertEqual(loader_a.parms["fileName"].value, "E:/in/a.abc")
        self.assertEqual(loader_b.type().name(), "file")
        self.assertEqual(loader_b.parms["file"].value, "E:/in/b.bgeo.sc")

    def test_missing_input_cache_leaves_in_null_unconnected(self):
        module = self._install()
        assets = [{"name": "a", "cfx_type": "cloth", "hda": "h", "preset": "p"}]
        result = build_houdini_scene(_shot(assets=assets))
        self.assertIsNone(result["assets"]["a"]["input"])
        geo = module.obj.children["cfx_seq010_shot020"].children["cloth_a"]
        self.assertEqual(geo.children["IN_ANIM_CACHE"].indexed_inputs, {})
        self.assertTrue(any("no input_cache_path" in w for w in result["warnings"]))

    def test_loader_type_failure_falls_back_to_null(self):
        module = self._install(fail_node_types={"alembic"})
        result = build_houdini_scene(_shot())
        geo = module.obj.children["cfx_seq010_shot020"].children["cloth_char_main"]
        self.assertEqual(geo.children["load_input_cache"].type().name(), "null")
        self.assertTrue(any("placeholder null" in w for w in result["warnings"]))

    def test_scene_template_loads_in_fresh_session(self):
        module = self._install(fresh_session=True)
        template = tempfile.NamedTemporaryFile(suffix=".hip", delete=False)
        template.close()
        self.addCleanup(Path(template.name).unlink)
        result = build_houdini_scene(_shot(scene_template=template.name))
        self.assertEqual(result["scene_template"]["action"], "loaded")
        self.assertEqual(module.hipFile.loaded, [template.name])
        self.assertEqual(module.hipFile.merged, [])

    def test_scene_template_merges_into_dirty_session(self):
        module = self._install(fresh_session=False)
        template = tempfile.NamedTemporaryFile(suffix=".hip", delete=False)
        template.close()
        self.addCleanup(Path(template.name).unlink)
        result = build_houdini_scene(_shot(scene_template=template.name))
        self.assertEqual(result["scene_template"]["action"], "merged")
        self.assertEqual(module.hipFile.merged, [template.name])
        self.assertEqual(module.hipFile.loaded, [])
        self.assertTrue(any("merged scene template" in w for w in result["warnings"]))

    def test_existing_nodes_are_reused(self):
        module = self._install()
        shot = _shot()
        first = build_houdini_scene(shot)
        second = build_houdini_scene(shot)
        self.assertEqual(first["container"], second["container"])
        subnet = module.obj.children["cfx_seq010_shot020"]
        self.assertEqual(len(subnet.children), 1)  # still one asset container


if __name__ == "__main__":
    unittest.main()
