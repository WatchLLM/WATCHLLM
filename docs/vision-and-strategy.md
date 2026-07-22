# WatchLLM: Vision & Strategy

**Deterministic governance for autonomous agents.**

---

## The Problem

Agents are probabilistic. Infrastructure cannot be.

When an AI agent writes code, we can inspect the output. When an AI agent scrapes the web, we have no cryptographic proof of what it actually saw. Screenshots are forgeable. Logs are mutable. Memory is fallible.

This creates a fundamental trust gap:

- You cannot prove an agent didn't hallucinate a web response.
- You cannot prove an agent didn't ignore a security boundary.
- You cannot replay an agent's decision with confidence.
- You cannot audit an agent's behavior for compliance.

**This is the problem WatchLLM solves.**

---

## The Vision

> **WatchLLM is the verifiable execution layer for autonomous agents.**

We provide cryptographic guarantees for both **inputs** (web data via zkTLS) and **outputs** (code via AST governance). Every agent action is auditable, replayable, and mathematically provable.

### The North Star

> **By 2028, every autonomous agent in production will run on a verifiable execution layer. WatchLLM will be the standard.**

---

## The Mission

Build the open-core infrastructure that makes agent governance:

1. **Deterministic** — Rules are evaluated predictably, every time.
2. **Cryptographically verifiable** — Inputs (web proofs) and outputs (code writes) are anchored to immutable ledgers.
3. **Developer-first** — Install via `pip`, configure via JSON, visualize via dashboard.
4. **Self-hostable** — The core runs locally, cloud is optional.

---

## Core Tenets (The Rules We Don't Break)

### 1. Inputs and Outputs Must Be Verifiable

- **Inputs**: Every web request an agent makes must be provable via zkTLS.
- **Outputs**: Every code write an agent makes must be evaluated by the kernel.
- **The Bridge**: If an agent cites a web fact in its code, that fact must have a matching proof hash.

### 2. Open-Core by Default

- The currently shipped kernel, schemas, VS Code extension, and examples are **MIT-licensed**.
- A MIT-licensed webproof client SDK is planned but has not shipped. Do not describe it as available until its package and public API exist.
- The Rust runtime, replay dashboard, reliability engine, klyd memory, orchestrator, and webproof proving/verification engine are **proprietary**.
- This maximizes distribution while preserving our moat.

### 3. Performance Is Non-Negotiable

- The Rust runtime must compile to Wasm for edge execution.
- The zkTLS prover must use Poseidon hashing for ZK-friendly performance.
- The Cloudflare Worker must handle proofs with sub-second latency.
- No Python bottlenecks — heavy lifting is in Rust.

### 4. The Agent Is the User

- We don't build for developers in the traditional sense.
- We build for **agent runtimes** (LangChain, AutoGPT, etc.).
- The SDK intercepts HTTP traffic transparently — agents don't even know they're being governed.

### 5. Ship Fast, Break Nothing

- 223 tests, 100% pass rate. This is the floor, not the ceiling.
- CI must pass before merge.
- Schema changes are backward-compatible.

---

## The Strategy

### Phase 0: The Foundation (✅ Done)
- Kernel with Tree-sitter AST parsing and rule evaluation.
- Rust runtime with sandbox and identity tokens.
- VS Code extension with save interception.
- Klyd memory engine with SQLite.
- Replay dashboard with DAG visualization.
- Reliability stress-testing framework.

### Phase 1: The Input Layer (🚧 Current)
- Add zkTLS webproof subsystem (this project).
- Python SDK with HTTP interception (open-source).
- Rust engine with Poseidon Merkle accumulator (closed-source).
- Cloudflare Worker for proof ingestion and L2 anchoring (closed-source).
- Integrate webproofs into Replay and Klyd.

### Phase 2: The Orchestrator (📋 Next)
- Expose ModelRouter and PolicyGraph via CLI subcommands.
- Dynamic routing based on proof requirements.
- Multi-agent session management.
