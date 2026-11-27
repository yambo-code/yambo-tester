# Cross-workflow dependency: GW workflows start from the DFT SAVE

## Context

Eight GW workflows download a tarball whose content is byte-for-byte identical to the DFT tarball of the same system. They also re-run p2y/a2y, and often `01_init`, which the DFT workflow already runs. The affected workflows are AlAs, Al_bulk, He, hBN, hBN_2D, Iron_Without-SOC, Nickel and PA_chain. The worst case is Nickel, which downloads about 95 MB twice.

The user wants:
- a workflow-level dependency, so that a GW workflow depends on the DFT workflow of the same system;
- a dependent workflow that downloads no tarball, with `sha256`/`tarball_url` no longer mandatory for it;
- DFT workflows that keep only the p2y/a2y step;
- `init` steps that stay in the GW workflows.

Decisions taken with the user:
- **DFT `02_HF` steps:** remove them (He, hBN_2D, Si_bulk), since the GW workflows already run `02_hf`.
- **DFT `01_init` references:** move them to GW `01_init` where the init is the same.
  - He, hBN_2D, Nickel: all of them.
  - Al_bulk, PA_chain: only the k-point index DBs, because the DFT init used `MaxGvecs` and `ndb.gops` differs.
- **Si_bulk:** out of scope for the dependency, since its GW SAVE is a different QE calculation. Si_bulk/GW and GW-RUNTIME keep their tarballs, but Si_bulk/DFT is still reduced to p2y only.
- **GW selected without its DFT:** the runner adds the DFT automatically, runs and validates it first, and logs this.
- **Plan/progress files:** use the existing suffix naming, `docs/codex/workflow-dependencies_plan.md` and `docs/codex/workflow-dependencies_progress.md`, written in English.

## Design

**New workflow-level key** in `tests.toml`:

```toml
requires = "DFT"   # workflow type of the same system; its SAVE is copied into this run dir
```

- Add `requires` to `WORKFLOW_METADATA_KEYS` in `src/yambo_tester/versioning.py:5`. This keeps it out of the step list, and `resolve_workflow_metadata` already applies version overlays to these keys.
- **SAVE is copied, not symlinked.** GW `01_init` writes `ndb.gops` and `ndb.kindx` into `SAVE`, which would otherwise modify the DFT run directory.

**Run order and automatic inclusion.** Add `expand_workflow_requirements(tests, tests_dir)` in `src/yambo_tester/selection.py`.
- It reads each selected workflow's source `tests.toml` with `source_workflow_config` from `runner.py:106`.
- It returns an ordered list of `(system, type)` pairs, with every required workflow placed before its dependents and duplicates removed.
- It raises on unknown required workflows or cycles.
- `cli.main` (`src/yambo_tester/cli.py:176`) iterates this list instead of the raw `config['tests']` dict and logs every auto-added workflow.

**Setup of a dependent workflow** (`setup_rundir`, `src/yambo_tester/runner.py:140`):
- When the resolved metadata has `requires`, skip the download, the `sha256` check and the extraction.
- Copy `<scratch_test>/<system>/<requires>/SAVE` into `run_dir/SAVE` with `shutil.copytree`.
- If that SAVE is missing, or the required workflow's conversion step did not return 0 in its `results.toml`, do not raise. Instead, mark the dependent workflow so that `run_test` records every step with a new skip code:
  - `DEPENDENCY_FAILED_RETURNCODE = -9996` with reason `"required-workflow-failed"`, added to `selection.py`;
  - `test_reference.py:190` and `:224` treat it as a skip, like `MISSING_EXECUTABLE_RETURNCODE`.
  - The DFT failure itself is already reported by the DFT workflow.

**Download-only mode.** `--donly` (`cli.py:164`) skips workflows that declare `requires`. `parameters_with_workflow_download_link` is never reached for them.

**Benchmark mode** (`link_save`, GrCo) is unchanged.

## Workflow data changes

- **DFT `tests.toml`, all p2y/a2y workflows including Si_bulk:**
  - Keep only `00_p2y`/`00_a2y` plus its references.
  - Remove `01_init` and `02_HF`, with their now-unused `INPUTS/Y5|Y6` files and `REFERENCE` files (`o-01_init.*`, `r-01_init*`, `l-01_init*`, `o-02_HF.*`, `r-02_HF*`, `l-02_HF*`).
  - Iron_With-SOC/DFT, AlAs/DFT, hBN/DFT and Iron_Without-SOC/DFT already contain only a2y.
- **GW `tests.toml` for the 8 systems:**
  - Add `requires = "DFT"` and drop `sha256`/`tarball_url`.
  - Remove the `00_p2y`/`00_a2y` step and its `REFERENCE/*/o-00_*` files, which the DFT already validates.
  - Set `01_init.dependencies = []`.
  - Keep `01_init` with its report check, and add the moved DFT init references:
    - He, hBN_2D, Nickel: `o-01_init.ndb.gops`, `o-01_init.ndb.kindx`, `o-01_init.ndb.KPT_indexes_fragment_*` where present, and `r-01_init_setup` (Y5 and Y6);
    - Al_bulk, PA_chain: only `ndb.kindx` (plus `KPT_indexes_*` for PA_chain), after checking that they match the GW init output.
  - Rename the files to the GW reference paths and keep the same `variables`/`tolerance` keys as in the DFT entries.
- **Si_bulk/GW and GW-RUNTIME:** no change; they keep their tarball and `00_p2y`.
- **Template expansion** (`src/yambo_tester/template_expansion.py`): the `init` template defaults `dependencies = ["{previous_step}"]`. For a first step, `previous_step` is `""`, so `01_init` in GW files must set `dependencies = []` explicitly, or `{previous_step}` must expand to no dependency. Fix whichever applies.

## Tests (pytest, `tests/`)

- **`test_selection.py`:** `expand_workflow_requirements` puts DFT before GW, auto-adds a missing DFT, removes duplicates, and rejects cycles and unknown requirements.
- **`test_runner_p2y.py`**, using the existing monkeypatch style from `test_setup_rundir_uses_same_resolved_metadata_url`, check that `setup_rundir` for a `requires` workflow:
  - copies the DFT SAVE;
  - never calls `download_test`;
  - needs no `sha256`;
  - records `DEPENDENCY_FAILED_RETURNCODE` steps when the SAVE is missing.
- **`test_workflow_metadata.py`:**
  - `test_imported_workflows_declare_version_support_and_tarball_url` (line 36): accept `requires` instead of the tarball keys, and assert that a `requires` workflow has no `tarball_url`/`sha256`.
  - Replace the hard-coded metadata-key sets at lines 63, 106 and 125 with `WORKFLOW_METADATA_KEYS`.
  - Add a check that every `requires` points to an existing sibling workflow.
- **Pre-existing failure:** `test_packaged_templates_cover_conversion_and_local_init_overrides` already fails on main; do not mask it.

## Docs

- **`docs/codex/workflow-dependencies_plan.md`:** this plan, in English, written as the first implementation step.
- **`docs/codex/workflow-dependencies_progress.md`:** a progress log in English, with a checklist of the steps below and a dated log section, updated after each step.
- **`README.md`:** a short "Workflow dependencies" subsection under Usage, near "Scratch and Cache Directories", covering `requires`, auto-inclusion and SAVE copying.
- **`AGENTS.md`:** extend the tarball-source rule. A workflow with `requires` has no tarball and starts from the required workflow's SAVE.
- **`docs/codex/test-layout.md`:** document the `requires` key.

## Implementation order

1. Write the plan and progress docs in `docs/codex`.
2. Python: the `requires` metadata key, `expand_workflow_requirements`, the `setup_rundir` copy, the skip code, the CLI loop and `--donly`, with unit tests.
3. Migrate He/DFT and He/GW first as the pilot, and run it end-to-end.
4. Migrate the other 7 systems and trim Si_bulk/DFT.
5. Update the docs and the metadata tests, and run a full validation run.

## Verification

- `pytest tests/`: everything passes except the known pre-existing template failure.
- **Pilot run** in `/home/nicola/tmp/yambo-tester-gw-y6/run_deps_he` with `[tests] He = ["GW"]` only, Yambo 5.3.0 module, 1 MPI task. Check that:
  - He/DFT is auto-added and runs first;
  - no `He_GW.tar.gz` is used;
  - `He/GW/SAVE` comes from He/DFT;
  - all references pass.
- **Full run** of the default `[tests]` without GrCo, 5.3.0 with 1 task. Compare `pytest-report.xml` with run `20261126_102638_serial_run_53_mpi1`: no new failures. GW workflow times drop by the p2y/a2y time, and Nickel no longer extracts 95 MB twice.
- **Negative check:** make the DFT p2y fail, for example with a missing executable path, and verify that the GW steps are reported as skipped with reason `required-workflow-failed`.
