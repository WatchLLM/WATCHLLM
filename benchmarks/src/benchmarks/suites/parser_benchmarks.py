"""Parser benchmarks — raw Tree-sitter parsing latency.

Measures ``watchllm_kernel.parser.parse_source`` time for JavaScript and
TypeScript files of varying sizes.  The suite generates synthetic source
of known line counts to keep measurements reproducible and self-contained.
"""

from __future__ import annotations

import time

from watchllm_kernel.parser import parse_source


BENCH_FILE_SIZES: tuple[int, ...] = (
    100,
    500,
    1_000,
    5_000,
    10_000,
)


def _generate_source(lines: int) -> str:
    r"""Build synthetic JavaScript source with *lines* non-blank lines.

    Each line is a simple ``const x_NNN = "value_NNN";\n`` assignment so
    Tree-sitter has real tokens to chew on without introducing external
    fixture files.
    """
    return "\n".join(
        f'const x_{i:04d} = "value_{i:04d}";' for i in range(lines)
    )


def _measure_one(size: int, *, warmup: int = 1, trials: int = 5) -> dict:
    """Benchmark parsing for a single file size.

    Returns a dict with lines, median_ms, min_ms, max_ms.
    """
    source = _generate_source(size)

    # Warmup round – parse once so grammar caches are hot.
    for _ in range(warmup):
        parse_source(source, language="javascript")

    samples: list[float] = []
    for _ in range(trials):
        t0 = time.perf_counter()
        parse_source(source, language="javascript")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        samples.append(elapsed_ms)

    samples.sort()
    return {
        "lines": size,
        "trials": trials,
        "median_ms": round(samples[len(samples) // 2], 3),
        "min_ms": round(samples[0], 3),
        "max_ms": round(samples[-1], 3),
    }


def run_parser_benchmarks(
    file_sizes: tuple[int, ...] = BENCH_FILE_SIZES,
) -> list[dict]:
    """Run parser latency benchmarks and return per-size result dicts."""
    results: list[dict] = []
    for size in file_sizes:
        entry = _measure_one(size)
        results.append(entry)
    return results


def print_parser_results(results: list[dict]) -> None:
    """Pretty-print parser benchmark results to stdout."""
    print("\n  Parser Benchmarks")
    print(f"  {'Lines':>6s}  {'Median':>10s}  {'Min':>10s}  {'Max':>10s}")
    print(f"  {'-'*6}  {'-'*10}  {'-'*10}  {'-'*10}")

    for entry in results:
        lines = entry["lines"]
        median = f"{entry['median_ms']:.3f} ms"
        min_v = f"{entry['min_ms']:.3f} ms"
        max_v = f"{entry['max_ms']:.3f} ms"
        print(f"  {lines:>6d}  {median:>10s}  {min_v:>10s}  {max_v:>10s}")

    # Check 10ms rule for 1k lines
    _1k = next((r for r in results if r["lines"] == 1000), None)
    if _1k:
        within = "✅" if _1k["median_ms"] <= 10.0 else "❌"
        print(
            f"\n  10ms SLO check (1k lines): {_1k['median_ms']:.3f} ms  {within}"
        )