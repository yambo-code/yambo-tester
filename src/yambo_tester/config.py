# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import shutil
import string
import tomllib
import argparse
import subprocess
from pathlib import Path
import importlib.resources
from datetime import datetime
from .versioning import resolve_yambo_version

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
    'download_link': "",
    'yambo_version': "",
    }

REQUIRED_EXECUTABLES = {
    'yambo': 'yambo',
    'p2y': 'p2y',
    'a2y': 'a2y',
}

LEGACY_PARAMETER_EXECUTABLES = {
    'yambo',
    'p2y',
    'a2y',
    'ypp',
    'yambo_ph',
    'ypp_ph',
    'yambo_sc',
    'ypp_sc',
    'yambo_rt',
    'ypp_rt',
    'yambo_nl',
    'ypp_nl',
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

    config.setdefault("parameters", {})
    if config["parameters"].get("download_link"):
        config["parameters"]["download_link_origin"] = "config"
    config.setdefault("executables", {})

    # Overwrite default parameters with those read from the config file.
    for parameter in PARAMETERS:
        if parameter not in config["parameters"]:
            config["parameters"][parameter] = PARAMETERS[parameter]
    if not config['parameters']['tests_dir']:
        config['parameters']['tests_dir'] = PARAMETERS['tests_dir']

    # Drop legacy top-level executable fields. The executable registry lives in [executables].
    for name in LEGACY_PARAMETER_EXECUTABLES:
        config["parameters"].pop(name, None)

    # Fill any missing executable entries from the required registry.
    for name, value in REQUIRED_EXECUTABLES.items():
        if name not in config["executables"]:
            config["executables"][name] = value

    if not "tests" in config:
        config['tests'] = {
            "Al_bulk": ["DFT", "GW-OPTICS", "ELPH"],
            "PA_chain": ["DFT", "PA_chain"],
            "He": ["DFT"],
            "Nickel": ["DFT"],
            "AlAs": ["DFT"],
            "hBN": ["DFT"],
            "Iron_With-SOC": ["DFT"],
            "Iron_Without-SOC": ["DFT"],
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


def resolve_runtime_yambo_version(parameters, detected_info=None, logger=None):
    """
    Resolve and store the effective Yambo major version.

    Tarball source URLs are workflow metadata, unless explicitly overridden by
    CLI or config. This keeps parameter validation independent of any selected
    workflow.
    """
    yambo_version = resolve_yambo_version(
        requested=parameters.get('yambo_version'),
        detected_info=detected_info,
    )
    parameters['yambo_version'] = yambo_version
    if logger:
        logger.info(f"yambo_version: {yambo_version}")
    return parameters


def check_parameters(parameters, executables=None, logger=None):
    """
    Check parameters one by one and report it in the main logger.
    """
    if logger is None:
        logger = executables
        executables = {}
    if executables is None:
        executables = {}

    # Check only cache directory
    if parameters['donly']:
        for par in ['tests_dir', 'cache_dir']:
            if parameters.get(par):
                parameters[par] = check_dir(par, parameters[par], logger)
        parameters = resolve_runtime_yambo_version(parameters, logger=logger)
        if parameters.get('download_link'):
            logger.info(f"download_link: {parameters['download_link']}")

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
        yambo_info = get_yambo_info(parameters['executables']['yambo'])
        parameters.update(yambo_info)
        parameters = resolve_runtime_yambo_version(parameters, yambo_info, logger)
        if parameters.get('download_link'):
            logger.info(f"download_link: {parameters['download_link']}")
        
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
