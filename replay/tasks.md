# WatchLLM Replay Tasks

## Task 01 — Backend Skeleton & Database

Status: Complete

Gate:
- `npm run dev:backend` starts the Express server.
- The database file is created successfully with the correct schema on startup.

Scope:
- Set up an Express.js server.
- Configure SQLite (e.g., using `better-sqlite3`).
- Create database tables: `runs`, `steps`, and `edges`.

Non-goals:
- Ingestion endpoints
- Frontend code

---

## Task 02 — Ingestion API

Status: Complete

Gate:
- A `curl` POST request successfully inserts a run and a step into the SQLite database.

Scope:
- `POST /api/runs` to start a trace.
- `POST /api/runs/:runId/steps` to append a tool call or state change.

Non-goals:
- Query API

---

## Task 03 — Query API

Status: Complete

Gate:
- A `curl` GET request returns the previously ingested trace data in a clean JSON format.

Scope:
- `GET /api/runs` to list traces.
- `GET /api/runs/:runId/graph` to return the nodes and edges for visualization.

Non-goals:
- Frontend scaffolding

---

## Task 04 — Frontend Skeleton

Status: Complete

Gate:
- `npm run dev:frontend` runs the app and displays a list of ingested runs.

Scope:
- Initialize a Vite + React + TypeScript app in `src/client`.
- Add `react-router-dom` and set up the layout.
- Create a `RunsList` view.

Non-goals:
- DAG visualizations

---

## Task 05 — DAG Visualization

Status: Complete

Gate:
- Clicking a run in the frontend renders a directed acyclic graph of its tool calls.

Scope:
- Install `reactflow`.
- Create a `RunGraph` component.
- Render the steps as nodes and dependencies as edges.

Non-goals:
- Timeline replay

---

## Task 06 — Timeline Replay

Status: Complete

Gate:
- Clicking "Step Forward" highlights the next node in the execution graph sequentially.

Scope:
- Create a playback component.
- Highlight the currently active node in the DAG.

---

## Task 07 — Divergence View

Status: Complete

Gate:
- Selecting a step displays a "Before/After" diff of the modified files or state variables.

Scope:
- Show tool call arguments and resulting state changes (file diffs, logs).
- Render code diffs clearly.

---

## Task 08 — Polish & E2E

Status: Complete

Gate:
- `npm start` launches a polished, fully functioning Replay dashboard with zero errors.

Scope:
- Add overall styling.
- Update `package.json` to concurrently boot both frontend and backend.
- Write basic integration tests.
