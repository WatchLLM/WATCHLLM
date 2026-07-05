"""Click CLI for the reliability harness."""

import shlex
import sys
from pathlib import Path

import click

from reliability.registry import default_registry, SuiteRegistry
from reliability.loader import load_all_suites
from reliability.runner import AgentRunner
from reliability.schema import TestCase
from reliability.scoring import (
    TestOutcome,
    calculate_score_report,
    format_score_report,
)
from reliability.suites.kernel_enforcement import KernelEnforcementSuite
from reliability.suites.prompt_injection import PromptInjectionSuite
from reliability.suites.tool_abuse import ToolAbuseSuite
from reliability.reporter import write_junit_report


_registry: SuiteRegistry = default_registry()

_EXPECTED_VIOLATION_TO_SUITE = {
    "secret-leak": "prompt-injection",
    "architectural-violation": "kernel-enforcement",
    "tool-abuse": "tool-abuse",
}


def _suite_for_case(test_case: TestCase) -> str | None:
    return _EXPECTED_VIOLATION_TO_SUITE.get(test_case.expected_violation)


def _default_agent_command() -> list[str]:
    return [
        sys.executable,
        "-c",
        "print('blocked by safety policy')",
    ]


def _command_from_option(agent_command: str | None) -> list[str]:
    if not agent_command:
        return _default_agent_command()

    command = shlex.split(agent_command)
    if not command:
        raise click.ClickException("--agent-command must not be empty")
    return command


def _run_case_for_score(
    suite_name: str,
    test_case: TestCase,
    command: list[str],
) -> TestOutcome:
    runner = AgentRunner(timeout=test_case.timeout)

    if suite_name == "prompt-injection":
        result = PromptInjectionSuite(runner).run_case(test_case, command)
    elif suite_name == "kernel-enforcement":
        result = KernelEnforcementSuite(runner).run_case(test_case, command)
    elif suite_name == "tool-abuse":
        result = ToolAbuseSuite(runner).run_case(test_case, command)
    else:
        raise click.ClickException(f"Unsupported suite for scoring: {suite_name}")

    return TestOutcome(
        suite_name=suite_name,
        test_name=test_case.name,
        passed=result.passed,
    )


@click.group()
def cli() -> None:
    """WatchLLM Reliability Stress Harness."""


@cli.command()
def list() -> None:
    """List all registered test suites and loaded test cases."""
    # Print registered suites
    click.echo("Registered suites:")
    for suite in _registry.all():
        click.echo(f"  {suite.name}  -  {suite.description}")

    # Load and print test cases from YAML suites
    suites_dir = Path("suites")
    cases = load_all_suites(suites_dir)
    if cases:
        click.echo("\nLoaded test cases:")
        for case in cases:
            desc = f" ({case.description})" if case.description else ""
            click.echo(f"  {case.name}{desc}")
    else:
        click.echo("\nNo test cases loaded from suites directory.")


@cli.command()
@click.option("--suite", default="all", help="Suite name to run (default: all)")
@click.option(
    "--suites-dir",
    default="suites",
    show_default=True,
    help="Directory containing YAML suite definitions.",
)
@click.option(
    "--agent-command",
    default=None,
    help="Target agent command to execute. Defaults to a safe simulated agent.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "junit"]),
    default="text",
    show_default=True,
    help="Report format to emit.",
)
@click.option(
    "--output",
    "output_path",
    default="reliability-report.xml",
    show_default=True,
    help="Output path for JUnit XML reports.",
)
@click.option(
    "--threshold",
    default=0.0,
    show_default=True,
    type=float,
    help="Minimum acceptable Safety Index. Exits with code 1 if below this value.",
)
def run(
    suite: str,
    suites_dir: str,
    agent_command: str | None,
    output_format: str,
    output_path: str,
    threshold: float,
) -> None:
    """Run selected test suites."""
    if suite == "all":
        selected = _registry.all()
    else:
        info = _registry.get(suite)
        if info is None:
            raise click.BadParameter(f"Unknown suite: {suite}")
        selected = [info]

    click.echo("Selected suites:")
    for s in selected:
        click.echo(f"  {s.name}")

    selected_names = {s.name for s in selected}
    cases = load_all_suites(Path(suites_dir))
    command = _command_from_option(agent_command)

    outcomes: list[TestOutcome] = []

    for case in cases:
        suite_name = _suite_for_case(case)
        if suite_name is None or suite_name not in selected_names:
            continue

        outcomes.append(_run_case_for_score(suite_name, case, command))

    report = calculate_score_report(
        outcomes,
        suite_names=selected_names,
    )

    click.echo("")
    click.echo(format_score_report(report))

    if output_format == "junit":
        written_path = write_junit_report(outcomes, report, output_path)
        click.echo(f"JUnit report written to: {written_path}")

    if report.safety_index < threshold:
        raise click.exceptions.Exit(1)
