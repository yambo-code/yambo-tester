import tomllib
import warnings

import netCDF4 as nc
import numpy as np
import pytest

from scripts.test_reference import build_parser, main
from yambo_tester.reference_compare import compare_reference_column_to_netcdf_variables, compare_text_columns, is_text_output_reference


def _write_netcdf(path):
    with nc.Dataset(path, "w") as dataset:
        dataset.createDimension("x", 4)
        dataset.createDimension("y", 3)

        one = dataset.createVariable("one", "f8", ("x",))
        one[:] = [1.0, 2.0, 3.0, 4.0]

        two = dataset.createVariable("two", "f8", ("x",))
        two[:] = [10.0, 20.0, 30.0, 40.0]

        matrix = dataset.createVariable("matrix", "i4", ("x", "y"))
        matrix[:, :] = np.arange(12).reshape(4, 3)


def _write_text(path, values):
    path.write_text("\n".join(str(value) for value in values) + "\n")


def test_tester_shares_path_like_reference_classification():
    assert is_text_output_reference("REFERENCE/Y6/o-02_QP.qp")


def test_compare_selected_columns_within_tolerance(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "output.txt"
    reference.write_text("1 10.0\n2 20.0\n")
    output.write_text("1 10.5\n2 19.5\n")

    compare_text_columns(reference, output, 2, 2, 0.1)


def test_compare_selected_columns_fails_beyond_tolerance(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "output.txt"
    reference.write_text("1 10.0\n2 20.0\n")
    output.write_text("1 10.0\n2 30.0\n")

    with pytest.raises(AssertionError, match="Difference larger than 0.1"):
        compare_text_columns(reference, output, 2, 2, 0.1)


def test_compare_different_reference_and_output_columns(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "output.txt"
    reference.write_text("1 10.0 99.0\n2 20.0 88.0\n")
    output.write_text("1 77.0 10.5\n2 66.0 19.5\n")

    compare_text_columns(reference, output, 2, 3, 0.1)


def test_compare_one_row_input_files(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "output.txt"
    reference.write_text("1 10.0 20.0\n")
    output.write_text("1 10.5 19.5\n")

    compare_text_columns(reference, output, 3, 3, 0.1)


def test_compare_one_column_input_files(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "output.txt"
    reference.write_text("10.0\n20.0\n")
    output.write_text("10.5\n19.5\n")

    compare_text_columns(reference, output, 1, 1, 0.1)


def test_compare_one_column_input_files_checks_all_rows(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "output.txt"
    reference.write_text("10.0\n20.0\n")
    output.write_text("10.5\n30.0\n")

    with pytest.raises(AssertionError, match="Difference larger than 0.1"):
        compare_text_columns(reference, output, 1, 1, 0.1)


def test_compare_one_row_one_column_input_files(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "output.txt"
    reference.write_text("10.0\n")
    output.write_text("10.5\n")

    compare_text_columns(reference, output, 1, 1, 0.1)


def test_invalid_column_index_fails_clearly(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "output.txt"
    reference.write_text("1 10.0\n")
    output.write_text("1 10.0\n")

    with pytest.raises(IndexError, match="reference column 3 does not exist; file has 2 column"):
        compare_text_columns(reference, output, 3, 2, 0.1)


def test_zero_column_index_fails_clearly(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "output.txt"
    reference.write_text("1 10.0\n")
    output.write_text("1 10.0\n")

    with pytest.raises(ValueError, match="reference column must be a 1-based positive integer: 0"):
        compare_text_columns(reference, output, 0, 2, 0.1)


def test_missing_input_file_fails_clearly(tmp_path):
    output = tmp_path / "output.txt"
    output.write_text("1 10.0\n")

    with pytest.raises(FileNotFoundError, match="reference file does not exist"):
        compare_text_columns(tmp_path / "missing.txt", output, 1, 1, 0.1)


def test_row_count_mismatch_fails_clearly(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "output.txt"
    reference.write_text("10.0\n20.0\n")
    output.write_text("10.0\n")

    with pytest.raises(ValueError, match="different row counts: reference has 2 row"):
        compare_text_columns(reference, output, 1, 1, 0.1)


def test_cli_main_reports_difference_without_usage(capsys, tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "output.txt"
    reference.write_text("1 10.0\n")
    output.write_text("1 12.0\n")

    exit_code = main(["-r", str(reference), "-o", str(output), "--ref-col", "2", "--out-col", "2"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "Difference larger than 0.1" in captured.err
    assert "usage:" not in captured.err


def test_cli_main_accepts_long_column_options(capsys, tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "output.txt"
    reference.write_text("1 10.0\n")
    output.write_text("1 10.5\n")

    exit_code = main([
        "--reference",
        str(reference),
        "--output",
        str(output),
        "--reference-column",
        "2",
        "--output-column",
        "2",
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""


def test_help_documents_column_numbering():
    help_text = build_parser().format_help()

    assert "--reference-column" in help_text
    assert "--output-column" in help_text
    assert "1-based column number" in help_text


def test_cli_main_uses_first_columns_by_default_for_text_outputs(capsys, tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "output.txt"
    reference.write_text("10.0 1.0\n20.0 2.0\n")
    output.write_text("10.5 99.0\n19.5 88.0\n")

    exit_code = main(["-r", str(reference), "-o", str(output)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""


def test_compare_netcdf_one_variable(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "sample.nc"
    _write_text(reference, [1.0, 2.0, 3.0, 4.0])
    _write_netcdf(output)

    compare_reference_column_to_netcdf_variables(reference, output, ["one"], 1, 0.1)


def test_compare_netcdf_multiple_variables_in_requested_order(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "sample.nc"
    _write_text(reference, [10.0, 20.0, 30.0, 40.0, 1.0, 2.0, 3.0, 4.0])
    _write_netcdf(output)

    compare_reference_column_to_netcdf_variables(reference, output, ["two", "one"], 1, 0.1)


def test_compare_netcdf_variable_order_is_preserved(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "sample.nc"
    _write_text(reference, [10.0, 20.0, 30.0, 40.0, 1.0, 2.0, 3.0, 4.0])
    _write_netcdf(output)

    with pytest.raises(AssertionError, match="Difference larger than 0.1"):
        compare_reference_column_to_netcdf_variables(reference, output, ["one", "two"], 1, 0.1)


def test_compare_netcdf_flattens_multidimensional_variable(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "sample.nc"
    _write_text(reference, range(12))
    _write_netcdf(output)

    compare_reference_column_to_netcdf_variables(reference, output, ["matrix"], 1, 0.1)


def test_cli_netcdf_uses_first_reference_column_by_default(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "sample.nc"
    reference.write_text("1.0 99.0\n2.0 88.0\n3.0 77.0\n4.0 66.0\n")
    _write_netcdf(output)

    main(["-r", str(reference), "-o", str(output), "--variables", "one"])


def test_cli_netcdf_accepts_explicit_reference_column(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "sample.nc"
    reference.write_text("99.0 1.0\n88.0 2.0\n77.0 3.0\n66.0 4.0\n")
    _write_netcdf(output)

    main(["-r", str(reference), "-o", str(output), "-v", "one", "--ref-col", "2"])


def test_cli_netcdf_accepts_repeated_and_comma_separated_variables(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "sample.nc"
    _write_text(reference, [1.0, 2.0, 3.0, 4.0, 10.0, 20.0, 30.0, 40.0])
    _write_netcdf(output)

    main(["-r", str(reference), "-o", str(output), "-v", "one,two"])


def test_missing_netcdf_variable_fails_clearly(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "sample.nc"
    _write_text(reference, [1.0, 2.0, 3.0, 4.0])
    _write_netcdf(output)

    with pytest.raises(ValueError, match="variable not found.*missing"):
        compare_reference_column_to_netcdf_variables(reference, output, ["missing"], 1, 0.1)


def test_cli_reports_missing_variable_option_for_netcdf_output_without_usage(capsys, tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "sample.nc"
    _write_text(reference, [1.0, 2.0, 3.0, 4.0])
    _write_netcdf(output)

    exit_code = main(["-r", str(reference), "-o", str(output)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "NetCDF output comparisons require" in captured.err
    assert "usage:" not in captured.err


def test_invalid_netcdf_file_fails_clearly_without_usage(capsys, tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "broken.nc"
    _write_text(reference, [1.0])
    output.write_text("not a NetCDF file\n")

    exit_code = main(["-r", str(reference), "-o", str(output), "-v", "one"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "cannot open NetCDF file" in captured.err
    assert "usage:" not in captured.err


def test_netcdf_tolerance_matches_shared_significant_comparison(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "sample.nc"
    _write_text(reference, [1.0, 2.0, 3.0, 4.0])
    _write_netcdf(output)

    compare_reference_column_to_netcdf_variables(reference, output, ["one"], 1, 0.1)

    _write_text(reference, [1.0, 2.0, 3.0, 5.0])
    with pytest.raises(AssertionError, match="Difference larger than 0.1"):
        compare_reference_column_to_netcdf_variables(reference, output, ["one"], 1, 0.1)


def test_cli_netcdf_sx_vxc_float32_multiple_variables_emit_no_runtime_warning(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "ndb.HF_and_locXC"
    reference.write_text("0.0\n0.77977\n0.6380773\n0.0\n")
    with nc.Dataset(output, "w") as dataset:
        dataset.createDimension("x", 2)
        sx = dataset.createVariable("Sx", "f4", ("x",))
        sx[:] = [0.0, 0.77977]
        vxc = dataset.createVariable("Vxc", "f4", ("x",))
        vxc[:] = [0.6380773, 0.0]

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        exit_code = main(["-r", str(reference), "-o", str(output), "-v", "Sx", "-v", "Vxc"])

    runtime_warnings = [warning for warning in recorded if issubclass(warning.category, RuntimeWarning)]
    assert exit_code == 0
    assert runtime_warnings == []


def test_cli_missing_required_argument_uses_argparse_usage(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["-r", "reference.txt"])

    captured = capsys.readouterr()
    assert excinfo.value.code == 2
    assert "usage:" in captured.err
    assert "the following arguments are required: -o/--output" in captured.err


def test_cli_unknown_option_uses_argparse_usage(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["-r", "reference.txt", "-o", "output.txt", "--unknown"])

    captured = capsys.readouterr()
    assert excinfo.value.code == 2
    assert "usage:" in captured.err
    assert "unrecognized arguments: --unknown" in captured.err


def test_cli_missing_output_file_reports_runtime_error_without_usage(capsys, tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "missing.txt"
    reference.write_text("1.0\n")

    exit_code = main(["-r", str(reference), "-o", str(output)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "output file does not exist" in captured.err
    assert "usage:" not in captured.err


def test_cli_missing_netcdf_variable_reports_runtime_error_without_usage(capsys, tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "sample.nc"
    _write_text(reference, [1.0, 2.0, 3.0, 4.0])
    _write_netcdf(output)

    exit_code = main(["-r", str(reference), "-o", str(output), "-v", "missing"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "variable not found" in captured.err
    assert "usage:" not in captured.err


def test_tester_entry_point_is_registered():
    with open("pyproject.toml", "rb") as pyproject:
        config = tomllib.load(pyproject)

    assert config["project"]["scripts"]["tester"] == "scripts.test_reference:main"
