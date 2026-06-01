# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import shutil
import string
import tomllib
import argparse
import subprocess
import urllib.request
from urllib.error import HTTPError
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
    'mpi_launcher': "mpirun",
    'nprocs': 2,
    'thrs': 1,
    'tollerance': 0.1,
    'runlevels': [],
    'download_link': "https://media.yambo-code.eu/robots/databases/tests",
    }

DEFAULT_EXECUTABLES = {
    'yambo': 'yambo',
    'p2y': 'p2y',
    'a2y': 'a2y',
    'ypp': 'ypp',
    'yambo_ph': 'yambo_ph',
    'ypp_ph': 'ypp_ph',
    'yambo_sc': 'yambo_sc',
    'ypp_sc': 'ypp_sc',
    'yambo_rt': 'yambo_rt',
    'ypp_rt': 'ypp_rt',
    'yambo_nl': 'yambo_nl',
    'ypp_nl': 'ypp_nl',
}

REQUIRED_EXECUTABLES = {'yambo', 'p2y', 'a2y'}


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

    config.setdefault("parameters", {})
    config.setdefault("executables", {})

    # Overwrite default parameters with those read from the config file.
    for parameter in PARAMETERS:
        if parameter not in config["parameters"]:
            config["parameters"][parameter] = PARAMETERS[parameter]
    if not config['parameters']['tests_dir']:
        config['parameters']['tests_dir'] = PARAMETERS['tests_dir']

    # Migrate legacy top-level executable fields from [parameters] into the new registry.
    for name in list(DEFAULT_EXECUTABLES):
        if name in config["parameters"]:
            if name not in config["executables"]:
                config["executables"][name] = config["parameters"][name]
            del config["parameters"][name]

    # Fill any missing executable entries from the default registry.
    for name, value in DEFAULT_EXECUTABLES.items():
        if name not in config["executables"]:
            config["executables"][name] = value

    if not "tests" in config:
        config['tests'] = {
            "Al_bulk": ["DFT", "GW-OPTICS"],
            "He": ["DFT"],
            "Si_bulk": ["GW-OPTICS"],
            "hBN": ["GW-OPTICS"],
            "LiF": ["GW-OPTICS"]
        }

    return config


def _resolve_candidate_executable(executable, yambo_bin=None):
    if not executable:
        return None

    candidate = Path(executable)
    if yambo_bin and not candidate.is_absolute() and len(candidate.parts) == 1:
        candidate = Path(yambo_bin).joinpath(candidate)

    resolved = shutil.which(str(candidate))
    if resolved is None:
        return None
    return Path(resolved)


def get_executable(parameters, name):
    """
    Return the resolved executable path stored in the runtime registry.
    """
    executables = parameters.get('executables', {})
    if name in executables:
        return executables[name]
    return parameters.get(name)


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


def get_yambo_info(yambo: str) -> dict:
    """
    Retrieve version and compilation configuration information from a Yambo executable.

    This function takes the path to the **yambo** executable, runs it with the
    '-h' option, and extracts useful metadata such as the software version and
    build configuration. The returned data is provided as a dictionary for easy
    programmatic access.

    Parameters
    ----------
    yambo : str
        Path to the Yambo executable.

    Returns
    -------
    info : dict
        A dictionary containing extracted properties of the Yambo installation.
        Typical keys include:

        * ``version`` — Yambo version: a list like [magior, minor, patch].
        * ``compilation`` — Details about configuration options.
    """
    process = subprocess.run([str(yambo), "-h"], capture_output=True, text=True)
    info = {}
    for line in process.stderr.split('\n'):
        if 'Version' in line:
            tmp = line.split(':')[1].strip().split()
            info['version'] = tmp[0].split('.')
            info['revision'] = tmp[2]
            info['hash'] = tmp[4]
        if 'Configuration' in line:
            info['compilation'] = line.split(':')[1].strip().split('+')
            tmp = [x.lower() for x in info['compilation']]
            info['mpi'] = True if 'mpi' in tmp else False
            info['omp'] = True if 'openmp' in tmp else False
            info['dp'] = True if 'dp' in tmp else False
            info['slk'] = True if 'slk' in tmp else False
            info['slepc'] = True if 'slepc' in tmp else False
            info['par_io'] = True if 'hdf5_mpi_io' in tmp else False
    return info


def check_parameters(parameters, executables=None, logger=None):
    """
    Check parameters one by one and report it in the main logger.
    """
    if logger is None:
        logger = executables
        executables = {}
    if executables is None:
        executables = {}

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
            shutil.copyfile(config_default, 'config.toml')
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
        resolved_executables = {}
        for name, executable in executables.items():
            resolved = _resolve_candidate_executable(executable, parameters['yambo_bin'])
            if resolved is not None:
                resolved_executables[name] = resolved
                logger.info(f"{name}: {resolved}")
            elif name in REQUIRED_EXECUTABLES:
                raise FileNotFoundError(f"{name}: {executable} do not exist.")
            else:
                resolved_executables[name] = None
                logger.warning(f"{name}: {executable} tests deactivated!")

        parameters['executables'] = resolved_executables

        # Extract info from "yambo -h"
        parameters.update(get_yambo_info(parameters['executables']['yambo']))
        
        if parameters['mpi_launcher']:
            try:
                parameters['mpi_launcher'] = Path(shutil.which(parameters['mpi_launcher']))
                logger.info(f"mpi_launcher: {parameters['mpi_launcher']}")
            except TypeError:
                raise FileNotFoundError(f"mpi_launcher: {parameters['mpi_launcher']} do not exist.")
        
        # Checks on nprocs, omp and tollerance
        if parameters['mpi'] and parameters["mpi_launcher"]:
            if isinstance(parameters['nprocs'], int):
                logger.info(f"nprocs: {parameters['nprocs']}")
            else:
                msg = f"nprocs: {parameters['nprocs']} not an int."
                logger.error(msg)
                raise TypeError(msg)
        if parameters['omp']:
            if isinstance(parameters['thrs'], int):
                logger.info(f"thrs: {parameters['thrs']}")
            else:
                msg = f"thrs: {parameters['thrs']} not an int."
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
