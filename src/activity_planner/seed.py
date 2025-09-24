"""Seed data helper for development convenience."""

from .database_manager import DatabaseManager
from .models import Activity, Deadline
from .repositories import create_activity, create_deadline


def seed_basic_data(db: DatabaseManager) -> None:  # pragma: no cover - optional utility
    if db.query_one("SELECT id FROM activities LIMIT 1"):
        return  # Already seeded
    create_activity(db, Activity(id=None, title="Reading", description="Books", effort_level=3))
    create_activity(db, Activity(id=None, title="Coding", description="Dev work", effort_level=7))
    create_deadline(
        db,
        Deadline(
            id=None,
            title="Sample Deadline",
            due_date="2030-01-01",
            priority=1,
            effort_required=5,
        ),
    )

__all__ = ["seed_basic_data"]
