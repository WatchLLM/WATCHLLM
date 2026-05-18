from pathlib import Path
from typing import Literal

from tree_sitter import Language, Parser, Tree

LanguageName = Literal['javascript', 'typescript']


def _to_language(value: object) -> Language:
    if isinstance(value, Language):
        return value

    return Language(value)


def get_language(language_name: LanguageName) -> Language:
    if language_name == 'javascript':
        import tree_sitter_javascript

        return _to_language(tree_sitter_javascript.language())

    if language_name == 'typescript':
        import tree_sitter_typescript

        return _to_language(tree_sitter_typescript.language_typescript())

    raise ValueError('Unsupported language')


def create_parser(language_name: LanguageName) -> Parser:
    parser = Parser()
    language = get_language(language_name)

    if hasattr(parser, 'set_language'):
        parser.set_language(language)
    else:
        parser.language = language

    return parser


def language_for_path(file_path: str) -> LanguageName:
    suffix = Path(file_path).suffix.lower()

    if suffix in {'.ts', '.tsx'}:
        return 'typescript'

    if suffix in {'.js', '.jsx', '.mjs', '.cjs'}:
        return 'javascript'

    raise ValueError('Unsupported file type')


def parse_source(source: str, language_name: LanguageName) -> Tree:
    return create_parser(language_name).parse(source.encode('utf-8'))


def parse_file(file_path: str) -> Tree:
    path = Path(file_path)

    return parse_source(path.read_text(encoding='utf-8'), language_for_path(file_path))
