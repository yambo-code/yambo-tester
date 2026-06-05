import logging
import os
import tomllib

from yambo_tester.runner import build_run_command, command_reference_output, run_test, stdout_filename


def test_build_run_command_accepts_p2y_without_input_or_output():
    run = {
        "exe": "p2y",
        "input_dir": "Al.save",
        "nprocs": 1,
    }
    parameters = {
        "mpi": False,
        "mpi_launcher": None,
        "nprocs": 2,
        "executables": {
            "p2y": "/usr/bin/p2y",
        },
    }

    assert build_run_command(run, parameters) == ["/usr/bin/p2y", "-I", "Al.save"]


def test_build_run_command_maps_a2y_input_to_file_flag():
    run = {
        "exe": "a2y",
        "input": "DB/file.nc",
        "nprocs": 1,
    }
    parameters = {
        "mpi": False,
        "mpi_launcher": None,
        "nprocs": 2,
        "executables": {
            "a2y": "/usr/bin/a2y",
        },
    }

    assert build_run_command(run, parameters) == ["/usr/bin/a2y", "-F", "DB/file.nc"]


def test_run_test_p2y_step_writes_stdout_file_and_uses_input_dir(tmp_path):
    executable = tmp_path / "fake_p2y.py"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib\n"
        "import sys\n"
        "pathlib.Path('argv.txt').write_text(' '.join(sys.argv[1:]))\n"
        "print('== P2Y completed ==')\n"
    )
    os.chmod(executable, 0o755)

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "tests.toml").write_text(
        "[01_p2y]\n"
        "exe = \"p2y\"\n"
        "input_dir = \"Al.save\"\n"
        "runlevel = \"p2y\"\n"
        "nprocs = 1\n"
        "dependencies = []\n"
        "[01_p2y.reference]\n"
        "\"STDOUT\" = [\"== P2Y completed ==\"]\n"
    )

    parameters = {
        "mpi": False,
        "mpi_launcher": None,
        "nprocs": 2,
        "omp": False,
        "thrs": 1,
        "tollerance": 0.1,
        "runlevels": [],
        "executables": {
            "p2y": executable,
        },
    }
    test = {"name": "Al_bulk", "type": "DFT", "run_dir": run_dir}

    run_test(test, parameters, logging.getLogger("test-runner-p2y"))

    assert (run_dir / "argv.txt").read_text() == "-I Al.save"
    assert (run_dir / stdout_filename("01_p2y")).read_text() == "== P2Y completed ==\n"

    with open(run_dir / "results.toml", "rb") as f:
        results = tomllib.load(f)
    assert results["01_p2y"]["returncode"] == 0
    assert results["01_p2y"]["cmd"] == f"{executable} -I Al.save"
    assert results["01_p2y"]["stdout_file"] == stdout_filename("01_p2y")


def test_command_reference_output_preserves_stdout_only(tmp_path):
    (tmp_path / "l_p2y").write_text("<--->  == P2Y completed ==\n")

    text = command_reference_output("== P2Y completed ==\n", {"exe": "p2y"}, tmp_path)

    assert text == "== P2Y completed ==\n"


def test_run_test_skips_missing_optional_executable(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "tests.toml").write_text(
        "[01_custom]\n"
        "exe = \"custom_tool\"\n"
        "input_dir = \"Al.save\"\n"
        "runlevel = \"custom\"\n"
        "dependencies = []\n"
        "[01_custom.reference]\n"
        "\"STDOUT\" = [\"unused\"]\n"
    )

    parameters = {
        "mpi": False,
        "mpi_launcher": None,
        "nprocs": 2,
        "omp": False,
        "thrs": 1,
        "tollerance": 0.1,
        "runlevels": [],
        "executables": {
            "yambo": tmp_path / "fake_yambo",
        },
    }
    test = {"name": "Al_bulk", "type": "DFT", "run_dir": run_dir}

    run_test(test, parameters, logging.getLogger("test-runner-custom"))

    with open(run_dir / "results.toml", "rb") as f:
        results = tomllib.load(f)

    assert results["01_custom"]["returncode"] == -9999
    assert results["01_custom"]["skip_reason"] == "missing-executable"
