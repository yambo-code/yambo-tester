# Logging Isolation Bugfix Plan

## Summary

Fix the logger management bug in `yambo-tester` so the main run log and each
per-test `tester.log` file are isolated from one another.

The current implementation configures the root logger in
`src/yambo_tester/log.py`, then reconfigures it again inside `run_test()`. That
causes handler reuse, mixed output, and log lines from one test to appear in
another test's directory.

## Key Changes

- Refactor logging setup to use named loggers instead of the root logger.
- Keep one main logger for the whole run and one dedicated logger per test
  directory.
- Ensure each logger owns its own handlers and never reuses another logger's
  file or console handlers.
- Disable propagation explicitly so local test logs cannot leak into the main
  log and vice versa.
- Keep the public logging API close to the current one, but add a clear helper
  for per-test logger setup.
- Log high-level lifecycle events in the main logger:
  - setup and parameter checks;
  - which test workflow is launching;
  - when a test workflow finishes.

## Test Plan

- Add unit tests for logger isolation and handler cleanup.
- Verify the main log only contains setup and lifecycle information.
- Verify each per-test `tester.log` only contains messages from its own run
  directory.
- Verify reconfiguring the same logger does not duplicate handlers or log
  lines.

## Assumptions

- `setup_logging()` remains the primary helper for the main run logger.
- Per-test log files continue to be written as `tester.log` inside each run
  directory.
- Overwrite mode remains the default for both main and local log files.
