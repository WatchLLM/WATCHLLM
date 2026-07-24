# Private WebProof Replay extension

This opt-in extension mounts the WebProof dashboard over the public Replay server. It stores a read-through SQLite projection; SQLite is not an authority for remote proof status.

## Configuration

- `REPLAY_WEBPROOF_INGEST_TOKEN` — required for `POST /api/internal/proofs/snapshot`. If unset, mutation fails closed with 404.
- `WEBPROOF_WORKER_BASE_URL` and `WEBPROOF_WORKER_API_KEY` — both required for server-only refresh of a **known** proof via `GET /proof/:id`. The browser never receives these values. No list endpoint or arbitrary target URL is proxied.
- `WEBPROOF_TIMEOUT_MS` (default 2500, max 10000), `WEBPROOF_MAX_RESPONSE_BYTES` (default 65536, max 262144), `WEBPROOF_STALE_MS` (default 300000).

Run `node src/webproof-private/server/index.cjs` and `npx vite --config src/webproof-private/vite.config.ts`. Production frontend output goes to ignored `replay/.private-build/`, never the tracked/exported public client tree.

Snapshot ingest accepts only the fixed local-merkle commitment schema and optionally an explicit `run_id` + `step_id`. It verifies step ownership in that run and the domain-separated Merkle authentication path before insertion. Target data is reduced to lowercase DNS domain plus path without query/fragment. Stored raw display data is recursively redacted and capped at 16 KiB. It is collapsed in the UI and omitted from PDFs.

`commitment_only` with `attestation:false` means exactly that: local inclusion-path verification is not remote verification and does not attest origin, transport, content truth, or signer identity. Worker failure serves an existing snapshot as stale and never promotes status. A missing local snapshot returns 404; reads never invent or discover Worker IDs.
