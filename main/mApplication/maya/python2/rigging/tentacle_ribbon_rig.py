# -*- coding: utf-8 -*-
"""============================================================================
촉수(Tentacle) Ribbon Auto-Rig

tentacle_rig_proto.ma(실제 프로덕션 리그)를 분석해서 그 구조를 기반으로 새로
작성하는 모듈. 기존 tentacle_autorig.py(motionPath+curve 기반)와는 무관한
별도 아키텍처 -- NURBS 리본 서피스 + follicle 기반이라 up-vector 기반 회전이
없어서 플립 문제가 구조적으로 없다.

1단계(베이스):
    1. mesh의 실제 vertex 중심선을 따라가는 center curve 생성
    2. 그 curve를 path로 삼아 얇은 리본 NURBS 서피스를 extrude
    3. 서피스에서 curveFromSurfaceIso로 curve를 다시 추출(라이브 -- 서피스가
       나중에 변형되면 같이 따라감)
    4. 그 curve에 restCurveLength 커스텀 attribute로 rest 길이를 저장
       (참조 리그와 동일 -- 나중에 Stretch 비율 계산에 씀)

2단계(IK): 리본 서피스를 따라 IK 컨트롤 N개를 배치하고, 각 컨트롤이 1:1
    parentConstraint로 구동하는 NurbsBind joint로 리본 서피스를 스킨 바인드한다
    (참조 리그의 L_IK_tentacle_XXX_CON / L_NurbsBind_tentacle_XXX_JNT 구조).
    마지막 IK 컨트롤에 Stretch(0~10) attribute를 추가한다(참조 리그와 동일한
    관례 -- 3단계의 출력 지점 재분배 방식을 여기서 제어).

3단계(출력): curve 위 M개 지점을 motionPath(position만)로 라이브 추적 ->
    closestPointOnSurface로 그 지점에 대응하는 실제 서피스 parameterU를 구함
    -> follicle을 그 U에 붙여서 최종 translate/rotate를 얻는다. follicle의
    회전은 서피스의 국소 tangent/normal에서 직접 계산되므로(motionPath의
    up-vector 방식과 달리) 구조적으로 플립이 없다 -- 참조 리그가 플립 문제를
    피하는 핵심 기법. (참조 리그는 이 follicle을 별도의 Attach joint에
    parentConstraint로 한 번 더 복사하는데, follicle의 transform 자체가 이미
    깨끗한 world translate/rotate를 내므로 그 중간 복사는 순수 중복이라 이
    모듈에서는 생략하고 follicle을 바로 4단계의 기준으로 쓴다.)

    각 지점의 motionPath uValue는 고정 fraction이 아니라 '유효 길이'
    (restCurveLength ~ 현재 arcLength를 Stretch로 blend, _build_stretch_ratio)
    기준으로 라이브 리매핑된다 -- fractionMode=1은 항상 현재 길이 기준으로
    균등 재분배하는데(Stretch=10 = 기존 동작), Stretch=0이면 늘어난 커브
    위에서도 rest 간격을 유지하며 tip 앞에서 멈추는 rigid 동작이 된다
    (참조 리그의 curveInfo/condition/blendTwoAttr 기반 stretch 비율 계산과
    같은 목적, 다만 이 모듈은 항상 stretchy와 rigid 사이를 부드럽게 blend
    한다).

4단계(FK/Skin): follicle 사이 로컬 delta(multMatrix: follicle[i].worldMatrix *
    follicle[i-1].worldInverseMatrix, i=0은 parentInverseMatrix)를 그대로
    받는 NUL 위에 애니메이터가 조작하는 FK 컨트롤을, follicle과 구조적으로
    평행한 하이라키로 쌓는다 -- IK가 만든 베이스 포즈 위에 얹는 추가 회전
    레이어. 최종 Skin joint(실제 캐릭터 메쉬를 바인드할 레이어, 이 모듈에서
    유일하게 진짜 skinning에 쓰이는 joint)는 대응하는 FK 컨트롤의 world pose를
    multMatrix/decomposeMatrix로 그대로 복제한다(참조 리그의
    L_FK_tentacle_XXX_CON / L_Skin_tentacle_XXX_JNT 구조).

5단계(Twist/Volume): Twist 시작/끝 컨트롤 2개(각각 Twist/Parameter
    attribute -- Parameter는 라이브로 조절 가능한 트위스트 구간의 경계, curve
    위에서 컨트롤 위치 자체가 그 값을 따라 슬라이드해서 씬에서 바로 보인다)
    -> 최종 Skin joint 각각의 rotateX(aim축)에 그 Parameter 구간 기준
    선형 그라디언트로 가산(구간 밖은 clamp로 가장 가까운 끝 값 고정). Skin
    joint는 서로 부모-자식으로 안 엮인 flat 구조라, 여기서 twist를 더하면 그
    joint 자신의 orientation만 돌아가고 다른 joint 위치에는 전혀 영향이 없다
    (FK 체인처럼 부모-자식으로 엮인 노드에 twist를 더하면 자식 전체가 그
    축을 중심으로 같이 돌면서 위치까지 끌려가 버린다 -- 그래서 twist는 FK
    체인이 아니라 flat한 Skin 레이어에 건다). Volume 컨트롤 N개(각각 Volume
    attribute, 고정 위치) -> 대응 구간을 선형보간해서 Skin joint의 scaleY/Z에
    연결(squash/stretch 볼륨 보정). Volume 컨트롤은 위치가 고정이라 두 컨트롤
    사이 보간 가중치를 빌드 타임에 파이썬으로 계산해서 blendTwoAttr 하나만
    연결하지만(_gradient_plug), Twist는 Parameter가 라이브라 비율 계산 자체를
    노드 네트워크로 만든다(_ranged_twist_plug).

6단계(Branch/TOP, 선택): 메인 리본 서피스를 복제해서, 그 위에 Demo(메인)를
    구동하는 마스터 컨트롤 레이어(TOP)를 만든다(build_branch). TOP은
    Demo와 반대 방향 하이라키를 쓴다 -- FK 컨트롤이 상위(굵은 마스터 포즈),
    그 자식으로 IK 컨트롤을 두어(로컬 미세조정) 그 IK가 1:1
    parentConstraint로 NurbsBind joint를 구동해서 {branch_name}_NSF({name}_NSF
    를 duplicate한, 같은 모양/parametrization의 복제 서피스)를 스킨한다.
    그렇게 변형된 TOP의 서피스 위에 Demo의 IK 컨트롤 개수와 동일한 개수의
    follicle을 Demo IK와 같은 arc-length 위치에 만들고, 그 출력으로 Demo의
    IK_OFF(오프셋 그룹)를 직접 구동한다 -- TOP을 움직이면 그 서피스 변형이
    follicle을 통해 그대로 Demo의 IK 컨트롤을 구동하는 마스터-슬레이브
    관계가 된다. Demo의 IK_CTL 자신은 OFF의 자식으로 남아 애니메이터가 그
    위에 추가로 움직일 수 있다(FK NUL/CTL과 동일한 패턴).

:Example:
    from python2.rigging import tentacle_ribbon_rig
    import importlib
    importlib.reload(tentacle_ribbon_rig)
    tentacle_ribbon_rig.build_base(mesh='pSphere1')
    tentacle_ribbon_rig.build_ik()
    tentacle_ribbon_rig.build_output()
    tentacle_ribbon_rig.build_fk()
    tentacle_ribbon_rig.build_twist_scale()
    tentacle_ribbon_rig.build_branch()
============================================================================"""
import maya.cmds as cmds
import maya.api.OpenMaya as om2
import numpy as np

_PERP_AXIS = {'x': (0.0, 0.0, 1.0), 'y': (1.0, 0.0, 0.0), 'z': (1.0, 0.0, 0.0)}


def _scatter_interior_points(mesh, resolution=30):
    """mesh의 bounding box 안에 격자로 점을 뿌리고, ray-cast 교차 횟수의
    홀짝으로 실제 오브젝트 내부에 있는 점만 남긴다(Houdini의 volume scatter와
    같은 개념 -- point-in-mesh 판정: 한쪽 방향으로 ray를 쏴서 표면과 교차한
    횟수가 홀수면 내부, 짝수면 외부).

    표면 vertex만 쓰면 폴리곤 해상도(각/세그먼트 개수)에 묶여서 밴드마다
    잡히는 점 분포가 불균등해지는데, 내부 scatter는 훨씬 촘촘하고 고르게
    분포해서 중심선 centroid가 더 매끄럽게 나온다.
    """
    sel = om2.MSelectionList()
    sel.add(mesh)
    mesh_fn = om2.MFnMesh(sel.getDagPath(0))

    bbox = cmds.exactWorldBoundingBox(mesh)
    lo = np.array(bbox[:3], dtype=float)
    hi = np.array(bbox[3:], dtype=float)
    size = hi-lo
    cell = size.max()/float(resolution)
    counts = np.maximum(2, np.round(size/cell).astype(int))

    # bbox 경계에 딱 붙는 값(lo/hi 그 자체)으로 샘플링하면, 둥근 단면에서는
    # 그 경계가 원의 접점(=표면 위 또는 바로 바깥)이라 안쪽으로 전혀 안 잡힐
    # 수 있다 -- 그래서 각 축을 counts개의 셀로 나눈 뒤 그 '셀 중심'만
    # 샘플링해서 경계에서 반 칸씩 안으로 들어오게 한다.
    xs = lo[0]+(np.arange(counts[0])+0.5)*(size[0]/counts[0])
    ys = lo[1]+(np.arange(counts[1])+0.5)*(size[1]/counts[1])
    zs = lo[2]+(np.arange(counts[2])+0.5)*(size[2]/counts[2])

    # 축에 딱 맞아 떨어지는 방향은 면/엣지와 평행하게 걸려서 교차 판정이
    # 불안정해질 수 있어 살짝 기울인 방향을 쓴다.
    ray_dir = om2.MFloatVector(1.0, 0.37, 0.19)

    interior = []
    for x in xs:
        for y in ys:
            for z in zs:
                pt = om2.MFloatPoint(float(x), float(y), float(z))
                res = mesh_fn.allIntersections(pt, ray_dir, om2.MSpace.kWorld,
                                                999999.0, False, tolerance=1e-6)
                count = 0 if res is None else len(res[0])
                if count % 2 == 1:
                    interior.append((x, y, z))
    return np.array(interior, dtype=float)


def _resample_uniform(points, num_points):
    """points로 이어진 폴리라인을 누적 arc length 기준 균등한 num_points개로
    다시 뽑는다. scatter가 표면 vertex보다 훨씬 적고 듬성듬성하면, centroid
    재계산만 반복할 때 인접 포인트끼리 너무 가까워지거나(심하면 겹침) 간격이
    불균등해질 수 있다 -- 매 반복 끝에 이 재배치를 해주면 다음 반복의 tangent
    계산이 항상 고르게 퍼진 포인트를 기준으로 이뤄져서 훨씬 안정적으로
    수렴한다(active contour/snake 알고리즘에서 흔히 쓰는 재정규화 기법).
    """
    seg = np.linalg.norm(points[1:]-points[:-1], axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = cum[-1]
    if total < 1e-9:
        return points.copy()
    targets = np.linspace(0.0, total, num_points)
    out = np.zeros_like(points)
    for k, t in enumerate(targets):
        j = int(np.searchsorted(cum, t))
        if j <= 0:
            out[k] = points[0]
        elif j >= len(points):
            out[k] = points[-1]
        else:
            t0, t1 = cum[j-1], cum[j]
            frac = 0.0 if t1 == t0 else (t-t0)/(t1-t0)
            out[k] = points[j-1]+(points[j]-points[j-1])*frac
    return out


def _get_axis_endpoints(mesh, axis='y'):
    """mesh의 world bounding box 중심을 지나는 축(base->tip 방향)의 양 끝점을 구한다."""
    bbox = cmds.exactWorldBoundingBox(mesh)
    if axis is None:
        lens = {'x': bbox[3]-bbox[0], 'y': bbox[4]-bbox[1], 'z': bbox[5]-bbox[2]}
        axis = max(lens, key=lens.get)
    mid = ((bbox[0]+bbox[3])/2.0, (bbox[1]+bbox[4])/2.0, (bbox[2]+bbox[5])/2.0)
    base = list(mid)
    tip = list(mid)
    idx = {'x': 0, 'y': 1, 'z': 2}[axis]
    lo = [bbox[0], bbox[1], bbox[2]][idx]
    hi = [bbox[3], bbox[4], bbox[5]][idx]
    base[idx], tip[idx] = lo, hi
    return tuple(base), tuple(tip), axis


def _get_centerline_points(mesh, axis, base, tip, num_points, iterations=4, band_ratio=0.75,
                            scatter_resolution=30):
    """반복적 로컬 프레임 슬라이싱(moving frame)으로 오브젝트의 실제 중심선을 구한다.

    표면 vertex 대신 오브젝트 내부에 뿌린 volume scatter 포인트(Houdini의
    scatter+centroid 방식과 동일한 개념, _scatter_interior_points)를 쓴다 --
    표면 vertex는 폴리곤 해상도에 묶여서 밴드마다 잡히는 점이 불균등한데,
    내부 scatter는 훨씬 촘촘하고 고르게 분포해서 centroid가 매끄럽게 나온다.

    세계축(axis) 방향 슬라이싱은 오브젝트가 그 축에 정렬돼 있고 거의 곧을 때만
    맞는다 -- 회전돼 있거나 휘어진 형태에서는 슬라이스 평면이 실제 단면과
    어긋나서 중심선이 틀어진다. 대신:
        1) base->tip 직선 보간으로 초기 커브를 추정한다.
        2) 매 반복마다 각 포인트의 로컬 tangent(인접 포인트 차분)를 구하고,
           '세계축'이 아니라 '그 tangent에 수직인' 국소 밴드 안의 scatter
           포인트만 모아서 centroid를 다시 계산한다.
        3) 갱신된 포인트로 tangent를 다시 구해서 반복한다.
    몇 번만 반복해도 곧은 형태뿐 아니라 휘어지거나 임의로 회전된 튜브형
    오브젝트에도 수렴한다 -- axis는 초기 추정에만 쓰이고, 반복이 끝나면
    실제로는 매 지점의 로컬 방향이 슬라이스 기준이 된다.

    초기 직선 추정은 많이 휜 오브젝트에서는 실제 형태와 크게 벗어날 수
    있다(base/tip의 나머지 두 좌표가 bbox 중심으로 고정되기 때문). 그래서
    밴드 폭을 처음엔 넓게 잡고(대략적으로라도 실제 포인트들을 붙잡도록)
    반복할수록 목표 폭(band_ratio 기준)까지 점점 좁혀가는 coarse-to-fine
    방식을 쓴다 -- 밴드를 처음부터 좁게 고정하면 초기 추정이 부정확한
    구간에서 포인트를 하나도 못 잡거나 잘못된 국소해에 갇혀 끝부분이
    수렴하지 않고 흔들릴 수 있다.
    """
    idx = {'x': 0, 'y': 1, 'z': 2}[axis]
    verts = _scatter_interior_points(mesh, resolution=scatter_resolution)
    if len(verts) < num_points*3:
        # scatter가 너무 안 나오면(해상도 부족/얇은 형태) 표면 vertex로 대체
        flat = cmds.xform('{}.vtx[*]'.format(mesh), q=True, ws=True, t=True)
        verts = np.array(flat, dtype=float).reshape(-1, 3)

    lo, hi = base[idx], tip[idx]
    span = hi-lo
    edge_band = (span/float(num_points-1))*band_ratio if num_points > 1 and span else abs(span) or 1.0
    min_bucket = max(3, len(verts)//num_points)

    def _edge_centroid(target):
        # base/tip은 bbox 중심으로 나머지 두 좌표가 고정된 값이라 휜 오브젝트의
        # 실제 끝 단면 중심과 다르다 -- axis 좌표만 target으로 고정하고 나머지는
        # 그 근처 vertex의 실제 centroid로 다시 잡는다(기존 방식과 동일한 원리).
        d = np.abs(verts[:, idx]-target)
        mask = d <= edge_band
        if not np.any(mask):
            nearest = np.argsort(d)[:min_bucket]
            mask = np.zeros(len(verts), dtype=bool)
            mask[nearest] = True
        c = verts[mask].mean(axis=0)
        c[idx] = target
        return c

    base_v = _edge_centroid(lo)
    tip_v = _edge_centroid(hi)
    t_vals = np.linspace(0.0, 1.0, num_points)
    points = base_v + np.outer(t_vals, tip_v-base_v)

    total_len = float(np.linalg.norm(tip_v-base_v)) or 1.0
    target_band = (total_len/float(num_points-1))*band_ratio if num_points > 1 else total_len
    # wide_band는 target_band의 배수로 잡는다(전체 길이의 절반처럼 오브젝트
    # 스케일에 비례한 값을 쓰면, scatter 포인트가 표면 vertex보다 훨씬 적고
    # 넓게 퍼져 있어서 첫 반복에 대부분의 포인트가 거의 전체 오브젝트의
    # '뭉치 centroid'로 쏠려버리고 이후 반복에서도 안 풀린다).
    wide_band = target_band*4.0

    for it in range(iterations):
        frac = it/float(iterations-1) if iterations > 1 else 1.0
        band_half = wide_band+(target_band-wide_band)*frac

        tangents = np.zeros_like(points)
        tangents[0] = points[1]-points[0]
        tangents[-1] = points[-1]-points[-2]
        tangents[1:-1] = points[2:]-points[:-2]
        norms = np.linalg.norm(tangents, axis=1, keepdims=True)
        norms[norms < 1e-9] = 1.0
        tangents = tangents/norms

        new_points = points.copy()
        for i in range(1, num_points-1):
            proj = (verts-points[i]).dot(tangents[i])
            mask = np.abs(proj) <= band_half
            if not np.any(mask):
                nearest = np.argsort(np.abs(proj))[:min_bucket]
                mask = np.zeros(len(verts), dtype=bool)
                mask[nearest] = True
            new_points[i] = verts[mask].mean(axis=0)

        # 양 끝은 세계축(axis) 좌표로 고정하지 않고, 로컬 tangent 방향으로
        # 가장 끝쪽(extremal)에 있는 scatter 슬라이스의 centroid로 매 반복
        # 다시 잡는다 -- 휘어진 오브젝트는 실제 끝 단면이 세계축에 대해
        # 기울어져 있어서, 세계축 좌표로 슬라이싱하면 그 기울어진 단면의
        # 일부만 걸리고 나머지는 못 잡아 centroid가 실제 중심에서 벗어난다.
        # tangent가 반복마다 실제 방향으로 수렴하면서 끝점도 같이 정확해진다.
        proj0 = verts.dot(tangents[0])
        base_mask = proj0 <= proj0.min()+band_half
        new_points[0] = verts[base_mask].mean(axis=0)

        proj_last = verts.dot(tangents[-1])
        tip_mask = proj_last >= proj_last.max()-band_half
        new_points[-1] = verts[tip_mask].mean(axis=0)

        # 재계산된 포인트들을 arc length 기준 균등 간격으로 재정규화 --
        # 그렇지 않으면 반복이 진행될수록 포인트끼리 뭉치거나 간격이
        # 들쑥날쑥해질 수 있다.
        points = _resample_uniform(new_points, num_points)

    return [tuple(p) for p in points]


def _build_groups(name):
    g = {}
    g['rig'] = cmds.createNode('transform', n='{}_rig_GRP'.format(name))
    g['geo'] = cmds.createNode('transform', n='{}_geo_GRP'.format(name), p=g['rig'])
    g['sys'] = cmds.createNode('transform', n='{}_sys_GRP'.format(name), p=g['rig'])
    cmds.setAttr(g['sys']+'.visibility', 0)
    return g


def _build_centerline_curve(name, mesh, axis, base, tip, num_cv):
    """base->tip 사이 오브젝트 실제 중심선을 따라가는 임시 degree-3 커브.
    리본 서피스를 loft하기 위한 프로필로만 쓰고 이후 삭제한다.
    """
    positions = _get_centerline_points(mesh, axis, base, tip, num_cv)
    crv = cmds.curve(n='{}_centerTemp_CRV'.format(name), d=3, p=positions)
    cmds.rebuildCurve(crv, ch=False, rpo=True, rt=0, end=1, kr=0, kcp=1,
                       kep=1, kt=0, s=len(positions)-3, d=3)
    return crv


def _build_ribbon_surface(name, center_crv, axis, width, sys_grp):
    """center_crv를 axis에 수직인 방향으로 +-width/2만큼 복제/이동한 두 커브를
    loft해서 얇은 리본 NURBS 서피스를 만든다.

    (참고) cmds.extrude(profile, path, et=2)로 시도했을 때는 path 위를
    정확히 따라가지 않고 profile 위치를 중심으로 대칭으로 스윕돼서 커브가
    오브젝트 중심선에서 절반만큼 벗어나는 문제가 있었다 -- loft가 훨씬
    예측 가능하고 정확하다. loft한 서피스는 U가 긴 방향(center_crv를 따라),
    V가 짧은 폭 방향이 된다.
    """
    perp = _PERP_AXIS[axis]
    half = width*0.5
    left = cmds.duplicate(center_crv, n='{}_ribbonLeftTemp_CRV'.format(name))[0]
    right = cmds.duplicate(center_crv, n='{}_ribbonRightTemp_CRV'.format(name))[0]
    cmds.move(-perp[0]*half, -perp[1]*half, -perp[2]*half, left, relative=True, objectSpace=True)
    cmds.move(perp[0]*half, perp[1]*half, perp[2]*half, right, relative=True, objectSpace=True)

    surf = cmds.loft(left, right, n='{}_NSF'.format(name), ch=False, u=True, c=False,
                      ar=True, d=3, ss=1, rn=False, po=0, rsn=True)[0]
    cmds.delete(left, right)
    return surf


def _extract_curve_from_surface(name, surface, v_param=0.5):
    """서피스의 V=0.5(중심선) isoparm에서 curve를 라이브로 추출한다
    (curveFromSurfaceIso -- 나중에 서피스가 IK로 변형되면 이 curve도 따라감).

    loft(left, right)로 만든 서피스는 U가 긴 방향(center_crv를 따라가는 방향),
    V가 짧은 폭 방향이 된다 -- 그래서 V를 고정하고 U를 따라가는 isoparm이
    중심선(긴 방향)이 된다.

    local=True로 서피스의 .local(조상 트랜스폼이 안 포함된 object space)을
    읽게 한다 -- local=False였을 때는 .worldSpace(조상까지 포함)를 읽어서,
    이 curve의 트랜스폼 자체도 같은 조상 체인 아래 있는 경우(예: 리본
    서피스 전체를 다른 곳에 재부모시키는 가지/branch 리그) 조상 트랜스폼이
    두 번 곱해져 위치가 완전히 틀어지는 버그가 있었다(메인 리그처럼 이
    조상이 항상 월드 원점에 고정이면 이 차이가 드러나지 않아서 오랫동안
    못 알아챘다).
    """
    dup = cmds.duplicateCurve('{}.v[{}]'.format(surface, v_param), ch=True,
                               rn=False, local=True)
    crv = cmds.rename(dup[0], '{}_CRV'.format(name))
    return crv


def _store_rest_length(curve):
    """curve의 현재 arc length를 restCurveLength 커스텀 attribute로 저장한다
    (참조 리그와 동일 -- 나중에 Stretch 비율 = 현재 길이 / 이 값).
    """
    length = cmds.arclen(curve)
    if not cmds.attributeQuery('restCurveLength', node=curve, exists=True):
        cmds.addAttr(curve, ln='restCurveLength', at='double', dv=length, k=False)
    else:
        cmds.setAttr(curve+'.restCurveLength', length)
    return length


def build_base(mesh='pSphere1', name='tentacle', axis='y', num_cv=19, ribbon_width=1.0):
    """1단계 베이스: mesh 중심선 -> 리본 서피스 -> 서피스에서 curve 재추출
    -> restCurveLength 저장.

    Arguments:
        mesh (str): 촉수 형상 스탠드인
        name (str): 리그 네이밍 프리픽스
        axis (str): 중심선이 뻗어나갈 축 ('x'/'y'/'z'). None이면 가장 긴 축 자동 감지.
        num_cv (int): center curve의 CV 개수(=리본 서피스 U방향 해상도)
        ribbon_width (float): 리본 서피스의 폭

    Returns:
        dict: surface, curve, axis, rest_length 등
    """
    if cmds.objExists('{}_rig_GRP'.format(name)):
        cmds.delete('{}_rig_GRP'.format(name))

    base, tip, axis = _get_axis_endpoints(mesh, axis)
    g = _build_groups(name)
    cmds.addAttr(g['rig'], ln='tentacleAxis', dt='string')
    cmds.setAttr(g['rig']+'.tentacleAxis', axis, type='string')

    center_crv = _build_centerline_curve(name, mesh, axis, base, tip, num_cv)
    surface = _build_ribbon_surface(name, center_crv, axis, ribbon_width, g['sys'])
    cmds.delete(center_crv)
    cmds.parent(surface, g['geo'])

    out_crv = _extract_curve_from_surface(name, surface)
    cmds.parent(out_crv, g['geo'])
    rest_length = _store_rest_length(out_crv)

    print('=' * 60)
    print('Tentacle Ribbon 베이스 완료: {}'.format(name))
    print('  axis            : {}'.format(axis))
    print('  surface         : {}'.format(surface))
    print('  curve           : {}'.format(out_crv))
    print('  restCurveLength : {:.4f}'.format(rest_length))
    print('=' * 60)
    return {'rig_grp': g['rig'], 'surface': surface, 'curve': out_crv,
            'axis': axis, 'rest_length': rest_length}


def _sample_curve_frame(curve, fraction, up_vector):
    """curve 위 한 지점의 world position/rotation을 motionPath로 샘플링한다
    (follow=1 -- 접선(tangent) 방향으로 자동 정렬, worldUpVector로 기울어짐을
    고정). 라이브 리그 연결이 아니라 IK 컨트롤의 초기 배치/방향을 한 번만
    계산하는 용도라, 세션 전체에서 지적된 up-vector 방식의 플립 문제는
    여기서는 해당되지 않는다(완만한 촉수 굴곡에서 정적인 bind pose를 잡는
    정도로 충분 -- 실제 라이브 출력 체인은 이후 단계에서 follicle로 만든다).
    up_vector는 리본 서피스의 폭 방향(_PERP_AXIS)과 동일한 벡터를 써서, 굴곡이
    있어도 표면의 실제 폭 방향과 컨트롤의 정렬 기준이 서로 어긋나지 않게 한다.
    """
    shape = cmds.listRelatives(curve, shapes=True, ni=True, fullPath=True)[0]
    mp = cmds.createNode('motionPath', n='tmp_sampleFrame_MPT')
    cmds.connectAttr(shape+'.worldSpace[0]', mp+'.geometryPath')
    cmds.setAttr(mp+'.fractionMode', 1)
    cmds.setAttr(mp+'.uValue', fraction)
    cmds.setAttr(mp+'.follow', 1)
    cmds.setAttr(mp+'.frontAxis', 0)
    cmds.setAttr(mp+'.upAxis', 1)
    cmds.setAttr(mp+'.worldUpType', 3)
    cmds.setAttr(mp+'.worldUpVectorX', up_vector[0])
    cmds.setAttr(mp+'.worldUpVectorY', up_vector[1])
    cmds.setAttr(mp+'.worldUpVectorZ', up_vector[2])
    pos = cmds.getAttr(mp+'.allCoordinates')[0]
    rot = (cmds.getAttr(mp+'.rotateX'), cmds.getAttr(mp+'.rotateY'), cmds.getAttr(mp+'.rotateZ'))
    cmds.delete(mp)
    return pos, rot


def _build_ik_controls(name, curve, axis, num_ik, radius, ctl_grp):
    """리본 curve 위에 arc-length 균등 배치된 IK 컨트롤 num_ik개를 만든다
    (참조 리그의 L_IK_tentacle_XXX_CON). 컨트롤 shape는 aim축(local X)을
    감싸는 원 -- 나중에 촉수를 굽힐 때 자연스러운 회전 링 형태.
    """
    up_vector = _PERP_AXIS[axis]
    ctrls, offsets = [], []
    for i in range(num_ik):
        frac = i/float(num_ik-1) if num_ik > 1 else 0.0
        pos, rot = _sample_curve_frame(curve, frac, up_vector)
        ctrl = cmds.circle(n='{}_IK{:02d}_CTL'.format(name, i+1), ch=False, nr=(1, 0, 0), r=radius)[0]
        off = cmds.group(ctrl, n='{}_IK{:02d}_OFF'.format(name, i+1))
        cmds.xform(off, ws=True, t=pos, ro=rot)
        cmds.setAttr(ctrl+'.overrideEnabled', 1)
        cmds.setAttr(ctrl+'.overrideColor', 17)
        cmds.parent(off, ctl_grp)
        ctrls.append(ctrl)
        offsets.append(off)
    return ctrls, offsets


def _build_nurbs_bind_joints(name, ik_ctrls, ik_offsets, jnt_grp):
    """IK 컨트롤 각각이 1:1 parentConstraint로 구동하는 NurbsBind joint를
    만든다(참조 리그의 L_NurbsBind_tentacle_XXX_JNT) -- 이 joint들이 리본
    서피스의 skinCluster influence가 된다.
    """
    jnts = []
    for i, (ctrl, off) in enumerate(zip(ik_ctrls, ik_offsets)):
        pos = cmds.xform(off, q=True, ws=True, t=True)
        rot = cmds.xform(off, q=True, ws=True, ro=True)
        cmds.select(clear=True)
        jnt = cmds.joint(n='{}_NurbsBind{:02d}_JNT'.format(name, i+1))
        cmds.parent(jnt, jnt_grp)
        cmds.xform(jnt, ws=True, t=pos, ro=rot)
        cmds.makeIdentity(jnt, apply=True, t=0, r=1, s=0, jo=1)
        cmds.parentConstraint(ctrl, jnt, mo=False)
        jnts.append(jnt)
    return jnts


def _skin_ribbon_surface(name, surface, bind_jnts):
    """NurbsBind joint들로 리본 서피스를 스킨 바인드한다."""
    skin = cmds.skinCluster(bind_jnts, surface, tsb=True, n='{}_ribbon_SKN'.format(name), mi=3)[0]
    return skin


def build_ik(name='tentacle', num_ik=9, ctrl_radius=1.0):
    """2단계: 리본 서피스를 따라 IK 컨트롤 N개 배치 -> 1:1 NurbsBind joint ->
    리본 서피스 스킨 바인드.

    build_base()가 먼저 실행되어 {name}_rig_GRP/{name}_CRV/{name}_NSF가 이미
    존재해야 한다.

    Arguments:
        name (str): build_base()와 동일한 리그 네이밍 프리픽스
        num_ik (int): IK 컨트롤 개수(=NurbsBind joint 개수)
        ctrl_radius (float): IK 컨트롤 shape 반경

    Returns:
        dict: ik_ctrls, bind_jnts, skin_cluster
    """
    rig_grp = '{}_rig_GRP'.format(name)
    curve = '{}_CRV'.format(name)
    surface = '{}_NSF'.format(name)
    if not cmds.objExists(rig_grp) or not cmds.objExists(curve) or not cmds.objExists(surface):
        raise RuntimeError('build_ik: build_base()를 먼저 실행하세요 ({} 없음)'.format(rig_grp))

    axis = cmds.getAttr(rig_grp+'.tentacleAxis')

    ctl_grp_name = '{}_ikCtl_GRP'.format(name)
    jnt_grp_name = '{}_bindJnt_GRP'.format(name)
    if cmds.objExists(ctl_grp_name):
        cmds.delete(ctl_grp_name)
    if cmds.objExists(jnt_grp_name):
        cmds.delete(jnt_grp_name)

    ctl_grp = cmds.createNode('transform', n=ctl_grp_name, p=rig_grp)
    sys_grp = '{}_sys_GRP'.format(name)
    jnt_grp = cmds.createNode('transform', n=jnt_grp_name,
                               p=sys_grp if cmds.objExists(sys_grp) else rig_grp)

    ik_ctrls, ik_offsets = _build_ik_controls(name, curve, axis, num_ik, ctrl_radius, ctl_grp)
    bind_jnts = _build_nurbs_bind_joints(name, ik_ctrls, ik_offsets, jnt_grp)
    skin = _skin_ribbon_surface(name, surface, bind_jnts)

    # Stretch는 마지막 IK 컨트롤에 둔다(참조 리그와 동일한 관례) -- 0이면
    # curve가 늘어나도 출력 지점들이 restCurveLength 기준 간격을 유지하다가
    # tip 앞에서 멈추고(rigid), 10이면 현재 arc length에 맞춰 항상 균등
    # 재분배된다(stretchy, 기존 동작과 동일) -- build_output()의
    # _build_output_follicles가 이 값을 읽어서 라이브로 uValue를 리매핑한다.
    # 기본값 10 = 기존 동작 그대로라 이 attribute를 안 만지면 아무것도
    # 안 바뀐다.
    cmds.addAttr(ik_ctrls[-1], ln='Stretch', at='double', min=0, max=10, dv=10, k=True)

    print('=' * 60)
    print('Tentacle Ribbon IK 완료: {}'.format(name))
    print('  ik ctrls  : {}'.format(len(ik_ctrls)))
    print('  bind jnts : {}'.format(len(bind_jnts)))
    print('  skin      : {}'.format(skin))
    print('=' * 60)
    return {'ik_ctrls': ik_ctrls, 'bind_jnts': bind_jnts, 'skin_cluster': skin}


def _build_stretch_ratio(name, curve, stretch_ctrl):
    """curve의 현재 arc length와 restCurveLength, stretch_ctrl의 Stretch(0~10)
    attribute로 '유효 길이'를 계산하는 라이브 plug을 만든다.

    Stretch=0이면 effectiveLength=restCurveLength(늘어나도 출력 지점 간격이
    rest 기준으로 고정돼 tip 앞에서 멈추는 rigid 동작), Stretch=10이면
    effectiveLength=현재 arcLength(항상 균등 재분배되는 stretchy 동작, 이
    attribute를 추가하기 전의 기존 동작과 동일). blendTwoAttr의
    attributesBlender에 라이브 plug을 그대로 연결할 수 있어서 별도의
    plusMinusAverage/multiply 조합 없이 한 노드로 끝난다.
    """
    curve_shape = cmds.listRelatives(curve, shapes=True, ni=True, fullPath=True)[0]
    cif = cmds.createNode('curveInfo', n='{}_stretch_CIF'.format(name))
    cmds.connectAttr(curve_shape+'.worldSpace[0]', cif+'.inputCurve')

    norm = cmds.createNode('multDoubleLinear', n='{}_stretchNorm_MDL'.format(name))
    cmds.setAttr(norm+'.input2', 0.1)
    cmds.connectAttr(stretch_ctrl+'.Stretch', norm+'.input1')

    blend = cmds.createNode('blendTwoAttr', n='{}_effectiveLength_BTA'.format(name))
    cmds.connectAttr(curve+'.restCurveLength', blend+'.input[0]')
    cmds.connectAttr(cif+'.arcLength', blend+'.input[1]')
    cmds.connectAttr(norm+'.output', blend+'.attributesBlender')

    return blend+'.output', cif+'.arcLength'


def _build_output_follicles(name, curve, surface, num_output, fol_grp, stretch_ctrl=None):
    """curve 위 num_output개 지점을 motionPath(position만)로 라이브 추적하고,
    그 위치를 closestPointOnSurface로 서피스의 실제 parameterU로 변환한 뒤
    그 U에 follicle을 붙인다.

    curve는 서피스에서 curveFromSurfaceIso로 라이브 추출된 것(_extract_curve_from_surface)
    이라 서피스가 IK로 변형되면 같이 움직이지만, curve 자체의 parametrization이
    서피스의 U parametrization과 정확히 일치하는 보장은 없다 -- 그래서 curve
    위치를 그대로 follicle에 쓰지 않고, closestPointOnSurface로 그 위치에
    대응하는 서피스의 실제 U를 다시 구해서 넘긴다. follicle의 출력 회전은
    서피스의 국소 tangent/normal에서 바로 계산되므로 motionPath의 up-vector
    방식과 달리 구조적으로 플립이 없다.

    motionPath의 geometryPath는 curve의 worldSpace를 읽으므로 allCoordinates
    출력도 이미 world space 좌표다 -- 그래서 closestPointOnSurface.inPosition에
    (같은 world space를 쓰는 inputSurface와 짝을 맞춰) 바로 연결한다. 예전엔
    중간에 위치 확인용 locator를 하나 두고 그 locator의 .translate(로컬
    attribute)에 이 world space 좌표를 connectAttr로 그대로 꽂았는데, 이
    locator가 identity가 아닌 조상(예: 다른 곳에 붙는 branch 리그의 follicle)
    아래에 있으면 조상 트랜스폼이 다시 한번 곱해져 위치가 완전히 틀어지는
    버그가 있었다(메인 리그는 조상이 항상 월드 원점이라 안 드러났다) --
    locator를 없애고 world space 값을 그대로 넘기면 이 문제가 원천적으로
    없어진다.

    stretch_ctrl을 주면(Stretch attribute를 가진 마지막 IK 컨트롤) 각 지점의
    motionPath uValue를 '고정 fraction'이 아니라 '유효 길이(_build_stretch_ratio)
    기준으로 리매핑된 fraction'으로 라이브 연결한다 -- fractionMode=1은 항상
    현재 arc length 기준으로 균등 재분배하는데, Stretch가 0에 가까울수록
    effectiveLength가 restCurveLength에 가까워져서 늘어난 커브 위에서도 rest
    간격을 유지하다가 tip 앞에서 멈추는(rigid) 동작이 된다.
    """
    crv_shape = cmds.listRelatives(curve, shapes=True, ni=True, fullPath=True)[0]
    surf_shape = cmds.listRelatives(surface, shapes=True, ni=True, fullPath=True)[0]

    if stretch_ctrl:
        effective_len_plug, arc_len_plug = _build_stretch_ratio(name, curve, stretch_ctrl)

    follicles = []
    for i in range(num_output):
        frac = i/float(num_output-1) if num_output > 1 else 0.0
        idx = i+1

        mp = cmds.createNode('motionPath', n='{}_output{:02d}_MPT'.format(name, idx))
        cmds.connectAttr(crv_shape+'.worldSpace[0]', mp+'.geometryPath')
        cmds.setAttr(mp+'.fractionMode', 1)

        if stretch_ctrl:
            frac_len = cmds.createNode('multDoubleLinear', n='{}_output{:02d}_fracLen_MDL'.format(name, idx))
            cmds.setAttr(frac_len+'.input2', frac)
            cmds.connectAttr(effective_len_plug, frac_len+'.input1')

            remap = cmds.createNode('multiplyDivide', n='{}_output{:02d}_remapU_MPD'.format(name, idx))
            cmds.setAttr(remap+'.operation', 2)
            cmds.connectAttr(frac_len+'.output', remap+'.input1X')
            cmds.connectAttr(arc_len_plug, remap+'.input2X')
            cmds.connectAttr(remap+'.outputX', mp+'.uValue')
        else:
            cmds.setAttr(mp+'.uValue', frac)

        cps = cmds.createNode('closestPointOnSurface', n='{}_output{:02d}_CPS'.format(name, idx))
        cmds.connectAttr(surf_shape+'.worldSpace[0]', cps+'.inputSurface')
        cmds.connectAttr(mp+'.allCoordinates', cps+'.inPosition')

        fol_shape = cmds.createNode('follicle', n='{}_output{:02d}_FOLShape'.format(name, idx))
        fol_xform = cmds.listRelatives(fol_shape, parent=True)[0]
        fol_xform = cmds.rename(fol_xform, '{}_output{:02d}_FOL'.format(name, idx))
        cmds.connectAttr(surf_shape+'.local', fol_shape+'.inputSurface')
        cmds.connectAttr(surf_shape+'.worldMatrix[0]', fol_shape+'.inputWorldMatrix')
        cmds.connectAttr(cps+'.parameterU', fol_shape+'.parameterU')
        cmds.setAttr(fol_shape+'.parameterV', 0.5)
        cmds.connectAttr(fol_shape+'.outTranslate', fol_xform+'.translate')
        cmds.connectAttr(fol_shape+'.outRotate', fol_xform+'.rotate')
        cmds.parent(fol_xform, fol_grp)

        follicles.append(fol_xform)
    return follicles


def build_output(name='tentacle', num_output=25):
    """3단계: curve -> motionPath(위치) -> closestPointOnSurface(서피스 실제 U) ->
    follicle(플립 없는 회전).

    build_base()/build_ik()가 먼저 실행되어 {name}_rig_GRP/{name}_CRV/{name}_NSF가
    이미 존재해야 한다(follicle이 서피스를 참조하므로 build_ik()의 스킨까지
    끝난 서피스를 쓴다).

    Arguments:
        name (str): build_base()/build_ik()와 동일한 리그 네이밍 프리픽스
        num_output (int): follicle 개수(최종 출력 해상도)

    Returns:
        dict: follicles
    """
    rig_grp = '{}_rig_GRP'.format(name)
    curve = '{}_CRV'.format(name)
    surface = '{}_NSF'.format(name)
    if not cmds.objExists(rig_grp) or not cmds.objExists(curve) or not cmds.objExists(surface):
        raise RuntimeError('build_output: build_base()/build_ik()를 먼저 실행하세요 ({} 없음)'.format(rig_grp))

    sys_grp = '{}_sys_GRP'.format(name)
    fol_grp_name = '{}_outputFol_GRP'.format(name)
    if cmds.objExists(fol_grp_name):
        cmds.delete(fol_grp_name)

    fol_grp = cmds.createNode('transform', n=fol_grp_name,
                               p=sys_grp if cmds.objExists(sys_grp) else rig_grp)

    ik_ctrls = sorted(cmds.ls('{}_IK*_CTL'.format(name)))
    stretch_ctrl = ik_ctrls[-1] if ik_ctrls and cmds.attributeQuery('Stretch', node=ik_ctrls[-1], exists=True) else None

    follicles = _build_output_follicles(name, curve, surface, num_output, fol_grp,
                                         stretch_ctrl=stretch_ctrl)

    print('=' * 60)
    print('Tentacle Ribbon Output 완료: {}'.format(name))
    print('  follicles : {}'.format(len(follicles)))
    print('=' * 60)
    return {'follicles': follicles}


def _gradient_plug(ctrls, attr, positions, t, node_prefix):
    """ctrls[k].attr들이 각각 고정 파라미터 positions[k](오름차순, 0~1)에
    있다고 볼 때, 임의의 t에서의 선형보간 값을 내는 live plug을 만든다.

    컨트롤 위치가 전부 고정(애니메이터가 옮기지 않음)이라 t를 감싸는 두
    컨트롤의 인덱스와 보간 가중치는 빌드 타임에 파이썬으로 바로 계산할 수
    있다 -- 그래서 런타임에 구간을 찾는 condition 체인 없이 blendTwoAttr
    하나만 연결하면 된다(t가 양 끝 바깥이면 가장 가까운 끝 값을 그대로
    반환 -- clamp와 동일한 효과).
    """
    n = len(ctrls)
    if t <= positions[0]:
        lo, hi = 0, 0
    elif t >= positions[-1]:
        lo, hi = n-1, n-1
    else:
        lo, hi = 0, n-1
        for k in range(n-1):
            if positions[k] <= t <= positions[k+1]:
                lo, hi = k, k+1
                break
    if lo == hi:
        return ctrls[lo]+'.'+attr
    span = positions[hi]-positions[lo]
    w = 0.0 if span < 1e-9 else (t-positions[lo])/span
    blend = cmds.createNode('blendTwoAttr', n=node_prefix+'_BTA')
    cmds.setAttr(blend+'.attributesBlender', w)
    cmds.connectAttr(ctrls[lo]+'.'+attr, blend+'.input[0]')
    cmds.connectAttr(ctrls[hi]+'.'+attr, blend+'.input[1]')
    return blend+'.output'


def _build_fk_chain(name, follicles, ctl_grp, ctrl_radius):
    """follicle 사이 로컬 delta(multMatrix: follicle[i].worldMatrix *
    follicle[i-1].worldInverseMatrix, i=0은 parentInverseMatrix ->
    decomposeMatrix -> NUL.translate/rotate)를 그대로 받는 NUL 위에,
    애니메이터가 조작하는 FK 컨트롤을 follicle과 구조적으로 평행한 하이라키
    (NUL_i -> CTL_i -> NUL_i+1 -> CTL_i+1 -> ...)로 쌓는다.

    각 FK 컨트롤의 로컬 transform은 0으로 유지한다(NUL이 이미 follicle의
    절대 포즈를 그대로 복제하고 있으므로) -- 애니메이터가 컨트롤을 돌리면 그
    값이 자식 NUL/CTL로 그대로 상속되어, IK가 만든 베이스 포즈 위에 얹는
    추가 회전 레이어가 된다.
    """
    fk_ctrls = []
    parent_node = ctl_grp
    prev_fol = None
    for i, fol in enumerate(follicles):
        idx = i+1
        nul = cmds.createNode('transform', n='{}_FK{:02d}_NUL'.format(name, idx), p=parent_node)

        mm = cmds.createNode('multMatrix', n='{}_FK{:02d}_MMX'.format(name, idx))
        cmds.connectAttr(fol+'.worldMatrix[0]', mm+'.matrixIn[0]')
        if prev_fol is None:
            cmds.connectAttr(nul+'.parentInverseMatrix[0]', mm+'.matrixIn[1]')
        else:
            cmds.connectAttr(prev_fol+'.worldInverseMatrix[0]', mm+'.matrixIn[1]')

        dcm = cmds.createNode('decomposeMatrix', n='{}_FK{:02d}_DCM'.format(name, idx))
        cmds.connectAttr(mm+'.matrixSum', dcm+'.inputMatrix')
        cmds.connectAttr(dcm+'.outputTranslate', nul+'.translate')
        cmds.connectAttr(dcm+'.outputRotate', nul+'.rotate')

        ctrl = cmds.circle(n='{}_FK{:02d}_CTL'.format(name, idx), ch=False, nr=(1, 0, 0), r=ctrl_radius)[0]
        cmds.setAttr(ctrl+'.overrideEnabled', 1)
        cmds.setAttr(ctrl+'.overrideColor', 6)
        cmds.parent(ctrl, nul)
        cmds.setAttr(ctrl+'.translate', 0, 0, 0)
        cmds.setAttr(ctrl+'.rotate', 0, 0, 0)

        fk_ctrls.append(ctrl)
        parent_node = ctrl
        prev_fol = fol

    return fk_ctrls


def _build_skin_joints(name, fk_ctrls, jnt_grp, twist_ctrls=None):
    """FK 컨트롤 각각의 world pose를 multMatrix/decomposeMatrix로 그대로
    복제하는 최종 Skin joint를 만든다(참조 리그의 L_Skin_tentacle_XXX_JNT) --
    실제 캐릭터 메쉬를 스킨 바인드할 때 쓰는 최종 레이어.

    Skin joint는 서로 부모-자식으로 엮이지 않은 flat 구조(jnt_grp 바로 아래)
    라서, twist_ctrls를 주면(시작/끝 2개, 각각 Twist/Parameter attribute) 각
    joint의 rotateX(aim축)에 Start~End Parameter 구간 기준 선형 그라디언트를
    가산해도(_ranged_twist_plug, 구간 밖은 clamp) 그 joint 자신의
    orientation만 바뀌고 다른 joint 위치에는 영향이 없다 -- FK 체인처럼
    부모-자식으로 엮인 곳에 twist를 걸면 자식 전체가 그 축을 중심으로 같이
    돌면서 위치까지 끌려가 버리는데, flat한 이 레이어에서는 그런 문제가 없다.
    parentConstraint 대신 multMatrix를 쓰는 이유도 이 rotateX 가산 지점을
    끼워 넣기 위해서다(constraint는 rotate 채널 전체를 통째로 덮어써서 중간에
    끼워 넣을 수 없다).
    """
    num = len(fk_ctrls)
    jnts = []
    for i, ctrl in enumerate(fk_ctrls):
        idx = i+1
        pos = cmds.xform(ctrl, q=True, ws=True, t=True)
        rot = cmds.xform(ctrl, q=True, ws=True, ro=True)
        cmds.select(clear=True)
        jnt = cmds.joint(n='{}_Skin{:02d}_JNT'.format(name, idx))
        cmds.parent(jnt, jnt_grp)
        cmds.xform(jnt, ws=True, t=pos, ro=rot)
        cmds.makeIdentity(jnt, apply=True, t=0, r=1, s=0, jo=1)

        mm = cmds.createNode('multMatrix', n='{}_Skin{:02d}_MMX'.format(name, idx))
        cmds.connectAttr(ctrl+'.worldMatrix[0]', mm+'.matrixIn[0]')
        cmds.connectAttr(jnt+'.parentInverseMatrix[0]', mm+'.matrixIn[1]')

        dcm = cmds.createNode('decomposeMatrix', n='{}_Skin{:02d}_DCM'.format(name, idx))
        cmds.connectAttr(mm+'.matrixSum', dcm+'.inputMatrix')
        cmds.connectAttr(dcm+'.outputTranslate', jnt+'.translate')

        if twist_ctrls:
            t = i/float(num-1) if num > 1 else 0.0
            twist_plug = _ranged_twist_plug(twist_ctrls[0], twist_ctrls[1], t,
                                             '{}_Skin{:02d}_twist'.format(name, idx))
            add = cmds.createNode('addDoubleLinear', n='{}_Skin{:02d}_twistADL'.format(name, idx))
            cmds.connectAttr(dcm+'.outputRotateX', add+'.input1')
            cmds.connectAttr(twist_plug, add+'.input2')
            cmds.connectAttr(add+'.output', jnt+'.rotateX')
            cmds.connectAttr(dcm+'.outputRotateY', jnt+'.rotateY')
            cmds.connectAttr(dcm+'.outputRotateZ', jnt+'.rotateZ')
        else:
            cmds.connectAttr(dcm+'.outputRotate', jnt+'.rotate')

        jnts.append(jnt)
    return jnts


def build_fk(name='tentacle', ctrl_radius=0.8, twist_ctrls=None):
    """4단계: follicle 체인과 구조적으로 평행한 matrix 기반 FK 하이라키
    (_build_fk_chain) 위에, 최종 Skin joint(_build_skin_joints)를 얹는다.

    build_output()이 먼저 실행되어 {name}_output##_FOL이 이미 존재해야 한다.
    twist_ctrls를 넘기면(build_twist_scale이 내부적으로 재호출할 때 씀) Skin
    joint 레이어에 Twist 그라디언트가 가산된다(FK 체인이 아니라 flat한 Skin
    레이어에 거는 이유는 _build_skin_joints 참고) -- 기존 FK/Skin 그룹은
    매번 새로 지우고 다시 만들기 때문에 twist_ctrls 유무와 관계없이 안전하게
    재호출 가능하다.

    Arguments:
        name (str): 이전 단계와 동일한 리그 네이밍 프리픽스
        ctrl_radius (float): FK 컨트롤 shape 반경
        twist_ctrls (list): [start_ctrl, end_ctrl] -- build_twist_scale()이
            먼저 만든 Twist 컨트롤. None이면 Twist 없이 빌드(기존과 동일).

    Returns:
        dict: fk_ctrls, skin_jnts
    """
    rig_grp = '{}_rig_GRP'.format(name)
    follicles = sorted(cmds.ls('{}_output*_FOL'.format(name)))
    if not cmds.objExists(rig_grp) or not follicles:
        raise RuntimeError('build_fk: build_output()을 먼저 실행하세요 ({} follicle 없음)'.format(name))

    fk_grp_name = '{}_fkCtl_GRP'.format(name)
    skin_grp_name = '{}_skinJnt_GRP'.format(name)
    if cmds.objExists(fk_grp_name):
        cmds.delete(fk_grp_name)
    if cmds.objExists(skin_grp_name):
        cmds.delete(skin_grp_name)

    fk_grp = cmds.createNode('transform', n=fk_grp_name, p=rig_grp)
    sys_grp = '{}_sys_GRP'.format(name)
    skin_grp = cmds.createNode('transform', n=skin_grp_name,
                                p=sys_grp if cmds.objExists(sys_grp) else rig_grp)

    fk_ctrls = _build_fk_chain(name, follicles, fk_grp, ctrl_radius)
    skin_jnts = _build_skin_joints(name, fk_ctrls, skin_grp, twist_ctrls=twist_ctrls)

    print('=' * 60)
    print('Tentacle Ribbon FK/Skin 완료: {}'.format(name))
    print('  fk ctrls  : {}'.format(len(fk_ctrls)))
    print('  skin jnts : {}'.format(len(skin_jnts)))
    print('=' * 60)
    return {'fk_ctrls': fk_ctrls, 'skin_jnts': skin_jnts}


def _build_twist_controls(name, curve, axis, ctl_grp, ctrl_radius):
    """curve의 시작/끝에 Twist(각도)와 Parameter(0~1, 트위스트 구간의 경계)
    attribute를 하나씩 가진 컨트롤 2개를 만든다.

    Parameter는 라이브로 연결된 motionPath(fractionMode=1, follow=1)를 통해
    컨트롤 OFF 그룹의 translate/rotate를 둘 다 curve 위에서 실시간으로
    구동한다 -- 애니메이터가 Parameter를 조절하면 컨트롤이 실제로 curve 위
    그 지점으로 슬라이드하면서 그 지점의 normal 방향에 맞춰 같이 회전해서,
    슬라이드 중에도 컨트롤 방향이 항상 curve에 맞게 유지된다. 이 컨트롤은
    값(Twist/Parameter)만 계산에 쓰이고 자기 자신의 world orientation은 어떤
    live 리그 연결에도 입력으로 안 들어가므로, follow 방식의 플립 위험이
    있어도(급격히 휜 구간에서 컨트롤 자체가 살짝 틀어지는 정도) 다른 노드로
    전파되지 않는다. _build_skin_joints가 Start/End의 Parameter 구간을
    기준으로 각 joint의 t가 몇 %인지(구간 밖은 clamp) 계산해서 Twist 값을
    선형보간한다(_ranged_twist_plug).
    """
    up_vector = _PERP_AXIS[axis]
    crv_shape = cmds.listRelatives(curve, shapes=True, ni=True, fullPath=True)[0]
    ctrls = []
    for label, default_param in (('Start', 0.0), ('End', 1.0)):
        ctrl = cmds.circle(n='{}_Twist{}_CTL'.format(name, label), ch=False,
                            nr=(1, 0, 0), r=ctrl_radius*1.4)[0]
        off = cmds.group(ctrl, n='{}_Twist{}_OFF'.format(name, label))
        cmds.setAttr(ctrl+'.overrideEnabled', 1)
        cmds.setAttr(ctrl+'.overrideColor', 18)
        cmds.addAttr(ctrl, ln='Twist', at='doubleAngle', dv=0, k=True)
        cmds.addAttr(ctrl, ln='Parameter', at='double', min=0, max=1, dv=default_param, k=True)
        cmds.parent(off, ctl_grp)

        mp = cmds.createNode('motionPath', n='{}_Twist{}_MPT'.format(name, label))
        cmds.connectAttr(crv_shape+'.worldSpace[0]', mp+'.geometryPath')
        cmds.setAttr(mp+'.fractionMode', 1)
        cmds.connectAttr(ctrl+'.Parameter', mp+'.uValue')
        cmds.setAttr(mp+'.follow', 1)
        cmds.setAttr(mp+'.frontAxis', 0)
        cmds.setAttr(mp+'.upAxis', 1)
        cmds.setAttr(mp+'.worldUpType', 3)
        cmds.setAttr(mp+'.worldUpVectorX', up_vector[0])
        cmds.setAttr(mp+'.worldUpVectorY', up_vector[1])
        cmds.setAttr(mp+'.worldUpVectorZ', up_vector[2])
        cmds.connectAttr(mp+'.allCoordinates', off+'.translate')
        cmds.connectAttr(mp+'.rotate', off+'.rotate')

        ctrls.append(ctrl)
    return ctrls


def _ranged_twist_plug(start_ctrl, end_ctrl, t, node_prefix):
    """start_ctrl/end_ctrl의 Parameter(라이브, 애니메이터가 조절 가능한 구간
    경계)를 기준으로, 고정된 t(해당 joint의 arc-length 위치)가 그 구간의
    몇 %에 해당하는지 0~1로 clamp해서 계산하고, 그 비율로 Start.Twist ~
    End.Twist를 선형보간한 값을 내는 live plug을 만든다.

    Parameter가 라이브로 바뀔 수 있어서 _gradient_plug처럼 빌드 타임에
    브래킷/가중치를 파이썬으로 미리 계산해둘 수 없다 -- 그래서 비율 계산
    자체를 노드 네트워크로 만든다. t가 구간 밖이면 clamp에 의해 가장 가까운
    끝의 Twist 값으로 고정된다(구간 밖 조인트는 안 끊기고 자연스럽게 이어짐).
    """
    diff = cmds.createNode('plusMinusAverage', n=node_prefix+'_diffPMA')
    cmds.setAttr(diff+'.operation', 2)
    cmds.connectAttr(end_ctrl+'.Parameter', diff+'.input1D[0]')
    cmds.connectAttr(start_ctrl+'.Parameter', diff+'.input1D[1]')

    sub = cmds.createNode('plusMinusAverage', n=node_prefix+'_subPMA')
    cmds.setAttr(sub+'.operation', 2)
    cmds.setAttr(sub+'.input1D[0]', t)
    cmds.connectAttr(start_ctrl+'.Parameter', sub+'.input1D[1]')

    ratio = cmds.createNode('multiplyDivide', n=node_prefix+'_ratioMPD')
    cmds.setAttr(ratio+'.operation', 2)
    cmds.connectAttr(sub+'.output1D', ratio+'.input1X')
    cmds.connectAttr(diff+'.output1D', ratio+'.input2X')

    clamp = cmds.createNode('clamp', n=node_prefix+'_CLM')
    cmds.setAttr(clamp+'.minR', 0.0)
    cmds.setAttr(clamp+'.maxR', 1.0)
    cmds.connectAttr(ratio+'.outputX', clamp+'.inputR')

    blend = cmds.createNode('blendTwoAttr', n=node_prefix+'_BTA')
    cmds.connectAttr(start_ctrl+'.Twist', blend+'.input[0]')
    cmds.connectAttr(end_ctrl+'.Twist', blend+'.input[1]')
    cmds.connectAttr(clamp+'.outputR', blend+'.attributesBlender')

    return blend+'.output'


def _build_volume_controls(name, curve, axis, num_volume, ctl_grp, ctrl_radius):
    """curve 위 고정 위치(0~1 균등)에 Volume attribute를 하나씩 가진 컨트롤
    num_volume개를 만든다. 인접 두 컨트롤 사이를 선형보간해서 Skin joint의
    scaleY/Z(aim축과 수직인 두 축)에 연결하면 구간별 squash/stretch 볼륨
    보정이 된다.
    """
    up_vector = _PERP_AXIS[axis]
    positions = [i/float(num_volume-1) for i in range(num_volume)] if num_volume > 1 else [0.0]
    ctrls = []
    for i, frac in enumerate(positions):
        pos, rot = _sample_curve_frame(curve, frac, up_vector)
        ctrl = cmds.circle(n='{}_Volume{:02d}_CTL'.format(name, i+1), ch=False,
                            nr=(1, 0, 0), r=ctrl_radius*1.15)[0]
        off = cmds.group(ctrl, n='{}_Volume{:02d}_OFF'.format(name, i+1))
        cmds.xform(off, ws=True, t=pos, ro=rot)
        cmds.setAttr(ctrl+'.overrideEnabled', 1)
        cmds.setAttr(ctrl+'.overrideColor', 14)
        cmds.addAttr(ctrl, ln='Volume', at='double', min=-10, max=10, dv=0, k=True)
        cmds.parent(off, ctl_grp)
        ctrls.append(ctrl)
    return ctrls, positions


def _apply_volume_scale(name, skin_jnts, volume_ctrls, positions):
    """Volume 컨트롤 값(-10~10)을 /10으로 정규화해서 1+delta 형태의 scale로
    만들고, Skin joint의 scaleY/Z에 연결한다(aim축인 scaleX는 그대로 둔다 --
    길이 방향까지 스케일하면 stretch 계산과 겹쳐서 이중으로 늘어난다).
    """
    num = len(skin_jnts)
    for i, jnt in enumerate(skin_jnts):
        t = i/float(num-1) if num > 1 else 0.0
        vol_plug = _gradient_plug(volume_ctrls, 'Volume', positions, t,
                                   '{}_Skin{:02d}_volume'.format(name, i+1))
        norm = cmds.createNode('multDoubleLinear', n='{}_Skin{:02d}_volumeNorm_MDL'.format(name, i+1))
        cmds.setAttr(norm+'.input2', 0.1)
        cmds.connectAttr(vol_plug, norm+'.input1')
        scale = cmds.createNode('addDoubleLinear', n='{}_Skin{:02d}_volumeScale_ADL'.format(name, i+1))
        cmds.setAttr(scale+'.input1', 1.0)
        cmds.connectAttr(norm+'.output', scale+'.input2')
        cmds.connectAttr(scale+'.output', jnt+'.scaleY')
        cmds.connectAttr(scale+'.output', jnt+'.scaleZ')


def build_twist_scale(name='tentacle', num_volume=5, ctrl_radius=0.8):
    """5단계: Twist 시작/끝 컨트롤 2개를 만들어 FK 체인에 그라디언트로 가산하고
    (FK/Skin을 twist_ctrls와 함께 재빌드), Volume 컨트롤 num_volume개를 만들어
    최종 Skin joint의 scaleY/Z에 구간별 볼륨 그라디언트로 연결한다.

    build_output()/build_fk()가 먼저 실행되어 있어야 한다. FK 체인은 Twist를
    얹기 위해 build_fk()를 내부적으로 다시 호출해서 재빌드한다(fk_ctrls의
    로컬 회전 등 그 사이 애니메이터가 손댄 값은 다시 0으로 초기화됨 -- 리그
    구성 단계이므로 문제 없음).

    Arguments:
        name (str): 이전 단계와 동일한 리그 네이밍 프리픽스
        num_volume (int): Volume 컨트롤 개수(참조 리그와 동일하게 기본 5)
        ctrl_radius (float): build_fk()에 그대로 전달할 FK 컨트롤 shape 반경

    Returns:
        dict: twist_ctrls, volume_ctrls, fk_ctrls, skin_jnts
    """
    rig_grp = '{}_rig_GRP'.format(name)
    curve = '{}_CRV'.format(name)
    follicles = cmds.ls('{}_output*_FOL'.format(name))
    if not cmds.objExists(rig_grp) or not cmds.objExists(curve) or not follicles:
        raise RuntimeError('build_twist_scale: build_output()을 먼저 실행하세요 ({} 없음)'.format(rig_grp))

    axis = cmds.getAttr(rig_grp+'.tentacleAxis')

    twist_grp_name = '{}_twistCtl_GRP'.format(name)
    volume_grp_name = '{}_volumeCtl_GRP'.format(name)
    for grp_name in (twist_grp_name, volume_grp_name):
        if cmds.objExists(grp_name):
            cmds.delete(grp_name)

    twist_grp = cmds.createNode('transform', n=twist_grp_name, p=rig_grp)
    volume_grp = cmds.createNode('transform', n=volume_grp_name, p=rig_grp)

    twist_ctrls = _build_twist_controls(name, curve, axis, twist_grp, ctrl_radius)
    volume_ctrls, positions = _build_volume_controls(name, curve, axis, num_volume, volume_grp, ctrl_radius)

    fk_result = build_fk(name=name, ctrl_radius=ctrl_radius, twist_ctrls=twist_ctrls)
    _apply_volume_scale(name, fk_result['skin_jnts'], volume_ctrls, positions)

    print('=' * 60)
    print('Tentacle Ribbon Twist/Volume 완료: {}'.format(name))
    print('  twist ctrls  : {}'.format(twist_ctrls))
    print('  volume ctrls : {}'.format(len(volume_ctrls)))
    print('=' * 60)
    return {'twist_ctrls': twist_ctrls, 'volume_ctrls': volume_ctrls,
            'fk_ctrls': fk_result['fk_ctrls'], 'skin_jnts': fk_result['skin_jnts']}


def _build_top_fk_ik_controls(name, curve, axis, num_ctrl, fk_radius, ik_radius, ctl_grp):
    """curve 위에 FK 컨트롤 num_ctrl개를 실제 체인(FK{i}_OFF가 FK{i-1}_CTL의
    자식)으로 쌓고, 각 FK_CTL의 자식으로 IK 컨트롤을 하나씩 둔다 -- FK가
    상위/마스터(체인이라 앞쪽 FK를 돌리면 뒤쪽 전체가 같이 딸려온다, 일반적인
    FK 체인과 동일), IK가 그 밑에서 로컬로 미세 조정하는 하위 레이어(TOP
    전용 하이라키, Demo의 FK-follows-IK-via-follicle 구조와는 반대 방향).
    IK 컨트롤의 최종 world pose(부모 FK 체인 전체의 누적 포즈 + 자기 로컬
    오프셋의 합)가 NurbsBind joint를 구동해서 표면을 스킨한다.
    """
    up_vector = _PERP_AXIS[axis]
    fk_ctrls, ik_ctrls = [], []
    parent_node = ctl_grp
    for i in range(num_ctrl):
        frac = i/float(num_ctrl-1) if num_ctrl > 1 else 0.0
        idx = i+1
        pos, rot = _sample_curve_frame(curve, frac, up_vector)

        fk_ctrl = cmds.circle(n='{}_FK{:02d}_CTL'.format(name, idx), ch=False, nr=(1, 0, 0), r=fk_radius)[0]
        fk_off = cmds.group(fk_ctrl, n='{}_FK{:02d}_OFF'.format(name, idx))
        cmds.xform(fk_off, ws=True, t=pos, ro=rot)
        cmds.setAttr(fk_ctrl+'.overrideEnabled', 1)
        cmds.setAttr(fk_ctrl+'.overrideColor', 6)
        cmds.parent(fk_off, parent_node)

        ik_ctrl = cmds.circle(n='{}_IK{:02d}_CTL'.format(name, idx), ch=False, nr=(1, 0, 0), r=ik_radius)[0]
        cmds.setAttr(ik_ctrl+'.overrideEnabled', 1)
        cmds.setAttr(ik_ctrl+'.overrideColor', 17)
        cmds.parent(ik_ctrl, fk_ctrl)
        cmds.setAttr(ik_ctrl+'.translate', 0, 0, 0)
        cmds.setAttr(ik_ctrl+'.rotate', 0, 0, 0)

        fk_ctrls.append(fk_ctrl)
        ik_ctrls.append(ik_ctrl)
        parent_node = fk_ctrl

    return fk_ctrls, ik_ctrls


def _build_master_drive_follicles(branch_name, top_curve, top_surface, main_ik_offsets, sys_grp):
    """top_surface(TOP의 FK/IK로 변형된 서피스) 위에 main_ik_offsets와 같은
    개수의 follicle을, main_ik_offsets가 원래 만들어진 것과 동일한 방식
    (motionPath arc-length fraction -> closestPointOnSurface, _build_output_follicles
    참고)으로 배치한다 -- 서피스의 raw parameterU를 그 fraction 값으로 직접
    쓰면 안 된다(surface parameter는 arc length와 선형 관계가 아니라서, 원래
    main IK가 커브의 arc-length 기준으로 배치된 위치와 다른 지점을 가리키게
    된다). top_curve(TOP 서피스에서 추출한 curve)를 통해 정확한 arc-length
    위치를 구하고, 그 위치를 closestPointOnSurface로 서피스의 실제 U로
    변환해야 rest 상태에서 main_ik_offsets 위치가 그대로 유지된다.

    follicle의 outTranslate/outRotate로 main_ik_offsets를 직접 구동한다 --
    main의 IK_CTL 자신은 그 OFF의 자식으로 그대로 남아 애니메이터가 그
    위에 추가로 움직일 수 있다(FK NUL/CTL과 동일한 패턴). 결과적으로 TOP을
    움직이면 그 서피스 변형이 follicle을 통해 그대로 main(Demo)의 IK
    컨트롤 위치/방향을 구동하는 마스터-슬레이브 관계가 된다.
    """
    crv_shape = cmds.listRelatives(top_curve, shapes=True, ni=True, fullPath=True)[0]
    surf_shape = cmds.listRelatives(top_surface, shapes=True, ni=True, fullPath=True)[0]
    num = len(main_ik_offsets)
    fols = []
    for i, off in enumerate(main_ik_offsets):
        frac = i/float(num-1) if num > 1 else 0.0
        idx = i+1

        mp = cmds.createNode('motionPath', n='{}_drive{:02d}_MPT'.format(branch_name, idx))
        cmds.connectAttr(crv_shape+'.worldSpace[0]', mp+'.geometryPath')
        cmds.setAttr(mp+'.fractionMode', 1)
        cmds.setAttr(mp+'.uValue', frac)

        cps = cmds.createNode('closestPointOnSurface', n='{}_drive{:02d}_CPS'.format(branch_name, idx))
        cmds.connectAttr(surf_shape+'.worldSpace[0]', cps+'.inputSurface')
        cmds.connectAttr(mp+'.allCoordinates', cps+'.inPosition')

        fol_shape = cmds.createNode('follicle', n='{}_drive{:02d}_FOLShape'.format(branch_name, idx))
        fol_xform = cmds.listRelatives(fol_shape, parent=True)[0]
        fol_xform = cmds.rename(fol_xform, '{}_drive{:02d}_FOL'.format(branch_name, idx))
        cmds.connectAttr(surf_shape+'.local', fol_shape+'.inputSurface')
        cmds.connectAttr(surf_shape+'.worldMatrix[0]', fol_shape+'.inputWorldMatrix')
        cmds.connectAttr(cps+'.parameterU', fol_shape+'.parameterU')
        cmds.setAttr(fol_shape+'.parameterV', 0.5)
        cmds.connectAttr(fol_shape+'.outTranslate', off+'.translate')
        cmds.connectAttr(fol_shape+'.outRotate', off+'.rotate')
        cmds.parent(fol_xform, sys_grp)
        fols.append(fol_xform)
    return fols


def build_branch(name='tentacle', branch_name='topTentacle', num_ctrl=4, fk_radius=0.9, ik_radius=0.6):
    """{branch_name}(TOP)을 {name}(Demo)을 구동하는 마스터 컨트롤 레이어로
    빌드한다.

    구조:
        1. {name}_NSF를 duplicate해서 {branch_name}_NSF를 만든다(모양/
           parametrization 그대로 복제).
        2. 그 복제 서피스에서 curve를 재추출하고 restCurveLength를 저장한다
           -- build_base()의 3~4번과 동일.
        3. curve 위에 FK 컨트롤 num_ctrl개 -> 그 자식으로 IK 컨트롤을
           하나씩 둔다(IK가 FK 하위 -- FK가 큰 포즈, IK가 로컬 미세조정).
           그 IK 컨트롤들이 1:1 parentConstraint로 구동하는 NurbsBind
           joint로 {branch_name}_NSF를 스킨 바인드한다.
        4. {branch_name}_NSF(이제 TOP의 FK/IK로 변형된 상태) 위에, {name}의
           IK 컨트롤 개수와 동일한 개수의 follicle을 {name} IK 컨트롤과
           같은 arc-length 위치에 만들고, 그 출력으로 {name}의 IK_OFF를
           직접 구동한다 -- TOP을 움직이면 그 서피스 변형이 follicle을
           통해 그대로 Demo의 IK 컨트롤 위치/방향을 구동한다.

    build_base()/build_ik()가 메인 리그(name)에 대해 먼저 실행되어 있어야
    한다(복제할 {name}_NSF와 follicle을 연결할 {name}의 IK_OFF들이 있어야
    하므로).

    Arguments:
        name (str): 메인(Demo) 리그 네이밍 프리픽스
        branch_name (str): 마스터(TOP) 컨트롤 레이어 네이밍 프리픽스
        num_ctrl (int): TOP 자신의 FK/IK 컨트롤 개수(둘 다 동일, Demo의 IK
            개수보다 적어도 됨 -- 굵은 마스터 컨트롤)
        fk_radius (float): TOP FK 컨트롤 shape 반경
        ik_radius (float): TOP IK 컨트롤 shape 반경(FK 자식이라 보통 더 작게)

    Returns:
        dict: surface, curve, fk_ctrls, ik_ctrls, drive_follicles
    """
    main_surface = '{}_NSF'.format(name)
    main_rig_grp = '{}_rig_GRP'.format(name)
    if not cmds.objExists(main_surface) or not cmds.objExists(main_rig_grp):
        raise RuntimeError('build_branch: {} build_base()를 먼저 실행하세요'.format(name))

    main_ik_ctrls = sorted(cmds.ls('{}_IK*_CTL'.format(name)))
    if not main_ik_ctrls:
        raise RuntimeError('build_branch: {} build_ik()를 먼저 실행하세요 (IK 컨트롤 없음)'.format(name))
    main_ik_offsets = ['{}_IK{:02d}_OFF'.format(name, i+1) for i in range(len(main_ik_ctrls))]

    if cmds.objExists('{}_rig_GRP'.format(branch_name)):
        cmds.delete('{}_rig_GRP'.format(branch_name))

    axis = cmds.getAttr(main_rig_grp+'.tentacleAxis')
    g = _build_groups(branch_name)
    cmds.addAttr(g['rig'], ln='tentacleAxis', dt='string')
    cmds.setAttr(g['rig']+'.tentacleAxis', axis, type='string')
    cmds.parent(g['rig'], main_rig_grp)

    surface = cmds.duplicate(main_surface, n='{}_NSF'.format(branch_name), renameChildren=True)[0]
    cmds.parent(surface, g['geo'])

    out_crv = _extract_curve_from_surface(branch_name, surface)
    cmds.parent(out_crv, g['geo'])
    rest_length = _store_rest_length(out_crv)

    ctl_grp = cmds.createNode('transform', n='{}_ctl_GRP'.format(branch_name), p=g['rig'])
    jnt_grp = cmds.createNode('transform', n='{}_bindJnt_GRP'.format(branch_name), p=g['sys'])

    fk_ctrls, ik_ctrls = _build_top_fk_ik_controls(branch_name, out_crv, axis, num_ctrl,
                                                     fk_radius, ik_radius, ctl_grp)
    bind_jnts = _build_nurbs_bind_joints(branch_name, ik_ctrls, ik_ctrls, jnt_grp)
    skin = _skin_ribbon_surface(branch_name, surface, bind_jnts)

    drive_fols = _build_master_drive_follicles(branch_name, out_crv, surface, main_ik_offsets, g['sys'])

    print('=' * 60)
    print('Tentacle Branch(master) 완료: {} -> {} 구동'.format(branch_name, name))
    print('  surface         : {}'.format(surface))
    print('  curve           : {}'.format(out_crv))
    print('  fk ctrls        : {}'.format(len(fk_ctrls)))
    print('  ik ctrls        : {}'.format(len(ik_ctrls)))
    print('  drive follicles : {}'.format(len(drive_fols)))
    print('=' * 60)
    return {'surface': surface, 'curve': out_crv, 'fk_ctrls': fk_ctrls, 'ik_ctrls': ik_ctrls,
            'drive_follicles': drive_fols}


if __name__ == '__main__':
    build_base()
    build_ik()
    build_output()
    build_fk()
    build_twist_scale()
    build_branch()
