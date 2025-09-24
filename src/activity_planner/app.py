from __future__ import annotations

import sys
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QListWidget,
    QWidget,
    QStackedWidget,
    QVBoxLayout,
    QLabel,
)

from .database_manager import DBConfig, DatabaseManager
from .timer_service import TimerService
from .dashboard import DashboardPage
from .activity_store import ActivityStore
from .activities_page import ActivitiesPage
from .deadlines_page import DeadlinesPage
from .planner_page import PlannerPage
from .win_activity_monitor import WinActivityMonitor
from .gemini_planner import GeminiClient, GeminiClientConfig, TitleCategorizer
from .notification_manager import NotificationManager
from .analytics_page import AnalyticsPage
from .settings_page import SettingsPage, THEME_KEY
from .pomodoro import PomodoroService, PomodoroConfig
from .privacy_page import PrivacyPage
from .logging_setup import configure_logging
from .keys import load_api_key, redact
from .updater import check_for_update_async


APP_NAME = "Activity Planner"


@dataclass(slots=True)
class AppState:
    db_path: Path
    db: DatabaseManager
    timer_service: TimerService
    activity_store: ActivityStore
    win_activity_monitor: WinActivityMonitor
    title_categorizer: TitleCategorizer | None


def get_app_state() -> AppState:
    # For now store db in local data/; later move to AppData on Windows (platform check)
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    # Logging first
    configure_logging(data_dir)
    db_path = data_dir / "activity_planner.sqlite"
    db = DatabaseManager(DBConfig(path=db_path))
    db.init_db()
    timer_service = TimerService(db)
    activity_store = ActivityStore(db); activity_store.load()
    win_monitor = WinActivityMonitor()
    # Gemini client (optional if no key)
    # Gemini key: prefer secure storage, fallback env only if none stored
    stored_key = load_api_key(data_dir)
    gemini_key = stored_key or os.environ.get("GEMINI_API_KEY", "")
    gemini_client = None
    title_categorizer = None
    if gemini_key:
        try:
            gemini_client = GeminiClient(GeminiClientConfig(api_key=gemini_key))
        except Exception:
            gemini_client = None
    if gemini_client:
        from .gemini_planner import TitleCategorizer as _TC

        title_categorizer = _TC(db, activity_store, gemini_client)
    logging.getLogger(__name__).info(
        "app_state_created", extra={"gemini_key": redact(gemini_key)}
    )
    return AppState(
        db_path=db_path,
        db=db,
        timer_service=timer_service,
        activity_store=activity_store,
        win_activity_monitor=win_monitor,
        title_categorizer=title_categorizer,
    )


class Sidebar(QListWidget):
    PAGES = ["Dashboard", "Activities", "Planner", "Deadlines", "Analytics", "Settings", "Privacy"]

    def __init__(self) -> None:
        super().__init__()
        self.addItems(self.PAGES)
        self.setFixedWidth(160)
        self.setCurrentRow(0)


class PlaceholderPage(QWidget):
    def __init__(self, title: str) -> None:  # pragma: no cover - simple UI
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel(f"{title} Page (stub)")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)


class MainWindow(QMainWindow):
    def __init__(self, state: AppState) -> None:  # noqa: D401
        super().__init__()
        self.state = state
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 700)
        self._pomo = PomodoroService()

        self.sidebar = Sidebar()
        self.pages = QStackedWidget()
        for page in Sidebar.PAGES:
            if page == "Dashboard":
                self.pages.addWidget(
                    DashboardPage(
                        state.db,
                        state.timer_service,
                        state.activity_store,
                        state.win_activity_monitor,
                        state.title_categorizer,
                    )
                )
            elif page == "Activities":
                self.pages.addWidget(ActivitiesPage(state.activity_store))
            elif page == "Deadlines":
                self.pages.addWidget(DeadlinesPage(state.db))
            elif page == "Planner":
                # Pass gemini client from categorizer if exists
                gem_client = None
                if state.title_categorizer and getattr(state.title_categorizer, "_client", None):
                    gem_client = state.title_categorizer._client  # type: ignore[attr-defined]
                self.pages.addWidget(PlannerPage(state.db, gem_client))
            elif page == "Analytics":
                self.pages.addWidget(AnalyticsPage(state.db))
            elif page == "Settings":
                self.pages.addWidget(SettingsPage(state.db, self._pomo, self.apply_theme))
            elif page == "Privacy":
                self.pages.addWidget(PrivacyPage())
            else:
                self.pages.addWidget(PlaceholderPage(page))

        container = QWidget()
        container_layout = QVBoxLayout(container)
        # Simple vertical layout for now; later switch to proper splitter / horizontal layout
        container_layout.addWidget(self.sidebar)
        container_layout.addWidget(self.pages, 1)
        self.setCentralWidget(container)
        self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)

        # Notification manager (system tray + timetable sync)
        self.notification_manager = NotificationManager(self, state.db, state.timer_service, state.activity_store)

        # Hook planner page save -> refresh notifications (rebuild schedule)
        # Assumes only one PlannerPage added in same order as Sidebar.PAGES
        for i in range(self.pages.count()):
            w = self.pages.widget(i)
            if w.__class__.__name__ == "PlannerPage" and hasattr(w, "timetable_saved"):
                try:  # pragma: no cover - signal connection
                    w.timetable_saved.connect(lambda _d: self.notification_manager.refresh())
                except Exception:
                    pass

        # Apply initial theme
        from .repositories import get_setting
        theme = get_setting(state.db, THEME_KEY) or "light"
        self.apply_theme(theme)

        # Check for updates asynchronously (GitHub repo assumed set via env APP_REPO)
        repo = os.environ.get("APP_REPO", "chakri68/activity-monitor-py")
        try:
            from . import __version__ as current_version  # type: ignore
        except Exception:  # pragma: no cover
            current_version = "0.1.0"
        def _update_cb(info):  # pragma: no cover UI callback
            if info:
                from .toast import show_toast
                show_toast(self, f"Update available: {info.latest}")
        check_for_update_async(repo, current_version, _update_cb)

    # --- Theme handling -----------------------------------------------
    def apply_theme(self, theme: str) -> None:  # pragma: no cover UI
        if theme == "dark":
            self.setStyleSheet(
                """
                QWidget { background-color: #202225; color: #ddd; }
                QLineEdit, QTextEdit, QSpinBox, QComboBox { background: #2b2d31; color: #eee; border: 1px solid #444; }
                QPushButton { background: #3a3d42; color: #eee; border: 1px solid #555; padding:4px 8px; }
                QPushButton:hover { background: #44484f; }
                QTableWidget { background: #2b2d31; }
                """
            )
        else:
            self.setStyleSheet("")


def run(argv: Optional[list[str]] = None) -> int:
    if argv is None:
        argv = sys.argv
    app = QApplication(argv)
    state = get_app_state()
    window = MainWindow(state)
    window.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run())
