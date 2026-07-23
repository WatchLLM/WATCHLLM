# watchllm-webproof

Public Python SDK for recording privacy-minimized HTTP request outcomes and producing a deterministic local Merkle summary.

> **Important:** `local_merkle_stub` is a local SHA-256 accumulator, not a TLS proof, remote-data proof, or cryptographic attestation. `reclaim` and `tlsnotary` route modes are declarative metadata only in this release. No private proof engine is included.

## Install and use

```bash
pip install watchllm-webproof
watchllm verify-url https://api.example.com/health --config webproof.yaml
```

```python
from watchllm_webproof import VerifiableAgent

with VerifiableAgent("webproof.yaml") as agent:
    response = agent.get("https://api.example.com/health", stream=True)
    print(agent.proof())
    response.close()
```

Async requests use the same recorder and an `httpx.AsyncClient`:

```python
async with VerifiableAgent("webproof.yaml") as agent:
    response = await agent.aget("https://example.org/data", stream=True)
    await response.aclose()
    print(agent.proof())
```

Only HTTP and HTTPS are supported. The SDK never records headers, cookies, request/response bodies, URL credentials, or query strings. It records method, normalized host, effective port, path, status/error type, and selected declarative prover mode. It does not eagerly inspect response bodies, so explicit streaming remains streaming.

## Configuration

See [`examples/webproof.yaml`](examples/webproof.yaml). Configuration is strict: unknown or duplicate keys and invalid types are rejected. `metadata` mappings are the forward-extension points. Host routing is case-insensitive and IDNA-normalized. Exact routes win; an `include_subdomains` route matches only label-boundary subdomains, and the most specific parent wins.

## Proof contract

`proof()` always includes `merkle_root`, `leaf_count`, and `session_id`, plus version/type metadata. With aggregation disabled, `merkle_root` is `null`. An empty enabled session has the conventional SHA-256 digest of empty bytes. Records are deterministic for the same request outcomes; timestamps are intentionally excluded.

## Development

```bash
python -m pip install -e '.[test]'
python -m pytest
python -m build
```
