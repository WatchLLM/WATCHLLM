# Now: Context Documents (SERIOUS STARTUP VERSION)

These are not docs for clarity.
These are **execution constraints**.

---

# 1. Product Brief — WatchLLM

## Definition

WatchLLM is a **write-path governance layer** that enforces architectural and security constraints on AI-generated code before it is written or committed.

It is not a code assistant.
It is not a reviewer.
It is a **gatekeeper**.

---

## Core Principle

> Code that violates architecture or security constraints must never be written.

---

## What WatchLLM does

* Intercepts code at **save-time / pre-commit**
* Evaluates against **deterministic rules**
* Blocks violations
* Explains why
* Suggests compliant rewrites

---

## What WatchLLM does NOT do

* Does not generate code
* Does not approve exceptions
* Does not host repositories
* Does not replace CI/CD
* Does not rely on prompt engineering

---

## Why it exists

Because:

* LLMs optimize for **local correctness**
* Systems require **global invariants**

That gap is WatchLLM.

---

# 2. Enforcement Philosophy (Non-Negotiable)

## Hierarchy of authority

```text
1. Deterministic Rules (ABSOLUTE)
2. Architecture Graph (STRUCTURAL TRUTH)
3. LLM (EXPLANATION ONLY)
```

---

## Rule

> If a deterministic rule fires, the code is invalid. No exceptions.

---

## LLM constraint

* Can explain violations
* Can suggest fixes
* Cannot override rules
* Cannot approve code

---

# 3. Rule System Specification (CORE IP)

## Rule Types

### 1. Presence Rules

Ensure something exists

```text
Example:
Every API endpoint must call auth.verify()
```

---

### 2. Absence Rules (MOST IMPORTANT)

Ensure something is NOT missing

```text
Example:
Any DB write must be preceded by input validation
```

---

### 3. Boundary Rules

```text
Service A cannot import Service B
```

---

### 4. Flow Rules

```text
Request → validation → auth → business logic → DB
```

---

## Rule Structure

```json
{
  "rule_key": "endpoint_requires_auth",
  "scope": "/api/**",
  "type": "absence",
  "assert": "must_call(auth.verify) before(db_access)",
  "severity": "critical"
}
```

---

## Enforcement Engine

* Tree-sitter parses AST
* Pattern matcher evaluates rules
* Violations are deterministic
* Output = pass / block / warn

---

# 4. Architecture Memory Spec

## Not summaries. Graph.

### Stored in KV:

```text
repo:{id}:services
repo:{id}:edges
repo:{id}:contracts
repo:{id}:violations_recent
```

---

## Graph Example

```text
Services:
- auth
- billing
- api

Edges:
- api → auth (allowed)
- billing → auth (allowed)
- auth → billing (forbidden)

Contracts:
- billing.createInvoice requires user_id
```

---

## Usage

* Validate cross-file changes
* Prevent forbidden dependencies
* Enforce invariants across services

---

# 5. Write-Path Enforcement Model

## Control Points

1. VS Code save
2. CLI check
3. (later) Git hooks

---

## Flow

```text
User writes code
→ Save triggered
→ AST rules run (local)
→ If violation:
    block immediately
→ Else:
    optional LLM explanation
→ Result shown inline
```

---

## Latency Requirement

* AST: <10ms
* Full pipeline: <200ms perceived

Anything slower → product dies

---

# 6. MVP Scope Lock (STRICT)

You will build ONLY this:

1. Policy bundle ingestion
2. 5–10 deterministic rules
3. AST enforcement engine
4. CLI (`watchllm check`)
5. VS Code save interception
6. Violation output
7. Basic audit logging

---

## Explicitly NOT in MVP

* dashboards beyond minimal
* advanced analytics
* multi-repo orchestration
* complex UI
* fancy onboarding

---

# 7. Success Criteria (Reality Check)

You have product-market signal ONLY if:

### Within 2 weeks of usage:

* A real bug is blocked before commit
* A dev is forced to rewrite code
* A team keeps it enabled voluntarily

---

## Failure signal

* “nice warnings”
* “helpful suggestions”
* “we’ll fix later”

That means you built a tool, not infrastructure.

---

# 8. Execution Constraints

## You will not:

* skip deterministic enforcement
* rely on LLM for decisions
* optimize UX before enforcement works
* add features before blocking works

---

## You will:

* ship blocking early
* accept friction initially
* prioritize correctness over smoothness

---


