# Copyright (c) 2026 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import argparse
import sys

from yambo_tester.reference_compare import (
    DEFAULT_MAX_MISMATCH_REPORTS,
    compare_reference_column_to_netcdf_variables,
    compare_text_columns,
    looks_like_netcdf_output,
    parse_variable_list,
)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="tester",
        description="Compare numeric text references with text outputs or selected NetCDF variables.",
    )
    parser.add_argument(
        "-r",
        "--reference",
        required=True,
        help="Reference text file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output text or NetCDF file to check.",
    )
    parser.add_argument(
        "--reference-column",
        "--ref-col",
        type=int,
        default=1,
        help="1-based column number to read from the reference file. Default: 1.",
    )
    parser.add_argument(
        "--output-column",
        "--out-col",
        type=int,
        default=1,
        help="1-based column number to read from text output files. Default: 1.",
    )
    parser.add_argument(
        "-v",
        "--variable",
        "--variables",
        action="append",
        dest="variables",
        help="NetCDF variable to compare. Repeat for multiple variables; comma-separated names are also accepted.",
    )
    parser.add_argument(
        "-t",
        "--tolerance",
        type=float,
        default=0.1,
        help="Relative tolerance for significant values. Default: 0.1.",
    )
    parser.add_argument(
        "--tollerance",
        type=float,
        dest="tolerance",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--max-mismatches",
        type=int,
        default=DEFAULT_MAX_MISMATCH_REPORTS,
        help=(
            "Maximum number of element-level mismatches to print. "
            f"Default: {DEFAULT_MAX_MISMATCH_REPORTS}."
        ),
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    variables = None
    if args.variables:
        try:
            variables = parse_variable_list(args.variables)
        except ValueError as exc:
            parser.error(str(exc))

    try:
        if variables is not None:
            compare_reference_column_to_netcdf_variables(
                args.reference,
                args.output,
                variables,
                args.reference_column,
                args.tolerance,
                max_mismatches=args.max_mismatches,
            )
            return 0

        if looks_like_netcdf_output(args.output):
            raise ValueError("NetCDF output comparisons require at least one variable with -v/--variable/--variables")

        compare_text_columns(
            args.reference,
            args.output,
            args.reference_column,
            args.output_column,
            args.tolerance,
            max_mismatches=args.max_mismatches,
        )
        return 0
    except (AssertionError, FileNotFoundError, IndexError, OSError, TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
