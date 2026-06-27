"""LLM provider abstraction for klyd.

Provides:
- Config loading from .klyd/config.json
- A structured extraction prompt that forces NEW/REINFORCE/CONTRADICT output
- Response parsing into typed dataclasses
- An Anthropic client wrapper (default provider)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ExtractedDecision:
    decision: str
    module: str | None = None
    file_patterns: list[str] = field(default_factory=list)
    confidence: float = 0.0
    event_type: str = "NEW"
    matching_decision_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "module": self.module,
            "file_patterns": self.file_patterns,
            "confidence": self.confidence,
            "event_type": self.event_type,
            "matching_decision_id": self.matching_decision_id,
        }


@dataclass
class ExtractionResult:
    decisions: list[ExtractedDecision] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decisions": [d.to_dict() for d in self.decisions],
        }


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_llm_config() -> dict[str, Any]:
    """Load the LLM configuration from `<cwd>/.klyd/config.json`."""
    config_file = Path.cwd() / ".klyd" / "config.json"

    if not config_file.exists():
        raise FileNotFoundError(
            "No .klyd/config.json found. Run 'kl init' first."
        )

    return json.loads(config_file.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT_TEMPLATE = """\
You are an architectural decision extractor for a software project.

You will receive a text block describing code changes (a git diff, commit message, \
or free-form description). Your job is to extract the literal text of the \
architectural decisions that this change clearly enacts.

Architectural decisions include: data store choice, auth strategy, API boundary \
contracts, module responsibility assignments, dependency/library choices, error \
handling patterns.

Rules:
- Only record if the text explicitly introduces, changes, or contradicts a decision.
- Do not guess. Do not infer. Only record what is clearly shown.
- If the text is a style fix, test update, or minor refactor with no architectural \
  significance: return {{"decisions": []}}.
- For each decision, classify as:
  - NEW — a novel architectural choice.
  - REINFORCE — confirms or repeats an existing decision.
  - CONTRADICT — conflicts with an existing decision.
- Assign confidence as a float between 0.0 and 1.0.
- Include the file_patterns that the decision applies to.

Return ONLY valid JSON matching this schema:
{{
  "decisions": [
    {{
      "decision": "<exact architectural rule>",
      "module": "<module or component name>",
      "file_patterns": ["<glob pattern>", ...],
      "confidence": <float 0.0-1.0>,
      "event_type": "NEW" | "REINFORCE" | "CONTRADICT",
      "matching_decision_id": <int or null>
    }}
  ]
}}

No prose. No markdown fences. No explanation. Only valid JSON.

INPUT TEXT:
{input_text}
"""


def build_extraction_prompt(
    input_text: str,
    existing_decisions: list[dict[str, Any]] | None = None,
) -> str:
    """Build the structured extraction prompt for the LLM."""
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(input_text=input_text)

    if existing_decisions:
        existing_block = "\n".join(
            f"- [#{d.get('id', '?')}] {d.get('decision', '')}"
            for d in existing_decisions
        )
        prompt += (
            "\n\nEXISTING DECISIONS (do not violate unless explicitly instructed):\n"
            + existing_block
        )

    return prompt


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def parse_extraction_response(raw: dict[str, Any]) -> ExtractionResult:
    """Parse a raw JSON dict (from the LLM) into a typed ExtractionResult."""
    decisions_raw = raw.get("decisions", [])
    decisions: list[ExtractedDecision] = []

    for item in decisions_raw:
        file_patterns = item.get("file_patterns", [])
        if isinstance(file_patterns, str):
            file_patterns = [file_patterns]

        decisions.append(
            ExtractedDecision(
                decision=item.get("decision", ""),
                module=item.get("module"),
                file_patterns=file_patterns,
                confidence=float(item.get("confidence", 0.0)),
                event_type=item.get("event_type", item.get("event", "NEW")),
                matching_decision_id=item.get("matching_decision_id"),
            )
        )

    return ExtractionResult(decisions=decisions)


# ---------------------------------------------------------------------------
# LLM Clients
# ---------------------------------------------------------------------------

class LLMClient:
    """Base LLM client interface."""

    def extract_decisions(
        self,
        text: str,
        existing_decisions: list[dict[str, Any]] | None = None,
    ) -> ExtractionResult:
        raise NotImplementedError("LLM client not yet implemented")


class AnthropicLLMClient(LLMClient):
    """Anthropic-backed LLM client for decision extraction.

    The ``_send_prompt`` method is separated so subclasses (including test
    fakes) can override the actual API call while keeping the prompt
    construction and response parsing logic intact.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.model = config.get("model", "claude-3-5-sonnet-latest")
        self.api_key_env = config.get("api_key_env", "ANTHROPIC_API_KEY")

    def _send_prompt(self, prompt: str) -> str:
        """Send a prompt to the Anthropic API and return the raw text response.

        Override this method in tests to avoid real API calls.
        """
        import os

        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError(
                "The 'anthropic' package is required. Install it with: "
                "pip install anthropic"
            ) from exc

        api_key = self.config.get("api_key") or os.environ.get(
            self.api_key_env, ""
        )

        if not api_key:
            raise ValueError(
                f"No Anthropic API key found. Set {self.api_key_env} or "
                "configure via 'kl config --api-key ...'."
            )

        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def extract_decisions(
        self,
        text: str,
        existing_decisions: list[dict[str, Any]] | None = None,
    ) -> ExtractionResult:
        prompt = build_extraction_prompt(text, existing_decisions)
        raw_response = self._send_prompt(prompt)

        # Strip markdown fences if the model wraps them
        content = raw_response.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        parsed = json.loads(content)
        return parse_extraction_response(parsed)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_llm_client(config: dict[str, Any] | None = None) -> LLMClient:
    """Return the configured LLM client.

    Currently only Anthropic is supported; additional providers can be
    added here by inspecting ``config["provider"]``.
    """
    if config is None:
        config = load_llm_config()

    provider = config.get("provider", "anthropic")

    if provider == "anthropic":
        return AnthropicLLMClient(config)

    raise ValueError(f"Unsupported LLM provider: {provider}")
