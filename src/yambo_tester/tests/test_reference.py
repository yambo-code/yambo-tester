# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import pytest
import tomllib
import numpy as np
import netCDF4 as nc
from glob import glob
from pathlib import Path
from yambo_tester.selection import (
    MISSING_EXECUTABLE_RETURNCODE,
    RUNLEVEL_FILTER_RETURNCODE,
)

ZERO_DFL = 1e-6
TOO_LARGE = 10e99
SIGNIFICANCE_THRESHOLD = 1e-3
METADATA_KEYS = {"sha256"}


def normalize_reference(reference):
    """
    Return a uniform reference spec from either the legacy list syntax or
    metadata-rich TOML table syntax.
    """
    if isinstance(reference, dict):
        path = reference.get("path", "")
        variables = reference.get("variables", [])
        skip_columns = reference.get("skip_columns", [])
        if isinstance(variables, str):
            variables = [variables]
        return {
            "path": path,
            "variables": variables,
            "skip_columns": {int(col) - 1 for col in skip_columns},
            "whitelist": bool(reference.get("whitelist", False)),
            "tolerance": reference.get("tolerance", reference.get("tollerance")),
            "contains": reference.get("contains", reference.get("string")),
        }

    if isinstance(reference, list):
        path = reference[0] if reference else ""
        return {
            "path": path,
            "variables": reference[1:],
            "skip_columns": set(),
            "whitelist": False,
            "tolerance": None,
            "contains": None,
        }

    return {
        "path": reference,
        "variables": [],
        "skip_columns": set(),
        "whitelist": False,
        "tolerance": None,
        "contains": None,
    }


def significant_mask(ref_data, out_data):
    max_abs = np.max(np.abs(ref_data))
    threshold = max_abs * SIGNIFICANCE_THRESHOLD
    return (np.abs(ref_data) >= threshold) | (np.abs(out_data) >= threshold)


def assert_finite_output(data, label):
    assert np.all(abs(data) < TOO_LARGE) and not np.all(np.isnan(data)), f"{label}: NaN or too large number!"


def assert_close_significant(out_data, ref_data, tol, label):
    mask = significant_mask(ref_data, out_data)
    assert np.allclose(out_data[mask], ref_data[mask], rtol=tol, atol=ZERO_DFL), f"{label}: Difference larger than {tol}!"


def compare_text_output(out_file, ref_file, ref, tol, skip_columns):
    ref_data = np.genfromtxt(str(ref_file))
    out_data = np.genfromtxt(str(out_file))

    for col in range(1, ref_data.shape[1]):
        if col in skip_columns:
            continue
        assert_finite_output(out_data[:, col], str(out_file))
        assert_close_significant(out_data[:, col], ref_data[:, col], tol, ref)


def compare_database(out_file, ref_file, variables, ref, tol):
    ref_data = np.genfromtxt(str(ref_file))
    nvars = len(variables)
    ndata = len(ref_data) // nvars

    ds = nc.Dataset(str(out_file))
    for i in range(nvars):
        out_data = ds[variables[i]][:].ravel()
        assert_finite_output(out_data, str(out_file))

        start, stop = i * ndata, i * ndata + ndata
        expected = ref_data[start:stop]
        actual = out_data[:len(expected)]
        assert_close_significant(actual, expected, tol, ref)


def resolve_output_file(rundir, odir, ref, path):
    if ref == "STDOUT":
        return rundir.joinpath(path)

    if ref[:2] == 'r-':
        if path:
            return rundir.joinpath(path)
        tmp = glob(str(rundir.joinpath(odir)) + '/r-*')
        if tmp:
            return Path(tmp[0])
        return rundir.joinpath(odir, ref)

    if path:
        out_path = Path(path)
        if len(out_path.parts) == 1:
            return rundir.joinpath(odir, out_path)
        return rundir.joinpath(out_path)

    return rundir.joinpath(odir, ref)


def string_check_spec(ref, ref_spec, result):
    if ref == "STDOUT":
        return {
            "path": result.get("stdout_file", ""),
            "contains": ref_spec["contains"] or ref_spec["path"],
        }

    if ref[:2] == "r-" and ref_spec["contains"] is None and ref_spec["path"]:
        return {
            "path": "",
            "contains": ref_spec["path"],
        }

    return {
        "path": ref_spec["path"],
        "contains": ref_spec["contains"],
    }


def assert_file_contains(path, expected, label):
    if not expected:
        return
    text = path.read_text(errors="replace")
    assert expected in text, f"{label}: expected string not found: {expected}"


def assert_stdout_or_log_contains(stdout_text, run_dir, exe, expected, label):
    if not expected:
        return

    stdout_text = stdout_text or ""
    candidates = [stdout_text]
    log_file = Path(run_dir).joinpath(f"l_{exe}")
    if log_file.exists():
        candidates.append(log_file.read_text(errors="replace"))

    if any(expected in text for text in candidates):
        return

    log_label = log_file.name if log_file.exists() else "log file"
    raise AssertionError(f"{label}: expected string not found in stdout or {log_label}: {expected}")


def pytest_generate_tests(metafunc):
    """
    Generates sequences usefull to be parsed by pytest test functions.
    """
    needs_rundir = {"run_item", "ref_item"} & set(metafunc.fixturenames)
    rundir_option = metafunc.config.getoption("rundir", default=None)
    if needs_rundir and rundir_option is None:
        for fixture_name in needs_rundir:
            metafunc.parametrize(
                fixture_name,
                [pytest.param(None, marks=pytest.mark.skip(reason="requires --rundir"))],
            )
        return

    rundir = Path(rundir_option)
    with open(rundir / "results.toml", 'rb') as f:
        results = tomllib.load(f)
    tollerance = results.pop('tollerance', None)
    with open(rundir / "tests.toml", 'rb') as f:
        tests = tomllib.load(f)
    sha256 = tests.pop('sha256', None)

    # Sequence for test_runs_ok func
    if "run_item" in metafunc.fixturenames:
        items = list(results.items())
        metafunc.parametrize(
            "run_item",
            items,
            ids=[name for name, info in items]
        )

    # Sequence for test_reference_ok func
    if "ref_item" in metafunc.fixturenames:
        items = []
        for key, val in tests.items():
            if key in METADATA_KEYS:
                continue
            skip = results[key]['returncode'] in {
                MISSING_EXECUTABLE_RETURNCODE,
                RUNLEVEL_FILTER_RETURNCODE,
            }
            for r, o in val['reference'].items():
                ref_spec = normalize_reference(o)
                string_spec = string_check_spec(r, ref_spec, results[key])
                items.append((r,{'out': o,
                                 'path': string_spec["path"],
                                 'variables': ref_spec["variables"],
                                 'skip_columns': ref_spec["skip_columns"],
                                 'whitelist': ref_spec["whitelist"],
                                 'exe': val["exe"],
                                 'dir': str(rundir),
                                 'run_dir': results[key]["run_dir"],
                                 'stdout': results[key].get("stdout", ""),
                                 'tol': ref_spec["tolerance"] or tollerance,
                                 'odir': val.get('output', ''),
                                 'contains': string_spec["contains"],
                                 'skip': skip,
                                 }))
        metafunc.parametrize(
            "ref_item",
            items,
            ids=[ref for ref, info in items]
        )


def test_runs_ok(run_item):
    """
    Checks if the returncode of the run is 0.
    """
    name, info = run_item
    if info["returncode"] == MISSING_EXECUTABLE_RETURNCODE:
        pytest.skip("Test skipped due to missing executable")
    elif info["returncode"] == RUNLEVEL_FILTER_RETURNCODE:
        pytest.skip("Test skipped by runlevel selection")
    else:
        assert info["returncode"] == 0, f"Subtest {name} failed: {info['stderr']}"

    
def test_reference_ok(ref_item):
    """
    Checks if the values in the output files are 
    """
    ref, info = ref_item
    if info['skip']:
        pytest.skip("Test skipped before reference validation")
    else:
        rundir = Path(info['dir'])
        tol = float(info['tol'])
        ref_file = rundir.joinpath('REFERENCE', ref)
        out_file = resolve_output_file(rundir, info['odir'], ref, info['path'])
    
        # Check if reference and output files exist
        if ref != "STDOUT" and not ref[:2] == 'r-': assert ref_file.exists(), f"{ref} file do not exists!"
        assert out_file.exists(), f"{info['out']} file do not exists!"

        if ref == "STDOUT":
            assert_stdout_or_log_contains(
                info['stdout'],
                info['run_dir'],
                info['exe'],
                info['contains'],
                ref,
            )

        # Check text output files
        if ref[:2] == 'o-' and not '.ndb' in ref:
            try:
                compare_text_output(out_file, ref_file, ref, tol, info['skip_columns'])
            except AssertionError as e:
                if info['whitelist']:
                    pytest.xfail(str(e))
                raise
    
        # Check output DBs
        if '.ndb' in ref:
            try:
                compare_database(out_file, ref_file, info['variables'], ref, tol)
            except AssertionError as e:
                if info['whitelist']:
                    pytest.xfail(str(e))
                raise
    
        # Check report files
        if ref[:2] == 'r-':
            report = False
            with open(str(out_file), 'rb') as f:
                for line in f:
                    if b"Game Over & Game summary" in line: report = True
            assert report, f"{ref}: report file incomplete!"
            assert_file_contains(out_file, info['contains'], ref)
