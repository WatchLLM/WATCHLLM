"""benchmarks CLI — ``watchllm-benchmarks`` entrypoint."""

from __future__ import annotations

import click
import json
import time

from benchmarks import __version__
from benchmarks.suites import load_suites
from benchmarks.suites.e2e_benchmarks import export_json_report, run_e2e_benchmarks


def _format_ms(value: float) -> str:
    """Return *value* as a human-readable milliseconds string."""
    return f"{value:.3f} ms"


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="watchllm-benchmarks")
def main() -> None:
    """WatchLLM benchmark suite CLI."""


@main.command()
@click.option(
    "--json", "json_output", is_flag=True, help="Emit results as JSON."
)
def run(json_output: bool) -> None:
    """Run all registered benchmark suites."""
    suites = load_suites()

    if not suites:
        click.echo("No benchmark suites registered.")
        return

    results: dict[str, object] = {}
    total_start = time.perf_counter()

    for suite in suites:
        click.echo(f"\n[{suite.name}] {suite.description}")
        t0 = time.perf_counter()
        try:
            suite_result = suite.runner()
        except Exception as exc:
            click.echo(f"  ERROR: {exc}", err=True)
            suite_result = {"error": str(exc)}
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        click.echo(f"  Completed in {_format_ms(elapsed_ms)}")

        results[suite.name] = suite_result

    total_ms = (time.perf_counter() - total_start) * 1000.0
    click.echo(f"\nTotal wall-clock: {_format_ms(total_ms)}")

    if json_output:
        # Produce a regression-ready JSON report from the E2E data
        e2e_results = results.get("e2e")
        if isinstance(e2e_results, list):
            click.echo(
                export_json_report(e2e_results)
            )
        else:
            click.echo(
                json.dumps(results, indent=2, default=str)
            )