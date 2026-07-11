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

from typing import Any

from .asset_builder import PUSH_APART_VEX, _child, _require_hou, build_vellum_chain
from .schema import AssetSetupConfig, ShotSimConfig


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
    @P *= inv;
    if (haspointattrib(0, "N")) @N = normalize(@N * matrix3(inv));
    if (haspointattrib(0, "v")) @v *= matrix3(inv);
}
"""

# fbx_material_name -> primitive group (Out/face_shading_group) for UE materials.
FACE_SHADING_VEX = """if (s@fbx_material_name != "")
    setprimgroup(0, s@fbx_material_name, @primnum, 1);
"""


# Copy a pose (P + transform) from in1 onto in0's joints by name. Used to
# retarget the take onto the clean REST_SKEL structure so the driving skeleton
# and the T-pose share topology (required by kinefx::skeletonblend) and the
# take's non-joint FBX-graph nodes are dropped.
POSE_COPY_VEX = """int i = findattribval(1, "point", "name", s@name);
if (i >= 0) {
    @P = point(1, "P", i);
    3@transform = matrix3(point(1, "transform", i));
}
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
def load_asset_caches(shot: ShotSimConfig, parent: str = "/obj") -> dict[str, Any]:
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

    The vellum constraint setup is handled separately (object_merge in
    :func:`build_shot_solve`), not here.

    Missing cache paths surface as warnings (an asset without hair has none).
    """

    geo = _shot_geo(shot, parent)
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
    loaded: list[dict[str, Any]] = []
    warnings: list[str] = []
    for node_name, out_name, path in specs:
        if not path:
            warnings.append(f"no cache path for {out_name}; skipped")
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
    return {"loaded": loaded, "warnings": warnings}


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

    # Retarget the take onto the CLEAN REST_SKEL structure: copy the take's pose
    # (P + transform) onto REST_SKEL's joints by name. This drops the take's ~282
    # non-joint FBX-graph nodes (which otherwise sit at the raw world offset and
    # blow up the bbox / blend) and gives a valid skeleton that matches the T-pose
    # topology — required for the skeletonblend.
    aclean = _child(geo, "anim_clean", "attribwrangle")
    aclean.parm("class").set(2)  # points
    aclean.parm("snippet").set(POSE_COPY_VEX)
    aclean.setInput(0, tpose, 0)   # REST_SKEL structure (924 joints)
    aclean.setInput(1, anim, 0)    # take pose

    # T-pose base with the authored offset (studio Tpos_offset_transform1).
    tofs = _child(geo, "anim_tpose_ofs", "xform")
    tofs.parmTuple("t").set(tuple(v * tp for v in fbx.t_pos_offset_translate))
    tofs.parmTuple("r").set(tuple(v * tp for v in fbx.t_pos_offset_rotate))
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
def build_shot_collision(shot: ShotSimConfig, parent: str = "/obj") -> dict[str, Any]:
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
    coll = geo.node("REST_COLLISION")
    corr = geo.node("REST_CORRECTIVE")
    anim_corr = geo.node("ANIM_CORRECTIVE")
    missing = [n for n, x in (("REST_COLLISION", coll), ("REST_CORRECTIVE", corr),
                              ("ANIM_CORRECTIVE", anim_corr)) if x is None]
    if missing:
        raise ValueError(f"missing {missing}; run load_asset_caches + build_shot_deform first")

    sp = shot.sim_params
    cdef = _child(geo, "coll_deform", "pointdeform")
    cdef.setInput(0, coll, 0)         # rest collision to deform
    cdef.setInput(1, corr, 0)         # rest cage
    cdef.setInput(2, anim_corr, 0)    # animated cage
    upstream = cdef

    if sp.get("push_apart", True):
        nrm = _child(geo, "sim_col_normal", "normal")
        nrm.parm("type").set(0)       # point normals for @N
        nrm.setInput(0, cdef, 0)
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
    return {"coll_deform": cdef.path(), "out_sim_collision": out.path(),
            "push_apart": sp.get("push_apart", True)}


# ---------------------------------------------------------------------------
# Stage 3.5a — instantiate the per-part constraint chain (deform upstream)
# ---------------------------------------------------------------------------
def build_shot_constraint(shot: ShotSimConfig, asset: AssetSetupConfig,
                          parent: str = "/obj") -> dict[str, Any]:
    """Stage 3.5a — instantiate the asset constraint chain WITH the animation.

    Under the confirmed HDA-instantiation model the asset's constraint setup is
    re-built per shot with the shot's animation, and the deform sits UPSTREAM of
    the constraints (:func:`asset_builder.build_vellum_chain`). Each part's rest
    proxy is isolated from the loaded rest caches (``REST_PROXY`` for cloth,
    ``REST_HAIR`` for hair) by its ``proxy_path``. CLOTH parts are pointDeformed
    to the animated pose by the shared body cage (REST_CORRECTIVE ->
    ANIM_CORRECTIVE) with a ``vellumrestblend`` restoring rest lengths; HAIR parts
    instead ride the animated HEAD joint rigidly (head-follow, REST_SKEL ->
    ANIM_SKEL). The per-part parameters come from the ASSET config; the shot only
    supplies the animation.

    Produces the packed ``OUT_CONSTRAINT`` consumed by :func:`build_shot_solve`.
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
            out0 (Vellum Geometry, animated) -> shot_constraint_edit --┐
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

    solver = _child(geo, "vellum_solve", "vellumsolver")
    solver.setInput(0, edit, 0)         # Vellum Geometry (animated)
    solver.setInput(1, unpack, 1)       # Constraint Geometry (rest lengths intact)
    solver.setInput(2, sim_col, 0)      # Collision Geometry
    # start the sim at the pre-roll start so the cloth settles before frame_start
    if solver.parm("startframe"):
        solver.parm("startframe").deleteAllKeyframes()
        solver.parm("startframe").set(shot.frame_start - shot.start_duration)
    if sp.get("substeps") is not None and solver.parm("substeps"):
        solver.parm("substeps").set(int(sp["substeps"]))
    thickness = sp.get("collision_thickness", sp.get("thickness"))
    if thickness is not None and solver.parm("thickness"):
        solver.parm("thickness").set(float(thickness))
    if sp.get("collision_iterations") is not None and solver.parm("collisionsiter"):
        solver.parm("collisionsiter").set(int(sp["collision_iterations"]))

    post = _child(geo, "vellum_post", "vellumpostprocess")
    post.setInput(0, solver, 0)
    out = _child(geo, "OUT_SIM", "null")
    out.setInput(0, post, 0)
    out.setDisplayFlag(True)
    geo.layoutChildren()
    return {"constraint_unpack": unpack.path(), "constraint_edit": edit.path(),
            "vellum_solve": solver.path(), "out_sim": out.path()}


# ---------------------------------------------------------------------------
# Stage 3.6 — sim filecache
# ---------------------------------------------------------------------------
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
    src = geo.node("OUT_SIM")
    if src is None:
        raise ValueError("OUT_SIM missing; run build_shot_solve first")
    if not shot.sim_cache_path:
        return {"skipped": "no sim_cache_path resolved"}

    fc = _child(geo, "sim_filecache", "filecache::2.0")
    fc.parm("filemethod").set(1)         # explicit filename
    fc.parm("file").set(shot.sim_cache_path)
    fc.parm("trange").set(1)             # frame range
    if fc.parm("f1"):
        fc.parm("f1").deleteAllKeyframes(); fc.parm("f1").set(shot.frame_start)
        fc.parm("f2").deleteAllKeyframes(); fc.parm("f2").set(shot.frame_end)
    fc.setInput(0, src, 0)

    written = False
    if execute and shot.sim_filecache and fc.parm("execute"):
        fc.parm("execute").pressButton()
        written = True
    geo.layoutChildren()
    return {"sim_filecache": fc.path(), "file": shot.sim_cache_path,
            "frame_range": [shot.frame_start, shot.frame_end],
            "gated_by_sim_filecache": shot.sim_filecache, "written": written}


# ---------------------------------------------------------------------------
# Stage 4 — Cache Out (detail-attach + joint-inverse + UE transform -> alembic)
# ---------------------------------------------------------------------------
def build_shot_cacheout(shot: ShotSimConfig, asset: AssetSetupConfig,
                        parent: str = "/obj", detail_attach: bool = True,
                        execute: bool = False) -> dict[str, Any]:
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
    result: dict[str, Any] = {"cloth": None, "hair": None, "warnings": []}

    def sim_part(part):
        b = _child(geo, f"co_{part.name}_sim", "blast")
        b.parm("grouptype").set(4)  # primitives
        b.parm("group").set(f"@name={part.name}")
        b.parm("negate").set(1)     # keep only this part
        b.setInput(0, sim, 0)
        return b

    cloth_outs, hair_outs = [], []
    for part in asset.proxy_parts:
        sp = sim_part(part)
        if part.cloth:
            if detail_attach and corr is not None and rproxy is not None and part.geo_path:
                hires = _child(geo, f"co_{part.name}_hires", "blast")
                hires.parm("group").set(part.geo_group())  # original hi-res by geo_path
                hires.parm("negate").set(1)
                hires.setInput(0, corr, 0)
                rp = _child(geo, f"co_{part.name}_rproxy", "blast")
                rp.parm("group").set(f"@proxy_path={part.proxy_path or part.name}")
                rp.parm("negate").set(1)
                rp.setInput(0, rproxy, 0)
                pd = _child(geo, f"co_{part.name}_deform", "pointdeform")
                pd.setInput(0, hires, 0)   # rest hi-res garment
                pd.setInput(1, rp, 0)      # rest proxy cage
                pd.setInput(2, sp, 0)      # sim proxy cage
                cloth_outs.append(pd)
            else:
                cloth_outs.append(sp)
        else:
            hair_outs.append(sp)

    # --- cloth branch: pelvis-inverse -> face shading -> UE transform ---
    if cloth_outs:
        cm = _child(geo, "co_cloth_merge", "merge")
        for i, o in enumerate(cloth_outs):
            cm.setInput(i, o, 0)
        pinv = _child(geo, "co_cloth_pelvis_inverse", "attribwrangle")
        pinv.parm("class").set(2)  # points
        pinv.parm("snippet").set(JOINT_INV_VEX.replace("__JOINT__", co.cloth_attach_joint))
        pinv.setInput(0, cm, 0)
        pinv.setInput(1, skel, 0)
        fsg = _child(geo, "co_face_shading", "attribwrangle")
        fsg.parm("class").set(1)  # primitives
        fsg.parm("snippet").set(FACE_SHADING_VEX)
        fsg.setInput(0, pinv, 0)
        ue = _child(geo, "co_cloth_ue", "xform")
        ue.parm("scale").set(co.ue_scale)
        ue.parmTuple("r").set(co.ue_rotate)
        ue.setInput(0, fsg, 0)
        out_cloth = _child(geo, "OUT_CLOTH", "null")
        out_cloth.setInput(0, ue, 0)
        out_cloth.setDisplayFlag(True)
        rop = _child(geo, "Cloth_Cache", "rop_alembic")
        if shot.cloth_abc_path:
            rop.parm("filename").set(shot.cloth_abc_path)
        rop.parm("trange").set(1)
        rop.parm("f1").deleteAllKeyframes(); rop.parm("f1").set(shot.frame_start)
        rop.parm("f2").deleteAllKeyframes(); rop.parm("f2").set(shot.frame_end)
        rop.setInput(0, out_cloth, 0)
        if execute and co.export_cloth and rop.parm("execute"):
            rop.parm("execute").pressButton()
        result["cloth"] = {"out": out_cloth.path(), "rop": rop.path(),
                           "file": shot.cloth_abc_path}

    # --- hair branch: head-inverse -> UE transform ---
    if hair_outs:
        hm = _child(geo, "co_hair_merge", "merge")
        for i, o in enumerate(hair_outs):
            hm.setInput(i, o, 0)
        head = co.hair_attach_chain[0] if co.hair_attach_chain else "head"
        hinv = _child(geo, "co_hair_head_inverse", "attribwrangle")
        hinv.parm("class").set(2)  # points
        hinv.parm("snippet").set(JOINT_INV_VEX.replace("__JOINT__", head))
        hinv.setInput(0, hm, 0)
        hinv.setInput(1, skel, 0)
        ueh = _child(geo, "co_hair_ue", "xform")
        ueh.parm("scale").set(co.ue_scale)
        ueh.parmTuple("r").set(co.ue_rotate)
        ueh.setInput(0, hinv, 0)
        out_hair = _child(geo, "OUT_HAIR", "null")
        out_hair.setInput(0, ueh, 0)
        roph = _child(geo, "Hair_Cache", "rop_alembic")
        if shot.hair_abc_path:
            roph.parm("filename").set(shot.hair_abc_path)
        roph.parm("trange").set(1)
        roph.parm("f1").deleteAllKeyframes(); roph.parm("f1").set(shot.frame_start)
        roph.parm("f2").deleteAllKeyframes(); roph.parm("f2").set(shot.frame_end)
        roph.setInput(0, out_hair, 0)
        if execute and co.export_hair and roph.parm("execute"):
            roph.parm("execute").pressButton()
        result["hair"] = {"out": out_hair.path(), "rop": roph.path(),
                          "file": shot.hair_abc_path}

    geo.layoutChildren()
    return result


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
