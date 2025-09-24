from datetime import datetime, timedelta

from PyQt6.QtCore import QCoreApplication

from activity_planner.timer_service import TimerService
from activity_planner.models import Activity
from activity_planner.repositories import create_activity


class FakeClock:
    def __init__(self, start: datetime):
        self.now = start

    def advance(self, seconds: int) -> None:
        self.now += timedelta(seconds=seconds)

    def __call__(self) -> datetime:
        return self.now


def test_timer_start_stop_persists_duration(db, qtbot):
    # Ensure at least one activity
    a = create_activity(db, Activity(id=None, title="Timed", description=None, effort_level=5))
    clock = FakeClock(datetime(2025, 1, 1, 12, 0, 0))
    service = TimerService(db, time_provider=clock)
    app = QCoreApplication.instance() or QCoreApplication([])  # pragma: no cover - infra

    instance_id = service.start(a.id)  # type: ignore[arg-type]
    clock.advance(125)  # Simulate 2m5s
    service.stop()

    inst = service.get_instance(instance_id)
    assert inst is not None
    assert inst.duration_seconds == 125

    # No second row created on stop
    rows = db.query_all("SELECT COUNT(*) as c FROM activity_instances")
    assert rows[0]["c"] == 1
