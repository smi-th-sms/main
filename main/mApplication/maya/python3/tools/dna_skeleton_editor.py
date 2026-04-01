"""
DNA Skeleton Editor for MetaHuman
----------------------------------
MetaHumanForMaya 내장 PyDNA / PyDNACalib2 라이브러리를 이용해
body.dna 파일을 읽고, 스켈레톤 neutral joint transform을 수정한 뒤
새 DNA 파일로 export합니다.

사용법:
    Maya Script Editor (Python) 에 붙여넣고 실행하거나
    import dna_skeleton_editor 로 임포트 후 사용

요구사항:
    MetaHumanForMaya 1.2.x 이상이 modules 에 설치되어 있어야 합니다.
"""

import os
import sys


# ─────────────────────────────────────────────
#  1.  PyDNA / PyDNACalib2 경로를 sys.path 에 등록
# ─────────────────────────────────────────────
MH_LIB = "C:/Users/smi_th/Documents/maya/modules/MetaHumanForMaya/lib"
PY_VER = "python-3.11"   # Maya 2025 기준. 2024 이하라면 "python-3.10"

_LIB_PATHS = [
    MH_LIB + "/PyDNA/9.4.7/platform-windows/.sanitizers-off/.json-0/" + PY_VER + "/lib",
    MH_LIB + "/PyDNACalib2/3.2.4/platform-windows/.sanitizers-off/" + PY_VER + "/lib",
]
for _p in _LIB_PATHS:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import dna
import dnacalib2


# ─────────────────────────────────────────────
#  2.  DNA 읽기 헬퍼
# ─────────────────────────────────────────────
def read_dna(dna_path):
    """DNA 파일을 읽어 (DNACalibDNAReader, stream) 를 반환합니다.

    Notes
    -----
    stream 은 reader 가 살아있는 동안 GC 되지 않도록 반드시 참조를 유지해야 합니다.
    반환값을 reader, stream = read_dna(...) 형태로 받아 두 변수 모두 보관하세요.
    """
    stream     = dna.FileStream(dna_path, dna.FileStream.AccessMode_Read, dna.FileStream.OpenMode_Binary)
    bin_reader = dna.BinaryStreamReader(stream, dna.DataLayer_All)
    bin_reader.read()
    reader = dnacalib2.DNACalibDNAReader(bin_reader)
    # bin_reader 도 stream 과 같이 살아있어야 하므로 stream 튜플에 포함
    return reader, (stream, bin_reader)


# ─────────────────────────────────────────────
#  3.  스켈레톤 정보 출력
# ─────────────────────────────────────────────
def print_joints(reader, lod=0):
    """joint 이름과 neutral translation/rotation을 출력합니다.

    getNeutralJointTranslation / getNeutralJointRotation 은
    [x, y, z] 리스트를 반환합니다.
    """
    count   = reader.getJointCount()
    indices = list(reader.getJointIndicesForLOD(lod))
    print("[DNA] Joint count: {}  /  LOD{} joint count: {}".format(count, lod, len(indices)))
    print("{:>5}  {:<45}  {:>10} {:>10} {:>10}  {:>8} {:>8} {:>8}".format(
        "idx","name","tx","ty","tz","rx","ry","rz"))
    print("-" * 115)
    for idx in indices:
        name = reader.getJointName(idx)
        t    = reader.getNeutralJointTranslation(idx)   # [x, y, z]
        r    = reader.getNeutralJointRotation(idx)
        print("{:>5}  {:<45}  {:>10.4f} {:>10.4f} {:>10.4f}  {:>8.3f} {:>8.3f} {:>8.3f}".format(
            idx, name, t[0], t[1], t[2], r[0], r[1], r[2]))


def get_joint_index_by_name(reader, joint_name):
    """이름으로 joint index를 반환합니다. 없으면 None."""
    count = reader.getJointCount()
    for i in range(count):
        if reader.getJointName(i) == joint_name:
            return i
    return None


# ─────────────────────────────────────────────
#  4.  Neutral Joint Translation 수정
# ─────────────────────────────────────────────
def set_neutral_joint_translations(reader, joint_overrides):
    """
    joint_overrides: dict  { joint_name: (tx, ty, tz), ... }
    현재 translation 배열을 복사한 뒤 지정 joint만 수정하고 Command를 실행합니다.
    """
    count = reader.getJointCount()

    # 현재 전체 translation 배열 복사
    xs = list(reader.getNeutralJointTranslationXs())
    ys = list(reader.getNeutralJointTranslationYs())
    zs = list(reader.getNeutralJointTranslationZs())

    for name, (tx, ty, tz) in joint_overrides.items():
        idx = get_joint_index_by_name(reader, name)
        if idx is None:
            print(f"[WARN] Joint '{name}' not found – skipped")
            continue
        print(f"[EDIT] '{name}' [{idx}]  ({xs[idx]:.4f}, {ys[idx]:.4f}, {zs[idx]:.4f})"
              f" → ({tx:.4f}, {ty:.4f}, {tz:.4f})")
        xs[idx] = tx
        ys[idx] = ty
        zs[idx] = tz

    cmd = dnacalib2.SetNeutralJointTranslationsCommand()
    cmd.setTranslations(xs, ys, zs)
    cmd.run(reader)


# ─────────────────────────────────────────────
#  5.  Neutral Joint Rotation 수정
# ─────────────────────────────────────────────
def set_neutral_joint_rotations(reader, joint_overrides):
    """
    joint_overrides: dict  { joint_name: (rx, ry, rz), ... }
    """
    xs = list(reader.getNeutralJointRotationXs())
    ys = list(reader.getNeutralJointRotationYs())
    zs = list(reader.getNeutralJointRotationZs())

    for name, (rx, ry, rz) in joint_overrides.items():
        idx = get_joint_index_by_name(reader, name)
        if idx is None:
            print(f"[WARN] Joint '{name}' not found – skipped")
            continue
        print(f"[EDIT] '{name}' [{idx}]  rot({xs[idx]:.4f}, {ys[idx]:.4f}, {zs[idx]:.4f})"
              f" → ({rx:.4f}, {ry:.4f}, {rz:.4f})")
        xs[idx] = rx
        ys[idx] = ry
        zs[idx] = rz

    cmd = dnacalib2.SetNeutralJointRotationsCommand()
    cmd.setRotations(xs, ys, zs)
    cmd.run(reader)


# ─────────────────────────────────────────────
#  6.  DNA 저장
# ─────────────────────────────────────────────
def write_dna(reader, output_path):
    """수정된 reader 내용을 output_path 에 저장합니다."""
    stream = dna.FileStream(
        output_path,
        dna.FileStream.AccessMode_Write,
        dna.FileStream.OpenMode_Binary,
    )
    writer = dna.BinaryStreamWriter(stream)
    writer.setFrom(reader)
    writer.write()
    print("[DNA] Saved -> {}  ({} bytes)".format(output_path, os.path.getsize(output_path)))


# ─────────────────────────────────────────────
#  7.  Maya 씬의 joint transform 을 DNA 에 반영하는 유틸
# ─────────────────────────────────────────────
def apply_maya_joints_to_dna(reader, joint_name_map=None):
    """
    Maya 씬에 열려 있는 MetaHuman rig 의 joint translate 값을 읽어
    DNA neutral joint translation 으로 반영합니다.

    joint_name_map: {maya_joint_name: dna_joint_name} (None 이면 이름 동일 가정)

    Returns: dict { dna_joint_name: (tx, ty, tz) }  (수정 내역 확인용)
    """
    try:
        import maya.cmds as cmds
    except ImportError:
        raise RuntimeError("Maya 환경에서만 사용 가능합니다.")

    count = reader.getJointCount()
    overrides = {}

    for i in range(count):
        dna_name = reader.getJointName(i)
        maya_name = dna_name
        if joint_name_map:
            maya_name = joint_name_map.get(dna_name, dna_name)

        if not cmds.objExists(maya_name):
            continue

        tx, ty, tz = cmds.getAttr(f"{maya_name}.translate")[0]
        overrides[dna_name] = (tx, ty, tz)

    set_neutral_joint_translations(reader, overrides)
    return overrides


# ─────────────────────────────────────────────
#  8.  원-스텝 편의 함수
# ─────────────────────────────────────────────
def edit_and_export_dna(
    input_path,
    output_path,
    translation_overrides=None,
    rotation_overrides=None,
    from_maya_scene=False,
):
    """
    DNA 읽기 → 수정 → 저장 원스텝 실행.

    Parameters
    ----------
    input_path          : str   원본 .dna 경로
    output_path         : str   저장할 .dna 경로
    translation_overrides : dict  { joint_name: (tx, ty, tz) }
    rotation_overrides    : dict  { joint_name: (rx, ry, rz) }
    from_maya_scene       : bool  True 이면 Maya 씬 joint 값으로 덮어씀

    Example
    -------
    edit_and_export_dna(
        input_path  = r"C:\\...\\body.dna",
        output_path = r"C:\\...\\body_modified.dna",
        translation_overrides = {
            "spine_01": (0.0, 98.5, 0.0),
            "spine_02": (0.0, 110.0, 0.0),
        },
    )
    """
    print("[DNA] Reading: {}".format(input_path))
    reader, stream = read_dna(input_path)

    if from_maya_scene:
        apply_maya_joints_to_dna(reader)

    if translation_overrides:
        set_neutral_joint_translations(reader, translation_overrides)

    if rotation_overrides:
        set_neutral_joint_rotations(reader, rotation_overrides)

    write_dna(reader, output_path)
    return reader


# ─────────────────────────────────────────────
#  실행 예시 (Script Editor 에서 직접 실행할 때)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    DNA_PATH = "C:/Users/smi_th/Documents/Megascans Library/Downloaded/DHI/aaMH/body.dna"
    OUT_PATH = "C:/Users/smi_th/Documents/Megascans Library/Downloaded/DHI/aaMH/body_modified.dna"

    # ── 1) joint 목록 확인 ──────────────────────────
    reader, stream = read_dna(DNA_PATH)
    print_joints(reader, lod=0)

    # ── 2) 원하는 joint translation 수정 후 export ──
    # (joint 이름은 위 print_joints 출력 참조)
    # getNeutralJointTranslation / Rotation 은 [x, y, z] 리스트 반환
    edit_and_export_dna(
        input_path=DNA_PATH,
        output_path=OUT_PATH,
        translation_overrides={
            # "joint_name": (tx, ty, tz),
            # 예: "spine_01": (7.0, 0.06, 0.0),
        },
        rotation_overrides={
            # "joint_name": (rx, ry, rz),
        },
    )
