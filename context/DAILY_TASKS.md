# WATCHLLM — DAILY TASKS (MVP BUILD)

RULE: Do not move to the next day unless the acceptance criteria is fully met.

---

## DAY 1 — Infra + Auth Foundation

TASK:
Set up Cloudflare Worker with Clerk authentication and D1 connection.

SCOPE:
- /workers/*
- No CLI or extension yet

REQUIREMENTS:
- Hono Worker running
- Clerk JWT verification middleware
- D1 binding configured
- /health endpoint

ACCEPTANCE CRITERIA:
- Valid Clerk token → request succeeds
- Invalid token → request rejected
- D1 insert + read works

CONSTRAINTS:
- No business logic
- No rule engine
- No shortcuts in auth

---

## DAY 2 — Data Layer Integrity

TASK:
Implement full D1 schema and repository access layer.

SCOPE:
- /workers/db/*
- schema.sql

REQUIREMENTS:
- All tables created (tenants, users, sessions, diffs, rules, etc.)
- CRUD helpers for:
  - sessions
  - rules
  - diffs

ACCEPTANCE CRITERIA:
- Can create session
- Can attach diff
- Can store and retrieve rules
- Data integrity verified

CONSTRAINTS:
- No enforcement logic
- No partial schema

---

## DAY 3 — CLI Foundation

TASK:
Build Python CLI with authentication and file submission.

SCOPE:
- /cli/*

REQUIREMENTS:
- `watchllm login`
- `watchllm check <file>`
- Store Clerk token locally
- Send file content to Worker

ACCEPTANCE CRITERIA:
- CLI authenticates successfully
- File content reaches Worker
- Worker logs received payload

CONSTRAINTS:
- No rule evaluation yet
- No parsing yet

---

## DAY 4 — AST Parsing Engine

TASK:
Implement Tree-sitter parsing for JS/TS files.

SCOPE:
- /cli/parser/*
- No Worker changes

REQUIREMENTS:
- Parse file into AST
- Extract:
  - function calls
  - imports
  - basic structure

ACCEPTANCE CRITERIA:
- Given a file:
  - returns list of function calls
  - returns list of imports
- Output is deterministic

CONSTRAINTS:
- No rules yet
- No heuristics

---

## DAY 5 — First Rule (Auth Enforcement)

TASK:
Implement `endpoint_requires_auth` rule.

SCOPE:
- /cli/rules/*
- parser integration

REQUIREMENTS:
- Detect API handler
- Check if `auth.verify()` exists before DB usage

ACCEPTANCE CRITERIA:
- Bad file → BLOCKED
- Good file → PASS
- Output includes rule name + reason

CONSTRAINTS:
- Hard block only
- No LLM
- No approximations

---

## DAY 6 — Rule Engine (Multi-rule Support)

TASK:
Generalize rule evaluation system.

SCOPE:
- /cli/rules/*
- evaluator module

REQUIREMENTS:
- Support multiple rules
- Severity levels
- Aggregated violations

Add rules:
- forbidden imports
- basic secret detection

ACCEPTANCE CRITERIA:
- Multiple violations detected in one run
- Structured output (JSON-like)

CONSTRAINTS:
- No UI formatting
- No LLM

---

## DAY 7 — VS Code Blocking (CRITICAL)

TASK:
Implement save-time enforcement in VS Code.

SCOPE:
- /vscode-extension/*

REQUIREMENTS:
- Hook into onWillSaveTextDocument
- Call CLI or Worker
- Block save on violation

ACCEPTANCE CRITERIA:
- Violating file cannot be saved
- Clean file saves normally

CONSTRAINTS:
- No fallback mode
- No silent warnings

---

## DAY 8 — Violation UX

TASK:
Improve violation output clarity.

SCOPE:
- CLI + extension output layer

REQUIREMENTS:
- Show:
  - rule name
  - file location
  - reason
- Clean formatting

ACCEPTANCE CRITERIA:
- Developer understands violation in <5 seconds
- No ambiguous messages

CONSTRAINTS:
- No UI overengineering

---

## DAY 9 — Architecture Memory (Graph v1)

TASK:
Build repo structure graph.

SCOPE:
- /cli/graph/*
- KV integration (Worker)

REQUIREMENTS:
- Detect modules (folder-based)
- Detect import relationships
- Store in KV

ACCEPTANCE CRITERIA:
- Graph reflects actual repo structure
- Can query module dependencies

CONSTRAINTS:
- No LLM
- No summaries

---

## DAY 10 — Cross-File Enforcement

TASK:
Implement service boundary rule.

SCOPE:
- rule engine + graph

REQUIREMENTS:
- Rule:
  - Module A cannot import Module B unless allowed

ACCEPTANCE CRITERIA:
- Cross-file violation detected
- Block triggered correctly

CONSTRAINTS:
- Must use graph
- No heuristics

---

## DAY 11 — LLM Explanation Layer

TASK:
Add explanation + suggestion layer.

SCOPE:
- /workers/llm/*
- CLI integration

REQUIREMENTS:
- Input:
  - violation + code
- Output:
  - explanation
  - suggested fix

ACCEPTANCE CRITERIA:
- LLM explains violation correctly
- Does NOT affect enforcement decision

CONSTRAINTS:
- LLM cannot override rules
- No blocking logic in LLM

---

## DAY 12 — Audit Logging

TASK:
Persist sessions, diffs, violations.

SCOPE:
- Worker audit module
- R2 integration

REQUIREMENTS:
- Store:
  - session
  - diff
  - violations

ACCEPTANCE CRITERIA:
- Can reconstruct:
  - what was blocked
  - why

CONSTRAINTS:
- No analytics
- No dashboards beyond minimal

---

## DAY 13 — Shadow Mode

TASK:
Implement enforcement modes.

SCOPE:
- CLI + Worker

REQUIREMENTS:
- Modes:
  - shadow (warn)
  - enforce (block)

ACCEPTANCE CRITERIA:
- Shadow logs violations without blocking
- Enforce blocks

CONSTRAINTS:
- No mixed behavior
- Mode must be explicit

---

## DAY 14 — Reality Test

TASK:
Run WatchLLM on real code.

SCOPE:
- Entire system

REQUIREMENTS:
- Test on:
  - messy code
  - AI-generated code

ACCEPTANCE CRITERIA:
- At least 3 real violations caught
- At least 2 forced rewrites
- False positives acceptable but not dominant

CONSTRAINTS:
- No tweaking rules mid-test
- No lowering standards

---

# FINAL RULE

If a day fails:
- Fix it
- Do not proceed

This is not a checklist.
This is a gating system.