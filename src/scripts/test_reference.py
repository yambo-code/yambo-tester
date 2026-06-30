# Copyright (c) 2026 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import argparse

from yambo_tester.reference_compare import compare_text_columns


def build_parser():
    parser = argparse.ArgumentParser(
        prog="tester",
        description="Compare one numeric text column from a reference file with one column from an output file.",
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
        help="Output text file to check.",
    )
    parser.add_argument(
        "--reference-column",
        "--ref-col",
        type=int,
        required=True,
        help="1-based column number to read from the reference file.",
    )
    parser.add_argument(
        "--output-column",
        "--out-col",
        type=int,
        required=True,
        help="1-based column number to read from the output file.",
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
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        compare_text_columns(
            args.reference,
            args.output,
            args.reference_column,
            args.output_column,
            args.tolerance,
        )
    except (AssertionError, FileNotFoundError, IndexError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
