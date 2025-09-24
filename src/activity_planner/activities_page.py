from __future__ import annotations

"""Activities CRUD page."""

from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QDialog,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QSpinBox,
    QDialogButtonBox,
    QMessageBox,
)

from .activity_store import ActivityStore
from .models import Activity
from .toast import show_toast


class ActivityDialog(QDialog):  # pragma: no cover simple UI
    def __init__(self, parent: QWidget, title: str, *, activity: Activity | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._activity = activity
        self.name_edit = QLineEdit(activity.title if activity else "")
        self.desc_edit = QTextEdit(activity.description if activity else "")
        self.effort_spin = QSpinBox()
        self.effort_spin.setRange(1, 10)
        self.effort_spin.setValue(activity.effort_level if activity else 5)
        form = QFormLayout()
        form.addRow("Title", self.name_edit)
        form.addRow("Description", self.desc_edit)
        form.addRow("Effort (1-10)", self.effort_spin)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_values(self) -> tuple[str, str | None, int]:
        desc = self.desc_edit.toPlainText().strip() or None
        return self.name_edit.text(), desc, self.effort_spin.value()


class ActivitiesPage(QWidget):  # pragma: no cover UI heavy
    def __init__(self, store: ActivityStore):
        super().__init__()
        self._store = store
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Effort", "Description", "Tags"])
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.btn_add = QPushButton("Add")
        self.btn_edit = QPushButton("Edit")
        self.btn_delete = QPushButton("Delete")
        self.btn_refresh = QPushButton("Refresh")

        btn_row = QHBoxLayout()
        for b in (self.btn_add, self.btn_edit, self.btn_delete, self.btn_refresh):
            btn_row.addWidget(b)
        btn_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(btn_row)
        layout.addWidget(self.table)

        # Signals
        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_delete.clicked.connect(self._delete)
        self.btn_refresh.clicked.connect(self.refresh)
        self._store.changed.connect(self.refresh)
        self._store.error.connect(lambda m: show_toast(self, m))

        # Shortcuts
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._add)
        QShortcut(QKeySequence("Delete"), self, activated=self._delete)
        QShortcut(QKeySequence("F5"), self, activated=self.refresh)

        self.refresh()

    # --- Helpers --------------------------------------------------------
    def _selected_activity(self) -> Optional[Activity]:
        items = self.table.selectedItems()
        if not items:
            return None
        row = items[0].row()
        act_id_item = self.table.item(row, 0)
        if not act_id_item:
            return None
        try:
            act_id = int(act_id_item.text())
        except ValueError:
            return None
        return next((a for a in self._store.activities() if a.id == act_id), None)

    def refresh(self) -> None:
        acts = self._store.activities()
        self.table.setRowCount(len(acts))
        for r, a in enumerate(acts):
            self.table.setItem(r, 0, QTableWidgetItem(str(a.id)))
            self.table.setItem(r, 1, QTableWidgetItem(a.title))
            self.table.setItem(r, 2, QTableWidgetItem(str(a.effort_level)))
            self.table.setItem(r, 3, QTableWidgetItem(a.description or ""))
            try:  # optional tag column
                from .repositories import get_tags_for_activity
                tags = ",".join(get_tags_for_activity(self._store._db, a.id)) if a.id else ""  # type: ignore[attr-defined]
                self.table.setItem(r, 4, QTableWidgetItem(tags))
            except Exception:
                self.table.setItem(r, 4, QTableWidgetItem(""))

    # --- CRUD ops -------------------------------------------------------
    def _add(self) -> None:
        dlg = ActivityDialog(self, "New Activity")
        if dlg.exec() == QDialog.DialogCode.Accepted:
            title, desc, effort = dlg.get_values()
            prev_count = len(self._store.activities())
            a = self._store.create(title, desc, effort)
            if a:
                show_toast(self, "Activity created")
                # optimistic already inserted
                if prev_count == 0:
                    self.refresh()

    def _edit(self) -> None:
        act = self._selected_activity()
        if not act:
            show_toast(self, "Select an activity to edit")
            return
        dlg = ActivityDialog(self, "Edit Activity", activity=act)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            title, desc, effort = dlg.get_values()
            if self._store.update(act, title=title, description=desc, effort_level=effort):
                show_toast(self, "Activity updated")

    def _delete(self) -> None:
        act = self._selected_activity()
        if not act:
            show_toast(self, "Select an activity to delete")
            return
        if QMessageBox.question(self, "Confirm", f"Delete '{act.title}'?") == QMessageBox.StandardButton.Yes:
            if self._store.delete(act.id):  # type: ignore[arg-type]
                show_toast(self, "Deleted")

__all__ = ["ActivitiesPage"]
