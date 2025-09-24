from __future__ import annotations

"""Analytics & History Page (Phase 8).

Features:
 - Date picker calendar to inspect activity instances of a given day.
 - Session list (start/end/duration) + total time summary.
 - Daily distribution donut (activity share for selected day).
 - Weekly bar chart (total seconds per day for week containing selected date).

Design notes:
 - Uses lightweight aggregation SQL (GROUP BY) queries.
 - Matplotlib FigureCanvas embedded; renders on-demand (no blocking long queries).
 - If matplotlib not available at runtime (headless minimal install), page degrades gracefully.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import List, Tuple, Optional

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QCalendarWidget, QSizePolicy
)

try:  # pragma: no cover - import guard
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
except Exception:  # pragma: no cover
    FigureCanvas = object  # type: ignore
    Figure = object  # type: ignore

from .database_manager import DatabaseManager


def _iso_day(dt: date) -> str:
    return dt.isoformat()


class AnalyticsPage(QWidget):  # pragma: no cover heavy UI
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self._db = db

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.sessions_list = QListWidget()
        self.total_label = QLabel("Total: 0m")

        charts_layout = QHBoxLayout()
        self.daily_canvas = self._build_canvas()
        self.weekly_canvas = self._build_canvas()
        if isinstance(self.daily_canvas, QWidget):
            charts_layout.addWidget(self.daily_canvas, 1)
        if isinstance(self.weekly_canvas, QWidget):
            charts_layout.addWidget(self.weekly_canvas, 1)

        top_row = QHBoxLayout()
        left_col = QVBoxLayout()
        left_col.addWidget(self.calendar)
        left_col.addWidget(self.total_label)
        top_row.addLayout(left_col, 0)
        top_row.addWidget(self.sessions_list, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(top_row, 2)
        layout.addLayout(charts_layout, 1)

        self.calendar.selectionChanged.connect(self._on_date_changed)
        self._on_date_changed()

    # --- Helpers ------------------------------------------------------
    def _build_canvas(self):  # pragma: no cover UI utility
        if Figure is object:
            return QLabel("matplotlib unavailable")
        fig = Figure(figsize=(3, 3))
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return canvas

    def _query_sessions_for_day(self, day: str) -> List[Tuple[str, str, int, int]]:
        rows = self._db.query_all(
            """
            SELECT ai.start_time, ai.end_time, ai.duration_seconds, a.id as activity_id, a.title
            FROM activity_instances ai
            JOIN activities a ON a.id = ai.activity_id
            WHERE ai.start_time LIKE ? || '%'
            ORDER BY ai.start_time
            """,
            (day,),
        )
        out: List[Tuple[str, str, int, int]] = []
        for r in rows:
            dur = r["duration_seconds"] or 0
            out.append((r["title"], r["start_time"], r["end_time"] or "", dur))
        return out

    def _query_daily_distribution(self, day: str) -> List[Tuple[str, int]]:
        rows = self._db.query_all(
            """
            SELECT a.title, SUM(ai.duration_seconds) as total
            FROM activity_instances ai
            JOIN activities a ON a.id = ai.activity_id
            WHERE ai.start_time LIKE ? || '%' AND ai.duration_seconds IS NOT NULL
            GROUP BY a.title
            HAVING total > 0
            ORDER BY total DESC
            """,
            (day,),
        )
        return [(r["title"], int(r["total"])) for r in rows]

    def _query_weekly_totals(self, anchor_day: str) -> List[Tuple[str, int]]:
        dt = datetime.strptime(anchor_day, "%Y-%m-%d").date()
        start_week = dt - timedelta(days=dt.weekday())  # Monday
        days = [start_week + timedelta(days=i) for i in range(7)]
        results: List[Tuple[str, int]] = []
        for d in days:
            rows = self._db.query_all(
                """
                SELECT SUM(duration_seconds) as total
                FROM activity_instances
                WHERE start_time LIKE ? || '%' AND duration_seconds IS NOT NULL
                """,
                (d.isoformat(),),
            )
            total = int(rows[0]["total"] or 0) if rows else 0
            results.append((d.isoformat(), total))
        return results

    # --- Slots --------------------------------------------------------
    def _on_date_changed(self):
        qd = self.calendar.selectedDate()
        day = qd.toString("yyyy-MM-dd")
        self._load_sessions(day)
        self._render_charts(day)

    def _load_sessions(self, day: str):
        sessions = self._query_sessions_for_day(day)
        self.sessions_list.clear()
        total_seconds = 0
        for title, start_iso, end_iso, dur in sessions:
            total_seconds += dur
            start_hm = start_iso.split("T")[1][:5]
            end_hm = (end_iso.split("T")[1][:5] if end_iso else "--:--")
            self.sessions_list.addItem(f"{start_hm}-{end_hm} {title} ({dur//60}m)")
        self.total_label.setText(f"Total: {total_seconds//60}m in {len(sessions)} sessions")

    def _render_charts(self, day: str):  # pragma: no cover heavy UI
        if Figure is object:
            return
        # Daily distribution donut/pie
        dist = self._query_daily_distribution(day)
        fig_daily: Figure = self.daily_canvas.figure  # type: ignore
        fig_daily.clear()
        if dist:
            labels, values = zip(*dist)
            ax = fig_daily.add_subplot(111)
            wedges, _ = ax.pie(values, labels=labels, wedgeprops=dict(width=0.45))
            ax.set_title("Daily Distribution")
        fig_daily.tight_layout()
        self.daily_canvas.draw()  # type: ignore

        # Weekly totals bar
        week = self._query_weekly_totals(day)
        fig_week: Figure = self.weekly_canvas.figure  # type: ignore
        fig_week.clear()
        ax2 = fig_week.add_subplot(111)
        days = [d[5:] for d, _ in week]  # MM-DD
        values = [v/3600 for _, v in week]  # hours
        ax2.bar(days, values, color="#4a90e2")
        ax2.set_title("Weekly Hours")
        ax2.set_ylabel("Hours")
        fig_week.tight_layout()
        self.weekly_canvas.draw()  # type: ignore


__all__ = ["AnalyticsPage"]
