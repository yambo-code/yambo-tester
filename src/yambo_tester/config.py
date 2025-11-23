# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import yaml
import shutil
import string
import argparse
import urllib.request
from pathlib import Path
import importlib.resources
from datetime import datetime

# Default parameters
PARAMETERS = {
    'label': "cirun",
    'yambo_bin': "",
    'tests_dir': importlib.resources.files("yambo_tester") / "tests",
    'scratch_dir': "scratch",
    'cache_dir': "cache",
    'yambo': "yambo",
    'ypp': "ypp",
    'p2y': "p2y",
    'mpi_launcher': "mpirun",
    'nprocs': 2,
    'tollerance': 0.1,
    'download_link': "https://media.yambo-code.eu/robots/databases/tests",
    }


def load_config(logger):
    """
    Look for a config.yaml file in the current directory.
    If it doesn't find one, use the one included in the package.
    Then overwrite the default parameters with the ones from the file.
    """
    local_config = Path("config.yaml")
    if local_config.exists():
        logger.info("Using local config.yaml")
        with open(local_config, "r") as f:
            config = yaml.safe_load(f)
    else:
        logger.info("Using default config.yaml from package")
        with importlib.resources.open_text("yambo_tester.data", "config.yaml") as f:
            config = yaml.safe_load(f)

    # Overwrites default parameters with those read from the conf.yaml file
    for parameter in PARAMETERS:
        if parameter not in config["parameters"]: config["parameters"][parameter] = PARAMETERS[parameter]
    if not config['parameters']['tests_dir']: config['parameters']['tests_dir'] = PARAMETERS['tests_dir']

    if not "tests" in config:
        logger.warning("Using default tests")
        config['tests'] = {
	    "Al_bulk": ["GW-OPTICS"],
	    "Si_bulk": ["GW-OPTICS"],
	    "hBN": ["GW-OPTICS"],
	    "LiF": ["GW-OPTICS"]
        }

    return config


def check_parameters(parameters, logger):
    """
    Check parameters one by one and report it in the main logger.
    """
    for par in ['yambo_bin', 'tests_dir', 'scratch_dir', 'cache_dir']:
        if parameters[par]:
            try:
                parameters[par] = Path(parameters[par]).resolve()
                if parameters[par].is_dir():
                    logger.info(f'{par}: {parameters[par]}')
                else:
                    raise NotADirectoryError(f"{par}: {parameters[par]} exists but it is not a directory.")
            except NotADirectoryError as e:
                if par in ['scratch_dir', 'cache_dir'] and not parameters[par].exists():
                    logger.warning(f"I'm making the {par} directory!")
                    parameters[par].mkdir()
                else:
                    logger.error(e)
                    raise e

    # Directory where to copy and run the test suite
    parameters['scratch_test'] = parameters['scratch_dir'].joinpath(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{parameters['label']}")

    # Checks on executables
    if parameters['yambo_bin']:
        parameters['yambo'] = parameters['yambo_bin'].joinpath(parameters['yambo'])
        parameters['ypp'] = parameters['yambo_bin'].joinpath(parameters['ypp'])
        parameters['p2y'] = parameters['yambo_bin'].joinpath(parameters['p2y'])
    for par in ["yambo", "ypp", "p2y", "mpi_launcher"]:
        try:
            parameters[par] = Path(shutil.which(parameters[par]))
        except TypeError:
            raise FileNotFoundError(f'{par}: {parameters[par]} do not exist.')

    # Checks on nprocs and tollerance
    if isinstance(parameters['nprocs'], int):
        logger.info(f"nprocs: {parameters['nprocs']}")
    else:
        msg = f"nprocs: {parameters['nprocs']} not an int."
        logger.error(msg)
        raise TypeError(msg)
    if isinstance(parameters['tollerance'], float):
        logger.info(f"tollerance: {parameters['tollerance']}")
    else:
        msg = f"tollerance: {parameters['tollerance']} not a float."
        logger.error(msg)
        raise TypeError(msg)

    # Check on download_link
    try:
        c = urllib.request.urlopen(parameters['download_link']).getcode()
        logger.info(f"download_link: {parameters['download_link']}")
    except HTTPError as e:
        logger.error(e)
        raise e

    return parameters

       
if __name__ == '__main__':
    pass
