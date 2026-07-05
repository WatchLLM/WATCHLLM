"""Minimal AgentRunner for subprocess execution in isolated temp directory."""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(frozen=True)
class FileChange:
    path: str
    change_type: str


@dataclass(frozen=True)
class RunResult:
    stdout: str
    stderr: str
    timed_out: bool
    returncode: int | None
    file_changes: list[FileChange]


class AgentRunner:
    """Execute a command in a temporary directory and capture outputs."""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    def run(
        self,
        command: Sequence[str],
        *,
        timeout: int | None = None,
        input_text: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> RunResult:
        """Run command and return RunResult."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            before = _snapshot(root)

            try:
                proc = subprocess.run(
                    list(command),
                    cwd=root,
                    capture_output=True,
                    text=True,
                    input=input_text,
                    timeout=timeout if timeout is not None else self.timeout,
                    env=env,
                )
                after = _snapshot(root)
                return RunResult(
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    timed_out=False,
                    returncode=proc.returncode,
                    file_changes=_diff_snapshots(before, after),
                )
            except subprocess.TimeoutExpired as exc:
                after = _snapshot(root)
                return RunResult(
                    stdout=_coerce_output(exc.stdout),
                    stderr=_coerce_output(exc.stderr),
                    timed_out=True,
                    returncode=None,
                    file_changes=_diff_snapshots(before, after),
                )


def _snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(root).as_posix()
        snapshot[relative_path] = _hash_file(path)

    return snapshot


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _diff_snapshots(
    before: dict[str, str],
    after: dict[str, str],
) -> list[FileChange]:
    changes: list[FileChange] = []

    for path in sorted(set(after) - set(before)):
        changes.append(FileChange(path=path, change_type="added"))

    for path in sorted(set(before) - set(after)):
        changes.append(FileChange(path=path, change_type="deleted"))

    for path in sorted(set(before) & set(after)):
        if before[path] != after[path]:
            changes.append(FileChange(path=path, change_type="modified"))

    return sorted(changes, key=lambda change: change.path)


def _coerce_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.decode("utf-8", errors="replace")
