from __future__ import annotations

"""Dashboard UI containing the live timer and activity selector."""

from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QMessageBox,
)

from .timer_service import TimerService
from .activity_store import ActivityStore
from .repositories import set_setting, get_setting


def format_hhmmss(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class DashboardPage(QWidget):
    def __init__(self, db_manager, timer_service: TimerService, activity_store: ActivityStore):  # noqa: D401
        super().__init__()
        self._db = db_manager
        self._timer_service = timer_service
        self._store = activity_store
        self._current_instance_id: Optional[int] = None
        self.activity_combo = QComboBox()
        self._store.changed.connect(self.refresh_activities)
        self.refresh_activities()

        self.timer_label = QLabel("00:00:00")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.timer_label.font()
        font.setPointSize(24)
        self.timer_label.setFont(font)

        self.btn_start = QPushButton("Start")
        self.btn_pause = QPushButton("Pause")
        self.btn_resume = QPushButton("Resume")
        self.btn_stop = QPushButton("Stop")
        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(False)
        self.btn_stop.setEnabled(False)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_pause)
        btn_row.addWidget(self.btn_resume)
        btn_row.addWidget(self.btn_stop)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Current Activity:"))
        layout.addWidget(self.activity_combo)
        layout.addWidget(self.timer_label)
        layout.addLayout(btn_row)
        layout.addStretch(1)

        # Wire signals
        self.btn_start.clicked.connect(self._on_start)
        self.btn_pause.clicked.connect(self._on_pause)
        self.btn_resume.clicked.connect(self._on_resume)
        self.btn_stop.clicked.connect(self._on_stop)
        self._timer_service.tick.connect(self._on_tick)
        self._timer_service.started.connect(self._on_started)
        self._timer_service.stopped.connect(self._on_stopped)
        self._timer_service.state_changed.connect(self._on_state_changed)

    # --- Activity list --------------------------------------------------
    def refresh_activities(self) -> None:
        sel = self._store.get_selected_activity_id()
        self.activity_combo.blockSignals(True)
        self.activity_combo.clear()
        acts = self._store.activities()
        if not acts:
            self.activity_combo.addItem("No activities - create one first", -1)
            self.activity_combo.setEnabled(False)
        else:
            for a in acts:
                self.activity_combo.addItem(a.title, a.id)
            self.activity_combo.setEnabled(True)
            if sel is not None:
                idx = self.activity_combo.findData(sel)
                if idx >= 0:
                    self.activity_combo.setCurrentIndex(idx)
        self.activity_combo.blockSignals(False)
        self.activity_combo.currentIndexChanged.connect(self._persist_selection)

    def _persist_selection(self) -> None:  # pragma: no cover trivial
        act_id = self.activity_combo.currentData()
        if act_id in (None, -1):
            self._store.set_selected_activity_id(None)
        else:
            self._store.set_selected_activity_id(int(act_id))

    # --- Button handlers ------------------------------------------------
    def _on_start(self) -> None:
        activity_id = self.activity_combo.currentData()
        if activity_id in (None, -1):
            QMessageBox.information(self, "Activity Required", "Please create/select an activity first.")
            return
        self._current_instance_id = self._timer_service.start(int(activity_id))

    def _on_pause(self) -> None:  # pragma: no cover UI glue
        self._timer_service.pause()

    def _on_resume(self) -> None:  # pragma: no cover UI glue
        self._timer_service.resume()

    def _on_stop(self) -> None:  # pragma: no cover UI glue
        self._timer_service.stop()

    # --- Timer service callbacks ---------------------------------------
    def _on_tick(self, elapsed: int) -> None:
        self.timer_label.setText(format_hhmmss(elapsed))

    def _on_started(self, instance_id: int) -> None:  # pragma: no cover simple assignment
        self._current_instance_id = instance_id

    def _on_stopped(self, instance_id: int, duration: int) -> None:  # pragma: no cover UI
        self._current_instance_id = None
        self.timer_label.setText(format_hhmmss(0))

    def _on_state_changed(self, state: str) -> None:  # pragma: no cover UI logic
        if state == "running":
            self.btn_start.setEnabled(False)
            self.btn_pause.setEnabled(True)
            self.btn_resume.setEnabled(False)
            self.btn_stop.setEnabled(True)
        elif state == "paused":
            self.btn_start.setEnabled(False)
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(True)
            self.btn_stop.setEnabled(True)
        elif state == "idle":
            self.btn_start.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(False)
            self.btn_stop.setEnabled(False)


__all__ = ["DashboardPage", "format_hhmmss"]
