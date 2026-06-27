import pytest

from orchestrator.model_router import (
    CAPABILITY_ARCHITECTURE,
    CAPABILITY_SIMPLE,
    ModelRoute,
    ModelRouter,
)


def test_simple_formatting_routes_to_cheapest_haiku():
    router = ModelRouter()

    route = router.route("Format this markdown into clean bullet points")

    assert route.provider == "anthropic"
    assert route.model == "claude-3-haiku-20240307"
    assert route.provider_url == "https://api.anthropic.com/v1/messages"
    assert route.schema == "anthropic"


def test_architecture_routes_to_opus():
    router = ModelRouter()

    route = router.route("Design the system architecture for a scalable orchestrator")

    assert route.provider == "anthropic"
    assert route.model == "claude-3-opus-20240229"
    assert route.provider_url == "https://api.anthropic.com/v1/messages"
    assert CAPABILITY_ARCHITECTURE in route.capabilities


def test_coding_routes_to_openai_compatible_provider():
    router = ModelRouter()

    route = router.route("Implement a Python function and unit test")

    assert route.provider == "openai"
    assert route.model == "gpt-4o-mini"
    assert route.provider_url == "https://api.openai.com/v1/chat/completions"
    assert route.schema == "openai-compatible"


def test_empty_task_defaults_to_simple_cheapest_model():
    router = ModelRouter()

    route = router.route("   ")

    assert route.model == "claude-3-haiku-20240307"
    assert CAPABILITY_SIMPLE in route.capabilities


def test_no_capable_route_raises_lookup_error():
    router = ModelRouter(
        catalog=[
            ModelRoute(
                provider="test",
                model="cheap-general",
                provider_url="https://example.test/v1/chat",
                schema="openai-compatible",
                capabilities=(CAPABILITY_SIMPLE,),
                cost_rank=1,
            )
        ]
    )

    with pytest.raises(LookupError):
        router.route("Plan the architecture for a distributed system")
