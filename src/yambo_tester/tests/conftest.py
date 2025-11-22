# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import pytest
from pathlib import Path
import yaml


def pytest_addoption(parser):
    parser.addoption(
        "--rundir",
        action="store",
        help="Directory where yambo-tester stored the results.yaml",
    )


@pytest.fixture
def rundir(request):
    """Return the path of the run directory passed by --rundir."""
    value = request.config.getoption("--rundir")
    if value is None:
        pytest.fail("Missing required option --rundir")
    return Path(value)


@pytest.fixture
def results(rundir):
    """Load and return the results.yaml content."""
    results_file = rundir / "results.yaml"

    if not results_file.exists():
        pytest.fail(f"Missing results.yaml in {rundir}")

    with open(results_file) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        pytest.fail("results.yaml must contain a mapping of run_name → info")

    return data
