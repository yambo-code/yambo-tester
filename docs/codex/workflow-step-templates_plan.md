# Workflow Step Templates Plan

Status: implemented.

## Summary

Many imported `tests.toml` files repeat the same step metadata for common DFT
workflows. Add reusable workflow step templates so local workflow files can
declare a compact step table with `step_type` plus only test-specific
overrides.

Template expansion should happen after the workflow directory is copied to
scratch and before tarball download/extraction logic consumes workflow
metadata. The source fixture stays compact, while the scratch `tests.toml` is
rewritten as a fully expanded file for normal execution and debugging.

## Template Location and Format

Store packaged templates in:

```text
src/yambo_tester/data/workflow_templates.toml
```

This keeps reusable metadata beside `config.toml` and
`workflow_keywords.toml`. Add the file to package data in `pyproject.toml`.

Each top-level template table is a reusable `step_type`:

```toml
[HF]
exe = "yambo"
input = "INPUTS/Y6/{step}"
output = "{step}"
runlevel = "hf"
nprocs = 1
dependencies = ["{previous_step}"]

[HF.reference]
"REFERENCE/Y6/o-{step}.ndb.SE_Fock" = ["{step}/ndb.SE_Fock", "SPECTRAL_FUNCTION"]

[HF.versions."5"]
input = "INPUTS/Y5/{step}"
```

Initial templates focus on exact, low-risk repetition already present in the
imported DFT suite:

- `p2y`: Quantum ESPRESSO SAVE conversion with common stdout references.
- `init`: standard Yambo initialization.
- `HF`: standard DFT Hartree-Fock/local-XC step.
- `a2y`: minimal ABINIT conversion smoke check.

Do not template broader GW, optics, ELPH, or PA-chain workflows in the first
pass unless an exact repeated shape is identified.

## Expansion Rules

Add a new module such as:

```text
src/yambo_tester/template_expansion.py
```

Responsibilities:

- Load packaged workflow templates.
- Detect workflow steps containing `step_type`.
- Expand only templated steps; leave fully expanded old-style steps unchanged.
- Preserve top-level workflow metadata such as `sha256`, `tarball_url`,
  `yambo_versions`, and `versions`.
- Return a normal expanded workflow config that can be written with `toml.dump`.

Supported placeholders:

- `{step}` resolves to the local step table name, for example `02_HF`.
- `{previous_step}` resolves to the previous workflow step table in TOML
  insertion order, excluding workflow metadata tables. For the first step it
  resolves to an empty string unless the local step overrides the relevant
  field.

Apply placeholders recursively in strings, lists, dictionaries, reference keys,
reference values, and version-specific sections.

## Precedence and References

For a step with `step_type`, construct expanded metadata in this order:

1. Template base fields.
2. Local step base overrides.
3. Template version sections.
4. Local version-section overrides.

Local scalar, list, and table values replace template values, except
`reference` tables are merged by reference key.

Reference merge order:

1. Template base `reference`.
2. Local base `reference`.
3. Template version `reference`.
4. Local version `reference`.

Version-specific reference tables should be written as complete merged
replacement tables under `[step.versions."<major>".reference]`. This preserves
the existing shallow behavior of `resolve_step_metadata()`, where a
version-specific `reference` replaces the base `reference`.

Unknown `step_type` should raise a clear `ValueError` naming the missing
template and workflow file.

## Runtime Flow

Update `runner.setup_rundir()`:

1. Copy the source workflow directory to scratch.
2. Read the scratch `tests.toml`.
3. If any step uses `step_type`, expand templates and rewrite the scratch
   `tests.toml` with fully expanded metadata.
4. Continue with existing version support checks, tarball URL resolution,
   checksum validation, tarball extraction, execution, and pytest validation.

This is the preferred strategy because the rest of the workflow can continue to
consume a normal expanded `tests.toml`, and users can inspect the scratch file
when debugging.

## Migration

Migrated:

- `src/yambo_tester/tests/Si_bulk/DFT/tests.toml`
- `src/yambo_tester/tests/He/DFT/tests.toml`
- `src/yambo_tester/tests/Al_bulk/DFT/tests.toml`
- `src/yambo_tester/tests/PA_chain/DFT/tests.toml`
- `src/yambo_tester/tests/Nickel/DFT/tests.toml`
- `src/yambo_tester/tests/AlAs/DFT/tests.toml`
- `src/yambo_tester/tests/hBN/DFT/tests.toml`
- `src/yambo_tester/tests/Iron_With-SOC/DFT/tests.toml`
- `src/yambo_tester/tests/Iron_Without-SOC/DFT/tests.toml`

`Si_bulk` and `He` add local `p2y` database references on top of the common
stdout conversion template. `Al_bulk` and `PA_chain` keep explicit init input
paths as local overrides on `step_type = "init"`. Existing fully expanded
workflows remain valid so migration can stay gradual.

## Documentation

Update:

- `docs/codex/test-layout.md`: detailed template format, placeholders,
  precedence, version interactions, and scratch expansion behavior.
- `README.md`: concise user-facing guide for `step_type`.
- `AGENTS.md`: note that reusable workflow behavior belongs in
  `data/workflow_templates.toml`, while per-workflow differences should stay as
  local overrides.

## Verification

Add focused tests for:

- A step with `step_type` expanding from a template.
- Local fields overriding template defaults.
- `{step}` in normal fields, reference keys, and reference values.
- `{previous_step}` dependency resolution.
- Template version-specific overrides.
- Local version-specific overrides winning over template version-specific
  values.
- Template and local references merging correctly.
- Fully expanded old-style `tests.toml` remaining unchanged.
- Yambo 5 and Yambo 6 metadata still resolving through existing version logic.
- `setup_rundir()` writing an expanded scratch `tests.toml` only when needed.

Useful validation commands:

```bash
python3 -m pytest tests/test_template_expansion.py tests/test_versioning.py tests/test_runner_p2y.py tests/test_workflow_metadata.py
python3 -m pytest
```
