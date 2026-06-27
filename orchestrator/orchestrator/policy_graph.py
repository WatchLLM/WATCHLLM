from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable


@dataclass(frozen=True)
class PolicyBinding:
    path: str
    role: str


class PolicyGraph:
    def __init__(self, bindings: Iterable[PolicyBinding] | None = None) -> None:
        self._bindings: dict[str, str] = {}
        if bindings is not None:
            for binding in bindings:
                self.bind(binding.path, binding.role)

    def bind(self, path: str, role: str) -> None:
        if not path or not path.strip():
            raise ValueError("path must not be empty or whitespace")
        if not role or not role.strip():
            raise ValueError("role must not be empty or whitespace")

        normalized = self._normalize_path(path)
        self._bindings[normalized] = role.strip()

    def required_role_for_path(self, path: str) -> str | None:
        normalized = self._normalize_path(path)
        best_match: tuple[int, str] | None = None  # (length, role)

        for binding_path, role in self._bindings.items():
            if normalized == binding_path or normalized.startswith(binding_path + "/"):
                length = len(binding_path)
                if best_match is None or length > best_match[0]:
                    best_match = (length, role)

        return best_match[1] if best_match is not None else None

    @staticmethod
    def _normalize_path(raw: str) -> str:
        # Replace backslashes with forward slashes
        path = raw.replace("\\", "/").strip()

        # Ensure path starts with '/'
        if not path.startswith("/"):
            path = "/" + path

        # Use PurePosixPath to collapse redundant separators and '.' segments
        posix = PurePosixPath(path)
        normalized = str(posix)

        # Remove trailing slash unless the result is exactly '/'
        if normalized != "/" and normalized.endswith("/"):
            normalized = normalized.rstrip("/")

        return normalized
