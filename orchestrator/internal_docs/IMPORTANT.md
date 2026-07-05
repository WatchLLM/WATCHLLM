# WatchLLM Orchestrator (Phase 7)

## 0) Purpose

This document defines the **orchestrator layer** for WatchLLM. The goal is to provide a Python-based centralized orchestration layer that manages model routing, identity-aware execution, and dynamic policy bindings.

---

## 1) Scope

### In scope
* A Python server/CLI (`watchllm-orchestrator`) built with FastAPI or Click.
* `ModelRouter`: Abstraction for routing requests to different LLM providers based on logic.
* `IdentityManager`: Issuing JWTs or tokens representing agent permission levels.
* `PolicyGraph`: A system to bind project paths to specific WatchLLM rule sets.

### Out of scope
* Modifying the WatchLLM Kernel. (Orchestrator configures the environment; Kernel enforces it).
* Generating actual code for the end-user.

---

## 2) Architecture Rules

### 2.1 The Token Rule
Agents do not have root access by default. The Orchestrator layer issues an Identity Token to the agent's environment (`WATCHLLM_AGENT_TOKEN`). The Kernel uses this to restrict access (e.g., a "frontend-agent" identity cannot modify `database.py`).

### 2.2 Provider Agnostic
The Model Router must support standard OpenAI-compatible API schemas and Anthropic schemas.

---

## 3) Implementation Order

1. **Skeleton & CLI**: Basic entry points.
2. **Identity Manager**: Token issuance and validation.
3. **Model Router**: LLM fallback and load balancing logic.
4. **Policy Graph**: Mapping rule sets to identities.
5. **Integration API**: An endpoint/CLI wrapper to spawn an agent with a specific identity.

---

## 4) Definition of Done
* We can spawn an agent via `watchllm-orchestrator spawn --identity frontend-agent`.
* The spawned agent has restricted boundaries set by the Orchestrator token.
