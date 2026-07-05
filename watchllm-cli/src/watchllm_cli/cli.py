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


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="watchllm")
def cli() -> None:
    """WatchLLM — Governance-aware orchestration for autonomous coding agents."""
    pass


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
    click.echo(f"  OK: Created {watchllm_dir}/")

    # --- .watchllm.toml config ---
    config_file = project_root / ".watchllm.toml"
    if config_file.exists() and not force:
        click.echo(f"  SKIP: {config_file.name} already exists (use --force to overwrite)")
    else:
        _write_default_config(config_file)
        click.echo(f"  OK: Created {config_file.name}")

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
                click.echo("  OK: klyd initialised (.klyd/ directory + git hooks)")
            else:
                # klyd init may fail if already initialised — that's fine.
                stderr = result.stderr.strip()
                if "already" in stderr.lower():
                    click.echo("  SKIP: klyd already initialised")
                else:
                    click.echo(f"  WARN: klyd init returned exit {result.returncode}: {stderr}")
        else:
            click.echo("  SKIP: klyd not installed (run: pip install -e klyd/)")
    except Exception as exc:
        click.echo(f"  WARN: klyd init failed: {exc}")

    click.echo()
    click.echo("WatchLLM initialised. Run `watchllm status` to verify.")


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
    click.echo("WatchLLM Component Status")
    click.echo("=" * 40)

    all_ok = True

    # Python components
    components = [
        ("Kernel", "watchllm_kernel"),
        ("klyd", "klyd"),
        ("Orchestrator", "orchestrator"),
    ]

    for name, import_path in components:
        label, version, ok = _check_module(name, import_path)
        status = click.style(f"OK: {version}", fg="green") if ok else click.style("MISSING: not installed", fg="red")
        click.echo(f"  {label:20s} {status}")
        if not ok:
            all_ok = False

    # Rust runtime (optional)
    label, version, ok = _check_command("Runtime (Rust)", ["watchllm-cli", "--version"])
    status = click.style(f"OK: {version}", fg="green") if ok else click.style("SKIP: not built", fg="yellow")
    click.echo(f"  {'Runtime (Rust)':20s} {status}")

    # Config file
    from watchllm_kernel.config import load_config

    config = load_config()
    if config.config_path:
        click.echo(f"  {'Config':20s} {click.style(f'OK: {config.config_path}', fg='green')}")
    else:
        click.echo(f"  {'Config':20s} {click.style('SKIP: no .watchllm.toml found', fg='yellow')}")

    # klyd database
    klyd_db = Path.cwd() / ".klyd" / "memory.db"
    if klyd_db.exists():
        click.echo(f"  {'klyd Memory':20s} {click.style('OK: .klyd/memory.db', fg='green')}")
    else:
        click.echo(f"  {'klyd Memory':20s} {click.style('SKIP: not initialised', fg='yellow')}")

    click.echo()
    if all_ok:
        click.echo(click.style("All core components installed.", fg="green"))
    else:
        click.echo(click.style("Some components are missing. See above.", fg="red"))
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

    exit_code = kernel_main(argv)
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
    try:
        from orchestrator.spawner import AgentSpawner

        exit_code = AgentSpawner().spawn(
            role=role,
            command=agent_command,
            permissions=permissions,
            expires_minutes=expires_minutes,
        )
    except ImportError:
        raise click.ClickException(
            "watchllm-orchestrator is not installed. Run: pip install -e orchestrator/"
        )
    except ValueError as exc:
        raise click.ClickException(str(exc))

    ctx.exit(exit_code)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
