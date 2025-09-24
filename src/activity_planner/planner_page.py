from __future__ import annotations

"""Planner page: generate & edit timetables."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QMessageBox
)
from PyQt6.QtCore import QDate

from .repositories import (
    list_activities, list_deadlines, create_timetable, get_timetable_by_date,
    delete_timetable_entries, create_timetable_entry, list_timetable_entries,
    get_activity_by_title
)
from .models import TimetableEntry, Timetable
from .toast import show_toast

from .gemini_planner import GeminiClient, GeminiError


@dataclass(slots=True)
class Slot:
    activity: str
    start: str  # HH:MM
    end: str
    notes: str | None = None


def parse_timetable_response(text: str) -> tuple[List[Slot], bool]:
    """Parse model output. Returns (slots, warning_flag)."""
    import json, re
    warning = "Too many tasks to be chill" in text
    # Find JSON array
    match = re.search(r"\[(?:.|\n)*\]", text)
    if not match:
        return ([], warning)
    try:
        data = json.loads(match.group(0))
        slots = []
        for item in data:
            act = item.get("activity")
            start = item.get("start")
            end = item.get("end")
            if not (act and start and end):
                continue
            slots.append(Slot(activity=act, start=start, end=end, notes=item.get("note")))
        return (slots, warning)
    except Exception:
        return ([], warning)


def detect_overlaps(slots: List[Slot]) -> bool:
    def to_minutes(hm: str) -> int:
        h, m = map(int, hm.split(":"))
        return h * 60 + m
    ordered = sorted(slots, key=lambda s: to_minutes(s.start))
    for a, b in zip(ordered, ordered[1:]):
        if to_minutes(a.end) > to_minutes(b.start):
            return True
    return False


class PlannerPage(QWidget):  # pragma: no cover heavy UI
    def __init__(self, db, gemini_client: GeminiClient | None):
        super().__init__()
        self._db = db
        self._client = gemini_client
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.mode_combo = QComboBox(); self.mode_combo.addItems(["CHILL", "LOCKED_IN"])
        self.generate_btn = QPushButton("Generate")
        self.save_btn = QPushButton("Save")
        self.refresh_btn = QPushButton("Load Existing")
        self.slots_table = QTableWidget(0, 4)
        self.slots_table.setHorizontalHeaderLabels(["Activity", "Start", "End", "Notes"])
        self.slots_table.horizontalHeader().setStretchLastSection(True)
        self.slots_table.setEditTriggers(self.slots_table.EditTrigger.DoubleClicked | self.slots_table.EditTrigger.EditKeyPressed)

        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("Date:")); header_row.addWidget(self.date_edit)
        header_row.addWidget(QLabel("Mode:")); header_row.addWidget(self.mode_combo)
        header_row.addWidget(self.generate_btn); header_row.addWidget(self.save_btn); header_row.addWidget(self.refresh_btn)
        header_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(header_row)
        layout.addWidget(self.slots_table)

        self.generate_btn.clicked.connect(self._on_generate)
        self.save_btn.clicked.connect(self._on_save)
        self.refresh_btn.clicked.connect(self._on_load_existing)

    # --- Generation ----------------------------------------------------
    def _on_generate(self):
        date = self.date_edit.date().toString("yyyy-MM-dd")
        mode = self.mode_combo.currentText()
        activities = list_activities(self._db)
        deadlines = list_deadlines(self._db)
        # Compose prompt
        if not activities:
            show_toast(self, "No activities available")
            return
        prompt = self._build_prompt(date, mode, activities, deadlines)
        result_text = ""
        if self._client:
            try:
                # Use same endpoint; treat as classification-like generation
                body = {
                    "contents": [{"parts": [{"text": prompt}]}]
                }
                from .gemini_planner import GEMINI_ENDPOINT
                params = {"key": self._client._config.api_key}  # type: ignore
                resp = self._client._client.post(GEMINI_ENDPOINT, params=params, json=body)  # type: ignore
                if resp.status_code >= 400:
                    raise GeminiError(str(resp.text)[:120])
                data = resp.json()
                blocks = []
                for c in data.get("candidates", []):
                    for part in c.get("content", {}).get("parts", []):
                        t = part.get("text")
                        if t:
                            blocks.append(t)
                result_text = "\n".join(blocks)
            except Exception as e:
                show_toast(self, f"AI error: {e}")
        else:
            # Fallback naive allocation: sequential 1h blocks until 18:00
            result_text = self._fallback_schedule_text(date, activities)
        slots, warning = parse_timetable_response(result_text)
        if not slots:
            show_toast(self, "No slots parsed")
            return
        if detect_overlaps(slots):
            show_toast(self, "Generated overlaps; please adjust")
        self._load_slots(slots)
        if warning:
            show_toast(self, "Model warning: Too many tasks to be chill today 😭")

    def _build_prompt(self, date: str, mode: str, activities, deadlines) -> str:
        act_desc = ", ".join(f"{a.title}(effort={a.effort_level})" for a in activities)
        dl_desc = ", ".join(f"{d.title}:{d.due_date}(p={d.priority},hrs={d.effort_required})" for d in deadlines) or "None"
        return (
            "You are a timetable assistant. Generate a JSON array of objects with keys activity,start,end,note for the day "
            f"{date}. Mode={mode}. Activities: {act_desc}. Deadlines: {dl_desc}. Use 24h HH:MM times, chronological order. "
            "If workload excessive for CHILL, include phrase 'Too many tasks to be chill today 😭'."
        )

    def _fallback_schedule_text(self, date: str, activities) -> str:
        start_hour = 9
        blocks = []
        cur = start_hour
        for a in activities[:5]:
            end = cur + 1
            blocks.append({"activity": a.title, "start": f"{cur:02d}:00", "end": f"{end:02d}:00"})
            cur = end
            if cur >= 18:
                break
        import json
        return json.dumps(blocks)

    # --- Slot table helpers -------------------------------------------
    def _load_slots(self, slots: List[Slot]):
        self.slots_table.setRowCount(len(slots))
        for r, s in enumerate(slots):
            self.slots_table.setItem(r, 0, QTableWidgetItem(s.activity))
            self.slots_table.setItem(r, 1, QTableWidgetItem(s.start))
            self.slots_table.setItem(r, 2, QTableWidgetItem(s.end))
            self.slots_table.setItem(r, 3, QTableWidgetItem(s.notes or ""))

    def _collect_slots(self) -> List[Slot]:
        slots: List[Slot] = []
        for r in range(self.slots_table.rowCount()):
            act = self.slots_table.item(r, 0).text().strip()
            start = self.slots_table.item(r, 1).text().strip()
            end = self.slots_table.item(r, 2).text().strip()
            note = self.slots_table.item(r, 3).text().strip() or None
            if act and start and end:
                slots.append(Slot(act, start, end, note))
        return slots

    # --- Persistence ---------------------------------------------------
    def _on_save(self):
        date = self.date_edit.date().toString("yyyy-MM-dd")
        mode = self.mode_combo.currentText()
        slots = self._collect_slots()
        if detect_overlaps(slots):
            show_toast(self, "Resolve overlaps first")
            return
        tt = get_timetable_by_date(self._db, date)
        if not tt:
            tt = create_timetable(self._db, Timetable(id=None, date=date, mode=mode))
        else:
            # Update mode if changed
            if tt.mode != mode:
                tt.mode = mode
                from sqlite3 import Connection
                c = self._db.connect()
                with c:
                    c.execute("UPDATE timetables SET mode=? WHERE id=?", (mode, tt.id))
        delete_timetable_entries(self._db, tt.id)  # type: ignore[arg-type]
        for s in slots:
            act = get_activity_by_title(self._db, s.activity)
            create_timetable_entry(
                self._db,
                TimetableEntry(
                    id=None,
                    timetable_id=tt.id,  # type: ignore[arg-type]
                    activity_id=act.id if act else None,  # type: ignore[union-attr]
                    start_time=f"{date}T{s.start}:00Z",
                    end_time=f"{date}T{s.end}:00Z",
                    notes=s.notes,
                ),
            )
        show_toast(self, "Timetable saved")

    def _on_load_existing(self):
        date = self.date_edit.date().toString("yyyy-MM-dd")
        tt = get_timetable_by_date(self._db, date)
        if not tt:
            show_toast(self, "No timetable")
            return
        entries = list_timetable_entries(self._db, tt.id)  # type: ignore[arg-type]
        slots: List[Slot] = []
        for e in entries:
            # Extract HH:MM from ISO times
            start_hm = e.start_time.split("T")[1][:5]
            end_hm = e.end_time.split("T")[1][:5]
            act_title = ""  # we will attempt to fetch
            if e.activity_id:
                from .repositories import get_activity
                a = get_activity(self._db, e.activity_id)
                act_title = a.title if a else ""  # type: ignore[union-attr]
            slots.append(Slot(act_title, start_hm, end_hm, e.notes))
        self._load_slots(slots)

__all__ = [
    "PlannerPage",
    "parse_timetable_response",
    "detect_overlaps",
    "Slot",
]