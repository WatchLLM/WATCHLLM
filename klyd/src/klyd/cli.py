"""CLI entrypoint for klyd."""

from __future__ import annotations

import fnmatch
import json
import os
import sqlite3
import stat
import subprocess
from pathlib import Path

import click

from klyd import __version__

KLYD_DIR = ".klyd"
DB_NAME = "memory.db"
CONFIG_NAME = "config.json"
INJECTION_NAME = "injection.txt"

POST_COMMIT_HOOK = "post-commit"
PRE_COMMIT_HOOK = "pre-commit"

HOOKS = {
    POST_COMMIT_HOOK: "kl extract-commit >> .klyd/errors.log 2>&1 || true",
    PRE_COMMIT_HOOK: "kl prepare-injection >> .klyd/errors.log 2>&1 || true",
}

DEFAULT_CONFIG = {
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-latest",
    "api_key_env": "ANTHROPIC_API_KEY",
}


def klyd_dir() -> Path:
    return Path.cwd() / KLYD_DIR


def db_path() -> Path:
    return klyd_dir() / DB_NAME


def config_path() -> Path:
    return klyd_dir() / CONFIG_NAME


def injection_path() -> Path:
    return klyd_dir() / INJECTION_NAME


def git_hooks_dir() -> Path:
    return Path.cwd() / ".git" / "hooks"


def run_git_command(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise click.ClickException(
            f"Git command failed: git {' '.join(args)}\n{message}"
        ) from exc

    return result.stdout


def get_staged_files() -> list[str]:
    output = run_git_command(["diff", "--cached", "--name-only"])
    return [line.strip() for line in output.splitlines() if line.strip()]


def normalise_repo_path(path: str) -> str:
    return path.replace("\\", "/")


def decode_file_patterns(raw: str | None) -> list[str]:
    if not raw:
        return []

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [raw]

    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, str)]

    if isinstance(parsed, str):
        return [parsed]

    return []


def patterns_match_files(
    patterns: list[str],
    files: list[str],
) -> bool:
    if not patterns:
        return True

    normalised_files = [normalise_repo_path(file) for file in files]
    normalised_patterns = [normalise_repo_path(pattern) for pattern in patterns]

    return any(
        fnmatch.fnmatch(file, pattern)
        for file in normalised_files
        for pattern in normalised_patterns
    )


def _connect_db() -> sqlite3.Connection:
    return sqlite3.connect(db_path(), timeout=0.1)


def fetch_relevant_injection_decisions(
    staged_files: list[str],
) -> list[sqlite3.Row]:
    ensure_database_exists(db_path())

    with _connect_db() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                id,
                decision,
                module,
                file_patterns,
                confidence,
                event_type,
                reinforcement_count,
                last_seen_commit,
                created_at
            FROM decisions
            WHERE archived = 0
              AND flagged = 0
            ORDER BY reinforcement_count DESC,
                     confidence DESC,
                     id ASC
            """
        ).fetchall()

    relevant: list[sqlite3.Row] = []

    for row in rows:
        patterns = decode_file_patterns(row["file_patterns"])

        if patterns_match_files(patterns, staged_files):
            relevant.append(row)

    return relevant


def format_injection_prompt(
    *,
    staged_files: list[str],
    decisions: list[sqlite3.Row],
) -> str:
    lines = [
        "KLYD ARCHITECTURAL MEMORY",
        "",
        "Use these repository-specific architectural constraints while editing.",
        "Do not blindly override them; if a change conflicts, preserve intent or ask for review.",
        "",
        "STAGED FILES:",
    ]

    if staged_files:
        lines.extend(f"- {file}" for file in staged_files)
    else:
        lines.append("- (none)")

    lines.extend(["", "RELEVANT DECISIONS:"])

    if not decisions:
        lines.append("- (none)")
    else:
        for row in decisions:
            patterns = decode_file_patterns(row["file_patterns"])
            pattern_text = ", ".join(patterns) if patterns else "global"

            confidence = row["confidence"]
            confidence_text = (
                "unknown" if confidence is None else f"{float(confidence):.2f}"
            )

            module = row["module"] or "general"

            lines.append(
                "- "
                f"[#{row['id']}] "
                f"{row['decision']} "
                f"(module: {module}; "
                f"patterns: {pattern_text}; "
                f"confidence: {confidence_text}; "
                f"reinforced: {row['reinforcement_count']}x)"
            )

    lines.append("")
    return "\n".join(lines)


def read_injection_context() -> str:
    path = injection_path()

    if not path.exists():
        raise click.ClickException(
            "No .klyd/injection.txt found. Run 'kl prepare-injection' first."
        )

    content = path.read_text(encoding="utf-8").strip()

    if not content:
        return "KLYD ARCHITECTURAL MEMORY\n\n- (no relevant decisions)"

    return content


def build_memory_message(injection_context: str) -> str:
    return f"[KLYD MEMORY]\n{injection_context}"


def build_agent_command(
    agent_cmd: tuple[str, ...],
    memory_message: str,
) -> list[str]:
    command = list(agent_cmd)

    if not command:
        raise click.ClickException("Usage: kl run <agent_cmd> [args]")

    agent_name = Path(command[0]).name.lower()

    if agent_name in {"aider", "aider.exe"}:
        return [*command, "--message", memory_message]

    if agent_name in {"opencode", "opencode.exe"}:
        return [*command, "--prompt", memory_message]

    return command


def build_agent_environment(memory_message: str) -> dict[str, str]:
    env = os.environ.copy()
    env["KLYD_MEMORY"] = memory_message
    return env


def initialise_database(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision TEXT NOT NULL,
                module TEXT,
                file_patterns TEXT,
                confidence REAL,
                event_type TEXT NOT NULL CHECK (
                    event_type IN ('NEW', 'REINFORCE', 'CONTRADICT')
                ),
                reinforcement_count INTEGER NOT NULL DEFAULT 1,
                last_seen_commit TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                flagged INTEGER NOT NULL DEFAULT 0,
                archived INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()


def initialise_config(path: Path) -> None:
    if path.exists():
        return

    path.write_text(
        json.dumps(DEFAULT_CONFIG, indent=2) + "\n",
        encoding="utf-8",
    )


def write_git_hook(path: Path, command: str) -> None:
    if os.name == "nt":
        hook_body = f"@{command}\n"
        path.write_text(hook_body, encoding="utf-8")
    else:
        hook_body = f"#!/bin/sh\n{command}\n"
        path.write_text(hook_body, encoding="utf-8")
        executable_mode = (
            path.stat().st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )
        path.chmod(executable_mode)


def initialise_git_hooks() -> None:
    git_dir = Path.cwd() / ".git"

    if not git_dir.exists():
        raise click.ClickException(
            "No .git directory found. Run 'kl init' from a git repository root."
        )

    hooks_dir = git_hooks_dir()
    hooks_dir.mkdir(parents=True, exist_ok=True)

    for hook_name, command in HOOKS.items():
        write_git_hook(hooks_dir / hook_name, command)


def ensure_database_exists(path: Path) -> None:
    if not path.exists():
        raise click.ClickException(
            "No .klyd/memory.db found. Run 'kl init' first."
        )


def fetch_decisions(*, flagged: int | None = None) -> list[sqlite3.Row]:
    ensure_database_exists(db_path())

    query = """
        SELECT
            id,
            decision,
            module,
            file_patterns,
            confidence,
            event_type,
            reinforcement_count,
            last_seen_commit,
            created_at,
            flagged,
            archived
        FROM decisions
        WHERE archived = 0
    """
    params: list[int] = []

    if flagged is not None:
        query += " AND flagged = ?"
        params.append(flagged)

    query += " ORDER BY id"

    with _connect_db() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(query, params).fetchall()


def shorten(value: object, *, max_length: int = 60) -> str:
    text = "" if value is None else str(value)

    if len(text) <= max_length:
        return text

    return text[: max_length - 3] + "..."


def format_decision_table(rows: list[sqlite3.Row]) -> str:
    if not rows:
        return "(none)"

    headers = ["ID", "TYPE", "COUNT", "CONF", "MODULE", "DECISION"]
    table_rows = [
        [
            str(row["id"]),
            str(row["event_type"]),
            str(row["reinforcement_count"]),
            "" if row["confidence"] is None else f"{float(row['confidence']):.2f}",
            shorten(row["module"], max_length=20),
            shorten(row["decision"], max_length=60),
        ]
        for row in rows
    ]

    widths = [
        max(len(headers[index]), *(len(row[index]) for row in table_rows))
        for index in range(len(headers))
    ]

    header_line = " | ".join(
        headers[index].ljust(widths[index])
        for index in range(len(headers))
    )
    separator = "-+-".join("-" * width for width in widths)

    body = [
        " | ".join(
            row[index].ljust(widths[index])
            for index in range(len(headers))
        )
        for row in table_rows
    ]

    return "\n".join([header_line, separator, *body])


def reject_flagged_decision(decision_id: int) -> None:
    ensure_database_exists(db_path())

    with _connect_db() as conn:
        cursor = conn.execute(
            """
            UPDATE decisions
            SET archived = 1
            WHERE id = ?
              AND flagged = 1
              AND archived = 0
            """,
            (decision_id,),
        )

        if cursor.rowcount != 1:
            raise click.ClickException(
                f"Cannot reject missing or unflagged decision ID: {decision_id}"
            )

        conn.commit()


def accept_flagged_decision(
    *,
    flagged_decision_id: int,
    old_decision_id: int | None,
) -> None:
    ensure_database_exists(db_path())

    with _connect_db() as conn:
        if old_decision_id is not None:
            old_cursor = conn.execute(
                """
                UPDATE decisions
                SET archived = 1
                WHERE id = ?
                  AND flagged = 0
                  AND archived = 0
                """,
                (old_decision_id,),
            )

            if old_cursor.rowcount != 1:
                raise click.ClickException(
                    f"Cannot archive missing active decision ID: {old_decision_id}"
                )

        new_cursor = conn.execute(
            """
            UPDATE decisions
            SET flagged = 0,
                archived = 0
            WHERE id = ?
              AND flagged = 1
              AND archived = 0
            """,
            (flagged_decision_id,),
        )

        if new_cursor.rowcount != 1:
            raise click.ClickException(
                f"Cannot accept missing flagged decision ID: {flagged_decision_id}"
            )

        conn.commit()


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="klyd")
def main() -> None:
    """klyd: Architectural memory for autonomous coding agents."""


@main.command()
def init() -> None:
    """Initialise local klyd memory storage."""
    root = klyd_dir()
    root.mkdir(parents=True, exist_ok=True)

    initialise_database(db_path())
    initialise_config(config_path())
    initialise_git_hooks()

    click.echo(f"Initialised klyd memory at {root}")
    click.echo(f"Database: {db_path()}")
    click.echo(f"Config: {config_path()}")
    click.echo(f"Git hooks: {git_hooks_dir()}")


# ------------------------------------------------------------------
# Task 04+05: Extraction Engine & Memory State Machine
# ------------------------------------------------------------------

def _get_last_commit_hash() -> str:
    """Return the short hash of the latest commit."""
    return run_git_command(["log", "-1", "--format=%H"]).strip()


def _get_last_commit_message() -> str:
    """Return the message of the latest commit."""
    return run_git_command(["log", "-1", "--format=%B"]).strip()


def _get_last_commit_diff() -> str:
    """Return the diff introduced by the latest commit."""
    return run_git_command(["diff", "HEAD~1", "HEAD"])


def _get_touched_files_from_diff(diff: str) -> list[str]:
    """Extract file paths from a unified diff."""
    files: list[str] = []
    for line in diff.splitlines():
        if line.startswith("diff --git a/"):
            parts = line.split(" b/")
            if len(parts) == 2:
                files.append(parts[1].strip())
    return list(set(files))


def _fetch_existing_decisions_for_files(
    touched_files: list[str],
) -> list[dict]:
    """Query existing active decisions whose file_patterns match the given files."""
    ensure_database_exists(db_path())

    with _connect_db() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, decision, module, file_patterns, confidence,
                   event_type, reinforcement_count
            FROM decisions
            WHERE archived = 0 AND flagged = 0
            ORDER BY reinforcement_count DESC
            """
        ).fetchall()

    relevant: list[dict] = []
    for row in rows:
        patterns = decode_file_patterns(row["file_patterns"])
        if patterns_match_files(patterns, touched_files):
            relevant.append(dict(row))

    return relevant


def _store_new_decision(
    decision_text: str,
    module: str | None,
    file_patterns: list[str],
    confidence: float,
    commit_hash: str,
    *,
    flagged: bool = False,
) -> int:
    """Insert a NEW or CONTRADICT decision into the database."""
    with _connect_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO decisions (
                decision, module, file_patterns, confidence,
                event_type, last_seen_commit, flagged
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_text,
                module or "",
                json.dumps(file_patterns),
                confidence,
                "CONTRADICT" if flagged else "NEW",
                commit_hash,
                1 if flagged else 0,
            ),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]


def _reinforce_decision(decision_id: int, commit_hash: str) -> None:
    """Increment the reinforcement count on an existing decision."""
    with _connect_db() as conn:
        conn.execute(
            """
            UPDATE decisions
            SET reinforcement_count = reinforcement_count + 1,
                last_seen_commit = ?
            WHERE id = ?
            """,
            (commit_hash, decision_id),
        )
        conn.commit()


def _process_extraction_results(
    decisions: list,
    commit_hash: str,
) -> dict[str, int]:
    """Process LLM extraction results through the state machine.

    Returns a summary dict: {"new": N, "reinforced": N, "contradicted": N}.
    """
    summary = {"new": 0, "reinforced": 0, "contradicted": 0}

    for d in decisions:
        event = d.event_type.upper()

        if event == "REINFORCE" and d.matching_decision_id is not None:
            _reinforce_decision(d.matching_decision_id, commit_hash)
            summary["reinforced"] += 1

        elif event == "CONTRADICT":
            _store_new_decision(
                decision_text=d.decision,
                module=d.module,
                file_patterns=d.file_patterns,
                confidence=d.confidence,
                commit_hash=commit_hash,
                flagged=True,
            )
            summary["contradicted"] += 1

        else:
            # NEW (default)
            _store_new_decision(
                decision_text=d.decision,
                module=d.module,
                file_patterns=d.file_patterns,
                confidence=d.confidence,
                commit_hash=commit_hash,
                flagged=False,
            )
            summary["new"] += 1

    return summary


@main.command("extract-commit")
def extract_commit() -> None:
    """Extract architectural decisions from the latest commit."""
    ensure_database_exists(db_path())

    # 1. Read the latest commit
    commit_hash = _get_last_commit_hash()
    commit_message = _get_last_commit_message()

    try:
        diff = _get_last_commit_diff()
    except click.ClickException:
        click.echo("No previous commit to diff against. Skipping extraction.")
        return

    if not diff.strip():
        click.echo("Empty diff. Nothing to extract.")
        return

    # 2. Identify touched files and query existing decisions
    touched_files = _get_touched_files_from_diff(diff)
    existing = _fetch_existing_decisions_for_files(touched_files)

    # 3. Build combined input for the LLM
    input_text = (
        f"COMMIT MESSAGE:\n{commit_message}\n\n"
        f"DIFF:\n{diff}"
    )

    # 4. Call the LLM
    from klyd.llm import get_llm_client, load_llm_config

    try:
        llm_config = load_llm_config()
    except FileNotFoundError:
        raise click.ClickException(
            "No .klyd/config.json found. Run 'kl init' first."
        )

    client = get_llm_client(llm_config)

    try:
        result = client.extract_decisions(input_text, existing)
    except Exception as exc:
        click.echo(f"LLM extraction failed: {exc}", err=True)
        return

    if not result.decisions:
        click.echo("No architectural decisions found in this commit.")
        return

    # 5. Process through the state machine
    summary = _process_extraction_results(result.decisions, commit_hash)

    click.echo(
        f"Extracted {len(result.decisions)} decision(s) from commit "
        f"{commit_hash[:8]}: "
        f"{summary['new']} new, "
        f"{summary['reinforced']} reinforced, "
        f"{summary['contradicted']} contradicted."
    )


@main.command()
def config() -> None:
    """Print the current klyd configuration."""
    path = config_path()

    if not path.exists():
        raise click.ClickException(
            "No .klyd/config.json found. Run 'kl init' first."
        )

    click.echo(path.read_text(encoding="utf-8").rstrip())


@main.command()
def status() -> None:
    """Print active architectural memory status."""
    active_rows = fetch_decisions(flagged=0)
    flagged_rows = fetch_decisions(flagged=1)

    click.echo("ACTIVE DECISIONS")
    click.echo(format_decision_table(active_rows))

    click.echo()
    click.echo("NEEDS REVIEW")
    click.echo(format_decision_table(flagged_rows))


@main.command()
def review() -> None:
    """Interactively review flagged architectural decisions."""
    flagged_rows = fetch_decisions(flagged=1)

    if not flagged_rows:
        click.echo("No flagged decisions need review.")
        return

    for row in flagged_rows:
        click.echo()
        click.echo(f"Flagged decision #{row['id']}")
        click.echo(f"Event type: {row['event_type']}")
        click.echo(f"Module: {row['module'] or ''}")
        click.echo(f"Decision: {row['decision']}")
        click.echo(f"File patterns: {row['file_patterns'] or ''}")
        click.echo(f"Confidence: {row['confidence']}")

        action = click.prompt(
            "Action: accept new, reject new, or skip",
            type=click.Choice(
                ["a", "accept", "r", "reject", "s", "skip"],
                case_sensitive=False,
            ),
            default="s",
        ).lower()

        if action in {"s", "skip"}:
            click.echo(f"Skipped decision #{row['id']}")
            continue

        if action in {"r", "reject"}:
            reject_flagged_decision(int(row["id"]))
            click.echo(f"Rejected and archived flagged decision #{row['id']}")
            continue

        active_rows = fetch_decisions(flagged=0)

        old_decision_id: int | None = None
        if active_rows:
            click.echo()
            click.echo("Existing active decisions:")
            click.echo(format_decision_table(active_rows))
            old_decision_id = click.prompt(
                "Old active decision ID to archive",
                type=int,
            )
        else:
            click.echo("No active old decisions found; accepting new decision only.")

        accept_flagged_decision(
            flagged_decision_id=int(row["id"]),
            old_decision_id=old_decision_id,
        )
        click.echo(f"Accepted flagged decision #{row['id']}")


@main.command("prepare-injection")
def prepare_injection() -> None:
    """Prepare architectural memory context for staged changes."""
    klyd_dir().mkdir(parents=True, exist_ok=True)

    staged_files = get_staged_files()
    decisions = fetch_relevant_injection_decisions(staged_files)

    content = format_injection_prompt(
        staged_files=staged_files,
        decisions=decisions,
    )

    path = injection_path()
    path.write_text(content, encoding="utf-8")

    click.echo(f"Wrote klyd injection context to {path}")


@main.command(
    "run",
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
    },
)
@click.argument("agent_cmd", nargs=-1, type=click.UNPROCESSED)
def run_agent(agent_cmd: tuple[str, ...]) -> None:
    """Run an agent command with klyd memory injected."""
    injection_context = read_injection_context()
    memory_message = build_memory_message(injection_context)

    command = build_agent_command(agent_cmd, memory_message)
    env = build_agent_environment(memory_message)

    completed = subprocess.run(
        command,
        cwd=Path.cwd(),
        env=env,
    )

    if completed.returncode != 0:
        raise click.exceptions.Exit(completed.returncode)


if __name__ == "__main__":
    main()
