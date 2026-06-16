# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import os
import toml
import shutil
import pytest
import tomllib
import tarfile
import subprocess
from pathlib import Path
import importlib.resources
from .log import setup_test_logger
from .config import get_executable
from .download import download_test, sha256sum
from .versioning import (
    DEFAULT_YAMBO_VERSION,
    resolve_workflow_tarball_url,
    workflow_steps_for_version,
    workflow_supports_version,
)
from .selection import (
    MISSING_EXECUTABLE_REASON,
    MISSING_EXECUTABLE_RETURNCODE,
    RUNLEVEL_FILTER_REASON,
    RUNLEVEL_FILTER_RETURNCODE,
    UNSUPPORTED_VERSION_REASON,
    UNSUPPORTED_VERSION_RETURNCODE,
    selected_step_names,
)


def step_sort_key(item):
    name, run = item
    return run.get('input', name)


def stdout_filename(step_name):
    return f"{step_name}.stdout"


def build_run_command(run, parameters):
    cmd = []
    if parameters['mpi'] and parameters['mpi_launcher']:
        nprocs = run.get('nprocs', parameters['nprocs'])
        cmd.extend([str(parameters['mpi_launcher']), '-np', str(nprocs)])
    executable = get_executable(parameters, run['exe'])
    if executable is None:
        raise FileNotFoundError(f"{run['exe']}: executable not available.")
    cmd.append(str(executable))
    if run.get('input'):
        cmd.extend(['-F', str(run['input'])])
    if run.get('input_dir'):
        cmd.extend(['-I', str(run['input_dir'])])
    flags = ""
    if run.get('flags'):
        flags = f",{run['flags']}"
    if run.get('output'):
        cmd.extend(['-J', str(run['output']) + flags, '-C', str(run['output'])])
    return cmd


def command_reference_output(std_out, run, run_dir):
    return std_out


def source_workflow_config(test, parameters):
    config_path = parameters['tests_dir'].joinpath(test['name'], test['type'], "tests.toml")
    if not config_path.exists():
        raise FileNotFoundError(f"{config_path} not available")
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def parameters_with_workflow_download_link(test, parameters, logger):
    workflow_config = source_workflow_config(test, parameters)
    yambo_version = parameters.get('yambo_version') or DEFAULT_YAMBO_VERSION
    if not workflow_supports_version(workflow_config, yambo_version):
        logger.info(f"[{test['name']}/{test['type']}] skipped download for unsupported Yambo version {yambo_version}")
        return None

    download_link = resolve_workflow_tarball_url(workflow_config, yambo_version, parameters)
    if not download_link:
        raise ValueError(
            f"No tarball_url metadata or explicit download_link for {test['name']}/{test['type']}."
        )

    resolved = dict(parameters)
    resolved['download_link'] = download_link
    logger.info(f"[{test['name']}/{test['type']}] download_link: {download_link}")
    return resolved


def download_workflow_tarball(test, parameters, logger):
    resolved_parameters = parameters_with_workflow_download_link(test, parameters, logger)
    if resolved_parameters is None:
        return None, None
    return download_test(test['name'], test['type'], resolved_parameters, logger)


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

    yambo_version = parameters.get('yambo_version') or DEFAULT_YAMBO_VERSION
    if workflow_supports_version(config, yambo_version):
        tar_file, process = download_workflow_tarball(test, parameters, logger)
        try:
            if process is not None:
                retcode = process.wait()
                if retcode != 0:
                    raise RuntimeError(f"Download of tarball {tar_file} failed.")
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
    else:
        logger.info(f"{this_test} skipped tarball extraction for unsupported Yambo version {yambo_version}")

    return test_dir, run_dir


def run_test(test, parameters, logger, verbose=False):
    this_test = f"[{test['name']}/{test['type']}]"
    local_logger = setup_test_logger(test['run_dir'])

    local_config = test['run_dir'].joinpath("tests.toml")
    with open(local_config, "rb") as f:
        workflow_config = tomllib.load(f)

    SAVE_converted = test['run_dir'].joinpath('SAVE_converted')
    SAVE = test['run_dir'].joinpath('SAVE')
    if SAVE_converted.exists():
        oldSAVE = SAVE.rename(test['run_dir'].joinpath('oldSAVE'))
        SAVE = SAVE_converted.rename(SAVE)

    yambo_version = parameters.get('yambo_version') or DEFAULT_YAMBO_VERSION
    config = workflow_steps_for_version(workflow_config, yambo_version)
    results = {
        "tollerance": parameters['tollerance'],
        "yambo_version": yambo_version,
    }

    if not workflow_supports_version(workflow_config, yambo_version):
        for name, run in config.items():
            results[name] = {
                "returncode": UNSUPPORTED_VERSION_RETURNCODE,
                "cmd": '',
                "stdout": None,
                "stderr": None,
                "run_dir": str(test['run_dir']),
                "skip_reason": UNSUPPORTED_VERSION_REASON,
                "runlevel": run.get("runlevel", ""),
            }
        with open(test['run_dir'].joinpath("results.toml"), "w") as f:
            toml.dump(results, f)
        local_logger.info(f"{this_test} skipped for unsupported Yambo version {yambo_version}")
        return local_logger

    subtests = list(config.items())
    subtests.sort(key=step_sort_key) # input sorting when available
    selected_names = selected_step_names(config, parameters.get('runlevels', []))

    # For OpenMP pralallelization
    env = os.environ.copy()
    if parameters['omp']: env["OMP_NUM_THREADS"] = str(parameters['thrs'])

    # Loop that launches the subtests
    for name, run in subtests:
        if name not in selected_names:
            results[name] = {
                "returncode": RUNLEVEL_FILTER_RETURNCODE,
                "cmd": '',
                "stdout": None,
                "stderr": None,
                "run_dir": str(test['run_dir']),
                "skip_reason": RUNLEVEL_FILTER_REASON,
                "runlevel": run.get("runlevel", ""),
            }
            local_logger.info(f"{name} skipped by runlevel selection")
        elif get_executable(parameters, run['exe']):
            
            # Execution of any actions
            if run.get('actions', False):
                for action in run["actions"]:
                    cmd = action.strip().split()
                    if cmd[0] == "mkdir":
                        assert len(cmd) == 2, f"Action 'mkdir' require 2 elements, {len(cmd)} provided."
                        ret_action = test['run_dir'].joinpath(cmd[1])
                        ret_action.mkdir(exist_ok=True)
                    elif cmd[0] == "cp":
                        assert len(cmd) == 3, f"Action 'cp' require 3 elements, {len(cmd)} provided."
                        if not test['run_dir'].glob(cmd[1]): local_logger.warning(f"No files found for action: {action}")
                        for f in test['run_dir'].glob(cmd[1]):
                            shutil.copy(Path(f), test['run_dir'].joinpath(cmd[2]))
                            #ret_action = Path(f).copy_into(test['run_dir'].joinpath(cmd[2]))
                    else:
                        ret_action = subprocess.run(cmd, shell=False, cwd=str(test['run_dir']))
                        if ret_action.returncode != 0:
                            local_logger.warning(f"{this_test} action failed: {cmd}")

            # Generation of the command line for the test
            cmd = build_run_command(run, parameters)

            # Launching the test
            logger.info(f"{this_test} Launching {name}")
            local_logger.info(f"{' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                cwd = str(test['run_dir']),
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
                text = True,
                shell = False,
                env = env
            )
            std_out, std_err = process.communicate()
            stdout_file = test['run_dir'].joinpath(stdout_filename(name))
            stdout_file.write_text(command_reference_output(std_out, run, test['run_dir']))
            if verbose: local_logger.info(std_out.strip())
            if std_err: local_logger.error(std_err)
    
            # Run info
            results[name] = {
                "returncode": process.returncode,
                "cmd": ' '.join(cmd),
                "stdout": std_out,
                "stdout_file": stdout_file.name,
                "stderr": std_err,
                "run_dir": str(test['run_dir']),
                "runlevel": run.get("runlevel", ""),
            }
            
        else:
            # Run skipped
            results[name] = {
                "returncode": MISSING_EXECUTABLE_RETURNCODE,
                "cmd": '',
                "stdout": None,
                "stderr": None,
                "run_dir": str(test['run_dir']),
                "skip_reason": MISSING_EXECUTABLE_REASON,
                "runlevel": run.get("runlevel", ""),
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
