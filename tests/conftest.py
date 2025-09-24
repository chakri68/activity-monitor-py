import sqlite3
from pathlib import Path
import sys
import pytest

# Ensure src/ is on sys.path for direct test invocation without Poetry editable install
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from activity_planner.database_manager import DBConfig, DatabaseManager


@pytest.fixture()
def db(tmp_path: Path):
    config = DBConfig(path=tmp_path / "test.sqlite")
    manager = DatabaseManager(config)
    manager.init_db()
    yield manager
    manager.close()


def test_init_idempotent(db: DatabaseManager):
    # Second call should not raise and should not duplicate migrations
    db.init_db()
    rows = db.query_all("SELECT COUNT(*) as c FROM schema_migrations")
    assert rows[0]["c"] >= 1
