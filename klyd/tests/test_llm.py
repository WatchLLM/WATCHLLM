import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import unittest

from klyd.llm import (
    AnthropicLLMClient,
    ExtractionResult,
    build_extraction_prompt,
    get_llm_client,
    load_llm_config,
    parse_extraction_response,
)


class TestLLMProvider(unittest.TestCase):
    def test_load_llm_config_reads_klyd_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_dir = tmp_path / ".klyd"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "provider": "anthropic",
                        "model": "claude-test-model",
                        "api_key_env": "ANTHROPIC_API_KEY",
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(Path, "cwd", return_value=tmp_path):
                config = load_llm_config()

        self.assertEqual(config["provider"], "anthropic")
        self.assertEqual(config["model"], "claude-test-model")
        self.assertEqual(config["api_key_env"], "ANTHROPIC_API_KEY")

    def test_build_extraction_prompt_contains_schema_and_input(self):
        prompt = build_extraction_prompt("Use SQLite for local memory.")

        self.assertIn("NEW", prompt)
        self.assertIn("REINFORCE", prompt)
        self.assertIn("CONTRADICT", prompt)
        self.assertIn("file_patterns", prompt)
        self.assertIn("Use SQLite for local memory.", prompt)

    def test_parse_extraction_response_returns_typed_result(self):
        raw = {
            "decisions": [
                {
                    "decision": "Store all state locally in .klyd.",
                    "module": "storage",
                    "file_patterns": [".klyd/*", "src/klyd/*"],
                    "confidence": 0.95,
                    "event_type": "NEW",
                }
            ]
        }

        result = parse_extraction_response(raw)

        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(len(result.decisions), 1)

        decision = result.decisions[0]
        self.assertEqual(decision.decision, "Store all state locally in .klyd.")
        self.assertEqual(decision.module, "storage")
        self.assertEqual(decision.file_patterns, [".klyd/*", "src/klyd/*"])
        self.assertEqual(decision.confidence, 0.95)
        self.assertEqual(decision.event_type, "NEW")

    def test_anthropic_wrapper_can_extract_dummy_text_without_api_call(self):
        class FakeAnthropicClient(AnthropicLLMClient):
            def _send_prompt(self, prompt: str) -> str:
                assert "Dummy architecture text" in prompt
                return json.dumps(
                    {
                        "decisions": [
                            {
                                "decision": "Use local SQLite memory.",
                                "module": "storage",
                                "file_patterns": ["src/klyd/*"],
                                "confidence": 0.9,
                                "event_type": "NEW",
                            }
                        ]
                    }
                )

        client = FakeAnthropicClient(
            {
                "provider": "anthropic",
                "model": "fake-model",
                "api_key_env": "FAKE_API_KEY",
            }
        )

        result = client.extract_decisions("Dummy architecture text")

        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(result.decisions[0].decision, "Use local SQLite memory.")
        self.assertEqual(result.decisions[0].event_type, "NEW")
        self.assertEqual(result.decisions[0].file_patterns, ["src/klyd/*"])

    def test_get_llm_client_returns_anthropic_client(self):
        client = get_llm_client(
            {
                "provider": "anthropic",
                "model": "fake-model",
                "api_key_env": "FAKE_API_KEY",
            }
        )

        self.assertIsInstance(client, AnthropicLLMClient)
