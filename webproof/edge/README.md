# WebProof Edge (private)

Closed-source Cloudflare Worker that **ingests and anchors commitments**. Current Rust output is `local_merkle_stub`, `attestation=false`; it is not remotely verified. Only `verification_mode=commitment_only` is accepted. Metadata is validated but not claimed to be bound by the supplied leaf hash.

## API and storage flow

`POST /proof` (Bearer `key_id.secret`) validates the strict v1 envelope, Rust-domain Merkle path, and ≤1 MiB decoded canonical base64 payload. It reserves the unique root in D1, writes bytes to R2, then queues only a small pointer. Success is `202` with `queued` (or current idempotent state), nullable tx hash, and commitment semantics. Same-root immutable conflicts return `409`. `GET /proof/:verification_id` reports `queued | processing | submitted | anchored | failed`.

Hashes accept prefixed/unprefixed 32-byte hex and canonicalize lowercase `0x`. Path direction follows leaf-index bits and historical node domain `watchllm-webproof-local-node-v1\0`. A sibling path cannot independently establish odd-level duplication context.

D1 is authoritative. R2/Queue failures mark a retryable failed reservation; queue failure also removes the object where safe. Duplicate POST repairs failed ingestion. No `202` precedes queue handoff. D1 fixed UTC-minute atomic conditional UPSERT allows exactly 100 accepted validation attempts/key, then returns 429 headers. No KV or isolate counter.

## Chain and retries

Base Sepolia (`84532`) defaults; Base mainnet (`8453`) is explicit. The viem adapter estimates EIP-1559 gas/fees immediately before signing real `anchor(bytes32)` calldata. Missing/placeholder contract, key, or chain mismatch fails closed. Fee ceilings defer with Queue exponential backoff+jitter. Signed hash+nonce persist before raw broadcast; uncertain broadcasts are reconciled, never blindly replaced. Configured confirmations are required for `anchored`. RPC fallback never switches chains. Single-root transactions are v1; production economics require epoch super-root batching.

## Setup (instructions only)

Create D1, R2, producer Queue and DLQ; replace all `wrangler.toml` placeholders; apply `schema.sql` with `npx wrangler d1 execute <name> --remote --file schema.sql`; then set:

```sh
npx wrangler secret put API_KEY_PEPPER
npx wrangler secret put EVM_PRIVATE_KEY
```

Provision `key_id.secret` offline: random 16-byte lowercase-hex salt, with D1 digest BLOB `HMAC-SHA256(API_KEY_PEPPER, salt + NUL + secret)`. Never store/log tokens. A separately reviewed deployed anchor contract is required; no address is invented here.

Run `npm ci && npm test && npm run typecheck && npm run lint && npm run check:schema && npm run dry-run && npm audit --audit-level=high`. Actual deployment/resources/transactions require explicit approval. Broad production also requires a real verifier, batching, and signer KMS/HSM hardening.
