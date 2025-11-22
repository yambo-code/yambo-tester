# yambo-tester

**A Python-based testing framework for validating Yambo simulations using the official Yambo test suite.**

---

## Overview

**yambo-tester** is a Python program designed to automate and simplify the validation of the open-source **Yambo** code for Many-Body Perturbation Theory and excited-state calculations.
Yambo is available on its official website: <https://www.yambo-code.eu/> and its source code can be found on GitHub: <https://github.com/yambo-code/yambo>.

The current version of yambo-tester relies on a curated subset of tests taken directly from the official Yambo test suite, available at
<https://github.com/yambo-code/yambo-tests>. Additional tests will be gradually integrated over time to provide broader coverage.

Users can execute **all available tests** or select a **specific subset**, making yambo-tester particularly suitable for **automated CI workflows** where fast, selective validation is required. Depending on how Yambo has been compiled on the system, tests can run in **serial** or **parallel** using OpenMP and MPI.

---

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

Note: yambo-tester is not yet published on PyPI, but it will become available once the first release is finalized.

---

## Usage

(*A full usage guide will be added soon. Placeholder section.*)

---

## Authors and Acknowledgments

**Nicola Spallanzani** is the main developer and current maintainer of yambo-tester.

Special acknowledgments:

- **Claudio Attaccalite**, whose earlier scripts inspired part of the initial design.
- The **Yambo developer team**, who maintain the official Yambo test suite from which many tests included in this project are derived.

---

## Contributing

Contributions are welcome!
Please refer to the guidelines in **CONTRIBUTING.md** before submitting pull requests.

---

## License

yambo-tester is distributed under the **MIT License**.
For details, see the **LICENSE** file included in this repository.

---

## TODO

The following features and improvements are planned for future releases of yambo-tester:

- [ ] Integration of additional tests from the official Yambo test suite and other validated sources, expanding the coverage of physical scenarios and computational workflows.
- [ ] Support for auxiliary executables such as p2y, a2y, and c2y, enabling full preparation and conversion workflows prior to Yambo runs.
- [ ] Support for project-specific executables (e.g., yambo_rt, ypp_rt, etc.).
- [ ] Publishing the package on PyPI, allowing installation via pip install yambo-tester and integration into CI pipelines without local cloning.
- [ ] Generation of a final test report suitable for upload to a web portal or dashboard, enabling remote monitoring of test outcomes.

---
