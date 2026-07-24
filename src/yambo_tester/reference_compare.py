# Copyright (c) 2026 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

from pathlib import Path

import netCDF4 as nc
import numpy as np


ZERO_DFL = 1e-6
TOO_LARGE = 10e99
SIGNIFICANCE_THRESHOLD = 1e-3
STDOUT_REFERENCE = "STDOUT"
NETCDF_MAGIC_HEADERS = (b"CDF", b"\x89HDF\r\n\x1a\n")


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
            data = np.asarray(dataset.variables[variable][:]).ravel()
            if not np.issubdtype(data.dtype, np.number):
                raise TypeError(f"variable is not numeric: {variable}")
            variable_data.append(data)
        return variable_data


def compare_reference_column_to_netcdf_variables(
    reference_file,
    output_file,
    variables,
    reference_column,
    tolerance,
    label=None,
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
    for index, data in enumerate(variable_data):
        start = index * rows_per_variable
        stop = start + rows_per_variable
        expected = ref_column[start:stop]
        if data.shape[0] < expected.shape[0]:
            raise ValueError(
                f"NetCDF variable {variables[index]} has {data.shape[0]} value(s), "
                f"reference expects {expected.shape[0]}"
            )
        actual = data[:expected.shape[0]]
        comparison_label = label or str(output_path)
        assert_finite_output(actual, str(output_path))
        assert_close_significant(actual, expected, tolerance, comparison_label)
