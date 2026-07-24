# Comparison Diagnostics Progress

- [x] Inspected current shared comparison paths in `reference_compare.py`, `src/scripts/test_reference.py`, and `src/yambo_tester/tests/test_reference.py`.
- [x] Confirmed tolerance semantics: significant-value mask plus NumPy close comparison with relative tolerance and `1e-6` absolute tolerance.
- [x] Added shared comparison result and mismatch detail structures.
- [x] Added bounded diagnostic formatting and retained the `assert_close_significant()` compatibility entry point.
- [x] Preserved current workflow text-column behavior while adding diagnostics to compared columns.
- [x] Preserved NetCDF flattening and added original-shape metadata for multidimensional index reports.
- [x] Added `tester --max-mismatches`.
- [x] Routed workflow assertion diagnostics to the per-run `tester.log`.
- [x] Added regression tests for shared logic, CLI output, NetCDF indices, and logging.
- [x] Run focused pytest checks.
- [x] Run full pytest suite if feasible.

## Verification Log

```bash
python3 -m compileall src/yambo_tester/reference_compare.py src/scripts/test_reference.py src/yambo_tester/log.py src/yambo_tester/tests/test_reference.py tests/test_reference_helpers.py tests/test_tester_reference.py tests/test_logging.py
# passed

.env/bin/pytest tests/test_reference_helpers.py tests/test_tester_reference.py tests/test_logging.py
# 86 passed

.env/bin/pytest
# 159 passed, 2 skipped, 1 failed
```

The full-suite failure is the existing `tests/test_template_expansion.py::test_packaged_templates_cover_conversion_and_local_init_overrides` expectation mismatch for packaged `p2y` template references. It is unrelated to comparison diagnostics.
