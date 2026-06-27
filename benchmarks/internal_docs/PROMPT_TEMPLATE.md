⇒ WatchLLM Benchmarks — 4-Day Prompt Pack

Copy **one full day block** below into your agent session. Each block uses the same template; only task, gate, and scope placeholders are filled from `internal_docs/IMPORTANT.md`.

**Repo:** `watchllm/benchmarks` (local: `d:\watchllm\benchmarks`)

---

⇒ Day 01 — Task 01: Skeleton & CLI Setup

⇒ Task Instructions

Today's task:
**BENCHMARKS Task 01 — Skeleton**
Set up the `watchllm-benchmarks` CLI using `click` and structure the suite loader.

Today's gate:
- Running `watchllm-benchmarks --help` outputs the CLI commands.

> Scope Constraints
Only work on: CLI scaffolding (Task 01 only).

---

⇒ Day 02 — Task 02: Parser Benchmarks

⇒ Task Instructions

Today's task:
**BENCHMARKS Task 02 — Parser Benchmarks**
Measure raw AST parsing latency. Write scripts to time Tree-sitter parsing of heavy source files.

Today's gate:
- Running parser benchmarks yields execution times under 5ms for 1k lines of code.

> Scope Constraints
Only work on: Parsing latency measurements (Task 02 only).

---

⇒ Day 03 — Task 03: Rule Evaluator Benchmarks

⇒ Task Instructions

Today's task:
**BENCHMARKS Task 03 — Rule Evaluator Benchmarks**
Measure the cost of AST traversal and rule execution.

Today's gate:
- Rule benchmarks yield execution times isolated from parser overhead.

> Scope Constraints
Only work on: Rule traversal cost logic (Task 03 only).

---

⇒ Day 04 — Task 04: E2E Pipeline Benchmarks

⇒ Task Instructions

Today's task:
**BENCHMARKS Task 04 — E2E Pipeline Benchmarks**
Measure the total write-path delay from file detection to ALLOW/BLOCK resolution, outputting a JSON regression report.

Today's gate:
- `watchllm-benchmarks run` yields a complete JSON output with P50/P99 latency data.

> Scope Constraints
Only work on: Aggregate timing and reporting (Task 04 only).
