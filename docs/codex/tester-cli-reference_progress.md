# Tester CLI Reference Comparison Progress

This file tracks work on aligning the lightweight `tester` CLI helper with the
main reference comparison behavior.

## Context

Current state identified during planning:

- `tester` is registered in `pyproject.toml` as `scripts.test_reference:main`.
- `src/scripts/test_reference.py` is an older standalone validator that tries to
  handle text outputs, NetCDF databases, report files, and run directories.
- The current pytest workflow validator in
  `src/yambo_tester/tests/test_reference.py` already contains the comparison
  rules that `tester` should share.
- The current validator uses `numpy.genfromtxt(..., ndmin=2)`, which handles
  one-row and one-column text files better than the old helper.
- Project documentation treats text-output column numbers as 1-based through
  `skip_columns`.

## Planned Work

- [x] Create a shared non-pytest comparison module.
- [x] Update the pytest workflow validator to import shared helpers.
- [x] Rework `src/scripts/test_reference.py` as a text-column comparator.
- [x] Add CLI tests for success, failure, different columns, edge-shaped inputs,
      invalid columns, and missing files.
- [x] Update README documentation for `tester`.
- [x] Update `AGENTS.md` with the alignment rule.
- [x] Run focused pytest checks.

## Verification Log

Implementation completed for the shared module, CLI helper, tests, README, and AGENTS guidance.

Focused check:

```bash
.env/bin/pytest tests/test_reference_helpers.py tests/test_tester_reference.py tests/test_tester_dump.py
# 49 passed
```
