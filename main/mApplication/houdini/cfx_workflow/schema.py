# -*- coding: utf-8 -*-
"""Data objects shared by the Houdini CFX workflow package."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class WorkflowStage(str, Enum):
    HDA_CHECK = "hda_check"
    HDA_PUBLISH = "hda_publish"
    SHOT_SETUP = "shot_setup"
    SIM_CACHE = "sim_cache"
    VALIDATE = "validate"
    PREVIEW = "preview"
    REVIEW = "review"
    FIX = "fix"
    PUBLISH = "publish"


@dataclass(frozen=True)
class AssetConfig:
    name: str
    cfx_type: str
    hda: str
    preset: str
    quality: str = "final"
    input_cache_path: str | None = None
    output_cache_path: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssetConfig":
        return cls(
            name=str(data["name"]),
            cfx_type=str(data["cfx_type"]),
            hda=str(data["hda"]),
            preset=str(data["preset"]),
            quality=str(data.get("quality", "final")),
            input_cache_path=data.get("input_cache_path"),
            output_cache_path=data.get("output_cache_path"),
            parameters=dict(data.get("parameters", {})),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "cfx_type": self.cfx_type,
            "hda": self.hda,
            "preset": self.preset,
            "quality": self.quality,
            "input_cache_path": self.input_cache_path,
            "output_cache_path": self.output_cache_path,
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True)
class BatchConfig:
    force_resim: bool = False
    generate_preview: bool = True
    validate_cache: bool = True
    publish_on_approved: bool = False
    frame_chunk: int = 50
    mode: str = "local"

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "BatchConfig":
        data = data or {}
        return cls(
            force_resim=bool(data.get("force_resim", False)),
            generate_preview=bool(data.get("generate_preview", True)),
            validate_cache=bool(data.get("validate_cache", True)),
            publish_on_approved=bool(data.get("publish_on_approved", False)),
            frame_chunk=int(data.get("frame_chunk", 50)),
            mode=str(data.get("mode", "local")),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "force_resim": self.force_resim,
            "generate_preview": self.generate_preview,
            "validate_cache": self.validate_cache,
            "publish_on_approved": self.publish_on_approved,
            "frame_chunk": self.frame_chunk,
            "mode": self.mode,
        }


@dataclass(frozen=True)
class ReviewIssue:
    issue_type: str
    description: str
    asset: str | None = None
    frames: list[int] = field(default_factory=list)
    severity: str = "medium"
    status: str = "open"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewIssue":
        return cls(
            issue_type=str(data["issue_type"]),
            description=str(data.get("description", "")),
            asset=data.get("asset"),
            frames=[int(frame) for frame in data.get("frames", [])],
            severity=str(data.get("severity", "medium")),
            status=str(data.get("status", "open")),
            metadata=dict(data.get("metadata", {})),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "issue_type": self.issue_type,
            "description": self.description,
            "asset": self.asset,
            "frames": list(self.frames),
            "severity": self.severity,
            "status": self.status,
            "metadata": dict(self.metadata),
        }

    @property
    def is_open(self) -> bool:
        return self.status.lower() not in {"approved", "closed", "done", "resolved"}


@dataclass(frozen=True)
class ShotConfig:
    show: str
    sequence: str
    shot: str
    frame_start: int
    frame_end: int
    assets: list[AssetConfig]
    department: str = "cfx"
    work_dir: str | None = None
    scene_template: str | None = None
    shot_scene_path: str | None = None
    review_dir: str | None = None
    batch: BatchConfig = field(default_factory=BatchConfig)
    review_issues: list[ReviewIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShotConfig":
        return cls(
            show=str(data["show"]),
            sequence=str(data["sequence"]),
            shot=str(data["shot"]),
            department=str(data.get("department", "cfx")),
            frame_start=int(data["frame_start"]),
            frame_end=int(data["frame_end"]),
            assets=[AssetConfig.from_dict(item) for item in data.get("assets", [])],
            work_dir=data.get("work_dir"),
            scene_template=data.get("scene_template"),
            shot_scene_path=data.get("shot_scene_path"),
            review_dir=data.get("review_dir"),
            batch=BatchConfig.from_dict(data.get("batch")),
            review_issues=[ReviewIssue.from_dict(item) for item in data.get("review_issues", [])],
            metadata=dict(data.get("metadata", {})),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "show": self.show,
            "sequence": self.sequence,
            "shot": self.shot,
            "department": self.department,
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
            "assets": [asset.as_dict() for asset in self.assets],
            "work_dir": self.work_dir,
            "scene_template": self.scene_template,
            "shot_scene_path": self.shot_scene_path,
            "review_dir": self.review_dir,
            "batch": self.batch.as_dict(),
            "review_issues": [issue.as_dict() for issue in self.review_issues],
            "metadata": dict(self.metadata),
        }

    @property
    def shot_id(self) -> str:
        return f"{self.show}_{self.sequence}_{self.shot}"

    @property
    def frame_range(self) -> tuple[int, int]:
        return self.frame_start, self.frame_end


@dataclass
class WorkflowTask:
    task_id: str
    stage: WorkflowStage
    label: str
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"
    command: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowTask":
        return cls(
            task_id=str(data["task_id"]),
            stage=WorkflowStage(data["stage"]),
            label=str(data.get("label", "")),
            depends_on=list(data.get("depends_on", [])),
            status=str(data.get("status", "pending")),
            command=data.get("command"),
            metadata=dict(data.get("metadata", {})),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "stage": self.stage.value,
            "label": self.label,
            "depends_on": list(self.depends_on),
            "status": self.status,
            "command": self.command,
            "metadata": dict(self.metadata),
        }


@dataclass
class WorkflowPlan:
    shot: ShotConfig
    tasks: list[WorkflowTask]

    def as_dict(self) -> dict[str, Any]:
        return {
            "shot_id": self.shot.shot_id,
            "show": self.shot.show,
            "sequence": self.shot.sequence,
            "shot": self.shot.shot,
            "frame_start": self.shot.frame_start,
            "frame_end": self.shot.frame_end,
            "tasks": [task.as_dict() for task in self.tasks],
        }

    def write_json(self, path: str | Path) -> Path:
        import json

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.as_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path

