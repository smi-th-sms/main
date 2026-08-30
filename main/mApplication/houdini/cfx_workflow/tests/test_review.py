# -*- coding: utf-8 -*-
"""Tests for issue-aware fix action routing."""

from __future__ import annotations

import unittest

from main.mApplication.houdini.cfx_workflow.review import issue_frame_range, route_issue
from main.mApplication.houdini.cfx_workflow.schema import ReviewIssue, ShotConfig

SHOT = ShotConfig.from_dict(
    {
        "show": "projectA",
        "sequence": "seq010",
        "shot": "shot020",
        "frame_start": 1001,
        "frame_end": 1120,
        "assets": [
            {"name": "char_main", "cfx_type": "cloth", "hda": "h", "preset": "p"}
        ],
    }
)


def _issue(issue_type: str, frames=None, asset="char_main") -> ReviewIssue:
    return ReviewIssue(
        issue_type=issue_type, description="", asset=asset, frames=list(frames or [])
    )


class RouteIssueTest(unittest.TestCase):
    def test_penetration_with_frames_is_partial(self):
        action = route_issue(_issue("penetration", [1042, 1043, 1044]), SHOT)
        self.assertEqual(action.resim_scope, "partial")
        self.assertEqual(action.frame_range, (1032, 1054))
        self.assertEqual(action.target_asset, "char_main")
        parms = {entry["parm"]: entry for entry in action.parameter_patch}
        self.assertEqual(
            parms["collision_thickness"],
            {"parm": "collision_thickness", "op": "scale", "value": 1.5},
        )
        self.assertEqual(parms["substeps"], {"parm": "substeps", "op": "add", "value": 1})

    def test_frame_range_clamps_to_shot(self):
        action = route_issue(_issue("penetration", [1003, 1118]), SHOT)
        self.assertEqual(action.frame_range, (1001, 1120))

    def test_no_frames_falls_back_to_full(self):
        action = route_issue(_issue("penetration"), SHOT)
        self.assertEqual(action.resim_scope, "full")
        self.assertIsNone(action.frame_range)

    def test_unstable_sim_never_partial(self):
        action = route_issue(_issue("unstable_sim", [1050]), SHOT)
        self.assertEqual(action.resim_scope, "full")
        self.assertEqual(action.frame_range, (1040, 1060))  # still reported for context
        self.assertEqual(action.parameter_patch, [{"parm": "substeps", "op": "add", "value": 2}])

    def test_preview_only_needs_no_resim(self):
        action = route_issue(_issue("preview_only", [1010]), SHOT)
        self.assertEqual(action.resim_scope, "none")
        self.assertFalse(action.requires_resim)

    def test_hda_change_flags(self):
        action = route_issue(_issue("hda_change"), SHOT)
        self.assertTrue(action.requires_hda_update)
        self.assertTrue(action.requires_scene_rebuild)
        self.assertEqual(action.resim_scope, "full")

    def test_unknown_type_routes_to_manual_review(self):
        action = route_issue(_issue("something_new"), SHOT)
        self.assertEqual(action.action_type, "manual_review")
        self.assertEqual(action.resim_scope, "full")

    def test_custom_padding(self):
        action = route_issue(_issue("penetration", [1050]), SHOT, frame_padding=2)
        self.assertEqual(action.frame_range, (1048, 1052))

    def test_as_dict_is_json_friendly(self):
        data = route_issue(_issue("penetration", [1042]), SHOT).as_dict()
        self.assertEqual(data["frame_range"], [1032, 1052])
        self.assertEqual(data["resim_scope"], "partial")
        self.assertIsInstance(data["parameter_patch"], list)


class IssueFrameRangeTest(unittest.TestCase):
    def test_padding_without_shot_is_unclamped(self):
        self.assertEqual(issue_frame_range(_issue("penetration", [1003, 1118])), (993, 1128))

    def test_no_frames_returns_none(self):
        self.assertIsNone(issue_frame_range(_issue("penetration")))


if __name__ == "__main__":
    unittest.main()
