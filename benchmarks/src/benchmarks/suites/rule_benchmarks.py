"""Rule evaluator benchmarks — rule traversal and execution latency.

Measures the cost of running WatchLLM kernel rules against parsed ASTs,
isolated from parsing overhead.  Uses the kernel engine's evaluate_source
entrypoint with timing around just the rule-evaluation phase.
"""

from __future__ import annotations

import time

from benchmarks.suites.parser_benchmarks import _generate_source
from watchllm_kernel.engine import evaluate_source
from watchllm_kernel.parser import parse_source
from watchllm_kernel.rules.secrets import SecretLiteralRule
from watchllm_kernel.rules.boundary import BoundaryRule
from watchllm_kernel.rules.forbidden_imports import ForbiddenImportRule
from watchllm_kernel.rules.auth_flow import AuthFlowRule


BENCH_RULES: tuple = (
    ("secrets", SecretLiteralRule()),
    ("boundary", BoundaryRule()),
    ("forbidden_imports", ForbiddenImportRule()),
    ("auth_flow", AuthFlowRule()),
)

BENCH_FILE_SIZES: tuple[int, ...] = (100, 500, 1_000)


def _measure_rule(
    rule_name: str,
    rule,
    source: str,
    *,
    warmup: int = 1,
    trials: int = 5,
) -> dict:
    """Benchmark a single rule against pre-parsed source.

    Parses once outside the timed loop so we measure only AST traversal +
    rule logic, not parsing.
    """
    parse_result = parse_source(source, language="javascript", file_path="bench.js")

    # Warmup
    for _ in range(warmup):
        rule.evaluate(source, file_path="bench.js", parse_result=parse_result)

    samples: list[float] = []
    for _ in range(trials):
        t0 = time.perf_counter()
        rule.evaluate(source, file_path="bench.js", parse_result=parse_result)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        samples.append(elapsed_ms)

    samples.sort()
    return {
        "rule": rule_name,
        "lines": len(source.splitlines()),
        "trials": trials,
        "median_ms": round(samples[len(samples) // 2], 4),
        "min_ms": round(samples[0], 4),
        "max_ms": round(samples[-1], 4),
    }


def run_rule_benchmarks(
    file_sizes: tuple[int, ...] = BENCH_FILE_SIZES,
    rules: tuple = BENCH_RULES,
) -> list[dict]:
    """Run rule evaluator benchmarks and return per-rule/size result dicts."""
    results: list[dict] = []
    for size in file_sizes:
        source = _generate_source(size)
        for rule_name, rule in rules:
            entry = _measure_rule(rule_name, rule, source)
            results.append(entry)
    return results


def print_rule_results(results: list[dict]) -> None:
    """Pretty-print rule evaluator benchmark results."""
    print("\n  Rule Evaluator Benchmarks")

    # Group by size for readability
    sizes = sorted({r["lines"] for r in results})

    for size in sizes:
        print(f"\n  ── {size} lines ──")
        print(f"  {'Rule':>18s}  {'Median':>10s}  {'Min':>10s}  {'Max':>10s}")
        print(f"  {'─'*18}  {'─'*10}  {'─'*10}  {'─'*10}")

        for entry in results:
            if entry["lines"] != size:
                continue
            median = f"{entry['median_ms']:.4f} ms"
            min_v = f"{entry['min_ms']:.4f} ms"
            max_v = f"{entry['max_ms']:.4f} ms"
            print(f"  {entry['rule']:>18s}  {median:>10s}  {min_v:>10s}  {max_v:>10s}")