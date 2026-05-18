# WATCHLLM — ARCHITECTURE

## Enforcement Hierarchy (ABSOLUTE)

1. Deterministic AST Rules (FINAL AUTHORITY)
2. Architecture Graph (STRUCTURAL CONSTRAINTS)
3. LLM (EXPLANATION ONLY)

---

## System Components

### CLI (Python)
- runs AST checks locally
- primary enforcement engine
- supports enforce and shadow modes
- can run local-only checks for save-time enforcement
- sends check payloads to the Worker during normal CLI execution

### VS Code Extension
- intercepts file save
- checks the current unsaved document content
- uses local-only CLI execution on the save path
- blocks writes in enforce mode
- allows writes with warnings in shadow mode

### Cloudflare Workers
- authentication (Clerk)
- production check ingestion through `/check`
- audit logging
- D1 persistence
- R2 content storage
- LLM explanation endpoint

### Rule Engine
- Tree-sitter based
- deterministic only
- evaluates source content directly
- no LLM decisions

### Architecture Memory
- stored in KV
- graph of services and dependencies

---

## Hard Constraints

- LLM cannot approve or override rules
- No probabilistic enforcement
- No silent failures
- Violations must block in enforce mode
- Shadow mode must be explicit
- Save-time enforcement must not depend on remote network availability

---

## Performance Requirements

- AST checks < 10ms
- total perceived save-path latency < 200ms
- remote ingestion must not be required for local blocking
