from activity_planner.models import Activity, ActivityInstance
from activity_planner.repositories import (
    create_activity,
    get_activity,
    list_activities,
    update_activity,
    delete_activity,
    create_activity_instance,
    update_activity_instance_end,
    get_activity_instance,
)


def test_activity_crud(db):
    a = create_activity(db, Activity(id=None, title="Test", description="Desc", effort_level=4))
    assert a.id is not None
    fetched = get_activity(db, a.id)
    assert fetched is not None and fetched.title == "Test"
    a.title = "Updated"
    update_activity(db, a)
    assert get_activity(db, a.id).title == "Updated"  # type: ignore[union-attr]
    delete_activity(db, a.id)
    assert get_activity(db, a.id) is None


def test_activity_instance_flow(db):
    a = create_activity(db, Activity(id=None, title="Tracked", description=None, effort_level=5))
    inst = create_activity_instance(
        db,
        ActivityInstance(
            id=None,
            activity_id=a.id,  # type: ignore[arg-type]
            start_time="2025-01-01T10:00:00Z",
            end_time=None,
            duration_seconds=None,
        ),
    )
    assert inst.id is not None
    update_activity_instance_end(db, inst.id, "2025-01-01T10:25:00Z", 1500)
    refreshed = get_activity_instance(db, inst.id)
    assert refreshed is not None and refreshed.duration_seconds == 1500
