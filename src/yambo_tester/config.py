# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import tomllib
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
    'yambo_ph': "yambo_ph",
    'ypp_ph': "ypp_ph",
    'yambo_sc': "yambo_sc",
    'ypp_sc': "ypp_sc",
    'yambo_rt': "yambo_rt",
    'ypp_rt': "ypp_rt",
    'yambo_nl': "yambo_nl",
    'ypp_nl': "ypp_nl",
    'p2y': "p2y",
    'a2y': "a2y",
    'c2y': "c2y",
    'mpi_launcher': "mpirun",
    'nprocs': 2,
    'tollerance': 0.1,
    'download_link': "https://media.yambo-code.eu/robots/databases/tests",
    }


def load_config():
    """
    Look for a config.toml file in the current directory.
    If it doesn't find one, use the one included in the package.
    Then overwrite the default parameters with the ones from the file.
    """
    local_config = Path("config.toml").resolve()
    if local_config.exists():
        with open(local_config, "rb") as f:
            config = tomllib.load(f)
            config['config'] = local_config
    else:
        with importlib.resources.open_binary("yambo_tester.data", "config.toml") as f:
            config = tomllib.load(f)
            config['config'] = importlib.resources.files("yambo_tester.data") / "config.toml"

    # Overwrites default parameters with those read from the conf.toml file
    for parameter in PARAMETERS:
        if parameter not in config["parameters"]: config["parameters"][parameter] = PARAMETERS[parameter]
    if not config['parameters']['tests_dir']: config['parameters']['tests_dir'] = PARAMETERS['tests_dir']

    if not "tests" in config:
        config['tests'] = {
	    "Al_bulk": ["GW-OPTICS"],
	    "Si_bulk": ["GW-OPTICS"],
	    "hBN": ["GW-OPTICS"],
	    "LiF": ["GW-OPTICS"]
        }

    return config


def check_dir(par, directory, logger):
    try:
        pathdir = Path(directory).resolve()
        if pathdir.is_dir():
            logger.info(f'{par}: {pathdir}')
        else:
            raise NotADirectoryError(f"{par}: {directory} exists but it is not a directory.")
    except NotADirectoryError as e:
        if par in ['scratch_dir', 'cache_dir'] and not pathdir.exists():
            logger.warning(f"I'm making the {par} directory!")
            pathdir.mkdir()
        else:
            logger.error(e)
            raise e
    return pathdir


def check_parameters(parameters, logger):
    """
    Check parameters one by one and report it in the main logger.
    """
    if not parameters['init']:
        # Check download_link
        try:
            logger.info(f"download_link: {parameters['download_link']}")
            c = urllib.request.urlopen(parameters['download_link']).getcode()
        except HTTPError as e:
            logger.warning(f"Link not reachable: the tests will be performed only if the tarball is available in the cache directory.")

    # Check only cache directory
    if parameters['donly']:
        parameters['cache_dir'] = check_dir('cache_dir', parameters['cache_dir'], logger)

    # Copy the default config.toml
    elif parameters['init']:
        if Path('config.toml').exists():
            logger.error('File config.toml already exists!')
        else:
            config_default = importlib.resources.files("yambo_tester.data") / "config.toml"
            config_template = config_default.copy('config.toml')
            logger.info("Copied the config.toml template.")

    else:
        # Check directories
        for par in ['yambo_bin', 'tests_dir', 'scratch_dir', 'cache_dir']:
            if parameters[par]:
                parameters[par] = check_dir(par, parameters[par], logger)
    
        # Directory where to copy and run the test suite
        parameters['scratch_test'] = parameters['scratch_dir'].joinpath(
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{parameters['label']}"
        )
    
        # Checks on executables
        for par in ["yambo", "ypp", "p2y", 'a2y', 'c2y', 'yambo_ph', 'ypp_ph',
                    'yambo_sc', 'ypp_sc', 'yambo_rt', 'ypp_rt', 'yambo_nl', 'ypp_nl']:
            if parameters['yambo_bin']:
                parameters[par] = parameters['yambo_bin'].joinpath(parameters[par])
            try:
                parameters[par] = Path(shutil.which(parameters[par]))
                logger.info(f"{par}: {parameters[par]}")
            except TypeError:
                if '_' in parameters[par]:
                    parameters[par] = None # Project's tests deactivated
                    logger.warning(f"{par}: {parameters[par]} project's tests deactivated!")
                else:
                    raise FileNotFoundError(f"{par}: {parameters[par]} do not exist.")
    
        if parameters['mpi_launcher']:
            try:
                parameters['mpi_launcher'] = Path(shutil.which(parameters['mpi_launcher']))
                logger.info(f"mpi_launcher: {parameters['mpi_launcher']}")
            except TypeError:
                raise FileNotFoundError(f"mpi_launcher: {parameters['mpi_launcher']} do not exist.")
    
        # Checks on nprocs and tollerance
        if parameters["mpi_launcher"]:
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

    return parameters


if __name__ == '__main__':
    pass
