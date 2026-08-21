"""
Namespace Replace Selector Tool for Maya
현재 선택한 오브젝트의 네임스페이스를 찾아서, 다른 네임스페이스로 치환했을 때
존재하는 동일 이름의 오브젝트를 찾아 선택해주는 UI 툴.

예) "Floyd_v001:hand_ctrl" 을 선택한 상태에서 대상 네임스페이스를
"Floyd_v002" 로 지정하면 "Floyd_v002:hand_ctrl" 을 찾아서 선택한다.

사용법:
    # 첫 실행
    import namespace_replace_selector_tool as ns_tool
    ns_tool.show()

    # 모듈 수정 후 리로드
    import importlib
    import namespace_replace_selector_tool as ns_tool
    importlib.reload(ns_tool)
    ns_tool.show()
"""

import sys
import importlib

import maya.cmds as cmds


def split_namespace(short_name):
    """짧은 이름을 (namespace, base_name) 으로 분리. namespace 는 콜론 제외."""
    if ":" in short_name:
        ns, base = short_name.rsplit(":", 1)
        return ns, base
    return "", short_name


def get_object_namespace(node):
    """노드(long/short 무관)의 네임스페이스를 반환. 없으면 빈 문자열."""
    short = node.split("|")[-1]
    ns, _base = split_namespace(short)
    return ns


def _replace_namespace_in_path(full_path, source_ns, target_ns):
    """full_path 의 각 계층 이름 중 source_ns 와 일치하는 부분만 target_ns 로 치환."""
    segments = full_path.split("|")
    new_segments = []
    for seg in segments:
        if not seg:
            new_segments.append(seg)
            continue
        ns, base = split_namespace(seg)
        if ns == source_ns:
            new_seg = "{}:{}".format(target_ns, base) if target_ns else base
        else:
            new_seg = seg
        new_segments.append(new_seg)
    return "|".join(new_segments)


def find_namespace_replaced(selection, target_namespace):
    """
    selection 의 각 오브젝트에 대해 자신의 네임스페이스를 target_namespace 로
    치환했을 때 존재하는 오브젝트를 찾는다.

    Returns:
        dict(mapping, found, missing, source_namespaces)
        - mapping: {원본 long name: 치환된 long name}
        - found: 실제 씬에 존재해서 선택 가능한 치환된 long name 리스트
        - missing: 치환 결과를 찾지 못한 원본 오브젝트 리스트
        - source_namespaces: 선택한 오브젝트들에서 발견된 네임스페이스 집합
    """
    mapping = {}
    found = []
    missing = []
    source_namespaces = set()

    for node in selection:
        short = node.split("|")[-1]
        src_ns, _base = split_namespace(short)
        source_namespaces.add(src_ns)

        new_path = _replace_namespace_in_path(node, src_ns, target_namespace)

        if new_path == node or not cmds.objExists(new_path):
            missing.append(node)
            continue

        resolved = cmds.ls(new_path, long=True)[0]
        mapping[node] = resolved
        found.append(resolved)

    return {
        "mapping": mapping,
        "found": found,
        "missing": missing,
        "source_namespaces": source_namespaces,
    }


class NamespaceReplaceSelectorTool:
    """선택한 오브젝트의 네임스페이스를 다른 네임스페이스로 치환해 선택하는 UI."""

    DIRECT_INPUT_LABEL = "(직접 입력)"

    def __init__(self):
        self.window_name = "namespaceReplaceSelectorWindow"
        self.selected_list = None
        self.target_menu = None
        self.target_field = None
        self.report_field = None
        self.captured_selection = []

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def create_ui(self):
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)

        window = cmds.window(
            self.window_name,
            title="Namespace Replace Selector",
            widthHeight=(460, 560),
            sizeable=True,
        )

        cmds.columnLayout(adjustableColumn=True, rowSpacing=5, columnAttach=("both", 15))

        cmds.separator(height=15, style="none")
        cmds.text(label="Namespace Replace Selector", font="boldLabelFont", height=28)
        cmds.text(
            label=(
                "선택한 오브젝트의 네임스페이스를 찾아서, 대상 네임스페이스로\n"
                "치환했을 때 존재하는 동일 이름의 오브젝트를 찾아 선택합니다."
            ),
            align="left",
            font="smallPlainLabelFont",
        )
        cmds.separator(height=10, style="in")

        # ── 선택한 오브젝트 ──────────────────────────────────────
        cmds.frameLayout(
            label="선택한 오브젝트", collapsable=False, marginWidth=5, marginHeight=5
        )
        cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
        self.selected_list = cmds.textScrollList(
            numberOfRows=8, allowMultiSelection=False, height=140
        )
        cmds.button(
            label="선택 새로고침 (현재 뷰포트 선택 가져오기)",
            command=self.refresh_selected_list,
            backgroundColor=(0.4, 0.4, 0.5),
        )
        cmds.setParent("..")
        cmds.setParent("..")

        cmds.separator(height=8, style="none")

        # ── 대상 네임스페이스 ────────────────────────────────────
        cmds.frameLayout(
            label="대상 네임스페이스", collapsable=False, marginWidth=5, marginHeight=5
        )
        cmds.columnLayout(adjustableColumn=True, rowSpacing=4)

        cmds.rowLayout(
            numberOfColumns=2,
            adjustableColumn=2,
            columnAttach=[(1, "both", 0), (2, "both", 5)],
        )
        cmds.text(label="씬 네임스페이스", align="left")
        self.target_menu = cmds.optionMenu(changeCommand=self.on_menu_changed)
        cmds.setParent("..")

        self.target_field = cmds.textField(
            placeholderText="콜론 없이 입력 (예: Floyd_v002). 빈 값이면 네임스페이스 제거된 오브젝트를 찾음",
        )

        cmds.button(
            label="네임스페이스 목록 새로고침",
            command=self.refresh_namespace_menu,
            backgroundColor=(0.4, 0.4, 0.5),
        )
        cmds.setParent("..")
        cmds.setParent("..")

        cmds.separator(height=8, style="none")

        cmds.button(
            label="치환된 오브젝트 선택",
            command=self.on_select_replaced,
            backgroundColor=(0.3, 0.55, 0.3),
            height=32,
        )

        cmds.separator(height=10, style="none")

        cmds.text(label="리포트", align="left", font="plainLabelFont")
        self.report_field = cmds.scrollField(editable=False, wordWrap=False, height=200)

        cmds.separator(height=15, style="none")

        cmds.showWindow(window)

        # 초기 데이터 로드
        self.refresh_selected_list()
        self.refresh_namespace_menu()

    # ------------------------------------------------------------------
    # 선택 오브젝트
    # ------------------------------------------------------------------
    def refresh_selected_list(self, *args):
        """현재 뷰포트 선택을 캡처해서 리스트에 표시."""
        cmds.textScrollList(self.selected_list, edit=True, removeAll=True)
        self.captured_selection = cmds.ls(selection=True, long=True) or []

        if not self.captured_selection:
            cmds.textScrollList(self.selected_list, edit=True, append="(선택된 오브젝트 없음)")
            return

        for node in self.captured_selection:
            short = node.split("|")[-1]
            ns, base = split_namespace(short)
            label = "{}   [ns: {}]".format(base, ns if ns else "(없음)")
            cmds.textScrollList(self.selected_list, edit=True, append=label)

    # ------------------------------------------------------------------
    # 대상 네임스페이스
    # ------------------------------------------------------------------
    def refresh_namespace_menu(self, *args):
        for item in cmds.optionMenu(self.target_menu, query=True, itemListLong=True) or []:
            cmds.deleteUI(item)

        cmds.menuItem(parent=self.target_menu, label=self.DIRECT_INPUT_LABEL)

        all_namespaces = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
        excluded = {"UI", "shared"}
        namespaces = sorted(ns for ns in all_namespaces if ns not in excluded)

        for ns in namespaces:
            cmds.menuItem(parent=self.target_menu, label=ns)

    def on_menu_changed(self, value):
        if value == self.DIRECT_INPUT_LABEL:
            return
        cmds.textField(self.target_field, edit=True, text=value)

    def _get_target_namespace(self):
        target = cmds.textField(self.target_field, query=True, text=True).strip()
        if target.endswith(":"):
            target = target[:-1]
        return target

    def _require_target_namespace(self, target):
        """빈 값은 허용(네임스페이스 제거). 값이 있으면 씬에 존재하는지 확인."""
        if not target:
            return ""
        if not cmds.namespace(exists=target):
            cmds.confirmDialog(
                title="네임스페이스 없음",
                message="네임스페이스가 존재하지 않습니다: {}".format(target),
                button=["확인"],
            )
            return None
        return target

    # ------------------------------------------------------------------
    # 실행
    # ------------------------------------------------------------------
    def on_select_replaced(self, *args):
        if not self.captured_selection:
            cmds.confirmDialog(
                title="선택 없음",
                message="먼저 오브젝트를 선택하고 [선택 새로고침]을 눌러주세요.",
                button=["확인"],
            )
            return

        target = self._require_target_namespace(self._get_target_namespace())
        if target is None:
            return

        result = find_namespace_replaced(self.captured_selection, target)

        if result["found"]:
            cmds.select(result["found"], replace=True)
        else:
            cmds.select(clear=True)

        self._set_report(self._format_report(target, result))

    def _set_report(self, text):
        cmds.scrollField(self.report_field, edit=True, text=text)

    def _format_report(self, target, result):
        source_ns_display = ", ".join(
            sorted(ns for ns in result["source_namespaces"] if ns)
        ) or "(없음)"

        lines = [
            "원본 네임스페이스 : {}".format(source_ns_display),
            "대상 네임스페이스 : {}".format(target if target else "(없음)"),
            "원본 오브젝트 수  : {}".format(len(self.captured_selection)),
            "치환 성공        : {}".format(len(result["found"])),
            "치환 실패        : {}".format(len(result["missing"])),
        ]

        if result["missing"]:
            lines.append("찾지 못한 오브젝트 ({}):".format(len(result["missing"])))
            for node in result["missing"][:20]:
                lines.append("   - {}".format(node))

        return "\n".join(lines)


def show():
    """UI 표시 함수."""
    tool = NamespaceReplaceSelectorTool()
    tool.create_ui()
    return tool


def reload_and_show():
    """모듈을 다시 로드하고 UI 표시."""
    module_name = __name__
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    return show()


if __name__ == "__main__":
    show()
