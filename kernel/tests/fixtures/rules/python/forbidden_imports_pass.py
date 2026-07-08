# SHOULD PASS: no forbidden imports — only safe stdlib and third-party
import json
import pathlib
from typing import Optional
from datetime import datetime


def process(data: dict) -> Optional[str]:
    """Safe data processing, no forbidden modules."""
    path = pathlib.Path(data.get("file", ""))
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None
