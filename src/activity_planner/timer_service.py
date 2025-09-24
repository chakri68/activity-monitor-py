from __future__ import annotations

"""Timer service handling start/pause/resume/stop and persistence.

Design:
 - Creates an activity_instance row on start (end_time, duration_seconds NULL).
 - Updates the row on stop with end_time + duration_seconds.
 - Maintains internal state machine: idle -> running -> paused -> running ... -> idle.
 - Emits Qt signals for UI binding.
"""

from datetime import datetime
from typing import Callable, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .database_manager import DatabaseManager
from .models import ActivityInstance
from .repositories import (
    create_activity_instance,
    update_activity_instance_end,
    get_activity_instance,
)

TimeProvider = Callable[[], datetime]


def _dt_to_iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat() + "Z"


class TimerService(QObject):
    tick = pyqtSignal(int)  # elapsed seconds
    started = pyqtSignal(int)  # activity_instance_id
    paused = pyqtSignal()
    resumed = pyqtSignal()
    stopped = pyqtSignal(int, int)  # instance_id, duration_seconds
    state_changed = pyqtSignal(str)

    def __init__(self, db: DatabaseManager, time_provider: Optional[TimeProvider] = None) -> None:
        super().__init__()
        self._db = db
        self._time_provider: TimeProvider = time_provider or datetime.utcnow
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

        self._state: str = "idle"
        self._activity_id: Optional[int] = None
        self._instance_id: Optional[int] = None
        self._start_dt: Optional[datetime] = None
        self._paused_accum: int = 0  # seconds accumulated before last pause
        self._last_resume_dt: Optional[datetime] = None

    # --- Properties -----------------------------------------------------
    @property
    def state(self) -> str:
        return self._state

    def _set_state(self, new_state: str) -> None:
        if new_state != self._state:
            self._state = new_state
            self.state_changed.emit(new_state)

    # --- Public API -----------------------------------------------------
    @property
    def current_activity_id(self) -> Optional[int]:
        return self._activity_id

    def start(self, activity_id: int) -> int:
        if self._state in {"running", "paused"}:
            raise RuntimeError("Timer already active; stop or reset before starting a new one")
        now = self._time_provider()
        self._activity_id = activity_id
        self._start_dt = now
        self._last_resume_dt = now
        instance = create_activity_instance(
            self._db,
            ActivityInstance(
                id=None,
                activity_id=activity_id,
                start_time=_dt_to_iso(now),
                end_time=None,
                duration_seconds=None,
            ),
        )
        self._instance_id = instance.id
        self._paused_accum = 0
        self._timer.start()
        self._set_state("running")
        self.started.emit(self._instance_id)  # type: ignore[arg-type]
        self.tick.emit(0)
        return self._instance_id  # type: ignore[return-value]

    def pause(self) -> None:
        if self._state != "running":
            return
        now = self._time_provider()
        if self._last_resume_dt:
            self._paused_accum += int((now - self._last_resume_dt).total_seconds())
        self._timer.stop()
        self._set_state("paused")
        self.paused.emit()

    def resume(self) -> None:
        if self._state != "paused":
            return
        self._last_resume_dt = self._time_provider()
        self._timer.start()
        self._set_state("running")
        self.resumed.emit()

    def stop(self) -> Optional[int]:
        if self._state == "idle":
            return None
        self._timer.stop()
        end_dt = self._time_provider()
        if self._state == "running" and self._last_resume_dt:
            self._paused_accum += int((end_dt - self._last_resume_dt).total_seconds())
        # If paused, _paused_accum already holds elapsed
        duration = self._paused_accum
        inst_id = self._instance_id
        if inst_id is not None:
            update_activity_instance_end(
                self._db, inst_id, _dt_to_iso(end_dt), duration_seconds=duration
            )
        self._activity_id = None
        self._instance_id = None
        self._start_dt = None
        self._last_resume_dt = None
        self._paused_accum = 0
        self._set_state("idle")
        if inst_id is not None:
            self.stopped.emit(inst_id, duration)
        return inst_id

    # --- Internal -------------------------------------------------------
    def _on_tick(self) -> None:
        if self._state != "running" or not self._last_resume_dt:
            return
        now = self._time_provider()
        elapsed = self._paused_accum + int((now - self._last_resume_dt).total_seconds())
        self.tick.emit(elapsed)

    # --- Utility --------------------------------------------------------
    def get_instance(self, instance_id: int) -> ActivityInstance | None:
        return get_activity_instance(self._db, instance_id)


__all__ = ["TimerService"]
