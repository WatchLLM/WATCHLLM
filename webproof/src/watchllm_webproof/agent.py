"""Synchronous and asynchronous WebProof HTTP agent."""

from __future__ import annotations

from threading import Lock
from typing import Any, Mapping
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
import requests

from .accumulator import merkle_root
from .config import RouteConfig, WebProofConfig, load_config, normalize_hostname
from .exceptions import AgentClosedError, UnsupportedSchemeError


class VerifiableAgent:
    """Record privacy-minimized HTTP request outcomes and summarize them locally.

    The returned proof is a deterministic local stub. It is explicitly not a
    TLSNotary/Reclaim proof and not a cryptographic attestation of remote data.
    Configured prover modes are routing metadata only in this SDK release.
    """

    def __init__(
        self,
        config: str | Mapping[str, Any] | WebProofConfig,
        *,
        session: requests.Session | None = None,
        async_client: httpx.AsyncClient | None = None,
        session_id: str | None = None,
    ) -> None:
        self.config = load_config(config)
        self.session_id = session_id or str(uuid4())
        self._session = session
        self._async_client = async_client
        self._owns_session = session is None
        self._owns_async_client = async_client is None
        self._records: list[dict[str, Any]] = []
        self._lock = Lock()
        self._sync_closed = False
        self._async_closed = False

    def __enter__(self) -> "VerifiableAgent":
        if self._sync_closed:
            raise AgentClosedError("agent's synchronous client is closed")
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    async def __aenter__(self) -> "VerifiableAgent":
        if self._async_closed:
            raise AgentClosedError("agent's asynchronous client is closed")
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.aclose()

    def close(self) -> None:
        if not self._sync_closed and self._owns_session and self._session is not None:
            self._session.close()
        self._sync_closed = True

    async def aclose(self) -> None:
        if not self._async_closed and self._owns_async_client and self._async_client is not None:
            await self._async_client.aclose()
        self._async_closed = True

    @property
    def session(self) -> requests.Session:
        """The persistent synchronous session, created lazily when needed."""
        if self._session is None:
            self._session = requests.Session()
        return self._session

    @property
    def async_client(self) -> httpx.AsyncClient:
        """The persistent asynchronous client, created lazily when needed."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient()
        return self._async_client

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        if self._sync_closed:
            raise AgentClosedError("agent's synchronous client is closed")
        target = self._target(url)
        try:
            response = self.session.request(method, url, **kwargs)
        except requests.RequestException as exc:
            self._record(method, target, None, type(exc).__name__)
            raise
        self._record(method, target, response.status_code, None)
        return response

    async def arequest(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        if self._async_closed:
            raise AgentClosedError("agent's asynchronous client is closed")
        target = self._target(url)
        stream = kwargs.pop("stream", False)
        try:
            if stream:
                auth = kwargs.pop("auth", httpx.USE_CLIENT_DEFAULT)
                follow_redirects = kwargs.pop("follow_redirects", httpx.USE_CLIENT_DEFAULT)
                request = self.async_client.build_request(method, url, **kwargs)
                response = await self.async_client.send(
                    request, stream=True, auth=auth, follow_redirects=follow_redirects
                )
            else:
                response = await self.async_client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            self._record(method, target, None, type(exc).__name__)
            raise
        self._record(method, target, response.status_code, None)
        return response

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", url, **kwargs)

    async def aget(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.arequest("GET", url, **kwargs)

    def proof(self) -> dict[str, Any]:
        with self._lock:
            records = [dict(record) for record in self._records]
        enabled = self.config.aggregation.enabled
        return {
            "proof_type": "local_merkle_stub",
            "proof_version": 1,
            "attestation": False,
            "algorithm": self.config.aggregation.algorithm,
            "aggregation_enabled": enabled,
            "merkle_root": merkle_root(records) if enabled else None,
            "leaf_count": len(records),
            "session_id": self.session_id,
        }

    @property
    def records(self) -> tuple[Mapping[str, Any], ...]:
        """Return immutable snapshots containing no headers, query strings, or bodies."""
        with self._lock:
            return tuple(dict(record) for record in self._records)

    def route_for(self, hostname: str) -> RouteConfig | None:
        normalized = normalize_hostname(hostname)
        exact = [r for r in self.config.routes if r.hostname == normalized]
        if exact:
            return exact[0]
        candidates = [
            route for route in self.config.routes
            if route.include_subdomains and normalized.endswith("." + route.hostname)
        ]
        return max(candidates, key=lambda route: len(route.hostname), default=None)

    def _target(self, url: str) -> dict[str, Any]:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"}:
            shown = parsed.scheme or "(missing)"
            raise UnsupportedSchemeError(
                f"unsupported URL scheme {shown!r}; watchllm-webproof supports HTTP and HTTPS only"
            )
        if parsed.username is not None or parsed.password is not None:
            raise UnsupportedSchemeError("credentials in URLs are not supported")
        if parsed.hostname is None:
            raise UnsupportedSchemeError("HTTP(S) URL must include a hostname")
        hostname = normalize_hostname(parsed.hostname)
        route = self.route_for(hostname)
        default_port = 80 if scheme == "http" else 443
        try:
            port = parsed.port
        except ValueError as exc:
            raise UnsupportedSchemeError(f"invalid URL port: {exc}") from exc
        return {
            "scheme": scheme,
            "hostname": hostname,
            "port": port or default_port,
            "path": parsed.path or "/",
            "prover": route.prover if route else None,
        }

    def _record(
        self,
        method: str,
        target: Mapping[str, Any],
        status_code: int | None,
        error_type: str | None,
    ) -> None:
        record = {
            "method": method.upper(),
            **target,
            "status_code": status_code,
            "error_type": error_type,
        }
        with self._lock:
            self._records.append(record)
