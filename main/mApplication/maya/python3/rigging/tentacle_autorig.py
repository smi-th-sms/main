# -*- coding: utf-8 -*-
"""============================================================================
촉수(Tentacle) Auto-Rig

curve(오브젝트 실제 vertex 중심선) 기반 IK/FK 하이브리드 리그.

파이프라인:
    1. mesh의 실제 vertex 중심선을 따라가는 base_CRV 생성
    2. base_CRV를 복사해 ik_CRV 생성, 적은 개수의 자유 이동 IK 컨트롤(hidden
       skin joint)로 skinCluster 구동 -- weight는 자동 dropoff 대신 파라미터
       기준 선형(tent) falloff로 직접 계산해서 설정한다(influence 개수/간격이
       바뀌어도 항상 예측 가능하게 부드럽게 분배됨). Stretch/Squash/Slide
       attribute는 별도 Settings 노드 없이 마지막 IK 컨트롤러 위에 둔다
    3. base_CRV 위에 motionPath 기반 null(위치만) 생성. attr_ctrl.Slide로
       전체 null 체인이 curve를 따라 미끄러질 수 있게 함
    4. ik_CRV를 따라가는 splineIK joint 체인 생성 -- Advanced Twist를 시작/끝
       IK 컨트롤의 회전에 연결. rest 상태에 남는 잔여 rotate는 jointOrient에
       구워서 rotate가 항상 0에서 시작하도록 정리. 이 체인에 Stretch(세그먼트
       translateX)/자체 Squash(scaleY/Z, 전역 게이트만) 적용
    5. 이 splineIK 체인과 정확히 같은 개수/위치에 FK 컨트롤(real DAG 하이라키)을
       생성 -- CTL_OFF(translate) -> OrientOff(jointOrient) -> ConnOff(rotate)
       순서를 ik 조인트와 동일하게 복제해서 위치+회전이 항상 IK 체인과 일치
       하게 만듦
    6. FK 조인트들로 base_CRV를 skinCluster 바인드(마찬가지로 dropoff 낮춤)
    7. null의 twist 참조를 공유 up-vector 대신 가장 가까운 FK 컨트롤 두 개의
       world rotation을 보간해서 얻음 -- 참조가 항상 국지적이라 커브가 크게
       휘어도 플립 위험이 훨씬 적음
    8. null 밑에 최종 BIND_JNT 생성. base_CRV 위를 파라미터로 움직이는
       SquashStart/End 컨트롤러 2개(Parameter+Volume attribute)를 만들어,
       그 구간에 속하는 BIND_JNT의 squash 볼륨을 start~end로 보간(구간 밖은
       가장 가까운 끝 값으로 고정)하고 attr_ctrl.Squash를 전역 게이트로 곱해
       BIND_JNT의 scaleY/Z에 적용 -- FK_JNT에는 더 이상 squash를 걸지 않음

:Example:
    from python3.rigging import tentacle_autorig
    import importlib
    importlib.reload(tentacle_autorig)
    tentacle_autorig.build_tentacle_rig(mesh='pSphere1')
============================================================================"""
import maya.cmds as cmds


def _sample_params(num_points, include_tip=True):
    """0~1 사이 균등 분배된 파라미터 리스트.
    include_tip=True면 끝점(t=1)까지 포함(num_points-1로 나눔).
    include_tip=False면 끝점을 만들지 않고 그 앞까지만 균등 분배한다
    (num_points로 나눔) -- 마지막 컨트롤이 curve의 맨 끝에 생기지 않게 하는 용도.
    """
    if num_points <= 1:
        return [0.0]
    denom = float(num_points-1) if include_tip else float(num_points)
    return [i/denom for i in range(num_points)]


def _sample_curve_points_at(curve, params):
    """curve 위에서 명시적으로 주어진 파라미터(params) 리스트 위치의
    world position을 샘플링한다 (임시 motionPath를 만들어 쓰고 바로 지운다).
    """
    shape = cmds.listRelatives(curve, shapes=True, ni=True, fullPath=True)[0]
    tmp_mp = cmds.createNode('motionPath', n='__sampleCurve_MP')
    cmds.connectAttr(shape+'.worldSpace[0]', tmp_mp+'.geometryPath')
    cmds.setAttr(tmp_mp+'.fractionMode', 1)
    points = []
    for u in params:
        cmds.setAttr(tmp_mp+'.uValue', u)
        points.append(tuple(cmds.getAttr(tmp_mp+'.allCoordinates')[0]))
    cmds.delete(tmp_mp)
    return points


def _sample_curve_points(curve, num_points, include_tip=True):
    """curve 위에서 arc-length 기준으로 균등 분배된 world position을 샘플링한다."""
    return _sample_curve_points_at(curve, _sample_params(num_points, include_tip))


def _sample_curve_frames(curve, num_points, up_loc, include_tip=True):
    """curve 위에서 arc-length 기준 위치 + tangent 기준 회전을 함께 샘플링한다
    (motionPath follow=1). IK 컨트롤 축을 커브 tangent에 맞추는 데 쓴다.
    """
    shape = cmds.listRelatives(curve, shapes=True, ni=True, fullPath=True)[0]
    tmp_mp = cmds.createNode('motionPath', n='__sampleCurveFrame_MP')
    cmds.connectAttr(shape+'.worldSpace[0]', tmp_mp+'.geometryPath')
    cmds.setAttr(tmp_mp+'.fractionMode', 1)
    cmds.setAttr(tmp_mp+'.follow', 1)
    cmds.setAttr(tmp_mp+'.frontAxis', 0)
    cmds.setAttr(tmp_mp+'.upAxis', 1)
    cmds.setAttr(tmp_mp+'.worldUpType', 2)
    cmds.connectAttr(up_loc+'.worldMatrix[0]', tmp_mp+'.worldUpMatrix')
    frames = []
    for u in _sample_params(num_points, include_tip):
        cmds.setAttr(tmp_mp+'.uValue', u)
        pos = tuple(cmds.getAttr(tmp_mp+'.allCoordinates')[0])
        rot = tuple(cmds.getAttr(tmp_mp+'.rotate')[0])
        frames.append((pos, rot))
    cmds.delete(tmp_mp)
    return frames


def _get_axis_endpoints(mesh, axis='y'):
    """mesh의 world bounding box 중심을 지나는 축(base->tip 방향)의 양 끝점을 구한다.

    axis를 명시하면 그 축을 그대로 쓰고(기본값 'y'), None을 주면 가장 긴
    축을 자동 감지한다. 나머지 두 축은 항상 bounding box 중심(오브젝트
    중심)에 고정된다.
    """
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


def _build_groups(name):
    g = {}
    g['rig'] = cmds.createNode('transform', n='{}_rig_GRP'.format(name))
    g['crv'] = cmds.createNode('transform', n='{}_CRV_GRP'.format(name), p=g['rig'])
    g['ctl'] = cmds.createNode('transform', n='{}_CTL_GRP'.format(name), p=g['rig'])
    g['fk_ctl'] = cmds.createNode('transform', n='{}_FK_CTL_GRP'.format(name), p=g['ctl'])
    g['ik_ctl'] = cmds.createNode('transform', n='{}_IK_CTL_GRP'.format(name), p=g['ctl'])
    g['null'] = cmds.createNode('transform', n='{}_NULL_GRP'.format(name), p=g['rig'])
    g['jnt'] = cmds.createNode('transform', n='{}_JNT_GRP'.format(name), p=g['rig'])
    g['sys'] = cmds.createNode('transform', n='{}_SYS_GRP'.format(name), p=g['rig'])
    cmds.setAttr('{}.visibility'.format(g['sys']), 0)
    return g


def _get_centerline_points(mesh, axis, base, tip, num_points):
    """오브젝트의 실제 vertex들을 axis 방향으로 얇게 슬라이스해서 각 슬라이스의
    centroid를 이어 만든 포인트 리스트.

    bounding box 중심을 지나는 직선이 아니라, 메쉬가 휘거나 비대칭이어도
    실제 vertex 분포의 중심을 따라가게 만든다. axis 좌표는 base->tip 사이
    균등분배를 유지하고, 나머지 두 좌표만 그 지점 근처 vertex들의 평균으로
    잡는다.
    """
    idx = {'x': 0, 'y': 1, 'z': 2}[axis]
    flat = cmds.xform('{}.vtx[*]'.format(mesh), q=True, ws=True, t=True)
    verts = [(flat[i], flat[i+1], flat[i+2]) for i in range(0, len(flat), 3)]

    lo, hi = base[idx], tip[idx]
    span = hi - lo
    half_band = (span/float(num_points-1))*0.75 if num_points > 1 and span else abs(span) or 1.0

    points = []
    for i in range(num_points):
        t = i/float(num_points-1)
        target = lo + span*t
        bucket = [v for v in verts if abs(v[idx]-target) <= half_band]
        if not bucket:
            bucket = sorted(verts, key=lambda v: abs(v[idx]-target))[:max(3, len(verts)//num_points)]
        centroid = [sum(v[a] for v in bucket)/len(bucket) for a in range(3)]
        centroid[idx] = target
        points.append(tuple(centroid))
    return points


def _build_base_curve(name, mesh, axis, base, tip, num_cv, crv_grp):
    """base->tip 사이, 오브젝트의 실제 중심선(centerline)을 따라가는 degree-3 커브 생성."""
    positions = _get_centerline_points(mesh, axis, base, tip, num_cv)
    crv = cmds.curve(n='{}_base_CRV'.format(name), d=3, p=positions)
    cmds.rebuildCurve(crv, ch=False, rpo=True, rt=0, end=1, kr=0, kcp=1,
                       kep=1, kt=0, s=len(positions)-3, d=3)
    cmds.parent(crv, crv_grp)
    shape = cmds.listRelatives(crv, shapes=True, fullPath=True)[0]
    return crv, shape


def _build_up_vector(name, sys_grp, axis, base):
    """IK 컨트롤 tangent 프레임 샘플링용 Object Rotation Up 참조 로케이터.

    up_loc의 로컬 Y축(회전 안 시키면 world Y)이 곧 up-reference 방향이 된다.
    이게 curve의 tangent 방향(=axis)과 평행해지면 forward/up이 겹치는
    특이점(singularity)이 생기므로, axis=='y'일 때만 90도 틸트해서 참조
    방향을 Z로 돌려 평행을 피한다.
    """
    up_off = cmds.createNode('transform', n='{}_up_OFF'.format(name), p=sys_grp)
    up_loc = cmds.spaceLocator(n='{}_up_LOC'.format(name))[0]
    cmds.parent(up_loc, up_off)
    cmds.xform(up_off, ws=True, t=base)
    cmds.move(5, 0, 0, up_loc, r=True, os=True)
    if axis == 'y':
        cmds.setAttr(up_loc+'.rotateX', 90)
    return up_loc


def _build_mp_nulls(name, num_nulls, base_shape, null_grp):
    """base_CRV 위에 균등 분배된 motionPath 기반 null 생성 (위치만).

    회전은 여기서 만들지 않는다 -- FK 컨트롤이 아직 없어서 나중에
    _build_null_rotation_from_fk에서 FK world rotation을 보간해 얻는다.
    """
    mps, nulls = [], []
    for i in range(num_nulls):
        u = i/float(num_nulls-1)
        mp = cmds.createNode('motionPath', n='{}_{:02d}_MP'.format(name, i))
        cmds.connectAttr(base_shape+'.worldSpace[0]', mp+'.geometryPath')
        cmds.setAttr(mp+'.uValue', u)
        cmds.setAttr(mp+'.fractionMode', 1)

        null = cmds.createNode('transform', n='{}_{:02d}_NULL'.format(name, i), p=null_grp)
        cmds.connectAttr(mp+'.allCoordinates', null+'.translate')

        mps.append(mp)
        nulls.append(null)
    return mps, nulls


def _build_slide(name, mps, attr_ctrl):
    """attr_ctrl.Slide(-10~10)를 모든 motionPath의 uValue에 더해서 전체 null
    체인이 curve를 따라 미끄러지게 한다. Stretch/Squash가 0~10 입력을 /10으로
    0~1 게이트로 정규화하는 것과 동일한 컨벤션으로, Slide도 /10해서 기존과
    동일한 -1~1 이동 범위를 유지한다. clamp(0,1)로 curve 끝을 넘지 않게 고정.
    """
    slide_norm = cmds.createNode('multDoubleLinear', n='{}_slideNorm_MDL'.format(name))
    cmds.setAttr(slide_norm+'.input2', 0.1)
    cmds.connectAttr(attr_ctrl+'.Slide', slide_norm+'.input1')

    for i, mp in enumerate(mps):
        base_u = cmds.getAttr(mp+'.uValue')
        add = cmds.createNode('plusMinusAverage', n='{}_slide{:02d}_PMA'.format(name, i))
        cmds.setAttr(add+'.input1D[0]', base_u)
        cmds.connectAttr(slide_norm+'.output', add+'.input1D[1]')
        clamp = cmds.createNode('clamp', n='{}_slide{:02d}_CLAMP'.format(name, i))
        cmds.setAttr(clamp+'.minR', 0)
        cmds.setAttr(clamp+'.maxR', 1)
        cmds.connectAttr(add+'.output1D', clamp+'.inputR')
        cmds.connectAttr(clamp+'.outputR', mp+'.uValue', f=True)


def _add_rig_attrs(ctrl):
    """Stretch/Squash/Slide attribute를 주어진 컨트롤(마지막 IK 컨트롤러)에 추가한다.
    Settings_CTL 같은 별도 허브 노드 없이, 늘 존재하는 마지막 IK 컨트롤러 위에 둔다.
    """
    cmds.addAttr(ctrl, ln='Stretch', at='double', min=0, max=10, dv=0, k=True)
    cmds.addAttr(ctrl, ln='Squash', at='double', min=0, max=10, dv=0, k=True)
    cmds.addAttr(ctrl, ln='Slide', at='double', min=-10, max=10, dv=0, k=True)


def _make_ctrl(n, radius, pos, rot=None, normal=(0, 1, 0)):
    ctrl = cmds.circle(n=n, r=radius, nr=normal, ch=False)[0]
    off = cmds.createNode('transform', n='{}_OFF'.format(n))
    cmds.parent(ctrl, off)
    cmds.xform(off, ws=True, t=pos)
    if rot is not None:
        cmds.xform(off, ws=True, ro=rot)
    return ctrl, off


def _build_ik_curve(name, crv_grp, base_crv):
    """base_CRV를 복사해서 IK 구동용 curve를 만든다."""
    ik_crv = cmds.duplicate(base_crv, n='{}_ik_CRV'.format(name))[0]
    current_parent = cmds.listRelatives(ik_crv, parent=True, fullPath=True) or []
    target_parent = cmds.ls(crv_grp, long=True)[0]
    if not current_parent or current_parent[0] != target_parent:
        cmds.parent(ik_crv, crv_grp)
    return ik_crv


def _build_stretch_ratio(name, ik_crv, attr_ctrl):
    """ik_CRV의 rest 대비 현재 arc length 비율(ratio_plug)과, attr_ctrl의 Stretch/
    Squash를 0~1 게이트로 바꾼 값(stretch_gate_plug/squash_gate_plug)을 만든다.
    """
    rest_length = cmds.arclen(ik_crv)
    ik_shape = cmds.listRelatives(ik_crv, shapes=True, ni=True, fullPath=True)[0]

    curve_info = cmds.createNode('curveInfo', n='{}_ikStretch_CI'.format(name))
    cmds.connectAttr(ik_shape+'.worldSpace[0]', curve_info+'.inputCurve')

    ratio_md = cmds.createNode('multiplyDivide', n='{}_stretchRatio_MD'.format(name))
    cmds.setAttr(ratio_md+'.operation', 2)  # divide
    cmds.connectAttr(curve_info+'.arcLength', ratio_md+'.input1X')
    cmds.setAttr(ratio_md+'.input2X', rest_length)

    stretch_gate = cmds.createNode('multDoubleLinear', n='{}_stretchGate_MDL'.format(name))
    cmds.setAttr(stretch_gate+'.input2', 0.1)
    cmds.connectAttr(attr_ctrl+'.Stretch', stretch_gate+'.input1')

    squash_gate = cmds.createNode('multDoubleLinear', n='{}_squashGate_MDL'.format(name))
    cmds.setAttr(squash_gate+'.input2', 0.1)
    cmds.connectAttr(attr_ctrl+'.Squash', squash_gate+'.input1')

    return ratio_md+'.outputX', stretch_gate+'.output', squash_gate+'.output'


def _apply_linear_skin_weights(skin, geo, num_cv, influences):
    """CV의 파라미터 위치(index/CV개수 기준 균등분배) 대비 influence의
    파라미터 위치(_sample_params와 동일 컨벤션) 사이 거리로 선형(tent)
    falloff weight를 직접 계산해서 skinPercent로 설정한다.

    skinCluster의 자동 smooth bind(dropoff 기반)는 influence 개수/간격이
    바뀌면 같은 dropoff 값이라도 실제 퍼지는 폭이 달라진다 -- influence가
    늘어나 서로 가까워지면 dropoff는 그대로인데 간격만 좁아져서 각 CV가
    가장 가까운 influence 쪽으로 더 뾰족하게 몰린다(예: num_ik_ctrls=2일 때는
    끝에서 끝까지 완전히 선형으로 퍼졌지만 4로 늘리면 중간 influence들이
    80% 넘게 뾰족해짐). influence 파라미터 간격에 맞춰 매번 새로 계산되는
    이 방식은 개수와 무관하게 항상 CV 사이가 끊김 없이 선형으로 블렌드된다.
    """
    params = _sample_params(num_cv, include_tip=True)
    inf_params = _sample_params(len(influences), include_tip=True)
    spacing = (inf_params[1]-inf_params[0]) if len(inf_params) > 1 else 1.0

    for i, u in enumerate(params):
        weights = [max(0.0, 1.0 - abs(u-up)/spacing) if spacing else 1.0 for up in inf_params]
        total = sum(weights)
        if total <= 0:
            closest = min(range(len(inf_params)), key=lambda j: abs(inf_params[j]-u))
            weights = [0.0]*len(inf_params)
            weights[closest] = 1.0
        else:
            weights = [w/total for w in weights]
        cmds.skinPercent(skin, '{}.cv[{}]'.format(geo, i),
                          transformValue=list(zip(influences, weights)))


def _build_ik_setup(name, num_ik_ctrls, ik_ctl_grp, ik_crv, up_loc):
    """IK 컨트롤은 서로 독립(부모관계 없음), 숨은 joint를 ik_CRV에 skinCluster로
    묶어서 자유 이동으로 curve 모양을 직접 조형한다. 위치/축은 ik_CRV 위에서
    직접 샘플링해서(FK/ikSpline 조인트와 동일한 tangent 프레임 컨벤션) 실제
    curve 모양과 방향을 그대로 따라가게 만든다.

    weight는 _apply_linear_skin_weights로 직접 설정한다 -- IK 컨트롤 개수가
    바뀌어도 항상 예측 가능하게 부드럽게 퍼진다.
    """
    frames = _sample_curve_frames(ik_crv, num_ik_ctrls, up_loc)
    ik_ctrls, ik_jnts = [], []
    for i, (pos, rot) in enumerate(frames):
        c, off = _make_ctrl('{}_IK{:02d}_CTL'.format(name, i), 1.6, pos, rot=rot)
        cmds.setAttr(c+'.overrideEnabled', 1)
        cmds.setAttr(c+'.overrideColor', 13)
        cmds.parent(off, ik_ctl_grp)

        cmds.select(cl=True)
        jnt = cmds.joint(n='{}_IK{:02d}_JNT'.format(name, i))
        cmds.setAttr(jnt+'.visibility', 0)
        cmds.parent(jnt, c)
        cmds.setAttr(jnt+'.translate', 0, 0, 0)
        cmds.setAttr(jnt+'.rotate', 0, 0, 0)
        # cmds.parent가 world 유지를 위해 rotate 대신 jointOrient에 보정값을
        # 구워 넣는 경우가 있다 -- 명시적으로 0으로 되돌려야 이 joint의 축이
        # IK 컨트롤과 완전히 같아진다 (안 그러면 skinCluster가 트위스트를
        # 엉뚱한 축 기준으로 적용하게 됨).
        cmds.setAttr(jnt+'.jointOrient', 0, 0, 0)

        ik_ctrls.append(c)
        ik_jnts.append(jnt)

    skin = cmds.skinCluster(ik_jnts + [ik_crv], n='{}_ik_SKIN'.format(name),
                             tsb=True, bm=0, sm=0, nw=1, mi=4, dr=1.0)[0]
    ik_shape = cmds.listRelatives(ik_crv, shapes=True, ni=True, fullPath=True)[0]
    num_cv = len(cmds.getAttr(ik_shape+'.cp[*]'))
    _apply_linear_skin_weights(skin, ik_crv, num_cv, ik_jnts)
    return ik_ctrls, ik_jnts


def _build_ik_spline_chain(name, num_jnts, ik_crv, ik_ctrls, jnt_grp, sys_grp,
                            ratio_plug, stretch_gate_plug, squash_gate_plug):
    """ik_CRV를 따라가는 splineIK joint 체인(num_jnts개, curve 양 끝 포함
    균등분배) + Advanced Twist(시작/끝 IK 컨트롤 회전 참조) + Stretch/Squash.

    ikHandle을 만들면 rest 상태에서도(orientJoint 컨벤션과 splineIK 솔버가
    실제로 요구하는 방향이 약간 어긋나서) 각 조인트에 크고 어색한 rotate
    값이 남는다. makeIdentity(rotate=True)로 그 값을 jointOrient에 구워서
    rotate가 항상 0에서 시작하도록 정리한다 (rotate=True만 -- jointOrient
    플래그를 같이 주면 반대로 jointOrient가 0이 되고 rotate가 커진다).

    조인트 체인은 SYS_GRP(숨김) 대신 jnt_grp(보이는 그룹)에 둔다.
    """
    positions = _sample_curve_points(ik_crv, num_jnts, include_tip=True)
    cmds.select(cl=True)
    jnts = []
    for i, pos in enumerate(positions):
        cmds.select(cl=True)
        j = cmds.joint(n='{}_ik{:02d}_JNT'.format(name, i), p=pos)
        jnts.append(j)
    for i in range(1, len(jnts)):
        cmds.parent(jnts[i], jnts[i-1])
    cmds.joint(jnts[0], e=True, zso=True, oj='xyz', sao='yup', ch=True)
    cmds.setAttr(jnts[0]+'.visibility', 0)
    cmds.parent(jnts[0], jnt_grp)

    ik_handle = cmds.ikHandle(n='{}_ikSpline_HDL'.format(name), sj=jnts[0], ee=jnts[-1],
                               sol='ikSplineSolver', ccv=False, pcv=False, c=ik_crv)[0]
    cmds.setAttr(ik_handle+'.dTwistControlEnable', 1)
    cmds.setAttr(ik_handle+'.dWorldUpType', 4)  # Object Rotation Up (Start/End)
    cmds.connectAttr(ik_ctrls[0]+'.worldMatrix[0]', ik_handle+'.dWorldUpMatrix')
    cmds.connectAttr(ik_ctrls[-1]+'.worldMatrix[0]', ik_handle+'.dWorldUpMatrixEnd')
    cmds.parent(ik_handle, sys_grp)

    for j in jnts:
        cmds.makeIdentity(j, apply=True, rotate=True, normal=0)

    for i in range(1, len(jnts)):
        rest_tx = cmds.getAttr(jnts[i]+'.translateX')
        stretched_tx = cmds.createNode('multDoubleLinear', n='{}_ik{:02d}_stretchTx_MDL'.format(name, i))
        cmds.setAttr(stretched_tx+'.input1', rest_tx)
        cmds.connectAttr(ratio_plug, stretched_tx+'.input2')
        tx_blend = cmds.createNode('blendTwoAttr', n='{}_ik{:02d}_stretchTx_BTA'.format(name, i))
        cmds.setAttr(tx_blend+'.input[0]', rest_tx)
        cmds.connectAttr(stretched_tx+'.output', tx_blend+'.input[1]')
        cmds.connectAttr(stretch_gate_plug, tx_blend+'.attributesBlender')
        cmds.connectAttr(tx_blend+'.output', jnts[i]+'.translateX', f=True)

    for i, j in enumerate(jnts):
        inv_ratio = cmds.createNode('multiplyDivide', n='{}_ik{:02d}_squashInv_MD'.format(name, i))
        cmds.setAttr(inv_ratio+'.operation', 2)  # divide
        cmds.setAttr(inv_ratio+'.input1X', 1.0)
        cmds.connectAttr(ratio_plug, inv_ratio+'.input2X')
        for axis in ('Y', 'Z'):
            sq_blend = cmds.createNode('blendTwoAttr', n='{}_ik{:02d}_squash{}_BTA'.format(name, i, axis))
            cmds.setAttr(sq_blend+'.input[0]', 1.0)
            cmds.connectAttr(inv_ratio+'.outputX', sq_blend+'.input[1]')
            cmds.connectAttr(squash_gate_plug, sq_blend+'.attributesBlender')
            cmds.connectAttr(sq_blend+'.output', j+'.scale'+axis, f=True)

    return jnts


def _build_fk_setup(name, ik_jnts, fk_ctl_grp):
    """splineIK 체인(ik_jnts)과 정확히 같은 개수/위치에 FK 컨트롤을 real DAG
    하이라키(spine2_.py 방식, 부모-자식)로 생성한다.

    각 레벨은 ik_jnts와 동일한 순서(translate -> jointOrient -> rotate)로
    쌓는다 -- translate가 로컬 오프셋 그대로(parent 기준) 연결되므로,
    jointOrient가 translate보다 먼저 오면 그 오프셋 벡터가 jointOrient만큼
    잘못 회전해서 위치가 틀어진다:

        CTL_OFF (translate = ik_jnts[i].translate, live)
          -> OrientOff (rotate = ik_jnts[i].jointOrient, 정적)
            -> ConnOff (rotate = ik_jnts[i].rotate, live)
              -> CTL (leaf)
                -> JNT (leaf, base_CRV skin influence 전용)

    Squash는 여기(FK_JNT)에 걸지 않는다 -- null 하위의 최종 BIND_JNT
    (_build_null_bind_joints)에서 구간별 볼륨으로 적용한다.
    """
    fk_ctrls, fk_jnts = [], []
    for i, jnt in enumerate(ik_jnts):
        jo = cmds.getAttr(jnt+'.jointOrient')[0]

        off = cmds.createNode('transform', n='{}_FK{:02d}_CTL_OFF'.format(name, i),
                               p=(fk_ctl_grp if i == 0 else fk_ctrls[i-1]))
        cmds.connectAttr(jnt+'.translate', off+'.translate')

        orient_off = cmds.createNode('transform', n='{}_FK{:02d}_OrientOff'.format(name, i), p=off)
        cmds.setAttr(orient_off+'.rotate', jo[0], jo[1], jo[2])

        conn_off = cmds.createNode('transform', n='{}_FK{:02d}_ConnOff'.format(name, i), p=orient_off)
        cmds.connectAttr(jnt+'.rotate', conn_off+'.rotate')

        c = cmds.circle(n='{}_FK{:02d}_CTL'.format(name, i), r=2.2, nr=(0, 1, 0), ch=False)[0]
        cmds.setAttr(c+'.overrideEnabled', 1)
        cmds.setAttr(c+'.overrideColor', 6)
        cmds.parent(c, conn_off)
        cmds.setAttr(c+'.translate', 0, 0, 0)
        cmds.setAttr(c+'.rotate', 0, 0, 0)

        cmds.select(cl=True)
        fk_jnt = cmds.joint(n='{}_FK{:02d}_JNT'.format(name, i))
        cmds.setAttr(fk_jnt+'.visibility', 0)
        cmds.parent(fk_jnt, c)
        cmds.setAttr(fk_jnt+'.translate', 0, 0, 0)
        cmds.setAttr(fk_jnt+'.rotate', 0, 0, 0)
        # cmds.parent가 world 유지를 위해 jointOrient에 보정값을 구워 넣으므로
        # (FK_CTL이 이미 회전돼 있는 상태에서 새 joint를 부모링하면) 명시적으로
        # 0으로 되돌려야 FK_JNT 축이 FK_CTL과 완전히 같아진다.
        cmds.setAttr(fk_jnt+'.jointOrient', 0, 0, 0)

        fk_ctrls.append(c)
        fk_jnts.append(fk_jnt)

    return fk_ctrls, fk_jnts


def _build_fk_skin(name, fk_jnts, base_crv):
    """FK 조인트로 base_CRV를 skinCluster 바인드. weight는
    _apply_linear_skin_weights로 직접 설정해서 FK 개수가 바뀌어도 항상
    예측 가능하게 부드럽게 퍼지게 한다.
    """
    skin = cmds.skinCluster(fk_jnts + [base_crv], n='{}_fk_SKIN'.format(name),
                             tsb=True, bm=0, sm=0, nw=1, mi=4, dr=1.0)[0]
    base_shape = cmds.listRelatives(base_crv, shapes=True, ni=True, fullPath=True)[0]
    num_cv = len(cmds.getAttr(base_shape+'.cp[*]'))
    _apply_linear_skin_weights(skin, base_crv, num_cv, fk_jnts)


def _build_null_rotation_from_fk(name, mps, nulls, num_nulls, fk_ctrls):
    """null의 motionPath follow 회전을 공유 up-vector 대신 가장 가까운 FK
    컨트롤 두 개의 world rotation을 보간해서 얻는다 -- 참조가 항상 국지적
    이라 커브가 크게 휘어도 (공유 up-vector 하나를 쓰는 방식보다) 플립
    위험이 훨씬 적다.
    """
    num_fk = len(fk_ctrls)
    fk_params = _sample_params(num_fk, include_tip=True)
    null_params = _sample_params(num_nulls, include_tip=True)

    fk_dm = []
    for i, ctrl in enumerate(fk_ctrls):
        dm = cmds.createNode('decomposeMatrix', n='{}_nullTwistFkRot{:02d}_DM'.format(name, i))
        cmds.connectAttr(ctrl+'.worldMatrix[0]', dm+'.inputMatrix')
        fk_dm.append(dm)

    for i, u in enumerate(null_params):
        mp = mps[i]
        cmds.setAttr(mp+'.follow', 1)
        cmds.setAttr(mp+'.frontAxis', 0)
        cmds.setAttr(mp+'.upAxis', 1)
        cmds.setAttr(mp+'.worldUpType', 2)  # Object Rotation Up

        lo = 0
        for j in range(len(fk_params)):
            if fk_params[j] <= u:
                lo = j
            else:
                break
        hi = min(lo+1, len(fk_params)-1)

        if lo == hi:
            cmds.connectAttr(fk_ctrls[lo]+'.worldMatrix[0]', mp+'.worldUpMatrix')
        else:
            t = (u-fk_params[lo]) / (fk_params[hi]-fk_params[lo])
            t = max(0.0, min(1.0, t))
            pb = cmds.createNode('pairBlend', n='{}_nullTwistUp{:02d}_PB'.format(name, i))
            cmds.setAttr(pb+'.rotInterpolation', 1)  # quaternion slerp
            cmds.connectAttr(fk_dm[lo]+'.outputRotate', pb+'.inRotate1')
            cmds.connectAttr(fk_dm[hi]+'.outputRotate', pb+'.inRotate2')
            cmds.setAttr(pb+'.weight', t)

            cm = cmds.createNode('composeMatrix', n='{}_nullTwistUp{:02d}_CM'.format(name, i))
            cmds.connectAttr(pb+'.outRotate', cm+'.inputRotate')
            cmds.connectAttr(cm+'.outputMatrix', mp+'.worldUpMatrix')

        cmds.connectAttr(mp+'.rotate', nulls[i]+'.rotate')


def _build_squash_region_ctrls(name, base_crv, ctl_grp):
    """base_CRV 위를 파라미터(0~1)로 움직이는 Squash Start/End 컨트롤러 2개.

    각자 Parameter(0~1)와 Volume(0 이상, 상한 없음) attribute를 갖는다 -- Parameter로
    커브 위 위치가, Volume으로 그 지점의 squash 강도가 결정된다. 둘 사이 구간에 속하는
    null/BIND_JNT의 squash 볼륨이 start~end 값으로 보간된다(_build_null_bind_joints).
    기본값은 Start=0/End=1(커브 전체를 덮음), Volume=0(꺼짐)이라 아무것도 안
    건드리면 이전과 동일하게 squash가 꺼진 상태로 시작한다.
    """
    shape = cmds.listRelatives(base_crv, shapes=True, ni=True, fullPath=True)[0]
    ctrls = []
    for label, default_param in (('Start', 0.0), ('End', 1.0)):
        c, off = _make_ctrl('{}_Squash{}_CTL'.format(name, label), 1.2, (0, 0, 0))
        cmds.setAttr(c+'.overrideEnabled', 1)
        cmds.setAttr(c+'.overrideColor', 17)
        cmds.parent(off, ctl_grp)
        cmds.addAttr(c, ln='Parameter', at='double', min=0, max=1, dv=default_param, k=True)
        cmds.addAttr(c, ln='Volume', at='double', min=0, dv=0, k=True)

        mp = cmds.createNode('motionPath', n='{}_squash{}_MP'.format(name, label))
        cmds.connectAttr(shape+'.worldSpace[0]', mp+'.geometryPath')
        cmds.setAttr(mp+'.fractionMode', 1)
        cmds.connectAttr(c+'.Parameter', mp+'.uValue')
        cmds.connectAttr(mp+'.allCoordinates', off+'.translate')

        ctrls.append(c)
    return ctrls[0], ctrls[1]


def _build_null_bind_joints(name, nulls, num_nulls, squash_start_ctrl, squash_end_ctrl,
                             ratio_plug, squash_gate_plug):
    """각 null 밑에 최종 바인드용 조인트를 만든다 -- 캐릭터 메쉬를 스키닝할
    때 실제로 쓰는 조인트로, null의 위치+회전(커브를 따라가며 twist까지
    반영된 최종 값)을 그대로 물려받는다. 다른 내부 유틸 joint(IK/FK_JNT)와
    달리 숨기지 않는다 -- 애니메이터/리거가 직접 선택해서 스키닝에 쓴다.

    Squash volume은 여기(scaleY/Z)에서만 적용한다. 각 BIND_JNT의 고정
    파라미터(u_i)를 squash_start_ctrl.Parameter~squash_end_ctrl.Parameter
    구간에서 0~1로 clamp한 t로 삼아, start.Volume~end.Volume을 보간한다 --
    t가 0/1로 clamp되므로 구간 밖은 자연히 가장 가까운 끝의 볼륨값으로
    고정된다. 여기에 전역 squash_gate_plug(마지막 IK 컨트롤러의 Squash)를
    곱해서 최종 게이트로 쓴다 -- 전역 Squash=0이면 구간 볼륨과 무관하게
    항상 꺼진다.
    """
    param_diff = cmds.createNode('plusMinusAverage', n='{}_squashParamRange_PMA'.format(name))
    cmds.setAttr(param_diff+'.operation', 2)  # subtract
    cmds.connectAttr(squash_end_ctrl+'.Parameter', param_diff+'.input1D[0]')
    cmds.connectAttr(squash_start_ctrl+'.Parameter', param_diff+'.input1D[1]')

    volume_diff = cmds.createNode('plusMinusAverage', n='{}_squashVolumeRange_PMA'.format(name))
    cmds.setAttr(volume_diff+'.operation', 2)  # subtract
    cmds.connectAttr(squash_end_ctrl+'.Volume', volume_diff+'.input1D[0]')
    cmds.connectAttr(squash_start_ctrl+'.Volume', volume_diff+'.input1D[1]')

    null_params = _sample_params(num_nulls, include_tip=True)

    bind_jnts = []
    for i, null in enumerate(nulls):
        cmds.select(cl=True)
        jnt = cmds.joint(n='{}_{:02d}_BIND_JNT'.format(name, i))
        cmds.parent(jnt, null)
        cmds.setAttr(jnt+'.translate', 0, 0, 0)
        cmds.setAttr(jnt+'.rotate', 0, 0, 0)
        # cmds.parent가 world 유지를 위해 jointOrient에 보정값을 구워 넣으므로
        # (null이 이미 twist로 회전돼 있는 상태에서 새 joint를 부모링하면)
        # 명시적으로 0으로 되돌려야 이 joint의 축이 null과 완전히 같아진다.
        cmds.setAttr(jnt+'.jointOrient', 0, 0, 0)

        u = null_params[i]
        pos_diff = cmds.createNode('plusMinusAverage', n='{}_squashPos{:02d}_PMA'.format(name, i))
        cmds.setAttr(pos_diff+'.operation', 2)  # subtract
        cmds.setAttr(pos_diff+'.input1D[0]', u)
        cmds.connectAttr(squash_start_ctrl+'.Parameter', pos_diff+'.input1D[1]')

        t_raw = cmds.createNode('multiplyDivide', n='{}_squashT{:02d}_MD'.format(name, i))
        cmds.setAttr(t_raw+'.operation', 2)  # divide
        cmds.connectAttr(pos_diff+'.output1D', t_raw+'.input1X')
        cmds.connectAttr(param_diff+'.output1D', t_raw+'.input2X')

        t_clamped = cmds.createNode('clamp', n='{}_squashT{:02d}_CLAMP'.format(name, i))
        cmds.setAttr(t_clamped+'.minR', 0)
        cmds.setAttr(t_clamped+'.maxR', 1)
        cmds.connectAttr(t_raw+'.outputX', t_clamped+'.inputR')

        volume_scaled = cmds.createNode('multDoubleLinear', n='{}_squashVolume{:02d}_MDL'.format(name, i))
        cmds.connectAttr(volume_diff+'.output1D', volume_scaled+'.input1')
        cmds.connectAttr(t_clamped+'.outputR', volume_scaled+'.input2')

        volume_i = cmds.createNode('addDoubleLinear', n='{}_squashVolume{:02d}_ADL'.format(name, i))
        cmds.connectAttr(squash_start_ctrl+'.Volume', volume_i+'.input1')
        cmds.connectAttr(volume_scaled+'.output', volume_i+'.input2')

        local_gate = cmds.createNode('multDoubleLinear', n='{}_squashLocalGate{:02d}_MDL'.format(name, i))
        cmds.setAttr(local_gate+'.input2', 0.1)
        cmds.connectAttr(volume_i+'.output', local_gate+'.input1')

        final_gate = cmds.createNode('multDoubleLinear', n='{}_squashFinalGate{:02d}_MDL'.format(name, i))
        cmds.connectAttr(local_gate+'.output', final_gate+'.input1')
        cmds.connectAttr(squash_gate_plug, final_gate+'.input2')

        inv_ratio = cmds.createNode('multiplyDivide', n='{}_squashInv{:02d}_MD'.format(name, i))
        cmds.setAttr(inv_ratio+'.operation', 2)  # divide
        cmds.setAttr(inv_ratio+'.input1X', 1.0)
        cmds.connectAttr(ratio_plug, inv_ratio+'.input2X')

        for axis in ('Y', 'Z'):
            sq_blend = cmds.createNode('blendTwoAttr', n='{}_squash{:02d}{}_BTA'.format(name, i, axis))
            cmds.setAttr(sq_blend+'.input[0]', 1.0)
            cmds.connectAttr(inv_ratio+'.outputX', sq_blend+'.input[1]')
            cmds.connectAttr(final_gate+'.output', sq_blend+'.attributesBlender')
            cmds.connectAttr(sq_blend+'.output', jnt+'.scale'+axis, f=True)

        bind_jnts.append(jnt)
    return bind_jnts


def build_tentacle_base_curve(mesh='pSphere1', name='tentacle', axis='y', num_nulls=13):
    """1단계: base_CRV까지만 생성한다.

    direction(축)과 CV 위치를 씬에서 직접 검토(필요하면 CV를 손으로 조정)한
    뒤, build_tentacle_rig_continue()로 이어서 나머지 파이프라인을 빌드한다.
    다음 단계에 필요한 mesh/axis/num_nulls는 rig_GRP에 attribute로 저장해
    두어서, continue 단계는 이 값들을 몰라도(같은 name만 알면) 이어서
    실행할 수 있다.

    Arguments:
        mesh (str): 촉수 형상 스탠드인
        name (str): 리그 네이밍 프리픽스
        axis (str): base curve가 오브젝트 중심을 지나며 뻗어나갈 축 ('x'/'y'/'z').
            기본값 'y'. None을 주면 bounding box에서 가장 긴 축을 자동 감지.
        num_nulls (int): base curve 위 motionPath null(=base_CRV CV) 개수

    Returns:
        dict: base_curve, rig_grp, axis 등
    """
    if cmds.objExists('{}_rig_GRP'.format(name)):
        cmds.delete('{}_rig_GRP'.format(name))

    base, tip, axis = _get_axis_endpoints(mesh, axis)
    g = _build_groups(name)
    base_crv, base_shape = _build_base_curve(name, mesh, axis, base, tip, num_nulls, g['crv'])

    cmds.addAttr(g['rig'], ln='sourceMesh', dt='string')
    cmds.setAttr(g['rig']+'.sourceMesh', mesh, type='string')
    cmds.addAttr(g['rig'], ln='rigAxis', dt='string')
    cmds.setAttr(g['rig']+'.rigAxis', axis, type='string')
    cmds.addAttr(g['rig'], ln='numNulls', at='long')
    cmds.setAttr(g['rig']+'.numNulls', num_nulls)

    print('=' * 60)
    print('Tentacle base curve 완료: {}'.format(name))
    print('  mesh    : {}'.format(mesh))
    print('  axis    : {}'.format(axis))
    print('  CV 개수 : {}'.format(num_nulls))
    print('  -> curve의 direction/CV 위치를 검토한 뒤 build_tentacle_rig_continue()로')
    print('     이어서 빌드하세요.')
    print('=' * 60)
    return {'rig_grp': g['rig'], 'base_curve': base_crv, 'axis': axis, 'base': base, 'tip': tip}


def build_tentacle_rig_continue(name='tentacle', num_ctrls=7, num_ik_ctrls=2):
    """2단계: build_tentacle_base_curve()로 만든 base_CRV를 기준으로 나머지
    파이프라인(null/IK/FK/skin/twist/bind joint)을 이어서 빌드한다.

    FK/IK 블렌드(스위치)는 없다 -- FK 조인트가 base_CRV에 직접 skinCluster로
    바인드되어 항상 최종 모양을 구동하고, IK는 ik_CRV를 변형시켜 splineIK
    joint 체인의 회전을 바꾸고, 그 회전(+위치)이 FK로 그대로 복제되어
    real DAG 하이라키를 통해 결과적으로 base_CRV에 반영된다.

    Arguments:
        name (str): build_tentacle_base_curve()에서 쓴 것과 같은 리그 이름
        num_ctrls (int): FK 컨트롤 개수 = splineIK joint 개수 (정확히 1:1로 매칭되어
            위치/회전이 항상 일치한다)
        num_ik_ctrls (int): IK 컨트롤 개수 (FK와 독립적으로 조절 가능). Advanced
            Twist는 항상 시작/끝 IK 컨트롤의 회전을 참조한다.

    Returns:
        dict: 주요 결과 노드 모음
    """
    rig_grp = '{}_rig_GRP'.format(name)
    base_crv = '{}_base_CRV'.format(name)
    if not cmds.objExists(rig_grp) or not cmds.objExists(base_crv):
        raise RuntimeError(
            '"{}" base curve가 없습니다. 먼저 build_tentacle_base_curve(name="{}")를 실행하세요.'.format(
                name, name))

    axis = cmds.getAttr(rig_grp+'.rigAxis')
    num_nulls = cmds.getAttr(rig_grp+'.numNulls')

    g = {
        'rig': rig_grp,
        'crv': '{}_CRV_GRP'.format(name),
        'ctl': '{}_CTL_GRP'.format(name),
        'fk_ctl': '{}_FK_CTL_GRP'.format(name),
        'ik_ctl': '{}_IK_CTL_GRP'.format(name),
        'null': '{}_NULL_GRP'.format(name),
        'jnt': '{}_JNT_GRP'.format(name),
        'sys': '{}_SYS_GRP'.format(name),
    }
    base_shape = cmds.listRelatives(base_crv, shapes=True, ni=True, fullPath=True)[0]
    base = cmds.pointPosition(base_crv+'.cv[0]', world=True)

    up_loc = _build_up_vector(name, g['sys'], axis, base)

    # Stretch/Squash/Slide는 Settings_CTL 없이 마지막 IK 컨트롤러 위에 얹는다 --
    # 그 컨트롤이 존재해야 하므로 ik_CRV/IK 컨트롤을 먼저 만든다.
    ik_crv = _build_ik_curve(name, g['crv'], base_crv)
    ik_ctrls, ik_ctrl_jnts = _build_ik_setup(name, num_ik_ctrls, g['ik_ctl'], ik_crv, up_loc)
    attr_ctrl = ik_ctrls[-1]
    _add_rig_attrs(attr_ctrl)
    ratio_plug, stretch_gate_plug, squash_gate_plug = _build_stretch_ratio(name, ik_crv, attr_ctrl)

    mps, nulls = _build_mp_nulls(name, num_nulls, base_shape, g['null'])
    _build_slide(name, mps, attr_ctrl)

    squash_start_ctrl, squash_end_ctrl = _build_squash_region_ctrls(name, base_crv, g['ctl'])

    ik_jnts = _build_ik_spline_chain(name, num_ctrls, ik_crv, ik_ctrls, g['jnt'], g['sys'],
                                      ratio_plug, stretch_gate_plug, squash_gate_plug)

    fk_ctrls, fk_jnts = _build_fk_setup(name, ik_jnts, g['fk_ctl'])

    _build_fk_skin(name, fk_jnts, base_crv)

    _build_null_rotation_from_fk(name, mps, nulls, num_nulls, fk_ctrls)

    bind_jnts = _build_null_bind_joints(name, nulls, num_nulls, squash_start_ctrl, squash_end_ctrl,
                                         ratio_plug, squash_gate_plug)

    result = {
        'rig_grp': g['rig'],
        'base_curve': base_crv,
        'ik_curve': ik_crv,
        'up_loc': up_loc,
        'motion_paths': mps,
        'nulls': nulls,
        'bind_jnts': bind_jnts,
        'attr_ctrl': attr_ctrl,
        'squash_start_ctrl': squash_start_ctrl,
        'squash_end_ctrl': squash_end_ctrl,
        'ik_ctrls': ik_ctrls,
        'ik_jnts': ik_jnts,
        'fk_ctrls': fk_ctrls,
        'fk_jnts': fk_jnts,
        'axis': axis,
    }
    print('=' * 60)
    print('Tentacle Rig 완료: {}'.format(name))
    print('  base->tip axis : {}'.format(axis))
    print('  MP null 개수   : {}'.format(len(nulls)))
    print('  bind jnts      : {}'.format(len(bind_jnts)))
    print('  FK ctrls       : {}'.format(len(fk_ctrls)))
    print('  IK ctrls       : {}'.format(len(ik_ctrls)))
    print('  ikSpline jnts  : {}'.format(len(ik_jnts)))
    print('  Stretch/Squash/Slide -> {}'.format(attr_ctrl))
    print('  Squash region  : {} ~ {}'.format(squash_start_ctrl, squash_end_ctrl))
    print('=' * 60)
    return result


def build_tentacle_rig(mesh='pSphere1', name='tentacle', axis='y', num_ctrls=7, num_ik_ctrls=2, num_nulls=13):
    """촉수 오토리그를 검토 단계 없이 한 번에 전체 빌드(build_tentacle_base_curve
    + build_tentacle_rig_continue를 그냥 이어서 호출하는 편의 함수). curve의
    direction/CV 위치를 중간에 검토하고 싶으면 두 함수를 따로 호출하세요.
    """
    build_tentacle_base_curve(mesh=mesh, name=name, axis=axis, num_nulls=num_nulls)
    return build_tentacle_rig_continue(name=name, num_ctrls=num_ctrls, num_ik_ctrls=num_ik_ctrls)


if __name__ == '__main__':
    build_tentacle_rig()
