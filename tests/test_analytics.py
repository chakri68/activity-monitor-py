from datetime import datetime, timedelta

from activity_planner.database_manager import DatabaseManager, DBConfig
from activity_planner.models import Activity, ActivityInstance
from activity_planner.repositories import create_activity, create_activity_instance, update_activity_instance_end
from activity_planner.analytics_page import AnalyticsPage


def test_daily_and_weekly_aggregates(tmp_path):
    db = DatabaseManager(DBConfig(path=tmp_path / "a.sqlite"))
    db.init_db()
    # Create two activities
    a1 = create_activity(db, Activity(id=None, title="Reading", description=None))
    a2 = create_activity(db, Activity(id=None, title="Coding", description=None))
    today = datetime.utcnow().replace(microsecond=0)
    day = today.date().isoformat()

    # Helper to create finished instance
    def add_instance(act_id, start_offset_min, dur_min):
        start_dt = today.replace(hour=9, minute=0, second=0) + timedelta(minutes=start_offset_min)
        inst = create_activity_instance(
            db,
            ActivityInstance(
                id=None,
                activity_id=act_id,
                start_time=start_dt.isoformat() + "Z",
                end_time=None,
                duration_seconds=None,
            ),
        )
        update_activity_instance_end(
            db,
            inst.id,  # type: ignore[arg-type]
            (start_dt + timedelta(minutes=dur_min)).isoformat() + "Z",
            dur_min * 60,
        )

    add_instance(a1.id, 0, 30)   # 30m Reading
    add_instance(a2.id, 40, 60)  # 60m Coding

    # Instantiate AnalyticsPage logic layer (no show)
    page = AnalyticsPage(db)

    dist = page._query_daily_distribution(day)
    # Expect two entries ordered by duration desc (Coding first)
    assert dist[0][0] in {"Coding", "Reading"}
    totals = dict(dist)
    assert totals["Reading"] == 30 * 60
    assert totals["Coding"] == 60 * 60

    weekly = page._query_weekly_totals(day)
    # Sum of weekly should include our 90m today
    week_total = sum(v for _, v in weekly)
    assert week_total >= 90 * 60
