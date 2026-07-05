# WatchLLM Replay

## 0) Purpose

This document defines the **Replay layer (Expansion B)** for WatchLLM. The goal of this layer is to take the execution logs, tool call traces, and state changes recorded by the Kernel and visualize them. This provides developers and security teams with an observability suite to replay agent histories in a visual timeline, perform branch comparisons, and analyze hallucinations with lineage tracing.

---

## 1) Scope

### In scope
* A backend ingestion API (`Express.js` + `SQLite`) to passively receive and store execution events.
* A frontend web application (`React` + `Vite`) to visualize traces.
* Visual execution graphs (DAGs) using libraries like `React Flow`.
* Timeline step-by-step replay UI.
* Divergence lineage and state diffing views.

### Out of scope
* Defining new kernel security rules.
* Any active agent orchestration (Replay does not execute agents, it only visualizes past runs).
* Modifying the editor extension or the kernel.
* Inline security enforcement (Replay is purely a diagnostics and forensics tool).

---

## 2) Architecture rules

### 2.1 The Passive Observer Rule
Replay must never interact with or block a running agent. It strictly ingests `POST` requests containing JSON traces sent by the agent or kernel.

### 2.2 The Immutable Ledger Rule
Trace events and execution graphs must be treated as append-only. Once ingested, a log entry or state change cannot be altered. 

### 2.3 The Visual Fidelity Rule
The UI must accurately reflect the chronological order of tool calls and state mutations. Divergences must be clearly highlighted.

---

## 3) Implementation order

1. **Backend Skeleton & Database**: Express setup + SQLite schema for runs, steps, and tool calls.
2. **Ingestion API**: Endpoints to ingest stream of JSON events.
3. **Query API**: Endpoints to fetch runs, timeline events, and DAG relationships.
4. **Frontend Skeleton**: Vite + React scaffold and routing.
5. **DAG Visualization**: Implementing `React Flow` to visualize the execution graph.
6. **Timeline Replay**: Step-by-step timeline component to step backward/forward in time.
7. **Divergence View**: Diffing component to see state changes before/after a tool call.
8. **Polish & E2E**: Styling, error handling, and end-to-end tests.

---

## 4) Definition of done
* A developer can send mock trace events via HTTP POST to the backend.
* The React frontend successfully displays the graph and timeline of the mock trace.
* The system is packaged and run easily via `npm start`.
