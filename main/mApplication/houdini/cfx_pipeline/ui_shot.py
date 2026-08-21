# -*- coding: utf-8 -*-
"""Shot-setup node UI — the per-shot artist entry point (shelf tool).

The shot mirror of :mod:`ui_asset`: an OBJ subnet whose parameters ARE the
:class:`ShotSimConfig`. It drives :mod:`shot_builder` (import anim -> load the
asset rest caches -> align -> deform -> collision -> constraint -> solve ->
sim cache -> UE alembic). The character is NOT rebuilt here; the expensive
reusable setup was baked once at asset time and is loaded from disk.

The asset side of the handoff (proxy_parts / constraint params / rest-cache
paths) comes from the asset's ``cfx_asset.json`` on disk (or, when the asset is
built in the SAME hip, from its live control node as a fallback).

Shelf usage (one line)::

    import sys; sys.path.insert(0, r"E:\\script\\pythonWorkSpace")
    from main.mApplication.houdini.cfx_pipeline import ui_shot
    ui_shot.create_shot_tool()

The built shot network lands INSIDE this subnet as ``{asset}_shot_setup``.
"""

from __future__ import annotations

import json
import os
from typing import Any

from . import shot_builder as _shot
from .schema import ShotSimConfig

# import path used by the button callbacks (resolved at click time)
_MOD = "main.mApplication.houdini.cfx_pipeline.ui_shot"


# ---------------------------------------------------------------------------
# callback / menu script bodies (with DEV auto-reload, mirrors ui_asset)
# ---------------------------------------------------------------------------
def _cb(func: str) -> str:
    """Python button-callback robust to sys.path not being set yet.

    The callback deliberately does not purge ``cfx_pipeline`` from
    ``sys.modules``.  Purging the package while Houdini is inside a parameter
    callback creates a second copy of this module (and its callback guards),
    which can re-enter Build and produce ``Recursion in parm callback``.
    Source changes are picked up when the tool UI is rebuilt or the module is
    explicitly reloaded from the Python shell."""

    return (
        "import sys\n"
        "root = r'E:\\\\script\\\\pythonWorkSpace'\n"
        "sys.path.insert(0, root) if root not in sys.path else None\n"
        f"import {_MOD} as m\n"
        f"m.{func}(kwargs['node'])"
    )


def _menu_script(func: str) -> str:
    """Python item-generator body (Houdini runs it as a function -> ``return``
    the flat menu list [value, label, ...])."""

    return (
        "import sys\n"
        "r = r'E:\\\\script\\\\pythonWorkSpace'\n"
        "sys.path.insert(0, r) if r not in sys.path else None\n"
        f"import {_MOD} as _m\n"
        f"return _m.{func}(kwargs['node'])"
    )


# ---------------------------------------------------------------------------
# directory scanning for the show / sequence / shot / asset menus
# ---------------------------------------------------------------------------
def _scan(path: str) -> list[str]:
    """Flat menu list [value, label, ...] of sub-directory names under ``path``."""

    import os
    try:
        dirs = sorted(d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d)))
    except OSError:
        return []
    out: list[str] = []
    for d in dirs:
        out += [d, d]
    return out


def _scan_files(path: str, exts: tuple[str, ...]) -> list[str]:
    """Flat menu list [full_path, filename, ...] of files under ``path``."""

    import os
    try:
        names = sorted(f for f in os.listdir(path)
                       if os.path.isfile(os.path.join(path, f))
                       and f.lower().endswith(exts))
    except OSError:
        return []
    out: list[str] = []
    for f in names:
        out += [os.path.join(path, f).replace("\\", "/"), f]
    return out


def scan_shows(node) -> list[str]:
    return _scan(node.evalParm("project_root"))


def scan_sequences(node) -> list[str]:
    try:
        rules = _path_rules_for_node(node)
        return _scan(rules.resolve("sequences_dir", show=node.evalParm("show")))
    except Exception:
        return []


def scan_shots(node) -> list[str]:
    try:
        rules = _path_rules_for_node(node)
        return _scan(rules.resolve("sequence_dir", show=node.evalParm("show"),
                                   sequence=node.evalParm("sequence")))
    except Exception:
        return []


def scan_asset_types(node) -> list[str]:
    try:
        rules = _path_rules_for_node(node)
        return _scan(rules.resolve("asset_types_dir", show=node.evalParm("show")))
    except Exception:
        return []


def scan_assets(node) -> list[str]:
    try:
        rules = _path_rules_for_node(node)
        return _scan(rules.resolve(
            "asset_type_dir", show=node.evalParm("show"),
            asset_type=node.evalParm("asset_type") or "Character"))
    except Exception:
        return []


def scan_anim_fbx(node) -> list[str]:
    return _scan_files(_shot_dir(node, "shot_anim_dir"), (".fbx", ".bclip", ".abc"))


# ---------------------------------------------------------------------------
# path-rules helpers
# ---------------------------------------------------------------------------
def _path_rules_for_node(node):
    data = {
        "root": node.evalParm("project_root"),
        "context": {
            "asset_type": node.evalParm("asset_type") or "Character",
        },
    }
    if node.parm("path_profile") is not None and node.evalParm("path_profile"):
        data["profile_file"] = node.evalParm("path_profile")
    else:
        data["context"].update({
            "asset_subpath": "assets/%s"
                             % (node.evalParm("asset_type") or "Character"),
            "seq_subpath": "sequences",
        })
    from .path_rules import PipelinePathRules
    return PipelinePathRules.from_dict(data)


def _shot_path_rules(node):
    """Build ``(rules, show, sequence, shot, asset, atype)`` from the Config tab,
    or ``None`` when Project Root / Show are missing."""

    root = node.evalParm("project_root")
    show = node.evalParm("show")
    if not (root and show):
        return None
    atype = node.evalParm("asset_type") or "Character"
    rules = _path_rules_for_node(node)
    return (rules, show, node.evalParm("sequence"), node.evalParm("shot"),
            node.evalParm("asset"), atype)


def _shot_dir(node, template: str) -> str:
    """Resolve a shot sub-directory (e.g. ``shot_anim_dir``) from the current
    selection. Empty when the selection is incomplete."""

    info = _shot_path_rules(node)
    if info is None:
        return ""
    rules, show, seq, shot, asset, _atype = info
    if not (seq and shot):
        return ""
    try:
        return rules.resolve(template, show=show, sequence=seq, shot=shot, asset=asset)
    except Exception:
        return ""


def _shot_config_path_for(node) -> str:
    """The shot's config file path from the current selection, or empty."""

    info = _shot_path_rules(node)
    if info is None:
        return ""
    rules, show, seq, shot, asset, _atype = info
    if not (seq and shot):
        return ""
    try:
        return rules.resolve("shot_config", show=show, sequence=seq, shot=shot, asset=asset)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# asset rest-cache VERSION selection (which version the LOAD stage reads)
# ---------------------------------------------------------------------------
def _asset_version_dir(node) -> str:
    """The folder holding the asset proxy rest-cache ``v###`` subdirs (i.e. where
    versions live on disk), or "" when the selection is incomplete."""

    import os
    info = _shot_path_rules(node)
    if info is None:
        return ""
    rules, show, _seq, _shot, asset, _atype = info
    if not (show and asset):
        return ""
    try:  # .../geo/{asset}_proxy_rest/{version}/file -> .../{asset}_proxy_rest
        sample = rules.resolve("asset_proxy_cache", show=show, asset=asset, version="v001")
        return os.path.dirname(os.path.dirname(sample))
    except Exception:
        return ""


def _asset_version_status(node) -> dict[str, Any]:
    """Resolve the CHOSEN asset-cache version and how it compares to disk.

    Returns ``concrete`` (the v### actually used — 'latest' resolves to newest),
    ``latest`` (newest on disk or None), ``is_latest``, and ``existing`` (labels)."""

    from .path_rules import existing_versions
    info = _shot_path_rules(node)
    rules = info[0] if info else None
    vdir = _asset_version_dir(node)
    nums = existing_versions(vdir) if vdir else []

    def _fmt(n):
        return rules.format_version(n) if rules else "v%03d" % n

    latest = _fmt(nums[-1]) if nums else None
    sel = (node.evalParm("asset_version") or "latest").strip() if node.parm("asset_version") else "latest"
    if sel == "" or sel.lower().startswith("latest"):
        concrete, is_latest = (latest or "v001"), True
    else:
        try:
            concrete = rules.format_version(sel) if rules else sel
        except Exception:
            concrete = sel
        is_latest = (latest is not None and concrete == latest)
    return {"concrete": concrete, "latest": latest, "is_latest": is_latest,
            "existing": [_fmt(n) for n in nums]}


def scan_asset_versions(node) -> list[str]:
    """Menu: 'latest' + the asset rest-cache versions found on disk (newest first)."""

    out = ["latest", "latest (newest on disk)"]
    st = _asset_version_status(node)
    for lbl in reversed(st["existing"]):
        out += [lbl, lbl]
    return out


# ---------------------------------------------------------------------------
# parameter interface
# ---------------------------------------------------------------------------
def _build_interface(node) -> None:
    import hou

    g = node.parmTemplateGroup()
    for nm in ("cfx_config", "cfx_shot", "cfx_align", "cfx_sim", "cfx_cacheout",
               "cfx_actions"):
        existing = g.findFolder(nm) or g.find(nm)
        if existing:
            g.remove(existing)

    file_t = hou.stringParmType.FileReference

    def _menu(name, label, func, callback=None):
        kw = {}
        if callback:
            kw = dict(script_callback=_cb(callback),
                      script_callback_language=hou.scriptLanguage.Python)
        return hou.StringParmTemplate(
            name, label, 1, menu_items=(), menu_labels=(),
            item_generator_script=_menu_script(func),
            item_generator_script_language=hou.scriptLanguage.Python,
            menu_type=hou.menuType.StringReplace, **kw)

    def _btn(name, label, cb):
        return hou.ButtonParmTemplate(name, label, script_callback=_cb(cb),
                                      script_callback_language=hou.scriptLanguage.Python)

    # --- Config ---
    config = hou.FolderParmTemplate("cfx_config", "Config", folder_type=hou.folderType.Simple)
    config.addParmTemplate(hou.StringParmTemplate("project_root", "Project Root", 1,
                                                  default_value=("Z:/show",),
                                                  string_type=file_t,
                                                  file_type=hou.fileType.Directory))
    profile = hou.StringParmTemplate("path_profile", "Project Path Profile", 1,
                                     string_type=file_t)
    profile.setHelp("Optional show/studio path profile JSON. Local Config values "
                    "override the shared profile. If explicitly set, a missing "
                    "profile is treated as an error.")
    config.addParmTemplate(profile)
    config.addParmTemplate(_menu("show", "Show", "scan_shows"))
    config.addParmTemplate(_menu("sequence", "Sequence", "scan_sequences"))
    config.addParmTemplate(_menu("shot", "Shot", "scan_shots", callback="on_shot_changed"))
    config.addParmTemplate(_menu("asset_type", "Asset Type", "scan_asset_types"))
    config.addParmTemplate(_menu("asset", "Asset", "scan_assets", callback="on_shot_changed"))
    config.addParmTemplate(hou.StringParmTemplate("version", "Version", 1,
                                                  default_value=("v001",)))
    # Asset rest-cache version the LOAD stage reads (independent of the shot's
    # output Version). Menu scans the versions on disk; 'latest' = newest.
    av = _menu("asset_version", "Asset Cache Version", "scan_asset_versions",
               callback="on_asset_version_changed")
    av.setDefaultValue(("latest",))
    config.addParmTemplate(av)
    config.addParmTemplate(_btn("check_asset_version", "Check Asset Cache Version",
                                "on_check_asset_version"))
    # instantiate the published asset CONSTRAINT HDA (hand-authored setup) instead
    # of rebuilding the chain from config; falls back to the config rebuild if no
    # HDA is published for this asset.
    config.addParmTemplate(hou.ToggleParmTemplate("use_constraint_hda",
                                                  "Use Constraint HDA", default_value=True))
    config.addParmTemplate(hou.ToggleParmTemplate(
        "use_collision_hda", "Use Asset Collision HDA", default_value=True))
    config.addParmTemplate(hou.StringParmTemplate(
        "collision_input_pattern", "Collision Input Mesh Pattern", 1,
        default_value=("@name=body_mesh @name=head_lod0_mesh1",)))
    config.addParmTemplate(hou.ToggleParmTemplate(
        "use_deform_hda", "Use Asset Deform HDA", default_value=True))
    config.addParmTemplate(hou.StringParmTemplate("config_json", "Config File", 1,
                                                  string_type=file_t))
    config.addParmTemplate(_btn("update_path", "Update Config Path", "on_update_path"))
    config.addParmTemplate(_btn("load_cfg", "Load Config", "on_load_config"))
    config.addParmTemplate(_btn("save_cfg", "Save Config", "on_save_config"))

    # --- Shot (anim import + timeline) ---
    shot = hou.FolderParmTemplate("cfx_shot", "Shot", folder_type=hou.folderType.Simple)
    shot.addParmTemplate(_menu("animation_import", "Animation FBX", "scan_anim_fbx"))
    shot.addParmTemplate(hou.IntParmTemplate("frame_start", "Frame Start", 1,
                                             default_value=(1001,)))
    shot.addParmTemplate(hou.IntParmTemplate("frame_end", "Frame End", 1,
                                             default_value=(1100,)))
    shot.addParmTemplate(hou.IntParmTemplate("start_duration", "Pre-roll", 1,
                                             default_value=(0,)))
    shot.addParmTemplate(hou.IntParmTemplate("end_duration", "Post-roll", 1,
                                             default_value=(0,)))
    shot.addParmTemplate(hou.ToggleParmTemplate("t_pose_blend", "T-pose Blend (pre-roll)",
                                                default_value=False))
    shot.addParmTemplate(hou.ToggleParmTemplate("timeline_from_clip",
                                                "Timeline From Clip Range", default_value=False))
    shot.addParmTemplate(_btn("set_timeline", "Set Timeline", "on_set_timeline"))

    # --- Alignment (mirrors the studio FBX node's Load Name / T-Pose / Mult) ---
    align = hou.FolderParmTemplate("cfx_align", "Alignment", folder_type=hou.folderType.Collapsible)
    align.addParmTemplate(hou.StringParmTemplate("root_name", "Root Joint", 1,
                                                 default_value=("root",)))
    align.addParmTemplate(hou.StringParmTemplate("pelvis_name", "Pelvis Joint", 1,
                                                 default_value=("pelvis",)))
    align.addParmTemplate(hou.StringParmTemplate("head_name", "Head Joint", 1,
                                                 default_value=("head",)))
    align.addParmTemplate(hou.FloatParmTemplate("t_pose_start_position",
                                                "Align Start to T-pose", 1,
                                                default_value=(1.0,), min=0.0, max=1.0))
    align.addParmTemplate(hou.FloatParmTemplate("t_pos", "T-pose Amount", 1,
                                                default_value=(0.0,), min=0.0, max=1.0))
    # T-pose base offset (studio FBX Tpos_offset_transform): nudge the T-pose itself
    # — e.g. rotate the arms down toward A-pose — so the blend to the take needs less
    # rotation. Scaled by T-pose Amount, mirrors the ref FBX T_pos_ofs_translate/rotate.
    align.addParmTemplate(hou.FloatParmTemplate("t_pos_offset_translate",
                                                "T-pose Offset Translate", 3,
                                                default_value=(0.0, 0.0, 0.0)))
    align.addParmTemplate(hou.FloatParmTemplate("t_pos_offset_rotate",
                                                "T-pose Offset Rotate", 3,
                                                default_value=(0.0, 0.0, 0.0)))
    align.addParmTemplate(hou.FloatParmTemplate("position_mult", "Root Motion Mult", 3,
                                                default_value=(1.0, 1.0, 1.0),
                                                min=0.0, max=1.0))
    align.addParmTemplate(hou.FloatParmTemplate("rotate_mult", "Root Rotation Mult", 1,
                                                default_value=(1.0,), min=0.0, max=1.0))
    align.addParmTemplate(hou.FloatParmTemplate("pelvis_rotate", "Pelvis Rotate", 3,
                                                default_value=(0.0, 0.0, 0.0)))

    # --- Sim params (the only sim knobs a shot may touch) ---
    sim = hou.FolderParmTemplate("cfx_sim", "Sim Params", folder_type=hou.folderType.Simple)
    sim.addParmTemplate(hou.IntParmTemplate("substeps", "Substeps", 1, default_value=(1,)))
    sim.addParmTemplate(hou.IntParmTemplate(
        "constraint_iterations", "Constraint Iterations", 1,
        default_value=(_shot.SOLVER_TUNED_DEFAULTS["constraint_iterations"],)))
    sim.addParmTemplate(hou.FloatParmTemplate("collision_thickness", "Collision Thickness", 1,
                                              default_value=(0.001,)))
    sim.addParmTemplate(hou.IntParmTemplate("collision_iterations", "Collision Iterations", 1,
        default_value=(_shot.SOLVER_TUNED_DEFAULTS["collision_iterations"],)))
    sim.addParmTemplate(hou.IntParmTemplate(
        "post_collision_iterations", "Post Collision Iterations", 1,
        default_value=(
            _shot.SOLVER_TUNED_DEFAULTS["post_collision_iterations"],)))
    sim.addParmTemplate(hou.ToggleParmTemplate("push_apart", "Collision Push-apart",
                                               default_value=True))
    sim.addParmTemplate(hou.FloatParmTemplate("push_peak", "Push Peak", 1,
                                              default_value=(0.005,)))
    sim.addParmTemplate(hou.FloatParmTemplate("push_voxel", "Push Voxel", 1,
                                              default_value=(0.01,)))
    sim.addParmTemplate(hou.FloatParmTemplate("push_move", "Push Move", 1,
                                              default_value=(1.5,)))
    # --- Cache Out (UE alembic) ---
    co = hou.FolderParmTemplate("cfx_cacheout", "Cache Out", folder_type=hou.folderType.Simple)
    co.addParmTemplate(hou.ToggleParmTemplate("sim_filecache", "Write Sim Filecache",
                                              default_value=True))
    co.addParmTemplate(hou.ToggleParmTemplate("export_cloth", "Export Cloth Alembic",
                                              default_value=True))
    co.addParmTemplate(hou.ToggleParmTemplate("export_hair", "Export Hair Alembic",
                                              default_value=False))
    co.addParmTemplate(hou.StringParmTemplate(
        "hair_split_geo_path", "Hair Split geo_path", 1,
        default_value=("",),
        help="Optional primitive geo_path to extract from the cloth Deform "
             "output and export through the Hair Alembic branch."))
    co.addParmTemplate(hou.StringParmTemplate(
        "hair_uv_source", "Legacy Hair UV0 Source (Ignored)", 1,
        default_value=("",),
        help="Retained only for compatibility with older configs. Cache Out "
             "no longer swaps UV attributes. Choose the exported UV channels "
             "on the Hair Alembic ROP instead."))
    co.addParmTemplate(hou.IntParmTemplate(
        "cache_frame_padding", "Alembic End Frame Padding", 1,
        default_value=(5,), min=0, min_is_strict=True))
    co.addParmTemplate(hou.StringParmTemplate("cloth_attach_joint", "Cloth Attach Joint", 1,
                                              default_value=("pelvis",)))
    co.addParmTemplate(hou.FloatParmTemplate("ue_scale", "UE Scale (m->cm)", 1,
                                             default_value=(100.0,)))
    co.addParmTemplate(hou.FloatParmTemplate("ue_rotate", "UE Rotate (Y->Z up)", 3,
                                             default_value=(-90.0, 0.0, 0.0)))

    # --- Actions ---
    actions = hou.FolderParmTemplate("cfx_actions", "Build", folder_type=hou.folderType.Simple)
    actions.addParmTemplate(_btn("build_shot", "Build / Check Shot Setup", "on_build_shot"))
    actions.addParmTemplate(_btn("validate_shot", "Validate Shot Setup",
                                 "on_validate_setup"))
    actions.addParmTemplate(_btn("force_build_shot", "Force Rebuild Shot Setup",
                                 "on_force_rebuild_shot"))
    actions.addParmTemplate(_btn("reset_build_state", "Reset Build State",
                                 "on_reset_build_state"))
    actions.addParmTemplate(hou.MenuParmTemplate(
        "cache_execution_mode", "Cache Execution",
        menu_items=("foreground", "background"),
        menu_labels=("Foreground", "Background (hython)"),
        default_value=1))
    actions.addParmTemplate(hou.IntParmTemplate(
        "background_max_threads", "Background CPU Threads", 1,
        default_value=(max(1, (os.cpu_count() or 4) // 2),),
        min=1, min_is_strict=True))
    actions.addParmTemplate(hou.MenuParmTemplate(
        "background_process_priority", "Background Process Priority",
        menu_items=("low", "below_normal", "normal"),
        menu_labels=("Low", "Below Normal", "Normal"),
        default_value=1))
    actions.addParmTemplate(hou.FloatParmTemplate(
        "background_memory_limit_gb", "Background Memory Limit (GB)", 1,
        default_value=(0.0,), min=0.0, min_is_strict=True,
        help="0 disables the hard memory limit. A positive value can make "
             "the cache fail if hython exceeds the limit."))
    actions.addParmTemplate(hou.ToggleParmTemplate(
        "background_open_console", "Open Background Progress Console",
        default_value=True,
        help="Open an independent PowerShell status/log window that remains "
             "visible after Houdini is closed. Press C, then Y, to cancel "
             "the running hython cache."))
    actions.addParmTemplate(hou.IntParmTemplate(
        "background_console_hold_seconds",
        "Completed Console Hold (Seconds)", 1,
        default_value=(60,), min=0, min_is_strict=True,
        help="Seconds to keep the console open after completion. "
             "0 waits for Enter."))
    actions.addParmTemplate(_btn("write_sim_cache", "Write Sim Cache", "on_write_sim_cache"))
    actions.addParmTemplate(_btn("background_cache_status", "Background Cache Status",
                                 "on_background_cache_status"))
    actions.addParmTemplate(_btn("cancel_background_cache", "Cancel Background Cache",
                                 "on_cancel_background_cache"))
    actions.addParmTemplate(_btn(
        "prepare_cache_out", "Prepare Cache Out Nodes",
        "on_prepare_cache_out"))
    actions.addParmTemplate(_btn("cache_out", "Cache Out (Alembic)", "on_cache_out"))

    for folder in (config, shot, align, sim, co, actions):
        g.append(folder)
    node.setParmTemplateGroup(g)
    # Existing HIPs can retain the old menu value (Foreground) when the
    # parameter template is replaced.  Migrate once, then preserve subsequent
    # user choices on later interface rebuilds.
    if node.userData("cfx_cache_execution_default_v1") is None:
        mode = node.parm("cache_execution_mode")
        if mode is not None:
            mode.set(1)
        node.setUserData("cfx_cache_execution_default_v1", "background")
    # One-time migration from the former generic solver defaults to the
    # artist-approved vellum_solve tuning captured from the current shot.
    if node.userData("cfx_solver_defaults_v1") is None:
        for parm_name, key in (
                ("constraint_iterations", "constraint_iterations"),
                ("collision_iterations", "collision_iterations"),
                ("post_collision_iterations", "post_collision_iterations")):
            parm = node.parm(parm_name)
            if parm is not None:
                parm.set(int(_shot.SOLVER_TUNED_DEFAULTS[key]))
        node.setUserData("cfx_solver_defaults_v1", "applied")


def create_shot_tool(parent: str = "/obj", name: str = "cfx_shot"):
    """Shelf entry: make the shot-setup control subnet with its UI."""

    import hou
    root = hou.node(parent)
    if root is None:
        raise ValueError(f"parent not found: {parent}")
    node = root.node(name) or root.createNode("subnet", name)
    _build_interface(node)
    node.setComment("CFX Shot Setup — fill Config, set Timeline, then Build")
    node.setGenericFlag(hou.nodeFlag.DisplayComment, True)
    return node


# ---------------------------------------------------------------------------
# node <-> config bridge
# ---------------------------------------------------------------------------
def node_to_shot_config(node, version: str | None = None) -> ShotSimConfig:
    """Read the node into a :class:`ShotSimConfig`, resolving shot + asset-handoff
    paths from path_rules. ``version`` overrides the Version parm for this read."""

    ver = version or (node.evalParm("version") or "v001")
    fbx = {
        "asset_name": node.evalParm("asset"),
        "root_name": node.evalParm("root_name") or "root",
        "pelvis_name": node.evalParm("pelvis_name") or "pelvis",
        "head_name": node.evalParm("head_name") or "head",
        "t_pose_start_position": node.evalParm("t_pose_start_position"),
        "t_pos": node.evalParm("t_pos"),
        "t_pos_offset_translate": [node.evalParm("t_pos_offset_translatex"),
                                   node.evalParm("t_pos_offset_translatey"),
                                   node.evalParm("t_pos_offset_translatez")],
        "t_pos_offset_rotate": [node.evalParm("t_pos_offset_rotatex"),
                                node.evalParm("t_pos_offset_rotatey"),
                                node.evalParm("t_pos_offset_rotatez")],
        "position_mult": [node.evalParm("position_multx"), node.evalParm("position_multy"),
                          node.evalParm("position_multz")],
        "rotate_mult": node.evalParm("rotate_mult"),
        "pelvis_rotate": [node.evalParm("pelvis_rotatex"), node.evalParm("pelvis_rotatey"),
                          node.evalParm("pelvis_rotatez")],
    }
    sim_params = {
        "substeps": node.evalParm("substeps"),
        "constraint_iterations": node.evalParm("constraint_iterations"),
        "collision_thickness": node.evalParm("collision_thickness"),
        "collision_iterations": node.evalParm("collision_iterations"),
        "post_collision_iterations": node.evalParm(
            "post_collision_iterations"),
        "push_apart": bool(node.evalParm("push_apart")),
        "push_peak": node.evalParm("push_peak"),
        "push_voxel": node.evalParm("push_voxel"),
        "push_move": node.evalParm("push_move"),
    }
    cache_out = {
        "cloth_attach_joint": node.evalParm("cloth_attach_joint") or "pelvis",
        "ue_scale": node.evalParm("ue_scale"),
        "ue_rotate": [node.evalParm("ue_rotatex"), node.evalParm("ue_rotatey"),
                      node.evalParm("ue_rotatez")],
        "export_cloth": bool(node.evalParm("export_cloth")),
        "export_hair": bool(node.evalParm("export_hair")),
        "frame_padding": int(node.evalParm("cache_frame_padding")),
        "hair_split_geo_path": (
            node.evalParm("hair_split_geo_path")
            if node.parm("hair_split_geo_path") else ""),
        "hair_uv_source": (
            node.evalParm("hair_uv_source")
            if node.parm("hair_uv_source") else ""),
    }
    data: dict[str, Any] = {
        "show": node.evalParm("show"),
        "sequence": node.evalParm("sequence"),
        "shot": node.evalParm("shot"),
        "asset": node.evalParm("asset"),
        "frame_start": int(node.evalParm("frame_start")),
        "frame_end": int(node.evalParm("frame_end")),
        "animation_import": node.evalParm("animation_import") or None,
        "start_duration": int(node.evalParm("start_duration")),
        "end_duration": int(node.evalParm("end_duration")),
        "fbx": fbx,
        "t_pose_blend": bool(node.evalParm("t_pose_blend")),
        "sim_params": sim_params,
        "sim_filecache": bool(node.evalParm("sim_filecache")),
        "cloth_alembic": bool(node.evalParm("export_cloth")),
        "hair_alembic": bool(node.evalParm("export_hair")),
        "cache_out": cache_out,
        "metadata": {"version": ver},
    }
    info = _shot_path_rules(node)
    if info is not None:
        from .config_loader import resolve_shot_paths, _link_asset_caches
        rules, _show, _seq, _shot, _asset, _atype = info
        data = resolve_shot_paths(data, rules)
        # the asset's own resolved rest caches are authoritative for the handoff
        asset_cfg = _resolve_asset_config(node)
        if asset_cfg is not None:
            _link_asset_caches(data, asset_cfg)
        # the shot chooses WHICH asset rest-cache version LOAD reads: re-resolve the
        # handoff cache paths at that version (overrides the asset config's version).
        aver = _asset_version_status(node)["concrete"]
        data["metadata"]["asset_version"] = aver
        actx = dict(show=data["show"], asset=data["asset"], version=aver)
        for key in ("asset_proxy_cache", "asset_hair_cache", "asset_collision_cache",
                    "asset_corrective_cache", "asset_skel_cache", "asset_constraint_cache"):
            try:
                data[key] = rules.resolve(key, **actx)
            except Exception:
                pass
    return ShotSimConfig.from_dict(data)


def config_to_node(node, cfg: ShotSimConfig) -> None:
    """Push a :class:`ShotSimConfig` onto the node parameters."""

    node.parm("show").set(cfg.show)
    node.parm("sequence").set(cfg.sequence)
    node.parm("shot").set(cfg.shot)
    node.parm("asset").set(cfg.asset)
    node.parm("frame_start").set(cfg.frame_start)
    node.parm("frame_end").set(cfg.frame_end)
    if cfg.animation_import:
        node.parm("animation_import").set(cfg.animation_import)
    node.parm("start_duration").set(cfg.start_duration)
    node.parm("end_duration").set(cfg.end_duration)
    node.parm("t_pose_blend").set(int(cfg.t_pose_blend))
    f = cfg.fbx
    node.parm("root_name").set(f.root_name)
    node.parm("pelvis_name").set(f.pelvis_name)
    if node.parm("head_name"):
        node.parm("head_name").set(getattr(f, "head_name", "") or "head")
    node.parm("t_pose_start_position").set(f.t_pose_start_position)
    node.parm("t_pos").set(f.t_pos)
    if node.parmTuple("t_pos_offset_translate"):
        node.parmTuple("t_pos_offset_translate").set(tuple(f.t_pos_offset_translate))
    if node.parmTuple("t_pos_offset_rotate"):
        node.parmTuple("t_pos_offset_rotate").set(tuple(f.t_pos_offset_rotate))
    node.parmTuple("position_mult").set(tuple(f.position_mult))
    node.parm("rotate_mult").set(f.rotate_mult)
    node.parmTuple("pelvis_rotate").set(tuple(f.pelvis_rotate))
    sp = cfg.sim_params
    for pk, default in (
            ("substeps", 1),
            ("constraint_iterations",
             _shot.SOLVER_TUNED_DEFAULTS["constraint_iterations"]),
            ("collision_iterations",
             _shot.SOLVER_TUNED_DEFAULTS["collision_iterations"]),
            ("post_collision_iterations",
             _shot.SOLVER_TUNED_DEFAULTS["post_collision_iterations"])):
        if sp.get(pk) is not None:
            node.parm(pk).set(int(sp[pk]))
    if sp.get("collision_thickness") is not None:
        node.parm("collision_thickness").set(float(sp["collision_thickness"]))
    node.parm("push_apart").set(int(sp.get("push_apart", True)))
    for pk in ("push_peak", "push_voxel", "push_move"):
        if sp.get(pk) is not None:
            node.parm(pk).set(float(sp[pk]))
    node.parm("sim_filecache").set(int(cfg.sim_filecache))
    co = cfg.cache_out
    node.parm("export_cloth").set(int(co.export_cloth))
    node.parm("export_hair").set(int(co.export_hair))
    if node.parm("hair_split_geo_path"):
        node.parm("hair_split_geo_path").set(co.hair_split_geo_path)
    if node.parm("hair_uv_source"):
        node.parm("hair_uv_source").set(co.hair_uv_source)
    if node.parm("cache_frame_padding"):
        node.parm("cache_frame_padding").set(int(co.frame_padding))
    node.parm("cloth_attach_joint").set(co.cloth_attach_joint)
    node.parm("ue_scale").set(co.ue_scale)
    node.parmTuple("ue_rotate").set(tuple(co.ue_rotate))
    if cfg.metadata.get("version"):
        node.parm("version").set(str(cfg.metadata["version"]))


# ---------------------------------------------------------------------------
# asset-config resolution (the Asset->Shot handoff)
# ---------------------------------------------------------------------------
def _resolve_asset_config(node):
    """Load the referenced asset's :class:`AssetSetupConfig`.

    Primary: the asset's ``cfx_asset.json`` on disk (rules-derived path).
    Fallback (same-hip testing): a built asset control node whose ``asset``
    matches — read it via :func:`ui_asset.node_to_config`. Returns ``None`` when
    neither is available."""

    import os
    info = _shot_path_rules(node)
    if info is None:
        return None
    rules, show, _seq, _shot, asset, _atype = info
    if not asset:
        return None
    try:
        from .config_loader import asset_config_path, load_asset_config
        path = asset_config_path(show, asset, rules)
        if path and os.path.isfile(path):
            return load_asset_config(path)
    except Exception:
        pass
    # fallback: a live asset control node in this hip
    try:
        import hou
        from . import ui_asset
        for n in hou.node("/obj").allSubChildren():
            if n.parm("asset") is not None and n.parm("project_root") is not None \
                    and n.evalParm("asset") == asset and n.node("%s_asset_setup" % asset):
                return ui_asset.node_to_config(n)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# popup helper
# ---------------------------------------------------------------------------
def _popup(msg: str, severity: str = "message") -> None:
    """Show modeless feedback; never enter a nested Houdini modal loop."""

    from .ui_feedback import show_message
    show_message("CFX Shot Setup", msg, severity)


# ---------------------------------------------------------------------------
# button callbacks
# ---------------------------------------------------------------------------
_BUSY = False


def on_shot_changed(node) -> None:
    """Shot/Asset menu changed: recompute the config path + auto-load if present."""

    global _BUSY
    if _BUSY:
        return
    path = _shot_config_path_for(node)
    if not path:
        return
    node.parm("config_json").set(path)
    import os
    if os.path.isfile(path) and _config_shot(path) == node.evalParm("shot"):
        _BUSY = True
        try:
            _load_file(node, path)
            node.parm("config_json").set(path)
        except Exception as exc:
            _popup("Found a config but failed to load it:\n%s\n\n%s" % (path, exc),
                   "warning")
        finally:
            _BUSY = False


def _config_shot(path: str) -> str:
    try:
        data = json.loads(open(path, encoding="utf-8").read())
        block = data["shot"] if isinstance(data.get("shot"), dict) else data
        return str(block.get("shot", ""))
    except Exception:
        return ""


def _load_file(node, path: str) -> None:
    from pathlib import Path
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    block = data["shot"] if isinstance(data.get("shot"), dict) else data
    config_to_node(node, ShotSimConfig.from_dict(block))
    rules = data.get("path_rules") or block.get("path_rules") or {}
    if rules.get("root"):
        node.parm("project_root").set(rules["root"])
    if node.parm("path_profile") is not None:
        node.parm("path_profile").set(rules.get("profile_file") or "")


def on_update_path(node) -> None:
    global _BUSY
    path = _shot_config_path_for(node)
    if not path:
        _popup("Set Project Root / Show / Sequence / Shot first.", "warning")
        return
    node.parm("config_json").set(path)
    import os
    if os.path.isfile(path):
        _BUSY = True
        try:
            _load_file(node, path)
            node.parm("config_json").set(path)
            _popup("Config path updated and loaded:\n%s" % path)
        except Exception as exc:
            _popup("Config path set but load failed:\n%s\n\n%s" % (path, exc), "warning")
        finally:
            _BUSY = False
    else:
        _popup("Config path set (no file yet — Save Config to create):\n%s" % path)


def on_load_config(node) -> None:
    path = node.evalParm("config_json")
    if not path:
        _popup("Config File path is empty — set it first.", "warning")
        return
    import os
    if not os.path.isfile(path):
        _popup("No config file at:\n%s\n\nFill the parameters and Save Config to "
               "create it." % path, "warning")
        return
    try:
        _load_file(node, path)
    except Exception as exc:
        _popup("Load failed:\n%s\n\n%s" % (path, exc), "error")
        return
    _popup("Config loaded.\n\nShot: %s\nAsset: %s\n%s"
           % (node.evalParm("shot"), node.evalParm("asset"), path))


def on_save_config(node) -> None:
    """Write the node's parameters to the shot config JSON as a standalone config
    (with a ``path_rules`` block) so it loads via ``config_loader`` / workflow."""

    path = node.evalParm("config_json")
    if not path:
        _popup("Config File path is empty — set it first.", "warning")
        return
    try:
        from pathlib import Path
        data = node_to_shot_config(node).as_dict()
        profile_file = (node.evalParm("path_profile")
                        if node.parm("path_profile") is not None else "")
        path_context = {"asset_type": node.evalParm("asset_type") or "Character"}
        if not profile_file:
            path_context.update({
                "asset_subpath": "assets/%s" % path_context["asset_type"],
                "seq_subpath": "sequences",
            })
        data["path_rules"] = {
            "root": node.evalParm("project_root") or "Z:/show",
            "context": path_context,
        }
        if profile_file:
            data["path_rules"]["profile_file"] = profile_file
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        _popup("Save failed:\n%s\n\n%s" % (path, exc), "error")
        return
    _popup("Config saved.\n\nShot: %s\nAsset: %s\n%s"
           % (node.evalParm("shot"), node.evalParm("asset"), path))


def on_set_timeline(node) -> dict[str, Any]:
    """Set fps + playbar from the shot frame range (or the clip's native range)."""

    cfg = node_to_shot_config(node)
    from_clip = bool(node.evalParm("timeline_from_clip"))
    # from_clip needs the anim_take node to exist -> build_shot_setup first
    if (from_clip
            and node.node("%s_shot_setup/anim_take"
                          % node.evalParm("asset")) is None):
        try:
            _shot.build_shot_setup(cfg, node.path())
        except Exception as exc:
            _popup("Timeline (from clip) needs the anim take:\n%s" % exc, "warning")
            from_clip = False
    try:
        res = _shot.set_shot_timeline(cfg, apply=True, from_clip=from_clip,
                                      parent=node.path())
    except Exception as exc:
        _popup("Set timeline failed:\n%s" % exc, "error")
        raise
    _popup("Timeline set: %d - %d  (fps: %s)"
           % (res["frame_start"], res["frame_end"], res.get("fps") or "unchanged"))
    return res


def _sync_built_parameters(node, cfg: ShotSimConfig) -> dict[str, Any]:
    """Force the current UI snapshot onto the rebuilt animation/solver nodes.

    Builders already set these values, but this final pass makes the contract
    explicit and records exactly what the last successful Build applied.
    """

    import json

    geo = _shot_geo_node(node)
    if geo is None:
        raise RuntimeError(
            "%s_shot_setup was not created" % cfg.asset)

    take = geo.node("anim_take")
    if take is not None and take.parm("playbackstartframe"):
        take.parm("playbackstartframe").deleteAllKeyframes()
        take.parm("playbackstartframe").set(cfg.frame_start)

    # Re-apply the T-pose blend explicitly. This is the parameter the user most
    # often changes between builds, and it must replace the previous constant or
    # ramp expression rather than coexist with it.
    tpose_blend = geo.node("anim_tpose_blend")
    if tpose_blend is not None and tpose_blend.parm("weight1"):
        weight = tpose_blend.parm("weight1")
        weight.deleteAllKeyframes()
        anim_amount = 1.0 - float(cfg.fbx.t_pos)
        if cfg.t_pose_blend and cfg.start_duration > 0:
            pre_start = cfg.frame_start - cfg.start_duration
            weight.setExpression(
                "fit(clamp($FF,%d,%d),%d,%d,0,%s)"
                % (pre_start, cfg.frame_start, pre_start, cfg.frame_start,
                   anim_amount))
        else:
            weight.set(anim_amount)

    solver = geo.node("vellum_solve")
    sp = cfg.sim_params
    if solver is not None:
        values = (
            ("substeps", sp.get("substeps"), int),
            ("niter", sp.get(
                "constraint_iterations",
                _shot.SOLVER_TUNED_DEFAULTS["constraint_iterations"]), int),
            ("thickness", sp.get(
                "collision_thickness", sp.get("thickness")), float),
            ("collisionsiter", sp.get(
                "collision_iterations",
                _shot.SOLVER_TUNED_DEFAULTS["collision_iterations"]), int),
            ("postcollisioniter", sp.get(
                "post_collision_iterations",
                _shot.SOLVER_TUNED_DEFAULTS[
                    "post_collision_iterations"]), int),
        )
        start = solver.parm("startframe")
        if start is not None:
            start.deleteAllKeyframes()
            start.setExpression("$FSTART", __import__("hou").exprLanguage.Hscript)
        for parm_name, value, cast in values:
            parm = solver.parm(parm_name)
            if parm is not None and value is not None:
                parm.deleteAllKeyframes()
                parm.set(cast(value))
        for parm_name in (
                "windshadow_maskfalloff1pos",
                "windshadow_maskfalloff1value",
                "windshadow_maskfalloff2pos"):
            parm = solver.parm(parm_name)
            if parm is not None:
                parm.deleteAllKeyframes()
                parm.set(_shot.SOLVER_TUNED_DEFAULTS[parm_name])

    snapshot = {
        "frame_start": int(cfg.frame_start),
        "frame_end": int(cfg.frame_end),
        "start_duration": int(cfg.start_duration),
        "end_duration": int(cfg.end_duration),
        "animation_import": cfg.animation_import or "",
        "t_pose_blend": bool(cfg.t_pose_blend),
        "t_pos": float(cfg.fbx.t_pos),
        "collision_input_pattern": (
            node.evalParm("collision_input_pattern")
            if node.parm("collision_input_pattern") else ""),
        "sim_params": dict(sp),
    }
    geo.setUserData(
        "cfx_last_build_parameters",
        json.dumps(snapshot, sort_keys=True))
    return snapshot


_SHOT_REQUIRED_INTERFACES = (
    "anim_take", "REST_PROXY", "REST_CORRECTIVE", "REST_COLLISION",
    "REST_SKEL", "ANIM_SKEL", "ANIM_CORRECTIVE", "cage_deform",
    "OUT_SIM_COLLISION", "OUT_CONSTRAINT", "OUT_SIM",
)


def validate_setup(node) -> dict[str, Any]:
    """Inspect the shot contract without cooking or changing the HIP."""

    geo = _shot_geo_node(node)
    if geo is None:
        return {"state": "missing", "missing": list(_SHOT_REQUIRED_INTERFACES),
                "conflicts": [], "path": ""}
    missing = [name for name in _SHOT_REQUIRED_INTERFACES if geo.node(name) is None]
    conflicts = []
    for name in ("OUT_SIM_COLLISION", "OUT_CONSTRAINT", "OUT_SIM"):
        out = geo.node(name)
        if out is not None:
            inputs = out.inputs()
            if not inputs or inputs[0] is None:
                conflicts.append("%s is disconnected" % name)
    state = "valid" if not missing and not conflicts else "partial"
    return {"state": state, "missing": missing, "conflicts": conflicts,
            "path": geo.path()}


def on_validate_setup(node) -> dict[str, Any]:
    report = validate_setup(node)
    lines = ["Shot setup: %s" % report["state"].upper()]
    if report["path"]:
        lines.append(report["path"])
    if report["missing"]:
        lines.append("Missing interfaces: %s" % ", ".join(report["missing"]))
    if report["conflicts"]:
        lines.append("Conflicts:\n- " + "\n- ".join(report["conflicts"]))
    _popup("\n\n".join(lines), "message" if report["state"] == "valid" else "warning")
    return report


def _on_build_shot_impl(node, force: bool = False) -> dict[str, Any]:
    """Build the full shot setup: import anim -> load asset caches -> align ->
    deform -> collision -> constraint -> solve."""

    # Capture a fresh parameter snapshot for every click. Never reuse a config
    # loaded on a previous build.
    cfg = node_to_shot_config(node)
    p = node.path()
    report = validate_setup(node)
    if not force and report["state"] == "valid":
        return {"built": report["path"], "changed": False,
                "validation": report, "warnings": [
                    "Existing Shot setup is complete; no nodes or parameters were changed. "
                    "Use Force Rebuild for an explicit reset."]}
    if not force and report["state"] == "partial":
        detail = (["Missing interfaces: %s" % ", ".join(report["missing"])]
                  if report["missing"] else []) + report["conflicts"]
        raise RuntimeError(
            "Existing Shot setup is incomplete/conflicting; nothing was changed. "
            "Repair it manually or use Force Rebuild intentionally.\n- %s"
            % "\n- ".join(detail))

    # Preflight all external dependencies before creating or deleting scene
    # nodes. A missing Asset config must never leave a half-built scaffold.
    asset_cfg = _resolve_asset_config(node)
    if asset_cfg is None:
        raise RuntimeError(
            "Asset config for '%s' is required. Save cfx_asset.json (or keep "
            "the asset built in this HIP) before building the Shot setup."
            % cfg.asset)

    previous = _shot_geo_node(node)
    if force and previous is not None:
        previous.destroy()
    setup_result = _shot.build_shot_setup(cfg, p) or {}
    asset_hda_version = _asset_version_status(node)["concrete"]
    steps = [
        ("load_caches", lambda: _shot.load_asset_caches(cfg, p)),
        ("timeline", lambda: _shot.set_shot_timeline(
            cfg, apply=True, from_clip=bool(node.evalParm("timeline_from_clip")), parent=p)),
        ("anim", lambda: _shot.build_shot_anim(cfg, p)),
        ("deform", lambda: _shot.build_shot_deform(cfg, p)),
        ("collision", lambda: _shot.build_shot_collision(
            cfg, p,
            use_hda=bool(node.evalParm("use_collision_hda"))
            if node.parm("use_collision_hda") else True,
            hda_version=asset_hda_version,
            input_pattern=(node.evalParm("collision_input_pattern")
                           if node.parm("collision_input_pattern") else None))),
        ("constraint", lambda: _shot.build_shot_constraint(
            cfg, asset_cfg, p,
            use_hda=bool(node.evalParm("use_constraint_hda"))
            if node.parm("use_constraint_hda") else True,
            hda_version=asset_hda_version)),
        ("solve", lambda: _shot.build_shot_solve(cfg, p)),
    ]
    warnings: list[str] = [
        "[setup] %s" % warning
        for warning in (setup_result.get("warnings") or [])
    ]
    try:
        for name, fn in steps:
            res = fn() or {}
            warnings += ["[%s] %s" % (name, w) for w in (res.get("warnings") or [])]
    except Exception as exc:
        raise RuntimeError(
            "Build shot failed at '%s': %s" % (name, exc)) from exc
    applied_parameters = _sync_built_parameters(node, cfg)
    built = "%s/%s_shot_setup" % (p, cfg.asset)
    try:
        _organize(node)   # visual tidying must never invalidate a valid build
    except Exception as exc:
        warnings.append("[organize] %s" % exc)
    st = _asset_version_status(node)
    if not st["is_latest"]:
        warnings.insert(0, "asset cache version %s is NOT the latest (newest on disk: %s)"
                        % (st["concrete"], st["latest"] or "(none)"))
    msg = ("Shot setup built.\n\nShot: %s\nAsset: %s\nAsset cache version: %s%s\n%s"
           % (cfg.shot, cfg.asset, st["concrete"],
              "  (latest)" if st["is_latest"] else "  (NOT latest)", built))
    if warnings:
        msg += "\n\nWarnings:\n- " + "\n- ".join(warnings)
    print("[CFX BUILD] %s" % msg)
    return {
        "built": built,
        "changed": True,
        "forced": bool(force),
        "warnings": warnings,
        "applied_parameters": applied_parameters,
        "validation": validate_setup(node),
    }


_BUILD_LOCK_KEY = "cfx_build_shot_in_progress"


def _build_lock(node):
    import time

    try:
        value = node.cachedUserData(_BUILD_LOCK_KEY)
    except Exception:
        value = node.userData(_BUILD_LOCK_KEY)
    # Setup builds should finish quickly.  Never let a crashed/deleted deferred
    # callback leave the artist locked out indefinitely.
    if isinstance(value, dict):
        timestamp = float(value.get("timestamp") or 0.0)
        if not timestamp or time.time() - timestamp > 900.0:
            _set_build_lock(node, None)
            return None
    elif value:
        # Legacy string locks predate timestamped recovery and cannot prove that
        # a live build still owns them.
        _set_build_lock(node, None)
        return None
    return value


def _set_build_lock(node, value) -> None:
    if value is not None and not isinstance(value, dict):
        import time
        value = {"phase": str(value), "timestamp": time.time()}
    try:
        if value is None:
            node.destroyCachedUserData(_BUILD_LOCK_KEY, must_exist=False)
        else:
            node.setCachedUserData(_BUILD_LOCK_KEY, value)
    except Exception:
        if value is None:
            node.destroyUserData(_BUILD_LOCK_KEY, must_exist=False)
        else:
            node.setUserData(_BUILD_LOCK_KEY, str(value))


def _run_deferred_build(node_path: str, force: bool = False) -> None:
    """Run after the Build button's parm callback has completely returned."""

    import hou

    node = hou.node(node_path)
    if node is None:
        return
    _set_build_lock(node, "running")
    try:
        node.destroyUserData("cfx_last_build_error", must_exist=False)
        result = _on_build_shot_impl(node, force=force)
        node.setUserData(
            "cfx_last_build_result",
            __import__("json").dumps(result, sort_keys=True, default=str))
        try:
            hou.ui.setStatusMessage(
                "CFX Build Shot Setup completed.",
                severity=hou.severityType.Message)
        except Exception:
            pass
    except Exception as exc:
        import traceback
        detail = "%s: %s\n%s" % (
            type(exc).__name__, exc, traceback.format_exc())
        node.setUserData("cfx_last_build_error", detail)
        print("[CFX ERROR] Build Shot Setup failed:\n%s" % detail)
        try:
            hou.ui.setStatusMessage(
                "CFX Build Shot Setup failed. See cfx_last_build_error or "
                "the Python console.",
                severity=hou.severityType.Error)
        except Exception:
            pass
    finally:
        _set_build_lock(node, None)


def on_reset_build_state(node) -> dict[str, Any]:
    """Artist escape hatch for a stale Build guard; never touches scene nodes."""

    _set_build_lock(node, None)
    try:
        import hou
        hou.ui.setStatusMessage("CFX Build state reset.")
    except Exception:
        pass
    return {"reset": True}


def on_build_shot(node) -> dict[str, Any]:
    """Queue the heavy build outside the Build button's parm callback.

    Building directly inside a parameter callback can cause Houdini to re-enter
    the same callback while nodes, timeline, or viewer state are being updated,
    producing ``Recursion in parm callback``. A node-local lock also protects
    against double-clicks and survives this module's development reload.
    """

    if _build_lock(node):
        try:
            import hou
            hou.ui.setStatusMessage(
                "CFX Build Shot Setup is already queued/running.",
                severity=hou.severityType.Warning)
        except Exception:
            pass
        return {"busy": True}

    _set_build_lock(node, "queued")
    try:
        import hou
        if hou.isUIAvailable():
            import hdefereval
            node_path = node.path()
            hdefereval.executeDeferred(
                lambda: _run_deferred_build(node_path, force=False))
            hou.ui.setStatusMessage("CFX Build Shot Setup queued.")
            return {"queued": True, "node": node_path}
        result = _on_build_shot_impl(node, force=False)
        _set_build_lock(node, None)
        return result
    except Exception:
        _set_build_lock(node, None)
        raise


def on_force_rebuild_shot(node) -> dict[str, Any]:
    """Request non-modal confirmation before the destructive Shot rebuild."""

    import hou
    if hou.isUIAvailable():
        from .ui_feedback import ask_choice
        node_path = node.path()
        ask_choice(
            "Force Rebuild Shot Setup",
            "This replaces the complete Shot setup container and discards "
            "artist edits inside it. Cache files on disk are not deleted.",
            [("Force Rebuild", True), ("Cancel", False)],
            lambda confirmed: _queue_force_rebuild_shot(node_path)
            if confirmed else None)
        return {"prompted": True}
    return _queue_force_rebuild_shot(node.path())


def _queue_force_rebuild_shot(node_path: str) -> dict[str, Any]:
    import hou
    node = hou.node(node_path)
    if node is None:
        return {"cancelled": True, "error": "control node no longer exists"}

    if _build_lock(node):
        return {"busy": True}
    # Validate config/dependencies before even queuing a destructive operation.
    node_to_shot_config(node)
    if _resolve_asset_config(node) is None:
        _popup("Force Rebuild stopped: the Asset config is unavailable. Existing "
               "Shot nodes were not changed.", "error")
        return {"changed": False, "error": "asset config unavailable"}
    _set_build_lock(node, "queued_force")
    try:
        import hou
        if hou.isUIAvailable():
            import hdefereval
            node_path = node.path()
            hdefereval.executeDeferred(
                lambda: _run_deferred_build(node_path, force=True))
            hou.ui.setStatusMessage("CFX Force Rebuild Shot Setup queued.")
            return {"queued": True, "forced": True, "node": node_path}
        result = _on_build_shot_impl(node, force=True)
        _set_build_lock(node, None)
        return result
    except Exception:
        _set_build_lock(node, None)
        raise


def _apply_asset_version(node) -> dict[str, Any]:
    """Push the chosen asset-cache version onto the EXISTING ``load_*`` filecache
    nodes in the built LOAD stage, in place — no full rebuild. Existing files are
    repointed; a version whose file is missing is left unchanged (and reported), so
    a bad pick never repoints a working node at a non-existent file. Returns
    ``updated`` / ``missing`` / ``version``."""

    import os
    geo = _shot_geo_node(node)
    if geo is None:
        return {"updated": [], "missing": [], "version": None, "note": "not built"}
    cfg = node_to_shot_config(node)
    specs = [
        ("load_proxy", "REST_PROXY", cfg.asset_proxy_cache),
        ("load_corrective", "REST_CORRECTIVE", cfg.asset_corrective_cache),
        ("load_collision", "REST_COLLISION", cfg.asset_collision_cache),
        ("load_skel", "REST_SKEL", cfg.asset_skel_cache),
        ("load_hair", "REST_HAIR", cfg.asset_hair_cache),
    ]
    updated, missing = [], []
    for name, out_name, path in specs:
        nodes = [n for n in geo.allSubChildren()
                 if n.name() == name and "filecache" in n.type().name()]
        if path and os.path.isfile(path):
            for fc in nodes:
                if fc.parm("file"):
                    fc.parm("file").set(path)
            if nodes:
                updated.append((name, path))
        else:
            # this version's file is missing -> remove the load node + its REST_ null
            # so nothing points at a non-existent file (a rebuild re-adds it if the
            # cache later appears).
            for fc in nodes:
                fc.destroy()
            for rn in [n for n in geo.allSubChildren() if n.name() == out_name]:
                rn.destroy()
            if nodes:
                missing.append(name)
    return {"updated": updated, "missing": missing,
            "version": _asset_version_status(node)["concrete"]}


def on_asset_version_changed(node) -> None:
    """Asset Cache Version menu changed: repoint the built LOAD filecache nodes at
    the new version in place. Silent when the shot isn't built yet."""

    res = _apply_asset_version(node)
    if not res.get("updated") and not res.get("missing"):
        return   # nothing built yet — the next Build will use the chosen version
    parts = ["Asset cache version -> %s" % res["version"],
             "updated: %s" % (", ".join(n for n, _ in res["updated"]) or "(none)")]
    if res["missing"]:
        parts.append("MISSING (left unchanged): %s" % ", ".join(res["missing"]))
    _popup("\n".join(parts), "warning" if res["missing"] else "message")


def on_check_asset_version(node) -> dict[str, Any]:
    """Report the chosen asset rest-cache version, whether it's the newest on
    disk, and each REST_* cache's presence/staleness — without building."""

    import os
    st = _asset_version_status(node)
    cfg = node_to_shot_config(node)   # resolves the handoff caches at the chosen version
    specs = [
        ("load_proxy", "REST_PROXY", cfg.asset_proxy_cache),
        ("load_corrective", "REST_CORRECTIVE", cfg.asset_corrective_cache),
        ("load_collision", "REST_COLLISION", cfg.asset_collision_cache),
        ("load_skel", "REST_SKEL", cfg.asset_skel_cache),
        ("load_hair", "REST_HAIR", cfg.asset_hair_cache),
    ]
    stale = set()
    try:      # reuse the builder's MISSING/STALE guard
        for w in _shot._rest_cache_warnings(specs):
            stale.add(w.split(":", 1)[0])
    except Exception:
        pass
    lines = []
    for _n, out, pth in specs:
        if not pth:
            lines.append("%s: (no path)" % out)
        elif not os.path.isfile(pth):
            lines.append("%s: MISSING" % out)
        else:
            lines.append("%s: OK%s" % (out, "  (STALE?)" if out in stale else ""))
    head = ("Asset Cache Version: %s  %s\nExisting on disk: %s\n\n"
            % (st["concrete"], "✓ latest" if st["is_latest"]
               else "⚠ NOT latest — newest is %s" % (st["latest"] or "(none)"),
               ", ".join(st["existing"]) or "(none)"))
    _popup(head + "\n".join(lines),
           "message" if st["is_latest"] and not any("MISSING" in l for l in lines)
           else "warning")
    return {"version": st["concrete"], "is_latest": st["is_latest"]}


def _prompt_version(node, what: str, template: str,
                    callback=None) -> str | None:
    """Prompt for the output version, suggesting the next unused one based on the
    resolved ``template`` folder on disk. Returns a ``vNNN`` label or None."""

    import os
    info = _shot_path_rules(node)
    if info is None:
        _popup("Set Project Root / Show / Sequence / Shot first.", "warning")
        return None
    rules, show, seq, shot, asset, _atype = info
    from .path_rules import existing_versions, next_version
    try:
        sample = rules.resolve(template, show=show, sequence=seq, shot=shot,
                               asset=asset, version="v001")
    except Exception as exc:
        _popup("Could not resolve the %s path:\n%s" % (what, exc), "warning")
        return None
    vdir = os.path.dirname(os.path.dirname(sample))
    existing = existing_versions(vdir)
    suggested = rules.format_version(next_version(vdir))
    listed = ", ".join(rules.format_version(v) for v in existing) or "(none)"
    prompt = ("%s\n\nShot: %s\nExisting versions: %s\n\n"
              "Enter version to write (e.g. v003; existing = overwrite):"
              % (what, shot, listed))
    import hou
    if not hou.isUIAvailable():
        return suggested
    if callback is None:
        return None
    from .ui_feedback import ask_text

    def validate(value):
        if not value:
            callback(None)
            return
        try:
            callback(rules.format_version(str(value).strip()))
        except Exception:
            _popup("Invalid version: %r (use e.g. v003)" % value, "warning")

    ask_text(what, prompt, suggested, validate)
    return None


def on_write_sim_cache(node) -> dict[str, Any]:
    """Cache the solved sim per-frame to disk (Stage 3.6)."""

    import hou
    if hou.isUIAvailable():
        node_path = node.path()
        _prompt_version(
            node, "Write Sim Cache", "shot_sim_cache",
            callback=lambda version:
            _write_sim_cache_version(node_path, version))
        return {"prompted": True}
    return _write_sim_cache_version(
        node.path(),
        _prompt_version(node, "Write Sim Cache", "shot_sim_cache"))


def _write_sim_cache_version(node_path: str, version) -> dict[str, Any]:
    import hou
    node = hou.node(node_path)
    if node is None or version is None:
        return {"cancelled": True}
    if (node.parm("cache_execution_mode") is not None
            and node.evalParm("cache_execution_mode") == 1):
        from . import background_jobs
        try:
            previous = background_jobs.node_job_status(node)
            if previous.get("state") in ("queued", "running"):
                raise RuntimeError(
                    "A background cache job is already active: %s"
                    % previous.get("job_id"))
            # Persist the exact cache setup in the artist's HIP before hython
            # starts. The worker only executes this saved node.
            cfg = node_to_shot_config(node, version=version)
            setup = _shot.build_shot_cache(
                cfg, node.path(), execute=False)
            hou.hipFile.save()
            status = background_jobs.launch_job(node, "sim_cache", version=version)
        except Exception as exc:
            _popup("Background sim cache launch failed:\n%s" % exc, "error")
            raise
        background_jobs.show_progress_monitor(node)
        return {"background": True, "setup": setup, "status": status}

    cfg = node_to_shot_config(node, version=version)
    try:
        res = _shot.build_shot_cache(cfg, node.path(), execute=True)
    except Exception as exc:
        _popup("Sim cache write failed:\n%s" % exc, "error")
        raise
    if res.get("skipped"):
        _popup("Sim cache skipped: %s" % res["skipped"], "warning")
        return res
    _popup("Sim cache written (%s)\nframes %s\n%s"
           % (version, res.get("frame_range"), res.get("file")),
           "message" if res.get("written") else "warning")
    return res


def on_background_cache_status(node) -> dict[str, Any]:
    from . import background_jobs
    status = background_jobs.node_job_status(node)
    background_jobs.show_progress_monitor(node)
    return status


def on_cancel_background_cache(node) -> dict[str, Any]:
    from . import background_jobs
    status = background_jobs.cancel_node_job(node)
    _popup(background_jobs.format_status(status), "warning")
    return status


def on_cache_out(node) -> dict[str, Any]:
    """Render the prepared UE Alembic nodes without rebuilding the shot."""

    import hou
    if hou.isUIAvailable():
        node_path = node.path()
        _prompt_version(
            node, "Cache Out (Alembic)", "shot_cloth_abc",
            callback=lambda version:
            _cache_out_version(node_path, version))
        return {"prompted": True}
    return _cache_out_version(
        node.path(),
        _prompt_version(node, "Cache Out (Alembic)", "shot_cloth_abc"))


def on_prepare_cache_out(node) -> dict[str, Any]:
    """Create/update inspectable CACHEOUT SOPs and /out Alembic ROPs."""

    import hou
    if hou.isUIAvailable():
        node_path = node.path()
        _prompt_version(
            node, "Prepare Cache Out Nodes", "shot_cloth_abc",
            callback=lambda version:
            _prepare_cache_out_version(node_path, version))
        return {"prompted": True}
    return _prepare_cache_out_version(
        node.path(),
        _prompt_version(node, "Prepare Cache Out Nodes", "shot_cloth_abc"))


def _prepare_cache_out_version(node_path: str, version) -> dict[str, Any]:
    import hou
    node = hou.node(node_path)
    if node is None or version is None:
        return {"cancelled": True}
    cfg = node_to_shot_config(node, version=version)
    asset_cfg = _resolve_asset_config(node)
    if asset_cfg is None:
        raise RuntimeError(
            "Could not resolve the asset config for '%s'."
            % node.evalParm("asset"))
    result = _shot.build_shot_cacheout(
        cfg, asset_cfg, node.path(), execute=False,
        use_deform_hda=bool(node.evalParm("use_deform_hda"))
        if node.parm("use_deform_hda") else True)
    hou.hipFile.save()
    parts = [value["rop"] for key, value in result.items()
             if key in ("cloth", "hair") and value]
    _popup("Cache Out nodes prepared (%s)\n%s"
           % (version, "\n".join(parts) or "No exports enabled"))
    return result


def _cache_out_is_prepared(node, cfg) -> bool:
    import hou
    geo = node.node("%s_shot_setup" % cfg.asset)
    outnet = hou.node("/out")
    if geo is None or outnet is None:
        return False
    prefix = "cfx_%s_%s" % (
        "".join(c if c.isalnum() or c == "_" else "_" for c in cfg.shot),
        "".join(c if c.isalnum() or c == "_" else "_" for c in cfg.asset))
    if cfg.cache_out.export_cloth:
        if (geo.node("OUT_CLOTH") is None
                or outnet.node(prefix + "_Cloth_Cache") is None):
            return False
    if cfg.cache_out.export_hair:
        # Hair is optional; execute_prepared_shot_cacheout reports a skip when
        # the asset has no prepared hair branch.
        pass
    return True


def _cache_out_version(node_path: str, version) -> dict[str, Any]:
    import hou
    node = hou.node(node_path)
    if node is None or version is None:
        return {"cancelled": True}
    if (node.parm("cache_execution_mode") is not None
            and node.evalParm("cache_execution_mode") == 1):
        from . import background_jobs
        try:
            previous = background_jobs.node_job_status(node)
            if previous.get("state") in ("queued", "running"):
                raise RuntimeError(
                    "A background cache job is already active: %s"
                    % previous.get("job_id"))
            cfg = node_to_shot_config(node, version=version)
            if not _cache_out_is_prepared(node, cfg):
                setup = _prepare_cache_out_version(node_path, version)
            else:
                setup = {"reused_prepared_nodes": True}
            status = background_jobs.launch_job(
                node, "alembic_cache", version=version)
        except Exception as exc:
            _popup("Background Alembic cache launch failed:\n%s" % exc, "error")
            raise
        background_jobs.show_progress_monitor(node)
        return {"background": True, "setup": setup, "status": status}

    cfg = node_to_shot_config(node, version=version)
    try:
        if not _cache_out_is_prepared(node, cfg):
            _prepare_cache_out_version(node_path, version)
        res = _shot.execute_prepared_shot_cacheout(cfg, node.path())
    except Exception as exc:
        _popup("Cache out failed:\n%s" % exc, "error")
        raise
    parts = []
    if res.get("cloth"):
        parts.append("cloth -> %s" % res["cloth"].get("file"))
    if res.get("hair"):
        parts.append("hair -> %s" % res["hair"].get("file"))
    _popup("Cache out done (%s)\n\n%s" % (version, "\n".join(parts) or "(nothing exported)"))
    return res


# ---------------------------------------------------------------------------
# layout / stage-subnet organization
# ---------------------------------------------------------------------------
def _shot_geo_node(node):
    """The built shot container ``{asset}_shot_setup`` under the control node,
    or None if it hasn't been built yet."""

    return node.node("%s_shot_setup" % node.evalParm("asset"))


def _flatten(node) -> None:
    """Dissolve stage subnets back to flat (before an idempotent rebuild)."""

    geo = _shot_geo_node(node)
    if geo is not None:
        _shot.flatten_shot_stages(geo)
        leftovers = [
            name for name in ("LOAD", "ANIM", "COLLISION", "CONSTRAINT",
                              "SOLVE", "CACHEOUT")
            if geo.node(name) is not None
            and geo.node(name).type().name() == "subnet"
        ]
        if leftovers:
            raise RuntimeError(
                "Could not flatten existing Shot stages: %s"
                % ", ".join(leftovers))


def _organize(node) -> None:
    """Collapse the auto-built nodes into stage subnets and tidy the layout."""

    geo = _shot_geo_node(node)
    if geo is not None:
        _shot.organize_shot_stages(geo)
    _layout(node)


def _layout(node) -> None:
    try:
        geo = _shot_geo_node(node)
        if geo is not None:
            geo.layoutChildren()
        node.layoutChildren()
    except Exception:
        pass
