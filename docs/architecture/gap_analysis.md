# WatchLLM Gap Analysis — What's Missing

> *Written 2026-06-25 after full ecosystem audit. Intent: honest structural assessment, not a todo list.*

---

## Executive Summary

WatchLLM is a **capable engine trapped inside a fragmented monorepo**. The kernel is solid. The Rust runtime has real parity. The VSCode hook works. Klyd and Replay are genuinely useful observability layers. But the whole thing lacks **a single integrated product surface** and the connective tissue that would make it feel like one thing instead of eleven.

---

## 1. No Unified Entry Point (The Biggest Gap)

There is no `watchllm` command. You can run:

- `watchllm-kernel evaluate` (Python)
- `watchllm-cli` (Rust)
- `kl init` / `kl extract-commit` / `kl prepare-injection` (Klyd)
- `replay` HTTP server
- `watchllm-benchmarks run`

But there's no `watchllm install`, `watchllm init`, `watchllm status`, or `watchllm run`. Nothing that says "here's the product, this is how you start."

**What's missing:** A top-level CLI (`watchllm`) that wraps all subsystems. Should handle init, status, evaluate, and point you to deeper tools. The orchestrator exists but only does token issuance and agent spawning — it doesn't integrate the kernel, klyd, or replay at all.

---

## 2. No Installation/Onboarding Story

There is no `pip install watchllm` or `cargo install watchllm`. Each component has its own setup:

- Kernel: `pip install -e .` from inside `kernel/`
- Runtime: `cargo build --release` from inside `runtime/`
- VSCode: manual `npm install` + symlink
- Klyd: `pip install -e .` from inside `klyd/`
- Replay: `npm install && npm run build`

There's no `Makefile`, `justfile`, or workspace-level script that bootstraps everything. A new developer has to read 11 READMEs to figure out how to get anything running.

**What's missing:** A monorepo-level build script or `watchllm init --dev` that installs all subsystems, runs migrations, and verifies health.

---

## 3. No End-to-End Integration Test

Each component has its own tests:
- Kernel: Python tests (13 files, good coverage)
- Runtime: Rust `#[cfg(test)]` inline tests (7 files, decent)
- Klyd: Click integration tests
- Reliability: YAML-based case runner
- Replay: 2 test files (query API + frontend build)

But there's **zero cross-component integration test**. No test that:
- Spins up the Replay API
- Runs the kernel against a fixture
- Checks that Klyd records a decision
- Verifies the VSCode save hook blocks correctly end-to-end

**What's missing:** A CI pipeline that exercises the full save → kernel → replay → klyd pipeline in a single test run. The Reliability harness has the scaffolding for this but isn't wired across components yet.

---

## 4. No Web Dashboard / UI

The Replay module has a React frontend with a RunGraph view — but it only visualizes execution traces that were posted to its API. There's no dashboard for:

- Viewing current policy violations across a codebase
- Seeing klyd architectural decisions and their confidence scores
- Monitoring kernel enforcement metrics over time
- Managing which rules are active on which paths

The Phase 8 (Cloud Dashboard) is marked Planned in the roadmap but completely unimplemented. Even a local dashboard (Electron or a simple web UI pointing at Replay) would make the observability story click.

**What's missing:** A local dashboard that aggregates kernel results, klyd decisions, and replay traces into a single pane of glass. This is the product layer that would make the whole system feel coherent.

---

## 5. Rust Runtime Is Unused in Production

The Rust/Wasm runtime is a technical marvel — it has feature-for-feature parity with the Python kernel and compiles to Wasm for zero-process latency. But it's **not wired into the VSCode extension**. The VSCode save hook spawns the Python kernel CLI as a subprocess (`watchllm-kernel evaluate`). The Wasm binary exists but no consumer uses it.

**What's missing:** A bridge that lets the VSCode extension call the Wasm binary directly (or at least the Rust CLI) instead of the Python kernel, and a benchmark report showing the latency difference.

---

## 6. Language Support Limited to JS/TS

The kernel only supports JavaScript, TypeScript, and TSX. The parser infrastructure is Tree-sitter (which supports dozens of languages), but the rules are all written against JS/TS AST node types. Python support is entirely absent despite Python being a massive target for AI-generated code.

The schemas and models are language-agnostic (they're JSON), but every actual rule (`auth_flow`, `boundary`, `forbidden_imports`, `secrets`) walks JS/TS-specific AST nodes.

**What's missing:** At minimum, Python language support with corresponding rules. Ideally, a language plugin interface so rules can be registered per-language.

---

## 7. No Policy Configuration Layer

Rules are hardcoded. The `DEFAULT_BOUNDARY_MAP` lives inline in `boundary.py`. The `DEFAULT_FORBIDDEN_MODULES` lives in `forbidden_imports.py`. There's no:

- `.watchllm.yaml` or `.watchllm.toml` per-project config
- Rule severity overrides
- Rule enable/disable per path
- Custom forbidden module lists
- Custom boundary maps

The ForbiddenImportRule constructor *accepts* custom parameters, but nothing reads them from a config file. Every deployment has to fork the code to customize rules.

**What's missing:** A project-level config file format, a config loader shared across kernel and runtime, and per-rule configuration surfaces.

---

## 8. Klyd Is Not Wired to the Kernel

Klyd extracts architectural decisions from commits and injects them into agent context. The kernel evaluates code against deterministic rules. These are **complementary but not connected**. A klyd decision like "auth module must never import db/internal" should feed into the kernel's boundary rule. But they're completely independent.

**What's missing:** A bridge where klyd decisions (especially `NEW` with high confidence) can generate or update kernel boundary maps and forbidden import lists.

---

## 9. No CI/CD Integration Patterns

There's no GitHub Action, GitLab CI template, pre-commit hook, or pre-receive hook that runs the kernel. Klyd has git hooks (`pre-commit` and `post-commit`), but they only run injection/extraction — not kernel enforcement. The kernel CLI exists but isn't wired into any automated pipeline template.

**What's missing:** CI integration templates:
- GitHub Action that runs `watchllm-kernel evaluate` on changed files
- Pre-commit hook that blocks commits with violations
- Pre-receive hook for server-side enforcement

---

## 10. Observability Is Fragmented

Three separate databases:
- **Klyd:** `.klyd/memory.db` (SQLite, architectural decisions)
- **Replay:** `data/replay.sqlite` (SQLite, execution traces)
- **Kernel:** Local JSONL log (blocked events, file-based)

No unified view. No aggregation. If a violation was blocked, you can't trace it from the kernel log → to the klyd decision it violated → to the replay trace of the agent that caused it. Each layer's data stays in its own silo.

**What's missing:** Trace correlation IDs that join kernel events → replay steps → klyd decisions, and a unified query API or dashboard querying all three stores.

---

## 11. No Multi-File / Cross-File Analysis

Every rule evaluates a single file at a time. The boundary rule checks `auth → db/internal` imports — but only *within a single file*. It can't detect that `handler.ts` imports `dangerousHelper.ts` which imports `child_process`. The call-order analysis in auth_flow is fully intra-file.

**What's missing:** Cross-file import graph construction, transitive forbidden import detection, and multi-file auth-flow analysis (which is substantially harder and may be out of MVP scope — but should at least be acknowledged).

---

## 12. No Upgrade / Migration Path

There's no versioning for klyd decisions, no schema migration system for the Replay database, and no version compatibility matrix. If you upgrade the kernel from 0.1.0 to 0.2.0, how does klyd know the decisions it extracted against the old kernel are still valid?

**What's missing:** Schema versioning with migration paths, and a compatibility matrix documenting which component versions work together.

---

## 13. No Release Artifacts

No published packages:
- No PyPI package for the kernel
- No crates.io crate for the runtime
- No npm package for the VSCode extension
- No Docker image
- No Homebrew tap
- No apt/deb repo

The code works, but nobody outside this repo can use it without cloning the monorepo and building from source.

**What's missing:** CI-driven release pipeline that publishes packages to their respective registries on version tags.

---

## What's Actually Good (Not Missing)

These parts are genuinely solid:

| Area | Assessment |
|------|-----------|
| Kernel engine | Clean, deterministic, well-structured. The engine + parser + rules separation is excellent. |
| Rule quality | All 4 rules (secrets, imports, boundaries, auth_flow) are AST-aware, not regex slop. The INCONCLUSIVE handling for ambiguous control flow is sophisticated. |
| Rust parity | The Rust runtime faithfully reproduces the Python kernel with identical output shape. The Wasm compilation target is forward-thinking. |
| Schema discipline | JSON Schema for all cross-component contracts. The decision/violation/event/kernel_execution_result schemas cover all message types. |
| Klyd state machine | NEW/REINFORCE/CONTRADICT classification with confidence scoring is a clean model. Git hook auto-injection is well-designed. |
| Replay append-only DB | Append-only triggers, WAL mode, foreign keys, proper indexing. This is production-grade SQLite. |
| Reliability harness | YAML-driven test cases with Safety Index scoring. Adversarial prompt-injection suite. JUnit XML output. |
| AST utility layer | The shared `_ast_utils.py` (and its Rust equivalent) eliminates the redundant parsing that early versions had. |

---

## Priority Triage

### Critical (blocks real adoption)
1. Unified entry point / install story
2. Policy configuration layer (YAML/TOML config)
3. CI/CD integration templates
4. Release artifacts (packages)

### High (structural debt)
5. Wire Rust/Wasm into VSCode extension
6. End-to-end integration tests
7. Klyd ↔ Kernel bridge
8. Local dashboard (aggregate observability)

### Medium (feature expansion)
9. Python language support
10. Cross-file import analysis
11. Trace correlation IDs across observability layers

### Low (hygiene)
12. Schema versioning / upgrade paths
13. Monorepo build script / developer onboarding doc

---

## Final Verdict

WatchLLM is not a "scattered mess." It's a **well-engineered engine that stopped one layer short of becoming a product**. Every component is individually well-built, the contracts between them exist, and the design philosophy (deterministic, local-first, AST-aware) is consistent throughout. But until there's a single `watchllm` command, a config file, and a way for someone to go from zero to enforcing policy in 5 minutes, it's a beautiful engine without a car around it.