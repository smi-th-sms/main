"""Non-blocking Houdini UI feedback.

CFX callbacks must never call ``hou.ui.displayMessage``/``readInput``.  Those
APIs start a nested modal event loop; a deferred callback can run inside that
loop and leave Houdini waiting on an invisible dialog.  These helpers keep Qt
windows modeless and retain them in ``hou.session`` until they close.
"""

from __future__ import annotations

from typing import Any, Callable


def _defer_if_needed(func: Callable, *args, **kwargs) -> bool:
    """Queue Qt creation when called from an MCP/background Python thread."""

    import threading
    if threading.current_thread() is threading.main_thread():
        return False
    try:
        import hdefereval
        hdefereval.executeDeferred(lambda: func(*args, **kwargs))
        return True
    except Exception:
        return False


def _qt():
    try:
        from PySide6 import QtCore, QtWidgets
    except ImportError:
        from PySide2 import QtCore, QtWidgets  # type: ignore
    return QtCore, QtWidgets


def _registry():
    import hou  # type: ignore

    name = "_cfx_modeless_dialogs"
    value = getattr(hou.session, name, None)
    if value is None:
        value = set()
        setattr(hou.session, name, value)
    return value


def _retain(dialog) -> None:
    registry = _registry()
    registry.add(dialog)
    dialog.finished.connect(lambda _result, d=dialog: registry.discard(d))


def show_message(title: str, message: str, severity: str = "message"):
    """Show a modeless, selectable-text notification."""

    if _defer_if_needed(show_message, title, message, severity):
        return None
    try:
        import hou  # type: ignore
        if not hou.isUIAvailable():
            print("[CFX %s] %s" % (severity.upper(), message))
            return None
        QtCore, QtWidgets = _qt()
        dialog = QtWidgets.QDialog(hou.qt.mainWindow())
        dialog.setWindowTitle(title)
        dialog.setModal(False)
        dialog.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        dialog.resize(560, 220)
        layout = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel(message)
        label.setWordWrap(True)
        label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        color = {
            "error": "#d95f59",
            "warning": "#d6a646",
            "message": "#6ba5d7",
        }.get(severity, "#6ba5d7")
        label.setStyleSheet(
            "QLabel { border-left: 4px solid %s; padding: 8px; }" % color)
        layout.addWidget(label)
        close = QtWidgets.QPushButton("Close")
        close.clicked.connect(dialog.close)
        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close)
        layout.addLayout(row)
        _retain(dialog)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        try:
            hou.ui.setStatusMessage(
                message.splitlines()[0],
                severity={
                    "error": hou.severityType.Error,
                    "warning": hou.severityType.Warning,
                }.get(severity, hou.severityType.Message))
        except Exception:
            pass
        return dialog
    except Exception:
        print("[CFX %s] %s" % (severity.upper(), message))
        return None


def ask_choice(title: str, message: str,
               choices: list[tuple[str, Any]],
               callback: Callable[[Any], None],
               cancel_value: Any = None):
    """Show a modeless choice window and invoke ``callback`` after it closes."""

    if _defer_if_needed(
            ask_choice, title, message, choices, callback, cancel_value):
        return None
    import hou  # type: ignore
    QtCore, QtWidgets = _qt()
    dialog = QtWidgets.QDialog(hou.qt.mainWindow())
    dialog.setWindowTitle(title)
    dialog.setModal(False)
    dialog.setWindowModality(QtCore.Qt.WindowModality.NonModal)
    dialog.resize(600, 230)
    layout = QtWidgets.QVBoxLayout(dialog)
    label = QtWidgets.QLabel(message)
    label.setWordWrap(True)
    label.setTextInteractionFlags(
        QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(label)
    row = QtWidgets.QHBoxLayout()
    row.addStretch(1)
    selected = {"done": False}

    def finish(value):
        if selected["done"]:
            return
        selected["done"] = True
        dialog.close()
        QtCore.QTimer.singleShot(0, lambda v=value: callback(v))

    for text, value in choices:
        button = QtWidgets.QPushButton(text)
        button.clicked.connect(lambda _checked=False, v=value: finish(v))
        row.addWidget(button)
    layout.addLayout(row)
    dialog.rejected.connect(lambda: finish(cancel_value))
    _retain(dialog)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog


def ask_text(title: str, message: str, initial: str,
             callback: Callable[[str | None], None]):
    """Show a modeless text-entry window."""

    if _defer_if_needed(ask_text, title, message, initial, callback):
        return None
    import hou  # type: ignore
    QtCore, QtWidgets = _qt()
    dialog = QtWidgets.QDialog(hou.qt.mainWindow())
    dialog.setWindowTitle(title)
    dialog.setModal(False)
    dialog.setWindowModality(QtCore.Qt.WindowModality.NonModal)
    dialog.resize(600, 250)
    layout = QtWidgets.QVBoxLayout(dialog)
    label = QtWidgets.QLabel(message)
    label.setWordWrap(True)
    label.setTextInteractionFlags(
        QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(label)
    edit = QtWidgets.QLineEdit(initial)
    edit.selectAll()
    layout.addWidget(edit)
    row = QtWidgets.QHBoxLayout()
    row.addStretch(1)
    write = QtWidgets.QPushButton("Continue")
    cancel = QtWidgets.QPushButton("Cancel")
    row.addWidget(write)
    row.addWidget(cancel)
    layout.addLayout(row)
    selected = {"done": False}

    def finish(value):
        if selected["done"]:
            return
        selected["done"] = True
        dialog.close()
        QtCore.QTimer.singleShot(0, lambda v=value: callback(v))

    write.clicked.connect(lambda: finish(edit.text().strip()))
    edit.returnPressed.connect(lambda: finish(edit.text().strip()))
    cancel.clicked.connect(lambda: finish(None))
    dialog.rejected.connect(lambda: finish(None))
    _retain(dialog)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    edit.setFocus()
    return dialog
