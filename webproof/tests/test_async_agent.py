import httpx
import pytest

from watchllm_webproof import AgentClosedError, VerifiableAgent


@pytest.mark.asyncio
async def test_async_requests_cookie_persistence_and_streaming(httpx_mock):
    httpx_mock.add_response(url="https://example.com/one", status_code=200, headers={"set-cookie": "sid=secret; Path=/"})
    httpx_mock.add_response(url="https://example.com/two", status_code=200, content=b"payload")
    async with VerifiableAgent({}) as agent:
        first = await agent.aget("https://example.com/one")
        assert first.status_code == 200
        second = await agent.aget("https://example.com/two", stream=True)
        assert not second.is_stream_consumed
        assert agent.async_client.cookies["sid"] == "secret"
        assert agent.proof()["leaf_count"] == 2
        await second.aclose()
    with pytest.raises(AgentClosedError):
        await agent.aget("https://example.com/three")


@pytest.mark.asyncio
async def test_async_failure_recorded():
    async def fail(request):
        raise httpx.ConnectError("offline", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(fail))
    agent = VerifiableAgent({}, async_client=client)
    with pytest.raises(httpx.ConnectError):
        await agent.aget("https://example.com/fail")
    assert agent.records[0]["error_type"] == "ConnectError"
    await agent.aclose()
    assert not client.is_closed
    await client.aclose()
