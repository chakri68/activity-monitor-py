from __future__ import annotations

import sys
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
from .win_activity_monitor import WinActivityMonitor
from .gemini_planner import GeminiClient, GeminiClientConfig, TitleCategorizer


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
    db_path = data_dir / "activity_planner.sqlite"
    db = DatabaseManager(DBConfig(path=db_path))
    db.init_db()
    timer_service = TimerService(db)
    activity_store = ActivityStore(db); activity_store.load()
    win_monitor = WinActivityMonitor()
    # Gemini client (optional if no key)
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
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
    return AppState(
        db_path=db_path,
        db=db,
        timer_service=timer_service,
        activity_store=activity_store,
        win_activity_monitor=win_monitor,
        title_categorizer=title_categorizer,
    )


class Sidebar(QListWidget):
    PAGES = ["Dashboard", "Activities", "Planner", "Deadlines"]

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
            else:
                self.pages.addWidget(PlaceholderPage(page))

        container = QWidget()
        container_layout = QVBoxLayout(container)
        # Simple vertical layout for now; later switch to proper splitter / horizontal layout
        container_layout.addWidget(self.sidebar)
        container_layout.addWidget(self.pages, 1)
        self.setCentralWidget(container)

        self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)


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
