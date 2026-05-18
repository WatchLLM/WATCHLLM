# WATCHLLM — MICRO TASKS (AIDER EXECUTION)

RULE:
- Execute ONE task at a time
- Commit after each task
- Reset Aider every 2–3 tasks

---

# DAY 1 — INFRA + AUTH

## TASK 1.1 — Worker Setup

SCOPE:
- workers/index.ts

DO NOT TOUCH:
- CLI
- extension

REQUIREMENTS:
- Hono app initialized
- basic route `/health`

ACCEPTANCE:
- GET /health returns 200

---

## TASK 1.2 — Clerk Middleware

SCOPE:
- workers/middleware/auth.ts

REQUIREMENTS:
- validate Clerk JWT
- attach user + org to request

ACCEPTANCE:
- valid token passes
- invalid token fails

---

## TASK 1.3 — D1 Connection

SCOPE:
- workers/db/client.ts

REQUIREMENTS:
- connect to D1
- simple query function

ACCEPTANCE:
- insert + read works

---

## TASK 1.4 — Protected Route

SCOPE:
- workers/routes/test.ts

REQUIREMENTS:
- route requiring auth
- test DB write

ACCEPTANCE:
- auth required
- DB write succeeds

---

# DAY 2 — DATA LAYER

## TASK 2.1 — Schema Creation

SCOPE:
- schema.sql

REQUIREMENTS:
- all tables defined

ACCEPTANCE:
- DB initializes without errors

---

## TASK 2.2 — Session Repository

SCOPE:
- workers/db/sessions.ts

REQUIREMENTS:
- create session
- fetch session

ACCEPTANCE:
- roundtrip works

---

## TASK 2.3 — Rules Repository

SCOPE:
- workers/db/rules.ts

REQUIREMENTS:
- insert rule
- fetch rules

---

## TASK 2.4 — Diff Repository

SCOPE:
- workers/db/diffs.ts

REQUIREMENTS:
- store diff
- retrieve diff

---

# DAY 3 — CLI

## TASK 3.1 — CLI Setup

SCOPE:
- cli/main.py

REQUIREMENTS:
- basic CLI structure

ACCEPTANCE:
- command runs

---

## TASK 3.2 — Login Command

SCOPE:
- cli/auth.py

REQUIREMENTS:
- store Clerk token locally

ACCEPTANCE:
- token saved + loaded

---

## TASK 3.3 — Check Command

SCOPE:
- cli/check.py

REQUIREMENTS:
- read file
- send to worker

ACCEPTANCE:
- worker receives file

---

# DAY 4 — AST

## TASK 4.1 — Tree-sitter Setup

SCOPE:
- cli/parser/setup.py

REQUIREMENTS:
- initialize parser

---

## TASK 4.2 — Extract Imports

SCOPE:
- cli/parser/imports.py

ACCEPTANCE:
- list imports correctly

---

## TASK 4.3 — Extract Function Calls

SCOPE:
- cli/parser/calls.py

ACCEPTANCE:
- list calls correctly

---

## TASK 4.4 — Detect Handlers

SCOPE:
- cli/parser/api.py

ACCEPTANCE:
- identifies API functions

---

# DAY 5 — AUTH RULE

## TASK 5.1 — Detect DB Calls

SCOPE:
- cli/rules/db.py

---

## TASK 5.2 — Detect auth.verify

SCOPE:
- cli/rules/auth.py

---

## TASK 5.3 — Rule Logic

SCOPE:
- cli/rules/auth.py

ACCEPTANCE:
- DB + no auth → violation

---

## TASK 5.4 — CLI Integration

SCOPE:
- cli/check.py

ACCEPTANCE:
- rule runs on file

---

# DAY 6 — RULE ENGINE

## TASK 6.1 — Rule Interface

SCOPE:
- cli/rules/base.py

---

## TASK 6.2 — Multi-rule Runner

SCOPE:
- cli/rules/engine.py

ACCEPTANCE:
- runs multiple rules

---

## TASK 6.3 — Forbidden Imports Rule

SCOPE:
- cli/rules/imports.py

---

## TASK 6.4 — Secret Detection Rule

SCOPE:
- cli/rules/secrets.py

---

# DAY 7 — VSCODE BLOCKING

## TASK 7.1 — Extension Setup

SCOPE:
- vscode-extension/src/extension.ts

---

## TASK 7.2 — Save Hook

SCOPE:
- extension.ts

---

## TASK 7.3 — CLI Integration

SCOPE:
- extension.ts

ACCEPTANCE:
- blocks save

---

# DAY 8 — UX

## TASK 8.1 — CLI Output Format

SCOPE:
- cli/output.py

---

## TASK 8.2 — VSCode Display

SCOPE:
- extension UI

---

# DAY 9 — GRAPH

## TASK 9.1 — Module Detection

SCOPE:
- cli/graph/modules.py

---

## TASK 9.2 — Dependency Graph

SCOPE:
- cli/graph/deps.py

---

## TASK 9.3 — KV Storage

SCOPE:
- workers/kv/graph.ts

---

# DAY 10 — CROSS FILE

## TASK 10.1 — Rule Definition

SCOPE:
- cli/rules/boundary.py

---

## TASK 10.2 — Graph Integration

SCOPE:
- rule engine

---

# DAY 11 — LLM

## TASK 11.1 — Worker LLM Call

SCOPE:
- workers/llm/review.ts

---

## TASK 11.2 — CLI Integration

SCOPE:
- cli/check.py

---

# DAY 12 — AUDIT

## TASK 12.1 — Session Logging

SCOPE:
- workers/audit/sessions.ts

---

## TASK 12.2 — Violation Logging

SCOPE:
- workers/audit/violations.ts

---

## TASK 12.3 — R2 Storage

SCOPE:
- workers/storage/r2.ts

---

# DAY 13 — MODES

## TASK 13.1 — Mode Flag

SCOPE:
- cli/config.py

---

## TASK 13.2 — Enforcement Toggle

SCOPE:
- rule engine

---

# DAY 14 — TEST

## TASK 14.1 — Run on Real Code

## TASK 14.2 — Validate Violations

## TASK 14.3 — Measure False Positives
