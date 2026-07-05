from dataclasses import dataclass
from typing import Iterable

CAPABILITY_SIMPLE = "simple"
CAPABILITY_GENERAL = "general"
CAPABILITY_CODING = "coding"
CAPABILITY_ARCHITECTURE = "architecture"


@dataclass(frozen=True)
class ModelRoute:
    provider: str
    model: str
    provider_url: str
    schema: str
    capabilities: tuple[str, ...]
    cost_rank: int


DEFAULT_MODEL_CATALOG = (
    ModelRoute(
        provider="anthropic",
        model="claude-3-haiku-20240307",
        provider_url="https://api.anthropic.com/v1/messages",
        schema="anthropic",
        capabilities=(CAPABILITY_SIMPLE, CAPABILITY_GENERAL),
        cost_rank=10,
    ),
    ModelRoute(
        provider="openai",
        model="gpt-4o-mini",
        provider_url="https://api.openai.com/v1/chat/completions",
        schema="openai-compatible",
        capabilities=(CAPABILITY_SIMPLE, CAPABILITY_GENERAL, CAPABILITY_CODING),
        cost_rank=20,
    ),
    ModelRoute(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        provider_url="https://api.anthropic.com/v1/messages",
        schema="anthropic",
        capabilities=(
            CAPABILITY_SIMPLE,
            CAPABILITY_GENERAL,
            CAPABILITY_CODING,
        ),
        cost_rank=30,
    ),
    ModelRoute(
        provider="anthropic",
        model="claude-3-opus-20240229",
        provider_url="https://api.anthropic.com/v1/messages",
        schema="anthropic",
        capabilities=(
            CAPABILITY_SIMPLE,
            CAPABILITY_GENERAL,
            CAPABILITY_CODING,
            CAPABILITY_ARCHITECTURE,
        ),
        cost_rank=40,
    ),
)


class ModelRouter:
    def __init__(self, catalog: Iterable[ModelRoute] = DEFAULT_MODEL_CATALOG) -> None:
        self._catalog = tuple(sorted(catalog, key=lambda route: route.cost_rank))
        if not self._catalog:
            raise ValueError("Model catalog must not be empty")

    def route(self, task_description: str) -> ModelRoute:
        required_capability = self._required_capability(task_description)

        for route in self._catalog:
            if required_capability in route.capabilities:
                return route

        raise LookupError(f"No model route supports capability: {required_capability}")

    def _required_capability(self, task_description: str) -> str:
        normalized = task_description.lower().strip()
        if not normalized:
            return CAPABILITY_SIMPLE

        # Architecture keywords must be checked before coding keywords
        architecture_keywords = (
            "architecture",
            "architect",
            "system design",
            "design the system",
            "distributed",
            "scalability",
            "scalable",
            "orchestrator design",
            "database schema",
            "migration strategy",
        )
        for keyword in architecture_keywords:
            if keyword in normalized:
                return CAPABILITY_ARCHITECTURE

        coding_keywords = (
            "code",
            "implement",
            "function",
            "class",
            "debug",
            "bug",
            "refactor",
            "unit test",
            "pytest",
            "api endpoint",
        )
        for keyword in coding_keywords:
            if keyword in normalized:
                return CAPABILITY_CODING

        simple_keywords = (
            "format",
            "formatting",
            "summarize",
            "summary",
            "rewrite",
            "grammar",
            "spelling",
            "markdown",
            "bullet",
        )
        for keyword in simple_keywords:
            if keyword in normalized:
                return CAPABILITY_SIMPLE

        return CAPABILITY_GENERAL
