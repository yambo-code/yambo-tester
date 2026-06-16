import logging
import os
import tarfile
import tomllib

from yambo_tester import runner
from yambo_tester.runner import build_run_command, command_reference_output, download_workflow_tarball, run_test, setup_rundir, stdout_filename


def test_build_run_command_accepts_p2y_without_input_or_output():
    run = {
        "exe": "p2y",
        "input_dir": "Al.save",
        "nprocs": 1,
    }
    parameters = {
        "yambo_version": "6",
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
        "yambo_version": "6",
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
    assert results["yambo_version"] == "6"
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


def test_run_test_skips_workflow_when_yambo_version_is_unsupported(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "tests.toml").write_text(
        "[yambo_versions]\n"
        "supported = [\"5\"]\n"
        "[01_p2y]\n"
        "exe = \"p2y\"\n"
        "input_dir = \"Al.save\"\n"
        "runlevel = \"dft\"\n"
        "dependencies = []\n"
        "[01_p2y.reference]\n"
        "\"STDOUT\" = [\"== P2Y completed ==\"]\n"
    )

    parameters = {
        "yambo_version": "6",
        "mpi": False,
        "mpi_launcher": None,
        "nprocs": 2,
        "omp": False,
        "thrs": 1,
        "tollerance": 0.1,
        "runlevels": [],
        "executables": {
            "p2y": tmp_path / "not-run",
        },
    }
    test = {"name": "Al_bulk", "type": "DFT", "run_dir": run_dir}

    run_test(test, parameters, logging.getLogger("test-runner-unsupported-version"))

    with open(run_dir / "results.toml", "rb") as f:
        results = tomllib.load(f)

    assert results["yambo_version"] == "6"
    assert results["01_p2y"]["returncode"] == -9997
    assert results["01_p2y"]["skip_reason"] == "unsupported-yambo-version"


def _write_source_workflow(tmp_path, tarball_url="https://example.invalid/tests", supported='["5", "6"]'):
    tests_dir = tmp_path / "tests-src"
    workflow_dir = tests_dir / "Al_bulk" / "DFT"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "tests.toml").write_text(
        f'sha256 = "unused"\n'
        f'tarball_url = "{tarball_url}"\n\n'
        '[yambo_versions]\n'
        f'supported = {supported}\n\n'
        '[01_p2y]\n'
        'exe = "p2y"\n'
        'input_dir = "Al.save"\n'
        'runlevel = "dft"\n'
        'dependencies = []\n'
        '[01_p2y.reference]\n'
        '"STDOUT" = ["== P2Y completed =="]\n'
    )
    return tests_dir


def _write_empty_tarball(tmp_path):
    tar_file = tmp_path / "Al_bulk_DFT.tar.gz"
    with tarfile.open(tar_file, "w:gz"):
        pass
    return tar_file


def test_download_workflow_tarball_uses_resolved_metadata_url(monkeypatch, tmp_path):
    tests_dir = _write_source_workflow(tmp_path, tarball_url="https://example.invalid/workflow")
    captured = []

    def fake_download_test(name, run_type, parameters, logger):
        captured.append((name, run_type, parameters["download_link"]))
        return tmp_path / "unused.tar.gz", None

    monkeypatch.setattr(runner, "download_test", fake_download_test)
    parameters = {
        "tests_dir": tests_dir,
        "cache_dir": tmp_path,
        "download_link": "",
        "yambo_version": "5",
        "verbose": False,
    }

    download_workflow_tarball({"name": "Al_bulk", "type": "DFT"}, parameters, logging.getLogger("test-download-url"))

    assert captured == [("Al_bulk", "DFT", "https://example.invalid/workflow")]


def test_setup_rundir_uses_same_resolved_metadata_url(monkeypatch, tmp_path):
    tests_dir = _write_source_workflow(tmp_path, tarball_url="https://example.invalid/workflow")
    tar_file = _write_empty_tarball(tmp_path)
    captured = []

    def fake_download_test(name, run_type, parameters, logger):
        captured.append((name, run_type, parameters["download_link"]))
        return tar_file, None

    monkeypatch.setattr(runner, "download_test", fake_download_test)
    parameters = {
        "tests_dir": tests_dir,
        "scratch_test": tmp_path / "scratch",
        "cache_dir": tmp_path,
        "download_link": "",
        "yambo_version": "5",
        "verbose": False,
        "nochecksum": True,
    }

    setup_rundir({"name": "Al_bulk", "type": "DFT"}, parameters, logging.getLogger("test-setup-url"))

    assert captured == [("Al_bulk", "DFT", "https://example.invalid/workflow")]


def test_download_workflow_tarball_skips_unsupported_version(monkeypatch, tmp_path):
    tests_dir = _write_source_workflow(tmp_path, supported='["5"]')

    def fake_download_test(*_args, **_kwargs):
        raise AssertionError("download_test should not be called")

    monkeypatch.setattr(runner, "download_test", fake_download_test)
    parameters = {
        "tests_dir": tests_dir,
        "cache_dir": tmp_path,
        "download_link": "",
        "yambo_version": "6",
        "verbose": False,
    }

    assert download_workflow_tarball({"name": "Al_bulk", "type": "DFT"}, parameters, logging.getLogger("test-unsupported-url")) == (None, None)
