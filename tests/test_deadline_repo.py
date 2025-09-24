from activity_planner.models import Deadline
from activity_planner.repositories import (
    create_deadline,
    get_deadline,
    list_deadlines,
    update_deadline,
    delete_deadline,
)


def test_deadline_crud(db):
    d = create_deadline(
        db,
        Deadline(id=None, title="Exam", due_date="2030-12-31", priority=2, effort_required=10),
    )
    assert d.id is not None
    assert get_deadline(db, d.id) is not None
    d.priority = 5
    update_deadline(db, d)
    assert get_deadline(db, d.id).priority == 5  # type: ignore[union-attr]
    assert len(list_deadlines(db)) >= 1
    delete_deadline(db, d.id)
    assert get_deadline(db, d.id) is None
