# Copyright (c) 2026 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

from pathlib import Path

import numpy as np


ZERO_DFL = 1e-6
TOO_LARGE = 10e99
SIGNIFICANCE_THRESHOLD = 1e-3


def significant_mask(ref_data, out_data):
    max_abs = np.max(np.abs(ref_data))
    threshold = max_abs * SIGNIFICANCE_THRESHOLD
    return (np.abs(ref_data) >= threshold) | (np.abs(out_data) >= threshold)


def assert_finite_output(data, label):
    assert np.all(abs(data) < TOO_LARGE) and not np.all(np.isnan(data)), f"{label}: NaN or too large number!"


def assert_close_significant(out_data, ref_data, tol, label):
    mask = significant_mask(ref_data, out_data)
    assert np.allclose(out_data[mask], ref_data[mask], rtol=tol, atol=ZERO_DFL), f"{label}: Difference larger than {tol}!"


def _count_data_rows(path):
    rows = 0
    with Path(path).open(encoding="utf-8") as data_file:
        for line in data_file:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                rows += 1
    return rows


def load_text_output_data(path):
    data = np.genfromtxt(str(path), ndmin=2)
    data_rows = _count_data_rows(path)
    if data_rows > 1 and data.shape[0] == 1 and data.shape[1] == data_rows:
        return data.T
    return data


def compare_text_output(out_file, ref_file, ref, tol, skip_columns):
    ref_data = load_text_output_data(ref_file)
    out_data = load_text_output_data(out_file)

    for col in range(1, ref_data.shape[1]):
        if col in skip_columns:
            continue
        assert_finite_output(out_data[:, col], str(out_file))
        assert_close_significant(out_data[:, col], ref_data[:, col], tol, ref)


def _validate_column_number(column, label):
    if column < 1:
        raise ValueError(f"{label} column must be a 1-based positive integer: {column}")


def selected_column(data, column, label):
    _validate_column_number(column, label)
    index = column - 1
    if index >= data.shape[1]:
        raise IndexError(f"{label} column {column} does not exist; file has {data.shape[1]} column(s)")
    return data[:, index]


def compare_text_columns(reference_file, output_file, reference_column, output_column, tolerance):
    reference_path = Path(reference_file)
    output_path = Path(output_file)

    if not reference_path.exists():
        raise FileNotFoundError(f"reference file does not exist: {reference_path}")
    if not output_path.exists():
        raise FileNotFoundError(f"output file does not exist: {output_path}")

    ref_data = load_text_output_data(reference_path)
    out_data = load_text_output_data(output_path)
    ref_column = selected_column(ref_data, reference_column, "reference")
    out_column = selected_column(out_data, output_column, "output")

    if ref_column.shape != out_column.shape:
        raise ValueError(
            "selected columns have different row counts: "
            f"reference has {ref_column.shape[0]} row(s), output has {out_column.shape[0]} row(s)"
        )

    assert_finite_output(out_column, str(output_path))
    assert_close_significant(out_column, ref_column, tolerance, str(output_path))
