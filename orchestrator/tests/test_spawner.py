from orchestrator.spawner import AgentSpawner, WATCHLLM_AGENT_TOKEN_ENV


class FakeIdentityManager:
    def issue_token(self, role: str, permissions: str = "read-write", expires_minutes: int = 60) -> str:
        assert role == "frontend-agent"
        assert permissions == "read-write"
        assert expires_minutes == 60
        return "fake-token"


class FakeCompletedProcess:
    returncode = 0


def test_spawn_injects_agent_token(monkeypatch):
    captured = {}

    def fake_run(args, env, check):
        captured["args"] = args
        captured["env"] = env
        captured["check"] = check
        return FakeCompletedProcess()

    monkeypatch.setattr("subprocess.run", fake_run)

    spawner = AgentSpawner(identity_manager=FakeIdentityManager())
    exit_code = spawner.spawn(role="frontend-agent", command="aider")

    assert exit_code == 0
    assert captured["args"] == ["aider"]
    assert captured["env"][WATCHLLM_AGENT_TOKEN_ENV] == "fake-token"
    assert captured["check"] is False


def test_spawn_rejects_empty_role():
    spawner = AgentSpawner(identity_manager=FakeIdentityManager())

    try:
        spawner.spawn(role=" ", command="aider")
    except ValueError as exc:
        assert "role is required" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_spawn_rejects_empty_command():
    spawner = AgentSpawner(identity_manager=FakeIdentityManager())

    try:
        spawner.spawn(role="frontend-agent", command=" ")
    except ValueError as exc:
        assert "command is required" in str(exc)
    else:
        raise AssertionError("expected ValueError")