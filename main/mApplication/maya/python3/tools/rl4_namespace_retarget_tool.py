"""
RL4 Namespace Retarget Tool for Maya
========================================
body_rl4Embedded / head_rl4Embedded 의 joint input/output 연결을
지정한 네임스페이스의 동일 이름 조인트로 재연결하는 UI 툴입니다.

실제 연결 로직은 rl4_namespace_retarget 모듈(collect_joint_links /
validate_retarget / retarget_rl4_joints / verify_transform_match /
bake_offset_parent_matrix_for_namespace)을 그대로 사용합니다.

사용법:
    # 첫 실행
    import rl4_namespace_retarget_tool as rl4tool
    rl4tool.show()

    # 모듈 수정 후 리로드
    import rl4_namespace_retarget_tool as rl4tool
    rl4tool.reload_and_show()

UI 사용 순서:
    1) 대상 네임스페이스 입력 (예: Floyd_Rigging_main_v001:) 후
       [네임스페이스 확인] 으로 존재 / joint 개수 확인
    2) Body / Head 섹션에서 [검증 (Dry Run)] 으로 missing/locked/occupied 확인
       + world 기준 transform 일치 여부(offsetParentMatrix 포함) 확인
    3) 문제 없으면 [실행] (Body, Head 각각 독립 실행 가능) 또는
       [Body + Head 모두 실행]

offsetParentMatrix Bake (선택):
    대상 네임스페이스의 조인트가 offsetParentMatrix 에 transform 을 숨겨두고
    channel box 는 0/identity 로만 보이는 경우(예: 일부 게임 리그), 그 값을
    translate/rotate/scale 로 꺼내 놓고 offsetParentMatrix 를 초기화합니다.
    world 위치/방향은 그대로 유지되며, 이후 channel box 값만으로 다른
    스켈레톤과 transform 을 비교/매칭하기 쉬워집니다.
"""

import os
import sys
import importlib

import maya.cmds as cmds

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import rl4_namespace_retarget as rl4rt


RL4_NODES = {
    "body": "body_rl4Embedded",
    "head": "head_rl4Embedded",
}


class RL4RetargetTool:
    """body/head rl4Embedded joint 연결을 다른 네임스페이스로 재연결하는 UI."""

    def __init__(self):
        self.window_name = "rl4NamespaceRetargetWindow"
        self.namespace_field = None
        self.ns_status_text = None
        self.report_field = None
        self.bake_force_checkbox = None

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def create_ui(self):
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)

        window = cmds.window(
            self.window_name,
            title="RL4 Namespace Retarget",
            widthHeight=(480, 580),
            sizeable=True,
        )
        self.build_tab_ui(window)
        cmds.showWindow(window)

    def build_tab_ui(self, parent=None):
        """탭 또는 독립 윈도우에 UI 를 빌드. rig_tool_hub 통합용."""
        scroll = cmds.scrollLayout(childResizable=True, parent=parent) if parent \
            else cmds.scrollLayout(childResizable=True)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=5, columnAttach=("both", 15))

        cmds.separator(height=15, style="none")
        cmds.text(label="RL4 Namespace Retarget", font="boldLabelFont", height=28)
        cmds.text(
            label=(
                "body_rl4Embedded / head_rl4Embedded 의 joint 연결만 골라\n"
                "지정한 네임스페이스의 동일 이름 조인트로 재연결합니다."
            ),
            align="left",
            font="smallPlainLabelFont",
        )
        cmds.separator(height=10, style="in")

        # ── 네임스페이스 입력 + 존재 확인 ────────────────────────
        cmds.text(label="대상 네임스페이스", align="left", font="plainLabelFont")
        cmds.rowLayout(
            numberOfColumns=3,
            adjustableColumn=1,
            columnAttach=[(1, "both", 0), (2, "both", 5), (3, "both", 5)],
        )
        self.namespace_field = cmds.textField(placeholderText="예: Floyd_Rigging_main_v001:")
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

        self.ns_status_text = cmds.text(
            label="", align="left", font="smallPlainLabelFont", height=18
        )

        cmds.separator(height=10, style="none")

        # ── Body ─────────────────────────────────────────────────
        cmds.frameLayout(
            label="Body (body_rl4Embedded)",
            collapsable=False,
            marginWidth=5,
            marginHeight=5,
        )
        cmds.rowLayout(
            numberOfColumns=2,
            adjustableColumn=1,
            columnAttach=[(1, "both", 5), (2, "both", 5)],
            height=30,
        )
        cmds.button(
            label="검증 (Dry Run)",
            command=lambda *_: self.on_run("body", dry_run=True),
            backgroundColor=(0.4, 0.4, 0.5),
        )
        cmds.button(
            label="실행",
            command=lambda *_: self.on_run("body", dry_run=False),
            backgroundColor=(0.3, 0.55, 0.3),
        )
        cmds.setParent("..")
        cmds.setParent("..")

        cmds.separator(height=8, style="none")

        # ── Head ─────────────────────────────────────────────────
        cmds.frameLayout(
            label="Head (head_rl4Embedded)",
            collapsable=False,
            marginWidth=5,
            marginHeight=5,
        )
        cmds.rowLayout(
            numberOfColumns=2,
            adjustableColumn=1,
            columnAttach=[(1, "both", 5), (2, "both", 5)],
            height=30,
        )
        cmds.button(
            label="검증 (Dry Run)",
            command=lambda *_: self.on_run("head", dry_run=True),
            backgroundColor=(0.4, 0.4, 0.5),
        )
        cmds.button(
            label="실행",
            command=lambda *_: self.on_run("head", dry_run=False),
            backgroundColor=(0.3, 0.55, 0.3),
        )
        cmds.setParent("..")
        cmds.setParent("..")

        cmds.separator(height=8, style="none")

        cmds.button(
            label="Body + Head 모두 실행",
            command=lambda *_: self.on_run_both(dry_run=False),
            backgroundColor=(0.55, 0.35, 0.2),
            height=30,
        )

        cmds.separator(height=8, style="none")

        # ── offsetParentMatrix Bake ───────────────────────────────
        cmds.frameLayout(
            label="offsetParentMatrix Bake (대상 네임스페이스)",
            collapsable=True,
            collapse=True,
            marginWidth=5,
            marginHeight=5,
        )
        cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
        cmds.text(
            label=(
                "offsetParentMatrix 에 transform 값이 들어있고 channel box(translate/\n"
                "rotate/scale)가 제로화된 조인트를 찾아 그 값을 채널로 옮기고\n"
                "offsetParentMatrix 는 identity 로 초기화합니다. world 위치/방향은\n"
                "그대로 유지됩니다 (Body/Head rl4 에 연결된 조인트 기준으로 대상 판단)."
            ),
            align="left",
            font="smallPlainLabelFont",
        )
        self.bake_force_checkbox = cmds.checkBox(
            label="이미 값이 있는 채널도 강제 정규화 (force)", value=False
        )
        cmds.button(
            label="Body + Head 조인트 offsetParentMatrix Bake",
            height=28,
            backgroundColor=(0.5, 0.35, 0.5),
            command=lambda *_: self.on_bake_offset_parent_matrix(
                cmds.checkBox(self.bake_force_checkbox, query=True, value=True)
            ),
        )
        cmds.setParent("..")
        cmds.setParent("..")

        cmds.separator(height=10, style="none")

        cmds.text(label="리포트", align="left", font="plainLabelFont")
        self.report_field = cmds.scrollField(editable=False, wordWrap=False, height=230)

        cmds.separator(height=15, style="none")

        cmds.setParent("..")  # columnLayout -> scroll
        return scroll

    # ------------------------------------------------------------------
    # 네임스페이스 확인
    # ------------------------------------------------------------------
    def _get_namespace(self):
        return cmds.textField(self.namespace_field, query=True, text=True).strip()

    @staticmethod
    def _bare(namespace):
        """끝의 콜론을 제거한 네임스페이스 이름."""
        return namespace[:-1] if namespace.endswith(":") else namespace

    def on_check_namespace(self, *args):
        ns = self._get_namespace()
        if not ns:
            cmds.text(self.ns_status_text, edit=True, label="네임스페이스를 입력하세요.")
            return

        bare = self._bare(ns)
        if not cmds.namespace(exists=bare):
            cmds.text(
                self.ns_status_text,
                edit=True,
                label="존재하지 않음: {}".format(bare),
                backgroundColor=(0.5, 0.2, 0.2),
            )
            return

        joint_count = len(cmds.ls(bare + ":*", type="joint") or [])
        cmds.text(
            self.ns_status_text,
            edit=True,
            label="존재함: {}  (joint {}개)".format(bare, joint_count),
            backgroundColor=(0.2, 0.4, 0.2),
        )

    def on_load_namespace_from_selection(self, *args):
        """현재 선택된 오브젝트의 네임스페이스를 입력 필드로 불러온다."""
        selection = cmds.ls(selection=True, long=False) or []
        if not selection:
            cmds.confirmDialog(
                title="선택 없음",
                message="네임스페이스를 가져올 오브젝트를 먼저 선택하세요.",
                button=["확인"],
            )
            return

        short = selection[0].split("|")[-1]
        if ":" not in short:
            cmds.confirmDialog(
                title="네임스페이스 없음",
                message="선택한 오브젝트에 네임스페이스가 없습니다: {}".format(short),
                button=["확인"],
            )
            return

        bare = short.rsplit(":", 1)[0]
        cmds.textField(self.namespace_field, edit=True, text=bare + ":")
        self.on_check_namespace()

    def _require_namespace(self, ns):
        """네임스페이스 입력/존재를 검사. 문제 있으면 dialog 표시 후 None 반환."""
        if not ns:
            cmds.confirmDialog(title="입력 필요", message="대상 네임스페이스를 입력하세요.", button=["확인"])
            return None
        bare = self._bare(ns)
        if not cmds.namespace(exists=bare):
            cmds.confirmDialog(
                title="네임스페이스 없음",
                message="네임스페이스가 존재하지 않습니다: {}\n레퍼런스/임포트 후 다시 시도하세요.".format(bare),
                button=["확인"],
            )
            return None
        return bare

    # ------------------------------------------------------------------
    # 실행
    # ------------------------------------------------------------------
    def _set_report(self, text):
        cmds.scrollField(self.report_field, edit=True, text=text)

    def on_run(self, which, dry_run):
        ns = self._get_namespace()
        bare = self._require_namespace(ns)
        if bare is None:
            return

        node = RL4_NODES[which]
        if not cmds.objExists(node):
            cmds.confirmDialog(title="노드 없음", message="{} 노드가 씬에 없습니다.".format(node), button=["확인"])
            return

        if not dry_run:
            confirm = cmds.confirmDialog(
                title="실행 확인",
                message="{} 의 joint 연결을 '{}:' 네임스페이스로 재연결합니다.\n계속할까요?".format(node, bare),
                button=["실행", "취소"],
                defaultButton="취소",
                cancelButton="취소",
                dismissString="취소",
            )
            if confirm != "실행":
                return

        report = rl4rt.retarget_rl4_joints(node, bare + ":", dry_run=dry_run)
        text = self._format_report(node, report, dry_run)

        if dry_run:
            transform_report = rl4rt.verify_transform_match(node, bare + ":")
            text += "\n\n" + self._format_transform_report(transform_report)

        self._set_report(text)

    def on_bake_offset_parent_matrix(self, force):
        ns = self._get_namespace()
        bare = self._require_namespace(ns)
        if bare is None:
            return

        confirm = cmds.confirmDialog(
            title="offsetParentMatrix Bake 확인",
            message=(
                "'{}:' 네임스페이스의 조인트 중 offsetParentMatrix 에 transform 값이\n"
                "들어있고 channel box 가 제로화된 조인트를 찾아, 그 값을 translate/\n"
                "rotate/scale 로 옮기고 offsetParentMatrix 를 identity 로 초기화합니다.\n\n"
                "world 상의 위치/방향은 변하지 않습니다.{}\n\n"
                "레퍼런스 조인트라면 reference edit 으로 기록됩니다. 계속할까요?"
            ).format(
                bare,
                "\n(force 모드: 이미 값이 있는 채널도 강제로 정규화합니다)" if force else "",
            ),
            button=["실행", "취소"],
            defaultButton="취소",
            cancelButton="취소",
            dismissString="취소",
        )
        if confirm != "실행":
            return

        blocks = []
        for which, node in RL4_NODES.items():
            if not cmds.objExists(node):
                blocks.append("=== {} ===\n{} 노드가 씬에 없어 건너뜀.".format(node, node))
                continue
            result = rl4rt.bake_offset_parent_matrix_for_namespace(node, bare + ":", force=force)
            blocks.append(self._format_bake_report(node, result))
        self._set_report("\n\n".join(blocks))

    def on_run_both(self, dry_run=False):
        ns = self._get_namespace()
        bare = self._require_namespace(ns)
        if bare is None:
            return

        if not dry_run:
            confirm = cmds.confirmDialog(
                title="실행 확인",
                message="body_rl4Embedded + head_rl4Embedded 를 '{}:' 네임스페이스로 재연결합니다.\n계속할까요?".format(bare),
                button=["실행", "취소"],
                defaultButton="취소",
                cancelButton="취소",
                dismissString="취소",
            )
            if confirm != "실행":
                return

        blocks = []
        for which, node in RL4_NODES.items():
            if not cmds.objExists(node):
                blocks.append("=== {} ===\n{} 노드가 씬에 없어 건너뜀.".format(node, node))
                continue
            report = rl4rt.retarget_rl4_joints(node, bare + ":", dry_run=dry_run)
            text = self._format_report(node, report, dry_run)
            if dry_run:
                transform_report = rl4rt.verify_transform_match(node, bare + ":")
                text += "\n" + self._format_transform_report(transform_report)
            blocks.append(text)
        self._set_report("\n\n".join(blocks))

    @staticmethod
    def _format_transform_report(report):
        lines = [
            "--- Transform 검증 (world 기준, offsetParentMatrix 포함) ---",
            "checked   : {}".format(report["checked"]),
            "matched   : {}".format(len(report["matched"])),
            "mismatched: {}".format(len(report["mismatched"])),
        ]
        if report["mismatched"]:
            lines.append("MISMATCHED ({}):".format(len(report["mismatched"])))
            for short, pos_diff, angle_diff in report["mismatched"][:15]:
                lines.append("   - {}  pos_diff={:.3f}cm  angle_diff={:.3f}deg".format(
                    short, pos_diff, angle_diff))
        if report["missing_target"]:
            lines.append("target 네임스페이스에 없음 ({}): {}".format(
                len(report["missing_target"]), ", ".join(report["missing_target"][:15])
            ))
        if not report["mismatched"] and not report["missing_target"]:
            lines.append("-> world 기준 전체 일치")
        return "\n".join(lines)

    @staticmethod
    def _format_bake_report(node, result):
        lines = [
            "=== {} : offsetParentMatrix Bake ===".format(node),
            "baked                  : {}".format(len(result["baked"])),
            "skipped (identity)     : {}".format(len(result["skipped_identity"])),
            "skipped (not zeroed)   : {}".format(len(result["skipped_not_zeroed"])),
            "skipped (locked)       : {}".format(len(result["skipped_locked"])),
            "reverted by constraint : {}".format(len(result.get("reverted_by_constraint", []))),
            "failed                 : {}".format(len(result.get("failed", []))),
        ]
        if result["baked"]:
            lines.append("baked joints ({}): {}".format(
                len(result["baked"]), ", ".join(result["baked"][:15])
            ))
        if result["skipped_not_zeroed"]:
            lines.append("channel box 가 이미 값이 있어 건너뜀 (force 로 강행 가능, {}): {}".format(
                len(result["skipped_not_zeroed"]), ", ".join(result["skipped_not_zeroed"][:15])
            ))
        if result.get("reverted_by_constraint"):
            lines.append("REVERTED BY CONSTRAINT - 재연결 후 constraint 가 값을 되돌림 ({}):".format(
                len(result["reverted_by_constraint"])
            ))
            for n, reason in result["reverted_by_constraint"][:15]:
                lines.append("   - {}: {}".format(n, reason))
        if result.get("failed"):
            lines.append("FAILED - 재시도에도 반영 안 됨 ({}):".format(len(result["failed"])))
            for n, reason in result["failed"][:15]:
                lines.append("   - {}: {}".format(n, reason))
        return "\n".join(lines)

    @staticmethod
    def _format_report(node, report, dry_run):
        links = report["links"]
        lines = [
            "=== {} ===".format(node),
            "namespace          : {}".format(report["namespace"]),
            "input joint links  : {}".format(len(links["input"])),
            "output joint links : {}".format(len(links["output"])),
            "amOutputs links    : {}".format(len(links.get("output_am", []))),
        ]
        if report["missing"]:
            lines.append("MISSING ({}): {}".format(
                len(report["missing"]), ", ".join(report["missing"][:10])
            ))
        if report["locked"]:
            lines.append("LOCKED ({})".format(len(report["locked"])))
        if report["occupied"]:
            lines.append("OCCUPIED ({})".format(len(report["occupied"])))
        if report.get("output_missing"):
            lines.append(
                "output target attr 없음 (그대로 둠, {}건): {}".format(
                    len(report["output_missing"]), ", ".join(report["output_missing"][:10])
                )
            )
        if report.get("am_missing"):
            lines.append(
                "amOutputs target 없음 (그대로 둠, {}건): {}".format(
                    len(report["am_missing"]), ", ".join(report["am_missing"][:10])
                )
            )

        if dry_run:
            lines.append("-> dry run: 변경 없음")
        elif "input_done" in report:
            lines.append("input reconnected  : {}/{}".format(
                report["input_done"], len(links["input"])
            ))
            lines.append("output reconnected : {}/{}".format(
                report["output_done"], len(links["output"])
            ))
            lines.append("amOutputs reconnected : {}/{}".format(
                report.get("am_done", 0), len(links.get("output_am", []))
            ))
            if report.get("output_skipped"):
                lines.append(
                    "output target attr 없음 - 그대로 둠 ({}건)".format(len(report["output_skipped"]))
                )
            if report.get("am_skipped"):
                lines.append(
                    "amOutputs target 없음 - 그대로 둠 ({}건)".format(len(report["am_skipped"]))
                )
            if report.get("old_retained"):
                lines.append(
                    "old connection retained (locked, {}건, 새 연결은 정상 추가됨)".format(
                        len(report["old_retained"])
                    )
                )
            if report.get("errors"):
                lines.append("ERRORS: {}".format(len(report["errors"])))
                for src, dst, msg in report["errors"][:10]:
                    lines.append("   - {} -> {}: {}".format(src, dst, msg))
        else:
            lines.append("-> BLOCKED (missing/locked/occupied 문제를 먼저 해결하세요)")

        return "\n".join(lines)


def show():
    """UI 표시 함수."""
    importlib.reload(rl4rt)
    tool = RL4RetargetTool()
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
