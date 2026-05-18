from pathlib import Path

from .setup import LanguageName, language_for_path, parse_source


def _node_text(source: bytes, start_byte: int, end_byte: int) -> str:
    return source[start_byte:end_byte].decode('utf-8')


def extract_function_calls_from_source(source: str, language_name: LanguageName) -> list[str]:
    source_bytes = source.encode('utf-8')
    tree = parse_source(source, language_name)
    calls: list[str] = []

    def walk(node) -> None:
        if node.type == 'call_expression':
            function_node = node.child_by_field_name('function')

            if function_node is not None:
                calls.append(_node_text(source_bytes, function_node.start_byte, function_node.end_byte))

        for child in node.children:
            walk(child)

    walk(tree.root_node)

    return calls


def extract_function_calls(file_path: str) -> list[str]:
    path = Path(file_path)

    return extract_function_calls_from_source(path.read_text(encoding='utf-8'), language_for_path(file_path))
