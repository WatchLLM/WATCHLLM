import re

from parser.setup import LanguageName

STRING_PATTERNS = (
    'sk_live_',
    'rk_live_',
    'ghp_',
    'github_pat_',
    'xoxb-',
    'xoxp-',
    'sk-',
    '-----BEGIN PRIVATE KEY-----',
    '-----BEGIN RSA PRIVATE KEY-----',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9',
)

REGEX_PATTERNS = (
    r'AKIA[0-9A-Z]{16}',
    r'ASIA[0-9A-Z]{16}',
    r'xox[baprs]-[0-9a-zA-Z]{10,48}',
    r'https:\/\/[^:\s]+:[^@\s]+@',
    r'AAAA[A-Za-z0-9_-]{7}:[A-Za-z0-9_-]{140}',
)


def check_secret_detection_from_source(source: str, language_name: LanguageName) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []

    for pattern in STRING_PATTERNS:
        if pattern in source:
            violations.append(
                {
                    'rule': 'secret_detection',
                    'severity': 'critical',
                    'reason': 'Secret pattern detected in code',
                },
            )

    for pattern in REGEX_PATTERNS:
        if re.search(pattern, source):
            violations.append(
                {
                    'rule': 'secret_detection',
                    'severity': 'critical',
                    'reason': 'Secret pattern detected in code',
                },
            )

    return violations
