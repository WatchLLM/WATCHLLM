from pathlib import Path

from graph.modules import SUPPORTED_SUFFIXES, detect_modules
from parser.imports import extract_imports


def detect_dependencies(root_path: str) -> list[dict[str, str]]:
    root = Path(root_path).resolve()
    dependencies: list[dict[str, str]] = []

    for path in sorted(root.rglob('*'), key=lambda item: item.as_posix()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue

        relative_parent = path.parent.relative_to(root)
        source_module = relative_parent.as_posix()

        if source_module == '.':
            source_module = ''

        for import_path in extract_imports(str(path)):
            target_module = import_path
            dependency_type = 'external'

            if import_path.startswith('.'):
                imported_path = (path.parent / import_path).resolve()
                candidates = [imported_path]

                if imported_path.suffix.lower() not in SUPPORTED_SUFFIXES:
                    candidates = [imported_path.with_suffix(suffix) for suffix in sorted(SUPPORTED_SUFFIXES)]
                    candidates.extend(imported_path / f'index{suffix}' for suffix in sorted(SUPPORTED_SUFFIXES))
                    candidates.append(imported_path)

                target_path = next((candidate for candidate in candidates if candidate.exists()), imported_path)

                if target_path.is_file() or target_path.suffix.lower() in SUPPORTED_SUFFIXES:
                    target_parent = target_path.parent
                else:
                    target_parent = target_path

                try:
                    relative_target = target_parent.relative_to(root)
                    target_module = relative_target.as_posix()

                    if target_module == '.':
                        target_module = ''

                    dependency_type = 'internal'
                except ValueError:
                    target_module = import_path

            dependencies.append(
                {
                    'source': source_module,
                    'target': target_module,
                    'import': import_path,
                    'type': dependency_type,
                },
            )

    return sorted(
        dependencies,
        key=lambda dependency: (
            dependency['source'],
            dependency['target'],
            dependency['import'],
            dependency['type'],
        ),
    )


def build_dependency_graph(root_path: str) -> dict[str, list[dict[str, str]]]:
    return {
        'modules': detect_modules(root_path),
        'dependencies': detect_dependencies(root_path),
    }


def get_module_dependencies(graph: dict[str, list[dict[str, str]]], module: str) -> list[str]:
    return sorted(
        {
            dependency['target']
            for dependency in graph['dependencies']
            if dependency['source'] == module
        },
    )
