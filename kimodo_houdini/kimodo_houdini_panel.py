"""Houdini Qt panel for running Kimodo generation and import workflows.

Run inside Houdini:

    import sys
    sys.path.insert(0, r"E:/script/pythonWorkSpace/kimodo_houdini")
    import kimodo_houdini_panel
    kimodo_houdini_panel.show()
"""

from __future__ import annotations

import glob
import importlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np


try:
    import hou
except ImportError:  # Allows syntax checking outside Houdini.
    hou = None

try:
    from hutil.Qt import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide6 import QtCore, QtGui, QtWidgets


WORKSPACE = Path("E:/script/pythonWorkSpace")
KIMODO_ROOT = WORKSPACE / "kimodo"
KIMODO_VENV = WORKSPACE / ".venv-kimodo310"
KIMODO_GEN_EXE = KIMODO_VENV / "Scripts" / "kimodo_gen.exe"
DEFAULT_OUTPUT_DIR = WORKSPACE / "kimodo_test_outputs"
DEFAULT_FBX = "Z:/show/ZETA/assets/Character/Scaglione/RIG/wip/maya/fbx/Scaglione_sim_v003.fbx"
DEFAULT_MODEL = "Kimodo-SOMA-RP-v1.1"
DEFAULT_PROMPT = "A person walks forward."
DEFAULT_DURATION = 6.0
DEFAULT_SOURCE_FPS = 30.0
DEFAULT_PLAYBACK_FPS = 15.0


SOMA77_NAMES = [
    "Hips",
    "Spine1",
    "Spine2",
    "Chest",
    "Neck1",
    "Neck2",
    "Head",
    "HeadEnd",
    "Jaw",
    "LeftEye",
    "RightEye",
    "LeftShoulder",
    "LeftArm",
    "LeftForeArm",
    "LeftHand",
    "LeftHandThumb1",
    "LeftHandThumb2",
    "LeftHandThumb3",
    "LeftHandThumbEnd",
    "LeftHandIndex1",
    "LeftHandIndex2",
    "LeftHandIndex3",
    "LeftHandIndex4",
    "LeftHandIndexEnd",
    "LeftHandMiddle1",
    "LeftHandMiddle2",
    "LeftHandMiddle3",
    "LeftHandMiddle4",
    "LeftHandMiddleEnd",
    "LeftHandRing1",
    "LeftHandRing2",
    "LeftHandRing3",
    "LeftHandRing4",
    "LeftHandRingEnd",
    "LeftHandPinky1",
    "LeftHandPinky2",
    "LeftHandPinky3",
    "LeftHandPinky4",
    "LeftHandPinkyEnd",
    "RightShoulder",
    "RightArm",
    "RightForeArm",
    "RightHand",
    "RightHandThumb1",
    "RightHandThumb2",
    "RightHandThumb3",
    "RightHandThumbEnd",
    "RightHandIndex1",
    "RightHandIndex2",
    "RightHandIndex3",
    "RightHandIndex4",
    "RightHandIndexEnd",
    "RightHandMiddle1",
    "RightHandMiddle2",
    "RightHandMiddle3",
    "RightHandMiddle4",
    "RightHandMiddleEnd",
    "RightHandRing1",
    "RightHandRing2",
    "RightHandRing3",
    "RightHandRing4",
    "RightHandRingEnd",
    "RightHandPinky1",
    "RightHandPinky2",
    "RightHandPinky3",
    "RightHandPinky4",
    "RightHandPinkyEnd",
    "LeftLeg",
    "LeftShin",
    "LeftFoot",
    "LeftToeBase",
    "LeftToeEnd",
    "RightLeg",
    "RightShin",
    "RightFoot",
    "RightToeBase",
    "RightToeEnd",
]


HELP_TEXT = """Kimodo in Houdini

Prompts
- Add one or more prompt rows.
- Duration is per prompt in seconds. Kimodo supports about 2-10 seconds per prompt.

Generate
- Generate launches the local Kimodo Python 3.10 venv.
- Constraints Path is passed directly to Kimodo's --constraints argument.
- Input Folder uses Kimodo's --input_folder mode and reads meta.json plus optional constraints.json.
- Auto Retarget builds a KineFX/MotionClip scene from the generated NPZ and the FBX path.

Constraints
- Root2D, FullBody, and End Effector constraints can be sampled from the current/loaded Kimodo NPZ.
- Houdini frame 1 is written as Kimodo frame index 0.
- Save writes a Kimodo-compatible constraints.json.

Visualization
- Use the display buttons to switch between source skeleton, retarget skeleton, motionclip, and skinned mesh.
"""


@dataclass
class PromptItem:
    text: str
    duration: float


def _norm(path: str | Path) -> str:
    return str(path).replace("\\", "/")


def _main_window():
    if hou is not None and hasattr(hou, "qt"):
        return hou.qt.mainWindow()
    return None


def _ensure_module_dir() -> None:
    module_dir = str(Path(__file__).resolve().parent)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)


def _load_npz(path: str) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        return {name: np.asarray(data[name]) for name in data.files}


def _axis_angle_from_matrix(matrix: np.ndarray) -> np.ndarray:
    trace = float(np.trace(matrix))
    cos_angle = np.clip((trace - 1.0) * 0.5, -1.0, 1.0)
    angle = float(np.arccos(cos_angle))
    if angle < 1.0e-8:
        return np.zeros(3, dtype=np.float64)
    denom = 2.0 * np.sin(angle)
    if abs(denom) < 1.0e-8:
        return np.zeros(3, dtype=np.float64)
    axis = np.array(
        (
            matrix[2, 1] - matrix[1, 2],
            matrix[0, 2] - matrix[2, 0],
            matrix[1, 0] - matrix[0, 1],
        ),
        dtype=np.float64,
    ) / denom
    return axis * angle


def _axis_angle_array(rot_mats: np.ndarray) -> np.ndarray:
    out = np.zeros(rot_mats.shape[:-2] + (3,), dtype=np.float64)
    flat_in = rot_mats.reshape(-1, 3, 3)
    flat_out = out.reshape(-1, 3)
    for index, matrix in enumerate(flat_in):
        flat_out[index] = _axis_angle_from_matrix(matrix)
    return out


def _frame_indices(start_frame: int, end_frame: int, frame_count: int) -> list[int]:
    start_idx = max(0, int(start_frame) - 1)
    end_idx = max(start_idx, int(end_frame) - 1)
    end_idx = min(end_idx, frame_count - 1)
    return list(range(start_idx, end_idx + 1))


def _constraint_from_npz(npz_path: str, constraint_type: str, start_frame: int, end_frame: int) -> dict:
    data = _load_npz(npz_path)
    positions = data["posed_joints"]
    local_rot_mats = data["local_rot_mats"]
    root_positions = data["root_positions"]
    frame_count = int(positions.shape[0])
    indices = _frame_indices(start_frame, end_frame, frame_count)
    if not indices:
        raise ValueError("No valid frames for constraint")

    root_subset = root_positions[indices]
    if constraint_type == "root2d":
        return {
            "type": "root2d",
            "frame_indices": indices,
            "smooth_root_2d": root_subset[:, [0, 2]].tolist(),
        }

    local_axis_angle = _axis_angle_array(local_rot_mats[indices])
    out = {
        "type": constraint_type,
        "frame_indices": indices,
        "local_joints_rot": local_axis_angle.tolist(),
        "root_positions": root_subset.tolist(),
        "smooth_root_2d": root_subset[:, [0, 2]].tolist(),
    }
    if constraint_type == "end-effector":
        out["joint_names"] = ["LeftHand", "RightHand", "LeftFoot", "RightFoot", "Hips"]
    return out


def _read_meta_prompts(example_dir: str) -> list[PromptItem]:
    meta_path = Path(example_dir) / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing meta.json: {meta_path}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if "texts" in meta:
        durations = meta.get("durations", [DEFAULT_DURATION] * len(meta["texts"]))
        return [PromptItem(str(text), float(duration)) for text, duration in zip(meta["texts"], durations)]
    if "prompts_text" in meta:
        prompts = meta.get("prompts_text", [])
        durations = meta.get("prompts_duration", [DEFAULT_DURATION] * len(prompts))
        return [PromptItem(str(text), float(duration)) for text, duration in zip(prompts, durations)]
    return [PromptItem(str(meta.get("text", DEFAULT_PROMPT)), float(meta.get("duration", DEFAULT_DURATION)))]


def _find_npz_for_output(output_stem: str, num_samples: int) -> str | None:
    stem = output_stem.rstrip("/\\")
    if num_samples <= 1:
        direct = stem if stem.lower().endswith(".npz") else stem + ".npz"
        return direct if os.path.exists(direct) else None

    folder = os.path.splitext(stem)[0]
    candidates = sorted(glob.glob(os.path.join(folder, "*.npz")))
    return candidates[0] if candidates else None


class KimodoHoudiniPanel(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kimodo for Houdini")
        self.resize(860, 720)
        self.process: QtCore.QProcess | None = None
        self.last_npz_path: str = _norm(DEFAULT_OUTPUT_DIR / "walk_natural_6s_post.npz")
        self.constraints: list[dict] = []
        self._build_ui()
        self._refresh_status()

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        root.addWidget(self.tabs)

        self._build_prompts_tab()
        self._build_generate_tab()
        self._build_constraints_tab()
        self._build_visualize_tab()
        self._build_help_tab()

        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)
        root.addWidget(self.log)

    def _build_prompts_tab(self) -> None:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        self.prompt_table = QtWidgets.QTableWidget(0, 2)
        self.prompt_table.setHorizontalHeaderLabels(["Prompt", "Duration sec"])
        self.prompt_table.horizontalHeader().setStretchLastSection(False)
        self.prompt_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.prompt_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        layout.addWidget(self.prompt_table)

        buttons = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("Add Prompt")
        del_btn = QtWidgets.QPushButton("Delete Selected")
        load_btn = QtWidgets.QPushButton("Load Example Prompts")
        buttons.addWidget(add_btn)
        buttons.addWidget(del_btn)
        buttons.addWidget(load_btn)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        add_btn.clicked.connect(lambda: self._add_prompt(DEFAULT_PROMPT, DEFAULT_DURATION))
        del_btn.clicked.connect(self._delete_selected_prompt)
        load_btn.clicked.connect(self._load_example_prompts_dialog)
        self._add_prompt(DEFAULT_PROMPT, DEFAULT_DURATION)
        self.tabs.addTab(tab, "Prompts")

    def _build_generate_tab(self) -> None:
        tab = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(tab)

        self.model_edit = QtWidgets.QLineEdit(DEFAULT_MODEL)
        self.output_edit = QtWidgets.QLineEdit(_norm(DEFAULT_OUTPUT_DIR / "houdini_kimodo_motion"))
        self.constraints_edit = QtWidgets.QLineEdit("")
        self.input_folder_edit = QtWidgets.QLineEdit("")
        self.fbx_edit = QtWidgets.QLineEdit(DEFAULT_FBX)
        self.steps_spin = QtWidgets.QSpinBox()
        self.steps_spin.setRange(1, 200)
        self.steps_spin.setValue(50)
        self.samples_spin = QtWidgets.QSpinBox()
        self.samples_spin.setRange(1, 8)
        self.samples_spin.setValue(1)
        self.seed_spin = QtWidgets.QSpinBox()
        self.seed_spin.setRange(-1, 2_147_483_647)
        self.seed_spin.setValue(7)
        self.transition_spin = QtWidgets.QSpinBox()
        self.transition_spin.setRange(0, 60)
        self.transition_spin.setValue(5)
        self.cfg_type_combo = QtWidgets.QComboBox()
        self.cfg_type_combo.addItems(["default", "nocfg", "regular", "separated"])
        self.cfg_weight_edit = QtWidgets.QLineEdit("")
        self.postprocess_check = QtWidgets.QCheckBox("Use MotionCorrection postprocess")
        self.postprocess_check.setChecked(True)
        self.bvh_check = QtWidgets.QCheckBox("Export BVH")
        self.bvh_check.setChecked(True)
        self.bvh_tpose_check = QtWidgets.QCheckBox("BVH standard T-pose")
        self.bvh_tpose_check.setChecked(True)
        self.save_example_check = QtWidgets.QCheckBox("Save demo-compatible example")
        self.auto_retarget_check = QtWidgets.QCheckBox("Auto import/retarget after generation")
        self.auto_retarget_check.setChecked(True)

        form.addRow("Model", self.model_edit)
        form.addRow("Output Stem", self.output_edit)
        form.addRow("Constraints JSON", self._with_browse(self.constraints_edit, self._browse_constraints_file))
        form.addRow("Input Example Folder", self._with_browse(self.input_folder_edit, self._browse_input_folder))
        form.addRow("FBX Target", self._with_browse(self.fbx_edit, self._browse_fbx_file))
        form.addRow("Diffusion Steps", self.steps_spin)
        form.addRow("Samples", self.samples_spin)
        form.addRow("Seed (-1 random)", self.seed_spin)
        form.addRow("Transition Frames", self.transition_spin)
        form.addRow("CFG Type", self.cfg_type_combo)
        form.addRow("CFG Weight(s)", self.cfg_weight_edit)
        form.addRow("", self.postprocess_check)
        form.addRow("", self.bvh_check)
        form.addRow("", self.bvh_tpose_check)
        form.addRow("", self.save_example_check)
        form.addRow("", self.auto_retarget_check)

        buttons = QtWidgets.QHBoxLayout()
        gen_btn = QtWidgets.QPushButton("Generate")
        input_btn = QtWidgets.QPushButton("Generate From Input Folder")
        import_btn = QtWidgets.QPushButton("Import Latest NPZ")
        retarget_btn = QtWidgets.QPushButton("Retarget Latest to FBX")
        buttons.addWidget(gen_btn)
        buttons.addWidget(input_btn)
        buttons.addWidget(import_btn)
        buttons.addWidget(retarget_btn)
        form.addRow(buttons)

        gen_btn.clicked.connect(self._generate_from_prompts)
        input_btn.clicked.connect(self._generate_from_input_folder)
        import_btn.clicked.connect(self._import_latest_npz)
        retarget_btn.clicked.connect(self._retarget_latest_npz)
        self.tabs.addTab(tab, "Generate")

    def _build_constraints_tab(self) -> None:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        form = QtWidgets.QFormLayout()
        self.constraint_npz_edit = QtWidgets.QLineEdit(self.last_npz_path)
        self.constraint_type_combo = QtWidgets.QComboBox()
        self.constraint_type_combo.addItems(["root2d", "fullbody", "left-hand", "right-hand", "left-foot", "right-foot", "end-effector"])
        self.start_frame_spin = QtWidgets.QSpinBox()
        self.start_frame_spin.setRange(1, 100000)
        self.start_frame_spin.setValue(1)
        self.end_frame_spin = QtWidgets.QSpinBox()
        self.end_frame_spin.setRange(1, 100000)
        self.end_frame_spin.setValue(1)
        self.constraints_save_edit = QtWidgets.QLineEdit(_norm(DEFAULT_OUTPUT_DIR / "houdini_constraints.json"))
        form.addRow("Source NPZ", self._with_browse(self.constraint_npz_edit, self._browse_constraint_npz))
        form.addRow("Constraint Type", self.constraint_type_combo)
        form.addRow("Start Houdini Frame", self.start_frame_spin)
        form.addRow("End Houdini Frame", self.end_frame_spin)
        form.addRow("Save Path", self._with_browse(self.constraints_save_edit, self._browse_constraints_save))
        layout.addLayout(form)

        buttons = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("Add Constraint From NPZ")
        current_btn = QtWidgets.QPushButton("Use Current Frame")
        save_btn = QtWidgets.QPushButton("Save Constraints JSON")
        load_btn = QtWidgets.QPushButton("Load Constraints JSON")
        clear_btn = QtWidgets.QPushButton("Clear")
        buttons.addWidget(add_btn)
        buttons.addWidget(current_btn)
        buttons.addWidget(save_btn)
        buttons.addWidget(load_btn)
        buttons.addWidget(clear_btn)
        layout.addLayout(buttons)

        self.constraints_list = QtWidgets.QListWidget()
        layout.addWidget(self.constraints_list)

        add_btn.clicked.connect(self._add_constraint_from_npz)
        current_btn.clicked.connect(self._set_constraint_frames_to_current)
        save_btn.clicked.connect(self._save_constraints_json)
        load_btn.clicked.connect(self._load_constraints_json)
        clear_btn.clicked.connect(self._clear_constraints)
        self.tabs.addTab(tab, "Constraints")

    def _build_visualize_tab(self) -> None:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        buttons = QtWidgets.QGridLayout()
        entries = [
            ("Source Pose", "OUT_KIMODO_SOURCE_POSE"),
            ("Source MotionClip", "OUT_KIMODO_SOURCE_MOTIONCLIP"),
            ("Target Rest", "OUT_SCAGLIONE_TARGET_REST"),
            ("Retarget Pose", "OUT_SCAGLIONE_RETARGET_POSE"),
            ("Retarget MotionClip", "OUT_SCAGLIONE_RETARGET_MOTIONCLIP"),
            ("Skinned Mesh", "OUT_SCAGLIONE_SKIN_DEFORM_PREVIEW"),
        ]
        for index, (label, node_name) in enumerate(entries):
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(lambda checked=False, n=node_name: self._display_node(n))
            buttons.addWidget(button, index // 2, index % 2)
        layout.addLayout(buttons)

        self.frame_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.frame_slider.setRange(1, 180)
        self.frame_slider.setValue(60)
        self.frame_label = QtWidgets.QLabel("Frame: 60")
        layout.addWidget(self.frame_label)
        layout.addWidget(self.frame_slider)
        self.frame_slider.valueChanged.connect(self._set_houdini_frame)

        focus_btn = QtWidgets.QPushButton("Focus Viewport")
        refresh_btn = QtWidgets.QPushButton("Refresh Panel State")
        focus_btn.clicked.connect(self._focus_viewport)
        refresh_btn.clicked.connect(self._refresh_status)
        layout.addWidget(focus_btn)
        layout.addWidget(refresh_btn)
        layout.addStretch(1)
        self.tabs.addTab(tab, "Visualize")

    def _build_help_tab(self) -> None:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        text = QtWidgets.QPlainTextEdit(HELP_TEXT)
        text.setReadOnly(True)
        layout.addWidget(text)
        self.tabs.addTab(tab, "Help")

    def _with_browse(self, line_edit: QtWidgets.QLineEdit, callback) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit)
        button = QtWidgets.QPushButton("...")
        button.setFixedWidth(32)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return widget

    def _add_prompt(self, text: str, duration: float) -> None:
        row = self.prompt_table.rowCount()
        self.prompt_table.insertRow(row)
        self.prompt_table.setItem(row, 0, QtWidgets.QTableWidgetItem(text))
        self.prompt_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(float(duration))))

    def _delete_selected_prompt(self) -> None:
        rows = sorted({idx.row() for idx in self.prompt_table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.prompt_table.removeRow(row)
        if self.prompt_table.rowCount() == 0:
            self._add_prompt(DEFAULT_PROMPT, DEFAULT_DURATION)

    def _prompt_items(self) -> list[PromptItem]:
        prompts = []
        for row in range(self.prompt_table.rowCount()):
            text_item = self.prompt_table.item(row, 0)
            duration_item = self.prompt_table.item(row, 1)
            text = text_item.text().strip() if text_item else ""
            if not text:
                continue
            duration = float(duration_item.text()) if duration_item and duration_item.text().strip() else DEFAULT_DURATION
            prompts.append(PromptItem(text, duration))
        if not prompts:
            raise ValueError("At least one prompt is required")
        return prompts

    def _load_example_prompts_dialog(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Kimodo example folder", _norm(KIMODO_ROOT / "kimodo" / "assets" / "demo" / "examples" / "kimodo-soma-rp"))
        if path:
            self._load_example_prompts(path)

    def _load_example_prompts(self, path: str) -> None:
        prompts = _read_meta_prompts(path)
        self.prompt_table.setRowCount(0)
        for item in prompts:
            self._add_prompt(item.text, item.duration)
        motion_path = Path(path) / "motion.npz"
        constraints_path = Path(path) / "constraints.json"
        if motion_path.exists():
            self._set_latest_npz(_norm(motion_path))
        if constraints_path.exists():
            self.constraints_edit.setText(_norm(constraints_path))
        self.input_folder_edit.setText(_norm(path))
        self._log(f"Loaded example prompts from {path}")

    def _browse_constraints_file(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select constraints.json", _norm(DEFAULT_OUTPUT_DIR), "JSON (*.json)")
        if path:
            self.constraints_edit.setText(path)

    def _browse_input_folder(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select input example folder", _norm(DEFAULT_OUTPUT_DIR))
        if path:
            self.input_folder_edit.setText(path)

    def _browse_fbx_file(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select FBX target", _norm(WORKSPACE), "FBX (*.fbx)")
        if path:
            self.fbx_edit.setText(path)

    def _browse_constraint_npz(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Kimodo NPZ", _norm(DEFAULT_OUTPUT_DIR), "NPZ (*.npz)")
        if path:
            self.constraint_npz_edit.setText(path)
            self._set_latest_npz(path)

    def _browse_constraints_save(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save constraints.json", self.constraints_save_edit.text(), "JSON (*.json)")
        if path:
            self.constraints_save_edit.setText(path)

    def _build_common_args(self) -> list[str]:
        args = [
            "--model",
            self.model_edit.text().strip() or DEFAULT_MODEL,
            "--num_samples",
            str(self.samples_spin.value()),
            "--diffusion_steps",
            str(self.steps_spin.value()),
            "--num_transition_frames",
            str(self.transition_spin.value()),
            "--output",
            self.output_edit.text().strip(),
        ]
        if self.seed_spin.value() >= 0:
            args.extend(["--seed", str(self.seed_spin.value())])
        constraints = self.constraints_edit.text().strip()
        if constraints:
            args.extend(["--constraints", constraints])
        if self.bvh_check.isChecked():
            args.append("--bvh")
        if self.bvh_tpose_check.isChecked():
            args.append("--bvh_standard_tpose")
        if not self.postprocess_check.isChecked():
            args.append("--no-postprocess")
        if self.save_example_check.isChecked():
            args.append("--save_example_dir")
        cfg_type = self.cfg_type_combo.currentText()
        if cfg_type != "default":
            args.extend(["--cfg_type", cfg_type])
        cfg_weights = self.cfg_weight_edit.text().strip()
        if cfg_weights:
            args.append("--cfg_weight")
            args.extend(cfg_weights.split())
        return args

    def _generate_from_prompts(self) -> None:
        prompts = self._prompt_items()
        prompt_text = " ".join(item.text if item.text.endswith(".") else item.text + "." for item in prompts)
        durations = " ".join(str(item.duration) for item in prompts)
        args = [prompt_text, "--duration", durations] + self._build_common_args()
        self._start_generation(args)

    def _generate_from_input_folder(self) -> None:
        folder = self.input_folder_edit.text().strip()
        if not folder:
            raise ValueError("Input example folder is empty")
        args = ["--input_folder", folder] + self._build_common_args()
        self._start_generation(args)

    def _start_generation(self, args: list[str]) -> None:
        if self.process is not None and self.process.state() != QtCore.QProcess.NotRunning:
            self._log("Generation is already running")
            return
        if not KIMODO_GEN_EXE.exists():
            raise FileNotFoundError(f"Missing kimodo_gen.exe: {KIMODO_GEN_EXE}")

        self._log("Starting Kimodo generation...")
        self._log(" ".join([_norm(KIMODO_GEN_EXE)] + args))
        self.process = QtCore.QProcess(self)
        env = QtCore.QProcessEnvironment.systemEnvironment()
        env.insert("TEXT_ENCODER_DEVICE", "cpu")
        self.process.setProcessEnvironment(env)
        self.process.setWorkingDirectory(_norm(WORKSPACE))
        self.process.readyReadStandardOutput.connect(self._read_process_stdout)
        self.process.readyReadStandardError.connect(self._read_process_stderr)
        self.process.finished.connect(self._generation_finished)
        self.process.start(_norm(KIMODO_GEN_EXE), args)

    def _read_process_stdout(self) -> None:
        if self.process:
            self._log(bytes(self.process.readAllStandardOutput()).decode("utf-8", "replace").rstrip())

    def _read_process_stderr(self) -> None:
        if self.process:
            self._log(bytes(self.process.readAllStandardError()).decode("utf-8", "replace").rstrip())

    def _generation_finished(self, exit_code: int, exit_status) -> None:
        self._log(f"Kimodo process finished: exit_code={exit_code}")
        npz = _find_npz_for_output(self.output_edit.text().strip(), self.samples_spin.value())
        if npz:
            self._set_latest_npz(_norm(npz))
            self._log(f"Latest NPZ: {npz}")
            if self.auto_retarget_check.isChecked():
                self._retarget_latest_npz()
        else:
            self._log("Could not find generated NPZ for output stem")

    def _set_latest_npz(self, path: str) -> None:
        self.last_npz_path = _norm(path)
        self.constraint_npz_edit.setText(self.last_npz_path)

    def _import_latest_npz(self) -> None:
        npz = self.constraint_npz_edit.text().strip() or self.last_npz_path
        _ensure_module_dir()
        import kimodo_npz_kinefx_importer

        importlib.reload(kimodo_npz_kinefx_importer)
        hip_path = os.path.splitext(npz)[0] + "_kinefx_direct.hip"
        kimodo_npz_kinefx_importer.create_scene_from_houdini(
            npz,
            hip_path,
            obj_name="kimodo_npz_kinefx",
            source_fps=DEFAULT_SOURCE_FPS,
            playback_fps=DEFAULT_PLAYBACK_FPS,
        )
        self._log(f"Imported NPZ as KineFX: {hip_path}")

    def _retarget_latest_npz(self) -> None:
        npz = self.constraint_npz_edit.text().strip() or self.last_npz_path
        if not os.path.exists(npz):
            raise FileNotFoundError(f"Missing NPZ: {npz}")
        fbx = self.fbx_edit.text().strip()
        _ensure_module_dir()
        import kimodo_fbx_retarget_setup

        importlib.reload(kimodo_fbx_retarget_setup)
        hip_path = os.path.splitext(npz)[0] + "_scaglione_retarget.hip"
        kimodo_fbx_retarget_setup.build_retarget_scene(
            npz,
            fbx,
            hip_path,
            obj_name="kimodo_scaglione_retarget",
            source_fps=DEFAULT_SOURCE_FPS,
            playback_fps=DEFAULT_PLAYBACK_FPS,
        )
        self._log(f"Retarget scene saved: {hip_path}")
        self._refresh_status()

    def _set_constraint_frames_to_current(self) -> None:
        frame = int(hou.frame()) if hou is not None else 1
        self.start_frame_spin.setValue(frame)
        self.end_frame_spin.setValue(frame)

    def _add_constraint_from_npz(self) -> None:
        npz = self.constraint_npz_edit.text().strip()
        ctype = self.constraint_type_combo.currentText()
        constraint = _constraint_from_npz(npz, ctype, self.start_frame_spin.value(), self.end_frame_spin.value())
        self.constraints.append(constraint)
        self._refresh_constraints_list()
        self._log(f"Added {ctype} constraint from {npz}")

    def _refresh_constraints_list(self) -> None:
        self.constraints_list.clear()
        for index, constraint in enumerate(self.constraints):
            frames = constraint.get("frame_indices", [])
            label = f"{index:02d}  {constraint['type']}  frames={frames[:3]}"
            if len(frames) > 3:
                label += f"...{frames[-1]}"
            self.constraints_list.addItem(label)

    def _save_constraints_json(self) -> None:
        path = self.constraints_save_edit.text().strip()
        if not path:
            raise ValueError("Constraint save path is empty")
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as stream:
            json.dump(self.constraints, stream, indent=2)
        self.constraints_edit.setText(path)
        self._log(f"Saved constraints: {path}")

    def _load_constraints_json(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load constraints.json", self.constraints_save_edit.text(), "JSON (*.json)")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as stream:
            data = json.load(stream)
        if not isinstance(data, list):
            raise ValueError("constraints.json must contain a list")
        self.constraints = data
        self.constraints_edit.setText(path)
        self.constraints_save_edit.setText(path)
        self._refresh_constraints_list()
        self._log(f"Loaded constraints: {path}")

    def _clear_constraints(self) -> None:
        self.constraints.clear()
        self._refresh_constraints_list()

    def _display_node(self, node_name: str) -> None:
        if hou is None:
            return
        obj = hou.node("/obj/kimodo_scaglione_retarget") or hou.node("/obj/kimodo_npz_kinefx")
        if obj is None:
            self._log("No Kimodo Houdini object found")
            return
        node = obj.node(node_name)
        if node is None:
            self._log(f"Node not found: {node_name}")
            return
        node.setDisplayFlag(True)
        if hasattr(node, "setRenderFlag"):
            node.setRenderFlag(True)
        node.setSelected(True, clear_all_selected=True)
        self._log(f"Display: {node.path()}")

    def _set_houdini_frame(self, value: int) -> None:
        self.frame_label.setText(f"Frame: {value}")
        if hou is not None:
            hou.setFrame(value)

    def _focus_viewport(self) -> None:
        if hou is None:
            return
        pane = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
        if pane:
            pane.curViewport().frameAll()

    def _refresh_status(self) -> None:
        if hou is None:
            return
        try:
            frame_range = hou.playbar.frameRange()
            self.frame_slider.setRange(int(frame_range[0]), int(frame_range[1]))
            self.frame_slider.setValue(int(hou.frame()))
        except Exception:
            pass

    def _log(self, text: str) -> None:
        if not text:
            return
        self.log.appendPlainText(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())


_PANEL: KimodoHoudiniPanel | None = None


def show() -> KimodoHoudiniPanel:
    global _PANEL
    if _PANEL is None:
        _PANEL = KimodoHoudiniPanel(parent=_main_window())
        _PANEL.setWindowModality(QtCore.Qt.NonModal)
    _PANEL.show()
    return _PANEL


def show_deferred() -> None:
    QtCore.QTimer.singleShot(0, show)
