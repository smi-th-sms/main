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
    """Python button-callback that is robust to sys.path not being set yet."""

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
    import os
    return _scan(os.path.join(node.evalParm("project_root"),
                              node.evalParm("show"), "assets"))


def scan_assets(node) -> list[str]:
    import os
    return _scan(os.path.join(node.evalParm("project_root"), node.evalParm("show"),
                              "assets", node.evalParm("asset_type")))


def _control_node(node):
    """Walk up to the CFX control node (the one carrying ``project_root``) so
    scans work whether called from the control node or a descendant subnet."""

    n = node
    while n is not None:
        if n.parm("project_root") is not None:
            return n
        n = n.parent()
    return node


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
    from .path_rules import PipelinePathRules
    rules = PipelinePathRules.from_dict(
        {"root": root, "context": {"asset_subpath": "assets/%s" % atype}})
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
    actions.addParmTemplate(hou.ButtonParmTemplate("build_asset", "Build Asset Setup",
                                                   script_callback=_cb("on_build"),
                                                   script_callback_language=hou.scriptLanguage.Python))
    actions.addParmTemplate(hou.ButtonParmTemplate("sim_test", "Build Sim Test",
                                                   script_callback=_cb("on_sim_test"),
                                                   script_callback_language=hou.scriptLanguage.Python))
    actions.addParmTemplate(hou.ButtonParmTemplate("write_cache", "Write Rest Cache",
                                                   script_callback=_cb("on_write_cache"),
                                                   script_callback_language=hou.scriptLanguage.Python))

    for folder in (config, actions):
        g.append(folder)
    node.setParmTemplateGroup(g)


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
    """(fbx dict, hair_scale) — from the FBX subnet when built (source of truth),
    else from the config JSON file, else empty defaults."""

    sub = _fbx_subnet(node)
    if sub is not None and sub.parm("character_import"):
        return ({"asset_name": node.evalParm("asset"),
                 "root_name": sub.evalParm("root_name") or "root",
                 "pelvis_name": sub.evalParm("pelvis_name") or "pelvis",
                 "character_import": sub.evalParm("character_import") or None,
                 "hair_import": sub.evalParm("hair_import") or None},
                sub.evalParm("hair_scale"))
    import os
    path = node.evalParm("config_json")
    if path and os.path.isfile(path):
        try:
            data = json.loads(open(path, encoding="utf-8").read())
            block = data["asset"] if isinstance(data.get("asset"), dict) else data
            return (block.get("fbx", {"asset_name": node.evalParm("asset")}),
                    block.get("hair_scale", 0.01))
        except Exception:
            pass
    return {"asset_name": node.evalParm("asset")}, 0.01


def node_to_config(node) -> AssetSetupConfig:
    """Read the node into an :class:`AssetSetupConfig`. FBX/Hair come from the
    built FBX subnet (source of truth), falling back to the config file."""

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
    from .path_rules import PipelinePathRules
    rules = PipelinePathRules.from_dict(
        {"root": root, "context": {"asset_subpath": "assets/%s" % atype}})
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
    """Show a message dialog (headless-safe: prints when hou.ui is unavailable)."""

    try:
        import hou
        sev = {"message": hou.severityType.Message,
               "warning": hou.severityType.Warning,
               "error": hou.severityType.Error}.get(severity, hou.severityType.Message)
        hou.ui.displayMessage(msg, severity=sev, title="CFX Asset Setup")
    except Exception:
        print("[CFX %s] %s" % (severity.upper(), msg))


def _autofill_fbx_from_config(node, sub) -> None:
    """Pull the FBX subnet's Character FBX / Hair Guide paths from the cfx_asset
    config: resolve the RIG dirs from the control node's selection and set a
    sensible default file (only when the param is empty, so user picks persist)."""

    import os

    def pick(dirpath, prefer, exts):
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

    if sub.parm("character_import") and not sub.evalParm("character_import"):
        v = pick(_asset_dir(node, "character_fbx_dir"), ("sim",), (".fbx",))
        if v:
            sub.parm("character_import").set(v)
    if sub.parm("hair_import") and not sub.evalParm("hair_import"):
        v = pick(_asset_dir(node, "hair_guide_dir"), ("guides", "guide"), (".abc",))
        if v:
            sub.parm("hair_import").set(v)


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

    asset = node.evalParm("asset")
    container = node.node("%s_asset_setup" % asset) if asset else None
    if container is not None:
        _layout_recursive(container)


def on_build(node) -> dict[str, Any]:
    """Build the full asset setup (setup→corrective→collision→proxy→hair→constraint)
    inside this node from its parameters."""

    cfg = node_to_config(node)
    p = node.path()
    steps = [
        _asset.build_asset_setup, _asset.build_corrective, _asset.build_collision,
        _asset.build_proxy, _asset.build_hair_proxy, _asset.build_constraint,
    ]
    try:
        for fn in steps:
            fn(cfg, p)
    except Exception as exc:
        _popup("Build failed:\n%s" % exc, "error")
        raise
    sub = _fbx_subnet(node)
    if sub is not None:
        _add_fbx_scan_menus(sub)          # RIG file-scan menus on the FBX subnet
        _autofill_fbx_from_config(node, sub)  # pull default paths from cfx_asset config
    psub = _proxy_subnet(node)
    if psub is not None:
        _add_parts_buttons(psub)          # Auto-detect / Clear on the PROXY subnet
    _layout_asset(node)                   # tidy the whole network
    built = f"{p}/{cfg.asset}_asset_setup"
    _popup("Asset setup built.\n\nAsset: %s\nParts: %d\n%s"
           % (cfg.asset, len(cfg.proxy_parts), built))
    return {"built": built}


def on_sim_test(node) -> dict[str, Any]:
    try:
        res = _asset.build_asset_sim_test(node_to_config(node), node.path())
    except Exception as exc:
        _popup("Sim test build failed:\n%s" % exc, "error")
        raise
    _popup("Sim test built:\n%s\n\nScrub the timeline to check the drape."
           % res.get("out_sim_test", ""))
    return res


def on_write_cache(node) -> dict[str, Any]:
    try:
        res = _asset.build_rest_cache(node_to_config(node), node.path(), execute=True)
    except Exception as exc:
        _popup("Rest cache write failed:\n%s" % exc, "error")
        raise
    n = len(res.get("caches", []))
    warns = res.get("warnings") or []
    msg = "Rest cache written (%d cache(s))." % n
    if warns:
        msg += "\n\nWarnings:\n- " + "\n- ".join(warns)
    _popup(msg, "warning" if warns else "message")
    return res


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
        data = node_to_config(node).as_dict()
        data["path_rules"] = {
            "root": node.evalParm("project_root") or "Z:/show",
            "context": {"asset_subpath": "assets/%s" % (node.evalParm("asset_type") or "Character")},
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)  # create the asset dir if new
        Path(path).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        _popup("Save failed:\n%s\n\n%s" % (path, exc), "error")
        return
    _popup("Config saved.\n\nAsset: %s\nParts: %d\n%s"
           % (node.evalParm("asset"), len(_parts_data(node)), path))
