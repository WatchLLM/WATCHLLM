import json
from pathlib import Path

import pytest

from watchllm_webproof import ConfigError, VerifiableAgent, WebProofConfig, load_config

SAMPLE = Path(__file__).parents[1] / "examples" / "webproof.json"


def test_exact_json_sample_and_domain_routing():
    config = load_config(SAMPLE)
    assert config.version == "1.0.0"
    assert config.session_persistence is True
    assert config.aggregation.batch_size == 100
    assert config.aggregation.timeout_seconds == 30
    agent = VerifiableAgent(config_path=SAMPLE)
    route = agent.route_for("WWW.API.EXAMPLE.COM.")
    assert route.domain == "api.example.com"
    assert route.prover_mode == "reclaim"
    assert route.sensitivity == "high"
    assert route.session_ttl == 3600
    assert agent.route_for("notexample.com") is None


def test_no_config_and_typed_or_mapping_config():
    assert VerifiableAgent().config == WebProofConfig()
    assert VerifiableAgent(config={"session_persistence": False}).config.session_persistence is False
    assert VerifiableAgent(config=WebProofConfig()).config.version == "1.0.0"


def test_config_path_conflicts_with_config():
    with pytest.raises(ValueError, match="mutually exclusive"):
        VerifiableAgent({}, config_path=SAMPLE)


def test_most_specific_parent_route_wins():
    base = {"prover_mode": "reclaim", "sensitivity": "low", "session_ttl": 60}
    agent = VerifiableAgent({"routes": [
        dict(base, domain="example.com"),
        dict(base, domain="api.example.com", prover_mode="tlsnotary"),
    ]})
    assert agent.route_for("x.api.example.com").prover_mode == "tlsnotary"


@pytest.mark.parametrize("raw,match", [
    ({"unknown": 1}, "unknown top-level"),
    ({"version": 1}, "string '1.0.0'"),
    ({"session_persistence": 1}, "must be a boolean"),
    ({"routes": {}}, "routes must be a list"),
    ({"routes": [{"domain": "https://example.com", "prover_mode": "reclaim", "sensitivity": "high", "session_ttl": 1}]}, "domain"),
    ({"routes": [{"domain": "example.com", "prover_mode": "fake", "sensitivity": "high", "session_ttl": 1}]}, "reclaim, tlsnotary"),
    ({"routes": [{"domain": "example.com", "prover_mode": "reclaim", "sensitivity": "secret", "session_ttl": 1}]}, "high, low, medium"),
    ({"routes": [{"domain": "example.com", "prover_mode": "reclaim", "sensitivity": "high", "session_ttl": 0}]}, "session_ttl"),
    ({"aggregation": {"batch_size": True}}, "batch_size"),
    ({"aggregation": {"timeout_seconds": 0}}, "timeout_seconds"),
    ({"aggregation": {"surprise": 1}}, "unknown aggregation"),
])
def test_invalid_config(raw, match):
    with pytest.raises(ConfigError, match=match):
        load_config(raw)


def test_extensions_are_explicitly_preserved():
    config = load_config({
        "options": {"future": True},
        "metadata": {"owner": "team"},
        "aggregation": {"options": {"flush": "manual"}},
        "routes": [{
            "domain": "example.com", "prover_mode": "reclaim", "sensitivity": "low", "session_ttl": 60,
            "options": {"vendor": "x"},
        }],
    })
    assert config.options["future"] is True
    assert config.metadata["owner"] == "team"
    assert config.aggregation.options["flush"] == "manual"
    assert config.routes[0].options["vendor"] == "x"


def test_duplicate_json_and_yaml_keys_rejected(tmp_path):
    json_path = tmp_path / "config.json"
    json_path.write_text('{"version":"1.0.0","version":"1.0.0"}')
    with pytest.raises(ConfigError, match="duplicate configuration key"):
        load_config(json_path)
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text('version: "1.0.0"\nversion: "1.0.0"\n')
    with pytest.raises(ConfigError, match="duplicate configuration key"):
        load_config(yaml_path)


def test_duplicate_normalized_domain_rejected():
    route = {"prover_mode": "reclaim", "sensitivity": "low", "session_ttl": 60}
    with pytest.raises(ConfigError, match="duplicate normalized route domain"):
        load_config({"routes": [dict(route, domain="example.com"), dict(route, domain="EXAMPLE.COM.")]})


def test_yaml_sample_remains_supported():
    config = load_config(Path(__file__).parents[1] / "examples" / "webproof.yaml")
    assert config == load_config(json.loads(SAMPLE.read_text()))
