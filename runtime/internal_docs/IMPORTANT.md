# WatchLLM Runtime

## 0) Purpose

This document defines the **Runtime layer (Expansion A)** for WatchLLM. The goal of this layer is to take the deterministic, AST-based enforcement logic proven in the Python kernel and port it to a high-performance, portable **Rust** core.

This Rust core exists to be compiled to **WebAssembly (Wasm)** so it can be natively embedded into editor extensions (like VS Code) without requiring a Python subprocess spawn on every save. It will also provide a native CLI binary for raw speed in CI/CD environments.

---

## 1) Scope

### In scope
* A core Rust library (`watchllm-core`) that parses JS/TS using `tree-sitter`.
* Re-implementing the 4 core kernel rules (Secrets, Imports, Boundaries, Auth-flow) in Rust.
* Exposing a `wasm-bindgen` interface (`watchllm-wasm`).
* Exposing a `clap` CLI interface (`watchllm-cli`).
* Strict JSON output parity with the Python kernel.

### Out of scope
* Defining new rules (only port the existing 4).
* Supporting new languages (stick to JS/TS).
* Modifying the editor extension (this repo just produces the `.wasm` package).
* Cloud features or agent integrations.

---

## 2) Architecture rules

### 2.1 The Zero-Cost Portability Rule
The core logic must live entirely in `watchllm-core`. The core crate must know absolutely nothing about Wasm or the CLI. The CLI and Wasm crates are just thin wrappers that pass strings into the core and serialize the JSON output.

### 2.2 The JSON Parity Rule
The output schema of the Rust runtime MUST be 1:1 identical to the output of the Python kernel.
If the Rust runtime outputs a different JSON key, the existing VS Code extension will break. This is a critical regression boundary.

### 2.3 The Determinism Rule
Like the Python kernel, no LLMs or probabilistic heuristics are allowed in the runtime. It is a strict AST parser and evaluator.

### 2.4 The No-Panic Rule
The runtime must never panic. A panic in Wasm crashes the host V8 engine (and the VS Code extension host). All errors must be caught and returned gracefully as valid JSON with `exitCode: 2` equivalents.

---

## 3) Implementation order

1. **Cargo Workspace Skeleton**: `core`, `cli`, `wasm` crates.
2. **Data Models & Python Parity Schema**: Define `serde` structs that match the Python output perfectly.
3. **Tree-sitter Rust integration**: Hook up `tree-sitter-javascript` and `tree-sitter-typescript`.
4. **Rule 1 & 2**: Secret literals and Forbidden imports.
5. **Rule 3 & 4**: Boundaries and Auth-flow.
6. **Decision Engine Aggregator**: Combines rule outputs into the final schema.
7. **Wasm Bindings**: `wasm-pack` build pipeline.
8. **Native CLI & Benchmarks**: `clap` CLI and `criterion` benchmarks.

---

## 4) Definition of done
* `wasm-pack build` produces a valid npm package that evaluates a TS file correctly.
* `cargo run --bin watchllm-cli` evaluates a TS file and outputs identical JSON to the Python kernel.
* All 4 core rules pass the original Python fixture corpus.
