⇒ WatchLLM Runtime (Expansion A) — 8-Day Prompt Pack

Copy **one full day block** below into your agent session. Each block uses the same template; only task, gate, and scope placeholders are filled from `internal_docs/IMPORTANT.md`.

**Repo:** `watchllm/runtime` (local: `d:\watchllm\runtime`)

---

⇒ Day 01 — Task 01: Cargo Workspace Skeleton

⇒ Task Instructions

Today's task:
**RUNTIME Task 01 — Cargo Workspace Skeleton**

Create the minimal Rust workspace layout:

- A root `Cargo.toml` configuring a workspace.
- `crates/core` (library crate for rule engine).
- `crates/cli` (binary crate).
- `crates/wasm` (cdylib crate).
- Basic `README.md`.

Today's gate:
- `cargo build --workspace` succeeds.
- No `tree-sitter` dependencies are required to build yet.

> Scope Constraints

Only work on:
- Cargo workspace scaffolding and basic crate setup (Task 01 only)

Do NOT:
- add tree-sitter yet
- write any rule logic

> Required Outputs

You must:
- implement the task narrowly
- verify workspace build passes

> Validation Requirements

Before finishing:
- verify gate behavior

---

⇒ Day 02 — Task 02: Data Models & Python Parity Schema

⇒ Task Instructions

Today's task:
**RUNTIME Task 02 — Data Models & Python Parity Schema**

Define the core structs in `crates/core/src/models.rs`:

- Use `serde` to define the input and output JSON schema.
- The output schema (`KernelExecutionResult`) must exactly match the Python kernel's output format (e.g. `status`, `exitCode`, `payload` with `allowed` and `violations`).

Today's gate:
- `cargo test` confirms that a mocked Rust output struct serializes to a JSON string that is 1:1 identical to a snapshot from the Python kernel.

> Scope Constraints

Only work on:
- Struct definitions and Serde derivations (Task 02 only)

Do NOT:
- parse ASTs yet

> Required Outputs

You must:
- implement the task narrowly
- write unit tests for JSON serialization parity
- explain architectural decisions

> Validation Requirements

Before finishing:
- verify gate behavior

---

⇒ Day 03 — Task 03: Tree-sitter Rust integration

⇒ Task Instructions

Today's task:
**RUNTIME Task 03 — Tree-sitter Rust integration**

Implement AST parsing in `crates/core/src/parser.rs`:

- Add `tree-sitter`, `tree-sitter-javascript`, and `tree-sitter-typescript`.
- Write a wrapper that takes a string of source code and returns a parsed Tree-sitter AST.

Today's gate:
- Unit tests can successfully parse a dummy TS file and traverse the AST to find a specific node.
- Compilation is fast and doesn't fail on missing C bindings.

> Scope Constraints

Only work on:
- Parsing infrastructure (Task 03 only)

Do NOT:
- write the actual security rules yet

> Required Outputs

You must:
- implement the task narrowly
- write tests for the parser
- explain architectural decisions

> Validation Requirements

Before finishing:
- verify gate behavior

---

⇒ Day 04 — Task 04: Rule 1 & 2 (Secrets & Imports)

⇒ Task Instructions

Today's task:
**RUNTIME Task 04 — Rule 1 & 2 (Secrets & Imports)**

Implement the first two rules in `crates/core/src/rules/`:

- Secret literal detection using AST queries.
- Forbidden import detection using AST queries.

Today's gate:
- Unit tests pass using the exact same positive/negative JS/TS fixtures from the Python kernel repository.

> Scope Constraints

Only work on:
- Rule 1 and Rule 2 AST traversal logic (Task 04 only)

Do NOT:
- build the decision aggregator yet

> Required Outputs

You must:
- implement the task narrowly
- write unit tests mirroring the Python test suite

> Validation Requirements

Before finishing:
- verify gate behavior

---

⇒ Day 05 — Task 05: Rule 3 & 4 (Boundaries & Auth-flow)

⇒ Task Instructions

Today's task:
**RUNTIME Task 05 — Rule 3 & 4 (Boundaries & Auth-flow)**

Implement the last two rules in `crates/core/src/rules/`:

- Boundary import constraints.
- Auth-flow sequence checking (detecting DB calls before auth calls in the same block).

Today's gate:
- Unit tests pass using the exact same positive/negative JS/TS fixtures from the Python kernel repository.

> Scope Constraints

Only work on:
- Rule 3 and Rule 4 AST traversal logic (Task 05 only)

> Required Outputs

You must:
- implement the task narrowly
- write unit tests mirroring the Python test suite

> Validation Requirements

Before finishing:
- verify gate behavior

---

⇒ Day 06 — Task 06: Decision Engine Aggregator

⇒ Task Instructions

Today's task:
**RUNTIME Task 06 — Decision Engine Aggregator**

Build the main entrypoint in `crates/core/src/engine.rs`:

- Combine all 4 rules.
- Accept the source code, run the parser, evaluate all rules, and return the final `models::KernelExecutionResult`.

Today's gate:
- A single test function can feed a string of TS code to the engine and receive a fully populated JSON-serializable decision object.

> Scope Constraints

Only work on:
- Rule aggregation and engine lifecycle (Task 06 only)

Do NOT:
- touch the Wasm or CLI crates yet

> Required Outputs

You must:
- implement the task narrowly
- verify the engine correctly aggregates multiple violations

> Validation Requirements

Before finishing:
- verify gate behavior

---

⇒ Day 07 — Task 07: Wasm Bindings

⇒ Task Instructions

Today's task:
**RUNTIME Task 07 — Wasm Bindings**

Expose the engine to JavaScript:

- Implement `crates/wasm/src/lib.rs` using `wasm-bindgen`.
- Expose a single function `evaluate_source(source: &str, config_json: &str) -> String` that returns the JSON result.
- Never panic; catch all errors and return them as valid JSON payload strings.

Today's gate:
- `wasm-pack build crates/wasm --target nodejs` succeeds.
- A simple `node` script can `require` the Wasm module and successfully call `evaluate_source()`.

> Scope Constraints

Only work on:
- `wasm-bindgen` integration and `crates/wasm` (Task 07 only)

Do NOT:
- add CLI features

> Required Outputs

You must:
- implement the task narrowly
- guarantee no panics can cross the FFI boundary

> Validation Requirements

Before finishing:
- verify gate behavior

---

⇒ Day 08 — Task 08: Native CLI & Benchmarks

⇒ Task Instructions

Today's task:
**RUNTIME Task 08 — Native CLI & Benchmarks**

Finish the native binary:

- Implement `crates/cli/src/main.rs` using `clap`.
- Support `--stdin`, `--json`, `--language` to match the Python CLI exactly.
- Add `criterion` benchmarks in `crates/core/benches/` to prove performance.

Today's gate:
- `cargo run --bin watchllm-cli -- --stdin --json` works exactly like the Python counterpart.
- `cargo bench` successfully runs without errors.

> Scope Constraints

Only work on:
- `clap` CLI and `criterion` benchmarks (Task 08 only)

> Required Outputs

You must:
- implement the task narrowly
- verify the CLI contract matches the VS Code extension's expectations

> Validation Requirements

Before finishing:
- verify gate behavior
