# AGENTS.md

## Purpose

`yambo-tester` is a Python test runner and validator for regression tests of the Yambo HPC code. Yambo itself is mainly Fortran/C and supports MPI, OpenMP, and accelerator builds, but this repository should remain clean, idiomatic Python.

Use the legacy `yambo-tests` repository only as a behavioral reference, not as code to port line by line. The local checkout is usually at `~/src/yambo-tests`.

## First Things To Read

- `README.md`: user-facing reference for installation, CLI usage, configuration precedence, executable discovery, scratch/cache behavior, and current roadmap.
- [docs/codex/test-layout.md](docs/codex/test-layout.md): imported test layout and `tests.toml` conventions.
- [docs/codex/validation-rules.md](docs/codex/validation-rules.md): Yambo output types and legacy validation concepts.
- [docs/codex/imported-test-validation-progress.md](docs/codex/imported-test-validation-progress.md): current progress on imported-test validation fixes.

## Repository Map

- `src/yambo_tester/cli.py`: `yambo-tester` CLI entry point.
- `src/yambo_tester/config.py`: defaults plus parameter, executable, and working-directory checks.
- `src/yambo_tester/download.py`: SAVE tarball download and extraction support.
- `src/yambo_tester/log.py`: logging setup.
- `src/yambo_tester/runner.py`: run-directory setup, Yambo command execution, and pytest launch.
- `src/yambo_tester/data/config.toml`: packaged default/template config.
- `src/yambo_tester/tests/test_reference.py`: main pytest validation logic.
- `src/scripts/test_reference.py`: standalone experimental validation script; use it for prototyping only.

## Working Rules

- Make small, incremental changes and preserve the current architecture.
- Prefer focused fixes for already imported tests before adding broad new features.
- Use pytest as the validation mechanism; avoid adding a parallel custom test framework.
- Keep `README.md` as the user-facing source of truth. Do not duplicate large usage docs here.
- Keep test data layout compatible with the imported `yambo-tests/TESTS/MAIN` structure when practical.
- Do not blindly translate Perl, Bash, or Fortran from `yambo-tests`; extract the behavior and implement it clearly in Python.
- Be careful with MPI/OpenMP/GPU assumptions. Missing project executables should skip only the affected tests, while missing core executables should fail early as described in the README.

## Current Priority

The urgent development path is to make the already imported tests pass correctly. Many failures are expected to come from incomplete Python equivalents of legacy `config/RULES.h`, `config/WHITELIST.h`, and `scripts/find_the_diff/` behavior.

When fixing validation:

- Inspect the failing imported test and its `tests.toml` first.
- Compare against `~/src/yambo-tests/config/RULES.h`, `~/src/yambo-tests/config/WHITELIST.h`, and `~/src/yambo-tests/scripts/find_the_diff/` only for semantics.
- Add focused pytest coverage or fixture coverage for the rule being implemented.
- Keep numerical tolerances and skip/whitelist behavior explicit and documented in code or supporting docs.

## Commands

Typical local setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Useful checks:

```bash
pytest
yambo-tester -h
yambo-tester -i
```

Full `yambo-tester` runs require valid Yambo executables and access to cached or downloadable SAVE tarballs.
