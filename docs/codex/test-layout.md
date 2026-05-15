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
3. `runner.run_test()` sorts workflow steps by their `input` field, runs each Yambo-related executable, and writes `results.toml`.
4. `runner.run_pytest()` invokes pytest with `--rundir=<run_dir>`.
5. `src/yambo_tester/tests/test_reference.py` reads `results.toml` plus `tests.toml` and validates runs and references.

## `tests.toml`

Each workflow step is a TOML table such as:

```toml
[03_qp_cohsex]
exe = "yambo"
input = "INPUTS/03_QP_COHSEX"
output = "03_QP_COHSEX"

[03_qp_cohsex.reference]
"o-03_QP_COHSEX.ndb.QP" = ["03_QP_COHSEX/ndb.QP", "QP_Z"]
"o-03_QP_COHSEX.qp" = ["o-03_QP_COHSEX.qp"]
"o-example.qp" = { path = "o-example.qp", skip_columns = [5], tolerance = 0.11, whitelist = false }
"r-03_QP_COHSEX_em1s_HF_and_locXC_gw0_cohsex" = [""]
```

Important fields:

- `exe`: key into validated executable parameters, for example `yambo`, `ypp`, `yambo_ph`.
- `input`: input file passed with `-F`; also used for step ordering.
- `output`: output directory/name passed with `-J` and `-C`.
- `flags`: optional suffix appended to the `-J` target.
- `nprocs`: optional per-step MPI-rank override; otherwise the global configured `nprocs` is used.
- `actions`: optional pre-run actions such as simple `mkdir` or `cp` steps.
- `reference`: maps reference files in `REFERENCE/` to generated output paths and, for NetCDF databases, selected variables.

Reference entries support two forms:

- Legacy list form: `["path/to/output", "optional_variable"]`.
- Metadata table form: `{ path = "output", variables = ["var"], skip_columns = [5], tolerance = 0.11, whitelist = true }`.

Bare output filenames resolve relative to the step `output` directory. `skip_columns` values are 1-based, matching Yambo text headers.

`SAVE/` and `SAVE_converted/` may be empty in the source tree. They are populated from private tarballs during setup.
