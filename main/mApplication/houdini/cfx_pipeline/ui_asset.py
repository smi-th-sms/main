# -*- coding: utf-8 -*-
"""Asset-setup node UI — the artist entry point (shelf tool).

Creates an OBJ subnet carrying a CFX-Assets-Manager-style parameter interface
(Config / FBX import / Cloth&Hair Parts multiparm / stage params + buttons) and
drives :mod:`asset_builder` from those parameters. The node's parameters ARE the
config: :func:`node_to_config` reads them into an :class:`AssetSetupConfig`
(``Save/Load Config`` sync a JSON on disk). Built as subnet + spare parms +
Python callbacks first; can be promoted to an HDA once stable.

Shelf usage (one line)::

    import sys; sys.path.insert(0, r"E:\\script\\pythonWorkSpace")
    from main.mApplication.houdini.cfx_pipeline import ui_asset
    ui_asset.create_asset_tool()

The build/cache/load/save buttons call the ``on_*`` functions here with the
clicked node. The built asset network lands INSIDE this subnet as
``{asset}_asset_setup`` (so ``parent`` = this node's path).
"""

from __future__ import annotations

import json
from typing import Any

from . import asset_builder as _asset
from .schema import AssetSetupConfig

# import path used by the button callbacks (resolved at click time)
_MOD = "main.mApplication.houdini.cfx_pipeline.ui_asset"


def _cb(func: str) -> str:
    """Python button-callback that is robust to sys.path not being set yet.

    Do not purge ``cfx_pipeline`` while Houdini is executing a parameter
    callback.  Re-importing the package mid-callback duplicates module globals
    and callback guards and can cause recursive button execution."""

    return (
        "import sys\n"
        "root = r'E:\\\\script\\\\pythonWorkSpace'\n"
        "sys.path.insert(0, root) if root not in sys.path else None\n"
        f"import {_MOD} as m\n"
        f"m.{func}(kwargs['node'])"
    )


# ---------------------------------------------------------------------------
# directory scanning for the show / asset_type / asset menus
# (mirrors the CFX Assets Manager: {root}/{show}/assets/{asset_type}/{asset})
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


def scan_shows(node) -> list[str]:
    return _scan(node.evalParm("project_root"))


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


def _control_node(node):
    """Walk up to the CFX control node (the one carrying ``project_root``) so
    scans work whether called from the control node or a descendant subnet."""

    n = node
    while n is not None:
        if n.parm("project_root") is not None:
            return n
        n = n.parent()
    return node


def _path_rules_for_node(node):
    """Return the selected project profile plus local UI overrides."""

    node = _control_node(node)
    data = {
        "root": node.evalParm("project_root"),
        "context": {
            "asset_type": node.evalParm("asset_type") or "Character",
        },
    }
    if node.parm("path_profile") is not None and node.evalParm("path_profile"):
        data["profile_file"] = node.evalParm("path_profile")
    else:
        data["context"]["asset_subpath"] = (
            "assets/%s" % (node.evalParm("asset_type") or "Character"))
    from .path_rules import PipelinePathRules
    return PipelinePathRules.from_dict(data)


def _asset_dir(node, template: str) -> str:
    """Resolve an asset sub-directory (e.g. ``character_fbx_dir``) from the
    current selection via ``path_rules``. Empty when selection is incomplete."""

    node = _control_node(node)
    root = node.evalParm("project_root")
    show = node.evalParm("show")
    atype = node.evalParm("asset_type") or "Character"
    asset = node.evalParm("asset")
    if not (root and show and asset):
        return ""
    rules = _path_rules_for_node(node)
    return rules.resolve(template, show=show, asset=asset)


def _scan_files(path: str, exts: tuple[str, ...]) -> list[str]:
    """Flat menu list [full_path, filename, ...] of files under ``path`` whose
    name ends with one of ``exts`` (full path = value, filename = label)."""

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


def scan_char_fbx(node) -> list[str]:
    return _scan_files(_asset_dir(node, "character_fbx_dir"), (".fbx",))


def scan_hair_guide(node) -> list[str]:
    return _scan_files(_asset_dir(node, "hair_guide_dir"),
                       (".abc", ".fbx", ".bgeo", ".bgeo.sc", ".obj", ".vdb"))


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
# parameter interface
# ---------------------------------------------------------------------------
def _build_interface(node) -> None:
    import hou

    g = node.parmTemplateGroup()
    # wipe any stale CFX folders so re-running the tool is idempotent
    for nm in ("cfx_config", "cfx_fbx", "cfx_parts", "cfx_stage", "cfx_actions"):
        existing = g.findFolder(nm) or g.find(nm)
        if existing:
            g.remove(existing)

    file_t = hou.stringParmType.FileReference

    # --- Config --- (show / asset_type / asset are scanned from the project root)
    def _menu(name, label, func, callback=None, string_type=None, file_type=None):
        kw = {}
        if callback:
            kw = dict(script_callback=_cb(callback),
                      script_callback_language=hou.scriptLanguage.Python)
        if string_type is not None:
            kw["string_type"] = string_type   # e.g. FileReference -> keeps a browse button
        if file_type is not None:
            kw["file_type"] = file_type
        return hou.StringParmTemplate(
            name, label, 1, menu_items=(), menu_labels=(),
            item_generator_script=_menu_script(func),
            item_generator_script_language=hou.scriptLanguage.Python,
            menu_type=hou.menuType.StringReplace, **kw)  # editable string + scanned menu

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
    config.addParmTemplate(_menu("asset_type", "Asset Type", "scan_asset_types",
                                 callback="on_asset_changed"))
    # picking an asset resolves its config file (auto-load if it exists)
    config.addParmTemplate(_menu("asset", "Asset", "scan_assets",
                                 callback="on_asset_changed"))
    config.addParmTemplate(hou.StringParmTemplate("config_json", "Config File", 1,
                                                  string_type=file_t))
    config.addParmTemplate(hou.ButtonParmTemplate("update_path", "Update Config Path",
                                                  script_callback=_cb("on_update_path"),
                                                  script_callback_language=hou.scriptLanguage.Python))
    config.addParmTemplate(hou.ButtonParmTemplate("load_cfg", "Load Config",
                                                  script_callback=_cb("on_load_config"),
                                                  script_callback_language=hou.scriptLanguage.Python))
    config.addParmTemplate(hou.ButtonParmTemplate("save_cfg", "Save Config",
                                                  script_callback=_cb("on_save_config"),
                                                  script_callback_language=hou.scriptLanguage.Python))

    # NOTE: FBX / Hair parameters (character_import, hair_import, root/pelvis,
    # hair_scale) live on the built FBX subnet (source of truth), not here.
    # Cloth/Hair Parts likewise live on the built PROXY subnet — the artist adds
    # and classifies (cloth vs hair) parts there directly.

    # NOTE: Collision params (body pattern + voxel ratio) live on the built
    # COLLISION subnet (source of truth). Cloth stiffness is authored per part
    # (on each vellumconstraints node), not globally.

    # --- actions ---
    actions = hou.FolderParmTemplate("cfx_actions", "Build", folder_type=hou.folderType.Simple)
    actions.addParmTemplate(hou.ButtonParmTemplate("build_asset", "Build / Check Asset Setup",
                                                   script_callback=_cb("on_build"),
                                                   script_callback_language=hou.scriptLanguage.Python))
    actions.addParmTemplate(hou.ButtonParmTemplate("validate_asset", "Validate Asset Setup",
                                                   script_callback=_cb("on_validate_setup"),
                                                   script_callback_language=hou.scriptLanguage.Python))
    actions.addParmTemplate(hou.ButtonParmTemplate("force_build_asset", "Force Rebuild Asset Setup",
                                                   script_callback=_cb("on_force_rebuild"),
                                                   script_callback_language=hou.scriptLanguage.Python))
    actions.addParmTemplate(hou.ButtonParmTemplate("sim_test", "Build Sim Test",
                                                   script_callback=_cb("on_sim_test"),
                                                   script_callback_language=hou.scriptLanguage.Python))
    # per-part flipbook of the sim test. Output dir is LOCAL only (empty -> a
    # temp dir under $HOUDINI_TEMP); a Z: path is rejected (production is read-only).
    fb_dir = hou.StringParmTemplate("flipbook_dir", "Flipbook Dir (local)", 1,
                                    default_value=('$HIP/flipbook/`chs("asset")`',),
                                    string_type=hou.stringParmType.FileReference,
                                    file_type=hou.fileType.Directory)
    fb_dir.setHelp("Local output dir for per-part sim-test MP4s. Leave empty to use "
                   "$HIP/flipbook/<asset> (falls back to the OS temp dir when the hip "
                   "lives on Z:). A Z: (production) path is always rejected.")
    actions.addParmTemplate(fb_dir)
    actions.addParmTemplate(hou.ButtonParmTemplate("flipbook_parts", "Flipbook Parts (MP4)",
                                                   script_callback=_cb("on_flipbook_parts"),
                                                   script_callback_language=hou.scriptLanguage.Python))
    actions.addParmTemplate(hou.ButtonParmTemplate("save_constraint_hda", "Save Constraint HDA",
                                                   script_callback=_cb("on_save_constraint_hda"),
                                                   script_callback_language=hou.scriptLanguage.Python))
    actions.addParmTemplate(hou.ButtonParmTemplate(
        "save_collision_hda", "Save Collision HDA",
        script_callback=_cb("on_save_collision_hda"),
        script_callback_language=hou.scriptLanguage.Python))
    actions.addParmTemplate(hou.ButtonParmTemplate(
        "save_deform_hda", "Save Deform HDA",
        script_callback=_cb("on_save_deform_hda"),
        script_callback_language=hou.scriptLanguage.Python))
    actions.addParmTemplate(hou.ButtonParmTemplate(
        "save_fbx_hda", "Save FBX HDA",
        script_callback=_cb("on_save_fbx_hda"),
        script_callback_language=hou.scriptLanguage.Python))
    actions.addParmTemplate(hou.ButtonParmTemplate(
        "save_corrective_hda", "Save Corrective HDA",
        script_callback=_cb("on_save_corrective_hda"),
        script_callback_language=hou.scriptLanguage.Python))
    actions.addParmTemplate(hou.ButtonParmTemplate(
        "save_proxy_hda", "Save Proxy HDA",
        script_callback=_cb("on_save_proxy_hda"),
        script_callback_language=hou.scriptLanguage.Python))
    actions.addParmTemplate(hou.MenuParmTemplate(
        "cache_execution_mode", "Cache Execution",
        menu_items=("foreground", "background"),
        menu_labels=("Foreground", "Background (hython)"),
        default_value=1))
    actions.addParmTemplate(hou.ButtonParmTemplate("write_cache", "Write Rest Cache",
                                                   script_callback=_cb("on_write_cache"),
                                                   script_callback_language=hou.scriptLanguage.Python))
    actions.addParmTemplate(hou.ButtonParmTemplate(
        "background_cache_status", "Background Cache Status",
        script_callback=_cb("on_background_cache_status"),
        script_callback_language=hou.scriptLanguage.Python))
    actions.addParmTemplate(hou.ButtonParmTemplate(
        "cancel_background_cache", "Cancel Background Cache",
        script_callback=_cb("on_cancel_background_cache"),
        script_callback_language=hou.scriptLanguage.Python))

    for folder in (config, actions):
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


def create_asset_tool(parent: str = "/obj", name: str = "cfx_asset"):
    """Shelf entry: make the asset-setup control subnet with its UI."""

    import hou
    root = hou.node(parent)
    if root is None:
        raise ValueError(f"parent not found: {parent}")
    node = root.node(name) or root.createNode("subnet", name)
    _build_interface(node)
    node.setComment("CFX Asset Setup — fill Config, add Parts, then Build")
    node.setGenericFlag(hou.nodeFlag.DisplayComment, True)
    return node


# ---------------------------------------------------------------------------
# node <-> config bridge
# ---------------------------------------------------------------------------
def _fbx_subnet(node):
    """The built FBX subnet under this control node (``{asset}_asset_setup/FBX``),
    or None before the network is built."""

    asset = node.evalParm("asset")
    return node.node("%s_asset_setup/FBX" % asset) if asset else None


def _proxy_subnet(node):
    """The built PROXY subnet under this control node (parts source of truth),
    or None before the network is built."""

    asset = node.evalParm("asset")
    return node.node("%s_asset_setup/PROXY" % asset) if asset else None


def _collision_subnet(node):
    """The built COLLISION subnet (collision params source of truth), or None."""

    asset = node.evalParm("asset")
    return node.node("%s_asset_setup/COLLISION" % asset) if asset else None


_DEFAULT_COLLISION_PATTERN = "@geo_path=*body* @geo_path=*head*"


def _collision_data(node) -> dict:
    """Collision params (body pattern + voxel ratio) — from the COLLISION subnet
    when built (source of truth), else the config JSON file, else defaults."""

    sub = _collision_subnet(node)
    if sub is not None and sub.parm("collision_pattern") is not None:
        return {"collision_pattern": sub.evalParm("collision_pattern") or _DEFAULT_COLLISION_PATTERN,
                "voxel_ratio": sub.evalParm("voxel_ratio")}
    import os
    path = node.evalParm("config_json")
    if path and os.path.isfile(path):
        try:
            data = json.loads(open(path, encoding="utf-8").read())
            block = data["asset"] if isinstance(data.get("asset"), dict) else data
            return {"collision_pattern": block.get("collision_pattern", _DEFAULT_COLLISION_PATTERN),
                    "voxel_ratio": (block.get("collision") or {}).get("voxel_ratio", 0.005)}
        except Exception:
            pass
    return {"collision_pattern": _DEFAULT_COLLISION_PATTERN, "voxel_ratio": 0.005}


def _parts_data(node) -> list:
    """Cloth/Hair parts — from the PROXY subnet's Parts multiparm when built
    (source of truth), else from the config JSON file, else empty."""

    sub = _proxy_subnet(node)
    if sub is not None and sub.parm("parts"):
        out = []
        for i in range(1, sub.evalParm("parts") + 1):
            nm = sub.evalParm("part_name_%d" % i)
            if not nm:
                continue
            geo = sub.evalParm("part_geo_%d" % i)
            out.append({"name": nm, "geo_path": [geo] if geo else [],
                        "cloth": bool(sub.evalParm("part_cloth_%d" % i))})
        return out
    import os
    path = node.evalParm("config_json")
    if path and os.path.isfile(path):
        try:
            data = json.loads(open(path, encoding="utf-8").read())
            block = data["asset"] if isinstance(data.get("asset"), dict) else data
            return block.get("proxy_parts", [])
        except Exception:
            pass
    return []


def _fbx_data(node) -> tuple[dict[str, Any], float]:
    """(fbx dict, hair_scale) — the built FBX subnet is the source of truth for
    fields the artist actually set, but EMPTY import paths fall back to the config
    JSON so the config is still referenced (e.g. after a first build that ran
    before the config was loaded). Config file used directly when not built yet."""

    import os
    cfg_fbx: dict[str, Any] = {}
    cfg_scale = 0.01
    path = node.evalParm("config_json")
    if path and os.path.isfile(path):
        try:
            data = json.loads(open(path, encoding="utf-8").read())
            block = data["asset"] if isinstance(data.get("asset"), dict) else data
            cfg_fbx = block.get("fbx", {}) or {}
            cfg_scale = block.get("hair_scale", 0.01)
        except Exception:
            pass

    sub = _fbx_subnet(node)
    if sub is not None and sub.parm("character_import"):
        # subnet wins, else config; still empty -> scan the current RIG dir on disk
        ci = (sub.evalParm("character_import") or cfg_fbx.get("character_import")
              or _scan_import(node, "character_import"))
        hi = (sub.evalParm("hair_import") or cfg_fbx.get("hair_import")
              or _scan_import(node, "hair_import"))
        return ({"asset_name": node.evalParm("asset"),
                 "root_name": sub.evalParm("root_name") or "root",
                 "pelvis_name": sub.evalParm("pelvis_name") or "pelvis",
                 "head_name": (sub.evalParm("head_name") if sub.parm("head_name") else "") or "head",
                 "character_import": ci,
                 "hair_import": hi},
                sub.evalParm("hair_scale"))
    cfg_fbx.setdefault("asset_name", node.evalParm("asset"))
    # first build (no subnet yet): config wins, else scan the RIG dir so the very
    # first build already has a real FBX/hair path instead of an empty import.
    if not cfg_fbx.get("character_import"):
        cfg_fbx["character_import"] = _scan_import(node, "character_import")
    if not cfg_fbx.get("hair_import"):
        cfg_fbx["hair_import"] = _scan_import(node, "hair_import")
    return cfg_fbx, cfg_scale


def _asset_path_rules(node):
    """Build ``(rules, show, asset, atype)`` for the current selection from the
    control node's ``project_root``/``show``/``asset_type``/``asset``. Returns
    ``None`` when the selection is incomplete."""

    ctrl = _control_node(node)
    root = ctrl.evalParm("project_root")
    show = ctrl.evalParm("show")
    asset = ctrl.evalParm("asset")
    atype = ctrl.evalParm("asset_type") or "Character"
    if not (root and show and asset):
        return None
    rules = _path_rules_for_node(ctrl)
    return rules, show, asset, atype


def node_to_config(node, version: str | None = None) -> AssetSetupConfig:
    """Read the node into an :class:`AssetSetupConfig`. FBX/Hair come from the
    built FBX subnet (source of truth), falling back to the config file.

    ``version`` (e.g. ``"v003"``) selects which rest-cache version the resolved
    ``*_cache_path`` fields point at; when omitted, path_rules defaults to v001.
    """

    parts = _parts_data(node)
    fbx_data, hair_scale = _fbx_data(node)
    coll = _collision_data(node)
    data: dict[str, Any] = {
        "show": node.evalParm("show"),
        "asset": node.evalParm("asset"),
        "asset_type": node.evalParm("asset_type") or "Character",
        "hair_scale": hair_scale,
        "collision_pattern": coll["collision_pattern"],
        "fbx": fbx_data,
        "proxy_parts": parts,
        "collision": {"voxel_ratio": coll["voxel_ratio"]},
        # cloth stiffness is authored per part (on each vellumconstraints node),
        # not globally — no cfg.constraint stretch/bend here.
    }
    # Resolve the rest-cache paths from path_rules (project_root + asset_subpath)
    # so Write Rest Cache has real output paths. Without this, every *_cache_path
    # is None and build_rest_cache skips all filecache nodes.
    if version:
        data["metadata"] = {"version": version}
    info = _asset_path_rules(node)
    if info is not None:
        from .config_loader import resolve_asset_paths
        rules, _show, _asset, _atype = info
        data = resolve_asset_paths(data, rules)
    return AssetSetupConfig.from_dict(data)


def config_to_node(node, cfg: AssetSetupConfig) -> None:
    """Push a config onto the node. Config-tab fields go on the control node;
    FBX/Hair go on the FBX subnet when it is built."""

    node.parm("show").set(cfg.show)
    node.parm("asset").set(cfg.asset)
    node.parm("asset_type").set(cfg.asset_type)
    sub = _fbx_subnet(node)
    if sub is not None and sub.parm("character_import"):
        sub.parm("character_import").set(cfg.fbx.character_import or "")
        sub.parm("hair_import").set(cfg.fbx.hair_import or "")
        sub.parm("root_name").set(cfg.fbx.root_name)
        sub.parm("pelvis_name").set(cfg.fbx.pelvis_name)
        if sub.parm("head_name"):
            sub.parm("head_name").set(getattr(cfg.fbx, "head_name", "") or "head")
        sub.parm("hair_scale").set(cfg.hair_scale)
    psub = _proxy_subnet(node)
    if psub is not None and psub.parm("parts"):
        psub.parm("parts").set(len(cfg.proxy_parts))
        for i, p in enumerate(cfg.proxy_parts, start=1):
            psub.parm("part_name_%d" % i).set(p.name)
            psub.parm("part_geo_%d" % i).set(p.geo_path[0] if p.geo_path else "")
            psub.parm("part_cloth_%d" % i).set(int(p.cloth))
    csub = _collision_subnet(node)
    if csub is not None and csub.parm("collision_pattern") is not None:
        csub.parm("collision_pattern").set(cfg.collision_pattern or _DEFAULT_COLLISION_PATTERN)
        if cfg.collision.get("voxel_ratio") is not None:
            csub.parm("voxel_ratio").set(float(cfg.collision["voxel_ratio"]))


# ---------------------------------------------------------------------------
# button callbacks
# ---------------------------------------------------------------------------
# reentrancy guard: config_to_node sets the asset parm, which would otherwise
# re-fire on_asset_changed.
_BUSY = False


def _config_path_for(node) -> str:
    """The asset's config file path from the current selection:
    ``{project_root}/{show}/assets/{asset_type}/{asset}/Sim/wip/houdini/cfx_asset.json``
    (via ``path_rules.asset_config``). Empty when the selection is incomplete."""

    root = node.evalParm("project_root")
    show = node.evalParm("show")
    atype = node.evalParm("asset_type") or "Character"
    asset = node.evalParm("asset")
    if not (root and show and asset):
        return ""
    rules = _path_rules_for_node(node)
    return rules.resolve("asset_config", show=show, asset=asset)


def _config_asset(path: str) -> str:
    """The ``asset`` name recorded in a config JSON (for the auto-load guard)."""

    try:
        data = json.loads(open(path, encoding="utf-8").read())
        block = data["asset"] if isinstance(data.get("asset"), dict) else data
        return str(block.get("asset", ""))
    except Exception:
        return ""


def _load_file(node, path: str) -> None:
    """Populate the node from a config JSON (no popup). Tolerant of path_rules
    present/absent; restores the scan root when the config carries one."""

    from pathlib import Path
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    block = data["asset"] if isinstance(data.get("asset"), dict) else data
    config_to_node(node, AssetSetupConfig.from_dict(block))
    rules = data.get("path_rules") or block.get("path_rules") or {}
    if rules.get("root"):
        node.parm("project_root").set(rules["root"])
    if node.parm("path_profile") is not None:
        node.parm("path_profile").set(rules.get("profile_file") or "")


def on_update_path(node) -> None:
    """Explicit 'Update Config Path' button: recompute Config File from the
    current selection (Project Root / Show / Asset Type / Asset), auto-load an
    existing config, and report — a reliable manual trigger when the menu-change
    callback didn't fire."""

    global _BUSY
    path = _config_path_for(node)
    if not path:
        _popup("Set Project Root / Show / Asset Type / Asset first.", "warning")
        return
    node.parm("config_json").set(path)
    import os
    if os.path.isfile(path):
        _BUSY = True
        try:
            _load_file(node, path)
            node.parm("config_json").set(path)
        except Exception as exc:
            _popup("Config found but load failed:\n%s\n\n%s" % (path, exc), "error")
            return
        finally:
            _BUSY = False
        _popup("Existing config found and loaded.\n\nAsset: %s\nParts: %d\n%s"
               % (node.evalParm("asset"), len(_parts_data(node)), path))
    else:
        _popup("No config yet — path set to:\n%s\n\nFill the parameters and "
               "Save Config to create it." % path)


def on_asset_changed(node) -> None:
    """When the asset (or asset type) changes, point Config File at that asset's
    ``Sim/wip/houdini`` config and auto-load it if it already exists; otherwise
    just set the target path so ``Save Config`` creates it there."""

    global _BUSY
    if _BUSY:
        return
    path = _config_path_for(node)
    if not path:
        return
    node.parm("config_json").set(path)
    import os
    if os.path.isfile(path) and _config_asset(path) == node.evalParm("asset"):
        # only auto-load when the file really is THIS asset's config, so a stale
        # path can never silently switch the selected asset (drift guard).
        _BUSY = True
        try:
            _load_file(node, path)
            node.parm("config_json").set(path)  # _load_file may have changed root
        except Exception as exc:               # keep the fields; just report
            _popup("Found a config but failed to load it:\n%s\n\n%s" % (path, exc),
                   "warning")
        finally:
            _BUSY = False


def _popup(msg: str, severity: str = "message") -> None:
    """Show modeless feedback; never enter a nested Houdini modal loop."""

    from .ui_feedback import show_message
    show_message("CFX Asset Setup", msg, severity)


def _pick_file(dirpath, prefer, exts) -> str:
    """First file in ``dirpath`` ending with ``exts`` (a name-matched ``prefer``
    key wins), or "" when the dir is missing/empty."""

    import os
    if not dirpath or not os.path.isdir(dirpath):
        return ""
    files = sorted(f for f in os.listdir(dirpath)
                   if f.lower().endswith(exts)
                   and os.path.isfile(os.path.join(dirpath, f)))
    if not files:
        return ""
    for key in prefer:                      # prefer a name-matched file
        for f in files:
            if key in f.lower():
                return os.path.join(dirpath, f).replace("\\", "/")
    return os.path.join(dirpath, files[0]).replace("\\", "/")


# import specs: (fbx field, RIG dir template, extensions, name-match preference)
_IMPORT_SPECS = [
    ("character_import", "character_fbx_dir", (".fbx",), ("sim",)),
    ("hair_import", "hair_guide_dir", (".abc",), ("guides", "guide")),
]


def _scan_import(node, field: str):
    """Disk-scan fallback for an import field (``character_import``/``hair_import``):
    pick the first matching file in the current project's RIG dir. Used when both the
    FBX subnet and the config JSON leave the field empty, so a file that actually
    exists on disk is still referenced. Returns ``None`` when nothing is found."""

    for f, template, exts, prefer in _IMPORT_SPECS:
        if f == field:
            return _pick_file(_asset_dir(node, template), prefer, exts) or None
    return None


def _reresolve_import(node, current: str, template: str, exts, prefer) -> str:
    """Re-point an import path at the CURRENT project's RIG dir (from path_rules)
    so it matches the current Project Root / Show / Asset. Prefer an actual file
    found there; else re-root the current filename onto the resolved dir; else
    keep ``current`` unchanged."""

    import os
    # A valid pub/wip file inside the selected Asset root is already correct.
    # Do not replace it with the first file in the template's scan directory.
    if current and os.path.isfile(current):
        info = _asset_path_rules(node)
        if info is not None:
            rules, show, asset, _atype = info
            asset_root = rules.resolve("asset_root", show=show, asset=asset)
            cur_norm = os.path.normcase(os.path.abspath(current))
            root_norm = os.path.normcase(os.path.abspath(asset_root))
            try:
                if os.path.commonpath((cur_norm, root_norm)) == root_norm:
                    return current
            except ValueError:
                pass
    rig_dir = _asset_dir(node, template)
    if not rig_dir:
        return current
    picked = _pick_file(rig_dir, prefer, exts)
    if picked:
        return picked
    if current:  # no file present -> keep the filename, fix the (stale) directory
        return rig_dir.rstrip("/\\") + "/" + os.path.basename(current)
    return current


def _autofill_fbx_from_config(node, sub) -> None:
    """Fill the FBX subnet's Character FBX / Hair Guide from the current project's
    RIG dir when the artist left them empty (so artist picks persist)."""

    for field, template, exts, prefer in _IMPORT_SPECS:
        if sub.parm(field) and not sub.evalParm(field):
            v = _pick_file(_asset_dir(node, template), prefer, exts)
            if v:
                sub.parm(field).set(v)


def _add_fbx_scan_menus(sub) -> None:
    """Upgrade the built FBX subnet's Character FBX / Hair Guide params to the
    RIG-directory scan menus (value preserved). Keeps FileReference so the browse
    button stays; the scan resolves the asset dir via the control-node ancestor."""

    import hou
    for pname, func in (("character_import", "scan_char_fbx"),
                        ("hair_import", "scan_hair_guide")):
        g = sub.parmTemplateGroup()
        old = g.find(pname)
        if old is None:
            continue
        val = sub.evalParm(pname)
        newpt = hou.StringParmTemplate(
            pname, old.label(), 1, string_type=hou.stringParmType.FileReference,
            menu_items=(), menu_labels=(), item_generator_script=_menu_script(func),
            item_generator_script_language=hou.scriptLanguage.Python,
            menu_type=hou.menuType.StringReplace)
        g.replace(old, newpt)
        sub.setParmTemplateGroup(g)
        sub.parm(pname).set(val)


def _add_parts_buttons(sub) -> None:
    """Install Auto-detect / Clear buttons just above the Parts multiparm on the
    PROXY subnet (idempotent). Per-row add/remove is the multiparm's native +/-."""

    import hou
    g = sub.parmTemplateGroup()
    if g.find("autodetect_parts") is not None:
        return
    btn_auto = hou.ButtonParmTemplate(
        "autodetect_parts", "Auto-detect Parts from geo_path",
        script_callback=_cb("on_autodetect_parts"),
        script_callback_language=hou.scriptLanguage.Python)
    btn_gen = hou.ButtonParmTemplate(
        "generate_structure", "Generate Structure (from cloth_ref)",
        script_callback=_cb("on_generate_structure"),
        script_callback_language=hou.scriptLanguage.Python)
    btn_clear = hou.ButtonParmTemplate(
        "clear_parts", "Clear Parts",
        script_callback=_cb("on_clear_parts"),
        script_callback_language=hou.scriptLanguage.Python)
    # hidden bookkeeping: every geo_path auto-detect has ever surfaced, so a
    # part the user removed is NOT re-added on the next Auto-detect (removals stick).
    known = hou.StringParmTemplate("known_geo", "Known Geo (internal)", 1,
                                   is_hidden=True)
    parts_pt = g.find("parts")
    if parts_pt is not None:
        g.insertBefore(parts_pt, btn_auto)
        g.insertBefore(parts_pt, btn_gen)
        g.insertBefore(parts_pt, btn_clear)
    else:
        g.append(btn_auto)
        g.append(btn_gen)
        g.append(btn_clear)
    g.append(known)
    sub.setParmTemplateGroup(g)


def _part_name_from_geo(geo_path: str) -> str:
    """Derive a friendly part name from a geo_path (``Pants_geo`` -> ``pants``)."""

    base = geo_path.rsplit("/", 1)[-1]
    for suf in ("_geo", "_grp", "_mesh", "_msh"):
        if base.lower().endswith(suf):
            base = base[: -len(suf)]
            break
    return base.lower()


def _collision_patterns(node) -> list:
    """Wildcard tokens from the Collision Body Pattern (COLLISION subnet), used
    to exclude collider geometry (body/head) from proxy-part auto-detect —
    those pieces belong to COLLISION, not to the cloth/hair parts."""

    ctrl = _control_node(node)
    raw = _collision_data(ctrl).get("collision_pattern") or _DEFAULT_COLLISION_PATTERN
    pats = []
    for tok in (raw or "").split():
        if tok.startswith("@geo_path="):
            tok = tok[len("@geo_path="):]
        if tok:
            pats.append(tok)
    return pats


def _known_geo(node) -> set:
    """geo_paths auto-detect has already surfaced (added or later removed)."""

    raw = node.evalParm("known_geo") if node.parm("known_geo") is not None else ""
    return {v for v in (raw or "").split("\n") if v}


def _set_known_geo(node, values) -> None:
    if node.parm("known_geo") is not None:
        node.parm("known_geo").set("\n".join(sorted(values)))


def on_autodetect_parts(node) -> None:
    """Populate the PROXY subnet's Parts multiparm from the distinct ``@geo_path``
    values on its input (the corrected mesh).

    - Collider geometry matching the Collision Body Pattern (body/head) is
      excluded — it belongs to COLLISION, not the cloth/hair parts.
    - Only geo_paths never surfaced before are added (tracked in ``known_geo``),
      so a part the user removed does NOT come back on the next Auto-detect.
    New rows default to cloth; the artist then toggles hair. To re-surface every
    piece from scratch, use Clear Parts first (it resets the memory)."""

    import fnmatch

    inputs = node.inputs()
    if not inputs or inputs[0] is None:
        _popup("PROXY subnet has no input to scan.", "warning")
        return
    try:
        g = inputs[0].geometry()
    except Exception as exc:
        _popup("Could not read input geometry:\n%s" % exc, "error")
        return
    attrib = g.findPrimAttrib("geo_path") if g is not None else None
    values = sorted(attrib.strings()) if attrib is not None else []
    if not values:
        _popup("No @geo_path values found on the input geometry.", "warning")
        return
    collider = _collision_patterns(node)
    known = _known_geo(node)
    existing = {node.evalParm("part_geo_%d" % i)
                for i in range(1, (node.evalParm("parts") or 0) + 1)}
    added, skipped, seen = [], [], set()
    for v in values:
        if any(fnmatch.fnmatch(v, p) for p in collider):  # body/head -> COLLISION
            skipped.append(v)
            continue
        seen.add(v)                       # a real cloth/hair candidate
        if v in existing or v in known:   # already listed, or user removed it before
            continue
        n = (node.evalParm("parts") or 0) + 1
        node.parm("parts").set(n)
        node.parm("part_name_%d" % n).set(_part_name_from_geo(v))
        node.parm("part_geo_%d" % n).set(v)
        node.parm("part_cloth_%d" % n).set(1)  # default cloth; user toggles hair
        added.append(v)
    _set_known_geo(node, known | seen)    # remember everything surfaced this run
    _popup("Auto-detect complete.\n\n%d geo_path value(s) found, %d new part(s) added.\n"
           "Excluded %d collider (body/head) piece(s).\n\n"
           "Removed parts are not re-added — use Clear Parts to reset."
           % (len(values), len(added), len(skipped)))


def on_clear_parts(node) -> None:
    """Remove all rows from the Parts multiparm and reset the Auto-detect memory,
    so the next Auto-detect surfaces every piece again."""

    if node.parm("parts"):
        node.parm("parts").set(0)
    _set_known_geo(node, set())
    _popup("Cleared all parts (Auto-detect memory reset).")


def on_generate_structure(node) -> None:
    """Auto-generate the cloth proxy structure inside the PROXY subnet by
    instancing the ``cloth_ref`` template once per cloth part (``node`` is the
    PROXY subnet). A default ``cloth_ref`` is created if the artist hasn't made
    one; copies for removed parts are retired. Hair is handled by HAIR."""

    import hou

    _asset._ensure_cloth_ref(node)   # create a default template if missing
    cloth = [p for p in _asset._parts_from_node(node) if p.cloth and p.geo_path]
    if not cloth:
        _popup("No cloth parts with a geo_path to generate.", "warning")
        return
    merge = node.node("proxy_merge") or node.createNode("merge", "proxy_merge")
    made = _asset._instance_cloth_ref(node, cloth, merge)
    # keep the subnet output wired to the merge
    out = node.node("output0") or node.createNode("output", "output0")
    if not out.inputs() or out.inputs()[0] is not merge:
        out.setInput(0, merge, 0)
    node.layoutChildren()
    # keep CONSTRAINT in sync — regenerate the per-part vellum setups to match
    ctrl = _control_node(node)
    con_msg = ""
    try:
        _asset.build_constraint(node_to_config(ctrl), ctrl.path())
        con_msg = "\n\nCONSTRAINT updated to match."
    except Exception as exc:
        con_msg = "\n\n(CONSTRAINT update failed: %s)" % exc
    _popup("Generated cloth structure for %d part(s):\n%s%s"
           % (len(made), "\n".join(made), con_msg))


def _layout_recursive(node) -> None:
    """Lay out a node's children, recursing into every subnet descendant so the
    whole asset_setup tree (stage subnets + cloth_ref copies) is tidy."""

    kids = node.children()
    if not kids:
        return
    for c in kids:
        _layout_recursive(c)
    node.layoutChildren()


def _layout_asset(node) -> None:
    """Tidy the whole built asset network under the control node."""

    container = _asset_container(node)
    if container is not None:
        _layout_recursive(container)


def _asset_container(node):
    """The built ``{asset}_asset_setup`` container, or None."""

    asset = node.evalParm("asset")
    return node.node("%s_asset_setup" % asset) if asset else None


def _flatten_asset(node) -> None:
    """Dissolve the CACHE/SIMTEST stage subnets so the flat cache/sim-test
    builders rebuild cleanly (the FBX/CORRECTIVE/... stage subnets are untouched)."""

    geo = _asset_container(node)
    if geo is not None:
        try:
            _asset.flatten_asset_stages(geo)
        except Exception:
            pass


def _organize_asset(node) -> None:
    """Group the flat rest-cache / sim-test nodes into stage subnets, then lay out."""

    geo = _asset_container(node)
    if geo is not None:
        try:
            _asset.organize_asset_stages(geo)
        except Exception:
            pass
    _layout_asset(node)


_ASSET_REQUIRED_STAGES = (
    "FBX", "CORRECTIVE", "COLLISION", "PROXY", "DEFORM", "CONSTRAINT",
)


def validate_setup(node) -> dict[str, Any]:
    """Inspect the artist network without cooking, rebuilding, or laying it out."""

    geo = _asset_container(node)
    if geo is None:
        return {"state": "missing", "missing": list(_ASSET_REQUIRED_STAGES),
                "conflicts": [], "path": ""}
    missing = [name for name in _ASSET_REQUIRED_STAGES if geo.node(name) is None]
    conflicts = []
    for name in _ASSET_REQUIRED_STAGES:
        stage = geo.node(name)
        if stage is not None and not (
                stage.type().name() == "subnet" or stage.type().definition() is not None):
            conflicts.append("%s exists but is not a stage subnet/HDA" % name)
    state = "valid" if not missing and not conflicts else "partial"
    return {"state": state, "missing": missing, "conflicts": conflicts,
            "path": geo.path()}


def on_validate_setup(node) -> dict[str, Any]:
    report = validate_setup(node)
    lines = ["Asset setup: %s" % report["state"].upper()]
    if report["path"]:
        lines.append(report["path"])
    if report["missing"]:
        lines.append("Missing stages: %s" % ", ".join(report["missing"]))
    if report["conflicts"]:
        lines.append("Conflicts:\n- " + "\n- ".join(report["conflicts"]))
    _popup("\n\n".join(lines), "message" if report["state"] == "valid" else "warning")
    return report


def _build_new_asset(node) -> dict[str, Any]:
    """Create a complete asset container. Caller guarantees it does not exist."""

    cfg = node_to_config(node)
    p = node.path()
    steps = [
        _asset.build_asset_setup, _asset.build_corrective, _asset.build_collision,
        _asset.build_proxy, _asset.build_hair_proxy,
        _asset.build_deform_handoff, _asset.build_constraint,
    ]
    for fn in steps:
        fn(cfg, p)
    # Cache nodes are authored as part of setup creation, but no files are
    # written here. Operational cache buttons execute this prepared stage only.
    _asset.build_rest_cache(cfg, p, execute=False)
    sub = _fbx_subnet(node)
    if sub is not None:
        _add_fbx_scan_menus(sub)
        _autofill_fbx_from_config(node, sub)
    psub = _proxy_subnet(node)
    if psub is not None:
        _add_parts_buttons(psub)
    _organize_asset(node)
    return {"built": "%s/%s_asset_setup" % (p, cfg.asset)}


def on_build(node) -> dict[str, Any]:
    """Create a setup only when absent; never rewrite an artist-edited setup."""

    report = validate_setup(node)
    if report["state"] == "valid":
        _popup("Asset setup is already complete. No nodes were changed.\n\n%s\n\n"
               "Use Validate to inspect it, or Force Rebuild for an explicit reset."
               % report["path"])
        return {"built": report["path"], "changed": False, "validation": report}
    if report["state"] == "partial":
        detail = []
        if report["missing"]:
            detail.append("Missing stages: %s" % ", ".join(report["missing"]))
        detail.extend(report["conflicts"])
        message = ("Existing Asset setup is incomplete or conflicts with the expected "
                   "structure. Nothing was changed.\n\n- %s\n\nRepair it manually or "
                   "use Force Rebuild if discarding its edits is intentional."
                   % "\n- ".join(detail))
        _popup(message, "warning")
        return {"changed": False, "validation": report}
    try:
        result = _build_new_asset(node)
    except Exception as exc:
        _popup("Build failed:\n%s" % exc, "error")
        raise
    cfg = node_to_config(node)
    built = result["built"]
    _popup("Asset setup built.\n\nAsset: %s\nParts: %d\n%s"
           % (cfg.asset, len(cfg.proxy_parts), built))
    result.update({"changed": True, "validation": validate_setup(node)})
    return result


def on_force_rebuild(node) -> dict[str, Any]:
    """Request a non-modal confirmation for the destructive rebuild."""

    import hou
    if hou.isUIAvailable():
        from .ui_feedback import ask_choice
        node_path = node.path()
        ask_choice(
            "Force Rebuild Asset Setup",
            "This replaces the complete Asset setup container and discards "
            "artist edits inside it. Cache files on disk are not deleted.",
            [("Force Rebuild", True), ("Cancel", False)],
            lambda confirmed: _force_rebuild_asset_path(node_path)
            if confirmed else None)
        return {"prompted": True}
    return _force_rebuild_asset_path(node.path())


def _force_rebuild_asset_path(node_path: str) -> dict[str, Any]:
    import hou
    node = hou.node(node_path)
    if node is None:
        return {"cancelled": True, "error": "control node no longer exists"}

    # Resolve config and all path rules before deleting the existing container.
    node_to_config(node)
    previous = _asset_container(node)
    if previous is not None:
        previous.destroy()
    try:
        result = _build_new_asset(node)
    except Exception as exc:
        _popup("Force rebuild failed:\n%s" % exc, "error")
        raise
    result.update({"changed": True, "forced": True,
                   "validation": validate_setup(node)})
    _popup("Asset setup force-rebuilt from the current parameters.\n\n%s"
           % result["built"], "warning")
    return result


def on_sim_test(node) -> dict[str, Any]:
    _flatten_asset(node)
    try:
        res = _asset.build_asset_sim_test(node_to_config(node), node.path())
    except Exception as exc:
        _organize_asset(node)
        _popup("Sim test build failed:\n%s" % exc, "error")
        raise
    _organize_asset(node)
    _popup("Sim test built:\n%s\n\nScrub the timeline to check the drape."
           % res.get("out_sim_test", ""))
    return res


def _local_flip_dir(node) -> str:
    """Resolve the LOCAL output dir for per-part flipbooks. Uses the node's
    ``flipbook_dir`` param when set, but NEVER a Z: (production) path; falls back
    to ``$HOUDINI_TEMP/cfx_sim_test/<asset>/flip`` so a click always has a
    writable local target."""

    import hou, tempfile
    asset = node.evalParm("asset") or "asset"

    def _prod(path):                       # Z: production drive is read-only
        return path[:2].upper() == "Z:"

    # 1. explicit param wins (unless it points at production Z:)
    p = node.evalParm("flipbook_dir") if node.parm("flipbook_dir") else ""
    if p:
        p = hou.expandString(p).replace("\\", "/")
        if not _prod(p):
            return p.rstrip("/")
    # 2. hip directory — natural per-scene location alongside the config/scene
    hip = hou.expandString("$HIP").replace("\\", "/")
    if hip and not _prod(hip):
        return "%s/flipbook/%s" % (hip.rstrip("/"), asset)
    # 3. safe local fallback when the hip lives on Z: (or $HIP is unset)
    return ("%s/cfx_sim_test/%s/flip"
            % (tempfile.gettempdir().replace("\\", "/").rstrip("/"), asset))


def on_flipbook_parts(node) -> dict[str, Any]:
    """Render one MP4 per cloth part from the sim-test output, into a LOCAL dir.

    Requires the sim test (``OUT_ASSET_SIMTEST``) to exist — run Build Sim Test
    first. GL rendering must run in Houdini's UI (this is a button callback), so
    scrubbing/flipbook uses the live OpenGL context."""

    out_dir = _local_flip_dir(node)
    try:
        res = _asset.build_part_flipbooks(
            node_to_config(node), node.path(), out_dir=out_dir)
    except Exception as exc:
        _popup("Flipbook failed:\n%s" % exc, "error")
        raise
    results = res.get("results", [])
    movies = res.get("movies", [])
    total_frames = sum(r.get("frames", 0) for r in results)
    lines = ["%s: %d frame(s)%s" % (r["part"], r.get("frames", 0),
                                    "  -> mp4" if r.get("mp4") else "  (no mp4)")
             for r in results[:20]]
    note = ""
    if total_frames == 0:
        note = ("\n\nWARNING: 0 frames were rendered — the viewport flipbook wrote "
                "nothing. Make sure a Scene Viewer is visible and try again.")
    elif not res.get("ffmpeg"):
        note = "\n\nNote: ffmpeg not found — JPG frames written, but no MP4 encoded."
    _popup("Flipbook: %d/%d part(s) -> MP4.\n\nOutput dir (local):\n%s%s\n\n%s"
           % (len(movies), len(results), res.get("out_dir", out_dir), note,
              "\n".join(lines)))
    return res


def _prompt_version(node, callback=None) -> str | None:
    """Choose whether to version up or overwrite the latest rest cache.

    The proxy cache is the authoritative version index because every rest-cache
    publish includes it. In UI mode the artist must explicitly choose between
    the next version and overwriting the latest existing version. Headless
    execution always chooses the next version so it never overwrites silently.
    """

    import os
    info = _asset_path_rules(node)
    if info is None:
        _popup("Set Project Root / Show / Asset before writing a cache.", "warning")
        return None
    rules, show, asset, _atype = info
    from .path_rules import existing_versions, next_version
    # version dir = the folder holding the vNNN subdirs (parent of the version dir
    # in the resolved proxy cache path .../geo/{asset}_proxy_rest/{version}/file).
    sample = rules.resolve("asset_proxy_cache", show=show, asset=asset, version="v001")
    vdir = os.path.dirname(os.path.dirname(sample))
    existing = existing_versions(vdir)
    suggested = rules.format_version(next_version(vdir))
    latest = rules.format_version(existing[-1]) if existing else None
    listed = ", ".join(rules.format_version(v) for v in existing) or "(none)"

    import hou
    if not hou.isUIAvailable():
        return suggested
    if callback is None:
        return None
    from .ui_feedback import ask_choice
    if latest is None:
        message = (
            "Write Rest Cache\n\nAsset: %s\nExisting versions: %s\n\n"
            "No cache exists yet. Write %s?" % (asset, listed, suggested))
        choices = [("Write %s" % suggested, suggested), ("Cancel", None)]
    else:
        message = (
            "Write Rest Cache\n\nAsset: %s\nExisting versions: %s\n"
            "Latest version: %s\n\nChoose how to publish the cache."
            % (asset, listed, latest))
        choices = [
            ("Version Up (%s)" % suggested, suggested),
            ("Overwrite (%s)" % latest, latest),
            ("Cancel", None),
        ]
    ask_choice("Write Rest Cache", message, choices, callback)
    return None


def _prompt_hda_version(node, stage: str = "constraint",
                        callback=None) -> str | None:
    """Ask which stage-HDA version to publish."""

    show = node.evalParm("show"); asset = node.evalParm("asset")
    if not (show and asset):
        _popup("Set Show / Asset before publishing the %s HDA." % stage,
               "warning")
        return None
    hda_dir = _asset.__dict__["_constraint_hda_dir"](_asset.CONSTRAINT_HDA_ROOT, show, asset) \
        if hasattr(_asset, "_constraint_hda_dir") else None
    if stage == "constraint":
        existing = (_asset._constraint_hda_versions(hda_dir, asset)
                    if hda_dir else [])
    else:
        existing = (_asset._stage_hda_versions(hda_dir, asset, stage)
                    if hda_dir else [])
    nextnum = (existing[-1] + 1) if existing else 1
    suggested = "v%03d" % nextnum
    listed = ", ".join("v%03d" % v for v in existing) or "(none)"
    import hou
    if not hou.isUIAvailable():
        return suggested
    if callback is None:
        return None
    from .ui_feedback import ask_text
    message = (
        "Save %s HDA\n\nAsset: %s\nDir: %s\nExisting: %s\n\n"
        "Enter version (e.g. v003; existing = overwrite):"
        % (stage.title(), asset, hda_dir, listed))

    def validate(value):
        if not value:
            callback(None)
            return
        try:
            text = str(value).strip()
            if not text.startswith("v"):
                text = "v%03d" % int(text)
            callback(text)
        except Exception:
            _popup("Invalid HDA version: %r" % value, "warning")

    ask_text("Save %s HDA" % stage.title(), message, suggested, validate)
    return None


def on_save_constraint_hda(node) -> dict[str, Any]:
    """Publish the asset's CONSTRAINT subnet as a versioned HDA under
    Z:/inhouse/Houdini/otls/{show}/{asset}/ so shots can instantiate it as-is."""

    import hou
    if hou.isUIAvailable():
        node_path = node.path()
        _prompt_hda_version(
            node, callback=lambda version:
            _save_constraint_hda_version(node_path, version))
        return {"prompted": True}
    return _save_constraint_hda_version(node.path(), _prompt_hda_version(node))


def _save_constraint_hda_version(node_path: str, version) -> dict[str, Any]:
    import hou
    node = hou.node(node_path)
    if node is None or version is None:
        return {"cancelled": True}
    try:
        res = _asset.save_constraint_hda(node, version=version)
    except Exception as exc:
        _popup("Save Constraint HDA failed:\n%s" % exc, "error")
        raise
    try:
        replacement = _asset.replace_stage_with_published_hda(
            node, "constraint", res)
    except Exception as exc:
        replacement = {"replaced": False, "reason": str(exc)}
    res["replacement"] = replacement
    replace_msg = (
        "Live CONSTRAINT replaced with the published HDA."
        if replacement.get("replaced") else
        ("Live CONSTRAINT already uses this HDA."
         if replacement.get("already_current") else
         "Live CONSTRAINT was kept unchanged: %s"
         % replacement.get("reason", "replacement validation failed")))
    _popup("Constraint HDA published.\n\nType: %s\nFile: %s\nVersion: %s\n"
           "Existing: %s\n\n%s\nShots can now instantiate this constraint setup."
           % (res["type_name"], res["hda_file"], res["version"],
              ", ".join(res["existing"]) or "(none)", replace_msg),
           "message" if (replacement.get("replaced")
                          or replacement.get("already_current")) else "warning")
    return res


def _save_stage_hda_ui(node, stage: str) -> dict[str, Any]:
    import hou
    if hou.isUIAvailable():
        node_path = node.path()
        _prompt_hda_version(
            node, stage, callback=lambda version:
            _save_stage_hda_version(node_path, stage, version))
        return {"prompted": True}
    return _save_stage_hda_version(
        node.path(), stage, _prompt_hda_version(node, stage))


def _save_stage_hda_version(node_path: str, stage: str,
                            version) -> dict[str, Any]:
    import hou
    node = hou.node(node_path)
    if node is None or version is None:
        return {"cancelled": True}
    try:
        result = _asset.save_stage_hda(node, stage, version=version)
    except Exception as exc:
        _popup("Save %s HDA failed:\n%s" % (stage.title(), exc), "error")
        raise
    try:
        replacement = _asset.replace_stage_with_published_hda(
            node, stage, result)
    except Exception as exc:
        replacement = {"replaced": False, "reason": str(exc)}
    result["replacement"] = replacement
    replace_msg = (
        "Live %s replaced with the published HDA." % stage.upper()
        if replacement.get("replaced") else
        ("Live %s already uses this HDA." % stage.upper()
         if replacement.get("already_current") else
         "Live %s was kept unchanged: %s"
         % (stage.upper(), replacement.get(
             "reason", "replacement validation failed"))))
    _popup(
        "%s HDA published.\n\nType: %s\nFile: %s\nVersion: %s\n"
        "Existing: %s\n\n%s\nShots will use this Asset-authored setup."
        % (stage.title(), result["type_name"], result["hda_file"],
           result["version"], ", ".join(result["existing"]) or "(none)",
           replace_msg),
        "message" if (replacement.get("replaced")
                       or replacement.get("already_current")) else "warning")
    return result


def on_save_collision_hda(node) -> dict[str, Any]:
    return _save_stage_hda_ui(node, "collision")


def on_save_deform_hda(node) -> dict[str, Any]:
    return _save_stage_hda_ui(node, "deform")


def on_save_fbx_hda(node) -> dict[str, Any]:
    return _save_stage_hda_ui(node, "fbx")


def on_save_corrective_hda(node) -> dict[str, Any]:
    return _save_stage_hda_ui(node, "corrective")


def on_save_proxy_hda(node) -> dict[str, Any]:
    return _save_stage_hda_ui(node, "proxy")


def _infer_proxy_parts_from_hda(proxy) -> list[dict[str, Any]]:
    """Recover the Parts multiparm from authored proxy child subnets."""

    import re
    parts = []
    if proxy is None:
        return parts
    for child in proxy.children():
        name = child.name()
        if name in ("cloth_ref", "hair_ref"):
            continue
        if name.startswith("cloth_"):
            cloth = True
            fallback_name = name[len("cloth_"):]
        elif name.startswith("hair_"):
            cloth = False
            fallback_name = name[len("hair_"):]
        else:
            continue
        proxy_name = fallback_name
        tag = child.node("proxypath")
        if tag is not None and tag.parm("snippet") is not None:
            match = re.search(r'proxy_path\s*=\s*"([^"]+)"',
                              tag.evalParm("snippet") or "")
            if match:
                proxy_name = match.group(1)
        geo_value = ""
        selector = child.node("parts_name")
        if selector is not None and selector.parm("group") is not None:
            group = selector.evalParm("group") or ""
            for prefix in ("@geo_path=", "@name="):
                if group.startswith(prefix) and " " not in group:
                    geo_value = group[len(prefix):]
                    break
        parts.append({"name": proxy_name, "geo_path": [geo_value] if geo_value else [],
                      "proxy_path": proxy_name, "cloth": cloth})
    return parts


def restore_hda_stage_interfaces(node) -> dict[str, Any]:
    """Repair parameter interfaces for stage HDAs created by older publishers."""

    import hou
    cfg = node_to_config(node)
    geo = _asset_container(node)
    if geo is None:
        raise ValueError("Asset setup container is missing")
    proxy = geo.node("PROXY")
    if not cfg.proxy_parts:
        inferred = _infer_proxy_parts_from_hda(proxy)
        if inferred:
            data = cfg.as_dict()
            data["proxy_parts"] = inferred
            cfg = AssetSetupConfig.from_dict(data)

    repaired = {}
    for stage in ("FBX", "COLLISION", "PROXY"):
        live = geo.node(stage)
        definition = live.type().definition() if live is not None else None
        if definition is None:
            continue
        temp = geo.createNode("subnet", "__cfx_interface_%s" % stage.lower())
        try:
            if stage == "FBX":
                _asset._fbx_subnet_params(temp, cfg, seed=True)
                _add_fbx_scan_menus(temp)
            elif stage == "COLLISION":
                _asset._collision_params(temp, cfg, seed=True)
            else:
                _asset._proxy_parts_multiparm(temp, cfg, seed=True)
                _add_parts_buttons(temp)
            interface = _asset._interface_with_current_defaults(temp)
            definition.setParmTemplateGroup(interface)
            _asset._copy_stage_parm_values(temp, live)
            repaired[stage] = {
                "node": live.path(), "hda_file": definition.libraryFilePath(),
                "parms": [parm.name() for parm in live.parms()],
            }
        finally:
            temp.destroy()
    return {"repaired": repaired,
            "proxy_parts": [part.as_dict() for part in cfg.proxy_parts]}


def on_write_cache(node) -> dict[str, Any]:
    import hou
    if hou.isUIAvailable():
        node_path = node.path()
        _prompt_version(
            node, callback=lambda version:
            _write_cache_version(node_path, version))
        return {"prompted": True}
    return _write_cache_version(node.path(), _prompt_version(node))


def _prepare_rest_cache(node, version) -> dict[str, Any]:
    """Create only a missing Rest Cache stage; never rebuild Asset stages."""

    cfg = node_to_config(node, version=version)
    geo = _asset_container(node)
    if geo is None:
        raise RuntimeError("Asset setup is missing; run Build Asset Setup first")
    if validate_setup(node).get("state") != "valid":
        raise RuntimeError(
            "Asset setup validation failed; Rest Cache preparation was not run")
    # An organized CACHE subnet is an existing authored/prepared stage. Do not
    # flatten it or create competing root-level cache nodes.
    if geo.node("CACHE") is not None:
        return {"prepared": True, "existing_stage": geo.node("CACHE").path()}
    return _asset.build_rest_cache(cfg, node.path(), execute=False)


def _write_cache_version(node_path: str, version) -> dict[str, Any]:
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
            setup = _prepare_rest_cache(node, version)
            # hython reads a frozen snapshot and must see the newly prepared
            # cache nodes. This save is part of the explicit cache action.
            hou.hipFile.save()
            status = background_jobs.launch_job(node, "rest_cache", version=version)
        except Exception as exc:
            _popup("Background rest cache launch failed:\n%s" % exc, "error")
            raise
        background_jobs.show_progress_monitor(node)
        return {"background": True, "setup": setup, "status": status}

    setup = _prepare_rest_cache(node, version)
    try:
        res = _asset.execute_prepared_rest_cache(
            node_to_config(node, version=version), node.path())
    except Exception as exc:
        _popup("Rest cache write failed:\n%s" % exc, "error")
        raise
    n = len(res.get("caches", []))
    warns = res.get("warnings") or []
    msg = "Rest cache written (%s, %d cache(s))." % (version, n)
    if warns:
        msg += "\n\nWarnings:\n- " + "\n- ".join(warns)
    _popup(msg, "warning" if warns else "message")
    res["setup"] = setup
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


def on_load_config(node) -> None:
    """Load a config JSON onto the node. Tolerant of path_rules being present or
    absent (the node UI only needs the asset fields, not resolved paths)."""

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
    _popup("Config loaded.\n\nAsset: %s\nParts: %d\n%s"
           % (node.evalParm("asset"), len(_parts_data(node)), path))


def on_save_config(node) -> None:
    """Write the node's parameters to the config JSON as a standalone config —
    includes a ``path_rules`` block (from Project Root + Asset Type) so the file
    loads directly via :func:`config_loader.load_asset_config` / the workflow."""

    path = node.evalParm("config_json")
    if not path:
        _popup("Config File path is empty — set it first.", "warning")
        return
    try:
        from pathlib import Path
        # re-resolve the FBX import paths against the CURRENT project settings so
        # the saved config matches (a config loaded from another show/root keeps
        # stale absolute import paths otherwise). Also write them back onto the
        # built FBX subnet so the node + config stay consistent.
        sub = _fbx_subnet(node)
        for field, template, exts, prefer in _IMPORT_SPECS:
            if sub is None or sub.parm(field) is None:
                continue
            newv = _reresolve_import(node, sub.evalParm(field), template, exts, prefer)
            if newv != sub.evalParm(field):
                sub.parm(field).set(newv)
        data = node_to_config(node).as_dict()
        profile_file = (node.evalParm("path_profile")
                        if node.parm("path_profile") is not None else "")
        path_context = {"asset_type": node.evalParm("asset_type") or "Character"}
        if not profile_file:
            path_context["asset_subpath"] = "assets/%s" % path_context["asset_type"]
        data["path_rules"] = {
            "root": node.evalParm("project_root") or "Z:/show",
            "context": path_context,
        }
        if profile_file:
            data["path_rules"]["profile_file"] = profile_file
        Path(path).parent.mkdir(parents=True, exist_ok=True)  # create the asset dir if new
        Path(path).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        _popup("Save failed:\n%s\n\n%s" % (path, exc), "error")
        return
    _popup("Config saved.\n\nAsset: %s\nParts: %d\n%s"
           % (node.evalParm("asset"), len(_parts_data(node)), path))
