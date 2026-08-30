# -*- coding: utf-8 -*-
"""Tests for centralized path/version rules."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from main.mApplication.houdini.cfx_workflow.path_rules import (
    PathRules,
    apply_path_rules,
    existing_versions,
    next_version,
)

SHOT_ARGS = ("projectA", "seq010", "shot020")


class PathRulesTest(unittest.TestCase):
    def setUp(self):
        self.rules = PathRules.from_dict({"root": "E:/show"})

    def test_root_is_required(self):
        with self.assertRaises(ValueError):
            PathRules.from_dict({})

    def test_format_version(self):
        self.assertEqual(self.rules.format_version(1), "v001")
        self.assertEqual(self.rules.format_version(12), "v012")
        self.assertEqual(self.rules.format_version("v007"), "v007")
        self.assertEqual(self.rules.format_version("7"), "v007")

    def test_parse_version(self):
        self.assertEqual(self.rules.parse_version("v012"), 12)
        with self.assertRaises(ValueError):
            self.rules.parse_version("version12")

    def test_version_padding(self):
        rules = PathRules.from_dict({"root": "E:/show", "version_padding": 4})
        self.assertEqual(rules.format_version(3), "v0003")

    def test_default_paths_match_studio_layout(self):
        self.assertEqual(
            self.rules.work_dir(*SHOT_ARGS),
            "E:/show/projectA/seq010/shot020/cfx/work",
        )
        self.assertEqual(
            self.rules.work_scene_path(*SHOT_ARGS, version="v001"),
            "E:/show/projectA/seq010/shot020/cfx/work/shot020_cfx_v001.hip",
        )
        self.assertEqual(
            self.rules.scene_template_path("projectA"),
            "E:/show/projectA/_templates/cfx_shot_template.hip",
        )
        self.assertEqual(
            self.rules.input_cache_path(*SHOT_ARGS, asset="char_main"),
            "E:/show/projectA/seq010/shot020/anim/cache/char_main.abc",
        )
        self.assertEqual(
            self.rules.cache_path(*SHOT_ARGS, asset="char_main", cfx_type="cloth", version=1),
            "E:/show/projectA/seq010/shot020/cfx/cache/cloth/char_main/v001/char_main.$F4.bgeo.sc",
        )
        self.assertEqual(
            self.rules.review_dir(*SHOT_ARGS, version="v001"),
            "E:/show/projectA/seq010/shot020/cfx/review/v001",
        )
        self.assertEqual(
            self.rules.publish_dir(*SHOT_ARGS, version="v001"),
            "E:/show/projectA/seq010/shot020/cfx/publish/v001",
        )

    def test_template_override(self):
        rules = PathRules.from_dict(
            {
                "root": "E:/show",
                "templates": {"cache_file": "{cache_dir}/{asset}.{version}.$F4.vdb"},
            }
        )
        path = rules.cache_path(*SHOT_ARGS, asset="fx_smoke", cfx_type="vellum", version=2)
        self.assertTrue(path.endswith("fx_smoke/v002/fx_smoke.v002.$F4.vdb"))

    def test_unknown_template_raises(self):
        with self.assertRaises(KeyError):
            self.rules.template("not_a_template")


class VersionScanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cfx_path_rules_test_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_empty_directory(self):
        self.assertEqual(existing_versions(self.tmp), [])
        self.assertEqual(next_version(self.tmp), 1)

    def test_missing_directory(self):
        self.assertEqual(existing_versions(self.tmp / "missing"), [])
        self.assertEqual(next_version(self.tmp / "missing"), 1)

    def test_version_dirs_and_filenames(self):
        (self.tmp / "v001").mkdir()
        (self.tmp / "v003").mkdir()
        (self.tmp / "shot020_cfx_v005.hip").write_text("x", encoding="utf-8")
        self.assertEqual(existing_versions(self.tmp), [1, 3, 5])
        self.assertEqual(next_version(self.tmp), 6)


class ApplyPathRulesTest(unittest.TestCase):
    def _data(self) -> dict:
        return {
            "show": "projectA",
            "sequence": "seq010",
            "shot": "shot020",
            "frame_start": 1001,
            "frame_end": 1120,
            "path_rules": {"root": "E:/show"},
            "assets": [
                {"name": "char_main", "cfx_type": "cloth", "hda": "h", "preset": "p"}
            ],
            "metadata": {"version": "v002"},
        }

    def test_missing_fields_are_generated(self):
        resolved = apply_path_rules(self._data())
        self.assertTrue(resolved["shot_scene_path"].endswith("shot020_cfx_v002.hip"))
        self.assertTrue(resolved["review_dir"].endswith("cfx/review/v002"))
        asset = resolved["assets"][0]
        self.assertTrue(
            asset["output_cache_path"].endswith(
                "cfx/cache/cloth/char_main/v002/char_main.$F4.bgeo.sc"
            )
        )
        self.assertTrue(asset["input_cache_path"].endswith("anim/cache/char_main.abc"))

    def test_explicit_values_win(self):
        data = self._data()
        data["work_dir"] = "X:/custom/work"
        data["assets"][0]["output_cache_path"] = "X:/custom/cache.$F4.bgeo.sc"
        resolved = apply_path_rules(data)
        self.assertEqual(resolved["work_dir"], "X:/custom/work")
        self.assertEqual(resolved["assets"][0]["output_cache_path"], "X:/custom/cache.$F4.bgeo.sc")

    def test_no_block_returns_input_unchanged(self):
        data = {"show": "a", "sequence": "b", "shot": "c", "assets": []}
        self.assertIs(apply_path_rules(data), data)

    def test_default_version_is_v001(self):
        data = self._data()
        del data["metadata"]
        resolved = apply_path_rules(data)
        self.assertTrue(resolved["shot_scene_path"].endswith("shot020_cfx_v001.hip"))


if __name__ == "__main__":
    unittest.main()
