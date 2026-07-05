# WatchLLM Kernel Tasks

## Task 01 — Build the repo skeleton

Status: Complete

Gate:
- Package entrypoint runs successfully.
- Repository installs cleanly in a fresh environment.
- No placeholder imports break startup.

Scope:
- Repository skeleton
- Project manifest
- Runnable --help entrypoint

Non-goals:
- Parser implementation
- Rule implementation
- Enforcement engine
- Editor integration

---

## Task 02 — Define the core data model

Status: Complete

Gate:
- Unit tests confirm the models serialize and deserialize correctly.
- A sample rule can return a structured decision object.
- No rule depends on editor-specific code.

Scope:
- Source file(s) for models/types.
- Typed decision object.
- Typed violation object.
- Typed rule interface.

Non-goals:
- Parser implementation
- Rule implementation
- Enforcement engine
- Editor integration

---

## Task 03 — Implement source loading and parse entrypoint

Status: Complete

Gate:
- Test fixture source can be loaded from stdin and file path.
- Parser entrypoint returns a structured parse result.
- Invalid input is handled without crashing the process.

Scope:
- Source loading through CLI file/stdin paths
- Parser entrypoint wiring
- Language parameter handling
- Invalid/unsupported language handling

Non-goals:
- Rule implementation
- Decision engine aggregation
- Editor integration
- Save-path interception

---

## Task 04 — Integrate AST parsing for JS/TS

Status: Complete

Gate:
- Known JS and TS fixtures parse successfully.
- Parse tree roots are visible to tests.
- Syntax-error fixtures do not crash the parser.

Scope:
- JavaScript parser integration
- TypeScript parser integration
- TSX parser support
- Structured ParseResult wrapper
- Parser helper tests

Non-goals:
- Rule implementation
- Rule engine aggregation
- CLI enforcement semantics
- Editor integration

---

## Task 05 — Build fixture corpus

Status: Complete

Gate:
- Each rule has at least one pass and one fail fixture.
- Fixtures are readable and minimal.
- Tests can load all fixtures automatically.

Scope:
- Fixture corpus for rule evidence
- Minimal JS/TS pass and fail examples
- Automatic fixture discovery tests

Non-goals:
- Rule implementation
- Rule evaluation
- Parser integration changes
- Decision engine aggregation
- CLI fixture commands
- Editor integration

---

## Task 06 — Implement the secret-literal rule

Status: Complete

Gate:
- Hardcoded secret fixtures fail.
- Env-var retrieval fixtures pass.
- Comment/string/mock false positives are not allowed to block.
- Unit tests cover at least 3 positive and 3 negative cases.

Scope:
- Secret-literal rule implementation
- AST context checks
- Safe retrieval allowance logic
- Tests against secret fixtures

Non-goals:
- Forbidden-import rule implementation
- Boundary rule implementation
- Auth-flow rule implementation
- Decision engine aggregation
- CLI rule execution
- Editor integration

---

## Task 07 — Implement the forbidden-import rule

Status: Complete

Gate:
- Forbidden imports fail.
- Allowed internal imports pass.
- Relative traversal violations are detected.
- Tests prove no accidental blocking of safe imports.

Scope:
- Forbidden-import rule implementation
- AST-based import extraction
- CommonJS require extraction
- Forbidden module denylist
- Relative traversal blocking
- Tests against forbidden-import fixtures

Non-goals:
- Boundary rule implementation
- Auth-flow rule implementation
- Repository-wide dependency graph analysis
- Decision engine aggregation
- Editor integration

---

## Task 08 — Implement the boundary rule

Status: Complete

Gate:
- Disallowed cross-boundary edges fail.
- Allowed edges pass.
- Circular dependency case is detected or explicitly excluded with a stated rule.

Scope:
- Boundary rule implementation
- Import edge extraction
- Boundary map configuration
- Cross-boundary enforcement logic
- Tests against boundary fixtures

Non-goals:
- Circular dependency detection
- Repository-wide dependency graph analysis
- Auth-flow rule implementation
- Decision engine aggregation
- CLI rule execution
- Editor integration

---

## Task 09 — Implement the auth-flow rule

Status: Complete

Gate:
- A handler that mutates data before auth fails.
- A handler that authenticates first passes.
- A handler with ambiguous order is either flagged or marked inconclusive by spec.

Scope:
- Auth-flow rule implementation
- Flow-sensitive call ordering within handler scope
- Protected-operation detection
- Guard-call detection
- Tests against auth-flow fixtures
- Explicit inconclusive behaviour documentation

Non-goals:
- Repository-wide control-flow analysis
- Full path-sensitive analysis
- Decision engine aggregation
- CLI rule execution
- Editor integration

---

## Task 10 — Build the decision engine

Status: Complete

Gate:
- Multiple rules can run on one source file.
- The engine returns a single coherent decision object.
- Blocking any one rule in enforce mode blocks the save.

Scope:
- Rule runner
- Violation aggregation
- Enforce/shadow decision reduction
- Deterministic evaluation order

Non-goals:
- CLI rule execution
- JSON output contract
- Editor integration
- Default remote policy loading
- Save-path interception

---

## Task 11 — Build CLI interface

Status: Complete

Gate:
- `--help` works.
- A sample file can be evaluated from stdin.
- Exit codes are correct.
- JSON output is valid and stable.

Scope:
- `--stdin` support
- File path support
- Language flag support
- Enforce/shadow mode switch
- Machine-readable output

Non-goals:
- Editor integration
- Remote policy loading
- Save-path interception

---

## Task 12 — Add tests for end-to-end behaviour

Status: Complete

Gate:
- Passing fixtures remain passing.
- Failing fixtures block in enforce mode.
- Shadow mode does not block.
- Regression tests are deterministic across runs.

Scope:
- End-to-end save-path tests
- Rule suite regression tests
- Fixture-based golden tests

Non-goals:
- Editor integration
- Remote policy loading
- Save-path interception

---

## Task 13 — Add performance benchmarks

Status: Complete

Gate:
- Benchmark command runs locally.
- Benchmark output is reproducible.
- Baseline numbers are recorded in docs.

Scope:
- Parser benchmark
- Rule evaluation benchmark
- End-to-end benchmark
- JSON benchmark output
- Baseline documentation

Non-goals:
- Performance optimisation
- Rust/Wasm migration
- Parser redesign
- Rule engine redesign
- Budget enforcement
- Editor integration

---

## Task 14 — Add local logging and violation reporting

Status: Complete

Gate:
- A blocked file yields a clear reason.
- Logs include rule id and location where available.
- No required report field is missing.

Scope:
- Local JSONL blocked-event logging
- Structured violation report schema
- Human-readable CLI violation output
- Tests for report schema and log writing
- Reporting contract documentation

Non-goals:
- Cloud telemetry
- Remote sync
- LLM explanations
- Policy override
- Editor UI diagnostics

---

## Task 15 — Wrap for editor integration readiness

Status: Complete

Gate:
- The CLI contract is stable enough for editor integration.
- The editor host can use the kernel without internal knowledge of rule mechanics.

Scope:
- CLI/output contract documentation
- Integration notes
- Stable exit codes and JSON structure

Non-goals:
- VSCode extension implementation
- Editor UI diagnostics
- Wasm runtime
- Cloud policy sync
- Remote telemetry
