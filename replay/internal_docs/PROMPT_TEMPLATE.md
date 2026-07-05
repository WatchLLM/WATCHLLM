⇒ WatchLLM Replay (Expansion B) — 8-Day Prompt Pack

Copy **one full day block** below into your agent session. Each block uses the same template; only task, gate, and scope placeholders are filled from `internal_docs/IMPORTANT.md`.

**Repo:** `watchllm/replay` (local: `d:\watchllm\replay`)

---

⇒ Day 01 — Task 01: Backend Skeleton & Database

⇒ Task Instructions

Today's task:
**REPLAY Task 01 — Backend Skeleton & Database**

Create the backend skeleton:

- Set up an Express.js server.
- Configure SQLite (e.g., using `better-sqlite3`).
- Create database tables: `runs` (session info), `steps` (tool calls, state changes), and `edges` (DAG relationships).

Today's gate:
- `npm run dev:backend` starts the Express server.
- The database file is created successfully with the correct schema on startup.

> Scope Constraints

Only work on:
- Express server setup and SQLite schema (Task 01 only)

Do NOT:
- add the ingestion endpoints yet
- write any frontend code

> Required Outputs

You must:
- implement the task narrowly
- verify server starts

> Validation Requirements

Before finishing:
- verify gate behavior

---

⇒ Day 02 — Task 02: Ingestion API

⇒ Task Instructions

Today's task:
**REPLAY Task 02 — Ingestion API**

Create the ingestion endpoints:

- `POST /api/runs` to start a trace.
- `POST /api/runs/:runId/steps` to append a tool call or state change.

Today's gate:
- A `curl` POST request successfully inserts a run and a step into the SQLite database.

> Scope Constraints

Only work on:
- Ingestion routes (Task 02 only)

Do NOT:
- build the Query API yet

> Required Outputs

You must:
- implement the task narrowly
- verify endpoints with curl or automated tests

> Validation Requirements

Before finishing:
- verify gate behavior

---

⇒ Day 03 — Task 03: Query API

⇒ Task Instructions

Today's task:
**REPLAY Task 03 — Query API**

Create the data access endpoints:

- `GET /api/runs` to list traces.
- `GET /api/runs/:runId/graph` to return the nodes and edges for visualization.

Today's gate:
- A `curl` GET request returns the previously ingested trace data in a clean JSON format.

> Scope Constraints

Only work on:
- Query routes (Task 03 only)

Do NOT:
- start frontend scaffolding

> Required Outputs

You must:
- implement the task narrowly
- write unit tests for the query endpoints

> Validation Requirements

Before finishing:
- verify gate behavior

---

⇒ Day 04 — Task 04: Frontend Skeleton

⇒ Task Instructions

Today's task:
**REPLAY Task 04 — Frontend Skeleton**

Scaffold the React application:

- Initialize a Vite + React + TypeScript app in `src/client`.
- Add `react-router-dom` and set up the layout (Sidebar, Main Content).
- Create a `RunsList` view to display traces fetched from `GET /api/runs`.

Today's gate:
- `npm run dev:frontend` runs the app and displays a list of ingested runs.

> Scope Constraints

Only work on:
- React/Vite scaffolding and the Runs list view (Task 04 only)

Do NOT:
- add DAG visualizations yet

> Required Outputs

You must:
- implement the task narrowly
- verify the frontend proxy connects to the backend

> Validation Requirements

Before finishing:
- verify gate behavior

---

⇒ Day 05 — Task 05: DAG Visualization

⇒ Task Instructions

Today's task:
**REPLAY Task 05 — DAG Visualization**

Implement the execution graph:

- Install `reactflow` (or similar DAG library).
- Create a `RunGraph` component that fetches `GET /api/runs/:runId/graph`.
- Render the steps as nodes and dependencies as edges.

Today's gate:
- Clicking a run in the frontend renders a directed acyclic graph of its tool calls.

> Scope Constraints

Only work on:
- `reactflow` integration and DAG rendering (Task 05 only)

Do NOT:
- build timeline replay yet

> Required Outputs

You must:
- implement the task narrowly
- verify graph visually renders

> Validation Requirements

Before finishing:
- verify gate behavior

---

⇒ Day 06 — Task 06: Timeline Replay

⇒ Task Instructions

Today's task:
**REPLAY Task 06 — Timeline Replay**

Add timeline controls:

- Create a playback component (Play, Pause, Step Forward, Step Back).
- Highlight the currently active node in the DAG based on the timeline state.

Today's gate:
- Clicking "Step Forward" highlights the next node in the execution graph sequentially.

> Scope Constraints

Only work on:
- Timeline state management and UI controls (Task 06 only)

> Required Outputs

You must:
- implement the task narrowly
- verify sequential traversal logic

> Validation Requirements

Before finishing:
- verify gate behavior

---

⇒ Day 07 — Task 07: Divergence View

⇒ Task Instructions

Today's task:
**REPLAY Task 07 — Divergence View**

Add state diffing:

- When a node is selected in the DAG, show the tool call arguments and the resulting state changes (file diffs, logs).
- Render code diffs clearly.

Today's gate:
- Selecting a step displays a "Before/After" diff of the modified files or state variables.

> Scope Constraints

Only work on:
- Node details pane and diff rendering (Task 07 only)

> Required Outputs

You must:
- implement the task narrowly
- verify diffs are legible

> Validation Requirements

Before finishing:
- verify gate behavior

---

⇒ Day 08 — Task 08: Polish & E2E

⇒ Task Instructions

Today's task:
**REPLAY Task 08 — Polish & E2E**

Finalize the observability suite:

- Add overall styling (CSS/Tailwind).
- Ensure `npm start` concurrently boots both frontend and backend.
- Write basic integration tests to verify the flow from ingestion to visualization.

Today's gate:
- `npm start` launches a polished, fully functioning Replay dashboard with zero errors.

> Scope Constraints

Only work on:
- Styling, build scripts, and tests (Task 08 only)

> Required Outputs

You must:
- implement the task narrowly
- verify concurrently running the app works seamlessly

> Validation Requirements

Before finishing:
- verify gate behavior
