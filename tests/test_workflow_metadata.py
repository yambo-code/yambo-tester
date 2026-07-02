import re
import tomllib
from pathlib import Path


DFT_URL = "https://media.yambo-code.eu/robots/databases/y6"
TESTS_URL = "https://media.yambo-code.eu/robots/databases/tests"
EXPECTED_DEFAULT_TESTS = {
    "Al_bulk": ["DFT", "GW-OPTICS", "ELPH"],
    "PA_chain": ["DFT", "PA_chain"],
    "Si_bulk": ["DFT"],
    "He": ["DFT"],
    "Nickel": ["DFT"],
    "AlAs": ["DFT"],
    "hBN": ["DFT"],
    "Iron_With-SOC": ["DFT"],
    "Iron_Without-SOC": ["DFT"],
}


def workflow_files():
    return sorted(Path("src/yambo_tester/tests").glob("*/*/tests.toml"))


def test_imported_workflows_declare_version_support_and_tarball_url():
    assert workflow_files()
    for path in workflow_files():
        with path.open("rb") as f:
            config = tomllib.load(f)

        if path.parent.name == "DFT":
            assert config["yambo_versions"]["supported"] == ["5", "6"], path
            assert config["tarball_url"] == DFT_URL, path
        else:
            assert config["yambo_versions"]["supported"] == ["5"], path
            assert config["tarball_url"] == TESTS_URL, path


def test_packaged_default_config_restores_validated_workflows():
    with Path("src/yambo_tester/data/config.toml").open("rb") as f:
        config = tomllib.load(f)

    assert config["tests"] == EXPECTED_DEFAULT_TESTS


def test_imported_reference_keys_are_explicit_relative_paths():
    for path in workflow_files():
        with path.open("rb") as f:
            config = tomllib.load(f)

        for step_name, step in config.items():
            if step_name in {"sha256", "tarball_url", "yambo_versions", "versions"}:
                continue
            references = [step.get("reference", {})]
            references.extend(
                overlay.get("reference", {})
                for overlay in step.get("versions", {}).values()
            )
            for reference in references:
                for key in reference:
                    assert key == "STDOUT" or key.startswith("REFERENCE/"), (path, step_name, key)


def test_imported_fixture_inputs_and_references_are_versioned_by_support():
    for path in workflow_files():
        with path.open("rb") as f:
            config = tomllib.load(f)
        supported = set(config["yambo_versions"]["supported"])
        workflow = path.parent

        if (workflow / "INPUTS").exists():
            assert (workflow / "INPUTS" / "Y5").is_dir(), path
            assert not any(p.is_file() for p in (workflow / "INPUTS").iterdir()), path
            if "6" in supported:
                assert (workflow / "INPUTS" / "Y6").is_dir(), path
            else:
                assert not (workflow / "INPUTS" / "Y6").exists(), path

        if (workflow / "REFERENCE").exists():
            assert (workflow / "REFERENCE" / "Y5").is_dir(), path
            assert not any(p.is_file() for p in (workflow / "REFERENCE").iterdir()), path
            if "6" in supported:
                assert (workflow / "REFERENCE" / "Y6").is_dir(), path
            else:
                assert not (workflow / "REFERENCE" / "Y6").exists(), path


def test_dft_workflows_use_yambo5_overlays_for_compatibility_metadata():
    for path in workflow_files():
        if path.parent.name != "DFT":
            continue
        with path.open("rb") as f:
            config = tomllib.load(f)

        assert config.get("versions", {}).get("5", {}).get("tarball_url") == TESTS_URL, path
        for step_name, step in config.items():
            if step_name in {"sha256", "tarball_url", "yambo_versions", "versions"}:
                continue
            if "reference" in step:
                assert all(key == "STDOUT" or key.startswith("REFERENCE/Y6/") for key in step["reference"]), (path, step_name)
            if "reference" in step.get("versions", {}).get("5", {}):
                assert all(
                    key == "STDOUT" or key.startswith("REFERENCE/Y5/")
                    for key in step["versions"]["5"]["reference"]
                ), (path, step_name)


def test_step_child_tables_are_grouped_with_their_step():
    table_re = re.compile(r"^\[([^\]]+)\]$", re.MULTILINE)
    metadata_tables = {"yambo_versions", "versions"}

    for path in workflow_files():
        text = path.read_text()
        headers = [(match.group(1), match.start()) for match in table_re.finditer(text)]
        with path.open("rb") as f:
            config = tomllib.load(f)
        step_names = [name for name in config if name not in {"sha256", "tarball_url", "yambo_versions", "versions"}]

        step_header_positions = {name: pos for name, pos in headers if name in step_names}
        assert set(step_header_positions) == set(step_names), path

        for index, step_name in enumerate(step_names):
            start = step_header_positions[step_name]
            next_positions = [
                step_header_positions[name]
                for name in step_names[index + 1:]
                if step_header_positions[name] > start
            ]
            end = min(next_positions) if next_positions else len(text)

            for header, pos in headers:
                if header in metadata_tables or header.startswith("versions."):
                    continue
                if header.startswith(f"{step_name}."):
                    assert start < pos < end, (path, step_name, header)
