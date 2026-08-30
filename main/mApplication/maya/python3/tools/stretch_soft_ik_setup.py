"""
Stretch Soft IK Setup
=====================
IK joint chain 에 Soft IK + Stretch 노드 네트워크를 자동 생성/제거.

공개 API:
  setup_stretch_soft_ik(joints, prefix, ctrl_start, ctrl_end, ...)
  remove_stretch_soft_ik(prefix)
  setup_from_selection(...)
  show()            ← 독립 윈도우
  build_tab_ui()    ← rig_tool_hub 탭 통합용

SoftIK 공식:  d' = L - s × (1/e)^((d-L+s)/s)
  L = total bone length (baked)
  s = softik_ctrl_value
  d = ctrlLen
"""

import math
import maya.cmds as cmds


# ═══════════════════════════════════════════════════════════
#  내부 헬퍼  (노드 생성)
# ═══════════════════════════════════════════════════════════

def _add_attr(node, long_name, attr_type='double', keyable=True, **kwargs):
    if not cmds.attributeQuery(long_name, node=node, exists=True):
        if attr_type == 'string':
            cmds.addAttr(node, longName=long_name, dataType='string', keyable=keyable)
        else:
            cmds.addAttr(node, longName=long_name, attributeType=attr_type,
                         keyable=keyable, **kwargs)


def _pma(name, op, static=None, dynamic=None):
    """plusMinusAverage. op: 1=add 2=sub 3=avg"""
    n = cmds.createNode('plusMinusAverage', name=name)
    cmds.setAttr(n + '.operation', op)
    for idx, val in (static or []):
        cmds.setAttr('{}.input1D[{}]'.format(n, idx), val)
    for idx, src in (dynamic or []):
        cmds.connectAttr(src, '{}.input1D[{}]'.format(n, idx))
    return n


def _md(name, op, static=None, dynamic=None):
    """multiplyDivide. op: 1=mul 2=div 3=pow"""
    n = cmds.createNode('multiplyDivide', name=name)
    cmds.setAttr(n + '.operation', op)
    for attr, val in (static or {}).items():
        cmds.setAttr('{}.{}'.format(n, attr), val)
    for attr, src in (dynamic or {}).items():
        cmds.connectAttr(src, '{}.{}'.format(n, attr))
    return n


def _cond(name, op, ft_src, st=None, st_src=None,
          tr_src=None, tr_val=None, fr_src=None, fr_val=None):
    """condition 노드."""
    n = cmds.createNode('condition', name=name)
    cmds.setAttr(n + '.operation', op)
    cmds.connectAttr(ft_src, n + '.firstTerm')
    if st_src:            cmds.connectAttr(st_src, n + '.secondTerm')
    elif st is not None:  cmds.setAttr(n + '.secondTerm', st)
    if tr_src:            cmds.connectAttr(tr_src, n + '.colorIfTrueR')
    elif tr_val is not None: cmds.setAttr(n + '.colorIfTrueR', tr_val)
    if fr_src:            cmds.connectAttr(fr_src, n + '.colorIfFalseR')
    elif fr_val is not None: cmds.setAttr(n + '.colorIfFalseR', fr_val)
    return n


# ═══════════════════════════════════════════════════════════
#  Setup
# ═══════════════════════════════════════════════════════════

def setup_stretch_soft_ik(joints, prefix, ctrl_start, ctrl_end,
                           stretch_axis='+X',
                           ik_ctrl=None,
                           softik_attr=None, stretch_attr=None,
                           parent_node=None, ref_node=None):
    """
    Parameters
    ----------
    joints        : list[str]  root → end (최소 3개)
    prefix        : str
    ctrl_start    : str   ctrlLen 측정 시작 transform
    ctrl_end      : str   ctrlLen 측정 끝 transform
                          ★ IK solver 가 rotate 를 구동하는 joint 와 무관해야 함
    stretch_axis  : str   스트레치를 적용할 translate 축
                          '+X'|'-X'|'+Y'|'-Y'|'+Z'|'-Z'  (기본값 '+X')
    ik_ctrl       : str|None   softIK / stretch attr 를 자동 추가할 컨트롤러
                               지정 시 softIK(0~L), stretch(0~1) attr 생성 후 연결
    softik_attr   : str|None   'ctrl.softIK'  (ik_ctrl 미사용 시 직접 지정)
    stretch_attr  : str|None   'ctrl.stretch' (ik_ctrl 미사용 시 직접 지정)
    parent_node   : str|None   IK_input/output 을 넣을 그룹
    ref_node      : str|None   local space 기준 transform (IK solver 구동 안 함)
                               None → world space 직접 측정 (권장, 사이클 안전)

    Returns
    -------
    dict: ik_input, ik_output, bone_lengths, ratios, total_length, stretch_axis
    """
    if len(joints) < 3:
        cmds.error('[stretch_soft_ik] 최소 3개의 조인트가 필요합니다.')
        return None

    ax_letter = stretch_axis[-1].upper()          # 'X' / 'Y' / 'Z'
    ax_sign   = -1 if stretch_axis.startswith('-') else 1
    tx_attr   = '.translate' + ax_letter

    n_bones = len(joints) - 1

    # 정적 정보 계산 (setup 시 베이크)
    # abs_lens : softIK 공식(L) 및 ratio 계산용 — 항상 양수
    # bone_lens: 노드 static 값용 — 부호 포함 (ax_sign 적용)
    abs_lens = []
    for i in range(n_bones):
        val = cmds.getAttr(joints[i + 1] + tx_attr)
        abs_v = abs(val)
        if abs_v < 1e-4:
            cmds.warning('[stretch_soft_ik] {} {}{} ≈ 0'.format(
                joints[i + 1], 'translate', ax_letter))
        abs_lens.append(abs_v)

    L         = sum(abs_lens)                              # 항상 양수 (softIK 공식용)
    bone_lens = [ax_sign * a for a in abs_lens]            # 부호 적용
    ratios    = [ax_sign * a / L for a in abs_lens]        # 부호 적용

    cmds.undoInfo(openChunk=True, chunkName='Setup Stretch SoftIK: ' + prefix)
    try:
        result = _build(joints, prefix, ctrl_start, ctrl_end,
                        ik_ctrl, softik_attr, stretch_attr, parent_node, ref_node,
                        abs_lens, bone_lens, ratios, L, n_bones, ax_letter)
    except Exception:
        cmds.undoInfo(closeChunk=True)
        raise
    cmds.undoInfo(closeChunk=True)
    result['stretch_axis'] = stretch_axis
    return result


def _build(joints, prefix, ctrl_start, ctrl_end,
           ik_ctrl, softik_attr, stretch_attr, parent_node, ref_node,
           abs_lens, bone_lens, ratios, L, n_bones, ax_letter):

    # IK_input / IK_output wrapper transforms
    ik_in  = cmds.createNode('transform', name=prefix + '_IK_input')
    ik_out = cmds.createNode('transform', name=prefix + '_IK_output')

    _add_attr(ik_in,  'ctrlLen')
    _add_attr(ik_in,  'softik_ctrl_value',  min=0, max=L)
    _add_attr(ik_in,  'stretch_ctrl_value', min=0, max=1)
    _add_attr(ik_out, 'output_softik')
    _add_attr(ik_out, 'stretched_len')
    for i in range(n_bones):
        _add_attr(ik_out, 'bone{}_stretched'.format(i))

    # joint 목록을 IK_input 에 저장 (remove 시 활용)
    _add_attr(ik_in, 'ik_joints', attr_type='string', keyable=False)
    cmds.setAttr(ik_in + '.ik_joints', '|'.join(joints), type='string')

    # ctrl 거리 측정
    # ★ 사이클 방지: ref_node=None 이면 world space 직접 측정으로 사이클 완전 차단.
    dist = cmds.createNode('distanceBetween', name=prefix + '_ctrlLen_DIST')
    if ref_node and cmds.objExists(ref_node):
        ms = cmds.createNode('multMatrix', name=prefix + '_ctrlStart_MTMX')
        cmds.connectAttr(ctrl_start + '.worldMatrix[0]', ms + '.matrixIn[0]')
        cmds.connectAttr(ref_node + '.worldInverseMatrix[0]', ms + '.matrixIn[1]')
        me = cmds.createNode('multMatrix', name=prefix + '_ctrlEnd_MTMX')
        cmds.connectAttr(ctrl_end + '.worldMatrix[0]', me + '.matrixIn[0]')
        cmds.connectAttr(ref_node + '.worldInverseMatrix[0]', me + '.matrixIn[1]')
        cmds.connectAttr(ms + '.matrixSum', dist + '.inMatrix1')
        cmds.connectAttr(me + '.matrixSum', dist + '.inMatrix2')
    else:
        cmds.connectAttr(ctrl_start + '.worldMatrix[0]', dist + '.inMatrix1')
        cmds.connectAttr(ctrl_end   + '.worldMatrix[0]', dist + '.inMatrix2')
    cmds.connectAttr(dist + '.distance', ik_in + '.ctrlLen')

    siv = ik_in + '.softik_ctrl_value'
    sic = ik_in + '.ctrlLen'

    # SoftIK 수식: d' = L - s × (1/e)^((d-L+s)/s)
    len_minus_s    = _pma(prefix + '_len_minus_softikV', 2,
                          static=[(0, L)], dynamic=[(1, siv)])
    ctrl_minus_dif = _pma(prefix + '_ctrlLen_minus_dif', 2,
                          dynamic=[(0, sic), (1, len_minus_s + '.output1D')])
    zdiv           = _cond(prefix + '_zerodivide_COND', 0, siv,
                           st=0.0, tr_val=1.0, fr_src=siv)
    div_node       = _md(prefix + '_divide_softikV', 2,
                         dynamic={'input1X': ctrl_minus_dif + '.output1D',
                                  'input2X': zdiv + '.outColorR'})
    pow_node       = _md(prefix + '_power_val', 3,
                         static={'input1X': 1.0 / math.e},
                         dynamic={'input2X': div_node + '.outputX'})
    mult_node      = _md(prefix + '_mult_softikV', 1,
                         dynamic={'input1X': siv,
                                  'input2X': pow_node + '.outputX'})
    result_node    = _pma(prefix + '_result_softik_len', 2,
                          static=[(0, L)],
                          dynamic=[(1, mult_node + '.outputX')])
    softik_cond    = _cond(prefix + '_softikV_COND', 2, siv,
                           st=0.0,
                           tr_src=result_node + '.output1D', fr_val=L)
    ctrllen_cond   = _cond(prefix + '_ctrllen_COND', 2, sic,
                           st_src=len_minus_s + '.output1D',
                           tr_src=softik_cond + '.outColorR', fr_src=sic)

    softik_result = ctrllen_cond + '.outColorR'
    cmds.connectAttr(softik_result, ik_out + '.output_softik')

    # Stretch 계산
    overshoot = _pma(prefix + '_stretchedLen', 2,
                     dynamic=[(0, sic), (1, softik_result)])
    cmds.connectAttr(overshoot + '.output1D', ik_out + '.stretched_len')

    stv   = ik_in + '.stretch_ctrl_value'
    blend = _md(prefix + '_blend_overshoot', 1,
                dynamic={'input1X': overshoot + '.output1D', 'input2X': stv})

    for i in range(n_bones):
        bi   = 'bone{}'.format(i)
        amt  = _md(prefix + '_{}_stretchAmt'.format(bi), 1,
                   static={'input2X': ratios[i]},
                   dynamic={'input1X': blend + '.outputX'})
        plus = _pma(prefix + '_{}_plus_stretch'.format(bi), 1,
                    static=[(0, bone_lens[i])],
                    dynamic=[(1, amt + '.outputX')])
        cmds.connectAttr(plus + '.output1D',
                         ik_out + '.{}_stretched'.format(bi))

    # IK_output → joint.translate{ax_letter}
    for i in range(n_bones):
        src = ik_out + '.bone{}_stretched'.format(i)
        dst = joints[i + 1] + '.translate' + ax_letter
        if cmds.isConnected(src, dst):
            cmds.disconnectAttr(src, dst)
        cmds.connectAttr(src, dst)

    # 외부 컨트롤러 연결 (optional)
    if ik_ctrl and cmds.objExists(ik_ctrl):
        _add_attr(ik_ctrl, 'softIK',  min=0, max=L,   defaultValue=0)
        _add_attr(ik_ctrl, 'stretch', min=0, max=1.0,  defaultValue=0)
        softik_attr  = ik_ctrl + '.softIK'
        stretch_attr = ik_ctrl + '.stretch'

    if softik_attr:
        cmds.connectAttr(softik_attr, ik_in + '.softik_ctrl_value')
    if stretch_attr:
        cmds.connectAttr(stretch_attr, ik_in + '.stretch_ctrl_value')

    if parent_node and cmds.objExists(parent_node):
        for node in [ik_in, ik_out]:
            cmds.parent(node, parent_node)

    result = {
        'ik_input':     ik_in,
        'ik_output':    ik_out,
        'bone_lengths': abs_lens,
        'ratios':       ratios,
        'total_length': L,
    }
    _log(result, joints)
    return result


# ═══════════════════════════════════════════════════════════
#  Remove
# ═══════════════════════════════════════════════════════════

def remove_stretch_soft_ik(prefix):
    """
    prefix 로 생성된 Stretch Soft IK 노드 네트워크를 전부 제거.
    IK_output 에서 joint.translateX 연결을 끊고 prefix_* 노드를 삭제.
    단일 undo 청크로 처리됩니다.
    """
    ik_out = prefix + '_IK_output'
    ik_in  = prefix + '_IK_input'

    if not cmds.objExists(ik_out) and not cmds.objExists(ik_in):
        cmds.warning('[stretch_soft_ik] "{}" 로 시작하는 IK 노드를 찾지 못했습니다.'.format(prefix))
        return False

    cmds.undoInfo(openChunk=True, chunkName='Remove Stretch SoftIK: ' + prefix)
    try:
        if cmds.objExists(ik_out):
            user_attrs = cmds.listAttr(ik_out, userDefined=True) or []
            for attr in user_attrs:
                if '_stretched' in attr and 'len' not in attr:
                    src   = ik_out + '.' + attr
                    dests = cmds.listConnections(
                        src, plugs=True, source=False, destination=True) or []
                    for dst in dests:
                        if cmds.isConnected(src, dst):
                            cmds.disconnectAttr(src, dst)

        nodes = cmds.ls(prefix + '_*')
        if nodes:
            cmds.delete(nodes)

        print('[stretch_soft_ik] Removed: {}'.format(prefix))
        return True

    except Exception as e:
        cmds.warning('[stretch_soft_ik] Remove 실패: {}'.format(str(e)))
        return False
    finally:
        cmds.undoInfo(closeChunk=True)


# ═══════════════════════════════════════════════════════════
#  Selection helper
# ═══════════════════════════════════════════════════════════

def setup_from_selection(prefix=None, ctrl_start=None, ctrl_end=None,
                          stretch_axis='+X', ik_ctrl=None,
                          parent_node=None, ref_node=None):
    """현재 선택된 조인트로 setup_stretch_soft_ik 실행."""
    sel = cmds.ls(selection=True, type='joint', long=False)
    if not sel:
        sel = cmds.ls(selection=True, long=False)
    if len(sel) < 3:
        cmds.error('[stretch_soft_ik] 최소 3개의 조인트를 선택하세요.')
        return None
    if prefix is None:
        prefix = sel[0].replace(':', '_').split('_')[0]
    return setup_stretch_soft_ik(
        joints=sel, prefix=prefix,
        ctrl_start=ctrl_start if ctrl_start else sel[0],
        ctrl_end=ctrl_end     if ctrl_end   else sel[-1],
        stretch_axis=stretch_axis,
        ik_ctrl=ik_ctrl,
        parent_node=parent_node, ref_node=ref_node,
    )


# ═══════════════════════════════════════════════════════════
#  로그
# ═══════════════════════════════════════════════════════════

def _log(result, joints):
    sep = '=' * 55
    print(sep)
    print('[stretch_soft_ik] Setup Complete')
    print('  Joints       :', ' -> '.join(joints))
    print('  Stretch Axis :', result.get('stretch_axis', '+X'))
    print('  Bone lengths :', [round(v, 4) for v in result['bone_lengths']])
    print('  Ratios       :', [round(v, 4) for v in result['ratios']])
    print('  Total length :', round(result['total_length'], 4))
    print('  IK_input     :', result['ik_input'])
    print('  IK_output    :', result['ik_output'])
    print('  [필수 연결]')
    print('  IK_input.softik_ctrl_value  <- ctrl.softIK  (0 ~ {:.4f})'.format(
        result['total_length']))
    print('  IK_input.stretch_ctrl_value <- ctrl.stretch (0 ~ 1)')
    print(sep)


# ═══════════════════════════════════════════════════════════
#  UI  (Maya native cmds)
# ═══════════════════════════════════════════════════════════

_WIN = 'StretchSoftIkWin'
_ui  = {}   # 위젯 컨트롤 이름 저장

# ─── 도움말 텍스트 ────────────────────────────────────────

_HELP_JOINT_CHAIN = (
    "[ Joint Chain ]\n\n"
    "Stretch + Soft IK 를 적용할 IK 조인트 체인을 로드합니다.\n\n"
    "Load Selected :\n"
    "  · 뷰포트 또는 Outliner 에서 조인트를 순서대로 선택한 뒤 클릭하세요.\n"
    "  · Root → End 순서여야 합니다.\n"
    "  · 최소 3개 (Root + 중간 1개 이상 + End) 가 필요합니다.\n\n"
    "▲ / ▼ :\n"
    "  · 선택한 항목의 순서를 변경합니다.\n\n"
    "✕ Remove :\n"
    "  · 선택한 항목을 목록에서 제거합니다."
)

_HELP_SETUP_SETTINGS = (
    "[ Setup Settings ]\n\n"
    "Prefix :\n"
    "  · 생성되는 모든 노드 이름 앞에 붙는 식별자입니다.\n"
    "  · 예)  arm_L  →  arm_L_IK_input, arm_L_IK_output ...\n"
    "  · 조인트 로드 시 첫 번째 조인트 이름으로 자동 제안됩니다.\n\n"
    "Stretch Axis :\n"
    "  · 체인에서 bone 길이 방향의 translate 축을 선택합니다.\n"
    "  · 일반적으로 조인트의 aim 축과 일치합니다.\n"
    "  · +X / -X / +Y / -Y / +Z / -Z 중 선택.\n"
    "  · -축 선택 시 스트레치 출력이 음수 방향으로 연결됩니다.\n"
    "  · 예) translateX = -10 인 체인 → Stretch Axis: -X\n\n"
    "Ctrl Start / Ctrl End :\n"
    "  · IK 길이(ctrlLen) 측정에 사용할 두 transform 입니다.\n"
    "  · IK Handle 의 루트 ~ 엔드 방향으로 지정하세요.\n\n"
    "  ★ 사이클 주의 :\n"
    "     IK solver 가 직접 rotate 를 구동하는 조인트의\n"
    "     worldMatrix / worldInverseMatrix 를 사용하면\n"
    "     IK → rotate → worldMatrix → ctrlLen → stretch\n"
    "     → translateX → IK 의 평가 사이클이 발생합니다.\n"
    "     Ctrl Start / End 에는 IK solver 가 구동하지 않는\n"
    "     별도의 transform (ctrl, locator 등) 을 지정하세요."
)

_HELP_OPTIONAL = (
    "[ Optional Connections ]\n\n"
    "IK Controller :\n"
    "  · 지정하면 해당 컨트롤러에 두 어트리뷰트를 자동 생성·연결합니다.\n"
    "      softIK  : 0 ~ Total Length  (soft zone 크기)\n"
    "      stretch : 0 ~ 1             (스트레치 강도)\n"
    "  · 미지정 시 IK_input 노드에서 직접 연결해야 합니다.\n\n"
    "Parent Node :\n"
    "  · IK_input / IK_output transform 을 지정한 그룹 아래로 parent 합니다.\n"
    "  · rig 계층 정리용으로 사용하세요.\n\n"
    "Ref Node :\n"
    "  · local space 기반으로 ctrlLen 을 측정할 기준 transform 입니다.\n"
    "  · 지정 시 multMatrix 로 local 공간 거리를 계산합니다.\n"
    "  · 미지정 (권장) 시 world space 직접 측정 — 사이클 완전 차단."
)

_HELP_RUN = (
    "[ Run Setup ]\n\n"
    "Soft IK + Stretch 노드 네트워크를 생성합니다.\n\n"
    "생성 노드 :\n"
    "  prefix_IK_input   : ctrlLen / softik_ctrl_value / stretch_ctrl_value\n"
    "  prefix_IK_output  : output_softik / stretched_len / boneN_stretched\n"
    "  prefix_ctrlLen_DIST          : 거리 측정 (distanceBetween)\n"
    "  Soft IK 연산 노드 (고정 7개) : PMA / MD / COND\n"
    "  Stretch 연산 노드 (2 × N개)  : 본마다 stretchAmt + plus_stretch\n\n"
    "Soft IK 공식 :\n"
    "  d' = L - s × (1/e)^((d - L + s) / s)\n"
    "  L = total bone length  (setup 시 translateX 합산으로 베이크)\n"
    "  s = softIK ctrl value  (0 이면 soft 없음 = 일반 IK)\n"
    "  d = ctrlLen            (현재 ctrl 거리)\n\n"
    "전체 setup 은 단일 Undo 청크로 처리됩니다."
)

_HELP_REMOVE = (
    "[ Remove Rig ]\n\n"
    "prefix 로 생성된 Stretch Soft IK 노드 네트워크를 전부 제거합니다.\n\n"
    "동작 순서 :\n"
    "  1. IK_output.boneN_stretched → joint.translateX 연결 해제\n"
    "  2. prefix_* 노드 전체 삭제\n\n"
    "Prefix 입력 :\n"
    "  · 직접 입력하거나 '현재 복사' 로 Setup prefix 를 가져오세요.\n"
    "  · Run Setup 완료 시 자동으로 채워집니다.\n\n"
    "전체 Remove 는 단일 Undo 청크로 처리됩니다."
)


def _show_help(title, msg):
    cmds.confirmDialog(
        title='Help  —  ' + title,
        message=msg,
        button=['확인'],
        defaultButton='확인',
    )


def _pick(field_ctrl, use_grp=True):
    """현재 선택한 첫 번째 오브젝트를 textFieldButtonGrp / textFieldGrp 에 입력."""
    sel = cmds.ls(selection=True, long=False)
    if not sel:
        return
    if use_grp:
        cmds.textFieldButtonGrp(field_ctrl, edit=True, text=sel[0])
    else:
        cmds.textFieldGrp(field_ctrl, edit=True, text=sel[0])


def _load_joints():
    sel = cmds.ls(selection=True, long=False)
    if not sel:
        cmds.warning('[stretch_soft_ik] 선택된 오브젝트가 없습니다.')
        return
    cmds.textScrollList(_ui['jnt_list'], edit=True, removeAll=True)
    for j in sel:
        cmds.textScrollList(_ui['jnt_list'], edit=True, append=j)
    # prefix 자동 제안
    cur = cmds.textFieldGrp(_ui['prefix'], q=True, text=True).strip()
    if not cur:
        raw = sel[0].replace(':', '_')
        cmds.textFieldGrp(_ui['prefix'], edit=True, text=raw.split('_')[0])
    print('[stretch_soft_ik] {} 개 조인트 로드됨'.format(len(sel)))


def _move_item(direction):
    sel = cmds.textScrollList(_ui['jnt_list'], q=True, selectItem=True)
    if not sel:
        return
    items = cmds.textScrollList(_ui['jnt_list'], q=True, allItems=True) or []
    idx     = items.index(sel[0])
    new_idx = idx + direction
    if new_idx < 0 or new_idx >= len(items):
        return
    items.insert(new_idx, items.pop(idx))
    cmds.textScrollList(_ui['jnt_list'], edit=True, removeAll=True)
    for item in items:
        cmds.textScrollList(_ui['jnt_list'], edit=True, append=item)
    cmds.textScrollList(_ui['jnt_list'], edit=True, selectItem=items[new_idx])


def _remove_items():
    sel = cmds.textScrollList(_ui['jnt_list'], q=True, selectItem=True) or []
    for item in sel:
        cmds.textScrollList(_ui['jnt_list'], edit=True, removeItem=item)


def _on_run():
    joints       = cmds.textScrollList(_ui['jnt_list'], q=True, allItems=True) or []
    prefix       = cmds.textFieldGrp(_ui['prefix'],      q=True, text=True).strip()
    stretch_axis = cmds.optionMenu(_ui['stretch_axis'],  q=True, value=True)
    ctrl_start   = cmds.textFieldButtonGrp(_ui['ctrl_start'], q=True, text=True).strip()
    ctrl_end     = cmds.textFieldButtonGrp(_ui['ctrl_end'],   q=True, text=True).strip()
    ik_ctrl      = cmds.textFieldButtonGrp(_ui['ik_ctrl'],    q=True, text=True).strip() or None
    parent_node  = cmds.textFieldButtonGrp(_ui['parent'],     q=True, text=True).strip() or None
    ref_node     = cmds.textFieldButtonGrp(_ui['ref'],        q=True, text=True).strip() or None

    # 유효성 검사
    if len(joints) < 3:
        cmds.warning('[stretch_soft_ik] 조인트를 3개 이상 로드하세요.'); return
    if not prefix:
        cmds.warning('[stretch_soft_ik] Prefix 를 입력하세요.'); return
    if not ctrl_start or not cmds.objExists(ctrl_start):
        cmds.warning('[stretch_soft_ik] Ctrl Start "{}" 를 찾을 수 없습니다.'.format(ctrl_start)); return
    if not ctrl_end or not cmds.objExists(ctrl_end):
        cmds.warning('[stretch_soft_ik] Ctrl End "{}" 를 찾을 수 없습니다.'.format(ctrl_end)); return
    if ik_ctrl and not cmds.objExists(ik_ctrl):
        cmds.warning('[stretch_soft_ik] IK Controller "{}" 를 찾을 수 없습니다.'.format(ik_ctrl)); return

    try:
        result = setup_stretch_soft_ik(
            joints=joints, prefix=prefix,
            ctrl_start=ctrl_start, ctrl_end=ctrl_end,
            stretch_axis=stretch_axis,
            ik_ctrl=ik_ctrl, parent_node=parent_node, ref_node=ref_node,
        )
        # Remove 섹션 prefix 자동 입력
        cmds.textFieldButtonGrp(_ui['remove_prefix'], edit=True, text=prefix)
        cmds.inViewMessage(
            assistMessage=(
                '<hl>Setup 완료</hl>  {p}  |  Bones: {b}  |  Total: {l:.4f}'
            ).format(p=prefix, b=len(result['bone_lengths']), l=result['total_length']),
            pos='midCenter', fade=True, fadeOutTime=3.0,
        )
    except Exception as e:
        cmds.warning('[stretch_soft_ik] Error: {}'.format(str(e)))
        import traceback; traceback.print_exc()


def _on_remove():
    prefix = cmds.textFieldButtonGrp(_ui['remove_prefix'], q=True, text=True).strip()
    if not prefix:
        cmds.warning('[stretch_soft_ik] 제거할 Prefix 를 입력하세요.'); return

    nodes = cmds.ls(prefix + '_*')
    if not nodes:
        cmds.warning('[stretch_soft_ik] "{}_*" 노드를 찾을 수 없습니다.'.format(prefix)); return

    confirm = cmds.confirmDialog(
        title='Remove Rig',
        message='"{}_*" 노드를 모두 삭제하고\njoint 연결을 해제합니다.\n\n계속하시겠습니까?'.format(prefix),
        button=['제거', '취소'],
        defaultButton='취소',
        cancelButton='취소',
        dismissString='취소',
    )
    if confirm != '제거':
        return

    try:
        ok = remove_stretch_soft_ik(prefix)
        if ok:
            cmds.inViewMessage(
                assistMessage='<hl>Removed</hl>  {}'.format(prefix),
                pos='midCenter', fade=True, fadeOutTime=2.0,
            )
    except Exception as e:
        cmds.warning('[stretch_soft_ik] Remove Error: {}'.format(str(e)))
        import traceback; traceback.print_exc()


def _fill_remove_prefix():
    """Setup prefix 를 Remove prefix 필드에 복사."""
    prefix = cmds.textFieldGrp(_ui['prefix'], q=True, text=True).strip()
    cmds.textFieldButtonGrp(_ui['remove_prefix'], edit=True, text=prefix)


# ─── UI 빌드 ─────────────────────────────────────────────

def build_tab_ui(parent=None):
    """탭 또는 독립 윈도우에 UI 를 빌드. rig_tool_hub 통합용."""
    global _ui
    _ui = {}

    scroll = (cmds.scrollLayout(childResizable=True, parent=parent)
              if parent else cmds.scrollLayout(childResizable=True))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4, columnOffset=['both', 8])

    # ── Joint Chain ──────────────────────────────────────────
    cmds.separator(h=6, style='none')
    cmds.frameLayout(
        label='  Joint Chain',
        collapsable=False, marginWidth=6, marginHeight=6,
    )
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)

    cmds.text(
        label='  Root → End 순서로 로드.  최소 3개 필요.  ▲▼ 버튼으로 순서 변경.',
        align='left', font='smallPlainLabelFont',
    )

    _ui['jnt_list'] = cmds.textScrollList(
        numberOfRows=5, allowMultiSelection=True,
    )

    cmds.rowLayout(numberOfColumns=5, columnWidth5=(130, 60, 60, 60, 26), adjustableColumn=1)
    cmds.button(
        label='Load Selected', height=24,
        backgroundColor=(0.28, 0.38, 0.50),
        annotation='현재 선택한 오브젝트를 순서대로 로드',
        command=lambda *_: _load_joints(),
    )
    cmds.button(label='▲  Up',     height=24, command=lambda *_: _move_item(-1))
    cmds.button(label='▼  Down',   height=24, command=lambda *_: _move_item(1))
    cmds.button(label='✕  Remove', height=24, command=lambda *_: _remove_items())
    cmds.button(
        label='?', width=26, height=24,
        backgroundColor=(0.25, 0.25, 0.35),
        command=lambda *_: _show_help('Joint Chain', _HELP_JOINT_CHAIN),
    )
    cmds.setParent('..')   # rowLayout
    cmds.setParent('..')   # columnLayout
    cmds.setParent('..')   # frameLayout

    # ── Setup Settings ───────────────────────────────────────
    cmds.frameLayout(
        label='  Setup Settings',
        collapsable=False, marginWidth=6, marginHeight=6,
    )
    cmds.columnLayout(adjustableColumn=True, rowSpacing=5)

    _ui['prefix'] = cmds.textFieldGrp(
        label='Prefix :',
        columnWidth2=(72, 220), adjustableColumn=2,
    )

    cmds.separator(h=4)

    cmds.rowLayout(numberOfColumns=4,
                   columnWidth4=(72, 80, 60, 130),
                   columnAlign4=['right', 'left', 'right', 'left'],
                   adjustableColumn=4)
    cmds.text(label='Stretch Axis :')
    _ui['stretch_axis'] = cmds.optionMenu(annotation='스트레치를 적용할 translate 축 (-축 포함)')
    for ax in ['+X', '-X', '+Y', '-Y', '+Z', '-Z']:
        cmds.menuItem(label=ax)
    cmds.text(label='  Bone Axis :')
    cmds.text(
        label='체인 방향 translate 축',
        font='smallPlainLabelFont',
    )
    cmds.setParent('..')   # rowLayout

    cmds.separator(h=4)

    _ui['ctrl_start'] = cmds.textFieldButtonGrp(
        label='Ctrl Start :', buttonLabel='Pick',
        columnWidth3=(72, 196, 46), adjustableColumn=2,
        annotation='IK 시작 transform — IK solver 가 직접 구동하지 않는 노드',
        buttonCommand=lambda *_: _pick(_ui['ctrl_start']),
    )
    _ui['ctrl_end'] = cmds.textFieldButtonGrp(
        label='Ctrl End :', buttonLabel='Pick',
        columnWidth3=(72, 196, 46), adjustableColumn=2,
        annotation='IK 끝 transform — IK solver 가 직접 구동하지 않는 노드',
        buttonCommand=lambda *_: _pick(_ui['ctrl_end']),
    )
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(314, 26), adjustableColumn=1)
    cmds.text(
        label='  ※ Ctrl Start / End 는 IK solver 가 직접 구동하지 않는 transform 을 지정하세요.',
        align='left', font='smallPlainLabelFont',
    )
    cmds.button(
        label='?', width=26,
        backgroundColor=(0.25, 0.25, 0.35),
        command=lambda *_: _show_help('Setup Settings', _HELP_SETUP_SETTINGS),
    )
    cmds.setParent('..')   # rowLayout

    cmds.setParent('..')   # columnLayout
    cmds.setParent('..')   # frameLayout

    # ── Optional Connections ─────────────────────────────────
    cmds.frameLayout(
        label='  Optional Connections',
        collapsable=True, collapse=True,
        marginWidth=6, marginHeight=6,
    )
    cmds.columnLayout(adjustableColumn=True, rowSpacing=5)

    _ui['ik_ctrl'] = cmds.textFieldButtonGrp(
        label='IK Controller :', buttonLabel='Pick',
        columnWidth3=(88, 178, 46), adjustableColumn=2,
        annotation='softIK / stretch attr 를 자동 추가·연결할 컨트롤러',
        buttonCommand=lambda *_: _pick(_ui['ik_ctrl']),
    )
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(314, 26), adjustableColumn=1)
    cmds.text(
        label='  softIK(0~L) / stretch(0~1) attr 를 선택 컨트롤러에 자동 생성·연결합니다.',
        align='left', font='smallPlainLabelFont',
    )
    cmds.button(
        label='?', width=26,
        backgroundColor=(0.25, 0.25, 0.35),
        command=lambda *_: _show_help('Optional Connections', _HELP_OPTIONAL),
    )
    cmds.setParent('..')   # rowLayout
    cmds.separator(h=4)

    _ui['parent'] = cmds.textFieldButtonGrp(
        label='Parent Node :', buttonLabel='Pick',
        columnWidth3=(88, 178, 46), adjustableColumn=2,
        annotation='IK_input / IK_output 을 넣을 그룹',
        buttonCommand=lambda *_: _pick(_ui['parent']),
    )
    _ui['ref'] = cmds.textFieldButtonGrp(
        label='Ref Node :', buttonLabel='Pick',
        columnWidth3=(88, 178, 46), adjustableColumn=2,
        annotation='local space 기준 transform — IK solver 가 구동하지 않는 노드',
        buttonCommand=lambda *_: _pick(_ui['ref']),
    )

    cmds.setParent('..')   # columnLayout
    cmds.setParent('..')   # frameLayout

    # ── Run Setup ────────────────────────────────────────────
    cmds.separator(h=6)
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(314, 26), adjustableColumn=1)
    cmds.button(
        label='▶   Run Setup',
        height=34,
        backgroundColor=(0.22, 0.50, 0.30),
        annotation='Stretch + Soft IK 노드 네트워크 생성',
        command=lambda *_: _on_run(),
    )
    cmds.button(
        label='?', width=26, height=34,
        backgroundColor=(0.25, 0.25, 0.35),
        command=lambda *_: _show_help('Run Setup', _HELP_RUN),
    )
    cmds.setParent('..')   # rowLayout

    # ── Remove Rig ───────────────────────────────────────────
    cmds.frameLayout(
        label='  Remove Rig',
        collapsable=False, marginWidth=6, marginHeight=6,
    )
    cmds.columnLayout(adjustableColumn=True, rowSpacing=5)

    cmds.text(
        label='  prefix_* 노드를 전부 삭제하고 joint.translateX 연결을 해제합니다.',
        align='left', font='smallPlainLabelFont',
    )
    _ui['remove_prefix'] = cmds.textFieldButtonGrp(
        label='Prefix :', buttonLabel='현재 복사',
        columnWidth3=(60, 196, 60), adjustableColumn=2,
        annotation='제거할 prefix 입력, 또는 "현재 복사" 로 Setup prefix 를 가져옵니다',
        buttonCommand=lambda *_: _fill_remove_prefix(),
    )
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(314, 26), adjustableColumn=1)
    cmds.button(
        label='✕   Remove Rig',
        height=30,
        backgroundColor=(0.52, 0.22, 0.22),
        annotation='확인 대화상자 후 제거 실행',
        command=lambda *_: _on_remove(),
    )
    cmds.button(
        label='?', width=26, height=30,
        backgroundColor=(0.25, 0.25, 0.35),
        command=lambda *_: _show_help('Remove Rig', _HELP_REMOVE),
    )
    cmds.setParent('..')   # rowLayout

    cmds.setParent('..')   # columnLayout
    cmds.setParent('..')   # frameLayout

    cmds.separator(h=8, style='none')
    cmds.setParent('..')   # columnLayout (root)
    return scroll


def show():
    """Stretch Soft IK Setup 독립 윈도우 실행."""
    if cmds.window(_WIN, exists=True):
        cmds.deleteUI(_WIN)

    win = cmds.window(
        _WIN,
        title='Stretch Soft IK Setup',
        widthHeight=(370, 600),
        sizeable=True,
    )
    build_tab_ui(win)
    cmds.showWindow(win)
