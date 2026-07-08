"""Project-level configuration for the WatchLLM kernel.

Loads settings from a ``.watchllm.toml`` file, environment variables, or
explicit paths.  Falls back to the same defaults that were previously
hardcoded in the rule constructors, so existing behaviour is unchanged
when no config file is present.

Resolution order (first match wins):
1. Explicit path passed to ``load_config(path=...)``.
2. ``WATCHLLM_CONFIG`` environment variable.
3. Walk up from *search_from* (or CWD) looking for ``.watchllm.toml``.
4. Built-in defaults.
"""

from __future__ import annotations

import dataclasses
import os
import sys
from pathlib import Path
from typing import Any, Optional

# tomllib is stdlib since 3.11; fall back to tomli for 3.10.
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIG_FILENAME = ".watchllm.toml"
CONFIG_ENV_VAR = "WATCHLLM_CONFIG"

# Match the existing defaults in forbidden_imports.py and boundary.py.
_DEFAULT_FORBIDDEN_MODULES: frozenset[str] = frozenset({
    "child_process",
    "vm",
})

# Python-specific defaults: modules that enable system access / code exec in Python.
_DEFAULT_PYTHON_FORBIDDEN_MODULES: frozenset[str] = frozenset({
    "subprocess",
    "pickle",
    "marshal",
})

_DEFAULT_FORBIDDEN_PREFIXES: frozenset[str] = frozenset({
    "../",
    "../../",
    "../../../",
    "../../../../",
    "../../../../../",
})

_DEFAULT_BOUNDARY_MAP: dict[str, dict] = {
    "auth": {
        "forbidden": (("db", "internal"),),
        "allowed": (("db", "public"),),
    },
}

DEFAULT_MODE = "enforce"


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class WatchLLMConfig:
    """Parsed project-level WatchLLM configuration.

    All fields match the constructor parameters of the existing rule
    classes so they can be passed through directly.
    """

    mode: str = DEFAULT_MODE
    forbidden_modules: frozenset[str] = dataclasses.field(
        default_factory=lambda: _DEFAULT_FORBIDDEN_MODULES
    )
    forbidden_prefixes: frozenset[str] = dataclasses.field(
        default_factory=lambda: _DEFAULT_FORBIDDEN_PREFIXES
    )
    boundary_map: dict[str, dict] = dataclasses.field(
        default_factory=lambda: dict(_DEFAULT_BOUNDARY_MAP)
    )
    python_forbidden_modules: frozenset[str] = dataclasses.field(
        default_factory=lambda: _DEFAULT_PYTHON_FORBIDDEN_MODULES
    )
    config_path: Optional[str] = None

    @property
    def is_default(self) -> bool:
        """True when no config file was loaded (all values are defaults)."""
        return self.config_path is None


# ---------------------------------------------------------------------------
# TOML parsing helpers
# ---------------------------------------------------------------------------


def _parse_boundary_map(raw: dict[str, Any]) -> dict[str, dict]:
    """Convert the TOML boundary table into the kernel's internal format.

    TOML input::

        [kernel.boundary]
        auth = { forbidden = ["db/internal"] }

    Kernel format::

        {"auth": {"forbidden": (("db", "internal"),), "allowed": ()}}
    """
    result: dict[str, dict] = {}

    for module_name, constraints in raw.items():
        if not isinstance(constraints, dict):
            continue

        forbidden_tuples = []
        for entry in constraints.get("forbidden", []):
            if isinstance(entry, str):
                parts = tuple(entry.split("/"))
                forbidden_tuples.append(parts)

        allowed_tuples = []
        for entry in constraints.get("allowed", []):
            if isinstance(entry, str):
                parts = tuple(entry.split("/"))
                allowed_tuples.append(parts)

        result[module_name] = {
            "forbidden": tuple(forbidden_tuples),
            "allowed": tuple(allowed_tuples),
        }

    return result


def _config_from_dict(data: dict[str, Any], config_path: str) -> WatchLLMConfig:
    """Build a WatchLLMConfig from parsed TOML data."""
    kernel = data.get("kernel", {})
    if not isinstance(kernel, dict):
        kernel = {}

    mode = kernel.get("mode", DEFAULT_MODE)
    if mode not in ("enforce", "shadow"):
        mode = DEFAULT_MODE

    forbidden_modules = _DEFAULT_FORBIDDEN_MODULES
    raw_modules = kernel.get("forbidden_modules")
    if isinstance(raw_modules, list):
        forbidden_modules = frozenset(
            m for m in raw_modules if isinstance(m, str)
        )

    forbidden_prefixes = _DEFAULT_FORBIDDEN_PREFIXES
    raw_prefixes = kernel.get("forbidden_prefixes")
    if isinstance(raw_prefixes, list):
        forbidden_prefixes = frozenset(
            p for p in raw_prefixes if isinstance(p, str)
        )

    boundary_map = dict(_DEFAULT_BOUNDARY_MAP)
    raw_boundary = kernel.get("boundary")
    if isinstance(raw_boundary, dict):
        boundary_map = _parse_boundary_map(raw_boundary)

    # [kernel.python] section
    python_section = data.get("kernel", {}).get("python", {})
    python_forbidden_modules = _DEFAULT_PYTHON_FORBIDDEN_MODULES
    raw_py_modules = python_section.get("forbidden_modules") if isinstance(python_section, dict) else None
    if isinstance(raw_py_modules, list):
        python_forbidden_modules = frozenset(
            m for m in raw_py_modules if isinstance(m, str)
        )

    return WatchLLMConfig(
        mode=mode,
        forbidden_modules=forbidden_modules,
        forbidden_prefixes=forbidden_prefixes,
        boundary_map=boundary_map,
        python_forbidden_modules=python_forbidden_modules,
        config_path=config_path,
    )


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def find_config_file(search_from: str | Path | None = None) -> Path | None:
    """Walk up the directory tree looking for ``.watchllm.toml``.

    Returns ``None`` when no config file is found.
    """
    start = Path(search_from) if search_from else Path.cwd()

    # If search_from is a file, start from its parent directory.
    if start.is_file():
        start = start.parent

    current = start.resolve()
    while True:
        candidate = current / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_config(
    path: str | Path | None = None,
    search_from: str | Path | None = None,
) -> WatchLLMConfig:
    """Load WatchLLM configuration with a clear resolution order.

    Parameters
    ----------
    path
        Explicit config file path.  Takes highest priority.
    search_from
        Starting directory (or file) for the upward directory walk.
        Ignored when *path* is given.  Defaults to CWD.

    Returns
    -------
    WatchLLMConfig
        Parsed configuration.  If no file is found, returns a config
        populated with the built-in defaults.
    """
    if tomllib is None:
        # Cannot parse TOML at all — fall back to defaults silently.
        return WatchLLMConfig()

    # 1. Explicit path.
    if path is not None:
        resolved = Path(path)
        if resolved.is_file():
            with resolved.open("rb") as fh:
                data = tomllib.load(fh)
            return _config_from_dict(data, str(resolved))
        # Explicit path was given but doesn't exist — use defaults.
        return WatchLLMConfig()

    # 2. Environment variable.
    env_path = os.environ.get(CONFIG_ENV_VAR)
    if env_path:
        resolved = Path(env_path)
        if resolved.is_file():
            with resolved.open("rb") as fh:
                data = tomllib.load(fh)
            return _config_from_dict(data, str(resolved))

    # 3. Directory walk.
    found = find_config_file(search_from)
    if found is not None:
        with found.open("rb") as fh:
            data = tomllib.load(fh)
        return _config_from_dict(data, str(found))

    # 4. Defaults.
    return WatchLLMConfig()


# ---------------------------------------------------------------------------
# Default config template (used by `watchllm init`)
# ---------------------------------------------------------------------------


DEFAULT_CONFIG_TEMPLATE = """\
# WatchLLM project configuration.
# https://watchllm.dev/docs/config

[kernel]
mode = "enforce"   # "enforce" blocks saves; "shadow" logs only

# JavaScript/TypeScript: modules that agents are forbidden from importing.
# Default: ["child_process", "vm"]
# forbidden_modules = ["child_process", "vm", "fs"]

# Relative import prefixes to block (directory traversal).
# Default: ["../", "../../", ...]
# forbidden_prefixes = ["../"]

# [kernel.python]
# Python-specific forbidden imports (separate from JS/TS defaults).
# Default: ["subprocess", "pickle", "marshal"]
# forbidden_modules = ["subprocess", "pickle", "marshal", "ctypes"]

# [kernel.boundary]
# auth = { forbidden = ["db/internal"], allowed = ["db/public"] }
"""
