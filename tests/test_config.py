import argparse
import logging
import os
import urllib.request

import pytest

from yambo_tester.cli import parse_executable_override
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


def test_load_config_migrates_legacy_executable_fields(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.toml").write_text(
        "[parameters]\n"
        "tests_dir = \"\"\n"
        "yambo = \"legacy-yambo\"\n"
        "p2y = \"legacy-p2y\"\n"
        "\n"
        "[executables]\n"
        "a2y = \"table-a2y\"\n"
    )

    config = load_config()

    assert "yambo" not in config["parameters"]
    assert "p2y" not in config["parameters"]
    assert config["executables"]["yambo"] == "legacy-yambo"
    assert config["executables"]["p2y"] == "legacy-p2y"
    assert config["executables"]["a2y"] == "table-a2y"


def test_parse_executable_override_accepts_key_value_pairs():
    assert parse_executable_override("ypp=/opt/ypp") == ("ypp", "/opt/ypp")


def test_parse_executable_override_rejects_malformed_values():
    with pytest.raises(argparse.ArgumentTypeError):
        parse_executable_override("missing-separator")


def test_check_parameters_resolves_optional_and_custom_executables(monkeypatch, tmp_path):
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_args, **_kwargs: type("Resp", (), {"getcode": lambda self: 200})())

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
        "ypp": "ypp",
        "custom_tool": "custom_tool",
    }

    resolved = check_parameters(parameters, executables, logging.getLogger("test-config"))

    assert resolved["executables"]["yambo"] == yambo_bin / "yambo"
    assert resolved["executables"]["p2y"] == yambo_bin / "p2y"
    assert resolved["executables"]["a2y"] == yambo_bin / "a2y"
    assert resolved["executables"]["ypp"] is None
    assert resolved["executables"]["custom_tool"] == yambo_bin / "custom_tool"
    assert resolved["mpi"] is True
    assert resolved["omp"] is True


def test_check_parameters_rejects_missing_required_executable(monkeypatch, tmp_path):
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_args, **_kwargs: type("Resp", (), {"getcode": lambda self: 200})())

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
