# Copyright (c) 2026 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import argparse
from pathlib import Path

import netCDF4 as nc
import numpy as np


MAX_VALUES_PER_VARIABLE = 100


def parse_variables(values):
    variables = []
    for value in values:
        variables.extend(part.strip() for part in value.split(",") if part.strip())
    if not variables:
        raise ValueError("at least one variable must be provided with -v/--variable")
    return variables


def format_numeric_value(value):
    return str(value)


def dump_variables(input_file, variables, output_file, limit=MAX_VALUES_PER_VARIABLE):
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"input NetCDF file does not exist: {input_path}")

    with nc.Dataset(input_path) as dataset:
        missing = [variable for variable in variables if variable not in dataset.variables]
        if missing:
            available = ", ".join(dataset.variables.keys())
            detail = f" Available variables: {available}" if available else ""
            raise ValueError(f"variable not found in {input_path}: {missing[0]}.{detail}")

        with output_path.open("w", encoding="utf-8") as output:
            for variable in variables:
                data = np.asarray(dataset.variables[variable][:]).ravel()
                if not np.issubdtype(data.dtype, np.number):
                    raise TypeError(f"variable is not numeric: {variable}")
                for value in data[:limit]:
                    output.write(f"{format_numeric_value(value)}\n")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="tester-dump",
        description="Dump selected NetCDF variables to a minimal numeric text reference.",
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Input NetCDF file.",
    )
    parser.add_argument(
        "-v",
        "--variable",
        action="append",
        dest="variables",
        required=True,
        help="Variable to dump. Repeat the option for multiple variables; comma-separated names are also accepted.",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output text reference file to create or overwrite.",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        variables = parse_variables(args.variables)
        dump_variables(args.input, variables, args.output)
    except (FileNotFoundError, TypeError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
