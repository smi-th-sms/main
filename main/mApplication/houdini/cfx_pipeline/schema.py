# -*- coding: utf-8 -*-
"""Two-tier config data model for the stage-based CFX pipeline.

* ``AssetSetupConfig`` — character-level, authored once and reused by every
  shot (Stage 2). Holds FBX import/T-pose, proxy parts, collision/constraint
  setup, and the rest-proxy cache location.
* ``ShotSimConfig`` — shot-level (Stage 3/4). References an asset by name,
  brings the animation FBX + duration, exposes only shot-adjustable sim
  parameters, and the UE cache-out settings.

Every gimmick catalogued in ``docs/CFX_ASSETS_HDA_ANALYSIS.md`` §4 maps onto a
field here so the stage HDAs can be driven entirely from config.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


# ---------------------------------------------------------------------------
# shared sub-configs
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FbxSetup:
    """FBX node parameters (Load Name / FBX Import / T Pose / Transform Mult)."""

    asset_name: str
    root_name: str = "root"
    pelvis_name: str = "pelvis"
    head_name: str = "head"
    character_import: str | None = None
    hair_import: str | None = None
    animation_import: str | None = None  # shot-only; None at asset setup time
    # Duration folder — offsets applied around the FBX clipinfo source range.
    start_duration: int = 0
    end_duration: int = 0
    # T Pose folder
    t_pose_start_position: float = 0.0
    t_pos: float = 0.0
    t_pos_offset_translate: tuple[float, float, float] = (0.0, 0.0, 0.0)
    t_pos_offset_rotate: tuple[float, float, float] = (0.0, 0.0, 0.0)
    # Transform Mult folder
    position_mult: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotate_mult: float = 0.0
    pelvis_rotate: tuple[float, float, float] = (0.0, 0.0, 0.0)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "FbxSetup":
        data = data or {}

        def vec3(key: str) -> tuple[float, float, float]:
            v = data.get(key, (0.0, 0.0, 0.0))
            return (float(v[0]), float(v[1]), float(v[2]))

        return cls(
            asset_name=str(data.get("asset_name", "")),
            root_name=str(data.get("root_name", "root")),
            pelvis_name=str(data.get("pelvis_name", "pelvis")),
            head_name=str(data.get("head_name", "head")),
            character_import=data.get("character_import"),
            hair_import=data.get("hair_import"),
            animation_import=data.get("animation_import"),
            start_duration=int(data.get("start_duration", 0)),
            end_duration=int(data.get("end_duration", 0)),
            t_pose_start_position=float(data.get("t_pose_start_position", 0.0)),
            t_pos=float(data.get("t_pos", 0.0)),
            t_pos_offset_translate=vec3("t_pos_offset_translate"),
            t_pos_offset_rotate=vec3("t_pos_offset_rotate"),
            position_mult=vec3("position_mult"),
            rotate_mult=float(data.get("rotate_mult", 0.0)),
            pelvis_rotate=vec3("pelvis_rotate"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "asset_name": self.asset_name,
            "root_name": self.root_name,
            "pelvis_name": self.pelvis_name,
            "head_name": self.head_name,
            "character_import": self.character_import,
            "hair_import": self.hair_import,
            "animation_import": self.animation_import,
            "start_duration": self.start_duration,
            "end_duration": self.end_duration,
            "t_pose_start_position": self.t_pose_start_position,
            "t_pos": self.t_pos,
            "t_pos_offset_translate": list(self.t_pos_offset_translate),
            "t_pos_offset_rotate": list(self.t_pos_offset_rotate),
            "position_mult": list(self.position_mult),
            "rotate_mult": self.rotate_mult,
            "pelvis_rotate": list(self.pelvis_rotate),
        }


@dataclass(frozen=True)
class ProxyPart:
    """One garment part driving the Proxy multifarm + Deform pairing.

    Authored interactively via the Proxy HDA's "Cloth Parts" multiparm
    (``part_name_#`` + ``delete_part_#``); config seeds and/or records the
    result rather than being the sole source of truth. See
    :func:`AssetSetupConfig.merge_parts` for the read-back merge.

    Split into two path families so the Deform stage can isolate one part's
    original geo and its matching proxy and ``pointDeform`` them per part
    (confirmed against the live HDA — ``Deform/Parts_Deform`` blasts by
    ``@proxy_path`` and ``@geo_path``):
      * ``geo_path``   — original geometry group path(s), selected from the
        Corrective output (the "기존 path"); a list so several can be combined.
      * ``proxy_path`` — the generated proxy group pattern (the "proxy path");
        defaults to a name-based ``*{name}*`` match when omitted.
    """

    name: str
    geo_path: list[str] = field(default_factory=list)
    proxy_path: str | None = None
    cloth: bool = True  # False => hair/rigid part
    parameters: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProxyPart":
        raw_geo = data.get("geo_path", [])
        geo_path = [raw_geo] if isinstance(raw_geo, str) else [str(g) for g in raw_geo]
        return cls(
            name=str(data["name"]),
            geo_path=geo_path,
            proxy_path=data.get("proxy_path"),
            cloth=bool(data.get("cloth", True)),
            parameters=dict(data.get("parameters", {})),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "geo_path": list(self.geo_path),
            "proxy_path": self.proxy_path,
            "cloth": self.cloth,
            "parameters": dict(self.parameters),
        }

    @property
    def proxy_group(self) -> str:
        """Blast group selecting this part's proxy (``@proxy_path=...``)."""

        return self.proxy_path or f"*{self.name}*"

    def geo_group(self) -> str:
        """Blast group selecting this part's original geo (``@geo_path=...``).

        Multiple ``geo_path`` entries are OR'd, matching how the HDA combines
        several geo groups into one part.
        """

        if not self.geo_path:
            return ""
        # Preserve a complete artist-authored group token instead of producing
        # ``@geo_path=@geo_path=...`` on a later rebuild.
        return " ".join(g if str(g).startswith("@") else "@geo_path=%s" % g
                        for g in self.geo_path)


@dataclass(frozen=True)
class CacheOutConfig:
    """Stage 4 export settings — the pelvis/head inverse gimmick + UE transform."""

    cloth_attach_joint: str = "pelvis"  # cloth baked in this joint's local space
    hair_attach_chain: tuple[str, ...] = (
        "head", "neck_02", "neck_01", "spine_05", "spine_04",
        "spine_03", "spine_02", "spine_01", "pelvis", "root",
    )
    ue_scale: float = 100.0  # m -> cm
    ue_rotate: tuple[float, float, float] = (-90.0, 0.0, 0.0)  # Y-up -> Z-up
    export_cloth: bool = True
    export_hair: bool = False
    frame_padding: int = 5
    # Optional post-process for Deform HDAs that return hair in their cloth
    # output. Empty values preserve the legacy builder behavior.
    hair_split_geo_path: str = ""
    hair_uv_source: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CacheOutConfig":
        data = data or {}
        chain = data.get("hair_attach_chain")
        rot = data.get("ue_rotate", (-90.0, 0.0, 0.0))
        return cls(
            cloth_attach_joint=str(data.get("cloth_attach_joint", "pelvis")),
            hair_attach_chain=tuple(chain) if chain else cls.__dataclass_fields__[
                "hair_attach_chain"
            ].default,
            ue_scale=float(data.get("ue_scale", 100.0)),
            ue_rotate=(float(rot[0]), float(rot[1]), float(rot[2])),
            export_cloth=bool(data.get("export_cloth", True)),
            export_hair=bool(data.get("export_hair", False)),
            frame_padding=max(0, int(data.get("frame_padding", 5))),
            hair_split_geo_path=str(data.get("hair_split_geo_path", "") or ""),
            hair_uv_source=str(data.get("hair_uv_source", "") or ""),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "cloth_attach_joint": self.cloth_attach_joint,
            "hair_attach_chain": list(self.hair_attach_chain),
            "ue_scale": self.ue_scale,
            "ue_rotate": list(self.ue_rotate),
            "export_cloth": self.export_cloth,
            "export_hair": self.export_hair,
            "frame_padding": self.frame_padding,
            "hair_split_geo_path": self.hair_split_geo_path,
            "hair_uv_source": self.hair_uv_source,
        }


# ---------------------------------------------------------------------------
# Stage 2 — asset (character) setup
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AssetSetupConfig:
    show: str
    asset: str
    asset_type: str = "Character"
    fbx: FbxSetup = field(default_factory=lambda: FbxSetup(asset_name=""))
    proxy_parts: list[ProxyPart] = field(default_factory=list)
    # geo_path pattern selecting the collision body (skin/head) — drives both
    # the Corrective BODY/CLOTH split and the Collision blast. Matches the
    # studio ``collision_pattern`` parm. HDA-authoritable (artist selects geo).
    collision_pattern: str = "@geo_path=*body* @geo_path=*head*"
    # uniform scale to align the hair guide alembic (Maya cm) to the character
    # (fbxcharacterimport meters). 0.01 = cm->m.
    hair_scale: float = 0.01
    # resim-independent setup params (collision thickness, vellum rest, etc.)
    collision: dict[str, Any] = field(default_factory=dict)
    constraint: dict[str, Any] = field(default_factory=dict)
    export_proxy_cache: bool = True
    # resolved paths (filled by config_loader from path_rules)
    character_fbx_dir: str | None = None
    hair_guide_dir: str | None = None
    asset_work: str | None = None
    proxy_cache_path: str | None = None
    hair_cache_path: str | None = None
    collision_cache_path: str | None = None
    corrective_cache_path: str | None = None
    skel_cache_path: str | None = None
    constraint_cache_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssetSetupConfig":
        return cls(
            show=str(data["show"]),
            asset=str(data["asset"]),
            asset_type=str(data.get("asset_type", "Character")),
            fbx=FbxSetup.from_dict(data.get("fbx")),
            proxy_parts=[ProxyPart.from_dict(p) for p in data.get("proxy_parts", [])],
            collision_pattern=str(data.get("collision_pattern", "@geo_path=*body* @geo_path=*head*")),
            hair_scale=float(data.get("hair_scale", 0.01)),
            collision=dict(data.get("collision", {})),
            constraint=dict(data.get("constraint", {})),
            export_proxy_cache=bool(data.get("export_proxy_cache", True)),
            character_fbx_dir=data.get("character_fbx_dir"),
            hair_guide_dir=data.get("hair_guide_dir"),
            asset_work=data.get("asset_work"),
            proxy_cache_path=data.get("proxy_cache_path"),
            hair_cache_path=data.get("hair_cache_path"),
            collision_cache_path=data.get("collision_cache_path"),
            corrective_cache_path=data.get("corrective_cache_path"),
            skel_cache_path=data.get("skel_cache_path"),
            constraint_cache_path=data.get("constraint_cache_path"),
            metadata=dict(data.get("metadata", {})),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "show": self.show,
            "asset": self.asset,
            "asset_type": self.asset_type,
            "fbx": self.fbx.as_dict(),
            "proxy_parts": [p.as_dict() for p in self.proxy_parts],
            "collision_pattern": self.collision_pattern,
            "hair_scale": self.hair_scale,
            "collision": dict(self.collision),
            "constraint": dict(self.constraint),
            "export_proxy_cache": self.export_proxy_cache,
            "character_fbx_dir": self.character_fbx_dir,
            "hair_guide_dir": self.hair_guide_dir,
            "asset_work": self.asset_work,
            "proxy_cache_path": self.proxy_cache_path,
            "hair_cache_path": self.hair_cache_path,
            "collision_cache_path": self.collision_cache_path,
            "corrective_cache_path": self.corrective_cache_path,
            "skel_cache_path": self.skel_cache_path,
            "constraint_cache_path": self.constraint_cache_path,
            "metadata": dict(self.metadata),
        }

    @property
    def cloth_parts(self) -> list[ProxyPart]:
        return [p for p in self.proxy_parts if p.cloth]

    def merge_parts(self, parts: list[dict[str, Any] | ProxyPart]) -> "AssetSetupConfig":
        """Return a copy with ``proxy_parts`` replaced by ``parts``.

        Supports the interactive flow: the artist adds/edits parts on the
        Proxy HDA multiparm in Houdini, the caller reads them back (as dicts
        or :class:`ProxyPart`), and this records them into config for reuse.
        """

        merged = [p if isinstance(p, ProxyPart) else ProxyPart.from_dict(p) for p in parts]
        return replace(self, proxy_parts=merged)


# ---------------------------------------------------------------------------
# Stage 3/4 — shot sim + cache out
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ShotSimConfig:
    show: str
    sequence: str
    shot: str
    asset: str  # references an AssetSetupConfig.asset
    frame_start: int
    frame_end: int
    animation_import: str | None = None
    # Duration folder: start_duration = pre-roll frames (settle before frame_start),
    # end_duration = post-roll. The sim starts at frame_start - start_duration.
    start_duration: int = 0
    end_duration: int = 0
    # Animation alignment (mirrors the studio FBX node's Load Name / T Pose /
    # Transform Mult folders — see anim_subnet1). Reuses :class:`FbxSetup`:
    #   root_name/pelvis_name, t_pose_start_position (align start to the T-pose
    #   pelvis vs keep native), t_pos + t_pos_offset_* (T-pose blend amount),
    #   position_mult (per-axis root-motion retention 0..1), rotate_mult,
    #   pelvis_rotate. animation_import above is the take.
    fbx: FbxSetup = field(default_factory=lambda: FbxSetup(asset_name=""))
    # blend the T-pose in over the pre-roll (ramps t_pos 1->0 across start_duration)
    t_pose_blend: bool = False
    # shot-only overrides for the incoming animation alignment
    transform_mult: dict[str, Any] = field(default_factory=dict)
    # the ONLY sim knobs a shot may touch (Stage 3 requirement)
    sim_params: dict[str, Any] = field(default_factory=dict)
    # cook toggles (mirror the HDA top-level toggles)
    sim_filecache: bool = True
    cloth_alembic: bool = True
    hair_alembic: bool = False
    cache_out: CacheOutConfig = field(default_factory=CacheOutConfig)
    # resolved paths
    shot_work: str | None = None
    shot_anim_dir: str | None = None
    sim_cache_path: str | None = None
    cloth_abc_path: str | None = None
    hair_abc_path: str | None = None
    # links to the asset's static rest caches (the Asset->Shot handoff, filled by
    # the loader). The shot loads and deforms these instead of rebuilding.
    asset_proxy_cache: str | None = None
    asset_hair_cache: str | None = None
    asset_collision_cache: str | None = None
    asset_corrective_cache: str | None = None
    asset_skel_cache: str | None = None
    asset_constraint_cache: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShotSimConfig":
        return cls(
            show=str(data["show"]),
            sequence=str(data["sequence"]),
            shot=str(data["shot"]),
            asset=str(data["asset"]),
            frame_start=int(data["frame_start"]),
            frame_end=int(data["frame_end"]),
            animation_import=data.get("animation_import"),
            start_duration=int(data.get("start_duration", 0)),
            end_duration=int(data.get("end_duration", 0)),
            fbx=FbxSetup.from_dict(data.get("fbx")),
            t_pose_blend=bool(data.get("t_pose_blend", False)),
            transform_mult=dict(data.get("transform_mult", {})),
            sim_params=dict(data.get("sim_params", {})),
            sim_filecache=bool(data.get("sim_filecache", True)),
            cloth_alembic=bool(data.get("cloth_alembic", True)),
            hair_alembic=bool(data.get("hair_alembic", False)),
            cache_out=CacheOutConfig.from_dict(data.get("cache_out")),
            shot_work=data.get("shot_work"),
            shot_anim_dir=data.get("shot_anim_dir"),
            sim_cache_path=data.get("sim_cache_path"),
            cloth_abc_path=data.get("cloth_abc_path"),
            hair_abc_path=data.get("hair_abc_path"),
            asset_proxy_cache=data.get("asset_proxy_cache"),
            asset_hair_cache=data.get("asset_hair_cache"),
            asset_collision_cache=data.get("asset_collision_cache"),
            asset_corrective_cache=data.get("asset_corrective_cache"),
            asset_skel_cache=data.get("asset_skel_cache"),
            asset_constraint_cache=data.get("asset_constraint_cache"),
            metadata=dict(data.get("metadata", {})),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "show": self.show,
            "sequence": self.sequence,
            "shot": self.shot,
            "asset": self.asset,
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
            "animation_import": self.animation_import,
            "start_duration": self.start_duration,
            "end_duration": self.end_duration,
            "fbx": self.fbx.as_dict(),
            "t_pose_blend": self.t_pose_blend,
            "transform_mult": dict(self.transform_mult),
            "sim_params": dict(self.sim_params),
            "sim_filecache": self.sim_filecache,
            "cloth_alembic": self.cloth_alembic,
            "hair_alembic": self.hair_alembic,
            "cache_out": self.cache_out.as_dict(),
            "shot_work": self.shot_work,
            "shot_anim_dir": self.shot_anim_dir,
            "sim_cache_path": self.sim_cache_path,
            "cloth_abc_path": self.cloth_abc_path,
            "hair_abc_path": self.hair_abc_path,
            "asset_proxy_cache": self.asset_proxy_cache,
            "asset_hair_cache": self.asset_hair_cache,
            "asset_collision_cache": self.asset_collision_cache,
            "asset_corrective_cache": self.asset_corrective_cache,
            "asset_skel_cache": self.asset_skel_cache,
            "asset_constraint_cache": self.asset_constraint_cache,
            "metadata": dict(self.metadata),
        }

    @property
    def shot_id(self) -> str:
        return f"{self.show}_{self.sequence}_{self.shot}"

    @property
    def frame_range(self) -> tuple[int, int]:
        return self.frame_start, self.frame_end
