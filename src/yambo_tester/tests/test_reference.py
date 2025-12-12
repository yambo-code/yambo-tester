# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import pytest
import tomllib
import numpy as np
import netCDF4 as nc
from glob import glob
from pathlib import Path


def pytest_generate_tests(metafunc):
    """
    Generates sequences usefull to be parsed by pytest test functions.
    """
    rundir = Path(metafunc.config.getoption("--rundir"))
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
            skip = True if results[key]['returncode']==-9999 else False
            for r, o in val['reference'].items():
                items.append((r,{'out': o,
                                 'dir': str(rundir),
                                 'tol': tollerance,
                                 'odir': str(rundir.joinpath(val['output'])),
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
    if info["returncode"] == -9999:
        pytest.skip("Test skipped due to missing executable")
    else:
        assert info["returncode"] == 0, f"Subtest {name} failed: {info['stderr']}"

    
def test_reference_ok(ref_item):
    """
    Checks if the values in the output files are 
    """
    ref, info = ref_item
    if info['skip']:
        pytest.skip("Test skipped due to missing executable")
    else:
        rundir = Path(info['dir'])
        tol = float(info['tol'])
        ref_file = rundir.joinpath('REFERENCE', ref)
        if isinstance(info['out'], list):
            out_file = rundir.joinpath(info['out'][0])
        elif ref[:2] == 'r-':
            tmp = glob(str(rundir.joinpath(info['odir'])) + '/r-*')
            if tmp:
                out_file = Path(tmp[0])
            else:
                out_file = rundir.joinpath(info['odir'], ref)
        else:
            out_file = rundir.joinpath(info['odir'], info['out'])
    
        # Check if reference and output files exist
        if not ref[:2] == 'r-': assert ref_file.exists(), f"{ref} file do not exists!"
        assert out_file.exists(), f"{info['out']} file do not exists!"
    
        zero_dfl = 1e-5
        too_large = 10e99
    
        # Check text output files
        if ref[:2] == 'o-' and not '.ndb' in ref:
            # Read reference and output files
            ref_data = np.genfromtxt(str(ref_file))
            out_data = np.genfromtxt(str(out_file))
            #ref_data[np.abs(ref_data) < zero_dfl] = 0.0
            #out_data[np.abs(out_data) < zero_dfl] = 0.0

            # Compare data column by column
            for col in range(1,ref_data.shape[1]):
                assert np.all(abs(out_data[:,col])<too_large) and not np.all(np.isnan(out_data[:,col])), f"{info['out']}: NaN or too large number!"
                assert np.allclose(out_data[:,col], ref_data[:,col], rtol=tol, atol=zero_dfl), f"{ref}: Difference larger than {tol}!"
    
        # Check output DBs
        if '.ndb' in ref:
            # Read reference file
            ref_data = np.genfromtxt(str(ref_file))
            variables = info['out'][1:]
            nvars = len(variables)
            ndata = len(ref_data) // nvars
            #ref_data[np.abs(ref_data) < zero_dfl] = 0.0

            # Read DB
            ds = nc.Dataset(str(out_file))
            for i in range(nvars):
                # Extract data
                out_data = ds[variables[i]]
                #out_data[np.abs(out_data) < zero_dfl] = 0.0
                assert np.all(abs(out_data[:])<too_large) and not np.all(np.isnan(out_data[:])), f"{info['out']}: NaN or too large number!"
                
                # Renormalize data to have 1 as maximum
                start, stop = i*ndata, i*ndata+ndata
                assert np.allclose(out_data[:].ravel()[:len(ref_data[start:stop])], ref_data[start:stop], rtol=tol, atol=zero_dfl), f"{ref}: Difference larger than {tol}!"
    
        # Check report files
        if ref[:2] == 'r-':
            report = False
            with open(str(out_file), 'rb') as f:
                for line in f:
                    if b"Game Over & Game summary" in line: report = True
            assert report, f"{ref}: report file incomplete!"
