from reliability.scoring import (
    TestOutcome,
    calculate_score_report,
    format_score_report,
)


def test_calculate_score_report_uses_weighted_safety_index():
    report = calculate_score_report(
        [
            TestOutcome(
                suite_name="prompt-injection",
                test_name="pi-pass",
                passed=True,
            ),
            TestOutcome(
                suite_name="kernel-enforcement",
                test_name="kernel-fail",
                passed=False,
            ),
        ]
    )

    assert report.total == 2
    assert report.passed == 1
    assert report.failed == 1
    assert report.safety_index == 33.3


def test_format_score_report_contains_table_and_safety_index():
    report = calculate_score_report(
        [
            TestOutcome(
                suite_name="prompt-injection",
                test_name="pi-pass",
                passed=True,
            ),
        ],
        suite_names=["prompt-injection", "tool-abuse"],
    )

    output = format_score_report(report)

    assert "Score summary:" in output
    assert "prompt-injection" in output
    assert "tool-abuse" in output
    assert "Safety Index: 100.0" in output
