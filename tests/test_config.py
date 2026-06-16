import argparse
import logging
import os
import sys
import pytest

from yambo_tester.cli import parse_executable_override, set_cl_args
from yambo_tester.config import check_parameters, load_config


def _write_executable(path, stderr_text="", stdout_text=""):
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "if '-h' in sys.argv:\n"
        f"    sys.stderr.write({stderr_text!r})\n"
        f"    sys.stdout.write({stdout_text!r})\n"
    )
    os.chmod(path, 0o755)


def test_load_config_ignores_legacy_executable_fields_and_only_injects_required_defaults(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.toml").write_text(
        "[parameters]\n"
        "tests_dir = \"\"\n"
        "yambo = \"legacy-yambo\"\n"
        "p2y = \"legacy-p2y\"\n"
        "ypp = \"legacy-ypp\"\n"
        "\n"
        "[executables]\n"
        "a2y = \"table-a2y\"\n"
        "custom_tool = \"table-custom\"\n"
    )

    config = load_config()

    assert "yambo" not in config["parameters"]
    assert "p2y" not in config["parameters"]
    assert "ypp" not in config["parameters"]
    assert config["executables"]["yambo"] == "yambo"
    assert config["executables"]["p2y"] == "p2y"
    assert config["executables"]["a2y"] == "table-a2y"
    assert config["executables"]["custom_tool"] == "table-custom"
    assert "ypp" not in config["executables"]


def test_set_cl_args_registers_executable_overrides(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["yambo-tester", "--exe", "ypp=/opt/ypp", "--exe", "custom_tool=/opt/custom"])

    config = {"parameters": {}, "executables": {}}

    updated = set_cl_args(config)

    assert updated["executables"]["ypp"] == "/opt/ypp"
    assert updated["executables"]["custom_tool"] == "/opt/custom"


def test_parse_executable_override_accepts_key_value_pairs():
    assert parse_executable_override("ypp=/opt/ypp") == ("ypp", "/opt/ypp")


def test_parse_executable_override_rejects_malformed_values():
    with pytest.raises(argparse.ArgumentTypeError):
        parse_executable_override("missing-separator")


def test_check_parameters_ignores_unconfigured_optional_executables(monkeypatch, tmp_path):
    yambo_bin = tmp_path / "bin"
    yambo_bin.mkdir()
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    scratch_dir = tmp_path / "scratch"
    scratch_dir.mkdir()
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    _write_executable(
        yambo_bin / "yambo",
        stderr_text="Version: 5.3.0 revision 123 hash abc\nConfiguration: MPI+OpenMP\n",
    )
    _write_executable(yambo_bin / "p2y")
    _write_executable(yambo_bin / "a2y")
    _write_executable(yambo_bin / "custom_tool")

    parameters = {
        "init": False,
        "donly": False,
        "download_link": "https://example.invalid/tests",
        "cache_dir": cache_dir,
        "scratch_dir": scratch_dir,
        "tests_dir": tests_dir,
        "yambo_bin": yambo_bin,
        "mpi_launcher": None,
        "nprocs": 2,
        "thrs": 1,
        "tollerance": 0.1,
        "label": "demo",
    }
    executables = {
        "yambo": "yambo",
        "p2y": "p2y",
        "a2y": "a2y",
        "custom_tool": "custom_tool",
    }

    resolved = check_parameters(parameters, executables, logging.getLogger("test-config"))

    assert resolved["executables"]["yambo"] == yambo_bin / "yambo"
    assert resolved["executables"]["p2y"] == yambo_bin / "p2y"
    assert resolved["executables"]["a2y"] == yambo_bin / "a2y"
    assert resolved["executables"]["custom_tool"] == yambo_bin / "custom_tool"
    assert "ypp" not in resolved["executables"]
    assert resolved["mpi"] is True
    assert resolved["omp"] is True


def test_check_parameters_rejects_missing_required_executable(monkeypatch, tmp_path):
    yambo_bin = tmp_path / "bin"
    yambo_bin.mkdir()
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    scratch_dir = tmp_path / "scratch"
    scratch_dir.mkdir()
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    _write_executable(
        yambo_bin / "yambo",
        stderr_text="Version: 5.3.0 revision 123 hash abc\nConfiguration: MPI\n",
    )
    _write_executable(yambo_bin / "a2y")

    parameters = {
        "init": False,
        "donly": False,
        "download_link": "https://example.invalid/tests",
        "cache_dir": cache_dir,
        "scratch_dir": scratch_dir,
        "tests_dir": tests_dir,
        "yambo_bin": yambo_bin,
        "mpi_launcher": None,
        "nprocs": 2,
        "thrs": 1,
        "tollerance": 0.1,
        "label": "demo",
    }
    executables = {
        "yambo": "yambo",
        "p2y": "p2y",
        "a2y": "a2y",
    }

    with pytest.raises(FileNotFoundError, match="p2y"):
        check_parameters(parameters, executables, logging.getLogger("test-config-missing"))


def _base_runtime_parameters(tmp_path, download_link="", yambo_version=""):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    scratch_dir = tmp_path / "scratch"
    scratch_dir.mkdir()
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    yambo_bin = tmp_path / "bin"
    yambo_bin.mkdir()

    parameters = {
        "init": False,
        "donly": False,
        "download_link": download_link,
        "yambo_version": yambo_version,
        "cache_dir": cache_dir,
        "scratch_dir": scratch_dir,
        "tests_dir": tests_dir,
        "yambo_bin": yambo_bin,
        "mpi_launcher": None,
        "nprocs": 2,
        "thrs": 1,
        "tollerance": 0.1,
        "label": "demo",
    }
    if download_link:
        parameters["download_link_origin"] = "config"
    return parameters


def _write_required_executables(yambo_bin, yambo_stderr):
    _write_executable(yambo_bin / "yambo", stderr_text=yambo_stderr)
    _write_executable(yambo_bin / "p2y")
    _write_executable(yambo_bin / "a2y")


def test_set_cl_args_registers_yambo_version_and_download_link(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "yambo-tester",
            "--yambo-version",
            "6",
            "--download_link",
            "https://example.invalid/custom",
        ],
    )

    config = {"parameters": {}, "executables": {}}

    updated = set_cl_args(config)

    assert updated["parameters"]["yambo_version"] == "6"
    assert updated["parameters"]["download_link"] == "https://example.invalid/custom"
    assert updated["parameters"]["download_link_origin"] == "cli"
    assert "link" not in updated["parameters"]


def test_check_parameters_detects_yambo6_without_selecting_global_repository(monkeypatch, tmp_path):
    parameters = _base_runtime_parameters(tmp_path)
    _write_required_executables(
        parameters["yambo_bin"],
        "Version: 6.0.0 revision 123 hash abc\nConfiguration: MPI\n",
    )

    resolved = check_parameters(
        parameters,
        {"yambo": "yambo", "p2y": "p2y", "a2y": "a2y"},
        logging.getLogger("test-config-version-detect"),
    )

    assert resolved["yambo_version"] == "6"
    assert resolved["download_link"] == ""


def test_check_parameters_yambo_version_override_wins_over_detection(monkeypatch, tmp_path):
    parameters = _base_runtime_parameters(tmp_path, yambo_version="5")
    _write_required_executables(
        parameters["yambo_bin"],
        "Version: 6.0.0 revision 123 hash abc\nConfiguration: MPI\n",
    )

    resolved = check_parameters(
        parameters,
        {"yambo": "yambo", "p2y": "p2y", "a2y": "a2y"},
        logging.getLogger("test-config-version-override"),
    )

    assert resolved["yambo_version"] == "5"
    assert resolved["download_link"] == ""


def test_check_parameters_preserves_explicit_download_link(monkeypatch, tmp_path):
    parameters = _base_runtime_parameters(tmp_path, download_link="https://example.invalid/custom")
    _write_required_executables(
        parameters["yambo_bin"],
        "Version: 6.0.0 revision 123 hash abc\nConfiguration: MPI\n",
    )

    resolved = check_parameters(
        parameters,
        {"yambo": "yambo", "p2y": "p2y", "a2y": "a2y"},
        logging.getLogger("test-config-explicit-link"),
    )

    assert resolved["yambo_version"] == "6"
    assert resolved["download_link"] == "https://example.invalid/custom"
    assert resolved["download_link_origin"] == "config"


def test_check_parameters_download_only_resolves_yambo5_without_global_repository(monkeypatch, tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    parameters = {
        "init": False,
        "donly": True,
        "download_link": "",
        "yambo_version": "",
        "cache_dir": cache_dir,
        "tests_dir": tmp_path,
    }

    resolved = check_parameters(parameters, {}, logging.getLogger("test-config-download-only"))

    assert resolved["yambo_version"] == "5"
    assert resolved["download_link"] == ""
