"""
MH Body Match Reference
========================
MetaHuman body 스켈레톤의 조인트 트랜스폼(.translate / .jointOrient)을
레퍼런스로 로드된 캐릭터(예: Floyd)의 동일 이름 조인트 값으로 맞추는 모듈입니다.

두 스켈레톤의 parent 계층이 조인트별로 동일하다는 전제 하에, 레퍼런스 조인트의
로컬 .matrix(= translate/rotate/jointOrient/offsetParentMatrix 등이 모두 합성된
최종 로컬 변환)를 translate + jointOrient 로 분해하여 그대로 복사합니다.
(world-space snap 아님 — 단순 .translate/.jointOrient 값 복사도 아님. 일부
레퍼런스 조인트는 bind orientation 을 rotate 에 넣거나 offsetParentMatrix 로
위치를 표현하기 때문에 개별 attribute 복사로는 정확한 결과가 나오지 않음.)

대상 조인트 목록은 씬 전체 joint 가 아니라 body.dna 자체의 joint 목록으로 한정합니다
(PyDNA 로 dnaFilePath 를 읽어 reader.getJointName(i) 사용) — 페이셜/헤어 조인트는
이름이 레퍼런스와 우연히 일치해도 head.dna 소속이므로 자동으로 제외됩니다.

secondary(twist/corrective) 조인트는 mh_body_edit_mode.enter_edit_mode() 가 world 로
unparent 하기 때문에, 그 상태에서 레퍼런스의 로컬값을 그대로 복사하면 틀어집니다.
그래서 Pass A(primary) / Pass B(secondary) 로 나누어 restore_structure() 전후에 실행합니다.

사용 순서
---------
    import mh_body_edit_mode as mhem
    import mh_body_match_reference as mhmr

    mhem.enter_edit_mode(rl4_node="body_rl4Embedded")
    mhmr.match_joints_to_reference("Floyd", primary_only=True)     # Pass A

    mhem.restore_structure()
    mhmr.match_joints_to_reference("Floyd", secondary_only=True)   # Pass B

    mhmr.verify_world_match("Floyd")
    # 뷰포트에서 스켈레톤 검수

    mhem.bake_rotate_to_joint_orient(namespace="")
    mhem.export_dna_from_scene(output_path, input_dna_path, namespace="")
    mhem.reconnect_rl4()

    # 위 전체를 Pass A/B + 검수 출력까지 한 번에:
    mhmr.run_full_match("Floyd")

요구사항
--------
mh_body_edit_mode.py 와 동일 (Maya 2025 / Python 3.11 / PyDNA 9.4.7 / PyDNACalib2 3.2.4)
"""

import os
import sys
import math
import maya.cmds as cmds
import maya.api.OpenMaya as om2

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import mh_body_edit_mode as mhem


# ══════════════════════════════════════════════════════════════
#  PyDNA / DNA 경로 유틸
# ══════════════════════════════════════════════════════════════

def _dna_lib_paths():
    """PyDNA / PyDNACalib2 lib 경로 목록 (mhem.MH_LIB_ROOT 기준)."""
    return [
        mhem.MH_LIB_ROOT + "/PyDNA/9.4.7/platform-windows/.sanitizers-off/.json-0/" + mhem.MH_PY_VER + "/lib",
        mhem.MH_LIB_ROOT + "/PyDNACalib2/3.2.4/platform-windows/.sanitizers-off/" + mhem.MH_PY_VER + "/lib",
    ]


def _ensure_dna_modules():
    """PyDNA / PyDNACalib2 를 sys.path 에 등록하고 import 하여 반환."""
    for p in _dna_lib_paths():
        if p not in sys.path:
            sys.path.insert(0, p)
    import dna
    import dnacalib2
    return dna, dnacalib2


def get_body_joint_names(dna_path):
    """dna_path 의 전체 joint 이름 목록을 순서대로 반환합니다."""
    dna, dnacalib2 = _ensure_dna_modules()
    stream     = dna.FileStream(dna_path, dna.FileStream.AccessMode_Read, dna.FileStream.OpenMode_Binary)
    bin_reader = dna.BinaryStreamReader(stream, dna.DataLayer_All)
    bin_reader.read()
    reader     = dnacalib2.DNACalibDNAReader(bin_reader)
    return [reader.getJointName(i) for i in range(reader.getJointCount())]


def _get_dna_path(dna_path=None):
    """dna_path 미지정시 body_rl4Embedded.dnaFilePath 에서 추론."""
    if dna_path:
        return dna_path
    rl4 = mhem.DEFAULT_RL4_NODE
    if not cmds.objExists(rl4):
        raise RuntimeError("[MHMatch] {} 를 찾을 수 없고 dna_path 도 지정되지 않았습니다.".format(rl4))
    path = cmds.getAttr(rl4 + ".dnaFilePath") or ""
    if not path:
        raise RuntimeError("[MHMatch] {}.dnaFilePath 가 비어 있습니다. dna_path 를 직접 지정하세요.".format(rl4))
    return path


def _infer_output_path(input_path):
    """입력 dna 경로에서 _edit 접미사를 정규화하여 출력 경로를 추론 (body.dna -> body_edit.dna)."""
    base, ext = os.path.splitext(input_path)
    while base.endswith("_edit"):
        base = base[:-5]
    return base + "_edit" + ext


def _attr_writable(node, attr):
    """
    attr(예: translate) 또는 그 하위 채널(translateX/Y/Z 등) 중 하나라도
    locked 이거나 incoming connection 이 있으면 False.

    복합 attribute 자체만 확인하면 부족합니다 — 다른 rl4(예: body_rl4Embedded)가
    재연결된 상태에서 그 rl4 가 특정 축(child plug)만 개별적으로 구동하는 경우,
    복합 attribute 의 lock/connection 조회에는 걸리지 않아 setAttr 이 그대로
    RuntimeError 를 던지게 됩니다.
    """
    full = node + "." + attr
    if cmds.getAttr(full, lock=True):
        return False
    if cmds.listConnections(full, source=True, destination=False):
        return False
    for child in cmds.attributeQuery(attr, node=node, listChildren=True) or []:
        child_full = node + "." + child
        if cmds.getAttr(child_full, lock=True):
            return False
        if cmds.listConnections(child_full, source=True, destination=False):
            return False
    return True


def _decompose_local_transform(node):
    """
    node 의 로컬 .matrix (parent 기준) 를 translate + jointOrient(XYZ euler) 로
    분해하여 반환합니다.

    .matrix 는 translate/rotate(+rotateOrder)/jointOrient 뿐 아니라
    offsetParentMatrix / rotateAxis 등 로컬 변환에 기여하는 모든 요소가 이미
    합성된 최종 로컬 매트릭스입니다. 일부 레퍼런스 스켈레톤(예: Floyd)은
    - bind orientation 을 jointOrient 대신 rotate 에 넣어두거나 (예: root)
    - offsetParentMatrix 로 실제 본 길이/위치를 표현하기도 하므로
    (예: spine_01 이후 체인), 개별 attribute 를 따로 읽는 대신 .matrix 를
    통째로 분해하는 것이 유일하게 안전한 방법입니다.

    Returns
    -------
    (translate_xyz, jointOrient_xyz) : 둘 다 (x, y, z) tuple, 각도는 degree.
    """
    # worldMatrix = matrix * offsetParentMatrix * parentMatrix (row-vector 컨벤션) 이므로
    # 실제 DAG parent 기준 로컬 매트릭스는 matrix * offsetParentMatrix 이다.
    # (offsetParentMatrix 는 .matrix 자체에는 포함되지 않는, "가상 부모"로 삽입되는
    # 별도 매트릭스이며 rig 에서 본 길이/위치를 표현하는 데 흔히 쓰인다.)
    mat = om2.MMatrix(cmds.getAttr(node + ".matrix"))
    opm = om2.MMatrix(cmds.getAttr(node + ".offsetParentMatrix"))
    tm  = om2.MTransformationMatrix(mat * opm)

    t = tm.translation(om2.MSpace.kTransform)

    rot = tm.rotation(asQuaternion=False)
    rot.reorderIt(0)  # jointOrient 은 항상 XYZ

    return (
        (t.x, t.y, t.z),
        (math.degrees(rot.x), math.degrees(rot.y), math.degrees(rot.z)),
    )


# ══════════════════════════════════════════════════════════════
#  Core API
# ══════════════════════════════════════════════════════════════

def match_joints_to_reference(
    reference_namespace="Floyd",
    dna_path=None,
    primary_only=False,
    secondary_only=False,
    exclude_snap=True,
):
    """
    body.dna 의 joint 목록을 기준으로, reference_namespace 의 동일 이름 조인트에서
    .translate / .jointOrient 를 로컬 값 그대로 복사합니다.

    Parameters
    ----------
    reference_namespace : str   레퍼런스 캐릭터 네임스페이스 (예: "Floyd")
    dna_path             : str | None   None 이면 body_rl4Embedded.dnaFilePath 사용
    primary_only         : bool  True 면 mhem._is_secondary() 가 False 인 조인트만 처리
    secondary_only       : bool  True 면 secondary 조인트만 처리
    exclude_snap         : bool  True 면 mhem._is_snap() 인 조인트(correctiveRoot/half)의
                                  translate 는 0 으로 강제 고정(parent 위치에 정확히 스냅
                                  하는 리그 규칙 유지)하되, jointOrient 는 여전히 레퍼런스
                                  값으로 갱신함 (자식 조인트들의 배치 축이 되기 때문)

    Returns
    -------
    dict : {"updated": [...], "skipped_missing_scene": [...],
            "skipped_missing_ref": [...], "skipped_locked": [...]}
    """
    ns   = reference_namespace.rstrip(":") + ":"
    path = _get_dna_path(dna_path)
    joint_names = get_body_joint_names(path)

    updated                = []
    skipped_missing_scene  = []
    skipped_missing_ref    = []
    skipped_locked         = []

    cmds.undoInfo(openChunk=True, chunkName="MHMatch_toReference")
    try:
        for name in joint_names:
            is_sec  = mhem._is_secondary(name)
            is_snap = is_sec and mhem._is_snap(name)
            if primary_only and is_sec:
                continue
            if secondary_only and not is_sec:
                continue

            if not cmds.objExists(name):
                skipped_missing_scene.append(name)
                continue
            ref_name = ns + name
            if not cmds.objExists(ref_name):
                skipped_missing_ref.append(name)
                continue

            if not (_attr_writable(name, "translate") and _attr_writable(name, "jointOrient")):
                skipped_locked.append(name)
                continue

            t, jo = _decompose_local_transform(ref_name)
            if exclude_snap and is_snap:
                # correctiveRoot/half 는 항상 parent 위치에 정확히 겹쳐야 하는 리그 규칙
                # (restore_structure() 가 이미 0 으로 스냅한 translate 를 유지) — 다만
                # 방향(jointOrient)은 그대로 두면 자식(bck/fwd/in/out 등)들이 잘못된 축
                # 기준으로 배치되므로, jointOrient 는 레퍼런스 값으로 갱신한다.
                cmds.setAttr(name + ".translate", 0.0, 0.0, 0.0, type="double3")
            else:
                cmds.setAttr(name + ".translate", t[0], t[1], t[2], type="double3")
            cmds.setAttr(name + ".jointOrient", jo[0], jo[1], jo[2], type="double3")
            updated.append(name)
    finally:
        cmds.undoInfo(closeChunk=True)

    print("[MHMatch] reference={} primary_only={} secondary_only={}".format(
        ns, primary_only, secondary_only))
    print("[MHMatch]   updated              : {}".format(len(updated)))
    print("[MHMatch]   skipped (no ref)     : {}".format(len(skipped_missing_ref)))
    print("[MHMatch]   skipped (no scene)   : {}".format(len(skipped_missing_scene)))
    print("[MHMatch]   skipped (locked/conn): {}".format(len(skipped_locked)))
    if skipped_missing_ref:
        print("[MHMatch]   -- missing in reference ({}):".format(len(skipped_missing_ref)))
        for n in skipped_missing_ref[:20]:
            print("       -", n)
    if skipped_locked:
        print("[MHMatch]   -- locked/connected ({}):".format(len(skipped_locked)))
        for n in skipped_locked[:20]:
            print("       -", n)

    return {
        "updated": updated,
        "skipped_missing_scene": skipped_missing_scene,
        "skipped_missing_ref": skipped_missing_ref,
        "skipped_locked": skipped_locked,
    }


def verify_world_match(reference_namespace="Floyd", joints=None, tolerance=0.01):
    """
    대표 조인트들의 world position 을 MH vs reference 로 비교합니다.
    로컬 복사만으로 world 가 맞는지(=계층 가정이 맞는지) 확인하는 용도입니다.

    Returns
    -------
    list[dict] : [{"joint": str, "diff": float, "ok": bool}, ...]
    """
    ns = reference_namespace.rstrip(":") + ":"
    if joints is None:
        joints = [
            "root", "pelvis", "spine_05", "clavicle_l", "upperarm_l", "lowerarm_l",
            "hand_l", "thigh_l", "calf_l", "foot_l", "neck_02", "head",
        ]

    results = []
    for j in joints:
        ref = ns + j
        if not (cmds.objExists(j) and cmds.objExists(ref)):
            results.append({"joint": j, "diff": None, "ok": False})
            continue
        p1 = cmds.xform(j,   q=True, ws=True, t=True)
        p2 = cmds.xform(ref, q=True, ws=True, t=True)
        diff = sum((a - b) ** 2 for a, b in zip(p1, p2)) ** 0.5
        results.append({"joint": j, "diff": diff, "ok": diff <= tolerance})

    for r in results:
        status = "OK" if r["ok"] else "!!"
        print("[MHMatch] verify {:<3} {:<16} diff={}".format(
            status, r["joint"], r["diff"]))
    return results


def summarize_match(reference_namespace="Floyd", dna_path=None, tolerance=0.05):
    """
    dna_path 의 joint 목록 전체를 reference_namespace 와 world position 기준으로
    비교하고, 결과를 사람이 읽기 좋게 분류하여 출력/반환합니다.

    mhem._is_secondary() 인 조인트는 rl4 가 재연결된 뒤에는 DNA 의 joint-behavior
    (RBF corrective) 로 라이브 구동되어 static 값과 달라지는 것이 정상이므로,
    "expected_secondary" 로 별도 분류하여 실제 문제(unexpected_primary)와
    구분합니다.

    Parameters
    ----------
    reference_namespace : str
    dna_path             : str | None   None 이면 body_rl4Embedded.dnaFilePath 사용
    tolerance             : float  world position 허용 오차 (cm)

    Returns
    -------
    dict: {"total": int, "ok": [...], "unexpected_primary": [(name, diff), ...],
           "expected_secondary": [(name, diff), ...], "missing": [...]}
    """
    ns   = reference_namespace.rstrip(":") + ":"
    path = _get_dna_path(dna_path)
    joint_names = get_body_joint_names(path)

    ok                 = []
    unexpected_primary = []
    expected_secondary = []
    missing            = []

    for name in joint_names:
        ref = ns + name
        if not (cmds.objExists(name) and cmds.objExists(ref)):
            missing.append(name)
            continue
        p1 = cmds.xform(name, q=True, ws=True, t=True)
        p2 = cmds.xform(ref,  q=True, ws=True, t=True)
        diff = sum((a - b) ** 2 for a, b in zip(p1, p2)) ** 0.5
        if diff <= tolerance:
            ok.append(name)
        elif mhem._is_secondary(name):
            expected_secondary.append((name, diff))
        else:
            unexpected_primary.append((name, diff))

    print("[MHMatch] summarize_match: reference={} total={} ok={} "
          "expected_secondary(rl4 live 구동, 정상)={} unexpected_primary(문제)={} missing={}".format(
              ns, len(joint_names), len(ok), len(expected_secondary),
              len(unexpected_primary), len(missing)))
    if unexpected_primary:
        print("[MHMatch]   UNEXPECTED PRIMARY MISMATCH ({}):".format(len(unexpected_primary)))
        for name, diff in sorted(unexpected_primary, key=lambda x: -x[1])[:30]:
            print("     - {:<28} diff={:.3f}cm".format(name, diff))
    if missing:
        print("[MHMatch]   missing (씬/레퍼런스에 없음, {}): {}".format(
            len(missing), ", ".join(missing[:20])))
    if expected_secondary:
        worst = sorted(expected_secondary, key=lambda x: -x[1])[:5]
        print("[MHMatch]   expected_secondary sample (상위 5, 참고용):")
        for name, diff in worst:
            print("     - {:<28} diff={:.3f}cm".format(name, diff))

    return {
        "total": len(joint_names),
        "ok": ok,
        "unexpected_primary": unexpected_primary,
        "expected_secondary": expected_secondary,
        "missing": missing,
    }


def run_full_match(
    reference_namespace="Floyd",
    output_dna_path=None,
    input_dna_path=None,
    rl4_node=None,
):
    """
    enter_edit_mode -> Pass A(primary) -> restore_structure -> Pass B(secondary) 까지
    한 번에 실행하는 편의 함수입니다. DNA export / reconnect 는 포함하지 않습니다 —
    뷰포트 검수 없이 자동으로 DNA 를 덮어쓰지 않기 위해, 검수 후 별도로
    mhem.export_dna_from_scene() / mhem.reconnect_rl4() 를 호출하세요.
    """
    rl4_node       = rl4_node or mhem.DEFAULT_RL4_NODE
    input_dna_path = _get_dna_path(input_dna_path)
    output_dna_path = output_dna_path or _infer_output_path(input_dna_path)

    mhem.enter_edit_mode(rl4_node=rl4_node)
    match_joints_to_reference(reference_namespace, input_dna_path, primary_only=True)

    mhem.restore_structure()
    match_joints_to_reference(reference_namespace, input_dna_path, secondary_only=True)

    verify_world_match(reference_namespace)

    print("[MHMatch] >>> Pass A/B 완료. 뷰포트에서 스켈레톤 검수 후 아래를 실행하세요: <<<")
    print("[MHMatch]     mhem.bake_rotate_to_joint_orient(namespace='')")
    print("[MHMatch]     mhem.export_dna_from_scene(r'{}', r'{}', namespace='')".format(
        output_dna_path, input_dna_path))
    print("[MHMatch]     mhem.reconnect_rl4()")
