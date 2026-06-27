from xml.etree import ElementTree as ET

from reliability.reporter import write_junit_report
from reliability.scoring import TestOutcome, calculate_score_report


def test_write_junit_report_contains_passes_and_failures(tmp_path):
    outcomes = [
        TestOutcome(
            suite_name="prompt-injection",
            test_name="safe-case",
            passed=True,
        ),
        TestOutcome(
            suite_name="tool-abuse",
            test_name="unsafe-case",
            passed=False,
        ),
    ]
    report = calculate_score_report(outcomes)
    output_path = tmp_path / "report.xml"

    written_path = write_junit_report(outcomes, report, output_path)

    assert written_path == output_path
    root = ET.parse(output_path).getroot()

    assert root.tag == "testsuites"
    assert root.attrib["tests"] == "2"
    assert root.attrib["failures"] == "1"

    testcases = root.findall(".//testcase")
    assert len(testcases) == 2

    failures = root.findall(".//failure")
    assert len(failures) == 1
    assert failures[0].attrib["type"] == "ReliabilityFailure"
