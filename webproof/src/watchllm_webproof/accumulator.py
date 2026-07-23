"""Deterministic local accumulator; this is not a remote cryptographic attestation."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def canonical_leaf(record: Mapping[str, Any]) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def leaf_hash(record: Mapping[str, Any]) -> bytes:
    return hashlib.sha256(b"watchllm-webproof-local-leaf-v1\0" + canonical_leaf(record)).digest()


def merkle_root(records: list[Mapping[str, Any]]) -> str:
    """Return a deterministic SHA-256 binary Merkle root, duplicating odd nodes."""
    if not records:
        return hashlib.sha256(b"").hexdigest()
    level = [leaf_hash(record) for record in records]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            hashlib.sha256(b"watchllm-webproof-local-node-v1\0" + level[i] + level[i + 1]).digest()
            for i in range(0, len(level), 2)
        ]
    return level[0].hex()
