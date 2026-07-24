# Tester NetCDF Support Plan

## Current implementation

`tester` is implemented in `src/scripts/test_reference.py` and is registered as `scripts.test_reference:main`. Before this feature it only compared one selected numeric column from a text reference with one selected numeric column from a text output. Column numbers are public 1-based CLI values.

The shared numeric comparison rules live in `src/yambo_tester/reference_compare.py`: text loading, column selection, finite-output checks, significance masking, and tolerance checks.

## Existing NetCDF path

The workflow validator in `src/yambo_tester/tests/test_reference.py` compares database references when `is_database_reference()` matches `.ndb.` or `.ns.` reference names. It reads variables from NetCDF with `netCDF4.Dataset`, flattens arrays with `ravel()`, and compares each variable against the matching reference slice using the same finite/significant/tolerance helpers.

`tester-dump` already uses repeatable `-v/--variable` options and accepts comma-separated names. It writes variables in requested order after flattening.

## Implementation

- Move NetCDF variable-list parsing, NetCDF opening, variable validation, flattening, and reference comparison into `reference_compare.py`.
- Keep `tester-dump` using the shared variable parser so `tester` and `tester-dump` accept the same syntax.
- Keep the workflow validator using the shared NetCDF comparison helper so there is one comparison path.
- Preserve the workflow behavior that a text reference can contain a truncated prefix per variable, as produced by `tester-dump`.
- Add output-type detection for standalone `tester`: supplied variables select NetCDF mode; otherwise files with NetCDF magic or database-style names require variables instead of guessing.

## CLI syntax

Use the `tester-dump` convention: `-v/--variable/--variables`, repeatable and comma-separated. Examples:

```bash
tester -r reference.txt -o output.txt
tester -r reference.txt -o sample.nc -v EIGENVALUES
tester -r reference.txt -o sample.nc --variables ng_in_shell,E_of_shell
```

`--reference-column/--ref-col` and `--output-column/--out-col` remain 1-based. Both default to `1`; `--output-column` applies only to text outputs.

## Tests and docs

Add regression tests for text defaults, one and multiple NetCDF variables, multidimensional flattening, variable order, explicit reference column selection, missing variables, missing variable option, invalid NetCDF files, and tolerance behavior. Update README examples and this progress file.
