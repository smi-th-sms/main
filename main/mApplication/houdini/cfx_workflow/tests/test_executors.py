# -*- coding: utf-8 -*-
"""Tests for per-stage task executors, run against the fake hou harness."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import fake_hou
from main.mApplication.houdini.cfx_workflow.config_loader import load_shot_config
from main.mApplication.houdini.cfx_workflow.executors import execute_payload, execute_task
from main.mApplication.houdini.cfx_workflow.schema import ShotConfig
from main.mApplication.houdini.cfx_workflow.shot_builder import build_houdini_scene
from main.mApplication.houdini.cfx_workflow.workflow import build_workflow_plan

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class ExecutorTestBase(unittest.TestCase):
    """Shared plan/task helpers; subclasses install fake hou as needed."""

    @classmethod
    def setUpClass(cls):
        cls.shot = load_shot_config(EXAMPLES / "shot_config.json")
        cls.plan = build_workflow_plan(cls.shot)
        cls.tasks = {task.task_id: task for task in cls.plan.tasks}

    def _install(self, **kwargs):
        module = fake_hou.create_fake_hou(**kwargs)
        fake_hou.install(module)
        self.addCleanup(fake_hou.uninstall)
        return module


class HdaCheckTest(ExecutorTestBase):
    def test_installed_hda_passes(self):
        self._install(available_hda_types={"studio::cloth_sim::1.0"})
        result = execute_task(self.shot, self.tasks["hda_check_char_main"])
        self.assertEqual(result.status, "done")
        self.assertTrue(result.details["installed"])

    def test_missing_hda_fails_with_warning(self):
        self._install()
        result = execute_task(self.shot, self.tasks["hda_check_char_main"])
        self.assertEqual(result.status, "failed")
        self.assertFalse(result.details["installed"])
        self.assertTrue(result.warnings)

    def test_outside_houdini_reports_failed_instead_of_raising(self):
        fake_hou.uninstall()
        result = execute_task(self.shot, self.tasks["hda_check_char_main"])
        self.assertEqual(result.status, "failed")
        self.assertIn("inside Houdini", result.message)


class ShotSetupAndFixTest(ExecutorTestBase):
    def test_shot_setup_builds_network(self):
        module = self._install()
        result = execute_task(self.shot, self.tasks["shot_setup"])
        self.assertEqual(result.status, "done")
        self.assertEqual(result.details["build"]["container"], "/obj/cfx_seq010_shot020")
        self.assertIn("cfx_seq010_shot020", module.obj.children)
        self.assertTrue(result.warnings)  # missing HDAs surface as warnings

    def test_fix_applies_parameter_patch(self):
        module = self._install()
        build_houdini_scene(self.shot)
        result = execute_task(self.shot, self.tasks["fix_01_collision_tuning"])
        self.assertEqual(result.status, "done")
        applied = {entry["parm"]: entry for entry in result.details["applied"]}
        self.assertAlmostEqual(applied["collision_thickness"]["old"], 0.015)
        self.assertAlmostEqual(applied["collision_thickness"]["new"], 0.0225)
        self.assertEqual(applied["substeps"]["old"], 4)
        self.assertEqual(applied["substeps"]["new"], 5)
        sim = module.node("/obj/cfx_seq010_shot020/cloth_char_main/sim_cloth")
        self.assertAlmostEqual(sim.parms["collision_thickness"].value, 0.0225)
        self.assertEqual(sim.parms["substeps"].value, 5)

    def test_fix_without_scene_fails(self):
        self._install()
        result = execute_task(self.shot, self.tasks["fix_01_collision_tuning"])
        self.assertEqual(result.status, "failed")
        self.assertIn("shot_setup", result.message)

    def test_fix_without_patch_is_manual(self):
        self._install()
        shot = ShotConfig.from_dict(
            {
                "show": "s", "sequence": "sq", "shot": "sh",
                "frame_start": 1001, "frame_end": 1100,
                "assets": [{"name": "a", "cfx_type": "cloth", "hda": "h", "preset": "p"}],
                "review_issues": [
                    {"issue_type": "wrong_input_cache", "asset": "a", "description": "d"}
                ],
            }
        )
        plan = build_workflow_plan(shot)
        fix = next(task for task in plan.tasks if task.stage.value == "fix")
        result = execute_task(shot, fix)
        self.assertEqual(result.status, "manual")


class SimCacheTest(ExecutorTestBase):
    def test_partial_resim_overrides_frame_range_and_cooks(self):
        module = self._install()
        build_houdini_scene(self.shot)
        result = execute_task(self.shot, self.tasks["sim_cache_char_main"])
        self.assertEqual(result.status, "done")
        self.assertEqual(result.details["frame_range"], [1032, 1054])
        self.assertEqual(result.details["resim_scope"], "partial")
        cache = module.node("/obj/cfx_seq010_shot020/cloth_char_main/write_cfx_cache")
        self.assertEqual(cache.parms["f1"].value, 1032)
        self.assertEqual(cache.parms["f2"].value, 1054)
        self.assertEqual(cache.parms["execute"].pressed, 1)

    def test_skipped_task_short_circuits_without_hou(self):
        fake_hou.uninstall()
        task = self.tasks["sim_cache_char_main"]
        skipped = type(task)(
            task_id=task.task_id,
            stage=task.stage,
            label=task.label,
            depends_on=task.depends_on,
            status="skipped",
            metadata=dict(task.metadata),
        )
        result = execute_task(self.shot, skipped)
        self.assertEqual(result.status, "skipped")

    def test_missing_scene_fails(self):
        self._install()
        result = execute_task(self.shot, self.tasks["sim_cache_char_main"])
        self.assertEqual(result.status, "failed")
        self.assertIn("shot_setup", result.message)


class ValidateTest(ExecutorTestBase):
    def test_missing_caches_fail_validation(self):
        result = execute_task(self.shot, self.tasks["validate_cache"])
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.details["report"]["status"], "fail")

    def test_complete_cache_passes(self):
        tmp = Path(tempfile.mkdtemp(prefix="cfx_executor_test_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        for frame in range(1001, 1011):
            (tmp / f"a.{frame:04d}.bgeo.sc").write_bytes(b"x" * 5000)
        shot = ShotConfig.from_dict(
            {
                "show": "s", "sequence": "sq", "shot": "sh",
                "frame_start": 1001, "frame_end": 1010,
                "assets": [
                    {
                        "name": "a", "cfx_type": "cloth", "hda": "h", "preset": "p",
                        "output_cache_path": str(tmp / "a.$F4.bgeo.sc"),
                    }
                ],
                "batch": {"force_resim": True},  # keep sim pending so validate runs
            }
        )
        plan = build_workflow_plan(shot)
        validate = next(task for task in plan.tasks if task.task_id == "validate_cache")
        result = execute_task(shot, validate)
        self.assertEqual(result.status, "done")
        self.assertEqual(result.details["report"]["status"], "pass")

    def test_incomplete_flush_only_for_partial_cache(self):
        from main.mApplication.houdini.cfx_workflow.executors import _incomplete_flush
        from main.mApplication.houdini.cfx_workflow.validator import validate_shot_caches

        def report_for(frames):
            tmp = Path(tempfile.mkdtemp(prefix="cfx_flush_"))
            self.addCleanup(shutil.rmtree, tmp, True)
            for frame in frames:
                (tmp / f"a.{frame:04d}.bgeo.sc").write_bytes(b"x" * 5000)
            shot = ShotConfig.from_dict(
                {
                    "show": "s", "sequence": "sq", "shot": "sh",
                    "frame_start": 1001, "frame_end": 1010,
                    "assets": [
                        {"name": "a", "cfx_type": "cloth", "hda": "h", "preset": "p",
                         "output_cache_path": str(tmp / "a.$F4.bgeo.sc")},
                    ],
                    "batch": {"force_resim": True},
                }
            )
            return validate_shot_caches(shot)

        # Some frames present but set incomplete -> looks like an in-flight flush.
        self.assertTrue(_incomplete_flush(report_for(range(1001, 1006))))
        # No frames at all -> genuine miss, must not trigger a retry/sleep.
        self.assertFalse(_incomplete_flush(report_for([])))
        # Complete cache -> nothing to retry.
        self.assertFalse(_incomplete_flush(report_for(range(1001, 1011))))


class PreviewReviewPublishTest(ExecutorTestBase):
    def test_preview_creates_and_cooks_opengl_rop(self):
        module = self._install()
        result = execute_task(self.shot, self.tasks["generate_preview"])
        self.assertEqual(result.status, "done")
        rop = module.node("/out/cfx_preview_seq010_shot020")
        self.assertEqual(rop.type().name(), "opengl")
        self.assertTrue(rop.parms["picture"].value.endswith("projectA_seq010_shot020.$F4.jpg"))
        self.assertEqual(rop.parms["f1"].value, 1001)
        self.assertEqual(rop.parms["f2"].value, 1120)
        self.assertEqual(rop.parms["execute"].pressed, 1)

    def test_preview_falls_back_to_manual_when_rop_type_missing(self):
        self._install(fail_node_types={"opengl"})
        result = execute_task(self.shot, self.tasks["generate_preview"])
        self.assertEqual(result.status, "manual")

    def test_review_is_manual_with_issue_summary(self):
        result = execute_task(self.shot, self.tasks["review_result"])
        self.assertEqual(result.status, "manual")
        self.assertEqual(result.details["open_issue_count"], 1)

    def test_blocked_publish_is_skipped(self):
        result = execute_task(self.shot, self.tasks["publish_final_cache"])
        self.assertEqual(result.status, "skipped")

    def test_unblocked_publish_is_manual_with_cache_list(self):
        task = self.tasks["publish_final_cache"]
        pending = type(task)(
            task_id=task.task_id,
            stage=task.stage,
            label=task.label,
            status="pending",
            metadata=dict(task.metadata),
        )
        result = execute_task(self.shot, pending)
        self.assertEqual(result.status, "manual")
        self.assertIn("char_main", result.details["caches"])


class PayloadRoundTripTest(ExecutorTestBase):
    def test_shot_config_round_trips_through_as_dict(self):
        self.assertEqual(ShotConfig.from_dict(self.shot.as_dict()), self.shot)

    def test_execute_payload_matches_execute_task(self):
        self._install()
        task = self.tasks["hda_check_char_main"]
        via_payload = execute_payload(task.as_dict(), self.shot.as_dict())
        direct = execute_task(self.shot, task).as_dict()
        self.assertEqual(via_payload, direct)


if __name__ == "__main__":
    unittest.main()
