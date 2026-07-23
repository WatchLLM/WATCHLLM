import hashlib

import pytest
import requests
import responses

from watchllm_webproof import AgentClosedError, UnsupportedSchemeError, VerifiableAgent

CONFIG = {"routes": [{
    "domain": "example.com", "prover_mode": "reclaim", "sensitivity": "high", "session_ttl": 3600,
}]}


@responses.activate
def test_get_post_and_generic_request_record_contract_without_secrets():
    responses.add(responses.GET, "https://example.com/start?token=secret", status=200, body="payload")
    responses.add(responses.POST, "https://example.com/items", status=201)
    responses.add(responses.DELETE, "https://example.com/items/1", status=204)
    with VerifiableAgent(CONFIG, session_id="fixed") as agent:
        assert agent.get("https://example.com/start?token=secret", headers={"Authorization": "secret"}).text == "payload"
        assert agent.post("https://example.com/items", json={"secret": True}).status_code == 201
        assert agent.request("DELETE", "https://example.com/items/1").status_code == 204
        record = agent.records[0]
        assert record["path"] == "/start"
        assert record["prover_mode"] == "reclaim"
        assert record["sensitivity"] == "high"
        assert record["session_ttl"] == 3600
        assert "secret" not in repr(agent.records)
        assert agent.proof()["leaf_count"] == 3


@responses.activate
def test_sync_streaming_unconsumed():
    responses.add(responses.GET, "https://example.com/data", body=b"payload")
    with VerifiableAgent(CONFIG) as agent:
        response = agent.get("https://example.com/data", stream=True)
        assert response._content is False
        response.close()


@responses.activate
def test_session_persistence_true_persists_cookies():
    responses.add(responses.GET, "https://example.com/one", status=200, headers={"Set-Cookie": "sid=secret; Path=/"})
    responses.add(responses.GET, "https://example.com/two", status=200)
    with VerifiableAgent() as agent:
        agent.get("https://example.com/one")
        agent.get("https://example.com/two")
        assert agent.session.cookies["sid"] == "secret"
        assert responses.calls[1].request.headers["Cookie"] == "sid=secret"


@responses.activate
def test_session_persistence_false_uses_per_request_sessions():
    responses.add(responses.GET, "https://example.com/one", status=200, headers={"Set-Cookie": "sid=secret; Path=/"})
    responses.add(responses.GET, "https://example.com/two", status=200)
    with VerifiableAgent({"session_persistence": False}) as agent:
        agent.get("https://example.com/one")
        agent.get("https://example.com/two")
        with pytest.raises(RuntimeError, match="unavailable"):
            _ = agent.session
    assert "Cookie" not in responses.calls[1].request.headers


@responses.activate
def test_nonpersistent_stream_owns_session_until_response_close(monkeypatch):
    closed = []
    original = requests.Session.close

    def close(session):
        closed.append(session)
        original(session)

    monkeypatch.setattr(requests.Session, "close", close)
    responses.add(responses.GET, "https://example.com/data", body=b"payload")
    agent = VerifiableAgent({"session_persistence": False})
    response = agent.get("https://example.com/data", stream=True)
    assert not closed
    response.close()
    assert len(closed) == 1
    agent.close()


def test_custom_session_is_not_closed_and_requires_persistence():
    session = requests.Session()
    agent = VerifiableAgent(session=session)
    agent.close()
    assert session.headers is not None
    with pytest.raises(ValueError, match="requires session_persistence=true"):
        VerifiableAgent({"session_persistence": False}, session=session)
    session.close()


def test_request_failure_recorded():
    session = requests.Session()
    session.mount("https://", _FailingAdapter())
    agent = VerifiableAgent(CONFIG, session=session)
    with pytest.raises(requests.ConnectionError):
        agent.get("https://example.com/fail")
    assert agent.records[0]["error_type"] == "ConnectionError"
    session.close()


class _FailingAdapter(requests.adapters.BaseAdapter):
    def send(self, request, **kwargs):
        raise requests.ConnectionError("offline")

    def close(self):
        pass


@pytest.mark.parametrize("url", ["ftp://example.com/x", "ws://example.com", "example.com", "https://user:pass@example.com"])
def test_unsupported_urls(url):
    with pytest.raises(UnsupportedSchemeError):
        VerifiableAgent().get(url)


def test_no_config_context_manager_proof_keys_and_lifecycle():
    with VerifiableAgent(session_id="fixed") as agent:
        proof = agent.proof()
        assert set(proof) == {
            "proof_type", "proof_version", "attestation", "algorithm", "aggregation_enabled",
            "merkle_root", "leaf_count", "session_id",
        }
        assert proof["proof_type"] == "local_merkle_stub"
        assert proof["proof_version"] == "1.0.0"
        assert proof["attestation"] is False
        assert proof["merkle_root"] == hashlib.sha256(b"").hexdigest()
    with pytest.raises(AgentClosedError):
        agent.get("https://example.com")
