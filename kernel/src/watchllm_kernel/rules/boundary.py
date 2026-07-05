"""Boundary rule: enforce declared service/module import boundaries.

Uses AST-extracted import paths from the forbidden-import rule to detect
cross-boundary edges.  Circular dependency detection is explicitly deferred.
"""

from __future__ import annotations

import dataclasses
from typing import Optional

from watchllm_kernel.models import (
    Rule,
    RuleDecision,
    RuleResult,
    Severity,
    SourceLocation,
    Violation,
)
from watchllm_kernel.rules._ast_utils import ensure_parse_result
from watchllm_kernel.rules.forbidden_imports import (
    extract_import_paths,
    normalize_import_path,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_BOUNDARY_MAP = {
    "auth": {
        "forbidden": (("db", "internal"),),
        "allowed": (("db", "public"),),
    },
}

CIRCULAR_DEPENDENCY_POLICY = (
    "EXCLUDED: Task 08 evaluates single-file import edges only; "
    "repository-wide circular dependency detection is deferred."
)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class ImportEdge:
    """A single import edge extracted from source code."""

    source_module: str
    import_path: str
    location: Optional[SourceLocation] = None


# ---------------------------------------------------------------------------
# Source module inference
# ---------------------------------------------------------------------------

def infer_source_module(file_path: str | None, defined_modules: list[str]) -> str:
    """Infer a logical module name from a file path based on known modules."""
    if not file_path:
        return "unknown"

    path = file_path.replace("\\", "/")
    segments = path.split("/")

    for mod in defined_modules:
        if mod in segments:
            return mod
        basename = segments[-1] if segments else ""
        if basename.startswith(f"{mod}_") or basename.startswith(f"{mod}-"):
            return mod

    return "unknown"


# ---------------------------------------------------------------------------
# Import graph extraction
# ---------------------------------------------------------------------------

def extract_import_edges(
    source: str, defined_modules: list[str], file_path: str | None = None, parse_result=None
) -> list[ImportEdge]:
    """Extract import edges from source text using AST-derived import paths."""
    source_module = infer_source_module(file_path, defined_modules)
    import_paths = extract_import_paths(source, parse_result=parse_result)

    edges: list[ImportEdge] = []
    for path in import_paths:
        edges.append(
            ImportEdge(
                source_module=source_module,
                import_path=path,
            )
        )
    return edges


# ---------------------------------------------------------------------------
# Boundary violation decision
# ---------------------------------------------------------------------------

def is_boundary_violation(
    edge: ImportEdge,
    boundary_map: dict
) -> tuple[bool, str]:
    """Return (True, matched_string) if *edge* violates the declared boundary map."""
    if edge.source_module not in boundary_map:
        return False, ""

    policy = boundary_map[edge.source_module]
    forbidden_tuples = policy.get("forbidden", ())
    
    import_path = normalize_import_path(edge.import_path)

    for forbidden_tuple in forbidden_tuples:
        forbidden_str = "/".join(forbidden_tuple)
        if forbidden_str in import_path:
            return True, forbidden_str

    return False, ""


# ---------------------------------------------------------------------------
# Rule class
# ---------------------------------------------------------------------------


class BoundaryRule(Rule):
    """Deterministic rule that blocks imports violating declared boundaries."""

    def __init__(self, boundary_map=None):
        super().__init__(
            rule_id="BOUNDARY",
            name="Boundary rule",
            description="Blocks imports that violate declared service/module boundaries.",
        )
        self.boundary_map = (
            boundary_map if boundary_map is not None else DEFAULT_BOUNDARY_MAP
        )

    def evaluate(self, source: str, file_path: str | None = None, parse_result=None) -> RuleResult:
        defined_modules = list(self.boundary_map.keys())
        edges = extract_import_edges(source, defined_modules, file_path=file_path, parse_result=parse_result)
        violations: list[Violation] = []

        for edge in edges:
            is_violation, target = is_boundary_violation(edge, self.boundary_map)
            if is_violation:
                violations.append(
                    Violation(
                        rule_id=self.rule_id,
                        message=(
                            f"Boundary violation: {edge.source_module} cannot import {target}"
                        ),
                        location=edge.location,
                        severity=Severity.HIGH,
                        evidence=edge.import_path,
                    )
                )

        if violations:
            return RuleResult(
                rule_id=self.rule_id,
                decision=RuleDecision.FAIL,
                violations=violations,
            )
        return RuleResult(rule_id=self.rule_id, decision=RuleDecision.PASS)
