from __future__ import annotations

"""Title Mapping Rule Management Dialog.
Allows viewing and deleting existing window-title -> activity mapping rules.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, QMessageBox, QLineEdit, QComboBox, QLabel
)
from PyQt6.QtCore import Qt

from .repositories import list_title_mapping_rules, delete_title_mapping_rule, list_activities, create_title_mapping_rule


class RuleManagerDialog(QDialog):  # pragma: no cover UI heavy
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self._db = db
        self.setWindowTitle("Title Mapping Rules")
        self.resize(600, 400)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Pattern", "Activity", "Rule ID"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # Add rule row
        add_row = QHBoxLayout()
        add_row.addWidget(QLabel("New Pattern:"))
        self.pattern_edit = QLineEdit()
        add_row.addWidget(self.pattern_edit)
        self.activity_combo = QComboBox()
        add_row.addWidget(QLabel("Activity:"))
        add_row.addWidget(self.activity_combo)
        self.btn_add = QPushButton("Add Rule")
        add_row.addWidget(self.btn_add)
        add_row.addStretch(1)
        layout.addLayout(add_row)

        btn_row = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_delete = QPushButton("Delete Selected")
        btn_row.addWidget(self.btn_refresh)
        btn_row.addWidget(self.btn_delete)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        self.btn_refresh.clicked.connect(self._load)
        self.btn_delete.clicked.connect(self._delete)
        self.btn_add.clicked.connect(self._add_rule)
        self._load()

    def _load(self):
        rules = list_title_mapping_rules(self._db)
        self.table.setRowCount(len(rules))
        for r, (rule_id, pattern, act_id, act_title) in enumerate(rules):
            self.table.setItem(r, 0, QTableWidgetItem(pattern))
            self.table.setItem(r, 1, QTableWidgetItem(act_title))
            id_item = QTableWidgetItem(str(rule_id))
            id_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(r, 2, id_item)
        # refresh activities list
        self.activity_combo.clear()
        acts = list_activities(self._db)
        for a in acts:
            self.activity_combo.addItem(a.title, a.id)

    def _delete(self):
        rows = set(i.row() for i in self.table.selectedIndexes())
        if not rows:
            return
        if QMessageBox.question(self, "Confirm", f"Delete {len(rows)} selected rule(s)?") != QMessageBox.StandardButton.Yes:
            return
        for r in sorted(rows, reverse=True):
            rid_item = self.table.item(r, 2)
            if rid_item:
                try:
                    delete_title_mapping_rule(self._db, int(rid_item.text()))
                except Exception:
                    pass
        self._load()

    def _add_rule(self):  # pragma: no cover UI
        pattern = self.pattern_edit.text().strip()
        if not pattern:
            return
        act_id = self.activity_combo.currentData()
        if act_id in (None, -1):
            return
        try:
            create_title_mapping_rule(self._db, pattern, int(act_id))  # type: ignore[arg-type]
        except Exception:
            pass
        self.pattern_edit.clear()
        self._load()

__all__ = ["RuleManagerDialog"]
