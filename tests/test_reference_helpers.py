import numpy as np
import pytest

from yambo_tester.tests.test_reference import (
    assert_file_contains,
    assert_close_significant,
    normalize_reference,
    resolve_output_file,
    assert_stdout_or_log_contains,
    test_reference_ok as reference_test_reference_ok,
    test_runs_ok as reference_test_runs_ok,
)
from yambo_tester.selection import RUNLEVEL_FILTER_RETURNCODE, UNSUPPORTED_VERSION_RETURNCODE


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
