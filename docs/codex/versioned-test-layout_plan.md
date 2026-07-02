# Versioned Test Layout Plan

## Goal

Make Yambo 6 the default metadata behavior and move Yambo 5 differences into
explicit `versions."5"` overlays. Imported inputs and references should live in
versioned `INPUTS/Y5`, `INPUTS/Y6`, `REFERENCE/Y5`, and `REFERENCE/Y6`
directories, with reference keys written as explicit workflow-relative paths.

## Phases

1. Add shared reference helpers for `STDOUT`, explicit relative reference paths,
   legacy bare keys, and basename-only type detection.
2. Change version resolution so Yambo 6 is the fallback when no override or
   executable detection is available.
3. Convert imported workflow metadata so Yambo 6 values are the base metadata
   and Yambo 5 differences are declared under `versions."5"`.
4. Move imported fixture files into versioned input and reference directories,
   preserving legacy filenames and canonical step input names.
5. Update unit tests and metadata checks for the new default, explicit
   reference paths, and compatibility behavior.
6. Update user and Codex-facing docs to describe the versioned layout.
7. Run focused tests, then the full suite if focused checks pass.
