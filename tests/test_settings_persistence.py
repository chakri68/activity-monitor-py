from PyQt6.QtCore import QCoreApplication

from activity_planner.activity_store import ActivityStore, SELECTED_KEY
from activity_planner.models import Activity
from activity_planner.repositories import create_activity, get_setting


def test_selected_activity_persists(db, qtbot):
    app = QCoreApplication.instance() or QCoreApplication([])  # pragma: no cover infra
    store = ActivityStore(db)
    store.load()
    a = create_activity(db, Activity(id=None, title="PersistMe", description=None, effort_level=4))
    store.set_selected_activity_id(a.id)
    # Simulate new store (session restart) using same db
    store2 = ActivityStore(db)
    store2.load()
    assert store2.get_selected_activity_id() == a.id
    assert get_setting(db, SELECTED_KEY) == str(a.id)
