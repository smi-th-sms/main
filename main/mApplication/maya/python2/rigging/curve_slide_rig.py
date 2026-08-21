# -*- coding: utf-8 -*-
"""============================================================================
Curve Slide Rig -- 범용 커브 슬라이드 유틸리티

임의의 NURBS curve(어떤 degree든, 그대로 유지) 위에 실제 CV 개수만큼 NUL을
만들어 curve 위 지점을 라이브로 따라가게 하고, 그 NUL로 curve를 복제한
curve의 controlPoints를 구동하는 독립 툴. tentacle_ribbon_rig.py와 무관한
별도 모듈 -- 리본 서피스/mesh 분석 없이, 이미 존재하는 curve 하나만 있으면
바로 쓸 수 있다.

1. (build_cv_nulls) CV 개수 기준 NUL로 복제 curve 구동: curve의 실제 CV
   개수(numCVs, degree를 바꾸지 않음)만큼 NUL을 만들어 pointOnCurveInfo로
   curve 위 지점을 라이브로 따라가게 하고(각 NUL의 base parameter는
   min_p~max_p 구간을 CV 개수만큼 균등 분할한 fraction), 동시에 curve를
   복제한 {name}_cvDriven_CRV의 같은 인덱스 controlPoints에 NUL의
   translate를 연결해서 반대로 NUL이 그 복제 curve를 구동하게 한다(복제라
   CV 개수가 항상 자기 자신과 같아서 별도 검증이 필요 없다). degree가 2
   이상이면 CV가 curve 위에 실제로 있지는 않으므로 NUL 위치가 정확히 그
   CV 자리라는 보장은 없다. 단일 컨트롤 {name}_cvSlideMaster_CTL의
   Slide(-1~1) attribute 하나로 전체 NUL을 간격 유지한 채 함께 밀 수
   있다(끝에 닿으면 그 끝에서부터 뭉침).

2. (show_ui) 선택 기반 간단 UI: curve(들)을 선택하고 버튼만 누르면 되는
   최소 UI -- name은 각 curve 이름에서 자동으로 뽑고(_derive_name), 나머지
   옵션은 전부 기본값을 쓴다. curve 여러 개를 동시에 선택하면 각각
   독립적으로 빌드된다.

:Example:
    from python2.rigging import curve_slide_rig
    import importlib
    importlib.reload(curve_slide_rig)

    # 코드로 직접 호출:
    curve_slide_rig.build_cv_nulls(curve='curve1', name='spine')

    # 또는 curve(들)을 선택하고 버튼으로:
    curve_slide_rig.show_ui()
============================================================================"""
import maya.cmds as cmds
import maya.api.OpenMaya as om2


def _shape_of(node):
    shapes = cmds.listRelatives(node, shapes=True, ni=True, fullPath=True)
    if not shapes:
        raise RuntimeError('_shape_of: {}에 shape가 없습니다'.format(node))
    return shapes[0]


def _cv_count(curve_shape):
    sel = om2.MSelectionList()
    sel.add(curve_shape)
    curve_fn = om2.MFnNurbsCurve(sel.getDagPath(0))
    return curve_fn.numCVs


def _knot_domain(curve_shape):
    """curve의 실제 parameter 구간(min, max)을 knot vector에서 직접 읽는다
    (Slide 0~1을 이 구간으로 선형 리매핑하는 데 쓴다). CV가 애니메이션/
    변형으로 움직여도 knot vector 자체(구간)는 바뀌지 않으므로 build
    타임에 한 번만 읽어서 고정값으로 써도 된다.
    """
    sel = om2.MSelectionList()
    sel.add(curve_shape)
    curve_fn = om2.MFnNurbsCurve(sel.getDagPath(0))
    return curve_fn.knotDomain


def build_cv_nulls(curve, name='curveSlide'):
    """curve의 실제 CV 개수(numCVs, curve의 degree 그대로 -- degree를
    바꾸거나 근사하지 않는다)만큼 NUL을 만들어 pointOnCurveInfo로 curve 위
    지점을 라이브로 따라가게 한다. 각 NUL의 pointOnCurveInfo parameter는
    min_p~max_p 구간을 CV 개수만큼 균등 분할한 fraction이다(i/(num_cv-1)).
    degree가 2 이상이면 CV가 curve 위에 실제로 있지는 않지만(control
    point일 뿐), NUL은 항상 curve 위의 점을 따라가고 그 점으로 CV를
    구동하는 개념이라 정확히 그 CV의 위치라는 보장은 없다 -- 대신 curve의
    degree를 그대로 유지하는 걸 우선한다.

    원본 curve는 건드리지 않는다 -- 먼저 원본을 복제한 {name}_cvBase_CRV를
    만들어서 그걸 실제 기준(base)으로 쓰고, NUL은 이 base curve를
    pointOnCurveInfo로 따라간다. base curve를 다시 복제한
    {name}_cvDriven_CRV의 같은 인덱스 controlPoints에 NUL의 translate를
    직접 connectAttr해서 반대로 NUL이 그 복제 curve를 구동하게 한다 --
    driven도 base의 복제라 degree가 동일하고 CV 개수도 항상 num_cv와
    같으므로(자기 자신의 CV 개수이므로) 별도 검증 없이 항상 1:1로 맞는다.
    base curve는 원본과의 connectAttr 연결이 없는 순수 정적 복제라(그냥
    cmds.duplicate), 원본이 나중에 변형돼도 base/NUL/driven은 따라가지
    않는다 -- 원본 production curve에 아무 outgoing connection도 만들지
    않기 위한 선택.

    NUL과 base/복제 curve 모두 이 함수가 새로 만드는 {name}_cvRig_GRP(월드
    원점, 부모 없음) 바로 아래에 둔다 -- pointOnCurveInfo의 출력, NUL의
    translate가 전부 이미 world space이고, 복제 curve도 makeIdentity로
    자신의 transform을 identity로 구워서(bake) object space 좌표가 world
    space와 같아지므로, 둘 사이에 별도 matrix 보정 없이 바로 연결해도
    정확히 맞는다.

    NUL 하나하나에 개별 Slide를 두지 않고, 이 함수가 새로 만드는 단일
    컨트롤({name}_cvSlideMaster_CTL)의 Slide(-1~1) attribute 하나로 전체
    NUL을 동시에 움직인다 -- base 자리가 이미 min_p~max_p 구간을 끝에서
    끝까지 채우고 있어서 그 상태에서 조금이라도 밀면 반대쪽 끝은 곧바로
    구간을 벗어나므로, Slide*(max_p-min_p)를 모든 NUL의 base parameter에
    똑같이 더한 뒤(offset은 한 번만 계산해서 전체 NUL이 공유)
    clamp(min_p, max_p)로 구간 밖으로 못 나가게 막는다 -- 그래서 전체 NUL이
    간격을 유지한 채 같은 방향/양으로 이동하다가, 어느 한쪽 끝에 닿은
    NUL부터 그 끝에서 뭉치기 시작한다(더 밀면 뭉치는 NUL이 늘어난다).

    Arguments:
        curve (str): 대상 curve(어떤 degree든 상관없음)
        name (str): 리그 네이밍 프리픽스

    Returns:
        dict: rig_grp, nulls, driven_curve, base_curve, master_ctl
    """
    if not cmds.objExists(curve):
        raise RuntimeError('build_cv_nulls: curve {}가 존재하지 않습니다'.format(curve))

    rig_grp_name = '{}_cvRig_GRP'.format(name)
    if cmds.objExists(rig_grp_name):
        cmds.delete(rig_grp_name)
    rig_grp = cmds.createNode('transform', n=rig_grp_name)

    base = cmds.duplicate(curve, n='{}_cvBase_CRV'.format(name))[0]
    if cmds.listRelatives(base, parent=True):
        cmds.parent(base, world=True)
    cmds.parent(base, rig_grp)
    base_shape = _shape_of(base)
    num_cv = _cv_count(base_shape)
    min_p, max_p = _knot_domain(base_shape)

    driven = cmds.duplicate(base, n='{}_cvDriven_CRV'.format(name))[0]
    cmds.makeIdentity(driven, apply=True, t=1, r=1, s=1, n=0)
    if cmds.listRelatives(driven, parent=True):
        cmds.parent(driven, world=True)
    cmds.parent(driven, rig_grp)

    master_ctl = cmds.spaceLocator(n='{}_cvSlideMaster_CTL'.format(name))[0]
    cmds.parent(master_ctl, rig_grp)
    cmds.addAttr(master_ctl, ln='Slide', at='double', min=-1, max=1, dv=0, k=True)

    offset_mdl = cmds.createNode('multDoubleLinear', n='{}_cvSlideOffset_MDL'.format(name))
    cmds.setAttr(offset_mdl+'.input2', max_p-min_p)
    cmds.connectAttr(master_ctl+'.Slide', offset_mdl+'.input1')

    nulls = []
    for i in range(num_cv):
        idx = i+1
        node_prefix = '{}_cv{:02d}'.format(name, idx)
        t = i/float(num_cv-1) if num_cv > 1 else 0.0
        base_param = min_p+(max_p-min_p)*t

        nul = cmds.spaceLocator(n=node_prefix+'_NUL')[0]
        cmds.parent(nul, rig_grp)

        raw_param_adl = cmds.createNode('addDoubleLinear', n=node_prefix+'_rawParam_ADL')
        cmds.setAttr(raw_param_adl+'.input1', base_param)
        cmds.connectAttr(offset_mdl+'.output', raw_param_adl+'.input2')

        clamp = cmds.createNode('clamp', n=node_prefix+'_param_CLM')
        cmds.setAttr(clamp+'.minR', min_p)
        cmds.setAttr(clamp+'.maxR', max_p)
        cmds.connectAttr(raw_param_adl+'.output', clamp+'.inputR')

        poci = cmds.createNode('pointOnCurveInfo', n=node_prefix+'_POCI')
        cmds.setAttr(poci+'.turnOnPercentage', 0)
        cmds.connectAttr(base_shape+'.worldSpace[0]', poci+'.inputCurve')
        cmds.connectAttr(clamp+'.outputR', poci+'.parameter')

        for comp in 'XYZ':
            cmds.connectAttr(poci+'.position'+comp, nul+'.translate'+comp)
        cmds.connectAttr(nul+'.translate', '{}.controlPoints[{}]'.format(driven, i))
        nulls.append(nul)

    print('=' * 60)
    print('Curve Slide Rig CV Nulls 완료: {}'.format(name))
    print('  curve        : {}'.format(curve))
    print('  base curve   : {}'.format(base))
    print('  driven curve : {}'.format(driven))
    print('  nulls        : {}'.format(len(nulls)))
    print('  master ctl   : {}'.format(master_ctl))
    print('=' * 60)
    return {'rig_grp': rig_grp, 'nulls': nulls, 'driven_curve': driven,
            'base_curve': base, 'master_ctl': master_ctl}


def _derive_name(curve):
    """curve transform 이름에서 흔한 접미사(_CRV 등)를 떼어 리그 네이밍
    프리픽스로 쓴다 -- UI에서 매번 name을 입력하지 않아도 되게.
    """
    short = curve.split('|')[-1].split(':')[-1]
    for suffix in ('_CRV', '_crv', '_curve', '_Curve'):
        if short.endswith(suffix):
            return short[:-len(suffix)]
    return short


def _attr_range(node, attr, default=(0.0, 1.0)):
    """node.attr에 이미 min/max가 있으면 그 값을, 없으면(또는 attr 자체가
    없으면) default를 반환한다.
    """
    if not cmds.attributeQuery(attr, node=node, exists=True):
        return default
    if not cmds.attributeQuery(attr, node=node, minExists=True):
        return default
    if not cmds.attributeQuery(attr, node=node, maxExists=True):
        return default
    lo = cmds.attributeQuery(attr, node=node, min=True)[0]
    hi = cmds.attributeQuery(attr, node=node, max=True)[0]
    return lo, hi


def link_slide_attrs(selection=None):
    """선택 리스트의 마지막 오브젝트를 컨트롤러로 삼아, 그 앞의 나머지
    오브젝트들 각각에 대해 그 오브젝트 이름을 딴 attribute를 컨트롤러에
    추가하고, 각 오브젝트에도(없으면 새로) Slide attribute를 만들어서
    컨트롤러의 그 attribute를 연결한다 -- 여러 오브젝트를 각각 개별
    제어할 수 있는 슬라이더를 컨트롤러 하나에 모아두는 범용 유틸리티.
    build_cv_nulls()가 만드는 NUL들처럼 자체 Slide attribute가 없는
    오브젝트에도 쓸 수 있다(이 함수가 만들어준다).

    새로 만드는 두 attribute(컨트롤러의 것과 target.Slide)의 min/max는
    항상 서로 동일하게 맞춘다 -- target.Slide가 이미 있으면 그 min/max를
    그대로 따르고(없으면 컨트롤러 쪽에 이미 있는 값을 따르고), 둘 다
    없으면 기본값 0~1을 함께 쓴다. 이미 있는 attribute는 range를 건드리지
    않는다(새로 만들 때만 적용).

    이미 같은 이름의 attribute/연결이 있으면 새로 만들지 않고 그대로
    재사용한다 -- 같은 선택으로 다시 실행해도 안전하다(재실행 가능).

    Arguments:
        selection (list): [target1, target2, ..., targetN, controller] 순서.
            None이면 현재 뷰포트 선택을 그대로 쓴다(마지막이 컨트롤러).

    Returns:
        dict: controller, targets, attrs
    """
    sel = selection if selection is not None else (cmds.ls(selection=True, long=True) or [])
    if len(sel) < 2:
        raise RuntimeError('link_slide_attrs: 오브젝트를 최소 2개(타겟 1개 이상 + '
                            '마지막 컨트롤러) 선택하세요.')

    controller = sel[-1]
    targets = sel[:-1]

    attrs = []
    for target in targets:
        attr_name = _derive_name(target)
        target_has_slide = cmds.attributeQuery('Slide', node=target, exists=True)
        controller_has_attr = cmds.attributeQuery(attr_name, node=controller, exists=True)

        if target_has_slide:
            lo, hi = _attr_range(target, 'Slide')
        elif controller_has_attr:
            lo, hi = _attr_range(controller, attr_name)
        else:
            lo, hi = 0.0, 1.0

        if not controller_has_attr:
            cmds.addAttr(controller, ln=attr_name, at='double', min=lo, max=hi, dv=lo, k=True)
        if not target_has_slide:
            cmds.addAttr(target, ln='Slide', at='double', min=lo, max=hi, dv=lo, k=True)
        if not cmds.isConnected('{}.{}'.format(controller, attr_name), '{}.Slide'.format(target)):
            cmds.connectAttr('{}.{}'.format(controller, attr_name), '{}.Slide'.format(target), force=True)
        attrs.append(attr_name)

    print('=' * 60)
    print('Curve Slide Rig Link Slide Attrs 완료')
    print('  controller : {}'.format(controller))
    print('  targets    : {}'.format(len(targets)))
    print('=' * 60)
    return {'controller': controller, 'targets': targets, 'attrs': attrs}


def _selected_curves():
    """현재 선택 중에서 curve transform만 골라 반환한다(curve shape나 다른
    타입 노드를 선택해도 그 부모 transform으로 정규화).
    """
    sel = cmds.ls(selection=True, long=True) or []
    curves = []
    for node in sel:
        if cmds.nodeType(node) == 'nurbsCurve':
            parent = cmds.listRelatives(node, parent=True, fullPath=True)
            if parent:
                curves.append(parent[0])
            continue
        shapes = cmds.listRelatives(node, shapes=True, type='nurbsCurve', fullPath=True)
        if shapes:
            curves.append(node)
    return curves


def _ui_build_cv_nulls(*_args):
    curves = _selected_curves()
    if not curves:
        cmds.warning('curve_slide_rig: curve를 먼저 선택하세요.')
        return
    for curve in curves:
        build_cv_nulls(curve=curve, name=_derive_name(curve))


def _ui_link_slide_attrs(*_args):
    try:
        link_slide_attrs()
    except RuntimeError as e:
        cmds.warning(str(e))


def show_ui():
    """선택한 curve(들) 기준으로 build_cv_nulls()를 실행하거나, 선택한
    오브젝트들의 Slide attribute를 마지막 오브젝트에 모아 연결하는 간단한
    버튼 두 개짜리 UI. name은 각 curve 이름에서 자동으로 뽑는다
    (_derive_name) -- curve 여러 개를 동시에 선택하면 그 개수만큼 각각
    독립적으로 빌드된다.
    """
    win_name = 'curveSlideRigUI'
    if cmds.window(win_name, exists=True):
        cmds.deleteUI(win_name)

    cmds.window(win_name, title='Curve Slide Rig', sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnAttach=('both', 8))
    cmds.text(label='curve(들)을 선택한 뒤 버튼을 누르세요.', align='left')
    cmds.separator(height=8, style='in')
    cmds.button(label='Build CV Nulls', height=32, command=_ui_build_cv_nulls)
    cmds.separator(height=8, style='in')
    cmds.text(label='타겟들 + 마지막에 컨트롤러를 선택한 뒤 누르세요.', align='left')
    cmds.button(label='Link Slide Attrs', height=32, command=_ui_link_slide_attrs)
    cmds.separator(height=8, style='in')
    cmds.showWindow(win_name)


if __name__ == '__main__':
    show_ui()
