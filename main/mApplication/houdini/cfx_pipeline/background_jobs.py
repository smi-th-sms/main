# -*- coding: utf-8 -*-
"""Detached hython jobs for long-running CFX cache publishes.

The interactive Houdini process only validates that the current HIP is saved
and launches a separate ``hython`` process.  The worker opens that saved
HIP without saving it back, writes the requested cache, and reports status via
JSON/log files under ``$HOUDINI_TEMP/cfx_background_jobs``.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_USER_DATA_KEY = "cfx_background_job_file"
_VALID_ACTIONS = {"rest_cache", "sim_cache", "alembic_cache", "probe"}
_WORKER_JOB_HANDLE = None
_MONITOR_SCRIPT = r"""param(
    [Parameter(Mandatory=$true)][string]$JobFile,
    [int]$HoldSeconds = 60
)
$ErrorActionPreference = "SilentlyContinue"

function Format-Duration([object]$Seconds) {
    if ($null -eq $Seconds) { return "-" }
    $total = [Math]::Max(0, [int][Math]::Round([double]$Seconds))
    $hours = [Math]::Floor($total / 3600)
    $minutes = [Math]::Floor(($total % 3600) / 60)
    $secs = $total % 60
    if ($hours -gt 0) { return "{0}h {1:00}m {2:00}s" -f $hours,$minutes,$secs }
    if ($minutes -gt 0) { return "{0}m {1:00}s" -f $minutes,$secs }
    return "{0}s" -f $secs
}

function Save-Status([object]$Status, [string]$State, [string]$Message) {
    $now = [DateTimeOffset]::UtcNow.ToString("o")
    $Status | Add-Member -NotePropertyName state -NotePropertyValue $State -Force
    $Status | Add-Member -NotePropertyName updated_at -NotePropertyValue $now -Force
    $Status | Add-Member -NotePropertyName message -NotePropertyValue $Message -Force
    if (@("complete","failed","cancelled") -contains $State) {
        $Status | Add-Member -NotePropertyName completed_at -NotePropertyValue $now -Force
    }
    $json = $Status | ConvertTo-Json -Depth 20
    $tempStatus = "$statusFile.console-$PID.tmp"
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($tempStatus, $json, $utf8)
    Move-Item -LiteralPath $tempStatus -Destination $statusFile -Force
}

$job = $null
while ($null -eq $job) {
    try { $job = Get-Content -LiteralPath $JobFile -Raw | ConvertFrom-Json }
    catch { Start-Sleep -Milliseconds 500 }
}
$statusFile = [string]$job.status_file
$logFile = [string]$job.log_file
$context = $job.shot_context
$shotLabel = if ($null -ne $context -and $null -ne $context.shot) {
    "{0} / {1} / {2} / {3}" -f
        $context.show,$context.sequence,$context.shot,$context.asset
} else {
    [IO.Path]::GetFileNameWithoutExtension([string]$job.hip_file)
}
$Host.UI.RawUI.WindowTitle = "CFX - $shotLabel - $($job.action) $($job.version)"
function Show-Header {
    Clear-Host
    Write-Host "CFX Background Cache" -ForegroundColor Cyan
    Write-Host ("Shot    : {0}" -f $shotLabel)
    Write-Host ("Cache   : {0}  {1}" -f $job.action,$job.version)
    Write-Host ("HIP     : {0}" -f [IO.Path]::GetFileName([string]$job.hip_file))
    Write-Host ""
}
Show-Header

while ($true) {
    $status = $null
    try { $status = Get-Content -LiteralPath $statusFile -Raw | ConvertFrom-Json }
    catch {}
    $logText = ""
    if (Test-Path -LiteralPath $logFile) {
        try { $logText = Get-Content -LiteralPath $logFile -Raw }
        catch {}
    }
    $progressValue = $null
    $currentFrame = $null
    $framesDone = $null
    $framesTotal = $null
    if ($null -ne $status.progress_percent) {
        $progressValue = [double]$status.progress_percent
    }
    $progressText = $logText
    $stageName = $null
    $stageIndex = 0
    $stageTotal = 0
    $abcStarts = [regex]::Matches(
        $logText, '\[CFX ABC\] START\s+(\S+)\s+(\d+)/(\d+)')
    if ($abcStarts.Count -gt 0) {
        $lastStart = $abcStarts[$abcStarts.Count - 1]
        $stageName = [string]$lastStart.Groups[1].Value
        $stageIndex = [int]$lastStart.Groups[2].Value
        $stageTotal = [Math]::Max(1, [int]$lastStart.Groups[3].Value)
        $progressText = $logText.Substring(
            $lastStart.Index + $lastStart.Length)
    }
    $progressMatches = [regex]::Matches(
        $progressText, 'ALF_PROGRESS\s+(\d+(?:\.\d+)?)%')
    if ($progressMatches.Count -gt 0) {
        $progressValue = [double]$progressMatches[
            $progressMatches.Count - 1].Groups[1].Value
    }
    $frameMatches = [regex]::Matches(
        $progressText,
        'render frame\s+(-?\d+)(?:\s+\((\d+)\s+of\s+(\d+)\))?')
    if ($frameMatches.Count -gt 0) {
        $lastFrame = $frameMatches[$frameMatches.Count - 1]
        $currentFrame = [int]$lastFrame.Groups[1].Value
        if ($lastFrame.Groups[2].Success) {
            $framesDone = [int]$lastFrame.Groups[2].Value
            $framesTotal = [int]$lastFrame.Groups[3].Value
            $progressValue = 100.0 * $framesDone /
                [Math]::Max(1, $framesTotal)
        }
    }
    if ($stageTotal -gt 0) {
        $stagePercent = if ($null -ne $progressValue) {
            [double]$progressValue
        } else { 0.0 }
        if ($progressText -match '\[CFX ABC\] COMPLETE') {
            $stagePercent = 100.0
        }
        $progressValue = 100.0 * (
            ($stageIndex - 1) + $stagePercent / 100.0) / $stageTotal
    }
    $startText = if ($null -ne $status.started_at) {
        [string]$status.started_at
    } else { [string]$job.created_at }
    $endText = if ($null -ne $status.completed_at) {
        [string]$status.completed_at
    } else { [DateTimeOffset]::UtcNow.ToString("o") }
    $elapsedValue = $null
    try {
        $elapsedValue = (
            [DateTimeOffset]::Parse($endText) -
            [DateTimeOffset]::Parse($startText)).TotalSeconds
    } catch {}
    $etaValue = $null
    if ($null -ne $elapsedValue -and $null -ne $progressValue -and
            $progressValue -gt 0 -and $progressValue -lt 100) {
        $etaValue = $elapsedValue * (100.0 - $progressValue) / $progressValue
    }
    $state = if ($null -ne $status) {
        [string]$status.state
    } else { "queued" }
    if ($state -eq "complete") { $progressValue = 100.0 }
    $activity = "{0} | {1} {2}" -f $shotLabel,$job.action,$job.version
    $progressStatus = if ($null -ne $currentFrame) {
        if ($null -ne $framesTotal) {
            "Frame {0} ({1}/{2})" -f $currentFrame,$framesDone,$framesTotal
        } else {
            "Frame {0}" -f $currentFrame
        }
    } elseif ($null -ne $stageName) {
        "Stage {0} ({1}/{2})" -f $stageName,$stageIndex,$stageTotal
    } else {
        "Waiting for frame progress"
    }
    if (@("queued","running") -contains $state) {
        $progressStatus = "$progressStatus | [C] Cancel"
    }
    $writeProgressArgs = @{
        Id = 1
        Activity = $activity
        Status = $progressStatus
        PercentComplete = $(if ($null -ne $progressValue) {
            [int][Math]::Round([Math]::Max(
                0.0, [Math]::Min(100.0, [double]$progressValue)))
        } else { 0 })
    }
    if ($null -ne $etaValue) {
        $writeProgressArgs.SecondsRemaining = [int][Math]::Round($etaValue)
    }
    Write-Progress @writeProgressArgs

    if (@("queued","running") -contains $state -and [Console]::KeyAvailable) {
        $pressed = [Console]::ReadKey($true)
        if ($pressed.Key -eq [ConsoleKey]::C) {
            Write-Progress -Id 1 -Activity $activity -Completed
            Write-Host ""
            Write-Host "Cancel this cache job? [Y/N]" -ForegroundColor Yellow
            $confirm = [Console]::ReadKey($true)
            if ($confirm.Key -eq [ConsoleKey]::Y) {
                $worker = Get-Process -Id ([int]$job.pid)
                if ($null -ne $worker -and $worker.ProcessName -ieq "hython") {
                    $cancelMessage = "Cancelled from PowerShell progress console."
                    Save-Status $status "cancel_requested" $cancelMessage
                    $utf8 = New-Object System.Text.UTF8Encoding($false)
                    [IO.File]::AppendAllText(
                        $logFile,
                        "[CFX BG] cancel requested from PowerShell monitor`r`n",
                        $utf8)
                    Stop-Process -Id ([int]$job.pid) -Force
                    Start-Sleep -Milliseconds 500
                    if ($null -eq (Get-Process -Id ([int]$job.pid))) {
                        Save-Status $status "cancelled" $cancelMessage
                        $state = "cancelled"
                    } else {
                        Save-Status $status "running" (
                            "Cancel failed: hython process is still running.")
                        Show-Header
                    }
                } else {
                    Write-Host "Cancel refused: job PID is no longer a hython process." `
                        -ForegroundColor Red
                    Start-Sleep -Seconds 2
                    Show-Header
                }
            } else {
                Show-Header
            }
        }
    }

    if (@("complete","failed","cancelled") -contains $state) {
        Write-Progress -Id 1 -Activity $activity -Completed
        Clear-Host
        $color = if ($state -eq "complete") {
            "Green"
        } elseif ($state -eq "cancelled") {
            "Yellow"
        } else {
            "Red"
        }
        Write-Host "CFX Background Cache" -ForegroundColor Cyan
        Write-Host ("Shot: {0}" -f $shotLabel)
        Write-Host ("Cache: {0} {1}" -f $job.action,$job.version)
        Write-Host ("Job {0}." -f $state.ToUpper()) -ForegroundColor $color
        Write-Host ("Elapsed: {0}" -f (Format-Duration $elapsedValue))
        if ($null -ne $currentFrame) {
            Write-Host ("Last frame: {0}" -f $currentFrame)
        }
        if ($null -ne $status.error) {
            Write-Host $status.error -ForegroundColor Red
            Write-Host ("Log: {0}" -f $logFile)
        }
        if ($null -ne $status.message) {
            Write-Host $status.message
        }
        if ($HoldSeconds -gt 0) {
            Write-Host ("This window will close in {0} seconds." -f $HoldSeconds)
            Start-Sleep -Seconds $HoldSeconds
        } else {
            $null = Read-Host "Press Enter to close"
        }
        break
    }
    Start-Sleep -Seconds 2
}
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: str, data: dict[str, Any]) -> None:
    """Atomically replace a small JSON state file."""

    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp-%s" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, default=str)
    os.replace(tmp, path)


def _read_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def _job_root(hou=None) -> str:
    if hou is not None:
        root = hou.expandString("$HOUDINI_TEMP")
        if not root or root == "$HOUDINI_TEMP":
            root = tempfile.gettempdir()
    else:
        root = tempfile.gettempdir()
    return os.path.join(root, "cfx_background_jobs").replace("\\", "/")


def _workspace_root() -> str:
    return str(Path(__file__).resolve().parents[4]).replace("\\", "/")


def _status_path(job: dict[str, Any]) -> str:
    return str(job["status_file"])


def _set_status(job: dict[str, Any], state: str, **extra: Any) -> dict[str, Any]:
    status = {
        "job_id": job["job_id"],
        "action": job["action"],
        "state": state,
        "hip_file": job["hip_file"],
        "control_node": job["control_node"],
        "version": job.get("version"),
        "pid": job.get("pid"),
        "updated_at": _utc_now(),
        "log_file": job["log_file"],
        "resources": job.get("resources", {}),
    }
    status.update(extra)
    _write_json(_status_path(job), status)
    return status


def _is_running(pid: int | None) -> bool:
    if not pid:
        return False
    if os.name == "nt":
        # ``os.kill(pid, 0)`` is not a reliable existence check in Houdini's
        # embedded Windows Python.  An invalid process handle can leak out as
        # ``SystemError: built-in function kill returned a result with an
        # exception set`` instead of a normal OSError (WinError 6).  Query the
        # process handle directly and always close it.
        try:
            import ctypes
            from ctypes import wintypes

            process_query_limited_information = 0x1000
            still_active = 259
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = (
                wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.GetExitCodeProcess.argtypes = (
                wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
            kernel32.GetExitCodeProcess.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
            kernel32.CloseHandle.restype = wintypes.BOOL

            handle = kernel32.OpenProcess(
                process_query_limited_information, False, int(pid))
            if not handle:
                return False
            try:
                exit_code = wintypes.DWORD()
                if not kernel32.GetExitCodeProcess(
                        handle, ctypes.byref(exit_code)):
                    return False
                return exit_code.value == still_active
            finally:
                kernel32.CloseHandle(handle)
        except (OSError, ValueError, TypeError):
            return False
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ProcessLookupError, ValueError, SystemError):
        return False


def read_job_status(job_file: str) -> dict[str, Any]:
    if not job_file or not os.path.isfile(job_file):
        return {"state": "missing", "job_file": job_file}
    job = _read_json(job_file)
    status_file = _status_path(job)
    status = _read_json(status_file) if os.path.isfile(status_file) else {
        "state": "queued", "job_id": job.get("job_id")
    }
    if status.get("state") in ("queued", "running") and not _is_running(job.get("pid")):
        status["state"] = "failed"
        status["error"] = "Background process exited without a final status."
        _write_json(status_file, status)
    status["job_file"] = job_file
    status["console_monitor"] = job.get("console_monitor", {})
    status["console_monitor_pid"] = job.get("console_monitor_pid")
    if job.get("console_monitor_error"):
        status["console_monitor_error"] = job["console_monitor_error"]
    _add_progress(status, job)
    return status


def _seconds_between(start_text: str | None, end_text: str | None = None) -> float | None:
    if not start_text:
        return None
    try:
        start = datetime.fromisoformat(start_text)
        end = datetime.fromisoformat(end_text) if end_text else datetime.now(timezone.utc)
        return max(0.0, (end - start).total_seconds())
    except (TypeError, ValueError):
        return None


def _add_progress(status: dict[str, Any], job: dict[str, Any]) -> None:
    """Add live frame/progress/timing fields parsed from the worker log."""

    log_file = status.get("log_file") or job.get("log_file")
    text = ""
    if log_file and os.path.isfile(log_file):
        try:
            # Progress is always near the tail; cap reads so status polling stays
            # cheap even when a long Houdini cook emits a large log.
            with open(log_file, "rb") as stream:
                stream.seek(0, os.SEEK_END)
                size = stream.tell()
                stream.seek(max(0, size - 131072), os.SEEK_SET)
                text = stream.read().decode("utf-8", errors="replace")
        except OSError:
            text = ""

    progress_text = text
    abc_starts = list(re.finditer(
        r"\[CFX ABC\] START\s+(\S+)\s+(\d+)/(\d+)", text))
    abc_stage = None
    if abc_starts:
        marker = abc_starts[-1]
        abc_stage = marker.group(1)
        abc_index = int(marker.group(2))
        abc_total = max(1, int(marker.group(3)))
        progress_text = text[marker.end():]
        status["progress_stage"] = abc_stage
        status["progress_stage_index"] = abc_index
        status["progress_stage_total"] = abc_total

    percentages = re.findall(
        r"ALF_PROGRESS\s+(\d+(?:\.\d+)?)%", progress_text)
    frames = re.findall(
        r"render frame\s+(-?\d+)(?:\s+\((\d+)\s+of\s+(\d+)\))?",
        progress_text)
    if percentages:
        status["progress_percent"] = min(100.0, float(percentages[-1]))
    if frames:
        frame, done, total = frames[-1]
        status["current_frame"] = int(frame)
        if done and total:
            status["frames_done"] = int(done)
            status["frames_total"] = int(total)
            # Frame counters are more precise than the rounded ALF percentage.
            status["progress_percent"] = min(
                100.0, 100.0 * int(done) / max(1, int(total)))
    if abc_stage is not None:
        stage_percent = float(status.get("progress_percent") or 0.0)
        stage_complete = re.search(
            r"\[CFX ABC\] COMPLETE\s+%s\s+%d/%d" % (
                re.escape(abc_stage), abc_index, abc_total),
            progress_text)
        if stage_complete:
            stage_percent = 100.0
        status["stage_progress_percent"] = stage_percent
        status["progress_percent"] = min(
            100.0, 100.0 * ((abc_index - 1) + stage_percent / 100.0)
            / abc_total)

    state = status.get("state")
    if state == "complete":
        status["progress_percent"] = 100.0
    start_text = status.get("started_at") or job.get("created_at")
    end_text = status.get("completed_at") if state in (
        "complete", "failed", "cancelled") else None
    elapsed = _seconds_between(start_text, end_text)
    if elapsed is not None:
        status["elapsed_seconds"] = elapsed
    progress = float(status.get("progress_percent") or 0.0)
    if state in ("queued", "running") and 0.0 < progress < 100.0 and elapsed:
        status["eta_seconds"] = max(0.0, elapsed * (100.0 - progress) / progress)
        status["estimated_total_seconds"] = elapsed + status["eta_seconds"]
    elif state == "running" and progress >= 100.0:
        status["phase"] = "finalizing"
    elif state == "complete":
        status["eta_seconds"] = 0.0


def node_job_status(node) -> dict[str, Any]:
    return read_job_status(_node_job_file(node))


def _format_duration(seconds: float | int | None) -> str:
    if seconds is None:
        return "-"
    value = max(0, int(round(float(seconds))))
    hours, value = divmod(value, 3600)
    minutes, secs = divmod(value, 60)
    if hours:
        return "%dh %02dm %02ds" % (hours, minutes, secs)
    if minutes:
        return "%dm %02ds" % (minutes, secs)
    return "%ds" % secs


def format_status(status: dict[str, Any]) -> str:
    lines = [
        "Background Cache Job",
        "",
        "State: %s" % status.get("state", "unknown"),
        "Action: %s" % status.get("action", "-"),
        "Version: %s" % (status.get("version") or "-"),
        "PID: %s" % (status.get("pid") or "-"),
    ]
    if status.get("progress_percent") is not None:
        lines.append("Progress: %.1f%%" % float(status["progress_percent"]))
    if status.get("frames_total"):
        lines.append("Frame: %s  (%s / %s)" % (
            status.get("current_frame", "-"), status.get("frames_done", "-"),
            status["frames_total"]))
    if status.get("progress_stage"):
        lines.append("Stage: %s  (%s / %s)" % (
            status["progress_stage"], status.get("progress_stage_index", "-"),
            status.get("progress_stage_total", "-")))
    if status.get("elapsed_seconds") is not None:
        lines.append("Elapsed: %s" % _format_duration(status["elapsed_seconds"]))
    if status.get("eta_seconds") is not None:
        lines.append("ETA: %s" % _format_duration(status["eta_seconds"]))
    if status.get("phase") == "finalizing":
        lines.append("Phase: Finalizing cache output")
    resources = status.get("resources") or {}
    if resources:
        lines.append("CPU Threads: %s" % (
            resources.get("actual_threads")
            or resources.get("max_threads")
            or "unlimited"))
        lines.append("Priority: %s" % (
            resources.get("priority") or "normal"))
        memory_gb = float(resources.get("memory_limit_gb") or 0.0)
        lines.append("Memory Limit: %s" % (
            ("%.1f GB" % memory_gb) if memory_gb else "unlimited"))
    if status.get("job_id"):
        lines.append("Job: %s" % status["job_id"])
    if status.get("log_file"):
        lines.append("Log: %s" % status["log_file"])
    if status.get("error"):
        lines.extend(("", "Error: %s" % status["error"]))
    return "\n".join(lines)


def show_progress_monitor(node):
    """Show a non-modal, auto-refreshing cache progress window in Houdini."""

    import hou  # type: ignore

    job_file = _node_job_file(node)
    if not job_file:
        from .ui_feedback import show_message
        show_message("Background Cache Progress",
                     "No background cache job is registered.", "warning")
        return None
    try:
        from PySide6 import QtCore, QtWidgets
    except ImportError:
        from PySide2 import QtCore, QtWidgets  # type: ignore

    registry_name = "_cfx_background_progress_dialogs"
    registry = getattr(hou.session, registry_name, None)
    if registry is None:
        registry = {}
        setattr(hou.session, registry_name, registry)
    key = node.path()
    previous = registry.get(key)
    if previous is not None:
        try:
            previous.close()
        except RuntimeError:
            pass

    class _ProgressDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("CFX Background Cache Progress")
            self.setModal(False)
            self.resize(520, 260)
            self._job_file = job_file
            self._terminal_notified = False

            layout = QtWidgets.QVBoxLayout(self)
            self.title_label = QtWidgets.QLabel()
            self.title_label.setStyleSheet("font-size: 15px; font-weight: bold;")
            layout.addWidget(self.title_label)
            self.progress = QtWidgets.QProgressBar()
            self.progress.setRange(0, 1000)
            self.progress.setTextVisible(True)
            layout.addWidget(self.progress)
            self.details = QtWidgets.QLabel()
            qt_flags = getattr(QtCore.Qt, "TextInteractionFlag", QtCore.Qt)
            self.details.setTextInteractionFlags(qt_flags.TextSelectableByMouse)
            self.details.setWordWrap(True)
            layout.addWidget(self.details)
            layout.addStretch(1)

            buttons = QtWidgets.QHBoxLayout()
            refresh = QtWidgets.QPushButton("Refresh Now")
            refresh.clicked.connect(self.refresh_status)
            close = QtWidgets.QPushButton("Close")
            close.clicked.connect(self.close)
            buttons.addStretch(1)
            buttons.addWidget(refresh)
            buttons.addWidget(close)
            layout.addLayout(buttons)

            self.timer = QtCore.QTimer(self)
            self.timer.setInterval(1000)
            self.timer.timeout.connect(self.refresh_status)
            self.timer.start()
            self.refresh_status()

        def refresh_status(self):
            status = read_job_status(self._job_file)
            state = status.get("state", "unknown")
            version = status.get("version") or "-"
            self.title_label.setText("%s  |  %s  |  %s" % (
                status.get("action", "cache"), version, state.upper()))
            percent = float(status.get("progress_percent") or 0.0)
            self.progress.setValue(int(round(percent * 10.0)))
            self.progress.setFormat("%.1f%%" % percent)
            detail_lines = []
            if status.get("frames_total"):
                detail_lines.append("Frame %s   (%s / %s)" % (
                    status.get("current_frame", "-"),
                    status.get("frames_done", "-"), status["frames_total"]))
            if status.get("progress_stage"):
                detail_lines.append("Stage: %s   (%s / %s)" % (
                    status["progress_stage"],
                    status.get("progress_stage_index", "-"),
                    status.get("progress_stage_total", "-")))
            detail_lines.append("Elapsed: %s" % _format_duration(
                status.get("elapsed_seconds")))
            detail_lines.append("ETA: %s" % _format_duration(
                status.get("eta_seconds")))
            if status.get("phase") == "finalizing":
                detail_lines.append("Finalizing cache output...")
            resources = status.get("resources") or {}
            if resources:
                detail_lines.append("CPU Threads: %s" % (
                    resources.get("actual_threads")
                    or resources.get("max_threads")
                    or "unlimited"))
                detail_lines.append("Priority: %s" % (
                    resources.get("priority") or "normal"))
                memory_gb = float(resources.get("memory_limit_gb") or 0.0)
                detail_lines.append("Memory Limit: %s" % (
                    ("%.1f GB" % memory_gb) if memory_gb else "unlimited"))
            detail_lines.append("PID: %s" % (status.get("pid") or "-"))
            if status.get("error"):
                detail_lines.extend(("", "Error: %s" % status["error"]))
            self.details.setText("\n".join(detail_lines))
            if state in ("complete", "failed", "cancelled", "missing"):
                self.timer.stop()
                if not self._terminal_notified:
                    self._terminal_notified = True
                    action = status.get("action", "cache")
                    version = status.get("version") or "-"
                    if state == "complete":
                        message = "%s (%s) completed successfully." % (
                            action, version)
                        severity = hou.severityType.Message
                    elif state == "failed":
                        message = "%s (%s) failed.\n\n%s" % (
                            action, version, status.get("error") or
                            "See the background job log for details.")
                        severity = hou.severityType.Error
                    else:
                        message = "%s (%s): %s" % (action, version, state)
                        severity = hou.severityType.Warning
                    # Keep this already-modeless progress window open as the
                    # completion notification.  A deferred displayMessage here
                    # creates a nested modal loop and can lock the whole HIP.
                    self.title_label.setText(message.splitlines()[0])
                    if state == "complete":
                        self.progress.setValue(1000)
                        self.progress.setFormat("100.0%")
                    self.details.setText(
                        self.details.text() + "\n\n" + message)
                    self.raise_()
                    self.activateWindow()
                    try:
                        hou.ui.setStatusMessage(message.splitlines()[0],
                                                severity=severity)
                    except Exception:
                        pass

    dialog = _ProgressDialog(hou.qt.mainWindow())
    registry[key] = dialog
    dialog.finished.connect(
        lambda _result, k=key, d=dialog:
        registry.pop(k, None) if registry.get(k) is d else None)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog


def _hython_path(hou) -> str:
    suffix = ".exe" if os.name == "nt" else ""
    path = hou.expandString("$HFS/bin/hython%s" % suffix)
    if not os.path.isfile(path):
        raise RuntimeError("hython not found: %s" % path)
    return path


def _node_resource_limits(node) -> dict[str, Any]:
    """Read optional background limits from a CFX control node."""

    threads_parm = node.parm("background_max_threads")
    priority_parm = node.parm("background_process_priority")
    memory_parm = node.parm("background_memory_limit_gb")
    default_threads = max(1, (os.cpu_count() or 4) // 2)
    max_threads = (
        int(threads_parm.eval()) if threads_parm is not None
        else default_threads)
    priority = (
        priority_parm.evalAsString()
        if priority_parm is not None else "below_normal")
    if priority not in ("low", "below_normal", "normal"):
        priority = "normal"
    memory_gb = float(memory_parm.eval()) if memory_parm is not None else 0.0
    return {
        "max_threads": max(0, max_threads),
        "priority": priority,
        "memory_limit_gb": max(0.0, memory_gb),
    }


def _node_console_monitor(node) -> dict[str, Any]:
    enabled_parm = node.parm("background_open_console")
    hold_parm = node.parm("background_console_hold_seconds")
    return {
        "enabled": bool(enabled_parm.eval()) if enabled_parm is not None else False,
        "hold_seconds": max(
            0, int(hold_parm.eval()) if hold_parm is not None else 60),
    }


def _node_shot_context(node) -> dict[str, str]:
    def value(name: str) -> str:
        parm = node.parm(name)
        return parm.evalAsString() if parm is not None else ""

    return {
        "show": value("show"),
        "sequence": value("sequence"),
        "shot": value("shot"),
        "asset": value("asset"),
    }


def _launch_console_monitor(job: dict[str, Any]) -> int | None:
    """Launch a visible status/log console independent of Houdini."""

    settings = job.get("console_monitor") or {}
    if os.name != "nt" or not settings.get("enabled"):
        return None
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    powershell = os.path.join(
        system_root, "System32", "WindowsPowerShell", "v1.0",
        "powershell.exe")
    if not os.path.isfile(powershell):
        raise RuntimeError("Windows PowerShell not found: %s" % powershell)
    script_file = os.path.join(
        os.path.dirname(job["job_file"]), "progress_monitor.ps1")
    with open(script_file, "w", encoding="utf-8") as stream:
        stream.write(_MONITOR_SCRIPT)
    cmd = [
        powershell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", script_file,
        "-JobFile", job["job_file"],
        "-HoldSeconds", str(settings.get("hold_seconds", 60)),
    ]
    process = subprocess.Popen(
        cmd,
        cwd=os.path.dirname(job["job_file"]),
        creationflags=(
            subprocess.CREATE_NEW_CONSOLE
            | subprocess.CREATE_NEW_PROCESS_GROUP),
        close_fds=True)
    return int(process.pid)


def _apply_windows_memory_limit(limit_bytes: int):
    """Apply a process memory cap that remains owned by the hython worker."""

    import ctypes
    from ctypes import wintypes

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class _BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _BASIC_LIMIT_INFORMATION),
            ("IoInfo", _IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = (
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = (
        wintypes.HANDLE, wintypes.HANDLE)
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

    handle = kernel32.CreateJobObjectW(None, None)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        info = _EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = 0x00000100
        info.ProcessMemoryLimit = int(limit_bytes)
        if not kernel32.SetInformationJobObject(
                handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not kernel32.AssignProcessToJobObject(
                handle, kernel32.GetCurrentProcess()):
            raise ctypes.WinError(ctypes.get_last_error())
    except BaseException:
        kernel32.CloseHandle(handle)
        raise
    return handle


def _apply_worker_limits(job: dict[str, Any]) -> dict[str, Any]:
    """Apply priority and memory limits inside the detached worker."""

    global _WORKER_JOB_HANDLE
    resources = dict(job.get("resources") or {})
    priority = resources.get("priority") or "normal"
    memory_gb = max(0.0, float(resources.get("memory_limit_gb") or 0.0))

    if os.name == "nt":
        import ctypes

        priority_classes = {
            "low": 0x00000040,
            "below_normal": 0x00004000,
            "normal": 0x00000020,
        }
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.SetPriorityClass.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        kernel32.SetPriorityClass.restype = ctypes.c_int
        if not kernel32.SetPriorityClass(
                kernel32.GetCurrentProcess(),
                priority_classes.get(priority, priority_classes["normal"])):
            raise ctypes.WinError(ctypes.get_last_error())
        if memory_gb:
            _WORKER_JOB_HANDLE = _apply_windows_memory_limit(
                int(memory_gb * 1024 ** 3))
    else:
        nice_increment = {"low": 10, "below_normal": 5, "normal": 0}.get(
            priority, 0)
        if nice_increment:
            os.nice(nice_increment)
        if memory_gb:
            import resource

            limit_bytes = int(memory_gb * 1024 ** 3)
            resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
    resources["priority"] = priority
    resources["memory_limit_gb"] = memory_gb
    return resources


def launch_job(node, action: str, version: str | None = None,
               probe_output: str | None = None) -> dict[str, Any]:
    """Validate the saved HIP and launch a detached worker for ``action``."""

    if action not in _VALID_ACTIONS:
        raise ValueError("Unsupported background action: %s" % action)

    import hou  # type: ignore

    previous = node_job_status(node)
    if previous.get("state") in ("queued", "running"):
        raise RuntimeError(
            "A background cache job is already active: %s" % previous.get("job_id")
        )

    hip_file = hou.hipFile.path()
    if not hip_file or hip_file.lower().startswith("untitled"):
        raise RuntimeError("Save the HIP to a real file before launching a background job.")

    # The worker intentionally sees a frozen, saved snapshot. Never open a modal
    # confirmation from this launch path: it can be called from a Qt/deferred
    # callback and would start a nested event loop. Require an explicit save.
    if hou.hipFile.hasUnsavedChanges() and hou.isUIAvailable():
        raise RuntimeError(
            "Background cache cancelled: the HIP has unsaved changes. "
            "Save the HIP, then launch the cache again.")
    if not os.path.isfile(hip_file):
        raise RuntimeError("HIP file not found: %s" % hip_file)

    job_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    job_dir = os.path.join(_job_root(hou), job_id).replace("\\", "/")
    os.makedirs(job_dir, exist_ok=False)
    job_file = job_dir + "/job.json"
    status_file = job_dir + "/status.json"
    log_file = job_dir + "/job.log"
    job: dict[str, Any] = {
        "job_id": job_id,
        "action": action,
        "version": version,
        "hip_file": hip_file.replace("\\", "/"),
        "control_node": node.path(),
        "workspace_root": _workspace_root(),
        "job_file": job_file,
        "status_file": status_file,
        "log_file": log_file,
        "probe_output": probe_output,
        "resources": _node_resource_limits(node),
        "console_monitor": _node_console_monitor(node),
        "shot_context": _node_shot_context(node),
        "created_at": _utc_now(),
    }
    _write_json(job_file, job)
    _set_status(job, "queued")

    env = os.environ.copy()
    workspace = job["workspace_root"]
    old_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = workspace + (os.pathsep + old_pythonpath if old_pythonpath else "")
    max_threads = int(job["resources"].get("max_threads") or 0)
    if max_threads:
        env["HOUDINI_MAXTHREADS"] = str(max_threads)
    cmd = [_hython_path(hou), "-u", os.path.abspath(__file__), job_file]
    popen_kwargs: dict[str, Any] = {
        "cwd": workspace,
        "env": env,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NO_WINDOW
        )
    else:
        popen_kwargs["start_new_session"] = True

    with open(log_file, "a", encoding="utf-8", buffering=1) as log:
        process = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                                   **popen_kwargs)
    job["pid"] = process.pid
    _write_json(job_file, job)
    try:
        job["console_monitor_pid"] = _launch_console_monitor(job)
    except Exception as exc:
        # The cache worker must keep running even if the optional viewer cannot
        # be opened (PowerShell policy, missing executable, etc.).
        job["console_monitor_error"] = str(exc)
    _write_json(job_file, job)
    # The worker may reach "running" before Popen returns on a fast machine;
    # never overwrite that newer state with "queued".
    current = _read_json(status_file) if os.path.isfile(status_file) else {}
    if current.get("state") == "queued":
        _set_status(job, "queued", pid=process.pid)
    _set_node_job_file(node, job_file)
    return read_job_status(job_file)


def cancel_node_job(node) -> dict[str, Any]:
    job_file = _node_job_file(node)
    if not job_file or not os.path.isfile(job_file):
        return {"state": "missing", "error": "No background job is registered."}
    job = _read_json(job_file)
    status = read_job_status(job_file)
    if status.get("state") not in ("queued", "running"):
        return status
    pid = int(job.get("pid") or 0)
    _set_status(job, "cancel_requested", pid=pid)
    if pid and _is_running(pid):
        os.kill(pid, signal.SIGTERM)
    return _set_status(job, "cancelled", pid=pid)


def _run_probe(job: dict[str, Any]) -> dict[str, Any]:
    """Small local File Cache write used to validate a loaded HIP worker."""

    import hou  # type: ignore
    from .asset_builder import _execute_filecache

    output = job.get("probe_output") or (
        os.path.dirname(job["job_file"]) + "/probe.bgeo.sc"
    )
    obj = hou.node("/obj")
    test = obj.createNode("geo", "__cfx_background_probe")
    try:
        box = test.createNode("box", "box1")
        cache = test.createNode("filecache::2.0", "probe_cache")
        cache.setInput(0, box)
        cache.parm("filemethod").set(1)
        cache.parm("file").set(output)
        cache.parm("trange").set(0)
        written = _execute_filecache(cache)
    finally:
        test.destroy()
    return {
        "probe_file": written,
        "probe_size": os.path.getsize(written),
        "asset_node_exists": bool(hou.node("/obj/cfx_asset")),
        "shot_node_exists": bool(hou.node("/obj/cfx_shot")),
        "frame_range": list(hou.playbar.frameRange()),
    }


def run_job_file(job_file: str) -> int:
    """Worker entry point. Called only by the detached hython process."""

    job = _read_json(job_file)
    job["pid"] = os.getpid()
    _write_json(job_file, job)
    started_at = _utc_now()
    _set_status(job, "running", pid=os.getpid(), started_at=started_at)
    print("[CFX BG] start job=%s action=%s hip=%s version=%s"
          % (job["job_id"], job["action"], job["hip_file"], job.get("version")),
          flush=True)
    try:
        resources = _apply_worker_limits(job)
        workspace = job["workspace_root"]
        if workspace not in sys.path:
            sys.path.insert(0, workspace)

        import hou  # type: ignore
        resources["actual_threads"] = int(hou.maxThreads())
        # Preserve fields written by the launcher while hython was starting
        # (notably the independent console monitor PID).
        latest_job = _read_json(job_file)
        latest_job.update(job)
        job = latest_job
        job["resources"] = resources
        _write_json(job_file, job)
        _set_status(
            job, "running", pid=os.getpid(), started_at=started_at,
            resources=resources)
        print(
            "[CFX BG] resources threads=%s priority=%s memory_limit_gb=%s"
            % (resources.get("actual_threads"), resources.get("priority"),
               resources.get("memory_limit_gb")),
            flush=True)

        hou.hipFile.load(job["hip_file"], suppress_save_prompt=True,
                         ignore_load_warnings=False)
        node = hou.node(job["control_node"])
        if node is None:
            raise RuntimeError("Control node not found: %s" % job["control_node"])

        action = job["action"]
        if action == "probe":
            result = _run_probe(job)
        elif action == "rest_cache":
            from . import asset_builder, ui_asset
            cfg = ui_asset.node_to_config(node, version=job["version"])
            result = asset_builder.execute_prepared_rest_cache(
                cfg, node.path())
        elif action == "sim_cache":
            from . import shot_builder, ui_shot
            cfg = ui_shot.node_to_shot_config(node, version=job["version"])
            result = shot_builder.execute_prepared_shot_cache(
                cfg, node.path())
        elif action == "alembic_cache":
            from . import shot_builder, ui_shot
            cfg = ui_shot.node_to_shot_config(node, version=job["version"])
            result = shot_builder.execute_prepared_shot_cacheout(
                cfg, node.path())
        else:  # guarded at launch, retained for hand-edited job files
            raise ValueError("Unsupported background action: %s" % action)

        _set_status(job, "complete", pid=os.getpid(), completed_at=_utc_now(),
                    result=result)
        print("[CFX BG] complete job=%s result=%s" % (job["job_id"], result),
              flush=True)
        return 0
    except BaseException as exc:
        traceback.print_exc()
        _set_status(job, "failed", pid=os.getpid(), completed_at=_utc_now(),
                    error=str(exc), traceback=traceback.format_exc())
        print("[CFX BG] failed job=%s error=%s" % (job["job_id"], exc),
              flush=True)
        return 1


def _bootstrap_main() -> int:
    if len(sys.argv) != 2:
        print("Usage: hython background_jobs.py JOB.json", file=sys.stderr)
        return 2
    workspace = _workspace_root()
    if workspace not in sys.path:
        sys.path.insert(0, workspace)
    from main.mApplication.houdini.cfx_pipeline.background_jobs import run_job_file
    return run_job_file(sys.argv[1])


if __name__ == "__main__":
    raise SystemExit(_bootstrap_main())
def _node_job_file(node) -> str:
    """Session-local job pointer, with legacy saved-user-data fallback."""

    try:
        cached = node.cachedUserData(_USER_DATA_KEY)
        if cached:
            return str(cached)
    except Exception:
        pass
    return node.userData(_USER_DATA_KEY) or ""


def _set_node_job_file(node, job_file: str) -> None:
    """Track a job without dirtying the artist's HIP."""

    try:
        node.setCachedUserData(_USER_DATA_KEY, job_file)
    except Exception:
        node.setUserData(_USER_DATA_KEY, job_file)
