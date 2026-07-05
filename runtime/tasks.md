# WatchLLM Runtime Tasks

## Task 01 — Cargo Workspace Skeleton

Status: Complete

Gate:
- `cargo build --workspace` succeeds.
- No `tree-sitter` dependencies are required to build yet.

Scope:
- A root `Cargo.toml` configuring a workspace.
- `crates/core` (library crate for rule engine).
- `crates/cli` (binary crate).
- `crates/wasm` (cdylib crate).
- Basic `README.md`.

Non-goals:
- Rule logic
- AST parsing

---

## Task 02 — Data Models & Python Parity Schema

Status: Complete

Gate:
- `cargo test` confirms that a mocked Rust output struct serializes to a JSON string that is 1:1 identical to a snapshot from the Python kernel.

Scope:
- Input and Output Serde schema definitions in `crates/core`.

Non-goals:
- Parsers

---

## Task 03 — Tree-sitter Rust integration

Status: Complete

Gate:
- Unit tests can successfully parse a dummy TS file and traverse the AST to find a specific node.
- Compilation is fast and doesn't fail on missing C bindings.

Scope:
- `tree-sitter`, `tree-sitter-javascript`, `tree-sitter-typescript`

Non-goals:
- Rules

---

## Task 04 — Rule 1 & 2 (Secrets & Imports)

Status: Complete

Gate:
- Unit tests pass using the exact same positive/negative JS/TS fixtures from the Python kernel repository.

Scope:
- Secret literal detection using AST queries.
- Forbidden import detection using AST queries.

---

## Task 05 — Rule 3 & 4 (Boundaries & Auth-flow)

Status: Complete

Gate:
- Unit tests pass using the exact same positive/negative JS/TS fixtures from the Python kernel repository.

Scope:
- Boundary import constraints.
- Auth-flow sequence checking (detecting DB calls before auth calls in the same block).

---

## Task 06 — Decision Engine Aggregator

Status: Complete

Gate:
- A single test function can feed a string of TS code to the engine and receive a fully populated JSON-serializable decision object.

Scope:
- Combining all 4 rules into the main evaluation entrypoint.

Non-goals:
- Wasm and CLI compilation

---

## Task 07 — Wasm Bindings

Status: Complete

Gate:
- `wasm-pack build crates/wasm --target nodejs` succeeds.
- A simple `node` script can `require` the Wasm module and successfully call `evaluate_source()`.

Scope:
- `crates/wasm/src/lib.rs` using `wasm-bindgen`.
- No panics across FFI.

Non-goals:
- CLI features

---

## Task 08 — Native CLI & Benchmarks

Status: Complete

Gate:
- `cargo run --bin watchllm-cli -- --stdin --json` works exactly like the Python counterpart.
- `cargo bench` successfully runs without errors.

Scope:
- `crates/cli/src/main.rs` using `clap`.
- `criterion` benchmarks in `crates/core/benches/`.
