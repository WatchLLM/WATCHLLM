import os

import click

from orchestrator.identity import DEFAULT_SECRET, IdentityManager
from orchestrator.spawner import AgentSpawner


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """WatchLLM Orchestrator CLI."""
    pass


@cli.command("issue-token")
@click.option("--role", required=True, help="Agent role to embed in the token.")
@click.option(
    "--permissions",
    default="read-write",
    show_default=True,
    help="Permission level for the agent.",
)
@click.option(
    "--expires-minutes",
    default=60,
    show_default=True,
    type=int,
    help="Token lifetime in minutes.",
)
def issue_token(role: str, permissions: str, expires_minutes: int) -> None:
    secret = os.environ.get("WATCHLLM_ORCHESTRATOR_SECRET", DEFAULT_SECRET)
    manager = IdentityManager(secret=secret)
    token = manager.issue_token(
        role=role,
        permissions=permissions,
        expires_minutes=expires_minutes,
    )
    click.echo(token)


@cli.command("spawn")
@click.option("--role", required=True, help="Agent role to embed in the orchestrator token.")
@click.option(
    "--command",
    "command",
    required=True,
    help='Command to launch, e.g. "aider".',
)
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
def spawn(
    ctx: click.Context,
    role: str,
    command: str,
    permissions: str,
    expires_minutes: int,
) -> None:
    """Spawn an agent process with WATCHLLM_AGENT_TOKEN injected."""
    try:
        exit_code = AgentSpawner().spawn(
            role=role,
            command=command,
            permissions=permissions,
            expires_minutes=expires_minutes,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    ctx.exit(exit_code)
