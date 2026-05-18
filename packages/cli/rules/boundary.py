from parser.imports import extract_imports, extract_imports_from_source
from parser.setup import LanguageName

MODULES = {'api', 'auth', 'billing', 'db'}

ALLOWED_DEPENDENCIES = {
    ('api', 'auth'),
    ('billing', 'auth'),
    ('auth', 'db'),
}

RULE_NAME = 'service_boundary'


def _resolve_source_module(file_path: str) -> str:
    path_parts = [part for part in file_path.replace('\\', '/').split('/') if part]

    if 'src' in path_parts:
        source_index = path_parts.index('src') + 1

        if source_index >= len(path_parts):
            return ''

        return path_parts[source_index]

    for part in path_parts:
        if part in MODULES:
            return part

    return ''


def _resolve_target_module(import_path: str) -> str:
    import_parts = import_path.split('/')

    if import_path.startswith('@/') and len(import_parts) > 1:
        return import_parts[1]

    for part in import_parts:
        if part and part not in {'.', '..'}:
            return part

    return ''


def _check_service_boundary_for_imports(file_path: str, imports: list[str]) -> list[dict[str, str]]:
    source_module = _resolve_source_module(file_path)

    if source_module not in MODULES:
        return []

    violations: list[dict[str, str]] = []

    for import_path in imports:
        target_module = _resolve_target_module(import_path)

        if target_module not in MODULES or target_module == source_module:
            continue

        if (source_module, target_module) not in ALLOWED_DEPENDENCIES:
            violations.append(
                {
                    'rule': RULE_NAME,
                    'severity': 'critical',
                    'source': source_module,
                    'target': target_module,
                    'import': import_path,
                    'reason': f'Service boundary violation: {source_module} cannot import {target_module}',
                },
            )

    return violations


def check_service_boundary_from_source(
    file_path: str,
    source: str,
    language_name: LanguageName,
) -> list[dict[str, str]]:
    return _check_service_boundary_for_imports(
        file_path,
        extract_imports_from_source(source, language_name),
    )


def check_service_boundary(file_path: str) -> list[dict[str, str]]:
    return _check_service_boundary_for_imports(file_path, extract_imports(file_path))
