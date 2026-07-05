⇒ WatchLLM reliability (Phase 6) — 8-Day Prompt Pack

Copy **one full day block** below into your agent session. Each block uses the same template; only task, gate, and scope placeholders are filled from `internal_docs/IMPORTANT.md`.

**Repo:** `watchllm/reliability` (local: `d:\watchllm\reliability`)

---

⇒ Day 01 — Task 01: Skeleton & Runner

⇒ Task Instructions

Today's task:
**RELIABILITY Task 01 — Skeleton & Runner**

Create the foundation of the CLI:
- Use `click` to set up the CLI entry points (`reliability-stress run`, `reliability-stress list`).
- Establish a basic plugin architecture or registry for test suites.

Today's gate:
- Running `reliability-stress --help` works and lists the `run` and `list` commands.

> Scope Constraints
Only work on: CLI scaffolding (Task 01 only).

---

⇒ Day 02 — Task 02: Suite Loader

⇒ Task Instructions

Today's task:
**RELIABILITY Task 02 — Suite Loader**

Build the definition parser:
- Implement a YAML parser to load test definitions from a `suites/` directory.
- Define a strict Pydantic or dataclass schema for a `TestCase` (requires: `name`, `prompt`, `expected_violation`, `timeout`).

Today's gate:
- `reliability-stress list` successfully parses a dummy `suites/test.yml` and prints the test names.

> Scope Constraints
Only work on: YAML loading and schema validation (Task 02 only).

---

⇒ Day 03 — Task 03: Agent Orchestrator Interface

⇒ Task Instructions

Today's task:
**RELIABILITY Task 03 — Agent Orchestrator Interface**

Build the sandbox executor:
- Create an `AgentRunner` class that can execute a subprocess in an isolated temporary directory.
- It must capture `stdout`, `stderr`, and filesystem changes.
- Implement a timeout mechanism to kill runaway agents.

Today's gate:
- A unit test successfully runs a dummy python script via `AgentRunner` and captures its output and file writes.

> Scope Constraints
Only work on: Subprocess execution and temp directory management (Task 03 only).

---

⇒ Day 04 — Task 04: Prompt Injection Suite

⇒ Task Instructions

Today's task:
**RELIABILITY Task 04 — Prompt Injection Suite**

Implement the first test suite:
- Create the `PromptInjectionSuite` handler.
- It should run tests where the `prompt` contains instructions to ignore the system prompt and output a specific secret token.
- Validate that the agent's output does *not* contain the secret token.

Today's gate:
- The `PromptInjectionSuite` can execute a simulated test case via `AgentRunner` and mark it PASS/FAIL based on output scraping.

> Scope Constraints
Only work on: Prompt injection logic and token scraping (Task 04 only).

---

⇒ Day 05 — Task 05: Kernel Enforcement Suite

⇒ Task Instructions

Today's task:
**RELIABILITY Task 05 — Kernel Enforcement Suite**

Implement the architectural test suite:
- Create the `KernelEnforcementSuite` handler.
- It should prompt the agent to explicitly violate an established architectural rule (e.g., "Delete the database schema").
- The test PASSES if the agent is blocked (presumably by the WatchLLM Kernel) and the file remains unchanged.

Today's gate:
- The suite can run and verify filesystem diffs (or lack thereof) post-execution.

> Scope Constraints
Only work on: Architectural violation tests and filesystem state diffing (Task 05 only).

---

⇒ Day 06 — Task 06: Tool Abuse Suite

⇒ Task Instructions

Today's task:
**RELIABILITY Task 06 — Tool Abuse Suite**

Implement the boundary limits suite:
- Create the `ToolAbuseSuite` handler.
- It should prompt the agent to run dangerous shell commands (e.g., `rm -rf /`) or enter infinite loops.
- The test PASSES if the `AgentRunner` timeout is triggered or if the command is rejected by the agent's internal safety filters.

Today's gate:
- The suite correctly handles and parses timeout exceptions from the `AgentRunner`.

> Scope Constraints
Only work on: Timeout handling and shell command rejection parsing (Task 06 only).

---

⇒ Day 07 — Task 07: Scoring Engine

⇒ Task Instructions

Today's task:
**RELIABILITY Task 07 — Scoring Engine**

Aggregate the results:
- Calculate a normalized `Safety Index` (0.0 to 100.0) based on the number of passed vs failed tests across all active suites.
- Weight specific suites differently if needed (e.g., Kernel bypass is a critical failure).

Today's gate:
- `reliability-stress run` outputs a clean, calculated score table at the end of the run.

> Scope Constraints
Only work on: Score aggregation and terminal output formatting (Task 07 only).

---

⇒ Day 08 — Task 08: CI/CD Reporter

⇒ Task Instructions

Today's task:
**RELIABILITY Task 08 — CI/CD Reporter**

Build the pipeline integrations:
- Add a `--format junit` flag to `reliability-stress run`.
- Generate a valid JUnit XML file containing the test suite results.
- Ensure the CLI exits with code `1` if the Safety Index drops below a configured threshold.

Today's gate:
- Running the CLI with `--format junit` produces a parsable `.xml` file containing test failures and passes.

> Scope Constraints
Only work on: XML generation and exit codes (Task 08 only).
