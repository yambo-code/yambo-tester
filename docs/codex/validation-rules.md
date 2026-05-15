# Validation Rules Notes

The Python validator is in `src/yambo_tester/tests/test_reference.py`. The legacy behavior is mainly in:

- `~/src/yambo-tests/scripts/find_the_diff/`
- `~/src/yambo-tests/config/RULES.h`
- `~/src/yambo-tests/config/WHITELIST.h`

Use those files to understand behavior, not as implementation templates.

## Output Types

- `r-*`: Yambo report files. Validate existence and a successful-run marker near the end. Current Python checks for `Game Over & Game summary`.
- `o-*`: text output files with numerical columns. Compare generated data against `REFERENCE/o-*`.
- `l_*`: log files, often in `LOG/` for parallel runs. No validation is currently required.
- `ndb.*`: NetCDF/HDF5-compatible databases. Read with `netCDF4`; compare only variables listed in `tests.toml`.

## Legacy Concepts To Preserve

`RULES.h` defines file-pattern rules that may alter comparison behavior. Common actions include:

- `skip`: ignore specific columns, titles, variables, materials, or file patterns.
- `average`: compare averaged data for noisy columns.
- `no_statistics`: suppress or alter statistical checks.
- `double_precision`: use stricter precision behavior for selected outputs.
- `sort` or `align`: sort or align rows before comparison.
- `last_row`: compare only the final row for convergence histories.

`WHITELIST.h` identifies known failures or noisy outputs. A whitelist entry should not silently pass as a normal success; future behavior should make accepted failures visible in reports.

## Current Python Behavior

The current validator is intentionally simpler than the legacy tool:

- For text `o-*` files, it reads arrays with `numpy.genfromtxt()` and compares columns after the first column with `numpy.allclose()`.
- For database references, it reads selected variables from the generated NetCDF file and compares their flattened values to reference data.
- It rejects NaN and extremely large values.
- It uses the configured `tollerance` as relative tolerance and `1e-6` as absolute tolerance.

## Development Guidance

When a validation failure appears wrong:

1. Identify the exact reference key in `tests.toml`.
2. Check whether the file pattern, material, column title, or variable is covered by `RULES.h` or `WHITELIST.h`.
3. Implement the smallest Python rule needed for the imported test.
4. Keep rule matching explicit and testable; avoid hard-coded one-off exceptions buried in comparison loops.
5. Document newly supported semantics here if they affect future behavior.
