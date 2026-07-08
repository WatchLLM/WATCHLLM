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
from rich import box as rich_box
from rich.console import Console
from rich.panel import Panel
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

def _header_title(subcommand: Optional[str] = None) -> Text:
    """Build the panel title: 'watchllm  ·  <subcommand>'."""
    t = Text()
    t.append(" watchllm ", style="bold cyan")
    if subcommand:
        t.append("  ·  ", style="dim")
        t.append(subcommand, style="bold magenta")
    t.append(f"  v{__version__}", style="dim")
    t.append(" ")
    return t


def _make_panel(content, subcommand: Optional[str] = None, border_style: str = "cyan") -> Panel:
    """Wrap any Rich renderable in the signature WatchLLM panel."""
    return Panel(
        content,
        title=_header_title(subcommand),
        title_align="left",
        border_style=border_style,
        box=rich_box.ROUNDED,
        padding=(1, 2),
    )


def _print_panel(content, subcommand: Optional[str] = None, border_style: str = "cyan") -> None:
    console.print(_make_panel(content, subcommand, border_style))


def _print_error(subcommand: str, title: str, message: str, hint: Optional[str] = None) -> None:
    body = Text()
    body.append(f"  {title}\n\n", style="bold red")
    body.append(message)
    if hint:
        body.append(f"\n\n{hint}", style="dim")
    _print_panel(body, subcommand=subcommand, border_style="red")


# ---------------------------------------------------------------------------
# Custom Click group that intercepts errors for styled output
# ---------------------------------------------------------------------------

class WatchLLMGroup(click.Group):
    """Click group that always wraps output in the signature panel."""

    def resolve_command(self, ctx: click.Context, args: list):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            attempted = args[0] if args else "?"
            _print_error(
                attempted,
                "Unknown Command",
                f"'{attempted}' is not a recognised watchllm command.",
                hint=f"Run  watchllm -h  to see available commands.",
            )
            sys.exit(2)

    def invoke(self, ctx: click.Context) -> None:  # type: ignore[override]
        try:
            super().invoke(ctx)
        except click.MissingParameter as exc:
            subcmd = ctx.invoked_subcommand or ""
            _print_error(
                subcmd,
                "Missing Parameter",
                exc.format_message(),
                hint=f"Run  watchllm {subcmd} -h  to see all options.",
            )
            sys.exit(2)
        except click.UsageError as exc:
            subcmd = ctx.invoked_subcommand or ""
            _print_error(
                subcmd,
                "Usage Error",
                exc.format_message(),
                hint=f"Run  watchllm {subcmd} -h  to see all options.",
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
        _print_panel(
            Text.from_markup(
                "[bold white]Governance-aware orchestration for autonomous coding agents.[/bold white]\n\n"
                + ctx.get_help()
            )
        )


# ---------------------------------------------------------------------------
# watchllm init
# ---------------------------------------------------------------------------


def _write_default_config(target: Path) -> None:
    """Write the default .watchllm.toml template."""
    from watchllm_kernel.config import DEFAULT_CONFIG_TEMPLATE
    target.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")


@cli.command("init")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing .watchllm.toml if present.")
def init_cmd(force: bool) -> None:
    """Initialise a project for WatchLLM governance."""
    project_root = Path.cwd()
    lines = Text()

    # --- .watchllm/ directory ---
    watchllm_dir = project_root / ".watchllm"
    logs_dir = watchllm_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    lines.append("  ✓  ", style="bold green")
    lines.append("Created  ", style="bold white")
    lines.append(f"{watchllm_dir}/\n", style="cyan")

    # --- .watchllm.toml config ---
    config_file = project_root / ".watchllm.toml"
    if config_file.exists() and not force:
        lines.append("  ~  ", style="bold yellow")
        lines.append(f"{config_file.name}", style="cyan")
        lines.append(" already exists  ", style="bold white")
        lines.append("(--force to overwrite)\n", style="dim")
    else:
        _write_default_config(config_file)
        lines.append("  ✓  ", style="bold green")
        lines.append("Created  ", style="bold white")
        lines.append(f"{config_file.name}\n", style="cyan")

    # --- klyd init ---
    try:
        kl_path = shutil.which("kl")
        if kl_path:
            result = subprocess.run([kl_path, "init"], capture_output=True, text=True, cwd=project_root)
            if result.returncode == 0:
                lines.append("  ✓  ", style="bold green")
                lines.append("klyd initialised  ", style="bold white")
                lines.append("(.klyd/ + git hooks)\n", style="dim")
            else:
                stderr = result.stderr.strip()
                if "already" in stderr.lower():
                    lines.append("  ~  ", style="bold yellow")
                    lines.append("klyd already initialised\n", style="bold white")
                else:
                    lines.append("  ✗  ", style="bold red")
                    lines.append(f"klyd init exit {result.returncode}: {stderr}\n", style="bold white")
        else:
            lines.append("  ~  ", style="bold yellow")
            lines.append("klyd not installed  ", style="bold white")
            lines.append("(pip install -e klyd/)\n", style="dim")
    except Exception as exc:
        lines.append("  ✗  ", style="bold red")
        lines.append(f"klyd init failed: {exc}\n", style="bold white")

    lines.append("\n")
    lines.append("WatchLLM initialised.", style="bold green")
    lines.append("  Run ", style="")
    lines.append("watchllm status", style="bold cyan")
    lines.append(" to verify.", style="")

    _print_panel(lines, subcommand="init", border_style="green")


# ---------------------------------------------------------------------------
# watchllm status
# ---------------------------------------------------------------------------


def _check_module(name: str, import_path: str) -> tuple[str, str, bool]:
    try:
        mod = importlib.import_module(import_path)
        version = getattr(mod, "__version__", "installed")
        return (name, version, True)
    except ImportError:
        return (name, "not installed", False)


def _check_command(name: str, cmd: list[str]) -> tuple[str, str, bool]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
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
    table = Table(show_header=True, header_style="bold magenta", box=rich_box.SIMPLE, padding=(0, 2))
    table.add_column("Component", style="cyan", width=18)
    table.add_column("Status", width=12)
    table.add_column("Details", style="dim")

    all_ok = True

    for name, import_path in [("Kernel", "watchllm_kernel"), ("klyd", "klyd"), ("Orchestrator", "orchestrator")]:
        label, version, ok = _check_module(name, import_path)
        table.add_row(label, "[bold green]● OK[/bold green]" if ok else "[bold red]● MISSING[/bold red]", version if ok else "not installed")
        if not ok:
            all_ok = False

    label, version, ok = _check_command("Runtime (Rust)", ["watchllm-cli", "--version"])
    table.add_row("Runtime (Rust)", "[bold green]● OK[/bold green]" if ok else "[bold yellow]● SKIP[/bold yellow]", version if ok else "not built")

    try:
        from watchllm_kernel.config import load_config
        config = load_config()
        table.add_row("Config", "[bold green]● OK[/bold green]" if config.config_path else "[bold yellow]● SKIP[/bold yellow]", str(config.config_path) if config.config_path else "no .watchllm.toml found")
    except ImportError:
        table.add_row("Config", "[bold red]● ERROR[/bold red]", "watchllm_kernel not found")

    klyd_db = Path.cwd() / ".klyd" / "memory.db"
    table.add_row("klyd Memory", "[bold green]● OK[/bold green]" if klyd_db.exists() else "[bold yellow]● SKIP[/bold yellow]", ".klyd/memory.db" if klyd_db.exists() else "not initialised")

    summary = Text("\n")
    if all_ok:
        summary.append("  ✓  All core components installed and ready.", style="bold green")
    else:
        summary.append("  ✗  Some components are missing. See above.", style="bold red")

    from rich.console import Group as RenderGroup
    _print_panel(RenderGroup(table, summary), subcommand="status", border_style="cyan" if all_ok else "red")

    if not all_ok:
        sys.exit(1)


# ---------------------------------------------------------------------------
# watchllm evaluate
# ---------------------------------------------------------------------------


@cli.command("evaluate")
@click.argument("file", required=False)
@click.option("--stdin", is_flag=True, help="Read source from stdin instead of a file path.")
@click.option("--language", default=None, help="Language identifier (e.g. javascript, typescript).")
@click.option("--mode", type=click.Choice(["enforce", "shadow"]), default=None, help="Evaluation mode. Overrides .watchllm.toml.")
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
            "evaluate",
            "Missing Argument",
            "Provide a file path or use --stdin.",
            hint="Example:  watchllm evaluate src/agent.py",
        )
        ctx.exit(2)
        return

    target_label = "<stdin>" if stdin else str(file)

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

    old_stdout = sys.stdout
    captured_io = io.StringIO()
    sys.stdout = captured_io
    try:
        exit_code = kernel_main(argv)
    finally:
        sys.stdout = old_stdout

    output = captured_io.getvalue()

    if output_json and not sys.stdout.isatty():
        print(output, end="")
        ctx.exit(exit_code)
        return

    meta = Text()
    meta.append("file: ", style="dim")
    meta.append(target_label, style="cyan")
    meta.append("   mode: ", style="dim")
    meta.append(mode or "default", style="magenta")
    meta.append("\n\n")

    if output_json:
        from rich.console import Group as RenderGroup
        body = RenderGroup(meta, Syntax(output, "json", theme="monokai", word_wrap=True))
    else:
        body_text = Text.from_markup(output.strip() or "[dim]No output[/dim]")
        from rich.console import Group as RenderGroup
        body = RenderGroup(meta, body_text)

    border = "green" if exit_code == 0 else "red"
    result_label = "✓  evaluate" if exit_code == 0 else "✗  evaluate"
    console.print(Panel(
        body,
        title=_header_title(result_label),
        title_align="left",
        border_style=border,
        box=rich_box.ROUNDED,
        padding=(1, 2),
    ))

    ctx.exit(exit_code)


# ---------------------------------------------------------------------------
# watchllm spawn
# ---------------------------------------------------------------------------


@cli.command("spawn")
@click.option("--role", default=None, help="Agent role to embed in the orchestrator token.")
@click.option("--command", "agent_command", default=None, help='Command to launch, e.g. "aider".')
@click.option("--permissions", default="read-write", show_default=True, help="Permissions claim to encode in the token.")
@click.option("--expires-minutes", default=60, show_default=True, type=click.IntRange(min=1), help="Token lifetime in minutes.")
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
        errors.append(("--role", "Identity role for this agent session", "dev, reviewer, ci-bot"))
    if not agent_command:
        errors.append(("--command", "Command to launch under governance", "aider, python agent.py"))

    if errors:
        table = Table(show_header=True, header_style="bold red", box=rich_box.SIMPLE, padding=(0, 2))
        table.add_column("Option", style="yellow", width=14)
        table.add_column("Purpose")
        table.add_column("Example", style="dim")
        for flag, purpose, example in errors:
            table.add_row(flag, purpose, example)

        hint = Text("\nExample:  ", style="dim")
        hint.append("watchllm spawn --role dev --command aider", style="bold cyan")

        from rich.console import Group as RenderGroup
        body = RenderGroup(
            Text("The following required options are missing:\n", style="bold white"),
            table,
            hint,
        )
        console.print(Panel(
            body,
            title=_header_title("spawn"),
            title_align="left",
            border_style="red",
            box=rich_box.ROUNDED,
            padding=(1, 2),
        ))
        ctx.exit(2)
        return

    # Show the session gateway panel
    info = Text()
    info.append("  Agent Command  ", style="dim")
    info.append(f"{agent_command}\n", style="bold cyan")
    info.append("  Identity Role  ", style="dim")
    info.append(f"{role}\n", style="bold magenta")
    info.append("  Permissions    ", style="dim")
    info.append(f"{permissions}\n", style="green")
    info.append("  Token TTL      ", style="dim")
    info.append(f"{expires_minutes} min\n", style="yellow")

    _print_panel(info, subcommand="spawn", border_style="blue")

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
            "spawn",
            "Orchestrator Not Installed",
            "The watchllm-orchestrator package is not installed.",
            hint="Run:  pip install -e orchestrator/",
        )
        ctx.exit(1)
        return
    except ValueError as exc:
        _print_error("spawn", "Spawn Error", str(exc))
        ctx.exit(1)
        return

    ctx.exit(exit_code)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
