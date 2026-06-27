# WatchLLM Replay Audit Specification (Phase 5 — Replay Engine)

This document defines the expected perfect state of the **WatchLLM Replay Engine** (Phase 5). It outlines the architecture, rules, interface contracts, and edge cases necessary to pass a complete verification run.

---

## 1. Purpose & Scope
Replay is an execution graph and observability suite for autonomous AI coding agents. It ingests execution events (tool calls, state modifications, LLM generations), saves them to an append-only ledger, and displays them via a visual React-based web dashboard. Replay is a diagnostic tool; it does not block or execute code itself.

---

## 2. Expected Directory & File Layout
A perfect implementation must contain:
```
d:\watchllm\replay\
├── src/
│   ├── server/                   # Backend Express.js server & SQLite db
│   │   ├── index.cjs             # API endpoints & routing
│   │   └── db.cjs                # SQLite schema (runs, steps, traces)
│   └── client/                   # Frontend React + Vite SPA
│       ├── index.html
│       ├── tsconfig.json
│       └── src/
│           ├── main.tsx          # App entrypoint
│           ├── App.tsx           # Layout & Routing
│           ├── components/
│           │   ├── DagGraph.tsx  # React Flow graph visualization (DAG)
│           │   ├── Timeline.tsx  # Playback step slider & list
│           │   └── DiffView.tsx  # Divergence / state change viewer
│           └── api.ts            # Client HTTP fetch layer
├── public/                       # Static web assets
├── test/
│   ├── server.test.js            # API endpoint integration tests
│   └── mock_traces.json          # Mock trace files for ingestion validation
├── package.json                  # Workspace client/server scripts
├── vite.config.ts                # Bundler configurations
└── tasks.md                      # Active gate checklist
```

---

## 3. Core Component Responsibilities & Interface Contracts

### A. Ingestion API (Passive & Immutable)
- **POST `/api/runs`**: Initialize a new agent run trace.
- **POST `/api/events`**: Ingest tool execution, state change, or decision logs.
- The backend must treat all entries as immutable. Update endpoints are not permitted; traces are append-only.

### B. Query API
- **GET `/api/runs`**: Retrieve a history of all recorded runs.
- **GET `/api/runs/:id`**: Get specific metadata and event counts for a run.
- **GET `/api/runs/:id/graph`**: Retrieve node relationships formatted for `React Flow` (Directed Acyclic Graph structure).
- **GET `/api/runs/:id/timeline`**: Retrieve chronologically sorted step listings.

### C. Frontend Dashboard (Vite + React)
- **Runs View**: Dashboard displaying recent runs, status (success, failed, blocked), and cost metrics.
- **DAG View**: Interactive node graph utilizing `React Flow` mapping execution paths (tool requests pointing to tool outputs).
- **Timeline Slider**: Step forward and backward buttons to animate state evolution line-by-line.
- **Divergence View**: Text-diff pane showing before/after changes of code variables or files touched during a selected step.

---

## 4. SQLite Database Schema (`replay.db`)
The backend database must define:
- `runs`: id (UUID), name, status, agent_id, started_at, completed_at, total_tokens, total_cost.
- `steps`: id, run_id, sequence_number, type (tool, LLM, kernel_decision), name, details, created_at.
- `state_diffs`: id, step_id, file_path, pre_state, post_state.

---

## 5. Critical Edge Cases & Error Recovery

| Edge Case | Expected Perfect Behavior |
|---|---|
| **Out-of-Order Ingestion** | Network lag can cause trace events to arrive out of chronological order. The server must sort events by `sequence_number` or client-side microsecond timestamps before insertion. |
| **Cyclic Dependencies** | In case of loops (e.g. agent repeating a tool call), the frontend DAG renderer must handle back-edges without throwing recursion errors or crashing `React Flow`. |
| **High Egress Volume** | If an agent runs a massive task (generating thousands of trace events), the API must batch writes using SQLite transactions to prevent API timeouts. |
| **Partial Traces** | If an agent execution is forcefully terminated (e.g. CLI killed), the backend must render the partial graph correctly and flag the run status as `DIVERGED` or `CRASHED` after a heartbeat timeout. |

---

## 6. Verification Checklist
To confirm Replay compliance, run:
1. **Server Ingestion Test**: Spin up the backend and post mock logs:
   ```bash
   node src/server/index.cjs
   curl -X POST -H "Content-Type: application/json" -d @test/mock_traces.json http://localhost:3000/api/events
   ```
2. **Frontend Compilation**: Run client assets compile:
   ```bash
   npm run build
   ```
3. **Integration Verify**: Run backend unit tests:
   ```bash
   npm run test
   ```
4. **Visual Inspection**: Open dashboard at `http://localhost:5173/` and verify:
   - DAG renders nodes cleanly without overlaps.
   - Timeline playback successfully moves execution markers.
   - Code diff displays correctly highlighted line additions/removals.
