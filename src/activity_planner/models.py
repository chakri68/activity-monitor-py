from __future__ import annotations

"""Dataclass models representing database entities."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


@dataclass(slots=True)
class Activity:
    id: Optional[int]
    title: str
    description: Optional[str]
    effort_level: int = 5
    created_at: Optional[str] = None


@dataclass(slots=True)
class ActivityInstance:
    id: Optional[int]
    activity_id: int
    start_time: str
    end_time: Optional[str]
    duration_seconds: Optional[int]
    created_at: Optional[str] = None


@dataclass(slots=True)
class Timetable:
    id: Optional[int]
    date: str  # YYYY-MM-DD
    mode: str  # CHILL or LOCKED_IN
    created_at: Optional[str] = None


@dataclass(slots=True)
class TimetableEntry:
    id: Optional[int]
    timetable_id: int
    activity_id: Optional[int]
    start_time: str
    end_time: str
    notes: Optional[str]
    created_at: Optional[str] = None


@dataclass(slots=True)
class Deadline:
    id: Optional[int]
    title: str
    due_date: str  # ISO date
    priority: int = 0
    effort_required: int = 0
    created_at: Optional[str] = None


__all__ = [
    "Activity",
    "ActivityInstance",
    "Timetable",
    "TimetableEntry",
    "Deadline",
    "utc_now_iso",
]
