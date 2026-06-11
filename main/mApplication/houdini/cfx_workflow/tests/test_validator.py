# -*- coding: utf-8 -*-
"""Tests for cache validation."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from main.mApplication.houdini.cfx_workflow.schema import ShotConfig
from main.mApplication.houdini.cfx_workflow.validator import (
    collect_frame_files,
    split_frame_pattern,
    validate_asset_cache,
    validate_shot_caches,
)


def _shot(assets: list[dict]) -> ShotConfig:
    return ShotConfig.from_dict(
        {
            "show": "projectA",
            "sequence": "seq010",
            "shot": "shot020",
            "frame_start": 1001,
            "frame_end": 1010,
            "assets": assets,
        }
    )


def _asset(name: str, cache_path: str | None) -> dict:
    return {
        "name": name,
        "cfx_type": "cloth",
        "hda": "h",
        "preset": "p",
        "output_cache_path": cache_path,
    }


class FramePatternTest(unittest.TestCase):
    def test_supported_tokens(self):
        self.assertEqual(split_frame_pattern("a.$F4.bgeo.sc"), ("a.", ".bgeo.sc"))
        self.assertEqual(split_frame_pattern("a.$F.bgeo.sc"), ("a.", ".bgeo.sc"))
        self.assertEqual(split_frame_pattern("a.####.exr"), ("a.", ".exr"))
        self.assertEqual(split_frame_pattern("a.%04d.exr"), ("a.", ".exr"))

    def test_static_path_has_no_token(self):
        self.assertIsNone(split_frame_pattern("a.abc"))

    def test_collect_frame_files_requires_token(self):
        with self.assertRaises(ValueError):
            collect_frame_files("a.abc")


class ValidateShotCachesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cfx_validator_test_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _write_frames(self, directory: Path, name: str, frames, size: int = 5000):
        directory.mkdir(parents=True, exist_ok=True)
        for frame in frames:
            (directory / f"{name}.{frame:04d}.bgeo.sc").write_bytes(b"x" * size)

    def test_complete_cache_passes(self):
        good = self.tmp / "cloth"
        self._write_frames(good, "char_main", range(1001, 1011))
        report = validate_shot_caches(
            _shot([_asset("char_main", str(good / "char_main.$F4.bgeo.sc"))])
        )
        self.assertEqual(report.status, "pass")
        checks = {c.name: c.status for c in report.assets[0].checks}
        self.assertEqual(
            checks,
            {
                "cache_exists": "pass",
                "frame_range_coverage": "pass",
                "frame_sequence_continuity": "pass",
                "file_size_sanity": "pass",
            },
        )

    def test_collect_frame_files_maps_frames(self):
        good = self.tmp / "cloth"
        self._write_frames(good, "char_main", range(1001, 1011))
        frames = collect_frame_files(str(good / "char_main.$F4.bgeo.sc"))
        self.assertEqual(sorted(frames), list(range(1001, 1011)))

    def test_missing_cache_fails_with_single_check(self):
        report = validate_shot_caches(
            _shot([_asset("char_main", str(self.tmp / "missing" / "x.$F4.bgeo.sc"))])
        )
        asset = report.assets[0]
        self.assertEqual(asset.status, "fail")
        self.assertEqual([c.name for c in asset.checks], ["cache_exists"])

    def test_gaps_and_bad_sizes_are_reported(self):
        bad = self.tmp / "hair"
        # 1001 and 1005 missing, 1003 empty
        frames = [f for f in range(1002, 1011) if f != 1005]
        self._write_frames(bad, "char_hair", frames)
        (bad / "char_hair.1003.bgeo.sc").write_bytes(b"")
        report = validate_shot_caches(
            _shot([_asset("char_hair", str(bad / "char_hair.$F4.bgeo.sc"))])
        )
        checks = {c.name: c for c in report.assets[0].checks}
        self.assertEqual(checks["cache_exists"].status, "pass")
        self.assertEqual(checks["frame_range_coverage"].status, "fail")
        self.assertEqual(checks["frame_sequence_continuity"].status, "fail")
        self.assertEqual(
            sorted(checks["frame_sequence_continuity"].details["missing_frames"]),
            [1001, 1005],
        )
        self.assertEqual(checks["file_size_sanity"].status, "fail")
        self.assertEqual(checks["file_size_sanity"].details["empty_frames"], [1003])

    def test_small_files_warn(self):
        directory = self.tmp / "cloth"
        self._write_frames(directory, "char_main", range(1001, 1011))
        (directory / "char_main.1007.bgeo.sc").write_bytes(b"x" * 100)  # 2% of median
        report = validate_shot_caches(
            _shot([_asset("char_main", str(directory / "char_main.$F4.bgeo.sc"))])
        )
        checks = {c.name: c for c in report.assets[0].checks}
        self.assertEqual(checks["file_size_sanity"].status, "warning")
        self.assertEqual(checks["file_size_sanity"].details["small_frames"], [1007])
        self.assertEqual(report.status, "warning")

    def test_no_cache_path_fails(self):
        report = validate_shot_caches(_shot([_asset("char_main", None)]))
        self.assertEqual(report.assets[0].status, "fail")

    def test_static_file_checks(self):
        static = self.tmp / "char_main.abc"
        static.write_bytes(b"x" * 100)
        shot = _shot([_asset("char_main", str(static))])
        result = validate_asset_cache(shot, shot.assets[0])
        self.assertEqual(result.status, "pass")

        static.write_bytes(b"")
        result = validate_asset_cache(shot, shot.assets[0])
        checks = {c.name: c.status for c in result.checks}
        self.assertEqual(checks["file_size_sanity"], "fail")

    def test_report_as_dict(self):
        report = validate_shot_caches(_shot([_asset("char_main", None)]))
        payload = report.as_dict()
        self.assertEqual(payload["shot_id"], "projectA_seq010_shot020")
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(len(payload["assets"]), 1)


if __name__ == "__main__":
    unittest.main()
