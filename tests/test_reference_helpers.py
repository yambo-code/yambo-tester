import numpy as np
import pytest

from yambo_tester.tests.test_reference import (
    assert_close_significant,
    normalize_reference,
    resolve_output_file,
)


def test_normalize_reference_preserves_legacy_list_syntax():
    spec = normalize_reference(["output/ndb.QP", "QP_Z"])

    assert spec == {
        "path": "output/ndb.QP",
        "variables": ["QP_Z"],
        "skip_columns": set(),
        "whitelist": False,
        "tolerance": None,
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
