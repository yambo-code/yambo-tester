# Workflow Step Templates Progress

## Status

Implemented for the first-pass DFT template scope.

## Completed

- Added packaged templates in `src/yambo_tester/data/workflow_templates.toml`
  and included them in package data.
- Added `src/yambo_tester/template_expansion.py` to load templates, detect
  `step_type`, apply placeholders recursively, merge local overrides, and keep
  old-style fully expanded steps unchanged.
- Wired scratch-side expansion into `runner.setup_rundir()` immediately after
  copying the workflow directory and before version support, tarball URL,
  checksum, extraction, execution, and validation logic consume metadata.
- Kept version resolution semantics unchanged: expanded step version overlays
  are still consumed by the existing shallow `resolve_step_metadata()` logic.
- Added focused tests for expansion, placeholders, local override precedence,
  template and local version overlays, reference merging, old-style workflow
  compatibility, unknown template errors, packaged template shapes, and
  `setup_rundir()` scratch rewrite behavior.
- Made workflow keyword and metadata tests template-aware.
- Migrated DFT workflows that match the initial templates:
  `Si_bulk/DFT`, `He/DFT`, `Al_bulk/DFT`, `PA_chain/DFT`, `Nickel/DFT`,
  `AlAs/DFT`, `hBN/DFT`, `Iron_With-SOC/DFT`, and
  `Iron_Without-SOC/DFT`.
- Removed the temporary `init_input` idea; workflows needing explicit init
  inputs use `step_type = "init"` with local `input` and version-specific
  `input` overrides.
- Kept DFT workflows on the Yambo 6 tarball repository for both Yambo 5 and
  Yambo 6 execution.
- Updated `docs/codex/test-layout.md`, `README.md`, and `AGENTS.md`.

## Remaining Work

No required work remains for the plan's first-pass scope. Broader GW, optics,
ELPH, or PA-chain workflow templates were intentionally left out because the
plan called for templating only exact, low-risk repeated shapes first. Future
work can add new templates if repeated shapes become clear and can be covered
with focused tests.

## Verification

Last verified with:

```bash
.env/bin/pytest
# 114 passed, 2 skipped
```
