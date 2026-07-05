import pytest

from orchestrator.policy_graph import PolicyBinding, PolicyGraph


def test_basic_mapping():
    graph = PolicyGraph(
        [
            PolicyBinding("/src/db/", "backend-agent"),
        ]
    )

    assert graph.required_role_for_path("/src/db/models.py") == "backend-agent"


def test_exact_directory_match():
    graph = PolicyGraph(
        [
            PolicyBinding("/src/db/", "backend-agent"),
        ]
    )

    assert graph.required_role_for_path("/src/db") == "backend-agent"


def test_no_match():
    graph = PolicyGraph(
        [
            PolicyBinding("/src/db/", "backend-agent"),
        ]
    )

    assert graph.required_role_for_path("/src/frontend/app.py") is None


def test_longest_prefix_wins():
    graph = PolicyGraph(
        [
            PolicyBinding("/src", "general-agent"),
            PolicyBinding("/src/db", "backend-agent"),
        ]
    )

    assert graph.required_role_for_path("/src/db/models.py") == "backend-agent"
    assert graph.required_role_for_path("/src/ui/view.py") == "general-agent"


def test_directory_aware_matching():
    graph = PolicyGraph(
        [
            PolicyBinding("/src/db", "backend-agent"),
        ]
    )

    assert graph.required_role_for_path("/src/db_backup/file.py") is None


def test_path_normalization():
    graph = PolicyGraph(
        [
            PolicyBinding("src\\db\\", "backend-agent"),
        ]
    )

    assert graph.required_role_for_path("src/db/./models.py") == "backend-agent"


def test_validation_empty_path():
    graph = PolicyGraph()

    with pytest.raises(ValueError):
        graph.bind("", "backend-agent")


def test_validation_empty_role():
    graph = PolicyGraph()

    with pytest.raises(ValueError):
        graph.bind("/src/db", "")
