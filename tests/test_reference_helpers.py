import warnings

import numpy as np
import pytest

from yambo_tester.reference_compare import (
    DEFAULT_MAX_MISMATCH_REPORTS,
    TOO_LARGE,
    compare_significant_values,
    format_comparison_diagnostics,
    assert_finite_output,
    is_database_reference,
    is_report_reference,
    is_text_output_reference,
    reference_basename,
    resolve_reference_path,
)
from yambo_tester.tests.test_reference import (
    assert_file_contains,
    assert_close_significant,
    compare_text_output,
    load_text_output_data,
    normalize_reference,
    resolve_output_file,
    assert_stdout_or_log_contains,
    test_reference_ok as reference_test_reference_ok,
    test_runs_ok as reference_test_runs_ok,
)
from yambo_tester.log import setup_test_logger
from yambo_tester.selection import RUNLEVEL_FILTER_RETURNCODE, UNSUPPORTED_VERSION_RETURNCODE


def test_comparison_result_reports_mismatch_details():
    ref = np.array([1.0, 2.0, 3.0])
    out = np.array([1.0, 3.0, 6.0])

    result = compare_significant_values(out, ref, 0.1, row_indices=[10, 11, 12], column=2)

    assert result.passed is False
    assert result.total_elements == 3
    assert result.mismatch_count == 2
    assert [item.flat_index for item in result.mismatches] == [1, 2]
    assert [item.row_index for item in result.mismatches] == [11, 12]
    assert result.mismatches[0].column == 2
    assert result.mismatches[0].reference == 2.0
    assert result.mismatches[0].output == 3.0
    assert result.mismatches[0].abs_diff == 1.0
    assert result.mismatches[0].rel_diff == 0.5


def test_comparison_result_passes_within_tolerance():
    ref = np.array([10.0, 20.0])
    out = np.array([10.5, 19.5])

    result = compare_significant_values(out, ref, 0.1)

    assert result.passed is True
    assert result.mismatch_count == 0
    assert result.mismatches == ()


def test_comparison_result_uses_same_significant_mask_as_assertion():
    ref = np.array([3.014e-6, 10.0])
    out = np.array([1.311e-6, 12.0])

    result = compare_significant_values(out, ref, 0.1)

    assert result.passed is False
    assert [item.flat_index for item in result.mismatches] == [1]
    with pytest.raises(AssertionError, match="Comparison failed: 1 of 2"):
        assert_close_significant(out, ref, 0.1, "consistent")


def test_comparison_diagnostics_limit_reported_mismatches():
    ref = np.ones(25)
    out = np.arange(25, dtype=float) + 10.0

    result = compare_significant_values(out, ref, 0.1, max_reported=3)
    report = format_comparison_diagnostics("limited", result, 0.1)

    assert result.mismatch_count == 25
    assert len(result.mismatches) == 3
    assert "Comparison failed: 25 of 25 values" in report
    assert "Showing the first 3 mismatches; 22 additional mismatches were omitted." in report


def test_comparison_result_handles_scalar_values():
    result = compare_significant_values(np.array(2.0), np.array(1.0), 0.1)

    assert result.total_elements == 1
    assert result.mismatch_count == 1
    assert result.mismatches[0].flat_index == 0


def test_comparison_result_preserves_reference_nan_semantics():
    ref = np.array([np.nan, 1.0])
    out = np.array([2.0, 1.0])

    result = compare_significant_values(out, ref, 0.1)

    assert result.passed is True
    assert result.mismatch_count == 0


def test_comparison_result_reports_infinity_mismatch_like_allclose():
    ref = np.array([1.0])
    out = np.array([np.inf])

    result = compare_significant_values(out, ref, 0.1)

    assert result.passed is False
    assert result.mismatches[0].abs_diff == float("inf")


def test_default_mismatch_report_limit_is_named_constant():
    result = compare_significant_values(np.arange(30.0), np.ones(30), 0.1)

    assert result.max_reported == DEFAULT_MAX_MISMATCH_REPORTS
    assert len(result.mismatches) == DEFAULT_MAX_MISMATCH_REPORTS


def test_resolve_reference_path_preserves_stdout_special_case(tmp_path):
    assert resolve_reference_path(tmp_path, "STDOUT") is None


def test_resolve_reference_path_uses_explicit_relative_key(tmp_path):
    assert (
        resolve_reference_path(tmp_path, "REFERENCE/Y6/o-02_HF.ndb.SE_Fock")
        == tmp_path / "REFERENCE" / "Y6" / "o-02_HF.ndb.SE_Fock"
    )


def test_resolve_reference_path_keeps_legacy_bare_key_compatibility(tmp_path):
    assert resolve_reference_path(tmp_path, "o-02_HF.hf") == tmp_path / "REFERENCE" / "o-02_HF.hf"


def test_reference_type_detection_uses_basename_for_path_like_keys():
    assert reference_basename("REFERENCE/Y6/o-02_HF.ndb.SE_Fock") == "o-02_HF.ndb.SE_Fock"
    assert is_text_output_reference("REFERENCE/Y6/o-02_HF.hf")
    assert is_report_reference("REFERENCE/Y5/r-01_init_setup")
    assert is_database_reference("REFERENCE/Y6/o-02_HF.ndb.SE_Fock")
    assert is_database_reference("REFERENCE/Y5/o-00_p2y.ns.db1")
    assert not is_database_reference("STDOUT")


def test_normalize_reference_preserves_legacy_list_syntax():
    spec = normalize_reference(["output/ndb.QP", "QP_Z"])

    assert spec == {
        "path": "output/ndb.QP",
        "variables": ["QP_Z"],
        "skip_columns": set(),
        "whitelist": False,
        "tolerance": None,
        "contains": None,
    }


def test_normalize_reference_reads_metadata_table_syntax():
    spec = normalize_reference({
        "path": "02_Lifetimes/o-02_Lifetimes.qp",
        "skip_columns": [5],
        "whitelist": True,
        "tolerance": 0.11,
    })

    assert spec == {
        "path": "02_Lifetimes/o-02_Lifetimes.qp",
        "variables": [],
        "skip_columns": {4},
        "whitelist": True,
        "tolerance": 0.11,
        "contains": None,
    }


def test_significant_comparison_ignores_tiny_relative_noise():
    ref = np.array([3.014e-6, 100.0])
    out = np.array([1.311e-6, 100.0])

    assert_close_significant(out, ref, 0.1, "small-noise")


def test_significant_comparison_fails_large_values():
    ref = np.array([10.0])
    out = np.array([12.0])

    with pytest.raises(AssertionError):
        assert_close_significant(out, ref, 0.1, "large-diff")


def _assert_no_runtime_warning(func, *args, **kwargs):
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        func(*args, **kwargs)

    runtime_warnings = [warning for warning in recorded if issubclass(warning.category, RuntimeWarning)]
    assert runtime_warnings == []


def test_finite_output_accepts_valid_float32_without_runtime_warning():
    data = np.array([0.0, 1.0, np.finfo(np.float32).max], dtype=np.float32)

    _assert_no_runtime_warning(assert_finite_output, data, "float32")


def test_finite_output_accepts_valid_float64_without_runtime_warning():
    data = np.array([0.0, 1.0, TOO_LARGE * 0.99], dtype=np.float64)

    _assert_no_runtime_warning(assert_finite_output, data, "float64")


def test_finite_output_accepts_valid_complex64_without_runtime_warning():
    value = np.finfo(np.float32).max / 4
    data = np.array([1.0 + 2.0j, value + value * 1j], dtype=np.complex64)

    _assert_no_runtime_warning(assert_finite_output, data, "complex64")


def test_finite_output_accepts_valid_complex128_without_runtime_warning():
    data = np.array([1.0 + 2.0j, (TOO_LARGE * 0.25) + (TOO_LARGE * 0.25j)], dtype=np.complex128)

    _assert_no_runtime_warning(assert_finite_output, data, "complex128")


def test_finite_output_rejects_nan_values():
    with pytest.raises(AssertionError, match="NaN or infinite number"):
        assert_finite_output(np.array([1.0, np.nan]), "nan-data")


def test_finite_output_rejects_positive_and_negative_infinity():
    with pytest.raises(AssertionError, match="NaN or infinite number"):
        assert_finite_output(np.array([np.inf, -np.inf]), "inf-data")


def test_finite_output_rejects_complex_nan_and_infinity():
    with pytest.raises(AssertionError, match="NaN or infinite number"):
        assert_finite_output(np.array([1.0 + np.nan * 1j, np.inf + 1j]), "complex-invalid")


def test_finite_output_rejects_excessive_finite_values():
    with pytest.raises(AssertionError, match="too large number"):
        assert_finite_output(np.array([TOO_LARGE * 2], dtype=np.float64), "large-data")


def test_text_output_loader_preserves_one_row_multiple_columns(tmp_path):
    data_file = tmp_path / "o-single-row.qp"
    data_file.write_text("1 10.0 20.0\n")

    data = load_text_output_data(data_file)

    assert data.shape == (1, 3)


def test_compare_text_output_handles_one_row_multiple_columns(tmp_path):
    ref_file = tmp_path / "ref.dat"
    out_file = tmp_path / "out.dat"
    ref_file.write_text("1 10.0 20.0\n")
    out_file.write_text("1 10.5 19.5\n")

    compare_text_output(out_file, ref_file, "o-single-row.qp", 0.1, set())


def test_compare_text_output_skips_one_row_column(tmp_path):
    ref_file = tmp_path / "ref.dat"
    out_file = tmp_path / "out.dat"
    ref_file.write_text("1 10.0 20.0\n")
    out_file.write_text("1 10.0 99.0\n")

    compare_text_output(out_file, ref_file, "o-single-row.qp", 0.1, {2})


def test_compare_text_output_handles_one_row_one_column(tmp_path):
    ref_file = tmp_path / "ref.dat"
    out_file = tmp_path / "out.dat"
    ref_file.write_text("1\n")
    out_file.write_text("2\n")

    compare_text_output(out_file, ref_file, "o-single-value.qp", 0.1, set())


def test_compare_text_output_handles_multiple_rows_one_column(tmp_path):
    ref_file = tmp_path / "ref.dat"
    out_file = tmp_path / "out.dat"
    ref_file.write_text("1\n2\n")
    out_file.write_text("3\n4\n")

    compare_text_output(out_file, ref_file, "o-one-column.qp", 0.1, set())


def test_compare_text_output_still_fails_multi_row_difference(tmp_path):
    ref_file = tmp_path / "ref.dat"
    out_file = tmp_path / "out.dat"
    ref_file.write_text("1 10.0\n2 20.0\n")
    out_file.write_text("1 10.0\n2 30.0\n")

    with pytest.raises(AssertionError):
        compare_text_output(out_file, ref_file, "o-multi-row.qp", 0.1, set())


def test_workflow_reference_failure_logs_diagnostics_to_tester_log(tmp_path):
    reference_dir = tmp_path / "REFERENCE"
    output_dir = tmp_path / "output"
    reference_dir.mkdir()
    output_dir.mkdir()
    (reference_dir / "o-fail.qp").write_text("1 10.0\n2 20.0\n")
    (output_dir / "o-fail.qp").write_text("1 10.0\n2 30.0\n")
    logger = setup_test_logger(tmp_path)

    with pytest.raises(AssertionError):
        reference_test_reference_ok(("o-fail.qp", {
            "out": "o-fail.qp",
            "path": "",
            "variables": [],
            "skip_columns": set(),
            "whitelist": False,
            "exe": "yambo",
            "stdout": "",
            "run_dir": str(tmp_path),
            "dir": str(tmp_path),
            "tol": 0.1,
            "odir": "output",
            "contains": None,
            "skip": False,
        }))

    for handler in logger.handlers:
        handler.flush()
    log_text = (tmp_path / "tester.log").read_text()
    assert "Comparison failed: 1 of 2 values differ beyond tolerance." in log_text
    assert "Index 1:" in log_text
    assert "reference = 20" in log_text
    assert "output    = 30" in log_text


def test_resolve_output_file_uses_reference_basename_for_explicit_key_without_path(tmp_path):
    assert (
        resolve_output_file(tmp_path, "02_QP", "REFERENCE/Y6/o-02_QP.qp", "")
        == tmp_path / "02_QP" / "o-02_QP.qp"
    )


def test_resolve_output_file_uses_output_directory_for_bare_paths(tmp_path):
    assert resolve_output_file(tmp_path, "02_QP", "o-02_QP.qp", "o-02_QP.qp") == tmp_path / "02_QP" / "o-02_QP.qp"


def test_resolve_output_file_preserves_explicit_relative_paths(tmp_path):
    assert resolve_output_file(tmp_path, "02_QP", "o-02_QP.qp", "02_QP/o-02_QP.qp") == tmp_path / "02_QP" / "o-02_QP.qp"


def test_resolve_output_file_uses_stdout_file(tmp_path):
    assert resolve_output_file(tmp_path, "", "STDOUT", "01_p2y.stdout") == tmp_path / "01_p2y.stdout"


def test_stdout_reference_checks_expected_string_from_stdout_without_log(tmp_path):
    stdout_file = tmp_path / "01_p2y.stdout"
    stdout_file.write_text("setup\n== P2Y completed ==\n")

    reference_test_reference_ok(("STDOUT", {
        "out": ["== P2Y completed =="],
        "path": "01_p2y.stdout",
        "variables": [],
        "skip_columns": set(),
        "whitelist": False,
        "exe": "p2y",
        "stdout": "setup\n== P2Y completed ==\n",
        "run_dir": str(tmp_path),
        "dir": str(tmp_path),
        "tol": 0.1,
        "odir": "",
        "contains": "== P2Y completed ==",
        "skip": False,
    }))


def test_stdout_reference_checks_expected_string_from_log_when_stdout_missing(tmp_path):
    stdout_file = tmp_path / "01_p2y.stdout"
    stdout_file.write_text("setup\n")
    (tmp_path / "l_p2y").write_text("<--->  == P2Y completed ==\n")

    reference_test_reference_ok(("STDOUT", {
        "out": ["== P2Y completed =="],
        "path": "01_p2y.stdout",
        "variables": [],
        "skip_columns": set(),
        "whitelist": False,
        "exe": "p2y",
        "stdout": "setup\n",
        "run_dir": str(tmp_path),
        "dir": str(tmp_path),
        "tol": 0.1,
        "odir": "",
        "contains": "== P2Y completed ==",
        "skip": False,
    }))


def test_a2y_stdout_reference_checks_completion_marker_from_log_when_stdout_empty(tmp_path):
    marker = "== Writing DB2 (wavefunctions) + nlPP ..."
    stdout_file = tmp_path / "01_a2y.stdout"
    stdout_file.write_text("")
    (tmp_path / "l_a2y").write_text(f"<--->  {marker}\n")

    reference_test_reference_ok(("STDOUT", {
        "out": [marker],
        "path": "01_a2y.stdout",
        "variables": [],
        "skip_columns": set(),
        "whitelist": False,
        "exe": "a2y",
        "stdout": "",
        "run_dir": str(tmp_path),
        "dir": str(tmp_path),
        "tol": 0.1,
        "odir": "",
        "contains": marker,
        "skip": False,
    }))


def test_stdout_reference_fails_when_string_is_missing_from_both_sources(tmp_path):
    stdout_file = tmp_path / "01_p2y.stdout"
    stdout_file.write_text("setup\n")

    with pytest.raises(AssertionError):
        reference_test_reference_ok(("STDOUT", {
            "out": ["== P2Y completed =="],
            "path": "01_p2y.stdout",
            "variables": [],
            "skip_columns": set(),
            "whitelist": False,
            "exe": "p2y",
            "stdout": "setup\n",
            "run_dir": str(tmp_path),
            "dir": str(tmp_path),
            "tol": 0.1,
            "odir": "",
            "contains": "== P2Y completed ==",
            "skip": False,
        }))


def test_report_reference_can_check_expected_string(tmp_path):
    out_dir = tmp_path / "01_init"
    out_dir.mkdir()
    report = out_dir / "r-01_init_setup"
    report.write_text("calculation ok\nGame Over & Game summary\nexpected report marker\n")

    reference_test_reference_ok(("r-01_init_setup", {
        "out": ["expected report marker"],
        "path": "",
        "variables": [],
        "skip_columns": set(),
        "whitelist": False,
        "dir": str(tmp_path),
        "tol": 0.1,
        "odir": "01_init",
        "contains": "expected report marker",
        "skip": False,
    }))


def test_file_contains_fails_when_string_is_missing(tmp_path):
    output = tmp_path / "STDOUT"
    output.write_text("different output\n")

    with pytest.raises(AssertionError):
        assert_file_contains(output, "== P2Y completed ==", "STDOUT")


def test_stdout_or_log_contains_passes_with_log_only(tmp_path):
    (tmp_path / "l_p2y").write_text("work\n== P2Y completed ==\n")

    assert_stdout_or_log_contains(
        "setup\n",
        tmp_path,
        "p2y",
        "== P2Y completed ==",
        "STDOUT",
    )


def test_stdout_or_log_contains_fails_when_missing_from_both(tmp_path):
    with pytest.raises(AssertionError):
        assert_stdout_or_log_contains(
            "setup\n",
            tmp_path,
            "p2y",
            "== P2Y completed ==",
            "STDOUT",
        )


def test_runs_ok_skips_runlevel_filtered_steps():
    with pytest.raises(pytest.skip.Exception):
        reference_test_runs_ok(("02_qp", {"returncode": RUNLEVEL_FILTER_RETURNCODE}))


def test_runs_ok_skips_unsupported_version_steps():
    with pytest.raises(pytest.skip.Exception):
        reference_test_runs_ok(("02_qp", {"returncode": UNSUPPORTED_VERSION_RETURNCODE}))
