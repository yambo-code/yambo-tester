# yambo-tester

**A Python-based testing framework for validating Yambo simulations using the official Yambo test suite.**

## Overview

**yambo-tester** is a Python program designed to automate and simplify the validation of the open-source **Yambo** code for Many-Body Perturbation Theory and excited-state calculations.
Yambo is available on its official website: <https://www.yambo-code.eu/> and its source code can be found on GitHub: <https://github.com/yambo-code/yambo>.

The current version of yambo-tester relies on a curated subset of tests taken directly from the official Yambo test suite, available at
<https://github.com/yambo-code/yambo-tests>. Additional tests will be gradually integrated over time to provide broader coverage.

Users can execute **all available tests** or select a **specific subset**, making yambo-tester particularly suitable for **automated CI workflows** where fast, selective validation is required. Depending on how Yambo has been compiled on the system, tests can run in **serial** or **parallel** using OpenMP and MPI.

## Installation

yambo-tester can be obtained by cloning the official repository:

```bash
git clone https://github.com/yambo-code/yambo-tester.git
cd yambo-tester
```

It is strongly recommended to install the package inside a dedicated Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

The package can then be installed using:

```bash
pip install -e .
```

In case of issues with the installation of the netcdf4 module, it is recommended to follow this procedure: after creating the virtual environment, install the netcdf4 module with the following command, then install yambo-tester:

```
pip install --only-binary=:all: netCDF4
```

Note: yambo-tester is not yet published on PyPI, but it will become available once the first release is finalized.

## Usage

The simplest way to run **yambo-tester** is:

```bash
yambo-tester
```

This command uses all default parameters and automatically runs all currently available tests.

A complete list of command-line arguments can be displayed with:

```bash
yambo-tester -h
```

You can generate a template configuration file (`config.toml`) using:

```bash
yambo-tester -i
```

To run only workflow steps for one or more Yambo runlevels, use the repeatable
`--runlevel` option:

```bash
yambo-tester --runlevel qp
yambo-tester --runlevel qp --runlevel bse
```

When a runlevel is selected, `yambo-tester` also runs the dependency steps
declared in each workflow's `tests.toml` and intentionally skips unrelated
steps during validation. The same selection can be configured with
`runlevels = ["qp", "bse"]` under `[parameters]` in `config.toml`.

Conversion steps use dedicated runlevels, so use `--runlevel p2y` for
Quantum ESPRESSO conversion steps and `--runlevel a2y` for ABINIT conversion
steps.

Executable names are configured under `[executables]` in `config.toml`. The
same values can be overridden on the command line with repeated
`--exe KEY=VALUE` arguments, for example:

```bash
yambo-tester --exe yambo=/opt/yambo/bin/yambo --exe custom_tool=/opt/tools/custom_tool
```

### Yambo Version Selection

By default, `yambo-tester` detects the installed Yambo major version from
`yambo -h` and falls back to Yambo 6 metadata when detection is unavailable.
The resolved major version selects version-specific workflow metadata in each
`tests.toml`, including whether the workflow is supported and which
test-database repository contains its tarball.

You can override detection with `--yambo-version` or `-y`:

```bash
yambo-tester --yambo-version 6
yambo-tester -y 5
```

Tarball URLs are resolved in this order: `--download_link`, then
`download_link` in `config.toml`, then the workflow metadata from `tests.toml`
after applying any `[versions."<major>"]` overlay. Workflows that declare no
support for the selected major version are skipped cleanly.
Imported workflows keep version-specific fixtures under `INPUTS/Y5`,
`INPUTS/Y6`, `REFERENCE/Y5`, and `REFERENCE/Y6`. Reference keys in
`tests.toml` should be explicit paths such as `REFERENCE/Y6/o-example.qp`;
legacy bare reference keys still resolve through `REFERENCE/<key>` for
compatibility.

When testing a build
outside `PATH`, combine version detection or override with `--bin`:

```bash
yambo-tester --bin /home/nicola/src/yambo-6.0/bin
```

### Development-branch variants

Some Yambo development branches read a different input dialect than the
released major version. For example, the `negf`/engine refactor turns on the
self-energy with the `HF_lXC`, `gw` and `dyson` runlevels instead of
`self_energy` plus `SEApprox`. Select the dialect by name with `--variant`, or
with `yambo_variant` in `[parameters]`:

```bash
yambo-tester --bin ~/codes/6.0-develop/bin --variant negf
```

The variant is never guessed from the binary, because revision numbers and
hashes are not ordered across branches. Its effects are:

- the runlevel rules in `src/yambo_tester/data/variants.toml` rewrite the
  scratch copy of every yambo input, so the same `INPUTS/Y6` files serve both
  dialects;
- in `tests.toml`, a `[versions."<major>-<variant>"]` overlay (e.g.
  `versions."6-negf"`) is applied after `[versions."<major>"]`, at workflow
  and step level. Use it only where the results really differ, e.g. a
  `reference` table pointing to `REFERENCE/Y6-negf/...`;
- `results.toml` records `yambo_variant` and `yambo_build` (the
  `Revision Hash` line of `yambo -h`), so every run says which build it tested.

An unknown variant, or one that belongs to another major version, stops the
run before any test starts. To add a dialect, add a table to
`variants.toml`: `major`, then one `[<name>.runlevels.<runlevel>]` table per
runlevel line to replace. Each such table holds the selector variable `by`,
the runlevel lists per selector value, `default`, and `drop`.

### Parameter Hierarchy

When a parameter is not explicitly provided, **yambo-tester** resolves it using the following hierarchical system:

1. **Command-line arguments** (highest priority)
2. **User’s local `config.toml` file**
3. **Package-provided `config.toml`**
4. **Internal default values** (lowest priority)

In typical usage, the user should set parameters either on the command line or in a local configuration file.

### Executable Discovery

- Core executables are `yambo`, `p2y`, and `a2y`. If any of them cannot be found, execution stops with an error.
- `ypp` and the project executables such as `yambo_rt`, `ypp_rt`, `yambo_ph`, and `ypp_ph` are optional. They are only checked if you register them under `[executables]` or with `--exe KEY=VALUE`; otherwise, the corresponding workflow steps are skipped.
- If `yambo_bin` is set, executable lookup starts there; otherwise, executables are searched in the system `PATH`.
- Additional executables can be registered under `[executables]` or with `--exe KEY=VALUE`.
- To inspect the packaged workflow keyword inventory without running tests, use `yambo-tester --list-executables` or `yambo-tester --list-runlevels`.
- The listed values come from `src/yambo_tester/data/workflow_keywords.toml`, which is kept in sync with the imported `tests.toml` files.

### Scratch and Cache Directories

If the `scratch` and `cache` directories specified in the configuration do **not** already exist, they will be **automatically created** by `yambo-tester`.

### Benchmark mode (SLURM)

A workflow becomes a strong-scaling benchmark when its `tests.toml` has a `[benchmark]` table. Write the parallel strategy once. Names of variables are intentionally general to keep them version-neutral. The names are `dip`, `chi`, `fock` and `gw`, and each block maps roles to formulas:

```toml
[benchmark]
nodes = [1, 2, 4, 8, 16]   # scaling points (a site can override them in [cluster])
[benchmark.vars]           # helper values, evaluated in order
sxp = "16 if ntasks>320 else 8 if ntasks>160 else 4 if ntasks>80 else 2 if ntasks>40 else 1"
[benchmark.parallel]       # generic block -> role -> formula
dip  = { k = "1", c = "ntasks", v = "1" }
chi  = { q = "1", g = "1", k = "1", c = "ntasks", v = "1" }
fock = { q = "sxp", b = "ntasks // sxp" }
gw   = { q = "1", qp = "1", b = "ntasks" }
[benchmark.names."6"]      # optional: override the packaged name map for one major version
chi = "EM1D"
```

How the strategy is applied:

- **Formulas.** A formula can use `ntasks`, `nodes`, `threads` and the earlier `vars`. Only numbers, `+ - * //`, comparisons, `if/else` and parentheses are allowed; anything else is rejected. In each block, the CPU counts must multiply to `ntasks`.
- **Name map.** `src/yambo_tester/data/parallel_names.toml` maps the generic blocks to the `<NAME>_CPU` / `<NAME>_ROLEs` variables:
  - Yambo 5: `DIP`, `X_and_IO`, `SX`, `SE`;
  - Yambo 6: `DIP`, `PPA`, `HFlXC`, `GW`.
- **Patching.** When a run gets `--nodes N`, the runner rewrites these lines in the scratch copy of every `yambo*` step input, or appends them if they are missing. The inputs in the workflow directory stay plain Yambo inputs. Steps that set their own `nprocs` are not supported in benchmark mode.

Everything machine-specific is in the `[cluster]` table of their own `config.toml`; yambo-tester hard-codes none of it.

- **SLURM settings:** `partition`, `account` and `qos`; an empty value drops the line.
- **Walltime:** `time`.
- **Environment:** `modules`, a list. `setup`, a list of raw shell lines run before the command, e.g. `source ~/env.sh` where `module` is unavailable in batch shells, or `export OMP_PROC_BIND=close`.
- **Launcher:** `mpi`, which can be a wrapper script, e.g. one that adds `--map-by` options. Empty means `[parameters].mpi_launcher`.
- **Node shape:** `tasks_per_node` and `threads`, required unless the workflow sets them. Optional `nodes` overrides the workflow's scaling points, e.g. fewer runs on a busy cluster.
- **Template:** `template`, the path of your own sbatch template. The default is the neutral `src/yambo_tester/data/slurm_job.sh`, with placeholders `{nodes} {ntasks_per_node} {threads} {partition} {account} {qos} {time} {modules} {cmd}`.

The workflow's `[benchmark]` holds only what belongs to the physics test: the formulas and default node counts.

```toml
[cluster]                      # example site section (values are per machine)
partition = "batch"
account = "my-project"
qos = "normal"
time = "10:00:00"
setup = ["source ~/my_env.sh"]
mpi = "/path/to/mpirun_wrapper.sh"
tasks_per_node = 8
threads = 16
```

```bash
yambo-tester --submit --dry-run   # write <scratch>/benchmark/<name>_<type>/nodes_NNN/{config.toml,job.sh} and print the jobs
yambo-tester --submit             # same, then sbatch each job.sh
yambo-tester --collect scratch/benchmark/<name>_<type>   # result.dat (MaX columns) + speedup/efficiency table
```

Each job runs `yambo-tester --nodes N --np <ntasks> --thrs <threads> --mpi <cluster.mpi>` on a job-local `config.toml` that selects only that workflow. The usual pytest reference checks therefore run inside every job.

**SAVE sharing.** For a workflow with `[benchmark]`, the tarball is extracted only once, into `<cache>/extracted/<tarball name>/`. Each job's run tree gets a symlink to that `SAVE` instead of a copy; any other files in the tarball are copied as usual. The shared `SAVE` is made read-only, so if a step tries to write into it, Yambo fails with an error instead of silently changing the databases for every job.
- Steps write through `-J`/`-C` (`output = "..."`).
- Later steps read earlier databases with `flags`. For example, `flags = "01_init"` gives `-J 02_gw,01_init`.

To refresh after the tarball changes, run `chmod -R u+w <cache>/extracted/<tarball name>`, then delete that directory.

`--collect` reads every `r-*` report (it skips those copied from `REFERENCE/`) and writes `result.dat`, all times in seconds. The columns are `Nodes;Tasks;Threads/Task;Time-Profile;Dipoles;Xo;X;Self Energy;Other`.

- Report labels for Yambo 5 and Yambo 6 live in `src/yambo_tester/data/benchmark_timers.toml`. For example, Y5 `HF + GW(ppa)` and Y6 `Fock + Plasmon-Pole` both feed `Self Energy`.
- If a column finds none of its labels in a report, `--collect` prints a `WARNING`; it does not write a silent 0. Add the new label to that file when Yambo 6 renames a timer.
- `Other` is the Time-Profile minus all the other columns.

### Documentation

- [Adding new tests](ADDING_TESTS.md): how to organize input and reference files, prepare the SAVE tarball, place it in the cache, and write `tests.toml`.

Workflow steps may also use packaged reusable metadata templates with
`step_type`. A compact step such as:

```toml
[02_HF]
step_type = "HF"
```

is expanded in the scratch copy of `tests.toml` before execution. Local fields
in the workflow file override template defaults, so per-workflow values such as
`input_dir`, `nprocs`, references, and version overlays still belong in the
local `tests.toml`. Reusable templates are packaged in
`src/yambo_tester/data/workflow_templates.toml`; current DFT templates include `p2y`, `init`, `HF`, and `a2y`.

When preparing NetCDF database references for new tests, use the installed
`tester-dump` helper to dump selected variables to minimal numeric text files:

```bash
tester-dump -i file.nc -v var1 -v var2 -o reference.txt --max-values 250
```

The helper writes variables in the requested order and limits each variable to
the first 100 flattened values by default. Use `--max-values` to choose a
different per-variable limit. See [Adding new tests](ADDING_TESTS.md) for the
full reference-preparation workflow.

For quick numeric checks, use the installed `tester` helper. It can compare a
text reference with either a text output file or selected variables from a
NetCDF output file:

```bash
tester -r reference.txt -o output.txt
tester -r reference.txt -o output.txt --ref-col 2 --out-col 3
tester -r reference.txt -o sample.nc -v EIGENVALUES
tester -r reference.txt -o sample.nc --variables ng_in_shell,E_of_shell
```

Column numbers are 1-based and default to the first column when omitted. For
NetCDF outputs, specify one or more variables with `-v`, `--variable`, or
`--variables`; repeat the option or use comma-separated names for multiple
variables. Variables are read in the requested order, multidimensional arrays
are flattened, and each variable is compared against the corresponding text
reference slice. The helper uses the same tolerance and significant-value
comparison rules as the main workflow reference validator.

Failed numerical comparisons report the total number of mismatching elements
and show bounded element-level details. Element indices are zero-based flat
indices; text comparisons also report zero-based row indices and the selected
1-based column, while NetCDF comparisons report the variable name and the
multidimensional index when the original variable shape is available. By
default the first 20 mismatches are printed; the total mismatch count is always
reported. Use `tester --max-mismatches N` to change the CLI detail limit.
Tolerance is applied only to significant values with NumPy close semantics
using the configured relative tolerance and an absolute tolerance of `1e-6`.

## Authors and Acknowledgments

**Nicola Spallanzani** is the main developer and current maintainer of yambo-tester.

Special acknowledgments:

- **Claudio Attaccalite**, whose earlier scripts inspired part of the initial design.
- The **Yambo developer team**, who maintain the official Yambo test suite from which many tests included in this project are derived.

## Contributing

Contributions are welcome!
Please refer to the guidelines in **CONTRIBUTING.md** before submitting pull requests.

## License

yambo-tester is distributed under the **MIT License**.
For details, see the **LICENSE** file included in this repository.

## TODO

The following features and improvements are planned for future releases of yambo-tester:

- [ ] Integration of additional tests from the official Yambo test suite and other validated sources, expanding the coverage of physical scenarios and computational workflows.
- [x] Support for auxiliary executables such as p2y and a2y, enabling full preparation and conversion workflows prior to Yambo runs.
- [x] Support for project-specific executables (e.g., yambo_rt, ypp_rt, etc.).
- [ ] Publishing the package on PyPI, allowing installation via pip install yambo-tester and integration into CI pipelines without local cloning.
- [x] Generation of a final test report suitable for upload to a web portal or dashboard, enabling remote monitoring of test outcomes.
- [ ] Parallel execution of tests using the `concurrent.futures.ProcessPoolExecutor` module
- [x] Definition of keys in tests.toml files for specific selections of tests types
- [x] Add support for different Yambo versions
- [x] Add support for internal definition of OMP_NUM_THREADS variable
