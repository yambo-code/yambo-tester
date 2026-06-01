# Test Layout Notes

Imported tests live under `src/yambo_tester/tests/` and intentionally resemble the legacy `yambo-tests/TESTS/MAIN/` layout:

```text
<system>/
  <workflow>/
    INPUTS/
    REFERENCE/
    SAVE/
    SAVE_converted/
    tests.toml
    optional extra data directories
```

Examples currently include `Al_bulk/GW-OPTICS`, `Al_bulk/ELPH`, and `PA_chain/PA_chain`.

## Runtime Flow

1. `cli.py` loads configuration, applies CLI overrides, validates parameters, then loops over selected tests.
2. `runner.setup_rundir()` downloads or reuses the test tarball, copies the imported fixture tree to scratch, extracts SAVE data, and returns the run directory.
3. `runner.run_test()` sorts workflow steps by their `input` field when present, runs each Yambo-related executable, and writes `results.toml`.
4. `runner.run_pytest()` invokes pytest with `--rundir=<run_dir>`.
5. `src/yambo_tester/tests/test_reference.py` reads `results.toml` plus `tests.toml` and validates runs and references.

## `tests.toml`

Each workflow step is a TOML table such as:

```toml
[03_qp_cohsex]
exe = "yambo"
input = "INPUTS/03_QP_COHSEX"
output = "03_QP_COHSEX"
runlevel = "qp"
dependencies = ["01_init"]

[03_qp_cohsex.reference]
"o-03_QP_COHSEX.ndb.QP" = ["03_QP_COHSEX/ndb.QP", "QP_Z"]
"o-03_QP_COHSEX.qp" = ["o-03_QP_COHSEX.qp"]
"o-example.qp" = { path = "o-example.qp", skip_columns = [5], tolerance = 0.11, whitelist = false }
"r-03_QP_COHSEX_em1s_HF_and_locXC_gw0_cohsex" = ["Game Over & Game summary"]
```

Important fields:

- `exe`: key into the executable registry, for example `yambo`, `ypp`,
  `yambo_ph`, `ypp_ph`, or a custom key declared under `[executables]`.
- `input`: input file passed with `-F`; also used for step ordering.
- `output`: output directory/name passed with `-J` and `-C`.
- `input_dir`: input directory passed with `-I`, used by conversion tools such as `p2y`.
- `runlevel`: primary Yambo runlevel represented by the step.
- `dependencies`: prerequisite step table names used for runlevel-based
  selection.
- `flags`: optional suffix appended to the `-J` target.
- `nprocs`: optional per-step MPI-rank override; otherwise the global configured `nprocs` is used.
- `actions`: optional pre-run actions such as simple `mkdir` or `cp` steps.
- `reference`: maps reference files in `REFERENCE/` to generated output paths and, for NetCDF databases, selected variables.

Reference entries support two forms:

- Legacy list form: `["path/to/output", "optional_variable"]`.
- Metadata table form: `{ path = "output", variables = ["var"], skip_columns = [5], tolerance = 0.11, whitelist = true }`.

Bare output filenames resolve relative to the step `output` directory. `skip_columns` values are 1-based, matching Yambo text headers.

Conversion-tool steps may omit `input` and `output`. A `STDOUT` reference key
checks that the expected string is present in the captured command stdout or,
if present, the step's `l_<exe>` log file. For example,
`STDOUT = ["== P2Y completed =="]`. Report references whose keys start with
`r-` still check report completeness; a non-empty string value additionally
checks that the string is present in the resolved report file, so avoid empty
placeholder strings in imported fixtures.

Executable discovery happens through the registry in `config.toml`, with
`yambo`, `p2y`, and `a2y` required at startup and optional tools checked only
when they are explicitly registered in `[executables]` or via `--exe KEY=VALUE`.

The packaged keyword inventory used by `--list-executables` and
`--list-runlevels` lives in `src/yambo_tester/data/workflow_keywords.toml` and
is kept in sync with the imported workflow `tests.toml` files.

`SAVE/` and `SAVE_converted/` may be empty in the source tree. They are populated from private tarballs during setup.

## Runlevel Selection

`yambo-tester --runlevel <name>` runs all steps whose `runlevel` matches
`<name>`, plus the transitive closure of their `dependencies`. Steps outside
that selected set are still written to `results.toml` with an intentional skip
marker so pytest reports them as skipped instead of failing on missing outputs.

With no selected runlevel, every workflow step runs as before.
