from parser.imports import extract_imports_from_source
from parser.setup import LanguageName

EXACT_FORBIDDEN_IMPORTS = {
    'fs',
    'child_process',
    'net',
    'tls',
    'dns',
    'process',
    'eval',
    'Function',
}

PREFIX_FORBIDDEN_IMPORTS = (
    '../db/',
    '../../db/',
    '@/db/',
    '../internal/',
    '../../internal/',
    '@internal/',
    '/secrets/',
    '/config/keys/',
)


def check_forbidden_imports_from_source(source: str, language_name: LanguageName) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []

    for import_path in extract_imports_from_source(source, language_name):
        if import_path in EXACT_FORBIDDEN_IMPORTS or import_path.startswith(PREFIX_FORBIDDEN_IMPORTS):
            violations.append(
                {
                    'rule': 'forbidden_imports',
                    'severity': 'critical',
                    'import': import_path,
                    'reason': 'Forbidden import is not allowed',
                },
            )

    return violations
