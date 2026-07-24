# Comparison Diagnostics Plan

## Current implementation

- Shared comparison code lives in `src/yambo_tester/reference_compare.py`.
- The standalone `tester` executable is `src/scripts/test_reference.py` and calls the shared text/NetCDF helpers.
- The main workflow validator is `src/yambo_tester/tests/test_reference.py`; it calls the same shared helpers from pytest.
- Text output references compare columns after the first column in workflow validation; `tester` compares the explicitly selected 1-based reference/output columns.
- NetCDF comparisons read variables with `netCDF4.Dataset`, flatten each selected variable, and compare each variable against its matching text-reference slice.

## Tolerance semantics

- Output values are rejected before comparison if they contain `NaN`, positive/negative infinity, or finite magnitudes greater than or equal to `TOO_LARGE`.
- Numerical comparison first builds `significant_mask(ref, out)` using `max(abs(reference)) * SIGNIFICANCE_THRESHOLD`.
- Only significant values are compared.
- Significant values use NumPy close semantics equivalent to `np.isclose(output, reference, rtol=tolerance, atol=ZERO_DFL)`.
- Diagnostics must use that same mask and close expression so pass/fail and mismatch details cannot diverge.

## Shared design

- Add `ComparisonResult` with `passed`, `total_elements`, `mismatch_count`, bounded `mismatches`, and `max_reported`.
- Add `MismatchDetail` with zero-based `flat_index`, optional text `row_index`, optional 1-based `column`, optional NetCDF `variable`, optional multidimensional `index`, reference/output values, absolute difference, and relative difference.
- Keep formatting separate from comparison using `format_comparison_diagnostics()`.
- Keep `assert_close_significant()` as the compatibility wrapper that raises `AssertionError` with the formatted report.

## Reporting strategy

- Use zero-based flat indices everywhere.
- Text diagnostics include zero-based `row_index` and the compared 1-based output column when known.
- NetCDF diagnostics preserve each variable's original shape and include `index = (...)` via `np.unravel_index` when available.
- Always report the total mismatch count.
- Limit detailed entries with named constant `DEFAULT_MAX_MISMATCH_REPORTS = 20`.
- Add `tester --max-mismatches N` for ad hoc CLI control.

## Tests and docs

- Cover passing comparisons, one/multiple mismatches, mismatch counts, values, indices, abs/rel differences, scalar/single-row/single-column/multiple-column data, NetCDF multidimensional indices, selected columns through `tester`, shape/length mismatches, report limiting, and NaN/infinity semantics.
- Verify workflow diagnostics are written to the per-run `tester.log` without using the main logger.
- Update README and validation-rules documentation with diagnostics, index convention, reporting limit, and tolerance application.
