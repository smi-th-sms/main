# -*- coding: utf-8 -*-
"""============================================================================
촉수(Tentacle) Auto-Rig UI

tentacle_autorig의 2단계 빌드 함수를 감싸는 UI.

    1단계: base_CRV만 생성 -- 씬에서 direction/CV 위치를 검토(필요하면 CV를
           직접 조정)한 뒤 2단계로 넘어간다.
    2단계: 1단계에서 만든 base_CRV를 기준으로 나머지 전체 파이프라인
           (null -> IK -> splineIK -> FK -> skin -> null twist -> bind joint)을
           빌드한다.

Usage:
    from python2.rigging import tentacle_autorig_ui
    import importlib
    importlib.reload(tentacle_autorig_ui)
    tentacle_autorig_ui.show()
============================================================================"""
import importlib
import traceback

import maya.cmds as cmds

from python2.rigging import tentacle_autorig as rig

_WIN_ID = 'tentacleAutoRigWin'


def _get_selected_mesh():
    sel = cmds.ls(sl=True, type='transform')
    if not sel:
        cmds.warning('tentacle_autorig_ui: 먼저 오브젝트를 선택하세요.')
        return None
    return sel[0]


class TentacleAutoRigUI(object):
    def __init__(self):
        self.window_name = _WIN_ID
        self._mesh_field = None
        self._name_field = None
        self._axis_menu = None
        self._num_nulls_field = None
        self._num_ctrls_field = None
        self._num_ik_ctrls_field = None
        self._step2_button = None
        self._status_field = None

    def create_ui(self):
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)
        win = cmds.window(self.window_name, title='Tentacle Auto-Rig',
                           widthHeight=(380, 560), sizeable=True)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnAttach=('both', 8), parent=win)
        self.build_tab_ui()
        cmds.showWindow(win)
        return win

    def build_tab_ui(self, parent=None):
        """단독 창 대신 다른 툴 허브의 탭으로도 얹을 수 있게 분리된 UI 빌드 진입점."""
        if parent is not None:
            cmds.scrollLayout(childResizable=True, parent=parent)

        cmds.text(label='촉수 Auto-Rig', font='boldLabelFont', height=24)
        cmds.separator(height=8, style='in')

        cmds.frameLayout(label='오브젝트', collapsable=True, collapse=False, marginWidth=5, marginHeight=5)
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                        columnAttach=[(1, 'both', 0), (2, 'both', 0)])
        self._mesh_field = cmds.textField(text='pSphere1', placeholderText='촉수 형상 mesh')
        cmds.button(label='<< 선택', width=70, c=lambda *_: self._grab_selected())
        cmds.setParent('..')
        cmds.setParent('..')

        cmds.frameLayout(label='1단계 -- Base Curve 생성', collapsable=True, collapse=False,
                          marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=4)

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
        cmds.text(label='Null 개수 (=CV 개수)', align='left')
        self._num_nulls_field = cmds.intField(value=13, minValue=2, maxValue=200)
        cmds.setParent('..')

        cmds.setParent('..')  # columnLayout

        cmds.separator(height=6, style='in')
        cmds.button(label='1. Curve 생성', height=32, backgroundColor=[0.25, 0.45, 0.3],
                    c=lambda *_: self._on_build_curve())
        cmds.text(label='-> 생성 후 씬에서 curve의 방향과 CV 위치를 검토하세요.',
                  align='left', font='smallPlainLabelFont')

        cmds.setParent('..')  # frameLayout

        cmds.frameLayout(label='2단계 -- 나머지 리그 빌드', collapsable=True, collapse=False,
                          marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=4)

        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='FK/IK 조인트 개수', align='left')
        self._num_ctrls_field = cmds.intField(value=7, minValue=2, maxValue=50)
        cmds.setParent('..')

        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 200))
        cmds.text(label='IK 컨트롤 개수', align='left')
        self._num_ik_ctrls_field = cmds.intField(value=2, minValue=2, maxValue=50)
        cmds.setParent('..')

        cmds.setParent('..')  # columnLayout

        cmds.separator(height=6, style='in')
        self._step2_button = cmds.button(label='2. 나머지 리그 빌드', height=32,
                                          backgroundColor=[0.2, 0.35, 0.5],
                                          c=lambda *_: self._on_build_rest())

        cmds.setParent('..')  # frameLayout

        cmds.separator(height=8, style='in')
        self._status_field = cmds.scrollField(editable=False, wordWrap=True, height=110,
                                               font='smallPlainLabelFont', text='')

    def _grab_selected(self):
        mesh = _get_selected_mesh()
        if mesh:
            cmds.textField(self._mesh_field, e=True, text=mesh)

    def _on_build_curve(self):
        mesh = cmds.textField(self._mesh_field, q=True, text=True).strip()
        name = cmds.textField(self._name_field, q=True, text=True).strip()
        axis_label = cmds.optionMenu(self._axis_menu, q=True, value=True)
        axis = None if axis_label.startswith('Auto') else axis_label
        num_nulls = cmds.intField(self._num_nulls_field, q=True, value=True)

        if not mesh or not cmds.objExists(mesh):
            self._set_status('오브젝트 "{}"를 찾을 수 없습니다.'.format(mesh))
            return
        if not name:
            self._set_status('리그 이름을 입력하세요.')
            return

        try:
            importlib.reload(rig)
            result = rig.build_tentacle_base_curve(mesh=mesh, name=name, axis=axis, num_nulls=num_nulls)
        except Exception as exc:
            cmds.warning('tentacle_autorig_ui: curve 생성 실패 -- {}'.format(exc))
            print(traceback.format_exc())
            self._set_status('curve 생성 실패: {}\n(자세한 내용은 Script Editor 확인)'.format(exc))
            return

        cmds.select(result['base_curve'])
        cmds.viewFit(result['base_curve'])

        msg = (
            '1단계 완료: {name}_base_CRV\n'
            '  axis    : {axis}\n'
            '  CV 개수 : {num_cv}\n\n'
            '씬에서 curve의 방향/CV 위치를 검토한 뒤 "2. 나머지 리그 빌드"를 누르세요.'
        ).format(name=name, axis=result['axis'], num_cv=num_nulls)
        self._set_status(msg)

    def _on_build_rest(self):
        name = cmds.textField(self._name_field, q=True, text=True).strip()
        num_ctrls = cmds.intField(self._num_ctrls_field, q=True, value=True)
        num_ik_ctrls = cmds.intField(self._num_ik_ctrls_field, q=True, value=True)

        if not name:
            self._set_status('리그 이름을 입력하세요.')
            return

        try:
            importlib.reload(rig)
            result = rig.build_tentacle_rig_continue(name=name, num_ctrls=num_ctrls,
                                                       num_ik_ctrls=num_ik_ctrls)
        except Exception as exc:
            cmds.warning('tentacle_autorig_ui: 리그 빌드 실패 -- {}'.format(exc))
            print(traceback.format_exc())
            self._set_status('리그 빌드 실패: {}\n(자세한 내용은 Script Editor 확인)'.format(exc))
            return

        msg = (
            '빌드 완료: {name}\n'
            '  axis        : {axis}\n'
            '  FK/IK jnt   : {num_fk}\n'
            '  IK ctrls    : {num_ik}\n'
            '  null        : {num_null}'
        ).format(name=name, axis=result['axis'], num_fk=len(result['fk_ctrls']),
                 num_ik=len(result['ik_ctrls']), num_null=len(result['nulls']))
        self._set_status(msg)

    def _set_status(self, text):
        cmds.scrollField(self._status_field, e=True, text=text)


def show():
    tool = TentacleAutoRigUI()
    tool.create_ui()
    return tool


if __name__ == '__main__':
    show()
