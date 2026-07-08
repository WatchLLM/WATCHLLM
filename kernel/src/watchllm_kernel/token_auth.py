"""Token authentication facade for the WatchLLM kernel.

Provides a thin, optionally-importable wrapper around the orchestrator's
``IdentityManager`` so that:

  1. The kernel can be used standalone (without orchestrator installed).
  2. Token extraction logic can be unit-tested independently.
  3. The rest of ``cli.py`` has a single clean call-site.

Usage::

    from watchllm_kernel.token_auth import extract_role_from_env
    role = extract_role_from_env()   # None if no token / orchestrator absent
"""

from __future__ import annotations

import os
import sys
from typing import Optional


AGENT_TOKEN_ENV = "WATCHLLM_AGENT_TOKEN"
TRACE_ID_ENV = "WATCHLLM_TRACE_ID"


def extract_role_from_env() -> Optional[str]:
    """Read ``WATCHLLM_AGENT_TOKEN`` from the environment and return the role.

    Returns ``None`` in any of these cases:
    - The env var is not set.
    - The orchestrator package is not installed.
    - The token is expired or invalid.

    A warning is printed to stderr when a token is present but cannot be
    validated, so that misconfiguration is surfaced without crashing.
    """
    token = os.environ.get(AGENT_TOKEN_ENV)
    if not token:
        return None

    try:
        from orchestrator.identity import IdentityManager
        payload = IdentityManager().validate_token(token)
        return payload.get("role")
    except ImportError:
        print(
            "Warning: WATCHLLM_AGENT_TOKEN is set but the orchestrator package "
            "is not installed — token will be ignored.",
            file=sys.stderr,
        )
        return None
    except Exception as exc:  # expired, bad signature, etc.
        print(
            f"Warning: Failed to validate WATCHLLM_AGENT_TOKEN: {exc}",
            file=sys.stderr,
        )
        return None


def get_trace_id() -> Optional[str]:
    """Return ``WATCHLLM_TRACE_ID`` from the environment, or ``None``."""
    return os.environ.get(TRACE_ID_ENV)
