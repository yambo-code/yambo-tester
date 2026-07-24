# Tester NetCDF Support Progress

## Status

- [x] Documented current `tester` text-column implementation and existing workflow NetCDF path.
- [x] Added shared NetCDF helpers to `src/yambo_tester/reference_compare.py`.
- [x] Updated workflow reference validation to use the shared NetCDF comparison helper.
- [x] Updated `tester` with NetCDF variable options and first-column defaults.
- [x] Updated `tester-dump` to reuse shared variable parsing.
- [x] Added focused text and NetCDF regression tests.
- [x] Updated README examples.

## Verification

Focused check passed:

```bash
.env/bin/pytest tests/test_reference_helpers.py tests/test_tester_reference.py tests/test_tester_dump.py
# 74 passed
```

Full suite check:

```bash
.env/bin/pytest
# 132 passed, 2 skipped, 1 failed
```

The full-suite failure is `tests/test_template_expansion.py::test_packaged_templates_cover_conversion_and_local_init_overrides`, where the expected packaged `p2y` template references do not match the current template data. No files in that area were changed for this feature.
