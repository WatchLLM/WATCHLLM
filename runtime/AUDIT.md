# WatchLLM Runtime Audit Specification (Phase 2 — Wasm Runtime)

This document defines the expected perfect state of the **WatchLLM Runtime** (Phase 2). It outlines the architecture, rules, interface contracts, and edge cases necessary to pass a complete verification run.

---

## 1. Purpose & Scope
The Runtime is a high-performance, native Rust implementation of the WatchLLM AST core. Its purpose is twofold:
1. Compile to **WebAssembly (Wasm)** to allow zero-subprocess, low-latency execution directly within editor extensions (like VS Code).
2. Compile to a **native CLI binary** for high-speed local check runs and CI/CD pipelines.

It does not add new rules or change the core logic of the Python kernel.

---

## 2. Expected Directory & File Layout
A perfect implementation must contain:
```
d:\watchllm\runtime\
├── crates/
│   ├── core/                      # Main rule engine crate (no CLI/Wasm dependencies)
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs             # Crate entrypoint
│   │   │   ├── parser.rs          # Tree-sitter JS/TS parser wrapper
│   │   │   ├── models.rs          # Serde data structs matching schemas
│   │   │   ├── engine.rs          # AST rule orchestrator
│   │   │   └── rules/
│   │   │       ├── mod.rs
│   │   │       ├── secrets.rs     # Rust secret literal rule
│   │   │       ├── imports.rs     # Rust forbidden imports rule
│   │   │       ├── boundaries.rs  # Rust service boundaries rule
│   │   │       └── auth_flow.rs   # Rust auth flow rule
│   │   └── benches/               # Criterion benchmarks for AST matching
│   ├── cli/                       # CLI wrapper crate (depends on core)
│   │   ├── Cargo.toml
│   │   └── src/
│   │       └── main.rs            # Clap CLI interface
│   └── wasm/                      # Wasm wrapper crate (depends on core)
│       ├── Cargo.toml
│       └── src/
│           └── lib.rs             # Wasm-bindgen exports
├── Cargo.toml                     # Cargo workspace configuration
├── Cargo.lock
├── README.md
└── tasks.md                       # Active gate checklist
```

---

## 3. Core Interface & Cargo Crate Responsibilities

### A. The Core Crate (`watchllm-core`)
- Must contain all rule logic and AST processing.
- Must remain strictly independent of Wasm and CLI dependencies to ensure maximum portability.
- Uses `tree-sitter` and language crates: `tree-sitter-javascript` and `tree-sitter-typescript` to build the AST.

### B. The CLI Crate (`watchllm-cli`)
- Thin CLI wrapper utilizing `clap` for arg parsing.
- Intercepts stdin (or reads file path), passes content to the core engine, formats results to stdout, and exits with matching exit codes.

### C. The Wasm Crate (`watchllm-wasm`)
- Uses `wasm-bindgen` to export evaluation functions to Node.js/V8 environments.
- Exposes `evaluate_source(source: &str, filepath: &str, language: &str, mode: &str) -> String` returning a stringified JSON payload matching the canonical schema.

---

## 4. Contract Parity & JSON Matching

### JSON Schema Contract
- The output structure of both CLI and Wasm engines must match the JSON output of the Python kernel 1:1.
- Nested structures (`rule_results` containing `violations` with `line`, `column`, `message`, `code_context`) must map exactly to prevent breakage in VS Code extension bindings.

### Exit Codes
- `0`: Pass.
- `1`: Block (Violations found in enforce mode).
- `2`: System Error / Parser Panic (Rust error or tree-sitter crash).

---

## 5. Critical Edge Cases & Error Recovery

| Edge Case | Expected Perfect Behavior |
|---|---|
| **No-Panic Guarantee** | The Rust runtime must never panic. All internal errors (`Result` failures, parser timeouts) must be caught and serialized as structured JSON outputs with exit code equivalents. Panics in Wasm crash the hosting JavaScript V8 environment. |
| **Wasm Memory Leaks** | JS wrappers calling Wasm methods must not leak memory. String allocations passed between JS and Rust must be cleaned up properly or handled via `wasm-bindgen` auto-free rules. |
| **Path Normalization** | Path comparisons in the boundary rule must handle Windows (`\`) and POSIX (`/`) file paths gracefully, normalizing separators before applying patterns. |
| **AST Tree Re-entry** | In TypeScript, interface or type declarations can break syntax chains. The Rust AST queries must be robust enough to skip type declarations and trace code flow correctly. |

---

## 6. Verification Checklist
To confirm Runtime compliance, run:
1. **Workspace Compilation**: Build the entire cargo workspace:
   ```bash
   cargo build --workspace
   ```
2. **Native Unit & Integration Tests**: Run tests inside the workspace:
   ```bash
   cargo test --workspace
   ```
3. **Wasm Target Packaging**: Pack the Wasm module using `wasm-pack`:
   ```bash
   cd crates/wasm
   wasm-pack build --target nodejs
   ```
4. **Performance Benchmarking**: Run latency checks:
   ```bash
   cargo bench -p watchllm-core
   ```
