from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QListWidget, QWidget, QStackedWidget, QVBoxLayout, QLabel


APP_NAME = "Activity Planner"


@dataclass(slots=True)
class AppState:
    db_path: Path


def get_app_state() -> AppState:
    # For now store db in local data/; later move to AppData on Windows
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    return AppState(db_path=data_dir / "activity_planner.sqlite")


class Sidebar(QListWidget):
    PAGES = ["Dashboard", "Activities", "Planner", "Deadlines"]

    def __init__(self) -> None:
        super().__init__()
        self.addItems(self.PAGES)
        self.setFixedWidth(160)
        self.setCurrentRow(0)


class PlaceholderPage(QWidget):
    def __init__(self, title: str) -> None:
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
