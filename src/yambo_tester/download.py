# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import hashlib
import argparse
import subprocess
from pathlib import Path
from .log import setup_logging


def get_args():
    tests_dir = './'
    download_link = 'https://media.yambo-code.eu/robots/databases/tests'
    parser = argparse.ArgumentParser()
    parser.add_argument('-cache', help='cache directory', type=str, dest='cache_dir', default=tests_dir)
    parser.add_argument('-link', help='download link', type=str, dest='link', default=download_link)
    args = parser.parse_args()
    parameters['cache_dir'] = Path(args.cache_dir).resolve()
    parameters['download_link'] = args.download_link
    return parameters


def sha256sum(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def wget(wargs, logger, verbose=False):
    cmd = "wget " + wargs
    process = subprocess.Popen(
        cmd,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        text = True,
        shell = True
    )
    std_out, std_err = process.communicate()
    if verbose:
        logger.info(std_out.strip())
        if std_err: logger.error(std_err)
    return process


def download_test(name, run_type, parameters, logger):
    """
    Check if the test tarball exists in the cache directory and download it if it is missing.
    """
    tar_name = name + "_" + run_type + ".tar.gz"
    process = None

    try:
        if not parameters['cache_dir'].is_dir(): raise
    except:
        logger.warning(f"Creating cache_dir: {parameters['cache_dir']}")
        parameters['cache_dir'].mkdir()

    tar_file = parameters['cache_dir'].joinpath(tar_name)
    if tar_file.exists():
        logger.info(f"File {tar_name} already available")
    else:
        try:
            logger.info(f"Downloading file {tar_name}")
            wargs = f"{parameters['download_link']}/{tar_name} -O {tar_file}"
            process = wget(wargs, logger, verbose=parameters['verbose'])
        except:
            logger.error("Not able to download the tarball.")
            raise

    return tar_file, process

    
if __name__ == '__main__':
    parameters = get_args()
    logger = setup_logging(Path('download_tests.log'))

    tests = {
	"Al_bulk": ["GW-OPTICS"],
	"Si_bulk": ["GW-OPTICS"],
	"hBN": ["GW-OPTICS"],
	"LiF": ["GW-OPTICS"]
    }

    for name, runs in tests.items():
        for run_type in runs:
            tar_file, process = download_test(name, run_type, patameters, logger)
            print(tar_file)

