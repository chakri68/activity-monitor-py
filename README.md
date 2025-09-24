# Activity Planner

Productivity & time‑tracking desktop application focused on structured activity logging, automatic window title suggestions, notifications, analytics, and (optional) AI assistance.

> NOTE: Foreground window auto‑detection currently works only on Windows. The application otherwise runs on macOS/Linux but auto-detect will be inert there.

---

## Table of Contents

1. Overview
2. Core Features
3. Quick Start (Development)
4. Running the App
5. Activities & Timers
6. Auto‑Detect, Suggestions & Auto‑Switch
7. Title Mapping Rules Management
8. Pomodoro Mode
9. Planner & Timetable Reminders
10. Notifications & Do Not Disturb
11. Analytics (History, Daily Distribution, Weekly Totals)
12. Tags
13. Settings Reference
14. Gemini AI Integration (Optional)
15. Storing the Gemini API Key Securely
16. Logging & Privacy
17. Update Checking
18. Packaging (PyInstaller Draft Guidance)
19. Development Workflow (Migrations, Style, Tests)
20. Troubleshooting
21. Roadmap / Future Enhancements

---

## 1. Overview

The Activity Planner helps you:

- Create and manage named activities.
- Track focused time with a start/pause/resume/stop timer.
- Optionally auto‑suggest (and auto‑switch to) an activity when you change foreground applications (Windows only).
- Classify window titles using a Gemini model (if API key is supplied) OR a local heuristic fallback.
- Build a daily/weekly picture of where time is spent.
- Use Pomodoro structured focus/break cycles.
- Plan the day with a timetable and receive per‑slot reminders.
- Analyse history via calendar + charts.
- Manage rule mappings for recurring window titles.

## 2. Core Features

| Feature                       | Status            | Notes                                       |
| ----------------------------- | ----------------- | ------------------------------------------- |
| Activities CRUD               | Implemented       | Via Activities page                         |
| Timer tracking                | Implemented       | Persists sessions to SQLite                 |
| Auto‑detect (window title)    | Windows only      | Poll ~700 ms, debounced                     |
| AI classification             | Optional          | Gemini via API key; fallback heuristic      |
| Auto‑switch + auto‑start      | Implemented       | Threshold & behavior configurable           |
| Title mapping rules           | Implemented       | Create (from suggestion) + manage dialog    |
| Planner / Timetable           | Implemented       | Saves day schedule; notifications integrate |
| System tray notifications     | Implemented       | Slot start/end reminders, snooze, DND       |
| Pomodoro cycles               | Implemented       | Work / short / long break sequencing        |
| Tags                          | Implemented       | Create/edit comma-separated tags per activity |
| Analytics (calendar + charts) | Implemented       | Daily distribution & weekly totals          |
| Logging (structured JSON)     | Implemented       | Rotating file handler in `data/logs/`       |
| Updater (GitHub check)        | Implemented       | Toast when newer release detected           |
| Secure key storage            | Implemented       | Keyring first, XOR fallback file            |
| Packaging (PyInstaller)       | In progress       | Spec guidance below                         |

## 3. Quick Start (Development)

Requires Python 3.11+ and Poetry.

```bash
git clone <this-repo>
cd activity-monitor-py
poetry install
poetry run python -m activity_planner.app
```

Run tests:

```bash
poetry run pytest -q
```

## 4. Running the App

```bash
poetry run python -m activity_planner.app
```

Creates (if absent) a `data/` directory at repo root containing:

```
data/
	activity_planner.sqlite   # SQLite DB
	logs/                     # Rotating JSON logs
	gemini.key                # (Only if keyring unavailable & you saved a key)
```

## 5. Activities & Timers

1. Create activities on the Activities page.
2. Select an activity on the Dashboard.
3. Use Start / Pause / Resume / Stop buttons.
4. Each run generates an `activity_instance` persisted with its duration.

## 6. Auto‑Detect, Suggestions & Auto‑Switch

Enable Auto‑Detect on Dashboard (or Settings). On Windows the app monitors foreground window titles roughly every 700 ms.

Suggestion pipeline priority:

1. Exact rule mapping (100% confidence).
2. Gemini classification (if API key present).
3. Local heuristic fallback (substring / token overlap scoring).

If `Automatically switch activity when confident` is enabled and confidence ≥ configured threshold (default 65%), the selection changes immediately. If `Start timer on auto switch if idle` is also enabled, the timer starts automatically when previously idle.

## 7. Title Mapping Rules Management

When a suggestion banner appears you can click “Always map this” which stores the exact window title → activity mapping. Manage existing rules in Settings → “Manage Title Rules” (view & delete). Rules are exact, case-insensitive matches.

## 8. Pomodoro Mode

Configure work / short break / long break durations and cycles-per-long-break in Settings. (UI elements to surface live phase and manual advance can be expanded later.) The service internally tracks phase transitions; you can hook UI indicators in the Dashboard in future work.

## 9. Planner & Timetable Reminders

Use the Planner page to define a day’s timetable (start/end times linked to activities). Notifications:

- Slot start reminder.
- Optional end wrap reminder.
  Notifications can be suppressed with DND.

## 10. Notifications & Do Not Disturb

System tray integration (where supported) surfaces reminders. A Snooze may be provided (implementation detail inside `notification_manager`). Toggle DND in Settings to suppress popups without canceling scheduled logic.

## 11. Analytics

Analytics page shows:

- Calendar view of tracked days.
- Daily distribution (pie / donut) of time by activity.
- Weekly totals bar chart.
  Backed by aggregate SQL queries over stored activity instances.

## 12. Tags

Database schema supports tagging activities and viewing tags in the Activities table. Future UI will allow editing tags and filtering analytics by tag.

## 13. Settings Reference

| Key                                | Purpose                                    | Values       |
| ---------------------------------- | ------------------------------------------ | ------------ |
| ui.theme                           | UI theme                                   | light / dark |
| auto_detect_enabled                | Enable window monitoring                   | 1 / 0        |
| notifications.dnd                  | Suppress notifications                     | 1 / 0        |
| pomo.work / pomo.short / pomo.long | Pomodoro durations (minutes)               | int          |
| pomo.cycles                        | Cycles before long break                   | int          |
| auto_switch.enabled                | Enable auto-switch on confident suggestion | 1 / 0        |
| auto_switch.start_timer            | Auto start timer when idle                 | 1 / 0        |
| auto_switch.conf_threshold         | Confidence threshold (%)                   | 10–100       |

Settings are persisted in the `settings` table; export/import via Settings page.

## 14. Gemini AI Integration (Optional)

Used for higher quality title → activity classification. If absent, heuristic fallback applies.

Set temporarily per run:

```bash
export GEMINI_API_KEY="YOUR_KEY"
poetry run python -m activity_planner.app
```

Or store (preferred) using keyring / fallback:

```bash
poetry run python -c "from pathlib import Path; from activity_planner.keys import save_api_key; save_api_key(Path('data'), 'YOUR_KEY')"
```

## 15. Storing the Gemini API Key Securely

Order of retrieval:

1. Keyring (macOS Keychain / Windows Credential Manager) – secure.
2. Fallback obfuscated file `data/gemini.key` (XOR+base64 – not strong encryption).
3. Environment variable `GEMINI_API_KEY` (only if nothing stored).

To rotate: call `save_api_key` again with new value.

## 16. Logging & Privacy

Structured JSON logs (rotating) under `data/logs/`. Sensitive values (Gemini key) are redacted before logging. Window titles are _not_ persisted by default except where you explicitly create a mapping rule.

Potential future log export: “Export Logs” action (roadmap).

## 17. Update Checking

On startup the app queries the GitHub Releases API (`/releases/latest`) for the configured repository and shows a toast if a newer version exists. (Network failures are logged as warnings.)

## 18. Packaging (PyInstaller Draft Guidance)

Create a spec (example outline):

```bash
pyinstaller -n ActivityPlanner \
	--add-data "activity_planner/resources:activity_planner/resources" \
	--hidden-import activity_planner \
	-w -y activity_planner/app.py
```

Recommended additions:

- Ensure `data/` path resolution works when frozen (`sys._MEIPASS` guard if you externalize resources).
- Add icon via `--icon path/to/icon.ico` (Windows) / `.icns` (macOS).
- Embed version: either via `__version__` constant or `--version-file` (Windows).

## 19. Development Workflow

### Style & Lint

Pre-commit hooks (black, isort, flake8, mypy) – install:

```bash
poetry run pre-commit install
```

### Database Migrations

Migrations are incremental functions (e.g., `migration_00X_...`) executed at startup. Add new schema changes by appending migration logic in `database_manager` following existing pattern.

### Tests

```bash
poetry run pytest -q
```

Add tests for new repository functions (e.g., rule CRUD), timer edge cases, heuristic classifier, etc.

## 20. Troubleshooting

| Symptom                                               | Cause                                     | Resolution                                                     |
| ----------------------------------------------------- | ----------------------------------------- | -------------------------------------------------------------- |
| Auto-detect shows ON but no suggestions (macOS/Linux) | Platform not supported yet                | Use manual activity switching; Windows only feature currently  |
| No suggestions even on Windows                        | Missing Gemini key & heuristic weak match | Lower threshold or add mapping rule manually                   |
| Key not picked up                                     | Stored old one still present              | Delete `data/gemini.key` or remove keyring entry, then re-save |
| Notifications not appearing                           | DND enabled                               | Disable DND in Settings                                        |
| Charts blank                                          | No activity instances recorded            | Start and stop a timer to generate data                        |
| Update toast never shows                              | Already latest or network blocked         | Check logs under `data/logs/`                                  |

## 21. Roadmap / Future Enhancements

- macOS/Linux foreground window support.
- Tag editing + analytics filtering by tag.
- Telemetry (opt-in) for feature usage metrics.
- Log export + diagnostics bundle.
- In-app Gemini key management UI.
- Automatic timer switching mid-run (with optional graceful finish).
- Improved heuristic via incremental learning of title→activity pairs.
- Packaged installers (.msi / .dmg) & auto-updater flow.

---

## License

TBD (add LICENSE file when decided).

---

Feel free to open issues or propose enhancements once packaging stabilizes.
