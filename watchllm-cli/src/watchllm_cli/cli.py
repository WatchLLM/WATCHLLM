"""Unified CLI entrypoint for the WatchLLM ecosystem.

Provides a single ``watchllm`` command that wraps all subsystems:

    watchllm init        — initialise a project for WatchLLM governance
    watchllm status      — check health of all installed components
    watchllm evaluate    — run the kernel against a source file
    watchllm spawn       — launch an agent with identity token injection
"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

try:
    from watchllm_cli import __version__
except ImportError:
    __version__ = "0.0.0"


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


WATCHLLM_ASCII_ART = """[bold cyan]░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░  ░░░░  ░░░      ░░░        ░░░      ░░░  ░░░░  ░░  ░░░░░░░░  ░░░░░░░░  ░░░░  ░
▒  ▒  ▒  ▒▒  ▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒▒▒▒▒  ▒▒▒▒▒▒▒▒   ▒▒   ▒
▓        ▓▓  ▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓▓▓▓        ▓▓  ▓▓▓▓▓▓▓▓  ▓▓▓▓▓▓▓▓        ▓
█   ██   ██        █████  █████  ████  ██  ████  ██  ████████  ████████  █  █  █
█  ████  ██  ████  █████  ██████      ███  ████  ██        ██        ██  ████  █
████████████████████████████████████████████████████████████████████████████████[/bold cyan]"""


WATCHLLM_FALLBACK_ART = """[bold cyan]
W A T C H L L M
Governance-aware orchestration for autonomous coding agents.
[/bold cyan]"""

@click.group(context_settings={"help_option_names": ["-h", "--help"]}, invoke_without_command=True)
@click.version_option(version=__version__, prog_name="watchllm")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """WatchLLM — Governance-aware orchestration for autonomous coding agents."""
    if ctx.invoked_subcommand is None:
        try:
            console.print(WATCHLLM_ASCII_ART)
        except UnicodeEncodeError:
            console.print(WATCHLLM_FALLBACK_ART)
        console.print()
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
    
    console.print("[bold blue]Initializing WatchLLM Governance...[/bold blue]\n")

    # --- .watchllm/ directory ---
    watchllm_dir = project_root / ".watchllm"
    logs_dir = watchllm_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"  [green][/[/green] Created [cyan]{watchllm_dir}/[/cyan]")

    # --- .watchllm.toml config ---
    config_file = project_root / ".watchllm.toml"
    if config_file.exists() and not force:
        console.print(f"  [yellow]?[/[/yellow] [cyan]{config_file.name}[/cyan] already exists (use --force to overwrite)")
    else:
        _write_default_config(config_file)
        console.print(f"  [green][/[/green] Created [cyan]{config_file.name}[/cyan]")

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
                console.print("  [green][/[/green] klyd initialised (.klyd/ directory + git hooks)")
            else:
                stderr = result.stderr.strip()
                if "already" in stderr.lower():
                    console.print("  [yellow]?[/[/yellow] klyd already initialised")
                else:
                    console.print(f"  [red]?[/[/red] klyd init returned exit {result.returncode}: {stderr}")
        else:
            console.print("  [yellow]?[/[/yellow] klyd not installed (run: pip install -e klyd/)")
    except Exception as exc:
        console.print(f"  [red]?[/[/red] klyd init failed: {exc}")

    console.print()
    console.print(Panel("[bold green]WatchLLM Initialised Successfully![/bold green]\n\nRun [bold cyan]watchllm status[/bold cyan] to verify your installation.", border_style="green", expand=False))


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
    table = Table(title="WatchLLM Component Status", show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan", width=20)
    table.add_column("Status", width=12)
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
        status_text = "[bold green]OK[/bold green]" if ok else "[bold red]MISSING[/bold red]"
        details_text = version if ok else "not installed"
        table.add_row(label, status_text, details_text)
        if not ok:
            all_ok = False

    # Rust runtime (optional)
    label, version, ok = _check_command("Runtime (Rust)", ["watchllm-cli", "--version"])
    status_text = "[bold green]OK[/bold green]" if ok else "[bold yellow]SKIP[/bold yellow]"
    details_text = version if ok else "not built"
    table.add_row("Runtime (Rust)", status_text, details_text)

    # Config file
    try:
        from watchllm_kernel.config import load_config
        config = load_config()
        if config.config_path:
            table.add_row("Config", "[bold green]OK[/bold green]", str(config.config_path))
        else:
            table.add_row("Config", "[bold yellow]SKIP[/bold yellow]", "no .watchllm.toml found")
    except ImportError:
        table.add_row("Config", "[bold red]ERROR[/bold red]", "watchllm_kernel not found")

    # klyd database
    klyd_db = Path.cwd() / ".klyd" / "memory.db"
    if klyd_db.exists():
        table.add_row("klyd Memory", "[bold green]OK[/bold green]", ".klyd/memory.db")
    else:
        table.add_row("klyd Memory", "[bold yellow]SKIP[/bold yellow]", "not initialised")

    console.print(table)
    console.print()
    
    if all_ok:
        console.print("[bold green]All core components installed and ready.[/bold green]")
    else:
        console.print("[bold red]Some components are missing. See table above.[/bold red]")
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
    """Evaluate a source file against WatchLLM governance rules.

    Wraps `watchllm-kernel evaluate` with config file auto-discovery.
    """
    from watchllm_kernel.cli import main as kernel_main

    import io
    from rich.syntax import Syntax

    # Build the argv list that the kernel CLI expects.
    argv = ["evaluate"]

    if stdin:
        argv.append("--stdin")
    elif file:
        argv.append(file)
    else:
        raise click.UsageError("Either a file path or --stdin is required.")

    if language:
        argv.extend(["--language", language])
    if mode:
        argv.extend(["--mode", mode])
    if output_json:
        argv.append("--json")
    if config_path:
        argv.extend(["--config", config_path])

    # Capture the output of kernel_main
    old_stdout = sys.stdout
    captured = io.StringIO()
    sys.stdout = captured
    
    try:
        exit_code = kernel_main(argv)
    finally:
        sys.stdout = old_stdout
        
    output = captured.getvalue()
    
    if output_json:
        if sys.stdout.isatty():
            console.print(Syntax(output, "json", theme="monokai", word_wrap=True))
        else:
            print(output, end="")
    else:
        if exit_code == 0:
            console.print(Panel(output.strip(), title="[bold green]Evaluation Passed[/bold green]", border_style="green", expand=False))
        else:
            console.print(Panel(output.strip(), title="[bold red]Evaluation Failed[/bold red]", border_style="red", expand=False))
            
    ctx.exit(exit_code)


# ---------------------------------------------------------------------------
# watchllm spawn
# ---------------------------------------------------------------------------


@cli.command("spawn")
@click.option("--role", required=True, help="Agent role to embed in the orchestrator token.")
@click.option("--command", "agent_command", required=True, help='Command to launch, e.g. "aider".')
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
    role: str,
    agent_command: str,
    permissions: str,
    expires_minutes: int,
) -> None:
    """Spawn an agent process with WATCHLLM_AGENT_TOKEN injected.

    Delegates to the orchestrator's agent spawner.
    """
    console.print(Panel(
        f"[bold blue]WatchLLM Orchestrator[/bold blue]\n"
        f"[dim]Spawning Agent:[/dim] [bold cyan]{agent_command}[/bold cyan]\n"
        f"[dim]Identity Role:[/dim] [bold magenta]{role}[/bold magenta]\n"
        f"[dim]Permissions:[/dim]   [green]{permissions}[/green]",
        title="Session Gateway", border_style="blue", expand=False
    ))
    
    try:
        from orchestrator.spawner import AgentSpawner

        # AgentSpawner().spawn uses subprocess to run the agent interactively.
        # We don't wrap this in a rich spinner because it will swallow stdout.
        exit_code = AgentSpawner().spawn(
            role=role,
            command=agent_command,
            permissions=permissions,
            expires_minutes=expires_minutes,
        )
    except ImportError:
        console.print("[bold red]watchllm-orchestrator is not installed.[/bold red] Run: [cyan]pip install -e orchestrator/[/cyan]")
        ctx.exit(1)
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        ctx.exit(1)

    ctx.exit(exit_code)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
