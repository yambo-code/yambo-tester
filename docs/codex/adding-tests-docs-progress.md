# Adding Tests Documentation Progress

## Completed

- Added `ADDING_TESTS.md` as a root-level guide for adding new tests.
- Documented the expected test layout with `INPUTS/`, `REFERENCE/`, `SAVE/`,
  and `tests.toml`.
- Documented how to prepare the `SAVE` tarball, where to place it in the cache,
  and how to compute the `sha256` value for `tests.toml`.
- Documented the supported `tests.toml` structure, including required step
  fields, optional fields, reference entry forms, and validation metadata.
- Checked the source behavior for `SAVE_converted/`: it is a legacy compatibility
  path that is renamed to `SAVE/` at runtime when present. New tests should use a
  single `SAVE/` directory with databases for the current supported Yambo version.
- Updated `README.md` to link the new guide from the Documentation section.

## Verification

- Checked the documentation against `runner.py`, `download.py`, and
  `test_reference.py`.
- Verified the README link and key guide sections with text search.
- Did not run pytest because this task changed documentation only.

## Notes

- An unrelated untracked `doc/` directory was present in the working tree and was
  not modified for this task.
