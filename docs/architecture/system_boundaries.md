# System Architecture & Boundaries

> Agents are probabilistic. Infrastructure cannot be.

## Architecture Diagram

```mermaid
graph TD
    subgraph Host Layer
        EDITOR[Editor<br/>VS Code / CLI]
    end

    subgraph Enforcement Core
        KERNEL[WatchLLM Kernel<br/>Python + Tree-sitter]
        RUNTIME[WatchLLM Runtime<br/>Rust + Wasm]
    end

    subgraph Memory & Observability
        KLYD[klyd<br/>Architectural Memory<br/>SQLite + Git Hooks]
        REPLAY[Replay<br/>Execution Trace DAG<br/>React + SQLite]
    end

    subgraph Governance
        ORCH[Orchestrator<br/>Agent Identity & Routing<br/>JWT + Policy Graph]
        SCHEMAS[Schemas<br/>Cross-Component JSON Contracts<br/>Draft-07]
    end

    subgraph Quality
        RELIABILITY[Reliability Harness<br/>Adversarial Testing<br/>Safety Index]
        BENCHMARKS[Benchmarks<br/>Perf Regression<br/>Criterion]
    end

    EDITOR -->|pre-save hook| KERNEL
    EDITOR -->|pre-save hook| RUNTIME
    KERNEL -->|ALLOW/BLOCK| EDITOR
    RUNTIME -->|ALLOW/BLOCK| EDITOR
    KERNEL -.->|JSON schema compliance| SCHEMAS
    RUNTIME -.->|JSON schema compliance| SCHEMAS
    KERNEL -->|violation events| KLYD
    KERNEL -->|trace ingestion| REPLAY
    ORCH -->|agent token + policy| KERNEL
    RELIABILITY -->|stress test| KERNEL
    RELIABILITY -->|stress test| RUNTIME
    BENCHMARKS -->|perf test| KERNEL
    BENCHMARKS -->|perf test| RUNTIME
```

## System Layers

### 1. Host Layer

The entry point for all enforcement. Two integration paths exist:

- **Editor Integration**: VS Code extension intercepts `onWillSaveTextDocument` and invokes the kernel before allowing disk write.
- **CLI Fallback**: Direct invocation via `watchllm-kernel evaluate` for CI/CD, pre-commit hooks, and manual checks.

### 2. Enforcement Core

The deterministic write-path gate. Two implementations with full parity:

- **Kernel (Python)**: Reference implementation using Tree-sitter for AST parsing. Pure, offline-capable, no network dependency on the critical path.
- **Runtime (Rust + Wasm)**: High-performance port with zero-process-latency embedding. Compiles to WebAssembly for browser/edge use. Maintains exact JSON schema parity with the Python kernel.

### 3. Memory & Observability

Passive telemetry and architectural trace layers that never block the write path:

- **klyd**: Persistent architectural memory engine. Tracks architectural intent via git hooks that parse commits into `NEW`, `REINFORCE`, or `CONTRADICT` SQLite mutations.
- **Replay**: Execution graph observability. Ingests tool-call traces and renders them as interactive DAGs for debugging agent behavior.

### 4. Governance

Agent identity, authorization, and policy distribution:

- **Orchestrator**: Issues agent identity tokens (JWT), routes to appropriate models based on capability requirements, and enforces path-based policy graphs.
- **Schemas**: Canonical JSON Schema (Draft-07) contracts defining every cross-component data structure: violations, decisions, kernel execution results, and events.

### 5. Quality

Continuous validation of enforcement correctness and performance:

- **Reliability Harness**: Adversarial stress-testing framework. Runs prompt injection, kernel enforcement, and tool abuse suites. Computes a quantitative Safety Index.
- **Benchmarks**: Criterion-based performance benchmarks for both Python and Rust runtimes.

## Data Flow: Save Path

```mermaid
sequenceDiagram
    participant Editor
    participant Kernel
    participant Disk
    participant Logger

    Editor->>Kernel: onWillSaveTextDocument(source, file_path)
    Kernel->>Kernel: Parse source → AST
    Kernel->>Kernel: Run rules in order (secrets, imports, boundaries, auth-flow)
    Kernel->>Kernel: Reduce → ALLOW or BLOCK
    alt Decision: ALLOW
        Kernel-->>Editor: exit 0, Decision.ALLOW
        Editor->>Disk: Write file
    else Decision: BLOCK
        Kernel-->>Editor: exit 1, Decision.BLOCK + violations
        Kernel->>Logger: Write JSONL blocked-event log
        Editor->>Editor: Surface diagnostics, block save
    end
```

## Runtime Boundaries

Each subsystem has explicit knowledge boundaries:

| Subsystem | Knows About | Does NOT Know About |
|-----------|-------------|---------------------|
| **Kernel** | Source text, AST structure, rules, file paths | Editor UI, agent identity, policy graphs |
| **Runtime** | Same as Kernel (Rust port) | Same as Kernel |
| **klyd** | Git diffs, commit messages, SQLite | AST internals, enforcement rules |
| **Replay** | Tool-call traces, DAG structure | Source code content, enforcement decisions |
| **Orchestrator** | Agent tokens, model routing, path policies | Source code, AST, enforcement rules |
| **Schemas** | JSON structure, data contracts | Any implementation detail |
| **Reliability** | Test suites, agent output | Production enforcement paths |
| **VS Code Extension** | Document state, diagnostics, kernel subprocess | Rule internals, AST structure |

## Language Runtime Mapping

```mermaid
graph LR
    subgraph Input
        JS[JavaScript]
        TS[TypeScript]
        TSX[TSX]
    end

    subgraph Parsers
        TJS[tree-sitter-javascript]
        TTS[tree-sitter-typescript]
    end

    subgraph Rules
        SECRETS[Secret Literal]
        IMPORTS[Forbidden Import]
        BOUNDARY[Boundary]
        AUTH[Auth Flow]
    end

    subgraph Output
        DECISION[ALLOW / BLOCK]
        VIOLATIONS[Violation List]
    end

    JS --> TJS
    TS --> TTS
    TSX --> TTS
    TJS --> SECRETS
    TTS --> SECRETS
    TJS --> IMPORTS
    TTS --> IMPORTS
    TJS --> BOUNDARY
    TTS --> BOUNDARY
    TJS --> AUTH
    TTS --> AUTH
    SECRETS --> DECISION
    IMPORTS --> DECISION
    BOUNDARY --> DECISION
    AUTH --> DECISION
    DECISION --> VIOLATIONS
```

## Deployment Topology

```
┌─────────────────────────────────────────────┐
│                 Developer Machine             │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐  │
│  │ VS Code │  │  Kernel  │  │    klyd    │  │
│  │  Ext.   │──│ (Python) │  │ (Git Hooks)│  │
│  └─────────┘  └──────────┘  └────────────┘  │
│                     │                         │
│              ┌──────┴──────┐                  │
│              │   Replay    │                  │
│              │ (localhost) │                  │
│              └─────────────┘                  │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│              CI/CD Pipeline                   │
│  ┌──────────┐  ┌────────────┐               │
│  │  Kernel  │  │ Reliability │               │
│  │   CLI    │  │  Harness    │               │
│  └──────────┘  └────────────┘               │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│           Browser / Edge Runtime              │
│  ┌──────────────────────┐                    │
│  │  Runtime (Wasm)      │                    │
│  │  Zero-process latency│                    │
│  └──────────────────────┘                    │
└─────────────────────────────────────────────┘
```

## Cross-Component Contracts

All components communicate through the schemas defined in `schemas/v1/`:

| Contract | Producer | Consumers |
|----------|----------|-----------|
| `violation.json` | Kernel, Runtime | VS Code, klyd, Replay, Orchestrator |
| `decision.json` | Kernel, Runtime | VS Code, klyd |
| `kernel_execution_result.json` | Runtime (Wasm + CLI) | VS Code, klyd, Replay, Orchestrator |
| `event.json` | (future telemetry) | Replay, Cloud Dashboard |