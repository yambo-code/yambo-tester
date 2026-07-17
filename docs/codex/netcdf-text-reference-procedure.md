# NetCDF Text Reference Procedure

## Purpose

Use this procedure when an imported workflow already declares NetCDF-backed
`o-*` references, but the small committed text reference files are missing.
The goal is to generate only the required `REFERENCE/Y*/o-*` text fixtures from
successful scratch outputs.

Do not commit runtime NetCDF files such as `ndb.*`, `ns.*`, scratch trees,
cache tarballs, or logs.

## Preflight

1. Inspect the target workflow `tests.toml` first. Confirm which steps are
   present, which Yambo versions are supported, and whether references come
   from local step metadata or reusable templates.
2. If a step uses `step_type`, inspect
   `src/yambo_tester/data/workflow_templates.toml` and expand the placeholders
   mentally:
   - `{step}` becomes the local step table name, such as `00_p2y`.
   - `{previous_step}` becomes the previous workflow step name.
3. Check existing `REFERENCE/Y5` and `REFERENCE/Y6` files. Do not overwrite
   existing references unless the task explicitly requires regenerating them.
4. Check `git status --short` before generating files. Treat unrelated local
   changes as user-owned and keep the reference update scoped.

## Run The Target Workflow

Create an isolated work directory for each debugging target, for example:

```bash
mkdir -p /tmp/yambo-tester-<system>-<workflow>-y5
cd /tmp/yambo-tester-<system>-<workflow>-y5
/home/nicola/src/yambo-tester/.env/bin/yambo-tester -i
```

Edit only that temporary `config.toml`:

- Select the target workflow under `[tests]` and comment out unrelated tests.
- Set `yambo_version = "5"` or `yambo_version = "6"` explicitly.
- For Yambo 6 builds outside `PATH`, set `yambo_bin` to the build `bin`
  directory, such as `/home/nicola/src/nicspalla/yambo6/bin`.
- If `mpirun` is not discoverable after loading modules, set `mpi_launcher` to
  the known OpenMPI path from a successful run.

Run one Yambo major version at a time. Typical commands are:

```bash
module load spack/1.0
module load yambo/5.3.0--gcc-14.3.0--openmpi-5.0.8-projects-omp-pario-slk-slepc-27vuyas
/home/nicola/src/yambo-tester/.env/bin/yambo-tester
```

```bash
module load profile/gcc-14.3.0
/home/nicola/src/yambo-tester/.env/bin/yambo-tester
```

The first run may fail in pytest with missing-reference assertions. That is
expected if the Yambo commands completed and produced the required NetCDF files
in the scratch workflow `SAVE/` or step output directories.

## Identify Missing References

Use the pytest failures and the expanded scratch `tests.toml` to map every
missing reference key to:

- The generated NetCDF output path.
- The variable or variables to dump.
- The committed reference path under `REFERENCE/Y5` or `REFERENCE/Y6`.

For DFT template steps, common mappings are:

| Version | Reference | Output | Variables |
| --- | --- | --- | --- |
| Y5 | `REFERENCE/Y5/o-00_p2y.ns.db1` | `SAVE/ns.db1` | `EIGENVALUES` |
| Y6 | `REFERENCE/Y6/o-00_p2y.ns.electrons` | `SAVE/ns.electrons` | `EIGENVALUES` |
| Y5 | `REFERENCE/Y5/o-00_p2y.ns.kb_pp_pwscf_fragment_1` | `SAVE/ns.kb_pp_pwscf_fragment_1` | `PP_KB_K1` |
| Y6 | `REFERENCE/Y6/o-00_p2y.ns.kb_pp_pwscf_fragment_1` | `SAVE/ns.kb_pp_pwscf_fragment_1` | `PP_KB_K1` |
| Y5 | `REFERENCE/Y5/o-00_p2y.ns.wf_fragments_1_1` | `SAVE/ns.wf_fragments_1_1` | `WF_COMPONENTS_@_SP_POL1_K1_BAND_GRP_1` |
| Y6 | `REFERENCE/Y6/o-00_p2y.ns.wf_fragments_1_1` | `SAVE/ns.wf_fragments_1_1` | `WF_COMPONENTS_@_SP_POL1_K1_BAND_GRP_1` |
| Y5 | `REFERENCE/Y5/o-01_init.ndb.gops` | `SAVE/ndb.gops` | `ng_in_shell`, `E_of_shell` |
| Y5 | `REFERENCE/Y5/o-01_init.ndb.kindx` | `SAVE/ndb.kindx` | `Qindx`, `Sindx` |
| Y6 | `REFERENCE/Y6/o-01_init.ndb.RL_shells` | `SAVE/ndb.RL_shells` | `ng_in_shell`, `E_of_shell` |
| Y6 | `REFERENCE/Y6/o-01_init.ndb.KPT_indexes_fragment_1` | `SAVE/ndb.KPT_indexes_fragment_1` | `Qindx` |
| Y6 | `REFERENCE/Y6/o-01_init.ndb.KPT_indexes_fragment_2` | `SAVE/ndb.KPT_indexes_fragment_2` | `Sindx` |

If the workflow uses local reference metadata, prefer that metadata over the
table above.

## Generate Text References

Generate committed references with `tester-dump` from the successful scratch
run. Repeat `-v` in the same order listed by `tests.toml` or the template:

```bash
/home/nicola/src/yambo-tester/.env/bin/tester-dump \
  -i /tmp/yambo-tester-nickel-y5/scratch/<run>/Nickel/DFT/SAVE/ns.db1 \
  -v EIGENVALUES \
  -o /home/nicola/src/yambo-tester/src/yambo_tester/tests/Nickel/DFT/REFERENCE/Y5/o-00_p2y.ns.db1
```

```bash
/home/nicola/src/yambo-tester/.env/bin/tester-dump \
  -i /tmp/yambo-tester-nickel-y5/scratch/<run>/Nickel/DFT/SAVE/ndb.gops \
  -v ng_in_shell -v E_of_shell \
  --max-values 250 \
  -o /home/nicola/src/yambo-tester/src/yambo_tester/tests/Nickel/DFT/REFERENCE/Y5/o-01_init.ndb.gops
```

`tester-dump` writes only numeric values, one per line. It flattens each
variable in `netCDF4` order and writes at most the first 100 values per
variable by default. Use `--max-values` to choose a different per-variable
limit.

## Handle Y5/Y6 Naming Differences

Y5 and Y6 often store equivalent data under different database names. Copying
or renaming a text reference across versions is acceptable only when the
workflow semantics and existing examples show that the dumped data are
equivalent, or when a direct comparison confirms it.

Examples from DFT workflows:

- Y5 `o-00_p2y.ns.db1` may correspond to Y6
  `o-00_p2y.ns.electrons`.
- Y5 `o-01_init.ndb.gops` may correspond to Y6
  `o-01_init.ndb.RL_shells`.
- The first `kb_pp_pwscf` and `wf_fragments` references may be byte-identical
  across Y5 and Y6 for the same workflow.

When in doubt, generate the Y5 and Y6 files independently from successful runs
instead of copying.

## Verify

Rerun the target workflow for every supported Yambo major version after adding
the references. The acceptance criterion is no missing-reference failures for
the target workflow.

For example, the Nickel/DFT reference update was verified with:

```text
Y5 Nickel/DFT: 9 passed
Y6 Nickel/DFT: 10 passed
```

If validation fails after references exist, inspect whether the failure is a
real numerical mismatch, a bad output path, an incorrect variable list, or a
version mismatch. Fix `tests.toml` metadata before changing generic Python
validation logic.

## Commit Checklist

Before committing:

- `git status --short` shows only intended workflow files.
- Added files are under `src/yambo_tester/tests/<system>/<workflow>/REFERENCE/Y5`
  or `REFERENCE/Y6`.
- Any `tests.toml` change is required for the workflow to run or validate, such
  as adding a missing templated step.
- No scratch files, cache tarballs, NetCDF runtime databases, logs, or pytest
  reports are staged.
- The commit message names the workflow and the reference kind, for example
  `Add Nickel DFT text references`.

## Troubleshooting Notes

- If the run cannot find `mpirun`, set `mpi_launcher` in the temporary
  `config.toml` to a known absolute launcher path.
- If `tester-dump` reports a missing variable, inspect the generated NetCDF
  file and compare it with the active `tests.toml` after template expansion.
- If a workflow supports both Y5 and Y6, do not assume one version's missing
  references are sufficient. Verify both versions separately.
- If an existing local change touches the target workflow, work with it and do
  not revert it unless explicitly asked.
