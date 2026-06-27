⇒ WatchLLM klyd (Phase 4) — 8-Day Prompt Pack

Copy **one full day block** below into your agent session. Each block uses the same template; only task, gate, and scope placeholders are filled from `internal_docs/IMPORTANT.md`.

**Repo:** `watchllm/klyd` (local: `d:\watchllm\klyd`)

---

⇒ Day 01 — Task 01: Skeleton & SQLite Schema

⇒ Task Instructions

Today's task:
**KLYD Task 01 — Skeleton & SQLite Schema**

Create the foundation of the klyd CLI:
- Use `click` to set up the CLI entry points (`kl init`, `kl config`).
- `kl init` should create the `.klyd/` directory.
- Initialize the SQLite database at `.klyd/memory.db` with the `decisions` table (columns: `decision`, `module`, `file_patterns`, `confidence`, `event_type`, `reinforcement_count`, `last_seen_commit`, `created_at`, `flagged`, `archived`).
- Set up `.klyd/config.json`.

Today's gate:
- Running `kl init` creates the `.klyd` folder and a valid SQLite DB.

> Scope Constraints
Only work on: CLI scaffolding, config management, and DB schema (Task 01 only).
Do NOT: write Git hooks yet.

> Required Outputs
You must implement the task narrowly and verify database creation.

---

⇒ Day 02 — Task 02: Git Hook Management

⇒ Task Instructions

Today's task:
**KLYD Task 02 — Git Hook Management**

Add git hook injection to the `init` process:
- `kl init` must also write two executable bash scripts to `.git/hooks/`:
  1. `post-commit`: Calls `kl extract-commit >> .klyd/errors.log 2>&1 || true`.
  2. `pre-commit`: Calls `kl prepare-injection >> .klyd/errors.log 2>&1 || true`.

Today's gate:
- Running `kl init` properly creates and `chmod +x` both hook files.

> Scope Constraints
Only work on: Git hook generation (Task 02 only).

> Required Outputs
You must implement the task narrowly and verify hook files exist and are executable.

---

⇒ Day 03 — Task 03: LLM Provider API

⇒ Task Instructions

Today's task:
**KLYD Task 03 — LLM Provider API**

Set up the LLM abstraction:
- Create a client abstraction that reads the API key and model from `.klyd/config.json`.
- Implement a basic Anthropic client wrapper (since it's the default).
- Create a structured JSON prompt schema that forces the LLM to output a list of decisions with their type (`NEW`, `REINFORCE`, `CONTRADICT`), `confidence`, and `file_patterns`.

Today's gate:
- A unit test can pass a dummy string to the LLM wrapper and get a properly typed JSON object back.

> Scope Constraints
Only work on: LLM wrapper and config reading (Task 03 only).
Do NOT: wire it up to `git diff` yet.

---

⇒ Day 04 — Task 04: Extraction Engine

⇒ Task Instructions

Today's task:
**KLYD Task 04 — Extraction Engine**

Implement `kl extract-commit`:
- Read the git diff of `HEAD~1` to `HEAD`.
- Read the latest commit message.
- Query the database for existing decisions relevant to the touched files.
- Combine diff + commit msg + existing decisions and pass to the LLM Provider API.

Today's gate:
- Running `kl extract-commit` outputs the parsed LLM payload to standard output (or a debug log).

> Scope Constraints
Only work on: Diff extraction and LLM parsing (Task 04 only).
Do NOT: save the results to the database yet.

---

⇒ Day 05 — Task 05: Memory State Machine

⇒ Task Instructions

Today's task:
**KLYD Task 05 — Memory State Machine**

Finish the extraction pipeline by saving to SQLite:
- If LLM says `NEW`, insert a new row.
- If LLM says `REINFORCE`, increment `reinforcement_count` on the matching decision ID and update `last_seen_commit`.
- If LLM says `CONTRADICT`, insert a new row but set `flagged=1`.

Today's gate:
- End-to-end `kl extract-commit` populates `.klyd/memory.db` with correct state transitions.

> Scope Constraints
Only work on: SQLite upserts based on LLM output (Task 05 only).

---

⇒ Day 06 — Task 06: Status & Review UX

⇒ Task Instructions

Today's task:
**KLYD Task 06 — Status & Review UX**

Build the interactive human-in-the-loop flows:
- `kl status`: Print a pretty table of active decisions and distinctly highlight any flagged decisions in a "NEEDS REVIEW" section.
- `kl review`: An interactive prompt (using something like `questionary` or basic input) that iterates through `flagged=1` rows. Allow the user to Accept (archives old), Reject (archives new), or Skip.

Today's gate:
- `kl status` correctly prints table data from SQLite.
- `kl review` successfully archives a flagged decision.

> Scope Constraints
Only work on: CLI views and interactive prompts (Task 06 only).

---

⇒ Day 07 — Task 07: Context Injection Engine

⇒ Task Instructions

Today's task:
**KLYD Task 07 — Context Injection Engine**

Implement `kl prepare-injection`:
- Get currently staged files (`git diff --cached --name-only`).
- Query SQLite for the most relevant unarchived, unflagged decisions matching those file patterns.
- Format them into a dense, readable prompt block.
- Write the result to `.klyd/injection.txt`.

Today's gate:
- Running `kl prepare-injection` successfully produces `.klyd/injection.txt` populated with relevant architectural constraints.

> Scope Constraints
Only work on: Pre-commit context formatting (Task 07 only).

---

⇒ Day 08 — Task 08: Agent Execution Wrapper

⇒ Task Instructions

Today's task:
**KLYD Task 08 — Agent Execution Wrapper**

Build the final runtime bridge:
- Implement `kl run <agent_cmd>`.
- It should read `.klyd/injection.txt`.
- It should automatically append the injection text as a system prompt or message flag to the target agent (e.g., `aider --message "... [KLYD MEMORY: ...]"`).

Today's gate:
- `kl run aider` successfully launches a subprocess that includes the memory injection file.

> Scope Constraints
Only work on: Subprocess management and CLI arg parsing for the wrapper (Task 08 only).
