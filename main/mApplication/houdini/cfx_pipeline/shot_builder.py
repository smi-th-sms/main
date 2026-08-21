# -*- coding: utf-8 -*-
"""Stage 3 — Shot (per-shot sim) setup, driven by :class:`ShotSimConfig`.

The shot stage reuses the asset's static rest caches (proxy / hair / collision,
the Asset->Shot handoff written by :mod:`asset_builder`) and brings them into
the shot's animation, then runs the vellum solve and writes the sim cache. It
deliberately does NOT rebuild the character: everything expensive and reusable
was baked once at asset time.

Sub-stages (built incrementally, mirroring the asset builder):
  3.1  anim import + timeline   <- this commit
  3.2  load asset rest caches
  3.3  skeletal deform rest proxy -> animated pose
  3.4  per-frame push-apart on the animated collision
  3.5  vellum solve (shot ``sim_params`` only)
  3.6  sim filecache

Import-safe without Houdini; ``hou`` is required lazily via the shared helpers
in :mod:`asset_builder` so the config helpers and tests run headless.
"""

from __future__ import annotations

import os
from typing import Any

from .asset_builder import (
    CONSTRAINT_HDA_ROOT,
    STAGE_HDA_ROOT,
    HEAD_APPLY_VEX,
    HEAD_DELTA_VEX,
    PUSH_APART_VEX,
    _child,
    _constraint_hda_dir,
    _constraint_hda_versions,
    _stage_hda_versions,
    _execute_filecache,
    _require_hou,
    build_vellum_chain,
    flatten_stages,
    organize_stages,
)
from .schema import AssetSetupConfig, ShotSimConfig


SOLVER_TUNED_DEFAULTS = {
    "constraint_iterations": 500,
    "collision_iterations": 50,
    "post_collision_iterations": 5,
    "collision_thickness": 0.001,
    "windshadow_maskfalloff1pos": 0.8500000238418579,
    "windshadow_maskfalloff1value": 1.0,
    "windshadow_maskfalloff2pos": 0.9973856210708618,
}


def _hair_uv_export_copy_vex(rop_path: str) -> str:
    """Build the non-destructive Hair UV channel-selection wrangle."""

    path = rop_path.replace("\\", "\\\\").replace('"', '\\"')
    return """string source0 = chs(\"%s/hair_uv0_source\");
string source1 = chs(\"%s/hair_uv1_source\");
string source2 = chs(\"%s/hair_uv2_source\");

vector value0 = vertex(0, source0, @vtxnum);
vector value1 = vertex(0, source1, @vtxnum);
vector value2 = vertex(0, source2, @vtxnum);

v@uv = value0;
if (chi(\"%s/hair_keep_uv1\"))
    v@uv2 = value1;
if (chi(\"%s/hair_keep_uv2\"))
    v@uv3 = value2;
""" % (path, path, path, path, path)


def _hair_uv_export_filter_vex(rop_path: str) -> str:
    """Build the Hair UV/varmap cleanup wrangle used immediately pre-export."""

    path = rop_path.replace("\\", "\\\\").replace('"', '\\"')
    return """if (!chi(\"%s/hair_keep_uv1\"))
    removeattrib(0, \"vertex\", \"uv2\");
if (!chi(\"%s/hair_keep_uv2\"))
    removeattrib(0, \"vertex\", \"uv3\");
if (chi(\"%s/hair_remove_varmap\"))
    removeattrib(0, \"detail\", \"varmap\");
""" % (path, path, path)


def _prepare_hair_uv_export(geo, source, rop, hou):
    """Create/preserve the selectable Hair UV chain and return its output.

    This replaces the legacy ``co_hair_uv0_swap`` behavior.  Values are copied
    into the Unreal UV slots only at the export boundary, so source attributes
    never exchange names or ordering inside CACHEOUT.
    """

    ptg = rop.parmTemplateGroup()
    if ptg.find("hair_uv_export_folder") is None:
        folder = hou.FolderParmTemplate(
            "hair_uv_export_folder", "Hair UV Export Selection")
        folder.addParmTemplate(hou.StringParmTemplate(
            "hair_uv0_source", "Unreal UV0 Source", 1,
            default_value=("uv",)))
        folder.addParmTemplate(hou.ToggleParmTemplate(
            "hair_keep_uv1", "Keep Unreal UV1", default_value=True))
        folder.addParmTemplate(hou.StringParmTemplate(
            "hair_uv1_source", "Unreal UV1 Source", 1,
            default_value=("uv2",)))
        folder.addParmTemplate(hou.ToggleParmTemplate(
            "hair_keep_uv2", "Keep Unreal UV2", default_value=False))
        folder.addParmTemplate(hou.StringParmTemplate(
            "hair_uv2_source", "Unreal UV2 Source", 1,
            default_value=("uv3",)))
        folder.addParmTemplate(hou.ToggleParmTemplate(
            "hair_remove_varmap", "Remove varmap Before Export",
            default_value=True))
        ptg.append(folder)
        rop.setParmTemplateGroup(ptg)

    uv_copy = _child(geo, "HAIR_UV_EXPORT_COPY", "attribwrangle")
    uv_copy.parm("class").set(3)  # vertices
    uv_copy.parm("snippet").set(_hair_uv_export_copy_vex(rop.path()))
    uv_copy.setInput(0, source, 0)

    uv_filter = _child(geo, "HAIR_UV_EXPORT_FILTER", "attribwrangle")
    uv_filter.parm("class").set(0)  # detail
    uv_filter.parm("snippet").set(_hair_uv_export_filter_vex(rop.path()))
    uv_filter.setInput(0, uv_copy, 0)

    # Alembic needs secondary UV sets explicitly listed.  Missing optional
    # attributes are harmless when their Keep toggle removes them upstream.
    for parm_name, value in (
            ("vertexAttributes", "N uv uv2 uv3 tangentu"),
            ("uvAttributes", "uv2 uv3")):
        parm = rop.parm(parm_name)
        if parm is not None:
            parm.deleteAllKeyframes()
            parm.set(value)
    return uv_filter


# ---------------------------------------------------------------------------
# Stage 3.1 — animation import + timeline
# ---------------------------------------------------------------------------
# The studio FBX subnet (docs §2.1) produces three outputs from the shot's
# animation fbx: output0 = animation_mesh (the character mesh deformed by the
# take), output1 = setting_animation_skeleton (retimed to the shot playbar),
# output2 = original_animation_skeleton (raw take). We reconstruct this with
# stock kinefx nodes:
#   fbxcharacterimport  -> out0 skin mesh (+boneCapture), out1 capture-pose skel
#   fbxanimimport       -> the animated skeleton (per-frame take)
#   bonedeform(mesh, capture-pose skel, animated skel) -> ANIM_MESH
# The animated skeleton (ANIM_SKEL) is what later drives the rest-proxy deform
# (Stage 3.3); ANIM_MESH is the corrective/collision driver.


# --- reconstructed from the studio FBX/anim_subnet1 -------------------------
# Strip the fbx namespace off joint names so the take matches the character /
# T-pose joint names (anim_subnet1/attribwrangle4 + namespace_remove).
NAMESPACE_STRIP_VEX = """string parts[] = split(s@name, ":");
s@name = parts[-1];
"""

# --- Stage 4 (Cache Out) VEX --------------------------------------------------
# Origin-ize a joint: build its world matrix from the skeleton (in1) and apply
# the inverse to the geometry (in0) so the joint sits at the world identity —
# UE then re-parents the alembic under that joint to restore world motion.
# Reconstructs Out/fix_pelvis_inverse_translate (cloth, pelvis) and
# Out/attribwrangle5 (hair, head). __JOINT__ is replaced with the joint name.
JOINT_INV_VEX = """matrix jm(int inp; int h) {
    matrix3 r = point(inp, "transform", h);
    vector p = point(inp, "P", h);
    vector ax = normalize(set(getcomp(r,0,0), getcomp(r,0,1), getcomp(r,0,2)));
    vector ay = normalize(set(getcomp(r,1,0), getcomp(r,1,1), getcomp(r,1,2)));
    vector az = normalize(set(getcomp(r,2,0), getcomp(r,2,1), getcomp(r,2,2)));
    matrix m = matrix(set(ax, ay, az));
    setcomp(m, p.x, 3, 0); setcomp(m, p.y, 3, 1); setcomp(m, p.z, 3, 2);
    return m;
}
int j = -1;
for (int i = 0; i < npoints(1); i++)
    if (point(1, "name", i) == "__JOINT__") { j = i; break; }
if (j >= 0) {
    matrix inv = invert(jm(1, j));
    matrix3 rinv = matrix3(inv);
    int has_point_n = haspointattrib(0, "N");
    int has_vertex_n = hasvertexattrib(0, "N");
    int has_velocity = haspointattrib(0, "v");
    for (int pt = 0; pt < npoints(0); pt++) {
        vector p = point(0, "P", pt);
        p *= inv;
        setpointattrib(0, "P", pt, p, "set");
        if (has_point_n) {
            vector n = point(0, "N", pt);
            setpointattrib(0, "N", pt, normalize(n * rinv), "set");
        }
        if (has_velocity) {
            vector v = point(0, "v", pt);
            setpointattrib(0, "v", pt, v * rinv, "set");
        }
    }
    if (has_vertex_n) {
        for (int vtx = 0; vtx < nvertices(0); vtx++) {
            vector n = vertex(0, "N", vtx);
            setvertexattrib(
                0, "N", vtx, -1, normalize(n * rinv), "set");
        }
    }
}
"""

# fbx_material_name -> primitive group (Out/face_shading_group) for UE materials.
FACE_SHADING_VEX = """if (s@fbx_material_name != "")
    setprimgroup(0, s@fbx_material_name, @primnum, 1);
"""


# Copy a pose (P + transform) from in1 onto in0's joints by name — the
# cached-skeleton equivalent of anim_subnet1/skeletonblend1 (see build_shot_anim
# for why a real kinefx::skeletonblend can't be used on the bgeo-cached skeleton).
POSE_COPY_VEX = """int i = findattribval(1, "point", "name", s@name);
if (i >= 0) {
    @P = point(1, "P", i);
    3@transform = matrix3(point(1, "transform", i));
}
"""

# FK-follow-parent for REST_SKEL joints the take LACKS (e.g. hairBand1). anim_clean
# copies WORLD transforms by name, so joints absent from the take never get their
# world recomputed from their (moving) parent — they freeze at rest. There is no FK
# step in the chain to propagate motion down the hierarchy. This wrangle restores
# that: for a take-absent joint it walks UP the REST_SKEL bone hierarchy (kinefx
# stores each bone as a polyline parent->child) to the nearest ancestor that IS in
# the take, then rigidly follows that ancestor's rest->anim delta:
#   joint_anim = joint_rest * invert(ancestor_rest) * ancestor_anim
# For hairBand1 the nearest animated ancestor is head, so it follows the head — but
# nothing is hard-coded; any accessory chain follows its real parent. in0 = current
# (aligned) skeleton, in1 = REST_SKEL (rest ref + hierarchy), in2 = the take.
ACCESSORY_FOLLOW_VEX = """matrix ortho(int inp; int i) {
    matrix3 r = point(inp, "transform", i);
    vector p = point(inp, "P", i);
    vector ax = normalize(set(getcomp(r,0,0), getcomp(r,0,1), getcomp(r,0,2)));
    vector ay = normalize(set(getcomp(r,1,0), getcomp(r,1,1), getcomp(r,1,2)));
    vector az = normalize(set(getcomp(r,2,0), getcomp(r,2,1), getcomp(r,2,2)));
    matrix m = matrix(set(ax, ay, az));
    setcomp(m, p.x, 3, 0); setcomp(m, p.y, 3, 1); setcomp(m, p.z, 3, 2);
    return m;
}
int parentpt(int inp; int pt) {
    int prims[] = pointprims(inp, pt);
    foreach (int pr; prims) {
        int vp[] = primpoints(inp, pr);
        for (int k = 1; k < len(vp); k++)
            if (vp[k] == pt) return vp[k-1];   // bone is ordered parent -> child
    }
    return -1;
}
if (findattribval(2, "point", "name", s@name) >= 0) return;   // take animates it
int jr = findattribval(1, "point", "name", s@name);           // me in REST_SKEL
if (jr < 0) return;
// walk up the rest hierarchy to the nearest ancestor present in the take
int anc = jr;
string ancname = "";
while (1) {
    int par = parentpt(1, anc);
    if (par < 0) return;                       // reached root: no animated ancestor
    string pn = point(1, "name", par);
    if (findattribval(2, "point", "name", pn) >= 0) { anc = par; ancname = pn; break; }
    anc = par;
}
int anc_cur = findattribval(0, "point", "name", ancname);   // ancestor in anim skel
if (anc_cur < 0) return;
matrix delta = invert(ortho(1, anc)) * ortho(0, anc_cur);
matrix rest = matrix(matrix3(point(1, "transform", jr)));
vector jp = point(1, "P", jr);
setcomp(rest, jp.x, 3, 0); setcomp(rest, jp.y, 3, 1); setcomp(rest, jp.z, 3, 2);
matrix jm = rest * delta;
@P = set(getcomp(jm,3,0), getcomp(jm,3,1), getcomp(jm,3,2));
3@transform = matrix3(jm);
"""

# Rigid root alignment (condenses anim_subnet1's attribwrangle8 + transform6 +
# transform1 into one per-point translation, since all are uniform pelvis-based
# shifts that leave joint rotations untouched — bonedeform matches by name so no
# skeletonblend retarget is needed).
#   in0 = current animation skeleton
#   in1 = animation skeleton at the start frame (timeshift)
#   in2 = the T-pose (offset) skeleton
# offset(f) = (tpose_pelvis - anim_start_pelvis) * T_pose_start_position   [align]
#           - (anim_pelvis(f) - anim_start_pelvis) * (1 - position_mult)   [motion]
# T_pose_start_position=1 lands the start pelvis on the T-pose (character
# origin); position_mult (per-axis 0..1) keeps that fraction of the root motion.
# Root ROTATION retention (reconstructs anim_subnet1/attribwrangle10). Detail
# wrangle: in0 = current aligned skel, in1 = same at the start frame. Stores the
# euler (deg) of the INVERSE of the current pelvis orientation ("rotate", used to
# cancel the current rotation) and the START pelvis orientation ("trotate", used
# to re-apply the start rotation). Two rigposes then freeze the pelvis at the
# start orientation, and a skeletonblend (weight1 = rotate_mul) blends that
# frozen pose against the full-rotation pose: rotate_mul=1 full world rotation,
# 0 holds the start facing.
ROT_DELTA_VEX = """string pn = "{pelvis}";
int a = findattribval(0, "point", "name", pn);
int b = findattribval(1, "point", "name", pn);
if (a >= 0 && b >= 0) {{
    matrix3 m = point(0, "transform", a);   // current pelvis orientation
    matrix3 t = point(1, "transform", b);   // start pelvis orientation
    setdetailattrib(0, "rotate", degrees(quaterniontoeuler(quaternion(invert(m)), 0)));
    setdetailattrib(0, "trotate", degrees(quaterniontoeuler(quaternion(t), 0)));
}}
"""

ANIM_ALIGN_VEX = """string pn = "{pelvis}";
float enable = {tpose_start};
vector mult = set({mx}, {my}, {mz});
int a = findattribval(0, "point", "name", pn);
int s = findattribval(1, "point", "name", pn);
int t = findattribval(2, "point", "name", pn);
vector cur = (a >= 0) ? point(0, "P", a) : {{0,0,0}};
vector st  = (s >= 0) ? point(1, "P", s) : {{0,0,0}};
vector tp  = (t >= 0) ? point(2, "P", t) : {{0,0,0}};
vector align  = (tp - st) * enable;
vector motion = (cur - st) * (1 - mult);
@P += align - motion;
"""


def _shot_container_name(shot: ShotSimConfig) -> str:
    """Container name unique per asset within a shot session (one hip = one shot,
    but a shot may carry several assets -> scope by asset)."""

    return f"{shot.asset}_shot_setup"


def _shot_geo(shot: ShotSimConfig, parent: str):
    hou = _require_hou()
    geo = hou.node(f"{parent}/{_shot_container_name(shot)}")
    if geo is None:
        raise ValueError(
            f"run build_shot_setup first ({_shot_container_name(shot)} not found)"
        )
    return geo


def build_shot_setup(shot: ShotSimConfig, parent: str = "/obj") -> dict[str, Any]:
    """Stage 3.1 — import the shot animation take (animation-only fbx).

    Builds (idempotently) ``{parent}/{asset}_shot_setup`` and imports the shot's
    animation TAKE, namespace-stripped, as ``ANIM_TAKE``. The shot fbx is
    animation-only (no skin mesh) — the bonedeform rest skeleton + geometry come
    from the asset rest caches (``REST_SKEL`` etc., Stage 3.2).

    The FBX playback gimmick lands the clip's first frame on ``frame_start`` so
    the pre-roll frames naturally hold the first pose. The full alignment
    (T-pose / position-mult / start-align — the studio ``anim_subnet1``) is done
    in :func:`build_shot_anim` once ``REST_SKEL`` is loaded.
    """

    hou = _require_hou()
    root = hou.node(parent)
    if root is None:
        raise ValueError(f"parent node not found: {parent}")

    geo = _child(root, _shot_container_name(shot), "geo")
    warnings: list[str] = []
    anim_file = shot.animation_import
    if not anim_file:
        warnings.append("shot.animation_import is empty; anim nodes have no file")

    take = _child(geo, "anim_take", "kinefx::fbxanimimport")
    if anim_file and take.parm("fbxfile"):
        take.parm("fbxfile").set(anim_file)
    if take.parm("useplaybackstartframe"):
        take.parm("useplaybackstartframe").set(1)
        # the parm ships with a $FSTART expression — clear it before setting
        take.parm("playbackstartframe").deleteAllKeyframes()
        take.parm("playbackstartframe").set(shot.frame_start)

    # strip fbx namespace so joint names match the character / T-pose
    ns = _child(geo, "anim_ns", "attribwrangle")
    ns.parm("class").set(2)  # points
    ns.parm("snippet").set(NAMESPACE_STRIP_VEX)
    ns.setInput(0, take, 0)
    out = _child(geo, "ANIM_TAKE", "null")
    out.setInput(0, ns, 0)

    # retire nodes from earlier flows
    for stale in ("anim_char", "anim_deform", "ANIM_MESH", "anim_worldzero",
                  "anim_xform", "anim_tpose_ref"):
        n = geo.node(stale)
        if n is not None:
            n.destroy()

    geo.layoutChildren()
    return {
        "container": geo.path(),
        "anim_take": take.path(),
        "anim_take_out": out.path(),
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Stage 3.2 — load the asset's static rest caches (Asset->Shot handoff)
# ---------------------------------------------------------------------------
def _rest_cache_warnings(specs) -> list[str]:
    """Guard the Asset->Shot handoff against MISSING or STALE rest caches.

    For each ``(node, out, path)``: warn if the cache file is absent, or if it
    predates the asset's ``cfx_asset.json`` — the tell-tale of the classic bug
    where the asset setup changed but its rest caches were not re-written, so the
    shot loads an out-of-date proxy/hair/skeleton (e.g. a hair cache from before
    the head-attach was added). The asset config path is derived from the cache
    path (``{asset_work}/geo/... -> {asset_work}/cfx_asset.json``)."""

    import os
    warnings: list[str] = []
    cfg_mtime = None
    for _n, _o, path in specs:
        p = (path or "").replace("\\", "/")
        if p and "/geo/" in p:
            cfg_path = p.split("/geo/")[0] + "/cfx_asset.json"
            if os.path.isfile(cfg_path):
                cfg_mtime = os.path.getmtime(cfg_path)
            break
    for _node, out, path in specs:
        if not path:
            continue
        if not os.path.isfile(path):
            warnings.append(f"{out}: cache file MISSING — write the asset rest cache ({path})")
        elif cfg_mtime is not None and os.path.getmtime(path) < cfg_mtime:
            warnings.append(f"{out}: cache is OLDER than the asset config — likely STALE; "
                            "re-run the asset's Write Rest Cache")
    return warnings


def _park_asset_stage_hdas(shot: ShotSimConfig, geo,
                           version: str | None = None) -> dict[str, Any]:
    """Park whichever FBX/CORRECTIVE/PROXY asset-stage HDAs are published as
    BYPASSED nodes inside the shot, purely so an artist can open/tweak the asset
    authoring recipe (e.g. a wrong ``geo_path``) without leaving the shot hip.

    These never feed ``REST_PROXY``/``REST_CORRECTIVE``/``REST_SKEL`` — those
    stay wired to the disk rest-cache exactly as before (unconditionally, see
    :func:`load_asset_caches`), so parking an HDA here has zero effect on a
    normal cook. To actually use an edit: unbypass the chain, wire a
    ``filecache::2.0`` (or point one of the REST_* nulls at it) to re-bake, then
    :func:`republish_stage_hda` to publish the fix as a new version for other
    shots to pick up.
    """

    requested = version or shot.metadata.get("asset_version")
    chain = [
        ("fbx", "fbx_hda", 0, None),
        ("corrective", "corrective_hda", 1, "fbx_hda"),
        ("proxy", "proxy_hda", 1, "corrective_hda"),
    ]
    parked: dict[str, str] = {}
    upstream = None
    for stage_key, node_name, _n_inputs, input_from in chain:
        type_name = _resolve_stage_hda(shot.show, shot.asset, stage_key, requested)
        stale = geo.node(node_name)
        if type_name is None:
            if stale is not None:
                stale.destroy()
            upstream = None  # a missing stage breaks the chain for downstream stages
            continue
        inst = _child(geo, node_name, type_name)
        if input_from is not None and upstream is not None:
            inst.setInput(0, upstream, 0)
        inst.bypass(True)   # present, editable, but never in the live cook path
        if inst.isLockedHDA():
            inst.allowEditingOfContents()
        parked[stage_key] = inst.path()
        upstream = inst
    return {"parked": parked}


def republish_stage_hda(shot: ShotSimConfig, stage: str,
                        version: str | None = None) -> dict[str, Any]:
    """Re-publish an edited ``fbx_hda``/``corrective_hda``/``proxy_hda`` shot
    instance as a new global asset-stage HDA version (mirrors
    :func:`asset_builder.save_stage_hda`, but sourced from the shot's live,
    already-a-digital-asset instance instead of a plain subnet in the asset
    hip). Other shots pick up the fix by bumping their pinned
    ``metadata.asset_version`` (or via ``hda_version=`` overrides).
    """

    hou = _require_hou()
    import os

    stage_key = stage.lower()
    node_name = {"fbx": "fbx_hda", "corrective": "corrective_hda",
                "proxy": "proxy_hda"}.get(stage_key)
    if node_name is None:
        raise ValueError("Unsupported stage HDA: %s" % stage)
    geo = _shot_geo(shot, "/obj")
    source = geo.node(node_name)
    if source is None:
        raise ValueError("%s not found; run load_asset_caches with the stage "
                         "HDA chain first" % node_name)
    definition = source.type().definition()
    if definition is None:
        raise ValueError("%s is not a digital asset instance" % node_name)
    # bake the instance's current (possibly hand-edited) contents into its
    # own definition before branching a new versioned file off of it.
    definition.updateFromNode(source)

    hda_dir = _constraint_hda_dir(STAGE_HDA_ROOT, shot.show, shot.asset)
    os.makedirs(hda_dir, exist_ok=True)
    existing = _stage_hda_versions(hda_dir, shot.asset, stage_key)
    vnum = (int(str(version).lstrip("v")) if version else
            ((existing[-1] + 1) if existing else 1))
    ver = "v%03d" % vnum
    hda_file = "%s/cfx_%s_%s_%s.hda" % (hda_dir, stage_key, shot.asset, ver)
    type_name = "cfx_%s_%s_%s_%s" % (stage_key, shot.show, shot.asset, ver)
    label = "CFX %s %s %s %s" % (stage_key.title(), shot.show, shot.asset, ver)
    definition.copyToHDAFile(hda_file, type_name, label)
    return {"stage": stage_key, "hda_file": hda_file, "type_name": type_name,
            "version": ver, "existing": ["v%03d" % v for v in existing]}


def load_asset_caches(shot: ShotSimConfig, parent: str = "/obj",
                      use_stage_hda: bool = True) -> dict[str, Any]:
    """Stage 3.2 — read the asset's static rest caches into the shot container.

    These were written once at asset time (:func:`asset_builder.build_rest_cache`)
    and are the whole point of the stage split: the shot loads and deforms them
    instead of rebuilding the character. Each becomes a ``filecache::2.0`` in
    load-from-disk mode feeding a named ``REST_*`` null:

    * ``REST_PROXY``      — the low-res cloth sim proxy (deformed in Stage 3.3)
    * ``REST_CORRECTIVE`` — the rest cage for the Stage 3.3 pointDeform
    * ``REST_COLLISION``  — the rest collision surface (deformed in Stage 3.4)
    * ``REST_SKEL``       — the capture-pose skeleton (bonedeform REST skeleton;
      the shot anim fbx is animation-only so the rest skeleton comes from here)
    * ``REST_HAIR``       — the rest hair proxy (optional)

    When the asset has published FBX/CORRECTIVE/PROXY stage HDAs, those are
    additionally parked (BYPASSED, editable) in this container — see
    :func:`_park_asset_stage_hdas` — purely so the recipe is reachable from the
    shot hip; they never replace the disk read below. Set ``use_stage_hda=False``
    to skip parking them.

    The vellum constraint setup is handled separately (object_merge in
    :func:`build_shot_solve`), not here.

    Missing cache paths surface as warnings (an asset without hair has none).
    """

    geo = _shot_geo(shot, parent)
    stage_hda = _park_asset_stage_hdas(shot, geo) if use_stage_hda else None
    # NOTE: the vellum constraint setup is NOT loaded from a bgeo cache — it comes
    # in live via object_merge + vellumunpack in build_shot_solve (packed vellum
    # data would be lossy through a plain file cache).
    specs = [
        ("load_proxy", "REST_PROXY", shot.asset_proxy_cache),
        ("load_corrective", "REST_CORRECTIVE", shot.asset_corrective_cache),
        ("load_collision", "REST_COLLISION", shot.asset_collision_cache),
        ("load_skel", "REST_SKEL", shot.asset_skel_cache),
        ("load_hair", "REST_HAIR", shot.asset_hair_cache),
    ]
    import os
    loaded: list[dict[str, Any]] = []
    warnings: list[str] = _rest_cache_warnings(specs)
    for node_name, out_name, path in specs:
        # Missing cache (no path, or the file isn't on disk — e.g. an asset with no
        # hair, or a version that was never written) -> warn and SKIP. Do NOT create
        # a filecache pointing at a non-existent file (it would cook to a red error
        # node); also remove any stale node left by a previous build.
        if not path or not os.path.isfile(path):
            if path:   # _rest_cache_warnings already reported a real MISSING path
                pass
            else:
                warnings.append(f"no cache path for {out_name}; skipped")
            for nm in (node_name, out_name):
                old = geo.node(nm)
                if old is not None:
                    old.destroy()
            continue
        fc = _child(geo, node_name, "filecache::2.0")
        fc.parm("filemethod").set(1)   # explicit filename
        fc.parm("file").set(path)
        if fc.parm("loadfromdisk"):
            fc.parm("loadfromdisk").set(1)  # read the existing cache, don't cook a source
        fc.parm("trange").set(0)       # static single frame
        out = _child(geo, out_name, "null")
        out.setInput(0, fc, 0)
        loaded.append({"node": fc.path(), "out": out.path(), "file": path})
    geo.layoutChildren()
    return {"loaded": loaded, "warnings": warnings,
            "parked_stage_hda": stage_hda["parked"] if stage_hda else {}}


# ---------------------------------------------------------------------------
# Stage 3.2b — animation alignment (reconstructs the studio FBX/anim_subnet1)
# ---------------------------------------------------------------------------
def build_shot_anim(shot: ShotSimConfig, parent: str = "/obj") -> dict[str, Any]:
    """Reconstruct the studio ``anim_subnet1`` alignment -> ``ANIM_SKEL``.

    Takes the namespace-stripped take (``ANIM_TAKE``) and the asset T-pose
    (``REST_SKEL``) and produces the "setting animation skeleton" that drives the
    deform, honoring the FBX-node gimmicks (``shot.fbx``):

    * name-match retarget the take onto the T-pose joints (``skeletonblend``)
    * ``t_pose_start_position`` — shift so the take's START pelvis sits on the
      T-pose pelvis (align to the character origin) vs keep the native position
    * ``position_mult`` (per-axis 0..1) — root-motion retention: 1 keeps the full
      world motion, 0 holds the character in place at the start
    * ``t_pos`` (+ ``t_pos_offset_*``) — blend the pose toward the T-pose; when
      ``t_pose_blend`` is set this ramps 1->t_pos across the pre-roll so the cloth
      settles from the T-pose
    * ``pelvis_rotate`` — extra pelvis rotation

    Mirrors anim_subnet1: attribwrangle8 (deltas) -> transform6 (start align) ->
    transform1 (position mult) -> skeletonblend toward the T-pose -> pelvis rotate.
    """

    hou = _require_hou()
    geo = _shot_geo(shot, parent)
    tpose = geo.node("REST_SKEL")
    anim = geo.node("ANIM_TAKE")
    missing = [n for n, x in (("REST_SKEL", tpose), ("ANIM_TAKE", anim)) if x is None]
    if missing:
        raise ValueError(f"missing {missing}; run build_shot_setup + load_asset_caches first")

    fbx = shot.fbx
    fs, ps = shot.frame_start, shot.frame_start - shot.start_duration
    tp = float(fbx.t_pos)

    # Retarget the take onto the CLEAN REST_SKEL structure by joint name: copy the
    # take's world pose (P + transform) onto REST_SKEL's joints. This is the
    # cached-skeleton equivalent of anim_subnet1/skeletonblend1 — we CANNOT use a
    # real kinefx::skeletonblend here because REST_SKEL is a bgeo-cached skeleton
    # (289 pts / 169 bone prims, no localtransform) whose hierarchy representation
    # differs from a fresh fbxcharacterimport, so skeletonblend miscomputes world
    # transforms. The name-matched world copy is exact (pelvis->pelvis) and robust
    # to the cache round-trip. The take's non-joint FBX-graph nodes are dropped
    # (they have no name match in REST_SKEL); joints absent from the take hold the
    # T-pose. NOTE: this outputs the RAW take world positions (large root offset);
    # the anim_align / rotate stages below apply the anim_subnet1 alignment.
    aclean = _child(geo, "anim_clean", "attribwrangle")
    aclean.parm("class").set(2)  # points
    aclean.parm("snippet").set(POSE_COPY_VEX)
    aclean.setInput(0, tpose, 0)   # REST_SKEL structure (name-matched target)
    aclean.setInput(1, anim, 0)    # take pose

    # T-pose base with the authored offset (studio Tpos_offset_transform1). The
    # offset RESHAPES the T-pose base itself (e.g. rotate the arms toward A-pose),
    # so it is applied directly — NOT scaled by t_pos. It is visible whenever the
    # T-pose base contributes: at the pre-roll start (weight1=0) and, when t_pos>0,
    # in the final blended pose. (Scaling by t_pos zeroed the offset at t_pos=0,
    # which defeated its purpose of minimizing the T-pose->take rotation.)
    tofs = _child(geo, "anim_tpose_ofs", "xform")
    tofs.parmTuple("t").set(tuple(fbx.t_pos_offset_translate))
    tofs.parmTuple("r").set(tuple(fbx.t_pos_offset_rotate))
    tofs.setInput(0, tpose, 0)

    # rigid root alignment: start-align (t_pose_start_position) + per-axis
    # position_mult root-motion retention, in one point wrangle. in1 = the take
    # at the start frame, in2 = the T-pose.
    ts_start = _child(geo, "anim_start_ts", "timeshift")
    ts_start.parm("frame").deleteAllKeyframes()
    ts_start.parm("frame").set(fs)
    ts_start.setInput(0, aclean, 0)
    align = _child(geo, "anim_align", "attribwrangle")
    align.parm("class").set(2)  # points
    align.parm("snippet").set(ANIM_ALIGN_VEX.format(
        pelvis=fbx.pelvis_name, tpose_start=float(fbx.t_pose_start_position),
        mx=float(fbx.position_mult[0]), my=float(fbx.position_mult[1]),
        mz=float(fbx.position_mult[2])))
    align.setInput(0, aclean, 0)
    align.setInput(1, ts_start, 0)
    align.setInput(2, tofs, 0)

    # root ROTATION retention (rotate_mult) — anim_subnet1 attribwrangle10 +
    # rigpose1/6 + skeletonblend4. Freeze the pelvis at its start orientation,
    # then blend that against the full-rotation pose by rotate_mult (1 = full
    # world rotation, 0 = hold the start facing). Rotation lives on `transform`,
    # untouched by the translation align above, so `align` carries it through.
    rmul = float(fbx.rotate_mult)
    rot_ts = _child(geo, "anim_rot_ts", "timeshift")
    rot_ts.parm("frame").deleteAllKeyframes()
    rot_ts.parm("frame").set(fs)
    rot_ts.setInput(0, align, 0)
    rdelta = _child(geo, "anim_rotdelta", "attribwrangle")
    rdelta.parm("class").set(0)  # detail
    rdelta.parm("snippet").set(ROT_DELTA_VEX.format(pelvis=fbx.pelvis_name))
    rdelta.setInput(0, align, 0)
    rdelta.setInput(1, rot_ts, 0)
    rremove = _child(geo, "anim_rot_remove", "kinefx::rigpose")  # cancel current rot
    rremove.parm("transformations").set(1)  # one pose entry -> group0/r0x appear
    rremove.parm("group0").set(f"@name={fbx.pelvis_name}")
    for i, ax in enumerate("xyz"):
        if rremove.parm("r0" + ax):
            rremove.parm("r0" + ax).setExpression('detail(0,"rotate",%d)' % i)
    rremove.setInput(0, rdelta, 0)
    rstart = _child(geo, "anim_rot_start", "kinefx::rigpose")  # re-apply start rot
    rstart.parm("transformations").set(1)
    rstart.parm("group0").set(f"@name={fbx.pelvis_name}")
    for i, ax in enumerate("xyz"):
        if rstart.parm("r0" + ax):
            rstart.parm("r0" + ax).setExpression('detail(0,"trotate",%d)' % i)
    rstart.setInput(0, rremove, 0)
    rblend = _child(geo, "anim_rot_blend", "kinefx::skeletonblend::3.0")
    rblend.parm("nblends").set(2)
    rblend.parm("weight0").set(0)
    if rblend.parm("matchattrib"):
        rblend.parm("matchattrib").set(1)
    rblend.setInput(0, rstart, 0)   # rotation frozen at start (weight1 = 0)
    rblend.setInput(1, align, 0)    # full rotation           (weight1 = 1)
    rblend.parm("weight1").deleteAllKeyframes()
    rblend.parm("weight1").set(rmul)

    # blend the pose between the T-pose and the animation (studio skeletonblend:
    # in0 = T-pose base, in1 = animation, weight1 = amount of ANIM). weight1=1 is
    # full animation, 0 is full T-pose. Static value = 1 - t_pos; when
    # t_pose_blend is set it ramps 0 -> (1 - t_pos) across the pre-roll so the
    # cloth settles from the T-pose. After alignment the start pelvis sits on the
    # T-pose, so this is a pose blend with no flying.
    tblend = _child(geo, "anim_tpose_blend", "kinefx::skeletonblend::3.0")
    tblend.parm("nblends").set(2)
    tblend.parm("weight0").set(0)
    if tblend.parm("matchattrib"):
        tblend.parm("matchattrib").set(1)
    tblend.setInput(0, tofs, 0)      # T-pose base (weight1 = 0)
    tblend.setInput(1, rblend, 0)    # animation (rotate_mult applied) (weight1 = 1)
    anim_amt = 1.0 - tp
    tblend.parm("weight1").deleteAllKeyframes()
    if shot.t_pose_blend and shot.start_duration > 0:
        tblend.parm("weight1").setExpression(
            f"fit(clamp($FF,{ps},{fs}),{ps},{fs},0,{anim_amt})")
    else:
        tblend.parm("weight1").set(anim_amt)

    # extra pelvis rotation (rigpose9)
    upstream = tblend
    pr = fbx.pelvis_rotate
    if any(pr):
        rp = _child(geo, "anim_pelvis_rot", "kinefx::rigpose")
        rp.setInput(0, tblend, 0)
        if rp.parm("group"):
            rp.parm("group").set(fbx.pelvis_name)
        for i, ax in enumerate("xyz"):
            if rp.parm("r0" + ax):
                rp.parm("r0" + ax).set(float(pr[i]))
        upstream = rp
    else:
        stale = geo.node("anim_pelvis_rot")
        if stale is not None:
            stale.destroy()

    # drive take-absent accessory joints (hairBand1) via the REST_SKEL bone
    # hierarchy so they follow their real parent (head) instead of freezing at
    # rest — see ACCESSORY_FOLLOW_VEX.
    accfollow = _child(geo, "anim_accessory_follow", "attribwrangle")
    accfollow.parm("class").set(2)  # points
    accfollow.parm("snippet").set(ACCESSORY_FOLLOW_VEX)
    accfollow.setInput(0, upstream, 0)
    accfollow.setInput(1, tpose, 0)   # REST_SKEL (rest reference + bone hierarchy)
    accfollow.setInput(2, anim, 0)    # ANIM_TAKE (name-membership test)
    upstream = accfollow

    anim_skel = _child(geo, "ANIM_SKEL", "null")
    anim_skel.setInput(0, upstream, 0)
    anim_skel.setDisplayFlag(True)
    geo.layoutChildren()
    return {"anim_skel": anim_skel.path(), "t_pose_start_position": fbx.t_pose_start_position,
            "position_mult": list(fbx.position_mult), "rotate_mult": rmul, "t_pos": tp,
            "t_pose_blend": shot.t_pose_blend}


# ---------------------------------------------------------------------------
# Stage 3.3 — skeletal deform: bring the rest proxy into the animated pose
# ---------------------------------------------------------------------------
def build_shot_deform(shot: ShotSimConfig, parent: str = "/obj") -> dict[str, Any]:
    """Stage 3.3 — build the animated BODY CAGE that drives every shot deform.

    A single cage is bone-deformed from the rest corrective by the take, and it
    drives the per-part proxy deform (inside the constraint chain, Stage 3.5) and
    the collision deform (Stage 3.4)::

        cage_rest     = REST_CORRECTIVE                        (asset rest cache)
        ANIM_CORRECTIVE = bonedeform(REST_CORRECTIVE, capture-pose, ANIM_SKEL)

    ``OUT_CORRECTIVE`` descends from the fbx skin mesh (which carries
    ``boneCapture``) through attribute-preserving split/edit/merge, so the cached
    corrective can be bone-deformed directly — no capture transfer, and because
    the rest cage (REST_CORRECTIVE) and deformed cage (ANIM_CORRECTIVE) are the
    same mesh, pointDeform pairings stay exact.

    NOTE: the proxy itself is no longer deformed here — under the confirmed HDA
    model the deform sits UPSTREAM of the per-part constraints, so the proxy
    deform happens inside :func:`build_shot_constraint`. This step only produces
    the shared cage.
    """

    hou = _require_hou()
    geo = _shot_geo(shot, parent)
    corr = geo.node("REST_CORRECTIVE")
    skel = geo.node("REST_SKEL")
    anim_skel = geo.node("ANIM_SKEL")
    missing = [n for n, x in (("REST_CORRECTIVE", corr), ("REST_SKEL", skel),
                              ("ANIM_SKEL", anim_skel)) if x is None]
    if missing:
        raise ValueError(
            f"missing {missing}; run build_shot_setup + load_asset_caches + "
            "build_shot_anim first"
        )

    # animate the corrective cage by the aligned take (ANIM_SKEL from
    # build_shot_anim, which already applied the anim_subnet1 alignment/blend).
    # in1 = the ASSET capture-pose skeleton (REST_SKEL, which OUT_CORRECTIVE's
    # boneCapture references), in2 = the aligned animated skeleton.
    cage = _child(geo, "cage_deform", "bonedeform")
    cage.setInput(0, corr, 0)
    cage.setInput(1, skel, 0)
    cage.setInput(2, anim_skel, 0)
    anim_corr = _child(geo, "ANIM_CORRECTIVE", "null")
    anim_corr.setInput(0, cage, 0)

    # the standalone proxy deform is retired (proxy is deformed per-part inside
    # the constraint chain now); clean up nodes from the old flow.
    for stale in ("proxy_deform", "ANIM_PROXY"):
        n = geo.node(stale)
        if n is not None:
            n.destroy()

    geo.layoutChildren()
    return {"cage_deform": cage.path(), "anim_corrective": anim_corr.path()}


# ---------------------------------------------------------------------------
# Stage 3.4 — animated collision + per-frame push-apart
# ---------------------------------------------------------------------------
def build_shot_collision(shot: ShotSimConfig, parent: str = "/obj",
                         use_hda: bool = True,
                         hda_version: str | None = None,
                         input_pattern: str | None = None) -> dict[str, Any]:
    """Stage 3.4 — bring the rest collision to the animation, resolve penetration.

    The rest collision is a VDB-reshrunk mesh (``convertvdb`` rebuilds topology,
    so it carries no ``boneCapture`` — it can't be bone-deformed). Like the
    studio ``collision_subnet/pointdeform2`` it is pointDeformed by the body
    cage instead (rest = REST_CORRECTIVE, deformed = ANIM_CORRECTIVE from Stage
    3.3), then the per-frame anti-penetration push-apart runs on the animated
    surface: peak (inflate) -> SDF -> :data:`asset_builder.PUSH_APART_VEX`
    self-intersection resolve -> group-expand -> localized smooth.

    Push-apart params come from ``shot.sim_params`` (meter-scale defaults). Set
    ``sim_params.push_apart = False`` to skip it (deform only).
    """

    hou = _require_hou()
    geo = _shot_geo(shot, parent)
    corr = geo.node("REST_CORRECTIVE")
    anim_corr = geo.node("ANIM_CORRECTIVE")
    coll = geo.node("REST_COLLISION")
    missing = [n for n, x in (("REST_CORRECTIVE", corr),
                              ("ANIM_CORRECTIVE", anim_corr)) if x is None]
    if missing:
        raise ValueError(f"missing {missing}; run load_asset_caches + build_shot_deform first")

    sp = shot.sim_params
    requested_version = hda_version or shot.metadata.get("asset_version")
    warnings: list[str] = []
    type_name = (_resolve_stage_hda(
        shot.show, shot.asset, "collision", requested_version)
                 if use_hda else None)
    if use_hda and type_name is None:
        warnings.append(
            "Asset Collision HDA is not published; using the legacy "
            "REST_COLLISION point-deform setup")
    elif type_name and requested_version:
        requested_label = "v%03d" % int(str(requested_version).lstrip("v"))
        if not type_name.endswith("_" + requested_label):
            warnings.append(
                "Collision HDA %s is unavailable; using %s"
                % (requested_label, type_name.rsplit("_", 1)[-1]))
    if type_name:
        # The published Collision HDA expects only the animated body/head mesh,
        # not the complete ANIM_CORRECTIVE stream.  Keep this selection as an
        # explicit shot-level node so asset-specific name patterns remain
        # inspectable and editable.
        collision_input = _child(
            geo, "collision_input_anim_mesh", "blast")
        collision_input.parm("group").set(
            input_pattern or
            "@name=body_mesh @name=head_lod0_mesh1")
        collision_input.parm("negate").set(1)
        collision_input.setInput(0, anim_corr, 0)
        collision_hda = _child(geo, "collision_hda", type_name)
        collision_hda.setInput(0, collision_input, 0)
        upstream = collision_hda
        stale = geo.node("coll_deform")
        if stale is not None:
            stale.destroy()
        mode = "asset_hda"
    else:
        collision_input = geo.node("collision_input_anim_mesh")
        if collision_input is not None:
            collision_input.destroy()
        if coll is None:
            raise ValueError(
                "REST_COLLISION missing and no Collision HDA is published")
        cdef = _child(geo, "coll_deform", "pointdeform")
        cdef.setInput(0, coll, 0)
        cdef.setInput(1, corr, 0)
        cdef.setInput(2, anim_corr, 0)
        upstream = cdef
        collision_hda = geo.node("collision_hda")
        if collision_hda is not None:
            collision_hda.destroy()
        mode = "legacy_pointdeform"

    # The Asset Collision HDA now mirrors assets1/Collision/collision_subnet and
    # already owns peak/SDF separation + local smoothing. Keep this legacy shot
    # branch only for assets that have not published the Collision HDA yet.
    apply_shot_push = bool(sp.get("push_apart", True) and mode != "asset_hda")
    if apply_shot_push:
        nrm = _child(geo, "sim_col_normal", "normal")
        nrm.parm("type").set(0)       # point normals for @N
        nrm.setInput(0, upstream, 0)
        peak = _child(geo, "sim_col_peak", "peak")
        peak.parm("dist").set(float(sp.get("push_peak", 0.005)))
        peak.setInput(0, nrm, 0)
        pvdb = _child(geo, "sim_col_push_vdb", "vdbfrompolygons")
        pvdb.parm("voxelsize").set(float(sp.get("push_voxel", 0.01)))
        pvdb.setInput(0, peak, 0)
        push = _child(geo, "sim_col_push", "attribwrangle")
        push.parm("class").set(2)  # points (0=detail,1=prim,2=point)
        push.parm("snippet").set(PUSH_APART_VEX.format(
            sample=float(sp.get("push_sample", 0.005)),
            move=float(sp.get("push_move", 1.5))))
        push.setInput(0, peak, 0)
        push.setInput(1, pvdb, 0)
        expand = _child(geo, "sim_col_push_expand", "groupexpand")
        if expand.parm("group"):
            expand.parm("group").set("pushed")
        if expand.parm("steps"):
            expand.parm("steps").set(int(sp.get("push_expand_steps", 2)))
        expand.setInput(0, push, 0)
        psm = _child(geo, "sim_col_push_smooth", "smooth::2.0")
        psm.parm("group").set("pushed")
        psm.setInput(0, expand, 0)
        upstream = psm
    else:  # keep the network clean when disabled
        for stale in ("sim_col_push_smooth", "sim_col_push_expand", "sim_col_push",
                      "sim_col_push_vdb", "sim_col_peak", "sim_col_normal"):
            n = geo.node(stale)
            if n is not None:
                n.destroy()

    out = _child(geo, "OUT_SIM_COLLISION", "null")
    out.setInput(0, upstream, 0)
    geo.layoutChildren()
    return {
        "mode": mode,
        "collision_hda": (collision_hda.path()
                          if type_name and collision_hda is not None else None),
        "collision_input": (
            collision_input.path() if type_name and collision_input is not None
            else None),
        "input_pattern": input_pattern,
        "out_sim_collision": out.path(),
        "push_apart": apply_shot_push,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Stage 3.5a — instantiate the per-part constraint chain (deform upstream)
# ---------------------------------------------------------------------------
def _resolve_constraint_hda(show: str, asset: str, version: str | None = None,
                            otl_root: str = CONSTRAINT_HDA_ROOT) -> str | None:
    """Find the published constraint HDA for ``show``/``asset`` (newest, or a given
    ``version``), install it, and return its operator type name — or None when no
    HDA has been published. Mirrors :func:`asset_builder.save_constraint_hda`."""

    import os
    hou = _require_hou()
    hda_dir = _constraint_hda_dir(otl_root, show, asset)
    vers = _constraint_hda_versions(hda_dir, asset)
    if not vers:
        return None
    requested = int(str(version).lstrip("v")) if version else vers[-1]
    # Rest-cache and HDA publish versions are independent.  Prefer an exact
    # match, but never rebuild the huge legacy constraint chain merely because
    # cache v003 is using the latest published Constraint HDA v001.
    vnum = requested if requested in vers else vers[-1]
    hda_file = "%s/cfx_constraint_%s_v%03d.hda" % (hda_dir, asset, vnum)
    if not os.path.isfile(hda_file):
        return None
    hou.hda.installFile(hda_file)
    return "cfx_constraint_%s_%s_v%03d" % (show, asset, vnum)


def _resolve_stage_hda(show: str, asset: str, stage: str,
                       version: str | None = None,
                       otl_root: str = STAGE_HDA_ROOT) -> str | None:
    """Install a published Asset Collision/Deform stage HDA.

    Prefer the requested Asset Cache version. If that stage was not published
    at the same version, use the newest available stage HDA so existing assets
    remain usable during migration.
    """

    import os

    hou = _require_hou()
    stage_key = stage.lower()
    hda_dir = _constraint_hda_dir(otl_root, show, asset)
    versions = _stage_hda_versions(hda_dir, asset, stage_key)
    if not versions:
        return None
    requested = int(str(version).lstrip("v")) if version else versions[-1]
    vnum = requested if requested in versions else versions[-1]
    hda_file = "%s/cfx_%s_%s_v%03d.hda" % (
        hda_dir, stage_key, asset, vnum)
    if not os.path.isfile(hda_file):
        return None
    hou.hda.installFile(hda_file)
    return "cfx_%s_%s_%s_v%03d" % (
        stage_key, show, asset, vnum)


# hair points: reset to the REST position (undo the cloth cage deform) then ride
# the animated head — so head-follow parts are not double-transformed by the cage.
_HDA_HAIR_FOLLOW_VEX = """matrix m = detail(1, "head_delta");
@P = v@__restP;
@P *= m;
if (haspointattrib(0, "N")) @N = normalize(@N * matrix3(m));
if (haspointattrib(0, "v")) @v *= matrix3(m);
"""


def _build_shot_constraint_from_hda(shot: ShotSimConfig, asset: AssetSetupConfig,
                                    geo, type_name: str) -> dict[str, Any]:
    """Build the shot constraint in the artist-authored *deform first* order.

    The approved Lucy setup point-deforms ``REST_PROXY`` to the animated cage
    before it enters the published CONSTRAINT HDA.  The HDA therefore creates
    cloth/pin/attach constraints from the animated start pose and receives the
    shot collision stream directly.  This mirrors the hand-edited shot network::

        REST_PROXY -> hda_deform -> constraint_hda -> unpack -> pack
                                      ^ input 1: shot collision
                                      ^ input 2: ANIM_CORRECTIVE

    Older builds constrained the rest proxy first and deformed the packed result
    afterwards.  Rebuilding such a shot would undo the artist's setup, so the HDA
    instance contents are deliberately made editable and its legacy top-level
    source nodes are reconnected to the same animated inputs used by the approved
    network.
    """

    _require_hou()
    proxy = geo.node("REST_PROXY")
    rest_cage = geo.node("REST_CORRECTIVE")
    anim_cage = geo.node("ANIM_CORRECTIVE")
    # Prefer the fully prepared shot collision.  During a flat rebuild this is
    # OUT_SIM_COLLISION; in an organized existing shot it can be the COLLISION
    # stage subnet.  REST_COLLISION is only a last-resort compatibility input.
    shot_collision = (geo.node("OUT_SIM_COLLISION") or geo.node("COLLISION")
                      or geo.node("REST_COLLISION"))

    # remove the config-rebuild (build_vellum_chain) nodes if switching from it
    for n in list(geo.children()):
        nm = n.name()
        if nm.startswith(("cin_", "vc_")) or nm == "constraint_merge" \
                or (nm.startswith("OUT_") and nm.endswith("_CONSTRAINT") and nm != "OUT_CONSTRAINT"):
            n.destroy()

    # 1. Move the rest proxy to the animated start pose BEFORE constraints.
    pd = _child(geo, "hda_deform", "pointdeform")
    pd.setInput(0, proxy, 0)
    pd.setInput(1, rest_cage, 0)
    pd.setInput(2, anim_cage, 0)

    # 2. Instantiate the hand-authored HDA on the animated proxy.
    # The stage node itself is the published HDA.  Do not hide it one level
    # deeper inside a generated subnet also named CONSTRAINT.
    stale_inst = geo.node("constraint_hda")
    if stale_inst is not None:
        stale_inst.destroy()
    inst = _child(geo, "CONSTRAINT", type_name)
    inst.setInput(0, pd, 0)
    if shot_collision is not None:
        inst.setInput(1, shot_collision, 0)
    inst.setInput(2, anim_cage, 0)

    # Published v001 HDAs ignored the original subnet's external references.
    # Recreate the approved hand-wired connections through the HDA's formal
    # indirect inputs.  Connecting child SOPs straight to nodes outside the HDA
    # works interactively but hou.Node.setInput correctly rejects that boundary
    # crossing; indirect inputs preserve the same data flow robustly.
    if inst.isLockedHDA():
        inst.allowEditingOfContents()
    hda_inputs = inst.indirectInputs()
    animated_input = hda_inputs[0]
    collision_input = hda_inputs[1] if len(hda_inputs) > 1 else None
    cage_input = hda_inputs[2] if len(hda_inputs) > 2 else None
    for child in inst.children():
        name = child.name()
        if name.startswith("cin_") or name == "hair_ref":
            child.setInput(0, animated_input, 0)
    cage_source = inst.node("blast1")
    if cage_source is not None and cage_input is not None:
        cage_source.setInput(0, cage_input, 0)
    collision_merge = inst.node("merge4")
    if collision_merge is not None and collision_input is not None:
        collision_merge.setInput(1, collision_input, 0)

    # 3. Normalize the HDA boundary to the packed geometry expected by SOLVE.
    unpack = _child(geo, "hda_unpack", "vellumunpack")
    unpack.setInput(0, inst, 0)
    pack = _child(geo, "hda_pack", "vellumpack")
    pack.setInput(0, unpack, 0)
    pack.setInput(1, unpack, 1)

    # Retire nodes from the previous constrain-first/post-deform implementation.
    for stale in ("hda_restsnap", "hda_hairgrp", "hda_headdelta",
                  "hda_headfollow"):
        node = geo.node(stale)
        if node is not None:
            node.destroy()

    out = _child(geo, "OUT_CONSTRAINT", "null")
    out.setInput(0, pack, 0)
    geo.layoutChildren()
    return {
        "mode": "hda_deform_first",
        "hda_type": type_name,
        "out_constraint": out.path(),
        "animated_proxy": pd.path(),
        "shot_collision": shot_collision.path() if shot_collision is not None else None,
    }


def build_shot_constraint(shot: ShotSimConfig, asset: AssetSetupConfig,
                          parent: str = "/obj", use_hda: bool = True,
                          hda_version: str | None = None) -> dict[str, Any]:
    """Stage 3.5a — bring in the asset's constraint setup WITH the animation.

    Preferred path (``use_hda``): instantiate the published asset CONSTRAINT HDA
    (:func:`asset_builder.save_constraint_hda`) so the shot uses the exact
    hand-authored setup, then animate its output (see
    :func:`_build_shot_constraint_from_hda`). When no HDA is published it falls
    back to rebuilding the chain from the asset CONFIG via
    :func:`asset_builder.build_vellum_chain` (the deform sits UPSTREAM of the
    constraints; cloth pointDeforms by the body cage with a ``vellumrestblend``,
    hair rides the head). Either way produces the packed ``OUT_CONSTRAINT``
    consumed by :func:`build_shot_solve`.
    """

    hou = _require_hou()
    geo = _shot_geo(shot, parent)
    rest_cage = geo.node("REST_CORRECTIVE")
    anim_cage = geo.node("ANIM_CORRECTIVE")
    proxy = geo.node("REST_PROXY")
    hair = geo.node("REST_HAIR")
    missing = [n for n, x in (("REST_CORRECTIVE", rest_cage),
                              ("ANIM_CORRECTIVE", anim_cage),
                              ("REST_PROXY", proxy)) if x is None]
    if missing:
        raise ValueError(
            f"missing {missing}; run load_asset_caches + build_shot_deform first"
        )

    # preferred: instantiate the published constraint HDA (hand-authored, as-is)
    if use_hda:
        type_name = _resolve_constraint_hda(shot.show, shot.asset, hda_version)
        if type_name:
            result = _build_shot_constraint_from_hda(
                shot, asset, geo, type_name)
            if hda_version:
                requested_label = "v%03d" % int(
                    str(hda_version).lstrip("v"))
                if not type_name.endswith("_" + requested_label):
                    result.setdefault("warnings", []).append(
                        "Constraint HDA %s is unavailable; using %s"
                        % (requested_label, type_name.rsplit("_", 1)[-1]))
            return result

    # fallback: rebuild from the asset config
    published_stage = geo.node("CONSTRAINT")
    if (published_stage is not None
            and published_stage.type().definition() is not None):
        published_stage.destroy()
    for stale in ("constraint_hda", "hda_unpack", "hda_restsnap", "hda_deform",
                  "hda_hairgrp", "hda_headdelta", "hda_headfollow", "hda_pack"):
        n = geo.node(stale)
        if n is not None:
            n.destroy()

    def src_for_part(part):
        base = proxy if part.cloth else hair
        if base is None:
            return None
        # isolate this part from the merged proxy cache by its proxy_path tag
        tag = part.proxy_path or part.name
        b = _child(geo, f"cin_{part.name}", "blast")
        b.parm("group").set(f"@proxy_path={tag}")
        b.parm("negate").set(1)  # keep only this part
        b.setInput(0, base, 0)
        return b

    # cloth deforms by the body cage; hair rides the animated head joint
    # (head-follow) -> pass the rest + animated skeletons too.
    res = build_vellum_chain(
        geo, asset.proxy_parts, asset.constraint, src_for_part,
        rest_cage=rest_cage, anim_cage=anim_cage,
        rest_skel=geo.node("REST_SKEL"), anim_skel=geo.node("ANIM_SKEL"),
    )
    return res


# ---------------------------------------------------------------------------
# Stage 3.5b — vellum solve (shot sim_params only)
# ---------------------------------------------------------------------------
def build_shot_solve(shot: ShotSimConfig, parent: str = "/obj") -> dict[str, Any]:
    """Stage 3.5b — solve the (already animated) cloth against the collision.

    The constraint chain (Stage 3.5a) already deformed the proxy to the animation
    upstream of the constraints and packed it into ``OUT_CONSTRAINT``. Here it is
    unpacked into its two branches and solved::

        OUT_CONSTRAINT -> vellumunpack
            out0 (Vellum Geometry, animated)
                -> shot_constraint_edit -> normalize_point_id ---------┐
            out1 (Constraint Geometry) --------------------------------┤
                                                                       v
                        vellumsolver(geo, constraints, collision=OUT_SIM_COLLISION)
                            -> vellumpostprocess -> OUT_SIM

    No deform here — it happened upstream in the constraint chain. The
    ``shot_constraint_edit`` gate is for optional per-shot constraint tweaks.
    Only the shot ``sim_params`` touch the solver (substeps / thickness /
    collision iterations).

    NOTE: pin-follows-animation still needs live tuning in an end-to-end cook.
    """

    hou = _require_hou()
    geo = _shot_geo(shot, parent)
    con = geo.node("OUT_CONSTRAINT")
    sim_col = geo.node("OUT_SIM_COLLISION")
    missing = [n for n, x in (("OUT_CONSTRAINT", con),
                              ("OUT_SIM_COLLISION", sim_col)) if x is None]
    if missing:
        raise ValueError(
            f"missing {missing}; run build_shot_constraint + build_shot_collision first"
        )

    # retire nodes from the earlier object_merge / in-solve-deform flow
    for stale in ("constraint_in", "constraint_deform", "ANIM_CONSTRAINT"):
        n = geo.node(stale)
        if n is not None:
            n.destroy()

    sp = shot.sim_params
    unpack = _child(geo, "constraint_unpack", "vellumunpack")
    unpack.setInput(0, con, 0)
    # optional per-shot tweak gate on the (animated) vellum geometry
    edit = _child(geo, "shot_constraint_edit", "edit")
    edit.setInput(0, unpack, 0)

    # Vellum Pack inputs can contain an ``id`` attribute on only some parts.
    # Vellum Unpack then fills the missing values with -1, producing thousands
    # of duplicate ids after the parts are combined.  Normalize once, after
    # all parts have been unpacked and any shot edit has run, so the solver
    # receives one globally unique point id per point.  This assumes the
    # simulation topology / point order is stable over the shot, which is the
    # contract of the prepared CFX proxy geometry.
    normalize_id = _child(geo, "normalize_point_id", "attribwrangle")
    normalize_id.setInput(0, edit, 0)
    if normalize_id.parm("class") is not None:
        normalize_id.parm("class").set("point")
    if normalize_id.parm("snippet") is not None:
        normalize_id.parm("snippet").set("i@id = @ptnum;")

    solver = _child(geo, "vellum_solve", "vellumsolver")
    solver.setInput(0, normalize_id, 0) # Vellum Geometry with unique point ids
    solver.setInput(1, unpack, 1)       # Constraint Geometry (rest lengths intact)
    solver.setInput(2, sim_col, 0)      # Collision Geometry
    # start the sim at the pre-roll start so the cloth settles before frame_start
    if solver.parm("startframe"):
        solver.parm("startframe").deleteAllKeyframes()
        solver.parm("startframe").setExpression(
            "$FSTART", hou.exprLanguage.Hscript)
    if sp.get("substeps") is not None and solver.parm("substeps"):
        solver.parm("substeps").set(int(sp["substeps"]))
    thickness = sp.get(
        "collision_thickness",
        sp.get("thickness", SOLVER_TUNED_DEFAULTS["collision_thickness"]))
    if thickness is not None and solver.parm("thickness"):
        solver.parm("thickness").set(float(thickness))
    solver_values = (
        ("niter", sp.get(
            "constraint_iterations",
            SOLVER_TUNED_DEFAULTS["constraint_iterations"])),
        ("collisionsiter", sp.get(
            "collision_iterations",
            SOLVER_TUNED_DEFAULTS["collision_iterations"])),
        ("postcollisioniter", sp.get(
            "post_collision_iterations",
            SOLVER_TUNED_DEFAULTS["post_collision_iterations"])),
    )
    for parm_name, value in solver_values:
        if solver.parm(parm_name) is not None:
            solver.parm(parm_name).set(int(value))
    for parm_name in (
            "windshadow_maskfalloff1pos",
            "windshadow_maskfalloff1value",
            "windshadow_maskfalloff2pos"):
        if solver.parm(parm_name) is not None:
            solver.parm(parm_name).set(
                SOLVER_TUNED_DEFAULTS[parm_name])

    post = _child(geo, "vellum_post", "vellumpostprocess")
    post.setInput(0, solver, 0)
    out = _child(geo, "OUT_SIM", "null")
    out.setInput(0, post, 0)
    out.setDisplayFlag(True)
    geo.layoutChildren()
    return {"constraint_unpack": unpack.path(), "constraint_edit": edit.path(),
            "normalize_point_id": normalize_id.path(),
            "vellum_solve": solver.path(), "out_sim": out.path()}


# ---------------------------------------------------------------------------
# Stage 3.6 — sim filecache
# ---------------------------------------------------------------------------
def _validate_sim_cache_wiring(geo, filecache=None):
    """Return the connected ``OUT_SIM`` or fail before writing an empty cache."""

    out_sim = geo.node("OUT_SIM")
    if out_sim is None:
        raise ValueError("OUT_SIM missing; run build_shot_solve first")
    if out_sim.input(0) is None:
        raise RuntimeError(
            "OUT_SIM is disconnected. Repair the SOLVE output before writing "
            "the sim cache."
        )
    if filecache is not None and filecache.input(0) != out_sim:
        actual = filecache.input(0)
        raise RuntimeError(
            "sim_filecache must read directly from OUT_SIM. Current input: %s"
            % (actual.path() if actual is not None else "<disconnected>")
        )
    return out_sim


def _validate_nonempty_sim_cache(path: str) -> dict[str, int]:
    """Reject a successful-looking render when the written sim is empty."""

    hou = _require_hou()
    geometry = hou.Geometry()
    geometry.loadFromFile(path)
    counts = {
        "points": len(geometry.points()),
        "primitives": len(geometry.prims()),
    }
    if not counts["points"] and not counts["primitives"]:
        raise RuntimeError(
            "Sim cache render wrote empty geometry: %s" % path
        )
    return counts


def build_shot_cache(shot: ShotSimConfig, parent: str = "/obj",
                     execute: bool = False) -> dict[str, Any]:
    """Stage 3.6 — cache the solved cloth per-frame to disk.

    Writes ``OUT_SIM`` over the shot frame range via ``filecache::2.0``
    (``$F4`` per-frame). Gated by ``shot.sim_filecache`` (mirrors the studio
    ``Sim_FileCache`` toggle). Path comes from ``path_rules``
    (``sim_cache_path``). ``execute=True`` cooks the range now.
    """

    hou = _require_hou()
    geo = _shot_geo(shot, parent)
    src = _validate_sim_cache_wiring(geo)
    if not shot.sim_cache_path:
        return {"skipped": "no sim_cache_path resolved"}

    created = geo.node("sim_filecache") is None
    fc = _child(geo, "sim_filecache", "filecache::2.0")
    fc.parm("filemethod").set(1)         # explicit filename
    fc.parm("file").set(shot.sim_cache_path)
    fc.parm("trange").set(1)             # frame range
    if fc.parm("f1"):
        # Always follow the current Houdini global playback range at write time.
        # Expressions keep the cache range in sync if $FSTART/$FEND changes.
        fc.parm("f1").deleteAllKeyframes()
        fc.parm("f1").setExpression("$FSTART", hou.exprLanguage.Hscript)
        fc.parm("f2").deleteAllKeyframes()
        fc.parm("f2").setExpression("$FEND", hou.exprLanguage.Hscript)
    fc.setInput(0, src, 0)
    if created:
        fc.setPosition(src.position() + hou.Vector2(0.0, -1.0))
    cacheout = geo.node("CACHEOUT")
    if cacheout is not None:
        cacheout.setInput(0, fc, 0)

    written = False
    written_file = None
    written_geometry = None
    if execute and shot.sim_filecache:
        written_file = _execute_filecache(fc)
        written_geometry = _validate_nonempty_sim_cache(written_file)
        written = True
    return {"sim_filecache": fc.path(), "file": shot.sim_cache_path,
            "frame_range": [int(fc.evalParm("f1")), int(fc.evalParm("f2"))],
            "gated_by_sim_filecache": shot.sim_filecache,
            "written_file": written_file,
            "written_geometry": written_geometry,
            "written": written}


def execute_prepared_shot_cache(shot: ShotSimConfig,
                                parent: str = "/obj") -> dict[str, Any]:
    """Execute the sim File Cache already saved in the source HIP.

    A background worker must use the visible setup from the artist's HIP rather
    than silently creating a worker-only node that disappears with hython.
    """

    hou = _require_hou()
    geo = _shot_geo(shot, parent)
    fc = geo.node("sim_filecache")
    if fc is None:
        raise RuntimeError(
            "Prepared sim_filecache is missing from the saved HIP. "
            "Run Write Sim Cache again to prepare and save the setup.")
    _validate_sim_cache_wiring(geo, fc)
    expected_raw = (shot.sim_cache_path or "").replace("\\", "/")
    actual_raw = (fc.parm("file").rawValue() or "").replace("\\", "/")
    expected = hou.expandString(expected_raw).replace("\\", "/")
    actual = hou.expandString(actual_raw).replace("\\", "/")
    if expected_raw and actual_raw != expected_raw and actual != expected:
        raise RuntimeError(
            "Saved sim_filecache path does not match the job version.\n"
            "Saved: %s\nExpected: %s" % (actual_raw, expected_raw))
    written = _execute_filecache(fc)
    written_geometry = _validate_nonempty_sim_cache(written)
    return {
        "sim_filecache": fc.path(),
        "file": actual_raw,
        "written_file": written,
        "written_geometry": written_geometry,
        "frame_range": [int(fc.evalParm("f1")), int(fc.evalParm("f2"))],
        "prepared_in_source_hip": True,
        "written": True,
    }


# ---------------------------------------------------------------------------
# Stage 4 — Cache Out (detail-attach + joint-inverse + UE transform -> alembic)
# ---------------------------------------------------------------------------
def build_shot_cacheout(shot: ShotSimConfig, asset: AssetSetupConfig,
                        parent: str = "/obj", detail_attach: bool = True,
                        execute: bool = False,
                        use_deform_hda: bool = True,
                        hda_version: str | None = None) -> dict[str, Any]:
    """Stage 4 — build the UE alembic outputs (reconstructs the studio Deform+Out).

    Per cloth part the original hi-res garment is re-attached to the low-res sim
    via a pointDeform (Deform/Parts_Deform: geometry = rest hi-res, rest cage =
    rest proxy, deformed cage = sim proxy); hair uses the sim guides directly.
    Then the studio Out gimmicks:

    * cloth -> **pelvis-inverse** (origin-ize ``cache_out.cloth_attach_joint``)
      so UE re-parents under the pelvis; hair -> **head-inverse** (origin-ize the
      head, ``cache_out.hair_attach_chain[0]``)
    * ``face_shading_group`` (fbx_material_name -> prim group) for UE materials
    * UE transform: ``ue_scale`` (m->cm) + ``ue_rotate`` (Y-up -> Z-up)
    * ``rop_alembic`` -> ``cloth_abc_path`` / ``hair_abc_path`` (gated by
      ``cache_out.export_cloth`` / ``export_hair``)

    ``detail_attach=False`` exports the proxy sim directly (lighter, for testing).
    """

    hou = _require_hou()
    geo = _shot_geo(shot, parent)
    # CACHEOUT is a prepared, artist-inspectable stage.  If it is already an
    # organizational subnet, update its contents in place; never flatten the
    # rest of the shot merely to prepare an Alembic export.
    cacheout_stage = geo.node("CACHEOUT")
    work = (cacheout_stage if cacheout_stage is not None
            and cacheout_stage.type().name() == "subnet"
            and cacheout_stage.type().definition() is None else geo)
    # source the SIM from its filecache when available (reads the cached result
    # off disk instead of re-simulating); fall back to the live OUT_SIM.
    sim = geo.node("sim_filecache")
    if sim is not None and sim.parm("loadfromdisk"):
        sim.parm("loadfromdisk").set(1)
    if sim is None:
        sim = geo.node("OUT_SIM")
    skel = geo.node("ANIM_SKEL")
    corr = geo.node("REST_CORRECTIVE")
    rproxy = geo.node("REST_PROXY")
    missing = [n for n, x in (("sim", sim), ("ANIM_SKEL", skel)) if x is None]
    if missing:
        raise ValueError(f"missing {missing}; run build_shot_solve + build_shot_cache first")
    co = shot.cache_out
    export_end = shot.frame_end + int(co.frame_padding)
    result: dict[str, Any] = {"cloth": None, "hair": None, "warnings": []}
    outnet = hou.node("/out")
    if outnet is None:
        raise RuntimeError("/out ROP network not found")
    rop_prefix = "cfx_%s_%s" % (
        "".join(c if c.isalnum() or c == "_" else "_" for c in shot.shot),
        "".join(c if c.isalnum() or c == "_" else "_" for c in shot.asset),
    )

    # Nodes inside an organizational subnet must connect through its indirect
    # inputs/outputs; Houdini does not allow new direct cross-network wires.
    if work is not geo:
        indirect = work.indirectInputs()
        if len(indirect) < 4:
            raise RuntimeError(
                "CACHEOUT subnet needs inputs: SIM, REST_CORRECTIVE, "
                "REST_PROXY, ANIM_SKEL")
        work_sim, work_corr, work_rproxy, work_skel = indirect[:4]
    else:
        work_sim, work_corr, work_rproxy, work_skel = sim, corr, rproxy, skel

    def expose_output(name, source, source_output, output_index):
        if work is geo:
            interface = _child(geo, name, "null")
            interface.setInput(0, source, source_output)
            return interface
        output = work.node("output%d" % output_index)
        if output is None:
            output = work.createNode("output", "output%d" % output_index)
        output.parm("outputidx").set(output_index)
        output.setInput(0, source, source_output)
        interface = _child(geo, name, "null")
        interface.setInput(0, work, output_index)
        return interface

    def sim_part(part):
        b = _child(work, f"co_{part.name}_sim", "blast")
        b.parm("grouptype").set(4)  # primitives
        b.parm("group").set(
            f"@proxy_path={part.proxy_path or part.name}")
        b.parm("negate").set(1)     # keep only this part
        b.setInput(0, work_sim, 0)
        return b

    cloth_outs, hair_outs = [], []
    requested_version = hda_version or shot.metadata.get("asset_version")
    deform_type = (_resolve_stage_hda(
        shot.show, shot.asset, "deform", requested_version)
                   if use_deform_hda and detail_attach else None)
    if use_deform_hda and detail_attach and deform_type is None:
        result["warnings"].append(
            "Asset Deform HDA is not published; rebuilding the legacy "
            "per-part point-deform setup in the shot")
    elif deform_type and requested_version:
        requested_label = "v%03d" % int(str(requested_version).lstrip("v"))
        if not deform_type.endswith("_" + requested_label):
            result["warnings"].append(
                "Deform HDA %s is unavailable; using %s"
                % (requested_label, deform_type.rsplit("_", 1)[-1]))
    if deform_type and corr is not None and rproxy is not None:
        deform_hda = _child(work, "deform_hda", deform_type)
        if (asset.cloth_parts
                and deform_hda.node("dform_cloth_merge_empty") is not None):
            result["warnings"].append(
                "Published Deform HDA contains only an empty cloth output; "
                "using the per-part deform setup instead")
            deform_hda.destroy()
            deform_type = None

    if deform_type and corr is not None and rproxy is not None:
        deform_hda = work.node("deform_hda")
        deform_hda.setInput(0, work_sim, 0)
        deform_hda.setInput(1, work_corr, 0)
        deform_hda.setInput(2, work_rproxy, 0)
        cloth_from_hda = _child(work, "co_deform_cloth", "null")
        cloth_from_hda.setInput(0, deform_hda, 0)
        hair_from_hda = _child(work, "co_deform_hair", "null")
        hair_from_hda.setInput(0, deform_hda, 1)
        if asset.cloth_parts:
            cloth_outs.append(cloth_from_hda)
        if any(not part.cloth for part in asset.proxy_parts):
            hair_outs.append(hair_from_hda)
        for part in asset.proxy_parts:
            for suffix in ("sim", "hires", "rproxy", "sim_clean_id",
                           "rproxy_clean_id", "deform"):
                stale = work.node("co_%s_%s" % (part.name, suffix))
                if stale is not None:
                    stale.destroy()
        deform_mode = "asset_hda"
    else:
        stale_hda = work.node("deform_hda")
        if stale_hda is not None:
            stale_hda.destroy()
        for stale_name in ("co_deform_cloth", "co_deform_hair"):
            stale = work.node(stale_name)
            if stale is not None:
                stale.destroy()
        for part in asset.proxy_parts:
            sp = sim_part(part)
            if part.cloth:
                if (detail_attach and corr is not None and rproxy is not None
                        and part.geo_path):
                    existing_hires = work.node(f"co_{part.name}_hires")
                    hires = _child(work, f"co_{part.name}_hires", "blast")
                    # A part's high-res selection is commonly refined by the
                    # artist after preparation (for example ``@class=59``).
                    # Preserve a non-empty authored group on later Prepare
                    # runs; seed from config only for a new/empty node.
                    if (existing_hires is None
                            or not hires.parm("group").rawValue().strip()):
                        hires.parm("group").set(part.geo_group())
                    hires.parm("negate").set(1)
                    hires.setInput(0, work_corr, 0)
                    rp = _child(work, f"co_{part.name}_rproxy", "blast")
                    rp.parm("group").set(
                        f"@proxy_path={part.proxy_path or part.name}")
                    rp.parm("negate").set(1)
                    rp.setInput(0, work_rproxy, 0)

                    # Point Deform automatically uses ``id`` when it exists.
                    # Vellum assigns globally unique ids to SIM, while older
                    # REST_PROXY caches can contain -1, duplicates, or another
                    # id range.  That mismatch makes Point Deform freeze or
                    # produce a collapsed transform.  Strip id only on these
                    # two CACHEOUT lattice branches so solver/cache ids remain
                    # untouched and point-number correspondence is used.
                    rest_clean = _child(
                        work, f"co_{part.name}_rproxy_clean_id",
                        "attribdelete")
                    rest_clean.parm("ptdel").set("id")
                    rest_clean.setInput(0, rp, 0)
                    sim_clean = _child(
                        work, f"co_{part.name}_sim_clean_id",
                        "attribdelete")
                    sim_clean.parm("ptdel").set("id")
                    sim_clean.setInput(0, sp, 0)

                    pd = _child(work, f"co_{part.name}_deform", "pointdeform")
                    pd.setInput(0, hires, 0)
                    pd.setInput(1, rest_clean, 0)
                    pd.setInput(2, sim_clean, 0)
                    cloth_outs.append(pd)
                else:
                    cloth_outs.append(sp)
            else:
                hair_outs.append(sp)
        deform_mode = "legacy_rebuild"

    split_hair_from_cloth = bool(co.hair_split_geo_path.strip())
    export_stages = []
    if cloth_outs and co.export_cloth:
        export_stages.append("cloth")
    if (hair_outs or split_hair_from_cloth) and co.export_hair:
        export_stages.append("hair")

    def render_alembic(rop, stage):
        """Render an Alembic ROP directly and emit parseable stage progress."""

        index = export_stages.index(stage) + 1
        total = len(export_stages)
        print("[CFX ABC] START %s %d/%d" % (stage, index, total), flush=True)
        rop.render(verbose=True, output_progress=True)
        print("[CFX ABC] COMPLETE %s %d/%d" % (stage, index, total), flush=True)

    split_hair_source = None

    # Old versions created this destructive swap on every Cache Out rebuild.
    # Remove both possible locations so upgrading an organized HIP is clean.
    for stale_path in ("co_hair_uv0_swap", "CACHEOUT/co_hair_uv0_swap"):
        stale_uv_swap = geo.node(stale_path)
        if stale_uv_swap is not None:
            stale_uv_swap.destroy()

    # --- cloth branch: pelvis-inverse -> face shading -> UE transform ---
    if cloth_outs:
        cm = _child(work, "co_cloth_merge", "merge")
        for i, o in enumerate(cloth_outs):
            cm.setInput(i, o, 0)
        pinv = _child(work, "co_cloth_pelvis_inverse", "attribwrangle")
        # Detail mode transforms P/v plus either point or vertex N without
        # binding @N as a point attribute.  Binding @N in point mode silently
        # collapsed the authored REST_CORRECTIVE vertex normals to point N.
        pinv.parm("class").set(0)  # detail
        pinv.parm("snippet").set(JOINT_INV_VEX.replace("__JOINT__", co.cloth_attach_joint))
        pinv.setInput(0, cm, 0)
        pinv.setInput(1, work_skel, 0)
        fsg = _child(work, "co_face_shading", "attribwrangle")
        fsg.parm("class").set(1)  # primitives
        fsg.parm("snippet").set(FACE_SHADING_VEX)
        fsg.setInput(0, pinv, 0)
        ue = _child(work, "co_cloth_ue", "xform")
        ue.parm("scale").set(co.ue_scale)
        ue.parmTuple("r").set(co.ue_rotate)
        ue.setInput(0, fsg, 0)
        normal = _child(work, "co_cloth_normal", "normal")
        normal.parm("docompute").set(0)
        normal.parm("normalize").set(1)
        normal.parm("reverse").set(0)
        normal.parm("type").set("typevertex")
        normal.setInput(0, ue, 0)
        cloth_export_source = normal
        cloth_export_output = 0
        if split_hair_from_cloth:
            hair_split = _child(work, "co_hair_split", "split")
            hair_split.parm("grouptype").set("prims")
            hair_split.parm("group").set(
                "@geo_path=%s" % co.hair_split_geo_path.strip())
            hair_split.setInput(0, normal, 0)
            split_hair_source = hair_split
            cloth_export_source = hair_split
            cloth_export_output = 1

        out_cloth = expose_output(
            "OUT_CLOTH", cloth_export_source, cloth_export_output, 0)
        out_cloth.setDisplayFlag(True)
        # Alembic is a ROP operation.  A same-named ROP placed inside the SOP
        # network can return from render without writing a file in Houdini 21;
        # use the standard /out driver and point it at the prepared SOP.
        stale_rop = work.node("Cloth_Cache")
        if stale_rop is not None:
            stale_rop.destroy()
        rop = _child(outnet, rop_prefix + "_Cloth_Cache", "alembic")
        if shot.cloth_abc_path:
            rop.parm("filename").set(shot.cloth_abc_path)
        rop.parm("use_sop_path").set(1)
        rop.parm("sop_path").set(out_cloth.path())
        rop.parm("trange").set(1)
        rop.parm("f1").deleteAllKeyframes()
        rop.parm("f1").setExpression(
            "$FSTART", language=hou.exprLanguage.Hscript)
        rop.parm("f2").deleteAllKeyframes(); rop.parm("f2").set(export_end)
        if execute and co.export_cloth:
            render_alembic(rop, "cloth")
        result["cloth"] = {"out": out_cloth.path(), "rop": rop.path(),
                           "file": shot.cloth_abc_path}

    # --- hair branch: optional cloth-output split, otherwise head-inverse ---
    if split_hair_from_cloth and split_hair_source is not None:
        stale_roph = work.node("Hair_Cache")
        if stale_roph is not None:
            stale_roph.destroy()
        roph = _child(outnet, rop_prefix + "_Hair_Cache", "alembic")
        hair_export_source = _prepare_hair_uv_export(
            work, split_hair_source, roph, hou)
        out_hair = expose_output("OUT_HAIR", hair_export_source, 0, 1)
        if shot.hair_abc_path:
            roph.parm("filename").set(shot.hair_abc_path)
        roph.parm("use_sop_path").set(1)
        roph.parm("sop_path").set(out_hair.path())
        roph.parm("trange").set(1)
        roph.parm("f1").deleteAllKeyframes()
        roph.parm("f1").setExpression(
            "$FSTART", language=hou.exprLanguage.Hscript)
        roph.parm("f2").deleteAllKeyframes(); roph.parm("f2").set(export_end)
        if execute and co.export_hair:
            render_alembic(roph, "hair")
        result["hair"] = {"out": out_hair.path(), "rop": roph.path(),
                          "file": shot.hair_abc_path}
    elif hair_outs:
        hm = _child(work, "co_hair_merge", "merge")
        for i, o in enumerate(hair_outs):
            hm.setInput(i, o, 0)
        head = co.hair_attach_chain[0] if co.hair_attach_chain else "head"
        hinv = _child(work, "co_hair_head_inverse", "attribwrangle")
        hinv.parm("class").set(0)  # detail
        hinv.parm("snippet").set(JOINT_INV_VEX.replace("__JOINT__", head))
        hinv.setInput(0, hm, 0)
        hinv.setInput(1, work_skel, 0)
        ueh = _child(work, "co_hair_ue", "xform")
        ueh.parm("scale").set(co.ue_scale)
        ueh.parmTuple("r").set(co.ue_rotate)
        ueh.setInput(0, hinv, 0)
        stale_roph = work.node("Hair_Cache")
        if stale_roph is not None:
            stale_roph.destroy()
        roph = _child(outnet, rop_prefix + "_Hair_Cache", "alembic")
        hair_export_source = _prepare_hair_uv_export(work, ueh, roph, hou)
        out_hair = expose_output("OUT_HAIR", hair_export_source, 0, 1)
        if shot.hair_abc_path:
            roph.parm("filename").set(shot.hair_abc_path)
        roph.parm("use_sop_path").set(1)
        roph.parm("sop_path").set(out_hair.path())
        roph.parm("trange").set(1)
        roph.parm("f1").deleteAllKeyframes()
        roph.parm("f1").setExpression(
            "$FSTART", language=hou.exprLanguage.Hscript)
        roph.parm("f2").deleteAllKeyframes(); roph.parm("f2").set(export_end)
        if execute and co.export_hair:
            render_alembic(roph, "hair")
        result["hair"] = {"out": out_hair.path(), "rop": roph.path(),
                          "file": shot.hair_abc_path}

    result["deform_mode"] = deform_mode
    result["deform_hda"] = (
        work.node("deform_hda").path()
        if work.node("deform_hda") is not None else None)
    return result


def execute_prepared_shot_cacheout(
        shot: ShotSimConfig, parent: str = "/obj") -> dict[str, Any]:
    """Render the Alembic ROPs already saved in the source HIP."""

    hou = _require_hou()
    geo = _shot_geo(shot, parent)
    outnet = hou.node("/out")
    if outnet is None:
        raise RuntimeError("/out ROP network not found")
    prefix = "cfx_%s_%s" % (
        "".join(c if c.isalnum() or c == "_" else "_" for c in shot.shot),
        "".join(c if c.isalnum() or c == "_" else "_" for c in shot.asset),
    )
    co = shot.cache_out
    expected_range = (
        int(hou.playbar.frameRange()[0]),
        shot.frame_end + int(co.frame_padding))
    result: dict[str, Any] = {
        "prepared_in_source_hip": True,
        "cloth": None,
        "hair": None,
        "warnings": [],
    }
    specs = []
    if co.export_cloth:
        specs.append((
            "cloth", outnet.node(prefix + "_Cloth_Cache"),
            shot.cloth_abc_path, geo.node("OUT_CLOTH")))
    if co.export_hair:
        hair_rop = outnet.node(prefix + "_Hair_Cache")
        hair_sop = geo.node("OUT_HAIR")
        if hair_rop is None or hair_sop is None:
            missing = []
            if hair_rop is None:
                missing.append("Hair Alembic ROP")
            if hair_sop is None:
                missing.append("OUT_HAIR")
            message = (
                "Hair Alembic skipped: %s is not present in the saved HIP."
                % " and ".join(missing))
            result["hair"] = {
                "skipped": True,
                "reason": message,
            }
            result["warnings"].append(message)
            print("[CFX ABC] SKIP hair - %s" % message, flush=True)
        else:
            specs.append((
                "hair", hair_rop, shot.hair_abc_path, hair_sop))
    if not specs:
        result["skipped"] = (
            "no prepared Alembic exports are available"
            if co.export_cloth or co.export_hair
            else "no Alembic exports enabled")
        return result

    for index, (stage, rop, expected_path, sop) in enumerate(specs, 1):
        if rop is None or sop is None:
            raise RuntimeError(
                "Prepared %s Alembic setup is missing from the saved HIP."
                % stage)
        actual = (rop.parm("filename").rawValue() or "").replace("\\", "/")
        expected = (expected_path or "").replace("\\", "/")
        if expected and actual != expected:
            raise RuntimeError(
                "Saved %s Alembic path does not match the job version.\n"
                "Saved: %s\nExpected: %s" % (stage, actual, expected))
        sop_path = rop.parm("sop_path").evalAsString()
        if sop_path != sop.path():
            raise RuntimeError(
                "Saved %s Alembic SOP path is stale.\nSaved: %s\nExpected: %s"
                % (stage, sop_path, sop.path()))
        start_parm = rop.parm("f1")
        actual_start_raw = (start_parm.rawValue() or "").strip().upper()
        if actual_start_raw != "$FSTART":
            raise RuntimeError(
                "Saved %s Alembic start frame must use the HIP frame range.\n"
                "Saved: %s\nExpected: $FSTART"
                % (stage, actual_start_raw or "<empty>"))
        actual_range = (int(rop.evalParm("f1")), int(rop.evalParm("f2")))
        if actual_range != expected_range:
            raise RuntimeError(
                "Saved %s Alembic frame range is stale.\n"
                "Saved: %s-%s\nExpected: %s-%s"
                % ((stage,) + actual_range + expected_range))
        previous_frame = hou.frame()
        try:
            hou.setFrame(actual_range[0])
            geometry = sop.geometry()
            point_count = len(geometry.points())
            prim_count = len(geometry.prims())
        finally:
            hou.setFrame(previous_frame)
        if point_count == 0 or prim_count == 0:
            raise RuntimeError(
                "Prepared %s Alembic source is empty at frame %s: %s. "
                "The export was not started. Check the REST inputs and "
                "CACHEOUT deform stage."
                % (stage, actual_range[0], sop.path()))
        print("[CFX ABC] START %s %d/%d"
              % (stage, index, len(specs)), flush=True)
        rop.render(verbose=True, output_progress=True)
        if not os.path.isfile(actual) or os.path.getsize(actual) < 4096:
            size = os.path.getsize(actual) if os.path.isfile(actual) else 0
            raise RuntimeError(
                "%s Alembic export produced no usable geometry: %s "
                "(%d bytes)" % (stage.title(), actual, size))
        print("[CFX ABC] COMPLETE %s %d/%d"
              % (stage, index, len(specs)), flush=True)
        result[stage] = {
            "out": sop.path(), "rop": rop.path(), "file": actual}
    return result


# ---------------------------------------------------------------------------
# Network organization — collapse the auto-built nodes into stage subnets
# ---------------------------------------------------------------------------
# The container keeps a flat INTERFACE layer (readable / cross-stage / artist
# gates): REST_* caches, ANIM_SKEL, ANIM_CORRECTIVE, cage_deform, anim_take,
# OUT_CONSTRAINT, OUT_SIM_COLLISION, OUT_SIM, sim_filecache, OUT_CLOTH, OUT_HAIR.
# Everything else collapses into a stage subnet. Each predicate matches ONLY the
# auto/internal container-level children of that stage (never the interface nodes
# above), so collapse/extract is loss-less and connections auto-rewire. Build is
# kept idempotent by flattening (extractAndDelete) before every flat rebuild.
_SHOT_STAGES = [
    ("LOAD",       lambda n: n.startswith("load_")),
    ("ANIM",       lambda n: (n.startswith("anim_") and n != "anim_take")
                             or n == "ANIM_TAKE"),
    ("COLLISION",  lambda n: n.startswith("coll_") or n.startswith("sim_col")),
    ("CONSTRAINT", lambda n: n.startswith("cin_") or n.startswith("vc_")
                             or n == "constraint_merge"
                             or n == "constraint_hda" or n.startswith("hda_")
                             or (n.startswith("OUT_") and n.endswith("_CONSTRAINT")
                                 and n != "OUT_CONSTRAINT")),
    ("SOLVE",      lambda n: n in ("constraint_unpack", "shot_constraint_edit",
                                   "normalize_point_id", "vellum_solve",
                                   "vellum_post")),
    ("CACHEOUT",   lambda n: n.startswith("co_") or n == "deform_hda"
                              or n in ("Cloth_Cache", "Hair_Cache")),
]
_SHOT_STAGE_COLORS = {
    "LOAD": (0.42, 0.42, 0.52), "ANIM": (0.29, 0.47, 0.63),
    "COLLISION": (0.66, 0.48, 0.30), "CONSTRAINT": (0.36, 0.56, 0.40),
    "SOLVE": (0.55, 0.38, 0.60), "CACHEOUT": (0.55, 0.55, 0.33),
}


def flatten_shot_stages(geo) -> None:
    """Dissolve the shot stage subnets back to flat (idempotent rebuild)."""

    stage_names = []
    for stage, _predicate in _SHOT_STAGES:
        node = geo.node(stage)
        # A published stage HDA is an interface node, not an organizational
        # subnet.  extractAndDelete would destroy the HDA boundary.
        if node is not None and node.type().definition() is not None:
            continue
        stage_names.append(stage)
    flatten_stages(geo, stage_names)


def organize_shot_stages(geo) -> dict[str, Any]:
    """Collapse the shot's auto nodes into per-stage subnets (shared core)."""

    stages = list(_SHOT_STAGES)
    constraint = geo.node("CONSTRAINT")
    if constraint is not None and constraint.type().definition() is not None:
        # Keep the HDA and its explicit pre/post adapters visible at the shot
        # root.  Only the legacy config-rebuilt chain is wrapped in a subnet.
        stages = [item for item in stages if item[0] != "CONSTRAINT"]
    return organize_stages(geo, stages, _SHOT_STAGE_COLORS)


def clip_range(shot: ShotSimConfig, parent: str = "/obj") -> dict[str, Any]:
    """Read the animation fbx take's native frame range from ``anim_take``.

    The ``kinefx::fbxanimimport`` exposes the clip's native range as
    ``animationstartframe`` / ``animationendframe`` (and the times as
    ``animationstarttime`` / ``animationendtime``). :func:`set_shot_timeline`
    uses this as the base range when ``from_clip=True``.
    """

    hou = _require_hou()
    geo = _shot_geo(shot, parent)
    probe = geo.node("anim_take")
    if probe is None:
        raise ValueError("anim_take missing; run build_shot_setup first")

    info: dict[str, Any] = {"source_rate": None, "source_start": None,
                            "source_end": None}
    if probe.parm("animationstartframe"):
        info["source_start"] = int(round(probe.evalParm("animationstartframe")))
    if probe.parm("animationendframe"):
        info["source_end"] = int(round(probe.evalParm("animationendframe")))
    # native rate = frames / seconds, derived from the take's start frame/time
    if probe.parm("animationstarttime") and probe.parm("animationstartframe"):
        t = probe.evalParm("animationstarttime")
        f = probe.evalParm("animationstartframe")
        if t:
            info["source_rate"] = round(f / t, 3)
    return info


def set_shot_timeline(shot: ShotSimConfig, apply: bool = True,
                      from_clip: bool = False, parent: str = "/obj") -> dict[str, Any]:
    """Set the fps + playbar for the shot.

    Config is authoritative: ``frame_start``/``frame_end`` define the shot range
    and ``start_duration``/``end_duration`` pad it (pre-roll / post-roll). When
    ``from_clip`` is set, the fbx clip's native range (see :func:`clip_range`) is
    used as the base instead of the config frames — matching the studio's
    ``timeline_set`` button. ``apply`` writes ``hou.setFps`` + the global playbar.
    """

    hou = _require_hou()
    start, end = shot.frame_start, shot.frame_end
    fps = None
    if from_clip:
        info = clip_range(shot, parent)
        if info.get("source_start") is not None:
            start, end = int(info["source_start"]), int(info["source_end"])
        fps = info.get("source_rate")

    # Duration folder: pre-roll before start, post-roll after end.
    start -= int(shot.start_duration)
    end += int(shot.end_duration)

    if apply:
        if fps:
            hou.setFps(float(fps))
        hou.playbar.setFrameRange(start, end)
        hou.playbar.setPlaybackRange(start, end)
        hou.setFrame(start)
    return {"frame_start": start, "frame_end": end, "fps": fps, "applied": apply}
