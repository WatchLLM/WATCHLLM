# WATCHLLM — PRODUCT DEFINITION

WatchLLM is a write-path governance layer for AI-generated code.

It enforces architectural and security constraints BEFORE code is written or committed.

---

## Core Principle

Code that violates constraints must not be written.

---

## What WatchLLM does

- Intercepts code at save-time and CLI
- Evaluates against deterministic rules
- Blocks violations
- Explains violations
- Suggests compliant rewrites

---

## What WatchLLM does NOT do

- Does not generate code
- Does not approve exceptions
- Does not execute code
- Does not host repositories

---

## Target User

- Engineering leads
- Platform engineers
- Security engineers

---

## Value Proposition

Approved architecture becomes the default output.

Invalid code never reaches the repository.