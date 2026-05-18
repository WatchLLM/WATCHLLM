from pathlib import Path

from .setup import LanguageName, language_for_path, parse_source


def _node_text(source: bytes, start_byte: int, end_byte: int) -> str:
    return source[start_byte:end_byte].decode('utf-8')


def extract_imports_from_source(source: str, language_name: LanguageName) -> list[str]:
    source_bytes = source.encode('utf-8')
    tree = parse_source(source, language_name)
    imports: list[str] = []

    def walk(node) -> None:
        if node.type == 'import_statement':
            for child in node.children:
                if child.type == 'string':
                    imports.append(_node_text(source_bytes, child.start_byte, child.end_byte).strip('\'"'))
                    break

        for child in node.children:
            walk(child)

    walk(tree.root_node)

    return imports


def extract_imports(file_path: str) -> list[str]:
    path = Path(file_path)

    return extract_imports_from_source(path.read_text(encoding='utf-8'), language_for_path(file_path))
