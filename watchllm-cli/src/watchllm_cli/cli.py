"""Unified CLI entrypoint for the WatchLLM ecosystem.

Provides a single ``watchllm`` command that wraps all subsystems:

    watchllm init        — initialise a project for WatchLLM governance
    watchllm status      — check health of all installed components
    watchllm evaluate    — run the kernel against a source file
    watchllm spawn       — launch an agent with identity token injection
"""

from __future__ import annotations

import importlib
import io
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

console = Console()

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

try:
    from watchllm_cli import __version__
except ImportError:
    __version__ = "0.0.0"


# ---------------------------------------------------------------------------
# Shared branding helpers
# ---------------------------------------------------------------------------

WATCHLLM_ASCII_ART = """\
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░  ░░░░  ░░░      ░░░        ░░░      ░░░  ░░░░  ░░  ░░░░░░░░  ░░░░░░░░  ░░░░  ░
▒  ▒  ▒  ▒▒  ▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒▒▒▒▒  ▒▒▒▒▒▒▒▒   ▒▒   ▒
▓        ▓▓  ▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓▓▓▓        ▓▓  ▓▓▓▓▓▓▓▓  ▓▓▓▓▓▓▓▓        ▓
█   ██   ██        █████  █████  ████  ██  ████  ██  ████████  ████████  █  █  █
█  ████  ██  ████  █████  ██████      ███  ████  ██        ██        ██  ████  █
████████████████████████████████████████████████████████████████████████████████"""

WATCHLLM_ASCII_FALLBACK = "W A T C H L L M"


def _print_header(subcommand: Optional[str] = None) -> None:
    """Print the consistent WatchLLM signature header before every command."""
    console.print()
    try:
        console.print(f"[bold cyan]{WATCHLLM_ASCII_ART}[/bold cyan]")
    except UnicodeEncodeError:
        console.print(f"[bold cyan]{WATCHLLM_ASCII_FALLBACK}[/bold cyan]")

    subtitle = Text()
    subtitle.append("Governance-aware orchestration for autonomous coding agents", style="dim")
    subtitle.append("  ·  ", style="dim")
    subtitle.append(f"v{__version__}", style="bold cyan")

    if subcommand:
        subtitle.append("  ·  ", style="dim")
        subtitle.append(subcommand, style="bold magenta")

    console.print(subtitle)
    console.print(Rule(style="cyan dim"))
    console.print()


def _print_error(title: str, message: str, hint: Optional[str] = None) -> None:
    """Print a consistently styled error panel."""
    body = f"[bold white]{message}[/bold white]"
    if hint:
        body += f"\n\n[dim]{hint}[/dim]"
    console.print(Panel(body, title=f"[bold red]  {title}[/bold red]", border_style="red", expand=False))
    console.print()


# ---------------------------------------------------------------------------
# Custom Click group that intercepts errors for styled output
# ---------------------------------------------------------------------------

class WatchLLMGroup(click.Group):
    """Click group that prints the signature header and rich-formats errors."""

    def invoke(self, ctx: click.Context) -> None:  # type: ignore[override]
        # Print header for every invocation that has a real subcommand.
        # (The bare `watchllm` case is handled in the callback.)
        if ctx.protected_args or ctx.args:
            subcommand_name = (ctx.protected_args + ctx.args)[0]
            _print_header(subcommand_name)
        try:
            super().invoke(ctx)
        except click.MissingParameter as exc:
            _print_error(
                "Missing Parameter",
                str(exc.format_message()),
                hint=f"Run [bold cyan]watchllm {ctx.invoked_subcommand or ''} -h[/bold cyan] to see all available options.",
            )
            sys.exit(2)
        except click.UsageError as exc:
            _print_error(
                "Usage Error",
                exc.format_message(),
                hint=f"Run [bold cyan]watchllm {ctx.invoked_subcommand or ''} -h[/bold cyan] to see all available options.",
            )
            sys.exit(2)

    def resolve_command(
        self, ctx: click.Context, args: list
    ):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError as exc:
            # Unknown command — show a styled header then a nice error
            _print_header()
            attempted = args[0] if args else "?"
            _print_error(
                "Unknown Command",
                f"[bold yellow]{attempted}[/bold yellow] is not a recognised watchllm command.",
                hint="Run [bold cyan]watchllm -h[/bold cyan] to see available commands.",
            )
            sys.exit(2)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group(
    cls=WatchLLMGroup,
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
)
@click.version_option(version=__version__, prog_name="watchllm")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """WatchLLM — Governance-aware orchestration for autonomous coding agents."""
    if ctx.invoked_subcommand is None:
        _print_header()
        click.echo(ctx.get_help())


# ---------------------------------------------------------------------------
# watchllm init
# ---------------------------------------------------------------------------


def _write_default_config(target: Path) -> None:
    """Write the default .watchllm.toml template."""
    from watchllm_kernel.config import DEFAULT_CONFIG_TEMPLATE

    target.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")


@cli.command("init")
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite existing .watchllm.toml if present.",
)
def init_cmd(force: bool) -> None:
    """Initialise a project for WatchLLM governance.

    Creates the .watchllm/ directory structure, generates a default
    .watchllm.toml config, and runs klyd init if available.
    """
    project_root = Path.cwd()

    # --- .watchllm/ directory ---
    watchllm_dir = project_root / ".watchllm"
    logs_dir = watchllm_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"  [bold green]✓[/bold green]  Created [cyan]{watchllm_dir}/[/cyan]")

    # --- .watchllm.toml config ---
    config_file = project_root / ".watchllm.toml"
    if config_file.exists() and not force:
        console.print(f"  [bold yellow]~[/bold yellow]  [cyan]{config_file.name}[/cyan] already exists  [dim](use --force to overwrite)[/dim]")
    else:
        _write_default_config(config_file)
        console.print(f"  [bold green]✓[/bold green]  Created [cyan]{config_file.name}[/cyan]")

    # --- klyd init ---
    try:
        kl_path = shutil.which("kl")
        if kl_path:
            result = subprocess.run(
                [kl_path, "init"],
                capture_output=True,
                text=True,
                cwd=project_root,
            )
            if result.returncode == 0:
                console.print("  [bold green]✓[/bold green]  klyd initialised  [dim](.klyd/ directory + git hooks)[/dim]")
            else:
                stderr = result.stderr.strip()
                if "already" in stderr.lower():
                    console.print("  [bold yellow]~[/bold yellow]  klyd already initialised")
                else:
                    console.print(f"  [bold red]✗[/bold red]  klyd init returned exit {result.returncode}: {stderr}")
        else:
            console.print("  [bold yellow]~[/bold yellow]  klyd not installed  [dim](run: pip install -e klyd/)[/dim]")
    except Exception as exc:
        console.print(f"  [bold red]✗[/bold red]  klyd init failed: {exc}")

    console.print()
    console.print(Panel(
        "[bold green]WatchLLM Initialised Successfully![/bold green]\n\n"
        "Run [bold cyan]watchllm status[/bold cyan] to verify your installation.",
        border_style="green",
        expand=False,
    ))


# ---------------------------------------------------------------------------
# watchllm status
# ---------------------------------------------------------------------------


def _check_module(name: str, import_path: str) -> tuple[str, str, bool]:
    """Try to import a module and return (name, version, ok)."""
    try:
        mod = importlib.import_module(import_path)
        version = getattr(mod, "__version__", "installed")
        return (name, version, True)
    except ImportError:
        return (name, "not installed", False)


def _check_command(name: str, cmd: list[str]) -> tuple[str, str, bool]:
    """Try to run a command and return (name, version/status, ok)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        version = result.stdout.strip().split("\n")[0] if result.stdout.strip() else "available"
        return (name, version, True)
    except FileNotFoundError:
        return (name, "not found", False)
    except subprocess.TimeoutExpired:
        return (name, "timeout", False)
    except Exception as exc:
        return (name, str(exc), False)


@cli.command("status")
def status_cmd() -> None:
    """Check the health of all installed WatchLLM components."""
    table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 2))
    table.add_column("Component", style="cyan", width=20)
    table.add_column("Status", width=10)
    table.add_column("Details", style="dim")

    all_ok = True

    # Python components
    components = [
        ("Kernel", "watchllm_kernel"),
        ("klyd", "klyd"),
        ("Orchestrator", "orchestrator"),
    ]

    for name, import_path in components:
        label, version, ok = _check_module(name, import_path)
        status_text = "[bold green]● OK[/bold green]" if ok else "[bold red]● MISSING[/bold red]"
        details_text = version if ok else "not installed"
        table.add_row(label, status_text, details_text)
        if not ok:
            all_ok = False

    # Rust runtime (optional)
    label, version, ok = _check_command("Runtime (Rust)", ["watchllm-cli", "--version"])
    status_text = "[bold green]● OK[/bold green]" if ok else "[bold yellow]● SKIP[/bold yellow]"
    details_text = version if ok else "not built"
    table.add_row("Runtime (Rust)", status_text, details_text)

    # Config file
    try:
        from watchllm_kernel.config import load_config
        config = load_config()
        if config.config_path:
            table.add_row("Config", "[bold green]● OK[/bold green]", str(config.config_path))
        else:
            table.add_row("Config", "[bold yellow]● SKIP[/bold yellow]", "no .watchllm.toml found")
    except ImportError:
        table.add_row("Config", "[bold red]● ERROR[/bold red]", "watchllm_kernel not found")

    # klyd database
    klyd_db = Path.cwd() / ".klyd" / "memory.db"
    if klyd_db.exists():
        table.add_row("klyd Memory", "[bold green]● OK[/bold green]", ".klyd/memory.db")
    else:
        table.add_row("klyd Memory", "[bold yellow]● SKIP[/bold yellow]", "not initialised")

    console.print(Panel(table, title="[bold]Component Status[/bold]", border_style="cyan"))
    console.print()

    if all_ok:
        console.print("[bold green]✓  All core components installed and ready.[/bold green]")
    else:
        console.print("[bold red]✗  Some components are missing. See table above.[/bold red]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# watchllm evaluate
# ---------------------------------------------------------------------------


@cli.command("evaluate")
@click.argument("file", required=False)
@click.option("--stdin", is_flag=True, help="Read source from stdin instead of a file path.")
@click.option("--language", default=None, help="Language identifier (e.g. javascript, typescript).")
@click.option(
    "--mode",
    type=click.Choice(["enforce", "shadow"]),
    default=None,
    help="Evaluation mode. Overrides .watchllm.toml.",
)
@click.option("--json", "output_json", is_flag=True, help="Output result as JSON.")
@click.option("--config", "config_path", default=None, help="Path to .watchllm.toml config file.")
@click.pass_context
def evaluate_cmd(
    ctx: click.Context,
    file: Optional[str],
    stdin: bool,
    language: Optional[str],
    mode: Optional[str],
    output_json: bool,
    config_path: Optional[str],
) -> None:
    """Evaluate a source file against WatchLLM governance rules."""
    from watchllm_kernel.cli import main as kernel_main

    if not stdin and not file:
        _print_error(
            "Missing Argument",
            "Either a [bold cyan]file path[/bold cyan] or the [bold cyan]--stdin[/bold cyan] flag is required.",
            hint="Example: [bold cyan]watchllm evaluate src/agent.py[/bold cyan]",
        )
        ctx.exit(2)
        return

    target_label = "<stdin>" if stdin else str(file)
    console.print(f"[dim]Evaluating[/dim] [bold cyan]{target_label}[/bold cyan]  "
                  f"[dim]mode:[/dim] [magenta]{mode or 'default'}[/magenta]\n")

    # Build the argv list that the kernel CLI expects.
    argv = ["evaluate"]
    if stdin:
        argv.append("--stdin")
    elif file:
        argv.append(file)
    if language:
        argv.extend(["--language", language])
    if mode:
        argv.extend(["--mode", mode])
    if output_json:
        argv.append("--json")
    if config_path:
        argv.extend(["--config", config_path])

    # Capture the kernel output so we can wrap it in Rich
    old_stdout = sys.stdout
    captured_io = io.StringIO()
    sys.stdout = captured_io
    try:
        exit_code = kernel_main(argv)
    finally:
        sys.stdout = old_stdout

    output = captured_io.getvalue()

    if output_json:
        # Syntax-highlight JSON if on a TTY, otherwise pass through for piping
        if sys.stdout.isatty():
            console.print(Syntax(output, "json", theme="monokai", word_wrap=True))
        else:
            print(output, end="")
    else:
        if exit_code == 0:
            console.print(Panel(
                output.strip() or "[dim]No output[/dim]",
                title="[bold green]  Evaluation Passed[/bold green]",
                border_style="green",
                expand=False,
            ))
        else:
            console.print(Panel(
                output.strip() or "[dim]No output[/dim]",
                title="[bold red]  Evaluation Failed[/bold red]",
                border_style="red",
                expand=False,
            ))

    ctx.exit(exit_code)


# ---------------------------------------------------------------------------
# watchllm spawn
# ---------------------------------------------------------------------------


@cli.command("spawn")
@click.option("--role", default=None, help="Agent role to embed in the orchestrator token.")
@click.option("--command", "agent_command", default=None, help='Command to launch, e.g. "aider".')
@click.option(
    "--permissions",
    default="read-write",
    show_default=True,
    help="Permissions claim to encode in the token.",
)
@click.option(
    "--expires-minutes",
    default=60,
    show_default=True,
    type=click.IntRange(min=1),
    help="Token lifetime in minutes.",
)
@click.pass_context
def spawn_cmd(
    ctx: click.Context,
    role: Optional[str],
    agent_command: Optional[str],
    permissions: str,
    expires_minutes: int,
) -> None:
    """Spawn an agent process with WATCHLLM_AGENT_TOKEN injected."""
    errors = []
    if not role:
        errors.append("  [bold yellow]--role[/bold yellow]     The identity role for this agent session  [dim](e.g. dev, reviewer)[/dim]")
    if not agent_command:
        errors.append("  [bold yellow]--command[/bold yellow]  The command to launch  [dim](e.g. aider, python agent.py)[/dim]")

    if errors:
        body = "[bold white]The following required options are missing:[/bold white]\n\n"
        body += "\n".join(errors)
        body += "\n\n[dim]Example:[/dim]\n  [bold cyan]watchllm spawn --role dev --command aider[/bold cyan]"
        console.print(Panel(body, title="[bold red]  Missing Options[/bold red]", border_style="red", expand=False))
        ctx.exit(2)
        return

    console.print(Panel(
        f"[dim]Agent Command:[/dim]  [bold cyan]{agent_command}[/bold cyan]\n"
        f"[dim]Identity Role:[/dim]  [bold magenta]{role}[/bold magenta]\n"
        f"[dim]Permissions:  [/dim]  [green]{permissions}[/green]\n"
        f"[dim]Token TTL:    [/dim]  [yellow]{expires_minutes} min[/yellow]",
        title="[bold blue]  Session Gateway[/bold blue]",
        border_style="blue",
        expand=False,
    ))
    console.print()

    try:
        from orchestrator.spawner import AgentSpawner
        exit_code = AgentSpawner().spawn(
            role=role,
            command=agent_command,
            permissions=permissions,
            expires_minutes=expires_minutes,
        )
    except ImportError:
        _print_error(
            "Orchestrator Not Installed",
            "The [bold cyan]watchllm-orchestrator[/bold cyan] package is not installed.",
            hint="Run: [bold cyan]pip install -e orchestrator/[/bold cyan]",
        )
        ctx.exit(1)
        return
    except ValueError as exc:
        _print_error("Spawn Error", str(exc))
        ctx.exit(1)
        return

    ctx.exit(exit_code)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
