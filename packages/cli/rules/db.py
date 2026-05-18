from pathlib import Path

from parser.calls import extract_function_calls_from_source
from parser.setup import LanguageName, language_for_path

DB_CALLS = {'query'}
DB_CALL_SUFFIXES = ('.DB.prepare', '.DB.batch', '.DB.exec')


def is_db_call(call: str) -> bool:
    return call in DB_CALLS or call.endswith(DB_CALL_SUFFIXES)


def detect_db_calls_from_source(source: str, language_name: LanguageName) -> list[str]:
    return [call for call in extract_function_calls_from_source(source, language_name) if is_db_call(call)]


def detect_db_calls(file_path: str) -> list[str]:
    path = Path(file_path)

    return detect_db_calls_from_source(path.read_text(encoding='utf-8'), language_for_path(file_path))
