# WatchLLM Master Roadmap

> Sequential product phases, milestones, and deliverables for the WatchLLM ecosystem.

## Phase Overview

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5 ──→ Phase 6 ──→ Phase 7 ──→ Phase 8
Kernel     Runtime    Editor      klyd        Replay      Reliability  Orchestrator  Cloud
 MVP      (Rust/Wasm) Integration  Memory      Engine       Harness      + Policy     Dashboard
 ✅         ✅          ✅          ✅           ✅           ✅            ✅            ⬜
```

## Phase 1 — Kernel MVP ✅ COMPLETE

**Status:** Complete (15/15 tasks)

Build the deterministic local write-path enforcement engine.

**Deliverables:**
- Repository skeleton with installable Python package
- Core data model: `Decision`, `RuleDecision`, `Violation`, `RuleResult`, `KernelResult`
- Tree-sitter integration for JavaScript and TypeScript (including TSX)
- Four deterministic rules:
  - **Secret Literal** — hardcoded credential detection with AST context
  - **Forbidden Import** — denylist-based dangerous module blocking
  - **Boundary** — cross-module import constraint enforcement
  - **Auth Flow** — call-order validation (DB before auth detection)
- Decision engine with enforce/shadow mode reduction
- CLI interface (`watchllm-kernel evaluate`) with stdin and file path input
- Machine-readable JSON output and human-readable text output
- Blocked-event JSONL logging to `.watchllm/logs/`
- Fixture corpus with pass/fail examples for every rule
- End-to-end regression test suite
- Performance benchmarks (parser, rules, e2e)

**Key Decisions:**
- Tree-sitter over regex for contextual, structure-aware enforcement
- Local-first: no network dependency on the critical enforcement path
- Enforce/shadow dual mode for safe rollout

---

## Phase 2 — Rust/Wasm Runtime ✅ COMPLETE

**Status:** Complete (8/8 tasks)

Port the kernel to Rust for high-performance, embeddable enforcement.

**Deliverables:**
- Cargo workspace: `core` (library), `cli` (binary), `wasm` (cdylib)
- Full data model parity with Python kernel (Serde schemas)
- Tree-sitter Rust bindings for JS/TS/TSX
- All four rules ported with identical fixture-based test pass rates
- Decision engine aggregator
- WebAssembly bindings via `wasm-bindgen` (Node.js target)
- Native CLI with `clap`, identical flags and exit codes to Python kernel
- Criterion benchmarks

**Key Decisions:**
- Exact JSON schema parity required between Python and Rust outputs
- Wasm target enables zero-process-latency embedding in browsers/editors
- All shared data structures compile cleanly to Wasm

---

## Phase 3 — Editor Integration ✅ COMPLETE

**Status:** Complete (7/7 tasks)

VS Code extension for real-time pre-save enforcement.

**Deliverables:**
- Extension skeleton with TypeScript, `package.json`, and activation events
- Configuration layer: `watchllm.pythonPath`, `watchllm.kernelPath`, `watchllm.mode`
- Kernel subprocess executor with stdin passing, JSON parsing, timeout enforcement
- `onWillSaveTextDocument` save interception hook
- Diagnostic mapping: kernel violations → VS Code Problems panel + squiggles
- End-to-end integration tests with real kernel
- Packaging: `.vsix` generation via `vsce`, esbuild bundling

**Key Decisions:**
- Graceful degradation: fail-open when kernel is unavailable
- Diagnostics surfaced inline (Problems panel + editor squiggles)
- Extension activates on `javascript` and `typescript` language modes

---

## Phase 4 — Architectural Memory (klyd) ✅ COMPLETE

**Status:** Complete (8/8 tasks)

Persistent architectural memory engine with git hook integration.

**Deliverables:**
- SQLite schema: `decisions` table with `reinforcement_count` and `flagged` fields
- CLI: `kl init`, `kl status`, `kl review`, `kl extract-commit`, `kl prepare-injection`, `kl run`
- Git hooks: `pre-commit` and `post-commit` auto-generated
- LLM provider integration (Anthropic API) for commit analysis
- Extraction engine: parses git diffs and commit messages into structured intents
- Memory state machine: maps LLM responses to `NEW`, `REINFORCE`, `CONTRADICT` DB mutations
- Context injection: `.klyd/injection.txt` for agent consumption
- Agent execution wrapper: `kl run <cmd>` with memory injection

**Key Decisions:**
- SQLite over remote DB: local-first, no network on memory path
- Three explicit mutation types: no free-form unclassified logs
- Git hooks as the natural integration point for architectural memory

---

## Phase 5 — Replay Engine ✅ COMPLETE

**Status:** Complete (8/8 tasks)

Execution graph observability platform for debugging agent behavior.

**Deliverables:**
- Express.js backend with SQLite (`better-sqlite3`)
- Database tables: `runs`, `steps`, `edges`
- Ingestion API: `POST /api/runs`, `POST /api/runs/:runId/steps`
- Query API: `GET /api/runs`, `GET /api/runs/:runId/graph`
- Vite + React + TypeScript frontend with React Router
- DAG visualization via ReactFlow (nodes as steps, edges as dependencies)
- Timeline replay with step-forward playback
- Divergence view: before/after diffs for state changes
- Polished E2E with concurrent frontend + backend launch

**Key Decisions:**
- Passive telemetry: never blocks execution loops
- SQLite for local trace storage
- ReactFlow for interactive DAG rendering

---

## Phase 6 — Reliability Harness ✅ COMPLETE

**Status:** Complete (8/8 tasks)

Adversarial stress-testing framework for enforcement correctness.

**Deliverables:**
- CLI: `reliability-stress run`, `reliability-stress list`
- YAML-based suite loader with test case dataclasses
- Agent orchestrator interface: subprocess execution with temp directory isolation
- Prompt injection suite: jailbreak and secret-leak scenarios
- Kernel enforcement suite: architectural violation testing with filesystem diffing
- Tool abuse suite: infinite loop detection and timeout parsing
- Scoring engine: quantitative Safety Index calculation
- CI/CD reporter: JUnit XML export with threshold exit codes

**Key Decisions:**
- Isolated temporary directories for each test run
- Quantitative Safety Index as a single measurable metric
- JUnit XML for CI/CD pipeline integration

---

## Phase 7 — Orchestrator & Policy ✅ COMPLETE

**Status:** Complete (5/5 tasks)

Agent identity management, model routing, and policy graph enforcement.

**Deliverables:**
- CLI: `watchllm-orchestrator issue-token`, `watchllm-orchestrator spawn`
- Identity manager: JWT token generation and validation with role-based claims
- Model router: capability-based model selection with fallback and load balancing
- Policy graph: path-to-role mapping with normalized paths and directory-aware binding
- Agent spawner: subprocess launch with `WATCHLLM_AGENT_TOKEN` environment injection

**Key Decisions:**
- JWT for agent identity tokens
- Policy graph is path-based and directory-aware
- Agent spawner injects identity via environment variables

---

## Phase 8 — Cloud Dashboard ⬜ PLANNED

**Status:** Not started

Centralized audit dashboard for team-wide enforcement visibility.

**Planned Deliverables:**
- Cloud-hosted dashboard for violation trends and team analytics
- Policy distribution: push rule configurations to team members
- Remote telemetry aggregation from local kernels
- Team-based access control and audit logs
- Integration with klyd for architectural drift visualization

**Non-goals for Phase 8:**
- Remote enforcement (enforcement remains local-first)
- Real-time blocking (local kernel always has final say)

---

## Cross-Cutting Principles (All Phases)

1. **Determinism**: Same input + same rules = same output. Every time.
2. **Local-First**: Critical enforcement path never depends on network.
3. **Schema Parity**: Python and Rust implementations produce identical JSON structures.
4. **Fail-Open Integration**: Editor and CI integrations degrade gracefully when the kernel is unavailable.
5. **AST Over Regex**: Structure-aware enforcement requires parse trees, not pattern matching.
6. **Isolated Testing**: Every rule has a fixture corpus with explicit pass and fail cases.
7. **Measurable Quality**: Quantitative Safety Index for reliability; Criterion benchmarks for performance.

## Version History

| Date | Change |
|------|--------|
| 2026-06-14 | Initial roadmap document seeded |
| 2026-06-25 | All phases 1–7 marked complete; Phase 8 planned |