# WatchLLM Orchestrator Tasks

## Task 01 — Skeleton & CLI
Status: Complete

Gate:
- Running `watchllm-orchestrator --help` works.

Scope:
- CLI setup and basic directory structure.

---

## Task 02 — Identity Manager
Status: Complete

Gate:
- `watchllm-orchestrator issue-token --role architect` outputs a valid token.

Scope:
- JWT/token generation and validation.

---

## Task 03 — Model Router
Status: Complete

Gate:
- Unit tests verify correct routing logic.

Scope:
- Fallback and load balancing LLM logic.

---

## Task 04 — Policy Graph
Status: Complete

Gate:
- Unit tests verify path-to-role mappings.

Scope:
- In-memory registry mapping schemas to paths.

---

## Task 05 — Agent Spawner API
Status: Complete

Gate:
- Spawn command launches agent with `WATCHLLM_AGENT_TOKEN` env var.

Scope:
- Subprocess execution and env manipulation.
