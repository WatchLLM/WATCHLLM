from pathlib import Path

from config import load_mode
from parser.setup import LanguageName, language_for_path
from rules.auth import check_endpoint_requires_auth_from_source
from rules.base import Rule, Violation
from rules.boundary import check_service_boundary_from_source
from rules.imports import check_forbidden_imports_from_source
from rules.secrets import check_secret_detection_from_source

RULES: tuple[Rule, ...] = (
    check_endpoint_requires_auth_from_source,
    check_forbidden_imports_from_source,
    check_secret_detection_from_source,
)


def _apply_mode(violation: Violation, mode: str) -> Violation:
    if 'severity' not in violation:
        violation = {**violation, 'severity': 'critical'}

    return {**violation, 'blocking': mode == 'enforce'}


def evaluate_rules_from_source(source: str, language_name: LanguageName) -> list[Violation]:
    mode = load_mode()
    violations: list[Violation] = []

    for rule in RULES:
        for violation in rule(source, language_name):
            violations.append(_apply_mode(violation, mode))

    return violations


def evaluate_rules_for_content(file_path: str, source: str) -> list[Violation]:
    mode = load_mode()
    language_name = language_for_path(file_path)
    violations = evaluate_rules_from_source(source, language_name)

    for violation in check_service_boundary_from_source(file_path, source, language_name):
        violations.append(_apply_mode(violation, mode))

    return violations


def evaluate_rules(file_path: str) -> list[Violation]:
    path = Path(file_path)

    return evaluate_rules_for_content(
        file_path,
        path.read_text(encoding='utf-8'),
    )
