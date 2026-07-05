"""Suite registry for the reliability harness."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SuiteInfo:
    name: str
    description: str


class SuiteRegistry:
    """Stores registered test suites by name."""

    def __init__(self) -> None:
        self._suites: Dict[str, SuiteInfo] = {}

    def register(self, suite: SuiteInfo) -> None:
        self._suites[suite.name] = suite

    def names(self) -> List[str]:
        return list(self._suites.keys())

    def get(self, name: str) -> Optional[SuiteInfo]:
        return self._suites.get(name)

    def all(self) -> List[SuiteInfo]:
        return list(self._suites.values())


def default_registry() -> SuiteRegistry:
    """Create a registry pre-populated with the three placeholder suites."""
    registry = SuiteRegistry()
    registry.register(SuiteInfo(name="prompt-injection", description="Prompt injection adversarial tests"))
    registry.register(SuiteInfo(name="kernel-enforcement", description="Kernel enforcement boundary tests"))
    registry.register(SuiteInfo(name="tool-abuse", description="Tool abuse and infinite loop tests"))
    return registry
