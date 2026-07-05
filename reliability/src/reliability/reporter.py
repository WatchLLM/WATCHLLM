from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from reliability.scoring import ScoreReport, TestOutcome


def write_junit_report(
    outcomes: Iterable[TestOutcome],
    report: ScoreReport,
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    grouped: dict[str, list[TestOutcome]] = defaultdict(list)
    outcome_list = list(outcomes)

    for outcome in outcome_list:
        grouped[outcome.suite_name].append(outcome)

    root = ET.Element(
        "testsuites",
        {
            "tests": str(report.total),
            "failures": str(report.failed),
            "errors": "0",
            "time": "0",
            "safety_index": f"{report.safety_index:.1f}",
        },
    )

    for suite_score in report.suite_scores:
        suite_outcomes = grouped.get(suite_score.suite_name, [])
        suite_element = ET.SubElement(
            root,
            "testsuite",
            {
                "name": suite_score.suite_name,
                "tests": str(suite_score.total),
                "failures": str(suite_score.failed),
                "errors": "0",
                "skipped": "0",
                "time": "0",
            },
        )

        for outcome in suite_outcomes:
            case_element = ET.SubElement(
                suite_element,
                "testcase",
                {
                    "classname": outcome.suite_name,
                    "name": outcome.test_name,
                    "time": "0",
                },
            )

            if not outcome.passed:
                failure = ET.SubElement(
                    case_element,
                    "failure",
                    {
                        "message": "Reliability test failed",
                        "type": "ReliabilityFailure",
                    },
                )
                failure.text = (
                    f"Test '{outcome.test_name}' failed in suite "
                    f"'{outcome.suite_name}'."
                )

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)

    return path
