from __future__ import annotations

"""Database management and migrations for Activity Planner.

This module provides a minimal SQLite migration system. Each new schema
change is represented as a function inside the MIGRATIONS list. The
applied versions are tracked in the ``schema_migrations`` table.

Idempotency: ``init_db`` can be safely called multiple times.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Callable, Iterable


@dataclass(slots=True)
class DBConfig:
    path: Path
    pragmas: tuple[tuple[str, str | int], ...] = (
        ("journal_mode", "WAL"),
        ("foreign_keys", 1),
        ("synchronous", "NORMAL"),
    )


class DatabaseManager:
    def __init__(self, config: DBConfig):
        self.config = config
        self._conn: sqlite3.Connection | None = None

    # --- Low level helpers -------------------------------------------------
    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self.config.path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.config.path)
            self._conn.row_factory = sqlite3.Row
            self._apply_pragmas(self._conn)
        return self._conn

    def _apply_pragmas(self, conn: sqlite3.Connection) -> None:
        cur = conn.cursor()
        for key, value in self.config.pragmas:
            cur.execute(f"PRAGMA {key}={value}")
        cur.close()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # --- Migration system --------------------------------------------------
    def init_db(self) -> None:
        conn = self.connect()
        with conn:  # Autocommit transaction scope
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                )
                """
            )

        applied_versions = self._get_applied_versions()
        for version, migration_fn in enumerate(MIGRATIONS, start=1):
            if version in applied_versions:
                continue
            with conn:
                migration_fn(conn)
                conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES (?)", (version,)
                )

    def _get_applied_versions(self) -> set[int]:
        conn = self.connect()
        cur = conn.execute("SELECT version FROM schema_migrations")
        return {row[0] for row in cur.fetchall()}

    # --- Convenience -------------------------------------------------------
    def execute(self, sql: str, params: Iterable | None = None) -> sqlite3.Cursor:
        conn = self.connect()
        cur = conn.cursor()
        cur.execute(sql, params or [])
        return cur

    def executemany(self, sql: str, seq_of_params: Iterable[Iterable]) -> None:
        conn = self.connect()
        conn.executemany(sql, seq_of_params)

    def query_all(self, sql: str, params: Iterable | None = None) -> list[sqlite3.Row]:
        cur = self.execute(sql, params)
        return cur.fetchall()

    def query_one(self, sql: str, params: Iterable | None = None) -> sqlite3.Row | None:
        cur = self.execute(sql, params)
        return cur.fetchone()


# --- Migration definitions --------------------------------------------------

def migration_001_create_core_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            description TEXT,
            effort_level INTEGER NOT NULL DEFAULT 5,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        CREATE TABLE activity_instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
            start_time TEXT NOT NULL,
            end_time TEXT,
            duration_seconds INTEGER,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        CREATE TABLE timetables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            mode TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        CREATE TABLE timetable_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timetable_id INTEGER NOT NULL REFERENCES timetables(id) ON DELETE CASCADE,
            activity_id INTEGER REFERENCES activities(id) ON DELETE SET NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        CREATE TABLE deadlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            due_date TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 0,
            effort_required INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        CREATE INDEX idx_activity_instances_activity ON activity_instances(activity_id);
        CREATE INDEX idx_timetable_entries_timetable ON timetable_entries(timetable_id);
        CREATE INDEX idx_timetable_entries_activity ON timetable_entries(activity_id);
        CREATE INDEX idx_deadlines_due_date ON deadlines(due_date);
        """
    )


def migration_002_add_settings_table(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )


def migration_003_add_title_mapping_rules(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS title_mapping_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT NOT NULL UNIQUE, -- exact match (case-insensitive compare done in query)
            activity_id INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );
        CREATE INDEX IF NOT EXISTS idx_title_mapping_rules_pattern ON title_mapping_rules(pattern);
        """
    )


MIGRATIONS: list[Callable[[sqlite3.Connection], None]] = [
    migration_001_create_core_tables,
    migration_002_add_settings_table,
    migration_003_add_title_mapping_rules,
]

__all__ = [
    "DBConfig",
    "DatabaseManager",
]
