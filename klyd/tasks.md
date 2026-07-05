# WatchLLM Architectural Memory (klyd) Tasks

## Task 01 — Skeleton & SQLite Schema
Status: Complete

Gate:
- Running `kl init` creates the `.klyd` folder and a valid SQLite DB.

Scope:
- `click` CLI setup.
- `.klyd/memory.db` initialization with `decisions` table.
- `.klyd/config.json` initialization.

---

## Task 02 — Git Hook Management
Status: Complete

Gate:
- Running `kl init` properly creates and `chmod +x` both hook files.

Scope:
- Write `post-commit` hook.
- Write `pre-commit` hook.

---

## Task 03 — LLM Provider API
Status: Complete

Gate:
- A unit test can pass a dummy string to the LLM wrapper and get a properly typed JSON object back.

Scope:
- Config reader for API keys.
- Anthropic API integration.
- Structured JSON schema definition for NEW/REINFORCE/CONTRADICT.

---

## Task 04 — Extraction Engine
Status: Complete

Gate:
- Running `kl extract-commit` outputs the parsed LLM payload to standard output.

Scope:
- Get diff and commit message via `git`.
- Query existing DB for context.
- Pass payload to LLM.

---

## Task 05 — Memory State Machine
Status: Complete

Gate:
- End-to-end `kl extract-commit` populates `.klyd/memory.db` with correct state transitions.

Scope:
- Map LLM response to SQLite INSERTs/UPDATEs.
- Handle `reinforcement_count` incrementing.
- Handle `flagged=1` for contradictions.

---

## Task 06 — Status & Review UX
Status: Complete

Gate:
- `kl status` correctly prints table data from SQLite.
- `kl review` successfully archives a flagged decision interactively.

Scope:
- Pretty print `kl status`.
- Interactive resolution loop in `kl review`.

---

## Task 07 — Context Injection Engine
Status: Complete

Gate:
- Running `kl prepare-injection` successfully produces `.klyd/injection.txt` populated with relevant architectural constraints.

Scope:
- Read staged files via `git diff --cached`.
- Query DB for relevant patterns.
- Format and write to `.klyd/injection.txt`.

---

## Task 08 — Agent Execution Wrapper
Status: Complete

Gate:
- `kl run aider` successfully launches a subprocess that includes the memory injection file.

Scope:
- Implement `kl run <cmd>` wrapper.
- Append memory file contents into the agent's CLI arguments or environment.
