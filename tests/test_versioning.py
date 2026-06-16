import pytest

from yambo_tester.versioning import (
    download_link_for_version,
    resolve_workflow_metadata,
    resolve_workflow_tarball_url,
    resolve_yambo_version,
    workflow_steps_for_version,
    workflow_supports_version,
)


def test_resolve_yambo_version_prefers_explicit_override():
    detected = {"version": ["6", "0", "0"]}

    assert resolve_yambo_version("5", detected) == "5"


def test_resolve_yambo_version_uses_detected_major_when_no_override():
    detected = {"version": ["6", "0", "0"]}

    assert resolve_yambo_version("", detected) == "6"


def test_resolve_yambo_version_falls_back_to_yambo5():
    assert resolve_yambo_version("", {}) == "5"


def test_resolve_yambo_version_rejects_unsupported_major():
    with pytest.raises(ValueError, match="Unsupported Yambo major version"):
        resolve_yambo_version("7")


def test_download_link_for_version_maps_supported_versions():
    assert download_link_for_version("5") == "https://media.yambo-code.eu/robots/databases/tests"
    assert download_link_for_version("6.0") == "https://media.yambo-code.eu/robots/databases/y6"


def test_workflow_steps_for_version_applies_shallow_step_overlay():
    workflow = {
        "sha256": "abc",
        "yambo_versions": {"supported": ["5", "6"]},
        "00_p2y": {
            "exe": "p2y",
            "input_dir": "Al.save",
            "reference": {"STDOUT": ["== P2Y completed =="]},
            "versions": {
                "6": {
                    "input_dir": "Al6.save",
                    "reference": {"STDOUT": ["Game Over"]},
                },
            },
        },
    }

    resolved = workflow_steps_for_version(workflow, "6")

    assert set(resolved) == {"00_p2y"}
    assert resolved["00_p2y"]["exe"] == "p2y"
    assert resolved["00_p2y"]["input_dir"] == "Al6.save"
    assert resolved["00_p2y"]["reference"] == {"STDOUT": ["Game Over"]}
    assert "versions" not in resolved["00_p2y"]


def test_workflow_steps_for_version_keeps_base_step_without_overlay():
    workflow = {
        "00_p2y": {
            "exe": "p2y",
            "reference": {"STDOUT": ["== P2Y completed =="]},
            "versions": {"6": {"reference": {"STDOUT": ["Game Over"]}}},
        },
    }

    resolved = workflow_steps_for_version(workflow, "5")

    assert resolved["00_p2y"]["reference"] == {"STDOUT": ["== P2Y completed =="]}


def test_workflow_supports_version_defaults_to_supported():
    assert workflow_supports_version({"00_p2y": {"exe": "p2y"}}, "6")


def test_workflow_supports_version_reads_supported_list():
    workflow = {"yambo_versions": {"supported": ["5"]}}

    assert workflow_supports_version(workflow, "5")
    assert not workflow_supports_version(workflow, "6")


def test_resolve_workflow_metadata_applies_top_level_version_overlay():
    workflow = {
        "sha256": "abc",
        "tarball_url": "https://example.invalid/tests",
        "yambo_versions": {"supported": ["5", "6"]},
        "versions": {"6": {"tarball_url": "https://example.invalid/y6"}},
        "00_p2y": {"exe": "p2y"},
    }

    metadata = resolve_workflow_metadata(workflow, "6")

    assert metadata == {
        "sha256": "abc",
        "tarball_url": "https://example.invalid/y6",
        "yambo_versions": {"supported": ["5", "6"]},
    }


def test_resolve_workflow_tarball_url_uses_base_metadata():
    workflow = {"tarball_url": "https://example.invalid/tests"}

    assert resolve_workflow_tarball_url(workflow, "5", {}) == "https://example.invalid/tests"


def test_resolve_workflow_tarball_url_uses_version_overlay():
    workflow = {
        "tarball_url": "https://example.invalid/tests",
        "versions": {"6": {"tarball_url": "https://example.invalid/y6"}},
    }

    assert resolve_workflow_tarball_url(workflow, "6", {}) == "https://example.invalid/y6"


def test_resolve_workflow_tarball_url_cli_override_wins():
    workflow = {"tarball_url": "https://example.invalid/tests"}
    parameters = {
        "download_link": "https://example.invalid/cli",
        "download_link_origin": "cli",
    }

    assert resolve_workflow_tarball_url(workflow, "5", parameters) == "https://example.invalid/cli"


def test_resolve_workflow_tarball_url_config_override_wins():
    workflow = {"tarball_url": "https://example.invalid/tests"}
    parameters = {
        "download_link": "https://example.invalid/config",
        "download_link_origin": "config",
    }

    assert resolve_workflow_tarball_url(workflow, "5", parameters) == "https://example.invalid/config"


def test_workflow_metadata_keys_are_excluded_from_steps():
    workflow = {
        "sha256": "abc",
        "tarball_url": "https://example.invalid/tests",
        "yambo_versions": {"supported": ["5"]},
        "versions": {"6": {"tarball_url": "https://example.invalid/y6"}},
        "00_p2y": {"exe": "p2y"},
    }

    assert set(workflow_steps_for_version(workflow, "5")) == {"00_p2y"}
