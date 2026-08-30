# -*- coding: utf-8 -*-
"""Tests for the TOPs/PDG graph builder, run against the fake hou harness."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import fake_hou
from main.mApplication.houdini.cfx_workflow.config_loader import load_shot_config
from main.mApplication.houdini.cfx_workflow.top_builder import build_top_network
from main.mApplication.houdini.cfx_workflow.workflow import build_workflow_plan

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class TopBuilderTest(unittest.TestCase):
    def setUp(self):
        self.module = fake_hou.create_fake_hou()
        fake_hou.install(self.module)
        self.addCleanup(fake_hou.uninstall)
        self.shot = load_shot_config(EXAMPLES / "shot_config.json")
        self.plan = build_workflow_plan(self.shot)
        self.result = build_top_network(self.plan)
        self.topnet = self.module.obj.children["cfx_top_seq010_shot020"]

    def test_requires_houdini(self):
        fake_hou.uninstall()
        with self.assertRaises(RuntimeError):
            build_top_network(self.plan)
        fake_hou.install(self.module)

    def test_topnet_and_node_per_task(self):
        self.assertEqual(self.result["topnet"], "/obj/cfx_top_seq010_shot020")
        self.assertEqual(
            set(self.result["nodes"]), {task.task_id for task in self.plan.tasks}
        )

    def test_stage_to_node_type_mapping(self):
        for task in self.plan.tasks:
            info = self.result["nodes"][task.task_id]
            expected = "ropfetch" if task.stage.value == "sim_cache" else "pythonscript"
            self.assertEqual(info["type"], expected, task.task_id)

    def test_dependency_wiring(self):
        sim = self.topnet.children["sim_cache_char_main"]
        self.assertEqual(
            [node.path() for node in sim.next_inputs],
            ["/obj/cfx_top_seq010_shot020/fix_01_collision_tuning"],
        )
        setup = self.topnet.children["shot_setup"]
        self.assertEqual(len(setup.next_inputs), 2)  # both hda_check tasks
        publish = self.topnet.children["publish_final_cache"]
        self.assertEqual(
            [node.path() for node in publish.next_inputs],
            ["/obj/cfx_top_seq010_shot020/review_result"],
        )

    def test_blocked_and_skipped_tasks_are_bypassed(self):
        publish = self.topnet.children["publish_final_cache"]
        self.assertTrue(publish.bypassed)
        self.assertTrue(self.result["nodes"]["publish_final_cache"]["bypassed"])
        self.assertFalse(self.result["nodes"]["sim_cache_char_main"]["bypassed"])

    def test_ropfetch_targets_shot_builder_cache_rop(self):
        sim = self.topnet.children["sim_cache_char_main"]
        self.assertEqual(
            sim.parms["roppath"].value,
            "/obj/cfx_seq010_shot020/cloth_char_main/write_cfx_cache",
        )
        self.assertEqual(sim.parms["framegeneration"].value, 1)
        # Sim must cook as a single sequential work item, not per-frame jobs.
        self.assertEqual(sim.parms["singletask"].value, 1)
        # char_main has an open penetration issue (frames 1042-1044), so the
        # ropfetch must cook only the padded partial range, not the full shot.
        self.assertEqual(sim.parms["range1x"].value, 1032)
        self.assertEqual(sim.parms["range1y"].value, 1054)
        self.assertEqual(sim.parms["range1z"].value, 1)

    def test_ropfetch_uses_full_range_without_fix(self):
        # char_main_hair has no issue, so its sim cooks the full shot range.
        sim = self.topnet.children["sim_cache_char_main_hair"]
        self.assertEqual(sim.parms["range1x"].value, 1001)
        self.assertEqual(sim.parms["range1y"].value, 1120)

    def test_preview_is_pythonscript_not_ropfetch(self):
        # The preview OpenGL ROP is created by run_preview at execution time, so
        # PREVIEW is a pythonscript stub (no build-time ROP to fetch, no warning).
        preview = self.topnet.children["generate_preview"]
        self.assertEqual(preview.type().name(), "pythonscript")
        self.assertIn("execute_payload", preview.parms["script"].value)
        warnings = [w for w in self.result["warnings"] if w.startswith("generate_preview:")]
        self.assertEqual(warnings, [])

    def test_pythonscript_stub_payloads_round_trip(self):
        script = self.topnet.children["validate_cache"].parms["script"].value
        self.assertIn("import json", script)
        blocks = script.split("r'''")
        task = json.loads(blocks[1].split("'''", 1)[0])
        self.assertEqual(task["task_id"], "validate_cache")
        self.assertEqual(task["stage"], "validate")
        shot_config = json.loads(blocks[2].split("'''", 1)[0])
        self.assertEqual(shot_config["show"], "projectA")
        self.assertEqual(len(shot_config["assets"]), 2)

    def test_pythonscript_stub_calls_executors(self):
        script = self.topnet.children["validate_cache"].parms["script"].value
        self.assertIn("from main.mApplication.houdini.cfx_workflow import executors", script)
        self.assertIn("executors.execute_payload(task, shot_config)", script)
        self.assertIn("raise RuntimeError", script)  # failed results fail the work item

    def test_display_flag_on_last_task_node(self):
        self.assertTrue(self.topnet.children["publish_final_cache"].display)

    def test_existing_nodes_are_reused(self):
        again = build_top_network(self.plan)
        self.assertEqual(again["topnet"], self.result["topnet"])
        self.assertEqual(len(self.topnet.children), len(self.plan.tasks))

    def test_node_type_failure_falls_back_to_null(self):
        module = fake_hou.create_fake_hou(fail_node_types={"ropfetch"})
        fake_hou.install(module)
        result = build_top_network(self.plan)
        topnet = module.obj.children["cfx_top_seq010_shot020"]
        self.assertEqual(topnet.children["sim_cache_char_main"].type().name(), "null")
        self.assertTrue(any("created null instead" in w for w in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
