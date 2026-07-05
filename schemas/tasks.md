# WatchLLM Schemas Tasks

## Task 01 — Skeleton
Status: Complete

Gate:
- Structure is created.

Scope:
- Setup `schemas/v1/` directory.

---

## Task 02 — Event Schema
Status: Complete

Gate:
- `event.json` is a valid Draft-07 schema.

Scope:
- Write `schemas/v1/event.json`.

---

## Task 03 — Violation Schema
Status: Complete

Gate:
- `violation.json` is a valid Draft-07 schema.

Scope:
- Write `schemas/v1/violation.json`.

---

## Task 04 — Decision Schema
Status: Complete

Gate:
- `decision.json` is a valid Draft-07 schema.

Scope:
- Write `schemas/v1/decision.json`.

---

## Task 05 — Kernel Execution Result Schema
Status: Complete

Gate:
- `kernel_execution_result.json` is a valid Draft-07 schema matching the Rust runtime output.

Scope:
- Write `schemas/v1/kernel_execution_result.json`.
- Covers Rust/Wasm `KernelExecutionResult` cross-component contract.

---

*All schemas audited 2026-06-15. Python KernelResult and Rust KernelExecutionResult both validate against their respective schemas. See `AUDIT.md` for details.*
