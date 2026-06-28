"""
watchllm — Unified entry point for the WatchLLM developer toolchain.

A premium terminal experience with live streaming, animated spinners,
color-coded status logs, interactive safety prompts, dry-runs,
session persistence, and graceful interrupt handling.

Commands:
  init        Generate a default .watchllm.yaml in the current directory.
  evaluate    Evaluate a file or stdin through the kernel.
  status      Report installation health of all WatchLLM subsystems.
  diff        Show a git-style unified diff of pending changes.
  preview     Dry-run: show what evaluate would do without enforcing.
  rollback    Undo the last file edit from the snapshot store.
  session     Manage persistent WatchLLM sessions (list/resume/clear).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Force UTF-8 for block/emoji characters on Windows
# ---------------------------------------------------------------------------
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# ---------------------------------------------------------------------------
# Rich ecosystem — the premium rendering engine
# ---------------------------------------------------------------------------
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich.layout import Layout
    from rich.columns import Columns
    from rich.rule import Rule
    from rich.spinner import Spinner
    from rich.progress import (
        Progress,
        SpinnerColumn,
        BarColumn,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )
    from rich.live import Live
    from rich.tree import Tree
    from rich.prompt import Confirm, Prompt
    from rich.status import Status

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ---------------------------------------------------------------------------
# Console instances
# ---------------------------------------------------------------------------
console = Console() if RICH_AVAILABLE else None
err_console = Console(stderr=True) if RICH_AVAILABLE else None

# ---------------------------------------------------------------------------
# Branding
# ---------------------------------------------------------------------------

LOGO = r"""
[bold bright_cyan]
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   ░██╗ ░░     ██╗    ██╗  ██████╗████████╗ ██████╗██╗  ██╗      ║
║   ░██║ ░░     ██║    ██║  ██╔═══╝╚══██╔══╝██╔════╝██║  ██║      ║
║   ░██║ ░░     ██║ █╗ ██║  ██║       ██║   ██║     ███████║      ║
║   ░██║ ░░     ██║███╗██║  ██║       ██║   ██║     ██╔══██║      ║
║   ░██████╗    ╚███╔███╔╝  ╚██████╗  ██║   ╚██████╗██║  ██║      ║
║   ░╚═════╝     ╚══╝╚══╝    ╚═════╝  ╚═╝    ╚═════╝╚═╝  ╚═╝      ║
║                                                                  ║
║     ██╗     ██╗     ██╗     ███╗   ███╗                         ║
║     ██║     ██║     ██║     ████╗ ████║                         ║
║     ██║     ██║     ██║     ██╔████╔██║                         ║
║     ██║     ██║     ██║     ██║╚██╔╝██║                         ║
║     ███████╗███████╗███████╗██║ ╚═╝ ██║                         ║
║     ╚══════╝╚══════╝╚══════╝╚═╝     ╚═╝                         ║
║                                                                  ║
║  Deterministic runtime governance for autonomous coding agents.   ║
╚══════════════════════════════════════════════════════════════════╝
[/bold bright_cyan]
"""

TAGLINE = "[italic bright_white]Deterministic runtime governance for autonomous coding agents.[/italic bright_white]"

# ---------------------------------------------------------------------------
# ANSI colour palette (fallback when Rich is unavailable)
# ---------------------------------------------------------------------------

C_GREEN = "\033[92m"
C_RED = "\033[91m"
C_YELLOW = "\033[93m"
C_CYAN = "\033[96m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_RESET = "\033[0m"


def _ok(msg: str) -> str:
    return f"{C_GREEN}✓{C_RESET} {msg}"


def _err(msg: str) -> str:
    return f"{C_RED}✗{C_RESET} {msg}"


def _warn(msg: str) -> str:
    return f"{C_YELLOW}⚠{C_RESET} {msg}"


def _info(msg: str) -> str:
    return f"{C_CYAN}→{C_RESET} {msg}"


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------

SESSION_DIR = Path.home() / ".watchllm" / "sessions"
SNAPSHOT_DIR = Path.home() / ".watchllm" / "snapshots"


def _ensure_dirs() -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(name: str) -> Path:
    _ensure_dirs()
    return SESSION_DIR / f"{name}.json"


def _snapshot_path(identifier: str) -> Path:
    _ensure_dirs()
    return SNAPSHOT_DIR / f"{identifier}.json"


def load_session(name: str = "default") -> dict:
    """Load a named session, or return an empty dict."""
    path = _session_path(name)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_session(name: str, data: dict) -> None:
    """Persist session data to disk."""
    path = _session_path(name)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def list_sessions() -> list[str]:
    """Return all known session names."""
    _ensure_dirs()
    return sorted(
        p.stem for p in SESSION_DIR.glob("*.json") if p.is_file()
    )


def clear_sessions() -> int:
    """Remove all sessions.  Returns count of deleted sessions."""
    _ensure_dirs()
    count = 0
    for p in SESSION_DIR.glob("*.json"):
        p.unlink()
        count += 1
    return count


def save_command_snapshot(command: str, affected_files: list[str]) -> str:
    """Save a rollback snapshot and return its id."""
    _ensure_dirs()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sid = f"snap-{ts}"
    snap = {
        "id": sid,
        "command": command,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "affected_files": affected_files,
        "backups": {},
    }
    for fp in affected_files:
        p = Path(fp)
        if p.exists():
            snap["backups"][fp] = p.read_text(encoding="utf-8")
    _snapshot_path(sid).write_text(json.dumps(snap, indent=2), encoding="utf-8")
    return sid


def load_last_snapshot() -> Optional[dict]:
    """Return the most recent snapshot or None."""
    _ensure_dirs()
    snaps = sorted(SNAPSHOT_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
    if snaps:
        return json.loads(snaps[0].read_text(encoding="utf-8"))
    return None


def apply_rollback(snapshot: dict) -> list[str]:
    """Restore files from snapshot.  Returns list of restored paths."""
    restored = []
    for fp, content in snapshot.get("backups", {}).items():
        Path(fp).write_text(content, encoding="utf-8")
        restored.append(fp)
    return restored


def clear_snapshots() -> int:
    """Remove all snapshots.  Returns count."""
    _ensure_dirs()
    count = 0
    for p in SNAPSHOT_DIR.glob("*.json"):
        p.unlink()
        count += 1
    return count


# ---------------------------------------------------------------------------
# Default config template
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = """# .watchllm.yaml — WatchLLM project configuration
# Generated by: watchllm init
#
# Customize rules per your project. Remove a section to use the built-in defaults.

rules:
  boundary:
    enabled: true
    severity: error
    map:
      auth:
        forbidden:
          - [db, internal]
        allowed:
          - [db, public]

  forbidden_imports:
    enabled: true
    severity: error
    modules:
      - child_process
      - vm
    forbidden_prefixes:
      - ../
      - ../../
      - ../../../
    allowed_relative_prefixes:
      - ../db/public
      - ../../db/public

  secrets:
    enabled: true
    severity: error

  auth_flow:
    enabled: true
    severity: error
"""

# ---------------------------------------------------------------------------
# Subsystem registry
# ---------------------------------------------------------------------------

SUBSYSTEMS = [
    {
        "name": "watchllm-kernel",
        "kind": "python",
        "check": "watchllm-kernel --help",
        "desc": "Deterministic AST-level rule engine",
    },
    {
        "name": "watchllm-cli",
        "kind": "rust",
        "check": "watchllm-cli --help",
        "desc": "Native Rust CLI accelerator",
    },
    {
        "name": "kl (klyd)",
        "kind": "python",
        "check": "kl --help",
        "desc": "Persistent architectural memory",
    },
    {
        "name": "replay",
        "kind": "node",
        "check": None,
        "desc": "Execution-graph observability UI",
    },
    {
        "name": "orchestrator",
        "kind": "python",
        "check": "watchllm-orchestrator --help",
        "desc": "Multi-agent workflow engine",
    },
]

# ---------------------------------------------------------------------------
# Rendering helpers (Rich wrappers)
# ---------------------------------------------------------------------------


def _render_banner() -> None:
    """Print the full brand banner."""
    if RICH_AVAILABLE:
        console.print(LOGO, justify="center")
        console.print(TAGLINE, justify="center")
        console.print()
    else:
        print(
            "\n  WatchLLM :: Deterministic runtime governance for autonomous coding agents.\n"
        )


def _render_header(title: str, subtitle: str = "") -> None:
    """Section header with optional subtitle."""
    if RICH_AVAILABLE:
        console.print(Rule(title=title, style="bold bright_cyan", align="left"))
        if subtitle:
            console.print(f"[dim]{subtitle}[/dim]")
    else:
        print(f"\n{C_CYAN}{C_BOLD}── {title} ──{C_RESET}")
        if subtitle:
            print(f"{C_DIM}{subtitle}{C_RESET}")
        print()


def _render_success(msg: str) -> None:
    if RICH_AVAILABLE:
        console.print(f"[bold green]✓[/bold green] {msg}")
    else:
        print(_ok(msg))


def _render_error(msg: str) -> None:
    if RICH_AVAILABLE:
        err_console.print(f"[bold red]✗[/bold red] {msg}")
    else:
        print(_err(msg), file=sys.stderr)


def _render_warning(msg: str) -> None:
    if RICH_AVAILABLE:
        console.print(f"[bold yellow]⚠[/bold yellow] {msg}")
    else:
        print(_warn(msg))


def _render_info(msg: str) -> None:
    if RICH_AVAILABLE:
        console.print(f"[bold cyan]→[/bold cyan] {msg}")
    else:
        print(_info(msg))


def _render_diff(old_text: str, new_text: str, old_label: str = "old", new_label: str = "new") -> None:
    """Render a rich unified diff between two strings."""
    if RICH_AVAILABLE:
        import difflib

        diff_lines = list(
            difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=old_label,
                tofile=new_label,
            )
        )
        if not diff_lines:
            _render_info("No differences found.")
            return

        diff_text = "".join(diff_lines)
        console.print(
            Syntax(diff_text, "diff", theme="monokai", line_numbers=False),
        )
    else:
        print(f"\n--- {old_label}\n+++ {new_label}\n")


def _render_code_block(code: str, language: str = "text") -> None:
    """Syntax-highlight a code block."""
    if RICH_AVAILABLE:
        console.print(
            Syntax(
                code,
                language,
                theme="monokai",
                line_numbers=True,
                word_wrap=True,
            )
        )
    else:
        print(code)


def _spinner_context(text: str):
    """Return a Rich Status spinner context manager, or a no-op."""
    if RICH_AVAILABLE:
        return console.status(f"[bold bright_cyan]{text}[/bold bright_cyan]", spinner="dots")
    else:
        from contextlib import nullcontext

        return nullcontext()


def _progress_context():
    """Return a Rich Progress bar context, or a no-op."""
    if RICH_AVAILABLE:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        )
        return progress
    else:
        from contextlib import nullcontext

        return nullcontext()


# ---------------------------------------------------------------------------
# Interactive safety helpers
# ---------------------------------------------------------------------------


def _confirm_destructive(action: str, details: str = "", default: bool = False) -> bool:
    """Ask for confirmation before a destructive operation."""
    if RICH_AVAILABLE:
        console.print()
        console.print(
            Panel(
                f"[bold yellow]⚠ Destructive Operation[/bold yellow]\n\n"
                f"[bold]{action}[/bold]\n"
                + (f"[dim]{details}[/dim]\n" if details else ""),
                border_style="yellow",
                title="Confirm",
            )
        )
        return Confirm.ask("Proceed?", default=default)
    else:
        prompt = f"\n{C_YELLOW}⚠ {action}{C_RESET}\n"
        if details:
            prompt += f"{C_DIM}{details}{C_RESET}\n"
        prompt += "Proceed? [y/N] "
        answer = input(prompt).strip().lower()
        return answer in ("y", "yes")


# ---------------------------------------------------------------------------
# Tab completion
# ---------------------------------------------------------------------------


def _setup_tab_completion():
    """Install shell tab-completion stubs (instruct only)."""
    if RICH_AVAILABLE:
        console.print()
        console.print(
            Panel(
                "[bold]Tab Completion Setup[/bold]\n\n"
                "Add one of these to your shell rc file:\n\n"
                "[cyan]Bash[/cyan] (append to ~/.bashrc):\n"
                "  eval \"$(_WATCHLLM_COMPLETE=bash_source watchllm)\"\n\n"
                "[cyan]Zsh[/cyan] (append to ~/.zshrc):\n"
                "  eval \"$(_WATCHLLM_COMPLETE=zsh_source watchllm)\"\n\n"
                "[cyan]Fish[/cyan]:\n"
                "  watchllm --install-completion fish",
                border_style="bright_cyan",
                title="Setup",
            )
        )
    else:
        print("Run: watchllm --install-completion <bash|zsh|fish>")


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> int:
    """Generate a default .watchllm.yaml in the target directory."""
    target_dir = Path(args.directory).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    config_path = target_dir / ".watchllm.yaml"

    if args.dry_run:
        _render_header("Dry-Run: init", f"Would create [bold]{config_path}[/bold]")
        _render_code_block(DEFAULT_CONFIG, "yaml")
        _render_success("Dry-run complete. No files were written.")
        return 0

    if config_path.exists() and not args.force:
        _render_warning(f"Config already exists: {config_path}")
        _render_info("Use --force to overwrite.")
        return 1

    with _spinner_context("Generating .watchllm.yaml..."):
        time.sleep(0.2)  # Brief pause so spinner is visible
        config_path.write_text(DEFAULT_CONFIG, encoding="utf-8")

    _render_success(f"Created: [bold]{config_path}[/bold]")
    if RICH_AVAILABLE:
        console.print()
        console.print(
            Panel(
                "Run [bold cyan]watchllm evaluate[/bold cyan] to start checking your code.\n"
                "Edit [bold bright_white].watchllm.yaml[/bold bright_white] to customize rules.",
                border_style="bright_cyan",
                title="Next Steps",
            )
        )
    return 0


# ---------------------------------------------------------------------------
# evaluate
# ---------------------------------------------------------------------------


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Evaluate a file (or stdin) through the kernel."""
    cmd = ["watchllm-kernel", "check", "--json"]

    if args.stdin:
        cmd.append("--stdin")
    elif args.file:
        cmd += ["--filepath", args.file]
    else:
        _render_error("Provide --file or --stdin")
        return 2

    if args.mode:
        cmd += ["--mode", args.mode]
    if args.language:
        cmd += ["--language", args.language]

    # Dry-run: preview without executing
    if args.dry_run:
        _render_header("Dry-Run: evaluate", "Preview of what would be checked")
        _render_info(f"Command: [bold]{' '.join(cmd)}[/bold]")
        if args.file:
            _render_info(f"File: [bold]{args.file}[/bold]")
            if Path(args.file).exists():
                content = Path(args.file).read_text(encoding="utf-8")
                _render_code_block(content, args.language or "text")
        _render_success("Dry-run complete. No checks were executed.")
        return 0

    _render_header("evaluate", f"Running kernel on [bold]{args.file or 'stdin'}[/bold]")

    progress = _progress_context()
    with progress:
        task = progress.add_task("[cyan]Evaluating...", total=100)
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120, check=False
            )
            progress.update(task, advance=100)
        except subprocess.TimeoutExpired:
            _render_error("Evaluation timed out (>120s)")
            return 2
        except FileNotFoundError:
            _render_error("watchllm-kernel not found. Run: [cyan]pip install -e d:/watchllm/kernel[/cyan]")
            return 2

    if result.returncode == 0:
        _render_success("All governance rules passed.")
        if result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                if RICH_AVAILABLE and data:
                    console.print(
                        Syntax(
                            json.dumps(data, indent=2),
                            "json",
                            theme="monokai",
                            line_numbers=False,
                        )
                    )
            except json.JSONDecodeError:
                if RICH_AVAILABLE:
                    console.print(result.stdout, style="dim")
    else:
        _render_error("Governance rule violations detected.")
        if RICH_AVAILABLE:
            console.print()
            panel_content = result.stderr if result.stderr else result.stdout
            console.print(
                Panel(
                    panel_content.strip() or "(no output)",
                    border_style="red",
                    title="Violations",
                )
            )
        else:
            print(result.stderr or result.stdout, file=sys.stderr)

    # Save snapshot for potential rollback
    affected = [args.file] if args.file else []
    if affected and Path(args.file).exists():
        sid = save_command_snapshot("evaluate", affected)
        _render_info(f"Snapshot saved: [dim]{sid}[/dim]")

    return result.returncode


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


def cmd_status(_args: argparse.Namespace) -> int:
    """Report installation health of all WatchLLM subsystems."""
    _render_banner()

    if not RICH_AVAILABLE:
        print("Rich not installed. Run: python d:/watchllm/bootstrap.py")
        return 1

    _render_header("System Status", "Installation health of all WatchLLM subsystems")

    table = Table(
        title=None,
        show_header=True,
        header_style="bold bright_cyan",
        border_style="bright_black",
        padding=(0, 2),
    )
    table.add_column("", width=2)
    table.add_column("Subsystem", style="bold")
    table.add_column("Kind", style="dim", width=8)
    table.add_column("Status", justify="center", width=12)
    table.add_column("Details", style="dim", max_width=40)

    all_ok = True
    for sub in SUBSYSTEMS:
        name = sub["name"]
        kind = sub["kind"]
        desc = sub.get("desc", "")
        check = sub.get("check")

        if check is None:
            table.add_row("", name, kind, "[yellow]SKIP[/yellow]", f"{desc} (no check)")
            continue

        parts = check.split()
        executable = parts[0]
        found = shutil.which(executable) is not None

        if found:
            table.add_row(
                "[green]●[/green]", name, kind, "[green]OK[/green]", desc
            )
        else:
            table.add_row(
                "[red]●[/red]", name, kind, "[red]MISSING[/red]", f"{executable} not found"
            )
            all_ok = False

    console.print(table)
    console.print()

    if all_ok:
        console.print(
            Panel(
                "[green]● All subsystems are operational.[/green]\n\n"
                "[dim]Your WatchLLM toolchain is ready.[/dim]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                "[red]● Some subsystems are missing.[/red]\n\n"
                "Run: [bold cyan]python d:/watchllm/bootstrap.py[/bold cyan]\n"
                "Then: [bold cyan]watchllm status[/bold cyan] to re-check.",
                border_style="red",
            )
        )
    return 0 if all_ok else 1


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------


def cmd_diff(args: argparse.Namespace) -> int:
    """Show a git-style diff against the last snapshot."""
    _render_header("Diff", "Changes since last snapshot")

    snap = load_last_snapshot()
    if not snap:
        _render_info("No snapshots found. Run [bold]evaluate[/bold] first to create one.")
        return 0

    if RICH_AVAILABLE:
        console.print(
            f"Snapshot: [bold]{snap['id']}[/bold]  "
            f"[dim]({snap['timestamp']})[/dim]  "
            f"Command: [cyan]{snap['command']}[/cyan]\n"
        )

    files = snap.get("affected_files", [])
    if not files:
        _render_info("No files in snapshot.")
        return 0

    for fp in files:
        p = Path(fp)
        if not p.exists():
            _render_warning(f"File missing: {fp}")
            continue

        current = p.read_text(encoding="utf-8")
        original = snap["backups"].get(fp, "")

        if RICH_AVAILABLE:
            console.print(Rule(title=f"[bold]{fp}[/bold]", style="bright_black"))
        else:
            print(f"\n--- {fp} ---")

        _render_diff(original, current, old_label=f"{fp} (before)", new_label=f"{fp} (now)")

    return 0


# ---------------------------------------------------------------------------
# preview (dry-run)
# ---------------------------------------------------------------------------


def cmd_preview(args: argparse.Namespace) -> int:
    """Dry-run an evaluate without enforcing rules."""
    # Reuse evaluate with dry_run=True
    new_args = argparse.Namespace(
        file=args.file,
        stdin=args.stdin,
        mode=args.mode,
        language=args.language,
        dry_run=True,
    )
    return cmd_evaluate(new_args)


# ---------------------------------------------------------------------------
# rollback
# ---------------------------------------------------------------------------


def cmd_rollback(_args: argparse.Namespace) -> int:
    """Undo the last file edit by restoring from snapshot."""
    _render_header("Rollback", "Restore files from the last snapshot")

    snap = load_last_snapshot()
    if not snap:
        _render_info("No snapshots to roll back.")
        return 0

    if RICH_AVAILABLE:
        console.print(
            Panel(
                f"[bold]Snapshot: {snap['id']}[/bold]\n"
                f"Created:   [dim]{snap['timestamp']}[/dim]\n"
                f"Command:   [cyan]{snap['command']}[/cyan]\n"
                f"Files:     [bold]{', '.join(snap.get('affected_files', ['none']))}[/bold]",
                border_style="yellow",
                title="Snapshot Details",
            )
        )

    if not _confirm_destructive(
        "Restore files from snapshot?",
        "This will overwrite current file contents with the snapshot versions.",
        default=False,
    ):
        _render_info("Rollback cancelled.")
        return 0

    with _spinner_context("Restoring files from snapshot..."):
        time.sleep(0.2)
        restored = apply_rollback(snap)

    for fp in restored:
        _render_success(f"Restored: [bold]{fp}[/bold]")

    _render_success(f"Rollback complete. {len(restored)} file(s) restored.")
    return 0


# ---------------------------------------------------------------------------
# session
# ---------------------------------------------------------------------------


def cmd_session(args: argparse.Namespace) -> int:
    """Manage persistent WatchLLM sessions."""
    if args.session_command == "list":
        _render_header("Sessions", "Persistent WatchLLM sessions")

        names = list_sessions()
        if not names:
            _render_info("No sessions found. Create one with [bold]watchllm session resume <name>[/bold]")
            return 0

        if RICH_AVAILABLE:
            table = Table(show_header=True, header_style="bold bright_cyan", border_style="bright_black")
            table.add_column("Name", style="bold")
            table.add_column("Last Active", style="dim")
            table.add_column("Model", style="cyan")
            table.add_column("Working Dir", style="dim", max_width=40)

            for name in names:
                data = load_session(name)
                table.add_row(
                    name,
                    data.get("last_active", "-"),
                    data.get("model", "-"),
                    data.get("cwd", "-"),
                )
            console.print(table)
        else:
            for name in names:
                data = load_session(name)
                print(f"  {name}  |  {data.get('last_active', '-')}  |  {data.get('model', '-')}  |  {data.get('cwd', '-')}")

        console.print() if RICH_AVAILABLE else print()
        return 0

    if args.session_command == "resume":
        name = args.name or "default"
        session = load_session(name)

        # If it exists, load it.  Otherwise create fresh.
        if session:
            cwd = session.get("cwd", os.getcwd())
            model = session.get("model", "default")
            _render_header(
                "Session Resumed",
                f"[bold]{name}[/bold] — Model: [cyan]{model}[/cyan]  |  Dir: [dim]{cwd}[/dim]",
            )
            if RICH_AVAILABLE:
                console.print("[dim]Session loaded from disk. Pick up where you left off.[/dim]")
        else:
            cwd = os.getcwd()
            model = args.model or "default"
            _render_header(
                "New Session",
                f"[bold]{name}[/bold] — Model: [cyan]{model}[/cyan]  |  Dir: [dim]{cwd}[/dim]",
            )

        # Persist the resumed session state
        save_session(
            name,
            {
                "name": name,
                "cwd": cwd,
                "model": model,
                "last_active": datetime.now(timezone.utc).isoformat(),
            },
        )

        _render_success(f"Session [bold]{name}[/bold] is active.")
        if RICH_AVAILABLE:
            console.print(
                Panel(
                    f"Your session [bold]{name}[/bold] is ready.\n"
                    f"  Working directory: [dim]{cwd}[/dim]\n"
                    f"  Model:             [cyan]{model}[/cyan]",
                    border_style="bright_cyan",
                    title="Ready",
                )
            )
        return 0

    if args.session_command == "clear":
        if not _confirm_destructive(
            "Clear all sessions?",
            "This will delete all saved session state. This cannot be undone.",
        ):
            _render_info("Clear cancelled.")
            return 0

        count = clear_sessions()
        _render_success(f"Cleared {count} session(s).")
        return 0

    return 0


# ---------------------------------------------------------------------------
# completion
# ---------------------------------------------------------------------------


def cmd_completion(args: argparse.Namespace) -> int:
    """Show tab-completion setup instructions."""
    _setup_tab_completion()
    return 0


# ---------------------------------------------------------------------------
# Signal handling
# ---------------------------------------------------------------------------

_shutdown_requested = False


def _handle_interrupt(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True
    if RICH_AVAILABLE:
        console.print()
        console.print("[bold yellow]⚠ Interrupted. Shutting down gracefully...[/bold yellow]")
    else:
        print(f"\n{C_YELLOW}⚠ Interrupted. Shutting down gracefully...{C_RESET}")
    sys.exit(130)


signal.signal(signal.SIGINT, _handle_interrupt)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class WatchLLMArgumentParser(argparse.ArgumentParser):
    """Custom ArgumentParser with premium help formatting."""

    def print_help(self, file=None):
        if RICH_AVAILABLE:
            _render_banner()
        super().print_help(file)
        if RICH_AVAILABLE:
            console.print()
            console.print(
                Panel(
                    "Examples:\n"
                    "  [cyan]watchllm init[/cyan]                     # Create config in current dir\n"
                    "  [cyan]watchllm evaluate src/main.ts[/cyan]     # Run kernel on a file\n"
                    "  [cyan]watchllm preview src/main.ts[/cyan]      # Dry-run the check\n"
                    "  [cyan]watchllm diff[/cyan]                      # Show changes since last snap\n"
                    "  [cyan]watchllm rollback[/cyan]                  # Undo last file edit\n"
                    "  [cyan]watchllm session resume[/cyan]            # Resume your session",
                    border_style="bright_black",
                    title="Quick Start",
                )
            )


def build_parser() -> argparse.ArgumentParser:
    parser = WatchLLMArgumentParser(
        prog="watchllm",
        description="WatchLLM — Deterministic runtime governance for autonomous coding agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    sub = parser.add_subparsers(dest="command", metavar="command")

    # ── init ──────────────────────────────────────────────────────────────
    init_p = sub.add_parser("init", help="Generate a default .watchllm.yaml")
    init_p.add_argument(
        "directory", nargs="?", default=".", help="Target directory (default: .)"
    )
    init_p.add_argument("--force", action="store_true", help="Overwrite existing config")
    init_p.add_argument("--dry-run", action="store_true", help="Preview without writing")

    # ── evaluate ──────────────────────────────────────────────────────────
    eval_p = sub.add_parser("evaluate", help="Evaluate a file through the kernel")
    eval_p.add_argument("file", nargs="?", default=None, help="Path to source file")
    eval_p.add_argument("--stdin", action="store_true", help="Read from stdin")
    eval_p.add_argument(
        "--mode", choices=["enforce", "shadow"], default=None,
        help="enforce=block violations | shadow=log only"
    )
    eval_p.add_argument("--language", choices=["js", "ts"], default=None)
    eval_p.add_argument("--dry-run", action="store_true", help="Preview without executing")

    # ── status ────────────────────────────────────────────────────────────
    sub.add_parser("status", help="Check health of all WatchLLM subsystems")

    # ── diff ──────────────────────────────────────────────────────────────
    sub.add_parser("diff", help="Show git-style diff since last snapshot")

    # ── preview ───────────────────────────────────────────────────────────
    prev_p = sub.add_parser("preview", help="Dry-run evaluate (alias for evaluate --dry-run)")
    prev_p.add_argument("file", nargs="?", default=None, help="Path to source file")
    prev_p.add_argument("--stdin", action="store_true", help="Read from stdin")
    prev_p.add_argument("--mode", choices=["enforce", "shadow"], default=None)
    prev_p.add_argument("--language", choices=["js", "ts"], default=None)

    # ── rollback ──────────────────────────────────────────────────────────
    sub.add_parser("rollback", help="Undo last file edit from snapshot")

    # ── session ───────────────────────────────────────────────────────────
    sess_p = sub.add_parser("session", help="Manage persistent sessions")
    sess_sub = sess_p.add_subparsers(dest="session_command", metavar="action")

    sess_sub.add_parser("list", help="List all saved sessions")
    resume_p = sess_sub.add_parser("resume", help="Resume (or create) a session")
    resume_p.add_argument("name", nargs="?", default="default", help="Session name")
    resume_p.add_argument("--model", help="Model to use for this session")
    sess_sub.add_parser("clear", help="Delete all sessions")

    # ── completion ────────────────────────────────────────────────────────
    sub.add_parser("completion", help="Show tab-completion setup instructions")

    return parser


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    command_map = {
        "init":       cmd_init,
        "evaluate":   cmd_evaluate,
        "status":     cmd_status,
        "diff":       cmd_diff,
        "preview":    cmd_preview,
        "rollback":   cmd_rollback,
        "session":    cmd_session,
        "completion": cmd_completion,
    }

    handler = command_map.get(args.command)
    if handler is None:
        _render_error(f"Unknown command: {args.command}")
        parser.print_help()
        return 2

    try:
        return handler(args)
    except KeyboardInterrupt:
        _handle_interrupt(signal.SIGINT, None)
        return 130
    except Exception:
        _render_error("Unexpected error.")
        if RICH_AVAILABLE:
            err_console.print(
                Panel(traceback.format_exc(), border_style="red", title="Traceback")
            )
        else:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
