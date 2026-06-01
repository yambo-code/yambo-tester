# Adding New Tests

This guide describes how to add a new test to `yambo-tester`. A test is made of
small files committed to the repository, plus a compressed tarball containing the
large `SAVE` databases used at runtime.

## Test Layout

Tests are organized by system name and workflow type:

```text
<system>/
  <workflow>/
    INPUTS/
    REFERENCE/
    SAVE/
    tests.toml
```

For example:

```text
Al_bulk/
  GW-OPTICS/
    INPUTS/
    REFERENCE/
    SAVE/
    tests.toml
```

The directory is copied to the scratch area before running. The tarball is then
extracted in the scratch test directory, so the extracted data must match the
same layout and provide the runtime `SAVE/` directory expected by Yambo.

Use only one `SAVE/` directory for new tests. Some imported legacy tests contain
both `SAVE/` and `SAVE_converted/`; when `SAVE_converted/` exists, the runner
renames the original `SAVE/` to `oldSAVE/` and uses `SAVE_converted/` as the
runtime `SAVE/`. This is retained for compatibility with imported tests and
should not be used for new tests. New tests should provide `SAVE/` databases for
the current supported Yambo version.

## Input And Reference Files

Put Yambo input files in `INPUTS/`. The path used in `tests.toml` is relative to
the workflow directory and is passed to Yambo with `-F`.

Put reference files in `REFERENCE/`. The validator currently understands these
reference types:

- `r-*`: report files. The generated report is checked for the successful-run
  marker `Game Over & Game summary`.
- `o-*`: text output files. Numerical columns are compared against the reference.
- `o-*.ndb.*`: text references for NetCDF database variables. The generated
  database is read with `netCDF4`, and only the variables listed in `tests.toml`
  are compared.

Large runtime databases should not be committed directly. Keep only small
placeholder files in the repository if needed, and put the real `SAVE/` content
in the test tarball.

## SAVE Tarball

The tarball name is derived from the test name and workflow type:

- Use `<system>_<workflow>.tar.gz` when the names differ, for example
  `Al_bulk_GW-OPTICS.tar.gz`.
- Use `<system>.tar.gz` when the names are the same, for example
  `PA_chain.tar.gz`.

Create the archive from a directory that contains the test runtime data with the
same workflow layout expected after extraction. The runner extracts the archive
inside the scratch `<system>/` directory, so for a workflow named `GW-OPTICS`
under `Al_bulk`, the archive must provide:

```text
GW-OPTICS/
  SAVE/
```

or any other runtime directories needed by that workflow. After extraction, the
runner copies the committed fixture into:

```text
<scratch>/<timestamp_label>/<system>/<workflow>/
```

and extracts the tarball into:

```text
<scratch>/<timestamp_label>/<system>/
```

A typical local command is:

```bash
cd Al_bulk
tar -czf ../Al_bulk_GW-OPTICS.tar.gz GW-OPTICS/SAVE
```

Place the tarball in the configured cache directory. The default cache directory
is `cache/`, and it can be changed in `config.toml` or on the command line:

```bash
yambo-tester --cache /path/to/cache
```

Compute the archive checksum and copy it into `tests.toml`:

```bash
sha256sum cache/Al_bulk_GW-OPTICS.tar.gz
```

## Writing `tests.toml`

Each workflow directory must contain a `tests.toml` file. It starts with the
tarball checksum, followed by one table per run step.

```toml
sha256 = "0123456789abcdef..."

[01_init]
exe = "yambo"
input = "INPUTS/01_init"
output = "01_init"
[01_init.reference]
"o-01_init.ndb.gops" = ["SAVE/ndb.gops", "ng_in_shell", "E_of_shell"]
"o-01_init.ndb.kindx" = ["SAVE/ndb.kindx", "Qindx", "Sindx"]
"r-01_init_setup" = [""]

[02_qp]
exe = "yambo"
input = "INPUTS/02_QP"
output = "02_QP"
runlevel = "qp"
dependencies = ["01_init"]
[02_qp.reference]
"o-02_QP.qp" = { path = "02_QP/o-02_QP.qp", skip_columns = [5] }
"o-02_QP.ndb.QP" = { path = "02_QP/ndb.QP", variables = ["QP_Z"] }
"r-02_QP_gw0_dyson" = [""]
```

Required step fields:

- `exe`: executable key from the configuration registry, such as `yambo`,
  `ypp`, `yambo_ph`, `ypp_ph`, or a custom key defined under `[executables]`.
- `input`: input file passed with `-F`.
- `output`: output name used with `-J` and `-C`.
- `runlevel`: primary Yambo runlevel covered by the step, such as `init`,
  `qp`, `bse`, `optics`, `lifetimes`, `gf`, `rim_cut`, or `ypp`.
- `dependencies`: list of prerequisite step table names needed when this step
  is selected by runlevel.
- `reference`: mapping from files in `REFERENCE/` to generated outputs.

Optional step fields:

- `flags`: suffix appended to the `-J` output target after a comma.
- `nprocs`: per-step MPI rank count, overriding the global `nprocs`.
- `actions`: pre-run shell-style actions. The runner supports simple `mkdir`
  and `cp` actions directly, and attempts other commands with `subprocess`.

Reference entries can use the compact list syntax:

```toml
"o-02_QP.qp" = ["02_QP/o-02_QP.qp"]
"o-02_QP.ndb.QP" = ["02_QP/ndb.QP", "QP_Z"]
```

or the metadata table syntax:

```toml
"o-02_QP.qp" = { path = "02_QP/o-02_QP.qp", skip_columns = [5], tolerance = 0.11 }
"o-02_QP.ndb.QP" = { path = "02_QP/ndb.QP", variables = ["QP_Z"], whitelist = true }
```

Supported metadata:

- `path`: generated output path. A bare filename is resolved inside the step
  output directory; paths with directories are resolved from the workflow root.
- `variables`: NetCDF variables to compare for database references.
- `skip_columns`: 1-based text-output columns to skip. The first data column is
  column 1.
- `tolerance`: per-reference comparison tolerance. `tollerance` is also accepted
  for compatibility with the existing configuration spelling.
- `whitelist`: mark a known noisy or accepted failure as an expected failure.

## Running The New Test

Add the test to the `[tests]` table in your local `config.toml`:

```toml
[tests]
Al_bulk = ["GW-OPTICS"]
```

Then run with the tests directory and cache directory you want to use:

```bash
yambo-tester --tests src/yambo_tester/tests --cache cache
```

The runner copies the test to scratch, extracts the tarball from the cache,
executes the steps in `tests.toml`, writes `results.toml`, and validates the
generated files with pytest.

To run only a runlevel and its declared dependencies:

```bash
yambo-tester --runlevel qp
```

Steps whose `runlevel` does not match and are not dependencies are marked as
intentional skips in `results.toml`, so their references are skipped during
pytest validation.

## Executable Registry

The main configuration file now stores executables under `[executables]`
instead of top-level `[parameters]` fields. Core executables are `yambo`,
`p2y`, and `a2y`. `ypp` and project executables such as `yambo_ph` are
optional. You can override any registry entry on the command line with
`--exe KEY=VALUE`.
