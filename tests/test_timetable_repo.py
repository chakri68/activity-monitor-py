from activity_planner.models import Timetable, TimetableEntry, Activity
from activity_planner.repositories import (
    create_timetable,
    get_timetable_by_date,
    list_timetables,
    create_timetable_entry,
    list_timetable_entries,
    create_activity,
)


def test_timetable_and_entries(db):
    t = create_timetable(db, Timetable(id=None, date="2025-02-01", mode="CHILL"))
    assert t.id is not None
    assert get_timetable_by_date(db, "2025-02-01") is not None
    a = create_activity(db, Activity(id=None, title="Focus", description=None, effort_level=6))
    e = create_timetable_entry(
        db,
        TimetableEntry(
            id=None,
            timetable_id=t.id,  # type: ignore[arg-type]
            activity_id=a.id,  # type: ignore[arg-type]
            start_time="2025-02-01T09:00:00Z",
            end_time="2025-02-01T10:00:00Z",
            notes="Morning block",
        ),
    )
    assert e.id is not None
    entries = list_timetable_entries(db, t.id)
    assert len(entries) == 1 and entries[0].notes == "Morning block"
    assert len(list_timetables(db)) >= 1
