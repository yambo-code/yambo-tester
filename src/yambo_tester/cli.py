# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import argparse
import importlib.resources
from pathlib import Path
from .log import setup_logging
from .config import load_config, check_parameters
from .runner import setup_rundir, run_test, run_pytest


def set_cl_args(config):
    """
    Collects command line arguments and overrides parameters.
    """
    # Parsing command line
    parser = argparse.ArgumentParser(prog='yambo-tester',
                                     description='Simple Python program for run Yambo tests',
                                     epilog="Copyright (c) 2025 Nicola Spallanzani")
    parser.add_argument('-v', help='verbose mode', dest='verbose', action='store_true')
    parser.add_argument('-label', help='label of the submisison', type=str, dest='label')
    parser.add_argument('-link', help='download link', type=str, dest='link')
    parser.add_argument('-tol', help='tollerance (between 0 - 100%%)', type=float, dest='tollerance')
    parser.add_argument('-scratch', help='scratch directory', type=str, dest='scratch_dir')
    parser.add_argument('-cache', help='cache directory', type=str, dest='cache_dir')
    parser.add_argument('-tests', help='tests directory', type=str, dest='tests_dir')
    parser.add_argument('-bin', help='yambo bin directory', type=str, dest='yambo_bin')
    parser.add_argument('-mpi', help='mpi launcher', type=str, dest='mpi_launcher')
    parser.add_argument('-np', help='number of mpi tasks', type=int, dest='nprocs')
    parser.add_argument('-yambo', help='yambo executable', type=str, dest='yambo')
    parser.add_argument('-ypp ', help='ypp exectuable', type=str, dest='ypp')
    parser.add_argument('-p2y ', help='p2y exectuable', type=str, dest='p2y')
    args = parser.parse_args()

    for arg, val in args.__dict__.items():
        if val: config['parameters'][arg] = val
    if not 'verbose' in config['parameters']: config['parameters']['verbose'] = False
    if not 'label' in config['parameters']: config['parameters']['label'] = ""

    return config


def main():
    """
    Main function for the command line executable.
    """
    # Setup
    logger = setup_logging(Path('yambo_tester.log'))
    config = load_config(logger=logger)
    config = set_cl_args(config)
    parameters = check_parameters(config['parameters'], logger=logger)

    # Running the tests
    for test_name, test_types in config['tests'].items():
        for test_type in test_types:
            test = {'name': test_name, 'type': test_type}
            test['test_dir'], test['run_dir']  = setup_rundir(test, parameters, logger)
            local_logger = run_test(test, parameters, logger, verbose=parameters['verbose'])
            run_pytest(test, local_logger, verbose=parameters['verbose'])



if __name__ == '__main__':
    main()
