import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from watchllm_webproof.accumulator import LocalMerkleAccumulator, canonical_leaf

VECTORS = json.loads((Path(__file__).parent / "vectors" / "commitment-v1.json").read_text())


@pytest.mark.parametrize("vector", VECTORS["vectors"], ids=lambda vector: vector["name"])
def test_historical_python_contract_golden_vectors(vector):
    accumulator = LocalMerkleAccumulator()
    for record, expected in zip(vector["records"], vector["canonical"], strict=True):
        historical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        assert historical == expected.encode()
        assert bytes(canonical_leaf(record)) == historical
        accumulator.record(record)
    assert accumulator.proof("golden")["merkle_root"] == vector["merkle_root"]
    assert accumulator.proof("golden")["leaf_count"] == len(vector["records"])


def test_proof_contract_is_local_and_non_attesting():
    proof = LocalMerkleAccumulator().proof("session")
    assert proof == {
        "proof_type": "local_merkle_stub",
        "proof_version": "1.0.0",
        "attestation": False,
        "algorithm": "sha256-local-merkle-v1",
        "aggregation_enabled": True,
        "merkle_root": hashlib.sha256(b"").hexdigest(),
        "leaf_count": 0,
        "session_id": "session",
    }


def test_records_are_deeply_immutable_snapshots():
    record = {"nested": {"items": [1, 2]}, "ok": True}
    accumulator = LocalMerkleAccumulator()
    accumulator.record(record)
    original_root = accumulator.proof("x")["merkle_root"]
    record["nested"]["items"].append(3)
    snapshot = accumulator.records
    snapshot[0]["nested"]["items"].append(4)
    assert accumulator.records == ({"nested": {"items": [1, 2]}, "ok": True},)
    assert accumulator.proof("x")["merkle_root"] == original_root


@pytest.mark.parametrize("value", [1.5, float("nan"), float("inf"), {"set": {1}}, {1: "not a string key"}, {"bytes": b"no"}, {"object": object()}])
def test_rejects_values_outside_supported_commitment_contract(value):
    with pytest.raises((TypeError, ValueError), match="unsupported|keys must be strings"):
        LocalMerkleAccumulator().record(value if isinstance(value, dict) else {"value": value})


def test_arbitrary_precision_integers_cross_native_boundary_without_truncation():
    enormous = 10**500
    accumulator = LocalMerkleAccumulator()
    accumulator.record({"enormous": enormous, "negative": -enormous})
    expected = json.dumps({"enormous": enormous, "negative": -enormous}, sort_keys=True, separators=(",", ":")).encode()
    assert bytes(canonical_leaf({"negative": -enormous, "enormous": enormous})) == expected
    assert accumulator.records[0]["enormous"] == enormous


def test_rejects_circular_and_excessively_nested_values():
    circular = []
    circular.append(circular)
    with pytest.raises(ValueError, match="circular references"):
        LocalMerkleAccumulator().record({"value": circular})

    nested = None
    for _ in range(130):
        nested = [nested]
    with pytest.raises(ValueError, match="nesting exceeds"):
        LocalMerkleAccumulator().record({"value": nested})


def test_rejects_lone_unicode_surrogates():
    with pytest.raises(ValueError, match="lone surrogates"):
        LocalMerkleAccumulator().record({"value": "\ud800"})


def test_concurrent_records_are_safe_and_complete():
    accumulator = LocalMerkleAccumulator()
    with ThreadPoolExecutor(max_workers=12) as executor:
        list(executor.map(lambda value: accumulator.record({"value": value}), range(500)))
    records = accumulator.records
    assert len(records) == 500
    assert {record["value"] for record in records} == set(range(500))
    assert accumulator.proof("concurrent")["leaf_count"] == 500
