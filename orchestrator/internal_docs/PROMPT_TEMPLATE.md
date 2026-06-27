⇒ WatchLLM Orchestrator (Phase 7) — 5-Day Prompt Pack

Copy **one full day block** below into your agent session. Each block uses the same template; only task, gate, and scope placeholders are filled from `internal_docs/IMPORTANT.md`.

**Repo:** `watchllm/orchestrator` (local: `d:\watchllm\orchestrator`)

---

⇒ Day 01 — Task 01: Skeleton & CLI

⇒ Task Instructions

Today's task:
**ORCH Task 01 — Skeleton & CLI**
Set up the `watchllm-orchestrator` CLI entrypoint using `click`.

Today's gate:
- Running `watchllm-orchestrator --help` works.

> Scope Constraints
Only work on: CLI scaffolding (Task 01 only).

---

⇒ Day 02 — Task 02: Identity Manager

⇒ Task Instructions

Today's task:
**ORCH Task 02 — Identity Manager**
Build a token generation system that creates signed JWTs containing agent role claims (e.g., `role: frontend-agent`, `permissions: read-write`).

Today's gate:
- `watchllm-orchestrator issue-token --role architect` outputs a valid token.

> Scope Constraints
Only work on: Identity Management (Task 02 only).

---

⇒ Day 03 — Task 03: Model Router

⇒ Task Instructions

Today's task:
**ORCH Task 03 — Model Router**
Create the routing logic that accepts a task description and selects the cheapest capable model (e.g., Claude 3 Haiku for simple formatting, Opus for architecture).

Today's gate:
- A unit test verifies the router correctly yields provider URLs based on input logic.

> Scope Constraints
Only work on: Model Routing logic (Task 03 only).

---

⇒ Day 04 — Task 04: Policy Graph

⇒ Task Instructions

Today's task:
**ORCH Task 04 — Policy Graph**
Create a registry that maps directory paths to required roles (e.g., `/src/db/` requires `role: backend-agent`).

Today's gate:
- Unit tests verify that the PolicyGraph correctly returns required roles for specific paths.

> Scope Constraints
Only work on: Policy mapping logic (Task 04 only).

---

⇒ Day 05 — Task 05: Agent Spawner API

⇒ Task Instructions

Today's task:
**ORCH Task 05 — Agent Spawner API**
Write a subprocess wrapper that spawns an autonomous agent (like Aider) and injects the Orchestrator Token into its environment variables.

Today's gate:
- `watchllm-orchestrator spawn --role frontend-agent --command "aider"` successfully launches the agent with `WATCHLLM_AGENT_TOKEN` set.

> Scope Constraints
Only work on: Subprocess spawning and env injection (Task 05 only).
