# -*- coding: utf-8 -*-
"""Stage 2 — Asset (character) setup, driven by :class:`AssetSetupConfig`.

Realizes the confirmed field-level authority model (see
``docs/CFX_ASSETS_HDA_ANALYSIS.md`` and the project memory):

* structural / identity / import fields  ->  pushed config -> HDA
* interactive tuning (T-pose, transform mult, ...)  ->  read back HDA -> config

This module is import-safe without Houdini; ``hou`` is required lazily so the
config helpers and tests run outside a Houdini session.
"""

from __future__ import annotations

from typing import Any

from .schema import AssetSetupConfig, FbxSetup


def _require_hou():
    try:
        import hou  # type: ignore
    except ImportError as exc:  # pragma: no cover - only in Houdini
        raise RuntimeError("asset_builder requires a Houdini session (hou)") from exc
    return hou


# FBX node field map: (config attr on FbxSetup, HDA parm name, kind).
#   kind: "s" str, "i" int, "f" float, "v3" 3-float tuple parm
FBX_STRUCTURAL: list[tuple[str, str, str]] = [
    ("asset_name", "asset_name", "s"),
    ("root_name", "root_name", "s"),
    ("pelvis_name", "pelvis_name", "s"),
    ("character_import", "character_import", "s"),
    ("hair_import", "hair_import", "s"),
    ("animation_import", "animation_import", "s"),
]
FBX_TUNING: list[tuple[str, str, str]] = [
    ("start_duration", "start_duration", "i"),
    ("end_duration", "end_duration", "i"),
    ("t_pose_start_position", "T_pose_start_position", "f"),
    ("t_pos", "T_pos", "f"),
    ("t_pos_offset_translate", "T_pos_ofs_translate", "v3"),
    ("t_pos_offset_rotate", "T_pos_ofs_rotate", "v3"),
    ("position_mult", "position_mult", "v3"),
    ("rotate_mult", "rotate_mul", "f"),
    ("pelvis_rotate", "pelvis_Rotate", "v3"),
]


def _set_parm(node, parm_name: str, kind: str, value: Any, warnings: list[str]) -> bool:
    if kind == "v3":
        pt = node.parmTuple(parm_name)
        if pt is None:
            warnings.append(f"tuple parm '{parm_name}' not found on {node.path()}")
            return False
        pt.set((float(value[0]), float(value[1]), float(value[2])))
        return True
    parm = node.parm(parm_name)
    if parm is None:
        warnings.append(f"parm '{parm_name}' not found on {node.path()}")
        return False
    parm.set(int(value) if kind == "i" else float(value) if kind == "f" else str(value))
    return True


def _get_parm(node, parm_name: str, kind: str) -> Any:
    if kind == "v3":
        pt = node.parmTuple(parm_name)
        return None if pt is None else tuple(round(float(x.eval()), 6) for x in pt)
    parm = node.parm(parm_name)
    if parm is None:
        return None
    if kind == "i":
        return int(parm.eval())
    if kind == "f":
        return round(float(parm.eval()), 6)
    return str(parm.eval())


def apply_fbx_setup(fbx_node, cfg: AssetSetupConfig, push_tuning: bool = False) -> dict[str, Any]:
    """Push config -> FBX node.

    By default only the config-authoritative structural fields (asset name,
    skeleton names, import paths) are written. Interactive tuning is left to
    the artist unless ``push_tuning`` is set (e.g. cloning a preset).
    Empty/None values are skipped so an unset config field never blanks the HDA.
    """

    fbx = cfg.fbx
    warnings: list[str] = []
    applied: list[str] = []
    table = FBX_STRUCTURAL + (FBX_TUNING if push_tuning else [])
    for attr, parm_name, kind in table:
        value = getattr(fbx, attr)
        if value is None or (kind == "s" and value == ""):
            continue
        if _set_parm(fbx_node, parm_name, kind, value, warnings):
            applied.append(parm_name)
    return {"applied": applied, "warnings": warnings, "push_tuning": push_tuning}


def read_fbx_setup(fbx_node) -> FbxSetup:
    """Read the FBX node back into a :class:`FbxSetup` (HDA -> config)."""

    data: dict[str, Any] = {}
    for attr, parm_name, kind in FBX_STRUCTURAL + FBX_TUNING:
        value = _get_parm(fbx_node, parm_name, kind)
        if value is not None:
            data[attr] = list(value) if kind == "v3" else value
    return FbxSetup.from_dict(data)


def skeleton_joint_names(skel_node) -> set[str]:
    """Set of joint ``name`` values on a skeleton geo (e.g. fbx capture pose)."""

    _require_hou()
    geo = skel_node.geometry()
    if geo is None or geo.findPointAttrib("name") is None:
        return set()
    return {pt.attribValue("name") for pt in geo.points()}


def validate_skeleton(skel_node, root_name: str | None, pelvis_name: str | None) -> dict[str, Any]:
    """Verify the config's root/pelvis joint names exist on the skeleton.

    Robust auto-derivation of the hierarchy root from a raw fbx capture pose
    proved unreliable (disjoint bone segments, non-hierarchy point order), and
    the config carries these names anyway (config-authoritative). So we
    validate rather than guess: missing names surface as a warning for the
    artist to correct in config.
    """

    names = skeleton_joint_names(skel_node)
    if not names:
        return {"ok": False, "error": "no 'name' attribute on skeleton geo"}
    warnings = []
    if root_name and root_name not in names:
        warnings.append(f"root joint '{root_name}' not found in skeleton")
    if pelvis_name and pelvis_name not in names:
        warnings.append(f"pelvis joint '{pelvis_name}' not found in skeleton")
    return {
        "ok": not warnings,
        "joint_count": len(names),
        "has_root": root_name in names if root_name else None,
        "has_pelvis": pelvis_name in names if pelvis_name else None,
        "warnings": warnings,
    }


# Anti-penetration push-apart (reconstructs collision_subnet/vdb_dist_attribute1).
# USED AT SHOT STAGE (Stage 3) on the ANIMATED collision, per-frame — kept here
# for the shot builder to reuse.
# on a peaked (inflated) surface, sample the surface's own SDF a little ahead
# along the normal; where that sample is inside (dist<0) the surface is
# self-intersecting (armpits/crotch/contact crevices where cloth would pinch and
# explode), so push the point back out by the penetration depth. Fully automatic
# from the SDF — no manual paint mask needed (the studio's attribpaint1 is
# optional and omitted by default to minimize hand-editing).
# Contact separation BEFORE the VDB (the point the user raised: body regions
# already touching, e.g. arm-vs-torso, fuse into one blob when VDB'd). Pure
# geometric auto-detection floods on anatomical thin features (lips/fingers/
# ears — ~15k pts on Jake), which is exactly why the studio used a hand paint
# here. So this is MASK-DRIVEN: the artist marks the few real contact zones in a
# `contact_mask` point group (their temp `check_point` group is the pattern) and
# those points are pulled inward by `gap` to open a sub-voxel gap. `@N` = point
# normal. The proportional voxel handles everything with a real gap already.
# "interaction" mode (default): within the artist `{mask}` region only, push a
# point inward by `{gap}` *only where it actually contacts another surface*
# (a point facing back at us, opposing normal, within `{radius}` and beyond the
# connected-neighbour `{mindist}`). The mask keeps it off anatomical thin
# features (fingers/lips); the interaction test opens just the real contacts
# (armpit/crotch) — this is the pre-VDB push the user asked for.
CONTACT_INTERACTION_VEX = """float w = point(0, "{mask}", @ptnum);   // painted weight 0..1
if (w <= 0.001) return;
int h = pcopen(0, "P", @P, {radius}, 200);
while (pciterate(h)) {{
    int nb = -1; float d = 0.0;
    pcimport(h, "point.number", nb);
    pcimport(h, "point.distance", d);
    if (nb == @ptnum || nb < 0 || d < {mindist}) continue;
    vector Nnb = point(0, "N", nb);
    if (dot(@N, Nnb) < {dot}) {{           // facing surface within mask = contact
        @P -= @N * {gap} * w;              // push scaled by paint weight
        setpointgroup(0, "pushed_contact", @ptnum, 1);
        break;
    }}
}}
"""

# "blanket" mode: push every painted point inward, scaled by paint weight.
CONTACT_BLANKET_VEX = """float w = point(0, "{mask}", @ptnum);
if (w > 0.001) @P -= @N * {gap} * w;
"""


PUSH_APART_VEX = """// input1 = SDF vdb of this (peaked) surface
vector P_sample = @P + @N * {sample};
float dist = volumesample(1, 0, P_sample);
if (dist < 0.0) {{
    @P -= @N * {move} * -dist;          // push out of the self-intersection
    setpointgroup(0, "pushed", @ptnum, 1);
}}
"""


# The gimmick that the whole Corrective/Proxy/Deform chain depends on: each
# skin-mesh primitive is named by its FBX mesh node; matching that name into the
# FBX node-graph output (out2, which carries `path`) yields the full hierarchy
# path stored as `geo_path`. (Reconstructs FBX/deform_subnet/attribwrangle10.)
GEO_PATH_VEX = """// primitive wrangle: input1 = FBX node graph (has point `name` + `path`)
int pt = findattribval(1, "point", "name", s@name);
if (pt >= 0)
    s@geo_path = point(1, "path", pt);
else
    warning("no node-graph path for mesh '%s'", s@name);
"""


def _child(parent, name: str, node_type: str):
    """Get-or-create a child node by name (idempotent builds)."""

    existing = parent.node(name)
    if existing is not None and existing.type().name() == node_type:
        return existing
    if existing is not None:
        existing.destroy()
    return parent.createNode(node_type, name)


def build_asset_setup(cfg: AssetSetupConfig, parent: str = "/obj") -> dict[str, Any]:
    """Stage 2 scaffold: import the character FBX into a clean geo container.

    Builds (idempotently) ``{parent}/{asset}_asset_setup`` with a stock
    ``kinefx::fbxcharacterimport`` and named rest outputs — the foundation the
    Corrective/Collision/Proxy chain will extend. Character only (no anim);
    the animation is a shot-stage concern.

    Outputs: ``REST_MESH`` (skinned rest geo, out0) and ``REST_SKEL``
    (capture-pose skeleton, out1).
    """

    hou = _require_hou()
    root = hou.node(parent)
    if root is None:
        raise ValueError(f"parent node not found: {parent}")

    geo = _child(root, f"{cfg.asset}_asset_setup", "geo")
    warnings: list[str] = []

    # FBX import lives in its own subnet whose parameters ARE the source of truth
    # (character/hair import, joint names, hair scale). Config seeds them only on
    # first creation; user edits on the subnet persist across rebuilds.
    fbx_existed = geo.node("FBX") is not None
    fbx = _child(geo, "FBX", "subnet")
    _fbx_subnet_params(fbx, cfg, seed=not fbx_existed)

    imp = _child(fbx, "fbx_import", "kinefx::fbxcharacterimport")
    imp.parm("fbxfile").setExpression('chs("../character_import")')
    if not cfg.fbx.character_import and not fbx_existed:
        warnings.append("character_import is empty; set it on the FBX subnet")

    # fbxcharacterimport outputs: 0=Rest Geometry (skin mesh), 1=Capture Pose
    # (skeleton), 2=Animated Pose (== full FBX node graph: path/name/fbx_node_type).
    node_graph = _child(fbx, "node_graph", "null")
    node_graph.setInput(0, imp, 2)
    skin_mesh = _child(fbx, "skin_mesh", "null")
    skin_mesh.setInput(0, imp, 0)
    add_geo_path = _child(fbx, "add_geo_path", "attribwrangle")
    add_geo_path.parm("class").set(1)  # primitives
    add_geo_path.parm("snippet").set(GEO_PATH_VEX)
    add_geo_path.setInput(0, skin_mesh, 0)
    add_geo_path.setInput(1, node_graph, 0)

    # hair guide import (studio Proxy/geo_hair_template01 head): alembic -> unpack
    # -> scale (Maya cm -> character m) -> hair guide.
    hair_abc = _child(fbx, "hair_import_abc", "alembic")
    hair_abc.parm("fileName").setExpression('chs("../hair_import")')
    if hair_abc.parm("addpath"):
        hair_abc.parm("addpath").set(1)
    hair_unpack = _child(fbx, "hair_unpack", "unpack")
    hair_unpack.setInput(0, hair_abc, 0)
    hair_xform = _child(fbx, "hair_xform", "xform")
    hair_xform.parm("scale").setExpression('ch("../hair_scale")')
    hair_xform.setInput(0, hair_unpack, 0)

    # subnet outputs: 0=rest mesh, 1=capture skeleton, 2=node graph, 3=hair guide
    for idx, src in ((0, add_geo_path), (1, imp), (2, node_graph), (3, hair_xform)):
        out = _child(fbx, "output%d" % idx, "output")
        out.parm("outputidx").set(idx)
        out.setInput(0, src, 1 if idx == 1 else 0)
    fbx.layoutChildren()

    # container-level named nulls wired to the FBX subnet outputs (downstream
    # Corrective/Collision/Proxy still reference these by name, unchanged).
    rest_mesh = _child(geo, "REST_MESH", "null"); rest_mesh.setInput(0, fbx, 0)
    rest_skel = _child(geo, "REST_SKEL", "null"); rest_skel.setInput(0, fbx, 1)
    ngraph = _child(geo, "NODE_GRAPH", "null"); ngraph.setInput(0, fbx, 2)
    hair_guide = _child(geo, "HAIR_GUIDE", "null"); hair_guide.setInput(0, fbx, 3)
    rest_mesh.setDisplayFlag(True)

    # retire the old flat FBX nodes from the pre-subnet layout
    for stale in ("fbx_import", "skin_mesh", "add_geo_path", "hair_import_abc",
                  "hair_unpack", "hair_xform"):
        n = geo.node(stale)
        if n is not None:
            n.destroy()

    geo.layoutChildren()
    return {
        "container": geo.path(), "fbx_subnet": fbx.path(),
        "rest_mesh": rest_mesh.path(), "rest_skel": rest_skel.path(),
        "node_graph": ngraph.path(), "hair_guide": hair_guide.path(),
        "warnings": warnings,
    }


def _fbx_subnet_params(fbx, cfg: AssetSetupConfig, seed: bool) -> None:
    """Add the FBX-stage parameters to the FBX subnet (idempotent). ``seed``
    (first build only) fills them from config so later user edits persist."""

    hou = _require_hou()
    file_t = hou.stringParmType.FileReference
    g = fbx.parmTemplateGroup()
    specs = [
        hou.StringParmTemplate("character_import", "Character FBX", 1, string_type=file_t),
        hou.StringParmTemplate("hair_import", "Hair Guide", 1, string_type=file_t),
        hou.StringParmTemplate("root_name", "Root Joint", 1, default_value=("root",)),
        hou.StringParmTemplate("pelvis_name", "Pelvis Joint", 1, default_value=("pelvis",)),
        hou.FloatParmTemplate("hair_scale", "Hair Scale", 1, default_value=(0.01,)),
    ]
    changed = False
    for pt in specs:
        if g.find(pt.name()) is None:
            g.append(pt)
            changed = True
    if changed:
        fbx.setParmTemplateGroup(g)
    if seed:
        fbx.parm("character_import").set(cfg.fbx.character_import or "")
        fbx.parm("hair_import").set(cfg.fbx.hair_import or "")
        fbx.parm("root_name").set(cfg.fbx.root_name or "root")
        fbx.parm("pelvis_name").set(cfg.fbx.pelvis_name or "pelvis")
        fbx.parm("hair_scale").set(cfg.hair_scale)


PROXY_PATH_VEX = 's@proxy_path = "{proxy_path}";   // tag the part proxy for Deform pairing\n'

# Rest hair root-finding (reconstructs geo_hair_template01/attribwrangle1). Prim
# wrangle over hair curves: input1 = scalp/head mesh; the curve vertex nearest
# the scalp is the hair root -> "FirstPoints" (pin), the next vertex ->
# "SecondPoints" (root direction). The head-follow (animation) is a SHOT step and
# is skipped here; this is the rest setup below `follow_hair`.
HAIR_ROOT_VEX = """int nverts = @numvtx;
float min_dist = 1e9;
int start_local = -1;
for (int i = 0; i < nverts; i++) {
    int pt = vertexpoint(0, primvertex(0, @primnum, i));
    vector pos = point(0, "P", pt);
    float d = distance(pos, minpos(1, pos));
    if (d < min_dist) { min_dist = d; start_local = i; }
}
if (start_local < 0) return;
setpointgroup(0, "FirstPoints", vertexpoint(0, primvertex(0, @primnum, start_local)), 1, "set");
int next_local = (start_local + 1 < nverts) ? start_local + 1 : start_local - 1;
setpointgroup(0, "SecondPoints", vertexpoint(0, primvertex(0, @primnum, next_local)), 1, "set");
"""


def _asset_geo(cfg: AssetSetupConfig, parent: str):
    hou = _require_hou()
    geo = hou.node(f"{parent}/{cfg.asset}_asset_setup")
    if geo is None:
        raise ValueError(f"run build_asset_setup first ({cfg.asset}_asset_setup not found)")
    return geo


def _stage_subnet(geo, name: str, *src_nodes):
    """Get-or-create a stage subnet in the container, wiring its external inputs
    from the given upstream container nodes. Internal nodes read the inputs via
    ``sub.indirectInputs()[i]``; a final ``output`` node exposes the result to
    the container. Keeps each stage tidy (see the FBX subnet pattern)."""

    sub = _child(geo, name, "subnet")
    for i, s in enumerate(src_nodes):
        if s is not None:
            sub.setInput(i, s, 0)
    return sub


def _stage_output(sub, src, idx: int = 0):
    """Wire an ``output`` node (index ``idx``) inside a stage subnet to ``src``."""

    out = _child(sub, "output%d" % idx, "output")
    if out.parm("outputidx"):
        out.parm("outputidx").set(idx)
    out.setInput(0, src, 0)
    return out


def build_corrective(cfg: AssetSetupConfig, parent: str = "/obj") -> dict[str, Any]:
    """Stage 2.3a — Corrective: split BODY vs CLOTH, gate cloth for manual edit.

    Built inside a ``CORRECTIVE`` subnet (input = REST_MESH, output ->
    OUT_CORRECTIVE): ``connectivity`` tags a per-piece ``@class`` (so downstream
    stages can reference it) -> ``split`` by ``collision_pattern`` (out0 = BODY =
    skin/head, out1 = cloth) -> ``edit`` (empty manual gate) -> merge -> output.
    """

    geo = _asset_geo(cfg, parent)
    src = geo.node("REST_MESH")
    if src is None:
        raise ValueError("REST_MESH missing; run build_asset_setup first")

    sub = _stage_subnet(geo, "CORRECTIVE", src)
    inp = sub.indirectInputs()[0]
    # Tag a per-connected-piece @class up front so every downstream stage that
    # reads OUT_CORRECTIVE can reference it. Primitive connectivity (connecttype=1).
    conn = _child(sub, "connectivity1", "connectivity")
    if conn.parm("connecttype"):
        conn.parm("connecttype").set(1)
    conn.setInput(0, inp)
    # Split BODY/CLOTH directly by geo_path pattern.
    split = _child(sub, "cor_split", "split")
    split.parm("group").set(cfg.collision_pattern)  # out0 in-group, out1 out-group
    split.setInput(0, conn, 0)
    body = _child(sub, "BODY", "null")
    body.setInput(0, split, 0)
    edit = _child(sub, "cor_edit", "edit")  # manual corrective gate (starts empty)
    edit.setInput(0, split, 1)
    cloth = _child(sub, "CLOTH", "null")
    cloth.setInput(0, edit, 0)
    merge = _child(sub, "cor_merge", "merge")
    merge.setInput(0, body, 0)
    merge.setInput(1, cloth, 0)
    _stage_output(sub, merge)
    sub.layoutChildren()

    out = _child(geo, "OUT_CORRECTIVE", "null")
    out.setInput(0, sub, 0)
    out.setDisplayFlag(True)
    # retire the old flat corrective nodes from the pre-subnet layout
    for stale in ("cor_split", "BODY", "cor_edit", "CLOTH", "cor_merge"):
        n = geo.node(stale)
        if n is not None:
            n.destroy()
    geo.layoutChildren()
    return {"corrective_subnet": sub.path(), "edit": edit.path(),
            "out_corrective": out.path()}


def _collision_params(sub, cfg: AssetSetupConfig, seed: bool) -> None:
    """Add the collision authoring params (body pattern + voxel ratio) to the
    COLLISION subnet — the collision source of truth. ``seed`` (first build)
    fills them from config so later edits on the subnet persist."""

    hou = _require_hou()
    g = sub.parmTemplateGroup()
    changed = False
    if g.find("collision_pattern") is None:
        g.append(hou.StringParmTemplate(
            "collision_pattern", "Collision Body Pattern", 1,
            default_value=("@geo_path=*body* @geo_path=*head*",)))
        changed = True
    if g.find("voxel_ratio") is None:
        g.append(hou.FloatParmTemplate("voxel_ratio", "Collision Voxel Ratio", 1,
                                       default_value=(0.005,)))
        changed = True
    if changed:
        sub.setParmTemplateGroup(g)
    if seed:
        sub.parm("collision_pattern").set(
            cfg.collision_pattern or "@geo_path=*body* @geo_path=*head*")
        vr = cfg.collision.get("voxel_ratio")
        if vr is not None:
            sub.parm("voxel_ratio").set(float(vr))


def build_collision(cfg: AssetSetupConfig, parent: str = "/obj") -> dict[str, Any]:
    """Stage 2.3b — Collision: watertight collision surface from the body geo.

    ``blast`` keeps only ``collision_pattern`` (negate) -> VDB reshrink
    (``vdbfrompolygons`` SDF -> ``convertvdb`` polygons) -> ``smooth`` -> a
    primitive group -> optional scale -> OUT_COLLISION. The studio's
    animation-driven blendshape/pointdeform steps are shot-stage and omitted
    at asset rest.
    """

    geo = _asset_geo(cfg, parent)
    src = geo.node("OUT_CORRECTIVE")
    if src is None:
        raise ValueError("OUT_CORRECTIVE missing; run build_corrective first")

    sub = _stage_subnet(geo, "COLLISION", src)
    # collision authoring params live on the COLLISION subnet (source of truth);
    # config only seeds them the first time the subnet is created.
    had_params = sub.parm("collision_pattern") is not None
    _collision_params(sub, cfg, seed=not had_params)
    inp = sub.indirectInputs()[0]
    col = dict(cfg.collision)
    col["voxel_ratio"] = sub.evalParm("voxel_ratio")   # subnet param wins
    blast = _child(sub, "col_blast", "blast")
    # live-reference the subnet's body pattern so editing it updates immediately
    blast.parm("group").setExpression('chs("../collision_pattern")',
                                      _require_hou().exprLanguage.Hscript)
    blast.parm("negate").set(1)  # keep only the pattern (body/head)
    blast.setInput(0, inp)

    # Proportional sizing off the body bbox so a value tuned on one character
    # carries to any other scale. `voxel_size` (absolute) overrides the ratio.
    blast.cook(force=True)
    diag = blast.geometry().boundingBox().sizevec().length() or 1.0
    voxel = float(col["voxel_size"]) if col.get("voxel_size") else diag * float(
        col.get("voxel_ratio", 0.005))

    # Optional mask-driven contact separation before voxelising (see
    # CONTACT_SEPARATE_VEX). Off by default — the proportional voxel already
    # keeps any real gap open; this is only for truly-touching sub-voxel zones.
    vdb_src = blast
    if col.get("contact_check", True):  # mask-corrective on by default (safe when unpainted)
        mask = col.get("contact_mask", "check_point")
        col_mask = _child(sub, "col_mask", "attribpaint")
        col_mask.parm("numattribs").set(1)
        col_mask.parm("attribname1").set(mask)
        col_mask.setInput(0, blast, 0)
        nrm = _child(sub, "col_normal", "normal")
        nrm.parm("type").set(0)  # point normals (needed for @N)
        nrm.setInput(0, col_mask, 0)
        contact = _child(sub, "col_contact", "attribwrangle")
        contact.parm("class").set(2)  # points (0=detail,1=prim,2=point)
        gap = float(col.get("contact_gap", diag * 0.0025))
        if col.get("contact_mode", "interaction") == "blanket":
            snippet = CONTACT_BLANKET_VEX.format(mask=mask, gap=gap)
        else:  # interaction: push only where a masked point contacts a surface
            snippet = CONTACT_INTERACTION_VEX.format(
                mask=mask, gap=gap,
                radius=float(col.get("contact_radius", diag * 0.02)),
                mindist=float(col.get("contact_mindist", diag * 0.003)),
                dot=float(col.get("contact_dot", -0.3)))
        contact.parm("snippet").set(snippet)
        contact.setInput(0, nrm, 0)
        vdb_src = contact
        if col.get("contact_smooth", True):
            csm = _child(sub, "col_contact_smooth", "smooth::2.0")
            csm.parm("strength").set(float(col.get("contact_smooth_strength", 5.0)))
            csm.parm("useweightattribute").set(1)
            csm.parm("weightattribute").set(mask)
            csm.setInput(0, contact, 0)
            vdb_src = csm
    else:  # keep the subnet clean when disabled
        for stale in ("col_contact_smooth", "col_contact", "col_normal", "col_mask"):
            n = sub.node(stale)
            if n is not None:
                n.destroy()

    vdb = _child(sub, "col_vdbfrompolygons", "vdbfrompolygons")
    vdb.parm("voxelsize").set(voxel)
    vdb.setInput(0, vdb_src, 0)
    convert = _child(sub, "col_convertvdb", "convertvdb")
    convert.parm("conversion").set("poly")  # SDF VDB -> watertight polygons
    convert.setInput(0, vdb, 0)
    smooth = _child(sub, "col_smooth", "smooth::2.0")
    smooth.setInput(0, convert, 0)

    # push-apart is a SHOT-stage per-frame op (see PUSH_APART_VEX); asset builds
    # only the clean REST surface. Clean up any push nodes from earlier builds.
    for stale in ("col_peak", "col_push_vdb", "col_push",
                  "col_push_expand", "col_push_smooth"):
        n = sub.node(stale)
        if n is not None:
            n.destroy()

    grp = _child(sub, "col_group", "groupcreate")
    grp.parm("grouptype").set(0)  # 0 = primitive
    grp.parm("groupname").set(f"{cfg.asset}_collision")
    grp.parm("basegroup").set("*")  # include all prims in the named group
    grp.setInput(0, smooth, 0)

    scale = float(cfg.collision.get("scale", 1.0))
    xf = _child(sub, "col_transform", "xform")
    if xf.parm("scale"):
        xf.parm("scale").set(scale)
    xf.setInput(0, grp, 0)
    _stage_output(sub, xf)
    sub.layoutChildren()

    col_out = _child(geo, "OUT_COLLISION", "null")
    col_out.setInput(0, sub, 0)
    # retire the old flat collision nodes from the pre-subnet layout
    for stale in ("col_blast", "col_mask", "col_normal", "col_contact",
                  "col_contact_smooth", "col_vdbfrompolygons", "col_convertvdb",
                  "col_smooth", "col_group", "col_transform"):
        n = geo.node(stale)
        if n is not None:
            n.destroy()
    geo.layoutChildren()
    return {"collision_subnet": sub.path(), "out_collision": col_out.path(),
            "voxel_size": round(voxel, 5), "bbox_diag": round(diag, 4),
            "contact_check": col.get("contact_check", True), "scale": scale}


def _proxy_parts_multiparm(sub, cfg: AssetSetupConfig, seed: bool) -> None:
    """Add the Cloth/Hair Parts multiparm to the PROXY subnet (the parts source
    of truth). ``seed`` (first build) fills it from config so later user edits on
    the subnet persist. ``part_cloth`` classifies cloth (on) vs hair (off)."""

    hou = _require_hou()
    g = sub.parmTemplateGroup()
    if g.find("parts") is None:
        folder = hou.FolderParmTemplate("parts", "Cloth / Hair Parts",
                                        folder_type=hou.folderType.MultiparmBlock)
        folder.addParmTemplate(hou.StringParmTemplate("part_name_#", "Part Name", 1))
        folder.addParmTemplate(hou.StringParmTemplate("part_geo_#", "Geo Path (@geo_path)", 1))
        folder.addParmTemplate(hou.ToggleParmTemplate("part_cloth_#", "Cloth (off = Hair)",
                                                      default_value=True))
        g.append(folder)
        sub.setParmTemplateGroup(g)
    if seed:
        sub.parm("parts").set(len(cfg.proxy_parts))
        for i, p in enumerate(cfg.proxy_parts, start=1):
            sub.parm("part_name_%d" % i).set(p.name)
            sub.parm("part_geo_%d" % i).set(p.geo_path[0] if p.geo_path else "")
            sub.parm("part_cloth_%d" % i).set(int(p.cloth))


def _parts_from_node(node) -> list:
    """Read a Parts multiparm (``part_name_#``/``part_geo_#``/``part_cloth_#``)
    into a list of :class:`ProxyPart`."""

    from .schema import ProxyPart
    n = node.parm("parts").eval() if node.parm("parts") else 0
    parts = []
    for i in range(1, n + 1):
        nm = node.evalParm("part_name_%d" % i)
        if not nm:
            continue
        geo = node.evalParm("part_geo_%d" % i)
        parts.append(ProxyPart(name=nm, geo_path=[geo] if geo else [],
                               cloth=bool(node.evalParm("part_cloth_%d" % i))))
    return parts


def _tag_proxy_path_in_copy(node, proxy_path: str) -> None:
    """Ensure a ``proxypath`` wrangle inside a cloth_ref copy tags ``@proxy_path``
    (just before its output null) so downstream stages pair parts as before."""

    out_null = node.node("parts_proxy_OUTPUT")
    if out_null is None:
        return
    tag = node.node("proxypath")
    if tag is None:
        upstream = out_null.inputs()[0] if out_null.inputs() else None
        tag = node.createNode("attribwrangle", "proxypath")
        tag.parm("class").set(1)  # primitives
        if upstream is not None:
            tag.setInput(0, upstream, 0)
        out_null.setInput(0, tag, 0)
    tag.parm("snippet").set(PROXY_PATH_VEX.format(proxy_path=proxy_path))


def _ensure_cloth_ref(sub):
    """Ensure a default ``cloth_ref`` template exists inside the PROXY subnet so
    Generate Structure always has a recipe to instance. The artist edits it (and
    may add per-part sub-group blasts); returns the existing one if present.

    Default recipe: ``parts_name`` (blast — the per-part isolation node) ->
    ``remesh1`` -> ``normal1`` -> ``parts_proxy_OUTPUT`` (null) -> ``output0``."""

    ref = sub.node("cloth_ref")
    if ref is not None:
        return ref
    ref = sub.createNode("subnet", "cloth_ref")
    for d in list(ref.children()):   # start from a clean subnet
        d.destroy()
    ref.setInput(0, sub.indirectInputs()[0])  # activate the subnet's indirect input
    pn = ref.createNode("blast", "parts_name")
    pn.parm("group").set("@name=parts_name")  # placeholder; _instance overrides
    pn.parm("negate").set(1)
    pn.setInput(0, ref.indirectInputs()[0])
    rm = ref.createNode("remesh::2.0", "remesh1")
    if rm.parm("targetsize"):
        rm.parm("targetsize").set(0.05)
    if rm.parm("hardenuvseams"):
        rm.parm("hardenuvseams").set(1)
    rm.setInput(0, pn, 0)
    nm = ref.createNode("normal", "normal1")
    nm.setInput(0, rm, 0)
    out_null = ref.createNode("null", "parts_proxy_OUTPUT")
    out_null.setInput(0, nm, 0)
    o0 = ref.createNode("output", "output0")
    o0.setInput(0, out_null, 0)
    ref.layoutChildren()
    return ref


def _copy_recipe_into_subnet(ref, dest) -> None:
    """Copy a template subnet's CHILDREN into a fresh subnet and reconnect any
    connection that referenced the template's indirect inputs to ``dest``'s.

    A wholesale ``copyNodesTo([ref])`` of a collapsed subnet keeps its broken
    output routing (output 0 passes the input straight through). Copying the
    children into a fresh subnet routes output 0 to the ``output`` node
    correctly — but the internal indirect-input wiring must be redone by hand."""

    hou = _require_hou()
    ref_ind = list(ref.indirectInputs())
    conns = []  # (child_name, input_idx, indirect_idx)
    for c in ref.children():
        for conn in c.inputConnections():
            item = conn.inputItem()
            if item in ref_ind:
                conns.append((c.name(), conn.inputIndex(), ref_ind.index(item)))
    hou.copyNodesTo(list(ref.children()), dest)
    dest_ind = list(dest.indirectInputs())
    for cname, iidx, indidx in conns:
        cn = dest.node(cname)
        if cn is not None and indidx < len(dest_ind):
            cn.setInput(iidx, dest_ind[indidx])


def _instance_cloth_ref(sub, parts, merge) -> list:
    """Auto-generate the cloth proxy structure by instancing the user's
    ``cloth_ref`` template once per cloth part. Each copy (``cloth_{part}``)
    isolates the part via its ``parts_name`` blast (``@name=``), drops the
    template's empty ``parts_blast01/02`` placeholders (the worker adds per-part
    sub-group blasts by hand if needed), takes the part's remesh size, tags
    ``@proxy_path``, and feeds ``proxy_merge``.

    Copies are rebuilt fresh each call. A wholesale copy of ``cloth_ref``
    (a collapsed subnet) keeps its broken output routing — its output 0 passes
    the input straight through — so instead each copy is a NEW subnet with the
    template's *children* copied in, which routes output 0 to ``output0``
    correctly. The template itself is left untouched."""

    ref = _ensure_cloth_ref(sub)  # default template if the artist hasn't made one
    inp = sub.indirectInputs()[0]
    for c in list(sub.children()):  # rebuild all copies fresh
        if c.name().startswith("cloth_") and c.name() != "cloth_ref":
            c.destroy()
    made = []
    for idx, part in enumerate(parts):
        nm = "cloth_%s" % part.name
        node = sub.createNode("subnet", nm)      # fresh subnet (clean output)
        _copy_recipe_into_subnet(ref, node)       # copy recipe + reconnect input
        node.setInput(0, inp)

        sel = part.geo_path[0].rsplit("/", 1)[-1] if part.geo_path else part.name
        blast = node.node("parts_name")
        if blast is not None:
            # exact @name match (unquoted — Houdini treats quotes literally here)
            blast.parm("group").set("@name=%s" % sel)
            blast.parm("negate").set(1)  # keep ONLY this part (isolate the garment)
        # drop the empty placeholder sub-group blasts; wire remesh straight off
        # the isolated part (the worker re-adds sub-group blasts by hand if wanted)
        remesh = node.node("remesh1")
        if remesh is not None and blast is not None:
            remesh.setInput(0, blast, 0)
        for extra in ("parts_blast01", "parts_blast02"):
            n2 = node.node(extra)
            if n2 is not None:
                n2.destroy()
        if remesh is not None and part.parameters.get("remesh_size") is not None:
            remesh.parm("targetsize").set(float(part.parameters["remesh_size"]))
        _tag_proxy_path_in_copy(node, part.proxy_path or part.name)
        # wire the subnet output to the end of the chain
        out0 = node.node("output0")
        end = node.node("parts_proxy_OUTPUT")
        if out0 is not None and end is not None:
            out0.setInput(0, end, 0)
            end.setDisplayFlag(True)
            end.setRenderFlag(True)
        node.layoutChildren()      # tidy the copy's internal chain
        merge.setInput(idx, node, 0)
        made.append(nm)
    return made


def build_proxy(cfg: AssetSetupConfig, parent: str = "/obj") -> dict[str, Any]:
    """Stage 2.4 — per-part cloth proxy (low-res sim mesh).

    Reconstructs the studio ``Proxy/geo_template01`` (its scatter->vdb branch is
    a dead end; the live proxy is the remeshed garment): for each cloth part,
    blast its ``geo_path`` out of the corrected mesh, remesh to a low-res proxy,
    tag ``proxy_path`` (for Deform pairing), output ``OUT_{part}_PROXY``. All
    part proxies merge into ``OUT_PROXY``.

    Parts are authored in config (``proxy_parts``, seeded from the artist's
    interactive selection); ``geo_path`` is the original garment group.
    """

    geo = _asset_geo(cfg, parent)
    src = geo.node("OUT_CORRECTIVE")
    if src is None:
        raise ValueError("OUT_CORRECTIVE missing; run build_corrective first")

    sub = _stage_subnet(geo, "PROXY", src)
    # Parts are authored on the PROXY subnet (source of truth); config only seeds
    # the multiparm the first time it is created so later user edits persist.
    had_parts = sub.parm("parts") is not None
    _proxy_parts_multiparm(sub, cfg, seed=not had_parts)
    inp = sub.indirectInputs()[0]
    all_parts = _parts_from_node(sub)
    parts = [p for p in all_parts if p.cloth]

    # Auto-generate the structure by instancing the ``cloth_ref`` template per
    # cloth part (a default template is created if the artist hasn't made one).
    ref = _ensure_cloth_ref(sub)
    if ref is not None:
        cloth = [p for p in parts if p.geo_path]
        merge = _child(sub, "proxy_merge", "merge")
        made = _instance_cloth_ref(sub, cloth, merge)
        _stage_output(sub, merge)
        for c in list(sub.children()):  # drop any leftover flat px_* chain
            nm = c.name()
            if nm.startswith("px_") or (nm.startswith("OUT_") and nm.endswith("_PROXY")):
                c.destroy()
        sub.layoutChildren()
        out_proxy = _child(geo, "OUT_PROXY", "null")
        out_proxy.setInput(0, sub, 0)
        out_proxy.setDisplayFlag(True)
        geo.layoutChildren()
        return {
            "proxy_subnet": sub.path(), "out_proxy": out_proxy.path(),
            "mode": "cloth_ref", "generated": made,
            "warnings": [f"part '{p.name}' has no geo_path; skipped"
                         for p in parts if not p.geo_path],
        }

    outs: list = []
    warnings: list[str] = []
    for part in parts:
        if not part.geo_path:
            warnings.append(f"part '{part.name}' has no geo_path; skipped")
            continue
        pfx = f"px_{part.name}"
        blast = _child(sub, f"{pfx}_blast", "blast")
        blast.parm("group").set(part.geo_group())  # @geo_path=... (may be several)
        blast.parm("negate").set(1)  # keep only this part's geo
        blast.setInput(0, inp)

        remesh = _child(sub, f"{pfx}_remesh", "remesh::2.0")
        remesh.parm("targetsize").set(float(part.parameters.get("remesh_size", 0.01)))
        if remesh.parm("iterations"):
            remesh.parm("iterations").set(2)
        remesh.setInput(0, blast, 0)

        tag = _child(sub, f"{pfx}_proxypath", "attribwrangle")
        tag.parm("class").set(1)  # primitives
        tag.parm("snippet").set(PROXY_PATH_VEX.format(proxy_path=part.proxy_path or part.name))
        tag.setInput(0, remesh, 0)

        out = _child(sub, f"OUT_{part.name}_PROXY", "null")
        out.setInput(0, tag, 0)
        outs.append(out)

    proxy_merge = _child(sub, "proxy_merge", "merge")
    for i, o in enumerate(outs):
        proxy_merge.setInput(i, o, 0)
    _stage_output(sub, proxy_merge)
    sub.layoutChildren()

    out_proxy = _child(geo, "OUT_PROXY", "null")
    out_proxy.setInput(0, sub, 0)
    out_proxy.setDisplayFlag(True)
    # retire the old flat cloth-proxy nodes from the pre-subnet layout
    stale = ["proxy_merge"]
    for p in parts:
        stale += [f"px_{p.name}_blast", f"px_{p.name}_remesh",
                  f"px_{p.name}_proxypath", f"OUT_{p.name}_PROXY"]
    for nm in stale:
        n = geo.node(nm)
        if n is not None:
            n.destroy()
    geo.layoutChildren()
    return {
        "proxy_subnet": sub.path(), "out_proxy": out_proxy.path(),
        "parts": [{"name": p.name, "out": f"OUT_{p.name}_PROXY"} for p in parts if p.geo_path],
        "warnings": warnings,
    }


def build_hair_proxy(cfg: AssetSetupConfig, parent: str = "/obj") -> dict[str, Any]:
    """Stage 2.4 — rest hair proxy from the imported guide (no head-follow).

    Reconstructs the rest part of ``geo_hair_template01`` (below ``follow_hair``):
    resample the guide curves, then find each curve's root (vertex nearest the
    scalp) into ``FirstPoints``/``SecondPoints`` for pinning. The
    ``apply_head_follow`` step (hair tracking the ANIMATED head joint) is a shot
    stage concern and is intentionally omitted here.
    """

    geo = _asset_geo(cfg, parent)
    guide = geo.node("HAIR_GUIDE")
    if guide is None:
        return {"skipped": "no HAIR_GUIDE (cfg.fbx.hair_import empty)"}
    # hair parts come from the PROXY subnet's Parts multiparm (parts source of
    # truth); fall back to config if the PROXY stage hasn't been built yet.
    proxy_sub = geo.node("PROXY")
    src_parts = _parts_from_node(proxy_sub) if proxy_sub is not None else cfg.proxy_parts
    hair_parts = [p for p in src_parts if not p.cloth]
    if not hair_parts:
        return {"skipped": "no hair parts (all proxy_parts are cloth)"}

    # HAIR subnet: input0 = HAIR_GUIDE, input1 = REST_MESH (scalp source)
    sub = _stage_subnet(geo, "HAIR", guide, geo.node("REST_MESH"))
    guide_in = sub.indirectInputs()[0]
    scalp = _child(sub, "hair_scalp", "blast")
    scalp.parm("group").set(cfg.collision.get("hair_scalp_pattern", "@geo_path=*head*"))
    scalp.parm("negate").set(1)  # keep only the head
    scalp.setInput(0, sub.indirectInputs()[1])

    outs: list = []
    for part in hair_parts:
        pfx = f"hx_{part.name}"
        src = guide_in
        if part.geo_path:  # optional: isolate a subset of the guide
            b = _child(sub, f"{pfx}_blast", "blast")
            b.parm("group").set(part.geo_group())
            b.parm("negate").set(1)
            b.setInput(0, guide_in)
            src = b

        resample = _child(sub, f"{pfx}_resample", "resample")
        resample.parm("dolength").set(1)
        resample.parm("length").set(float(part.parameters.get("resample_length", 0.02)))
        resample.setInput(0, src, 0)

        root = _child(sub, f"{pfx}_root", "attribwrangle")
        root.parm("class").set(1)  # run over primitives (curves)
        root.parm("snippet").set(HAIR_ROOT_VEX)
        root.setInput(0, resample, 0)
        root.setInput(1, scalp, 0)

        tag = _child(sub, f"{pfx}_proxypath", "attribwrangle")
        tag.parm("class").set(1)
        tag.parm("snippet").set(PROXY_PATH_VEX.format(proxy_path=part.proxy_path or part.name))
        tag.setInput(0, root, 0)

        out = _child(sub, f"OUT_{part.name}_PROXY", "null")
        out.setInput(0, tag, 0)
        outs.append(out)

    # retire stale per-part hair nodes inside the subnet (removed hair parts)
    wanted = {"hair_scalp", "hair_proxy_merge"}
    for p in hair_parts:
        wanted |= {f"hx_{p.name}_blast", f"hx_{p.name}_resample", f"hx_{p.name}_root",
                   f"hx_{p.name}_proxypath", f"OUT_{p.name}_PROXY"}
    for c in list(sub.children()):
        nm = c.name()
        if nm in ("output0",) or nm in wanted:
            continue
        if nm.startswith("hx_") or (nm.startswith("OUT_") and nm.endswith("_PROXY")):
            c.destroy()

    hair_merge = _child(sub, "hair_proxy_merge", "merge")
    for i, o in enumerate(outs):
        hair_merge.setInput(i, o, 0)
    _stage_output(sub, hair_merge)
    sub.layoutChildren()

    out_hair = _child(geo, "OUT_HAIR_PROXY", "null")
    out_hair.setInput(0, sub, 0)
    # retire the old flat hair-proxy nodes from the pre-subnet layout
    stale = ["hair_scalp", "hair_proxy_merge"]
    for p in hair_parts:
        stale += [f"hx_{p.name}_blast", f"hx_{p.name}_resample",
                  f"hx_{p.name}_root", f"hx_{p.name}_proxypath", f"OUT_{p.name}_PROXY"]
    for nm in stale:
        n = geo.node(nm)
        if n is not None:
            n.destroy()
    geo.layoutChildren()
    return {"hair_subnet": sub.path(), "out_hair_proxy": out_hair.path(),
            "parts": [p.name for p in hair_parts]}


# default point group a hair guide pins by its root (set by HAIR_ROOT_VEX).
HAIR_ROOT_GROUP = "FirstPoints"

# Head-follow (reconstructs Proxy/geo_hair_template01 compute_head_xform +
# apply_head_follow). Hair rides the animated head joint rigidly instead of the
# full-body cage pointDeform. HEAD_DELTA_VEX (detail, in0=animated skeleton,
# in1=rest skeleton) computes the rest->anim head world-matrix delta; the studio
# builds an orthonormal 4x4 from the head joint's transform + P.
HEAD_DELTA_VEX = """matrix headmat(int inp; int h) {
    matrix3 r = point(inp, "transform", h);
    vector p = point(inp, "P", h);
    vector ax = normalize(set(getcomp(r,0,0), getcomp(r,0,1), getcomp(r,0,2)));
    vector ay = normalize(set(getcomp(r,1,0), getcomp(r,1,1), getcomp(r,1,2)));
    vector az = normalize(set(getcomp(r,2,0), getcomp(r,2,1), getcomp(r,2,2)));
    matrix m = matrix(set(ax, ay, az));
    setcomp(m, p.x, 3, 0); setcomp(m, p.y, 3, 1); setcomp(m, p.z, 3, 2);
    return m;
}
int findhead(int inp; string hn) {
    for (int i = 0; i < npoints(inp); i++)
        if (point(inp, "name", i) == hn) return i;
    return -1;
}
int ha = findhead(0, "__HEAD__");
int hr = findhead(1, "__HEAD__");
if (ha < 0 || hr < 0) { 4@head_delta = ident(); return; }
4@head_delta = invert(headmat(1, hr)) * headmat(0, ha);
"""

# Apply the head delta to the rest hair (point wrangle, in0 = hair, in1 = delta).
HEAD_APPLY_VEX = """matrix m = detail(1, "head_delta");
@P *= m;
if (haspointattrib(0, "N")) @N = normalize(@N * matrix3(m));
if (haspointattrib(0, "v")) @v *= matrix3(m);
"""


def _cparm(part, con: dict[str, Any], key: str, default: Any) -> Any:
    """Per-part parameter with fallback: part.parameters -> cfg.constraint -> default."""

    if key in part.parameters:
        return part.parameters[key]
    return con.get(key, default)


def build_vellum_chain(geo, parts, con: dict[str, Any], src_for_part,
                       rest_cage=None, anim_cage=None,
                       rest_skel=None, anim_skel=None) -> dict[str, Any]:
    """Shared PER-PART vellum constraint chain (used by asset + shot).

    For each part::

        cloth: proxy -> pointDeform(rest_cage -> anim_cage) -> vellumconstraints
                     -> vellumrestblend(rest = proxy) [-> pin] -> vellumpack
        hair:  proxy -> head-follow(rest_skel -> anim_skel) -> vellumconstraints
                     [-> pin] -> vellumpack
        ... -> merge -> OUT_CONSTRAINT

    The DEFORM sits UPSTREAM of the constraints (per the confirmed HDA model).
    CLOTH parts pointDeform to the animated pose by the full-body cage; HAIR
    parts instead ride the animated HEAD joint rigidly (head-follow, from
    geo_hair_template01) — passed ``rest_skel``/``anim_skel``. Because
    ``vellumconstraints`` bakes rest lengths from the *current* positions (it
    ignores a plain ``rest`` attribute — verified), a ``vellumrestblend`` right
    after restores the true rest state from the undeformed proxy (its 4th input),
    so an animated garment still solves toward its tailored rest shape. At the
    asset (authoring) call ``anim_cage`` is ``None`` -> identity, no restblend.

    ``src_for_part(part)`` returns that part's rest proxy node. Each part is
    ``vellumpack``-ed so the constraint data stays intact through the packed
    ``OUT_CONSTRAINT`` (the HDA boundary; the shot ``vellumunpack``s it).
    """

    outs: list = []
    info: list[dict[str, Any]] = []
    warnings: list[str] = []
    for part in parts:
        src = src_for_part(part)
        if src is None:
            warnings.append(f"no proxy source for '{part.name}'; skipped")
            continue
        pfx = f"vc_{part.name}"

        # Materialize the pin group at REST (before the deform) so it is a stable
        # point group that rides through the deform — otherwise a positional
        # expression (e.g. @P.y>..) would re-select different points every frame.
        pin_group = _cparm(part, con, "pin_group",
                           HAIR_ROOT_GROUP if not part.cloth else None)
        base = src
        pin_name = None
        if pin_group:
            pg = _child(geo, f"{pfx}_pingrp", "groupcreate")
            pg.parm("grouptype").set("point")
            pin_name = f"pin_{part.name}"
            pg.parm("groupname").set(pin_name)
            pg.parm("basegroup").set(pin_group)
            pg.setInput(0, src, 0)
            base = pg
        else:
            stale = geo.node(f"{pfx}_pingrp")
            if stale is not None:
                stale.destroy()

        # deform UPSTREAM of the constraints (only when animated inputs are given).
        # cloth -> full-body cage pointDeform; hair -> rigid head-follow (rides
        # the animated head joint, reconstructs geo_hair_template01/follow_hair).
        upstream = base
        deformed = False           # cloth pointDeform can stretch -> needs restblend
        head_nodes = (f"{pfx}_headdelta", f"{pfx}_headfollow")
        if part.cloth and anim_cage is not None and rest_cage is not None:
            dfm = _child(geo, f"{pfx}_deform", "pointdeform")
            dfm.setInput(0, base, 0)         # part proxy (rest, + pin group)
            dfm.setInput(1, rest_cage, 0)    # rest cage
            dfm.setInput(2, anim_cage, 0)    # animated cage
            upstream = dfm
            deformed = True
            for hn in head_nodes:
                n = geo.node(hn)
                if n is not None:
                    n.destroy()
        elif (not part.cloth) and anim_skel is not None and rest_skel is not None:
            head = _cparm(part, con, "head_joint", "head")
            hdelta = _child(geo, f"{pfx}_headdelta", "attribwrangle")
            hdelta.parm("class").set(0)  # detail
            hdelta.parm("snippet").set(HEAD_DELTA_VEX.replace("__HEAD__", head))
            hdelta.setInput(0, anim_skel, 0)   # animated skeleton
            hdelta.setInput(1, rest_skel, 0)   # rest skeleton
            hfollow = _child(geo, f"{pfx}_headfollow", "attribwrangle")
            hfollow.parm("class").set(2)  # points
            hfollow.parm("snippet").set(HEAD_APPLY_VEX)
            hfollow.setInput(0, base, 0)
            hfollow.setInput(1, hdelta, 0)
            upstream = hfollow             # rigid -> no restblend needed
            n = geo.node(f"{pfx}_deform")
            if n is not None:
                n.destroy()
        else:
            for stale in (f"{pfx}_deform",) + head_nodes:
                n = geo.node(stale)
                if n is not None:
                    n.destroy()

        vc = _child(geo, pfx, "vellumconstraints")
        vc.parm("constrainttype").set("cloth" if part.cloth else "hair")
        vc.parm("stretchstiffness").set(float(_cparm(part, con, "stretch_stiffness", 1.0)))
        vc.parm("bendstiffness").set(float(
            _cparm(part, con, "bend_stiffness", 0.01 if part.cloth else 0.001)))
        thickness = _cparm(part, con, "thickness", None)
        if thickness is not None:
            vc.parm("dothickness").set(1)
            vc.parm("thickness").set(float(thickness))
        mass = _cparm(part, con, "mass", None)
        if mass is not None:
            vc.parm("domass").set(1)
            vc.parm("mass").set(float(mass))
        vc.setInput(0, upstream, 0)
        cur = vc  # invariant: cur out0 = Vellum Geometry, out1 = Constraint Geometry

        # restore rest lengths from the undeformed proxy when deformed upstream
        if deformed:
            rb = _child(geo, f"{pfx}_restblend", "vellumrestblend")
            rb.setInput(0, vc, 0)   # geometry
            rb.setInput(1, vc, 1)   # constraints
            rb.setInput(3, base, 0)  # REST geometry (undeformed proxy + pin group)
            if rb.parm("blend"):
                rb.parm("blend").set(1.0)
            cur = rb
        else:
            stale = geo.node(f"{pfx}_restblend")
            if stale is not None:
                stale.destroy()

        # pin: cloth pins an authored group (waistband/collar); hair pins its root.
        # The pinned points hold their (animated) positions each frame, so with the
        # per-frame deform upstream the pin follows the body.
        if pin_name:
            pin = _child(geo, f"{pfx}_pin", "vellumconstraints")
            pin.parm("constrainttype").set("pin")
            pin.parm("grouptype").set(0)  # points
            pin.parm("group").set(pin_name)
            pin.setInput(0, cur, 0)
            pin.setInput(1, cur, 1)
            cur = pin
        else:
            stalepin = geo.node(f"{pfx}_pin")
            if stalepin is not None:
                stalepin.destroy()

        pack = _child(geo, f"{pfx}_pack", "vellumpack")
        pack.setInput(0, cur, 0)   # Vellum Geometry
        pack.setInput(1, cur, 1)   # Constraint Geometry
        if pack.parm("doname"):
            pack.parm("doname").set(1)
            pack.parm("name").set(part.name)

        out = _child(geo, f"OUT_{part.name}_CONSTRAINT", "null")
        out.setInput(0, pack, 0)
        outs.append(out)
        info.append({
            "part": part.name, "type": "cloth" if part.cloth else "hair",
            "deformed": deformed,
            "stretch_stiffness": float(_cparm(part, con, "stretch_stiffness", 1.0)),
            "bend_stiffness": float(_cparm(part, con, "bend_stiffness",
                                          0.01 if part.cloth else 0.001)),
            "pin_group": pin_group or None,
        })

    merge = _child(geo, "constraint_merge", "merge")
    for i, o in enumerate(outs):
        merge.setInput(i, o, 0)
    out = _child(geo, "OUT_CONSTRAINT", "null")
    out.setInput(0, merge, 0)
    geo.layoutChildren()
    return {"out_constraint": out.path(), "parts": info, "warnings": warnings}


def _ensure_hair_ref(sub):
    """Ensure a default ``hair_ref`` constraint template exists inside the
    CONSTRAINT subnet so hair parts get a recipe to instance. Returns the
    existing one if present (the artist may edit it).

    Default recipe (input 0 = one isolated hair proxy): ``hair_pingrp`` (root
    pin group from ``FirstPoints``) -> ``hair_vc`` (vellum HAIR constraints) ->
    ``hair_pin`` (pin the root) -> ``hair_pack`` (vellumpack) -> ``output0``."""

    ref = sub.node("hair_ref")
    if ref is not None:
        return ref
    ref = sub.createNode("subnet", "hair_ref")
    for d in list(ref.children()):   # start from a clean subnet
        d.destroy()
    ref.setInput(0, sub.indirectInputs()[0])  # activate the subnet's indirect input
    pg = ref.createNode("groupcreate", "hair_pingrp")
    pg.parm("grouptype").set("point")
    pg.parm("groupname").set("pin_root")
    pg.parm("basegroup").set(HAIR_ROOT_GROUP)   # "FirstPoints" (hair root points)
    pg.setInput(0, ref.indirectInputs()[0])
    vc = ref.createNode("vellumconstraints", "hair_vc")
    vc.parm("constrainttype").set("hair")
    vc.setInput(0, pg, 0)
    pin = ref.createNode("vellumconstraints", "hair_pin")
    pin.parm("constrainttype").set("pin")
    pin.parm("grouptype").set(0)  # points
    pin.parm("group").set("pin_root")
    pin.setInput(0, vc, 0)
    pin.setInput(1, vc, 1)
    pack = ref.createNode("vellumpack", "hair_pack")
    pack.setInput(0, pin, 0)
    pack.setInput(1, pin, 1)
    o0 = ref.createNode("output", "output0")
    o0.setInput(0, pack, 0)
    ref.layoutChildren()
    return ref


def _instance_hair_ref(sub, hair_parts, hair_in, ref, merge, base_idx) -> list:
    """Instance the user's ``hair_ref`` constraint template once per hair part.

    Each part is isolated from ``OUT_HAIR_PROXY`` by ``@proxy_path`` (fed to the
    copy's input 0); the copy's output 0 is appended to ``constraint_merge``.
    Mirrors the cloth flow: fresh subnet + copied recipe so output 0 routes
    cleanly. Copies are rebuilt fresh; the template is left untouched."""

    for c in list(sub.children()):  # rebuild hair-constraint copies fresh
        if c.name().startswith("hcon_") or c.name().startswith("hcin_"):
            c.destroy()
    made = []
    for i, part in enumerate(hair_parts):
        cin = _child(sub, "hcin_%s" % part.name, "blast")
        cin.parm("group").set("@proxy_path=%s" % (part.proxy_path or part.name))
        cin.parm("negate").set(1)  # keep only this hair part
        cin.setInput(0, hair_in)
        node = sub.createNode("subnet", "hcon_%s" % part.name)
        _copy_recipe_into_subnet(ref, node)
        node.setInput(0, cin, 0)
        # name the packed prims after the part (parity with cloth vellumpack)
        for c in node.children():
            if c.type().name() == "vellumpack" and c.parm("doname"):
                c.parm("doname").set(1)
                c.parm("name").set(part.name)
        node.layoutChildren()
        merge.setInput(base_idx + i, node, 0)
        made.append(part.name)
    return made


def build_constraint(cfg: AssetSetupConfig, parent: str = "/obj") -> dict[str, Any]:
    """Stage 2.6 — PER-PART vellum constraint REST authoring (asset stage).

    Builds the per-part constraint chain on the asset's rest proxies at REST (no
    deform) so an artist can author/preview per-garment stiffness, thickness and
    pins. This is the asset-stage "definition"; a shot instantiates the same
    chain WITH its animation via :func:`shot_builder.build_shot_constraint`
    (deform upstream + restblend). Parameters resolve per part
    (``part.parameters`` over ``cfg.constraint``); hair parts get a ``hair``
    constraint and pin their root group. Not disk-cached.
    """

    geo = _asset_geo(cfg, parent)
    proxy_out = geo.node("OUT_PROXY")
    hair_out = geo.node("OUT_HAIR_PROXY")
    srcs = [proxy_out] + ([hair_out] if hair_out is not None else [])
    sub = _stage_subnet(geo, "CONSTRAINT", *srcs)
    proxy_in = sub.indirectInputs()[0]
    hair_in = sub.indirectInputs()[1] if hair_out is not None else None

    # Parts come from the PROXY subnet (source of truth) so the constraint setups
    # always match the proxies actually generated there; fall back to config.
    proxy_sub = geo.node("PROXY")
    all_parts = _parts_from_node(proxy_sub) if proxy_sub is not None else cfg.proxy_parts

    # Hair parts are instanced from the ``hair_ref`` template (a default one is
    # created if the artist hasn't made one); cloth goes through the built-in
    # vellum chain.
    hair_ref = _ensure_hair_ref(sub)
    chain_parts = [p for p in all_parts if p.cloth]
    hair_parts = [p for p in all_parts if not p.cloth]

    # retire stale per-part nodes so removed parts leave no orphans (keep hair_ref)
    for c in list(sub.children()):
        nm = c.name()
        if (nm.startswith("cin_") or nm.startswith("vc_") or nm == "constraint_merge"
                or nm.startswith("hcin_") or nm.startswith("hcon_")
                or (nm.endswith("_CONSTRAINT") and nm != "OUT_CONSTRAINT")):
            c.destroy()

    def src_for_part(part):
        # isolate this part from the merged proxy input by its proxy_path tag
        base = (hair_in if (not part.cloth and hair_in is not None) else proxy_in)
        b = _child(sub, f"cin_{part.name}", "blast")
        b.parm("group").set(f"@proxy_path={part.proxy_path or part.name}")
        b.parm("negate").set(1)  # keep only this part
        b.setInput(0, base)
        return b

    res = build_vellum_chain(sub, chain_parts, cfg.constraint,
                             src_for_part=src_for_part, rest_cage=None, anim_cage=None)
    merge = sub.node("constraint_merge")
    made_hair = []
    if hair_ref is not None and hair_parts and hair_in is not None:
        made_hair = _instance_hair_ref(sub, hair_parts, hair_in, hair_ref, merge,
                                       len(merge.inputs()))
    _stage_output(sub, sub.node("OUT_CONSTRAINT"))  # build_vellum_chain's merge output
    sub.layoutChildren()

    out = _child(geo, "OUT_CONSTRAINT", "null")
    out.setInput(0, sub, 0)
    # retire the old flat constraint nodes from the pre-subnet layout
    for c in list(geo.children()):
        nm = c.name()
        if (nm.startswith("vc_") or nm.startswith("cin_") or nm == "constraint_merge"
                or nm in ("vellum_constraints", "vellum_pin")
                or (nm.endswith("_CONSTRAINT") and nm != "OUT_CONSTRAINT")):
            c.destroy()
    geo.layoutChildren()
    return {"constraint_subnet": sub.path(), "out_constraint": out.path(),
            "parts": res.get("parts"), "hair_parts": made_hair,
            "warnings": res.get("warnings", [])}


def build_rest_cache(cfg: AssetSetupConfig, parent: str = "/obj",
                     execute: bool = False) -> dict[str, Any]:
    """Stage 2.5 — cache the static rest proxy/hair/collision to disk.

    These single-frame caches are the Asset->Shot handoff: a shot loads them and
    deforms by animation instead of rebuilding the asset. Paths come from
    ``path_rules`` (config-authoritative). ``execute=True`` writes them now.

    NOTE: paths resolve under the show root (production) — pass ``execute=False``
    or a config with a local root when testing so nothing is written to Z:.
    """

    geo = _asset_geo(cfg, parent)
    specs = [
        ("cache_proxy", "OUT_PROXY", cfg.proxy_cache_path),
        ("cache_hair", "OUT_HAIR_PROXY", cfg.hair_cache_path),
        ("cache_collision", "OUT_COLLISION", cfg.collision_cache_path),
        # rest corrective mesh = the pointDeform REST cage for the shot stage
        # (Stage 3.3, decision B). Static single frame like the others.
        ("cache_corrective", "OUT_CORRECTIVE", cfg.corrective_cache_path),
        # capture-pose skeleton = the bonedeform REST skeleton for the shot
        # (the shot's anim fbx is animation-only; its rest skeleton comes from
        # here so boneCapture stays consistent).
        ("cache_skel", "REST_SKEL", cfg.skel_cache_path),
    ]
    # NOTE: OUT_CONSTRAINT is intentionally NOT cached here — the packed vellum
    # constraint setup is handed to the shot live via object_merge + vellumunpack
    # (see shot_builder.build_shot_solve) so no vellum data is lost through bgeo.
    stale_con = geo.node("cache_constraint")
    if stale_con is not None:
        stale_con.destroy()
    caches: list[dict[str, Any]] = []
    warnings: list[str] = []
    for node_name, src_name, path in specs:
        src = geo.node(src_name)
        if src is None:
            warnings.append(f"{src_name} missing; skipped {node_name}")
            continue
        if not path:
            warnings.append(f"no cache path for {node_name}")
            continue
        fc = _child(geo, node_name, "filecache::2.0")
        fc.parm("filemethod").set(1)   # explicit filename
        fc.parm("file").set(path)
        fc.parm("trange").set(0)       # single (current) frame — static rest
        fc.setInput(0, src, 0)
        if execute and fc.parm("execute"):
            fc.parm("execute").pressButton()
        caches.append({"node": fc.path(), "src": src_name, "file": path,
                       "written": bool(execute)})
    geo.layoutChildren()
    return {"caches": caches, "warnings": warnings}


def build_asset_sim_test(cfg: AssetSetupConfig, parent: str = "/obj",
                         frames: tuple[int, int] = (1, 48),
                         execute: bool = False,
                         cache_path: str | None = None) -> dict[str, Any]:
    """Stage 2.x — quick asset-level test sim to validate the cloth setup.

    Before committing to shots, drape the rest proxy under gravity (no
    animation) so the per-part vellum constraints + collision can be eyeballed:
    the packed ``OUT_CONSTRAINT`` is unpacked and solved against
    ``OUT_COLLISION``; pinned parts should hold, unpinned parts fall/drape.
    Output ``OUT_ASSET_SIMTEST``. ``execute`` cooks the range; ``cache_path``
    (local!) additionally writes it to disk.
    """

    geo = _asset_geo(cfg, parent)
    con = geo.node("OUT_CONSTRAINT")
    if con is None:
        raise ValueError("OUT_CONSTRAINT missing; run build_constraint first")
    coll = geo.node("OUT_COLLISION")

    unpack = _child(geo, "simtest_unpack", "vellumunpack")
    unpack.setInput(0, con, 0)
    solver = _child(geo, "simtest_solve", "vellumsolver")
    solver.setInput(0, unpack, 0)      # Vellum Geometry
    solver.setInput(1, unpack, 1)      # Constraint Geometry
    if coll is not None:
        solver.setInput(2, coll, 0)    # Collision Geometry
    if solver.parm("startframe"):
        solver.parm("startframe").deleteAllKeyframes()
        solver.parm("startframe").set(frames[0])
    if cfg.constraint.get("substeps") is not None and solver.parm("substeps"):
        solver.parm("substeps").set(int(cfg.constraint["substeps"]))
    post = _child(geo, "simtest_post", "vellumpostprocess")
    post.setInput(0, solver, 0)
    out = _child(geo, "OUT_ASSET_SIMTEST", "null")
    out.setInput(0, post, 0)
    out.setDisplayFlag(True)

    written = False
    if execute and cache_path:
        fc = _child(geo, "simtest_cache", "filecache::2.0")
        fc.parm("filemethod").set(1)
        fc.parm("file").set(cache_path)
        fc.parm("trange").set(1)
        fc.parm("f1").deleteAllKeyframes(); fc.parm("f1").set(frames[0])
        fc.parm("f2").deleteAllKeyframes(); fc.parm("f2").set(frames[1])
        fc.setInput(0, out, 0)
        if fc.parm("execute"):
            fc.parm("execute").pressButton()
            written = True
    geo.layoutChildren()
    return {"out_sim_test": out.path(), "frames": list(frames), "written": written}
