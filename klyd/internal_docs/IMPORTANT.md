# WatchLLM Architectural Memory (klyd)

## 0) Purpose

This document defines the **klyd layer (Phase 4 / Expansion C)** for WatchLLM. The goal of this layer is to solve the "slop fortress" problem: autonomous coding agents progressively destroying a codebase because they forget earlier architectural decisions and patch blindly to fix failing tests. 

`klyd` acts as a **persistent architectural memory harness**. It watches your commits, extracts architectural intent using LLMs, saves it locally, and automatically injects it back into your agent's context the next time you write code.

---

## 1) Scope

### In scope
* A Python CLI (`kl`) using `click`.
* A local SQLite database (`.klyd/memory.db`) to store architectural decisions.
* Git hook integrations (`post-commit` and `pre-commit`) to trigger extraction and injection.
* LLM integrations (Anthropic, OpenAI, etc.) via BYOK (Bring Your Own Key) for semantic extraction.
* Interactive CLI flows (`kl review`, `kl status`) to manage memory conflicts.

### Out of scope
* Writing actual production application code (klyd only reads diffs and writes context docs).
* Blocking file saves inline (this is the Kernel's job).
* Cloud storage for memory (everything MUST be strictly local in `.klyd/`).

---

## 2) Architecture Rules

### 2.1 The Local-First Rule
All state, configuration, and logs must live strictly inside the `.klyd/` directory in the root of the user's repository. No centralized cloud backend is allowed.

### 2.2 The Two-Call Limit
To save money and latency, klyd should make at most two LLM calls per commit cycle (one for extraction, one for summarization if needed).

### 2.3 The Three-State Memory Engine
When evaluating a commit against the existing memory, klyd must strictly classify the new decision into one of three states:
* **NEW**: A novel architectural decision. (Saved normally).
* **REINFORCE**: Matches an existing decision. (Increments `reinforcement_count`).
* **CONTRADICT**: Directly conflicts with a known decision. (Saved but `flagged=1` for human review).

---

## 3) Implementation Order

1. **Skeleton & SQLite DB**: Set up `click` CLI, `.klyd` init logic, and SQLite schema.
2. **Git Hook Management**: Automate the creation of `pre-commit` and `post-commit` hooks.
3. **LLM Provider API**: Abstraction over Anthropic/OpenAI for passing diffs.
4. **Extraction Engine**: Reading `git diff HEAD~1 HEAD`, hitting the LLM, and getting the NEW/REINFORCE/CONTRADICT JSON payload.
5. **Memory State Machine**: Processing the extraction payload, handling SQLite upserts, and flagging contradictions.
6. **UX & Review Flow**: `kl status` and the interactive `kl review` prompt for flagged items.
7. **Injection Engine**: Reading staged files, mapping to decisions, and generating `.klyd/injection.txt`.
8. **Agent Wrapper**: `kl run` command to seamlessly pass the injection context into `aider` or `opencode`.

---

## 4) Definition of Done
* A user can run `kl init` and make a commit.
* The `post-commit` hook successfully extracts a decision into SQLite.
* A contradictory commit gets flagged.
* The `pre-commit` hook successfully generates an accurate `injection.txt`.
