# WatchLLM Benchmarks

## 0) Purpose

This document defines the rules for the `watchllm/benchmarks` repository. The goal is to provide ecosystem-wide performance benchmarking to ensure the Kernel can evaluate codebase writes in under 10 milliseconds.

---

## 1) Scope

### In scope
* A benchmarking CLI built with `click`.
* Latency tracking for tree-sitter AST parsing.
* Execution time tracking for rules validation.
* End-to-end write-path latency validation.
* Report generation (JSON export).

### Out of scope
* Defining new Kernel rules.
* Modifying the AST parser logic.
* Runtime telemetry interception.

---

## 2) Architecture Rules

### 2.1 The 10ms Rule
The primary constraint: The sum of file reading, AST parsing, and rule evaluation must complete in under 10ms on a single CPU core for a typical 1000-line file. 

### 2.2 Independent Validation
The benchmark scripts must import the `kernel` cleanly without relying on mocked internals, testing the public validation interface directly.

---

## 3) Implementation Order

1. **Skeleton**: Set up `click` CLI and `pytest-benchmark` or custom timing tools.
2. **Parser Benchmarks**: Measure raw Tree-sitter parsing times across large source files.
3. **Rule Evaluator Benchmarks**: Measure the execution time of AST traversal bounds.
4. **End-to-End Suite**: Measure full pipeline latency and generate regression JSON reports.

---

## 4) Definition of Done
* Developers can run `watchllm-benchmarks run`.
* Output clearly displays milliseconds per file size with P50/P99 latencies.
