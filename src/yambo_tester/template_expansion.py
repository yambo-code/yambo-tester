# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

from copy import deepcopy
import importlib.resources
import tomllib

from .versioning import WORKFLOW_METADATA_KEYS


TEMPLATE_FILE = "workflow_templates.toml"


def load_workflow_templates():
    """
    Load packaged reusable workflow step templates.
    """
    template_path = importlib.resources.files("yambo_tester").joinpath("data", TEMPLATE_FILE)
    with template_path.open("rb") as f:
        return tomllib.load(f)


def workflow_uses_templates(workflow_config):
    """
    Return True when at least one workflow step declares a reusable template.
    """
    return any(
        isinstance(step, dict) and "step_type" in step
        for name, step in workflow_config.items()
        if name not in WORKFLOW_METADATA_KEYS
    )


def expand_workflow_templates(workflow_config, templates=None, workflow_file=None):
    """
    Return workflow metadata with templated steps expanded.

    Non-templated steps are copied unchanged. Templated steps merge packaged
    defaults with local overrides, then apply placeholders in fields,
    references, and version overlays.
    """
    templates = templates or load_workflow_templates()
    expanded = {}
    previous_step = ""

    for name, value in workflow_config.items():
        if name in WORKFLOW_METADATA_KEYS:
            expanded[name] = deepcopy(value)
            continue

        if not isinstance(value, dict) or "step_type" not in value:
            expanded[name] = deepcopy(value)
            previous_step = name
            continue

        step_type = value["step_type"]
        if step_type not in templates:
            location = f" in {workflow_file}" if workflow_file else ""
            raise ValueError(f"Unknown workflow step_type '{step_type}' for step '{name}'{location}.")

        context = {"step": name, "previous_step": previous_step}
        expanded[name] = _expand_step(templates[step_type], value, context)
        previous_step = name

    return expanded


def _expand_step(template_step, local_step, context):
    template_step = _apply_placeholders(deepcopy(template_step), context)
    local_step = _apply_placeholders(deepcopy(local_step), context)

    step = {}
    step.update(_base_fields(template_step))
    step.update(_base_fields(local_step))
    step.pop("step_type", None)

    base_reference = {}
    base_reference.update(template_step.get("reference", {}))
    base_reference.update(local_step.get("reference", {}))
    if base_reference:
        step["reference"] = base_reference

    versions = _expand_versions(template_step, local_step, base_reference)
    if versions:
        step["versions"] = versions

    return step


def _base_fields(step):
    return {
        key: deepcopy(value)
        for key, value in step.items()
        if key not in {"reference", "versions"}
    }


def _version_fields(version_step):
    return {
        key: deepcopy(value)
        for key, value in version_step.items()
        if key != "reference"
    }


def _expand_versions(template_step, local_step, base_reference):
    template_versions = template_step.get("versions", {})
    local_versions = local_step.get("versions", {})
    version_names = list(template_versions)
    version_names.extend(name for name in local_versions if name not in template_versions)

    versions = {}
    for version in version_names:
        template_version = template_versions.get(version, {})
        local_version = local_versions.get(version, {})

        version_step = {}
        version_step.update(_version_fields(template_version))
        version_step.update(_version_fields(local_version))

        reference = {}
        reference.update(template_version.get("reference", {}))
        reference.update(local_version.get("reference", {}))
        if reference:
            version_step["reference"] = reference

        if version_step:
            versions[version] = version_step

    return versions


def _apply_placeholders(value, context):
    if isinstance(value, str):
        return value.format(**context)
    if isinstance(value, list):
        return [_apply_placeholders(item, context) for item in value]
    if isinstance(value, dict):
        return {
            _apply_placeholders(key, context): _apply_placeholders(item, context)
            for key, item in value.items()
        }
    return value
