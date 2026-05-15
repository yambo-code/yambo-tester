import sys

import pytest

from yambo_tester.cli import set_cl_args
from yambo_tester.selection import normalize_runlevels, selected_step_names


def test_normalize_runlevels_accepts_repeated_and_csv_values():
    assert normalize_runlevels(["QP", "bse,optics", " "]) == {"qp", "bse", "optics"}


def test_selected_step_names_returns_all_steps_without_filter():
    steps = {
        "01_init": {"runlevel": "init", "dependencies": []},
        "02_qp": {"runlevel": "qp", "dependencies": ["01_init"]},
    }

    assert selected_step_names(steps, []) == {"01_init", "02_qp"}


def test_selected_step_names_includes_transitive_dependencies():
    steps = {
        "01_init": {"runlevel": "init", "dependencies": []},
        "02_qp": {"runlevel": "qp", "dependencies": ["01_init"]},
        "03_bse": {"runlevel": "bse", "dependencies": ["02_qp"]},
        "04_optics": {"runlevel": "optics", "dependencies": ["01_init"]},
    }

    assert selected_step_names(steps, ["bse"]) == {"01_init", "02_qp", "03_bse"}


def test_selected_step_names_rejects_unknown_dependencies():
    steps = {
        "02_qp": {"runlevel": "qp", "dependencies": ["missing"]},
    }

    with pytest.raises(ValueError, match="unknown dependency"):
        selected_step_names(steps, ["qp"])


def test_set_cl_args_collects_repeated_runlevels(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["yambo-tester", "--runlevel", "qp", "--runlevel", "bse"])
    config = {"parameters": {}}

    updated = set_cl_args(config)

    assert updated["parameters"]["runlevels"] == ["qp", "bse"]
