"""
Controller Generator Tool
선택한 오브젝트 기준으로 컨트롤러를 생성합니다.

Features:
  - Shape 선택 (circle / square / cube / sphere 등 13종)
  - 계층 구조 자유 선택 (Grp / Offset / Cnt / Ctrl)
  - Single(독립 생성) / Tree(선택 오브젝트 계층 반영) 모드
  - 크기 / 노말 축 / 컬러 설정
  - Prefix / Suffix / Search-Replace 네이밍

Usage:
    import importlib
    import ctrl_generator_tool
    importlib.reload(ctrl_generator_tool)
    ctrl_generator_tool.show()
"""
import maya.cmds as cmds

try:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtCore import Qt
    from shiboken2 import wrapInstance
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtCore import Qt
    from shiboken6 import wrapInstance

import maya.OpenMayaUI as omui


# ─────────────────────────────────────────────────────────────────────────────
#  Shape Data  { name: (degree, [points], [knots]) }
#  None = circle → cmds.circle() 사용
# ─────────────────────────────────────────────────────────────────────────────
_SHAPES = {
    'circle':      None,
    'square':      (1, [(-1,0,1),(-1,0,-1),(1,0,-1),(1,0,1),(-1,0,1)],
                       [0,1,2,3,4]),
    'roundSquare': (1, [(0,0,1.019),(-.273,0,1.019),(-.577,0,.985),(-.841,0,.841),
                        (-.985,0,.577),(-1.016,0,.279),(-1.012,0,0),(-1.019,0,-.273),
                        (-.985,0,-.577),(-.841,0,-.841),(-.577,0,-.985),(-.273,0,-1.019),
                        (0,0,-1.012),(.279,0,-1.016),(.577,0,-.985),(.841,0,-.841),
                        (.985,0,-.577),(1.019,0,-.273),(1.019,0,0),(1.017,0,.279),
                        (.985,0,.577),(.841,0,.841),(.577,0,.985),(.273,0,1.019),(0,0,1.019)],
                       list(range(25))),
    'cube':        (1, [(.5,-.5,.5),(.5,.5,.5),(.5,.5,-.5),(.5,-.5,-.5),(.5,-.5,.5),
                        (-.5,-.5,.5),(-.5,.5,.5),(-.5,.5,-.5),(-.5,-.5,-.5),(.5,-.5,-.5),
                        (.5,.5,-.5),(-.5,.5,-.5),(-.5,-.5,-.5),(-.5,-.5,.5),(-.5,.5,.5),(.5,.5,.5)],
                       list(range(16))),
    'sphere':      (1, [(0,0,1),(0,.309,.951),(0,.588,.809),(0,.809,.588),(0,.951,.309),(0,1,0),
                        (.309,.951,0),(.588,.809,0),(.809,.588,0),(.951,.309,0),(1,0,0),
                        (.951,0,.309),(.809,0,.588),(.588,0,.809),(.309,0,.951),(0,0,1),
                        (0,-.309,.951),(0,-.588,.809),(0,-.809,.588),(0,-.951,.309),(0,-1,0),
                        (.309,-.951,0),(.588,-.809,0),(.809,-.588,0),(.951,-.309,0),(1,0,0),
                        (.951,0,-.309),(.809,0,-.588),(.588,0,-.809),(.309,0,-.951),(0,0,-1),
                        (0,.309,-.951),(0,.588,-.809),(0,.809,-.588),(0,.951,-.309),(0,1,0),
                        (-.309,.951,0),(-.588,.809,0),(-.809,.588,0),(-.951,.309,0),(-1,0,0),
                        (-.951,0,-.309),(-.809,0,-.588),(-.588,0,-.809),(-.309,0,-.951),(0,0,-1),
                        (0,-.309,-.951),(0,-.588,-.809),(0,-.809,-.588),(0,-.951,-.309),(0,-1,0),
                        (-.309,-.951,0),(-.588,-.809,0),(-.809,-.588,0),(-.951,-.309,0),(-1,0,0),
                        (-.951,0,.309),(-.809,0,.588),(-.588,0,.809),(-.309,0,.951),(0,0,1)],
                       list(range(61))),
    'octah':       (1, [(0,.6,0),(0,0,-.6),(-.6,0,0),(0,.6,0),(0,0,.6),(-.6,0,0),(0,-.6,0),
                        (0,0,.6),(.6,0,0),(0,.6,0),(0,0,-.6),(.6,0,0),(0,-.6,0),(0,0,-.6)],
                       list(range(14))),
    'diamond':     (1, [(0,1,0),(1,0,0),(0,-1,0),(-1,0,0),(0,1,0),(0,0,1),(0,-1,0),(0,0,-1),(0,1,0)],
                       list(range(9))),
    'cross':       (1, [(0,0,-1),(0,0,1),(0,0,0),(1,0,0),(-1,0,0)], [0,1,2,3,4]),
    'triangle':    (1, [(0,0,1.5),(-1,0,0),(1,0,0),(0,0,1.5)],       [0,1,2,3]),
    'pin':         (1, [(0,0,0),(0,2,0),(1,3,0),(0,4,0),(-1,3,0),(0,2,0),(0,3,1),(0,4,0),
                        (0,3,-1),(1,3,0),(0,3,1),(-1,3,0),(0,3,-1),(0,2,0)],
                       list(range(14))),
    'locate':      (1, [(0,-1,0),(0,1,0),(0,0,0),(-1,0,0),(1,0,0),(0,0,0),(0,0,1),(0,0,-1)],
                       list(range(8))),
    'gear':        (1, [(-.4,0,0),(-.2,0,-.346),(.2,0,-.346),(.4,0,0),(.2,0,.346),(-.2,0,.346),
                        (-.4,0,0),(-1.366,0,0),(-.866,0,-.5),(-.683,0,-1.183),(0,0,-1),
                        (.683,0,-1.183),(.866,0,-.5),(1.366,0,0),(.866,0,.5),(.683,0,1.183),
                        (0,0,1),(-.683,0,1.183),(-.866,0,.5),(-1.366,0,0)],
                       list(range(20))),
}

SHAPE_ORDER = ['circle', 'square', 'roundSquare', 'cube', 'sphere', 'octah',
               'diamond', 'cross', 'triangle', 'pin', 'locate', 'gear']

# ─────────────────────────────────────────────────────────────────────────────
#  Color Palette  [(label, maya_override_index, (R,G,B))]
# ─────────────────────────────────────────────────────────────────────────────
COLOR_PALETTE = [
    ('None',      0,  (100,100,100)), ('Black',    1,  (  0,  0,  0)),
    ('DkRed',     4,  (156,  0, 41)), ('Red',      13, (255,  0,  0)),
    ('Orange',    21, (228,174,123)), ('Yellow',   17, (255,255,  0)),
    ('DkGreen',   23, (  0,153, 84)), ('Green',    14, (  0,255,  0)),
    ('LtGreen',   19, ( 66,255,163)), ('LtBlue',   18, ( 99,219,255)),
    ('DkBlue',    5,  (  0,  5, 97)), ('Blue',     6,  (  0,  0,255)),
    ('Magenta',   9,  (199,  0,199)), ('Pink',     20, (255,176,176)),
    ('White',     16, (255,255,255)), ('Grey',     3,  (153,153,153)),
    ('Purple',    8,  ( 90,  0,130)), ('DkGray',   2,  ( 70, 70, 70)),
    ('Tan',       24, (175,100,  0)), ('Teal',     27, (  0,160,120)),
    ('Navy',      28, ( 30, 60,200)), ('YlwGrn',   22, (190,220, 50)),
    ('Crimson',   30, (160,  0, 40)), ('Olive',    25, (100,120,  0)),
]


# ─────────────────────────────────────────────────────────────────────────────
#  Core Logic
# ─────────────────────────────────────────────────────────────────────────────
def _get_maya_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)


def _rotate_pts(pts, axis):
    """XZ 평면 기준 포인트를 다른 축 방향으로 회전."""
    if axis == 'Y':
        return pts
    result = []
    for x, y, z in pts:
        if axis == 'X':
            # Z축 기준 +90°: (x,y,z) → (-y, x, z) → y=0이면 (0, x, z)
            result.append((-y, x, z))
        else:  # Z
            # X축 기준 +90°: (x,y,z) → (x, -z, y) → y=0이면 (x, -z, 0)
            result.append((x, -z, y))
    return result


def _create_curve(shape_key, size, axis):
    """지정 shape의 커브를 생성하고 노드 이름을 반환."""
    data = _SHAPES.get(shape_key)
    if data is None:          # circle
        nrm = {'X': (1,0,0), 'Z': (0,0,1)}.get(axis, (0,1,0))
        crv = cmds.circle(radius=size, normalX=nrm[0], normalY=nrm[1], normalZ=nrm[2],
                          constructionHistory=False)[0]
    else:
        deg, raw_pts, knots = data
        pts = _rotate_pts(raw_pts, axis)
        pts = [(x*size, y*size, z*size) for x, y, z in pts]
        crv = cmds.curve(degree=deg, point=pts, knot=knots)
    return crv


def _set_color(node, idx):
    if idx == 0:
        return
    for sh in (cmds.listRelatives(node, shapes=True, type='nurbsCurve') or []):
        cmds.setAttr(sh + '.overrideEnabled', 1)
        cmds.setAttr(sh + '.overrideColor', idx)


def _apply_display_settings(node, line_width):
    for sh in (cmds.listRelatives(node, shapes=True, type='nurbsCurve') or []):
        if line_width > 1:
            cmds.setAttr(sh + '.lineWidth', float(line_width))


import string as _string

def _apply_method(method_, name_, index=0):
    """
    reNamer01 호환 네이밍 메서드를 적용해 컨트롤러 base 이름을 반환.

    패턴:
      old>>new   — name_ 내 old를 new로 치환        e.g.  _jnt>>
      pre%suf    — name_ 앞뒤에 prefix/suffix 추가  e.g.  C_%_FK
      name###    — # 자릿수 숫자 패딩으로 대체       e.g.  ctrl_###
      name@      — @ 를 알파벳(A,B,C…) 으로 대체    e.g.  ctrl_@
    """
    if not method_:
        return name_
    if '>>' in method_:
        old, new = method_.split('>>', 1)
        return name_.replace(old, new)
    if '#' in method_:
        slot = method_.count('#')
        pad  = str(index + 1).zfill(slot)
        return method_.replace('#' * slot, pad)
    if '@' in method_:
        pad = _string.ascii_uppercase[index % 26]
        return method_.replace('@', pad)
    if '%' in method_:
        parts  = method_.split('%', 1)
        prefix = parts[0]
        suffix = parts[1] if len(parts) > 1 else ''
        return prefix + name_ + suffix
    return method_ + name_


def _build_one(obj, layer_cfg, name_method, index,
               shape_key, size, axis, color_idx,
               line_width=1, parent_node=None):
    """
    단일 오브젝트에 대해 컨트롤러 계층을 생성.
    layer_cfg  : [(enabled, suffix), …]  외부 → 내부 순서, 마지막이 Ctrl
    name_method: reNamer01 패턴 문자열
    index      : 선택 목록 내 순서 (# / @ 패턴에 사용)
    Returns    : (top_node, ctrl_node)
    """
    short    = obj.split('|')[-1].split(':')[-1]
    fullbase = _apply_method(name_method, short, index)

    pos = cmds.xform(obj, q=True, ws=True, rp=True)
    rot = cmds.xform(obj, q=True, ws=True, ro=True)

    top_node  = None
    prev_node = parent_node
    ctrl_node = None

    for i, (enabled, sfx) in enumerate(layer_cfg):
        is_ctrl = (i == len(layer_cfg) - 1)
        if not enabled and not is_ctrl:
            continue

        node_name = fullbase + sfx

        if is_ctrl:
            raw = _create_curve(shape_key, size, axis)
            node = cmds.rename(raw, node_name)
            shapes = cmds.listRelatives(node, shapes=True) or []
            if shapes:
                cmds.rename(shapes[0], node_name + 'Shape')
            _set_color(node, color_idx)
            _apply_display_settings(node, line_width)
            ctrl_node = node
        else:
            node = cmds.createNode('transform', name=node_name)

        # 월드 트랜스폼 매칭 (parent 이전에 설정 → cmds.parent가 ws 유지)
        cmds.xform(node, ws=True, t=pos, ro=rot)

        if prev_node:
            cmds.parent(node, prev_node)

        if top_node is None:
            top_node = node
        prev_node = node

    return top_node, ctrl_node


def _analyze(selection):
    """
    선택 오브젝트 내 부모-자식 관계를 분석.
    Returns (roots, children_map)
      roots        : 선택 내 부모가 없는 오브젝트 목록
      children_map : {obj_long: [child_long, …]}
    """
    sel_set = set(selection)
    children_map = {obj: [] for obj in selection}
    roots = []

    for obj in selection:
        parents = cmds.listRelatives(obj, parent=True, fullPath=True) or []
        parent_long = parents[0] if parents else None
        if parent_long and parent_long in sel_set:
            children_map[parent_long].append(obj)
        else:
            roots.append(obj)

    return roots, children_map


def create_controllers(layer_cfg, name_method,
                       shape_key, size, axis, color_idx, line_width, tree_mode):
    """메인 생성 함수. 현재 선택을 가져와 컨트롤러를 생성."""
    selection = cmds.ls(selection=True, long=True)
    if not selection:
        cmds.warning('ctrl_generator_tool: 오브젝트를 선택하세요.')
        return

    cmds.undoInfo(openChunk=True, chunkName='ctrlGenerator')
    try:
        if tree_mode:
            roots, children_map = _analyze(selection)
            counter = [0]   # 재귀 중 전역 인덱스 유지

            def _recurse(obj, parent_ctrl=None):
                idx = counter[0]
                counter[0] += 1
                _, ctrl = _build_one(obj, layer_cfg, name_method, idx,
                                     shape_key, size, axis, color_idx,
                                     line_width=line_width, parent_node=parent_ctrl)
                for child in children_map.get(obj, []):
                    _recurse(child, ctrl)

            for root in roots:
                _recurse(root)
        else:
            for idx, obj in enumerate(selection):
                _build_one(obj, layer_cfg, name_method, idx,
                           shape_key, size, axis, color_idx,
                           line_width=line_width)

        print('ctrl_generator_tool: {} 컨트롤러 생성 완료.'.format(len(selection)))
    finally:
        cmds.undoInfo(closeChunk=True)


# ─────────────────────────────────────────────────────────────────────────────
#  Stylesheet
# ─────────────────────────────────────────────────────────────────────────────
_QSS = """
QDialog {
    background: #282828;
    color: #d0d0d0;
}
QGroupBox {
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    margin-top: 10px;
    padding: 8px 6px 6px 6px;
    color: #787878;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 1.5px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QListWidget {
    background: #1c1c1c;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    color: #c8c8c8;
    font-size: 12px;
    outline: none;
}
QListWidget::item { padding: 4px 10px; }
QListWidget::item:selected {
    background: #2d5a9e;
    color: #ffffff;
    border-radius: 2px;
}
QListWidget::item:hover:!selected { background: #313131; }
QDoubleSpinBox, QSpinBox {
    background: #1c1c1c;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    color: #d0d0d0;
    padding: 2px 6px;
    min-height: 22px;
}
QDoubleSpinBox:focus, QSpinBox:focus { border-color: #4a7adf; }
QLineEdit {
    background: #1c1c1c;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    color: #d0d0d0;
    padding: 3px 6px;
    min-height: 22px;
}
QLineEdit:focus { border-color: #4a7adf; }
QCheckBox { color: #d0d0d0; spacing: 5px; }
QCheckBox::indicator {
    width: 13px; height: 13px;
    border: 1px solid #555;
    border-radius: 2px;
    background: #1c1c1c;
}
QCheckBox::indicator:checked { background: #4a7adf; border-color: #4a7adf; }
QRadioButton { color: #d0d0d0; spacing: 5px; }
QRadioButton::indicator {
    width: 13px; height: 13px;
    border: 1px solid #555;
    border-radius: 7px;
    background: #1c1c1c;
}
QRadioButton::indicator:checked { background: #4a7adf; border-color: #4a7adf; }
QLabel { color: #d0d0d0; }
QFrame[frameShape="4"] { color: #3c3c3c; }   /* HLine */
QPushButton#createBtn {
    background: #2d5a9e;
    border: none;
    border-radius: 4px;
    color: #ffffff;
    font-size: 13px;
    font-weight: bold;
    padding: 10px;
    min-height: 38px;
}
QPushButton#createBtn:hover  { background: #3a6ab0; }
QPushButton#createBtn:pressed { background: #1e4a8a; }
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Sub-Widgets
# ─────────────────────────────────────────────────────────────────────────────
class _ColorBtn(QtWidgets.QPushButton):
    def __init__(self, maya_idx, rgb, tooltip, parent=None):
        super().__init__(parent)
        self.maya_idx = maya_idx
        r, g, b = rgb
        self.setFixedSize(20, 20)
        self.setCheckable(True)
        self.setToolTip('{} ({})'.format(tooltip, maya_idx))
        self.setStyleSheet(
            'QPushButton{{background:rgb({r},{g},{b});border:1px solid #444;border-radius:2px;}}'
            'QPushButton:checked{{border:2px solid #fff;}}'
            'QPushButton:hover{{border:1px solid #aaa;}}'
            .format(r=r, g=g, b=b)
        )


class _LayerRow(QtWidgets.QWidget):
    """단일 계층 행: 활성화 체크박스 + 레이블 + 서픽스 입력."""

    def __init__(self, label, default_sfx, fixed=False, checked=False, parent=None):
        super().__init__(parent)
        self._fixed = fixed
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 1, 0, 1)
        lay.setSpacing(6)

        if fixed:
            dot = QtWidgets.QLabel('◆')
            dot.setFixedWidth(18)
            dot.setAlignment(Qt.AlignCenter)
            dot.setStyleSheet('color:#4a7adf; font-size:9px;')
            lay.addWidget(dot)
            self._chk = None
        else:
            self._chk = QtWidgets.QCheckBox()
            self._chk.setChecked(checked)
            self._chk.setFixedWidth(18)
            lay.addWidget(self._chk)

        lbl = QtWidgets.QLabel(label)
        lbl.setFixedWidth(44)
        lbl.setStyleSheet('color:#aaa; font-size:11px;')
        lay.addWidget(lbl)

        self._sfx = QtWidgets.QLineEdit(default_sfx)
        self._sfx.setFixedWidth(96)
        lay.addWidget(self._sfx)
        lay.addStretch()

    @property
    def enabled(self):
        return True if self._fixed else self._chk.isChecked()

    @property
    def suffix(self):
        return self._sfx.text()

    def set_checked(self, v):
        if self._chk:
            self._chk.setChecked(v)


# ─────────────────────────────────────────────────────────────────────────────
#  Main Window
# ─────────────────────────────────────────────────────────────────────────────
class CtrlGeneratorTool(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent or _get_maya_window())
        self.setWindowTitle('Controller Generator')
        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setFixedWidth(390)
        self.setStyleSheet(_QSS)

        self._color_idx  = 0
        self._color_btns = []
        self._rows       = []
        self._sel_job    = None

        self._build_ui()
        self._sel_job = cmds.scriptJob(event=['SelectionChanged', self._update_preview])

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        root.addWidget(self._section_shape())
        root.addWidget(self._section_hierarchy())
        root.addWidget(self._section_naming())
        root.addWidget(self._btn_create())

    # ── Shape Section ─────────────────────────────────────────────────────────
    def _section_shape(self):
        box = QtWidgets.QGroupBox('SHAPE')
        outer = QtWidgets.QHBoxLayout(box)
        outer.setContentsMargins(8, 14, 8, 8)
        outer.setSpacing(10)

        # 왼쪽: 쉐입 리스트
        self._shape_list = QtWidgets.QListWidget()
        self._shape_list.setFixedWidth(122)
        self._shape_list.setFixedHeight(160)
        for name in SHAPE_ORDER:
            self._shape_list.addItem(name)
        self._shape_list.setCurrentRow(0)
        outer.addWidget(self._shape_list)

        # 오른쪽: 설정
        right = QtWidgets.QVBoxLayout()
        right.setSpacing(7)

        # Size
        row_size = QtWidgets.QHBoxLayout()
        row_size.addWidget(self._label('Size', 32))
        self._size = QtWidgets.QDoubleSpinBox()
        self._size.setRange(0.001, 9999.0)
        self._size.setValue(1.0)
        self._size.setSingleStep(0.1)
        self._size.setDecimals(3)
        row_size.addWidget(self._size)
        right.addLayout(row_size)

        # Normal Axis
        row_norm = QtWidgets.QHBoxLayout()
        row_norm.addWidget(self._label('Normal', 46))
        self._axis_grp = QtWidgets.QButtonGroup(self)
        for ax in ('X', 'Y', 'Z'):
            rb = QtWidgets.QRadioButton(ax)
            self._axis_grp.addButton(rb)
            row_norm.addWidget(rb)
        row_norm.addStretch()
        self._axis_grp.buttons()[1].setChecked(True)  # Y default
        right.addLayout(row_norm)

        # Color
        right.addWidget(self._label('Color', 0))
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(3)
        for i, (lbl, idx, rgb) in enumerate(COLOR_PALETTE):
            btn = _ColorBtn(idx, rgb, lbl)
            btn.clicked.connect(lambda *_, b=btn: self._pick_color(b))
            self._color_btns.append(btn)
            grid.addWidget(btn, i // 8, i % 8)
        self._color_btns[0].setChecked(True)
        right.addLayout(grid)

        # Line Width
        row_disp = QtWidgets.QHBoxLayout()
        row_disp.addWidget(self._label('LineW', 38))
        self._line_width = QtWidgets.QSpinBox()
        self._line_width.setRange(1, 10)
        self._line_width.setValue(1)
        self._line_width.setFixedWidth(55)
        row_disp.addWidget(self._line_width)
        row_disp.addStretch()
        right.addLayout(row_disp)
        right.addStretch()

        outer.addLayout(right)
        return box

    # ── Hierarchy Section ─────────────────────────────────────────────────────
    def _section_hierarchy(self):
        box = QtWidgets.QGroupBox('HIERARCHY')
        lay = QtWidgets.QVBoxLayout(box)
        lay.setContentsMargins(8, 14, 8, 8)
        lay.setSpacing(5)

        # Mode
        row_mode = QtWidgets.QHBoxLayout()
        row_mode.addWidget(self._label('Mode', 36))
        self._mode_grp = QtWidgets.QButtonGroup(self)
        for label in ('Single', 'Tree'):
            rb = QtWidgets.QRadioButton(label)
            self._mode_grp.addButton(rb)
            row_mode.addWidget(rb)
        self._mode_grp.buttons()[0].setChecked(True)
        row_mode.addStretch()
        lay.addLayout(row_mode)

        # Divider
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        lay.addWidget(sep)

        # Header
        hdr = QtWidgets.QHBoxLayout()
        for txt, w in [('', 18), ('Layer', 44), ('Suffix', 96)]:
            l = QtWidgets.QLabel(txt)
            l.setFixedWidth(w)
            l.setStyleSheet('color:#585858; font-size:10px;')
            hdr.addWidget(l)
        hdr.addStretch()
        lay.addLayout(hdr)

        # Layer rows (outer → inner)
        cfg = [
            ('Grp',    '_grp',    False, False),
            ('Offset', '_offset', False, True),
            ('Cnt',    '_cnt',    False, False),
            ('Ctrl',   '_ctrl',   True,  True),
        ]
        for label, sfx, fixed, checked in cfg:
            row = _LayerRow(label, sfx, fixed=fixed, checked=checked)
            # Ctrl suffix 변경 시 NAMING preview 갱신 (Ctrl 행은 마지막)
            row._sfx.textChanged.connect(
                lambda _: self._update_preview() if self._rows else None
            )
            lay.addWidget(row)
            self._rows.append(row)

        return box

    # ── Naming Section ────────────────────────────────────────────────────────
    def _section_naming(self):
        box = QtWidgets.QGroupBox('NAMING')
        lay = QtWidgets.QVBoxLayout(box)
        lay.setContentsMargins(8, 14, 8, 8)
        lay.setSpacing(6)

        # Method input
        row_m = QtWidgets.QHBoxLayout()
        row_m.addWidget(self._label('Method', 50))
        self._method = QtWidgets.QLineEdit()
        self._method.setPlaceholderText('e.g.  _jnt>>   or   C_%_FK')
        row_m.addWidget(self._method)
        lay.addLayout(row_m)

        # Syntax reference chips
        chip_row = QtWidgets.QHBoxLayout()
        chip_row.setSpacing(4)
        chip_row.addSpacing(50)
        chip_data = [
            ('old>>new',  '_jnt>>'),
            ('pre%suf',   'C_%_FK'),
            ('###',       'ctrl_###'),
            ('@',         'ctrl_@'),
        ]
        for label, example in chip_data:
            btn = QtWidgets.QPushButton(label)
            btn.setFixedHeight(18)
            btn.setStyleSheet(
                'QPushButton{background:#333;border:1px solid #4a4a4a;border-radius:3px;'
                'color:#888;font-size:10px;padding:0 5px;}'
                'QPushButton:hover{background:#3a3a3a;color:#bbb;}'
            )
            btn.setToolTip(example)
            btn.clicked.connect(lambda _, ex=example: self._method.setText(ex))
            chip_row.addWidget(btn)
        chip_row.addStretch()
        lay.addLayout(chip_row)

        # Divider
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setStyleSheet('color:#3c3c3c;')
        lay.addWidget(sep)

        # Preview row
        row_p = QtWidgets.QHBoxLayout()
        row_p.addWidget(self._label('Preview', 50))
        self._preview_src = QtWidgets.QLineEdit()
        self._preview_src.setReadOnly(True)
        self._preview_src.setPlaceholderText('(no selection)')
        self._preview_src.setFixedWidth(108)
        self._preview_src.setStyleSheet('background:#1a1a1a; color:#888; border:1px solid #333;')
        row_p.addWidget(self._preview_src)
        arrow = QtWidgets.QLabel('→')
        arrow.setAlignment(Qt.AlignCenter)
        arrow.setFixedWidth(18)
        arrow.setStyleSheet('color:#555;')
        row_p.addWidget(arrow)
        self._preview_dst = QtWidgets.QLineEdit()
        self._preview_dst.setReadOnly(True)
        self._preview_dst.setStyleSheet(
            'background:#1a1a1a; color:#6a9adf; border:1px solid #333;'
        )
        row_p.addWidget(self._preview_dst)
        lay.addLayout(row_p)

        # Preview 실시간 업데이트
        self._method.textChanged.connect(self._update_preview)
        # Ctrl suffix가 바뀌어도 preview 갱신 (LayerRow 생성 후 연결)
        self._update_preview()

        return box

    def _update_preview(self, *_):
        method = self._method.text()
        sel    = cmds.ls(selection=True, long=False)
        src    = sel[0].split('|')[-1].split(':')[-1] if sel else ''
        self._preview_src.setText(src)
        if not method or not src:
            self._preview_dst.setText('')
            return
        ctrl_sfx = self._rows[-1].suffix if self._rows else '_ctrl'
        base     = _apply_method(method, src, 0)
        self._preview_dst.setText(base + ctrl_sfx)

    def closeEvent(self, event):
        try:
            if self._sel_job and cmds.scriptJob(exists=self._sel_job):
                cmds.scriptJob(kill=self._sel_job, force=True)
        except Exception:
            pass
        super().closeEvent(event)

    # ── Create Button ─────────────────────────────────────────────────────────
    def _btn_create(self):
        btn = QtWidgets.QPushButton('▶   Create Controllers')
        btn.setObjectName('createBtn')
        btn.clicked.connect(self._on_create)
        return btn

    # ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _label(text, width):
        l = QtWidgets.QLabel(text)
        if width:
            l.setFixedWidth(width)
        l.setStyleSheet('color:#aaa; font-size:11px;')
        return l

    def _pick_color(self, clicked):
        for b in self._color_btns:
            if b is not clicked:
                b.setChecked(False)
        self._color_idx = clicked.maya_idx

    # ── Action ────────────────────────────────────────────────────────────────
    def _on_create(self):
        item = self._shape_list.currentItem()
        shape_key = item.text() if item else 'circle'
        size      = self._size.value()

        # Normal axis
        axes = ['X', 'Y', 'Z']
        checked_btn = next((b for b in self._axis_grp.buttons() if b.isChecked()), None)
        axis = axes[self._axis_grp.buttons().index(checked_btn)] if checked_btn else 'Y'

        # Hierarchy
        layer_cfg = [(r.enabled, r.suffix) for r in self._rows]
        tree_mode = self._mode_grp.buttons()[1].isChecked()

        # Naming
        name_method = self._method.text()

        line_width = self._line_width.value()

        create_controllers(
            layer_cfg, name_method,
            shape_key, size, axis, self._color_idx, line_width, tree_mode
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────────────────────────────────────
_window = None


def show():
    global _window
    if _window is not None:
        try:
            _window.close()
            _window.deleteLater()
        except Exception:
            pass
    _window = CtrlGeneratorTool()
    _window.show()
    return _window
