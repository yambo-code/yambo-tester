# Copyright (c) 2026 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

from dataclasses import dataclass
from pathlib import Path

import netCDF4 as nc
import numpy as np


ZERO_DFL = 1e-6
TOO_LARGE = 10e99
SIGNIFICANCE_THRESHOLD = 1e-3
STDOUT_REFERENCE = "STDOUT"
NETCDF_MAGIC_HEADERS = (b"CDF", b"\x89HDF\r\n\x1a\n")
DEFAULT_MAX_MISMATCH_REPORTS = 20


@dataclass(frozen=True)
class MismatchDetail:
    flat_index: int
    reference: object
    output: object
    abs_diff: float
    rel_diff: float
    row_index: int | None = None
    column: int | None = None
    variable: str | None = None
    index: tuple[int, ...] | None = None


@dataclass(frozen=True)
class ComparisonResult:
    passed: bool
    total_elements: int
    mismatch_count: int
    mismatches: tuple[MismatchDetail, ...]
    max_reported: int

    @property
    def omitted_count(self):
        return max(self.mismatch_count - len(self.mismatches), 0)


@dataclass(frozen=True)
class NetcdfVariableData:
    name: str
    data: np.ndarray
    original_shape: tuple[int, ...]

    @property
    def shape(self):
        return self.data.shape

    def __array__(self, dtype=None):
        return np.asarray(self.data, dtype=dtype)

    def __getitem__(self, item):
        return self.data[item]


def reference_basename(reference_key):
    """
    Return the filename portion used for reference type classification.
    """
    if reference_key == STDOUT_REFERENCE:
        return STDOUT_REFERENCE
    return Path(reference_key).name


def resolve_reference_path(workflow_root, reference_key):
    """
    Return the filesystem path for a tests.toml reference key.

    ``STDOUT`` is not a reference file. Explicit relative keys such as
    ``REFERENCE/Y6/o-file`` are resolved from the workflow root. Legacy bare
    keys continue to resolve through ``REFERENCE/<key>``.
    """
    if reference_key == STDOUT_REFERENCE:
        return None

    key_path = Path(reference_key)
    if len(key_path.parts) == 1:
        return Path(workflow_root).joinpath("REFERENCE", key_path)
    return Path(workflow_root).joinpath(key_path)


def is_report_reference(reference_key):
    return reference_basename(reference_key).startswith("r-")


def is_text_output_reference(reference_key):
    basename = reference_basename(reference_key)
    return basename.startswith("o-") and not is_database_reference(reference_key)


def is_database_reference(reference_key):
    basename = reference_basename(reference_key)
    return ".ndb." in basename or ".ns." in basename


def is_netcdf_database_path(path):
    basename = Path(path).name
    return (
        basename.endswith(".nc")
        or basename.startswith(("ndb.", "ns."))
        or ".ndb." in basename
        or ".ns." in basename
    )


def has_netcdf_magic(path):
    try:
        with Path(path).open("rb") as data_file:
            header = data_file.read(8)
    except FileNotFoundError:
        raise
    except OSError:
        return False
    return any(header.startswith(magic) for magic in NETCDF_MAGIC_HEADERS)


def looks_like_netcdf_output(path):
    path = Path(path)
    return is_netcdf_database_path(path) or (path.exists() and has_netcdf_magic(path))


def parse_variable_list(values):
    variables = []
    for value in values or []:
        variables.extend(part.strip() for part in value.split(",") if part.strip())
    if not variables:
        raise ValueError("at least one NetCDF variable must be provided with -v/--variable/--variables")
    return variables


def significant_mask(ref_data, out_data):
    max_abs = np.max(np.abs(ref_data))
    threshold = max_abs * SIGNIFICANCE_THRESHOLD
    return (np.abs(ref_data) >= threshold) | (np.abs(out_data) >= threshold)


def _safe_magnitude(data):
    values = np.asarray(data)
    if np.iscomplexobj(values):
        return np.abs(values.astype(np.complex128, copy=False))
    return np.abs(values.astype(np.float64, copy=False))


def assert_finite_output(data, label):
    values = np.asarray(data)
    if not np.all(np.isfinite(values)):
        raise AssertionError(f"{label}: NaN or infinite number!")

    magnitude = _safe_magnitude(values)
    if np.any(magnitude >= TOO_LARGE):
        raise AssertionError(f"{label}: too large number!")


def _relative_difference(abs_diff, reference):
    ref_abs = abs(reference)
    if ref_abs == 0:
        return 0.0 if abs_diff == 0 else float("inf")
    return float(abs_diff / ref_abs)


def compare_significant_values(
    out_data,
    ref_data,
    tol,
    *,
    max_reported=DEFAULT_MAX_MISMATCH_REPORTS,
    row_indices=None,
    column=None,
    variable=None,
    original_shape=None,
):
    if max_reported < 0:
        raise ValueError(f"maximum mismatch report count must be non-negative: {max_reported}")

    ref_values = np.asarray(ref_data)
    out_values = np.asarray(out_data)
    if ref_values.shape != out_values.shape:
        raise ValueError(
            "comparison arrays have different shapes: "
            f"reference has {ref_values.shape}, output has {out_values.shape}"
        )

    ref_flat = ref_values.ravel()
    out_flat = out_values.ravel()
    mask = significant_mask(ref_flat, out_flat)
    close = np.isclose(out_flat[mask], ref_flat[mask], rtol=tol, atol=ZERO_DFL)
    masked_indices = np.flatnonzero(mask)
    mismatch_indices = masked_indices[~close]
    mismatch_count = int(mismatch_indices.shape[0])

    details = []
    rows = None if row_indices is None else np.asarray(row_indices).ravel()
    for flat_index in mismatch_indices[:max_reported]:
        ref_value = ref_flat[flat_index].item()
        out_value = out_flat[flat_index].item()
        abs_diff = float(abs(out_value - ref_value))
        row_index = None if rows is None else int(rows[flat_index])
        multi_index = None
        if original_shape is not None:
            multi_index = tuple(int(i) for i in np.unravel_index(int(flat_index), original_shape))
        details.append(MismatchDetail(
            flat_index=int(flat_index),
            row_index=row_index,
            column=column,
            variable=variable,
            index=multi_index,
            reference=ref_value,
            output=out_value,
            abs_diff=abs_diff,
            rel_diff=_relative_difference(abs_diff, ref_value),
        ))

    return ComparisonResult(
        passed=mismatch_count == 0,
        total_elements=int(ref_flat.shape[0]),
        mismatch_count=mismatch_count,
        mismatches=tuple(details),
        max_reported=max_reported,
    )


def _format_value(value):
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.12g}"
    return str(value)


def _format_diff(value):
    if np.isinf(value):
        return "inf"
    if np.isnan(value):
        return "nan"
    return f"{value:.6g}"


def format_comparison_diagnostics(label, result, tolerance):
    lines = [
        f"{label}: Difference larger than {tolerance}!",
        f"Comparison failed: {result.mismatch_count} of {result.total_elements} values differ beyond tolerance.",
    ]
    if result.omitted_count:
        lines.append(
            f"Showing the first {len(result.mismatches)} mismatches; "
            f"{result.omitted_count} additional mismatches were omitted."
        )

    for mismatch in result.mismatches:
        lines.append("")
        lines.append(f"Index {mismatch.flat_index}:")
        lines.append(f"  flat_index = {mismatch.flat_index}")
        if mismatch.row_index is not None:
            lines.append(f"  row_index  = {mismatch.row_index}")
        if mismatch.column is not None:
            lines.append(f"  column     = {mismatch.column}")
        if mismatch.variable is not None:
            lines.append(f"  variable   = {mismatch.variable}")
        if mismatch.index is not None:
            lines.append(f"  index      = {mismatch.index}")
        lines.append(f"  reference = {_format_value(mismatch.reference)}")
        lines.append(f"  output    = {_format_value(mismatch.output)}")
        lines.append(f"  abs_diff  = {_format_diff(mismatch.abs_diff)}")
        lines.append(f"  rel_diff  = {_format_diff(mismatch.rel_diff)}")

    return "\n".join(lines)


def assert_close_significant(out_data, ref_data, tol, label, **kwargs):
    result = compare_significant_values(out_data, ref_data, tol, **kwargs)
    if not result.passed:
        raise AssertionError(format_comparison_diagnostics(label, result, tol))


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


def compare_text_output(out_file, ref_file, ref, tol, skip_columns, max_mismatches=DEFAULT_MAX_MISMATCH_REPORTS):
    ref_data = load_text_output_data(ref_file)
    out_data = load_text_output_data(out_file)

    if ref_data.shape != out_data.shape:
        raise ValueError(
            "text files have different shapes: "
            f"reference has {ref_data.shape}, output has {out_data.shape}"
        )

    for col in range(1, ref_data.shape[1]):
        if col in skip_columns:
            continue
        assert_finite_output(out_data[:, col], str(out_file))
        assert_close_significant(
            out_data[:, col],
            ref_data[:, col],
            tol,
            ref,
            max_reported=max_mismatches,
            row_indices=np.arange(ref_data.shape[0]),
            column=col + 1,
        )


def _validate_column_number(column, label):
    if column < 1:
        raise ValueError(f"{label} column must be a 1-based positive integer: {column}")


def selected_column(data, column, label):
    _validate_column_number(column, label)
    index = column - 1
    if index >= data.shape[1]:
        raise IndexError(f"{label} column {column} does not exist; file has {data.shape[1]} column(s)")
    return data[:, index]


def compare_text_columns(
    reference_file,
    output_file,
    reference_column,
    output_column,
    tolerance,
    max_mismatches=DEFAULT_MAX_MISMATCH_REPORTS,
):
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
    assert_close_significant(
        out_column,
        ref_column,
        tolerance,
        str(output_path),
        max_reported=max_mismatches,
        row_indices=np.arange(ref_column.shape[0]),
        column=output_column,
    )


def _open_netcdf_dataset(path):
    try:
        return nc.Dataset(str(path))
    except OSError as exc:
        raise OSError(f"cannot open NetCDF file: {path}") from exc


def load_netcdf_variable_data(output_file, variables):
    output_path = Path(output_file)
    if not output_path.exists():
        raise FileNotFoundError(f"output NetCDF file does not exist: {output_path}")
    if not variables:
        raise ValueError("at least one NetCDF variable must be provided with -v/--variable/--variables")

    with _open_netcdf_dataset(output_path) as dataset:
        missing = [variable for variable in variables if variable not in dataset.variables]
        if missing:
            available = ", ".join(dataset.variables.keys())
            detail = f" Available variables: {available}" if available else ""
            raise ValueError(f"variable not found in {output_path}: {missing[0]}.{detail}")

        variable_data = []
        for variable in variables:
            raw_data = np.asarray(dataset.variables[variable][:])
            if not np.issubdtype(raw_data.dtype, np.number):
                raise TypeError(f"variable is not numeric: {variable}")
            variable_data.append(NetcdfVariableData(variable, raw_data.ravel(), raw_data.shape))
        return variable_data


def compare_reference_column_to_netcdf_variables(
    reference_file,
    output_file,
    variables,
    reference_column,
    tolerance,
    label=None,
    max_mismatches=DEFAULT_MAX_MISMATCH_REPORTS,
):
    reference_path = Path(reference_file)
    output_path = Path(output_file)

    if not reference_path.exists():
        raise FileNotFoundError(f"reference file does not exist: {reference_path}")

    ref_data = load_text_output_data(reference_path)
    ref_column = selected_column(ref_data, reference_column, "reference")
    variable_data = load_netcdf_variable_data(output_path, variables)

    nvars = len(variable_data)
    if ref_column.shape[0] % nvars != 0:
        raise ValueError(
            "reference row count is not divisible by the number of NetCDF variables: "
            f"{ref_column.shape[0]} row(s), {nvars} variable(s)"
        )

    rows_per_variable = ref_column.shape[0] // nvars
    for index, variable_info in enumerate(variable_data):
        start = index * rows_per_variable
        stop = start + rows_per_variable
        expected = ref_column[start:stop]
        if variable_info.shape[0] < expected.shape[0]:
            raise ValueError(
                f"NetCDF variable {variables[index]} has {variable_info.shape[0]} value(s), "
                f"reference expects {expected.shape[0]}"
            )
        actual = variable_info[:expected.shape[0]]
        comparison_label = label or str(output_path)
        assert_finite_output(actual, str(output_path))
        assert_close_significant(
            actual,
            expected,
            tolerance,
            comparison_label,
            max_reported=max_mismatches,
            row_indices=np.arange(start, stop),
            variable=variable_info.name,
            original_shape=variable_info.original_shape,
        )
