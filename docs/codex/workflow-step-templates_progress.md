# Workflow Step Templates Progress

## Status

Planning documents have been added. Implementation has not started yet.

## Completed

- Inspected current workflow metadata loading in `runner.setup_rundir()` and
  `runner.run_test()`.
- Confirmed that scratch-side expansion fits the current flow: the workflow
  tree is copied first, then `tests.toml` is read from the scratch copy for
  version checks, tarball handling, execution, and pytest validation.
- Confirmed that the existing version resolver applies shallow step overlays
  late, so template expansion should produce a normal expanded `tests.toml`
  rather than changing version-resolution semantics.
- Identified the best template location as
  `src/yambo_tester/data/workflow_templates.toml`.
- Identified initial low-risk migration targets:
  `Si_bulk/DFT/tests.toml` and `He/DFT/tests.toml`.

## Next Steps

- Add `src/yambo_tester/data/workflow_templates.toml` and package it in
  `pyproject.toml`.
- Add `src/yambo_tester/template_expansion.py`.
- Wire expansion into `runner.setup_rundir()` immediately after copying the
  workflow directory to scratch.
- Add unit tests for expansion, placeholders, merge precedence, version
  overlays, and old-style compatibility.
- Migrate the first DFT workflows to compact `step_type` syntax.
- Update `docs/codex/test-layout.md`, `README.md`, and `AGENTS.md`.

## Notes

- `{step}` should resolve to the local step table name.
- `{previous_step}` should resolve from TOML insertion order, excluding workflow
  metadata tables.
- Local overrides should win over template defaults.
- Reference tables should merge by key, with local references overriding
  template references.
- Version-specific reference tables should be expanded as complete merged
  replacement tables so existing Yambo 5/Yambo 6 behavior stays intact.
