"""Schema definitions for reliability test cases."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TestCase:
    name: str
    prompt: str
    expected_violation: str
    timeout: int = 30
    description: Optional[str] = None
