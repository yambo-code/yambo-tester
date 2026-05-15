# Runlevel Selection Progress

## 2026-05-15

- Created the implementation plan in `docs/codex/runlevel-selection_plan.md`.
- Created this progress log with the requested `_progress` suffix placement.
- Confirmed that `AGENTS.md` does not need a new link because this task is already covered by the existing docs/codex guidance.
- Added a pure selection helper for runlevel normalization, dependency validation, and transitive dependency expansion.
- Wired `--runlevel`/`runlevels` through CLI/config, runner selection, and pytest skip handling.
- Annotated imported workflow `tests.toml` files with `runlevel` and `dependencies`.
- Updated README, `ADDING_TESTS.md`, and `docs/codex/test-layout.md` with the new selection contract.
- Added unit coverage for runlevel normalization, dependency expansion, dependency validation, CLI parsing, and filtered-step pytest skips.
- Corrected the package-data entry so `data/config.toml` is included when packaging the project.
- Verified `.env/bin/pytest -q`: 12 passed, 2 skipped.
- Verified `.env/bin/yambo-tester -h` includes the repeatable `--runlevel` option.
- Added the standard isolated imported-test execution procedure to `AGENTS.md`.
- Verified the default imported-test run using the standard isolated procedure in `/home/nicola/tmp/yambo-tester-imported-all`:
  - `Al_bulk/GW-OPTICS`: 29 passed
  - `Al_bulk/ELPH`: 14 passed
  - `PA_chain/PA_chain`: 92 passed
- Verified `--runlevel qp` using the standard isolated procedure in `/home/nicola/tmp/yambo-tester-runlevel-qp`:
  - `Al_bulk/GW-OPTICS`: 16 passed, 13 skipped
  - `Al_bulk/ELPH`: 14 passed
  - `PA_chain/PA_chain`: 47 passed, 45 skipped
- Confirmed `results.toml` uses `returncode = -9998` and `skip_reason = "runlevel-filter"` for runlevel-filtered steps.
- Added next-week follow-up items to the plan file: runlevel vocabulary review, README runlevel table, and handling the unrelated `doc/` directory.
