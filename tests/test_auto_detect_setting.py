from activity_planner.repositories import get_setting
from activity_planner.win_activity_monitor import AUTO_DETECT_KEY, WinActivityMonitor
from activity_planner.activity_store import ActivityStore


def test_auto_detect_toggle_persists(db, qtbot):
    # Create monitor (no-op on non-Windows) and simulate toggle logic
    monitor = WinActivityMonitor()
    # simulate UI toggling ON via settings
    from activity_planner.repositories import set_setting

    set_setting(db, AUTO_DETECT_KEY, "1")
    assert get_setting(db, AUTO_DETECT_KEY) == "1"
    # start/stop should not raise
    monitor.start()
    monitor.stop()
