from pathlib import Path

from .setup import LanguageName, language_for_path, parse_source

HTTP_METHODS = {'get', 'post', 'put', 'patch', 'delete'}


def _node_text(source: bytes, start_byte: int, end_byte: int) -> str:
    return source[start_byte:end_byte].decode('utf-8')


def _has_function_argument(node) -> bool:
    arguments = node.child_by_field_name('arguments')

    if arguments is None:
        return False

    return any(child.type in {'arrow_function', 'function_expression'} for child in arguments.children)


def _route_path(source: bytes, node) -> str:
    arguments = node.child_by_field_name('arguments')

    if arguments is None:
        return ''

    for child in arguments.children:
        if child.type == 'string':
            return _node_text(source, child.start_byte, child.end_byte).strip('\'"')

    return ''


def _method_name(source: bytes, node) -> str | None:
    function_node = node.child_by_field_name('function')

    if function_node is None or function_node.type != 'member_expression':
        return None

    property_node = function_node.child_by_field_name('property')

    if property_node is None:
        return None

    method = _node_text(source, property_node.start_byte, property_node.end_byte)

    if method in HTTP_METHODS:
        return method

    return None


def detect_api_handlers_from_source(source: str, language_name: LanguageName) -> list[dict[str, str]]:
    source_bytes = source.encode('utf-8')
    tree = parse_source(source, language_name)
    handlers: list[dict[str, str]] = []

    def walk(node) -> None:
        if node.type == 'call_expression':
            method = _method_name(source_bytes, node)

            if method is not None and _has_function_argument(node):
                handlers.append(
                    {
                        'type': 'route',
                        'method': method,
                        'path': _route_path(source_bytes, node),
                    },
                )

        if node.type == 'export_statement':
            for child in node.children:
                if child.type == 'function_declaration':
                    name_node = child.child_by_field_name('name')

                    if name_node is not None:
                        handlers.append(
                            {
                                'type': 'exported_function',
                                'name': _node_text(source_bytes, name_node.start_byte, name_node.end_byte),
                            },
                        )

        for child in node.children:
            walk(child)

    walk(tree.root_node)

    return handlers


def detect_api_handlers(file_path: str) -> list[dict[str, str]]:
    path = Path(file_path)

    return detect_api_handlers_from_source(path.read_text(encoding='utf-8'), language_for_path(file_path))
