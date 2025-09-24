from __future__ import annotations

"""Foreground window monitor for Windows with graceful no-op fallback on other OS.

Emits active_window(title, exe_path) when the foreground window *title or process*
changes (debounced). Poll interval ~700 ms to balance responsiveness (<1s lag)
and low CPU usage.
"""

from typing import Optional, Tuple
import sys
from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

AUTO_DETECT_KEY = "auto_detect_enabled"

IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:
    try:  # pragma: no cover - platform specific
        import win32gui  # type: ignore
        import win32process  # type: ignore
        import win32con  # type: ignore
        import psutil  # type: ignore
    except Exception as e:  # pragma: no cover
        win32gui = None  # type: ignore
        psutil = None  # type: ignore
else:  # Non Windows placeholders
    win32gui = None  # type: ignore
    psutil = None  # type: ignore


class _Worker(QObject):  # pragma: no cover - hard to unit test reliably cross-platform
    active_window = pyqtSignal(str, str)
    finished = pyqtSignal()

    def __init__(self, interval_ms: int = 700):
        super().__init__()
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._poll)
        self._last: Tuple[str, str] | None = None
        self._running = False

    def start(self):
        self._running = True
        self._timer.start()

    def stop(self):
        self._running = False
        self._timer.stop()
        self.finished.emit()

    # Windows-specific polling
    def _poll(self):
        if not self._running:
            return
        if not IS_WINDOWS or win32gui is None:  # safety
            return
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return
            title = win32gui.GetWindowText(hwnd) or ""
            if not title.strip():
                return
            # Get process exe
            tid, pid = win32process.GetWindowThreadProcessId(hwnd)
            exe = ""
            try:
                if psutil:
                    p = psutil.Process(pid)
                    exe = p.name() or ""
            except Exception:  # process might have exited
                exe = ""
            current = (title, exe)
            if current != self._last:
                self._last = current
                self.active_window.emit(title, exe)
        except Exception:
            # Swallow errors to avoid UI stutter
            pass


class WinActivityMonitor(QObject):
    active_window = pyqtSignal(str, str)  # title, exe
    started = pyqtSignal()
    stopped = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._thread: Optional[QThread] = None
        self._worker: Optional[_Worker] = None
        self._running = False

    def start(self):
        if self._running:
            return
        if not IS_WINDOWS:
            # No-op but still mark started for uniform UI behaviour
            self._running = True
            self.started.emit()
            return
        self._thread = QThread()
        self._worker = _Worker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start)
        self._worker.active_window.connect(self.active_window)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)
        self._thread.start()
        self._running = True
        self.started.emit()

    def stop(self):
        if not self._running:
            return
        if not IS_WINDOWS:
            self._running = False
            self.stopped.emit()
            return
        if self._worker:
            self._worker.stop()
        self._running = False
        self.stopped.emit()

    def _cleanup(self):  # pragma: no cover trivial
        self._worker = None
        self._thread = None

    @property
    def is_running(self) -> bool:
        return self._running


__all__ = ["WinActivityMonitor", "AUTO_DETECT_KEY", "IS_WINDOWS"]
