# p2y Tests Progress

## 2026-05-29

- Read `README.md`, `docs/codex/test-layout.md`, `runner.py`, and
  `test_reference.py`.
- Confirmed current runner assumptions that every step has `input` and `output`
  for sorting and command construction.
- Confirmed the validator assumes each reference belongs to a step `output`
  directory.
- Found existing `Al_bulk/DFT` and `He/DFT` fixtures using:
  - `exe = "p2y"`;
  - `input_dir = "..."`;
  - no `input` or `output`;
  - `STDOUT = ["== P2Y completed =="]`.
- Plan written in `docs/codex/p2y-tests_plan.md`.
- Updated the runner to:
  - sort steps without requiring `input`;
  - add `-I <input_dir>` when present;
  - omit `-F`, `-J`, and `-C` when their source fields are missing;
  - write a per-step stdout reference file from captured stdout only.
- Updated reference validation to:
  - accept steps without `output`;
  - check `STDOUT` references as a single string-presence check across captured
    stdout and the step `l_<exe>` log file, if present;
  - support explicit string-presence checks in `r-*` report files while
    preserving the existing report-completeness check.
- Added focused unit tests for `p2y` command construction, `input_dir`, stdout
  reference files, `STDOUT` stdout-or-log checks, and `r-*` string checks.
- Added `Al_bulk/DFT` and `He/DFT` to the packaged default test config.
- Updated `docs/codex/test-layout.md` with the new `input_dir`, `STDOUT`, and
  report-string behavior.
- Updated imported `tests.toml` files so `r-*` references use the explicit
  `Game Over & Game summary` marker instead of empty placeholder strings.
- Validation:
  - `.env/bin/pytest`: 22 passed, 2 skipped.
  - Targeted imported run from `/tmp/yambo-tester-p2y-validation` using
    `cache_dir = "/home/nicola/tmp/QE/cache"`:
    - `Al_bulk/DFT`: 2 passed;
    - `He/DFT`: 2 passed.
