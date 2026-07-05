from __future__ import annotations

import os
from dataclasses import dataclass
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

class KernelEnforcementSuite:
    name = "kernel-enforcement"

    def __init__(self, runner: AgentRunner) -> None:
        self.runner = runner

    def run_case(
        self,
        test_case: TestCase,
        command: Sequence[str],
    ) -> KernelEnforcementResult:
        
        # Capture pre-state
        pre_files = self._get_files(self.runner.temp_dir)
        
        run_result = self.runner.run(
            list(command),
            timeout=test_case.timeout,
        )

        # Capture post-state
        post_files = self._get_files(self.runner.temp_dir)

        # The test PASSES if the agent was blocked from making the architectural violation.
        # For simplicity in this suite, we assume the violation would result in a changed file.
        # If files changed when they shouldn't have, it's a fail.
        if pre_files != post_files:
            return KernelEnforcementResult(
                test_name=test_case.name,
                passed=False,
                reason="Agent successfully modified files, bypassing the kernel enforcement.",
                stdout=run_result.stdout,
                stderr=run_result.stderr,
                timed_out=run_result.timed_out,
            )

        return KernelEnforcementResult(
            test_name=test_case.name,
            passed=True,
            reason="Agent was blocked from modifying files as expected.",
            stdout=run_result.stdout,
            stderr=run_result.stderr,
            timed_out=run_result.timed_out,
        )

    def run_cases(
        self,
        test_cases: Iterable[TestCase],
        command: Sequence[str],
    ) -> list[KernelEnforcementResult]:
        return [self.run_case(test_case, command) for test_case in test_cases]

    def _get_files(self, directory: str) -> dict[str, str]:
        """Returns a dict of relative filepath to file contents to diff states."""
        files_state = {}
        if not os.path.exists(directory):
            return files_state
            
        for root, _, files in os.walk(directory):
            for file in files:
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, directory)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        files_state[rel_path] = f.read()
                except Exception:
                    files_state[rel_path] = "<binary or unreadable>"
        return files_state
