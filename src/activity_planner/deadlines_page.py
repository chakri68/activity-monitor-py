from __future__ import annotations

"""Deadlines CRUD page with simple calendar view."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QDialog, QFormLayout, QLineEdit, QSpinBox, QDialogButtonBox, QCalendarWidget, QMessageBox
)
from PyQt6.QtCore import QDate
from datetime import datetime

from .repositories import (
    list_deadlines, create_deadline, update_deadline, delete_deadline
)
from .models import Deadline
from .toast import show_toast


def _validate_date(text: str) -> bool:
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return True
    except ValueError:
        return False


class DeadlineDialog(QDialog):  # pragma: no cover - UI
    def __init__(self, parent=None, deadline: Deadline | None = None):
        super().__init__(parent)
        self.setWindowTitle("Deadline")
        self.title_edit = QLineEdit(deadline.title if deadline else "")
        self.due_edit = QLineEdit(deadline.due_date if deadline else datetime.utcnow().strftime("%Y-%m-%d"))
        self.priority_spin = QSpinBox(); self.priority_spin.setRange(0, 10); self.priority_spin.setValue(deadline.priority if deadline else 0)
        self.effort_spin = QSpinBox(); self.effort_spin.setRange(0, 200); self.effort_spin.setValue(deadline.effort_required if deadline else 0)
        form = QFormLayout()
        form.addRow("Title", self.title_edit)
        form.addRow("Due Date (YYYY-MM-DD)", self.due_edit)
        form.addRow("Priority", self.priority_spin)
        form.addRow("Effort Required (hrs)", self.effort_spin)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_values(self):
        return (
            self.title_edit.text().strip(),
            self.due_edit.text().strip(),
            self.priority_spin.value(),
            self.effort_spin.value(),
        )


class DeadlinesPage(QWidget):  # pragma: no cover heavy UI
    def __init__(self, db):
        super().__init__()
        self._db = db
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Due Date", "Priority", "Effort Hrs"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.calendar = QCalendarWidget()
        self.calendar.selectionChanged.connect(self._on_calendar_selection)

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
        layout.addWidget(self.calendar)
        layout.addWidget(self.table)

        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_delete.clicked.connect(self._delete)
        self.btn_refresh.clicked.connect(self.refresh)

        self.refresh()

    def _selected_id(self):
        items = self.table.selectedItems()
        if not items:
            return None
        try:
            return int(self.table.item(items[0].row(), 0).text())
        except Exception:
            return None

    def refresh(self):
        dls = list_deadlines(self._db)
        dls.sort(key=lambda d: d.due_date)
        self.table.setRowCount(len(dls))
        for r, d in enumerate(dls):
            self.table.setItem(r, 0, QTableWidgetItem(str(d.id)))
            self.table.setItem(r, 1, QTableWidgetItem(d.title))
            self.table.setItem(r, 2, QTableWidgetItem(d.due_date))
            self.table.setItem(r, 3, QTableWidgetItem(str(d.priority)))
            self.table.setItem(r, 4, QTableWidgetItem(str(d.effort_required)))

    def _on_calendar_selection(self):
        date_str = self.calendar.selectedDate().toString("yyyy-MM-dd")
        # Optional future filter; for now highlight rows with that date
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 2)
            if item and item.text() == date_str:
                self.table.selectRow(r)

    def _add(self):
        dlg = DeadlineDialog(self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            title, due_date, priority, effort = dlg.get_values()
            if not title:
                show_toast(self, "Title required")
                return
            if not _validate_date(due_date):
                show_toast(self, "Invalid date format")
                return
            create_deadline(self._db, Deadline(id=None, title=title, due_date=due_date, priority=priority, effort_required=effort))
            show_toast(self, "Deadline created")
            self.refresh()

    def _edit(self):
        sel_id = self._selected_id()
        if not sel_id:
            show_toast(self, "Select a deadline")
            return
        # Fetch existing
        from .repositories import get_deadline
        d = get_deadline(self._db, sel_id)
        if not d:
            return
        dlg = DeadlineDialog(self, d)
        if dlg.exec() == dlg.DialogCode.Accepted:
            title, due_date, priority, effort = dlg.get_values()
            if not title or not _validate_date(due_date):
                show_toast(self, "Validation failed")
                return
            d.title = title; d.due_date = due_date; d.priority = priority; d.effort_required = effort
            update_deadline(self._db, d)
            show_toast(self, "Updated")
            self.refresh()

    def _delete(self):
        sel_id = self._selected_id()
        if not sel_id:
            show_toast(self, "Select a deadline")
            return
        if QMessageBox.question(self, "Confirm", "Delete deadline?") == QMessageBox.StandardButton.Yes:
            delete_deadline(self._db, sel_id)
            show_toast(self, "Deleted")
            self.refresh()

__all__ = ["DeadlinesPage"]