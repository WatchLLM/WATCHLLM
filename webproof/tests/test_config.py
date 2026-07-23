from pathlib import Path

import pytest

from watchllm_webproof import ConfigError, VerifiableAgent, load_config


def test_sample_config_and_domain_routing():
    config = load_config(Path(__file__).parents[1] / "examples" / "webproof.yaml")
    agent = VerifiableAgent(config)
    assert agent.route_for("API.EXAMPLE.COM.").prover == "reclaim"
    assert agent.route_for("www.example.org").prover == "tlsnotary"
    assert agent.route_for("notexample.org") is None
    assert agent.route_for("example.org").prover == "tlsnotary"


def test_exact_and_most_specific_subdomain_routing():
    agent = VerifiableAgent({"routes": [
        {"hostname": "example.com", "prover": "reclaim", "include_subdomains": True},
        {"hostname": "api.example.com", "prover": "tlsnotary", "include_subdomains": True},
        {"hostname": "x.api.example.com", "prover": "reclaim"},
    ]})
    assert agent.route_for("x.api.example.com").prover == "reclaim"
    assert agent.route_for("y.api.example.com").prover == "tlsnotary"


@pytest.mark.parametrize("raw,match", [
    ({"unknown": 1}, "unknown top-level"),
    ({"version": True}, "integer 1"),
    ({"routes": {}}, "routes must be a list"),
    ({"routes": [{"hostname": "https://example.com", "prover": "reclaim"}]}, "hostname"),
    ({"routes": [{"hostname": "example.com", "prover": "fake"}]}, "reclaim, tlsnotary"),
])
def test_invalid_config(raw, match):
    with pytest.raises(ConfigError, match=match):
        load_config(raw)


def test_duplicate_yaml_key_rejected(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("version: 1\nversion: 1\n")
    with pytest.raises(ConfigError, match="duplicate configuration key"):
        load_config(path)


def test_duplicate_route_rejected():
    with pytest.raises(ConfigError, match="duplicate route"):
        load_config({"routes": [
            {"hostname": "example.com", "prover": "reclaim"},
            {"hostname": "EXAMPLE.COM.", "prover": "tlsnotary"},
        ]})
