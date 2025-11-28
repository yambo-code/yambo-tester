# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import argparse
from pathlib import Path
import importlib.resources
from .log import setup_logging
from .download import download_test
from .config import load_config, check_parameters
from .runner import setup_rundir, run_test, run_pytest


def set_cl_args(config):
    """
    Collects command line arguments and overrides parameters.
    """
    # Parsing command line
    parser = argparse.ArgumentParser(prog='yambo-tester',
                                     description='A Python-based testing framework for validating Yambo simulations using the official Yambo test suite.',
                                     epilog="Copyright (c) 2025 Nicola Spallanzani")
    parser.add_argument('-i', '--init',
                        help='Create a config.toml file to be used as template', dest='init', action='store_true')
    parser.add_argument('-v', '--verbose',
                        help='Verbose mode', dest='verbose', action='store_true')
    parser.add_argument('-l', '--label',
                        help='Label of the submisison', type=str, dest='label')
    parser.add_argument('-d', '--download_link',
                        help='Download link', type=str, dest='link')
    parser.add_argument('--download_only',
                        help="Download only the tests' tarballs", dest='donly', action='store_true')
    parser.add_argument('-t', '--tollerance',
                        help='Tollerance (between 0 - 100%%)', type=float, dest='tollerance')
    parser.add_argument('-s', '--scratch',
                        help='Scratch directory', type=str, dest='scratch_dir')
    parser.add_argument('-c', '--cache',
                        help='Cache directory', type=str, dest='cache_dir')
    parser.add_argument('--tests',
                        help='Tests directory', type=str, dest='tests_dir')
    parser.add_argument('--bin',
                        help='Yambo bin directory', type=str, dest='yambo_bin')
    parser.add_argument('--logger',
                        help='Logger file', type=str, dest='logger', default="yambo_tester.log")
    parser.add_argument('--mpi',
                        help='MPI launcher', type=str, dest='mpi_launcher')
    parser.add_argument('--np',
                        help='Number of MPI tasks', type=int, dest='nprocs')
    parser.add_argument('--yambo',
                        help='Yambo executable', type=str, dest='yambo')
    parser.add_argument('--ypp ',
                        help='Y(ambo) P(ost)/(re) P(rocessor) exectuable', type=str, dest='ypp')
    parser.add_argument('--p2y ',
                        help='P(Wscf) 2 Y(ambo) interface exectuable', type=str, dest='p2y')
    parser.add_argument('--a2y ',
                        help='A(binit) 2 Y(ambo) interface exectuable', type=str, dest='a2y')
    parser.add_argument('--c2y ',
                        help='C(pmd) 2 Y(ambo) interface exectuable', type=str, dest='c2y')
    args = parser.parse_args()

    for arg, val in args.__dict__.items():
        if val: config['parameters'][arg] = val
    if not 'init' in config['parameters']: config['parameters']['init'] = False
    if not 'verbose' in config['parameters']: config['parameters']['verbose'] = False
    if not 'donly' in config['parameters']: config['parameters']['donly'] = False
    if not 'label' in config['parameters']: config['parameters']['label'] = ""

    return config


def main():
    """
    Main function for the command line executable.
    """
    # Setup
    config = load_config()
    config = set_cl_args(config)
    logger = setup_logging(Path(config['parameters']['logger']))
    if not parameters['init']: logger.info(f"Using {config['config']}")
    parameters = check_parameters(config['parameters'], logger)

    if parameters['donly']:
        for test_name, test_types in config['tests'].items():
            for test_type in test_types:
                test = {'name': test_name, 'type': test_type}
                tar_file, process = download_test(test['name'], test['type'], parameters, logger)
    elif parameters['init']:
        pass
    else:
        # Running the tests
        for test_name, test_types in config['tests'].items():
            for test_type in test_types:
                test = {'name': test_name, 'type': test_type}
                test['test_dir'], test['run_dir']  = setup_rundir(test, parameters, logger)
                local_logger = run_test(test, parameters, logger, verbose=parameters['verbose'])
                run_pytest(test, local_logger, verbose=parameters['verbose'])


if __name__ == '__main__':
    main()
