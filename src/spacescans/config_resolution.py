# src/spacescans/config_resolution.py
"""Resolve YAML config paths via 3-tier priority (CLI > env > YAML).

Public functions:
- expand_path: turn one path string into an absolute Path
- resolve_data_dir: pick the data root for relative-path resolution
- resolve_output_dir: pick the output root
- resolve_config: rewrite a config dict so all path fields are absolute
"""
from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Any


class ConfigResolutionError(ValueError):
    """Raised when a path can't be resolved (no data_dir configured, etc)."""


# Fields known to hold filesystem paths. These are the ones we rewrite.
_INPUT_PATH_FIELDS = (
    "file",            # source.file (str OR list[str])
    "county_file",     # source.county_file (tiger_proximity)
    "patient_file",    # buffer.patient_file
    "zbp_file",        # source.zbp_file (cbp_fallback dep)
    "label_file",      # source.label_file (FARA)
    "road_cache_dir",  # source.road_cache_dir (c3 tiger_proximity / nhd_proximity)
)
_OUTPUT_PATH_FIELDS = (
    "path",            # output.path
    "label_path",      # output.label_path
)

_VAR_PATTERN = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def expand_path(raw: str, *, data_dir: Path | None) -> Path:
    """Expand a single path string to an absolute Path.

    Rules:
    1. ${VAR} placeholders are expanded from os.environ.
    2. Absolute path → returned as-is.
    3. Relative path → joined with data_dir; ConfigResolutionError if data_dir is None.
    """
    # Step 1: expand ${VAR} placeholders
    def _replace(m):
        var = m.group(1)
        val = os.environ.get(var)
        if val is None:
            # Special case: ${SPACESCANS_DATA_DIR} can fall back to data_dir arg
            if var == "SPACESCANS_DATA_DIR" and data_dir is not None:
                return str(data_dir)
            raise ConfigResolutionError(
                f"Path contains undefined variable ${{{var}}} and no fallback. "
                f"Set {var} in environment or use an absolute path."
            )
        return val

    expanded = _VAR_PATTERN.sub(_replace, raw)
    p = Path(expanded)

    # Step 2: absolute → done
    if p.is_absolute():
        return p

    # Step 3: relative → need data_dir
    if data_dir is None:
        raise ConfigResolutionError(
            f"Path '{raw}' is relative but no data root configured. Choose one:\n"
            f"  1. Pass --data-dir /path/to/data on the command line\n"
            f"  2. Set SPACESCANS_DATA_DIR environment variable\n"
            f"  3. Add `base_dir: /path/to/data` to the YAML top level\n"
            f"  4. Change the path to absolute"
        )
    return data_dir / p


def resolve_data_dir(*, cli_value: str | None, yaml_value: str | None) -> Path | None:
    """Pick data_dir: CLI > $SPACESCANS_DATA_DIR > YAML base_dir > None."""
    if cli_value:
        return Path(cli_value).resolve()
    env = os.environ.get("SPACESCANS_DATA_DIR")
    if env:
        return Path(env).resolve()
    if yaml_value:
        return Path(yaml_value).resolve()
    return None


def resolve_output_dir(*, cli_value: str | None, yaml_value: str | None) -> Path:
    """Pick output_dir: CLI > $SPACESCANS_OUTPUT_DIR > YAML > cwd/output."""
    if cli_value:
        return Path(cli_value).resolve()
    env = os.environ.get("SPACESCANS_OUTPUT_DIR")
    if env:
        return Path(env).resolve()
    if yaml_value:
        return Path(yaml_value).resolve()
    return (Path.cwd() / "output").resolve()


def resolve_config(
    config_dict: dict[str, Any],
    *,
    data_dir: Path | None,
    output_dir: Path,
) -> dict[str, Any]:
    """Rewrite a config dict so every known path field is an absolute string.

    Returns a new dict; does not mutate input.
    """
    result: dict[str, Any] = {}
    for top_key, top_val in config_dict.items():
        if not isinstance(top_val, dict):
            result[top_key] = top_val
            continue

        is_output_section = top_key == "output"
        new_sub: dict[str, Any] = {}
        for sub_key, sub_val in top_val.items():
            if sub_key in _OUTPUT_PATH_FIELDS and is_output_section:
                new_sub[sub_key] = str(expand_path(sub_val, data_dir=output_dir))
            elif sub_key in _INPUT_PATH_FIELDS:
                if isinstance(sub_val, list):
                    new_sub[sub_key] = [str(expand_path(p, data_dir=data_dir)) for p in sub_val]
                else:
                    new_sub[sub_key] = str(expand_path(sub_val, data_dir=data_dir))
            else:
                new_sub[sub_key] = sub_val
        result[top_key] = new_sub
    return result
