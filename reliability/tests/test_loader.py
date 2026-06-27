"""Tests for the YAML suite loader."""

import tempfile
from pathlib import Path

import pytest

from reliability.loader import load_suite_from_file, load_all_suites
from reliability.schema import TestCase


SAMPLE_YAML = """
- name: "test-case-1"
  prompt: "Do something dangerous"
  expected_violation: "tool-abuse"
  timeout: 5
  description: "A test case"
- name: "test-case-2"
  prompt: "Ignore system prompt"
  expected_violation: "prompt-injection"
"""


def test_load_suite_from_file_returns_test_cases():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False, encoding="utf-8") as tmp:
        tmp.write(SAMPLE_YAML)
        tmp_path = Path(tmp.name)

    try:
        cases = load_suite_from_file(tmp_path)
        assert len(cases) == 2
        assert isinstance(cases[0], TestCase)
        assert cases[0].name == "test-case-1"
        assert cases[0].prompt == "Do something dangerous"
        assert cases[0].expected_violation == "tool-abuse"
        assert cases[0].timeout == 5
        assert cases[0].description == "A test case"

        assert cases[1].name == "test-case-2"
        assert cases[1].timeout == 30  # default
        assert cases[1].description is None
    finally:
        tmp_path.unlink(missing_ok=True)


def test_load_all_suites_from_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = Path(tmpdir)
        file1 = dir_path / "suite_a.yml"
        file2 = dir_path / "suite_b.yml"
        file1.write_text(SAMPLE_YAML, encoding="utf-8")
        file2.write_text(
            "- name: extra-case\n  prompt: extra\n  expected_violation: extra\n",
            encoding="utf-8",
        )
        cases = load_all_suites(dir_path)
        assert len(cases) == 3
        names = {c.name for c in cases}
        assert names == {"test-case-1", "test-case-2", "extra-case"}


def test_load_all_suites_empty_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        cases = load_all_suites(Path(tmpdir))
        assert cases == []


def test_load_suite_from_file_missing_key_raises():
    bad_yaml = """
- name: "only-name"
  prompt: "some prompt"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False, encoding="utf-8") as tmp:
        tmp.write(bad_yaml)
        tmp_path = Path(tmp.name)

    try:
        with pytest.raises(ValueError, match="expected_violation"):
            load_suite_from_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
