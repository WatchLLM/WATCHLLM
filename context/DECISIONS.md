# WATCHLLM — DECISIONS

This file records durable product and architecture decisions.

These decisions should not be changed casually. If a decision changes, document why.

---

## DECISION 001 — Deterministic Rules Are Final

WatchLLM enforcement decisions are made by deterministic rules.

The rule engine is the final authority. If a deterministic rule fires in enforce mode, the code is invalid.

LLM output cannot approve, override, suppress, downgrade, or reinterpret a deterministic violation.

---

## DECISION 002 — LLM Is Explanation-Only

The LLM layer exists only to explain violations and suggest compliant rewrites.

It must not be used for:

- approving code
- rejecting code
- deciding severity
- detecting violations
- granting exceptions
- changing enforcement mode

This keeps WatchLLM predictable, auditable, and safe for write-path enforcement.

---

## DECISION 003 — Write Path Comes Before Dashboarding

The MVP prioritises blocking invalid writes over dashboards, analytics, onboarding, or advanced reporting.

A simple blocking loop with clear violations is more important than a polished management interface.

---

## DECISION 004 — Local AST Enforcement Is Primary

The CLI runs deterministic AST rules locally.

Remote Worker ingestion is important for audit logging, persistence, and explanation, but it must not become the source of truth for local blocking.

This prevents network latency or outages from weakening deterministic enforcement.

---

## DECISION 005 — VS Code Save Path Is Local-Only

The VS Code extension must evaluate the current unsaved document content locally.

The save path must not require:

- Worker availability
- R2 availability
- D1 availability
- LLM availability
- network access

Remote ingestion can happen through normal CLI workflows, background tasks, or later async extension flows, but it must not be required for the save decision.

---

## DECISION 006 — Worker Routes Must Be Authenticated

Any route that accepts source code, returns private explanation data, writes audit records, or accesses tenant data must be protected by Clerk authentication.

Public routes should be limited to safe operational endpoints such as health checks.

---

## DECISION 007 — Audit Logs Must Reconstruct Enforcement

Audit storage must allow the system to reconstruct:

- who initiated the check
- which tenant or organisation it belonged to
- which file was checked
- what content or diff was submitted
- which violations were observed
- whether the session completed, passed, or blocked
- when the event occurred

This is required for trust, debugging, and enterprise adoption.

---

## DECISION 008 — Shadow Mode Must Be Explicit

Shadow mode may log violations without blocking, but it must be explicitly configured.

There should be no implicit mixed mode where some violations block and others silently warn without a clear policy.

---

## DECISION 009 — Service Boundaries Are Structural

Service boundary enforcement should come from explicit module and dependency rules, not naming guesses or LLM interpretation.

Path handling must support realistic repository layouts including:

- `src/`
- `apps/`
- `packages/`
- monorepos
- custom workspace roots

When a module cannot be determined safely, the rule should return no violation rather than produce a false positive.

---

## DECISION 010 — Function-Scoped Flow Checks Are Required

Flow-sensitive rules must operate within the relevant AST scope.

For example, `endpoint_requires_auth` must verify that `auth.verify()` occurs before database access inside the same function block.

Global flattened call arrays are not acceptable because they create false positives and false negatives.

---

## DECISION 011 — No Silent Failures

Failures in authentication, parsing, storage, or enforcement should be explicit.

WatchLLM must avoid behaviour where a failed check appears to pass.

Silent failures weaken trust in the product and violate the gatekeeper model.

---

## DECISION 012 — Minimal Scope Until Blocking Works

New features should not be added before the core blocking loop is reliable.

The minimum useful loop is:

```text
code change
→ deterministic rule check
→ violation detected
→ write blocked in enforce mode
→ clear explanation shown
→ audit record stored when remote ingestion is available
```

Everything else is secondary.

---

## DECISION 013 — Current MVP Completion Status

The MVP is close to completion.

Completed foundation:

- Worker auth
- D1 schema
- session and diff repositories
- production `/check` ingestion route
- R2 storage
- LLM explanation endpoint
- CLI login and check commands
- Tree-sitter parsing
- deterministic rules
- service boundary rule
- shadow and enforce modes
- VS Code save-time local blocking

Remaining validation work:

- run against real messy code
- measure false positives
- verify at least three real violations
- force at least two real rewrites
- tighten rules only after the reality test
