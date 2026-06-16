# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

DEFAULT_YAMBO_VERSION = "5"
WORKFLOW_METADATA_KEYS = {"sha256", "tarball_url", "yambo_versions", "versions"}

YAMBO_VERSION_DOWNLOAD_LINKS = {
    "5": "https://media.yambo-code.eu/robots/databases/tests",
    "6": "https://media.yambo-code.eu/robots/databases/y6",
}


def normalize_yambo_version(value):
    """
    Return a supported Yambo major version string from user input.
    """
    if value is None:
        return None

    value = str(value).strip()
    if not value:
        return None

    major = value.split(".", 1)[0]
    if major not in YAMBO_VERSION_DOWNLOAD_LINKS:
        supported = ", ".join(sorted(YAMBO_VERSION_DOWNLOAD_LINKS))
        raise ValueError(f"Unsupported Yambo major version '{major}'. Supported versions: {supported}.")
    return major


def detected_yambo_major(info):
    """
    Extract a supported Yambo major version from get_yambo_info() output.
    """
    version = info.get("version") if info else None
    if not version:
        return None
    return normalize_yambo_version(version[0])


def resolve_yambo_version(requested=None, detected_info=None, default=DEFAULT_YAMBO_VERSION):
    """
    Resolve the effective Yambo major version.

    Explicit user configuration wins over executable auto-detection. If neither
    is available, keep the Yambo 5 compatibility default.
    """
    requested_major = normalize_yambo_version(requested)
    if requested_major:
        return requested_major

    detected_major = detected_yambo_major(detected_info or {})
    if detected_major:
        return detected_major

    return normalize_yambo_version(default)


def download_link_for_version(yambo_version):
    """
    Return the test database repository URL for a supported Yambo major version.
    """
    major = normalize_yambo_version(yambo_version)
    return YAMBO_VERSION_DOWNLOAD_LINKS[major]


def resolve_workflow_metadata(workflow_config, yambo_version):
    """
    Return workflow-level metadata after applying a shallow version overlay.

    Step tables are intentionally excluded. Version overlays under top-level
    ``versions."<major>"`` are for workflow metadata such as tarball source
    selection; step-level overlays remain handled by resolve_step_metadata().
    """
    major = normalize_yambo_version(yambo_version)
    resolved = {
        key: value
        for key, value in workflow_config.items()
        if key in WORKFLOW_METADATA_KEYS and key != "versions"
    }
    overlay = workflow_config.get("versions", {}).get(major, {})
    resolved.update(overlay)
    return resolved


def resolve_workflow_tarball_url(workflow_config, yambo_version, parameters=None):
    """
    Resolve the tarball source URL for a workflow.

    Precedence is CLI --download_link, then config.toml download_link, then the
    resolved workflow metadata after applying the selected version overlay.
    """
    parameters = parameters or {}
    if parameters.get("download_link_origin") in {"cli", "config"} and parameters.get("download_link"):
        return parameters["download_link"]

    metadata = resolve_workflow_metadata(workflow_config, yambo_version)
    return metadata.get("tarball_url", "")


def workflow_supports_version(workflow_config, yambo_version):
    """
    Return whether workflow metadata allows the selected Yambo major version.
    """
    version_metadata = resolve_workflow_metadata(workflow_config, yambo_version).get("yambo_versions", {})
    supported = version_metadata.get("supported", [])
    if not supported:
        return True

    major = normalize_yambo_version(yambo_version)
    return major in {normalize_yambo_version(item) for item in supported}


def resolve_step_metadata(step, yambo_version):
    """
    Apply a shallow per-version overlay to a workflow step.

    Base fields remain the default. If the selected version provides an
    override under ``versions."<major>"``, those top-level fields replace the
    base values. A version-specific ``reference`` table therefore replaces the
    base reference table for that version.
    """
    major = normalize_yambo_version(yambo_version)
    resolved = {key: value for key, value in step.items() if key != "versions"}
    overlay = step.get("versions", {}).get(major, {})
    resolved.update(overlay)
    return resolved


def workflow_steps_for_version(workflow_config, yambo_version):
    """
    Return executable workflow steps with per-version metadata resolved.
    """
    return {
        name: resolve_step_metadata(step, yambo_version)
        for name, step in workflow_config.items()
        if name not in WORKFLOW_METADATA_KEYS
    }
