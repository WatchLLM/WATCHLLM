from __future__ import annotations

import os
import shlex
import subprocess
import uuid
from collections.abc import Mapping

from orchestrator.identity import IdentityManager

WATCHLLM_AGENT_TOKEN_ENV = "WATCHLLM_AGENT_TOKEN"
WATCHLLM_TRACE_ID_ENV = "WATCHLLM_TRACE_ID"


class AgentSpawner:
    def __init__(self, identity_manager: IdentityManager | None = None) -> None:
        self._identity_manager = identity_manager or IdentityManager()

    def spawn(
        self,
        role: str,
        command: str,
        permissions: str = "read-write",
        expires_minutes: int = 60,
        extra_env: Mapping[str, str] | None = None,
    ) -> int:
        role = role.strip()
        command = command.strip()

        if not role:
            raise ValueError("role is required")
        if not command:
            raise ValueError("command is required")

        token = self._identity_manager.issue_token(
            role=role,
            permissions=permissions,
            expires_minutes=expires_minutes,
        )

        env = os.environ.copy()
        env[WATCHLLM_AGENT_TOKEN_ENV] = token
        
        trace_id = str(uuid.uuid4())
        env[WATCHLLM_TRACE_ID_ENV] = trace_id

        if extra_env:
            env.update(extra_env)

        args = shlex.split(command, posix=os.name != "nt")
        if not args:
            raise ValueError("command is required")

        completed = subprocess.run(
            args,
            env=env,
            check=False,
        )
        return completed.returncode