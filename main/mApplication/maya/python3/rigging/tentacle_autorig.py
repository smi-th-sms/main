# -*- coding: utf-8 -*-
"""============================================================================
촉수(Tentacle) Auto-Rig -- BASE

1단계(베이스)만 구현한다:
    1. mesh의 world bounding box에서 가장 긴 축을 base->tip 방향으로 잡아 curve 생성
    2. 그 curve 위에서 motionPath로 위치/회전을 뽑는 null 그룹을
       원하는 개수(num_nulls)만큼 균등 분배로 생성

FK/IK 하이브리드, SubFK, Stretch/Squash, Slide, Curl 등은 이후 단계에서
이 베이스 위에 하나씩 얹는다.

:Example:
    from python3.rigging import tentacle_autorig
    reload(tentacle_autorig)
    tentacle_autorig.build_tentacle_base(mesh='pCone1')
============================================================================"""
import maya.cmds as cmds


def _lerp3(a, b, t):
    return (a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t, a[2] + (b[2]-a[2])*t)


def _get_axis_endpoints(mesh):
    """mesh의 world bounding box에서 가장 긴 축을 촉수의 base->tip 방향으로 사용."""
    bbox = cmds.exactWorldBoundingBox(mesh)
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
    g['sys'] = cmds.createNode('transform', n='{}_SYS_GRP'.format(name), p=g['rig'])
    cmds.setAttr('{}.visibility'.format(g['sys']), 0)
    return g


def _build_base_curve(name, base, tip, num_nulls, crv_grp):
    """base->tip을 num_nulls개 지점으로 균등분배한 포인트로 degree-3 커브 생성."""
    positions = [_lerp3(base, tip, i/float(num_nulls-1)) for i in range(num_nulls)]
    crv = cmds.curve(n='{}_base_CRV'.format(name), d=3, p=positions)
    cmds.rebuildCurve(crv, ch=False, rpo=True, rt=0, end=1, kr=0, kcp=1,
                       kep=1, kt=0, s=len(positions)-3, d=3)
    cmds.parent(crv, crv_grp)
    shape = cmds.listRelatives(crv, shapes=True)[0]
    return crv, shape


def _build_up_vector(name, sys_grp, axis, base):
    """motionPath의 Object Rotation Up 참조 로케이터.

    up_loc의 로컬 Y축(회전 안 시키면 world Y)이 곧 up-reference 방향이 된다.
    이게 curve의 tangent 방향(=axis)과 평행해지면 forward/up이 겹치는
    특이점(singularity)이 생겨서, motionPath 프레임이 체인 중간 어딘가에서
    180도 뒤집히는 문제가 생긴다. axis=='y'일 때만 이 조건에 걸리므로
    up_loc을 90도 틸트해서 참조 방향을 Z로 돌려 평행을 피한다.
    """
    up_off = cmds.createNode('transform', n='{}_up_OFF'.format(name), p=sys_grp)
    up_loc = cmds.spaceLocator(n='{}_up_LOC'.format(name))[0]
    cmds.parent(up_loc, up_off)
    cmds.xform(up_off, ws=True, t=base)
    cmds.move(5, 0, 0, up_loc, r=True, os=True)
    if axis == 'y':
        cmds.setAttr(up_loc+'.rotateX', 90)
    return up_loc


def _build_mp_nulls(name, num_nulls, base_shape, up_loc, null_grp):
    """curve 위에 균등 분배된 motionPath 기반 null 그룹 생성."""
    mps, nulls = [], []
    for i in range(num_nulls):
        u = i/float(num_nulls-1)
        mp = cmds.createNode('motionPath', n='{}_{:02d}_MP'.format(name, i))
        cmds.connectAttr(base_shape+'.worldSpace[0]', mp+'.geometryPath')
        cmds.setAttr(mp+'.uValue', u)
        cmds.setAttr(mp+'.fractionMode', 1)
        cmds.setAttr(mp+'.follow', 1)
        cmds.setAttr(mp+'.frontAxis', 0)   # X: 체인 진행(aim) 방향
        cmds.setAttr(mp+'.upAxis', 1)      # Y: up
        cmds.setAttr(mp+'.worldUpType', 2)  # Object Rotation Up
        cmds.connectAttr(up_loc+'.worldMatrix[0]', mp+'.worldUpMatrix')

        null = cmds.createNode('transform', n='{}_{:02d}_NULL'.format(name, i), p=null_grp)
        cmds.connectAttr(mp+'.allCoordinates', null+'.translate')
        cmds.connectAttr(mp+'.rotate', null+'.rotate')

        mps.append(mp)
        nulls.append(null)
    return mps, nulls


def _build_settings_ctl(name, base_pos, ctl_grp):
    s = cmds.createNode('transform', n='{}_Settings_CTL'.format(name), p=ctl_grp)
    cmds.xform(s, ws=True, t=base_pos)
    cmds.addAttr(s, ln='IkFkBlend', at='double', min=0, max=1, dv=0, k=True)
    cmds.addAttr(s, ln='Stretch', at='double', min=0, max=10, dv=0, k=True)
    cmds.addAttr(s, ln='Squash', at='double', min=0, max=10, dv=0, k=True)
    return s


def _make_ctrl(n, radius, pos, normal=(0, 1, 0)):
    ctrl = cmds.circle(n=n, r=radius, nr=normal, ch=False)[0]
    off = cmds.createNode('transform', n='{}_OFF'.format(n))
    cmds.parent(ctrl, off)
    cmds.xform(off, ws=True, t=pos)
    return ctrl, off


def _build_fk_ik_curves(name, crv_grp, base_crv):
    """base_CRV를 복사해서 FK/IK 각각의 구동용 curve를 만든다."""
    fk_crv = cmds.duplicate(base_crv, n='{}_fk_CRV'.format(name))[0]
    ik_crv = cmds.duplicate(base_crv, n='{}_ik_CRV'.format(name))[0]
    cmds.parent(fk_crv, ik_crv, crv_grp)
    return fk_crv, ik_crv


def _build_ik_spline_joints(name, base, tip, num_fk_ctrls, ik_crv, up_loc, sys_grp):
    """ik_CRV를 따라가는 splineIK joint 체인. FK 컨트롤 1개당 1개씩 필요하므로
    개수는 num_fk_ctrls를 그대로 따른다.

    jointOrient를 rest tangent에 맞춰두기 때문에(표준 orientJoint),
    ik_CRV가 아직 안 변형된 rest 상태에서는 각 joint의 .rotate가 0에
    가깝다. IK 컨트롤이 ik_CRV를 변형시키면 splineIK 솔버가 매 프레임
    .rotate를 갱신해서 '그 변형분만큼'만 나타난다 (jointOrient와 rotate는
    서로 다른 채널이라 별도 matrix 연산 없이 자연스럽게 delta만 얻어짐).
    """
    positions = [_lerp3(base, tip, i/float(num_fk_ctrls-1)) for i in range(num_fk_ctrls)]
    cmds.select(cl=True)
    jnts = []
    for i, pos in enumerate(positions):
        cmds.select(cl=True)
        j = cmds.joint(n='{}_ikSpline{:02d}_JNT'.format(name, i), p=pos)
        jnts.append(j)
    for i in range(1, len(jnts)):
        cmds.parent(jnts[i], jnts[i-1])
    cmds.joint(jnts[0], e=True, zso=True, oj='xyz', sao='yup', ch=True)
    for j in jnts:
        cmds.setAttr(j+'.jointOrient', 0, 0, 0)
    cmds.setAttr(jnts[0]+'.visibility', 0)
    cmds.parent(jnts[0], sys_grp)

    ik_handle = cmds.ikHandle(n='{}_ikSpline_HDL'.format(name), sj=jnts[0], ee=jnts[-1],
                               sol='ikSplineSolver', ccv=False, pcv=False, c=ik_crv)[0]
    cmds.setAttr(ik_handle+'.dTwistControlEnable', 1)
    cmds.setAttr(ik_handle+'.dWorldUpType', 4)  # Object Rotation Up (start/end)
    cmds.connectAttr(up_loc+'.worldMatrix[0]', ik_handle+'.dWorldUpMatrix')
    cmds.connectAttr(up_loc+'.worldMatrix[0]', ik_handle+'.dWorldUpMatrixEnd')
    cmds.parent(ik_handle, sys_grp)
    return jnts


def _build_fk_setup(name, base, tip, num_fk_ctrls, fk_ctl_grp, fk_crv, ik_spline_jnts):
    """FK 컨트롤은 spine2_.py 방식대로 단순 DAG 부모-자식 체인.

    각 컨트롤의 offset과 컨트롤 사이에 ConnOff를 끼워서, 같은 인덱스의
    splineIK joint(ik_CRV를 따라가는) rotate를 connectAttr로 직접 받는다
    (matrix 연산 없이 rotate 채널만 그대로 연결) -- IK 컨트롤을 움직여
    ik_CRV가 휘면 FK 체인 전체가 real DAG 부모링을 통해 그 휨을 따라간다.

    각 컨트롤 안에는 숨은 joint를 하나씩 넣어 fk_CRV에 skinCluster로
    묶는다 (컨트롤 개수 < curve CV 개수라 dropoff로 부드럽게 퍼짐).
    """
    positions = [_lerp3(base, tip, i/float(num_fk_ctrls-1)) for i in range(num_fk_ctrls)]
    fk_ctrls, fk_jnts = [], []
    for i, pos in enumerate(positions):
        off = cmds.createNode('transform', n='{}_FK{:02d}_CTL_OFF'.format(name, i))
        cmds.xform(off, ws=True, t=pos)
        cmds.parent(off, fk_ctl_grp if i == 0 else fk_ctrls[i-1])
        # i>0일 때 부모(이전 FK 컨트롤)가 이미 ConnOff로 회전돼 있으면
        # cmds.parent의 "world 위치 보존"이 그 회전을 상쇄하는 값을
        # off의 rotate에 몰래 구워 넣는다 -- off는 위치 전용이어야 하므로
        # 명시적으로 0으로 되돌린다.
        cmds.setAttr(off+'.rotate', 0, 0, 0)

        conn_off = cmds.createNode('transform', n='{}_FK{:02d}_ConnOff'.format(name, i), p=off)
        cmds.connectAttr(ik_spline_jnts[i]+'.rotate', conn_off+'.rotate')

        c = cmds.circle(n='{}_FK{:02d}_CTL'.format(name, i), r=2.2, nr=(0, 1, 0), ch=False)[0]
        cmds.setAttr(c+'.overrideEnabled', 1)
        cmds.setAttr(c+'.overrideColor', 6)
        cmds.parent(c, conn_off)
        cmds.setAttr(c+'.translate', 0, 0, 0)
        cmds.setAttr(c+'.rotate', 0, 0, 0)

        cmds.select(cl=True)
        jnt = cmds.joint(n='{}_FK{:02d}_JNT'.format(name, i))
        cmds.setAttr(jnt+'.visibility', 0)
        cmds.parent(jnt, c)
        cmds.setAttr(jnt+'.translate', 0, 0, 0)
        cmds.setAttr(jnt+'.rotate', 0, 0, 0)

        fk_ctrls.append(c)
        fk_jnts.append(jnt)

    cmds.skinCluster(fk_jnts + [fk_crv], n='{}_fk_SKIN'.format(name),
                      tsb=True, bm=0, sm=0, nw=1, mi=4, dr=4.0)
    return fk_ctrls, fk_jnts


def _build_ik_setup(name, base, tip, num_ik_ctrls, ik_ctl_grp, ik_crv):
    """IK 컨트롤은 서로 독립(부모관계 없음), 마찬가지로 숨은 joint를
    ik_CRV에 skinCluster로 묶어서 자유 이동으로 curve 모양을 직접 조형한다.
    """
    positions = [_lerp3(base, tip, i/float(num_ik_ctrls-1)) for i in range(num_ik_ctrls)]
    ik_ctrls, ik_jnts = [], []
    for i, pos in enumerate(positions):
        c, off = _make_ctrl('{}_IK{:02d}_CTL'.format(name, i), 1.6, pos)
        cmds.setAttr(c+'.overrideEnabled', 1)
        cmds.setAttr(c+'.overrideColor', 13)
        cmds.parent(off, ik_ctl_grp)

        cmds.select(cl=True)
        jnt = cmds.joint(n='{}_IK{:02d}_JNT'.format(name, i))
        cmds.setAttr(jnt+'.visibility', 0)
        cmds.parent(jnt, c)
        cmds.setAttr(jnt+'.translate', 0, 0, 0)
        cmds.setAttr(jnt+'.rotate', 0, 0, 0)

        ik_ctrls.append(c)
        ik_jnts.append(jnt)

    cmds.skinCluster(ik_jnts + [ik_crv], n='{}_ik_SKIN'.format(name),
                      tsb=True, bm=0, sm=0, nw=1, mi=4, dr=4.0)
    return ik_ctrls, ik_jnts


def _build_hybrid_blend(name, fk_crv, ik_crv, base_crv, settings_ctl):
    """fk_CRV/ik_CRV를 base_CRV에 blendShape로 얹어서 Settings.IkFkBlend
    (0=FK, 1=IK)로 전환/블렌드한다. base_CRV는 MP null들이 이미 샘플링하고
    있으므로, 이 블렌드 결과가 그대로 베이스 전체에 반영된다.
    """
    bs = cmds.blendShape(fk_crv, ik_crv, base_crv, n='{}_hybrid_BS'.format(name))[0]
    rev = cmds.createNode('reverse', n='{}_ikFkBlend_RVS'.format(name))
    cmds.connectAttr(settings_ctl+'.IkFkBlend', rev+'.inputX')
    cmds.connectAttr(rev+'.outputX', bs+'.weight[0]')       # fk_crv weight = 1-blend
    cmds.connectAttr(settings_ctl+'.IkFkBlend', bs+'.weight[1]')  # ik_crv weight = blend
    return bs


def _build_stretch_squash(name, mps, nulls, num_nulls, ik_crv, settings_ctl):
    """ik_CRV의 arc length(rest 대비 현재 비율)를 기준으로 Stretch/Squash를 만든다.

    이 리그의 MP null들은 motionPath fractionMode=1이라 항상 '현재 길이의
    n%% 지점'을 따라가는(=늘 완전히 stretchy한) 상태다. Stretch 속성으로
    "rigid(절대 거리 고정)"와 "완전 stretchy(지금 동작)" 사이를 블렌드하려면
    uValue 자체를 아래처럼 바꿔야 한다:

        stretchyU_i = i/(n-1)                (지금 쓰던 상수, 비율 고정)
        rigidU_i    = stretchyU_i / ratio     (ratio=현재길이/rest길이 -- 커브가
                                                늘어난 만큼 절대 거리를 맞추려면
                                                오히려 작은 비율을 써야 함)
        finalU_i    = blend(rigidU_i, stretchyU_i, Stretch/10)

    Squash는 같은 ratio를 Settings.Squash로 게이트한 뒤 역수를 취해 null의
    진행축(X) 수직축(Y/Z)에 곱해 볼륨을 보존한다.
    """
    rest_length = cmds.arclen(ik_crv)
    ik_shape = cmds.listRelatives(ik_crv, shapes=True, ni=True)[0]

    curve_info = cmds.createNode('curveInfo', n='{}_ikStretch_CI'.format(name))
    cmds.connectAttr(ik_shape+'.worldSpace[0]', curve_info+'.inputCurve')

    ratio_md = cmds.createNode('multiplyDivide', n='{}_stretchRatio_MD'.format(name))
    cmds.setAttr(ratio_md+'.operation', 2)  # divide
    cmds.connectAttr(curve_info+'.arcLength', ratio_md+'.input1X')
    cmds.setAttr(ratio_md+'.input2X', rest_length)

    stretch_gate = cmds.createNode('multDoubleLinear', n='{}_stretchGate_MDL'.format(name))
    cmds.setAttr(stretch_gate+'.input2', 0.1)
    cmds.connectAttr(settings_ctl+'.Stretch', stretch_gate+'.input1')

    squash_gate = cmds.createNode('multDoubleLinear', n='{}_squashGate_MDL'.format(name))
    cmds.setAttr(squash_gate+'.input2', 0.1)
    cmds.connectAttr(settings_ctl+'.Squash', squash_gate+'.input1')

    # Squash: ratio를 Squash 게이트로 1~ratio 사이 블렌드한 뒤 역수 -> 진행축(X) 수직축(Y/Z)
    squash_blend = cmds.createNode('blendTwoAttr', n='{}_squashBlend_BTA'.format(name))
    cmds.setAttr(squash_blend+'.input[0]', 1.0)
    cmds.connectAttr(ratio_md+'.outputX', squash_blend+'.input[1]')
    cmds.connectAttr(squash_gate+'.output', squash_blend+'.attributesBlender')
    squash_inv = cmds.createNode('multiplyDivide', n='{}_squashInv_MD'.format(name))
    cmds.setAttr(squash_inv+'.operation', 2)
    cmds.setAttr(squash_inv+'.input1X', 1.0)
    cmds.connectAttr(squash_blend+'.output', squash_inv+'.input2X')

    for i in range(num_nulls):
        stretchy_u = i/float(num_nulls-1)

        rigid_u_md = cmds.createNode('multiplyDivide', n='{}_rigidU{:02d}_MD'.format(name, i))
        cmds.setAttr(rigid_u_md+'.operation', 2)  # divide
        cmds.setAttr(rigid_u_md+'.input1X', stretchy_u)
        cmds.connectAttr(ratio_md+'.outputX', rigid_u_md+'.input2X')

        u_blend = cmds.createNode('blendTwoAttr', n='{}_uBlend{:02d}_BTA'.format(name, i))
        cmds.connectAttr(rigid_u_md+'.outputX', u_blend+'.input[0]')
        cmds.setAttr(u_blend+'.input[1]', stretchy_u)
        cmds.connectAttr(stretch_gate+'.output', u_blend+'.attributesBlender')
        cmds.connectAttr(u_blend+'.output', mps[i]+'.uValue', f=True)

        cmds.connectAttr(squash_inv+'.outputX', nulls[i]+'.scaleY')
        cmds.connectAttr(squash_inv+'.outputX', nulls[i]+'.scaleZ')


def build_tentacle_rig(mesh='pCone1', name='tentacle', num_nulls=9, num_fk_ctrls=6, num_ik_ctrls=4):
    """베이스(curve + MP null) 위에 FK/IK 하이브리드를 얹어서 빌드.

    Arguments:
        mesh (str): 촉수 형상 스탠드인
        name (str): 리그 네이밍 프리픽스
        num_nulls (int): base curve 위 motionPath null 개수
        num_fk_ctrls (int): FK 컨트롤 개수 (curve CV 개수보다 적어도 skinCluster로 부드럽게 매핑).
            같은 개수의 splineIK joint가 생성되어 FK가 ik_CRV를 따라가는 데 쓰인다.
        num_ik_ctrls (int): IK 컨트롤 개수 (FK와 독립적으로 조절 가능)

    Returns:
        dict: 주요 결과 노드 모음
    """
    if cmds.objExists('{}_rig_GRP'.format(name)):
        cmds.delete('{}_rig_GRP'.format(name))

    base, tip, axis = _get_axis_endpoints(mesh)
    g = _build_groups(name)

    base_crv, base_shape = _build_base_curve(name, base, tip, num_nulls, g['crv'])
    up_loc = _build_up_vector(name, g['sys'], axis, base)
    mps, nulls = _build_mp_nulls(name, num_nulls, base_shape, up_loc, g['null'])

    settings_ctl = _build_settings_ctl(name, base, g['ctl'])
    fk_crv, ik_crv = _build_fk_ik_curves(name, g['crv'], base_crv)
    ik_spline_jnts = _build_ik_spline_joints(name, base, tip, num_fk_ctrls, ik_crv, up_loc, g['sys'])
    fk_ctrls, fk_jnts = _build_fk_setup(name, base, tip, num_fk_ctrls, g['fk_ctl'], fk_crv, ik_spline_jnts)
    ik_ctrls, ik_jnts = _build_ik_setup(name, base, tip, num_ik_ctrls, g['ik_ctl'], ik_crv)
    _build_hybrid_blend(name, fk_crv, ik_crv, base_crv, settings_ctl)
    _build_stretch_squash(name, mps, nulls, num_nulls, ik_crv, settings_ctl)

    result = {
        'rig_grp': g['rig'],
        'base_curve': base_crv,
        'fk_curve': fk_crv,
        'ik_curve': ik_crv,
        'up_loc': up_loc,
        'motion_paths': mps,
        'nulls': nulls,
        'settings_ctl': settings_ctl,
        'fk_ctrls': fk_ctrls,
        'ik_ctrls': ik_ctrls,
        'ik_spline_jnts': ik_spline_jnts,
        'axis': axis,
    }
    print('=' * 60)
    print('Tentacle Rig (base + FK/IK hybrid) 완료: {}'.format(name))
    print('  base->tip axis : {}'.format(axis))
    print('  MP null 개수   : {}'.format(len(nulls)))
    print('  FK ctrls       : {}'.format(num_fk_ctrls))
    print('  IK ctrls       : {}'.format(num_ik_ctrls))
    print('=' * 60)
    return result


def build_tentacle_base(mesh='pCone1', name='tentacle', num_nulls=9):
    """촉수 오토리그 베이스 빌드 (curve + motionPath null 그룹만).

    Arguments:
        mesh (str): 촉수 형상 스탠드인 (bounding box의 최장축을 base->tip으로 사용)
        name (str): 리그 네이밍 프리픽스
        num_nulls (int): curve 위에 균등 분배할 motionPath null 개수

    Returns:
        dict: 주요 결과 노드 모음
    """
    if cmds.objExists('{}_rig_GRP'.format(name)):
        cmds.delete('{}_rig_GRP'.format(name))

    base, tip, axis = _get_axis_endpoints(mesh)
    g = _build_groups(name)

    base_crv, base_shape = _build_base_curve(name, base, tip, num_nulls, g['crv'])
    up_loc = _build_up_vector(name, g['sys'], axis, base)
    mps, nulls = _build_mp_nulls(name, num_nulls, base_shape, up_loc, g['null'])

    result = {
        'rig_grp': g['rig'],
        'base_curve': base_crv,
        'up_loc': up_loc,
        'motion_paths': mps,
        'nulls': nulls,
        'axis': axis,
    }
    print('=' * 60)
    print('Tentacle Base 완료: {}'.format(name))
    print('  base->tip axis : {}'.format(axis))
    print('  MP null 개수   : {}'.format(len(nulls)))
    print('  base curve     : {}'.format(base_crv))
    print('=' * 60)
    return result


if __name__ == '__main__':
    build_tentacle_base()
