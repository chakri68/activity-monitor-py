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
    QCheckBox,
)

from .timer_service import TimerService
from .activity_store import ActivityStore
from .repositories import set_setting, get_setting
from .win_activity_monitor import AUTO_DETECT_KEY, WinActivityMonitor
from .gemini_planner import TitleCategorizer


def format_hhmmss(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class DashboardPage(QWidget):
    def __init__(self, db_manager, timer_service: TimerService, activity_store: ActivityStore, monitor: WinActivityMonitor | None = None, categorizer: TitleCategorizer | None = None):  # noqa: D401
        super().__init__()
        self._db = db_manager
        self._timer_service = timer_service
        self._store = activity_store
        self._monitor = monitor
        self._categorizer = categorizer
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
        # Auto-detect row
        detect_row = QHBoxLayout()
        self.auto_detect_checkbox = QCheckBox("Auto-detect activities")
        self.auto_detect_status = QLabel("OFF")
        self.auto_detect_status.setStyleSheet("color: #a33; font-weight: bold;")
        self.auto_detect_checkbox.setToolTip(
            "When enabled, foreground window titles are monitored locally to suggest or auto-start activities. No raw titles are uploaded unless you opt-in later."
        )
        detect_row.addWidget(self.auto_detect_checkbox)
        detect_row.addWidget(self.auto_detect_status)
        detect_row.addStretch(1)
        layout.addLayout(detect_row)
        # Suggestion banner (hidden by default)
        self.suggest_banner = QWidget()
        sb_layout = QHBoxLayout(self.suggest_banner)
        self.suggest_label = QLabel("")
        self.btn_switch = QPushButton("Switch")
        self.btn_ignore = QPushButton("Ignore")
        self.btn_always = QPushButton("Always map this")
        for w in (self.suggest_label, self.btn_switch, self.btn_ignore, self.btn_always):
            sb_layout.addWidget(w)
        sb_layout.addStretch(1)
        self.suggest_banner.hide()
        layout.addWidget(self.suggest_banner)
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
        if self._monitor:
            self._monitor.active_window.connect(self._on_active_window)
            self._monitor.started.connect(lambda: self._update_monitor_status(True))
            self._monitor.stopped.connect(lambda: self._update_monitor_status(False))
        self.auto_detect_checkbox.toggled.connect(self._on_auto_detect_toggled)
        if self._categorizer:
            self._categorizer.suggestion_ready.connect(self._on_suggestion)
        # Initialize checkbox from settings
        enabled = get_setting(self._db, AUTO_DETECT_KEY) == "1"
        self.auto_detect_checkbox.setChecked(enabled)
        if enabled and self._monitor:
            self._monitor.start()

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

    # --- Auto-detect handlers ------------------------------------------
    def _on_auto_detect_toggled(self, checked: bool) -> None:  # pragma: no cover UI
        set_setting(self._db, AUTO_DETECT_KEY, "1" if checked else "0")
        if self._monitor:
            if checked:
                self._monitor.start()
            else:
                self._monitor.stop()
        else:
            self._update_monitor_status(False)

    def _update_monitor_status(self, running: bool) -> None:  # pragma: no cover UI
        if running:
            self.auto_detect_status.setText("ON")
            self.auto_detect_status.setStyleSheet("color: #2a2; font-weight: bold;")
        else:
            self.auto_detect_status.setText("OFF")
            self.auto_detect_status.setStyleSheet("color: #a33; font-weight: bold;")

    def _on_active_window(self, title: str, exe: str) -> None:  # pragma: no cover placeholder
        if self.auto_detect_checkbox.isChecked() and self._categorizer:
            self._categorizer.submit_title(title)

    # --- Suggestion banner -------------------------------------------------
    def _on_suggestion(self, category: str, confidence: float, original_title: str):  # pragma: no cover UI
        # Only show if different from current selected activity
        current_data = self.activity_combo.currentData()
        current_title = None
        if current_data not in (None, -1):
            idx = self.activity_combo.currentIndex()
            current_title = self.activity_combo.itemText(idx)
        if current_title == category:
            return
        self._pending_category = category
        self._pending_original_title = original_title
        self.suggest_label.setText(f"Switch to {category}? ({confidence:.0%})")
        self.suggest_banner.show()
        self.btn_switch.clicked.connect(self._apply_suggestion)
        self.btn_ignore.clicked.connect(self._ignore_suggestion)
        self.btn_always.clicked.connect(self._always_map_suggestion)

    def _apply_suggestion(self):  # pragma: no cover UI
        self._select_activity_title(self._pending_category)
        self._hide_banner()

    def _ignore_suggestion(self):  # pragma: no cover UI
        self._hide_banner()

    def _always_map_suggestion(self):  # pragma: no cover UI
        from .repositories import create_title_mapping_rule, list_activities

        acts = self._store.activities()
        target = next((a for a in acts if a.title == self._pending_category), None)
        if target and self._pending_original_title:
            create_title_mapping_rule(self._db, self._pending_original_title, target.id)  # type: ignore[arg-type]
        self._select_activity_title(self._pending_category)
        self._hide_banner()

    def _select_activity_title(self, title: str):  # pragma: no cover UI
        idx = self.activity_combo.findText(title, Qt.MatchFlag.MatchExactly)
        if idx >= 0:
            self.activity_combo.setCurrentIndex(idx)

    def _hide_banner(self):  # pragma: no cover UI
        self.suggest_banner.hide()
        for btn in (self.btn_switch, self.btn_ignore, self.btn_always):
            try:
                btn.clicked.disconnect()
            except Exception:  # already disconnected
                pass

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
