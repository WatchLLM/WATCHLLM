# WATCHLLM — EXECUTION RULES

This document defines how the agent (Aider) must behave.

---

## Core Rule

Implement only the requested task. Nothing else.

---

## Strict Prohibitions

- Do not refactor existing code
- Do not modify unrelated files
- Do not introduce new abstractions
- Do not rename variables or files unless required
- Do not optimize beyond requirements

---

## Required Behavior

- Follow scope exactly
- Write minimal code
- Prefer explicit logic over abstraction
- Ask for clarification if unsure

---

## Task Execution

Each task must:
- modify only specified files
- satisfy acceptance criteria exactly
- avoid side effects

---

## Failure Handling

If unclear:
- stop
- ask for clarification

Do not guess.

---

## Output Constraints

- minimal code
- no unused functions
- no speculative logic