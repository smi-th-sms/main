# -*- coding: utf-8 -*-
"""Stage 1 (Config) tests — path rules, schema round-trip, handoff linking."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from main.mApplication.houdini.cfx_pipeline.config_loader import (
    asset_config_path,
    load_asset_config,
    load_pipeline_config,
    load_shot_config,
)
from main.mApplication.houdini.cfx_pipeline.path_rules import (
    PipelinePathRules,
    next_version,
)
from main.mApplication.houdini.cfx_pipeline.schema import (
    AssetSetupConfig,
    CacheOutConfig,
    ProxyPart,
    ShotSimConfig,
)

_EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
EXAMPLE_ASSET = _EXAMPLES / "asset_jake.json"
EXAMPLE_SHOT = _EXAMPLES / "shot_pubgom_seq010_shot020.json"

_JAKE_REST_PROXY = (
    "Z:/show/PUBGOM/assets/Character/Jake/Sim/wip/houdini/geo/"
    "Jake_proxy_rest/v001/Jake_proxy_rest.bgeo.sc"
)


class PathRulesTest(unittest.TestCase):
    def setUp(self):
        self.rules = PipelinePathRules.from_dict({"root": "Z:/show"})

    def test_asset_paths_match_manager_conventions(self):
        ctx = dict(show="PUBGOM", asset="Jake", version="v001")
        self.assertEqual(
            self.rules.resolve("asset_work", **ctx),
            "Z:/show/PUBGOM/assets/Character/Jake/Sim/wip/houdini",
        )
        self.assertEqual(
            self.rules.resolve("character_fbx_dir", **ctx),
            "Z:/show/PUBGOM/assets/Character/Jake/RIG/wip/maya/fbx",
        )
        self.assertEqual(
            self.rules.resolve("hair_guide_dir", **ctx),
            "Z:/show/PUBGOM/assets/Character/Jake/RIG/wip/maya/cache/alembic",
        )

    def test_shot_paths_match_manager_conventions(self):
        ctx = dict(show="PUBGOM", sequence="seq010", shot="shot020",
                   asset="Jake", version="v002")
        self.assertEqual(
            self.rules.resolve("shot_work", **ctx),
            "Z:/show/PUBGOM/sequences/seq010/shot020/SIM/wip/houdini",
        )
        self.assertEqual(
            self.rules.resolve("shot_anim_dir", **ctx),
            "Z:/show/PUBGOM/sequences/seq010/shot020/ANM/pub/fbx",
        )
        # version normalized + embedded
        self.assertIn("/v002/", self.rules.resolve("shot_sim_cache", **ctx))

    def test_recursive_template_expansion(self):
        # asset_proxy_cache embeds {asset_work} which embeds {asset_root}
        path = self.rules.resolve("asset_proxy_cache", show="S", asset="A", version=3)
        self.assertTrue(path.startswith("Z:/show/S/assets/Character/A/Sim/wip/houdini/geo/"))
        self.assertIn("A_proxy_rest", path)
        self.assertTrue(path.endswith("A_proxy_rest.bgeo.sc"))  # static rest, no $F4

    def test_template_and_context_override(self):
        rules = PipelinePathRules.from_dict({
            "root": "E:/local",
            "templates": {"asset_work": "{asset_root}/houdini"},
            "context": {"asset_subpath": "chars"},
        })
        self.assertEqual(
            rules.resolve("asset_work", show="X", asset="Y", version=1),
            "E:/local/X/chars/Y/houdini",
        )

    def test_missing_context_raises(self):
        with self.assertRaises(KeyError):
            self.rules.resolve("shot_work", show="S")  # missing sequence/shot

    def test_int_version_normalized(self):
        self.assertEqual(self.rules.format_version(2), "v002")
        self.assertEqual(self.rules.format_version("v015"), "v015")


class VersionScanTest(unittest.TestCase):
    def test_next_version(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(next_version(d), 1)
            (Path(d) / "v001").mkdir()
            (Path(d) / "v003").mkdir()
            self.assertEqual(next_version(d), 4)


class SchemaRoundTripTest(unittest.TestCase):
    def test_cache_out_defaults_preserve_gimmick(self):
        c = CacheOutConfig.from_dict({})
        self.assertEqual(c.cloth_attach_joint, "pelvis")
        self.assertEqual(c.hair_attach_chain[0], "head")
        self.assertEqual(c.hair_attach_chain[-1], "root")
        self.assertEqual(c.ue_scale, 100.0)
        self.assertEqual(c.ue_rotate, (-90.0, 0.0, 0.0))

    def test_asset_roundtrip(self):
        data = {
            "show": "S", "asset": "A",
            "fbx": {"asset_name": "A", "pelvis_name": "pelvis_jnt"},
            "proxy_parts": [{"name": "pants"}, {"name": "hair", "cloth": False}],
        }
        cfg = AssetSetupConfig.from_dict(data)
        self.assertEqual(cfg.fbx.pelvis_name, "pelvis_jnt")
        self.assertEqual([p.name for p in cfg.cloth_parts], ["pants"])
        again = AssetSetupConfig.from_dict(cfg.as_dict())
        self.assertEqual(again.as_dict(), cfg.as_dict())

    def test_proxy_part_path_split(self):
        # geo_path accepts a single string or a list; proxy_path defaults by name
        p = ProxyPart.from_dict({"name": "pants",
                                 "geo_path": "/Jake/geo/Pants_geo"})
        self.assertEqual(p.geo_path, ["/Jake/geo/Pants_geo"])
        self.assertEqual(p.proxy_group, "*pants*")  # derived
        self.assertEqual(p.geo_group(), "@geo_path=/Jake/geo/Pants_geo")

    def test_proxy_part_combines_multiple_geo_paths(self):
        # a part can group several geo_paths (the "묶어서" case)
        p = ProxyPart.from_dict({
            "name": "upper", "proxy_path": "*upper*",
            "geo_path": ["/C/head_grp/head", "/C/cloth_grp/collar"],
        })
        self.assertEqual(p.proxy_group, "*upper*")  # explicit wins
        self.assertEqual(
            p.geo_group(),
            "@geo_path=/C/head_grp/head @geo_path=/C/cloth_grp/collar",
        )

    def test_merge_parts_readback(self):
        # interactive flow: parts authored in Houdini merged back into config
        cfg = AssetSetupConfig.from_dict({"show": "S", "asset": "A"})
        self.assertEqual(cfg.proxy_parts, [])
        merged = cfg.merge_parts([
            {"name": "pants", "geo_path": "/A/Pants"},
            ProxyPart(name="hair", cloth=False),
        ])
        self.assertEqual([p.name for p in merged.proxy_parts], ["pants", "hair"])
        self.assertEqual([p.name for p in merged.cloth_parts], ["pants"])
        # original unchanged (frozen dataclass, replace returns a copy)
        self.assertEqual(cfg.proxy_parts, [])

    def test_shot_roundtrip(self):
        data = {
            "show": "S", "sequence": "q", "shot": "h", "asset": "A",
            "frame_start": 1001, "frame_end": 1050,
            "sim_params": {"substeps": 6},
        }
        cfg = ShotSimConfig.from_dict(data)
        self.assertEqual(cfg.shot_id, "S_q_h")
        self.assertEqual(cfg.frame_range, (1001, 1050))
        self.assertEqual(cfg.sim_params["substeps"], 6)
        again = ShotSimConfig.from_dict(cfg.as_dict())
        self.assertEqual(again.as_dict(), cfg.as_dict())


class LoaderTest(unittest.TestCase):
    def test_asset_example_loads_bare(self):
        # bare file: top-level "asset" is the name string, not a wrapper block
        asset = load_asset_config(EXAMPLE_ASSET)
        self.assertIsInstance(asset, AssetSetupConfig)
        self.assertEqual(asset.asset, "Jake")
        self.assertEqual(asset.proxy_cache_path, _JAKE_REST_PROXY)
        self.assertEqual([p.name for p in asset.cloth_parts], ["pants", "shirts", "belt"])
        # geo_path selected from real REST_MESH values
        self.assertTrue(asset.proxy_parts[0].geo_path[0].endswith("Pants_geo"))

    def test_shot_example_loads_bare(self):
        shot = load_shot_config(EXAMPLE_SHOT)
        self.assertIsInstance(shot, ShotSimConfig)
        self.assertEqual(shot.shot_id, "PUBGOM_seq010_shot020")
        self.assertTrue(shot.sim_cache_path.endswith("Jake_sim.$F4.bgeo.sc"))
        self.assertIn("seq010/shot020", shot.cloth_abc_path)
        # asset config not on the real Z: drive -> handoff path derived from rules
        self.assertEqual(shot.asset_proxy_cache, _JAKE_REST_PROXY)

    def test_shot_links_explicit_asset(self):
        asset = load_asset_config(EXAMPLE_ASSET)
        shot = load_shot_config(EXAMPLE_SHOT, asset=asset)
        self.assertEqual(shot.asset_proxy_cache, asset.proxy_cache_path)

    def test_shot_autodiscovers_asset_on_disk(self):
        # asset config placed at its rules-derived path is auto-found + linked,
        # and its OWN version (v005) wins over the shot default (v001).
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).as_posix()
            rules = {"root": root}
            asset_dir = Path(d) / "PUBGOM/assets/Character/Jake/Sim/wip/houdini"
            asset_dir.mkdir(parents=True)
            (asset_dir / "cfx_asset.json").write_text(json.dumps({
                "path_rules": rules, "show": "PUBGOM", "asset": "Jake",
                "metadata": {"version": "v005"},
            }), encoding="utf-8")
            shot_path = Path(d) / "shot.json"
            shot_path.write_text(json.dumps({
                "path_rules": rules, "show": "PUBGOM", "sequence": "seq010",
                "shot": "shot020", "asset": "Jake",
                "frame_start": 1001, "frame_end": 1080,
                "metadata": {"version": "v001"},
            }), encoding="utf-8")
            shot = load_shot_config(shot_path)
            self.assertIn("/v005/", shot.asset_proxy_cache)

    def test_asset_config_path_helper(self):
        from main.mApplication.houdini.cfx_pipeline.path_rules import PipelinePathRules
        rules = PipelinePathRules.from_dict({"root": "Z:/show"})
        self.assertEqual(
            asset_config_path("PUBGOM", "Jake", rules),
            "Z:/show/PUBGOM/assets/Character/Jake/Sim/wip/houdini/cfx_asset.json",
        )

    def test_explicit_paths_win(self):
        data = {
            "path_rules": {"root": "Z:/show"},
            "show": "S", "asset": "A",
            "asset_work": "D:/override/work",
        }
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "cfx_asset.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            cfg = load_asset_config(p)
            self.assertEqual(cfg.asset_work, "D:/override/work")
            self.assertTrue(cfg.character_fbx_dir.endswith("RIG/wip/maya/fbx"))

    def test_combined_file_still_supported(self):
        # load_pipeline_config keeps working for a single combined file
        data = {
            "path_rules": {"root": "Z:/show"},
            "asset": {"show": "PUBGOM", "asset": "Jake"},
            "shot": {
                "show": "PUBGOM", "sequence": "seq010", "shot": "shot020",
                "asset": "Jake", "frame_start": 1001, "frame_end": 1080,
            },
        }
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "combined.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            asset, shot = load_pipeline_config(p)
            self.assertEqual(shot.asset_proxy_cache, asset.proxy_cache_path)

    def test_all_handoff_caches_linked(self):
        # every asset rest cache (proxy/hair/collision/corrective) is linked
        # onto the shot for the Stage 3.2 load.
        data = {
            "path_rules": {"root": "Z:/show"},
            "asset": {"show": "PUBGOM", "asset": "Jake"},
            "shot": {
                "show": "PUBGOM", "sequence": "seq010", "shot": "shot020",
                "asset": "Jake", "frame_start": 1001, "frame_end": 1080,
            },
        }
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "combined.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            asset, shot = load_pipeline_config(p)
            self.assertEqual(shot.asset_proxy_cache, asset.proxy_cache_path)
            self.assertEqual(shot.asset_hair_cache, asset.hair_cache_path)
            self.assertEqual(shot.asset_collision_cache, asset.collision_cache_path)
            self.assertEqual(shot.asset_corrective_cache, asset.corrective_cache_path)
            self.assertTrue(shot.asset_corrective_cache.endswith(
                "Jake_corrective_rest.bgeo.sc"))

    def test_shot_standalone_derives_all_handoff_caches(self):
        # no asset config on disk -> all four still derived from rules
        shot = load_shot_config(EXAMPLE_SHOT)
        for path in (shot.asset_proxy_cache, shot.asset_hair_cache,
                     shot.asset_collision_cache, shot.asset_corrective_cache):
            self.assertTrue(path and "Jake" in path)
        self.assertIn("corrective_rest", shot.asset_corrective_cache)


if __name__ == "__main__":
    unittest.main()
