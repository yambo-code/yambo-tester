# Executables Refactor Plan

## Summary

Refactor executable handling so startup validation and workflow execution use a single executable registry instead of one config field per executable.

The new model keeps `yambo`, `p2y`, and `a2y` always required, makes `ypp` optional, removes `c2y`, and allows any additional optional executable to be configured without changing the core schema again.

Track implementation progress in `docs/codex/executables-refactor_progress.md`.

## Current State

- `src/yambo_tester/config.py` uses a registry-oriented executable model and resolves required tools automatically while only checking optional tools when they are explicitly registered.
- `src/yambo_tester/cli.py` accepts generic `--exe KEY=VALUE` overrides instead of one flag per executable.
- `src/yambo_tester/runner.py` resolves each step's `exe` through the executable registry.
- `src/yambo_tester/data/config.toml`, `README.md`, `ADDING_TESTS.md`, and `docs/codex/test-layout.md` document the registry model.
- Missing optional executables are handled as step-level skips instead of startup failures.

## Proposed Design

Use a dedicated executable registry in config:

```toml
[executables]
yambo = "yambo"
p2y = "p2y"
a2y = "a2y"
ypp = "ypp"
yambo_ph = "yambo_ph"
ypp_ph = "ypp_ph"
custom_tool = "my_custom_executable"
```

Workflow steps continue to use `exe = "..."` keywords in `tests.toml`, but the keyword is now resolved through the registry.

### Why this design

- It removes the need to add one config field per future executable.
- It keeps the workflow `exe` value as the stable indirection point.
- It makes required vs optional status an application rule, not a config-schema rule.
- It avoids the positional fragility of parallel `extra_exe_keywords` / `extra_exe_names` lists.

### Rejected alternatives

- Parallel keyword/name lists: too easy to misalign and harder to review.
- Separate required/optional config tables: the required set is fixed by the application, so letting users edit that split adds confusion.
- Array of tables: useful only if executable-specific metadata becomes necessary later.

## Implementation Plan

### 1. Configuration model

- Completed.

### 2. Discovery and validation

- Completed.

### 3. CLI and config overrides

- Completed.

### 4. Runner behavior

- Completed.

### 5. Documentation cleanup

- Completed.

## Tests To Add Or Update

- Implemented and covered by focused pytest cases.

## Backward Compatibility

This refactor is intentionally a breaking cleanup.

- Legacy per-executable config keys under `[parameters]` are not preserved as the public interface.
- Dedicated executable CLI flags are removed instead of translated.
- The only stable interface for workflow steps remains the `exe` keyword in `tests.toml`.

## Assumptions

- Required executables are application-defined and cannot be downgraded in TOML.
- Optional executables are only checked if configured in the registry.
- Missing optional executables should lead to skipped steps, not startup failure.
- No special dependency-propagation rule is introduced for skipped steps.
