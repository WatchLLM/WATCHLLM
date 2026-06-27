# WatchLLM Kernel Audit Specification (Phase 1 — Kernel MVP)

This document defines the expected perfect state of the **WatchLLM Kernel** (Phase 1). It outlines the architecture, rules, interface contracts, and edge cases necessary to pass a complete verification run.

---

## 1. Purpose & Scope
The Kernel is the local, offline-first write-path governance engine. It blocks structurally unsafe file saves (in TS/JS) deterministically using AST analysis before they reach disk. It does not handle cloud state, agent coordination, or visual execution tracking.

---

## 2. Expected Directory & File Layout
A perfect implementation must contain:
```
d:\watchllm\kernel\
├── src/
│   └── watchllm_kernel/
│       ├── __init__.py           # Package exports
│       ├── __main__.py           # Submodule runner
│       ├── cli.py                # Click CLI logic
│       ├── engine.py             # Rule aggregator & orchestrator
│       ├── models.py             # Typed dataclasses (Violations, Decisions)
│       ├── parser.py             # Tree-sitter AST parser wrappers
│       ├── reporting.py          # Terminal & JSON formatter
│       └── rules/                # AST check submodules
│           ├── __init__.py
│           ├── _ast_utils.py     # AST helper utilities
│           ├── auth_flow.py      # Auth-before-mutation flow-sensitive check
│           ├── boundary.py       # Cross-module service bounds check
│           ├── forbidden_imports.py # Import denylist checker
│           └── secrets.py        # Safe-function aware credentials checker
├── tests/
│   ├── fixtures/                 # Golden JS/TS code samples (pass/fail)
│   ├── test_auth_flow_rule.py
│   ├── test_boundary_rule.py
│   ├── test_forbidden_import_rule.py
│   ├── test_secrets_rule.py
│   ├── test_cli_contract.py
│   └── test_e2e.py              # Full save-blocking checks
├── pyproject.toml                # Build system (e.g. Hatchling/Poetry)
└── tasks.md                      # Active gate checklist
```

---

## 3. Core Rule Implementation Expectations

### A. Secret Literal Rule (`watchllm-rule-secrets`)
- **Objective**: Block hardcoded secret literals (e.g., Stripe, AWS, OpenAI, GitHub keys) assigned directly to variables or config values.
- **AST Verification**:
  - Must identify variable assignment contexts (`const api_key = "..."`) or property assignments (`apiKey: "..."`).
  - **Safe-Function Filtering (Crucial)**: If the matched string is passed as an argument to environment getters or vaults (e.g., `process.env.get("STRIPE_KEY")`, `os.getenv("API_KEY")`), it must be **ignored** (PASS).
  - Comment blocks, mock objects in test directories, and import paths containing matches must be ignored.

### B. Forbidden Import Rule (`watchllm-rule-imports`)
- **Objective**: Prevent usage of unsafe built-in modules or traversal patterns.
- **AST Verification**:
  - Check `import` statements and `require()` calls.
  - Denylist standard libraries like `child_process`, `eval`, or direct raw filesystem libraries (`fs` when prohibited by local policy).
  - Normalize relative path imports to catch directory-traversal bypasses (e.g., importing from `../../db` from a restricted sandbox).

### C. Boundary Rule (`watchllm-rule-boundaries`)
- **Objective**: Prevent circular dependencies or illegal cross-boundary relationships (e.g., `auth` importing `database` directly when a repository layer is required).
- **AST Verification**:
  - Parse imports to construct an internal dependency graph.
  - Map target file path and import targets against the project boundary map.
  - Violations must trigger block decisions if module boundary configurations are breached.

### D. Auth-Flow Rule (`watchllm-rule-auth`)
- **Objective**: Require authenticating guards prior to performing protected operations inside route/API handlers.
- **AST Verification**:
  - Flow-sensitive traversal: Analyze the sequence of calls inside Express/Next API handler scopes.
  - If a database query, file write, or external egress node is reached before an authentication middleware or guard function call (e.g., `auth.verify()`, `req.user.authenticate()`) in the same execution branch, a block decision must be generated.

---

## 4. CLI & Interface Contracts

### Command Structure
```bash
python -m watchllm_kernel check [OPTIONS]
```
Options:
- `--stdin`: Read code text directly from standard input.
- `--filepath <path>`: Path to evaluate (determines boundaries/rules).
- `--language <js|ts>`: Explicitly state the target language.
- `--mode <shadow|enforce>`: Determines blocking behavior.

### Exit Code Contract
- `0`: Success (Allow Save / No violations).
- `1`: Violation Block (Violations exist, and mode is `enforce`).
- `2`: System Error / Inconclusive Parse (Internal failure, invalid arguments, crash).

### JSON Output Contract (`decision.json`)
The CLI outputs structured JSON to standard output. Example:
```json
{
  "decision": "BLOCK",
  "mode": "enforce",
  "rule_results": [
    {
      "rule_id": "watchllm-rule-secrets",
      "status": "FAIL",
      "violations": [
        {
          "message": "Hardcoded secret key detected.",
          "line": 42,
          "column": 15,
          "code_context": "const stripeKey = 'sk_live_...'"
        }
      ]
    }
  ]
}
```

---

## 5. Critical Edge Cases & Error Recovery

| Edge Case | Expected Perfect Behavior |
|---|---|
| **Malformed Syntax** | The Tree-sitter parser must use incremental recovery to parse surrounding valid AST chunks. Rules must execute on the valid sections without causing a process crash (Exit Code 2). |
| **Ambiguous Auth Order** | If auth execution order cannot be determined (e.g., async handler branching), the engine should flag as `INCONCLUSIVE` (with diagnostic warning) or fall back to a safe fail-closed state in strict environments. |
| **Large File Size** | Evaluation of a 1000-line file must complete in under 10 milliseconds to prevent noticeable delay on editor saves. |
| **No Network Access** | The entire evaluation process must execute offline. Telemetry calls must run asynchronously or fail silently, never blocking the save decision. |

---

## 6. Verification Checklist
To confirm Kernel compliance, run:
1. **Fixture Tests**: Confirm that the fixture suite passes:
   ```bash
   pytest tests/test_fixture_corpus.py
   ```
2. **Deterministic Rules Checks**: Run unit tests for individual rules:
   ```bash
   pytest tests/test_secrets_rule.py tests/test_forbidden_import_rule.py
   ```
3. **E2E Blocking Flow**: Execute integration tests to verify save interception and shadow mode:
   ```bash
   pytest tests/test_e2e.py
   ```
4. **Contract Conformity**: Confirm JSON validation against schemas:
   ```bash
   pytest tests/test_cli_contract.py
   ```
