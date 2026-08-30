"""
Fit Chains Config Editor
========================
Maya 오브젝트를 Parts 단위로 JSON에 등록/편집하는 툴.

JSON 구조:
    {
      "parts": {
        "arm_L": ["jnt_arm_L_01", "jnt_arm_L_02"],
        "leg_R": ["jnt_leg_R_01"]
      }
    }

Usage:
    import importlib
    import fit_chains_config_editor
    importlib.reload(fit_chains_config_editor)
    fit_chains_config_editor.show()
"""

import os
import json
import maya.cmds as cmds

# ─────────────────────────────────────────────────────────────
# 기본 경로
# ─────────────────────────────────────────────────────────────
_TOOL_DIR     = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_JSON = os.path.join(_TOOL_DIR, "fit_chains_config.json")

_WIN_ID = "fitChainsConfigEditorWin"


# ─────────────────────────────────────────────────────────────
# JSON I/O
# ─────────────────────────────────────────────────────────────
def _load_json(path):
    """JSON 파일을 읽어 dict 반환. 없거나 오류 시 빈 dict."""
    if not os.path.exists(path):
        return {"parts": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "parts" not in data or not isinstance(data["parts"], dict):
            data["parts"] = {}
        return data
    except Exception as e:
        cmds.warning("fit_chains_config_editor: JSON load error - " + str(e))
        return {"parts": {}}


def _save_json(path, data):
    """dict를 JSON 파일로 저장."""
    try:
        dirpath = os.path.dirname(path)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        cmds.warning("fit_chains_config_editor: JSON save error - " + str(e))
        return False


# ─────────────────────────────────────────────────────────────
# Namespace Helpers
# ─────────────────────────────────────────────────────────────
def _get_ns(name):
    """
    'refNS:sub:jnt_01' → 'refNS:sub'
    'jnt_01'           → ''
    """
    if ":" not in name:
        return ""
    return name.rsplit(":", 1)[0]


def _strip_ns(name):
    """
    'refNS:sub:jnt_01' → 'jnt_01'
    'jnt_01'           → 'jnt_01'
    """
    return name.rsplit(":", 1)[-1]


def _replace_ns(name, old_ns, new_ns):
    """
    old_ns='refNS', new_ns='charA'
      'refNS:jnt_01'        → 'charA:jnt_01'
      'refNS:sub:jnt_01'    → 'charA:sub:jnt_01'  (최상위 NS만 교체)
      'other:jnt_01'        → 'other:jnt_01'       (무관한 NS는 유지)
    new_ns='' 이면 해당 NS 제거 (strip).
    """
    if ":" not in name:
        return name
    parts = name.split(":", 1)
    if parts[0] != old_ns:
        return name
    rest = parts[1]
    return (new_ns + ":" + rest) if new_ns else rest


def _collect_ns_from_data(data):
    """data['parts'] 내 모든 오브젝트의 최상위 namespace를 수집. '' 는 제외."""
    ns_set = set()
    for objs in data.get("parts", {}).values():
        for obj in objs:
            ns = _get_ns(obj).split(":")[0] if ":" in obj else ""
            if ns:
                ns_set.add(ns)
    return sorted(ns_set)


# ─────────────────────────────────────────────────────────────
# UI Class
# ─────────────────────────────────────────────────────────────
class FitChainsConfigEditor:

    def __init__(self):
        self._data        = {"parts": {}}   # 현재 로드된 데이터
        self._json_path   = _DEFAULT_JSON
        self._dirty       = False           # 미저장 변경 여부
        self._sel_part    = None            # 리스트에서 선택된 part 이름

        # UI 컨트롤 레퍼런스
        self._wf_path         = None   # textField  – 파일 경로
        self._tsl_parts       = None   # textScrollList – parts 목록
        self._tsl_objects     = None   # textScrollList – 선택 part의 오브젝트 목록
        self._tf_part_name    = None   # textField  – 새 part 이름 입력
        self._tsl_sel_objects = None   # textScrollList – 현재 마야 선택 오브젝트
        self._btn_save        = None   # Save 버튼
        # Namespace
        self._tsl_scene_ns    = None   # textScrollList – 씬 namespace 목록
        self._tsl_json_ns     = None   # textScrollList – JSON namespace 목록
        self._tf_remap_from   = None   # textField  – remap 원본 ns
        self._tf_remap_to     = None   # textField  – remap 대상 ns
        self._cb_strip_on_reg = None   # checkBox   – 등록 시 ns 제거

    # ── UI 빌드 ──────────────────────────────────────────────
    def build(self):
        if cmds.window(_WIN_ID, exists=True):
            cmds.deleteUI(_WIN_ID)

        win = cmds.window(
            _WIN_ID,
            title="Fit Chains Config Editor",
            widthHeight=(560, 720),
            sizeable=True,
            mxb=True,
        )

        root = cmds.columnLayout(adjustableColumn=True, rowSpacing=0, parent=win)

        # ── 1) 파일 경로 ───────────────────────────────────
        cmds.frameLayout(
            label="  JSON File",
            collapsable=False,
            marginWidth=6,
            marginHeight=6,
            parent=root,
        )
        cmds.columnLayout(adjustableColumn=True, rowSpacing=4)

        cmds.rowLayout(numberOfColumns=3, columnWidth3=(400, 60, 60),
                       adjustableColumn=1, columnAttach3=("both","both","both"),
                       columnOffset3=(4, 2, 2))
        self._wf_path = cmds.textField(text=self._json_path,
                                       placeholderText="fit_chains_config.json 경로",
                                       changeCommand=self._on_path_changed)
        cmds.button(label="Browse", command=self._browse_json)
        cmds.button(label="Load",   command=self._load_from_ui_path,
                    backgroundColor=(0.3, 0.5, 0.3))
        cmds.setParent("..")   # rowLayout

        cmds.setParent("..")   # columnLayout
        cmds.setParent("..")   # frameLayout

        # ── 2) 등록 패널 ────────────────────────────────────
        cmds.frameLayout(
            label="  Register New Part",
            collapsable=True,
            collapse=False,
            marginWidth=6,
            marginHeight=6,
            parent=root,
        )
        reg_col = cmds.columnLayout(adjustableColumn=True, rowSpacing=4)

        # Part Name 입력
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 200),
                       adjustableColumn=2,
                       columnAttach2=("both","both"), columnOffset2=(0,4))
        cmds.text(label="Part Name :", align="right")
        self._tf_part_name = cmds.textField(placeholderText="예) arm_L  /  spine")
        cmds.setParent("..")

        # 선택 오브젝트 표시
        cmds.text(label="Selected Objects (Maya viewport selection):",
                  align="left", font="smallBoldLabelFont")

        self._tsl_sel_objects = cmds.textScrollList(
            numberOfRows=5,
            allowMultiSelection=True,
            deleteKeyCommand=self._remove_sel_object,
        )

        cmds.rowLayout(numberOfColumns=2, columnWidth2=(280, 260),
                       adjustableColumn=1,
                       columnAttach2=("both","both"), columnOffset2=(0,4))
        cmds.button(label="Get Selection from Maya",
                    command=self._get_maya_selection,
                    backgroundColor=(0.35, 0.45, 0.6))
        cmds.button(label="Clear",
                    command=self._clear_sel_objects)
        cmds.setParent("..")

        cmds.separator(height=6, style="in")

        cmds.button(
            label="  Register Part  ",
            height=30,
            command=self._register_part,
            backgroundColor=(0.25, 0.6, 0.35),
        )

        # Strip NS 체크박스 (등록 시 자동 제거)
        cmds.separator(height=4, style="none")
        self._cb_strip_on_reg = cmds.checkBox(
            label="Strip Namespace on Register",
            value=True,
            annotation="오브젝트를 등록할 때 namespace를 자동으로 제거합니다",
        )

        cmds.setParent(reg_col)
        cmds.setParent("..")   # frameLayout

        # ── 3) Namespace Detector ─────────────────────────────
        cmds.frameLayout(
            label="  Namespace Detector",
            collapsable=True,
            collapse=False,
            marginWidth=6,
            marginHeight=6,
            parent=root,
        )
        ns_col = cmds.columnLayout(adjustableColumn=True, rowSpacing=4)

        # 상단: Scene NS / JSON NS 나란히
        ns_pane = cmds.paneLayout(configuration="vertical2",
                                  paneSize=[(1, 50, 100), (2, 50, 100)])

        # 왼쪽 – Scene Namespaces
        cmds.columnLayout(adjustableColumn=True, rowSpacing=2, parent=ns_pane)
        cmds.text(label="Scene Namespaces", font="boldLabelFont",
                  align="center", height=18)
        self._tsl_scene_ns = cmds.textScrollList(
            numberOfRows=5,
            allowMultiSelection=False,
            selectCommand=self._on_scene_ns_selected,
        )
        cmds.button(label="Detect Scene NS",
                    command=self._detect_scene_namespaces,
                    backgroundColor=(0.35, 0.45, 0.55))
        cmds.setParent("..")

        # 오른쪽 – JSON Namespaces
        cmds.columnLayout(adjustableColumn=True, rowSpacing=2, parent=ns_pane)
        cmds.text(label="JSON Namespaces", font="boldLabelFont",
                  align="center", height=18)
        self._tsl_json_ns = cmds.textScrollList(
            numberOfRows=5,
            allowMultiSelection=False,
            selectCommand=self._on_json_ns_selected,
        )
        cmds.button(label="Refresh JSON NS",
                    command=self._detect_json_namespaces,
                    backgroundColor=(0.45, 0.4, 0.3))
        cmds.setParent("..")

        cmds.setParent(ns_col)

        cmds.separator(height=6, style="in")

        # Remap 행
        cmds.text(label="Remap Namespace  ( JSON 내 오브젝트 이름 일괄 치환 )",
                  align="left", font="smallBoldLabelFont")
        cmds.rowLayout(numberOfColumns=5,
                       columnWidth5=(50, 160, 30, 160, 80),
                       adjustableColumn=4,
                       columnAttach5=("both","both","both","both","both"),
                       columnOffset5=(0, 2, 2, 2, 2))
        cmds.text(label="From :", align="right")
        self._tf_remap_from = cmds.textField(placeholderText="기존 NS  (예: refNS)")
        cmds.text(label=" →", align="center")
        self._tf_remap_to   = cmds.textField(placeholderText="새 NS  (빈칸=제거)")
        cmds.button(label="Remap",
                    command=self._remap_namespace,
                    backgroundColor=(0.5, 0.4, 0.25))
        cmds.setParent("..")

        cmds.separator(height=4, style="none")

        # Strip All 버튼
        cmds.rowLayout(numberOfColumns=2,
                       columnWidth2=(280, 260), adjustableColumn=1,
                       columnAttach2=("both","both"), columnOffset2=(0, 4))
        cmds.button(label="Strip ALL Namespaces from JSON",
                    command=self._strip_all_ns_from_json,
                    backgroundColor=(0.55, 0.3, 0.25))
        cmds.button(label="Apply NS to JSON Objects",
                    command=self._apply_ns_to_json,
                    backgroundColor=(0.3, 0.45, 0.35))
        cmds.setParent("..")

        cmds.setParent(ns_col)
        cmds.setParent("..")   # frameLayout

        # ── 5) Parts 목록 / 오브젝트 편집 ───────────────────
        cmds.frameLayout(
            label="  Parts List",
            collapsable=True,
            collapse=False,
            marginWidth=6,
            marginHeight=6,
            parent=root,
        )
        list_col = cmds.columnLayout(adjustableColumn=True, rowSpacing=4)

        # 좌: parts 리스트 / 우: objects 리스트 (formLayout으로 나란히)
        pane = cmds.paneLayout(configuration="vertical2",
                               paneSize=[(1, 42, 100), (2, 58, 100)])

        # 왼쪽 – Parts
        left_col = cmds.columnLayout(adjustableColumn=True, rowSpacing=2, parent=pane)
        cmds.text(label="Parts", font="boldLabelFont", align="center", height=20)
        self._tsl_parts = cmds.textScrollList(
            numberOfRows=14,
            allowMultiSelection=False,
            selectCommand=self._on_part_selected,
            deleteKeyCommand=self._delete_selected_part,
        )
        cmds.rowLayout(numberOfColumns=2,
                       columnWidth2=(100, 100), adjustableColumn=1,
                       columnAttach2=("both","both"), columnOffset2=(0,2),
                       parent=left_col)
        cmds.button(label="Rename", command=self._rename_part,
                    backgroundColor=(0.5, 0.45, 0.25))
        cmds.button(label="Delete", command=self._delete_selected_part,
                    backgroundColor=(0.6, 0.25, 0.25))
        cmds.setParent("..")  # rowLayout
        cmds.setParent("..")  # left_col

        # 오른쪽 – Objects
        right_col = cmds.columnLayout(adjustableColumn=True, rowSpacing=2, parent=pane)
        cmds.text(label="Objects  (selected part)", font="boldLabelFont",
                  align="center", height=20)
        self._tsl_objects = cmds.textScrollList(
            numberOfRows=14,
            allowMultiSelection=True,
            deleteKeyCommand=self._remove_object_from_part,
        )
        cmds.rowLayout(numberOfColumns=3,
                       columnWidth3=(100, 100, 100), adjustableColumn=2,
                       columnAttach3=("both","both","both"), columnOffset3=(0,2,2),
                       parent=right_col)
        cmds.button(label="+ Add Sel",    command=self._add_objects_to_part,
                    backgroundColor=(0.3, 0.5, 0.4))
        cmds.button(label="Select",       command=self._select_objects_in_maya,
                    backgroundColor=(0.35, 0.45, 0.6))
        cmds.button(label="Remove",       command=self._remove_object_from_part,
                    backgroundColor=(0.6, 0.25, 0.25))
        cmds.setParent("..")  # rowLayout
        cmds.setParent("..")  # right_col

        cmds.setParent(list_col)
        cmds.setParent("..")  # frameLayout

        # ── 6) 하단 Save 버튼 ───────────────────────────────
        cmds.separator(height=8, style="in", parent=root)
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(180, 190, 170),
                       adjustableColumn=2,
                       columnAttach3=("both","both","both"), columnOffset3=(6,4,6),
                       parent=root)
        cmds.button(label="Reload JSON",    command=self._load_from_ui_path,
                    backgroundColor=(0.3, 0.3, 0.3))
        self._btn_save = cmds.button(
            label="Save JSON",
            height=34,
            command=self._save,
            backgroundColor=(0.25, 0.55, 0.75),
        )
        cmds.button(label="Save As...",     command=self._save_as,
                    backgroundColor=(0.25, 0.4, 0.6))
        cmds.setParent("..")

        cmds.separator(height=8, style="none", parent=root)

        cmds.showWindow(win)

        # 기본 JSON 로드 시도
        if os.path.exists(self._json_path):
            self._load_data(self._json_path)

    # ── 파일 경로 콜백 ───────────────────────────────────────
    def _on_path_changed(self, *_):
        self._json_path = cmds.textField(self._wf_path, q=True, text=True).strip()

    def _browse_json(self, *_):
        start = os.path.dirname(self._json_path) if self._json_path else _TOOL_DIR
        result = cmds.fileDialog2(
            fileFilter="JSON Files (*.json);;All Files (*.*)",
            dialogStyle=2,
            fileMode=0,       # 0 = 새 파일 or 기존 파일 (저장 형식)
            startingDirectory=start,
        )
        if not result:
            return
        path = result[0]
        self._json_path = path
        cmds.textField(self._wf_path, edit=True, text=path)
        if os.path.exists(path):
            self._load_data(path)

    def _load_from_ui_path(self, *_):
        path = cmds.textField(self._wf_path, q=True, text=True).strip()
        if not path:
            cmds.warning("fit_chains_config_editor: 파일 경로를 입력하세요.")
            return
        self._json_path = path
        self._load_data(path)

    # ── 데이터 로드 / UI 갱신 ────────────────────────────────
    def _load_data(self, path):
        self._data      = _load_json(path)
        self._dirty     = False
        self._sel_part  = None
        self._refresh_parts_list()
        self._refresh_objects_list()
        self._detect_json_namespaces()
        cmds.textField(self._wf_path, edit=True, text=path)
        print("fit_chains_config_editor: loaded <- " + path)

    def _refresh_parts_list(self):
        cmds.textScrollList(self._tsl_parts, edit=True, removeAll=True)
        for name in sorted(self._data["parts"].keys()):
            count = len(self._data["parts"][name])
            cmds.textScrollList(self._tsl_parts, edit=True,
                                append="{} ({})".format(name, count))

    def _refresh_objects_list(self):
        cmds.textScrollList(self._tsl_objects, edit=True, removeAll=True)
        if self._sel_part and self._sel_part in self._data["parts"]:
            for obj in self._data["parts"][self._sel_part]:
                cmds.textScrollList(self._tsl_objects, edit=True, append=obj)

    # parts 리스트 선택 → 오브젝트 패널 갱신
    def _on_part_selected(self, *_):
        sel = cmds.textScrollList(self._tsl_parts, q=True, selectItem=True)
        if not sel:
            self._sel_part = None
            self._refresh_objects_list()
            return
        # 표시 형식 "arm_L (3)" → "arm_L"
        raw = sel[0]
        self._sel_part = raw.rsplit(" (", 1)[0]
        self._refresh_objects_list()

    def _current_part_name_from_label(self, label):
        """'arm_L (3)' → 'arm_L'"""
        return label.rsplit(" (", 1)[0]

    # ── 선택 오브젝트 패널 ────────────────────────────────────
    def _get_maya_selection(self, *_):
        sel = cmds.ls(selection=True, long=False) or []
        if not sel:
            cmds.warning("fit_chains_config_editor: Maya에서 오브젝트를 선택하세요.")
            return
        strip = cmds.checkBox(self._cb_strip_on_reg, q=True, value=True)
        existing = cmds.textScrollList(self._tsl_sel_objects, q=True, allItems=True) or []
        for obj in sel:
            name = _strip_ns(obj) if strip else obj
            if name not in existing:
                cmds.textScrollList(self._tsl_sel_objects, edit=True, append=name)

    def _clear_sel_objects(self, *_):
        cmds.textScrollList(self._tsl_sel_objects, edit=True, removeAll=True)

    def _remove_sel_object(self, *_):
        sel = cmds.textScrollList(self._tsl_sel_objects, q=True, selectItem=True) or []
        for item in sel:
            cmds.textScrollList(self._tsl_sel_objects, edit=True, removeItem=item)

    # ── Register Part ─────────────────────────────────────────
    def _register_part(self, *_):
        part_name = cmds.textField(self._tf_part_name, q=True, text=True).strip()
        if not part_name:
            cmds.warning("fit_chains_config_editor: Part Name을 입력하세요.")
            return

        objects = cmds.textScrollList(self._tsl_sel_objects, q=True, allItems=True) or []

        if part_name in self._data["parts"]:
            # 기존 파트에 병합 (중복 제외)
            existing = self._data["parts"][part_name]
            merged   = list(existing)
            for o in objects:
                if o not in merged:
                    merged.append(o)
            self._data["parts"][part_name] = merged
            action = "updated"
        else:
            self._data["parts"][part_name] = list(objects)
            action = "registered"

        self._dirty = True
        self._refresh_parts_list()

        # 등록한 part를 선택 상태로
        self._sel_part = part_name
        for i, label in enumerate(
            cmds.textScrollList(self._tsl_parts, q=True, allItems=True) or []
        ):
            if self._current_part_name_from_label(label) == part_name:
                cmds.textScrollList(self._tsl_parts, edit=True, selectIndexedItem=i + 1)
                break
        self._refresh_objects_list()

        # 입력 필드 초기화
        cmds.textField(self._tf_part_name, edit=True, text="")
        cmds.textScrollList(self._tsl_sel_objects, edit=True, removeAll=True)

        print("fit_chains_config_editor: part '{}' {} ({} objects)".format(
            part_name, action, len(self._data["parts"][part_name])))

    # ── Parts 조작 ───────────────────────────────────────────
    def _delete_selected_part(self, *_):
        if not self._sel_part:
            return
        confirm = cmds.confirmDialog(
            title="Delete Part",
            message="'{}' 를 삭제하시겠습니까?".format(self._sel_part),
            button=["Delete", "Cancel"],
            defaultButton="Delete",
            cancelButton="Cancel",
            dismissString="Cancel",
        )
        if confirm != "Delete":
            return
        del self._data["parts"][self._sel_part]
        self._dirty    = True
        self._sel_part = None
        self._refresh_parts_list()
        self._refresh_objects_list()

    def _rename_part(self, *_):
        if not self._sel_part:
            cmds.warning("fit_chains_config_editor: Part를 선택하세요.")
            return
        result = cmds.promptDialog(
            title="Rename Part",
            message="새 이름:",
            text=self._sel_part,
            button=["OK", "Cancel"],
            defaultButton="OK",
            cancelButton="Cancel",
            dismissString="Cancel",
        )
        if result != "OK":
            return
        new_name = cmds.promptDialog(q=True, text=True).strip()
        if not new_name or new_name == self._sel_part:
            return
        if new_name in self._data["parts"]:
            cmds.warning("fit_chains_config_editor: '{}' 이름이 이미 존재합니다.".format(new_name))
            return

        # 순서 유지하며 key 교체
        new_parts = {}
        for k, v in self._data["parts"].items():
            new_parts[new_name if k == self._sel_part else k] = v
        self._data["parts"] = new_parts
        self._dirty    = True
        self._sel_part = new_name
        self._refresh_parts_list()

        # 선택 복원
        for i, label in enumerate(
            cmds.textScrollList(self._tsl_parts, q=True, allItems=True) or []
        ):
            if self._current_part_name_from_label(label) == new_name:
                cmds.textScrollList(self._tsl_parts, edit=True, selectIndexedItem=i + 1)
                break
        self._refresh_objects_list()

    # ── Objects 패널 조작 ────────────────────────────────────
    def _add_objects_to_part(self, *_):
        if not self._sel_part:
            cmds.warning("fit_chains_config_editor: 먼저 Part를 선택하세요.")
            return
        sel = cmds.ls(selection=True, long=False) or []
        if not sel:
            cmds.warning("fit_chains_config_editor: Maya에서 오브젝트를 선택하세요.")
            return
        existing = self._data["parts"].get(self._sel_part, [])
        added = 0
        for obj in sel:
            if obj not in existing:
                existing.append(obj)
                added += 1
        self._data["parts"][self._sel_part] = existing
        self._dirty = True
        self._refresh_objects_list()
        self._refresh_parts_list()
        # 선택 복원
        for i, label in enumerate(
            cmds.textScrollList(self._tsl_parts, q=True, allItems=True) or []
        ):
            if self._current_part_name_from_label(label) == self._sel_part:
                cmds.textScrollList(self._tsl_parts, edit=True, selectIndexedItem=i + 1)
                break
        print("fit_chains_config_editor: {} objects added to '{}'.".format(added, self._sel_part))

    def _remove_object_from_part(self, *_):
        if not self._sel_part:
            return
        sel_objs = cmds.textScrollList(self._tsl_objects, q=True, selectItem=True) or []
        if not sel_objs:
            return
        objs = self._data["parts"].get(self._sel_part, [])
        for o in sel_objs:
            if o in objs:
                objs.remove(o)
        self._data["parts"][self._sel_part] = objs
        self._dirty = True
        self._refresh_objects_list()
        self._refresh_parts_list()
        # 선택 복원
        for i, label in enumerate(
            cmds.textScrollList(self._tsl_parts, q=True, allItems=True) or []
        ):
            if self._current_part_name_from_label(label) == self._sel_part:
                cmds.textScrollList(self._tsl_parts, edit=True, selectIndexedItem=i + 1)
                break

    def _select_objects_in_maya(self, *_):
        """Objects 리스트에서 선택한 항목을 Maya 뷰포트에서 선택."""
        sel_objs = cmds.textScrollList(self._tsl_objects, q=True, selectItem=True) or []
        if not sel_objs:
            sel_objs = cmds.textScrollList(self._tsl_objects, q=True, allItems=True) or []
        if not sel_objs:
            return
        existing = [o for o in sel_objs if cmds.objExists(o)]
        missing  = [o for o in sel_objs if not cmds.objExists(o)]
        if missing:
            cmds.warning("fit_chains_config_editor: 씬에 없는 오브젝트: " + ", ".join(missing))
        if existing:
            cmds.select(existing, replace=True)

    # ── 저장 ─────────────────────────────────────────────────
    def _save(self, *_):
        path = cmds.textField(self._wf_path, q=True, text=True).strip()
        if not path:
            cmds.warning("fit_chains_config_editor: 파일 경로를 입력하세요.")
            return
        self._json_path = path
        if _save_json(path, self._data):
            self._dirty = False
            print("fit_chains_config_editor: saved -> " + path)
            cmds.inViewMessage(
                amg="<hl>Saved:</hl> " + os.path.basename(path),
                pos="topCenter", fade=True, fst=800,
            )

    def _save_as(self, *_):
        start = os.path.dirname(self._json_path) if self._json_path else _TOOL_DIR
        result = cmds.fileDialog2(
            fileFilter="JSON Files (*.json);;All Files (*.*)",
            dialogStyle=2,
            fileMode=0,
            startingDirectory=start,
        )
        if not result:
            return
        path = result[0]
        if not path.lower().endswith(".json"):
            path += ".json"
        self._json_path = path
        cmds.textField(self._wf_path, edit=True, text=path)
        self._save()

    # ── Namespace ─────────────────────────────────────────────
    def _detect_scene_namespaces(self, *_):
        """현재 Maya 씬의 모든 namespace를 수집하여 목록에 표시."""
        try:
            all_ns = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
        except Exception:
            all_ns = []
        # 기본 네임스페이스 제외
        exclude = {"UI", "shared"}
        ns_list = sorted(ns for ns in all_ns if ns not in exclude)

        cmds.textScrollList(self._tsl_scene_ns, edit=True, removeAll=True)
        if ns_list:
            for ns in ns_list:
                cmds.textScrollList(self._tsl_scene_ns, edit=True, append=ns)
        else:
            cmds.textScrollList(self._tsl_scene_ns, edit=True,
                                append="(namespace 없음)")
        print("fit_chains_config_editor: scene namespaces: " + str(ns_list))

    def _detect_json_namespaces(self, *_):
        """JSON 데이터 내 오브젝트들의 namespace를 파싱하여 목록에 표시."""
        if self._tsl_json_ns is None:
            return
        ns_list = _collect_ns_from_data(self._data)

        cmds.textScrollList(self._tsl_json_ns, edit=True, removeAll=True)
        if ns_list:
            for ns in ns_list:
                # 해당 namespace를 가진 오브젝트 수 표시
                count = sum(
                    1 for objs in self._data["parts"].values()
                    for obj in objs
                    if obj.split(":")[0] == ns and ":" in obj
                )
                cmds.textScrollList(self._tsl_json_ns, edit=True,
                                    append="{} ({} objects)".format(ns, count))
        else:
            cmds.textScrollList(self._tsl_json_ns, edit=True,
                                append="(namespace 없음)")

    def _on_scene_ns_selected(self, *_):
        """Scene NS 클릭 → From 필드에 자동 입력."""
        sel = cmds.textScrollList(self._tsl_scene_ns, q=True, selectItem=True)
        if not sel or sel[0] == "(namespace 없음)":
            return
        cmds.textField(self._tf_remap_from, edit=True, text=sel[0])

    def _on_json_ns_selected(self, *_):
        """JSON NS 클릭 → From 필드에 자동 입력."""
        sel = cmds.textScrollList(self._tsl_json_ns, q=True, selectItem=True)
        if not sel or sel[0] == "(namespace 없음)":
            return
        ns = sel[0].rsplit(" (", 1)[0]
        cmds.textField(self._tf_remap_from, edit=True, text=ns)

    def _remap_namespace(self, *_):
        """JSON 내 오브젝트의 old_ns를 new_ns로 일괄 교체."""
        old_ns = cmds.textField(self._tf_remap_from, q=True, text=True).strip()
        new_ns = cmds.textField(self._tf_remap_to,   q=True, text=True).strip()

        if not old_ns:
            cmds.warning("fit_chains_config_editor: From 필드에 교체할 namespace를 입력하세요.")
            return

        changed = 0
        for part, objs in self._data["parts"].items():
            new_objs = []
            for obj in objs:
                replaced = _replace_ns(obj, old_ns, new_ns)
                if replaced != obj:
                    changed += 1
                new_objs.append(replaced)
            self._data["parts"][part] = new_objs

        if changed:
            self._dirty = True
            self._refresh_objects_list()
            self._detect_json_namespaces()
            action = "→ '{}'".format(new_ns) if new_ns else "(제거됨)"
            print("fit_chains_config_editor: '{}' {} – {} objects 변경.".format(
                old_ns, action, changed))
            cmds.inViewMessage(
                amg="NS Remap: <hl>{}</hl> {} ({} changed)".format(
                    old_ns, action, changed),
                pos="topCenter", fade=True, fst=900,
            )
        else:
            cmds.warning(
                "fit_chains_config_editor: '{}' namespace를 가진 오브젝트가 없습니다.".format(old_ns))

    def _strip_all_ns_from_json(self, *_):
        """JSON 내 모든 오브젝트의 namespace를 제거."""
        ns_list = _collect_ns_from_data(self._data)
        if not ns_list:
            cmds.warning("fit_chains_config_editor: JSON에 namespace가 없습니다.")
            return

        confirm = cmds.confirmDialog(
            title="Strip All Namespaces",
            message="JSON 내 모든 오브젝트에서 namespace를 제거합니다.\n"
                    "감지된 NS: {}\n\n계속하시겠습니까?".format(", ".join(ns_list)),
            button=["Strip", "Cancel"],
            defaultButton="Strip",
            cancelButton="Cancel",
            dismissString="Cancel",
        )
        if confirm != "Strip":
            return

        changed = 0
        for part, objs in self._data["parts"].items():
            new_objs = []
            for obj in objs:
                stripped = _strip_ns(obj)
                if stripped != obj:
                    changed += 1
                new_objs.append(stripped)
            self._data["parts"][part] = new_objs

        self._dirty = True
        self._refresh_objects_list()
        self._detect_json_namespaces()
        print("fit_chains_config_editor: {} objects에서 namespace 제거 완료.".format(changed))
        cmds.inViewMessage(
            amg="Strip NS 완료: <hl>{} objects</hl> 변경".format(changed),
            pos="topCenter", fade=True, fst=900,
        )

    def _apply_ns_to_json(self, *_):
        """
        To 필드에 입력된 namespace를 JSON 내 namespace 없는 오브젝트에 추가.
        이미 namespace가 있는 오브젝트는 건드리지 않는다.
        """
        new_ns = cmds.textField(self._tf_remap_to, q=True, text=True).strip()
        if not new_ns:
            cmds.warning("fit_chains_config_editor: To 필드에 적용할 namespace를 입력하세요.")
            return

        changed = 0
        for part, objs in self._data["parts"].items():
            new_objs = []
            for obj in objs:
                if ":" not in obj:
                    new_objs.append(new_ns + ":" + obj)
                    changed += 1
                else:
                    new_objs.append(obj)
            self._data["parts"][part] = new_objs

        if changed:
            self._dirty = True
            self._refresh_objects_list()
            self._detect_json_namespaces()
            print("fit_chains_config_editor: '{}:' namespace 적용 – {} objects 변경.".format(
                new_ns, changed))
            cmds.inViewMessage(
                amg="NS Apply: <hl>{}:</hl> {} objects".format(new_ns, changed),
                pos="topCenter", fade=True, fst=900,
            )
        else:
            cmds.warning(
                "fit_chains_config_editor: namespace 없는 오브젝트가 없거나 이미 모두 적용되었습니다.")


# ─────────────────────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────────────────────
_editor_instance = None


def show():
    global _editor_instance
    _editor_instance = FitChainsConfigEditor()
    _editor_instance.build()


if __name__ == "__main__":
    show()
