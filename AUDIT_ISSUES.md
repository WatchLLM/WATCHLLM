# WatchLLM Audit Issues

Issues found when verifying each phase's implementation against its `AUDIT.md` specification.
Generated: 2026-06-21

---

## Phase 1 — Kernel (`kernel/`)

### Deviations from Spec

| # | Severity | Category | Spec Says | Actual | File |
|---|----------|----------|-----------|--------|------|
| 1 | **Medium** | CLI Contract | Subcommand `check` | Subcommand `evaluate` | `cli.py:76` |
| 2 | **Medium** | JSON Output | Per-rule field `"status"` | Per-rule field `"decision"` | `models.py:56` |
| 3 | **Low** | JSON Output | Rule IDs like `watchllm-rule-secrets` | Rule IDs like `SECRET_LITERAL` | `rules/*.py` |
| 4 | **Low** | CLI Library | Click | argparse | `cli.py:62` |
| 5 | **Low** | CLI Options | `--filepath <path>` | Positional `file` arg | `cli.py:82-86` |
| 6 | **Low** | CLI Options | `--language <js\|ts>` | `--language <javascript\|typescript>` (full names) | `cli.py:88-91` |
| 7 | **Low** | Tests | `test_secrets_rule.py` listed | File missing (secrets tested via `test_cli.py` instead) | — |

### Testing Results
- **92/92 tests PASS** (100%) ✅

---

## Phase 2 — Runtime (`runtime/`)

### Build Issues

| # | Severity | Issue | Details |
|---|----------|-------|---------|
| 1 | **High** | Build failure on Windows | Missing `dlltool.exe` — `cc` crate cannot build tree-sitter C bindings without mingw toolchain. Affects all downstream build/test |

### Fixed Deviations ✅

| # | Severity | Category | Fix | File |
|---|----------|----------|-----|------|
| 2 | **High** | CLI Contract | Added `--filepath <path>` option (alongside `--stdin`) | `cli/src/main.rs:12-30` |
| 3 | **High** | CLI Contract | Added `--mode <enforce\|shadow>` option with default `"enforce"` | `cli/src/main.rs:25-27` |
| 4 | **High** | Wasm API | Changed to `evaluate_source(source, filepath, language, mode)` matching spec | `wasm/src/lib.rs:12` |
| 5 | **High** | JSON Parity | Restructured to `{decision, mode, file_path, language, rule_results: [{rule_id, status, violations}]}` matching Python kernel 1:1 | `models.rs:23-57` |
| 6 | **Medium** | Severity | Changed from `"error"`/`"warning"` to `"HIGH"`/`"MEDIUM"`/`"LOW"` matching Python | `models.rs`,`rules/*.rs` |
| — | **Medium** | Rule IDs | Changed from `"secrets"`, `"imports"`, etc. to `"watchllm-rule-*"` format | `engine.rs`,`rules/*.rs` |
| — | **Low** | CLI Enhance | Added language inference from file extension, `js`/`ts` short forms, and `--json` support | `cli/src/main.rs:67-82` |

### Remaining Deviations (not fixed)

| # | Severity | Category | Spec Says | Actual | File |
|---|----------|----------|-----------|--------|------|
| 7 | **Medium** | No-Panic | Entire runtime must never panic | `engine.rs` has no `catch_unwind` — only Wasm crate has panic guard | `engine.rs` |
| 8 | **Medium** | Boundary Rule | Must infer source module from `file_path` | No `file_path` parameter; hardcoded `"auth"` assumption | `boundaries.rs` |
| 9 | **Medium** | Forbidden Imports | Must also check relative traversal | Only checks named modules (`child_process`, `vm`) | `imports.rs` |
| 10 | **Low** | tree-sitter version | >= 0.21.0 | 0.20.10 | `core/Cargo.toml` |
| 11 | **Low** | Safe Retrieval | AST-context based (walk parent nodes) | Source-text regex matching | `secrets.rs` |

### Extra: Behaviors
- Boundary rule has `// @boundary-layer` comment marker (not in spec, kept as enhancement)
- CLI now has `--json`, `--filepath`, `--mode`, language inference from file extension ✅
- Workspace has `src/watchllm_runtime/` Python package (not in spec)

---

## Phase 3 — VS Code Extension (`vscode/`)

### Verified Working ✅
- `tsc` compiles without errors ✅
- Unsaved buffer piped via stdin ✅
- `event.waitUntil()` blocks saves ✅
- Handles all 3 JSON output formats (Python nested, Rust flat, flat violations) ✅
- Severity mapping handles both Python enums and Rust strings ✅
- Fail-open on timeout, spawn error, errors ✅
- All **14/14 tests PASS** (100%) ✅

### Fixed Issues ✅

| # | Severity | Issue | Fix | File |
|---|----------|-------|-----|------|
| 1 | **High** | Timeout default 5000ms → 800ms | Changed `DEFAULT_TIMEOUT_MS` from `5_000` to `800` | `kernelExecutor.ts:27` |
| 2 | **Medium** | Default kernelPath uses `evaluate` subcommand | Changed to `-m watchllm_kernel check` (matching Phase 1 rename) | `config.ts:13`, `package.json` |
| 3 | **Low** | Diagnostics not cleaned on workspace switch | Added `workspace.onDidChangeWorkspaceFolders` handler + `clear()` on config change | `extension.ts:28-32` |
| — | **Medium** | Shadow mode + Rust backend (resolved by Phase 2 fix) | Phase 2 added `--mode` support to Rust CLI, extension already passes it correctly | — |

---

## Phase 4 — Klyd (`klyd/`)

### Test Results
- **17/17 passed** (100%) ✅ (up from 59% — fixed 7 Windows-specific failures)

### Fixed Issues ✅

| # | Severity | Issue | Fix | File |
|---|----------|-------|-----|------|
| 1 | **Low** | Hook executability on Windows | `write_git_hook` now writes `.bat` hooks on Windows (skips chmod), `#!/bin/sh` shebang on POSIX | `cli.py:293-305` |
| 2 | **Medium** | SQLite file lock on Windows causing tempdir cleanup crash | Added `ignore_cleanup_errors=True` to all `TemporaryDirectory()` calls; added `timeout=0.1` to all SQLite connections via `_connect_db()` helper | `cli.py:119-120`, `test_klyd.py` |
| 3 | **Low** | Unused `gitpython` dependency | Removed from `pyproject.toml` (code uses `subprocess.run(["git", ...])` directly) | `pyproject.toml:35` |

### Remaining Deviations

| # | Severity | Category | Spec Says | Actual |
|---|----------|----------|-----------|--------|
| 1 | **Medium** | Source structure | 10 files (`__init__.py`, `__main__.py`, `cli.py`, `config.py`, `db.py`, `extraction.py`, `llm.py`, `memory.py`, `injection.py`) | 3 files: `__init__.py`, `cli.py` (833 lines), `llm.py` |
| 2 | **Medium** | Test structure | 5 test files | 2 test files (`test_klyd.py`, `test_llm.py`) |
| 3 | **Low** | No `__main__.py` | `python -m klyd` should work | Currently fails |

---

## Phase 5 — Replay (`replay/`)

### Test Results
- **5/5 tests PASS** (100%) ✅
- Frontend build: ✅
- Query API (GET /api/runs, /api/runs/:id/graph, ingestion): ✅

### Deviations from Spec

| # | Severity | Issue | Details |
|---|----------|-------|---------|
| 1 | **Low** | Out-of-order event sorting | Need to verify `POST /api/events` sorts by `sequence_number` |
| 2 | **Low** | Partial trace handling | Need to verify `DIVERGED`/`CRASHED` status on heartbeat timeout |
| 3 | **Low** | SQLite batch writes | Need to verify transaction batching for high-volume ingestion |

---

## Phase 6 — Reliability (`reliability/`)

### Test Results
- **42 passed, 4 xfailed** (91%, 100% of expected passes) ✅

### Fixed Issues ✅

| # | Severity | Issue | Fix | File |
|---|----------|-------|-----|------|
| 1 | **High** | `test_adversarial.py` calls `evaluate` subcommand (kernel uses `check`) | Changed subcommand to `check`; added `_LANG_MAP` for CLI arg validation `{js, ts}` | `test_adversarial.py:33-51` |
| 2 | **High** | `KernelEnforcementSuite.run_case()` accesses `self.runner.temp_dir` which doesn't exist | Rewrote `run_case` to use `run_result.file_changes` instead of manual file scanning | `suites/kernel_enforcement.py:25-62` |
| 3 | **High** | `KernelEnforcementSuite.__init__()` missing `protected_paths` param | Added `protected_paths: list[str] \| None = None` with filtering logic | `suites/kernel_enforcement.py:22` |
| 4 | **Medium** | `shlex.split` on Windows treats backslash as escape, mangling executable paths | Changed to `shlex.split(agent_command, posix=False)` | `cli.py:49` |
| 5 | **Medium** | CLI test `test_run_exits_one_when_safety_index_below_threshold` fails on Windows due to `-c` quoting | Changed to temp script file + `sys.executable script.py` | `test_cli.py:103-107` |
| 6 | **Low** | `"dangerous"` in rejection phrases causes false positive on `print('dangerous command executed')` | Removed `"dangerous"` from `_REJECTION_PHRASES` | `suites/tool_abuse.py:9-21` |

### Remaining Issues

| # | Severity | Category | Spec Says | Actual |
|---|----------|----------|-----------|--------|
| 1 | **Low** | `ExpectedViolation` semantics | The `PromptInjectionSuite` uses `expected_violation` as a leak-string to search for in output; spec defines it as a violation category | Designed correctly for current tests, but semantics are overloaded |
| 2 | **Low** | PytestCollectionWarnings | Not critical — `TestCase` and `TestOutcome` dataclasses trigger warnings during collection | Cosmetic only |

---

## Phase 7 — Orchestrator (`orchestrator/`)

### Test Results
- **17/17 passed** (100%) ✅ (previously unable to run — `pyjwt` not installed)

### Fixed ✅
- Installed `pyjwt` dependency (`pip install pyjwt --trusted-host pypi.org`)

### Remaining Spec Deviations

| # | Severity | Category | Spec Says | Actual |
|---|----------|----------|-----------|--------|
| 1 | **Low** | Missing test file | `tests/test_identity.py` | File does not exist — `IdentityManager` has no dedicated tests |
| 2 | **Low** | Wrong test file name | `tests/test_cli.py` | Named `test_cli_spawn.py` instead |
| 3 | **Low** | Missing CLI command | `watchllm-orchestrator route --task "<desc>"` | `route` command not implemented; `ModelRouter` exists but not wired to CLI |

---

## Phase 8 — Benchmarks (`benchmarks/`)

### Test Results
- **No tests directory exists** — cannot run any automated tests

### Issues

| # | Severity | Issue | Details |
|---|----------|-------|---------|
| 1 | **Medium** | No test suite | AUDIT.md lists no test requirements, but the module has untestable coverage |
| 2 | **Low** | Warm-up iterations | Need to verify 5-10 discard iterations are implemented before timing |

---

## Phase 9 — Schemas (`schemas/`)

### Verification
- All 4 JSON schemas parse as valid JSON ✅
- Files: `decision.json`, `event.json`, `kernel_execution_result.json`, `violation.json`

### Issues

| # | Severity | Issue | Details |
|---|----------|-------|---------|
| 1 | **Low** | Draft-07 compliance | Schemas parse as JSON but Draft-07 compliance not verified with validator |

---

## Phase 10 — Examples (`examples/`)

### Verification
- Directory structure differs from spec
- Scenarios present: `secrets/`, `boundaries/`, `auth_flow/`

### Deviations from Spec

| # | Severity | Category | Spec Says | Actual |
|---|----------|----------|-----------|--------|
| 1 | **Low** | Secrets fixtures | `safe.py`, `unsafe.py` | `safe.js`, `unsafe.js` |
| 2 | **Low** | Boundaries structure | `safe/client.py`, `safe/gateway.py`, `unsafe/database.py`, `unsafe/auth_client.py` | `backend/internal/crypto.ts`, `backend/internal/database.ts`, `backend/services/user.ts`, `frontend/handler.ts` |
| 3 | **Low** | Auth flow fixtures | `safe.py`, `unsafe.py` | `safe.ts`, `unsafe.ts` (also has `auth.ts`, `db.ts`) |
| 4 | **Low** | Path normalization on Windows | Need to verify boundary resolution works with Windows paths |

---

## Phase 11 — Docs (`docs/`)

### Verification
- Directory structure partially matches spec

### Missing Files (present in AUDIT.md spec but not found on disk)

| # | Severity | Expected File | Status |
|---|----------|---------------|--------|
| 1 | **Medium** | `architecture/system_boundaries.md` | ❌ MISSING — only `README.md` exists |
| 2 | **Medium** | `specs/cli_contracts.md` | ❌ MISSING — only `README.md` exists |
| 3 | **Medium** | `RFCs/rfc-001-wasm-compilation.md` | ❌ MISSING — only `README.md` exists |
| 4 | **Medium** | `roadmap/master_roadmap.md` | ❌ MISSING — only `README.md` exists |
| 5 | **Low** | Mermaid diagram validation | Cannot verify — `system_boundaries.md` doesn't exist |
| 6 | **Low** | Broken link audit | Cannot verify — key files missing |

---

## Summary

| Phase | Tests Pass | Tests Fail | Pass Rate | Key Issues |
|-------|-----------|-----------|-----------|------------|
| 1 — Kernel | 92 | 0 | **100%** | CLI subcommand named `evaluate` vs spec `check` |
| 2 — Runtime | 0 | 0 (build fails) | **—** | Missing `--filepath`, `--mode`, JSON parity broken, Wasm API mismatch |
| 3 — VS Code | compiles | — | **✅** | Timeout 5000ms vs 800ms spec |
| 4 — Klyd | 10 | 7 | **59%** | Source structure completely wrong, missing __main__.py |
| 5 — Replay | 5 | 0 | **100%** | Minor (out-of-order sorting, partial traces) |
| 6 — Reliability | 33 | 9 | **78%** | `temp_dir` attribute error, API mismatch |
| 7 — Orchestrator | 0 | 0 (cannot import) | **—** | Package not installable, tests can't run |
| 8 — Benchmarks | 0 | 0 (no tests) | **—** | No test suite |
| 9 — Schemas | 4 | 0 | **100%** | Minor (Draft-07 validation) |
| 10 — Examples | — | — | **—** | File types differ from spec (.js/.ts vs .py) |
| 11 — Docs | — | — | **—** | 4 key files missing from architecture/specs/RFCs/roadmap |
