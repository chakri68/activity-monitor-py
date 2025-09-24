from __future__ import annotations

"""Simple toast notification overlay widget."""

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QLabel, QWidget


class Toast(QLabel):  # pragma: no cover - UI utility
    def __init__(self, parent: QWidget, message: str, timeout_ms: int = 2500):
        super().__init__(parent)
        self.setText(message)
        self.setStyleSheet(
            """
            background: rgba(40,40,40,0.85);
            color: #fff; padding: 6px 12px; border-radius: 6px;
            """
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.adjustSize()
        w = parent.width()
        self.move(int((w - self.width()) / 2), 30)
        self.show()
        QTimer.singleShot(timeout_ms, self.close)


def show_toast(parent: QWidget, message: str, timeout_ms: int = 2500) -> None:  # pragma: no cover
    Toast(parent, message, timeout_ms)

__all__ = ["show_toast"]
