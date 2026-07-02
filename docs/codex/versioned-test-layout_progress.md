# Versioned Test Layout Progress

## 2026-07-02

- Created implementation tracking docs.
- Starting with shared reference helper and version-default changes before
  migrating imported metadata and fixtures.

- Added shared reference path and basename classification helpers.
- Switched the fallback Yambo major version to 6.
- Migrated imported `INPUTS` and `REFERENCE` fixtures into versioned directories.
- Inverted DFT workflow metadata so Yambo 6 is base and Yambo 5 lives under overlays.
- Updated tests and docs for explicit reference paths.

- Reorganized imported `tests.toml` files so each step is followed immediately by its `reference` and `versions."5"` child tables.
- Added metadata coverage to keep step child tables grouped with their owning step.
