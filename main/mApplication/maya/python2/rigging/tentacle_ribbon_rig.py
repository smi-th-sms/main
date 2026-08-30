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
    체인이 아니라 flat한 Skin 레이어에 건다). Volume 컨트롤 N개(각각 volumeY,
    volumeZ attribute) -> 대응 구간을 선형보간해서 Skin joint의 scaleY/Z에 각각 연결
    (squash/stretch 볼륨 보정). Volume 컨트롤의 OFF 그룹은 자신과 같은
    arc-length 위치에 가장 가까운 Skin joint의 worldMatrix를 multMatrix/
    decomposeMatrix로 라이브로 따라간다(_connect_volume_to_skin) -- 그래서
    리그가 애니메이션으로 휘어져도 Volume 컨트롤이 build 시점 정적 위치가
    아니라 그 순간의 실제 표면 위치에 남아 있다. 두 컨트롤 사이 보간
    가중치는 고정 fraction 기준이라 빌드 타임에 파이썬으로 계산해서
    blendTwoAttr 하나만 연결하지만(_gradient_plug), Twist는 Parameter가
    라이브라 비율 계산 자체를 노드 네트워크로 만든다(_ranged_twist_plug).

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
import math

import maya.cmds as cmds
import maya.api.OpenMaya as om2

_AXIS_VECTOR = {'x': (1.0, 0.0, 0.0), 'y': (0.0, 1.0, 0.0), 'z': (0.0, 0.0, 1.0)}
# up_axis를 명시하지 않았을 때 쓰는 기본값 -- 기존 _PERP_AXIS 하드코딩과 동일한 결과
# (x->z, y->x, z->x)를 내도록 맞춘 값이라 기존 리그의 방향은 바뀌지 않는다.
_DEFAULT_UP_AXIS = {'x': 'z', 'y': 'x', 'z': 'x'}


def _static_param_at_fraction(curve, frac):
    """curve의 arc-length fraction(0~1)에 해당하는 raw parameter를 빌드 타임에
    한 번 계산한다(MFnNurbsCurve.findParamFromLength).

    예전엔 이 값을 motionPath(fractionMode=1)로 3D 위치를 얻은 뒤
    nearestPointOnCurve/closestPointOnSurface로 '그 위치에서 가장 가까운 점'을
    다시 찾는 방식으로 구했는데, curve가 촉수답게 실제로 구불구불 말리면
    (curl) 서로 다른 arc-length 구간이 3D 공간에서 서로 가까이 지나가는
    경우가 흔해서 -- '가장 가까운 점'이 의도한 지점이 아니라 근처를 지나가는
    다른 구간을 잘못 짚는 문제가 있었다(빌드 직후, 애니메이터가 아무것도
    안 만졌는데도 위치/회전이 크게 틀어짐 -- 끝점 두 개만 우연히 맞고 중간은
    전부 틀어지는 패턴으로 나타났다). findParamFromLength는 3D 위치 검색이
    전혀 없이 curve 자신의 arc-length만 따라가는 1차원 이분탐색이라 curve가
    스스로 얼마나 가까이 지나가든 절대 모호해지지 않는다.

    이 값은 빌드 시점에 한 번 계산해서 follicle의 parameterU에 고정
    (connectAttr 없이 setAttr)한다 -- follicle의 parameter 좌표는 material
    point의 고정 주소라서 surface/curve가 나중에 변형돼도(TOP을 움직이는 등)
    라이브로 다시 풀 필요가 없다. 라이브 재계산이 필요한 유일한 경우는
    Stretch로 유효 길이 자체가 실시간으로 바뀌는 _build_output_follicles의
    stretch_ctrl 경로뿐이다(그 경로는 기존 방식을 그대로 쓴다).

    follicle.parameterU/V는 curve/surface의 실제(raw) parameter range가 아니라
    항상 정규화된 0~1 값을 요구한다. curveFromSurfaceIso로 뽑은 curve의 raw
    range가 0~1이 아닐 수 있으므로, findParamFromLength가 돌려준 raw parameter를
    knotDomain 기준으로 0~1로 정규화해서 돌려준다.
    """
    curve_fn = _curve_fn(curve)
    raw_param = curve_fn.findParamFromLength(frac * curve_fn.length())
    min_u, max_u = curve_fn.knotDomain
    return (raw_param - min_u) / (max_u - min_u)


def _curve_fn(curve):
    sel = om2.MSelectionList()
    sel.add(curve)
    return om2.MFnNurbsCurve(sel.getDagPath(0))


def _raw_param_at_fraction(curve, frac):
    """curve의 arc-length fraction(0~1)에 해당하는 raw(=curve/surface의 실제
    knotDomain 기준) parameter를 계산한다(_static_param_at_fraction과 동일한
    findParamFromLength 기반이지만 0~1 정규화는 안 함). follicle.parameterU
    처럼 항상 정규화가 필요한 게 아니라, pointOnSurfaceInfo/closestPointOnSurface
    처럼 raw range를 그대로 받는 곳(_sample_surface_frame)에 쓴다 -- curve가
    curveFromSurfaceIso로 뽑힌 것이라 이 raw parameter가 surface의 실제
    parameterU와 그대로 대응한다.
    """
    curve_fn = _curve_fn(curve)
    return curve_fn.findParamFromLength(frac * curve_fn.length())


def _rotate_vector_by_node(vec, node):
    """vec(월드 축 단위벡터)를 node의 현재 월드 회전으로 같이 돌린다.

    up_vector는 리본의 실제 폭 방향을 가리켜야 하는데, 리본(curve/surface)은
    항상 rig_grp 밑에 있어서 rig_grp를 회전시키면 리본도 그 회전을 그대로
    따라간다. up_vector를 고정된 세계축 그대로 쓰면(rig_grp가 identity일
    때만 맞음), rig_grp를 build_base 이후에 다시 방향을 잡아둔 리그에서는(
    캐릭터 위에 다른 자세로 얹는 경우 등) up_vector가 리본의 실제(회전된)
    폭 방향과 어긋나서 _build_twist_controls가 계산하는 컨트롤 roll이 서피스의
    진짜 폭 방향과 안 맞게 된다 -- 그래서 매번 rig_grp의 현재 회전을 반영해야
    한다.
    """
    m = cmds.xform(node, q=True, ws=True, m=True)
    rows = (m[0:3], m[4:7], m[8:11])
    return tuple(sum(vec[k]*rows[k][i] for k in range(3)) for i in range(3))


def _get_up_vector(rig_grp, axis):
    """rig_grp에 저장된 tentacleUpAxis(build_base의 up_axis 인자)를 읽어
    rig_grp의 현재 월드 회전을 반영한 단위벡터로 변환한다(_rotate_vector_by_node
    참고). 옛 리그처럼 attribute가 없으면 기존 동작과 동일한 기본값
    (_DEFAULT_UP_AXIS)으로 대체한다.

    이름은 "up"이지만 실제로는 리본의 폭(width, V-tangent 계열) 방향을
    가리키는 참조 벡터다 -- 진짜 surface normal이 아니다("up_axis"라는
    이름 자체가 오해의 소지가 있다). IK/Volume/TOP FK-IK 컨트롤의 정지
    배치는 이제 이 근사 대신 _sample_surface_frame(pointOnSurfaceInfo로
    매 지점의 실제 tangentU/normal을 직접 읽음, follicle과 완전히 동일한
    재료)을 쓴다 -- 이 함수(및 이 함수를 쓰는 _build_twist_controls)는
    Twist 컨트롤처럼 Parameter 값에 따라 라이브로 위치가 바뀌어야 하고,
    자신의 world orientation이 다른 라이브 연결의 입력으로 쓰이지 않는
    경우에만 남아있다 -- motionPath(follow=1)에 worldUpVector로 넘겨서
    tangent(front_axis)에 수직인 성분만 남긴 방향을 컨트롤의 up_local_axis
    자리에 배치하는데, motionPath는 세 로컬 축 중 front_axis/up_local_axis
    두 자리만 명시적으로 지정할 수 있고 나머지 한 자리(third axis)는 항상
    그 둘의 cross product로 자동 채워진다 -- 그 남는 자리가 결과적으로
    surface의 실제 normal에 가장 가깝다(front ⊥ up_vector인 평면적인/완만한
    형태에서는 거의 정확히 normal과 일치, 많이 휘거나 꼬인 형태에서는
    근사치, 이 근사가 실제 프로덕션 촉수에서 60도 이상 벌어지는 경우가
    확인되어 다른 정지 배치 함수들은 전부 _sample_surface_frame으로
    교체됐다).
    """
    if cmds.attributeQuery('tentacleUpAxis', node=rig_grp, exists=True):
        up_axis = cmds.getAttr(rig_grp+'.tentacleUpAxis')
    else:
        up_axis = _DEFAULT_UP_AXIS[axis]
    return _rotate_vector_by_node(_AXIS_VECTOR[up_axis], rig_grp)


# motionPath.frontAxis/upAxis 는 0=X, 1=Y, 2=Z 인덱스를 받는다(기존 하드코딩
# frontAxis=0/upAxis=1과 동일한 기본값).
_AXIS_INDEX = {'x': 0, 'y': 1, 'z': 2}


def _permutation_parity(perm):
    """perm(0,1,2의 순열 tuple)이 짝순열이면 1, 홀순열이면 -1을 돌린다(inversion
    개수로 계산) -- _axis_remap_matrix가 회전을 유지(det=+1, 뒤집히지 않게)하는
    데 쓴다.
    """
    p = list(perm)
    parity = 1
    for i in range(len(p)):
        for j in range(i+1, len(p)):
            if p[i] > p[j]:
                parity *= -1
    return parity


def _axis_remap_matrix(front_axis, up_local_axis):
    """follicle의 네이티브 회전(row0=tangentU/forward, row1=Gram-Schmidt로
    보정된 secondary, row2=normal -- 실측으로 확인된 순서. follicle 노드
    자체는 frontAxis/upAxis 같은 걸 몰라서 항상 이 고정 순서로만 낸다)을
    원하는 로컬 축 배치로 다시 매핑하는 고정 4x4 행렬을 만든다.

    forward(native row0)는 front_axis 자리로, normal(native row2)은
    up_local_axis 자리로("up"이 실제로 surface normal을 뜻하도록), 남는
    secondary(native row1)는 나머지 자리로 옮긴다(부호는 오른손 좌표계
    유지를 위해 순열의 parity로 결정). _build_master_drive_follicles에서
    이 행렬을 follicle 출력 앞에 곱해서 main IK_OFF에 연결하면, front_axis/
    up_local_axis가 무엇이었든 _sample_surface_frame으로 잡은 static 배치
    (forward=tangentU, up_local_axis=normal)와 항상 정확히 일치한다.
    """
    front_idx = _AXIS_INDEX[front_axis]
    up_idx = _AXIS_INDEX[up_local_axis]
    third_idx = ({0, 1, 2} - {front_idx, up_idx}).pop()

    # native row0(forward)->front_idx, native row2(normal)->up_idx,
    # native row1(secondary)->third_idx -- perm[new_slot] = native_row_index
    perm = [None, None, None]
    perm[front_idx] = 0
    perm[up_idx] = 2
    perm[third_idx] = 1
    sign = _permutation_parity(tuple(perm))

    rows = [[0.0]*4 for _ in range(4)]
    rows[front_idx][0] = 1.0
    rows[up_idx][2] = 1.0
    rows[third_idx][1] = sign
    rows[3][3] = 1.0
    return [v for row in rows for v in row]


def _get_ctrl_axes(rig_grp):
    """rig_grp에 저장된 tentacleCtrlFrontAxis/tentacleCtrlUpAxis(컨트롤 자신의
    로컬 forward/up 축, build_base의 front_axis/up_local_axis 인자)를 읽는다.
    옛 리그처럼 attribute가 없으면 기존 동작과 동일한 기본값('x'/'y')으로
    대체한다. 이 값은 _sample_surface_frame이 배치하는 forward/up 자리와
    컨트롤 shape의 circle normal을 함께 결정한다 -- 서로 다른 두 값을 따로
    저장해야 하나가 아니라 둘 다 필요하다.
    """
    if cmds.attributeQuery('tentacleCtrlFrontAxis', node=rig_grp, exists=True):
        front_axis = cmds.getAttr(rig_grp+'.tentacleCtrlFrontAxis')
    else:
        front_axis = 'x'
    if cmds.attributeQuery('tentacleCtrlUpAxis', node=rig_grp, exists=True):
        up_local_axis = cmds.getAttr(rig_grp+'.tentacleCtrlUpAxis')
    else:
        up_local_axis = 'y'
    return front_axis, up_local_axis


def _set_string_attr(node, attr, value):
    if not cmds.attributeQuery(attr, node=node, exists=True):
        cmds.addAttr(node, ln=attr, dt='string')
    cmds.setAttr(node+'.'+attr, value, type='string')


def _set_ctrl_axes(rig_grp, front_axis, up_local_axis):
    """rig_grp의 tentacleCtrlFrontAxis/tentacleCtrlUpAxis를 갱신한다.

    build_ik/build_twist_scale/build_branch에서 front_axis/up_local_axis를
    override로 받으면, build_base를 다시 실행하지 않고도 이후 단계(Twist/
    Volume, Branch)가 바뀐 값을 그대로 이어받도록 여기 저장소를 같이
    갱신해둔다 -- 안 그러면 여기서만 바뀐 축으로 컨트롤이 만들어지고, 뒤
    단계는 build_base 때 저장된 옛 값을 계속 읽어서 서로 어긋난다.
    """
    _set_string_attr(rig_grp, 'tentacleCtrlFrontAxis', front_axis)
    _set_string_attr(rig_grp, 'tentacleCtrlUpAxis', up_local_axis)


def _set_up_axis(rig_grp, up_axis):
    """rig_grp의 tentacleUpAxis를 갱신한다(_set_ctrl_axes와 동일한 이유 --
    build_ik 등에서 up_axis override를 받으면 이후 단계도 이어받게 한다).
    """
    _set_string_attr(rig_grp, 'tentacleUpAxis', up_axis)


def _vec_sub(a, b):
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


def _vec_add(a, b):
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])


def _vec_scale(a, s):
    return (a[0]*s, a[1]*s, a[2]*s)


def _vec_dot(a, b):
    return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]


def _vec_norm(a):
    return math.sqrt(_vec_dot(a, a))


def _vec_normalize(a):
    n = _vec_norm(a)
    return _vec_scale(a, 1.0/n) if n > 1e-9 else a


def _vec_cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _vec_mean(vecs):
    n = len(vecs)
    sx = sy = sz = 0.0
    for v in vecs:
        sx += v[0]
        sy += v[1]
        sz += v[2]
    return (sx/n, sy/n, sz/n)


def _scatter_interior_points(mesh, resolution=30):
    """mesh의 bounding box 안에 격자로 점을 뿌리고, ray-cast 교차 횟수의
    홀짝으로 실제 오브젝트 내부에 있는 점만 남긴다(Houdini의 volume scatter와
    같은 개념 -- point-in-mesh 판정: 한쪽 방향으로 ray를 쏴서 표면과 교차한
    횟수가 홀수면 내부, 짝수면 외부).

    표면 vertex만 쓰면 폴리곤 해상도(각/세그먼트 개수)에 묶여서 밴드마다
    잡히는 점 분포가 불균등해지는데, 내부 scatter는 훨씬 촘촘하고 고르게
    분포해서 중심선 centroid가 더 매끄럽게 나온다.

    (python2 버전은 numpy 없이 순수 파이썬 list/loop로 동작한다 -- Maya의
    python2 환경엔 numpy가 기본으로 없는 경우가 많다. 알고리즘/결과는
    python3 버전과 동일, 벡터 연산만 _vec_* 헬퍼로 대체.)
    """
    sel = om2.MSelectionList()
    sel.add(mesh)
    mesh_fn = om2.MFnMesh(sel.getDagPath(0))

    bbox = cmds.exactWorldBoundingBox(mesh)
    lo = bbox[:3]
    hi = bbox[3:]
    size = [hi[i]-lo[i] for i in range(3)]
    cell = max(size)/float(resolution)
    counts = [max(2, int(round(size[i]/cell))) for i in range(3)]

    # bbox 경계에 딱 붙는 값(lo/hi 그 자체)으로 샘플링하면, 둥근 단면에서는
    # 그 경계가 원의 접점(=표면 위 또는 바로 바깥)이라 안쪽으로 전혀 안 잡힐
    # 수 있다 -- 그래서 각 축을 counts개의 셀로 나눈 뒤 그 '셀 중심'만
    # 샘플링해서 경계에서 반 칸씩 안으로 들어오게 한다.
    xs = [lo[0]+(k+0.5)*(size[0]/counts[0]) for k in range(counts[0])]
    ys = [lo[1]+(k+0.5)*(size[1]/counts[1]) for k in range(counts[1])]
    zs = [lo[2]+(k+0.5)*(size[2]/counts[2]) for k in range(counts[2])]

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
    return interior


def _resample_uniform(points, num_points):
    """points로 이어진 폴리라인을 누적 arc length 기준 균등한 num_points개로
    다시 뽑는다. scatter가 표면 vertex보다 훨씬 적고 듬성듬성하면, centroid
    재계산만 반복할 때 인접 포인트끼리 너무 가까워지거나(심하면 겹침) 간격이
    불균등해질 수 있다 -- 매 반복 끝에 이 재배치를 해주면 다음 반복의 tangent
    계산이 항상 고르게 퍼진 포인트를 기준으로 이뤄져서 훨씬 안정적으로
    수렴한다(active contour/snake 알고리즘에서 흔히 쓰는 재정규화 기법).
    """
    seg = [_vec_norm(_vec_sub(points[i], points[i-1])) for i in range(1, len(points))]
    cum = [0.0]
    for s in seg:
        cum.append(cum[-1]+s)
    total = cum[-1]
    if total < 1e-9:
        return list(points)
    out = []
    for k in range(num_points):
        t = total*(k/float(num_points-1)) if num_points > 1 else 0.0
        # np.searchsorted(cum, t)와 동일 -- cum[j-1] < t <= cum[j]인 가장 작은 j
        j = 0
        while j < len(cum) and cum[j] < t:
            j += 1
        if j <= 0:
            out.append(points[0])
        elif j >= len(points):
            out.append(points[-1])
        else:
            t0, t1 = cum[j-1], cum[j]
            frac = 0.0 if t1 == t0 else (t-t0)/(t1-t0)
            out.append(_vec_add(points[j-1], _vec_scale(_vec_sub(points[j], points[j-1]), frac)))
    return out


_AXIS_MISMATCH_RATIO = 0.5


def _resolve_axis(obj, axis):
    """obj(mesh/curve 등 아무 DAG 오브젝트)의 world bbox 기준으로 axis를 검증/보정한다.

    axis가 None이면 가장 긴 축으로 자동 감지한다. axis가 명시돼도 그 축의
    bbox 길이가 실제 가장 긴 축의 절반에도 못 미치면(오브젝트가 axis와 다른
    방향으로 뻗어있다는 뜻 -- 예: 실린더를 눕혀놨는데 axis='y' 기본값을 그대로
    쓴 경우) 무시하고 가장 긴 축으로 자동 전환한다. 그렇지 않으면(mesh 경로)
    base/tip이 실제 형태의 거의 같은 지점(짧은 축 방향의 좁은 단면)으로 잡혀서
    _get_centerline_points의 반복이 한쪽 끝에서 중간까지 갔다가 같은 끝으로
    되돌아오는 식으로 접혀 curve/surface가 자기 자신과 겹쳐버리는 문제가
    있었다.

    obj가 방금 편집된(예: build_base() 이후 사용자가 NSF의 CV를 직접 옮긴)
    curveFromSurfaceIso 등 라이브 히스토리 체인의 하류에 있으면,
    cmds.exactWorldBoundingBox()가 그 편집을 아직 안 당겨온 stale한 값을
    돌려주는 경우가 있다(Maya의 지연 평가 -- 이후 아무 쿼리 하나만 더 해도
    다음 호출부턴 정상 값이 나온다). 그래서 bbox를 구하기 전에 shape의
    worldSpace/worldMesh를 한 번 강제로 평가해서 이 문제를 피한다.
    """
    for shape in cmds.listRelatives(obj, shapes=True, ni=True, fullPath=True) or []:
        for attr in ('.worldSpace[0]', '.worldMesh[0]'):
            try:
                cmds.getAttr(shape+attr)
                break
            except (RuntimeError, ValueError):
                continue
    bbox = cmds.exactWorldBoundingBox(obj)
    lens = {'x': bbox[3]-bbox[0], 'y': bbox[4]-bbox[1], 'z': bbox[5]-bbox[2]}
    longest_axis = max(lens, key=lens.get)
    if axis is None:
        return longest_axis
    if lens[axis] < lens[longest_axis] * _AXIS_MISMATCH_RATIO:
        cmds.warning(
            '_resolve_axis: axis={}의 bbox 길이({:.4f})가 실제 가장 긴 축 '
            '{}({:.4f})보다 너무 짧습니다 -- 오브젝트 방향과 axis가 안 맞는 것으로 '
            '보고 {}로 자동 전환합니다.'.format(
                axis, lens[axis], longest_axis, lens[longest_axis], longest_axis))
        return longest_axis
    return axis


def _get_axis_endpoints(mesh, axis='y'):
    """mesh의 world bounding box 중심을 지나는 축(base->tip 방향)의 양 끝점을 구한다."""
    axis = _resolve_axis(mesh, axis)
    bbox = cmds.exactWorldBoundingBox(mesh)
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
        verts = [tuple(flat[i:i+3]) for i in range(0, len(flat), 3)]

    lo, hi = base[idx], tip[idx]
    span = hi-lo
    edge_band = (span/float(num_points-1))*band_ratio if num_points > 1 and span else abs(span) or 1.0
    min_bucket = max(3, len(verts)//num_points)

    def _edge_centroid(target):
        # base/tip은 bbox 중심으로 나머지 두 좌표가 고정된 값이라 휜 오브젝트의
        # 실제 끝 단면 중심과 다르다 -- axis 좌표만 target으로 고정하고 나머지는
        # 그 근처 vertex의 실제 centroid로 다시 잡는다(기존 방식과 동일한 원리).
        picked = [v for v in verts if abs(v[idx]-target) <= edge_band]
        if not picked:
            picked = sorted(verts, key=lambda v: abs(v[idx]-target))[:min_bucket]
        c = list(_vec_mean(picked))
        c[idx] = target
        return tuple(c)

    base_v = _edge_centroid(lo)
    tip_v = _edge_centroid(hi)
    diff = _vec_sub(tip_v, base_v)
    points = [_vec_add(base_v, _vec_scale(diff, k/float(num_points-1) if num_points > 1 else 0.0))
              for k in range(num_points)]

    total_len = _vec_norm(diff) or 1.0
    target_band = (total_len/float(num_points-1))*band_ratio if num_points > 1 else total_len
    # wide_band는 target_band의 배수로 잡는다(전체 길이의 절반처럼 오브젝트
    # 스케일에 비례한 값을 쓰면, scatter 포인트가 표면 vertex보다 훨씬 적고
    # 넓게 퍼져 있어서 첫 반복에 대부분의 포인트가 거의 전체 오브젝트의
    # '뭉치 centroid'로 쏠려버리고 이후 반복에서도 안 풀린다).
    wide_band = target_band*4.0

    for it in range(iterations):
        frac = it/float(iterations-1) if iterations > 1 else 1.0
        band_half = wide_band+(target_band-wide_band)*frac

        tangents = [None]*num_points
        tangents[0] = _vec_sub(points[1], points[0])
        tangents[-1] = _vec_sub(points[-1], points[-2])
        for i in range(1, num_points-1):
            tangents[i] = _vec_sub(points[i+1], points[i-1])
        for i in range(num_points):
            n = _vec_norm(tangents[i])
            if n < 1e-9:
                n = 1.0
            tangents[i] = _vec_scale(tangents[i], 1.0/n)

        new_points = list(points)
        for i in range(1, num_points-1):
            projected = [(_vec_dot(_vec_sub(v, points[i]), tangents[i]), v) for v in verts]
            picked = [v for (p, v) in projected if abs(p) <= band_half]
            if not picked:
                picked = [v for (p, v) in sorted(projected, key=lambda pv: abs(pv[0]))[:min_bucket]]
            new_points[i] = _vec_mean(picked)

        # 양 끝은 세계축(axis) 좌표로 고정하지 않고, 로컬 tangent 방향으로
        # 가장 끝쪽(extremal)에 있는 scatter 슬라이스의 centroid로 매 반복
        # 다시 잡는다 -- 휘어진 오브젝트는 실제 끝 단면이 세계축에 대해
        # 기울어져 있어서, 세계축 좌표로 슬라이싱하면 그 기울어진 단면의
        # 일부만 걸리고 나머지는 못 잡아 centroid가 실제 중심에서 벗어난다.
        # tangent가 반복마다 실제 방향으로 수렴하면서 끝점도 같이 정확해진다.
        proj0 = [_vec_dot(v, tangents[0]) for v in verts]
        min0 = min(proj0)
        new_points[0] = _vec_mean([v for v, p in zip(verts, proj0) if p <= min0+band_half])

        proj_last = [_vec_dot(v, tangents[-1]) for v in verts]
        max_last = max(proj_last)
        new_points[-1] = _vec_mean([v for v, p in zip(verts, proj_last) if p >= max_last-band_half])

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


def _build_ribbon_surface(name, center_crv, perp_vector, width, sys_grp):
    """center_crv를 perp_vector(up_axis) 방향으로 +-width/2만큼 복제/이동한 두
    커브를 loft해서 얇은 리본 NURBS 서피스를 만든다.

    (참고) cmds.extrude(profile, path, et=2)로 시도했을 때는 path 위를
    정확히 따라가지 않고 profile 위치를 중심으로 대칭으로 스윕돼서 커브가
    오브젝트 중심선에서 절반만큼 벗어나는 문제가 있었다 -- loft가 훨씬
    예측 가능하고 정확하다. loft한 서피스는 U가 긴 방향(center_crv를 따라),
    V가 짧은 폭 방향이 된다.
    """
    perp = perp_vector
    half = width*0.5
    left = cmds.duplicate(center_crv, n='{}_ribbonLeftTemp_CRV'.format(name))[0]
    right = cmds.duplicate(center_crv, n='{}_ribbonRightTemp_CRV'.format(name))[0]
    cmds.move(-perp[0]*half, -perp[1]*half, -perp[2]*half, left, relative=True, objectSpace=True)
    cmds.move(perp[0]*half, perp[1]*half, perp[2]*half, right, relative=True, objectSpace=True)

    surf = cmds.loft(left, right, n='{}_NSF'.format(name), ch=False, u=True, c=False,
                      ar=True, d=3, ss=1, rn=False, po=0, rsn=True)[0]
    cmds.delete(left, right)
    return surf


def _shape_owner(node, shape_type, label):
    """node가 지정 타입 shape 또는 그 transform이면 transform 이름을 돌린다."""
    if not cmds.objExists(node):
        raise ValueError('build_base: {} "{}"가 씬에 없습니다'.format(label, node))

    node_type = cmds.nodeType(node)
    if node_type == shape_type:
        parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
        if not parents:
            raise ValueError('build_base: {} "{}"의 transform을 찾을 수 없습니다'.format(label, node))
        return parents[0]

    shapes = cmds.listRelatives(node, shapes=True, ni=True, fullPath=True) or []
    if any(cmds.nodeType(shape) == shape_type for shape in shapes):
        return node

    raise ValueError('build_base: {} "{}"는 {}가 아닙니다'.format(label, node, shape_type))


def _duplicate_base_surface(name, source_surface):
    """입력 surface 원본은 보존하고 리그가 변형할 전용 NSF 복제본을 만든다."""
    surface = cmds.duplicate(source_surface, n='{}_NSF'.format(name), renameChildren=True)[0]
    return surface


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


def build_base(mesh=None, curve=None, surface=None, name='tentacle', axis='y', up_axis=None,
                front_axis='x', up_local_axis='y', num_cv=19, ribbon_width=1.0):
    """1단계 베이스: (이미 있는 surface 또는 mesh 가이드) -> 리본 서피스 ->
    서피스에서 curve 재추출 -> restCurveLength 저장.

    surface를 주면 그 NURBS surface를 리본 베이스로 사용한다. 원본 surface를
    직접 스킨/재부모하지 않고 {name}_NSF로 복제해서 이후 단계가 변형할 전용
    리본으로 쓴다. surface가 있으면 mesh보다 우선한다.

    curve 기반 surface 생성은 불안정해서 더 이상 지원하지 않는다. curve 인자는
    예전 호출부 호환성을 위해 남겨두지만, surface/mesh 선택에는 쓰지 않는다.

    Arguments:
        surface (str): 사용자가 직접 만든 리본 NURBS surface(주면 mesh 무시,
            우선순위 가장 높음). 원본은 보존하고 복제본을 리그 베이스로 쓴다.
        mesh (str): 촉수 형상 스탠드인(surface가 없을 때만 사용).
        curve (str): deprecated. curve 기반 리본 surface 생성은 더 이상 사용하지 않는다.
        name (str): 리그 네이밍 프리픽스
        axis (str): 리본 폭 방향 기본값(up_axis) 계산 등에 참고하는 축('x'/'y'/'z').
            None이면 surface/mesh의 bbox에서 가장 긴 축을 자동 감지한다.
        up_axis (str): 리본 서피스의 폭(width) 방향 기준으로 쓸 세계축('x'/'y'/'z',
            axis와 달라야 함) -- 이름은 "up"이지만 실제로는 surface normal이
            아니라 리본의 폭 방향 참조 벡터다(_get_up_vector 참고, Twist 컨트롤
            정지 배치에만 쓰인다 -- 아래 up_local_axis와는 별개). None이면
            기존 동작과 동일한 기본값(_DEFAULT_UP_AXIS: axis='x'->'z', 'y'/'z'
            ->'x')을 쓴다. build_ik/build_branch 등 이후 단계도 여기서 저장한
            값(tentacleUpAxis)을 그대로 읽으므로, base와 top(branch)이 항상
            같은 폭 방향 기준으로 정렬된다.
        front_axis (str): IK/Volume/TOP FK-IK 컨트롤의 로컬 축 중 surface
            tangentU(forward)에 맞출 축('x'/'y'/'z', 기본 'x' -- 기존 동작과
            동일). 컨트롤 shape의 circle normal도 이 축에 맞춰 같이 돈다.
        up_local_axis (str): 위 컨트롤들의 로컬 축 중 실제 surface normal에
            맞출 축('x'/'y'/'z', 기본 'y' -- 기존 동작과 동일, front_axis와
            달라야 함). _sample_surface_frame이 pointOnSurfaceInfo로 매 지점의
            실제 normal(Gram-Schmidt로 tangentU에 수직인 성분만 남긴 값)을
            읽어 이 축 자리에 직접 넣는다 -- follicle이 회전을 내는 것과
            동일한 재료(_axis_remap_matrix가 follicle 쪽과 이 자리를 맞춘다).
            front_axis/up_local_axis로 지정 안 한 나머지 로컬 축(third axis)은
            그 둘에 수직인 secondary(forward×up) 방향이 자동으로 채워진다.
        num_cv (int): center curve의 CV 개수(=리본 서피스 U방향 해상도, mesh
            모드에서만 쓰임).
        ribbon_width (float): mesh 모드에서 생성할 리본 서피스의 폭

    Returns:
        dict: surface, curve, axis, rest_length 등
    """
    if mesh is None and surface is None:
        raise ValueError('build_base: surface 또는 mesh 중 하나는 반드시 지정해야 합니다')
    if surface is not None:
        surface = _shape_owner(surface, 'nurbsSurface', 'surface')

    source_surface = None
    if cmds.objExists('{}_rig_GRP'.format(name)):
        if surface is not None:
            rig_path = cmds.ls('{}_rig_GRP'.format(name), long=True)[0]
            surf_path = cmds.ls(surface, long=True)[0]
            if surf_path.startswith(rig_path + '|'):
                source_surface = cmds.duplicate(surface, n='{}_surfaceSourceTemp_NSF'.format(name),
                                                renameChildren=True)[0]
                cmds.parent(source_surface, world=True)
        cmds.delete('{}_rig_GRP'.format(name))
    if source_surface is not None:
        surface = source_surface

    if surface is not None:
        axis = _resolve_axis(surface, axis)
    else:
        base, tip, axis = _get_axis_endpoints(mesh, axis)

    if up_axis is None:
        up_axis = _DEFAULT_UP_AXIS[axis]
    elif up_axis == axis:
        raise ValueError('build_base: up_axis({})는 axis({})와 달라야 합니다'.format(up_axis, axis))
    if front_axis == up_local_axis:
        raise ValueError('build_base: front_axis({})는 up_local_axis({})와 달라야 합니다'.format(
            front_axis, up_local_axis))

    g = _build_groups(name)
    cmds.addAttr(g['rig'], ln='tentacleAxis', dt='string')
    cmds.setAttr(g['rig']+'.tentacleAxis', axis, type='string')
    cmds.addAttr(g['rig'], ln='tentacleUpAxis', dt='string')
    cmds.setAttr(g['rig']+'.tentacleUpAxis', up_axis, type='string')
    cmds.addAttr(g['rig'], ln='tentacleCtrlFrontAxis', dt='string')
    cmds.setAttr(g['rig']+'.tentacleCtrlFrontAxis', front_axis, type='string')
    cmds.addAttr(g['rig'], ln='tentacleCtrlUpAxis', dt='string')
    cmds.setAttr(g['rig']+'.tentacleCtrlUpAxis', up_local_axis, type='string')

    if surface is not None:
        surface = _duplicate_base_surface(name, surface)
        if source_surface is not None and cmds.objExists(source_surface):
            cmds.delete(source_surface)
    else:
        center_crv = _build_centerline_curve(name, mesh, axis, base, tip, num_cv)
        surface = _build_ribbon_surface(name, center_crv, _AXIS_VECTOR[up_axis], ribbon_width, g['sys'])
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


def _sample_surface_frame(surface, u_param, front_axis='x', up_local_axis='y'):
    """surface 위 (u_param, v=0.5) 지점의 world position/rotation을
    pointOnSurfaceInfo로 직접 계산한다 -- forward=tangentU, up=normal
    (Gram-Schmidt로 forward에 수직인 성분만 남김), secondary=forward×up.
    follicle이 회전을 내는 것과 완전히 동일한 재료(tangentU/normal)를 쓰기
    때문에, build_output()/build_branch()의 follicle 기반 라이브 출력과
    항상 정확히 일치한다(_axis_remap_matrix가 이 함수와 follicle 양쪽에
    동일한 규칙으로 맞춰져 있다).

    예전 _sample_curve_frame(motionPath+고정 world up-vector)은 표면이
    거의 평평할 때만 "up"이 실제 normal과 가까웠고, 많이 휘거나 꼬인
    표면에서는(실제 프로덕션 촉수에서 확인됨) up이 normal과 60도 이상
    벌어지는 경우도 있었다 -- 그 근사를 없애고 매 지점마다 surface 자신의
    실제 tangentU/normal을 직접 읽는다.

    u_param은 curve/surface의 raw(정규화 안 된) parameter다(_raw_param_at_fraction
    참고, follicle.parameterU가 요구하는 0~1 정규화 값과는 다르다).
    """
    surf_shape = cmds.listRelatives(surface, shapes=True, ni=True, fullPath=True)[0]
    psi = cmds.createNode('pointOnSurfaceInfo', n='tmp_sampleSurfFrame_PSI')
    cmds.connectAttr(surf_shape+'.worldSpace[0]', psi+'.inputSurface')
    cmds.setAttr(psi+'.parameterU', u_param)
    cmds.setAttr(psi+'.parameterV', 0.5)
    pos = cmds.getAttr(psi+'.position')[0]
    tangent_u = (cmds.getAttr(psi+'.tangentUx'), cmds.getAttr(psi+'.tangentUy'), cmds.getAttr(psi+'.tangentUz'))
    normal_raw = (cmds.getAttr(psi+'.normalX'), cmds.getAttr(psi+'.normalY'), cmds.getAttr(psi+'.normalZ'))
    cmds.delete(psi)

    forward = _vec_normalize(tangent_u)
    up = _vec_normalize(_vec_sub(normal_raw, _vec_scale(forward, _vec_dot(normal_raw, forward))))
    secondary = _vec_cross(forward, up)

    front_idx = _AXIS_INDEX[front_axis]
    up_idx = _AXIS_INDEX[up_local_axis]
    third_idx = ({0, 1, 2} - {front_idx, up_idx}).pop()

    # forward/up/secondary는 (front_idx, up_idx, third_idx)=(0,1,2)일 때만
    # secondary=forward×up가 그대로 det=+1(제대로 된 회전)이 된다 -- 다른
    # 배치 조합에서는 부호를 뒤집어야 오른손 좌표계가 유지된다(_axis_remap_matrix
    # 와 동일한 순열 parity 로직).
    perm = [None, None, None]
    perm[front_idx] = 0
    perm[up_idx] = 1
    perm[third_idx] = 2
    sign = _permutation_parity(tuple(perm))

    rows = [None, None, None]
    rows[front_idx] = forward
    rows[up_idx] = up
    rows[third_idx] = _vec_scale(secondary, sign)

    m = om2.MMatrix((
        rows[0][0], rows[0][1], rows[0][2], 0.0,
        rows[1][0], rows[1][1], rows[1][2], 0.0,
        rows[2][0], rows[2][1], rows[2][2], 0.0,
        pos[0], pos[1], pos[2], 1.0,
    ))
    euler = om2.MTransformationMatrix(m).rotation(asQuaternion=False)
    rot_deg = (math.degrees(euler.x), math.degrees(euler.y), math.degrees(euler.z))
    return (pos[0], pos[1], pos[2]), rot_deg


def _build_ik_controls(name, curve, surface, num_ik, radius, ctl_grp, front_axis='x', up_local_axis='y'):
    """리본 curve 위에 arc-length 균등 배치된 IK 컨트롤 num_ik개를 만든다
    (참조 리그의 L_IK_tentacle_XXX_CON). 컨트롤 shape는 aim축(local front_axis)을
    감싸는 원 -- 나중에 촉수를 굽힐 때 자연스러운 회전 링 형태.

    _sample_surface_frame으로 배치한다 -- surface의 실제 tangentU/normal을
    직접 읽어서 follicle 기반 라이브 출력(build_output/build_branch)과
    항상 정확히 일치한다.
    """
    front_vec = _AXIS_VECTOR[front_axis]
    ctrls, offsets = [], []
    for i in range(num_ik):
        frac = i/float(num_ik-1) if num_ik > 1 else 0.0
        u_param = _raw_param_at_fraction(curve, frac)
        pos, rot = _sample_surface_frame(surface, u_param, front_axis, up_local_axis)
        ctrl = cmds.circle(n='{}_IK{:02d}_CTL'.format(name, i+1), ch=False, nr=front_vec, r=radius)[0]
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


def build_ik(name='tentacle', num_ik=9, ctrl_radius=1.0,
             up_axis=None, front_axis=None, up_local_axis=None):
    """2단계: 리본 서피스를 따라 IK 컨트롤 N개 배치 -> 1:1 NurbsBind joint ->
    리본 서피스 스킨 바인드.

    build_base()가 먼저 실행되어 {name}_rig_GRP/{name}_CRV/{name}_NSF가 이미
    존재해야 한다.

    Arguments:
        name (str): build_base()와 동일한 리그 네이밍 프리픽스
        num_ik (int): IK 컨트롤 개수(=NurbsBind joint 개수)
        ctrl_radius (float): IK 컨트롤 shape 반경
        up_axis (str): build_base()가 저장한 값을 override(build_base를 다시
            돌리지 않고 축만 바꿔서 IK를 다시 만들 때 사용). None이면 build_base
            때 저장된 값을 그대로 쓴다. override하면 이후 build_twist_scale/
            build_branch도 이어받도록 rig_grp에 다시 저장된다.
        front_axis (str): 위와 동일한 방식의 override(컨트롤 로컬 forward축).
        up_local_axis (str): 위와 동일한 방식의 override(컨트롤 로컬 up축).

    Returns:
        dict: ik_ctrls, bind_jnts, skin_cluster

    Note:
        build_base() 이후 사용자가 {name}_NSF를 직접(CV 이동, sculpt 등) 다시
        모양을 바꿨을 수 있다 -- curve는 curveFromSurfaceIso로 라이브 추출된
        것이라 그 편집을 그대로 반영하지만(_extract_curve_from_surface),
        저장된 tentacleAxis는 build_base() 시점 mesh 기준으로 딱 한 번만
        정해진 값이라 그 뒤 모양이 바뀌어도 자동으로 다시 안 맞춰진다. 그래서
        매번 build_ik() 실행 시 저장된 축을 curve의 현재(=수정 반영된) bbox
        기준으로 다시 검증한다(_resolve_axis -- 실제 가장 긴 축의 절반에도
        못 미치면 자동 전환+경고, 아니면 그대로 유지). 이후 build_twist_scale/
        build_branch도 여기서 갱신된 값을 이어받는다.
    """
    rig_grp = '{}_rig_GRP'.format(name)
    curve = '{}_CRV'.format(name)
    surface = '{}_NSF'.format(name)
    if not cmds.objExists(rig_grp) or not cmds.objExists(curve) or not cmds.objExists(surface):
        raise RuntimeError('build_ik: build_base()를 먼저 실행하세요 ({} 없음)'.format(rig_grp))

    stored_axis = cmds.getAttr(rig_grp+'.tentacleAxis')
    axis = _resolve_axis(curve, stored_axis)
    if axis != stored_axis:
        _set_string_attr(rig_grp, 'tentacleAxis', axis)
    if up_axis is not None:
        _set_up_axis(rig_grp, up_axis)

    stored_front_axis, stored_up_local_axis = _get_ctrl_axes(rig_grp)
    front_axis = front_axis if front_axis is not None else stored_front_axis
    up_local_axis = up_local_axis if up_local_axis is not None else stored_up_local_axis
    if front_axis == up_local_axis:
        raise ValueError('build_ik: front_axis({})는 up_local_axis({})와 달라야 합니다'.format(
            front_axis, up_local_axis))
    _set_ctrl_axes(rig_grp, front_axis, up_local_axis)

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

    ik_ctrls, ik_offsets = _build_ik_controls(name, curve, surface, num_ik, ctrl_radius, ctl_grp,
                                               front_axis=front_axis, up_local_axis=up_local_axis)
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
    """curve 위 num_output개 지점을 follicle의 parameterU에 배치한다.

    stretch_ctrl이 없으면(고정 fraction) 빌드 타임에 _static_param_at_fraction
    (findParamFromLength -- 3D 위치 검색이 없는 1차원 arc-length 이분탐색)
    으로 parameter를 한 번에 정확히 계산해서 setAttr로 고정한다. curve가
    curveFromSurfaceIso로 뽑힌 것(_extract_curve_from_surface)이라 curve의
    parameter range/값이 서피스의 parameterU와 그대로 대응하고, follicle의
    parameter 좌표는 material point의 고정 주소라서 서피스가 나중에 IK로
    변형돼도 라이브로 다시 풀 필요가 없다.

    stretch_ctrl을 주면(Stretch attribute를 가진 마지막 IK 컨트롤) 유효 길이
    자체가 라이브로 바뀌므로, 그 경우만 motionPath(fractionMode=1)로 3D
    위치를 얻은 뒤 nearestPointOnCurve로 curve에서 parameter를 역산하는
    라이브 방식을 쓴다 -- fractionMode=1은 항상 현재 arc length 기준으로
    균등 재분배하는데, Stretch가 0에 가까울수록 effectiveLength가
    restCurveLength에 가까워져서 늘어난 커브 위에서도 rest 간격을 유지하다가
    tip 앞에서 멈추는(rigid) 동작이 된다. (이 라이브 경로는 curve가 심하게
    말려 있으면서 동시에 Stretch를 라이브로 조절하는 경우에만, 서로 다른
    arc-length 구간이 3D 공간에서 가까이 지나가는 self-proximity로 인한
    오차가 남는 더 좁은 잔여 한계가 있다 -- 고정 fraction 경로는 이 문제가
    아예 없다.)

    follicle의 출력 회전은 서피스의 국소 tangent/normal에서 바로 계산되므로
    motionPath의 up-vector 방식과 달리 구조적으로 플립이 없다.
    """
    crv_shape = cmds.listRelatives(curve, shapes=True, ni=True, fullPath=True)[0]
    surf_shape = cmds.listRelatives(surface, shapes=True, ni=True, fullPath=True)[0]
    crv_min = cmds.getAttr(crv_shape+'.minValue')
    crv_max = cmds.getAttr(crv_shape+'.maxValue')

    if stretch_ctrl:
        effective_len_plug, arc_len_plug = _build_stretch_ratio(name, curve, stretch_ctrl)

    follicles = []
    for i in range(num_output):
        frac = i/float(num_output-1) if num_output > 1 else 0.0
        idx = i+1

        fol_shape = cmds.createNode('follicle', n='{}_output{:02d}_FOLShape'.format(name, idx))
        fol_xform = cmds.listRelatives(fol_shape, parent=True)[0]
        fol_xform = cmds.rename(fol_xform, '{}_output{:02d}_FOL'.format(name, idx))
        cmds.connectAttr(surf_shape+'.local', fol_shape+'.inputSurface')
        cmds.connectAttr(surf_shape+'.worldMatrix[0]', fol_shape+'.inputWorldMatrix')

        if stretch_ctrl:
            # Stretch는 라이브로 바뀌는 값이라(유효 길이가 실시간으로 변함) 여기만
            # 예전 방식(motionPath 3D 위치 -> nearestPointOnCurve 역산)을 그대로
            # 쓴다 -- curve가 심하게 말려 있으면서 동시에 Stretch를 라이브로
            # 조절하는 경우에만 self-proximity로 인한 오차가 남는, 더 좁은 잔여
            # 한계다. 고정 fraction(아래 else)은 _static_param_at_fraction으로
            # 빌드 타임에 한 번에 정확히 계산해서 이 문제가 아예 없다.
            mp = cmds.createNode('motionPath', n='{}_output{:02d}_MPT'.format(name, idx))
            cmds.connectAttr(crv_shape+'.worldSpace[0]', mp+'.geometryPath')
            cmds.setAttr(mp+'.fractionMode', 1)

            frac_len = cmds.createNode('multDoubleLinear', n='{}_output{:02d}_fracLen_MDL'.format(name, idx))
            cmds.setAttr(frac_len+'.input2', frac)
            cmds.connectAttr(effective_len_plug, frac_len+'.input1')

            remap = cmds.createNode('multiplyDivide', n='{}_output{:02d}_remapU_MPD'.format(name, idx))
            cmds.setAttr(remap+'.operation', 2)
            cmds.connectAttr(frac_len+'.output', remap+'.input1X')
            cmds.connectAttr(arc_len_plug, remap+'.input2X')
            cmds.connectAttr(remap+'.outputX', mp+'.uValue')

            npc = cmds.createNode('nearestPointOnCurve', n='{}_output{:02d}_NPC'.format(name, idx))
            cmds.connectAttr(crv_shape+'.worldSpace[0]', npc+'.inputCurve')
            cmds.connectAttr(mp+'.allCoordinates', npc+'.inPosition')

            # follicle.parameterU는 항상 정규화된 0~1을 기대하는데 npc.parameter는
            # curve의 raw range라서 그대로 연결하면 follicle이 1보다 큰 값을
            # 1로 clamp해버린다 -- knotDomain 기준으로 라이브 정규화한다
            # (_static_param_at_fraction과 동일한 이유).
            norm_sub = cmds.createNode('plusMinusAverage', n='{}_output{:02d}_paramNorm_PMA'.format(name, idx))
            cmds.setAttr(norm_sub+'.operation', 2)
            cmds.connectAttr(npc+'.parameter', norm_sub+'.input1D[0]')
            cmds.setAttr(norm_sub+'.input1D[1]', crv_min)

            norm_scale = cmds.createNode('multDoubleLinear', n='{}_output{:02d}_paramNorm_MDL'.format(name, idx))
            cmds.setAttr(norm_scale+'.input2', 1.0/(crv_max-crv_min) if crv_max != crv_min else 1.0)
            cmds.connectAttr(norm_sub+'.output1D', norm_scale+'.input1')
            cmds.connectAttr(norm_scale+'.output', fol_shape+'.parameterU')
        else:
            cmds.setAttr(fol_shape+'.parameterU', _static_param_at_fraction(curve, frac))

        cmds.setAttr(fol_shape+'.parameterV', 0.5)
        cmds.parent(fol_xform, fol_grp)

        # follicle.outTranslate/outRotate는 월드 스페이스인데 fol_xform.translate/
        # rotate는 로컬이라, fol_grp(-> sys_grp -> rig_grp) 체인이 월드 원점이
        # 아니면(리그를 캐릭터 위 다른 위치/회전으로 옮겨두면) 그대로 연결 시 위치가
        # 완전히 틀어진다 -- fol_xform.parentInverseMatrix로 반드시 로컬 변환해야
        # 한다(_build_fk_chain/_build_skin_joints와 동일한 matrix-follow 패턴).
        compose = cmds.createNode('composeMatrix', n='{}_output{:02d}_worldComposeCMX'.format(name, idx))
        cmds.connectAttr(fol_shape+'.outTranslate', compose+'.inputTranslate')
        cmds.connectAttr(fol_shape+'.outRotate', compose+'.inputRotate')

        local_mm = cmds.createNode('multMatrix', n='{}_output{:02d}_toLocalMMX'.format(name, idx))
        cmds.connectAttr(compose+'.outputMatrix', local_mm+'.matrixIn[0]')
        cmds.connectAttr(fol_xform+'.parentInverseMatrix[0]', local_mm+'.matrixIn[1]')

        local_dcm = cmds.createNode('decomposeMatrix', n='{}_output{:02d}_toLocalDCM'.format(name, idx))
        cmds.connectAttr(local_mm+'.matrixSum', local_dcm+'.inputMatrix')
        cmds.connectAttr(local_dcm+'.outputTranslate', fol_xform+'.translate')
        cmds.connectAttr(local_dcm+'.outputRotate', fol_xform+'.rotate')

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


def _build_twist_controls(name, curve, up_vector, ctl_grp, ctrl_radius, front_axis='x', up_local_axis='y'):
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
    front_idx, up_idx = _AXIS_INDEX[front_axis], _AXIS_INDEX[up_local_axis]
    front_vec = _AXIS_VECTOR[front_axis]
    crv_shape = cmds.listRelatives(curve, shapes=True, ni=True, fullPath=True)[0]
    ctrls = []
    for label, default_param in (('Start', 0.0), ('End', 1.0)):
        ctrl = cmds.circle(n='{}_Twist{}_CTL'.format(name, label), ch=False,
                            nr=front_vec, r=ctrl_radius*1.4)[0]
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
        cmds.setAttr(mp+'.frontAxis', front_idx)
        cmds.setAttr(mp+'.upAxis', up_idx)
        cmds.setAttr(mp+'.worldUpType', 3)
        cmds.setAttr(mp+'.worldUpVectorX', up_vector[0])
        cmds.setAttr(mp+'.worldUpVectorY', up_vector[1])
        cmds.setAttr(mp+'.worldUpVectorZ', up_vector[2])

        # motionPath의 geometryPath가 월드 스페이스 curve라 allCoordinates/rotate도
        # 월드 스페이스로 나온다 -- off.translate/rotate는 로컬이라 ctl_grp(->rig_grp)
        # 체인이 월드 원점이 아니면 그대로 연결 시 위치가 틀어진다. off.parentInverseMatrix
        # 로 반드시 로컬 변환해야 한다(_build_output_follicles와 동일한 이유/패턴).
        compose = cmds.createNode('composeMatrix', n='{}_Twist{}_worldComposeCMX'.format(name, label))
        cmds.connectAttr(mp+'.allCoordinates', compose+'.inputTranslate')
        cmds.connectAttr(mp+'.rotate', compose+'.inputRotate')

        local_mm = cmds.createNode('multMatrix', n='{}_Twist{}_toLocalMMX'.format(name, label))
        cmds.connectAttr(compose+'.outputMatrix', local_mm+'.matrixIn[0]')
        cmds.connectAttr(off+'.parentInverseMatrix[0]', local_mm+'.matrixIn[1]')

        local_dcm = cmds.createNode('decomposeMatrix', n='{}_Twist{}_toLocalDCM'.format(name, label))
        cmds.connectAttr(local_mm+'.matrixSum', local_dcm+'.inputMatrix')
        cmds.connectAttr(local_dcm+'.outputTranslate', off+'.translate')
        cmds.connectAttr(local_dcm+'.outputRotate', off+'.rotate')

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


def _build_volume_controls(name, curve, surface, num_volume, ctl_grp, ctrl_radius,
                            front_axis='x', up_local_axis='y'):
    """curve 위 고정 위치(0~1 균등)에 volumeY/volumeZ attribute를 가진 컨트롤
    num_volume개를 만든다. 인접 두 컨트롤 사이를 선형보간해서 Skin joint의
    scaleY/Z(aim축과 수직인 두 축)에 각각 연결하면 구간별 squash/stretch 볼륨
    보정이 된다.
    """
    front_vec = _AXIS_VECTOR[front_axis]
    positions = [i/float(num_volume-1) for i in range(num_volume)] if num_volume > 1 else [0.0]
    ctrls = []
    for i, frac in enumerate(positions):
        u_param = _raw_param_at_fraction(curve, frac)
        pos, rot = _sample_surface_frame(surface, u_param, front_axis, up_local_axis)
        ctrl = cmds.circle(n='{}_Volume{:02d}_CTL'.format(name, i+1), ch=False,
                            nr=front_vec, r=ctrl_radius*1.15)[0]
        off = cmds.group(ctrl, n='{}_Volume{:02d}_OFF'.format(name, i+1))
        cmds.xform(off, ws=True, t=pos, ro=rot)
        cmds.setAttr(ctrl+'.overrideEnabled', 1)
        cmds.setAttr(ctrl+'.overrideColor', 14)
        cmds.addAttr(ctrl, ln='volumeY', at='double', min=-10, max=10, dv=0, k=True)
        cmds.addAttr(ctrl, ln='volumeZ', at='double', min=-10, max=10, dv=0, k=True)
        cmds.parent(off, ctl_grp)
        ctrls.append(ctrl)
    return ctrls, positions


def _connect_volume_to_skin(name, volume_ctrls, positions, skin_jnts):
    """Volume 컨트롤의 OFF 그룹이 같은 위치(positions[i]의 t)의 Skin joint를
    라이브로 따라가게 한다(multMatrix: skin_jnt.worldMatrix[0] *
    off.parentInverseMatrix[0] -> decomposeMatrix -> OFF.translate/rotate --
    _build_fk_chain/_build_skin_joints와 동일한 matrix-follow 패턴).

    Volume 컨트롤은 build 시점에 curve 위 정적 위치에 한 번 배치되는데(
    _build_volume_controls), 그 뒤로는 리그가 애니메이션으로 휘어져도 그
    자리에 그대로 남아 있었다 -- 이 connection을 걸면 해당 위치에 가장 가까운
    Skin joint의 실제 world pose를 그대로 따라간다. 연결 대상은 CTL이 아니라
    그 부모인 OFF 그룹이라 CTL 자신의 로컬 transform은 계속 0으로 비워둘 수
    있고, 애니메이터가 그 위에 추가로 오프셋을 얹을 수 있다(다른 단계의
    NUL/CTL 패턴과 동일).

    positions(Volume 컨트롤들의 고정 arc-length fraction)와 Skin joint 개수로
    가장 가까운 인덱스를 골라 매칭한다 -- Volume 컨트롤 개수와 Skin joint
    개수가 다를 수 있어서(기본 5개 vs 기본 25개) 1:1 대응이 아니라 fraction
    기준 최근접 매칭을 쓴다.
    """
    num_skin = len(skin_jnts)
    for i, (ctrl, t) in enumerate(zip(volume_ctrls, positions)):
        off = cmds.listRelatives(ctrl, parent=True, fullPath=True)[0]
        skin_idx = int(round(t*(num_skin-1))) if num_skin > 1 else 0
        skin_idx = max(0, min(num_skin-1, skin_idx))
        jnt = skin_jnts[skin_idx]

        mm = cmds.createNode('multMatrix', n='{}_Volume{:02d}_followMMX'.format(name, i+1))
        cmds.connectAttr(jnt+'.worldMatrix[0]', mm+'.matrixIn[0]')
        cmds.connectAttr(off+'.parentInverseMatrix[0]', mm+'.matrixIn[1]')

        dcm = cmds.createNode('decomposeMatrix', n='{}_Volume{:02d}_followDCM'.format(name, i+1))
        cmds.connectAttr(mm+'.matrixSum', dcm+'.inputMatrix')
        cmds.connectAttr(dcm+'.outputTranslate', off+'.translate')
        cmds.connectAttr(dcm+'.outputRotate', off+'.rotate')


def _apply_volume_scale(name, skin_jnts, volume_ctrls, positions):
    """Volume 컨트롤 값(-10~10)을 /10으로 정규화해서 1+delta 형태의 scale로
    만들고, volumeY는 Skin joint scaleY에, volumeZ는 scaleZ에 연결한다
    (aim축인 scaleX는 그대로 둔다 --
    길이 방향까지 스케일하면 stretch 계산과 겹쳐서 이중으로 늘어난다).
    """
    num = len(skin_jnts)
    for i, jnt in enumerate(skin_jnts):
        t = i/float(num-1) if num > 1 else 0.0
        vol_y_plug = _gradient_plug(volume_ctrls, 'volumeY', positions, t,
                                    '{}_Skin{:02d}_volumeY'.format(name, i+1))
        norm_y = cmds.createNode('multDoubleLinear', n='{}_Skin{:02d}_volumeYNorm_MDL'.format(name, i+1))
        cmds.setAttr(norm_y+'.input2', 0.1)
        cmds.connectAttr(vol_y_plug, norm_y+'.input1')
        scale_y = cmds.createNode('addDoubleLinear', n='{}_Skin{:02d}_volumeYScale_ADL'.format(name, i+1))
        cmds.setAttr(scale_y+'.input1', 1.0)
        cmds.connectAttr(norm_y+'.output', scale_y+'.input2')
        cmds.connectAttr(scale_y+'.output', jnt+'.scaleY')

        vol_z_plug = _gradient_plug(volume_ctrls, 'volumeZ', positions, t,
                                    '{}_Skin{:02d}_volumeZ'.format(name, i+1))
        norm_z = cmds.createNode('multDoubleLinear', n='{}_Skin{:02d}_volumeZNorm_MDL'.format(name, i+1))
        cmds.setAttr(norm_z+'.input2', 0.1)
        cmds.connectAttr(vol_z_plug, norm_z+'.input1')
        scale_z = cmds.createNode('addDoubleLinear', n='{}_Skin{:02d}_volumeZScale_ADL'.format(name, i+1))
        cmds.setAttr(scale_z+'.input1', 1.0)
        cmds.connectAttr(norm_z+'.output', scale_z+'.input2')
        cmds.connectAttr(scale_z+'.output', jnt+'.scaleZ')


def build_twist_scale(name='tentacle', num_volume=5, ctrl_radius=0.8,
                       up_axis=None, front_axis=None, up_local_axis=None):
    """5단계: Twist 시작/끝 컨트롤 2개를 만들어 FK 체인에 그라디언트로 가산하고
    (FK/Skin을 twist_ctrls와 함께 재빌드), Volume 컨트롤 num_volume개를 만들어
    최종 Skin joint의 scaleY/Z에 구간별 볼륨 그라디언트로 각각 연결한다. 또한 각
    Volume 컨트롤의 OFF 그룹을 같은 위치의 Skin joint에 라이브로 연결해서
    (_connect_volume_to_skin) 리그가 휘어질 때 Volume 컨트롤이 그 표면 위치를
    따라가게 한다.

    build_output()/build_fk()가 먼저 실행되어 있어야 한다. FK 체인은 Twist를
    얹기 위해 build_fk()를 내부적으로 다시 호출해서 재빌드한다(fk_ctrls의
    로컬 회전 등 그 사이 애니메이터가 손댄 값은 다시 0으로 초기화됨 -- 리그
    구성 단계이므로 문제 없음). Volume 컨트롤은 build_fk() 재호출로 skin_jnts가
    다시 만들어진 뒤에 연결해야 하므로, _build_volume_controls -> build_fk() ->
    _connect_volume_to_skin 순서로 호출한다.

    Arguments:
        name (str): 이전 단계와 동일한 리그 네이밍 프리픽스
        num_volume (int): Volume 컨트롤 개수(참조 리그와 동일하게 기본 5)
        ctrl_radius (float): build_fk()에 그대로 전달할 FK 컨트롤 shape 반경
        up_axis (str): build_base()/build_ik()가 저장한 값을 override(None이면
            그대로 씀). build_ik()와 동일한 override+저장 방식(_set_up_axis).
        front_axis (str): 위와 동일한 방식의 override(컨트롤 로컬 forward축).
        up_local_axis (str): 위와 동일한 방식의 override(컨트롤 로컬 up축).

    Returns:
        dict: twist_ctrls, volume_ctrls, fk_ctrls, skin_jnts
    """
    rig_grp = '{}_rig_GRP'.format(name)
    curve = '{}_CRV'.format(name)
    surface = '{}_NSF'.format(name)
    follicles = cmds.ls('{}_output*_FOL'.format(name))
    if not cmds.objExists(rig_grp) or not cmds.objExists(curve) or not follicles:
        raise RuntimeError('build_twist_scale: build_output()을 먼저 실행하세요 ({} 없음)'.format(rig_grp))

    axis = cmds.getAttr(rig_grp+'.tentacleAxis')
    if up_axis is not None:
        _set_up_axis(rig_grp, up_axis)
    up_vector = _get_up_vector(rig_grp, axis)

    stored_front_axis, stored_up_local_axis = _get_ctrl_axes(rig_grp)
    front_axis = front_axis if front_axis is not None else stored_front_axis
    up_local_axis = up_local_axis if up_local_axis is not None else stored_up_local_axis
    if front_axis == up_local_axis:
        raise ValueError('build_twist_scale: front_axis({})는 up_local_axis({})와 달라야 합니다'.format(
            front_axis, up_local_axis))
    _set_ctrl_axes(rig_grp, front_axis, up_local_axis)

    twist_grp_name = '{}_twistCtl_GRP'.format(name)
    volume_grp_name = '{}_volumeCtl_GRP'.format(name)
    for grp_name in (twist_grp_name, volume_grp_name):
        if cmds.objExists(grp_name):
            cmds.delete(grp_name)

    twist_grp = cmds.createNode('transform', n=twist_grp_name, p=rig_grp)
    volume_grp = cmds.createNode('transform', n=volume_grp_name, p=rig_grp)

    twist_ctrls = _build_twist_controls(name, curve, up_vector, twist_grp, ctrl_radius,
                                         front_axis=front_axis, up_local_axis=up_local_axis)
    volume_ctrls, positions = _build_volume_controls(name, curve, surface, num_volume, volume_grp, ctrl_radius,
                                                       front_axis=front_axis, up_local_axis=up_local_axis)

    fk_result = build_fk(name=name, ctrl_radius=ctrl_radius, twist_ctrls=twist_ctrls)
    _connect_volume_to_skin(name, volume_ctrls, positions, fk_result['skin_jnts'])
    _apply_volume_scale(name, fk_result['skin_jnts'], volume_ctrls, positions)

    print('=' * 60)
    print('Tentacle Ribbon Twist/Volume 완료: {}'.format(name))
    print('  twist ctrls  : {}'.format(twist_ctrls))
    print('  volume ctrls : {}'.format(len(volume_ctrls)))
    print('=' * 60)
    return {'twist_ctrls': twist_ctrls, 'volume_ctrls': volume_ctrls,
            'fk_ctrls': fk_result['fk_ctrls'], 'skin_jnts': fk_result['skin_jnts']}


def _build_top_fk_ik_controls(name, curve, surface, num_ctrl, fk_radius, ik_radius, ctl_grp,
                               front_axis='x', up_local_axis='y'):
    """curve 위에 FK 컨트롤 num_ctrl개를 실제 체인(FK{i}_OFF가 FK{i-1}_CTL의
    자식)으로 쌓고, 각 FK_CTL의 자식으로 IK 컨트롤을 하나씩 둔다 -- FK가
    상위/마스터(체인이라 앞쪽 FK를 돌리면 뒤쪽 전체가 같이 딸려온다, 일반적인
    FK 체인과 동일), IK가 그 밑에서 로컬로 미세 조정하는 하위 레이어(TOP
    전용 하이라키, Demo의 FK-follows-IK-via-follicle 구조와는 반대 방향).
    IK 컨트롤의 최종 world pose(부모 FK 체인 전체의 누적 포즈 + 자기 로컬
    오프셋의 합)가 NurbsBind joint를 구동해서 표면을 스킨한다.
    """
    front_vec = _AXIS_VECTOR[front_axis]
    fk_ctrls, ik_ctrls = [], []
    parent_node = ctl_grp
    for i in range(num_ctrl):
        frac = i/float(num_ctrl-1) if num_ctrl > 1 else 0.0
        idx = i+1
        u_param = _raw_param_at_fraction(curve, frac)
        pos, rot = _sample_surface_frame(surface, u_param, front_axis, up_local_axis)

        fk_ctrl = cmds.circle(n='{}_FK{:02d}_CTL'.format(name, idx), ch=False, nr=front_vec, r=fk_radius)[0]
        fk_off = cmds.group(fk_ctrl, n='{}_FK{:02d}_OFF'.format(name, idx))
        cmds.xform(fk_off, ws=True, t=pos, ro=rot)
        cmds.setAttr(fk_ctrl+'.overrideEnabled', 1)
        cmds.setAttr(fk_ctrl+'.overrideColor', 6)
        cmds.parent(fk_off, parent_node)

        ik_ctrl = cmds.circle(n='{}_IK{:02d}_CTL'.format(name, idx), ch=False, nr=front_vec, r=ik_radius)[0]
        cmds.setAttr(ik_ctrl+'.overrideEnabled', 1)
        cmds.setAttr(ik_ctrl+'.overrideColor', 17)
        cmds.parent(ik_ctrl, fk_ctrl)
        cmds.setAttr(ik_ctrl+'.translate', 0, 0, 0)
        cmds.setAttr(ik_ctrl+'.rotate', 0, 0, 0)

        fk_ctrls.append(fk_ctrl)
        ik_ctrls.append(ik_ctrl)
        parent_node = fk_ctrl

    return fk_ctrls, ik_ctrls


def _build_master_drive_follicles(branch_name, top_curve, top_surface, main_ik_offsets, sys_grp,
                                   front_axis='x', up_local_axis='y'):
    """top_surface(TOP의 FK/IK로 변형된 서피스) 위에 main_ik_offsets와 같은
    개수의 follicle을, main_ik_offsets가 원래 놓인 것과 동일한 arc-length
    fraction의 parameterU에 배치한다(_static_param_at_fraction) -- 서피스의
    raw parameterU를 그 fraction 값으로 직접 쓰면 안 된다(surface parameter는
    arc length와 선형 관계가 아니라서, 원래 main IK가 커브의 arc-length
    기준으로 배치된 위치와 다른 지점을 가리키게 된다). top_curve(TOP 서피스에서
    추출한 curve, top_surface의 v=0.5 isoparm이라 parameter range/값이
    top_surface의 parameterU와 그대로 대응한다)의 arc-length fraction에서
    parameter를 빌드 타임에 직접 계산해서 고정한다.

    예전엔 이 U를 (1) closestPointOnSurface로 서피스 전체(U, V 둘 다)에서
    찾거나 (2) motionPath로 3D 위치를 얻은 뒤 nearestPointOnCurve로 그 위치에
    가장 가까운 점을 curve에서 다시 찾는 방식으로 구했는데, 둘 다 '3D 위치
    기준으로 가장 가까운 점 찾기'라는 공통 결함이 있었다 -- 촉수답게 실제로
    구불구불 말리면(curl) 서로 다른 arc-length 구간이 3D 공간에서 서로
    가까이 지나가는 경우가 흔해서, '가장 가까운 점'이 의도한 지점이 아니라
    근처를 지나가는 다른 구간을 잘못 짚었다(빌드 직후, 애니메이터가 아무것도
    안 만졌는데도 main IK_OFF/base NSF가 크게 틀어져 보이는 원인 -- 양 끝점만
    우연히 맞고 중간 지점들은 전부 틀어지는 패턴으로 나타났다).
    _static_param_at_fraction(findParamFromLength)은 3D 위치 검색이 전혀 없이
    curve 자신의 arc-length만 따라가는 1차원 이분탐색이라 curve가 스스로 얼마나
    가까이 지나가든 절대 모호해지지 않는다.

    follicle의 outTranslate/outRotate는 월드 스페이스다(_build_output_follicles와
    동일한 이유) -- 그런데 main_ik_offsets(off)는 LOCAL translate/rotate라서
    바로 연결하면 안 된다. off의 부모 체인(ctl_grp -> rig_grp)이 항상 월드
    원점(identity)이라는 보장이 없기 때문이다(실제 프로덕션에서는 리그 전체를
    캐릭터 위 다른 위치/회전으로 옮겨두는 게 정상). 그래서 매번 off.
    parentInverseMatrix로 로컬로 변환해야 한다(_build_fk_chain/_build_skin_joints
    와 동일한 matrix-follow 패턴).

    거기에 축 보정도 같은 matrixSum 체인에서 같이 처리한다(matrixIn[0]=remap
    -- _axis_remap_matrix) -- follicle 노드는 항상 자기 로컬 X=tangent/
    Y=up-vector 기준으로만 회전을 낸다(front_axis/up_local_axis를 모른다).
    main IK_OFF는 build_ik() 때 front_axis/up_local_axis 기준으로 배치돼
    있으므로, 그 축이 기본값('x'/'y')이 아니면 follicle의 raw outRotate를
    그대로 연결하는 순간 IK_OFF의 회전이 follicle의 기본 축 배치로 홱
    돌아가 버린다(빌드 직후, 애니메이터가 아무것도 안 만졌는데도 rest pose가
    바뀌는 것처럼 보임) -- 그래서 remap을 적용해야 build_ik()가 잡은 방향과
    어긋나지 않는다.

    main의 IK_CTL 자신은 그 OFF의 자식으로 그대로 남아 애니메이터가 그
    위에 추가로 움직일 수 있다(FK NUL/CTL과 동일한 패턴). 결과적으로 TOP을
    움직이면 그 서피스 변형이 follicle을 통해 그대로 main(Demo)의 IK
    컨트롤 위치/방향을 구동하는 마스터-슬레이브 관계가 된다.
    """
    remap = _axis_remap_matrix(front_axis, up_local_axis)
    surf_shape = cmds.listRelatives(top_surface, shapes=True, ni=True, fullPath=True)[0]
    num = len(main_ik_offsets)
    fols = []
    for i, off in enumerate(main_ik_offsets):
        frac = i/float(num-1) if num > 1 else 0.0
        idx = i+1
        param = _static_param_at_fraction(top_curve, frac)

        fol_shape = cmds.createNode('follicle', n='{}_drive{:02d}_FOLShape'.format(branch_name, idx))
        fol_xform = cmds.listRelatives(fol_shape, parent=True)[0]
        fol_xform = cmds.rename(fol_xform, '{}_drive{:02d}_FOL'.format(branch_name, idx))
        cmds.connectAttr(surf_shape+'.local', fol_shape+'.inputSurface')
        cmds.connectAttr(surf_shape+'.worldMatrix[0]', fol_shape+'.inputWorldMatrix')
        cmds.setAttr(fol_shape+'.parameterU', param)
        cmds.setAttr(fol_shape+'.parameterV', 0.5)

        # follicle.outTranslate/outRotate는 월드 스페이스다(_build_output_follicles와
        # 동일). off는 tentacle_ikCtl_GRP -> tentacle_rig_GRP 밑이라 그 체인이 항상
        # identity(월드 원점)라는 보장이 없다 -- 실제 프로덕션에서는 리그 전체를
        # 캐릭터 위 다른 위치/회전으로 옮겨두는 게 정상이라, 그 경우 월드 값을
        # local attribute에 그냥 꽂으면 위치/회전이 완전히 틀어진다. 그래서
        # off.parentInverseMatrix로 로컬 공간으로 변환하는 단계가 반드시 필요하다
        # -- axis remap(follicle 고유 축 -> front_axis/up_local_axis)까지 같은
        # matrixSum 체인에서 한 번에 처리한다(remap * 월드 매트릭스 * parentInverseMatrix).
        compose = cmds.createNode('composeMatrix', n='{}_drive{:02d}_worldComposeCMX'.format(branch_name, idx))
        cmds.connectAttr(fol_shape+'.outTranslate', compose+'.inputTranslate')
        cmds.connectAttr(fol_shape+'.outRotate', compose+'.inputRotate')

        local_mm = cmds.createNode('multMatrix', n='{}_drive{:02d}_toLocalMMX'.format(branch_name, idx))
        cmds.setAttr(local_mm+'.matrixIn[0]', remap, type='matrix')
        cmds.connectAttr(compose+'.outputMatrix', local_mm+'.matrixIn[1]')
        cmds.connectAttr(off+'.parentInverseMatrix[0]', local_mm+'.matrixIn[2]')

        local_dcm = cmds.createNode('decomposeMatrix', n='{}_drive{:02d}_toLocalDCM'.format(branch_name, idx))
        cmds.connectAttr(local_mm+'.matrixSum', local_dcm+'.inputMatrix')
        cmds.connectAttr(local_dcm+'.outputTranslate', off+'.translate')
        cmds.connectAttr(local_dcm+'.outputRotate', off+'.rotate')

        cmds.parent(fol_xform, sys_grp)
        fols.append(fol_xform)
    return fols


def build_branch(name='tentacle', branch_name='topTentacle', num_ctrl=4, fk_radius=0.9, ik_radius=0.6,
                  up_axis=None, front_axis=None, up_local_axis=None):
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
        up_axis (str): main(name)에 저장된 값을 override(None이면 그대로 씀).
            base/top이 항상 같은 축을 쓰도록, override하면 main_rig_grp의
            저장값도 같이 갱신한다(build_ik()와 동일한 이유 -- 안 그러면 이후
            main 쪽에서 build_ik()/build_twist_scale()을 다시 돌릴 때 옛
            값으로 되돌아가 버린다).
        front_axis (str): 위와 동일한 방식의 override(컨트롤 로컬 forward축).
        up_local_axis (str): 위와 동일한 방식의 override(컨트롤 로컬 up축).

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
    if up_axis is not None:
        _set_up_axis(main_rig_grp, up_axis)
    up_axis = cmds.getAttr(main_rig_grp+'.tentacleUpAxis') if cmds.attributeQuery(
        'tentacleUpAxis', node=main_rig_grp, exists=True) else _DEFAULT_UP_AXIS[axis]

    stored_front_axis, stored_up_local_axis = _get_ctrl_axes(main_rig_grp)
    front_axis = front_axis if front_axis is not None else stored_front_axis
    up_local_axis = up_local_axis if up_local_axis is not None else stored_up_local_axis
    if front_axis == up_local_axis:
        raise ValueError('build_branch: front_axis({})는 up_local_axis({})와 달라야 합니다'.format(
            front_axis, up_local_axis))
    _set_ctrl_axes(main_rig_grp, front_axis, up_local_axis)

    g = _build_groups(branch_name)
    cmds.addAttr(g['rig'], ln='tentacleAxis', dt='string')
    cmds.setAttr(g['rig']+'.tentacleAxis', axis, type='string')
    cmds.addAttr(g['rig'], ln='tentacleUpAxis', dt='string')
    cmds.setAttr(g['rig']+'.tentacleUpAxis', up_axis, type='string')
    cmds.addAttr(g['rig'], ln='tentacleCtrlFrontAxis', dt='string')
    cmds.setAttr(g['rig']+'.tentacleCtrlFrontAxis', front_axis, type='string')
    cmds.addAttr(g['rig'], ln='tentacleCtrlUpAxis', dt='string')
    cmds.setAttr(g['rig']+'.tentacleCtrlUpAxis', up_local_axis, type='string')
    # relative=True(월드 프리저브 없이 그대로 붙임)가 필수다 -- 기본 동작(월드
    # 위치 보존)으로 붙이면, g['rig']가 (막 만들어진 직후라 identity인) 현재
    # 월드 위치를 유지하려고 main_rig_grp의 오프셋을 상쇄하는 local transform을
    # 자동으로 넣어버린다. 그러면 TOP의 duplicate 서피스가 main_rig_grp가 월드
    # 원점이 아닐 때(실제 리그를 캐릭터 위로 옮겨둔 상태) main의 서피스와 같은
    # 월드 프레임에 있지 않게 되어, _build_master_drive_follicles가 그 위에서
    # 계산한 arc-length 위치가 main IK_OFF가 실제로 있어야 할 위치와 어긋난다.
    cmds.parent(g['rig'], main_rig_grp, relative=True)

    surface = cmds.duplicate(main_surface, n='{}_NSF'.format(branch_name), renameChildren=True)[0]
    cmds.parent(surface, g['geo'])

    out_crv = _extract_curve_from_surface(branch_name, surface)
    cmds.parent(out_crv, g['geo'])
    rest_length = _store_rest_length(out_crv)

    ctl_grp = cmds.createNode('transform', n='{}_ctl_GRP'.format(branch_name), p=g['rig'])
    jnt_grp = cmds.createNode('transform', n='{}_bindJnt_GRP'.format(branch_name), p=g['sys'])

    fk_ctrls, ik_ctrls = _build_top_fk_ik_controls(branch_name, out_crv, surface, num_ctrl,
                                                     fk_radius, ik_radius, ctl_grp,
                                                     front_axis=front_axis, up_local_axis=up_local_axis)
    bind_jnts = _build_nurbs_bind_joints(branch_name, ik_ctrls, ik_ctrls, jnt_grp)
    skin = _skin_ribbon_surface(branch_name, surface, bind_jnts)

    drive_fols = _build_master_drive_follicles(branch_name, out_crv, surface, main_ik_offsets, g['sys'],
                                                front_axis=front_axis, up_local_axis=up_local_axis)

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
    build_base(mesh='pSphere1')
    build_ik()
    build_output()
    build_fk()
    build_twist_scale()
    build_branch()
