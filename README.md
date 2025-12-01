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

### Parameter Hierarchy

When a parameter is not explicitly provided, **yambo-tester** resolves it using the following hierarchical system:

1. **Command-line arguments** (highest priority)
2. **User’s local `config.toml` file**
3. **Package-provided `config.toml`**
4. **Internal default values** (lowest priority)

In typical usage, the user should set parameters either on the command line or in a local configuration file.

### Executable Discovery

- If the parameter `yambo_bin` is not defined, Yambo executables are searched in the system `PATH`.
- If the program cannot find the **core executables**, execution stops with an error.
- If **project executables** (e.g., `yambo_rt`, `ypp_rt`, etc.) are missing, the corresponding tests are simply skipped.

### Scratch and Cache Directories

If the `scratch` and `cache` directories specified in the configuration do **not** already exist, they will be **automatically created** by `yambo-tester`.

### Documentation

A detailed documentation — including usage examples, launch configurations, and a tutorial on how to add new tests — will be available soon.

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
- [ ] Support for auxiliary executables such as p2y, a2y, and c2y, enabling full preparation and conversion workflows prior to Yambo runs.
- [x] Support for project-specific executables (e.g., yambo_rt, ypp_rt, etc.).
- [ ] Publishing the package on PyPI, allowing installation via pip install yambo-tester and integration into CI pipelines without local cloning.
- [x] Generation of a final test report suitable for upload to a web portal or dashboard, enabling remote monitoring of test outcomes.
- [ ] Parallel execution of tests using the `concurrent.futures.ProcessPoolExecutor` module
- [ ] Definition of keys in tests.toml files for specific selections of tests types
