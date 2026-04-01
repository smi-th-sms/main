# -*- coding: utf-8 -*-
"""
DemBones Transfer Tool
======================
시뮬레이션된 메시 → DemBones → Joint FBX 추출 워크플로우

Workflow:
    1. Maya에서 시뮬 메시 선택
    2. Rest Pose FBX 익스포트 (입력 지오메트리)
    3. 애니메이션 Alembic 익스포트 (움직임 데이터)
    4. DemBones.exe 실행 → Joint + SkinWeight 계산
    5. 결과 FBX Maya로 임포트

Usage (Maya Script Editor):
    import importlib
    from python3.tools import dem_bones_tool
    importlib.reload(dem_bones_tool)
    dem_bones_tool.show()
"""

import os
import subprocess
import tempfile
import traceback

import maya.cmds as cmds
import maya.mel as mel

try:
    from PySide2 import QtWidgets, QtCore, QtGui
    from shiboken2 import wrapInstance
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui
    from shiboken6 import wrapInstance

import maya.OpenMayaUI as omui


# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# tools/ → python3/ → maya/ → mApplication/ → main/ → utils/
DEM_BONES_EXE = os.path.normpath(
    os.path.join(
        _SCRIPT_DIR,
        "../../../../utils/dem-bones-master/bin/Windows/DemBones.exe"
    )
)


# ---------------------------------------------------------------------------
# 유틸 함수
# ---------------------------------------------------------------------------
def get_maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)


# ---------------------------------------------------------------------------
# 메인 UI
# ---------------------------------------------------------------------------
class DemBonesTool(QtWidgets.QDialog):
    WINDOW_TITLE = "DemBones Transfer Tool"
    WINDOW_OBJ   = "DemBonesTransferToolUI"

    def __init__(self, parent=None):
        if parent is None:
            parent = get_maya_main_window()
        super(DemBonesTool, self).__init__(parent)

        self.setObjectName(self.WINDOW_OBJ)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumWidth(500)
        self.setWindowFlags(
            self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
        )

        self._build_widgets()
        self._build_layouts()
        self._build_connections()
        self._init_defaults()

    # ------------------------------------------------------------------
    # UI 구성
    # ------------------------------------------------------------------
    def _build_widgets(self):
        # ── 입력 메시 ──────────────────────────────────────────────────
        self.mesh_label     = QtWidgets.QLabel("Simulated Mesh:")
        self.mesh_field     = QtWidgets.QLineEdit()
        self.mesh_field.setPlaceholderText("Maya 뷰포트에서 메시 선택 후 << 버튼")
        self.mesh_pick_btn  = QtWidgets.QPushButton("<<")
        self.mesh_pick_btn.setFixedWidth(32)
        self.mesh_pick_btn.setToolTip("현재 선택된 메시를 가져옵니다")

        # ── 출력 디렉토리 ──────────────────────────────────────────────
        self.output_label       = QtWidgets.QLabel("Output Directory:")
        self.output_field       = QtWidgets.QLineEdit()
        self.output_browse_btn  = QtWidgets.QPushButton("...")
        self.output_browse_btn.setFixedWidth(32)

        # ── 프레임 범위 ────────────────────────────────────────────────
        self.start_spin = QtWidgets.QSpinBox()
        self.start_spin.setRange(-99999, 99999)
        self.end_spin   = QtWidgets.QSpinBox()
        self.end_spin.setRange(-99999, 99999)

        # ── 본 개수 ────────────────────────────────────────────────────
        self.nbones_spin = QtWidgets.QSpinBox()
        self.nbones_spin.setRange(1, 256)
        self.nbones_spin.setValue(10)
        self.nbones_spin.setToolTip("자동 생성할 본(Joint)의 개수")

        # ── 고급 옵션 ──────────────────────────────────────────────────
        self.adv_group = QtWidgets.QGroupBox("Advanced Options")
        self.adv_group.setCheckable(True)
        self.adv_group.setChecked(False)

        self.niters_spin = QtWidgets.QSpinBox()
        self.niters_spin.setRange(1, 1000)
        self.niters_spin.setValue(30)
        self.niters_spin.setToolTip("반복 횟수 (많을수록 정확하지만 느림)")

        self.nnz_spin = QtWidgets.QSpinBox()
        self.nnz_spin.setRange(1, 32)
        self.nnz_spin.setValue(8)
        self.nnz_spin.setToolTip("정점당 최대 영향 본 개수")

        self.bind_update_combo = QtWidgets.QComboBox()
        self.bind_update_combo.addItems([
            "0 - 변경 없음 (기본)",
            "1 - 본 위치 업데이트",
            "2 - 본을 루트 아래로 재그룹화",
        ])
        self.bind_update_combo.setToolTip("바인드 포즈 업데이트 방식")

        self.weights_smooth_spin = QtWidgets.QDoubleSpinBox()
        self.weights_smooth_spin.setRange(0.0, 1.0)
        self.weights_smooth_spin.setValue(0.0001)
        self.weights_smooth_spin.setDecimals(6)
        self.weights_smooth_spin.setSingleStep(0.0001)
        self.weights_smooth_spin.setToolTip("스킨 웨이트 평활도 (클수록 부드러움)")

        # ── 실행 버튼 ──────────────────────────────────────────────────
        self.run_btn = QtWidgets.QPushButton("Run DemBones")
        self.run_btn.setFixedHeight(36)
        self.run_btn.setStyleSheet(
            "background-color: #4a7a4a; color: white; "
            "font-weight: bold; font-size: 13px;"
        )

        self.open_output_btn = QtWidgets.QPushButton("Output 폴더 열기")
        self.open_output_btn.setFixedHeight(26)

        # ── 로그 ───────────────────────────────────────────────────────
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(120)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet(
            "background-color: #1e1e1e; color: #cccccc; "
            "font-family: Consolas, monospace; font-size: 11px;"
        )

        self.clear_log_btn = QtWidgets.QPushButton("Log 지우기")
        self.clear_log_btn.setFixedHeight(22)

    def _build_layouts(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(6)

        # ── 입력 섹션 레이블 ──────────────────────────────────────────
        input_group = QtWidgets.QGroupBox("Input / Output")
        form = QtWidgets.QFormLayout(input_group)
        form.setSpacing(6)

        # 메시 행
        mesh_row = QtWidgets.QHBoxLayout()
        mesh_row.addWidget(self.mesh_field)
        mesh_row.addWidget(self.mesh_pick_btn)
        form.addRow(self.mesh_label, mesh_row)

        # 출력 디렉토리 행
        output_row = QtWidgets.QHBoxLayout()
        output_row.addWidget(self.output_field)
        output_row.addWidget(self.output_browse_btn)
        form.addRow(self.output_label, output_row)

        # 프레임 행
        frame_row = QtWidgets.QHBoxLayout()
        frame_row.addWidget(QtWidgets.QLabel("Start:"))
        frame_row.addWidget(self.start_spin)
        frame_row.addSpacing(10)
        frame_row.addWidget(QtWidgets.QLabel("End:"))
        frame_row.addWidget(self.end_spin)
        frame_row.addStretch()
        form.addRow(QtWidgets.QLabel("Frame Range:"), frame_row)

        # 본 개수 행
        form.addRow(QtWidgets.QLabel("Number of Bones:"), self.nbones_spin)

        main_layout.addWidget(input_group)

        # ── 고급 옵션 ─────────────────────────────────────────────────
        adv_form = QtWidgets.QFormLayout()
        adv_form.setSpacing(6)
        adv_form.addRow(QtWidgets.QLabel("Iterations:"),     self.niters_spin)
        adv_form.addRow(QtWidgets.QLabel("Max Influences:"), self.nnz_spin)
        adv_form.addRow(QtWidgets.QLabel("Bind Update:"),    self.bind_update_combo)
        adv_form.addRow(QtWidgets.QLabel("Weight Smooth:"),  self.weights_smooth_spin)
        self.adv_group.setLayout(adv_form)
        main_layout.addWidget(self.adv_group)

        # ── 실행 버튼 ─────────────────────────────────────────────────
        main_layout.addWidget(self.run_btn)

        # ── 로그 ─────────────────────────────────────────────────────
        log_header = QtWidgets.QHBoxLayout()
        log_header.addWidget(QtWidgets.QLabel("Log:"))
        log_header.addStretch()
        log_header.addWidget(self.open_output_btn)
        log_header.addWidget(self.clear_log_btn)
        main_layout.addLayout(log_header)
        main_layout.addWidget(self.log_text)

    def _build_connections(self):
        self.mesh_pick_btn.clicked.connect(self._pick_mesh)
        self.output_browse_btn.clicked.connect(self._browse_output)
        self.run_btn.clicked.connect(self._run)
        self.clear_log_btn.clicked.connect(self.log_text.clear)
        self.open_output_btn.clicked.connect(self._open_output_dir)

    def _init_defaults(self):
        self.output_field.setText(
            os.path.join(tempfile.gettempdir(), "dem_bones").replace("\\", "/")
        )
        self.start_spin.setValue(int(cmds.playbackOptions(q=True, min=True)))
        self.end_spin.setValue(int(cmds.playbackOptions(q=True, max=True)))

    # ------------------------------------------------------------------
    # 콜백
    # ------------------------------------------------------------------
    def _pick_mesh(self):
        sel = cmds.ls(sl=True, type="transform")
        if not sel:
            self._log("[WARNING] 메시가 선택되지 않았습니다.")
            return
        mesh = sel[0]
        shapes = cmds.listRelatives(mesh, shapes=True, type="mesh") or []
        if not shapes:
            self._log(f"[WARNING] '{mesh}'에 폴리곤 메시 셰이프가 없습니다.")
            return
        self.mesh_field.setText(mesh)
        self._log(f"[INFO] 메시 선택: {mesh}")

    def _browse_output(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Output 디렉토리 선택"
        )
        if path:
            self.output_field.setText(path.replace("\\", "/"))

    def _open_output_dir(self):
        out_dir = self.output_field.text().strip()
        if os.path.isdir(out_dir):
            os.startfile(out_dir)
        else:
            self._log(f"[WARNING] 폴더가 없습니다: {out_dir}")

    # ------------------------------------------------------------------
    # 메인 실행 흐름
    # ------------------------------------------------------------------
    def _run(self):
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Running...")
        QtWidgets.QApplication.processEvents()
        try:
            self._execute_pipeline()
        except Exception as e:
            self._log(f"[ERROR] {e}")
            self._log(traceback.format_exc())
        finally:
            self.run_btn.setEnabled(True)
            self.run_btn.setText("Run DemBones")

    def _execute_pipeline(self):
        # ── 파라미터 수집 ─────────────────────────────────────────────
        mesh       = self.mesh_field.text().strip()
        out_dir    = self.output_field.text().strip().replace("\\", "/")
        start      = self.start_spin.value()
        end        = self.end_spin.value()
        n_bones    = self.nbones_spin.value()
        n_iters    = self.niters_spin.value()
        nnz        = self.nnz_spin.value()
        bind_upd   = self.bind_update_combo.currentIndex()
        w_smooth   = self.weights_smooth_spin.value()

        # ── 검증 ──────────────────────────────────────────────────────
        if not mesh:
            raise ValueError("메시를 지정해주세요.")
        if not cmds.objExists(mesh):
            raise ValueError(f"씬에 '{mesh}'가 존재하지 않습니다.")
        if start >= end:
            raise ValueError(f"프레임 범위 오류: {start} ~ {end}")
        if not os.path.isfile(DEM_BONES_EXE):
            raise FileNotFoundError(
                f"DemBones.exe를 찾을 수 없습니다:\n{DEM_BONES_EXE}"
            )

        # ── 출력 디렉토리 생성 ────────────────────────────────────────
        os.makedirs(out_dir, exist_ok=True)
        safe_name = mesh.replace(":", "_").replace("|", "_")

        geom_fbx   = f"{out_dir}/{safe_name}_rest.fbx"
        anim_abc   = f"{out_dir}/{safe_name}_anim.abc"
        result_fbx = f"{out_dir}/{safe_name}_demBones.fbx"

        self._log("=" * 52)
        self._log(f"[START] DemBones Pipeline")
        self._log(f"  Mesh     : {mesh}")
        self._log(f"  Frames   : {start} ~ {end}")
        self._log(f"  Bones    : {n_bones}")
        self._log(f"  Out dir  : {out_dir}")
        self._log("=" * 52)

        # ── Step 1: Rest Pose FBX 익스포트 ────────────────────────────
        self._log("[1/4] Rest pose FBX 익스포트...")
        self._export_rest_fbx(mesh, geom_fbx, start)
        self._log(f"      -> {geom_fbx}")

        # ── Step 2: Animation Alembic 익스포트 ────────────────────────
        self._log("[2/4] Animation Alembic 익스포트...")
        self._export_anim_abc(mesh, anim_abc, start, end)
        self._log(f"      -> {anim_abc}")

        # ── Step 3: DemBones 실행 ─────────────────────────────────────
        self._log("[3/4] DemBones 실행 중...")
        self._run_dem_bones(
            geom_fbx, anim_abc, result_fbx,
            n_bones, n_iters, nnz, bind_upd, w_smooth
        )
        self._log(f"      -> {result_fbx}")

        # ── Step 4: 결과 FBX Maya 임포트 ──────────────────────────────
        self._log("[4/4] 결과 FBX 임포트...")
        self._import_result_fbx(result_fbx)

        self._log("=" * 52)
        self._log("[DONE] 완료! 씬에 Joint + SkinMesh가 추가되었습니다.")
        self._log("=" * 52)

    # ------------------------------------------------------------------
    # Step 1: Rest Pose FBX 익스포트
    # ------------------------------------------------------------------
    @staticmethod
    def _ensure_fbx_plugin():
        """fbxmaya 플러그인 로드 (이미 로드됐으면 스킵)"""
        if not cmds.pluginInfo("fbxmaya", q=True, loaded=True):
            cmds.loadPlugin("fbxmaya")

    @staticmethod
    def _safe_mel(cmd):
        """MEL 명령어 실행 — 해당 버전에 없으면 경고만 출력하고 계속"""
        try:
            mel.eval(cmd)
        except RuntimeError:
            pass  # 버전에 따라 없는 명령어는 스킵

    def _export_rest_fbx(self, mesh, fbx_path, frame):
        """현재 프레임의 메시만 FBX로 익스포트 (애니메이션 없음)"""
        self._ensure_fbx_plugin()

        orig_frame = cmds.currentTime(q=True)
        try:
            cmds.currentTime(frame)
            cmds.select(mesh, r=True)

            # FBXResetExport 로 기본값으로 초기화 후 필요한 옵션만 설정
            self._safe_mel("FBXResetExport")
            self._safe_mel("FBXExportSmoothingGroups -v true")
            self._safe_mel("FBXExportHardEdges -v false")
            self._safe_mel("FBXExportTangents -v false")
            self._safe_mel("FBXExportSmoothMesh -v false")
            self._safe_mel("FBXExportAnimationOnly -v false")
            self._safe_mel("FBXExportBakeAnimation -v false")
            self._safe_mel("FBXExportInputConnections -v false")
            self._safe_mel("FBXExportSkeletonDefinitions -v false")
            self._safe_mel("FBXExportUpAxis y")

            fbx_path_mel = fbx_path.replace("\\", "/")
            mel.eval(f'FBXExport -f "{fbx_path_mel}" -s')
        finally:
            cmds.currentTime(orig_frame)

        if not os.path.isfile(fbx_path):
            raise RuntimeError(f"FBX 익스포트 실패: {fbx_path}")

    # ------------------------------------------------------------------
    # Step 2: Animation Alembic 익스포트
    # ------------------------------------------------------------------
    def _export_anim_abc(self, mesh, abc_path, start, end):
        """메시 애니메이션을 Alembic으로 익스포트"""
        abc_path_mel = abc_path.replace("\\", "/")
        abc_cmd = (
            f"-frameRange {start} {end} "
            f"-dataFormat ogawa "
            f"-worldSpace "
            f"-uvWrite "
            f"-root {mesh} "
            f'-file "{abc_path_mel}"'
        )
        cmds.AbcExport(j=abc_cmd)

        if not os.path.isfile(abc_path):
            raise RuntimeError(f"ABC 익스포트 실패: {abc_path}")

    # ------------------------------------------------------------------
    # Step 3: DemBones 실행
    # ------------------------------------------------------------------
    def _run_dem_bones(self, geom_fbx, anim_abc, out_fbx,
                       n_bones, n_iters, nnz, bind_upd, w_smooth):
        """DemBones.exe 호출"""
        cmd = [
            DEM_BONES_EXE,
            f"-i={geom_fbx}",
            f"-a={anim_abc}",
            f"-b={n_bones}",
            f"-n={n_iters}",
            f"--nnz={nnz}",
            f"--bindUpdate={bind_upd}",
            f"--weightsSmooth={w_smooth}",
            f"-o={out_fbx}",
        ]

        self._log("      CMD: " + " ".join(os.path.basename(c) if i == 0 else c
                                           for i, c in enumerate(cmd)))

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )

        # 출력 로그
        for line in (result.stdout or "").splitlines():
            if line.strip():
                self._log(f"      | {line}")
        if result.stderr:
            for line in result.stderr.splitlines():
                if line.strip():
                    self._log(f"      [STDERR] {line}")

        if result.returncode != 0:
            raise RuntimeError(
                f"DemBones 실행 실패 (returncode={result.returncode})"
            )
        if not os.path.isfile(out_fbx):
            raise RuntimeError(f"출력 FBX가 생성되지 않았습니다: {out_fbx}")

    # ------------------------------------------------------------------
    # Step 4: 결과 FBX 임포트
    # ------------------------------------------------------------------
    def _import_result_fbx(self, fbx_path):
        """결과 FBX를 현재 씬에 추가"""
        self._ensure_fbx_plugin()
        self._safe_mel("FBXImportMode -v add")
        self._safe_mel("FBXImportConvertUnit -v cm")
        self._safe_mel("FBXImportSetLockedAttribute -v true")

        fbx_path_mel = fbx_path.replace("\\", "/")
        mel.eval(f'FBXImport -f "{fbx_path_mel}"')

        self._log("      -> 임포트 완료. Joint + SkinMesh 가 씬에 추가됐습니다.")

    # ------------------------------------------------------------------
    # 로그 헬퍼
    # ------------------------------------------------------------------
    def _log(self, msg):
        self.log_text.append(msg)
        QtWidgets.QApplication.processEvents()


# ---------------------------------------------------------------------------
# 글로벌 인스턴스 관리
# ---------------------------------------------------------------------------
_instance = None


def show():
    global _instance
    # 기존 창 닫기
    try:
        _instance.close()
        _instance.deleteLater()
    except Exception:
        pass
    _instance = DemBonesTool()
    _instance.show()
    return _instance


if __name__ == "__main__":
    show()
