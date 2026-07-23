import hashlib

import httpx
import pytest
import requests
import responses

from watchllm_webproof import AgentClosedError, UnsupportedSchemeError, VerifiableAgent

CONFIG = {"routes": [{"hostname": "example.com", "prover": "reclaim", "include_subdomains": True}]}


@responses.activate
def test_sync_records_without_secrets_and_preserves_cookies_redirects():
    responses.add(responses.GET, "https://example.com/start?token=secret", status=302, headers={"Location": "/final", "Set-Cookie": "sid=secret; Path=/"})
    responses.add(responses.GET, "https://example.com/final", status=200, body="payload")
    with VerifiableAgent(CONFIG, session_id="fixed") as agent:
        response = agent.get("https://example.com/start?token=secret", headers={"Authorization": "Bearer secret"})
        assert response.text == "payload"
        assert agent.session.cookies["sid"] == "secret"
        record = agent.records[0]
        assert record["path"] == "/start"
        assert record["status_code"] == 200
        assert record["prover"] == "reclaim"
        assert "secret" not in repr(agent.records)
        assert agent.proof()["leaf_count"] == 1


@responses.activate
def test_sync_streaming_is_not_eagerly_consumed():
    responses.add(responses.GET, "https://example.com/data", body=b"payload")
    agent = VerifiableAgent(CONFIG)
    response = agent.get("https://example.com/data", stream=True)
    assert response._content is False
    assert response.raw is not None
    response.close()
    agent.close()


@responses.activate
def test_sync_session_persists_default_headers():
    session = requests.Session()
    session.headers["X-Test"] = "present"
    responses.add(responses.GET, "https://example.com/one", status=204)
    responses.add(responses.GET, "https://example.com/two", status=204)
    agent = VerifiableAgent(CONFIG, session=session)
    agent.get("https://example.com/one")
    agent.get("https://example.com/two")
    assert all(call.request.headers["X-Test"] == "present" for call in responses.calls)
    agent.close()
    assert session.headers["X-Test"] == "present"  # supplied client remains caller-owned
    session.close()


def test_request_failure_recorded():
    session = requests.Session()
    session.mount("https://", _FailingAdapter())
    agent = VerifiableAgent(CONFIG, session=session)
    with pytest.raises(requests.ConnectionError):
        agent.get("https://example.com/fail")
    assert agent.records[0]["status_code"] is None
    assert agent.records[0]["error_type"] == "ConnectionError"


class _FailingAdapter(requests.adapters.BaseAdapter):
    def send(self, request, **kwargs):
        raise requests.ConnectionError("offline")

    def close(self):
        pass


@pytest.mark.parametrize("url", ["ftp://example.com/x", "ws://example.com", "example.com", "https://user:pass@example.com"])
def test_unsupported_urls(url):
    agent = VerifiableAgent(CONFIG)
    with pytest.raises(UnsupportedSchemeError):
        agent.get(url)


def test_empty_and_deterministic_proof_and_lifecycle():
    empty = VerifiableAgent({}, session_id="fixed")
    proof = empty.proof()
    assert proof["merkle_root"] == hashlib.sha256(b"").hexdigest()
    assert proof["leaf_count"] == 0
    assert proof["attestation"] is False
    empty._record("GET", {"scheme": "https", "hostname": "example.com", "port": 443, "path": "/", "prover": None}, 200, None)
    other = VerifiableAgent({}, session_id="different")
    other._record("GET", {"scheme": "https", "hostname": "example.com", "port": 443, "path": "/", "prover": None}, 200, None)
    assert empty.proof()["merkle_root"] == other.proof()["merkle_root"]
    empty.close()
    with pytest.raises(AgentClosedError):
        empty.get("https://example.com")


def test_disabled_aggregation_has_null_root():
    agent = VerifiableAgent({"aggregation": {"enabled": False}})
    assert agent.proof()["merkle_root"] is None
