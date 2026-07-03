import logging
import tarfile
import tomllib

import pytest

from yambo_tester import runner
from yambo_tester.template_expansion import expand_workflow_templates, load_workflow_templates, workflow_uses_templates
from yambo_tester.versioning import workflow_steps_for_version


TEMPLATES = {
    "demo": {
        "exe": "yambo",
        "input": "INPUTS/Y6/{step}",
        "output": "{step}",
        "runlevel": "base",
        "dependencies": ["{previous_step}"],
        "reference": {
            "REFERENCE/Y6/o-{step}.base": ["{step}/base", "A"],
        },
        "versions": {
            "5": {
                "input": "INPUTS/Y5/{step}",
                "reference": {
                    "REFERENCE/Y5/o-{step}.base": ["{step}/base5", "A5"],
                },
            },
        },
    },
}


def test_step_type_expands_template_fields_and_placeholders():
    workflow = {
        "sha256": "abc",
        "00_prepare": {"exe": "p2y"},
        "01_demo": {"step_type": "demo"},
    }

    expanded = expand_workflow_templates(workflow, templates=TEMPLATES)

    assert expanded["sha256"] == "abc"
    assert expanded["00_prepare"] == {"exe": "p2y"}
    assert expanded["01_demo"]["input"] == "INPUTS/Y6/01_demo"
    assert expanded["01_demo"]["output"] == "01_demo"
    assert expanded["01_demo"]["dependencies"] == ["00_prepare"]
    assert expanded["01_demo"]["reference"] == {
        "REFERENCE/Y6/o-01_demo.base": ["01_demo/base", "A"],
    }
    assert "step_type" not in expanded["01_demo"]


def test_local_fields_override_template_defaults_and_reference_keys_merge():
    workflow = {
        "01_demo": {
            "step_type": "demo",
            "runlevel": "custom",
            "reference": {
                "REFERENCE/Y6/o-01_demo.local": ["local", "B"],
            },
        },
    }

    expanded = expand_workflow_templates(workflow, templates=TEMPLATES)

    assert expanded["01_demo"]["runlevel"] == "custom"
    assert expanded["01_demo"]["reference"] == {
        "REFERENCE/Y6/o-01_demo.base": ["01_demo/base", "A"],
        "REFERENCE/Y6/o-01_demo.local": ["local", "B"],
    }


def test_template_and_local_version_overrides_resolve_through_versioning():
    workflow = {
        "01_demo": {
            "step_type": "demo",
            "versions": {
                "5": {
                    "runlevel": "legacy",
                    "reference": {
                        "REFERENCE/Y5/o-01_demo.local": ["local5", "B5"],
                    },
                },
            },
        },
    }

    expanded = expand_workflow_templates(workflow, templates=TEMPLATES)
    resolved = workflow_steps_for_version(expanded, "5")

    assert resolved["01_demo"]["input"] == "INPUTS/Y5/01_demo"
    assert resolved["01_demo"]["runlevel"] == "legacy"
    assert resolved["01_demo"]["reference"] == {
        "REFERENCE/Y5/o-01_demo.base": ["01_demo/base5", "A5"],
        "REFERENCE/Y5/o-01_demo.local": ["local5", "B5"],
    }


def test_packaged_templates_cover_conversion_and_input_init_variants():
    workflow = {
        "00_p2y": {"step_type": "p2y", "input_dir": "Al.save"},
        "01_init": {"step_type": "init_input"},
        "02_a2y": {"step_type": "a2y", "input": "DB/WFK.nc"},
    }

    expanded = expand_workflow_templates(workflow, templates=load_workflow_templates())

    assert expanded["00_p2y"]["reference"] == {"STDOUT": ["Game Over"]}
    assert expanded["00_p2y"]["versions"]["5"]["reference"] == {"STDOUT": ["== P2Y completed =="]}
    assert expanded["01_init"]["input"] == "INPUTS/Y6/01_init"
    assert expanded["01_init"]["dependencies"] == []
    assert expanded["01_init"]["versions"]["5"]["input"] == "INPUTS/Y5/01_init"
    assert expanded["02_a2y"]["reference"] == {"STDOUT": ["== Writing DB2 (wavefunctions) + nlPP ..."]}



def test_fully_expanded_workflow_remains_unchanged():
    workflow = {"01_plain": {"exe": "yambo", "reference": {"STDOUT": ["ok"]}}}

    assert not workflow_uses_templates(workflow)
    assert expand_workflow_templates(workflow, templates=TEMPLATES) == workflow


def test_unknown_step_type_names_workflow_file():
    workflow = {"01_missing": {"step_type": "missing"}}

    with pytest.raises(ValueError, match="missing.*example/tests.toml"):
        expand_workflow_templates(workflow, templates=TEMPLATES, workflow_file="example/tests.toml")


def _write_empty_tarball(tmp_path):
    tar_file = tmp_path / "Template_DFT.tar.gz"
    with tarfile.open(tar_file, "w:gz"):
        pass
    return tar_file


def test_setup_rundir_rewrites_scratch_tests_toml_when_templates_are_used(monkeypatch, tmp_path):
    tests_dir = tmp_path / "tests-src"
    workflow_dir = tests_dir / "Template" / "DFT"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "tests.toml").write_text(
        'sha256 = "unused"\n'
        'tarball_url = "https://example.invalid/workflow"\n\n'
        '[yambo_versions]\n'
        'supported = ["6"]\n\n'
        '[01_demo]\n'
        'step_type = "demo"\n'
    )
    tar_file = _write_empty_tarball(tmp_path)

    def fake_download_test(name, run_type, parameters, logger):
        return tar_file, None

    monkeypatch.setattr(runner, "download_test", fake_download_test)
    monkeypatch.setattr(runner, "load_workflow_templates", lambda: TEMPLATES, raising=False)
    monkeypatch.setattr(
        runner,
        "expand_workflow_templates",
        lambda config, workflow_file=None: expand_workflow_templates(config, templates=TEMPLATES, workflow_file=workflow_file),
    )
    parameters = {
        "tests_dir": tests_dir,
        "scratch_test": tmp_path / "scratch",
        "cache_dir": tmp_path,
        "download_link": "",
        "yambo_version": "6",
        "verbose": False,
        "nochecksum": True,
    }

    _, run_dir = runner.setup_rundir({"name": "Template", "type": "DFT"}, parameters, logging.getLogger("test-template-setup"))

    with (run_dir / "tests.toml").open("rb") as f:
        config = tomllib.load(f)
    assert config["01_demo"]["input"] == "INPUTS/Y6/01_demo"
    assert "step_type" not in config["01_demo"]
