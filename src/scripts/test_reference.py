# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import argparse
import numpy as np
import netCDF4 as nc
from glob import glob
from pathlib import Path


def test_reference_ok(out, ref, var, rundir, tol):
    """
    Checks if the values in the output files are close to the ones in reference files
    """
    _rundir = Path(rundir).resolve()

    #if 'REFERENCE' in str(ref):
    ref_file = _rundir.joinpath(ref)
    #else:
    #    ref_file = _rundir.joinpath('REFERENCE', str(ref))
    out_file = _rundir.joinpath(out)

    out_name = out_file.name
    out_type = None
    if out_name[:2] == 'r-': out_type = 'report'
    if out_name[:2] == 'o-': out_type = 'output'
    if 'ndb.' in out_name: out_type = 'database'

    assert out_type, f"{out}: file type not recognized."

    # Check if reference and output files exist
    if out_type != 'report': assert ref_file.exists(), f"{ref_file} file do not exists!"
    assert out_file.exists(), f"{out_file} file do not exists!"
    #print("LOG: both files exists")
    
    zero_dfl = 1e-6
    too_large = 10e99
    
    # Check text output files
    if out_type == 'output':
        # Read reference and output files
        ref_data = np.genfromtxt(str(ref_file))
        out_data = np.genfromtxt(str(out_file))

        assert np.all(abs(out_data[:])<too_large) and not np.all(np.isnan(out_data[:])), f"{out_file.name}: NaN or too large number!"
        print("LOG: not NaN or too large numbers in output file")
        # Compare data column by column
        for col in range(0,ref_data.shape[1]):
            max_abs = np.max(np.abs(ref_data[:,col]))
            threshold = max_abs * 1e-3
            mask = (np.abs(ref_data[:,col]) >= threshold) | (np.abs(out_data[:,col]) >= threshold)
            print('len:', len(ref_data[:,col]), 'thr:', threshold, 'max_abs:', max_abs)
            
            try:
                assert np.allclose(out_data[:,col][mask], ref_data[:,col][mask], rtol=tol, atol=zero_dfl), f"{out_file.name}: Difference larger than {tol} in column {col}!"
                print(f"LOG: no difference larger than {tol} in column {col}!")
            except AssertionError as e:
                print(np.isclose(out_data[:,col][mask], ref_data[:,col][mask], rtol=tol, atol=zero_dfl))
                print(ref_data[:,col][mask])
                print(out_data[:,col][mask])
                print(f"ERROR: {e}")
    
    # Check output DBs
    if out_type == 'database':
        # Read reference file
        ref_data = np.genfromtxt(str(ref_file))
        variables = var.split(',')
        nvars = len(variables)
        ndata = len(ref_data) // nvars

        # Read DB
        ds = nc.Dataset(str(out_file))
        for i in range(nvars):
            start, stop = i*ndata, i*ndata+ndata
            # Extract data
            out_data = ds[variables[i]]
            out_data = out_data[:].ravel()
            max_abs = np.max(np.abs(ref_data[start:stop]))
            threshold = max_abs * 1e-3
            mask = (np.abs(ref_data[start:stop]) >= threshold) | (np.abs(out_data[:len(ref_data[start:stop])]) >= threshold)

            assert np.all(abs(out_data)<too_large) and not np.all(np.isnan(out_data)), f"{out_file.name}: NaN or too large number!"
            print("LOG: not NaN or too large numbers in output file")
            
            try:
                assert np.allclose(out_data[:len(ref_data[start:stop])][mask], ref_data[start:stop][mask], rtol=tol, atol=zero_dfl), f"{out_file.name}: Difference larger than {tol}!"
                print(f"LOG: no difference larger than {tol}!")
            except AssertionError as e:
                print(np.isclose(out_data[:len(ref_data[start:stop])][mask], ref_data[start:stop][mask], rtol=tol, atol=zero_dfl))
                print(ref_data[start:stop][mask])
                print(out_data[:len(ref_data[start:stop])][mask])
                print(f"ERROR: {e}")
    
    # Check report files
    if out_type == 'report':
        report = False
        with open(str(out_file), 'rb') as f:
            for line in f:
                if b"Game Over & Game summary" in line: report = True
        assert report, f"{out_file.name}: report file incomplete!"
        print("LOG: 'Game Over & Game summary' found in report file")


def main():
    parser = argparse.ArgumentParser(prog='tester',
                                     description='A python script to test an output file of Yambo',
                                     epilog="Copyright (c) 2025 Nicola Spallanzani")
    parser.add_argument('-o', '--output',
                        help='Yambo output file or database', type=str, dest='out', required=True)
    parser.add_argument('-r', '--reference',
                        help='Reference file', type=str, dest='ref')
    parser.add_argument('-v', '--variables',
                        help='List of variables to check if the output is a database (separate them with a comma)', type=str, dest='var')
    parser.add_argument('-d', '--rundir',
                        help='Directory of the run [default "./"]', type=str, dest='rundir', default="./")
    parser.add_argument('-t', '--tollerance',
                        help='Tollerance (between 0 - 100%%) [default: 0.1]', type=float, dest='tol', default=0.1)
    args = parser.parse_args()
    
    test_reference_ok(args.out, args.ref, args.var, args.rundir, args.tol)

        
if __name__ == '__main__':
    main()
