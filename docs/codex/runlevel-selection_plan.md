# Runlevel-Based Test Selection Plan

## Summary

Add per-step workflow metadata in `tests.toml` so `yambo-tester` can run only steps matching selected Yambo runlevels, plus their declared dependencies, while pytest intentionally skips unrelated references.

Maintain task progress in `docs/codex/runlevel-selection_progress.md`.

## Key Changes

- Extend each workflow step table with `runlevel = "..."` and `dependencies = ["step_id", ...]`.
- Add repeatable CLI selection with `yambo-tester --runlevel qp --runlevel bse`.
- Add equivalent config selection with `runlevels = ["qp", "bse"]` under `[parameters]`.
- If no runlevel is selected, run all steps as before.
- If runlevels are selected, execute matching steps plus the transitive closure of their dependencies.
- Preserve current step ordering by sorted `input`.
- Fail early when a dependency references an unknown step.
- Mark unrelated steps as intentionally skipped in `results.toml` so pytest skips their references.

## Implementation Details

- Add a small selection helper to normalize selected runlevels, validate dependency references, and compute the selected step set.
- Update `runner.run_test()` so every step still gets a `results.toml` entry:
  - Executed steps keep current behavior.
  - Missing executable skips keep `returncode = -9999`.
  - Runlevel-filtered skips use `returncode = -9998` and `skip_reason = "runlevel-filter"`.
- Update pytest generation in `test_reference.py` so references for filtered steps are skipped cleanly.
- Update packaged config and user docs to describe `runlevel`, `dependencies`, and `--runlevel`.
- Add runlevel/dependency metadata to the imported workflow `tests.toml` files.

## Test Plan

- Add focused unit tests for selection expansion, dependency validation, no-selection behavior, and CLI parsing.
- Add validation coverage showing runlevel-filtered steps do not fail reference checks.
- Run `.env/bin/pytest -q`.
- Run `.env/bin/yambo-tester -h`.

## Assumptions

- Dependency values reference step table names.
- A selected runlevel always runs its dependencies by default.
- Each step has one primary runlevel for this task.
- `AGENTS.md` does not need a link for this task-specific plan.
