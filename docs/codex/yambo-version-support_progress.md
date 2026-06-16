# Yambo 5 and Yambo 6 Support Progress

## Status

Workflow-owned support metadata and tarball source selection are implemented.
The global version-to-download-link map is no longer used as the automatic
default when CLI/config do not provide `download_link`; workflow metadata is the
default source of truth.

## Completed

- Added generic workflow metadata resolution with top-level version overlays.
- Added tarball URL precedence: CLI, config, then resolved workflow metadata.
- Updated normal setup and `--download_only` to use the same per-workflow URL
  resolution path.
- Kept unsupported Yambo-version handling at workflow scope with skipped
  `results.toml` entries.
- Restored the packaged default config to include validated DFT, GW-OPTICS,
  ELPH, and PA_chain workflows.
- Added metadata to imported workflows for the initial DFT/non-DFT matrix.
- Added focused unit and fixture coverage for metadata resolution and URL flow.

## Remaining

Scientific/reference validation for broader Yambo 6 workflows remains follow-up
work beyond this metadata and runner plumbing.
