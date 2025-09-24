from __future__ import annotations

"""Settings & Themes page (Phase 9 core)."""

import json
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QPushButton, QSpinBox, QFileDialog, QComboBox
)

from .database_manager import DatabaseManager
from .repositories import get_setting, set_setting
from .pomodoro import PomodoroService, PomodoroConfig
from .toast import show_toast
from .win_activity_monitor import AUTO_DETECT_KEY
from .rule_manager import RuleManagerDialog


THEME_KEY = "ui.theme"  # light|dark
POMO_WORK = "pomo.work"
POMO_SB = "pomo.short"
POMO_LB = "pomo.long"
POMO_CYC = "pomo.cycles"
NOTIFY_DND = "notifications.dnd"  # already used
AUTO_SWITCH = "auto_switch.enabled"
AUTO_START = "auto_switch.start_timer"
AUTO_CONF_THRESHOLD = "auto_switch.conf_threshold"


class SettingsPage(QWidget):  # pragma: no cover UI heavy
    def __init__(self, db: DatabaseManager, pomo: PomodoroService, apply_theme_cb):
        super().__init__()
        self._db = db
        self._pomo = pomo
        self._apply_theme_cb = apply_theme_cb

        layout = QVBoxLayout(self)
        # Theme
        theme_row = QHBoxLayout(); theme_row.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox(); self.theme_combo.addItems(["light", "dark"])
        theme_row.addWidget(self.theme_combo); theme_row.addStretch(1)
        layout.addLayout(theme_row)

        # Auto detect toggle (mirror dashboard)
        self.auto_detect_cb = QCheckBox("Enable Auto-Detect")
        layout.addWidget(self.auto_detect_cb)

        # Notifications DND toggle
        self.dnd_cb = QCheckBox("Do Not Disturb (suppress popups)")
        layout.addWidget(self.dnd_cb)

        # Auto switch group
        layout.addWidget(QLabel("Auto Switch Behaviour"))
        auto_row = QHBoxLayout()
        self.auto_switch_cb = QCheckBox("Automatically switch activity when confident")
        self.auto_start_cb = QCheckBox("Start timer on auto switch if idle")
        self.conf_spin = QSpinBox(); self.conf_spin.setRange(10, 100); self.conf_spin.setSuffix("%")
        auto_row.addWidget(self.auto_switch_cb)
        auto_row.addWidget(self.auto_start_cb)
        auto_row.addWidget(QLabel("Min Confidence:"))
        auto_row.addWidget(self.conf_spin)
        auto_row.addStretch(1)
        layout.addLayout(auto_row)

        # Pomodoro config
        layout.addWidget(QLabel("Pomodoro Configuration (minutes)"))
        pomo_row = QHBoxLayout()
        self.work_spin = QSpinBox(); self.work_spin.setRange(1, 180)
        self.short_spin = QSpinBox(); self.short_spin.setRange(1, 60)
        self.long_spin = QSpinBox(); self.long_spin.setRange(1, 180)
        self.cycles_spin = QSpinBox(); self.cycles_spin.setRange(1, 12)
        for lbl, w in [("Work", self.work_spin), ("Short Break", self.short_spin), ("Long Break", self.long_spin), ("Cycles/Long", self.cycles_spin)]:
            pomo_row.addWidget(QLabel(lbl)); pomo_row.addWidget(w)
        pomo_row.addStretch(1)
        layout.addLayout(pomo_row)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_save = QPushButton("Save Settings")
        self.btn_export = QPushButton("Export JSON")
        self.btn_import = QPushButton("Import JSON")
        self.btn_rules = QPushButton("Manage Title Rules")
        for b in (self.btn_save, self.btn_export, self.btn_import, self.btn_rules):
            btn_row.addWidget(b)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        layout.addStretch(1)

        self._load_settings()

        self.btn_save.clicked.connect(self._save)
        self.btn_export.clicked.connect(self._export)
        self.btn_import.clicked.connect(self._import)
        self.btn_rules.clicked.connect(self._open_rules)

    # --- Core ---------------------------------------------------------
    def _load_settings(self):
        theme = get_setting(self._db, THEME_KEY) or "light"
        idx = self.theme_combo.findText(theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.auto_detect_cb.setChecked(get_setting(self._db, AUTO_DETECT_KEY) == "1")
        self.dnd_cb.setChecked(get_setting(self._db, NOTIFY_DND) == "1")
        # Auto switch settings
        self.auto_switch_cb.setChecked(get_setting(self._db, AUTO_SWITCH) == "1")
        self.auto_start_cb.setChecked(get_setting(self._db, AUTO_START) == "1")
        self.conf_spin.setValue(int(float(get_setting(self._db, AUTO_CONF_THRESHOLD) or 65)))
        # Pomodoro
        self.work_spin.setValue(int(get_setting(self._db, POMO_WORK) or 25))
        self.short_spin.setValue(int(get_setting(self._db, POMO_SB) or 5))
        self.long_spin.setValue(int(get_setting(self._db, POMO_LB) or 15))
        self.cycles_spin.setValue(int(get_setting(self._db, POMO_CYC) or 4))

    def _save(self):
        theme = self.theme_combo.currentText()
        set_setting(self._db, THEME_KEY, theme)
        set_setting(self._db, AUTO_DETECT_KEY, "1" if self.auto_detect_cb.isChecked() else "0")
        set_setting(self._db, NOTIFY_DND, "1" if self.dnd_cb.isChecked() else "0")
        set_setting(self._db, AUTO_SWITCH, "1" if self.auto_switch_cb.isChecked() else "0")
        set_setting(self._db, AUTO_START, "1" if self.auto_start_cb.isChecked() else "0")
        set_setting(self._db, AUTO_CONF_THRESHOLD, str(self.conf_spin.value()))
        set_setting(self._db, POMO_WORK, str(self.work_spin.value()))
        set_setting(self._db, POMO_SB, str(self.short_spin.value()))
        set_setting(self._db, POMO_LB, str(self.long_spin.value()))
        set_setting(self._db, POMO_CYC, str(self.cycles_spin.value()))
        # Apply theme live
        self._apply_theme_cb(theme)
        # Update Pomodoro config
        self._pomo.update_config(
            PomodoroConfig(
                work_minutes=self.work_spin.value(),
                short_break_minutes=self.short_spin.value(),
                long_break_minutes=self.long_spin.value(),
                cycles_before_long_break=self.cycles_spin.value(),
            )
        )
        show_toast(self, "Settings saved")

    # --- Export/Import ------------------------------------------------
    def _export(self):  # pragma: no cover UI
        path, _ = QFileDialog.getSaveFileName(self, "Export Settings", filter="JSON (*.json)")
        if not path:
            return
        keys = [THEME_KEY, AUTO_DETECT_KEY, NOTIFY_DND, AUTO_SWITCH, AUTO_START, AUTO_CONF_THRESHOLD, POMO_WORK, POMO_SB, POMO_LB, POMO_CYC]
        data = {k: (get_setting(self._db, k) or "") for k in keys}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        show_toast(self, "Exported")

    def _import(self):  # pragma: no cover UI
        path, _ = QFileDialog.getOpenFileName(self, "Import Settings", filter="JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                set_setting(self._db, k, str(v))
            show_toast(self, "Imported")
            self._load_settings()
            self._apply_theme_cb(get_setting(self._db, THEME_KEY) or "light")
        except Exception as e:
            show_toast(self, f"Import failed: {e}")

    def _open_rules(self):  # pragma: no cover UI
        dlg = RuleManagerDialog(self._db, self)
        dlg.exec()


__all__ = ["SettingsPage", "THEME_KEY"]
