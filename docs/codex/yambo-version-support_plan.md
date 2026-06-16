# Yambo 5 and Yambo 6 Support Plan

Status: implemented for workflow-owned support metadata and tarball source selection.

## Summary

Yambo major-version resolution is performed once during parameter validation.
Each workflow `tests.toml` owns support metadata and tarball URL metadata; Python
logic applies shallow workflow-level and step-level overlays generically.
Unsupported workflows are copied to scratch and recorded as skipped with
`unsupported-yambo-version`.

## Metadata Model

```toml
sha256 = "..."
tarball_url = "https://media.yambo-code.eu/robots/databases/tests"

[yambo_versions]
supported = ["5"]

[versions."6"]
tarball_url = "https://media.yambo-code.eu/robots/databases/y6"
```

Top-level `[versions."<major>"]` overlays affect workflow metadata.
Step-level `[step.versions."<major>"]` overlays continue to affect only that
step, including reference overrides.

Tarball URL precedence is: CLI `--download_link`, config
`[parameters].download_link`, resolved workflow metadata.

## Initial Matrix

- Imported DFT workflows: `supported = ["5", "6"]`, Yambo 6 tarball URL.
- Imported non-DFT workflows: `supported = ["5"]`, legacy tests tarball URL.

## Verification Targets

- Workflow metadata resolution, version overlays, unsupported-version skips.
- URL precedence for CLI, config, and workflow metadata.
- Shared URL resolution in normal setup and `--download_only`.
- Fixture coverage for the imported workflow metadata matrix and default test list.
