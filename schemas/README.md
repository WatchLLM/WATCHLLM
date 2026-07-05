# WatchLLM Database Schemas

WatchLLM uses SQLite databases for various components. To prevent structural changes from breaking backward compatibility and corrupting local data, we employ strict schema versioning.

## Versioning Strategy

Every local database now contains a `migrations` table:
```sql
CREATE TABLE migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
)
```

During initialization:
1. The highest version is read from `migrations`.
2. If the table is empty (e.g. fresh installation), the current application's `SCHEMA_VERSION` is inserted.
3. If the DB version is lower than the application's `SCHEMA_VERSION`, the application will abort and prompt the user to upgrade their database.
4. If the DB version is higher than the application's `SCHEMA_VERSION`, the application will abort and prompt the user to upgrade the application.

## Current Schema Versions

### Klyd (`.klyd/memory.db`)
**Current Version:** `1`
- **Tables:** 
  - `migrations`
  - `decisions` (id, decision, module, file_patterns, confidence, event_type, reinforcement_count, last_seen_commit, created_at, flagged, archived, trace_id)

### Replay (`data/replay.sqlite`)
**Current Version:** `1`
- **Tables:**
  - `migrations`
  - `runs` (id, name, metadata, created_at)
  - `steps` (id, run_id, sequence, type, label, tool_name, input, output, state_before, state_after, created_at)
  - `edges` (id, run_id, source_step_id, target_step_id, relationship, created_at)
