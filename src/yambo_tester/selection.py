# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

RUNLEVEL_FILTER_RETURNCODE = -9998
MISSING_EXECUTABLE_RETURNCODE = -9999
RUNLEVEL_FILTER_REASON = "runlevel-filter"
MISSING_EXECUTABLE_REASON = "missing-executable"


def normalize_runlevels(runlevels):
    """
    Return a normalized set of requested runlevels.

    Accepts values from both config files and argparse: strings, repeated option
    lists, comma-separated strings, or empty values.
    """
    if not runlevels:
        return set()
    if isinstance(runlevels, str):
        values = [runlevels]
    else:
        values = runlevels

    normalized = set()
    for value in values:
        if not value:
            continue
        for item in str(value).split(","):
            item = item.strip().lower()
            if item:
                normalized.add(item)
    return normalized


def step_dependencies(step_name, step):
    dependencies = step.get("dependencies", [])
    if isinstance(dependencies, str):
        return [dependencies]
    if not isinstance(dependencies, list):
        raise TypeError(f"{step_name}: dependencies must be a list of step names.")
    return dependencies


def validate_dependencies(steps):
    step_names = set(steps)
    for name, step in steps.items():
        for dependency in step_dependencies(name, step):
            if dependency not in step_names:
                raise ValueError(f"{name}: unknown dependency '{dependency}'.")


def selected_step_names(steps, runlevels):
    """
    Return the workflow step names selected by runlevel plus dependencies.

    If no runlevel is requested, every step is selected after dependency
    validation. Runlevel matching is case-insensitive.
    """
    selected_runlevels = normalize_runlevels(runlevels)
    validate_dependencies(steps)
    if not selected_runlevels:
        return set(steps)

    selected = {
        name for name, step in steps.items()
        if str(step.get("runlevel", "")).strip().lower() in selected_runlevels
    }
    stack = list(selected)
    while stack:
        name = stack.pop()
        for dependency in step_dependencies(name, steps[name]):
            if dependency not in selected:
                selected.add(dependency)
                stack.append(dependency)
    return selected
