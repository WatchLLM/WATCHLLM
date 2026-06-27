"""End-to-end pipeline benchmarks — full write-path latency.

Measures the complete pipeline from file detection to ALLOW/BLOCK resolution
by calling ``watchllm_kernel.engine.evaluate_source`` with all rules active.

Produces a JSON regression report with P50/P95/P99 latency data.
"""

from __future__ import annotations

import json
import statistics
import time
from typing import Any

from benchmarks.suites.parser_benchmarks import _generate_source
from watchllm_kernel.engine import evaluate_source
from watchllm_kernel.rules.auth_flow import AuthFlowRule
from watchllm_kernel.rules.boundary import BoundaryRule
from watchllm_kernel.rules.forbidden_imports import ForbiddenImportRule
from watchllm_kernel.rules.secrets import SecretLiteralRule


PIPELINE_RULES: tuple = (
    SecretLiteralRule(),
    BoundaryRule(),
    ForbiddenImportRule(),
    AuthFlowRule(),
)

BENCH_FILE_SIZES: tuple[int, ...] = (100, 500, 1_000)

TRIALS_PER_SIZE = 50


def _measure_e2e(
    source: str,
    *,
    file_path: str = "bench.js",
    warmup: int = 2,
    trials: int = TRIALS_PER_SIZE,
) -> dict[str, Any]:
    """Run the full kernel pipeline against *source* and return latency stats.

    Includes parsing + all rule evaluations in every trial.
    """
    # Warmup
    for _ in range(warmup):
        evaluate_source(
            source,
            file_path=file_path,
            language="javascript",
            rules=PIPELINE_RULES,
            mode="enforce",
        )

    samples: list[float] = []
    for _ in range(trials):
        t0 = time.perf_counter()
        evaluate_source(
            source,
            file_path=file_path,
            language="javascript",
            rules=PIPELINE_RULES,
            mode="enforce",
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        samples.append(elapsed_ms)

    samples.sort()
    return {
        "lines": len(source.splitlines()),
        "trials": len(samples),
        "p50_ms": round(statistics.median(samples), 3),
        "p95_ms": round(_percentile(samples, 95), 3),
        "p99_ms": round(_percentile(samples, 99), 3),
        "min_ms": round(samples[0], 3),
        "max_ms": round(samples[-1], 3),
        "mean_ms": round(statistics.mean(samples), 3),
        "stdev_ms": round(statistics.stdev(samples), 3) if len(samples) >= 2 else 0.0,
        "slo_10ms": round(sum(1 for s in samples if s <= 10.0) / len(samples) * 100, 1),
    }


def _percentile(sorted_data: list[float], p: float) -> float:
    """Return the p-th percentile from sorted data using linear interpolation."""
    if not sorted_data:
        return 0.0
    k = (len(sorted_data) - 1) * (p / 100.0)
    f = int(k)
    c = k - f
    if f + 1 < len(sorted_data):
        return sorted_data[f] + c * (sorted_data[f + 1] - sorted_data[f])
    return sorted_data[f]


def run_e2e_benchmarks(
    file_sizes: tuple[int, ...] = BENCH_FILE_SIZES,
) -> list[dict[str, Any]]:
    """Run end-to-end pipeline benchmarks and return per-size stats."""
    results: list[dict[str, Any]] = []
    for size in file_sizes:
        source = _generate_source(size)
        entry = _measure_e2e(source, file_path=f"bench_{size}.js")
        results.append(entry)
    return results


def print_e2e_results(results: list[dict[str, Any]]) -> None:
    """Pretty-print E2E pipeline benchmark results with SLO check."""
    print("\n  End-to-End Pipeline Benchmarks")
    print(f"  Rules active: {', '.join(r.__class__.__name__ for r in PIPELINE_RULES)}")
    print(f"  Trials per size: {TRIALS_PER_SIZE}")
    print()

    header = (
        f"  {'Lines':>6s}  {'P50':>10s}  {'P95':>10s}  {'P99':>10s}"
        f"  {'Mean':>10s}  {'SLO%':>8s}"
    )
    print(header)
    print(f"  {'─'*6}  {'─'*10}  {'─'*10}  {'─'*10}  {'─'*10}  {'─'*8}")

    for entry in results:
        lines = entry["lines"]
        p50 = f"{entry['p50_ms']:.3f} ms"
        p95 = f"{entry['p95_ms']:.3f} ms"
        p99 = f"{entry['p99_ms']:.3f} ms"
        mean = f"{entry['mean_ms']:.3f} ms"
        slo = f"{entry['slo_10ms']:.1f}%"
        print(f"  {lines:>6d}  {p50:>10s}  {p95:>10s}  {p99:>10s}  {mean:>10s}  {slo:>8s}")

    print()
    _1k = next((r for r in results if r["lines"] == 1000), None)
    if _1k:
        within = "✅" if _1k["p50_ms"] <= 10.0 else "❌"
        print(
            f"  10ms SLO check (1k lines, P50): {_1k['p50_ms']:.3f} ms  {within}"
        )


def export_json_report(results: list[dict[str, Any]]) -> str:
    """Return a full JSON regression report."""
    report = {
        "benchmark": "watchllm-e2e-pipeline",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rules": [r.__class__.__name__ for r in PIPELINE_RULES],
        "trials_per_size": TRIALS_PER_SIZE,
        "results": results,
    }
    return json.dumps(report, indent=2)