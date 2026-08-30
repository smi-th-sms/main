# -*- coding: utf-8 -*-
"""Small execution/reporting layer for CFX workflow plans."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .schema import WorkflowPlan


@dataclass
class BatchReport:
    shot_id: str
    mode: str
    generated_at: str
    tasks: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "shot_id": self.shot_id,
            "mode": self.mode,
            "generated_at": self.generated_at,
            "tasks": self.tasks,
        }

    def write_json(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.as_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path


class BatchRunner:
    """Dry-run runner for workflow plans.

    The first scaffold intentionally records what would run instead of calling
    Houdini hython/farm commands. That keeps the workflow inspectable while the
    HDA and TOPs pieces are still being designed.
    """

    def __init__(self, mode: str = "dry_run") -> None:
        self.mode = mode

    def run(self, plan: WorkflowPlan) -> BatchReport:
        report_tasks: list[dict[str, Any]] = []
        for task in plan.tasks:
            status = task.status
            if status == "pending" and self.mode == "dry_run":
                status = "planned"
            report_tasks.append(
                {
                    **task.as_dict(),
                    "result": {
                        "mode": self.mode,
                        "message": "Task planned; no external Houdini process executed.",
                    },
                    "status": status,
                }
            )

        return BatchReport(
            shot_id=plan.shot.shot_id,
            mode=self.mode,
            generated_at=datetime.now().isoformat(timespec="seconds"),
            tasks=report_tasks,
        )

