# Activity Planner (MVP Scaffold)

Phase 0 bootstrap for the Windows-only Activity Tracking App.

## Features (Planned)

- PyQt6 desktop UI (Dashboard, Activities, Planner, Deadlines)
- SQLite persistence
- AI (Gemini) timetable + classification (future phase)
- Packaging with PyInstaller

## Dev Setup

Using Poetry.

```bash
poetry install
poetry run pytest -q
poetry run python -m activity_planner.app  # Run app
```

## Code Style

- black, isort, flake8, mypy via pre-commit.

## Tests

Minimal smoke test placeholder in `tests/`.
