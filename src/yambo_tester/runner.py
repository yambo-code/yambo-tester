# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import toml
import shutil
import pytest
import tomllib
import tarfile
import subprocess
from pathlib import Path
import importlib.resources
from .log import setup_logging
from .download import download_test, sha256sum


def setup_rundir(test, parameters, logger):
    """
    Prepare the test environment.

    Within the scratch directory, create a subdirectory named after the test and a random suffix.
    Copy the input and reference files associated with the test type. Check whether the test
    tarball needs to be downloaded and extract it into the test directory.

    :param test: dict containing metadata for the test.
    :param parameters: dict containg parameters metadata.
    :param logger: main logger instance.
    :return: tuple containing the Path to the created test directory and run directory.
    """
    this_test = f"[{test['name']}/{test['type']}]"
    tar_file, process = download_test(test['name'], test['type'], parameters, logger)

    try:
        if not parameters['scratch_test'].exists():
            parameters['scratch_test'].mkdir(exist_ok=True)
        test_dir = parameters['scratch_test'].joinpath(test['name'])
        test_dir.mkdir(exist_ok=True)
        logger.info(f"Working in {test_dir}")
    except:
        logger.error(f"Not able to create runtest folder into {parameters['scratch_test']}")
        raise

    try:
        src_dir = parameters['tests_dir'].joinpath(test['name'], test['type'])
        run_dir = shutil.copytree(src_dir, test_dir.joinpath(test['type']))
        logger.info(f"Copied input and reference files from {src_dir} to {run_dir}")
    except:
        logger.error(f"Copying input and reference files from {src_dir} to {run_dir}")
        raise

    local_config = run_dir.joinpath("tests.toml")
    if local_config.exists():
        logger.info(f"{this_test} Using local tests.toml")
        with open(local_config, "rb") as f:
            config = tomllib.load(f)
    else:
        logger.error(f"{local_config} not available")
        raise FileNotFoundError(f"{local_config} not available") 

    try:
        if process != None:
            retcode = process.wait()
            if retcode != 0:
                raise RuntimeError(f"Dawnload of tarball {tar_file} failed.")
        if not parameters['nochecksum']:
            if not config['sha256'] == sha256sum(tar_file):
                logger.error(f"SHA-256 mismatch for file '{tar_file.name}'.")
                raise ValueError(f"SHA-256 mismatch for file '{tar_file.name}'.")
        with tarfile.open(tar_file) as tar:
            tar.extractall(path=test_dir)
        logger.info(f"Extracted tarball")
    except RuntimeError as e:
        logger.error(e)
        raise e
    except Exception as e:
        logger.error(f"Unable to extract the tarball into {test_dir}")
        raise e

    return test_dir, run_dir


def run_test(test, parameters, logger, verbose=False):
    this_test = f"[{test['name']}/{test['type']}]"
    logger.info(f"{this_test} Starting test")
    local_logger = setup_logging(test['run_dir'].joinpath('tester.log'))

    local_config = test['run_dir'].joinpath("tests.toml")
    with open(local_config, "rb") as f:
        config = tomllib.load(f)
    sha256 = config.pop('sha256', None)

    SAVE_converted = test['run_dir'].joinpath('SAVE_converted')
    SAVE = test['run_dir'].joinpath('SAVE')
    if SAVE_converted.exists():
        oldSAVE = SAVE.rename(test['run_dir'].joinpath('oldSAVE'))
        SAVE = SAVE_converted.rename(SAVE)

    results = {"tollerance": parameters['tollerance']} # collect info about a run
    subtests = list(config.items())
    subtests.sort(key=lambda x: x[1]['input']) # input sorting

    # Loop that launches the subtests
    for name, run in subtests:
        cmd = []
        if parameters['mpi_launcher']: cmd.extend([str(parameters['mpi_launcher']), '-np', str(parameters['nprocs'])])
        cmd.append(str(parameters[run['exe']]))
        if 'actions' in run:
            if run['actions']: pass # TODO
        if run['input']: cmd.extend(['-F', str(run['input'])])
        flags = ""
        if 'flags' in run:
            if run['flags']: flags = f",{run['flags']}"
        if run['output']: cmd.extend(['-J', str(run['output'])+flags, '-C', str(run['output'])])

        logger.info(f"{this_test} Launching {name}")
        if verbose: local_logger.info(f"{' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            cwd = str(test['run_dir']),
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            text = True,
            shell = False
        )
        std_out, std_err = process.communicate()
        if verbose: local_logger.info(std_out.strip())
        if std_err: local_logger.error(std_err)

        # Run info
        results[name] = {
            "returncode": process.returncode,
            "cmd": ' '.join(cmd),
            "stdout": std_out,
            "stderr": std_err,
            "run_dir": str(test['run_dir']),
        }

    with open(test['run_dir'].joinpath("results.toml"), "w") as f:
        toml.dump(results, f)
        
    return local_logger


def run_pytest(test, local_logger, verbose=False):
    args = []

    if verbose:
        args.append("-vv")
    else:
        args.append("-q")
    local_logger.info(f"[{test['name']}/{test['type']}] Start checking results with pytest")

    #validation_tests_dir = Path(__file__).parent / "tests"
    validation_tests_dir = importlib.resources.files("yambo_tester") / "tests"

    if not validation_tests_dir.exists():
        local_logger.error(f"Validation tests directory not found: {validation_tests_dir}")
        raise FileNotFoundError(validation_tests_dir)

    # Pytest report in JUnit XML
    report_path = Path(test['run_dir']) / "pytest-report.xml"
    args.append(f"--junitxml={report_path}")

    args.append(f"--rundir={test['run_dir']}")
    # Run pytest in the tests folder of the package
    return pytest.main(args + [str(validation_tests_dir)])


if __name__ == '__main__':
    pass

