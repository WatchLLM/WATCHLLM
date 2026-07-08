"""Safe TOML config merge for WatchLLM kernel configuration.

Used by ``kl export-kernel-config --merge`` to inject klyd-derived
boundary rules and forbidden modules into an existing ``.watchllm.toml``
without clobbering user-managed sections.

Strategy:
- Sections marked with the ``# [watchllm:auto]`` header comment are
  considered auto-generated and will be replaced on each export.
- All other sections are treated as user-managed and are preserved verbatim.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Marker inserted above every auto-generated section.
_AUTO_MARKER = "# [watchllm:auto] — managed by `kl export-kernel-config`. Do not edit."
_AUTO_SECTION_RE = re.compile(
    r"(?:^|\n)" + re.escape(_AUTO_MARKER) + r".*?(?=\n\[|\Z)",
    re.DOTALL,
)


def _render_forbidden_modules(modules: list[str]) -> str:
    """Render a ``forbidden_modules`` TOML array."""
    items = ", ".join(f'"{m}"' for m in sorted(modules))
    return f"forbidden_modules = [{items}]"


def _render_boundary_section(boundary: dict[str, list[str]]) -> str:
    """Render a ``[kernel.boundary]`` TOML section."""
    lines = ["[kernel.boundary]"]
    for module, patterns in sorted(boundary.items()):
        encoded = json.dumps(patterns)
        lines.append(f"{module} = {{ forbidden = {encoded} }}")
    return "\n".join(lines)


def merge_toml_patch(
    base_path: Path,
    forbidden_modules: list[str] | None = None,
    boundary: dict[str, list[str]] | None = None,
) -> str:
    """Merge klyd-derived config into an existing ``.watchllm.toml``.

    Parameters
    ----------
    base_path:
        Path to the ``.watchllm.toml`` file (created if absent).
    forbidden_modules:
        List of module names to add to the auto-generated forbidden list.
        ``None`` means skip this section.
    boundary:
        Dict of ``{module: [forbidden_path, ...]}`` to write as
        ``[kernel.boundary]``. ``None`` means skip this section.

    Returns
    -------
    str
        The new file content (also written to *base_path*).
    """
    if base_path.exists():
        content = base_path.read_text(encoding="utf-8")
    else:
        content = ""

    # Strip all previously auto-generated blocks
    content = _AUTO_SECTION_RE.sub("", content).rstrip()

    new_blocks: list[str] = []

    if forbidden_modules:
        block = f"{_AUTO_MARKER}\n[kernel]\n{_render_forbidden_modules(forbidden_modules)}"
        new_blocks.append(block)

    if boundary:
        block = f"{_AUTO_MARKER}\n{_render_boundary_section(boundary)}"
        new_blocks.append(block)

    if new_blocks:
        content = content + "\n\n" + "\n\n".join(new_blocks) + "\n"
    
    # Ensure the file starts cleanly (no leading blank lines)
    content = content.lstrip("\n")

    base_path.write_text(content, encoding="utf-8")
    return content
