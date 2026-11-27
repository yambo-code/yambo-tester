# Cross-workflow dependency progress

Tracks the implementation of [workflow-dependencies_plan.md](workflow-dependencies_plan.md):
GW workflows declare `requires = "DFT"` and start from the DFT SAVE instead of
downloading their own tarball.

## Checklist

- [x] 1. Plan and progress documents in `docs/codex`.
- [x] 2. Python support:
  - [x] `requires` in `WORKFLOW_METADATA_KEYS` (`versioning.py`);
  - [x] `expand_workflow_requirements` (`selection.py`) and CLI run loop;
  - [x] `setup_rundir` copies the required SAVE, skips download/checksum;
  - [x] `DEPENDENCY_FAILED_RETURNCODE` / `required-workflow-failed` skip;
  - [x] `--donly` skips dependent workflows;
  - [x] unit tests (`test_selection.py`, `test_runner_p2y.py`).
- [x] 3. Pilot migration: He/DFT (p2y only) and He/GW (`requires = "DFT"`),
  end-to-end run.
- [x] 4. Migrate AlAs, Al_bulk, hBN, hBN_2D, Iron_Without-SOC, Nickel,
  PA_chain; trim Si_bulk/DFT to p2y only.
- [x] 5. Documentation (`README.md`, `AGENTS.md`, `test-layout.md`),
  metadata tests, full validation run.

## Scope Notes

- In scope (GW tarball identical to the DFT tarball, checked file by file on
  2026-11-26): AlAs, Al_bulk, He, hBN, hBN_2D, Iron_Without-SOC, Nickel,
  PA_chain.
- Out of scope: Si_bulk/GW and Si_bulk/GW-RUNTIME. Their `si.save` comes from
  a different QE calculation (ONCV PBE, 20 Ry, unshifted 4x4x4 grid, 10 bands)
  than Si_bulk/DFT (vbc LDA, 15 Ry, shifted grid, 32 bands); the QE inputs
  for the GW SAVE are not in the repository.
- Init references to move from DFT to GW `01_init`:
  - He, hBN_2D, Nickel: all init DBs (DFT and GW init are identical);
  - Al_bulk, PA_chain: k-point index DBs only (DFT init uses `MaxGvecs`, so
    `ndb.gops` differs from the GW init).

## Log

### 2026-11-26

- Compared GW and DFT tarballs in the cache: identical content for the eight
  in-scope systems; Si_bulk differs.
- Compared the first two steps of GW and DFT workflows (expanded
  `tests.toml` and generated SAVE/init databases, ignoring `SERIAL_NUMBER`).
- Agreed design with the user and wrote the plan.

### 2026-11-27

- Step 2 done (uncommitted):
  - `versioning.py`: `requires` added to `WORKFLOW_METADATA_KEYS`.
  - `selection.py`: `DEPENDENCY_FAILED_RETURNCODE = -9996`,
    `DEPENDENCY_FAILED_REASON = "required-workflow-failed"`,
    `expand_workflow_requirements(tests, requires_of)` (required workflow
    first, auto-added, deduplicated, cycles rejected).
  - `runner.py`: `workflow_requires()`; `parameters_with_workflow_download_link`
    returns `None` for a `requires` workflow (no download, also in `--donly`);
    `setup_rundir` calls `copy_required_save()` instead of download/checksum/
    extraction; `required_workflow_problem()` requires `results.toml` with all
    step return codes 0 and a `SAVE` directory, otherwise the test gets
    `required_workflow_failed` and `run_test` records every step as -9996.
  - `tests/test_reference.py` (packaged): -9996 is a skip.
  - `cli.py`: iterates `expand_workflow_requirements(...)`, logs auto-added
    workflows; `--donly` uses the same list.
- Design addition: a workflow required by another selected workflow ignores
  `--runlevel` filtering (it is run in full and the CLI logs it), otherwise a
  filtered-out conversion step would leave no SAVE and every dependent step
  would be skipped.
- `pytest tests`: 196 passed; only the known pre-existing failure
  `test_packaged_templates_cover_conversion_and_local_init_overrides` remains.
  `tests/test_logging.py` CLI test now stubs `workflow_requires`.
- Not yet covered by unit tests: the CLI runlevel override for required
  workflows (exercised in the step 3 pilot run).

### 2026-11-27 (step 3)

- He/DFT: only `00_p2y`; removed `INPUTS/Y*/01_init*`, `INPUTS/Y*/02_HF`
  and every `REFERENCE/*/{l,o,r}-0[12]_*` file, including the unreferenced
  Y5 `KPT_indexes` and `l-` logs.
- He/GW: `requires = "DFT"`, no `sha256`/`tarball_url`, no `00_p2y` (its
  `o-00_p2y.*` references removed); `01_init` is now `step_type = "init"`, so
  it gets the template init references. The init DBs referenced by the DFT
  template (Y5 `ndb.gops`, `ndb.kindx`; Y6 `ndb.RL_shells`,
  `KPT_indexes_fragment_1/2`) were moved with `git mv`; the GW
  `r-01_init_setup` reports were kept.
- `template_expansion.py`: empty dependencies are dropped, so a first
  templated step (`{previous_step}` = `""`) gets `dependencies = []`
  (test `test_first_templated_step_has_no_empty_previous_step_dependency`).
- `tests/test_workflow_metadata.py` (planned for step 5, needed now): uses
  `WORKFLOW_METADATA_KEYS`; a `requires` workflow must have no
  `tarball_url`/`sha256`; new
  `test_required_workflows_exist_and_have_no_requirement_themselves`.
- `pytest tests`: 198 passed, only the known template failure remains.
- Pilot runs in `/home/nicola/tmp/yambo-tester-gw-y6/run_deps_he`
  (`[tests] He = ["GW"]`, Yambo 5.3.0, 1 MPI task):
  - plain run: He/DFT auto-added and run first, no GW download, SAVE copied
    (DFT SAVE untouched by the GW init); DFT 5/5 and GW 19/19 passed;
  - `--runlevel rim_cut`: DFT run in full (logged); DFT 5/5, GW 19/19;
  - `--exe p2y=/bin/false`: DFT fails (5 failures); GW logs "required
    workflow He/DFT not usable: step 00_p2y returned 1" and all 19 GW tests
    are skipped ("required workflow failed").

### 2026-11-27 (step 4)

- GW `tests.toml` of AlAs, Al_bulk, hBN, hBN_2D, Iron_Without-SOC, Nickel,
  PA_chain: `requires = "DFT"` replaces `sha256`/`tarball_url`; the
  `00_p2y`/`00_a2y` step and its `REFERENCE/*/o-00_*` files are removed;
  `01_init` has `dependencies = []`. No later GW step uses tarball files
  other than `SAVE` (checked `actions`, `DB/`, `*.save` uses).
- Init references:
  - Nickel: `01_init` is now `step_type = "init"`; Y5 `ndb.gops`,
    `ndb.kindx` and Y6 `ndb.RL_shells`, `KPT_indexes_fragment_1/2` moved
    from DFT with `git mv`.
  - hBN_2D: GW already used `step_type = "init"` with its own init DB
    references; the DFT copies were deleted.
  - Al_bulk, PA_chain: explicit `01_init` gets only the k-point index
    references (Y5 `ndb.kindx`: `Qindx`, `Sindx`; Y6
    `KPT_indexes_fragment_1`: `Qindx`, `KPT_indexes_fragment_2`: `Sindx`),
    moved from DFT.
  - AlAs, hBN, Iron_Without-SOC: DFT had no init step; nothing to move.
- DFT `tests.toml` of Al_bulk, hBN_2D, Nickel, PA_chain, Si_bulk: only the
  conversion step is left; `INPUTS/Y*/01_init`, `INPUTS/Y*/02_HF` and every
  remaining `REFERENCE/*/{l,o,r}-0[12]_*` file were deleted.
- `pytest tests`: 198 passed, only the known template failure remains.
- Full run started in `/home/nicola/tmp/yambo-tester-gw-y6/run_deps_all`
  (config of `serial_run_53_mpi1`, Yambo 5.3.0, 1 MPI task).
- Full run finished (08:35:33 -> 09:16:51, about 41 min; scratch
  `20261127_083533_run_deps_all`): 0 failures, 0 errors in all 23
  workflows.
  - The 7 GW workflows log "Copied SAVE from <system>/DFT" and do not
    download; all other workflows download as before.
  - Skips: Al_bulk/ELPH 14 (`ypp` not registered, as before); hBN_2D/GW
    `o-05_rimw.qp` xfail (whitelisted).
  - AlAs/DFT passed only because a temporary reference regenerated from
    a2y 5.3.0 was in place when the run copied the workflow; that
    reference was then restored and whitelisted (a2y 5.3 and 5.4 permute
    G-vectors inside equal-|G| shells; which is correct is under
    investigation). A separate AlAs/DFT run with the restored reference
    gives 4 passed, 1 xfailed.
  - Run time is the same as the 2026-11-26 serial run (about 40 min): the
    saved p2y/a2y, DFT init/HF and tarball extraction take seconds; the
    time is spent in the GW steps.
- Future full runs: Yambo 5.3.0 with 4 MPI tasks (user request, to reduce
  run time).

### 2026-11-27 (step 5)

- `README.md`: new "Workflow Dependencies" subsection under Usage (before
  "Scratch and Cache Directories").
- `AGENTS.md`: rule for `requires` workflows next to the tarball-source rule.
- `docs/codex/test-layout.md`: runtime flow updated, new "Workflow
  Dependencies" section, `{previous_step}` empty-dependency note, `requires`
  listed among preserved metadata.
- Metadata tests were already updated in step 3; full validation run done in
  step 4. All planned steps are complete; nothing committed yet.
- Follow-ups outside this plan: AlAs a2y G-vector ordering (5.3 vs 5.4,
  reference whitelisted); next full runs with Yambo 5.3.0 on 4 MPI tasks.
