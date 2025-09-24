from __future__ import annotations

"""Pomodoro timer service (Phase 9).

Features:
 - Configurable work/break lengths and cycles.
 - Auto-starts next period.
 - Emits transitions via Qt signals for UI & notification manager integration.
 - Optional sound hook (placeholder function call to integrate later).
"""

from dataclasses import dataclass
from typing import Optional
from PyQt6.QtCore import QObject, QTimer, pyqtSignal


@dataclass(slots=True)
class PomodoroConfig:
    work_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    cycles_before_long_break: int = 4


class PomodoroService(QObject):  # pragma: no cover time-based logic
    tick = pyqtSignal(int, str)  # remaining_seconds, phase
    phase_changed = pyqtSignal(str)  # work|short_break|long_break|idle
    cycle_completed = pyqtSignal(int)  # completed cycles count
    finished = pyqtSignal()  # after last long break when stopped manually

    def __init__(self, config: PomodoroConfig | None = None):
        super().__init__()
        self._config = config or PomodoroConfig()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)
        self._phase: str = "idle"
        self._remaining: int = 0
        self._current_cycle: int = 0
        self._running: bool = False

    # Public API -------------------------------------------------------
    def start(self) -> None:
        if self._running:
            return
        self._current_cycle = 0
        self._start_work_phase()
        self._running = True

    def stop(self) -> None:
        self._timer.stop()
        self._phase = "idle"
        self._remaining = 0
        self._running = False
        self.phase_changed.emit("idle")

    def config(self) -> PomodoroConfig:
        return self._config

    def update_config(self, cfg: PomodoroConfig) -> None:
        was_running = self._running
        if was_running:
            self.stop()
        self._config = cfg
        if was_running:
            self.start()

    # Internal ---------------------------------------------------------
    def _start_work_phase(self):
        self._phase = "work"
        self._remaining = self._config.work_minutes * 60
        self.phase_changed.emit(self._phase)
        self.tick.emit(self._remaining, self._phase)
        self._timer.start()

    def _start_short_break(self):
        self._phase = "short_break"
        self._remaining = self._config.short_break_minutes * 60
        self.phase_changed.emit(self._phase)
        self.tick.emit(self._remaining, self._phase)

    def _start_long_break(self):
        self._phase = "long_break"
        self._remaining = self._config.long_break_minutes * 60
        self.phase_changed.emit(self._phase)
        self.tick.emit(self._remaining, self._phase)

    def _on_tick(self):
        if self._remaining <= 0:
            self._advance_phase()
            return
        self._remaining -= 1
        self.tick.emit(self._remaining, self._phase)

    def _advance_phase(self):
        # End of a phase
        if self._phase == "work":
            self._current_cycle += 1
            self.cycle_completed.emit(self._current_cycle)
            if self._current_cycle % self._config.cycles_before_long_break == 0:
                self._start_long_break()
            else:
                self._start_short_break()
        elif self._phase in {"short_break", "long_break"}:
            # After long break we start a new work block automatically
            self._start_work_phase()
        else:  # idle
            self._timer.stop()


__all__ = ["PomodoroService", "PomodoroConfig"]
