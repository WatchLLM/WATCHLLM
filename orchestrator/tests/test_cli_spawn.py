from click.testing import CliRunner

from orchestrator.cli import cli


def test_spawn_cli_invokes_spawner(monkeypatch):
    captured = {}

    def fake_spawn(self, role, command, permissions="read-write", expires_minutes=60):
        captured["role"] = role
        captured["command"] = command
        captured["permissions"] = permissions
        captured["expires_minutes"] = expires_minutes
        return 0

    monkeypatch.setattr("orchestrator.cli.AgentSpawner.spawn", fake_spawn)

    result = CliRunner().invoke(
        cli,
        ["spawn", "--role", "frontend-agent", "--command", "aider"],
    )

    assert result.exit_code == 0
    assert captured == {
        "role": "frontend-agent",
        "command": "aider",
        "permissions": "read-write",
        "expires_minutes": 60,
    }