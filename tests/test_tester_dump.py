import tomllib

import netCDF4 as nc
import numpy as np
import pytest

from scripts.tester_dump import dump_variables, format_numeric_value, main, parse_variables


def _write_dataset(path):
    with nc.Dataset(path, "w") as dataset:
        dataset.createDimension("x", 4)
        dataset.createDimension("y", 3)
        dataset.createDimension("long", 105)

        one = dataset.createVariable("one", "f8", ("x",))
        one[:] = [1.0, 2.5, 3.0, 4.25]

        two = dataset.createVariable("two", "i4", ("x",))
        two[:] = [10, 20, 30, 40]

        matrix = dataset.createVariable("matrix", "i4", ("x", "y"))
        matrix[:, :] = np.arange(12).reshape(4, 3)

        long = dataset.createVariable("long", "i4", ("long",))
        long[:] = np.arange(105)


def _read_lines(path):
    return path.read_text().splitlines()


def test_parse_variables_accepts_repeatable_and_comma_separated_values():
    assert parse_variables(["one", "two,three", "four"]) == ["one", "two", "three", "four"]


def test_format_numeric_value_preserves_numpy_scalar_type_formatting():
    assert format_numeric_value(np.float32(0.1)) == "0.1"
    assert format_numeric_value(np.float64(0.1)) == "0.1"
    assert format_numeric_value(np.int32(10)) == "10"


def test_dump_one_variable(tmp_path):
    input_file = tmp_path / "sample.nc"
    output_file = tmp_path / "reference.txt"
    _write_dataset(input_file)

    dump_variables(input_file, ["one"], output_file)

    assert _read_lines(output_file) == ["1.0", "2.5", "3.0", "4.25"]


def test_dump_multiple_variables_in_requested_order(tmp_path):
    input_file = tmp_path / "sample.nc"
    output_file = tmp_path / "reference.txt"
    _write_dataset(input_file)

    dump_variables(input_file, ["two", "one"], output_file)

    assert _read_lines(output_file) == ["10", "20", "30", "40", "1.0", "2.5", "3.0", "4.25"]


def test_dump_flattens_multidimensional_variable(tmp_path):
    input_file = tmp_path / "sample.nc"
    output_file = tmp_path / "reference.txt"
    _write_dataset(input_file)

    dump_variables(input_file, ["matrix"], output_file)

    assert _read_lines(output_file) == [str(value) for value in range(12)]


def test_dump_truncates_each_variable_to_first_100_values(tmp_path):
    input_file = tmp_path / "sample.nc"
    output_file = tmp_path / "reference.txt"
    _write_dataset(input_file)

    dump_variables(input_file, ["long"], output_file)

    assert _read_lines(output_file) == [str(value) for value in range(100)]


def test_missing_variable_fails_clearly(tmp_path):
    input_file = tmp_path / "sample.nc"
    output_file = tmp_path / "reference.txt"
    _write_dataset(input_file)

    with pytest.raises(ValueError, match="variable not found.*missing"):
        dump_variables(input_file, ["missing"], output_file)


def test_missing_input_file_fails_clearly(tmp_path):
    with pytest.raises(FileNotFoundError, match="input NetCDF file does not exist"):
        dump_variables(tmp_path / "missing.nc", ["one"], tmp_path / "reference.txt")


def test_cli_main_writes_output_with_comma_separated_variables(tmp_path):
    input_file = tmp_path / "sample.nc"
    output_file = tmp_path / "reference.txt"
    _write_dataset(input_file)

    main(["-i", str(input_file), "-v", "one,two", "-o", str(output_file)])

    assert _read_lines(output_file) == ["1.0", "2.5", "3.0", "4.25", "10", "20", "30", "40"]


def test_cli_main_reports_missing_file(capsys, tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        main(["-i", str(tmp_path / "missing.nc"), "-v", "one", "-o", str(tmp_path / "reference.txt")])

    assert excinfo.value.code == 2
    assert "input NetCDF file does not exist" in capsys.readouterr().err


def test_tester_dump_entry_point_is_registered():
    with open("pyproject.toml", "rb") as pyproject:
        config = tomllib.load(pyproject)

    assert config["project"]["scripts"]["tester-dump"] == "scripts.tester_dump:main"
