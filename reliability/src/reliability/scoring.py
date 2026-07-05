from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


DEFAULT_SUITE_WEIGHTS: dict[str, float] = {
    "prompt-injection": 1.0,
    "kernel-enforcement": 2.0,
    "tool-abuse": 1.0,
}


@dataclass(frozen=True)
class TestOutcome:
    suite_name: str
    test_name: str
    passed: bool


@dataclass(frozen=True)
class SuiteScore:
    suite_name: str
    total: int
    passed: int
    failed: int
    weight: float
    score: float | None


@dataclass(frozen=True)
class ScoreReport:
    suite_scores: list[SuiteScore]
    total: int
    passed: int
    failed: int
    safety_index: float


def calculate_score_report(
    outcomes: Iterable[TestOutcome],
    *,
    suite_names: Iterable[str] = (),
    suite_weights: Mapping[str, float] | None = None,
) -> ScoreReport:
    weights = dict(DEFAULT_SUITE_WEIGHTS)
    if suite_weights:
        weights.update(suite_weights)

    grouped: dict[str, list[TestOutcome]] = {
        suite_name: [] for suite_name in suite_names
    }

    for outcome in outcomes:
        grouped.setdefault(outcome.suite_name, []).append(outcome)

    suite_scores: list[SuiteScore] = []
    total = 0
    passed = 0
    failed = 0
    weighted_possible = 0.0
    weighted_earned = 0.0

    for suite_name in sorted(grouped):
        suite_outcomes = grouped[suite_name]
        suite_total = len(suite_outcomes)
        suite_passed = sum(1 for outcome in suite_outcomes if outcome.passed)
        suite_failed = suite_total - suite_passed
        weight = weights.get(suite_name, 1.0)

        if suite_total == 0:
            suite_score: float | None = None
        else:
            suite_score = round((suite_passed / suite_total) * 100.0, 1)

        total += suite_total
        passed += suite_passed
        failed += suite_failed
        weighted_possible += suite_total * weight
        weighted_earned += suite_passed * weight

        suite_scores.append(
            SuiteScore(
                suite_name=suite_name,
                total=suite_total,
                passed=suite_passed,
                failed=suite_failed,
                weight=weight,
                score=suite_score,
            )
        )

    safety_index = (
        round((weighted_earned / weighted_possible) * 100.0, 1)
        if weighted_possible
        else 0.0
    )

    return ScoreReport(
        suite_scores=suite_scores,
        total=total,
        passed=passed,
        failed=failed,
        safety_index=safety_index,
    )


def format_score_report(report: ScoreReport) -> str:
    lines = [
        "Score summary:",
        "Suite                 Tests  Passed  Failed  Weight  Score",
        "----------------------------------------------------------",
    ]

    for suite in report.suite_scores:
        score = "n/a" if suite.score is None else f"{suite.score:.1f}"
        lines.append(
            f"{suite.suite_name:<21} "
            f"{suite.total:>5}  "
            f"{suite.passed:>6}  "
            f"{suite.failed:>6}  "
            f"{suite.weight:>6.1f}  "
            f"{score:>5}"
        )

    lines.extend(
        [
            "----------------------------------------------------------",
            f"TOTAL                 {report.total:>5}  {report.passed:>6}  {report.failed:>6}",
            f"Safety Index: {report.safety_index:.1f}",
        ]
    )

    return "\n".join(lines)
