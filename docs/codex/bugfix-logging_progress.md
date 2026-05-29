# Logging Isolation Bugfix Progress

## 2026-05-29

- Created the implementation plan in `docs/codex/bugfix-logging_plan.md`.
- Confirmed the bug source in `src/yambo_tester/log.py`: the helper configures
  the root logger and clears global handlers on every call.
- Confirmed `run_test()` currently calls the same helper for each test run
  directory, which explains the mixed log output.
- Confirmed the main run path already has the right high-level events available
  to log once the logger ownership is fixed.
- Began the refactor to named loggers with explicit handler ownership and
  propagation control.
- Reworked `src/yambo_tester/log.py` so the main logger and per-test loggers
  are named, isolated, and reconfigurable without duplicate handlers.
- Added `setup_test_logger()` for the per-test `tester.log` files and ensured
  their parent directories are created automatically.
- Updated `src/yambo_tester/runner.py` to use dedicated per-test loggers.
- Updated `src/yambo_tester/cli.py` so the main run log records workflow
  start/finish boundaries at the top level.
- Added focused coverage in `tests/test_logging.py` for:
  - main vs local logger isolation;
  - repeated logger setup without duplicated lines;
  - CLI lifecycle logging with separate main/local outputs.
- Verified `.env/bin/pytest -q tests/test_logging.py tests/test_selection.py`:
  8 passed.
- Verified `.env/bin/pytest -q`:
  15 passed, 2 skipped.
