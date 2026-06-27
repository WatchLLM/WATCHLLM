# WatchLLM Architectural Memory Audit Specification (Phase 4 — Klyd Integration)

This document defines the expected perfect state of the **WatchLLM Architectural Memory (klyd)** (Phase 4). It outlines the architecture, rules, interface contracts, and edge cases necessary to pass a complete verification run.

---

## 1. Purpose & Scope
`klyd` is a local-first persistent architectural memory harness. Its goal is to prevent AI coding agents from degrading a codebase ("slop fortress" syndrome) by capturing architectural decisions from git commit diffs, saving them in a local database, and injecting relevant constraints back into the agent's prompt context during code modification.

---

## 2. Expected Directory & File Layout
A perfect implementation must contain:
```
d:\watchllm\klyd\
├── src/
│   └── klyd/
│       ├── __init__.py           # Package exports
│       ├── __main__.py           # CLI entrypoint
│       ├── cli.py                # Click CLI command definitions
│       ├── config.py             # Config file manager (.klyd/config.json)
│       ├── db.py                 # SQLite database initializer and helpers
│       ├── extraction.rs/py      # Diff reading & LLM query logic
│       ├── llm.py                # Anthropic / OpenAI API client wrappers
│       ├── memory.py             # SQLite decision state machine (NEW/REINFORCE/CONTRADICT)
│       └── injection.py          # Context formatter and pre-commit handler
├── tests/
│   ├── test_cli.py               # Click command tests
│   ├── test_db.py                # Database schema & constraint tests
│   ├── test_extraction.py        # Diff parsing tests
│   ├── test_llm.py               # Provider mocks and key handling tests
│   └── test_memory.py            # Decision lifecycle state machine tests
├── pyproject.toml                # Project configurations (Hatchling/Poetry)
└── tasks.md                      # Active gate checklist
```

---

## 3. Core Component Responsibilities & State Machine

### A. Local SQLite DB Schema (`.klyd/memory.db`)
The database must contain a `decisions` table with the following constraints:
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `decision`: TEXT NOT NULL (The architectural rule description)
- `module`: TEXT (Target system area or path)
- `file_patterns`: TEXT NOT NULL (Comma-separated list of affected file globs)
- `confidence`: REAL (LLM extraction confidence)
- `event_type`: TEXT NOT NULL (CHECK constraint enforcing `NEW`, `REINFORCE`, `CONTRADICT`)
- `reinforcement_count`: INTEGER DEFAULT 1
- `last_seen_commit`: TEXT (Git commit SHA)
- `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `flagged`: INTEGER DEFAULT 0 (Boolean 0 or 1, set to 1 if CONTRADICT)
- `archived`: INTEGER DEFAULT 0 (Boolean 0 or 1)

### B. Memory State Machine (`memory.py`)
Decisions extracted from git diffs are categorized:
- **NEW**: Brand new decision. Inserts row into SQLite.
- **REINFORCE**: Matches an existing decision. Increments `reinforcement_count` and updates `last_seen_commit`.
- **CONTRADICT**: Directly conflicts with a prior decision. Inserts new row with `flagged=1`.

### C. Git Hook Integrations
`kl init` must drop executable hooks inside `.git/hooks/`:
1. `post-commit`: Invokes `kl extract-commit >> .klyd/errors.log 2>&1 || true`.
2. `pre-commit`: Invokes `kl prepare-injection >> .klyd/errors.log 2>&1 || true`.

---

## 4. CLI Commands Contract

- `kl init`: Creates `.klyd/` folder, initializes `.klyd/memory.db` SQLite schema, writes `.klyd/config.json`, and installs `pre-commit`/`post-commit` hooks.
- `kl status`: Lists all active decisions, highlighting `flagged` contradictions in a "NEEDS REVIEW" section.
- `kl review`: Interactive wizard to resolve flagged contradictions. Allows user to Accept (archives old), Reject (archives new), or Skip.
- `kl config`: Gets or sets configurations in `.klyd/config.json` (such as API keys and provider models).
- `kl extract-commit`: Invoked by `post-commit`. Reads `git diff HEAD~1 HEAD`, queries LLM to classify changes, and updates database.
- `kl prepare-injection`: Invoked by `pre-commit`. Reads staged changes, queries relevant decisions, and writes context string to `.klyd/injection.txt`.
- `kl run <agent_cmd>`: Wraps AI agent execution. Reads `.klyd/injection.txt` and appends it to the agent's argument flags (e.g. `aider --message "... [KLYD MEMORY: ...]"`).

---

## 5. Critical Edge Cases & Error Recovery

| Edge Case | Expected Perfect Behavior |
|---|---|
| **LLM Call Failure** | If the Anthropic/OpenAI API is down or keys are missing during commit, `post-commit` and `pre-commit` hooks must **never** block the commit. The command must fail-open gracefully (`|| true`), logging errors to `.klyd/errors.log`. |
| **No Git Repo** | Running `kl init` in a directory without a `.git` folder must fail immediately with a descriptive error message instead of corrupting paths. |
| **Database Lock** | Multiple commits in rapid succession must be handled by SQLite's busy-timeout (default: 5000ms) to prevent transaction aborts. |
| **Overlapping File Patterns** | The query in `prepare-injection` must match globs (e.g., `src/**/*.py`) against touched paths. In case of multiple matches, the engine should rank them by specificity. |

---

## 6. Verification Checklist
To confirm `klyd` compliance, run:
1. **Database Setup**: Execute `kl init` in a test repo and verify `.klyd/memory.db` database tables exist.
2. **Git Commit Hook Verification**: Commit a file. Verify `post-commit` runs and writes a `NEW` decision row to SQLite.
3. **Contradiction Check**: Commit code that violates the previous commit's architectural rule. Run `kl status` and verify it is displayed under "NEEDS REVIEW".
4. **Context Injection Check**: Stage a file matching the decision's patterns. Run `kl prepare-injection` and confirm `.klyd/injection.txt` contains the extracted rule.
5. **Unit Tests**: Run Python unit tests:
   ```bash
   pytest tests/
   ```