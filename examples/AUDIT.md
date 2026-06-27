# WatchLLM Examples Audit Specification (Example Scenarios)

This document defines the expected perfect state of the **WatchLLM Examples** repository. It outlines the architecture, rules, interface contracts, and edge cases necessary to pass a complete verification run.

---

## 1. Purpose & Scope
The Examples repository holds the benchmark and integration scenarios used to verify the enforcement fidelity of the WatchLLM Kernel and Runtime. It provides reference target codebases that represent either fully compliant operations (PASS) or security/architectural policy violations (FAIL). It does not contain execution logic of the platform.

---

## 2. Expected Directory & File Layout
A perfect implementation must contain:
```
d:\watchllm\examples/
├── scenarios/
│   ├── README.md                 # Scenario directory guide
│   ├── secrets/
│   │   ├── safe.py               # Credentials loaded via env (PASS)
│   │   └── unsafe.py             # Credentials hardcoded in variables (FAIL)
│   ├── boundaries/
│   │   ├── safe/
│   │   │   ├── client.py         # Imports within boundaries (PASS)
│   │   │   └── gateway.py
│   │   └── unsafe/
│   │       ├── database.py       # Unauthorized direct cross-module import (FAIL)
│   │       └── auth_client.py
│   └── auth_flow/
│       ├── safe.py               # Mutates database after auth verification (PASS)
│       └── unsafe.py             # Mutates database prior to auth check (FAIL)
├── README.md                     # Main documentation page
└── tasks.md                      # Active gate checklist
```

---

## 3. Core Scenario Assertions & Behaviors

### A. Secrets Scenario
- **Safe File (`safe.py`)**: Imports `os` and loads API keys using `os.getenv("STRIPE_KEY")` or `os.environ.get("OPENAI_KEY")`.
- **Unsafe File (`unsafe.py`)**: Declares literal variables matching secret formats directly in source lines (e.g., `stripe_key = "sk_live_abc123..."`).
- **Assertion**: Running `watchllm-kernel check` on `safe.py` must return exit code `0` (PASS). On `unsafe.py`, it must return exit code `1` (BLOCK).

### B. Boundaries Scenario
- **Safe File (`safe/client.py`)**: Imports are structured according to architectural limits (e.g. client maps only to gateways).
- **Unsafe File (`unsafe/database.py`)**: Violates boundaries (e.g. a low-level module imports high-level controllers, or cross-boundary circular imports).
- **Assertion**: Running checks on `safe/` must return `0`. On `unsafe/`, it must block with boundary infraction details.

### C. Auth Flow Scenario
- **Safe File (`safe.py`)**: Defines route execution paths where an authenticator method (e.g., `auth.verify()`) executes before a DB query method.
- **Unsafe File (`unsafe.py`)**: Defines route handlers where execution flow triggers a database operation prior to any guard validation.
- **Assertion**: Checking `safe.py` must yield `PASS`, while checking `unsafe.py` must yield `FAIL` and block.

---

## 4. Critical Edge Cases & Verification Scenarios

| Edge Case | Expected Perfect Behavior |
|---|---|
| **String Mock False Positives** | Testing files sometimes contain mock key prefixes (e.g. `stripe_key = "sk_live_mock_only"`). The engine must ignore these when running in test contexts or when matching mock strings. |
| **Partial Auth Guard** | In `auth_flow`, an asynchronous route might execute authentication in a `.then()` callback. The example must test if the AST parser handles nested callbacks accurately. |
| **Path Normalization** | Boundary scenarios must verify that files are resolved using workspace-relative paths to ensure that checks execute identically across OS filesystems. |

---

## 5. Verification Checklist
To verify the Examples suite compliance, run:
1. **Secrets Interception Check**:
   ```bash
   python -m watchllm_kernel check --filepath scenarios/secrets/unsafe.py
   ```
   Verify it returns exit code `1` and details the line of the leaked credential.
2. **Safe Code Check**:
   ```bash
   python -m watchllm_kernel check --filepath scenarios/secrets/safe.py
   ```
   Verify it returns exit code `0`.
3. **Boundaries Verification**: Check relative imports in `scenarios/boundaries/unsafe/` and confirm boundary violations are detected.
4. **Auth Flow Verification**: Check execution flow order inside `scenarios/auth_flow/unsafe.py` and confirm blocking.
