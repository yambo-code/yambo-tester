# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.
"""Input dialects of Yambo development branches (data/variants.toml)."""

import re  # input line matching
import tomllib  # read the packaged table
from importlib.resources import files  # packaged data path

from .versioning import normalize_yambo_version  # major version check


def load_variant(name, yambo_version):
    """Return the rules of variant `name`, checking it exists and belongs to `yambo_version`."""
    if not name:  # no variant selected
        return {}  # nothing to apply
    table = tomllib.loads(files("yambo_tester.data").joinpath("variants.toml").read_text())  # all variants
    if name not in table:  # unknown name
        raise ValueError(f"Unknown Yambo variant '{name}'. Known variants: {', '.join(sorted(table))}.")  # clear error
    major = normalize_yambo_version(yambo_version)  # selected major
    if normalize_yambo_version(table[name]["major"]) != major:  # wrong major
        raise ValueError(f"Variant '{name}' is for Yambo {table[name]['major']}, not Yambo {major}.")  # clear error
    return table[name]  # rules


def rewrite_input(path, variant):
    """Rewrite the runlevel lines of one scratch input in place, following the variant rules."""
    text = path.read_text()  # input content
    for runlevel, rule in variant.get("runlevels", {}).items():  # each runlevel to replace
        line = re.compile(rf"^{re.escape(runlevel)}\b.*\n?", re.M)  # the runlevel line
        if not line.search(text):  # runlevel not in this input
            continue  # nothing to do
        var = re.compile(rf"^{re.escape(rule['by'])}\s*=\s*\"?([^\"\s#]*)\"?.*\n?", re.M)  # selector variable line
        found = var.search(text)  # its value, if set
        value = found.group(1).upper() if found else ""  # case-insensitive key
        choice = {k.upper(): v for k, v in rule.items() if isinstance(v, list)}  # value -> runlevels
        new = choice.get(value, rule["default"])  # chosen runlevels
        text = line.sub("".join(f"{r}\n" for r in new), text, count=1)  # replace the runlevel line
        if rule.get("drop") and found:  # selector not known to the variant
            text = var.sub("", text, count=1)  # remove it
    path.write_text(text)  # save
