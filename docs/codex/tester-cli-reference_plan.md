# Tester CLI Reference Comparison Plan

## Summary

Update `src/scripts/test_reference.py`, exposed as `tester`, into a focused
numeric text-column comparison helper. The CLI should stay lightweight while
using the same comparison rules as `src/yambo_tester/tests/test_reference.py`.

The intended interface is:

```bash
tester --reference reference.txt --output output.txt --reference-column 2 --output-column 3
tester -r reference.txt -o output.txt --ref-col 2 --out-col 3
```

Column numbers are 1-based, matching the existing `skip_columns` convention in
`tests.toml` and the project documentation.

## Implementation Changes

- Move reusable comparison primitives from `src/yambo_tester/tests/test_reference.py`
  into a non-pytest module such as `src/yambo_tester/reference_compare.py`.
- Keep the workflow validator behavior unchanged by importing those helpers back
  into `src/yambo_tester/tests/test_reference.py`.
- Replace the old `tester` script behavior that tries to infer reports, text
  outputs, databases, and run directories with a dedicated text-column comparator.
- Reuse the current validator rules:
  - `numpy.genfromtxt(..., ndmin=2)` for robust one-row and one-column loading.
  - finite and too-large output checks.
  - significance masking with the existing threshold.
  - `numpy.allclose(..., rtol=tolerance, atol=1e-6)`.
- Support different selected columns in the reference and output files.
- Validate file existence before reading and report clear `argparse` errors.
- Validate column indexes before comparison and report the available column count.

## CLI Interface

- `-r, --reference PATH`: reference text file.
- `-o, --output PATH`: output text file to check.
- `--reference-column, --ref-col N`: 1-based column in the reference file.
- `--output-column, --out-col N`: 1-based column in the output file.
- `-t, --tolerance FLOAT`: relative tolerance, default `0.1`.
- Keep `--tollerance` as a hidden deprecated alias for compatibility with the old
  misspelled option.

## Tests

Add focused tests for `scripts.test_reference` covering:

- Successful comparison when selected columns match within tolerance.
- Failure when selected columns differ beyond tolerance.
- Comparison using different reference and output column numbers.
- One-row input files.
- One-column input files.
- One-row, one-column input files.
- Invalid column index.
- Missing input file.
- `tester` entry point registration in `pyproject.toml`.

Run at least:

```bash
python3 -m pytest tests/test_reference_helpers.py tests/test_tester_reference.py tests/test_tester_dump.py
```

## Documentation

- Add a short README note near `tester-dump` documenting the `tester` command.
- State that column numbers are 1-based.
- State that the CLI uses the shared reference-comparison tolerance and
  significance rules.
- Add a small `AGENTS.md` note that `tester` must remain aligned with the shared
  comparison module used by the pytest reference validator.

## Assumptions

- `tester` is for numeric text columns only.
- Database, report, stdout/log, and workflow run-directory validation remain owned
  by `yambo-tester` and the pytest workflow validator.
- The default tolerance stays `0.1`, matching the existing helper and packaged
  config default.
- Files may have different total column counts as long as the requested columns
  exist.
