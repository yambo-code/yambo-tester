import tomllib

import pytest

from scripts.test_reference import build_parser, main
from yambo_tester.reference_compare import compare_text_columns


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


def test_cli_main_reports_difference(capsys, tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "output.txt"
    reference.write_text("1 10.0\n")
    output.write_text("1 12.0\n")

    with pytest.raises(SystemExit) as excinfo:
        main(["-r", str(reference), "-o", str(output), "--ref-col", "2", "--out-col", "2"])

    assert excinfo.value.code == 2
    assert "Difference larger than 0.1" in capsys.readouterr().err


def test_cli_main_accepts_long_column_options(tmp_path):
    reference = tmp_path / "reference.txt"
    output = tmp_path / "output.txt"
    reference.write_text("1 10.0\n")
    output.write_text("1 10.5\n")

    main([
        "--reference",
        str(reference),
        "--output",
        str(output),
        "--reference-column",
        "2",
        "--output-column",
        "2",
    ])


def test_help_documents_column_numbering():
    help_text = build_parser().format_help()

    assert "--reference-column" in help_text
    assert "--output-column" in help_text
    assert "1-based column number" in help_text


def test_tester_entry_point_is_registered():
    with open("pyproject.toml", "rb") as pyproject:
        config = tomllib.load(pyproject)

    assert config["project"]["scripts"]["tester"] == "scripts.test_reference:main"
