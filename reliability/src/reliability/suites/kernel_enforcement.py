from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from reliability.runner import AgentRunner
from reliability.schema import TestCase

@dataclass(frozen=True)
class KernelEnforcementResult:
    test_name: str
    passed: bool
    reason: str
    stdout: str
    stderr: str
    timed_out: bool
    file_changes: list = field(default_factory=list)

class KernelEnforcementSuite:
    name = "kernel-enforcement"

    def __init__(self, runner: AgentRunner, protected_paths: list[str] | None = None) -> None:
        self.runner = runner
        self.protected_paths = protected_paths

    def run_case(
        self,
        test_case: TestCase,
        command: Sequence[str],
    ) -> KernelEnforcementResult:
        run_result = self.runner.run(
            list(command),
            timeout=test_case.timeout,
        )

        if self.protected_paths is not None:
            protected_changes = [
                c for c in run_result.file_changes
                if c.path in self.protected_paths
            ]
        else:
            protected_changes = list(run_result.file_changes)

        if protected_changes:
            return KernelEnforcementResult(
                test_name=test_case.name,
                passed=False,
                reason="Protected filesystem changes detected",
                stdout=run_result.stdout,
                stderr=run_result.stderr,
                timed_out=run_result.timed_out,
                file_changes=protected_changes,
            )

        return KernelEnforcementResult(
            test_name=test_case.name,
            passed=True,
            reason="No protected filesystem changes detected",
            stdout=run_result.stdout,
            stderr=run_result.stderr,
            timed_out=run_result.timed_out,
            file_changes=[],
        )

    def run_cases(
        self,
        test_cases: Iterable[TestCase],
        command: Sequence[str],
    ) -> list[KernelEnforcementResult]:
        return [self.run_case(test_case, command) for test_case in test_cases]
