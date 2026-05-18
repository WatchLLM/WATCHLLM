from typing import Callable

from parser.setup import LanguageName

Violation = dict[str, object]
Rule = Callable[[str, LanguageName], list[Violation]]
