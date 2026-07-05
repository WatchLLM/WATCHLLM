# WatchLLM Reliability Harness Tasks

## Task 01 — Skeleton & Runner
Status: Complete

Gate:
- Running `reliability-stress --help` works and lists the `run` and `list` commands.

Scope:
- `click` CLI setup.
- Basic suite registry.

---

## Task 02 — Suite Loader
Status: Complete

Gate:
- `reliability-stress list` successfully parses a dummy `suites/test.yml` and prints the test names.

Scope:
- YAML parsing.
- Test case dataclass/schema.

---

## Task 03 — Agent Orchestrator Interface
Status: Complete

Gate:
- A unit test successfully runs a dummy python script via `AgentRunner` and captures its output and file writes.

Scope:
- Subprocess execution wrapper.
- Temporary directory isolation.
- Timeout handling.

---

## Task 04 — Prompt Injection Suite
Status: Complete

Gate:
- The `PromptInjectionSuite` can execute a simulated test case via `AgentRunner` and mark it PASS/FAIL.

Scope:
- Jailbreak/secret-leak test scenarios.
- Output string matching.

---

## Task 05 — Kernel Enforcement Suite
Status: Complete

Gate:
- The suite can run and verify filesystem diffs (or lack thereof) post-execution.

Scope:
- Architectural violation scenarios.
- File state diffing.

---

## Task 06 — Tool Abuse Suite
Status: Complete

Gate:
- The suite correctly handles and parses timeout exceptions from the `AgentRunner`.

Scope:
- Infinite loop testing.
- Timeout parsing.

---

## Task 07 — Scoring Engine
Status: Complete

Gate:
- `reliability-stress run` outputs a clean, calculated score table at the end of the run.

Scope:
- Quantitative Safety Index calculation.
- Table formatting.

---

## Task 08 — CI/CD Reporter
Status: Complete

Gate:
- Running the CLI with `--format junit` produces a parsable `.xml` file containing test failures and passes.

Scope:
- JUnit XML export.
- Threshold exit codes.
