from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt


DEFAULT_SECRET = "watchllm-orchestrator-dev-secret"
DEFAULT_ISSUER = "watchllm-orchestrator"
DEFAULT_ALGORITHM = "HS256"


class IdentityManager:
    def __init__(
        self,
        secret: str = DEFAULT_SECRET,
        issuer: str = DEFAULT_ISSUER,
        algorithm: str = DEFAULT_ALGORITHM,
    ) -> None:
        self.secret = secret
        self.issuer = issuer
        self.algorithm = algorithm

    def issue_token(
        self,
        role: str,
        permissions: str = "read-write",
        expires_minutes: int = 60,
    ) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "role": role,
            "permissions": permissions,
            "iss": self.issuer,
            "iat": now,
            "exp": now + timedelta(minutes=expires_minutes),
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def validate_token(self, token: str) -> dict[str, Any]:
        return jwt.decode(
            token,
            self.secret,
            algorithms=[self.algorithm],
            issuer=self.issuer,
        )
