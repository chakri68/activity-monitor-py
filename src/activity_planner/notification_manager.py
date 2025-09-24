from __future__ import annotations

"""Notification & reminder manager.

Phase 7 features:
 - System tray icon with menu (Show/Hide, Snooze, Do Not Disturb, Quit)
 - Timetable slot start/end reminders
 - Snooze (re-show last start reminder after 5 minutes)
 - Do Not Disturb (suppresses visual notifications)
 - Timer ↔ Timetable sync (auto start/stop when slot boundaries hit)

Design notes:
 - We maintain a queue of (dt, kind, entry) events for today's timetable.
 - A single QTimer drives the next event; on trigger we process then schedule the next.
 - Auto start: If a slot start fires and timer idle -> start that activity automatically.
 - Auto stop/switch: If slot end fires and current timer running for that slot's activity -> stop. If next slot begins immediately (same moment) we chain start of next slot.
 - Snooze: Re-dispatches the *last start* notification toast after 5 minutes (does not alter auto timer behaviour).
 - Do Not Disturb: Hides toasts & tray balloon messages but logic (auto start/stop) still executes.

Limitations / Future:
 - Does not yet re-scan at midnight or handle multi‑day span; restart app for new day.
 - No per-slot user confirmation UI; future enhancement could add actionable popups.
"""

from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from typing import List, Literal, Optional, Tuple

from PyQt6.QtCore import QObject, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QWidget

from .database_manager import DatabaseManager
from .repositories import (
    get_timetable_by_date,
    list_timetable_entries,
    get_activity,
    get_setting,
    set_setting,
)
from .timer_service import TimerService
from .activity_store import ActivityStore
from .toast import show_toast


EventKind = Literal["start", "end"]


@dataclass(slots=True)
class TimetableEvent:
    when: datetime
    kind: EventKind
    entry_id: int
    activity_id: int
    start_time: str
    end_time: str
    notes: str


def _parse_hhmm(hhmm: str) -> time:
    hh, mm = hhmm.split(":")
    return time(int(hh), int(mm))


class NotificationManager(QObject):  # pragma: no cover - UI heavy
    # Signals for potential test hooks / UI updates later
    slot_start = pyqtSignal(int)  # activity_id
    slot_end = pyqtSignal(int)    # activity_id

    DND_KEY = "notifications.dnd"

    def __init__(self, parent: QWidget, db: DatabaseManager, timer: TimerService, store: ActivityStore) -> None:
        super().__init__(parent)
        self._db = db
        self._timer_service = timer
        self._store = store
        self._parent_widget = parent

        self._tray = QSystemTrayIcon(parent)
        self._tray.setToolTip("Activity Planner")
        # Basic fallback icon (empty); downstream packaging can bundle an icon file.
        self._tray.setIcon(QIcon())
        self._tray.setVisible(True)

        self._menu = QMenu()
        self._act_show = self._menu.addAction("Show / Hide")
        self._act_snooze = self._menu.addAction("Snooze 5m")
        self._act_dnd = self._menu.addAction("Do Not Disturb")
        self._act_dnd.setCheckable(True)
        dnd_enabled = self._is_dnd()
        self._act_dnd.setChecked(dnd_enabled)
        self._menu.addSeparator()
        self._act_quit = self._menu.addAction("Quit")
        self._tray.setContextMenu(self._menu)

        self._act_show.triggered.connect(self._toggle_main_visibility)
        self._act_snooze.triggered.connect(self.snooze_current)
        self._act_dnd.toggled.connect(self._set_dnd)
        self._act_quit.triggered.connect(QApplication.instance().quit)  # type: ignore[arg-type]

        # Scheduling
        self._events: List[TimetableEvent] = []
        self._event_timer = QTimer(self)
        self._event_timer.setSingleShot(True)
        self._event_timer.timeout.connect(self._process_next_event)

        self._last_start_notification: Optional[TimetableEvent] = None
        self._snooze_timer: Optional[QTimer] = None

        self._build_today_schedule()

    # --- Public API ----------------------------------------------------
    def refresh(self) -> None:
        self._build_today_schedule()

    def snooze_current(self) -> None:
        if not self._last_start_notification:
            return
        if self._snooze_timer:
            self._snooze_timer.stop()
        self._snooze_timer = QTimer(self)
        self._snooze_timer.setSingleShot(True)
        self._snooze_timer.timeout.connect(lambda: self._show_start_notification(self._last_start_notification))
        self._snooze_timer.start(5 * 60 * 1000)  # 5 minutes
        self._notify("Snoozed reminder for 5 minutes")

    # --- Internal: DND -------------------------------------------------
    def _is_dnd(self) -> bool:
        val = get_setting(self._db, self.DND_KEY)
        return val == "1"

    def _set_dnd(self, enabled: bool) -> None:
        set_setting(self._db, self.DND_KEY, "1" if enabled else "0")
        self._notify("Do Not Disturb ON" if enabled else "Do Not Disturb OFF", force_tray=True)

    # --- Scheduling -----------------------------------------------------
    def _build_today_schedule(self) -> None:
        self._events.clear()
        today = date.today().isoformat()
        tt = get_timetable_by_date(self._db, today)
        if not tt:
            return
        entries = list_timetable_entries(self._db, tt.id)  # type: ignore[arg-type]
        now = datetime.now()
        for e in entries:
            try:
                st = _parse_hhmm(e.start_time)
                et = _parse_hhmm(e.end_time)
            except Exception:
                continue
            start_dt = datetime.combine(now.date(), st)
            end_dt = datetime.combine(now.date(), et)
            if end_dt <= start_dt:
                continue  # skip invalid or overnight for now
            self._events.append(
                TimetableEvent(start_dt, "start", e.id, e.activity_id, e.start_time, e.end_time, e.notes or "")
            )
            self._events.append(
                TimetableEvent(end_dt, "end", e.id, e.activity_id, e.start_time, e.end_time, e.notes or "")
            )
        self._events.sort(key=lambda ev: ev.when)
        self._schedule_next()

    def _schedule_next(self) -> None:
        self._event_timer.stop()
        now = datetime.now()
        # Remove past events (already elapsed)
        while self._events and self._events[0].when <= now:
            self._events.pop(0)
        if not self._events:
            return
        next_ev = self._events[0]
        delta_ms = max(0, int((next_ev.when - now).total_seconds() * 1000))
        self._event_timer.start(delta_ms)

    def _process_next_event(self) -> None:
        if not self._events:
            return
        ev = self._events.pop(0)
        if ev.kind == "start":
            self._handle_slot_start(ev)
        else:
            self._handle_slot_end(ev)
        self._schedule_next()

    # --- Event Handlers ------------------------------------------------
    def _handle_slot_start(self, ev: TimetableEvent) -> None:
        self._last_start_notification = ev
        self._show_start_notification(ev)
        # Auto start timer if idle
        if self._timer_service.state == "idle":
            try:
                self._timer_service.start(ev.activity_id)
            except Exception:
                pass
        self.slot_start.emit(ev.activity_id)

    def _handle_slot_end(self, ev: TimetableEvent) -> None:
        # Stop timer if running for this activity
        if self._timer_service.state in {"running", "paused"} and self._timer_service.current_activity_id == ev.activity_id:
            self._timer_service.stop()
        self._notify(f"Slot ended: {self._activity_title(ev.activity_id)}")
        # If next event is an immediate start (same timestamp) trigger it early
        if self._events and self._events[0].kind == "start" and abs((self._events[0].when - ev.when).total_seconds()) < 1:
            next_ev = self._events.pop(0)
            self._handle_slot_start(next_ev)
        self.slot_end.emit(ev.activity_id)

    # --- Notification helpers -----------------------------------------
    def _show_start_notification(self, ev: TimetableEvent) -> None:
        title = self._activity_title(ev.activity_id)
        note_part = f" – {ev.notes}" if ev.notes else ""
        self._notify(f"Slot starting: {title}{note_part}")

    def _activity_title(self, activity_id: int) -> str:
        act = get_activity(self._db, activity_id)
        return act.title if act else f"Activity {activity_id}"

    def _notify(self, message: str, *, force_tray: bool = False) -> None:
        if not force_tray and self._is_dnd():
            return
        # Toast in main window
        show_toast(self._parent_widget, message)
        # Tray balloon (no-op on some platforms)
        try:
            self._tray.showMessage("Activity Planner", message, QSystemTrayIcon.MessageIcon.NoIcon, 3000)
        except Exception:
            pass

    # --- UI actions ----------------------------------------------------
    def _toggle_main_visibility(self) -> None:
        w = self._parent_widget
        if w.isVisible():
            w.hide()
        else:
            # If hidden, show & raise
            w.show()
            w.activateWindow()


__all__ = ["NotificationManager"]
