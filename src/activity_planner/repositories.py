from __future__ import annotations

"""Repository helper functions for CRUD operations."""

from typing import Iterable, Sequence
import sqlite3

from .database_manager import DatabaseManager
from .models import (
    Activity,
    ActivityInstance,
    Deadline,
    Timetable,
    TimetableEntry,
)


# --- Generic helpers -------------------------------------------------------

def _last_row_id(cur: sqlite3.Cursor) -> int:
    return int(cur.lastrowid)  # type: ignore[arg-type]


# --- Activity ---------------------------------------------------------------

def create_activity(db: DatabaseManager, activity: Activity) -> Activity:
    cur = db.execute(
        "INSERT INTO activities (title, description, effort_level) VALUES (?,?,?)",
        (activity.title, activity.description, activity.effort_level),
    )
    activity.id = _last_row_id(cur)
    row = db.query_one("SELECT * FROM activities WHERE id=?", (activity.id,))
    if row:
        activity.created_at = row["created_at"]
    return activity


def get_activity(db: DatabaseManager, activity_id: int) -> Activity | None:
    row = db.query_one("SELECT * FROM activities WHERE id=?", (activity_id,))
    if not row:
        return None
    return Activity(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        effort_level=row["effort_level"],
        created_at=row["created_at"],
    )


def list_activities(db: DatabaseManager) -> list[Activity]:
    rows = db.query_all("SELECT * FROM activities ORDER BY id")
    return [
        Activity(
            id=r["id"],
            title=r["title"],
            description=r["description"],
            effort_level=r["effort_level"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


def update_activity(db: DatabaseManager, activity: Activity) -> None:
    assert activity.id is not None, "Activity must have id to update"
    db.execute(
        "UPDATE activities SET title=?, description=?, effort_level=? WHERE id=?",
        (activity.title, activity.description, activity.effort_level, activity.id),
    )


def delete_activity(db: DatabaseManager, activity_id: int) -> None:
    db.execute("DELETE FROM activities WHERE id=?", (activity_id,))


# --- Deadlines --------------------------------------------------------------

def create_deadline(db: DatabaseManager, deadline: Deadline) -> Deadline:
    cur = db.execute(
        "INSERT INTO deadlines (title, due_date, priority, effort_required) VALUES (?,?,?,?)",
        (deadline.title, deadline.due_date, deadline.priority, deadline.effort_required),
    )
    deadline.id = _last_row_id(cur)
    row = db.query_one("SELECT * FROM deadlines WHERE id=?", (deadline.id,))
    if row:
        deadline.created_at = row["created_at"]
    return deadline


def get_deadline(db: DatabaseManager, deadline_id: int) -> Deadline | None:
    row = db.query_one("SELECT * FROM deadlines WHERE id=?", (deadline_id,))
    if not row:
        return None
    return Deadline(
        id=row["id"],
        title=row["title"],
        due_date=row["due_date"],
        priority=row["priority"],
        effort_required=row["effort_required"],
        created_at=row["created_at"],
    )


def list_deadlines(db: DatabaseManager) -> list[Deadline]:
    rows = db.query_all("SELECT * FROM deadlines ORDER BY due_date")
    return [
        Deadline(
            id=r["id"],
            title=r["title"],
            due_date=r["due_date"],
            priority=r["priority"],
            effort_required=r["effort_required"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


def update_deadline(db: DatabaseManager, deadline: Deadline) -> None:
    assert deadline.id is not None
    db.execute(
        "UPDATE deadlines SET title=?, due_date=?, priority=?, effort_required=? WHERE id=?",
        (
            deadline.title,
            deadline.due_date,
            deadline.priority,
            deadline.effort_required,
            deadline.id,
        ),
    )


def delete_deadline(db: DatabaseManager, deadline_id: int) -> None:
    db.execute("DELETE FROM deadlines WHERE id=?", (deadline_id,))


# --- Timetables & Entries ---------------------------------------------------

def create_timetable(db: DatabaseManager, timetable: Timetable) -> Timetable:
    cur = db.execute(
        "INSERT INTO timetables (date, mode) VALUES (?,?)",
        (timetable.date, timetable.mode),
    )
    timetable.id = _last_row_id(cur)
    row = db.query_one("SELECT * FROM timetables WHERE id=?", (timetable.id,))
    if row:
        timetable.created_at = row["created_at"]
    return timetable


def get_timetable_by_date(db: DatabaseManager, date: str) -> Timetable | None:
    row = db.query_one("SELECT * FROM timetables WHERE date=?", (date,))
    if not row:
        return None
    return Timetable(
        id=row["id"], date=row["date"], mode=row["mode"], created_at=row["created_at"]
    )


def list_timetables(db: DatabaseManager) -> list[Timetable]:
    rows = db.query_all("SELECT * FROM timetables ORDER BY date")
    return [
        Timetable(id=r["id"], date=r["date"], mode=r["mode"], created_at=r["created_at"]) for r in rows
    ]


def create_timetable_entry(db: DatabaseManager, entry: TimetableEntry) -> TimetableEntry:
    cur = db.execute(
        """
        INSERT INTO timetable_entries (timetable_id, activity_id, start_time, end_time, notes)
        VALUES (?,?,?,?,?)
        """,
        (entry.timetable_id, entry.activity_id, entry.start_time, entry.end_time, entry.notes),
    )
    entry.id = _last_row_id(cur)
    row = db.query_one("SELECT * FROM timetable_entries WHERE id=?", (entry.id,))
    if row:
        entry.created_at = row["created_at"]
    return entry


def list_timetable_entries(db: DatabaseManager, timetable_id: int) -> list[TimetableEntry]:
    rows = db.query_all(
        "SELECT * FROM timetable_entries WHERE timetable_id=? ORDER BY start_time",
        (timetable_id,),
    )
    return [
        TimetableEntry(
            id=r["id"],
            timetable_id=r["timetable_id"],
            activity_id=r["activity_id"],
            start_time=r["start_time"],
            end_time=r["end_time"],
            notes=r["notes"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


def delete_timetable(db: DatabaseManager, timetable_id: int) -> None:
    db.execute("DELETE FROM timetables WHERE id=?", (timetable_id,))


# --- Activity Instances -----------------------------------------------------

def create_activity_instance(db: DatabaseManager, instance: ActivityInstance) -> ActivityInstance:
    cur = db.execute(
        """
        INSERT INTO activity_instances (activity_id, start_time, end_time, duration_seconds)
        VALUES (?,?,?,?)
        """,
        (
            instance.activity_id,
            instance.start_time,
            instance.end_time,
            instance.duration_seconds,
        ),
    )
    instance.id = _last_row_id(cur)
    row = db.query_one("SELECT * FROM activity_instances WHERE id=?", (instance.id,))
    if row:
        instance.created_at = row["created_at"]
    return instance


def update_activity_instance_end(db: DatabaseManager, instance_id: int, end_time: str, duration_seconds: int) -> None:
    db.execute(
        "UPDATE activity_instances SET end_time=?, duration_seconds=? WHERE id=?",
        (end_time, duration_seconds, instance_id),
    )


def get_activity_instance(db: DatabaseManager, instance_id: int) -> ActivityInstance | None:
    row = db.query_one("SELECT * FROM activity_instances WHERE id=?", (instance_id,))
    if not row:
        return None
    return ActivityInstance(
        id=row["id"],
        activity_id=row["activity_id"],
        start_time=row["start_time"],
        end_time=row["end_time"],
        duration_seconds=row["duration_seconds"],
        created_at=row["created_at"],
    )


__all__ = [
    # Activities
    "create_activity",
    "get_activity",
    "list_activities",
    "update_activity",
    "delete_activity",
    # Deadlines
    "create_deadline",
    "get_deadline",
    "list_deadlines",
    "update_deadline",
    "delete_deadline",
    # Timetables
    "create_timetable",
    "get_timetable_by_date",
    "list_timetables",
    "create_timetable_entry",
    "list_timetable_entries",
    "delete_timetable",
    # Activity Instances
    "create_activity_instance",
    "update_activity_instance_end",
    "get_activity_instance",
]

# --- Settings ---------------------------------------------------------------

def get_setting(db: DatabaseManager, key: str) -> str | None:
    row = db.query_one("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row else None


def set_setting(db: DatabaseManager, key: str, value: str) -> None:
    conn = db.connect()
    with conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

__all__ += ["get_setting", "set_setting"]
