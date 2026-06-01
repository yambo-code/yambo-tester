# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import argparse
from pathlib import Path
import importlib.resources
import tomllib
from .log import setup_logging
from .download import download_test
from .config import load_config, check_parameters
from .runner import setup_rundir, run_test, run_pytest


def parse_executable_override(value):
    """
    Parse a generic executable override of the form KEY=VALUE.
    """
    if "=" not in value:
        raise argparse.ArgumentTypeError("Executable overrides must use KEY=VALUE syntax.")

    key, executable = value.split("=", 1)
    key = key.strip()
    executable = executable.strip()
    if not key or not executable:
        raise argparse.ArgumentTypeError("Executable overrides must use KEY=VALUE syntax.")
    return key, executable


def load_workflow_keywords():
    keywords_file = importlib.resources.files("yambo_tester.data") / "workflow_keywords.toml"
    with keywords_file.open("rb") as f:
        keywords = tomllib.load(f)

    return {
        "executables": list(keywords.get("executables", [])),
        "runlevels": list(keywords.get("runlevels", [])),
    }


def print_keywords(keywords):
    for keyword in keywords:
        print(keyword)


def set_cl_args(config):
    """
    Collects command line arguments and overrides parameters.
    """
    config.setdefault('executables', {})
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
    parser.add_argument('--nochecksum',
                        help='Disable checksum on tarballs', dest='nochecksum', action='store_false')
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
    parser.add_argument('--thrs',
                        help='Number of OpenMP threads per task', type=int, dest='thrs')
    parser.add_argument('--runlevel',
                        help='Run only workflow steps matching this runlevel and their dependencies. May be repeated.',
                        type=str, action='append', dest='runlevels')
    list_group = parser.add_mutually_exclusive_group()
    list_group.add_argument('--list-executables',
                            help='List the executable keywords known to the tester and exit.',
                            dest='list_executables',
                            action='store_true')
    list_group.add_argument('--list-runlevels',
                            help='List the runlevel keywords known to the tester and exit.',
                            dest='list_runlevels',
                            action='store_true')
    parser.add_argument('--exe',
                        help='Executable override in KEY=VALUE form. May be repeated.',
                        type=parse_executable_override,
                        action='append',
                        dest='executables')
    args = parser.parse_args()

    for arg, val in args.__dict__.items():
        if arg == 'executables':
            continue
        if val:
            config['parameters'][arg] = val
    if args.executables:
        config.setdefault('executables', {})
        for key, executable in args.executables:
            config['executables'][key] = executable
    if not 'init' in config['parameters']: config['parameters']['init'] = False
    if not 'verbose' in config['parameters']: config['parameters']['verbose'] = False
    if not 'donly' in config['parameters']: config['parameters']['donly'] = False
    if not 'nochecksum' in config['parameters']: config['parameters']['nochecksum'] = False
    if not 'label' in config['parameters']: config['parameters']['label'] = ""

    return config


def main():
    """
    Main function for the command line executable.
    """
    # Setup
    config = load_config()
    config = set_cl_args(config)
    if config['parameters'].get('list_executables') or config['parameters'].get('list_runlevels'):
        keywords = load_workflow_keywords()
        if config['parameters'].get('list_executables'):
            print_keywords(keywords["executables"])
        if config['parameters'].get('list_runlevels'):
            print_keywords(keywords["runlevels"])
        return
    logger = setup_logging(Path(config['parameters']['logger']))
    if not config['parameters']['init']: logger.info(f"Using {config['config']}")
    parameters = check_parameters(config['parameters'], config['executables'], logger)

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
                logger.info(f"[{test_name}/{test_type}] Starting test")
                test['test_dir'], test['run_dir']  = setup_rundir(test, parameters, logger)
                local_logger = run_test(test, parameters, logger, verbose=parameters['verbose'])
                run_pytest(test, local_logger, verbose=parameters['verbose'])
                logger.info(f"[{test_name}/{test_type}] Finished test")


if __name__ == '__main__':
    main()
