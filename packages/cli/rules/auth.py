from pathlib import Path

from parser.api import detect_api_handlers_from_source
from parser.calls import extract_function_calls_from_source
from parser.setup import LanguageName, language_for_path, parse_source
from rules.db import is_db_call

AUTH_VERIFY_CALL = 'auth.verify'
RULE_NAME = 'endpoint_requires_auth'
FUNCTION_NODE_TYPES = {'function_declaration', 'arrow_function', 'function_expression'}


def is_auth_verify_call(call: str) -> bool:
    return call == AUTH_VERIFY_CALL


def detect_auth_verify_from_source(source: str, language_name: LanguageName) -> list[str]:
    return [
        call
        for call in extract_function_calls_from_source(source, language_name)
        if is_auth_verify_call(call)
    ]


def detect_auth_verify(file_path: str) -> list[str]:
    path = Path(file_path)

    return detect_auth_verify_from_source(path.read_text(encoding='utf-8'), language_for_path(file_path))


def _node_text(source: bytes, start_byte: int, end_byte: int) -> str:
    return source[start_byte:end_byte].decode('utf-8')


def _call_name(source: bytes, node) -> str:
    function_node = node.child_by_field_name('function')

    if function_node is None:
        return ''

    return _node_text(source, function_node.start_byte, function_node.end_byte).strip()


def _function_scopes(root_node) -> list:
    scopes = []

    def walk(node) -> None:
        if node.type in FUNCTION_NODE_TYPES:
            scopes.append(node)

        for child in node.children:
            walk(child)

    walk(root_node)

    return scopes


def _function_body_node(function_node):
    return function_node.child_by_field_name('body') or function_node


def _calls_in_function_scope(source: bytes, function_node) -> list[str]:
    calls: list[tuple[int, str]] = []
    body_node = _function_body_node(function_node)

    def walk(node) -> None:
        if node is not body_node and node.type in FUNCTION_NODE_TYPES:
            return

        if node.type == 'call_expression':
            call = _call_name(source, node)

            if call:
                calls.append((node.start_byte, call))

        for child in node.children:
            walk(child)

    walk(body_node)

    return [call for _, call in sorted(calls, key=lambda item: item[0])]


def check_endpoint_requires_auth_from_source(source: str, language_name: LanguageName) -> list[dict[str, str]]:
    handlers = detect_api_handlers_from_source(source, language_name)

    if not handlers:
        return []

    source_bytes = source.encode('utf-8')
    tree = parse_source(source, language_name)
    violations: list[dict[str, str]] = []

    for function_node in _function_scopes(tree.root_node):
        calls = _calls_in_function_scope(source_bytes, function_node)

        for index, call in enumerate(calls):
            if not is_db_call(call):
                continue

            has_auth_before_db = any(is_auth_verify_call(previous_call) for previous_call in calls[:index])

            if not has_auth_before_db:
                violations.append(
                    {
                        'rule': RULE_NAME,
                        'reason': 'API handler accesses database before auth.verify()',
                    },
                )

            break

    return violations


def check_endpoint_requires_auth(file_path: str) -> list[dict[str, str]]:
    path = Path(file_path)

    return check_endpoint_requires_auth_from_source(
        path.read_text(encoding='utf-8'),
        language_for_path(file_path),
    )
