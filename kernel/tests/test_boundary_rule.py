"""Tests for the boundary rule (Task 08)."""

from pathlib import Path
import unittest

from watchllm_kernel.models import RuleDecision
from watchllm_kernel.rules.boundary import (
    BoundaryRule,
    CIRCULAR_DEPENDENCY_POLICY,
    extract_import_edges,
    infer_source_module,
    is_boundary_violation,
    DEFAULT_BOUNDARY_MAP,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "rules" / "boundary"


def read_fixture(outcome: str, name: str) -> str:
    return (FIXTURE_DIR / outcome / name).read_text(encoding="utf-8")


class TestBoundaryRule(unittest.TestCase):
    # -- source module inference ------------------------------------------------

    def test_infer_source_module_from_auth_path(self):
        self.assertEqual(infer_source_module("src/auth/load-user.ts", ["auth"]), "auth")
        self.assertEqual(
            infer_source_module("auth_imports_db_internal.ts", ["auth"]), "auth"
        )
        self.assertEqual(infer_source_module("src/shared/util.ts", ["auth"]), "unknown")

    # -- import edge extraction -------------------------------------------------

    def test_extract_import_edges_from_fail_fixture(self):
        source = read_fixture("fail", "auth_imports_db_internal.ts")
        edges = extract_import_edges(source, ["auth"], file_path="src/auth/load-user.ts")
        self.assertTrue(len(edges) >= 1)

        # Find the edge that matches the expected internal import
        internal_edge = None
        for e in edges:
            if e.import_path == "../db/internal/query":
                internal_edge = e
                break
        self.assertIsNotNone(internal_edge, "Expected internal import edge not found")
        self.assertEqual(internal_edge.source_module, "auth")

    # -- rule evaluation --------------------------------------------------------

    def test_disallowed_cross_boundary_edge_fails(self):
        source = read_fixture("fail", "auth_imports_db_internal.ts")
        result = BoundaryRule().evaluate(source, file_path="src/auth/load-user.ts")
        self.assertEqual(result.decision, RuleDecision.FAIL)
        self.assertEqual(len(result.violations), 1)
        self.assertEqual(result.violations[0].evidence, "../db/internal/query")

    def test_allowed_boundary_edge_passes(self):
        source = read_fixture("pass", "auth_imports_public_contract.ts")
        result = BoundaryRule().evaluate(source, file_path="src/auth/load-user.ts")
        self.assertEqual(result.decision, RuleDecision.PASS)
        self.assertEqual(result.violations, [])

    # -- violation helper -------------------------------------------------------

    def test_boundary_violation_helper(self):
        fail_source = read_fixture("fail", "auth_imports_db_internal.ts")
        fail_edges = extract_import_edges(
            fail_source, ["auth"], file_path="src/auth/load-user.ts"
        )
        # At least one edge should be a violation
        self.assertTrue(
            any(is_boundary_violation(e, DEFAULT_BOUNDARY_MAP)[0] for e in fail_edges),
            "Expected at least one boundary violation in fail fixture",
        )

        pass_source = read_fixture("pass", "auth_imports_public_contract.ts")
        pass_edges = extract_import_edges(
            pass_source, ["auth"], file_path="src/auth/load-user.ts"
        )
        # No edge should be a violation
        self.assertFalse(
            any(is_boundary_violation(e, DEFAULT_BOUNDARY_MAP)[0] for e in pass_edges),
            "Expected no boundary violations in pass fixture",
        )

    # -- circular dependency policy ---------------------------------------------

    def test_circular_dependency_policy_is_explicitly_excluded(self):
        self.assertIn("EXCLUDED", CIRCULAR_DEPENDENCY_POLICY)
        self.assertIn("deferred", CIRCULAR_DEPENDENCY_POLICY)


if __name__ == "__main__":
    unittest.main()

