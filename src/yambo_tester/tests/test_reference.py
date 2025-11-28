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
    with open(rundir / "tests.toml", 'rb') as f:
        tests = tomllib.load(f)
    tollerance = results.pop('tollerance', None)

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
            for r, o in val['reference'].items():
                items.append((r,{'out': o,
                                 'dir': str(rundir),
                                 'tol': tollerance,
                                 'odir': str(rundir.joinpath(val['output'])),
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
    assert info["returncode"] == 0, f"Subtest {name} failed: {info['stderr']}"

    
def test_reference_ok(ref_item):
    """
    Checks if the values in the output files are 
    """
    ref, info = ref_item
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
    assert ref_file.exists(), f"{ref} file do not exists!"
    assert out_file.exists(), f"{info['out']} file do not exists!"

    zero_dfl = 1e-6
    too_large = 10e99

    # Check text output files
    if ref[:2] == 'o-' and '.ndb' not in ref:
        # Read reference and output files
        ref_data = np.genfromtxt(str(ref_file))
        out_data = np.genfromtxt(str(out_file))
        
        # Renormalize data to have 1 as maximum
        maxval=np.amax(ref_data[:,1:])
        if maxval == 0.0: maxval = 1.0
        
        # Compare data column by column
        for col in range(1,ref_data.shape[1]):
            assert np.any(abs(out_data[:,col])<too_large) and not np.any(np.isnan(out_data[:,col])), f"{info['out']}: NaN or too large number!"
            
            diff = abs(ref_data[:,col]-out_data[:,col]) / maxval
            for row in range(ref_data.shape[0]):
                if abs(ref_data[row,col] / maxval) > zero_dfl:
                    diff[row] = diff[row] / (ref_data[row,col] / maxval)
            
            assert np.any(diff<tol), f"{ref}: Difference larger than {tol}!"

    # Check output DBs
    if '.ndb' in ref:
        # Read reference and output files
        ref_data = np.genfromtxt(str(ref_file))
        variables = info['out'][1:]
        #if info['out'] == 'SAVE/ndb.gops': variables = ['ng_in_shell', 'E_of_shell']
        #if info['out'] == 'SAVE/ndb.kindx': variables = ['Qindx', 'Sindx']
        nvars = len(variables)
        ndata = len(ref_data) // nvars
        # Read DB
        ds = nc.Dataset(str(out_file))
        for i in range(nvars):
            # Extract data
            out_data = ds[variables[i]]
            assert np.any(abs(out_data[:])<too_large) and not np.any(np.isnan(out_data[:])), f"{info['out']}: NaN or too large number!"
            
            # Renormalize data to have 1 as maximum
            start, stop = i*ndata, i*ndata+ndata
            maxval=np.amax(ref_data[start:stop])
            if maxval == 0.0: maxval = 1.0

            diff = abs(ref_data[start:stop]-out_data[:].ravel()) / maxval
            for row in range(ndata):
                if abs(ref_data[start+row] / maxval) > zero_dfl:
                    diff[row] = diff[row] / (ref_data[start+row] / maxval)

            assert np.any(diff<tol), f"{ref}: Difference larger than {tol}!" 

    # Check report files
    if ref[:2] == 'r-':
        report = False
        with open(str(out_file)) as f:
            for line in f:
                if "Game Over & Game summary" in line: report = True
        assert report, f"{ref}: report file incomplete!"
