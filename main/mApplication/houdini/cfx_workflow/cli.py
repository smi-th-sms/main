# -*- coding: utf-8 -*-
"""Command line entry points for CFX workflow planning."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .batch_runner import BatchRunner
from .config_loader import load_shot_config
from .validator import validate_shot_caches
from .workflow import build_workflow_plan


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan Houdini CFX shot workflow tasks.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Create a dynamic workflow plan.")
    plan_parser.add_argument("--config", required=True, help="Path to shot_config.json")
    plan_parser.add_argument("--output", help="Optional output JSON path")

    run_parser = subparsers.add_parser("dry-run", help="Create a dry-run batch report.")
    run_parser.add_argument("--config", required=True, help="Path to shot_config.json")
    run_parser.add_argument("--output", help="Optional report JSON path")

    validate_parser = subparsers.add_parser("validate", help="Validate written CFX caches.")
    validate_parser.add_argument("--config", required=True, help="Path to shot_config.json")
    validate_parser.add_argument("--output", help="Optional report JSON path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    shot = load_shot_config(args.config)
    plan = build_workflow_plan(shot)

    if args.command == "plan":
        payload = plan.as_dict()
        if args.output:
            output_path = plan.write_json(args.output)
            print(f"Wrote workflow plan: {output_path}")
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "dry-run":
        report = BatchRunner(mode="dry_run").run(plan)
        if args.output:
            output_path = report.write_json(Path(args.output))
            print(f"Wrote dry-run report: {output_path}")
        else:
            print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "validate":
        report = validate_shot_caches(shot)
        if args.output:
            output_path = report.write_json(Path(args.output))
            print(f"Wrote validation report: {output_path}")
        else:
            print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        print(f"Validation status: {report.status}")
        return 0 if report.status != "fail" else 1

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

