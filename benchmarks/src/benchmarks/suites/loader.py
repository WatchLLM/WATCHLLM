"""benchmark suite discovery and registration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# Callable that runs a benchmark suite and returns results.
# Actual return type is suite-specific; kept generic for extensibility.
BenchmarkRunner = Callable[[], Any]


@dataclass(frozen=True)
class SuiteSpec:
    """Metadata for a single benchmark suite."""

    name: str
    description: str
    runner: BenchmarkRunner
    tags: tuple[str, ...] = field(default_factory=tuple)


_REGISTERED_SUITES: list[SuiteSpec] = []


def load_suites() -> list[SuiteSpec]:
    """Return every registered benchmark suite."""
    return list(_REGISTERED_SUITES)


def register(*specs: SuiteSpec) -> None:
    """Register one or more :class:`SuiteSpec` instances."""
    _REGISTERED_SUITES.extend(specs)


# ---------------------------------------------------------------------------
# Auto-register benchmark suites
# ---------------------------------------------------------------------------

# -- Parser benchmarks --------------------------------------------------------

from benchmarks.suites.parser_benchmarks import (  # noqa: E402
    print_parser_results,
    run_parser_benchmarks,
)


def _run_parser_pretty() -> list[dict]:
    results = run_parser_benchmarks()
    print_parser_results(results)
    return results


register(
    SuiteSpec(
        name="parser",
        description="Raw Tree-sitter parsing latency across file sizes",
        runner=_run_parser_pretty,
        tags=("parsing", "latency", "tree-sitter"),
    )
)

# -- Rule benchmarks -----------------------------------------------------------

from benchmarks.suites.rule_benchmarks import (  # noqa: E402
    print_rule_results,
    run_rule_benchmarks,
)


def _run_rules_pretty() -> list[dict]:
    results = run_rule_benchmarks()
    print_rule_results(results)
    return results


register(
    SuiteSpec(
        name="rules",
        description="Rule evaluator latency (AST traversal + rule logic)",
        runner=_run_rules_pretty,
        tags=("rules", "latency", "ast-traversal"),
    )
)

# -- E2E pipeline benchmarks ---------------------------------------------------

from benchmarks.suites.e2e_benchmarks import (  # noqa: E402
    export_json_report,
    print_e2e_results,
    run_e2e_benchmarks,
)


def _run_e2e_pretty() -> list[dict]:
    results = run_e2e_benchmarks()
    print_e2e_results(results)
    return results


register(
    SuiteSpec(
        name="e2e",
        description="Full write-path latency (parse + all rules → ALLOW/BLOCK)",
        runner=_run_e2e_pretty,
        tags=("e2e", "pipeline", "regression"),
    )
)