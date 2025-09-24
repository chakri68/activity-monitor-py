from activity_planner import run


def test_import_and_run_smoke(monkeypatch):
    # Avoid starting full Qt event loop in test; just ensure callable.
    assert callable(run)
