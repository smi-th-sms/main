# -*- coding: utf-8 -*-
"""Tests for config loading, validation, and path_rules fill-in."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from main.mApplication.houdini.cfx_workflow.config_loader import (
    ConfigError,
    load_shot_config,
    validate_shot_config,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

MINIMAL_CONFIG = {
    "show": "projectA",
    "sequence": "seq010",
    "shot": "shot020",
    "frame_start": 1001,
    "frame_end": 1120,
    "assets": [
        {"name": "char_main", "cfx_type": "cloth", "hda": "studio::cloth_sim::1.0", "preset": "p"}
    ],
}


class LoadShotConfigTest(unittest.TestCase):
    def _write_config(self, data: dict) -> Path:
        tmp = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        )
        self.addCleanup(Path(tmp.name).unlink)
        json.dump(data, tmp)
        tmp.close()
        return Path(tmp.name)

    def test_load_example_config(self):
        shot = load_shot_config(EXAMPLES / "shot_config.json")
        self.assertEqual(shot.shot_id, "projectA_seq010_shot020")
        self.assertEqual(shot.frame_range, (1001, 1120))
        self.assertEqual([asset.name for asset in shot.assets], ["char_main", "char_main_hair"])
        self.assertEqual(len(shot.review_issues), 1)

    def test_missing_file_raises(self):
        with self.assertRaises(ConfigError):
            load_shot_config(EXAMPLES / "does_not_exist.json")

    def test_invalid_json_raises(self):
        path = self._write_config({})
        path.write_text("{ not json", encoding="utf-8")
        with self.assertRaises(ConfigError):
            load_shot_config(path)

    def test_missing_required_keys_raise(self):
        data = dict(MINIMAL_CONFIG)
        del data["assets"]
        with self.assertRaises(ConfigError) as ctx:
            validate_shot_config(data)
        self.assertIn("assets", str(ctx.exception))

    def test_reversed_frame_range_rejected(self):
        data = dict(MINIMAL_CONFIG)
        data["frame_start"], data["frame_end"] = 1120, 1001
        with self.assertRaises(ConfigError):
            validate_shot_config(data)

    def test_empty_assets_rejected(self):
        data = dict(MINIMAL_CONFIG)
        data["assets"] = []
        with self.assertRaises(ConfigError):
            validate_shot_config(data)

    def test_asset_missing_keys_rejected(self):
        data = dict(MINIMAL_CONFIG)
        data["assets"] = [{"name": "char_main"}]
        with self.assertRaises(ConfigError) as ctx:
            validate_shot_config(data)
        self.assertIn("cfx_type", str(ctx.exception))

    def test_path_rules_example_matches_explicit_config(self):
        explicit = load_shot_config(EXAMPLES / "shot_config.json")
        generated = load_shot_config(EXAMPLES / "shot_config_path_rules.json")
        self.assertEqual(generated.work_dir, explicit.work_dir)
        self.assertEqual(generated.shot_scene_path, explicit.shot_scene_path)
        self.assertEqual(generated.scene_template, explicit.scene_template)
        self.assertEqual(generated.review_dir, explicit.review_dir)
        for gen_asset, exp_asset in zip(generated.assets, explicit.assets):
            self.assertEqual(gen_asset.input_cache_path, exp_asset.input_cache_path)
            self.assertEqual(gen_asset.output_cache_path, exp_asset.output_cache_path)

    def test_invalid_path_rules_block_raises_config_error(self):
        data = dict(MINIMAL_CONFIG)
        data["path_rules"] = {"templates": {}}  # missing required "root"
        path = self._write_config(data)
        with self.assertRaises(ConfigError) as ctx:
            load_shot_config(path)
        self.assertIn("path_rules", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
