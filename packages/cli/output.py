import os
import sys
from typing import TextIO

# Ensure stdout/stderr use UTF-8 on Windows (cp1252 can't encode box-draw chars)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

RESET = '\033[0m'
BOLD = '1'
DIM = '2'
GREEN = '32'
YELLOW = '33'
RED = '31'
CYAN = '36'
GREY = '90'


def _supports_colour(stream: TextIO | None = None) -> bool:
    target = stream or sys.stdout

    return (
        hasattr(target, 'isatty')
        and target.isatty()
        and 'NO_COLOR' not in os.environ
        and os.environ.get('TERM') != 'dumb'
    )


def _colour(text: str, code: str, enable_colour: bool | None = None) -> str:
    if enable_colour is None:
        enable_colour = _supports_colour()

    if not enable_colour:
        return text

    return f'\033[{code}m{text}{RESET}'


def _severity_colour(severity: str) -> str:
    if severity == 'critical':
        return RED

    if severity == 'warn':
        return YELLOW

    return CYAN


def format_banner(enable_colour: bool | None = None) -> str:
    banner = r'''
 __        __    _       _     _     _     __  __
 \ \      / /_ _| |_ ___| |__ | |   | |   |  \/  |
  \ \ /\ / / _` | __/ __| '_ \| |   | |   | |\/| |
   \ V  V / (_| | || (__| | | | |___| |___| |  | |
    \_/\_/ \__,_|\__\___|_| |_|_____|_____|_|  |_|
'''

    tagline = 'Write-path governance for AI-generated code'

    return f'{_colour(banner.rstrip(), CYAN, enable_colour)}\n{_colour(tagline, DIM, enable_colour)}'


def format_success(message: str = 'WatchLLM check passed') -> str:
    return _colour(f'[OK] {message}', GREEN)


def format_warning_text(text: str) -> str:
    return _colour(text, YELLOW)


def format_error(message: str) -> str:
    return _colour(f'[FAIL] {message}', RED)


def format_violations(file_path: str, violations: list[dict[str, object]]) -> str:
    lines = [_colour('[FAIL] WatchLLM blocked this file', f'{BOLD};{RED}'), '']

    for index, violation in enumerate(violations, start=1):
        rule = violation.get('rule', '')
        reason = violation.get('reason', '')
        severity = str(violation.get('severity', 'critical'))
        line = violation.get('line')
        column = violation.get('column')
        location = file_path

        if isinstance(line, int):
            location = f'{location}:{line}'

            if isinstance(column, int):
                location = f'{location}:{column}'

        header = _colour(
            f'{index}. Rule: {rule}',
            f'{BOLD};{_severity_colour(severity)}',
        )

        lines.extend(
            [
                header,
                f'   Severity: {_colour(severity, _severity_colour(severity))}',
                f'   Location: {_colour(location, GREY)}',
                f'   Reason: {reason}',
                '',
            ],
        )

    return '\n'.join(lines).rstrip()
