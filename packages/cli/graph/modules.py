from pathlib import Path

SUPPORTED_SUFFIXES = {'.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx'}


def detect_modules(root_path: str) -> list[dict[str, str]]:
    root = Path(root_path)
    modules: set[str] = set()

    for path in root.rglob('*'):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            relative_parent = path.parent.relative_to(root)
            module_path = relative_parent.as_posix()

            if module_path == '.':
                module_path = ''

            modules.add(module_path)

    return [{'name': module, 'path': module} for module in sorted(modules)]
