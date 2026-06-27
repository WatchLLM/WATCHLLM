# CLI Contracts

> Machine-level interface contracts for `watchllm-kernel evaluate`.

## Subcommand: `evaluate`

Evaluates source code against the default rule set and returns a deterministic ALLOW or BLOCK decision.

### Invocation

```bash
watchllm-kernel evaluate [--stdin | <file>] [flags]
```

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `file` | path | Conditional | Path to source file. Required unless `--stdin` is used. |

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--stdin` | boolean | `false` | Read source from stdin instead of a file path. |
| `--language` | string | auto-detect | Language identifier: `javascript`, `typescript`, `tsx`. Inferred from file extension when omitted. |
| `--mode` | `enforce` \| `shadow` | `enforce` | Evaluation mode. `enforce` blocks on rule failure; `shadow` records but always allows. |
| `--json` | boolean | `false` | Output result as JSON to stdout. Default is human-readable text. |
| `--version` | — | — | Print version and exit. |

### Language Inference

When `--language` is not explicitly set, the kernel infers the language from the file extension:

| Extension | Language |
|-----------|----------|
| `.js`, `.jsx`, `.mjs`, `.cjs` | `javascript` |
| `.ts`, `.tsx` | `typescript` |

If neither `--language` nor a recognizable extension is present, language defaults to `None` and rules may produce INCONCLUSIVE results.

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Source passed all rules (Decision: ALLOW) |
| `1` | One or more rules blocked (Decision: BLOCK) |
| `2` | Runtime error (file read failure, invalid arguments, unsupported language) |

### JSON Output Schema

When `--json` is specified, the kernel writes a JSON object to stdout matching the `decision.json` schema:

```json
{
  "decision": "ALLOW | BLOCK",
  "rule_results": [
    {
      "rule_id": "string",
      "decision": "PASS | FAIL | INCONCLUSIVE",
      "violations": [
        {
          "rule_id": "string",
          "message": "string",
          "severity": "CRITICAL | HIGH | MEDIUM | LOW | INFO",
          "location": {
            "line": 42,
            "column": 5,
            "end_line": 42,
            "end_column": 25
          },
          "evidence": "string | null"
        }
      ]
    }
  ],
  "file_path": "string | null",
  "language": "string | null",
  "mode": "enforce | shadow"
}
```

### Human-Readable Output

Without `--json`, the kernel writes a stable text report:

```
Decision: BLOCK
File: src/auth.ts
Language: typescript
Mode: enforce
  - Hardcoded secret detected at line 12, col 5
  - DB mutation before auth guard at line 34, col 9
```

### Default Rule Set

The kernel evaluates source against these rules in order:

| # | Rule | Rule ID | Description |
|---|------|---------|-------------|
| 1 | Secret Literal | `secret-literal` | Detects hardcoded credentials. Optional — silently skipped if module unavailable. |
| 2 | Forbidden Import | `forbidden-import` | Blocks imports from a denylist of dangerous modules (e.g., `child_process`, `vm`). |
| 3 | Boundary | `boundary` | Enforces declared module boundary constraints. |
| 4 | Auth Flow | `auth-flow` | Detects DB mutations before authentication guards in handler scope. |

### Mode Behavior

| Mode | Rule Evaluation | Block on FAIL? | JSONL Log Written? |
|------|----------------|----------------|---------------------|
| `enforce` (default) | Runs all rules | Yes | Yes, on BLOCK |
| `shadow` | Runs all rules | Never (always ALLOW) | No |

In `shadow` mode, violations are still reported in output but never block the write path. This enables safe rollout and rule tuning without disrupting workflows.

### Blocked-Event Logging

When the kernel returns a BLOCK decision in `enforce` mode, a JSONL entry is appended to the violations log.

**Log path resolution order:**
1. Explicit path argument (programmatic API only)
2. `WATCHLLM_LOG_PATH` environment variable
3. Default: `.watchllm/logs/violations.jsonl` relative to CWD

**Log entry format** (one JSON object per line, matching `kernel_execution_result.json`):

```json
{
  "schema_version": "watchllm.kernel.violation_report.v1",
  "timestamp": "2026-06-25T00:00:00.000000+00:00",
  "decision": "BLOCK",
  "file_path": "src/api.ts",
  "language": "typescript",
  "mode": "enforce",
  "parse_status": "not_recorded",
  "violations": [ ... ]
}
```

### Example Invocations

```bash
# Evaluate a file
watchllm-kernel evaluate src/handler.ts

# Evaluate from stdin
cat src/handler.ts | watchllm-kernel evaluate --stdin

# Machine-readable output
watchllm-kernel evaluate --stdin --json < src/handler.ts

# Shadow mode (record but don't block)
watchllm-kernel evaluate src/handler.ts --mode shadow

# Explicit language override
watchllm-kernel evaluate --stdin --language javascript < bundle.js
```

## Error Handling Contract

| Condition | Exit Code | stderr Message |
|-----------|-----------|----------------|
| No subcommand or `--help` | 0 | Usage text to stdout |
| No file and no `--stdin` | 2 | `Error: either --stdin or a file path is required` |
| File not found / unreadable | 2 | `Error reading file <path>: <exception>` |
| Unsupported language | Raises ValueError | — |

## Rust Runtime CLI Parity

The Rust runtime (`watchllm-cli`) maintains exact argument and exit code parity with the Python kernel:

```bash
cargo run --bin watchllm-cli -- --stdin --json < src/handler.ts
```

The Rust runtime emits `KernelExecutionResult` (matching `schemas/v1/kernel_execution_result.json`) instead of the Python `KernelResult` shape, but maintains semantic equivalence.

## Stability Guarantees

- **Exit codes 0, 1, 2** are stable and will not change within major version 0.x.
- **JSON output structure** matches the published JSON Schema contracts. Fields may be added but not removed or re-typed.
- **Rule evaluation order** is deterministic and stable (secrets → imports → boundaries → auth-flow).
- **Language inference from extension** is stable.

Breaking changes to the CLI contract require a new schema version and a corresponding schema file in `schemas/v2/`.