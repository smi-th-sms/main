# -*- coding: utf-8 -*-
"""Workflow orchestrator — headless structure + graceful-failure tests.

The live cook is verified in a Houdini session; here we check the orchestrator
sequences the right steps and captures failures into the report without raising
(each build step needs ``hou`` and fails cleanly when it is absent).
"""

from __future__ import annotations

import unittest
from pathlib import Path

from main.mApplication.houdini.cfx_pipeline import workflow
from main.mApplication.houdini.cfx_pipeline.schema import (
    AssetSetupConfig,
    ShotSimConfig,
)

EXAMPLE_ASSET = (
    Path(__file__).resolve().parents[1] / "examples" / "asset_jake.json"
)


def _has_hou() -> bool:
    try:
        import hou  # noqa: F401
        return True
    except ImportError:
        return False


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.asset = AssetSetupConfig.from_dict({"show": "S", "asset": "A"})
        self.shot = ShotSimConfig.from_dict({
            "show": "S", "sequence": "q", "shot": "h", "asset": "A",
            "frame_start": 1001, "frame_end": 1010,
        })

    @unittest.skipIf(_has_hou(), "headless-only: needs hou absent")
    def test_asset_stage_stops_and_reports_without_hou(self):
        report = workflow.run_asset(self.asset)
        # first step fails (no hou) and the stage stops there
        self.assertEqual(len(report), 1)
        self.assertEqual(report[0]["step"], "asset:setup")
        self.assertFalse(report[0]["ok"])
        self.assertIn("error", report[0])

    @unittest.skipIf(_has_hou(), "headless-only: needs hou absent")
    def test_run_pipeline_skips_shot_when_asset_fails(self):
        report = workflow.run_pipeline(self.asset, self.shot)
        self.assertIsNone(report["shot"])
        self.assertEqual(report["stopped"], "asset stage failed")
        self.assertTrue(any(not e["ok"] for e in report["asset"]))

    def test_run_coerces_config_path_and_lists_stages(self):
        # a file path is loaded; the stages list is the full asset stage order
        report = workflow.run(str(EXAMPLE_ASSET))  # shot omitted -> asset only
        self.assertEqual(report["stages"][0], "asset:setup")
        self.assertIn("asset:rest_cache", report["stages"])
        self.assertNotIn("shot:setup", report["stages"])  # no shot given

    def test_run_asset_sim_test_inserts_stage(self):
        report = workflow.run(self.asset, asset_sim_test=True, to_stage="asset:setup")
        self.assertIn("asset:sim_test", report["stages"])

    def test_run_from_stage_slices(self):
        # slicing is name-based and happens before any hou call
        report = workflow.run(self.asset, from_stage="asset:proxy",
                              to_stage="asset:proxy")
        # only the sliced step ran (and failed without hou), full list preserved
        self.assertIn("asset:proxy", report["stages"])
        if report["ran"]:
            self.assertEqual(report["ran"][0]["step"], "asset:proxy")

    def test_summary_handles_run_shape(self):
        rep = {"stages": ["asset:setup"], "ran": [{"step": "asset:setup", "ok": True}]}
        self.assertIn("OK   asset:setup", workflow.summary(rep))

    def test_summary_is_text(self):
        report = {"asset": [{"step": "asset:setup", "ok": True}],
                  "shot": None, "stopped": "x"}
        text = workflow.summary(report)
        self.assertIn("OK   asset:setup", text)
        self.assertIn("STOPPED: x", text)


if __name__ == "__main__":
    unittest.main()
