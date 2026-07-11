"""
MH Body Match Reference Tool
=============================
mh_body_match_reference.py + mh_body_edit_mode.py 워크플로우를 단계별 버튼으로
실행하는 UI 툴입니다. 각 단계 실행 결과(print 로그)가 화면 리포트에 그대로
누적 표시되므로, 자동화 중간 과정을 그때그때 확인할 수 있습니다.

Body / Head 모두 지원합니다 — Domain 을 선택하면 rl4_node / 기본 DNA 경로 /
skinCluster 탐색 방식(고정 패턴 vs 동적 탐색)이 자동으로 맞춰집니다.

사용법:
    import mh_body_match_reference_tool as mhmrtool
    mhmrtool.show()

    # 모듈 수정 후 리로드
    mhmrtool.reload_and_show()

UI 사용 순서:
    0) Domain(Body/Head) 선택 + 레퍼런스 네임스페이스 입력 (예: Floyd)
       → Source DNA 경로가 자동으로 채워짐 (rl4_node.dnaFilePath 기준)
    1) Enter Edit Mode
    2) Match Primary (Pass A)
    3) Restore Structure
    4) Match Secondary (Pass B)
    5) Verify (검증) — unexpected_primary 가 있으면 원인을 먼저 확인하세요
    6) Bake Rotate → JointOrient
    7) Export DNA (경로 확인 후 확인 대화상자)
    8) Reconnect RL4 (확인 대화상자 — secondary/corrective 조인트는 rl4 재연결 후
       DNA joint-behavior 로 라이브 구동되어 static 값과 달라지는 것이 정상입니다)
"""

import os
import sys
import io
import contextlib
import importlib

import maya.cmds as cmds

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import mh_body_edit_mode as mhem
import mh_body_match_reference as mhmr


DOMAIN_RL4 = {
    "Body": "body_rl4Embedded",
    "Head": "head_rl4Embedded",
}


class MHMatchReferenceTool:
    """레퍼런스 조인트 트랜스폼 → DNA neutral 값 매칭 워크플로우 UI."""

    def __init__(self):
        self.window_name   = "mhMatchReferenceWindow"
        self.domain_menu    = None
        self.namespace_field = None
        self.ns_status_text  = None
        self.input_field     = None
        self.output_field    = None
        self.report_field    = None

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def create_ui(self):
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)

        window = cmds.window(
            self.window_name,
            title="MH Match Reference",
            widthHeight=(480, 760),
            sizeable=True,
        )
        self.build_tab_ui(window)
        cmds.showWindow(window)

    def build_tab_ui(self, parent=None):
        """탭 또는 독립 윈도우에 UI 를 빌드. rig_tool_hub 통합용."""
        scroll = cmds.scrollLayout(childResizable=True, parent=parent) if parent \
            else cmds.scrollLayout(childResizable=True)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5, columnAttach=("both", 15))

        cmds.separator(height=12, style="none")
        cmds.text(label="MH Body/Head Match Reference", font="boldLabelFont", height=26)
        cmds.text(
            label=(
                "레퍼런스 캐릭터의 조인트 트랜스폼으로 MetaHuman DNA neutral 값을\n"
                "맞추는 워크플로우입니다. 각 단계 실행 후 아래 리포트에서 결과를\n"
                "확인하고 다음 단계로 진행하세요."
            ),
            align="left",
            font="smallPlainLabelFont",
        )
        cmds.separator(height=10, style="in")

        # ── Domain 선택 ──────────────────────────────────────────
        cmds.rowLayout(
            numberOfColumns=2, adjustableColumn=2,
            columnAttach=[(1, "both", 0), (2, "both", 5)],
        )
        cmds.text(label="Domain :")
        self.domain_menu = cmds.optionMenu(changeCommand=lambda *_: self._refresh_dna_paths())
        for d in DOMAIN_RL4:
            cmds.menuItem(label=d)
        cmds.setParent("..")

        # ── 네임스페이스 입력 + 존재 확인 ────────────────────────
        cmds.text(label="레퍼런스 네임스페이스", align="left", font="plainLabelFont")
        cmds.rowLayout(
            numberOfColumns=3, adjustableColumn=1,
            columnAttach=[(1, "both", 0), (2, "both", 5), (3, "both", 5)],
        )
        self.namespace_field = cmds.textField(text="Floyd", placeholderText="예: Floyd")
        cmds.button(
            label="선택에서 불러오기",
            command=self.on_load_namespace_from_selection,
            backgroundColor=(0.35, 0.45, 0.55),
        )
        cmds.button(
            label="네임스페이스 확인",
            command=self.on_check_namespace,
            backgroundColor=(0.4, 0.4, 0.5),
        )
        cmds.setParent("..")
        self.ns_status_text = cmds.text(label="", align="left", font="smallPlainLabelFont", height=18)

        cmds.separator(height=8, style="none")

        # ── DNA 경로 ─────────────────────────────────────────────
        cmds.frameLayout(label="  DNA 경로", collapsable=True, collapse=False, marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
        self.input_field = cmds.textFieldButtonGrp(
            label="Source :", buttonLabel="...", columnWidth3=(52, 260, 34),
            adjustableColumn=2,
            buttonCommand=lambda *_: self._browse_file(self.input_field, mode=1, caption="Select Source DNA"),
        )
        self.output_field = cmds.textFieldButtonGrp(
            label="Output :", buttonLabel="...", columnWidth3=(52, 260, 34),
            adjustableColumn=2,
            buttonCommand=lambda *_: self._browse_file(self.output_field, mode=0, caption="Save DNA As"),
        )
        cmds.text(
            label="Domain 변경 시 rl4_node.dnaFilePath 기준으로 자동 채워집니다.",
            align="left", font="smallPlainLabelFont",
        )
        cmds.setParent("..")
        cmds.setParent("..")

        cmds.separator(height=8, style="none")

        # ── Step 1~4 ─────────────────────────────────────────────
        self._build_step(
            "1. Enter Edit Mode",
            "rl4 disconnect → secondary joints unparent+hide → skinCluster envelope=0",
            "Enter Edit Mode", self.on_enter_edit_mode, (0.28, 0.48, 0.32),
        )
        self._build_step(
            "2. Match Primary (Pass A)",
            "primary joint 의 translate/jointOrient 를 레퍼런스 값으로 복사",
            "Match Primary", lambda *_: self.on_match(primary_only=True), (0.28, 0.42, 0.58),
        )
        self._build_step(
            "3. Restore Structure",
            "secondary joints 재parent + correctiveRoot/half local translate 0 스냅",
            "Restore Structure", self.on_restore_structure, (0.52, 0.44, 0.28),
        )
        self._build_step(
            "4. Match Secondary (Pass B)",
            "secondary(twist/corrective 등) joint 를 레퍼런스 값으로 복사",
            "Match Secondary", lambda *_: self.on_match(secondary_only=True), (0.28, 0.42, 0.58),
        )
        self._build_step(
            "5. Verify (검증)",
            "전체 joint 를 레퍼런스와 world 기준으로 비교 — 반드시 확인하세요",
            "Verify", self.on_verify, (0.5, 0.35, 0.5),
        )
        self._build_step(
            "6. Bake Rotate → JointOrient",
            "RL4 reconnect 전 안전장치 (rotate 가 이미 0 이면 보통 no-op)",
            "Bake Rotate", self.on_bake_rotate, (0.4, 0.4, 0.4),
        )

        cmds.button(
            label="7. Export DNA",
            height=30, backgroundColor=(0.52, 0.28, 0.28),
            command=self.on_export_dna,
        )
        cmds.separator(height=4, style="none")
        cmds.button(
            label="8. Reconnect RL4",
            height=30, backgroundColor=(0.55, 0.35, 0.2),
            command=self.on_reconnect_rl4,
        )

        cmds.separator(height=8, style="none")
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnAttach=[(1, "both", 0), (2, "both", 5)])
        cmds.button(
            label="Full Exit (DNA export 없이 원복)",
            height=26, backgroundColor=(0.36, 0.36, 0.36),
            command=lambda *_: self._run_captured(mhem.full_exit),
        )
        cmds.button(
            label="상태 확인",
            height=26, backgroundColor=(0.3, 0.3, 0.3),
            command=lambda *_: self._run_captured(mhem.get_state),
        )
        cmds.setParent("..")

        cmds.separator(height=10, style="none")
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnAttach=[(1, "both", 0), (2, "both", 5)])
        cmds.text(label="리포트 (각 단계 실행 결과가 누적됩니다)", align="left", font="plainLabelFont")
        cmds.button(label="지우기", width=60, command=lambda *_: self._clear_report())
        cmds.setParent("..")
        self.report_field = cmds.scrollField(editable=False, wordWrap=False, height=260)

        cmds.separator(height=12, style="none")

        cmds.setParent("..")  # columnLayout -> scroll
        self._refresh_dna_paths()
        return scroll

    def _build_step(self, title, desc, button_label, command, color):
        cmds.frameLayout(label="  " + title, collapsable=False, marginWidth=5, marginHeight=5)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
        cmds.text(label=desc, align="left", font="smallPlainLabelFont")
        cmds.button(label=button_label, height=28, backgroundColor=color, command=command)
        cmds.setParent("..")
        cmds.setParent("..")

    # ------------------------------------------------------------------
    # 리포트 (stdout 캡처)
    # ------------------------------------------------------------------
    def _append_report(self, text):
        if not text:
            return
        current = cmds.scrollField(self.report_field, query=True, text=True) or ""
        new_text = current + text
        if not new_text.endswith("\n"):
            new_text += "\n"
        cmds.scrollField(self.report_field, edit=True, text=new_text)
        cmds.scrollField(self.report_field, edit=True, insertionPosition=len(new_text) + 1)

    def _clear_report(self):
        cmds.scrollField(self.report_field, edit=True, text="")

    def _run_captured(self, func, *args, **kwargs):
        """func 실행 중 print() 출력을 캡처해 리포트에 그대로 이어붙인다."""
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                result = func(*args, **kwargs)
        except Exception as e:
            self._append_report(buf.getvalue())
            self._append_report("[ERROR] {}: {}".format(func.__name__, e))
            raise
        self._append_report(buf.getvalue())
        return result

    # ------------------------------------------------------------------
    # Domain / 경로
    # ------------------------------------------------------------------
    def _get_domain(self):
        return cmds.optionMenu(self.domain_menu, query=True, value=True)

    def _get_rl4_node(self):
        return DOMAIN_RL4[self._get_domain()]

    def _get_input_dna(self):
        return cmds.textFieldButtonGrp(self.input_field, query=True, text=True).strip()

    def _get_output_dna(self):
        return cmds.textFieldButtonGrp(self.output_field, query=True, text=True).strip()

    @staticmethod
    def _strip_edit_suffix(path):
        """_edit 접미사를 모두 제거하여 원본 DNA 경로 반환 (mh_fit_tool.py 와 동일 규칙)."""
        base, ext = os.path.splitext(path)
        while base.endswith("_edit"):
            base = base[:-5]
        return base + ext

    def _refresh_dna_paths(self, *_):
        """
        rl4_node.dnaFilePath 기준으로 Source/Output 을 자동 채운다.
        dnaFilePath 가 이미 이전 실행의 *_edit.dna 를 가리키고 있어도
        _strip_edit_suffix 로 원본을 복원하므로, 재실행 시 _edit 이 누적되지 않는다.
        """
        rl4_node = self._get_rl4_node()
        raw = ""
        if cmds.objExists(rl4_node):
            try:
                raw = cmds.getAttr(rl4_node + ".dnaFilePath") or ""
            except Exception:
                raw = ""
        src = self._strip_edit_suffix(raw) if raw else ""
        cmds.textFieldButtonGrp(self.input_field, edit=True, text=src)
        cmds.textFieldButtonGrp(
            self.output_field, edit=True,
            text=mhmr._infer_output_path(src) if src else "",
        )

    def _browse_file(self, field_ctrl, mode, caption="Select DNA File"):
        result = cmds.fileDialog2(
            fileFilter="DNA Files (*.dna);;All Files (*.*)",
            dialogStyle=2, fileMode=mode, caption=caption,
        )
        if result:
            cmds.textFieldButtonGrp(field_ctrl, edit=True, text=result[0])

    # ------------------------------------------------------------------
    # 네임스페이스 확인
    # ------------------------------------------------------------------
    def _get_namespace(self):
        return cmds.textField(self.namespace_field, query=True, text=True).strip()

    def on_check_namespace(self, *_):
        ns = self._get_namespace()
        if not ns:
            cmds.text(self.ns_status_text, edit=True, label="네임스페이스를 입력하세요.")
            return
        bare = ns[:-1] if ns.endswith(":") else ns
        if not cmds.namespace(exists=bare):
            cmds.text(
                self.ns_status_text, edit=True,
                label="존재하지 않음: {}".format(bare),
                backgroundColor=(0.5, 0.2, 0.2),
            )
            return
        joint_count = len(cmds.ls(bare + ":*", type="joint") or [])
        cmds.text(
            self.ns_status_text, edit=True,
            label="존재함: {}  (joint {}개)".format(bare, joint_count),
            backgroundColor=(0.2, 0.4, 0.2),
        )

    def on_load_namespace_from_selection(self, *_):
        selection = cmds.ls(selection=True, long=False) or []
        if not selection:
            cmds.confirmDialog(title="선택 없음", message="네임스페이스를 가져올 오브젝트를 먼저 선택하세요.", button=["확인"])
            return
        short = selection[0].split("|")[-1]
        if ":" not in short:
            cmds.confirmDialog(title="네임스페이스 없음", message="선택한 오브젝트에 네임스페이스가 없습니다: {}".format(short), button=["확인"])
            return
        bare = short.rsplit(":", 1)[0]
        cmds.textField(self.namespace_field, edit=True, text=bare)
        self.on_check_namespace()

    # ------------------------------------------------------------------
    # Step 1~8
    # ------------------------------------------------------------------
    def on_enter_edit_mode(self, *_):
        domain   = self._get_domain()
        rl4_node = self._get_rl4_node()
        if not cmds.objExists(rl4_node):
            cmds.confirmDialog(title="노드 없음", message="{} 가 씬에 없습니다.".format(rl4_node), button=["확인"])
            return

        if domain == "Body":
            self._run_captured(mhem.enter_edit_mode, rl4_node=rl4_node, force=True)
        else:
            dna_path = self._get_input_dna()
            if not dna_path:
                cmds.confirmDialog(title="DNA 경로 필요", message="Source DNA 경로를 확인하세요.", button=["확인"])
                return
            exclude_sc = set(mhem._collect_sc_info().keys())
            self._append_report(
                "[Tool] Head domain: body 쪽 skinCluster {}개를 탐색에서 제외합니다.".format(len(exclude_sc))
            )
            self._run_captured(
                mhem.enter_edit_mode, rl4_node=rl4_node, dna_path=dna_path,
                exclude_sc=exclude_sc, force=True,
            )

    def on_match(self, primary_only=False, secondary_only=False):
        ns = self._get_namespace()
        if not ns:
            cmds.confirmDialog(title="입력 필요", message="레퍼런스 네임스페이스를 입력하세요.", button=["확인"])
            return
        dna_path = self._get_input_dna()
        if not dna_path:
            cmds.confirmDialog(title="DNA 경로 필요", message="Source DNA 경로를 확인하세요.", button=["확인"])
            return
        self._run_captured(
            mhmr.match_joints_to_reference, ns, dna_path,
            primary_only=primary_only, secondary_only=secondary_only,
        )

    def on_restore_structure(self, *_):
        self._run_captured(mhem.restore_structure)

    def on_verify(self, *_):
        ns = self._get_namespace()
        dna_path = self._get_input_dna()
        if not ns or not dna_path:
            cmds.confirmDialog(title="입력 필요", message="네임스페이스와 Source DNA 경로를 확인하세요.", button=["확인"])
            return
        self._run_captured(mhmr.summarize_match, ns, dna_path)

    def on_bake_rotate(self, *_):
        self._run_captured(mhem.bake_rotate_to_joint_orient, namespace="")

    def on_export_dna(self, *_):
        out = self._get_output_dna()
        src = self._get_input_dna()
        if not out or not src:
            cmds.confirmDialog(title="경로 필요", message="Output / Source DNA 경로를 확인하세요.", button=["확인"])
            return
        confirm = cmds.confirmDialog(
            title="Export DNA — 검수 확인",
            message=(
                "뷰포트/Verify 결과를 검수했습니까?\n\n"
                "Output : {}\n"
                "Source : {}\n\n"
                "확인을 누르면 DNA 를 저장합니다."
            ).format(out, src),
            button=["Export", "취소"],
            defaultButton="취소", cancelButton="취소", dismissString="취소",
        )
        if confirm != "Export":
            return
        self._run_captured(mhem.export_dna_from_scene, out, src, namespace="")

    def on_reconnect_rl4(self, *_):
        confirm = cmds.confirmDialog(
            title="Reconnect RL4 확인",
            message=(
                "rl4 를 재연결하고 관련 skinCluster 를 unbind/rebind 합니다.\n\n"
                "주의: secondary/corrective 조인트(twist, bulge, correctiveRoot 등)는\n"
                "재연결 후 DNA 의 joint-behavior(RBF)로 라이브 구동되어 static 매칭\n"
                "값과 달라질 수 있습니다 — 이는 정상입니다 (DNA 파일 자체는 정확함).\n\n"
                "계속할까요?"
            ),
            button=["실행", "취소"],
            defaultButton="취소", cancelButton="취소", dismissString="취소",
        )
        if confirm != "실행":
            return
        self._run_captured(mhem.reconnect_rl4)


def show():
    """UI 표시 함수."""
    importlib.reload(mhem)
    importlib.reload(mhmr)
    tool = MHMatchReferenceTool()
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
