const Database = require('better-sqlite3');
const fs = require('fs');
const path = require('path');

const dbPath = process.env.REPLAY_DB_PATH
  ? path.resolve(process.env.REPLAY_DB_PATH)
  : path.join(process.cwd(), 'data', 'replay.sqlite');

fs.mkdirSync(path.dirname(dbPath), { recursive: true });

const db = new Database(dbPath);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

const SCHEMA_VERSION = 1;

db.exec(`
  CREATE TABLE IF NOT EXISTS migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
  );
`);

const versionRow = db.prepare('SELECT MAX(version) as version FROM migrations').get();
let currentVersion = versionRow && versionRow.version ? versionRow.version : 0;

if (currentVersion === 0) {
  db.prepare('INSERT INTO migrations (version) VALUES (?)').run(SCHEMA_VERSION);
  currentVersion = SCHEMA_VERSION;
}

if (currentVersion < SCHEMA_VERSION) {
  console.error(`Error: Database schema version ${currentVersion} is out of date. Expected ${SCHEMA_VERSION}. Please upgrade your database.`);
  process.exit(1);
} else if (currentVersion > SCHEMA_VERSION) {
  console.error(`Error: Database schema version ${currentVersion} is newer than expected ${SCHEMA_VERSION}. Please upgrade the server.`);
  process.exit(1);
}

db.exec(`
  CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    name TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS steps (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    type TEXT NOT NULL,
    label TEXT,
    tool_name TEXT,
    input TEXT,
    output TEXT,
    state_before TEXT,
    state_after TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runs(id),
    UNIQUE (run_id, sequence)
  );

  CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    source_step_id TEXT NOT NULL,
    target_step_id TEXT NOT NULL,
    relationship TEXT NOT NULL DEFAULT 'next',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runs(id),
    FOREIGN KEY (source_step_id) REFERENCES steps(id),
    FOREIGN KEY (target_step_id) REFERENCES steps(id),
    UNIQUE (run_id, source_step_id, target_step_id, relationship)
  );

  CREATE INDEX IF NOT EXISTS idx_steps_run_id ON steps(run_id);
  CREATE INDEX IF NOT EXISTS idx_steps_run_sequence ON steps(run_id, sequence);
  CREATE INDEX IF NOT EXISTS idx_edges_run_id ON edges(run_id);
  CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_step_id);
  CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_step_id);

  CREATE TRIGGER IF NOT EXISTS prevent_runs_update
  BEFORE UPDATE ON runs
  BEGIN
    SELECT RAISE(ABORT, 'runs table is append-only');
  END;

  CREATE TRIGGER IF NOT EXISTS prevent_runs_delete
  BEFORE DELETE ON runs
  BEGIN
    SELECT RAISE(ABORT, 'runs table is append-only');
  END;

  CREATE TRIGGER IF NOT EXISTS prevent_steps_update
  BEFORE UPDATE ON steps
  BEGIN
    SELECT RAISE(ABORT, 'steps table is append-only');
  END;

  CREATE TRIGGER IF NOT EXISTS prevent_steps_delete
  BEFORE DELETE ON steps
  BEGIN
    SELECT RAISE(ABORT, 'steps table is append-only');
  END;

  CREATE TRIGGER IF NOT EXISTS prevent_edges_update
  BEFORE UPDATE ON edges
  BEGIN
    SELECT RAISE(ABORT, 'edges table is append-only');
  END;

  CREATE TRIGGER IF NOT EXISTS prevent_edges_delete
  BEFORE DELETE ON edges
  BEGIN
    SELECT RAISE(ABORT, 'edges table is append-only');
  END;
`);

module.exports = {
  db,
  dbPath,
};
