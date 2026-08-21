# -*- coding: utf-8 -*-
"""============================================================================
촉수(Tentacle) Ribbon Auto-Rig UI

tentacle_ribbon_rig의 6단계 빌드 함수(build_base ~ build_branch)를 감싸는 UI.
tentacle_rig_proto.ma(실제 프로덕션 리그)를 분석해서 만든 단계별 파이프라인을
하나씩 실행하고 씬에서 검토한 뒤 다음 단계로 넘어가는 방식으로 쓴다.

    1단계: Base   -- mesh 중심선 -> 리본 서피스 -> curve 재추출
    2단계: IK     -- IK 컨트롤 -> NurbsBind joint -> 리본 스킨 (+ Stretch)
    3단계: Output -- curve -> closestPointOnSurface -> follicle(플립 없음)
    4단계: FK     -- follicle 기반 FK 체인 -> 최종 Skin joint
    5단계: Twist/Volume -- Twist 구간(Parameter로 조절) + Volume 그라디언트
    6단계: Branch(TOP) -- 메인 리본 복제 위의 마스터 FK/IK 레이어로 메인의
           IK 컨트롤을 follicle로 구동

Usage:
    from python2.rigging import tentacle_ribbon_rig_ui
    import importlib
    importlib.reload(tentacle_ribbon_rig_ui)
    tentacle_ribbon_rig_ui.show()
============================================================================"""
import importlib
import sys
import traceback

import maya.cmds as cmds

from python2.rigging import tentacle_ribbon_rig as rig

_WIN_ID = 'tentacleRibbonRigWin'


def _reload_rig():
    """importlib.reload(rig)가 'module ... not in sys.modules'로 실패하는
    경우(python3가 여러 namespace package 조각으로 섞여 있을 때 rig의
    __name__이 sys.modules의 등록 키와 어긋나면서 생김)에 대비한다.
    실패하면 sys.modules에서 지우고 새로 import해서 rig 참조를 다시 맞춘다.
    """
    global rig
    try:
        importlib.reload(rig)
    except ImportError:
        sys.modules.pop('python2.rigging.tentacle_ribbon_rig', None)
        rig = importlib.import_module('python2.rigging.tentacle_ribbon_rig')


def _get_selected_mesh():
    sel = cmds.ls(sl=True, type='transform')
    if not sel:
        cmds.warning('tentacle_ribbon_rig_ui: 먼저 오브젝트를 선택하세요.')
        return None
    return sel[0]


def _get_selected_curve():
    sel = cmds.ls(sl=True, type='transform')
    sel = [s for s in sel if cmds.listRelatives(s, shapes=True, type='nurbsCurve')]
    if not sel:
        cmds.warning('tentacle_ribbon_rig_ui: 먼저 nurbsCurve를 선택하세요.')
        return None
    return sel[0]


class TentacleRibbonRigUI(object):
    def __init__(self):
        self.window_name = _WIN_ID
        self._mesh_field = None
        self._curve_field = None
        self._name_field = None
        self._axis_menu = None
        self._up_axis_menu = None
        self._front_axis_menu = None
        self._up_local_axis_menu = None
        self._num_cv_field = None
        self._ribbon_width_field = None
        self._num_ik_field = None
        self._ik_radius_field = None
        self._num_output_field = None
        self._fk_radius_field = None
        self._num_volume_field = None
        self._ts_radius_field = None
        self._branch_name_field = None
        self._num_ctrl_field = None
        self._branch_fk_radius_field = None
        self._branch_ik_radius_field = None
        self._status_field = None

    def create_ui(self):
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)
        win = cmds.window(self.window_name, title='Tentacle Ribbon Auto-Rig',
                           widthHeight=(400, 780), sizeable=True)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnAttach=('both', 8), parent=win)
        self.build_tab_ui()
        cmds.showWindow(win)
        return win

    def build_tab_ui(self, parent=None):
        """단독 창 대신 다른 툴 허브의 탭으로도 얹을 수 있게 분리된 UI 빌드 진입점."""
        if parent is not None:
            cmds.scrollLayout(childResizable=True, parent=parent)

        cmds.text(label='촉수 Ribbon Auto-Rig', font='boldLabelFont', height=24)
        cmds.text(label='(NURBS 리본 + follicle 기반, 플립 없음)',
                  align='left', font='smallPlainLabelFont')
        cmds.separator(height=8, style='in')

        cmds.frameLayout(label='공용 -- 오브젝트/리그 이름', collapsable=True, collapse=False,
                          marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=4)

        cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                        columnAttach=[(1, 'both', 0), (2, 'both', 0)])
        self._mesh_field = cmds.textField(text='pSphere1', placeholderText='촉수 형상 mesh (1단계용)')
        cmds.button(label='<< 선택', width=70, c=lambda *_: self._grab_selected())
        cmds.setParent('..')

        cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                        columnAttach=[(1, 'both', 0), (2, 'both', 0)])
        self._curve_field = cmds.textField(placeholderText='(선택) 직접 그린 center curve -- 채우면 mesh 무시')
        cmds.button(label='<< 선택', width=70, c=lambda *_: self._grab_selected_curve())
        cmds.setParent('..')
        cmds.text(label='-> curve를 채우면 mesh 기반 중심선 추출 없이 그 curve를 그대로 씁니다.',
                  align='left', font='smallPlainLabelFont')

        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='리그 이름', align='left')
        self._name_field = cmds.textField(text='tentacle')
        cmds.setParent('..')

        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='축(axis)', align='left')
        self._axis_menu = cmds.optionMenu()
        cmds.menuItem(label='y')
        cmds.menuItem(label='x')
        cmds.menuItem(label='z')
        cmds.menuItem(label='Auto (가장 긴 축)')
        cmds.setParent('..')

        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='폭 방향(up_axis)', align='left')
        self._up_axis_menu = cmds.optionMenu()
        cmds.menuItem(label='Auto (axis 기준)')
        cmds.menuItem(label='x')
        cmds.menuItem(label='y')
        cmds.menuItem(label='z')
        cmds.setParent('..')

        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='컨트롤 forward축', align='left')
        self._front_axis_menu = cmds.optionMenu()
        cmds.menuItem(label='x')
        cmds.menuItem(label='y')
        cmds.menuItem(label='z')
        cmds.setParent('..')

        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='컨트롤 폭(width)축', align='left')
        self._up_local_axis_menu = cmds.optionMenu()
        cmds.menuItem(label='y')
        cmds.menuItem(label='x')
        cmds.menuItem(label='z')
        cmds.setParent('..')
        cmds.text(label='-> up_axis(세계축)는 리본의 폭 방향 참조 벡터입니다(surface normal\n'
                        '   아님). forward/폭축은 IK 등 컨트롤 로컬 축 중 tangent/폭 방향에\n'
                        '   맞출 축이고, 지정 안 한 나머지 로컬 축이 surface normal에 가장\n'
                        '   가까운 방향이 됩니다.',
                  align='left', font='smallPlainLabelFont')

        cmds.setParent('..')  # columnLayout
        cmds.setParent('..')  # frameLayout

        cmds.frameLayout(label='1단계 -- Base (중심선 -> 리본 서피스)', collapsable=True,
                          collapse=False, marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='Curve CV 개수', align='left')
        self._num_cv_field = cmds.intField(value=15, minValue=4, maxValue=100)
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='리본 폭', align='left')
        self._ribbon_width_field = cmds.floatField(value=1.5, minValue=0.01)
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.separator(height=4, style='in')
        cmds.button(label='1. Base 생성', height=30, backgroundColor=[0.25, 0.45, 0.3],
                    c=lambda *_: self._on_build_base())
        cmds.setParent('..')

        cmds.frameLayout(label='2단계 -- IK (컨트롤 -> NurbsBind -> 리본 스킨)', collapsable=True,
                          collapse=False, marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='IK 컨트롤 개수', align='left')
        self._num_ik_field = cmds.intField(value=9, minValue=2, maxValue=50)
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='IK 컨트롤 반경', align='left')
        self._ik_radius_field = cmds.floatField(value=1.0, minValue=0.01)
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.text(label='-> 마지막 IK 컨트롤에 Stretch(0~10) attribute가 추가됩니다.',
                  align='left', font='smallPlainLabelFont')
        cmds.separator(height=4, style='in')
        cmds.button(label='2. IK 생성', height=30, backgroundColor=[0.25, 0.4, 0.45],
                    c=lambda *_: self._on_build_ik())
        cmds.setParent('..')

        cmds.frameLayout(label='3단계 -- Output (follicle, 플립 없음)', collapsable=True,
                          collapse=False, marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='Follicle 개수', align='left')
        self._num_output_field = cmds.intField(value=25, minValue=2, maxValue=100)
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.separator(height=4, style='in')
        cmds.button(label='3. Output 생성', height=30, backgroundColor=[0.3, 0.35, 0.5],
                    c=lambda *_: self._on_build_output())
        cmds.setParent('..')

        cmds.frameLayout(label='4단계 -- FK / 최종 Skin joint', collapsable=True,
                          collapse=False, marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='FK 컨트롤 반경', align='left')
        self._fk_radius_field = cmds.floatField(value=0.8, minValue=0.01)
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.separator(height=4, style='in')
        cmds.button(label='4. FK/Skin 생성', height=30, backgroundColor=[0.4, 0.3, 0.5],
                    c=lambda *_: self._on_build_fk())
        cmds.setParent('..')

        cmds.frameLayout(label='5단계 -- Twist / Volume', collapsable=True,
                          collapse=False, marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='Volume 컨트롤 개수', align='left')
        self._num_volume_field = cmds.intField(value=5, minValue=2, maxValue=20)
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='컨트롤 반경', align='left')
        self._ts_radius_field = cmds.floatField(value=0.8, minValue=0.01)
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.text(label='-> Twist Start/End는 Parameter(0~1)로 구간을 조절합니다.',
                  align='left', font='smallPlainLabelFont')
        cmds.separator(height=4, style='in')
        cmds.button(label='5. Twist/Volume 생성', height=30, backgroundColor=[0.5, 0.35, 0.3],
                    c=lambda *_: self._on_build_twist_scale())
        cmds.setParent('..')

        cmds.frameLayout(label='6단계 -- Branch(TOP, 마스터 컨트롤) [선택]', collapsable=True,
                          collapse=True, marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='Branch(TOP) 이름', align='left')
        self._branch_name_field = cmds.textField(text='topTentacle')
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='TOP FK/IK 개수', align='left')
        self._num_ctrl_field = cmds.intField(value=4, minValue=2, maxValue=30)
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='TOP FK 반경', align='left')
        self._branch_fk_radius_field = cmds.floatField(value=0.9, minValue=0.01)
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='TOP IK 반경', align='left')
        self._branch_ik_radius_field = cmds.floatField(value=0.6, minValue=0.01)
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.text(label='-> 메인 리본을 복제해서 TOP을 만들고, TOP의 FK/IK가 그\n'
                        '   서피스를 변형시키면 follicle로 메인의 IK 컨트롤을 구동합니다.',
                  align='left', font='smallPlainLabelFont')
        cmds.separator(height=4, style='in')
        cmds.button(label='6. Branch(TOP) 생성', height=30, backgroundColor=[0.35, 0.35, 0.35],
                    c=lambda *_: self._on_build_branch())
        cmds.setParent('..')

        cmds.separator(height=6, style='in')
        cmds.button(label='전체 빌드 (1~5단계)', height=26,
                    c=lambda *_: self._on_build_all())

        cmds.separator(height=8, style='in')
        self._status_field = cmds.scrollField(editable=False, wordWrap=True, height=130,
                                               font='smallPlainLabelFont', text='')

    def _grab_selected(self):
        mesh = _get_selected_mesh()
        if mesh:
            cmds.textField(self._mesh_field, e=True, text=mesh)

    def _grab_selected_curve(self):
        curve = _get_selected_curve()
        if curve:
            cmds.textField(self._curve_field, e=True, text=curve)

    def _get_name(self):
        name = cmds.textField(self._name_field, q=True, text=True).strip()
        if not name:
            self._set_status('리그 이름을 입력하세요.')
            return None
        return name

    def _get_axis(self):
        axis_label = cmds.optionMenu(self._axis_menu, q=True, value=True)
        return None if axis_label.startswith('Auto') else axis_label

    def _get_up_axis(self):
        up_axis_label = cmds.optionMenu(self._up_axis_menu, q=True, value=True)
        return None if up_axis_label.startswith('Auto') else up_axis_label

    def _get_front_axis(self):
        return cmds.optionMenu(self._front_axis_menu, q=True, value=True)

    def _get_up_local_axis(self):
        return cmds.optionMenu(self._up_local_axis_menu, q=True, value=True)

    def _run(self, label, func):
        try:
            _reload_rig()
            result = func()
        except Exception as exc:
            cmds.warning('tentacle_ribbon_rig_ui: {} 실패 -- {}'.format(label, exc))
            print(traceback.format_exc())
            self._set_status('{} 실패: {}\n(자세한 내용은 Script Editor 확인)'.format(label, exc))
            return None
        self._set_status('{} 완료.\n{}'.format(label, result))
        return result

    def _get_mesh_or_curve(self):
        """curve 필드가 채워져 있으면 그걸 우선 쓰고(mesh 무시), 아니면 mesh
        필드를 쓴다. (mesh, curve, viewfit_target) 튜플을 돌려준다. 둘 다
        없거나 존재하지 않으면 상태창에 에러를 띄우고 None을 돌려준다.
        """
        curve = cmds.textField(self._curve_field, q=True, text=True).strip()
        if curve:
            if not cmds.objExists(curve):
                self._set_status('curve "{}"를 찾을 수 없습니다.'.format(curve))
                return None
            return None, curve, curve

        mesh = cmds.textField(self._mesh_field, q=True, text=True).strip()
        if not mesh or not cmds.objExists(mesh):
            self._set_status('오브젝트 "{}"를 찾을 수 없습니다.'.format(mesh))
            return None
        return mesh, None, mesh

    def _on_build_base(self):
        name = self._get_name()
        if name is None:
            return
        mesh_curve = self._get_mesh_or_curve()
        if mesh_curve is None:
            return
        mesh, curve, viewfit_target = mesh_curve
        axis = self._get_axis()
        up_axis = self._get_up_axis()
        front_axis = self._get_front_axis()
        up_local_axis = self._get_up_local_axis()
        num_cv = cmds.intField(self._num_cv_field, q=True, value=True)
        ribbon_width = cmds.floatField(self._ribbon_width_field, q=True, value=True)

        result = self._run('1단계(Base)', lambda: rig.build_base(
            mesh=mesh, curve=curve, name=name, axis=axis, up_axis=up_axis,
            front_axis=front_axis, up_local_axis=up_local_axis,
            num_cv=num_cv, ribbon_width=ribbon_width))
        if result:
            cmds.select(result['surface'])
            cmds.viewFit(result['surface'], viewfit_target)

    def _on_build_ik(self):
        name = self._get_name()
        if name is None:
            return
        num_ik = cmds.intField(self._num_ik_field, q=True, value=True)
        ctrl_radius = cmds.floatField(self._ik_radius_field, q=True, value=True)
        up_axis = self._get_up_axis()
        front_axis = self._get_front_axis()
        up_local_axis = self._get_up_local_axis()
        self._run('2단계(IK)', lambda: rig.build_ik(
            name=name, num_ik=num_ik, ctrl_radius=ctrl_radius,
            up_axis=up_axis, front_axis=front_axis, up_local_axis=up_local_axis))

    def _on_build_output(self):
        name = self._get_name()
        if name is None:
            return
        num_output = cmds.intField(self._num_output_field, q=True, value=True)
        self._run('3단계(Output)', lambda: rig.build_output(name=name, num_output=num_output))

    def _on_build_fk(self):
        name = self._get_name()
        if name is None:
            return
        ctrl_radius = cmds.floatField(self._fk_radius_field, q=True, value=True)
        self._run('4단계(FK/Skin)', lambda: rig.build_fk(name=name, ctrl_radius=ctrl_radius))

    def _on_build_twist_scale(self):
        name = self._get_name()
        if name is None:
            return
        num_volume = cmds.intField(self._num_volume_field, q=True, value=True)
        ctrl_radius = cmds.floatField(self._ts_radius_field, q=True, value=True)
        up_axis = self._get_up_axis()
        front_axis = self._get_front_axis()
        up_local_axis = self._get_up_local_axis()
        self._run('5단계(Twist/Volume)', lambda: rig.build_twist_scale(
            name=name, num_volume=num_volume, ctrl_radius=ctrl_radius,
            up_axis=up_axis, front_axis=front_axis, up_local_axis=up_local_axis))

    def _on_build_branch(self):
        name = self._get_name()
        if name is None:
            return
        branch_name = cmds.textField(self._branch_name_field, q=True, text=True).strip()
        if not branch_name:
            self._set_status('Branch(TOP) 이름을 입력하세요.')
            return
        num_ctrl = cmds.intField(self._num_ctrl_field, q=True, value=True)
        fk_radius = cmds.floatField(self._branch_fk_radius_field, q=True, value=True)
        ik_radius = cmds.floatField(self._branch_ik_radius_field, q=True, value=True)
        up_axis = self._get_up_axis()
        front_axis = self._get_front_axis()
        up_local_axis = self._get_up_local_axis()
        self._run('6단계(Branch/TOP)', lambda: rig.build_branch(
            name=name, branch_name=branch_name, num_ctrl=num_ctrl,
            fk_radius=fk_radius, ik_radius=ik_radius,
            up_axis=up_axis, front_axis=front_axis, up_local_axis=up_local_axis))

    def _on_build_all(self):
        name = self._get_name()
        if name is None:
            return
        mesh_curve = self._get_mesh_or_curve()
        if mesh_curve is None:
            return
        mesh, curve, _ = mesh_curve
        axis = self._get_axis()
        up_axis = self._get_up_axis()
        front_axis = self._get_front_axis()
        up_local_axis = self._get_up_local_axis()
        num_cv = cmds.intField(self._num_cv_field, q=True, value=True)
        ribbon_width = cmds.floatField(self._ribbon_width_field, q=True, value=True)
        num_ik = cmds.intField(self._num_ik_field, q=True, value=True)
        ik_radius = cmds.floatField(self._ik_radius_field, q=True, value=True)
        num_output = cmds.intField(self._num_output_field, q=True, value=True)
        fk_radius = cmds.floatField(self._fk_radius_field, q=True, value=True)
        num_volume = cmds.intField(self._num_volume_field, q=True, value=True)
        ts_radius = cmds.floatField(self._ts_radius_field, q=True, value=True)

        def _all():
            rig.build_base(mesh=mesh, curve=curve, name=name, axis=axis, up_axis=up_axis,
                            front_axis=front_axis, up_local_axis=up_local_axis,
                            num_cv=num_cv, ribbon_width=ribbon_width)
            rig.build_ik(name=name, num_ik=num_ik, ctrl_radius=ik_radius)
            rig.build_output(name=name, num_output=num_output)
            rig.build_fk(name=name, ctrl_radius=fk_radius)
            return rig.build_twist_scale(name=name, num_volume=num_volume, ctrl_radius=ts_radius)

        self._run('전체 빌드(1~5단계)', _all)

    def _set_status(self, text):
        cmds.scrollField(self._status_field, e=True, text=text)


def show():
    tool = TentacleRibbonRigUI()
    tool.create_ui()
    return tool


if __name__ == '__main__':
    show()
