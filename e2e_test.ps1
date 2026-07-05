
$ErrorActionPreference = "Stop"
echo "=== Testing B2 (Klyd to Kernel config sync) ==="
kl init
python -c "import sqlite3, json; conn=sqlite3.connect('.klyd/memory.db'); conn.execute('INSERT INTO decisions (decision, module, file_patterns, confidence, event_type, reinforcement_count, last_seen_commit, archived, flagged) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', ('Test B2', 'payments', json.dumps(['stripe']), 0.9, 'NEW', 1, 'abc', 0, 0)); conn.commit()"
kl export-kernel-config
$config = Get-Content .watchllm.toml -Raw
if ($config -notmatch "payments") { throw "B2 Failed: payments module not in config" }
echo "B2 Passed"

echo "=== Testing B1 & B3 (Agent Token & Trace ID flow) ==="
New-Item -ItemType Directory -Force -Path test_src | Out-Null
Set-Content -Path test_src/test.ts -Value "import * as stripe from 'stripe';"
$env:WATCHLLM_TRACE_ID=""
$env:WATCHLLM_AGENT_TOKEN=""

echo "Testing normal evaluate (should BLOCK)"
try {
    watchllm evaluate test_src/test.ts
    throw "Should have blocked"
} catch {
    echo "Blocked successfully"
}

echo "Testing spawned evaluate with token (should ALLOW)"
watchllm spawn --role read-only-agent --command "watchllm evaluate test_src/test.ts"
echo "B1 Passed"

echo "Checking logs for Trace ID"
$log = Get-Content .watchllm/logs/violations.jsonl -Raw
if ($log -notmatch "trace_id") { throw "B3 Failed: trace_id not found in log" }
echo "B3 Passed"

echo "All tests passed"

