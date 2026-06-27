# WatchLLM Orchestrator Audit Specification (Phase 7 — Orchestrator)

This document defines the expected perfect state of the **WatchLLM Orchestrator** (Phase 7). It outlines the architecture, rules, interface contracts, and edge cases necessary to pass a complete verification run.

---

## 1. Purpose & Scope
The Orchestrator is a Python-based server and CLI application. Its purpose is to manage model routing (cost/performance arbitration), issue JWT-based agent identity tokens (Non-Human Identity), maintain a path-to-role Policy Graph, and spawn autonomous agents with restricted privileges. It operates at the command/configuration level, configuring the environment variables that the local Kernel later enforces.

---

## 2. Expected Directory & File Layout
A perfect implementation must contain:
```
d:\watchllm\orchestrator/
├── orchestrator/
│   ├── __init__.py           # Package exports
│   ├── cli.py                # Click CLI command definitions
│   ├── identity.py           # JWT creation and validation engine (IdentityManager)
│   ├── model_router.py       # LLM provider routing and fallback logic (ModelRouter)
│   ├── policy_graph.py       # Directory path-to-role policy mapper (PolicyGraph)
│   └── spawner.py            # Subprocess wrapper that injects identity tokens
├── tests/
│   ├── test_cli.py
│   ├── test_identity.py
│   ├── test_model_router.py
│   ├── test_policy_graph.py
│   └── test_spawner.py
├── pyproject.toml            # Project metadata manifest
└── tasks.md                  # Active gate checklist
```

---

## 3. Core Component Responsibilities & Contracts

### A. Identity Manager (`identity.py`)
- Issues cryptographically signed JSON Web Tokens (JWTs) representing the agent's identity.
- Tokens must include role claims (e.g. `role: frontend-agent`, `permissions: read-write`, `exp: <timestamp>`).
- Exposes validation interfaces for the Kernel to verify incoming tokens before enforcing permissions.

### B. Model Router (`model_router.py`)
- Standardizes requests to multiple providers (Anthropic, OpenAI, local models).
- Implements load-balancing, performance-cost routing (e.g., routing formatting changes to cheaper models, refactoring to Opus), and fallback mechanisms.

### C. Policy Graph (`policy_graph.py`)
- Maps filesystem patterns/directories to specific permission levels (e.g., `/db/` folder requires `db-write` permission).
- Exposes lookup methods to query required permissions for a given path.

### D. Agent Spawner (`spawner.py`)
- Launches the autonomous agent (e.g., `aider`) as a child process.
- Injects the signed JWT into the environment variable: `WATCHLLM_AGENT_TOKEN`.

---

## 4. CLI & Interface Contracts

- `watchllm-orchestrator issue-token --role <role>`: Generates and prints a signed JWT token containing claims.
- `watchllm-orchestrator spawn --role <role> --command "<cmd>"`: Spawns the agent process with the JWT injected.
- `watchllm-orchestrator route --task "<desc>"`: Queries the router and prints the selected model configuration.

---

## 5. Critical Edge Cases & Error Recovery

| Edge Case | Expected Perfect Behavior |
|---|---|
| **Token Expiry** | When the JWT token expires, the Kernel must intercept this and block further write operations immediately. The spawner must support token renewal callbacks. |
| **Provider Down** | If the primary LLM provider fails (e.g. OpenAI outage), the Model Router must catch the timeout and transparently route the request to a secondary fallback provider. |
| **Path Normalization** | The Policy Graph must normalize relative path lookups and prevent directory traversal bypasses (e.g. `/db/../other` should resolve correctly). |
| **Token Erasure** | If a spawned agent attempts to delete `WATCHLLM_AGENT_TOKEN` from its environment, the Kernel (executing outside the agent's process space) must default to a guest/untrusted policy (fail-closed). |

---

## 6. Verification Checklist
To confirm Orchestrator compliance, run:
1. **Token Generation**: Generate an identity token:
   ```bash
   watchllm-orchestrator issue-token --role backend-agent
   ```
   Verify the output is a valid JWT containing the claims.
2. **Model Routing Test**: Route a task description:
   ```bash
   watchllm-orchestrator route --task "Add a new endpoint with db write"
   ```
   Verify it selects a premium reasoning model.
3. **Policy Graph Match**: Register a policy and query permissions for a file under `/db/schema.sql`.
4. **Execution Spawner**: Launch a shell script via spawner. Verify that `WATCHLLM_AGENT_TOKEN` is present in the environment variables.
5. **Unit Tests**: Run Python test suite:
   ```bash
   pytest tests/
   ```
