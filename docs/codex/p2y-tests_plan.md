# p2y Tests Plan

## Goal

Add first-class support for imported `p2y` tests and enable the new `Al_bulk/DFT`
and `He/DFT` fixtures to run from the local cache at `/home/nicola/tmp/QE/cache`.

## Implementation Plan

1. Inspect the current runner and validator assumptions around `input`, `output`,
   command-line construction, and reference resolution.
2. Keep `tests.toml` step fields optional where appropriate:
   - only pass `-F` when `input` is present and non-empty;
   - only pass `-J/-C` when `output` is present and non-empty;
   - pass `-I <input_dir>` when `input_dir` is present and non-empty;
   - sort steps without requiring `input`.
3. Persist command stdout to a deterministic file in the run directory so
   `STDOUT` references can reuse the validation path.
4. Extend reference validation for string checks:
   - `STDOUT` reference keys search expected strings in captured stdout and,
     if present, the `l_<exe>` log file as one logical check;
   - `r-*` reference keys keep the existing report-completeness check;
   - when an `r-*` reference provides a non-empty string, also assert that the
     string is present in the resolved report file.
5. Include `Al_bulk/DFT` and `He/DFT` in the default packaged config so they are
   selectable through normal `yambo-tester` runs.
6. Add focused tests for:
   - `p2y` steps without `input` and `output`;
   - `input_dir` to `-I` command translation;
   - stdout persistence and `STDOUT` string checks;
   - string checks against `r-*` report files;
   - compatibility of the existing reference helpers.
7. Run the local pytest suite. Full `p2y` execution requires valid Yambo/QE
   executables and the tarballs in `/home/nicola/tmp/QE/cache`.

## Notes

- Avoid broad refactoring; add small helper functions only where they make the
  new behavior testable and keep existing Yambo tests unchanged.
- The existing `Al_bulk/DFT` and `He/DFT` fixture files already declare
  `input_dir` and `STDOUT` references. Their `r-*` entries should use the
  explicit `Game Over & Game summary` marker.
