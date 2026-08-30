# -*- coding: utf-8 -*-
"""============================================================================
NURBS Surface 기반 Spline_IK 모듈 Auto-Rig

프로덕션 레퍼런스 씬(tentacle_rig_proto.ma)을 Maya MCP로 리버스엔지니어링해서
재구성한 구조. tentacle_autorig.py(커브+splineIK) 와 달리 NURBS 서피스를
변형체로 쓰고, follicle을 "커브 위 길이보존 보정 -> 현재 서피스에 재투영"
2단계로 샘플링해서 stretch와 무관하게 항상 균등하게 재배치되는 게 핵심이다.

하나의 "모듈"(build_spline_ik_module)이 촉수 하나 전체를 만든다. 레퍼런스 씬의
TopTentacle 브랜치가 라이브로 메인에 붙어있는 게 아니라 완전히 독립된 정적
모듈(개수만 축소)이었던 것처럼, 이 모듈은 world_matrix로 원하는 자리에 배치만
하면 몇 번이든 반복 호출해서 보조 촉수(가지)를 만들 수 있다 (재귀적으로
쓰려면 그냥 이 함수를 다시 호출하면 됨 -- 모듈 사이에 라이브 부모 연결은
레퍼런스 씬에도 없었다).

파이프라인 (한 모듈 기준):
    1. mesh 중심선(base curve)에 수직인 평면(직선) 프로파일을 extrude해서 flat
       리본형 NSF(NURBS surface) 생성 (원형 튜브로 만들면 follicle 재투영 결과가
       튜브 표면으로 오프셋되어 컨트롤/조인트가 중심선을 벗어나기 때문에 평면형을 쓴다)
    2. IK 컨트롤(num_ik_ctrls, 서로 독립) -> 숨은 NurbsBind_JNT -> skinCluster로
       NSF를 직접 변형(선형 tent falloff weight)
    3. NSF에서 curveFromSurfaceIso로 라이브 CRV 추출(V=0.5) -> curveInfo로
       실시간 arcLength 측정
    4. Stretch 게이트 체인: attr_ctrl.Stretch(0~10)를 0~1로 반전한
       preserveLength와, "현재길이>=레스트길이" condition을 곱해 활성 플래그를
       만들고, blendTwoAttr로 레스트길이/현재길이 중 하나를 선택(preserveLengthIndex).
       Stretch=0(기본)이면 늘어난 만큼 U를 앞으로 당겨서 세그먼트 길이가 항상
       레스트값으로 유지(무늘어남 체인), Stretch=10이면 그냥 균등 U(자유 스트레치).
    5. 각 skin joint 자리(num_skin_jnts개)마다 위 보정 U로 CRV 위 위치/회전을
       motionPath로 샘플 -> decomposeMatrix -> closestPointOnSurface로 "현재
       변형된 NSF" 위의 실제 UV로 재투영(parameterV는 0.5 고정) -> follicle.
       (커브 파라미터화와 서피스 파라미터화가 정확히 안 맞기 때문에 재투영이
       필요함)
    6. follicle 출력을 실제 부모-자식 체인인 Attach_JNT에 parentConstraint로
       그대로 물림.
    7. multMatrix로 "Attach[i]의 Attach[i-1] 기준 로컬 행렬"을 계산해
       FK_NUL[i].translate/rotate에 연결 -- 서피스 변형이 FK_NUL을 직접
       구동하고(라이브), 그 자식인 FK_CON(레스트 0)이 애니메이터용 추가 오프셋,
       다시 그 자식인 FK_JNT(항상 0)가 최종 스킨 소스가 되는 3단 구조.
    8. Skin_JNT(따로 평평하게 배치)는 FK_JNT를 parentConstraint(translate+rotate)로
       그대로 복사 -- 실제 캐릭터 스키닝에 쓰는 조인트.
    9. Twist start/end 컨트롤: 첫/끝 FK_CON의 world를 parentConstraint로 그대로
       받는다 (advanced twist 참조용).
   10. Scale 컨트롤(num_scale_ctrls개, 등간격): 인접한 두 Scale_CON의 scale을
       각 skin joint 자리의 정규화 위치로 pairBlend 보간하고, 전역 thickness로
       한 번 더 곱해서 FK_JNT.scale에 직결(볼륨/두께 컨트롤).
   11. RigMeta network 노드에 모듈 메타데이터(partName/side/moduleType 등)를
       기록 -- 레퍼런스 씬의 "Spline_IK" 모듈형 시스템을 흉내낸 것.

:Example:
    from python2.rigging import tentacle_autorig_nsf as nsf_rig
    import importlib
    importlib.reload(nsf_rig)

    # 메인 촉수
    main = nsf_rig.build_spline_ik_module(mesh='pSphere1', name='tentacle', side='L')

    # 메인 촉수 표면 위 특정 지점에서 갈라지는 보조 촉수(Top 브랜치) --
    # 레퍼런스 씬처럼 라이브 부착이 아니라 원하는 위치에 정적으로 배치한다.
    branch_mtx = cmds.xform(main['fk_ctrls'][15], q=True, ws=True, m=True)
    nsf_rig.build_spline_ik_module(mesh='pSphere1', name='topTentacle', side='L',
                                    world_matrix=branch_mtx, num_ik_ctrls=5,
                                    num_skin_jnts=9, width=1.0)
============================================================================"""
import maya.cmds as cmds


# ----------------------------------------------------------------------------
# 공용 유틸 (tentacle_autorig.py와 동일 컨벤션)
# ----------------------------------------------------------------------------

def _sample_params(num_points, include_tip=True):
    """0~1 사이 균등 분배된 파라미터 리스트."""
    if num_points <= 1:
        return [0.0]
    denom = float(num_points - 1) if include_tip else float(num_points)
    return [i / denom for i in range(num_points)]


def _sample_curve_frames(curve, num_points, up_loc):
    """curve 위에서 arc-length 기준 위치 + tangent 기준 회전을 함께 샘플링한다."""
    shape = cmds.listRelatives(curve, shapes=True, ni=True, fullPath=True)[0]
    tmp_mp = cmds.createNode('motionPath', n='__sampleCurveFrame_MP')
    cmds.connectAttr(shape + '.worldSpace[0]', tmp_mp + '.geometryPath')
    cmds.setAttr(tmp_mp + '.fractionMode', 1)
    cmds.setAttr(tmp_mp + '.follow', 1)
    cmds.setAttr(tmp_mp + '.frontAxis', 0)
    cmds.setAttr(tmp_mp + '.upAxis', 1)
    cmds.setAttr(tmp_mp + '.worldUpType', 2)
    cmds.connectAttr(up_loc + '.worldMatrix[0]', tmp_mp + '.worldUpMatrix')
    frames = []
    for u in _sample_params(num_points, include_tip=True):
        cmds.setAttr(tmp_mp + '.uValue', u)
        pos = tuple(cmds.getAttr(tmp_mp + '.allCoordinates')[0])
        rot = tuple(cmds.getAttr(tmp_mp + '.rotate')[0])
        frames.append((pos, rot))
    cmds.delete(tmp_mp)
    return frames


def _get_axis_endpoints(mesh, axis='y'):
    """mesh의 world bounding box 중심을 지나는 축의 양 끝점을 구한다."""
    bbox = cmds.exactWorldBoundingBox(mesh)
    if axis is None:
        lens = {'x': bbox[3] - bbox[0], 'y': bbox[4] - bbox[1], 'z': bbox[5] - bbox[2]}
        axis = max(lens, key=lens.get)
    mid = ((bbox[0] + bbox[3]) / 2.0, (bbox[1] + bbox[4]) / 2.0, (bbox[2] + bbox[5]) / 2.0)
    base = list(mid)
    tip = list(mid)
    idx = {'x': 0, 'y': 1, 'z': 2}[axis]
    lo = [bbox[0], bbox[1], bbox[2]][idx]
    hi = [bbox[3], bbox[4], bbox[5]][idx]
    base[idx], tip[idx] = lo, hi
    return tuple(base), tuple(tip), axis


def _get_centerline_points(mesh, axis, base, tip, num_points):
    """mesh의 실제 vertex 분포를 따라가는 중심선 포인트 리스트."""
    idx = {'x': 0, 'y': 1, 'z': 2}[axis]
    flat = cmds.xform('{}.vtx[*]'.format(mesh), q=True, ws=True, t=True)
    verts = [(flat[i], flat[i + 1], flat[i + 2]) for i in range(0, len(flat), 3)]

    lo, hi = base[idx], tip[idx]
    span = hi - lo
    half_band = (span / float(num_points - 1)) * 0.75 if num_points > 1 and span else abs(span) or 1.0

    points = []
    for i in range(num_points):
        t = i / float(num_points - 1)
        target = lo + span * t
        bucket = [v for v in verts if abs(v[idx] - target) <= half_band]
        if not bucket:
            bucket = sorted(verts, key=lambda v: abs(v[idx] - target))[:max(3, len(verts) // num_points)]
        centroid = [sum(v[a] for v in bucket) / len(bucket) for a in range(3)]
        centroid[idx] = target
        points.append(tuple(centroid))
    return points


def _make_ctrl(n, radius, pos, rot=None, normal=(0, 1, 0)):
    ctrl = cmds.circle(n=n, r=radius, nr=normal, ch=False)[0]
    off = cmds.createNode('transform', n='{}_OFF'.format(n))
    cmds.parent(ctrl, off)
    cmds.xform(off, ws=True, t=pos)
    if rot is not None:
        cmds.xform(off, ws=True, ro=rot)
    return ctrl, off


# ----------------------------------------------------------------------------
# 그룹 / NSF / IK
# ----------------------------------------------------------------------------

def _build_module_groups(name, side):
    g = {}
    prefix = '{}_{}'.format(side, name)
    g['xform'] = cmds.createNode('transform', n='{}_transform_GRP'.format(prefix))
    g['none'] = cmds.createNode('transform', n='{}_noneTransform_GRP'.format(prefix))

    g['subik'] = cmds.createNode('transform', n='{}_SubIK_GRP'.format(prefix), p=g['xform'])
    g['ik_ctl'] = cmds.createNode('transform', n='{}_IK_controller_GRP'.format(prefix), p=g['subik'])
    g['attach_jnt'] = cmds.createNode('transform', n='{}_Attach_joint_GRP'.format(prefix), p=g['subik'])
    g['nurbsbind_jnt'] = cmds.createNode('transform', n='{}_NurbsBind_joint_GRP'.format(prefix), p=g['subik'])

    g['fk'] = cmds.createNode('transform', n='{}_FK_GRP'.format(prefix), p=g['xform'])
    g['skin_jnt'] = cmds.createNode('transform', n='{}_Skin_joint_GRP'.format(prefix), p=g['xform'])
    g['twistscale'] = cmds.createNode('transform', n='{}_TwistScale_GRP'.format(prefix), p=g['xform'])
    g['twist'] = cmds.createNode('transform', n='{}_Twist_GRP'.format(prefix), p=g['twistscale'])
    g['scale'] = cmds.createNode('transform', n='{}_Scale_GRP'.format(prefix), p=g['twistscale'])

    g['sys'] = cmds.createNode('transform', n='{}_SYS_GRP'.format(prefix), p=g['none'])
    cmds.setAttr(g['sys'] + '.visibility', 0)
    return g, prefix


def _build_planar_surface(prefix, base_curve, up_loc, width, none_grp, sys_grp, history=False):
    """base_curve를 따라 평면(직선) 프로파일을 extrude한 flat 리본형 NSF 생성.

    원형 프로파일로 튜브를 만들면 follicle이 "커브 위 위치 -> 현재 서피스에
    재투영" 할 때 튜브 표면(반지름만큼 옆으로 오프셋된 위치)으로 떨어져서
    컨트롤/조인트가 원래 있어야 할 중심선에서 벗어나게 된다. 프로파일을 curve에
    수직인 직선(폭=width)으로 바꾸면, follicle이 항상 폭 방향 정중앙(0.5)에서
    재투영되므로 결과가 정확히 base_curve(=중심선) 위에 놓인다.

    history=True면 construction history를 살려서 base_curve가 계속 라이브로
    NSF를 구동하게 한다 -- 상위 레이어의 curve를 그대로 base_curve로 재사용하는
    세부(Top) 레이어에서, 상위 레이어가 움직이면 이 레이어도 그 위에서 같이
    따라가면서 자기 IK로 얹은 디테일만 추가로 더해지게 하는 데 필요하다.
    """
    start_pos = cmds.pointPosition(base_curve + '.cv[0]', world=True)
    start_rot = _sample_curve_frames(base_curve, 2, up_loc)[0][1]

    half = width / 2.0
    profile = cmds.curve(n='__{}_profile_TMP'.format(prefix), d=1, p=[(0, 0, -half), (0, 0, half)])
    cmds.xform(profile, ws=True, ro=start_rot)
    cmds.xform(profile, ws=True, t=start_pos)

    surf = cmds.extrude(profile, base_curve, n='{}_NSF'.format(prefix), ch=history, rn=False,
                         po=0, et=2, ucp=1, fpt=1, upn=1, rotation=0, scale=1, rsp=1)[0]
    if history:
        cmds.parent(profile, sys_grp)
    else:
        cmds.delete(profile)
    cmds.parent(surf, none_grp)
    surf_shape = cmds.listRelatives(surf, shapes=True, ni=True, fullPath=True)[0]
    return surf, surf_shape


def _build_iso_curve(prefix, surf_shape, none_grp):
    """NSF의 단면(U)=0.5 위치를 따라가는, 길이(V) 방향 전체를 도는 isoparm을
    라이브로 추출한 CRV (서피스가 변형되면 같이 움직임)."""
    iso = cmds.createNode('curveFromSurfaceIso', n='{}_CFSI'.format(prefix))
    cmds.setAttr(iso + '.isoparmDirection', 1)  # U 고정, V로 뻗는 커브
    cmds.setAttr(iso + '.isoparmValue', 0.5)
    cmds.connectAttr(surf_shape + '.local', iso + '.inputSurface')

    crv = cmds.createNode('transform', n='{}_CRV'.format(prefix), p=none_grp)
    cmds.setAttr(crv + '.visibility', 0)
    crv_shape = cmds.createNode('nurbsCurve', n='{}_CRVShape'.format(prefix), p=crv)
    cmds.connectAttr(iso + '.outputCurve', crv_shape + '.create')
    return crv, crv_shape


def _build_up_vector(prefix, sys_grp, axis, base):
    up_off = cmds.createNode('transform', n='{}_up_OFF'.format(prefix), p=sys_grp)
    up_loc = cmds.spaceLocator(n='{}_up_LOC'.format(prefix))[0]
    cmds.parent(up_loc, up_off)
    cmds.xform(up_off, ws=True, t=base)
    cmds.move(5, 0, 0, up_loc, r=True, os=True)
    if axis == 'y':
        cmds.setAttr(up_loc + '.rotateX', 90)
    return up_loc


def _build_ik_setup(prefix, num_ik_ctrls, ik_ctl_grp, nurbsbind_grp, base_curve, up_loc,
                     surf, surf_shape):
    """IK 컨트롤(독립) -> 숨은 NurbsBind_JNT -> skinCluster로 NSF를 직접 변형."""
    frames = _sample_curve_frames(base_curve, num_ik_ctrls, up_loc)
    ik_ctrls, bind_jnts = [], []
    for i, (pos, rot) in enumerate(frames):
        c, off = _make_ctrl('{}_IK_{:02d}_CON'.format(prefix, i), 1.4, pos, rot=rot)
        cmds.setAttr(c + '.overrideEnabled', 1)
        cmds.setAttr(c + '.overrideColor', 13)
        cmds.parent(off, ik_ctl_grp)

        cmds.select(cl=True)
        jnt = cmds.joint(n='{}_NurbsBind_{:02d}_JNT'.format(prefix, i))
        cmds.setAttr(jnt + '.visibility', 0)
        cmds.parent(jnt, c)
        cmds.setAttr(jnt + '.translate', 0, 0, 0)
        cmds.setAttr(jnt + '.rotate', 0, 0, 0)
        cmds.setAttr(jnt + '.jointOrient', 0, 0, 0)
        cmds.parent(jnt, nurbsbind_grp)
        cmds.pointConstraint(c, jnt, mo=False)
        cmds.orientConstraint(c, jnt, mo=False)

        ik_ctrls.append(c)
        bind_jnts.append(jnt)

    # 레퍼런스 씬(skinCluster3) 그대로 -- 커스텀 weight 없이 Maya 기본 smooth
    # bind(Classic Linear, Closest Distance, dropoffRate=4.0, maxInfluences=5)를
    # 그대로 쓴다. 인접 CV가 부드러운 종형 falloff로 자연스럽게 섞인다.
    skin = cmds.skinCluster(bind_jnts + [surf], n='{}_ik_SKIN'.format(prefix),
                             tsb=True, bm=0, sm=0, nw=1, mi=5, dr=4.0)[0]
    return ik_ctrls, bind_jnts


# ----------------------------------------------------------------------------
# Stretch 게이트 + follicle 재투영
# ----------------------------------------------------------------------------

def _add_rig_attrs(ctrl, surf):
    cmds.addAttr(ctrl, ln='Stretch', at='double', min=0, max=10, dv=0, k=True)
    # 레퍼런스 씬에도 Squash는 존재하지만 실제로는 어디에도 연결되지 않은
    # 미사용 attribute였다 -- 여기서도 그 상태(플레이스홀더)를 그대로 둔다.
    cmds.addAttr(ctrl, ln='Squash', at='double', min=0, max=10, dv=0, k=True)
    cmds.addAttr(ctrl, ln='Slide', at='double', min=-10, max=10, dv=0, k=True)
    cmds.addAttr(ctrl, ln='NsfVis', at='bool', dv=True, k=True)
    cmds.connectAttr(ctrl + '.NsfVis', surf + '.visibility')


def _build_stretch_gate(prefix, crv_shape, attr_ctrl):
    """CRV의 rest/현재 arcLength를 비교해 "길이보존 활성" 게이트와, 활성일 때
    쓸 preserveLengthIndex(레스트~현재 사이에서 선택된 길이)를 만든다.
    """
    rest_length = cmds.arclen(cmds.listRelatives(crv_shape, p=True)[0])

    curve_info = cmds.createNode('curveInfo', n='{}_CIF'.format(prefix))
    cmds.connectAttr(crv_shape + '.worldSpace[0]', curve_info + '.inputCurve')

    stretch_srg = cmds.createNode('setRange', n='{}_stretch_SRG'.format(prefix))
    cmds.setAttr(stretch_srg + '.oldMaxX', 10)
    cmds.setAttr(stretch_srg + '.maxX', 1)
    cmds.connectAttr(attr_ctrl + '.Stretch', stretch_srg + '.valueX')

    reverse = cmds.createNode('reverse', n='{}_stretch_REV'.format(prefix))
    cmds.connectAttr(stretch_srg + '.outValueX', reverse + '.inputX')

    crv = cmds.listRelatives(crv_shape, p=True)[0]
    cmds.addAttr(crv, ln='restCurveLength', at='double', dv=rest_length)
    cmds.addAttr(crv, ln='preserveLength', at='double', min=0, max=1, dv=1)
    cmds.connectAttr(reverse + '.outputX', crv + '.preserveLength')

    active_cnd = cmds.createNode('condition', n='{}_active_CND'.format(prefix))
    cmds.setAttr(active_cnd + '.operation', 3)  # >=
    cmds.setAttr(active_cnd + '.colorIfTrueR', 1)
    cmds.setAttr(active_cnd + '.colorIfFalseR', 0)
    cmds.connectAttr(curve_info + '.arcLength', active_cnd + '.firstTerm')
    cmds.connectAttr(crv + '.restCurveLength', active_cnd + '.secondTerm')

    active_flag = cmds.createNode('multDoubleLinear', n='{}_activeFlag_MDL'.format(prefix))
    cmds.connectAttr(crv + '.preserveLength', active_flag + '.input1')
    cmds.connectAttr(active_cnd + '.outColorR', active_flag + '.input2')

    length_index = cmds.createNode('blendTwoAttr', n='{}_lengthIndex_BTA'.format(prefix))
    cmds.connectAttr(crv + '.restCurveLength', length_index + '.input[0]')
    cmds.connectAttr(curve_info + '.arcLength', length_index + '.input[1]')
    cmds.connectAttr(active_flag + '.output', length_index + '.attributesBlender')

    ratio = cmds.createNode('multiplyDivide', n='{}_lengthRatio_MPD'.format(prefix))
    cmds.setAttr(ratio + '.operation', 2)  # divide
    cmds.setAttr(ratio + '.input1X', rest_length)
    cmds.connectAttr(length_index + '.output', ratio + '.input2X')

    return crv, curve_info, ratio + '.outputX'


def _build_uvalue_chain(prefix, num_points, ratio_plug, attr_ctrl):
    """각 포인트의 레스트 U(균등분배)에 length ratio를 곱하고, Slide 오프셋을
    더해서 최종 motionPath uValue plug를 만든다 (레스트=균등, 늘어나면 앞으로
    당겨져서 세그먼트 길이가 레스트값으로 유지됨).
    """
    slide_norm = cmds.createNode('multDoubleLinear', n='{}_slideNorm_MDL'.format(prefix))
    cmds.setAttr(slide_norm + '.input2', 0.1)
    cmds.connectAttr(attr_ctrl + '.Slide', slide_norm + '.input1')

    plugs = []
    for i, rest_u in enumerate(_sample_params(num_points, include_tip=True)):
        scaled = cmds.createNode('multDoubleLinear', n='{}_uValue_{:02d}_MDL'.format(prefix, i))
        cmds.setAttr(scaled + '.input1', rest_u)
        cmds.connectAttr(ratio_plug, scaled + '.input2')

        offset = cmds.createNode('addDoubleLinear', n='{}_uValue_{:02d}_ADL'.format(prefix, i))
        cmds.connectAttr(scaled + '.output', offset + '.input1')
        cmds.connectAttr(slide_norm + '.output', offset + '.input2')

        clamp = cmds.createNode('clamp', n='{}_uValue_{:02d}_CLAMP'.format(prefix, i))
        cmds.setAttr(clamp + '.minR', 0)
        cmds.setAttr(clamp + '.maxR', 1)
        cmds.connectAttr(offset + '.output', clamp + '.inputR')
        plugs.append(clamp + '.outputR')
    return plugs


def _build_follicles(prefix, crv_shape, surf, surf_shape, uvalue_plugs, up_loc, none_grp):
    """CRV에서 U보정 위치 샘플 -> 현재 NSF에 재투영해서 follicle을 배치한다."""
    follicles = []
    for i, u_plug in enumerate(uvalue_plugs):
        mp = cmds.createNode('motionPath', n='{}_{:02d}_MPT'.format(prefix, i))
        cmds.connectAttr(crv_shape + '.worldSpace[0]', mp + '.geometryPath')
        cmds.setAttr(mp + '.fractionMode', 1)
        cmds.setAttr(mp + '.follow', 1)
        cmds.setAttr(mp + '.frontAxis', 0)
        cmds.setAttr(mp + '.upAxis', 1)
        cmds.setAttr(mp + '.worldUpType', 2)
        cmds.connectAttr(up_loc + '.worldMatrix[0]', mp + '.worldUpMatrix')
        cmds.connectAttr(u_plug, mp + '.uValue', f=True)

        loc = cmds.spaceLocator(n='{}_{:02d}_LOC'.format(prefix, i))[0]
        cmds.setAttr(loc + '.visibility', 0)
        cmds.parent(loc, none_grp)
        cmds.connectAttr(mp + '.allCoordinates', loc + '.translate')
        cmds.connectAttr(mp + '.rotate', loc + '.rotate')

        dcm = cmds.createNode('decomposeMatrix', n='{}_{:02d}_DCM'.format(prefix, i))
        cmds.connectAttr(loc + '.worldMatrix[0]', dcm + '.inputMatrix')

        cps = cmds.createNode('closestPointOnSurface', n='{}_{:02d}_CPS'.format(prefix, i))
        cmds.connectAttr(surf_shape + '.worldSpace[0]', cps + '.inputSurface')
        cmds.connectAttr(dcm + '.outputTranslate', cps + '.inPosition')

        flc_shape = cmds.createNode('follicle', n='{}_{:02d}_FLCShape'.format(prefix, i))
        flc = cmds.listRelatives(flc_shape, p=True)[0]
        flc = cmds.rename(flc, '{}_{:02d}_FLC'.format(prefix, i))
        cmds.connectAttr(surf_shape + '.local', flc + '.inputSurface')
        cmds.connectAttr(surf_shape + '.worldMatrix[0]', flc + '.inputWorldMatrix')
        # extrude 서피스는 U=profile(폭), V=path(길이, fixedPath라 0~1 정규화)이다.
        # follicle.parameterU/V는 surface의 실제 U/V에 그대로 매핑되므로, 길이
        # 방향인 V에는 closestPointOnSurface가 구한 값을 연결하고, 폭 방향인
        # U는 항상 정중앙(0.5, =base_curve 위)으로 고정한다.
        cmds.connectAttr(cps + '.parameterV', flc + '.parameterV')
        cmds.setAttr(flc + '.parameterU', 0.5)
        cmds.connectAttr(flc + '.outTranslate', flc + '.translate')
        cmds.connectAttr(flc + '.outRotate', flc + '.rotate')
        cmds.setAttr(flc + '.visibility', 0)
        cmds.parent(flc, none_grp)

        follicles.append(flc)
    return follicles


# ----------------------------------------------------------------------------
# Attach -> FK -> Skin
# ----------------------------------------------------------------------------

def _build_attach_chain(prefix, follicles, attach_grp):
    """follicle 출력을 그대로 물리는 실제 부모-자식 Attach_JNT 체인."""
    jnts = []
    for i, flc in enumerate(follicles):
        cmds.select(cl=True)
        jnt = cmds.joint(n='{}_Attach_{:02d}_JNT'.format(prefix, i))
        cmds.setAttr(jnt + '.visibility', 0)
        jnts.append(jnt)
    for i in range(1, len(jnts)):
        cmds.parent(jnts[i], jnts[i - 1])
    cmds.parent(jnts[0], attach_grp)
    for i, jnt in enumerate(jnts):
        cmds.setAttr(jnt + '.jointOrient', 0, 0, 0)
        pc = cmds.parentConstraint(follicles[i], jnt, mo=False)[0]
        sc = cmds.scaleConstraint(follicles[i], jnt, mo=False)[0]
    return jnts


def _build_fk_from_attach(prefix, attach_jnts, fk_grp):
    """Attach[i]의 Attach[i-1] 기준 로컬행렬을 FK_NUL에 넣는다 -- 서피스 변형이
    NUL을 직접 구동하고, 그 자식 FK_CON(레스트 0)이 애니메이터용 추가 오프셋,
    다시 그 자식 FK_JNT(항상 0)가 최종 스킨 소스가 되는 3단 구조.
    """
    fk_nuls, fk_ctrls, fk_jnts = [], [], []
    for i, attach in enumerate(attach_jnts):
        parent = fk_grp if i == 0 else fk_ctrls[i - 1]
        nul = cmds.createNode('transform', n='{}_FK_{:02d}_NUL'.format(prefix, i), p=parent)

        mm = cmds.createNode('multMatrix', n='{}_FK_{:02d}_MM'.format(prefix, i))
        cmds.connectAttr(attach + '.worldMatrix[0]', mm + '.matrixIn[0]')
        if i == 0:
            cmds.connectAttr(nul + '.parentInverseMatrix[0]', mm + '.matrixIn[1]')
        else:
            cmds.connectAttr(attach_jnts[i - 1] + '.worldInverseMatrix[0]', mm + '.matrixIn[1]')

        dcm = cmds.createNode('decomposeMatrix', n='{}_FK_{:02d}_DCM'.format(prefix, i))
        cmds.connectAttr(mm + '.matrixSum', dcm + '.inputMatrix')
        cmds.connectAttr(dcm + '.outputTranslate', nul + '.translate')
        cmds.connectAttr(dcm + '.outputRotate', nul + '.rotate')

        c = cmds.circle(n='{}_FK_{:02d}_CON'.format(prefix, i), r=1.6, nr=(0, 1, 0), ch=False)[0]
        cmds.setAttr(c + '.overrideEnabled', 1)
        cmds.setAttr(c + '.overrideColor', 6)
        cmds.parent(c, nul)
        cmds.setAttr(c + '.translate', 0, 0, 0)
        cmds.setAttr(c + '.rotate', 0, 0, 0)

        cmds.select(cl=True)
        jnt = cmds.joint(n='{}_FK_{:02d}_JNT'.format(prefix, i))
        cmds.setAttr(jnt + '.visibility', 0)
        cmds.parent(jnt, c)
        cmds.setAttr(jnt + '.translate', 0, 0, 0)
        cmds.setAttr(jnt + '.rotate', 0, 0, 0)
        cmds.setAttr(jnt + '.jointOrient', 0, 0, 0)

        fk_nuls.append(nul)
        fk_ctrls.append(c)
        fk_jnts.append(jnt)
    return fk_nuls, fk_ctrls, fk_jnts


def _build_skin_joints(prefix, fk_jnts, skin_grp):
    """최종 캐릭터 스키닝용 조인트. FK_JNT의 translate+rotate를 그대로 복사."""
    skin_jnts = []
    for i, fk_jnt in enumerate(fk_jnts):
        cmds.select(cl=True)
        jnt = cmds.joint(n='{}_Skin_{:02d}_JNT'.format(prefix, i))
        cmds.parent(jnt, skin_grp)
        cmds.setAttr(jnt + '.jointOrient', 0, 0, 0)
        cmds.parentConstraint(fk_jnt, jnt, mo=False)
        skin_jnts.append(jnt)
    return skin_jnts


def _build_fine_offset_layer(prefix, main_fk_jnts, fk_grp):
    """메인 레이어의 FK_JNT 1:1마다 가벼운 NUL(parentConstraint로 메인을 라이브
    추적)->CON(레스트 0, 애니메이터 세부 오프셋)->Skin_JNT(leaf, 최종 캐릭터
    스키닝용)만 쌓는다. 별도 NSF/IK/Attach 파이프라인이 없는 얇은 레이어라서,
    메인이 움직이면 그대로 따라가고 여기서 추가한 오프셋만 위에 더해진다
    (레퍼런스 씬의 TopFK_GRP가 실제로 이런 가벼운 구조였다).
    """
    fk_cons, skin_jnts = [], []
    for i, main_jnt in enumerate(main_fk_jnts):
        nul = cmds.createNode('transform', n='{}_FK_{:02d}_NUL'.format(prefix, i), p=fk_grp)
        cmds.parentConstraint(main_jnt, nul, mo=False)

        c = cmds.circle(n='{}_FK_{:02d}_CON'.format(prefix, i), r=1.0, nr=(0, 1, 0), ch=False)[0]
        cmds.setAttr(c + '.overrideEnabled', 1)
        cmds.setAttr(c + '.overrideColor', 6)
        cmds.parent(c, nul)
        cmds.setAttr(c + '.translate', 0, 0, 0)
        cmds.setAttr(c + '.rotate', 0, 0, 0)

        cmds.select(cl=True)
        jnt = cmds.joint(n='{}_Skin_{:02d}_JNT'.format(prefix, i))
        cmds.parent(jnt, c)
        cmds.setAttr(jnt + '.translate', 0, 0, 0)
        cmds.setAttr(jnt + '.rotate', 0, 0, 0)
        cmds.setAttr(jnt + '.jointOrient', 0, 0, 0)

        fk_cons.append(c)
        skin_jnts.append(jnt)
    return fk_cons, skin_jnts


def _build_twist_ctrls(prefix, fk_ctrls, twist_grp):
    ctrls = []
    for label, fk_ctrl in (('start', fk_ctrls[0]), ('end', fk_ctrls[-1])):
        pos = cmds.xform(fk_ctrl, q=True, ws=True, t=True)
        c, off = _make_ctrl('{}_Twist_{}_CON'.format(prefix, label), 1.2, pos)
        cmds.setAttr(c + '.overrideEnabled', 1)
        cmds.setAttr(c + '.overrideColor', 17)
        cmds.parent(off, twist_grp)
        cmds.parentConstraint(fk_ctrl, off, mo=False)
        ctrls.append(c)
    return ctrls[0], ctrls[1]


def _build_scale_ctrls(prefix, num_scale_ctrls, fk_jnts, scale_grp):
    """등간격 Scale 컨트롤을 배치하고, 각 fk_jnt 자리에서 인접한 두 Scale_CON의
    scale을 정규화 위치로 pairBlend 보간한 뒤 전역 thickness를 곱해
    FK_JNT.scale에 직결한다.
    """
    scale_params = _sample_params(num_scale_ctrls, include_tip=True)
    scale_ctrls = []
    for i, u in enumerate(scale_params):
        pos = cmds.xform(fk_jnts[int(round(u * (len(fk_jnts) - 1)))], q=True, ws=True, t=True)
        c, off = _make_ctrl('{}_Scale_{:02d}_CON'.format(prefix, i), 1.0, pos)
        cmds.setAttr(c + '.overrideEnabled', 1)
        cmds.setAttr(c + '.overrideColor', 21)
        cmds.parent(off, scale_grp)
        scale_ctrls.append(c)

    attr_ctrl = scale_ctrls[0]
    cmds.addAttr(attr_ctrl, ln='thickness', at='double', min=0, dv=1, k=True)

    fk_params = _sample_params(len(fk_jnts), include_tip=True)
    for i, (jnt, u) in enumerate(zip(fk_jnts, fk_params)):
        lo = 0
        for j in range(len(scale_params)):
            if scale_params[j] <= u:
                lo = j
            else:
                break
        hi = min(lo + 1, len(scale_params) - 1)
        t = 0.0 if lo == hi else max(0.0, min(1.0, (u - scale_params[lo]) / (scale_params[hi] - scale_params[lo])))

        pb = cmds.createNode('pairBlend', n='{}_Scale_{:02d}_PBL'.format(prefix, i))
        cmds.setAttr(pb + '.weight', t)
        cmds.connectAttr(scale_ctrls[lo] + '.scale', pb + '.inTranslate1')
        cmds.connectAttr(scale_ctrls[hi] + '.scale', pb + '.inTranslate2')

        for axis in ('X', 'Y', 'Z'):
            mdl = cmds.createNode('multDoubleLinear', n='{}_Thickness_{:02d}{}_MDL'.format(prefix, i, axis))
            cmds.connectAttr(pb + '.outTranslate' + axis, mdl + '.input1')
            cmds.connectAttr(attr_ctrl + '.thickness', mdl + '.input2')
            cmds.connectAttr(mdl + '.output', jnt + '.scale' + axis, f=True)

    return scale_ctrls, attr_ctrl


def _build_rig_meta(prefix, name, side, xform_grp, attach_jnts, ik_ctrls, module_length):
    meta = cmds.createNode('network', n='{}_RigMeta_NTW'.format(prefix))
    cmds.addAttr(meta, ln='partName', dt='string')
    cmds.setAttr(meta + '.partName', name, type='string')
    cmds.addAttr(meta, ln='side', dt='string')
    cmds.setAttr(meta + '.side', side, type='string')
    cmds.addAttr(meta, ln='moduleType', dt='string')
    cmds.setAttr(meta + '.moduleType', 'Spline_IK', type='string')
    cmds.addAttr(meta, ln='version', at='double', dv=1.0)
    cmds.addAttr(meta, ln='jointCount', at='long', dv=len(attach_jnts))
    cmds.addAttr(meta, ln='conCount', at='long', dv=len(ik_ctrls))
    cmds.addAttr(meta, ln='moduleLength', at='double', dv=module_length)
    cmds.addAttr(meta, ln='buildState', dt='string')
    cmds.setAttr(meta + '.buildState', 'Base', type='string')
    cmds.addAttr(meta, ln='topGroup', at='message')
    cmds.connectAttr(xform_grp + '.message', meta + '.topGroup')
    cmds.addAttr(meta, ln='joints', at='message', multi=True)
    for i, jnt in enumerate(attach_jnts):
        cmds.connectAttr(jnt + '.message', '{}.joints[{}]'.format(meta, i))
    cmds.addAttr(meta, ln='controls', at='message', multi=True)
    for i, ctrl in enumerate(ik_ctrls):
        cmds.connectAttr(ctrl + '.message', '{}.controls[{}]'.format(meta, i))
    cmds.addAttr(meta, ln='configController', at='message')
    return meta


# ----------------------------------------------------------------------------
# 모듈 진입점
# ----------------------------------------------------------------------------

def build_spline_ik_module(mesh='pSphere1', name='tentacle', side='L', axis='y',
                            num_skin_jnts=25, num_ik_ctrls=9, num_scale_ctrls=5,
                            width=2.0, world_matrix=None, parent_curve=None,
                            build_twist_scale=True):
    """NSF 기반 Spline_IK 모듈 하나를 통째로 빌드한다.

    NSF는 원형 튜브가 아니라 base_curve에 수직인 평면(직선) 프로파일을 extrude한
    flat 리본이다 -- 튜브로 만들면 follicle 재투영 결과가 튜브 표면(반지름만큼
    옆으로 오프셋된 위치)에 떨어져서 컨트롤/조인트가 실제 중심선에서 벗어난다.

    Arguments:
        mesh (str): 촉수 형상 스탠드인 (중심선 추정용). parent_curve를 쓰면 무시된다.
        name (str): 모듈 이름 (RigMeta partName)
        side (str): 'L'/'R' 등 사이드 프리픽스
        axis (str): 위/전방 축 기준('x'/'y'/'z', None이면 최장축 자동감지) --
            up-vector 계산에 쓰인다. parent_curve를 쓸 때도 원본 레이어와 같은
            값을 넘겨야 한다.
        num_skin_jnts (int): 최종 Skin/FK/Attach 조인트 개수 (전부 1:1)
        num_ik_ctrls (int): NSF를 변형시키는 IK 컨트롤 개수(독립)
        num_scale_ctrls (int): 두께 컨트롤 개수(등간격)
        width (float): NSF 평면 프로파일의 폭 (follicle은 항상 이 폭의 정중앙에서
            재투영되므로 결과 위치에는 영향 없음 -- 순수 스킨 안정성/시각화용)
        world_matrix (list[16] or None): 모듈 전체를 배치할 world matrix.
            world_matrix를 쓰면 완전히 독립된 정적 보조 모듈(레퍼런스 씬의
            TopTentacle이 실제로는 이런 독립 브랜치였다)이 된다. 같은 구간을
            덮는 세부 조정 레이어를 만들려면 world_matrix 대신 parent_curve를
            쓴다.
        parent_curve (str or None): 지정하면 mesh 중심선을 새로 뽑는 대신 이
            커브(다른 모듈의 result['curve'])를 그대로 base_curve로 재사용하고,
            NSF도 construction history를 살려서(ch=True) 그 커브에 라이브로
            묶는다. 상위 레이어가 움직이면 이 레이어의 NSF 베이스 모양도 같이
            따라가고, 그 위에 이 레이어 자신의 IK가 만드는 디테일이 더해지는
            "coarse layer 위의 fine layer" 구조가 된다 (build_tentacle_with_top_layer
            참고).
        build_twist_scale (bool): False면 Twist/Scale 컨트롤을 만들지 않는다
            (여러 레이어를 쌓을 때 최종 레이어에만 1세트 두고 싶을 때 False로).

    Returns:
        dict: 주요 결과 노드 모음
    """
    g, prefix = _build_module_groups(name, side)

    if parent_curve is not None:
        base = cmds.pointPosition(parent_curve + '.cv[0]', world=True)
        base_curve = cmds.duplicate(parent_curve, n='{}_baseGuide_CRV'.format(prefix))[0]
        cmds.parent(base_curve, g['sys'])
        src_shape = cmds.listRelatives(parent_curve, shapes=True, ni=True, fullPath=True)[0]
        dup_shape = cmds.listRelatives(base_curve, shapes=True, ni=True, fullPath=True)[0]
        cmds.connectAttr(src_shape + '.worldSpace[0]', dup_shape + '.create', force=True)
    else:
        base, tip, axis = _get_axis_endpoints(mesh, axis)
        positions = _get_centerline_points(mesh, axis, base, tip, max(num_ik_ctrls, 4))
        base_curve = cmds.curve(n='{}_baseGuide_CRV'.format(prefix), d=3, p=positions)
        cmds.rebuildCurve(base_curve, ch=False, rpo=True, rt=0, end=1, kr=0, kcp=1,
                           kep=1, kt=0, s=max(len(positions) - 3, 1), d=3)
        cmds.parent(base_curve, g['sys'])

    up_loc = _build_up_vector(prefix, g['sys'], axis, base)

    surf, surf_shape = _build_planar_surface(prefix, base_curve, up_loc, width, g['none'], g['sys'],
                                              history=(parent_curve is not None))
    crv, crv_shape = _build_iso_curve(prefix, surf_shape, g['none'])

    ik_ctrls, bind_jnts = _build_ik_setup(prefix, num_ik_ctrls, g['ik_ctl'], g['nurbsbind_jnt'],
                                          base_curve, up_loc, surf, surf_shape)
    attr_ctrl = ik_ctrls[-1]
    _add_rig_attrs(attr_ctrl, surf)

    crv, curve_info, ratio_plug = _build_stretch_gate(prefix, crv_shape, attr_ctrl)
    uvalue_plugs = _build_uvalue_chain(prefix, num_skin_jnts, ratio_plug, attr_ctrl)
    follicles = _build_follicles(prefix, crv_shape, surf, surf_shape, uvalue_plugs, up_loc, g['none'])

    attach_jnts = _build_attach_chain(prefix, follicles, g['attach_jnt'])
    fk_nuls, fk_ctrls, fk_jnts = _build_fk_from_attach(prefix, attach_jnts, g['fk'])
    skin_jnts = _build_skin_joints(prefix, fk_jnts, g['skin_jnt'])

    if build_twist_scale:
        twist_start, twist_end = _build_twist_ctrls(prefix, fk_ctrls, g['twist'])
        scale_ctrls, thickness_ctrl = _build_scale_ctrls(prefix, num_scale_ctrls, fk_jnts, g['scale'])
    else:
        twist_start = twist_end = thickness_ctrl = None
        scale_ctrls = []

    module_length = cmds.arclen(crv)
    meta = _build_rig_meta(prefix, name, side, g['xform'], attach_jnts, ik_ctrls, module_length)

    if world_matrix is not None:
        cmds.xform(g['xform'], ws=True, m=world_matrix)
        cmds.xform(g['none'], ws=True, m=world_matrix)

    result = {
        'xform_grp': g['xform'],
        'none_grp': g['none'],
        'fk_grp': g['fk'],
        'twist_grp': g['twist'],
        'scale_grp': g['scale'],
        'surface': surf,
        'curve': crv,
        'up_loc': up_loc,
        'ik_ctrls': ik_ctrls,
        'nurbsbind_jnts': bind_jnts,
        'follicles': follicles,
        'attach_jnts': attach_jnts,
        'fk_nuls': fk_nuls,
        'fk_ctrls': fk_ctrls,
        'fk_jnts': fk_jnts,
        'skin_jnts': skin_jnts,
        'twist_start': twist_start,
        'twist_end': twist_end,
        'scale_ctrls': scale_ctrls,
        'thickness_ctrl': thickness_ctrl,
        'attr_ctrl': attr_ctrl,
        'rig_meta': meta,
    }
    print('=' * 60)
    print('Spline_IK 모듈 완료: {}_{}'.format(side, name))
    print('  IK ctrls     : {}'.format(len(ik_ctrls)))
    print('  Skin jnts    : {}'.format(len(skin_jnts)))
    print('  Scale ctrls  : {}'.format(len(scale_ctrls)))
    print('  Stretch/Squash/Slide -> {}'.format(attr_ctrl))
    print('  Thickness    -> {}'.format(thickness_ctrl))
    print('=' * 60)
    return result


def build_tentacle_with_top_layer(mesh='pSphere1', name='tentacle', side='L', axis='y',
                                   num_ik_ctrls=4, num_skin_jnts=25, num_scale_ctrls=5,
                                   width=2.0, top_name=None):
    """메인(coarse) 레이어 위에 가벼운 세부조정(fine) FK 레이어를 얹는 2-레이어
    구조.

    메인은 num_ik_ctrls(적게)로 NSF+IK+Attach+FK 풀 파이프라인을 만들어 전체
    큰 움직임만 담당한다. 세부 레이어는 별도 NSF/IK/Attach가 없는 가벼운
    구조로, 메인의 FK_JNT 1:1마다 parentConstraint로 라이브 추적하는 NUL ->
    애니메이터용 FK_CON(레스트 0) -> 최종 Skin_JNT만 쌓는다 (레퍼런스 씬의
    TopFK_GRP가 실제로 이런 가벼운 구조였다). 조인트 개수(=num_skin_jnts)만큼
    컨트롤이 생기므로 메인의 IK 컨트롤(coarse)보다 자연히 훨씬 많아진다(fine).

    메인을 움직이면 세부 레이어가 그대로 따라가지만(parentConstraint), 세부
    레이어의 FK_CON을 움직여도 메인에는 영향이 없다 -- 단방향 레이어링. 최종
    캐릭터 스키닝에는 이 함수가 리턴하는 'skin_jnts'를 쓰면 된다(메인+세부
    오프셋이 합쳐진 최종 결과). Twist/Scale(볼륨)은 이 최종 레이어에만 1세트
    만든다.

    Arguments:
        num_ik_ctrls (int): 메인(coarse) IK 컨트롤 개수 -- 적게 잡아서 큰
            실루엣만 조절하게 한다.
        num_skin_jnts (int): 최종 조인트 개수 -- 세부 레이어의 FK_CON도 이
            개수만큼 1:1로 생겨서 자연히 "많은" 세부조정 컨트롤이 된다.
        num_scale_ctrls (int): Twist/Scale(볼륨)용 등간격 컨트롤 개수.
        top_name (str): None이면 'top'+name(첫글자 대문자) 사용 (레퍼런스의
            'tentacle'->'topTentacle' 네이밍과 동일 컨벤션).

    Returns:
        dict: {'main': <build_spline_ik_module 결과>, 'fk_grp', 'fk_ctrls',
               'skin_jnts', 'twist_start', 'twist_end', 'scale_ctrls', 'thickness_ctrl'}
    """
    main = build_spline_ik_module(mesh=mesh, name=name, side=side, axis=axis,
                                   num_skin_jnts=num_skin_jnts, num_ik_ctrls=num_ik_ctrls,
                                   width=width, build_twist_scale=False)

    resolved_top_name = top_name or ('top' + name[0].upper() + name[1:])
    prefix_top = '{}_{}'.format(side, resolved_top_name)

    # 레퍼런스 씬도 Top 레이어가 별도의 top-level GRP를 갖지 않고 메인의
    # transform_GRP 밑에 서브그룹으로 얹혀 있었다(하나의 캐릭터 파츠 밑에
    # SubIK/TopFK가 같이 등록된 구조).
    fk_grp = cmds.createNode('transform', n='{}_FK_GRP'.format(prefix_top), p=main['xform_grp'])
    fk_ctrls, skin_jnts = _build_fine_offset_layer(prefix_top, main['fk_jnts'], fk_grp)

    twist_start, twist_end = _build_twist_ctrls(prefix_top, fk_ctrls, main['twist_grp'])
    scale_ctrls, thickness_ctrl = _build_scale_ctrls(prefix_top, num_scale_ctrls, skin_jnts, main['scale_grp'])

    return {
        'main': main,
        'fk_grp': fk_grp,
        'fk_ctrls': fk_ctrls,
        'skin_jnts': skin_jnts,
        'twist_start': twist_start,
        'twist_end': twist_end,
        'scale_ctrls': scale_ctrls,
        'thickness_ctrl': thickness_ctrl,
    }


if __name__ == '__main__':
    build_spline_ik_module()
