"""Load test suites from YAML definition files."""

from pathlib import Path
from typing import List

import yaml

from reliability.schema import TestCase


def load_suite_from_file(file_path: Path) -> List[TestCase]:
    """Parse a YAML file and return a list of TestCase instances."""
    with file_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if not isinstance(raw, list):
        raise ValueError(f"Suite file {file_path} must contain a list of test cases")

    cases: List[TestCase] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"Item {idx} in {file_path} is not a mapping")
        try:
            case = TestCase(
                name=item["name"],
                prompt=item["prompt"],
                expected_violation=item["expected_violation"],
                timeout=int(item.get("timeout", 30)),
                description=item.get("description"),
            )
        except KeyError as exc:
            raise ValueError(f"Missing required key {exc} in item {idx} of {file_path}") from exc
        cases.append(case)
    return cases


def load_all_suites(suites_dir: Path) -> List[TestCase]:
    """Load all YAML suite files from a directory and return combined test cases."""
    all_cases: List[TestCase] = []
    if not suites_dir.is_dir():
        return all_cases
    for yaml_file in sorted(suites_dir.glob("*.yml")):
        all_cases.extend(load_suite_from_file(yaml_file))
    return all_cases
