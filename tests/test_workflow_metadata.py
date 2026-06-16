import tomllib
from pathlib import Path


DFT_URL = "https://media.yambo-code.eu/robots/databases/y6"
TESTS_URL = "https://media.yambo-code.eu/robots/databases/tests"
EXPECTED_DEFAULT_TESTS = {
    "Al_bulk": ["DFT", "GW-OPTICS", "ELPH"],
    "PA_chain": ["DFT", "PA_chain"],
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
