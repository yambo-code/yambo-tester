import sys

import pytest

from yambo_tester.cli import set_cl_args
from yambo_tester.selection import expand_workflow_requirements, normalize_runlevels, selected_step_names


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


def _requires(table):
    return lambda name, workflow_type: table.get((name, workflow_type))


def test_expand_workflow_requirements_puts_required_workflow_first():
    tests = {"He": ["GW", "DFT"], "Si_bulk": ["GW"]}
    requires = _requires({("He", "GW"): "DFT"})

    assert expand_workflow_requirements(tests, requires) == [
        ("He", "DFT"), ("He", "GW"), ("Si_bulk", "GW"),
    ]


def test_expand_workflow_requirements_adds_missing_required_workflow_once():
    tests = {"He": ["GW", "GW-OPTICS"]}
    requires = _requires({("He", "GW"): "DFT", ("He", "GW-OPTICS"): "DFT"})

    assert expand_workflow_requirements(tests, requires) == [
        ("He", "DFT"), ("He", "GW"), ("He", "GW-OPTICS"),
    ]


def test_expand_workflow_requirements_rejects_cycles():
    requires = _requires({("He", "GW"): "DFT", ("He", "DFT"): "GW"})

    with pytest.raises(ValueError, match="cycle"):
        expand_workflow_requirements({"He": ["GW"]}, requires)
