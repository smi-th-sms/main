# -*- coding: utf-8 -*-
"""Tests for dynamic workflow plan building."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from main.mApplication.houdini.cfx_workflow.config_loader import load_shot_config
from main.mApplication.houdini.cfx_workflow.schema import ShotConfig
from main.mApplication.houdini.cfx_workflow.workflow import build_workflow_plan

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _config(**overrides) -> ShotConfig:
    data = {
        "show": "projectA",
        "sequence": "seq010",
        "shot": "shot020",
        "frame_start": 1001,
        "frame_end": 1120,
        "assets": [
            {"name": "char_main", "cfx_type": "cloth", "hda": "h", "preset": "p"}
        ],
    }
    data.update(overrides)
    return ShotConfig.from_dict(data)


class ExamplePlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shot = load_shot_config(EXAMPLES / "shot_config.json")
        cls.plan = build_workflow_plan(cls.shot)
        cls.tasks = {task.task_id: task for task in cls.plan.tasks}

    def test_plan_shape(self):
        self.assertEqual(len(self.plan.tasks), 10)
        self.assertEqual(
            [task.stage.value for task in self.plan.tasks],
            [
                "hda_check", "hda_check", "shot_setup", "fix",
                "sim_cache", "sim_cache", "validate", "preview",
                "review", "publish",
            ],
        )

    def test_setup_depends_on_all_hda_checks(self):
        self.assertEqual(
            self.tasks["shot_setup"].depends_on,
            ["hda_check_char_main", "hda_check_char_main_hair"],
        )

    def test_fix_task_carries_routed_action(self):
        action = self.tasks["fix_01_collision_tuning"].metadata["fix_action"]
        self.assertEqual(action["resim_scope"], "partial")
        self.assertEqual(action["frame_range"], [1032, 1054])
        self.assertEqual(action["target_asset"], "char_main")
        self.assertEqual(
            {entry["parm"] for entry in action["parameter_patch"]},
            {"collision_thickness", "substeps"},
        )

    def test_sim_tasks_depend_on_fixes_and_carry_resim_scope(self):
        sim_main = self.tasks["sim_cache_char_main"]
        self.assertEqual(sim_main.depends_on, ["fix_01_collision_tuning"])
        self.assertEqual(sim_main.metadata["resim_scope"], "partial")
        self.assertEqual(sim_main.metadata["resim_frame_range"], [1032, 1054])

        sim_hair = self.tasks["sim_cache_char_main_hair"]
        self.assertEqual(sim_hair.metadata["resim_scope"], "full")
        self.assertIsNone(sim_hair.metadata["resim_frame_range"])

    def test_publish_blocked_by_default(self):
        self.assertEqual(self.tasks["publish_final_cache"].status, "blocked")


class DynamicBranchTest(unittest.TestCase):
    def test_validate_disabled_skips_validation_stage(self):
        plan = build_workflow_plan(_config(batch={"validate_cache": False}))
        stages = [task.stage.value for task in plan.tasks]
        self.assertNotIn("validate", stages)
        preview = next(task for task in plan.tasks if task.task_id == "generate_preview")
        self.assertEqual(preview.depends_on, ["sim_cache_char_main"])

    def test_preview_disabled_skips_preview_stage(self):
        plan = build_workflow_plan(_config(batch={"generate_preview": False}))
        stages = [task.stage.value for task in plan.tasks]
        self.assertNotIn("preview", stages)
        review = next(task for task in plan.tasks if task.task_id == "review_result")
        self.assertEqual(review.depends_on, ["validate_cache"])

    def test_publish_pending_when_enabled(self):
        plan = build_workflow_plan(_config(batch={"publish_on_approved": True}))
        publish = next(task for task in plan.tasks if task.task_id == "publish_final_cache")
        self.assertEqual(publish.status, "pending")

    def test_hda_change_issue_adds_publish_task(self):
        plan = build_workflow_plan(
            _config(
                review_issues=[
                    {"issue_type": "hda_change", "asset": "char_main", "description": "d"}
                ]
            )
        )
        task_ids = [task.task_id for task in plan.tasks]
        self.assertIn("hda_publish_char_main", task_ids)
        hda_publish = next(t for t in plan.tasks if t.task_id == "hda_publish_char_main")
        self.assertEqual(hda_publish.depends_on, ["fix_01_hda_iteration"])

    def test_closed_issues_add_no_fix_tasks(self):
        plan = build_workflow_plan(
            _config(
                review_issues=[
                    {
                        "issue_type": "penetration",
                        "asset": "char_main",
                        "status": "approved",
                        "description": "d",
                    }
                ]
            )
        )
        self.assertNotIn("fix", [task.stage.value for task in plan.tasks])


class SimSkipTest(unittest.TestCase):
    def _config_with_cache(self, **overrides) -> ShotConfig:
        cache = tempfile.NamedTemporaryFile(suffix=".abc", delete=False)
        cache.close()
        self.addCleanup(Path(cache.name).unlink)
        asset = {
            "name": "char_main",
            "cfx_type": "cloth",
            "hda": "h",
            "preset": "p",
            "output_cache_path": cache.name,
        }
        return _config(assets=[asset], **overrides)

    def test_sim_skipped_when_cache_exists(self):
        plan = build_workflow_plan(self._config_with_cache())
        sim = next(task for task in plan.tasks if task.task_id == "sim_cache_char_main")
        self.assertEqual(sim.status, "skipped")
        self.assertEqual(sim.metadata["resim_scope"], "none")

    def test_sim_skipped_when_frame_sequence_cache_exists(self):
        # Regression: a cache path with a $F token must resolve to the real
        # frame files on disk. Checking the literal "...char_main.$F4.bgeo.sc"
        # path always reports missing, so the sim never skipped.
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for frame in (1001, 1002, 1003):
            Path(tmp, f"char_main.{frame}.bgeo.sc").write_text("x")
        asset = {
            "name": "char_main", "cfx_type": "cloth", "hda": "h", "preset": "p",
            "output_cache_path": str(Path(tmp, "char_main.$F4.bgeo.sc")),
        }
        plan = build_workflow_plan(_config(assets=[asset]))
        sim = next(task for task in plan.tasks if task.task_id == "sim_cache_char_main")
        self.assertEqual(sim.status, "skipped")
        self.assertEqual(sim.metadata["resim_scope"], "none")

    def test_force_resim_keeps_sim_pending(self):
        plan = build_workflow_plan(self._config_with_cache(batch={"force_resim": True}))
        sim = next(task for task in plan.tasks if task.task_id == "sim_cache_char_main")
        self.assertEqual(sim.status, "pending")
        self.assertEqual(sim.metadata["resim_scope"], "full")

    def test_open_issue_keeps_sim_pending(self):
        plan = build_workflow_plan(
            self._config_with_cache(
                review_issues=[
                    {
                        "issue_type": "penetration",
                        "asset": "char_main",
                        "frames": [1050],
                        "description": "d",
                    }
                ]
            )
        )
        sim = next(task for task in plan.tasks if task.task_id == "sim_cache_char_main")
        self.assertEqual(sim.status, "pending")
        self.assertEqual(sim.metadata["resim_scope"], "partial")
        self.assertEqual(sim.metadata["resim_frame_range"], [1040, 1060])


class ResimScopeTest(unittest.TestCase):
    def test_partial_ranges_merge(self):
        plan = build_workflow_plan(
            _config(
                frame_end=1200,
                review_issues=[
                    {"issue_type": "penetration", "asset": "char_main", "frames": [1020]},
                    {"issue_type": "penetration", "asset": "char_main", "frames": [1150, 1152]},
                ],
            )
        )
        sim = next(task for task in plan.tasks if task.task_id == "sim_cache_char_main")
        self.assertEqual(sim.metadata["resim_scope"], "partial")
        self.assertEqual(sim.metadata["resim_frame_range"], [1010, 1162])

    def test_full_scope_overrides_partials(self):
        plan = build_workflow_plan(
            _config(
                review_issues=[
                    {"issue_type": "penetration", "asset": "char_main", "frames": [1020]},
                    {"issue_type": "unstable_sim", "asset": "char_main"},
                ]
            )
        )
        sim = next(task for task in plan.tasks if task.task_id == "sim_cache_char_main")
        self.assertEqual(sim.metadata["resim_scope"], "full")
        self.assertIsNone(sim.metadata["resim_frame_range"])

    def test_preview_only_issue_does_not_force_resim_scope(self):
        plan = build_workflow_plan(
            _config(
                review_issues=[
                    {"issue_type": "preview_only", "asset": "char_main", "description": "d"}
                ]
            )
        )
        sim = next(task for task in plan.tasks if task.task_id == "sim_cache_char_main")
        # No cache on disk -> full pass, not driven by the preview-only fix
        self.assertEqual(sim.metadata["resim_scope"], "full")


if __name__ == "__main__":
    unittest.main()
