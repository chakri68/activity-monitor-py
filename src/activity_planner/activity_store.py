from __future__ import annotations

"""ActivityStore provides a cached list of activities with change signals."""

from typing import List, Optional
from PyQt6.QtCore import QObject, pyqtSignal

from .repositories import (
    list_activities,
    create_activity,
    update_activity,
    delete_activity,
    get_setting,
    set_setting,
)
from .models import Activity


SELECTED_KEY = "selected_activity_id"


class ActivityStore(QObject):
    changed = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, db):
        super().__init__()
        self._db = db
        self._activities: List[Activity] = []
        self._loaded = False

    # --- Loading --------------------------------------------------------
    def load(self) -> None:
        self._activities = list_activities(self._db)
        self._loaded = True
        self.changed.emit()

    # --- CRUD -----------------------------------------------------------
    def create(self, title: str, description: str | None, effort_level: int) -> Optional[Activity]:
        if not title.strip():
            self.error.emit("Title required")
            return None
        if not (1 <= effort_level <= 10):
            self.error.emit("Effort must be 1-10")
            return None
        # Unique check
        if any(a.title.lower() == title.strip().lower() for a in self._activities):
            self.error.emit("Activity title must be unique")
            return None
        a = create_activity(self._db, Activity(id=None, title=title.strip(), description=description, effort_level=effort_level))
        self._activities.append(a)
        self.changed.emit()
        return a

    def update(self, activity: Activity, *, title: str, description: str | None, effort_level: int) -> bool:
        if activity.id is None:
            self.error.emit("Activity has no id")
            return False
        if not title.strip():
            self.error.emit("Title required")
            return False
        if not (1 <= effort_level <= 10):
            self.error.emit("Effort must be 1-10")
            return False
        if any(a.id != activity.id and a.title.lower() == title.strip().lower() for a in self._activities):
            self.error.emit("Activity title must be unique")
            return False
        activity.title = title.strip()
        activity.description = description
        activity.effort_level = effort_level
        update_activity(self._db, activity)
        self.changed.emit()
        return True

    def delete(self, activity_id: int) -> bool:
        idx = next((i for i, a in enumerate(self._activities) if a.id == activity_id), None)
        if idx is None:
            return False
        delete_activity(self._db, activity_id)
        del self._activities[idx]
        self.changed.emit()
        # Clear selection if needed
        sel = self.get_selected_activity_id()
        if sel == activity_id:
            set_setting(self._db, SELECTED_KEY, "")
        return True

    # --- Access ---------------------------------------------------------
    def activities(self) -> List[Activity]:
        if not self._loaded:
            self.load()
        return list(self._activities)

    # --- Selection persistence -----------------------------------------
    def get_selected_activity_id(self) -> int | None:
        v = get_setting(self._db, SELECTED_KEY)
        if not v:
            return None
        try:
            return int(v)
        except ValueError:
            return None

    def set_selected_activity_id(self, activity_id: int | None) -> None:
        if activity_id is None:
            set_setting(self._db, SELECTED_KEY, "")
        else:
            set_setting(self._db, SELECTED_KEY, str(activity_id))

__all__ = ["ActivityStore", "SELECTED_KEY"]
